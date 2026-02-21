"""
TITAN V7.5 SINGULARITY — Ollama LLM Bridge
Local LLM integration for dynamic data generation.

Uses Ollama (local) to generate/expand datasets that were previously hardcoded:
- Target merchant sites
- BIN databases
- Country profiles
- Target presets (history, cookies, warmup searches)
- Persona data

Architecture:
    1. Prompt template + seed data → Ollama API → parsed JSON response
    2. Results cached to /opt/titan/data/ollama_cache/<key>.json
    3. Falls back to seed data if Ollama unavailable
    4. Cache TTL configurable (default 24h)

Requirements:
    - Ollama running locally: ollama serve
    - Model pulled: ollama pull llama3.1 (or mistral, etc.)
"""

import json
import hashlib
import logging
import time
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger("TITAN-OLLAMA")

OLLAMA_API = os.environ.get("OLLAMA_API", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1")
CACHE_DIR = Path("/opt/titan/data/ollama_cache")
CACHE_TTL_HOURS = int(os.environ.get("OLLAMA_CACHE_TTL", "24"))


def _cache_path(key: str) -> Path:
    """Get cache file path for a given key."""
    safe = hashlib.sha256(key.encode()).hexdigest()[:16]
    return CACHE_DIR / f"{safe}.json"


def _cache_valid(path: Path) -> bool:
    """Check if cache file exists and is within TTL."""
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text())
        cached_at = datetime.fromisoformat(data.get("_cached_at", "2000-01-01"))
        return datetime.utcnow() - cached_at < timedelta(hours=CACHE_TTL_HOURS)
    except Exception:
        return False


def _read_cache(path: Path) -> Optional[Any]:
    """Read cached data."""
    try:
        data = json.loads(path.read_text())
        return data.get("result")
    except Exception:
        return None


def _write_cache(path: Path, result: Any, key: str):
    """Write result to cache."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "_cached_at": datetime.utcnow().isoformat(),
            "_key": key,
            "_model": OLLAMA_MODEL,
            "result": result,
        }
        path.write_text(json.dumps(data, indent=2, default=str))
    except Exception as e:
        logger.warning(f"Cache write failed: {e}")


def is_ollama_available() -> bool:
    """Check if Ollama is running and accessible."""
    try:
        proc = subprocess.run(
            ["curl", "-s", "--max-time", "3", f"{OLLAMA_API}/api/tags"],
            capture_output=True, text=True, timeout=5
        )
        if proc.returncode == 0 and proc.stdout:
            data = json.loads(proc.stdout)
            return "models" in data
    except Exception:
        pass
    return False


def get_available_models() -> List[str]:
    """List available Ollama models."""
    try:
        proc = subprocess.run(
            ["curl", "-s", "--max-time", "5", f"{OLLAMA_API}/api/tags"],
            capture_output=True, text=True, timeout=8
        )
        if proc.returncode == 0:
            data = json.loads(proc.stdout)
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        pass
    return []


def query_ollama(prompt: str, model: str = None, temperature: float = 0.7,
                 max_tokens: int = 4096, timeout: int = 120) -> Optional[str]:
    """
    Send a prompt to Ollama and return the text response.
    
    Returns None if Ollama is unavailable or errors.
    """
    model = model or OLLAMA_MODEL
    
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
             "-X", "POST", f"{OLLAMA_API}/api/generate",
             "-H", "Content-Type: application/json",
             "-d", payload],
            capture_output=True, text=True, timeout=timeout + 10
        )
        
        if proc.returncode == 0 and proc.stdout:
            data = json.loads(proc.stdout)
            return data.get("response", "").strip()
    except subprocess.TimeoutExpired:
        logger.warning(f"Ollama query timed out after {timeout}s")
    except Exception as e:
        logger.warning(f"Ollama query failed: {e}")
    
    return None


def query_ollama_json(prompt: str, model: str = None, temperature: float = 0.3,
                      max_tokens: int = 8192, timeout: int = 180) -> Optional[Any]:
    """
    Send a prompt to Ollama expecting a JSON response.
    Automatically extracts JSON from the response text.
    
    Returns parsed JSON or None.
    """
    # Add JSON instruction to prompt
    full_prompt = (
        f"{prompt}\n\n"
        "IMPORTANT: Respond ONLY with valid JSON. No markdown, no explanation, "
        "no code fences. Just the raw JSON array or object."
    )
    
    raw = query_ollama(full_prompt, model=model, temperature=temperature,
                       max_tokens=max_tokens, timeout=timeout)
    if not raw:
        return None
    
    # Try to extract JSON from response
    return _extract_json(raw)


def _extract_json(text: str) -> Optional[Any]:
    """Extract JSON from LLM response text, handling common formatting issues."""
    # Strip markdown code fences
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines (code fences)
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
        # Find matching end
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


def generate_with_cache(cache_key: str, prompt: str, fallback: Any = None,
                        model: str = None, temperature: float = 0.3,
                        max_tokens: int = 8192, timeout: int = 180) -> Any:
    """
    Generate data via Ollama with caching.
    
    1. Check cache → return if valid
    2. Query Ollama → parse JSON → cache → return
    3. Fall back to provided fallback data if Ollama fails
    
    Args:
        cache_key: Unique key for caching this query
        prompt: The prompt to send to Ollama
        fallback: Data to return if Ollama is unavailable
        model: Ollama model to use (default from env)
        temperature: LLM temperature (lower = more deterministic)
        max_tokens: Max response tokens
        timeout: Request timeout in seconds
    
    Returns:
        Parsed JSON result, or fallback if generation fails
    """
    path = _cache_path(cache_key)
    
    # Check cache
    if _cache_valid(path):
        cached = _read_cache(path)
        if cached is not None:
            logger.info(f"Cache hit for '{cache_key}'")
            return cached
    
    # Query Ollama
    logger.info(f"Generating '{cache_key}' via Ollama ({model or OLLAMA_MODEL})...")
    result = query_ollama_json(prompt, model=model, temperature=temperature,
                               max_tokens=max_tokens, timeout=timeout)
    
    if result is not None:
        _write_cache(path, result, cache_key)
        logger.info(f"Generated and cached '{cache_key}': {type(result).__name__}")
        return result
    
    # Fallback
    logger.warning(f"Ollama unavailable for '{cache_key}', using fallback data")
    return fallback


def invalidate_cache(cache_key: str = None):
    """Invalidate cache for a specific key, or all cache if key is None."""
    if cache_key:
        path = _cache_path(cache_key)
        if path.exists():
            path.unlink()
            logger.info(f"Invalidated cache: {cache_key}")
    else:
        if CACHE_DIR.exists():
            for f in CACHE_DIR.glob("*.json"):
                f.unlink()
            logger.info("Invalidated all Ollama cache")


def get_cache_stats() -> Dict:
    """Get cache statistics."""
    if not CACHE_DIR.exists():
        return {"total_files": 0, "total_size_kb": 0, "cache_dir": str(CACHE_DIR)}
    
    files = list(CACHE_DIR.glob("*.json"))
    total_size = sum(f.stat().st_size for f in files)
    
    return {
        "total_files": len(files),
        "total_size_kb": round(total_size / 1024, 1),
        "cache_dir": str(CACHE_DIR),
        "ollama_available": is_ollama_available(),
        "model": OLLAMA_MODEL,
    }
