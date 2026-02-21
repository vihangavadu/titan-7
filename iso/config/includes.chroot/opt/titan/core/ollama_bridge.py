"""
TITAN V7.5 SINGULARITY — Multi-Provider LLM Bridge
Unified LLM integration supporting multiple providers with task-specific routing.

Supported Providers:
    - Ollama (local)
    - OpenAI (GPT-4o, GPT-4o-mini)
    - Anthropic (Claude 3.5 Sonnet)
    - Groq (Llama 3.1 70B — fast inference)
    - OpenRouter (any model via unified API)

Architecture:
    1. Config loaded from /opt/titan/config/llm_config.json
    2. Task type → route to best available provider+model
    3. Provider tried in priority order; first success wins
    4. Results cached to /opt/titan/data/llm_cache/<key>.json
    5. Falls back to seed data if all providers fail

Backward Compatibility:
    All original functions (generate_with_cache, query_ollama_json, etc.)
    are preserved with identical signatures. Existing callers need zero changes.
"""

import json
import hashlib
import logging
import time
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("TITAN-LLM")

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

_CONFIG_PATH = Path("/opt/titan/config/llm_config.json")
_CONFIG: Dict = {}
_PROVIDER_STATUS: Dict[str, Any] = {}  # cached availability checks: key -> (timestamp, bool)


def _load_config() -> Dict:
    """Load LLM config from disk. Falls back to minimal defaults."""
    global _CONFIG
    if _CONFIG:
        return _CONFIG

    # Try primary config path
    for cfg_path in [_CONFIG_PATH, Path(__file__).parent.parent / "config" / "llm_config.json"]:
        if cfg_path.exists():
            try:
                _CONFIG = json.loads(cfg_path.read_text())
                logger.info(f"LLM config loaded from {cfg_path}")
                return _CONFIG
            except Exception as e:
                logger.warning(f"Failed to parse {cfg_path}: {e}")

    # Env-var fallback (backward compat)
    _CONFIG = {
        "providers": {
            "ollama": {
                "enabled": True,
                "api_key": "",
                "base_url": os.environ.get("OLLAMA_API", "http://127.0.0.1:11434"),
                # V7.5 FIX: Use correct default model installed on VPS
                "default_model": os.environ.get("OLLAMA_MODEL", "mistral:7b-instruct-v0.2-q4_0"),
                "max_retries": 1,
                "timeout": 180,
            }
        },
        "task_routing": {
            "default": [{"provider": "ollama", "model": "mistral:7b-instruct-v0.2-q4_0"}]
        },
        "cache": {
            "enabled": True,
            "directory": "/opt/titan/data/llm_cache",
            "ttl_hours": int(os.environ.get("OLLAMA_CACHE_TTL", "24")),
        },
        "global": {
            "default_temperature": 0.3,
            "default_max_tokens": 8192,
            "log_prompts": False,
            "log_responses": False,
        },
    }
    logger.info("Using default LLM config (no config file found)")
    return _CONFIG


def reload_config():
    """Force reload config from disk."""
    global _CONFIG, _PROVIDER_STATUS
    _CONFIG = {}
    _PROVIDER_STATUS = {}
    return _load_config()


def get_config() -> Dict:
    """Return current config (read-only copy)."""
    return dict(_load_config())


# ═══════════════════════════════════════════════════════════════════════════════
# PROVIDER HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _provider_cfg(name: str) -> Dict:
    """Get config dict for a provider."""
    cfg = _load_config()
    return cfg.get("providers", {}).get(name, {})


def _api_key(provider: str) -> str:
    """Resolve API key: config file → env var → empty."""
    pcfg = _provider_cfg(provider)
    key = pcfg.get("api_key", "")
    if key:
        return key
    # Env var fallback: OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.
    env_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "groq": "GROQ_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
    }
    return os.environ.get(env_map.get(provider, ""), "")


def _is_provider_enabled(provider: str) -> bool:
    """Check if a provider is enabled in config."""
    pcfg = _provider_cfg(provider)
    if not pcfg.get("enabled", False):
        return False
    # Cloud providers need an API key
    if provider != "ollama" and not _api_key(provider):
        return False
    return True


