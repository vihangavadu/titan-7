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


# =============================================================================
# TITAN V7.6 P0 CRITICAL ENHANCEMENTS
# =============================================================================

import threading
import random
from collections import deque
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class ProviderHealth:
    """Health status for an LLM provider"""
    provider: str
    model: str
    is_healthy: bool
    latency_ms: float
    success_rate: float
    last_check: float
    consecutive_failures: int = 0


@dataclass
class LLMUsageRecord:
    """Record of LLM API usage"""
    provider: str
    model: str
    task_type: str
    tokens_sent: int
    tokens_received: int
    latency_ms: float
    cost_estimate: float
    timestamp: float
    success: bool


@dataclass
class PromptTemplate:
    """Template for prompt optimization"""
    name: str
    task_type: str
    template: str
    system_prompt: str = ""
    temperature: float = 0.3
    max_tokens: int = 8192


class LLMLoadBalancer:
    """
    V7.6 P0 CRITICAL: Load balance across multiple LLM providers.
    
    Distributes requests across providers based on health, latency,
    and configured weights to maximize reliability and performance.
    
    Usage:
        balancer = get_llm_load_balancer()
        
        # Configure providers with weights
        balancer.add_provider("ollama", "mistral:7b", weight=1.0)
        balancer.add_provider("groq", "llama-3.1-70b", weight=2.0)
        
        # Get next provider
        provider, model = balancer.get_next_provider("bin_generation")
    """
    
    def __init__(self):
        self.providers: Dict[str, Dict] = {}
        self.health_status: Dict[str, ProviderHealth] = {}
        self._request_counts: Dict[str, int] = {}
        self._lock = threading.Lock()
        self._health_check_interval = 60.0
        self._last_health_check = 0.0
        logger.info("LLMLoadBalancer initialized")
    
    def add_provider(self, provider: str, model: str, 
                    weight: float = 1.0, priority: int = 1) -> None:
        """Add a provider to the load balancer"""
        key = f"{provider}/{model}"
        with self._lock:
            self.providers[key] = {
                "provider": provider,
                "model": model,
                "weight": weight,
                "priority": priority,
                "enabled": True,
            }
            self._request_counts[key] = 0
            self.health_status[key] = ProviderHealth(
                provider=provider,
                model=model,
                is_healthy=True,
                latency_ms=0,
                success_rate=1.0,
                last_check=time.time()
            )
        logger.info(f"Added provider: {key} (weight={weight})")
    
    def remove_provider(self, provider: str, model: str) -> None:
        """Remove a provider"""
        key = f"{provider}/{model}"
        with self._lock:
            self.providers.pop(key, None)
            self._request_counts.pop(key, None)
            self.health_status.pop(key, None)
    
    def _calculate_score(self, key: str) -> float:
        """Calculate selection score for a provider"""
        config = self.providers.get(key, {})
        health = self.health_status.get(key)
        
        if not config.get("enabled", False):
            return -1
        
        if health and not health.is_healthy:
            return -1
        
        weight = config.get("weight", 1.0)
        priority = config.get("priority", 1)
        
        # Higher weight = more likely, lower priority number = more likely
        score = weight / (priority + 0.1)
        
        # Adjust for latency
        if health and health.latency_ms > 0:
            latency_factor = 1.0 / (1 + health.latency_ms / 1000)
            score *= latency_factor
        
        # Adjust for success rate
        if health and health.success_rate < 1.0:
            score *= health.success_rate
        
        return score
    
    def get_next_provider(self, task_type: str = "default") -> Optional[Tuple[str, str]]:
        """
        Get next provider using weighted selection.
        
        Returns:
            Tuple of (provider, model) or None
        """
        with self._lock:
            # Check if health check needed
            if time.time() - self._last_health_check > self._health_check_interval:
                self._update_health_status()
            
            # Calculate scores
            scores = {}
            for key, config in self.providers.items():
                score = self._calculate_score(key)
                if score > 0:
                    scores[key] = score
            
            if not scores:
                return None
            
            # Weighted random selection
            total = sum(scores.values())
            r = random.random() * total
            
            cumulative = 0
            for key, score in scores.items():
                cumulative += score
                if r <= cumulative:
                    self._request_counts[key] += 1
                    config = self.providers[key]
                    return (config["provider"], config["model"])
            
            # Fallback to first available
            key = list(scores.keys())[0]
            config = self.providers[key]
            return (config["provider"], config["model"])
    
    def _update_health_status(self) -> None:
        """Update health status for all providers"""
        self._last_health_check = time.time()
        
        for key, config in self.providers.items():
            provider = config["provider"]
            is_healthy = _check_provider_available(provider)
            
            if key in self.health_status:
                health = self.health_status[key]
                if is_healthy:
                    health.consecutive_failures = 0
                else:
                    health.consecutive_failures += 1
                health.is_healthy = is_healthy and health.consecutive_failures < 3
                health.last_check = time.time()
    
    def record_success(self, provider: str, model: str, latency_ms: float) -> None:
        """Record successful request"""
        key = f"{provider}/{model}"
        with self._lock:
            if key in self.health_status:
                health = self.health_status[key]
                health.is_healthy = True
                health.consecutive_failures = 0
                # Exponential moving average for latency
                health.latency_ms = 0.8 * health.latency_ms + 0.2 * latency_ms
                # Update success rate
                health.success_rate = min(1.0, health.success_rate * 0.9 + 0.1)
    
    def record_failure(self, provider: str, model: str) -> None:
        """Record failed request"""
        key = f"{provider}/{model}"
        with self._lock:
            if key in self.health_status:
                health = self.health_status[key]
                health.consecutive_failures += 1
                health.success_rate = max(0.0, health.success_rate * 0.9)
                if health.consecutive_failures >= 3:
                    health.is_healthy = False
    
    def get_status(self) -> Dict[str, Any]:
        """Get load balancer status"""
        with self._lock:
            return {
                "provider_count": len(self.providers),
                "healthy_count": sum(1 for h in self.health_status.values() if h.is_healthy),
                "request_distribution": dict(self._request_counts),
                "providers": {
                    key: {
                        "is_healthy": health.is_healthy,
                        "latency_ms": round(health.latency_ms, 1),
                        "success_rate": round(health.success_rate, 2),
                        "weight": self.providers.get(key, {}).get("weight", 0),
                    }
                    for key, health in self.health_status.items()
                }
            }