def _check_provider_available(provider: str) -> bool:
    """Check if a provider is reachable. Results are cached for 5 min."""
    global _PROVIDER_STATUS
    cache_key = f"{provider}_avail"
    cached = _PROVIDER_STATUS.get(cache_key)
    if cached is not None:
        ts, val = cached
        if time.time() - ts < 300:  # 5 min cache
            return val

    available = False
    try:
        if provider == "ollama":
            available = _check_ollama()
        else:
            available = _check_cloud_provider(provider)
    except Exception as e:
        logger.debug(f"Provider {provider} check failed: {e}")

    _PROVIDER_STATUS[cache_key] = (time.time(), available)
    return available


def _check_ollama() -> bool:
    """Check if Ollama is running locally."""
    pcfg = _provider_cfg("ollama")
    base = pcfg.get("base_url", "http://127.0.0.1:11434")
    try:
        proc = subprocess.run(
            ["curl", "-s", "--max-time", "3", f"{base}/api/tags"],
            capture_output=True, text=True, timeout=5
        )
        if proc.returncode == 0 and proc.stdout:
            data = json.loads(proc.stdout)
            return "models" in data
    except Exception:
        pass
    return False


def _check_cloud_provider(provider: str) -> bool:
    """Quick health check for a cloud provider."""
    pcfg = _provider_cfg(provider)
    base = pcfg.get("base_url", "")
    key = _api_key(provider)
    if not base or not key:
        return False

    try:
        if provider == "anthropic":
            # Anthropic uses a different auth header
            proc = subprocess.run(
                ["curl", "-s", "--max-time", "5",
                 "-H", f"x-api-key: {key}",
                 "-H", "anthropic-version: 2023-06-01",
                 f"{base}/messages"],
                capture_output=True, text=True, timeout=8
            )
            # Even a 400 means the API is reachable
            return proc.returncode == 0 and len(proc.stdout) > 0
        else:
            # OpenAI-compatible: openai, groq, openrouter
            proc = subprocess.run(
                ["curl", "-s", "--max-time", "5",
                 "-H", f"Authorization: Bearer {key}",
                 f"{base}/models"],
                capture_output=True, text=True, timeout=8
            )
            if proc.returncode == 0 and proc.stdout:
                data = json.loads(proc.stdout)
                return "data" in data or "error" not in data
    except Exception:
        pass
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# TASK-SPECIFIC MODEL ROUTING
# ═══════════════════════════════════════════════════════════════════════════════

TASK_TYPES = [
    "bin_generation",
    "site_discovery",
    "preset_generation",
    "country_profiles",
    "dork_generation",
    "warmup_searches",
    "default",
]


def resolve_provider_for_task(task_type: str = "default") -> Optional[Tuple[str, str]]:
    """
    Resolve the best available provider+model for a given task type.

    Walks the priority list in llm_config.json → task_routing → <task_type>.
    Returns (provider_name, model_name) or None if nothing is available.
    """
    cfg = _load_config()
    routing = cfg.get("task_routing", {})
    candidates = routing.get(task_type, routing.get("default", []))

    for entry in candidates:
        prov = entry.get("provider", "")
        model = entry.get("model", "")
        if not _is_provider_enabled(prov):
            continue
        if _check_provider_available(prov):
            logger.debug(f"Task '{task_type}' → {prov}/{model}")
            return (prov, model)

    logger.warning(f"No available provider for task '{task_type}'")
    return None


def get_provider_status() -> Dict[str, Dict]:
    """Return status of all configured providers."""
    cfg = _load_config()
    status = {}
    for name, pcfg in cfg.get("providers", {}).items():
        has_key = bool(_api_key(name)) if name != "ollama" else True
        status[name] = {
            "enabled": pcfg.get("enabled", False),
            "has_api_key": has_key,
            "available": _check_provider_available(name) if pcfg.get("enabled") and has_key else False,
            "default_model": pcfg.get("default_model", ""),
        }
    return status


# ═══════════════════════════════════════════════════════════════════════════════
# CACHE LAYER
# ═══════════════════════════════════════════════════════════════════════════════

def _cache_dir() -> Path:
    cfg = _load_config()
    return Path(cfg.get("cache", {}).get("directory", "/opt/titan/data/llm_cache"))


def _cache_ttl() -> int:
    cfg = _load_config()
    return cfg.get("cache", {}).get("ttl_hours", 24)


def _cache_path(key: str) -> Path:
    """Get cache file path for a given key."""
    safe = hashlib.sha256(key.encode()).hexdigest()[:16]
    return _cache_dir() / f"{safe}.json"


def _cache_valid(path: Path) -> bool:
    """Check if cache file exists and is within TTL."""
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text())
        cached_at = datetime.fromisoformat(data.get("_cached_at", "2000-01-01"))
        # V7.5 FIX: Use timezone-aware datetime
        now = datetime.now(timezone.utc)
        if cached_at.tzinfo is None:
            cached_at = cached_at.replace(tzinfo=timezone.utc)
        return now - cached_at < timedelta(hours=_cache_ttl())
    except Exception:
        return False


def _read_cache(path: Path) -> Optional[Any]:
    """Read cached data."""
    try:
        data = json.loads(path.read_text())
        return data.get("result")
    except Exception:
        return None


def _write_cache(path: Path, result: Any, key: str, provider: str = "", model: str = ""):
    """Write result to cache."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "_cached_at": datetime.now(timezone.utc).isoformat(),
            "_key": key,
            "_provider": provider,
            "_model": model,
            "result": result,
        }
        path.write_text(json.dumps(data, indent=2, default=str))
    except Exception as e:
        logger.warning(f"Cache write failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# PROVIDER-SPECIFIC QUERY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _query_ollama(prompt: str, model: str, temperature: float,
                  max_tokens: int, timeout: int) -> Optional[str]:
    """Send prompt to local Ollama instance."""
    pcfg = _provider_cfg("ollama")
    base = pcfg.get("base_url", "http://127.0.0.1:11434")

    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        }
    })

    try:
        proc = subprocess.run(
            ["curl", "-s", "--max-time", str(timeout),
             "-X", "POST", f"{base}/api/generate",
             "-H", "Content-Type: application/json",
             "-d", payload],
            capture_output=True, text=True, timeout=timeout + 10
        )
        if proc.returncode == 0 and proc.stdout:
            data = json.loads(proc.stdout)
            return data.get("response", "").strip()
    except subprocess.TimeoutExpired:
        logger.warning(f"Ollama timed out after {timeout}s")
    except Exception as e:
        logger.warning(f"Ollama query failed: {e}")
    return None


def _query_openai_compatible(provider: str, prompt: str, model: str,
                              temperature: float, max_tokens: int,
                              timeout: int) -> Optional[str]:
    """Query OpenAI-compatible API (OpenAI, Groq, OpenRouter)."""
    pcfg = _provider_cfg(provider)
    base = pcfg.get("base_url", "")
    key = _api_key(provider)

    headers = [
        "-H", f"Authorization: Bearer {key}",
        "-H", "Content-Type: application/json",
    ]
    # OpenRouter needs extra headers
    if provider == "openrouter":
        headers += ["-H", "HTTP-Referer: https://titan-os.local",
                    "-H", "X-Title: TITAN-LLM"]

    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a precise data generation assistant. Always respond with valid JSON only. No markdown, no explanation, no code fences."},
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    })

    try:
        cmd = ["curl", "-s", "--max-time", str(timeout),
               "-X", "POST", f"{base}/chat/completions"] + headers + ["-d", payload]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)

        if proc.returncode == 0 and proc.stdout:
            data = json.loads(proc.stdout)
            if "choices" in data and data["choices"]:
                msg = data["choices"][0].get("message", {})
                return msg.get("content", "").strip()
            if "error" in data:
                logger.warning(f"{provider} API error: {data['error']}")
    except subprocess.TimeoutExpired:
        logger.warning(f"{provider} timed out after {timeout}s")
    except Exception as e:
        logger.warning(f"{provider} query failed: {e}")
    return None


def _query_anthropic(prompt: str, model: str, temperature: float,
                     max_tokens: int, timeout: int) -> Optional[str]:
    """Query Anthropic Claude API."""
    pcfg = _provider_cfg("anthropic")
    base = pcfg.get("base_url", "https://api.anthropic.com/v1")
    key = _api_key("anthropic")

    payload = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": "You are a precise data generation assistant. Always respond with valid JSON only. No markdown, no explanation, no code fences.",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    })

    try:
        proc = subprocess.run(
            ["curl", "-s", "--max-time", str(timeout),
             "-X", "POST", f"{base}/messages",
             "-H", f"x-api-key: {key}",
             "-H", "anthropic-version: 2023-06-01",
             "-H", "Content-Type: application/json",
             "-d", payload],
            capture_output=True, text=True, timeout=timeout + 10
        )
        if proc.returncode == 0 and proc.stdout:
            data = json.loads(proc.stdout)
            if "content" in data and data["content"]:
                # Anthropic returns content as array of blocks
                text_blocks = [b["text"] for b in data["content"] if b.get("type") == "text"]
                return "\n".join(text_blocks).strip()
            if "error" in data:
                logger.warning(f"Anthropic API error: {data['error']}")
    except subprocess.TimeoutExpired:
        logger.warning(f"Anthropic timed out after {timeout}s")
    except Exception as e:
        logger.warning(f"Anthropic query failed: {e}")
    return None


def _query_provider(provider: str, prompt: str, model: str,
                    temperature: float, max_tokens: int,
                    timeout: int) -> Optional[str]:
    """Route query to the correct provider function."""
    if provider == "ollama":
        return _query_ollama(prompt, model, temperature, max_tokens, timeout)
    elif provider == "anthropic":
        return _query_anthropic(prompt, model, temperature, max_tokens, timeout)
    elif provider in ("openai", "groq", "openrouter"):
        return _query_openai_compatible(provider, prompt, model, temperature, max_tokens, timeout)
    else:
        logger.error(f"Unknown provider: {provider}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# JSON EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_json(text: str) -> Optional[Any]:
    """Extract JSON from LLM response text, handling common formatting issues."""
    text = text.strip()
    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON array or object in text
    for start_char, end_char in [("[", "]"), ("{", "}")]:
        start = text.find(start_char)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            if text[i] == start_char:
                depth += 1
            elif text[i] == end_char:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i+1])
                    except json.JSONDecodeError:
                        break

    return None


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API — Backward-compatible + new task-routed interface
# ═══════════════════════════════════════════════════════════════════════════════

def query_llm(prompt: str, task_type: str = "default",
              provider: str = None, model: str = None,
              temperature: float = None, max_tokens: int = None,
              timeout: int = None) -> Optional[str]:
    """
    Send a prompt to the best available LLM for the given task.

    New unified entry point. Resolves provider via task routing unless
    provider/model are explicitly given.

    Returns raw text response or None.
    """
    cfg = _load_config()
    gcfg = cfg.get("global", {})
    temperature = temperature if temperature is not None else gcfg.get("default_temperature", 0.3)
    max_tokens = max_tokens or gcfg.get("default_max_tokens", 8192)

    # Explicit provider override
    if provider and model:
        pcfg = _provider_cfg(provider)
        timeout = timeout or pcfg.get("timeout", 120)
        retries = pcfg.get("max_retries", 2)
        for attempt in range(retries + 1):
            result = _query_provider(provider, prompt, model, temperature, max_tokens, timeout)
            if result is not None:
                return result
            if attempt < retries:
                time.sleep(1)
        return None

    # Task-based routing: try each candidate
    routing = cfg.get("task_routing", {})
    candidates = routing.get(task_type, routing.get("default", []))

    for entry in candidates:
        prov = entry.get("provider", "")
        mdl = entry.get("model", "")
        if not _is_provider_enabled(prov):
            continue
        pcfg = _provider_cfg(prov)
        tout = timeout or pcfg.get("timeout", 120)
        retries = pcfg.get("max_retries", 2)

        for attempt in range(retries + 1):
            result = _query_provider(prov, prompt, mdl, temperature, max_tokens, tout)
            if result is not None:
                logger.info(f"[{task_type}] Success via {prov}/{mdl}")
                return result
            if attempt < retries:
                time.sleep(0.5)

    return None


def query_llm_json(prompt: str, task_type: str = "default",
                   **kwargs) -> Optional[Any]:
    """
    Send a prompt expecting JSON response. Wraps query_llm + JSON extraction.
    """
    full_prompt = (
        f"{prompt}\n\n"
        "IMPORTANT: Respond ONLY with valid JSON. No markdown, no explanation, "
        "no code fences. Just the raw JSON array or object."
    )
    raw = query_llm(full_prompt, task_type=task_type, **kwargs)
    if not raw:
        return None
    return _extract_json(raw)


# --- Backward-compatible wrappers (existing callers use these) ---

# Legacy globals for backward compat
OLLAMA_API = os.environ.get("OLLAMA_API", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "mistral:7b-instruct-v0.2-q4_0")
CACHE_DIR = _cache_dir()
CACHE_TTL_HOURS = _cache_ttl()


def is_ollama_available() -> bool:
    """Check if ANY LLM provider is available (not just Ollama)."""
    cfg = _load_config()
    for name in cfg.get("providers", {}):
        if _is_provider_enabled(name) and _check_provider_available(name):
            return True
    return False


def get_available_models() -> List[str]:
    """List available models across all providers."""
    models = []
    cfg = _load_config()
    for name, pcfg in cfg.get("providers", {}).items():
        if _is_provider_enabled(name) and _check_provider_available(name):
            models.append(f"{name}/{pcfg.get('default_model', 'unknown')}")
    return models


def query_ollama(prompt: str, model: str = None, temperature: float = 0.7,
                 max_tokens: int = 4096, timeout: int = 120) -> Optional[str]:
    """
    Backward-compatible: send prompt to best available provider.
    Original callers pass no task_type, so we use 'default' routing.
    """
    return query_llm(prompt, task_type="default", temperature=temperature,
                     max_tokens=max_tokens, timeout=timeout)


def query_ollama_json(prompt: str, model: str = None, temperature: float = 0.3,
                      max_tokens: int = 8192, timeout: int = 180) -> Optional[Any]:
    """Backward-compatible: query expecting JSON via best available provider."""
    return query_llm_json(prompt, task_type="default", temperature=temperature,
                          max_tokens=max_tokens, timeout=timeout)


def generate_with_cache(cache_key: str, prompt: str, fallback: Any = None,
                        model: str = None, temperature: float = 0.3,
                        max_tokens: int = 8192, timeout: int = 180,
                        task_type: str = "default") -> Any:
    """
    Generate data via LLM with caching. Backward-compatible + new task_type param.

    1. Check cache → return if valid
    2. Route to best provider for task_type → parse JSON → cache → return
    3. Fall back to provided fallback data if all providers fail
    """
    path = _cache_path(cache_key)

    # Check cache
    if _cache_valid(path):
        cached = _read_cache(path)
        if cached is not None:
            logger.info(f"Cache hit for '{cache_key}'")
            return cached

    # Resolve provider for logging
    resolved = resolve_provider_for_task(task_type)
    prov_name = f"{resolved[0]}/{resolved[1]}" if resolved else "none"
    logger.info(f"Generating '{cache_key}' via {prov_name} (task={task_type})...")

    result = query_llm_json(prompt, task_type=task_type, temperature=temperature,
                            max_tokens=max_tokens, timeout=timeout)

    if result is not None:
        _write_cache(path, result, cache_key,
                     provider=resolved[0] if resolved else "",
                     model=resolved[1] if resolved else "")
        logger.info(f"Generated and cached '{cache_key}': {type(result).__name__}")
        return result

    # Fallback
    logger.warning(f"All providers failed for '{cache_key}', using fallback data")
    return fallback


def invalidate_cache(cache_key: str = None):
    """Invalidate cache for a specific key, or all cache if key is None."""
    cdir = _cache_dir()
    if cache_key:
        path = _cache_path(cache_key)
        if path.exists():
            path.unlink()
            logger.info(f"Invalidated cache: {cache_key}")
    else:
        if cdir.exists():
            for f in cdir.glob("*.json"):
                f.unlink()
            logger.info("Invalidated all LLM cache")


def get_cache_stats() -> Dict:
    """Get cache statistics."""
    cdir = _cache_dir()
    if not cdir.exists():
        return {"total_files": 0, "total_size_kb": 0, "cache_dir": str(cdir)}

    files = list(cdir.glob("*.json"))
    total_size = sum(f.stat().st_size for f in files)

    return {
        "total_files": len(files),
        "total_size_kb": round(total_size / 1024, 1),
        "cache_dir": str(cdir),
        "providers": get_provider_status(),
        "any_available": is_ollama_available(),
    }