# Singleton instance
_llm_load_balancer: Optional[LLMLoadBalancer] = None

def get_llm_load_balancer() -> LLMLoadBalancer:
    """Get singleton LLMLoadBalancer instance"""
    global _llm_load_balancer
    if _llm_load_balancer is None:
        _llm_load_balancer = LLMLoadBalancer()
    return _llm_load_balancer


class PromptOptimizer:
    """
    V7.6 P0 CRITICAL: Optimize prompts for better model responses.
    
    Manages prompt templates, optimizes prompts for specific models,
    and tracks prompt effectiveness.
    
    Usage:
        optimizer = get_prompt_optimizer()
        
        # Register template
        optimizer.register_template(PromptTemplate(
            name="bin_gen",
            task_type="bin_generation",
            template="Generate BINs for {card_type} in {country}..."
        ))
        
        # Optimize prompt
        optimized = optimizer.optimize_prompt(
            "Generate 10 BINs",
            task_type="bin_generation"
        )
    """
    
    # Model-specific optimization hints
    MODEL_HINTS: Dict[str, Dict[str, str]] = {
        "mistral": {
            "json_hint": "Output ONLY valid JSON. No markdown, no explanations.",
            "format_style": "concise",
        },
        "llama": {
            "json_hint": "Respond with raw JSON only. No text before or after.",
            "format_style": "detailed",
        },
        "gpt": {
            "json_hint": "Respond with valid JSON.",
            "format_style": "balanced",
        },
        "claude": {
            "json_hint": "Output only the JSON object or array.",
            "format_style": "verbose",
        },
    }
    
    def __init__(self):
        self.templates: Dict[str, PromptTemplate] = {}
        self._effectiveness_scores: Dict[str, deque] = {}
        self._lock = threading.Lock()
        logger.info("PromptOptimizer initialized")
    
    def register_template(self, template: PromptTemplate) -> None:
        """Register a prompt template"""
        with self._lock:
            self.templates[template.name] = template
            self._effectiveness_scores[template.name] = deque(maxlen=50)
        logger.info(f"Registered template: {template.name}")
    
    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """Get template by name"""
        return self.templates.get(name)
    
    def optimize_prompt(self, prompt: str, task_type: str = "default",
                       model_hint: str = "") -> str:
        """
        Optimize a prompt for better model response.
        
        Args:
            prompt: Original prompt
            task_type: Task type for context
            model_hint: Model family hint (mistral, llama, gpt, claude)
            
        Returns:
            Optimized prompt
        """
        optimized = prompt
        
        # Find matching template
        template = None
        with self._lock:
            for t in self.templates.values():
                if t.task_type == task_type:
                    template = t
                    break
        
        if template and template.system_prompt:
            optimized = f"{template.system_prompt}\n\n{optimized}"
        
        # Add model-specific hints
        hints = self.MODEL_HINTS.get(model_hint.lower(), {})
        if hints.get("json_hint") and "json" in task_type.lower():
            optimized += f"\n\n{hints['json_hint']}"
        
        # Add common optimizations
        if "json" in task_type.lower() or "generation" in task_type.lower():
            if "JSON" not in optimized:
                optimized += "\n\nIMPORTANT: Respond ONLY with valid JSON. No markdown, no explanation."
        
        return optimized
    
    def record_effectiveness(self, template_name: str, success: bool,
                            quality_score: float = 0.0) -> None:
        """Record template effectiveness"""
        with self._lock:
            if template_name in self._effectiveness_scores:
                self._effectiveness_scores[template_name].append({
                    "success": success,
                    "quality": quality_score,
                    "timestamp": time.time()
                })
    
    def get_template_stats(self, template_name: str) -> Dict:
        """Get effectiveness stats for a template"""
        with self._lock:
            if template_name not in self._effectiveness_scores:
                return {"exists": False}
            
            scores = list(self._effectiveness_scores[template_name])
        
        if not scores:
            return {"exists": True, "samples": 0}
        
        success_rate = sum(1 for s in scores if s["success"]) / len(scores)
        avg_quality = sum(s["quality"] for s in scores) / len(scores)
        
        return {
            "exists": True,
            "samples": len(scores),
            "success_rate": round(success_rate, 2),
            "avg_quality": round(avg_quality, 2),
        }
    
    def suggest_improvements(self, template_name: str) -> List[str]:
        """Suggest prompt improvements based on effectiveness data"""
        stats = self.get_template_stats(template_name)
        suggestions = []
        
        if stats.get("success_rate", 1.0) < 0.8:
            suggestions.append("Add clearer output format instructions")
            suggestions.append("Break complex requests into steps")
        
        if stats.get("avg_quality", 1.0) < 0.6:
            suggestions.append("Add examples of expected output")
            suggestions.append("Be more specific about requirements")
        
        return suggestions


# Singleton instance
_prompt_optimizer: Optional[PromptOptimizer] = None

def get_prompt_optimizer() -> PromptOptimizer:
    """Get singleton PromptOptimizer instance"""
    global _prompt_optimizer
    if _prompt_optimizer is None:
        _prompt_optimizer = PromptOptimizer()
    return _prompt_optimizer


class LLMResponseValidator:
    """
    V7.6 P0 CRITICAL: Validate and sanitize LLM responses.
    
    Ensures LLM responses meet quality standards and don't contain
    harmful content or malformed data.
    
    Usage:
        validator = get_llm_response_validator()
        
        # Validate JSON response
        is_valid, errors = validator.validate_json_response(response, schema)
        
        # Sanitize response
        clean = validator.sanitize_response(response)
    """
    
    # Forbidden content patterns
    FORBIDDEN_PATTERNS = [
        r"<script[^>]*>",
        r"javascript:",
        r"data:text/html",
    ]
    
    def __init__(self):
        self._validation_history: deque = deque(maxlen=100)
        self._lock = threading.Lock()
        logger.info("LLMResponseValidator initialized")
    
    def validate_json_response(self, response: str, 
                               expected_type: type = None) -> Tuple[bool, List[str]]:
        """
        Validate a JSON response.
        
        Args:
            response: Raw response text
            expected_type: Expected Python type (list, dict)
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        if not response or not response.strip():
            errors.append("Empty response")
            return False, errors
        
        # Try to parse JSON
        parsed = _extract_json(response)
        
        if parsed is None:
            errors.append("Invalid JSON format")
            return False, errors
        
        # Check expected type
        if expected_type and not isinstance(parsed, expected_type):
            errors.append(f"Expected {expected_type.__name__}, got {type(parsed).__name__}")
            return False, errors
        
        # Check for empty containers
        if isinstance(parsed, (list, dict)) and len(parsed) == 0:
            errors.append("Response is empty container")
            # Not necessarily an error, but record it
        
        self._record_validation(True, errors)
        return len(errors) == 0, errors
    
    def validate_structure(self, data: Any, 
                          required_fields: List[str] = None) -> Tuple[bool, List[str]]:
        """Validate data structure has required fields"""
        errors = []
        
        if not isinstance(data, dict):
            errors.append("Data is not a dictionary")
            return False, errors
        
        if required_fields:
            missing = [f for f in required_fields if f not in data]
            if missing:
                errors.append(f"Missing required fields: {missing}")
        
        return len(errors) == 0, errors
    
    def sanitize_response(self, response: str) -> str:
        """Remove potentially harmful content from response"""
        import re
        
        sanitized = response
        
        # Remove script tags
        for pattern in self.FORBIDDEN_PATTERNS:
            sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE)
        
        # Strip excessive whitespace
        sanitized = "\n".join(line.strip() for line in sanitized.split("\n"))
        sanitized = re.sub(r"\n{3,}", "\n\n", sanitized)
        
        return sanitized.strip()
    
    def check_quality(self, response: str, min_length: int = 10,
                     max_length: int = 100000) -> Tuple[bool, str]:
        """Check response quality"""
        if len(response) < min_length:
            return False, f"Response too short ({len(response)} < {min_length})"
        
        if len(response) > max_length:
            return False, f"Response too long ({len(response)} > {max_length})"
        
        # Check for repetitive content
        words = response.lower().split()
        if len(words) > 10:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < 0.3:
                return False, "Response appears repetitive"
        
        return True, "Quality OK"
    
    def _record_validation(self, success: bool, errors: List[str]) -> None:
        """Record validation result"""
        with self._lock:
            self._validation_history.append({
                "success": success,
                "error_count": len(errors),
                "timestamp": time.time()
            })
    
    def get_validation_stats(self) -> Dict:
        """Get validation statistics"""
        with self._lock:
            results = list(self._validation_history)
        
        if not results:
            return {"samples": 0}
        
        success_count = sum(1 for r in results if r["success"])
        
        return {
            "samples": len(results),
            "success_rate": round(success_count / len(results), 2),
            "avg_errors": round(sum(r["error_count"] for r in results) / len(results), 2),
        }


# Singleton instance
_response_validator: Optional[LLMResponseValidator] = None

def get_llm_response_validator() -> LLMResponseValidator:
    """Get singleton LLMResponseValidator instance"""
    global _response_validator
    if _response_validator is None:
        _response_validator = LLMResponseValidator()
    return _response_validator


class LLMUsageTracker:
    """
    V7.6 P0 CRITICAL: Track LLM usage and costs across providers.
    
    Monitors API usage, estimates costs, and provides usage analytics
    for operational budgeting and optimization.
    
    Usage:
        tracker = get_llm_usage_tracker()
        
        # Record usage
        tracker.record_usage(
            provider="openai",
            model="gpt-4o",
            tokens_sent=1000,
            tokens_received=500,
            success=True
        )
        
        # Get usage report
        report = tracker.get_usage_report()
    """
    
    # Approximate token costs per 1K tokens (as of 2024)
    COST_PER_1K_TOKENS: Dict[str, Tuple[float, float]] = {
        "gpt-4o": (0.005, 0.015),           # (input, output)
        "gpt-4o-mini": (0.00015, 0.0006),
        "claude-3-5-sonnet": (0.003, 0.015),
        "llama-3.1-70b": (0.0008, 0.0008),  # Groq
        "mistral:7b": (0.0, 0.0),           # Local/free
        "default": (0.001, 0.002),
    }
    
    def __init__(self):
        self.usage_records: deque = deque(maxlen=10000)
        self._daily_totals: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        logger.info("LLMUsageTracker initialized")
    
    def record_usage(self, provider: str, model: str, task_type: str,
                    tokens_sent: int, tokens_received: int,
                    latency_ms: float, success: bool) -> None:
        """Record LLM API usage"""
        # Calculate cost estimate
        cost_key = model if model in self.COST_PER_1K_TOKENS else "default"
        input_cost, output_cost = self.COST_PER_1K_TOKENS.get(cost_key, (0.001, 0.002))
        
        cost_estimate = (tokens_sent / 1000 * input_cost + 
                        tokens_received / 1000 * output_cost)
        
        record = LLMUsageRecord(
            provider=provider,
            model=model,
            task_type=task_type,
            tokens_sent=tokens_sent,
            tokens_received=tokens_received,
            latency_ms=latency_ms,
            cost_estimate=cost_estimate,
            timestamp=time.time(),
            success=success
        )
        
        with self._lock:
            self.usage_records.append(record)
            
            # Update daily totals
            date_key = datetime.now().strftime("%Y-%m-%d")
            if date_key not in self._daily_totals:
                self._daily_totals[date_key] = {
                    "tokens_sent": 0,
                    "tokens_received": 0,
                    "cost": 0.0,
                    "requests": 0,
                    "successes": 0,
                }
            
            day = self._daily_totals[date_key]
            day["tokens_sent"] += tokens_sent
            day["tokens_received"] += tokens_received
            day["cost"] += cost_estimate
            day["requests"] += 1
            if success:
                day["successes"] += 1
    
    def get_usage_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate usage report for specified time period"""
        cutoff = time.time() - (hours * 3600)
        
        with self._lock:
            recent = [r for r in self.usage_records if r.timestamp > cutoff]
        
        if not recent:
            return {
                "period_hours": hours,
                "total_requests": 0,
                "message": "No usage data"
            }
        
        total_tokens_sent = sum(r.tokens_sent for r in recent)
        total_tokens_received = sum(r.tokens_received for r in recent)
        total_cost = sum(r.cost_estimate for r in recent)
        success_count = sum(1 for r in recent if r.success)
        
        # Group by provider
        by_provider: Dict[str, Dict] = {}
        for r in recent:
            key = f"{r.provider}/{r.model}"
            if key not in by_provider:
                by_provider[key] = {
                    "requests": 0,
                    "tokens": 0,
                    "cost": 0.0,
                    "avg_latency": 0.0,
                }
            by_provider[key]["requests"] += 1
            by_provider[key]["tokens"] += r.tokens_sent + r.tokens_received
            by_provider[key]["cost"] += r.cost_estimate
        
        # Calculate averages
        avg_latency = sum(r.latency_ms for r in recent) / len(recent)
        
        return {
            "period_hours": hours,
            "total_requests": len(recent),
            "success_rate": round(success_count / len(recent), 2),
            "total_tokens_sent": total_tokens_sent,
            "total_tokens_received": total_tokens_received,
            "total_cost_usd": round(total_cost, 4),
            "avg_latency_ms": round(avg_latency, 1),
            "by_provider": {
                k: {
                    "requests": v["requests"],
                    "tokens": v["tokens"],
                    "cost_usd": round(v["cost"], 4),
                }
                for k, v in by_provider.items()
            },
        }
    
    def get_daily_report(self, date: str = None) -> Dict:
        """Get report for a specific day"""
        date_key = date or datetime.now().strftime("%Y-%m-%d")
        
        with self._lock:
            day = self._daily_totals.get(date_key, {})
        
        if not day:
            return {"date": date_key, "has_data": False}
        
        return {
            "date": date_key,
            "has_data": True,
            "total_requests": day.get("requests", 0),
            "success_rate": round(day.get("successes", 0) / max(day.get("requests", 1), 1), 2),
            "tokens_sent": day.get("tokens_sent", 0),
            "tokens_received": day.get("tokens_received", 0),
            "estimated_cost_usd": round(day.get("cost", 0), 4),
        }
    
    def get_cost_projection(self, days: int = 30) -> Dict:
        """Project costs based on current usage"""
        report = self.get_usage_report(hours=24)
        daily_cost = report.get("total_cost_usd", 0)
        daily_tokens = report.get("total_tokens_sent", 0) + report.get("total_tokens_received", 0)
        
        return {
            "projection_days": days,
            "daily_cost_usd": round(daily_cost, 4),
            "projected_cost_usd": round(daily_cost * days, 2),
            "daily_tokens": daily_tokens,
            "projected_tokens": daily_tokens * days,
        }
    
    def export_usage(self, format: str = "json") -> str:
        """Export usage data"""
        with self._lock:
            records = [
                {
                    "provider": r.provider,
                    "model": r.model,
                    "task_type": r.task_type,
                    "tokens_sent": r.tokens_sent,
                    "tokens_received": r.tokens_received,
                    "latency_ms": r.latency_ms,
                    "cost_estimate": r.cost_estimate,
                    "timestamp": r.timestamp,
                    "success": r.success,
                }
                for r in self.usage_records
            ]
        
        if format == "json":
            return json.dumps(records, indent=2)
        else:
            # CSV
            lines = ["provider,model,task_type,tokens_sent,tokens_received,cost,success"]
            for r in records:
                lines.append(
                    f"{r['provider']},{r['model']},{r['task_type']},"
                    f"{r['tokens_sent']},{r['tokens_received']},"
                    f"{r['cost_estimate']},{r['success']}"
                )
            return "\n".join(lines)


# Singleton instance
_usage_tracker: Optional[LLMUsageTracker] = None

def get_llm_usage_tracker() -> LLMUsageTracker:
    """Get singleton LLMUsageTracker instance"""
    global _usage_tracker
    if _usage_tracker is None:
        _usage_tracker = LLMUsageTracker()
    return _usage_tracker
