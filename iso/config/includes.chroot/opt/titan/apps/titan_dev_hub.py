#!/usr/bin/env python3
"""
TITAN Dev Hub v4 - Agentic IDE with Full Pipeline Engine

Purpose:
- Host a web IDE on a dedicated VPS port for TITAN OS development.
- Provide safe system-level editing with backup + syntax validation.
- Run agentic tasks (scan OS/apps/APIs/UI, upgrade readiness, research).
- Integrate AI providers (Windsurf/Copilot compatible + Ollama fallback).
- Integrate Hostinger API operations for VPS visibility.

Agentic Engine (v4):
- Task decomposition: complex tasks auto-split into atomic sub-steps.
- Multi-model pipeline: chain analyst -> strategist -> fast per sub-step.
- Persistent checkpoints: every sub-step result saved, resume on failure.
- Auto-retry with self-validation: bad output retried with refined prompt.
- Structured chain-of-thought: makes 7B local models perform near-Opus.
- Zero credit-gating: tasks ALWAYS run to completion, never stop mid-way.
"""

from __future__ import annotations

import argparse
import ast
import copy
import fnmatch
import hashlib
import json
import logging
import os
import re
import shutil
import shlex
import subprocess
import tempfile
import threading
import time
import traceback
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Deque, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

import requests
from flask import Flask, Response, jsonify, request


LOG = logging.getLogger("titan-dev-hub")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        LOG.warning("Failed to load JSON from %s: %s", path, exc)
        return fallback


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def safe_rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except Exception:
        return str(path.resolve())


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


DEFAULT_CONFIG: Dict[str, Any] = {
    "service": {
        "host": "0.0.0.0",
        "port": 8877,
        "debug": False,
    },
    "auth": {
        "require_token": False,
        "api_token": "",
        "api_token_env": "TITAN_DEV_HUB_TOKEN",
    },
    "ai": {
        "default_provider": "ollama",
        "timeout_seconds": 120,
        "reasoning_boost": True,
        "parallel_providers": ["windsurf", "copilot"],
        "ensemble_synthesizer": "ollama",
        "ensemble_synthesizer_model": "deepseek-r1:8b",
    },
    "providers": {
        "ollama": {
            "enabled": True,
            "endpoint": "http://127.0.0.1:11434/api/generate",
            "model": "qwen2.5:7b",
        },
        "windsurf": {
            "enabled": True,
            "endpoint": "",
            "model": "",
            "api_key": "",
            "api_key_env": "WINDSURF_API_KEY",
            "openai_compatible": True,
        },
        "copilot": {
            "enabled": True,
            "endpoint": "",
            "model": "",
            "api_key": "",
            "api_key_env": "GITHUB_COPILOT_TOKEN",
            "openai_compatible": True,
        },
        "openai_compatible": {
            "enabled": True,
            "endpoint": "",
            "model": "",
            "api_key": "",
            "api_key_env": "OPENAI_API_KEY",
            "openai_compatible": True,
        },
    },
    "safety": {
        "allowed_extensions": [
            ".py",
            ".md",
            ".txt",
            ".json",
            ".yaml",
            ".yml",
            ".sh",
            ".bat",
            ".ps1",
            ".xml",
            ".kt",
            ".java",
            ".js",
            ".css",
            ".html",
        ],
        "max_file_size_mb": 5,
        "backup_enabled": True,
        "editable_system_roots": [
            "/opt",
            "/etc",
            "/usr/local",
        ],
        "protected_paths": [
            "/proc",
            "/sys",
            "/dev",
            "/boot",
            "/bin",
            "/sbin",
            "/lib",
            "/lib64",
            "/usr/bin",
            "/usr/sbin",
            "/etc/passwd",
            "/etc/shadow",
            "/etc/gshadow",
            "/etc/sudoers",
        ],
    },
    "scanner": {
        "roots": ["core", "apps", "scripts", "docs"],
        "exclude_dirs": [".git", "__pycache__", "node_modules", ".venv", "venv"],
        "max_files": 5000,
    },
    "scraper": {
        "enabled": True,
        "timeout_seconds": 20,
        "max_response_bytes": 1500000,
        "max_pages": 20,
        "max_depth": 2,
        "same_domain_default": True,
        "user_agent": "TITAN-DevHub-Scraper/1.0",
    },
    "vastai": {
        "enabled": True,
        "api_key": "",
        "api_key_env": "VASTAI_API_KEY",
        "default_gpu": "RTX_4090",
        "default_image": "pytorch/pytorch:2.2.0-cuda12.1-cudnn8-devel",
        "default_disk_gb": 40,
    },
    "hostinger": {
        "enabled": True,
        "base_url": "https://developers.hostinger.com",
        "api_token": "",
        "api_token_env": "HOSTINGER_API_TOKEN",
    },
    "ops": {
        "scan_allow_roots": [
            "/opt/titan",
            "/etc",
            "/usr/local",
            "/var",
            "/home",
        ],
        "max_scan_files_per_request": 8000,
        "scan_max_depth": 8,
        "service_allowlist": [
            "titan-*",
            "lucid-*",
            "redis-server",
            "ollama",
            "xray",
            "ntfy",
        ],
        "verification_scripts": [
            "/opt/titan/vps_verify_real.sh",
            "/opt/titan/core/titan_master_verify.py",
            "/opt/titan/core/verify_deep_identity.py",
        ],
        "test_commands": {
            "test_runner": ["python3", "-m", "testing.test_runner"],
            "titan_master_verify": ["python3", "core/titan_master_verify.py"],
            "verify_deep_identity": ["python3", "core/verify_deep_identity.py"],
        },
        "allow_reboot": False,
    },
}


@dataclass
class HubTask:
    id: str
    title: str
    task_type: str
    priority: str = "medium"
    status: str = "pending"
    agent: str = "analyst"
    description: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    result: Optional[Dict[str, Any]] = None
    error: str = ""


class TaskStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            save_json(self.path, {"tasks": []})

    def _load(self) -> Dict[str, Any]:
        return load_json(self.path, {"tasks": []})

    def _save(self, data: Dict[str, Any]) -> None:
        save_json(self.path, data)

    def list_tasks(self) -> List[Dict[str, Any]]:
        with self._lock:
            return self._load().get("tasks", [])

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            tasks = self._load().get("tasks", [])
            for task in tasks:
                if task.get("id") == task_id:
                    return task
        return None

    def create_task(self, task: HubTask) -> Dict[str, Any]:
        payload = asdict(task)
        with self._lock:
            data = self._load()
            data.setdefault("tasks", []).append(payload)
            self._save(data)
        return payload

    def update_task(self, task_id: str, **patch: Any) -> Optional[Dict[str, Any]]:
        with self._lock:
            data = self._load()
            tasks = data.get("tasks", [])
            updated = None
            for task in tasks:
                if task.get("id") == task_id:
                    task.update(patch)
                    task["updated_at"] = utc_now()
                    updated = task
                    break
            if updated is not None:
                self._save(data)
            return updated


def assign_agent(task_type: str, title: str) -> str:
    text = f"{task_type} {title}".lower()
    if "scan" in text or "audit" in text or "api" in text:
        return "analyst"
    if "upgrade" in text or "plan" in text or "architecture" in text:
        return "strategist"
    if "edit" in text or "patch" in text or "fix" in text:
        return "operator"
    return "analyst"


class SafeSystemEditor:
    def __init__(self, titan_root: Path, config: Dict[str, Any]) -> None:
        self.titan_root = titan_root.resolve()
        self.config = config
        self.backup_dir = self.titan_root / "apps" / "backups"
        self.audit_log = self.titan_root / "state" / "dev_hub_audit.jsonl"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.audit_log.parent.mkdir(parents=True, exist_ok=True)

    def resolve_path(self, raw_path: str) -> Path:
        candidate = Path(os.path.expanduser(raw_path.strip()))
        if not candidate.is_absolute():
            candidate = (self.titan_root / candidate).resolve()
        else:
            candidate = candidate.resolve()
        return candidate

    def _is_protected(self, path: Path) -> bool:
        protected_paths = self.config.get("safety", {}).get("protected_paths", [])
        path_str = str(path)
        for protected in protected_paths:
            protected_path = str(Path(protected))
            if path_str == protected_path or path_str.startswith(protected_path + os.sep):
                return True
        return False

    def _is_within_root(self, path: Path, root: str) -> bool:
        root_path = Path(root).resolve()
        try:
            path.resolve().relative_to(root_path)
            return True
        except Exception:
            return False

    def validate_edit(self, path: Path, system_mode: bool = False) -> Tuple[bool, str]:
        if not path.exists():
            return False, f"File not found: {path}"
        if path.is_dir():
            return False, "Directories cannot be edited"
        if self._is_protected(path):
            return False, f"Protected path: {path}"

        ext = path.suffix.lower()
        allowed = self.config.get("safety", {}).get("allowed_extensions", [])
        if ext not in allowed:
            return False, f"Extension not allowed: {ext}"

        max_size = int(self.config.get("safety", {}).get("max_file_size_mb", 5)) * 1024 * 1024
        if path.stat().st_size > max_size:
            return False, f"File exceeds max size ({max_size} bytes)"

        if self._is_within_root(path, str(self.titan_root)):
            return True, "allowed"

        if not system_mode:
            return (
                False,
                "System-level edit requires system_mode=true",
            )

        for root in self.config.get("safety", {}).get("editable_system_roots", []):
            if self._is_within_root(path, root):
                return True, "allowed-system-mode"

        return False, f"Path not inside editable system roots: {path}"

    def list_files(self, root: str, limit: int = 400) -> List[str]:
        target = self.resolve_path(root)
        if not target.exists() or not target.is_dir():
            return []

        results: List[str] = []
        exclude_dirs = set(self.config.get("scanner", {}).get("exclude_dirs", []))
        for current_root, dirs, files in os.walk(target):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for file_name in files:
                full_path = Path(current_root) / file_name
                if full_path.suffix.lower() in self.config.get("safety", {}).get("allowed_extensions", []):
                    results.append(safe_rel(full_path, self.titan_root))
                    if len(results) >= limit:
                        return results
        return results

    def read_file(self, raw_path: str, system_mode: bool = False) -> Tuple[bool, str]:
        path = self.resolve_path(raw_path)
        allowed, reason = self.validate_edit(path, system_mode=system_mode)
        if not allowed:
            return False, reason

        try:
            return True, path.read_text(encoding="utf-8")
        except Exception as exc:
            return False, f"Read failed: {exc}"

    def _write_audit(self, record: Dict[str, Any]) -> None:
        with self.audit_log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")

    def _backup(self, path: Path) -> Optional[Path]:
        if not path.exists():
            return None
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rel = safe_rel(path, self.titan_root).replace(os.sep, "__")
        backup = self.backup_dir / f"{rel}.{stamp}.bak"
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup)
        return backup

    def write_file(
        self,
        raw_path: str,
        content: str,
        actor: str,
        reason: str,
        system_mode: bool = False,
    ) -> Tuple[bool, str, Optional[str]]:
        path = self.resolve_path(raw_path)
        allowed, check_reason = self.validate_edit(path, system_mode=system_mode)
        if not allowed:
            return False, check_reason, None

        if path.suffix.lower() == ".py":
            try:
                ast.parse(content)
            except SyntaxError as exc:
                return False, f"Python syntax validation failed: {exc}", None

        backup_path = None
        try:
            if self.config.get("safety", {}).get("backup_enabled", True):
                backup = self._backup(path)
                backup_path = str(backup) if backup else None

            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=str(path.parent), delete=False
            ) as temp_handle:
                temp_handle.write(content)
                temp_name = temp_handle.name

            os.replace(temp_name, path)

            self._write_audit(
                {
                    "timestamp": utc_now(),
                    "actor": actor,
                    "path": str(path),
                    "backup": backup_path,
                    "reason": reason,
                    "system_mode": system_mode,
                }
            )
            return True, "saved", backup_path
        except Exception as exc:
            return False, f"Write failed: {exc}", backup_path


class TitanScanner:
    def __init__(self, titan_root: Path, config: Dict[str, Any]) -> None:
        self.titan_root = titan_root.resolve()
        self.config = config

    def _scan_python_syntax(self, path: Path) -> Optional[str]:
        try:
            ast.parse(path.read_text(encoding="utf-8"))
            return None
        except Exception as exc:
            return str(exc)

    def _extract_api_routes(self, path: Path) -> List[str]:
        if not path.exists():
            return []
        text = path.read_text(encoding="utf-8", errors="ignore")
        route_hits = re.findall(r"['\"](/api[^'\"]+)['\"]", text)
        return sorted(set(route_hits))

    def scan(self, system_scan: bool = False) -> Dict[str, Any]:
        roots = self.config.get("scanner", {}).get("roots", ["core", "apps"])
        max_files = int(self.config.get("scanner", {}).get("max_files", 5000))
        excludes = set(self.config.get("scanner", {}).get("exclude_dirs", []))

        totals = {
            "files": 0,
            "python_files": 0,
            "markdown_files": 0,
            "gui_files": 0,
            "syntax_errors": 0,
        }
        findings: List[Dict[str, Any]] = []

        scanned_paths: List[str] = []

        for root_name in roots:
            root_path = self.titan_root / root_name
            if not root_path.exists():
                findings.append(
                    {
                        "severity": "medium",
                        "area": "scan",
                        "message": f"Missing scan root: {root_name}",
                    }
                )
                continue

            for current_root, dirs, files in os.walk(root_path):
                dirs[:] = [d for d in dirs if d not in excludes]
                for file_name in files:
                    path = Path(current_root) / file_name
                    totals["files"] += 1
                    scanned_paths.append(safe_rel(path, self.titan_root))

                    suffix = path.suffix.lower()
                    if suffix == ".py":
                        totals["python_files"] += 1
                        syntax_error = self._scan_python_syntax(path)
                        if syntax_error:
                            totals["syntax_errors"] += 1
                            findings.append(
                                {
                                    "severity": "high",
                                    "area": "python",
                                    "path": safe_rel(path, self.titan_root),
                                    "message": syntax_error,
                                }
                            )

                    if suffix == ".md":
                        totals["markdown_files"] += 1

                    if path.name.startswith("titan_") or path.name.startswith("app_"):
                        if suffix in {".py", ".ui", ".qml"}:
                            totals["gui_files"] += 1

                    if totals["files"] >= max_files:
                        findings.append(
                            {
                                "severity": "medium",
                                "area": "scan",
                                "message": f"Scan hit max_files cap ({max_files})",
                            }
                        )
                        break
                if totals["files"] >= max_files:
                    break
            if totals["files"] >= max_files:
                break

        api_routes = self._extract_api_routes(self.titan_root / "core" / "titan_api.py")

        if not (self.titan_root / "apps" / "titan_dev_hub.py").exists():
            findings.append(
                {
                    "severity": "high",
                    "area": "devhub",
                    "message": "Missing apps/titan_dev_hub.py",
                }
            )

        system_summary: Dict[str, Any] = {}
        if system_scan:
            system_roots = ["/etc", "/usr/local", str(self.titan_root)]
            sys_data = []
            for root in system_roots:
                p = Path(root)
                if not p.exists():
                    continue
                file_count = 0
                dir_count = 0
                for _, dirs, files in os.walk(p):
                    dir_count += len(dirs)
                    file_count += len(files)
                    if file_count > 10000:
                        break
                sys_data.append({"root": root, "files_estimate": file_count, "dirs": dir_count})
            system_summary = {"roots": sys_data}

        return {
            "timestamp": utc_now(),
            "totals": totals,
            "api_routes_count": len(api_routes),
            "api_routes_sample": api_routes[:30],
            "findings": findings,
            "scanned_paths_sample": scanned_paths[:60],
            "system_scan": system_summary,
        }

    def scan_paths(
        self,
        raw_paths: List[str],
        max_files: int = 8000,
        max_depth: int = 8,
        exclude_dirs: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        excludes = set(exclude_dirs if exclude_dirs is not None else self.config.get("scanner", {}).get("exclude_dirs", []))
        totals = {
            "files": 0,
            "python_files": 0,
            "markdown_files": 0,
            "gui_files": 0,
            "syntax_errors": 0,
        }
        findings: List[Dict[str, Any]] = []
        scanned_paths: List[str] = []
        scanned_roots: List[str] = []

        requested: List[str] = []
        for item in raw_paths:
            text = str(item).strip()
            if text and text not in requested:
                requested.append(text)

        def record_file(path: Path) -> None:
            totals["files"] += 1
            scanned_paths.append(safe_rel(path, self.titan_root))

            suffix = path.suffix.lower()
            if suffix == ".py":
                totals["python_files"] += 1
                syntax_error = self._scan_python_syntax(path)
                if syntax_error:
                    totals["syntax_errors"] += 1
                    findings.append(
                        {
                            "severity": "high",
                            "area": "python",
                            "path": safe_rel(path, self.titan_root),
                            "message": syntax_error,
                        }
                    )

            if suffix == ".md":
                totals["markdown_files"] += 1

            if path.name.startswith("titan_") or path.name.startswith("app_"):
                if suffix in {".py", ".ui", ".qml"}:
                    totals["gui_files"] += 1

        for raw in requested:
            target = Path(os.path.expanduser(raw))
            if not target.is_absolute():
                target = (self.titan_root / target).resolve()
            else:
                target = target.resolve()

            scanned_roots.append(str(target))

            if not target.exists():
                findings.append(
                    {
                        "severity": "medium",
                        "area": "scan",
                        "message": f"Missing scan path: {target}",
                    }
                )
                continue

            if target.is_file():
                record_file(target)
                if totals["files"] >= max_files:
                    break
                continue

            for current_root, dirs, files in os.walk(target):
                try:
                    depth = len(Path(current_root).resolve().relative_to(target).parts)
                except Exception:
                    depth = max_depth

                if depth >= max_depth:
                    dirs[:] = []
                else:
                    dirs[:] = [d for d in dirs if d not in excludes]

                for file_name in files:
                    path = Path(current_root) / file_name
                    record_file(path)
                    if totals["files"] >= max_files:
                        findings.append(
                            {
                                "severity": "medium",
                                "area": "scan",
                                "message": f"Scan hit max_files cap ({max_files})",
                            }
                        )
                        break
                if totals["files"] >= max_files:
                    break
            if totals["files"] >= max_files:
                break

        return {
            "timestamp": utc_now(),
            "scanned_roots": scanned_roots,
            "totals": totals,
            "findings": findings,
            "scanned_paths_sample": scanned_paths[:120],
        }


class AIClient:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config

    def _provider_cfg(self, provider: str) -> Dict[str, Any]:
        return self.config.get("providers", {}).get(provider, {})

    def _resolve_api_key(self, cfg: Dict[str, Any], explicit_key: str = "") -> str:
        if explicit_key:
            return explicit_key
        if cfg.get("api_key"):
            return cfg.get("api_key")
        env_name = cfg.get("api_key_env", "")
        if env_name:
            return os.environ.get(env_name, "")
        return ""

    def _boost_context(self, context: str) -> str:
        if not bool(self.config.get("ai", {}).get("reasoning_boost", True)):
            return context
        boost = (
            "Reasoning protocol: 1) understand task, 2) analyze constraints, "
            "3) propose steps, 4) execute, 5) self-validate, 6) final answer. "
            "Be precise and complete."
        )
        if context.strip():
            return f"{context.strip()}\n\n{boost}"
        return boost

    def _chat_single(
        self,
        prompt: str,
        provider: Optional[str] = None,
        context: str = "",
        api_key: str = "",
        model: str = "",
    ) -> Dict[str, Any]:
        ai_cfg = self.config.get("ai", {})
        selected = provider or ai_cfg.get("default_provider") or ai_cfg.get("provider") or "ollama"
        cfg = self._provider_cfg(selected)
        if not cfg:
            return {"ok": False, "error": f"Provider not configured: {selected}", "provider": selected}

        boosted_context = self._boost_context(context)
        if selected == "ollama":
            return self._chat_ollama(
                prompt,
                boosted_context,
                cfg,
                model_override=model,
                provider_name=selected,
            )

        return self._chat_openai_compatible(
            prompt,
            boosted_context,
            cfg,
            api_key=api_key,
            model_override=model,
            provider_name=selected,
        )

    def chat(
        self,
        prompt: str,
        provider: Optional[str] = None,
        context: str = "",
        api_key: str = "",
        model: str = "",
        mode: str = "single",
        providers: Optional[List[str]] = None,
        provider_api_keys: Optional[Dict[str, str]] = None,
        provider_models: Optional[Dict[str, str]] = None,
        synthesis_model: str = "",
    ) -> Dict[str, Any]:
        requested_mode = (mode or "single").strip().lower()
        if requested_mode == "ensemble" or (providers and len(providers) > 1):
            return self.ensemble_chat(
                prompt=prompt,
                providers=providers,
                context=context,
                provider_api_keys=provider_api_keys,
                provider_models=provider_models,
                synthesis_model=synthesis_model,
            )

        return self._chat_single(
            prompt=prompt,
            provider=provider,
            context=context,
            api_key=api_key,
            model=model,
        )

    def ensemble_chat(
        self,
        prompt: str,
        providers: Optional[List[str]] = None,
        context: str = "",
        provider_api_keys: Optional[Dict[str, str]] = None,
        provider_models: Optional[Dict[str, str]] = None,
        synthesis_model: str = "",
    ) -> Dict[str, Any]:
        ai_cfg = self.config.get("ai", {})
        default_parallel = ai_cfg.get("parallel_providers", ["windsurf", "copilot"])
        requested = providers or default_parallel

        ordered: List[str] = []
        for provider in requested:
            name = str(provider).strip()
            if name and name not in ordered:
                ordered.append(name)

        if not ordered:
            return {"ok": False, "error": "No providers selected for ensemble mode"}

        key_map = provider_api_keys or {}
        model_map = provider_models or {}

        results: List[Dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=min(4, len(ordered))) as pool:
            futures = {
                pool.submit(
                    self._chat_single,
                    prompt,
                    provider_name,
                    context,
                    str(key_map.get(provider_name, "")),
                    str(model_map.get(provider_name, "")),
                ): provider_name
                for provider_name in ordered
            }
            for future in as_completed(futures):
                provider_name = futures[future]
                try:
                    response = future.result()
                except Exception as exc:
                    response = {"ok": False, "provider": provider_name, "error": str(exc)}
                results.append(response)

        provider_index = {name: idx for idx, name in enumerate(ordered)}
        results.sort(key=lambda item: provider_index.get(str(item.get("provider", "")), 999))

        successes = [item for item in results if item.get("ok") and str(item.get("response", "")).strip()]
        if not successes:
            return {
                "ok": False,
                "mode": "ensemble",
                "providers": ordered,
                "responses": results,
                "error": "All ensemble providers failed",
            }

        synthesizer_provider = str(ai_cfg.get("ensemble_synthesizer", "ollama") or "ollama")
        synthesizer_model = synthesis_model or str(ai_cfg.get("ensemble_synthesizer_model", "") or "")

        synthesis_prompt = (
            "You are an answer synthesizer. Merge the strongest parts of each provider response into one "
            "accurate, practical final response. Resolve contradictions and keep only verified/high-quality content.\n\n"
            f"Original user prompt:\n{prompt}\n\n"
            "Provider outputs:\n"
            + "\n\n".join(
                [
                    f"[{entry.get('provider', 'unknown')} | model={entry.get('model', '')}]\n"
                    f"{entry.get('response', '')}"
                    for entry in successes
                ]
            )
        )

        synthesis_result = self._chat_single(
            prompt=synthesis_prompt,
            provider=synthesizer_provider,
            context="Produce one best final answer.",
            api_key="",
            model=synthesizer_model,
        )

        if synthesis_result.get("ok") and str(synthesis_result.get("response", "")).strip():
            return {
                "ok": True,
                "mode": "ensemble",
                "providers": ordered,
                "successful_providers": [entry.get("provider") for entry in successes],
                "responses": results,
                "synthesized": True,
                "synthesis_provider": synthesizer_provider,
                "response": synthesis_result.get("response", ""),
                "model": synthesis_result.get("model", ""),
            }

        best_fallback = max(successes, key=lambda item: len(str(item.get("response", ""))))
        return {
            "ok": True,
            "mode": "ensemble",
            "providers": ordered,
            "successful_providers": [entry.get("provider") for entry in successes],
            "responses": results,
            "synthesized": False,
            "response": best_fallback.get("response", ""),
            "model": best_fallback.get("model", ""),
            "provider": best_fallback.get("provider", ""),
            "warning": "Synthesis step failed; returning best provider response",
        }

    def _chat_ollama(
        self,
        prompt: str,
        context: str,
        cfg: Dict[str, Any],
        model_override: str = "",
        provider_name: str = "ollama",
    ) -> Dict[str, Any]:
        endpoint = cfg.get("endpoint", "http://127.0.0.1:11434/api/generate")
        model = model_override or cfg.get("model", "qwen2.5:7b")
        timeout = int(self.config.get("ai", {}).get("timeout_seconds", 120))

        user_prompt = prompt.strip()
        if context.strip():
            user_prompt = f"Context:\n{context.strip()}\n\nTask:\n{user_prompt}"

        try:
            response = requests.post(
                endpoint,
                json={
                    "model": model,
                    "prompt": user_prompt,
                    "stream": False,
                },
                timeout=timeout,
            )
            response.raise_for_status()
            payload = response.json()
            return {
                "ok": True,
                "provider": provider_name,
                "model": model,
                "response": payload.get("response", ""),
            }
        except Exception as exc:
            return {"ok": False, "provider": provider_name, "error": str(exc)}

    def _chat_openai_compatible(
        self,
        prompt: str,
        context: str,
        cfg: Dict[str, Any],
        api_key: str = "",
        model_override: str = "",
        provider_name: str = "openai-compatible",
    ) -> Dict[str, Any]:
        endpoint = cfg.get("endpoint", "").strip()
        model = model_override or cfg.get("model", "")
        if not endpoint:
            return {
                "ok": False,
                "error": "Provider endpoint not configured. Add endpoint in dev_hub_config.json",
                "provider": provider_name,
            }

        token = self._resolve_api_key(cfg, explicit_key=api_key)
        if not token:
            return {
                "ok": False,
                "error": "Provider API key missing. Configure api_key or api_key_env.",
                "provider": provider_name,
            }

        timeout = int(self.config.get("ai", {}).get("timeout_seconds", 120))
        messages = []
        if context.strip():
            messages.append({"role": "system", "content": context.strip()})
        messages.append({"role": "user", "content": prompt.strip()})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(endpoint, json=payload, headers=headers, timeout=timeout)
            response.raise_for_status()
            data = response.json()

            text = ""
            choices = data.get("choices")
            if isinstance(choices, list) and choices:
                first = choices[0]
                message = first.get("message", {})
                text = message.get("content", "") or first.get("text", "")

            if not text:
                text = data.get("response", "")

            return {
                "ok": True,
                "provider": provider_name,
                "model": model,
                "response": text,
                "raw": data,
            }
        except Exception as exc:
            return {"ok": False, "provider": provider_name, "error": str(exc)}


class ResearchClient:
    def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        query = query.strip()
        if not query:
            return {"ok": False, "error": "query is required"}

        try:
            from duckduckgo_search import DDGS  # type: ignore
        except Exception:
            return {
                "ok": False,
                "error": "duckduckgo-search is not installed. Install dependencies from apps/requirements.txt",
            }

        results: List[Dict[str, str]] = []
        try:
            with DDGS() as ddgs:
                for item in ddgs.text(query, max_results=max_results):
                    results.append(
                        {
                            "title": item.get("title", ""),
                            "url": item.get("href", ""),
                            "snippet": item.get("body", ""),
                        }
                    )
            return {"ok": True, "query": query, "results": results}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}


class _SimpleLinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attr_map = {k.lower(): (v or "") for k, v in attrs}
        target = ""
        if tag.lower() in {"a", "link"}:
            target = attr_map.get("href", "")
        elif tag.lower() in {"iframe", "script"}:
            target = attr_map.get("src", "")

        if target:
            self.links.append(target.strip())


class WebScraperClient:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config

    def _cfg(self) -> Dict[str, Any]:
        return self.config.get("scraper", {})

    def _enabled(self) -> bool:
        return bool(self._cfg().get("enabled", True))

    def _headers(self) -> Dict[str, str]:
        user_agent = str(self._cfg().get("user_agent", "TITAN-DevHub-Scraper/1.0"))
        return {"User-Agent": user_agent}

    def _extract_links(self, base_url: str, html: str) -> List[str]:
        parser = _SimpleLinkExtractor()
        try:
            parser.feed(html)
        except Exception:
            return []

        normalized: List[str] = []
        for raw_link in parser.links:
            absolute = urljoin(base_url, raw_link)
            scheme = urlparse(absolute).scheme.lower()
            if scheme in {"http", "https"} and absolute not in normalized:
                normalized.append(absolute)
        return normalized

    def _same_domain(self, left: str, right: str) -> bool:
        return urlparse(left).netloc.lower() == urlparse(right).netloc.lower()

    def _extract_title(self, html: str) -> str:
        match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if not match:
            return ""
        title = re.sub(r"\s+", " ", match.group(1)).strip()
        return title[:200]

    def _text_excerpt(self, html: str, limit: int = 1200) -> str:
        no_script = re.sub(r"<script.*?</script>", " ", html, flags=re.IGNORECASE | re.DOTALL)
        no_style = re.sub(r"<style.*?</style>", " ", no_script, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", no_style)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:limit]

    def build_operator_query(self, query: str, operators: Optional[Dict[str, Any]] = None) -> str:
        base = query.strip()
        op_map = operators or {}
        parts = [base] if base else []
        allowed = {"site", "filetype", "intitle", "inurl", "ext", "after", "before"}
        for key, value in op_map.items():
            op = str(key).strip().lower()
            val = str(value).strip()
            if op in allowed and val:
                parts.append(f"{op}:{val}")
        return " ".join(parts).strip()

    def search(self, query: str, operators: Optional[Dict[str, Any]] = None, max_results: int = 8) -> Dict[str, Any]:
        if not self._enabled():
            return {"ok": False, "error": "scraper integration disabled in config"}

        effective_query = self.build_operator_query(query, operators)
        if not effective_query:
            return {"ok": False, "error": "query is required"}

        try:
            from duckduckgo_search import DDGS  # type: ignore
        except Exception:
            return {
                "ok": False,
                "error": "duckduckgo-search is not installed. Install dependencies from apps/requirements.txt",
            }

        rows: List[Dict[str, str]] = []
        try:
            with DDGS() as ddgs:
                for item in ddgs.text(effective_query, max_results=max_results):
                    rows.append(
                        {
                            "title": item.get("title", ""),
                            "url": item.get("href", ""),
                            "snippet": item.get("body", ""),
                        }
                    )
            return {
                "ok": True,
                "query": query,
                "effective_query": effective_query,
                "results": rows,
                "note": "Use only authorized/legal research targets.",
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc), "effective_query": effective_query}

    def crawl(
        self,
        start_url: str,
        max_depth: Optional[int] = None,
        max_pages: Optional[int] = None,
        same_domain: Optional[bool] = None,
    ) -> Dict[str, Any]:
        if not self._enabled():
            return {"ok": False, "error": "scraper integration disabled in config"}

        parsed = urlparse(start_url.strip())
        if parsed.scheme.lower() not in {"http", "https"}:
            return {"ok": False, "error": "start_url must be http/https"}

        cfg = self._cfg()
        depth_limit = int(max_depth if max_depth is not None else cfg.get("max_depth", 2))
        page_limit = int(max_pages if max_pages is not None else cfg.get("max_pages", 20))
        same_domain_only = bool(
            cfg.get("same_domain_default", True) if same_domain is None else same_domain
        )
        timeout = int(cfg.get("timeout_seconds", 20))
        max_bytes = int(cfg.get("max_response_bytes", 1500000))

        queue: Deque[Tuple[str, int]] = deque([(start_url.strip(), 0)])
        visited: Set[str] = set()
        pages: List[Dict[str, Any]] = []

        while queue and len(pages) < page_limit:
            current_url, depth = queue.popleft()
            if current_url in visited or depth > depth_limit:
                continue
            visited.add(current_url)

            try:
                response = requests.get(
                    current_url,
                    headers=self._headers(),
                    timeout=timeout,
                    allow_redirects=True,
                )
                status_code = response.status_code
                raw_content = response.content[:max_bytes]
                body = raw_content.decode(response.encoding or "utf-8", errors="ignore")
                content_type = response.headers.get("Content-Type", "")

                title = self._extract_title(body)
                excerpt = self._text_excerpt(body)
                links = self._extract_links(current_url, body)

                pages.append(
                    {
                        "url": current_url,
                        "depth": depth,
                        "status_code": status_code,
                        "content_type": content_type,
                        "title": title,
                        "excerpt": excerpt,
                        "links_found": len(links),
                        "links_sample": links[:12],
                    }
                )

                if depth < depth_limit:
                    for link in links:
                        if link in visited:
                            continue
                        if same_domain_only and not self._same_domain(start_url, link):
                            continue
                        queue.append((link, depth + 1))

            except Exception as exc:
                pages.append(
                    {
                        "url": current_url,
                        "depth": depth,
                        "status_code": 0,
                        "error": str(exc),
                    }
                )

        return {
            "ok": True,
            "start_url": start_url,
            "same_domain": same_domain_only,
            "max_depth": depth_limit,
            "max_pages": page_limit,
            "visited_urls": len(visited),
            "pages": pages,
            "note": "Crawl only systems you are authorized to assess.",
        }

    def discover(
        self,
        query: str,
        operators: Optional[Dict[str, Any]] = None,
        max_results: int = 5,
        crawl_depth: int = 1,
        crawl_pages_per_seed: int = 4,
        same_domain: bool = True,
    ) -> Dict[str, Any]:
        search_data = self.search(query=query, operators=operators, max_results=max_results)
        if not search_data.get("ok"):
            return search_data

        crawls: List[Dict[str, Any]] = []
        for row in search_data.get("results", [])[: max(1, min(max_results, 5))]:
            target = str(row.get("url", "")).strip()
            if not target:
                continue
            crawls.append(
                self.crawl(
                    start_url=target,
                    max_depth=crawl_depth,
                    max_pages=crawl_pages_per_seed,
                    same_domain=same_domain,
                )
            )

        return {
            "ok": True,
            "search": search_data,
            "crawls": crawls,
            "seed_count": len(crawls),
        }


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    SKIPPED = "skipped"


@dataclass
class PipelineStep:
    id: str
    title: str
    step_type: str
    model_role: str
    prompt_template: str
    depends_on: List[str] = field(default_factory=list)
    status: str = StepStatus.PENDING
    attempt: int = 0
    max_retries: int = 3
    result: Optional[Dict[str, Any]] = None
    error: str = ""
    started_at: str = ""
    completed_at: str = ""
    validation_rules: List[str] = field(default_factory=list)


@dataclass
class PipelineState:
    pipeline_id: str
    task_id: str
    task_title: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "pending"
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    current_step_index: int = 0
    total_steps: int = 0
    error: str = ""


MODEL_ROLE_MAP = {
    "analyze": {"ollama_model": "qwen2.5:7b", "role": "analyst"},
    "strategize": {"ollama_model": "deepseek-r1:8b", "role": "strategist"},
    "execute": {"ollama_model": "mistral:7b", "role": "fast"},
    "validate": {"ollama_model": "qwen2.5:7b", "role": "analyst"},
    "research": {"ollama_model": "qwen2.5:7b", "role": "analyst"},
    "plan": {"ollama_model": "deepseek-r1:8b", "role": "strategist"},
    "summarize": {"ollama_model": "mistral:7b", "role": "fast"},
}

COT_SYSTEM_PROMPT = """You are an expert Titan OS development agent operating inside the Titan Dev Hub IDE.
You MUST follow this exact reasoning protocol for EVERY response:

## PROTOCOL
1. UNDERSTAND: Restate the task in your own words. What exactly is being asked?
2. ANALYZE: What information do you have? What are the constraints? What could go wrong?
3. PLAN: List the exact steps you will take, numbered.
4. EXECUTE: Carry out each step, showing your work.
5. VALIDATE: Check your output. Does it satisfy the original task? Any errors?
6. RESULT: Provide the final clean output.

## RULES
- Never skip steps. Never give partial answers.
- If you are uncertain, say so and explain what additional info you need.
- Output valid JSON when the task requires structured data.
- Be precise with file paths, class names, and function signatures.
- Think step by step. Quality over speed."""


class ChainOfThoughtPrompter:
    def build_prompt(
        self,
        task_description: str,
        step_context: str,
        prior_results: List[Dict[str, Any]],
        step_type: str,
    ) -> str:
        prior_summary = ""
        if prior_results:
            summaries = []
            for pr in prior_results[-5:]:
                step_title = pr.get("title", "unknown")
                step_result = pr.get("result", {})
                result_text = json.dumps(step_result, indent=1)[:800] if step_result else "no result"
                summaries.append(f"[{step_title}]: {result_text}")
            prior_summary = "\n\nPrior completed steps:\n" + "\n".join(summaries)

        refinement = ""
        if step_type == "analyze":
            refinement = "\nFocus: Be thorough. List every file, every issue, every finding. Miss nothing."
        elif step_type == "strategize":
            refinement = "\nFocus: Think deeply about trade-offs, risks, and the optimal approach. Consider failure modes."
        elif step_type == "execute":
            refinement = "\nFocus: Produce exact code/commands. No pseudocode. Every line must be runnable."
        elif step_type == "validate":
            refinement = "\nFocus: Check correctness rigorously. List any issues found. Be the harshest critic."
        elif step_type == "plan":
            refinement = "\nFocus: Break the problem into the smallest possible atomic steps. Each step must be independently completable."

        return f"""{COT_SYSTEM_PROMPT}
{refinement}

## CURRENT TASK
{task_description}

## STEP CONTEXT
{step_context}
{prior_summary}

Now follow the PROTOCOL above. Think step by step."""


class StepValidator:
    @staticmethod
    def validate(step: Dict[str, Any], result: Dict[str, Any]) -> Tuple[bool, str]:
        rules = step.get("validation_rules", [])
        response_text = str(result.get("response", ""))

        if not response_text.strip():
            return False, "Empty response from model"

        if len(response_text.strip()) < 20:
            return False, f"Response too short ({len(response_text.strip())} chars), likely incomplete"

        for rule in rules:
            if rule == "must_have_json":
                if "{" not in response_text and "[" not in response_text:
                    return False, "Response must contain JSON but none found"
            elif rule == "must_have_code":
                if "def " not in response_text and "class " not in response_text and "import " not in response_text:
                    return False, "Response must contain code but none found"
            elif rule == "must_have_steps":
                if not re.search(r"(?:step\s*\d|^\d+[\.\)]\s)", response_text, re.IGNORECASE | re.MULTILINE):
                    return False, "Response must contain numbered steps but none found"
            elif rule == "must_have_file_paths":
                if "/" not in response_text and "\\" not in response_text:
                    return False, "Response must reference file paths but none found"
            elif rule.startswith("min_length:"):
                min_len = int(rule.split(":")[1])
                if len(response_text.strip()) < min_len:
                    return False, f"Response shorter than minimum {min_len} chars"

        return True, "valid"

    @staticmethod
    def build_retry_prompt(original_prompt: str, error: str, attempt: int) -> str:
        return f"""Your previous attempt had this issue: {error}

Please try again with more care. This is attempt {attempt + 1}.
Pay extra attention to completeness and correctness.

ORIGINAL TASK:
{original_prompt}

Remember: Follow the PROTOCOL. Think step by step. Do NOT give partial answers."""


class TaskDecomposer:
    TEMPLATES = {
        "scan_full_stack": [
            {
                "title": "Scan Python syntax across all modules",
                "step_type": "analyze",
                "model_role": "analyze",
                "prompt_template": "Analyze the scan results below. List every syntax error, missing file, and structural issue. Be exhaustive.\n\nScan data: {scan_data}",
                "validation_rules": ["min_length:100"],
            },
            {
                "title": "Identify API route coverage gaps",
                "step_type": "analyze",
                "model_role": "analyze",
                "prompt_template": "Given these API routes and scan results, identify which routes may be missing handlers, which modules are unwired, and any dead endpoints.\n\nRoutes: {api_routes}\nScan: {scan_summary}",
                "validation_rules": ["min_length:100"],
            },
            {
                "title": "Produce prioritized fix plan",
                "step_type": "plan",
                "model_role": "strategize",
                "prompt_template": "Based on the analysis results, create a prioritized fix plan. Rank by impact (critical > high > medium > low). Each item must have: file path, issue, fix description, estimated complexity.\n\nAnalysis: {prior_results}",
                "validation_rules": ["must_have_steps", "min_length:200"],
            },
            {
                "title": "Summarize findings for operator",
                "step_type": "summarize",
                "model_role": "summarize",
                "prompt_template": "Create a concise executive summary of the full stack scan. Include: total files, errors found, critical issues, recommended next actions. Keep under 500 words.\n\nFull analysis: {prior_results}",
                "validation_rules": ["min_length:100"],
            },
        ],
        "upgrade_readiness": [
            {
                "title": "Scan current system state",
                "step_type": "analyze",
                "model_role": "analyze",
                "prompt_template": "Analyze the current Titan OS state for upgrade readiness. Check: all modules parse, API routes loaded, services running, dependencies installed.\n\nScan data: {scan_data}\nVPS info: {vps_data}",
                "validation_rules": ["min_length:100"],
            },
            {
                "title": "Identify upgrade blockers",
                "step_type": "analyze",
                "model_role": "analyze",
                "prompt_template": "From the system state analysis, identify every upgrade blocker: broken imports, missing dependencies, incompatible versions, unwired modules, config issues.\n\nState analysis: {prior_results}",
                "validation_rules": ["min_length:100"],
            },
            {
                "title": "Research best practices for upgrade",
                "step_type": "research",
                "model_role": "research",
                "prompt_template": "What are the best practices for safely upgrading a Python-based OS platform? Consider: dependency management, rollback strategy, staged rollout, testing gates.\n\nCurrent blockers: {prior_results}",
                "validation_rules": ["min_length:100"],
            },
            {
                "title": "Create upgrade execution plan",
                "step_type": "plan",
                "model_role": "strategize",
                "prompt_template": "Create a detailed, step-by-step upgrade execution plan. Each step must be atomic and reversible. Include pre-checks, execution, post-validation, and rollback for each step.\n\nBlockers: {prior_results}\nBest practices: {research_results}",
                "validation_rules": ["must_have_steps", "min_length:300"],
            },
            {
                "title": "Generate pre-upgrade validation checklist",
                "step_type": "validate",
                "model_role": "validate",
                "prompt_template": "Create a validation checklist that must pass BEFORE the upgrade begins. Each item must be a concrete, automatable check (e.g., 'python3 -c \"import X\"').\n\nUpgrade plan: {prior_results}",
                "validation_rules": ["must_have_steps", "min_length:200"],
            },
        ],
        "agentic_code_fix": [
            {
                "title": "Analyze the target file/module",
                "step_type": "analyze",
                "model_role": "analyze",
                "prompt_template": "Analyze this code for issues. List every bug, style issue, missing import, broken reference, and potential runtime error.\n\nFile: {file_path}\nContent:\n{file_content}",
                "validation_rules": ["min_length:100"],
            },
            {
                "title": "Plan the fix strategy",
                "step_type": "plan",
                "model_role": "strategize",
                "prompt_template": "Based on the analysis, plan the minimal set of changes needed. Each change must be atomic. Specify exact line ranges and what to change.\n\nAnalysis: {prior_results}",
                "validation_rules": ["must_have_steps", "min_length:100"],
            },
            {
                "title": "Generate the fixed code",
                "step_type": "execute",
                "model_role": "execute",
                "prompt_template": "Apply the fix plan to generate the corrected code. Output the COMPLETE fixed file content.\n\nOriginal file: {file_content}\nFix plan: {prior_results}",
                "validation_rules": ["must_have_code", "min_length:50"],
            },
            {
                "title": "Validate the fix",
                "step_type": "validate",
                "model_role": "validate",
                "prompt_template": "Validate the fixed code. Check: syntax correctness, all imports valid, no regressions, fix plan items addressed. List any remaining issues.\n\nOriginal: {file_content}\nFixed: {prior_results}",
                "validation_rules": ["min_length:100"],
            },
        ],
        "agentic_research": [
            {
                "title": "Formulate research queries",
                "step_type": "plan",
                "model_role": "plan",
                "prompt_template": "Break this research question into 3-5 specific, searchable queries. Each query should target a different aspect of the problem.\n\nQuestion: {query}",
                "validation_rules": ["must_have_steps", "min_length:50"],
            },
            {
                "title": "Analyze research results",
                "step_type": "analyze",
                "model_role": "analyze",
                "prompt_template": "Analyze these web research results. Extract key findings, best practices, and actionable recommendations relevant to Titan OS development.\n\nResults: {research_results}",
                "validation_rules": ["min_length:150"],
            },
            {
                "title": "Synthesize implementation recommendations",
                "step_type": "strategize",
                "model_role": "strategize",
                "prompt_template": "Synthesize the research analysis into concrete implementation recommendations for Titan OS. Prioritize by impact and feasibility. Include code patterns where applicable.\n\nAnalysis: {prior_results}",
                "validation_rules": ["must_have_steps", "min_length:200"],
            },
        ],
        "_default": [
            {
                "title": "Analyze the request",
                "step_type": "analyze",
                "model_role": "analyze",
                "prompt_template": "Analyze this task request thoroughly. What needs to be done? What are the constraints? What information is available?\n\nTask: {task_description}\nPayload: {task_payload}",
                "validation_rules": ["min_length:50"],
            },
            {
                "title": "Plan execution",
                "step_type": "plan",
                "model_role": "strategize",
                "prompt_template": "Create a step-by-step execution plan for this task.\n\nAnalysis: {prior_results}",
                "validation_rules": ["must_have_steps"],
            },
            {
                "title": "Execute and produce result",
                "step_type": "execute",
                "model_role": "execute",
                "prompt_template": "Execute the plan and produce the final result.\n\nPlan: {prior_results}",
                "validation_rules": ["min_length:50"],
            },
        ],
    }

    @classmethod
    def decompose(cls, task_type: str, task_title: str, payload: Dict[str, Any]) -> List[PipelineStep]:
        templates = cls.TEMPLATES.get(task_type, cls.TEMPLATES["_default"])
        steps: List[PipelineStep] = []
        prev_id = ""
        for idx, tmpl in enumerate(templates):
            step_id = f"step_{idx:03d}_{uuid.uuid4().hex[:6]}"
            step = PipelineStep(
                id=step_id,
                title=tmpl["title"],
                step_type=tmpl["step_type"],
                model_role=tmpl["model_role"],
                prompt_template=tmpl["prompt_template"],
                depends_on=[prev_id] if prev_id else [],
                validation_rules=tmpl.get("validation_rules", []),
            )
            steps.append(step)
            prev_id = step_id
        return steps


class CheckpointStore:
    def __init__(self, state_dir: Path) -> None:
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _path(self, pipeline_id: str) -> Path:
        return self.state_dir / f"pipeline_{pipeline_id}.json"

    def save(self, state: PipelineState) -> None:
        state.updated_at = utc_now()
        with self._lock:
            save_json(self._path(state.pipeline_id), asdict(state))

    def load(self, pipeline_id: str) -> Optional[PipelineState]:
        path = self._path(pipeline_id)
        if not path.exists():
            return None
        data = load_json(path, None)
        if not data:
            return None
        steps_raw = data.pop("steps", [])
        state = PipelineState(**{k: v for k, v in data.items() if k != "steps"})
        state.steps = steps_raw
        return state

    def list_pipelines(self) -> List[Dict[str, Any]]:
        results = []
        for p in sorted(self.state_dir.glob("pipeline_*.json")):
            data = load_json(p, None)
            if data:
                results.append({
                    "pipeline_id": data.get("pipeline_id", ""),
                    "task_id": data.get("task_id", ""),
                    "task_title": data.get("task_title", ""),
                    "status": data.get("status", ""),
                    "current_step_index": data.get("current_step_index", 0),
                    "total_steps": data.get("total_steps", 0),
                    "updated_at": data.get("updated_at", ""),
                })
        return results


class AgenticPipelineEngine:
    def __init__(
        self,
        ai_client: "AIClient",
        scanner: "TitanScanner",
        editor: "SafeSystemEditor",
        research_client: "ResearchClient",
        hostinger_client: "HostingerClient",
        checkpoint_store: CheckpointStore,
        config: Dict[str, Any],
    ) -> None:
        self.ai = ai_client
        self.scanner = scanner
        self.editor = editor
        self.research = research_client
        self.hostinger = hostinger_client
        self.checkpoints = checkpoint_store
        self.config = config
        self.cot = ChainOfThoughtPrompter()
        self.validator = StepValidator()
        self._active: Dict[str, threading.Thread] = {}

    def _select_model_for_role(self, role: str) -> str:
        role_cfg = MODEL_ROLE_MAP.get(role, MODEL_ROLE_MAP["analyze"])
        providers = self.config.get("providers", {})
        ollama_cfg = providers.get("ollama", {})
        if ollama_cfg.get("enabled"):
            return role_cfg["ollama_model"]
        return ollama_cfg.get("model", "qwen2.5:7b")

    def _call_model(self, prompt: str, role: str) -> Dict[str, Any]:
        model = self._select_model_for_role(role)
        ollama_cfg = self.config.get("providers", {}).get("ollama", {})
        endpoint = ollama_cfg.get("endpoint", "http://127.0.0.1:11434/api/generate")
        timeout = int(self.config.get("ai", {}).get("timeout_seconds", 120))

        try:
            resp = requests.post(
                endpoint,
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            return {"ok": True, "response": data.get("response", ""), "model": model}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "model": model}

    def _gather_context(self, task: Dict[str, Any], step: Dict[str, Any], prior_results: List[Dict[str, Any]]) -> Dict[str, str]:
        ctx: Dict[str, str] = {}
        payload = task.get("payload", {}) or {}

        ctx["task_description"] = task.get("title", "") + "\n" + task.get("description", "")
        ctx["task_payload"] = json.dumps(payload, indent=1)[:2000]

        prior_text = json.dumps(
            [{"title": p.get("title", ""), "result_excerpt": str(p.get("result", {}))[:600]} for p in prior_results[-5:]],
            indent=1,
        )
        ctx["prior_results"] = prior_text

        task_type = task.get("task_type", "")
        if task_type in ("scan_full_stack", "upgrade_readiness"):
            scan = self.scanner.scan(system_scan=task_type == "upgrade_readiness")
            ctx["scan_data"] = json.dumps(scan, indent=1)[:4000]
            ctx["scan_summary"] = json.dumps(scan.get("totals", {}))
            ctx["api_routes"] = json.dumps(scan.get("api_routes_sample", [])[:20])

        if task_type == "upgrade_readiness":
            vps = self.hostinger.list_vps()
            ctx["vps_data"] = json.dumps(vps, indent=1)[:2000]

        if task_type in ("agentic_research", "research"):
            query = str(payload.get("query", task.get("title", "")))
            results = self.research.search(query, max_results=6)
            ctx["research_results"] = json.dumps(results, indent=1)[:3000]
            ctx["query"] = query

        if task_type == "agentic_code_fix":
            fpath = str(payload.get("path", ""))
            if fpath:
                ok, content = self.editor.read_file(fpath, system_mode=bool(payload.get("system_mode", False)))
                ctx["file_path"] = fpath
                ctx["file_content"] = content[:6000] if ok else f"ERROR: {content}"

        return ctx

    def _render_prompt(self, template: str, context: Dict[str, str]) -> str:
        rendered = template
        for key, value in context.items():
            rendered = rendered.replace("{" + key + "}", str(value))
        return rendered

    def _execute_step(
        self,
        task: Dict[str, Any],
        step: Dict[str, Any],
        prior_results: List[Dict[str, Any]],
        state: PipelineState,
    ) -> Dict[str, Any]:
        ctx = self._gather_context(task, step, prior_results)
        raw_prompt = self._render_prompt(step.get("prompt_template", ""), ctx)
        role = step.get("model_role", "analyze")

        full_prompt = self.cot.build_prompt(
            task_description=ctx.get("task_description", ""),
            step_context=raw_prompt,
            prior_results=prior_results,
            step_type=step.get("step_type", "analyze"),
        )

        max_retries = step.get("max_retries", 3)
        last_error = ""

        for attempt in range(max_retries):
            step["attempt"] = attempt + 1
            step["status"] = StepStatus.RUNNING if attempt == 0 else StepStatus.RETRYING
            step["started_at"] = utc_now()
            self.checkpoints.save(state)

            prompt_to_use = full_prompt if attempt == 0 else self.validator.build_retry_prompt(full_prompt, last_error, attempt)

            result = self._call_model(prompt_to_use, role)

            if not result.get("ok"):
                last_error = result.get("error", "model call failed")
                LOG.warning("Step %s attempt %d failed: %s", step["id"], attempt + 1, last_error)
                time.sleep(min(2 ** attempt, 10))
                continue

            is_valid, validation_msg = self.validator.validate(step, result)
            if is_valid:
                step["status"] = StepStatus.COMPLETED
                step["result"] = result
                step["completed_at"] = utc_now()
                step["error"] = ""
                self.checkpoints.save(state)
                return result

            last_error = validation_msg
            LOG.warning("Step %s attempt %d validation failed: %s", step["id"], attempt + 1, validation_msg)
            time.sleep(min(2 ** attempt, 8))

        step["status"] = StepStatus.FAILED
        step["error"] = f"Failed after {max_retries} attempts: {last_error}"
        step["completed_at"] = utc_now()
        self.checkpoints.save(state)
        return {"ok": False, "error": step["error"]}

    def run_pipeline(self, task: Dict[str, Any], task_store: "TaskStore") -> Dict[str, Any]:
        task_id = task.get("id", "")
        task_type = task.get("task_type", "")
        task_title = task.get("title", "")
        payload = task.get("payload", {}) or {}

        pipeline_id = hashlib.md5(f"{task_id}:{utc_now()}".encode()).hexdigest()[:12]

        steps = TaskDecomposer.decompose(task_type, task_title, payload)
        step_dicts = [asdict(s) for s in steps]

        state = PipelineState(
            pipeline_id=pipeline_id,
            task_id=task_id,
            task_title=task_title,
            steps=step_dicts,
            status="running",
            total_steps=len(step_dicts),
        )
        self.checkpoints.save(state)

        task_store.update_task(task_id, status="running", error="",
                               pipeline_id=pipeline_id, pipeline_total_steps=len(step_dicts))

        prior_results: List[Dict[str, Any]] = []
        all_ok = True

        for idx, step in enumerate(state.steps):
            state.current_step_index = idx
            self.checkpoints.save(state)
            task_store.update_task(task_id, pipeline_current_step=idx,
                                   pipeline_step_title=step.get("title", ""))

            if step.get("status") == StepStatus.COMPLETED and step.get("result"):
                prior_results.append(step)
                continue

            LOG.info("Pipeline %s: executing step %d/%d: %s (role=%s)",
                     pipeline_id, idx + 1, len(state.steps), step.get("title"), step.get("model_role"))

            result = self._execute_step(task, step, prior_results, state)

            if result.get("ok"):
                prior_results.append(step)
            else:
                all_ok = False
                LOG.error("Pipeline %s: step %d failed: %s", pipeline_id, idx + 1, step.get("error"))

        state.status = "completed" if all_ok else "completed_with_errors"
        state.updated_at = utc_now()
        self.checkpoints.save(state)

        final_summary = {
            "pipeline_id": pipeline_id,
            "total_steps": len(state.steps),
            "completed_steps": sum(1 for s in state.steps if s.get("status") == StepStatus.COMPLETED),
            "failed_steps": sum(1 for s in state.steps if s.get("status") == StepStatus.FAILED),
            "steps": [
                {
                    "id": s.get("id"),
                    "title": s.get("title"),
                    "status": s.get("status"),
                    "model_role": s.get("model_role"),
                    "attempt": s.get("attempt", 0),
                    "result_excerpt": str(s.get("result", {}).get("response", ""))[:500] if s.get("result") else "",
                    "error": s.get("error", ""),
                }
                for s in state.steps
            ],
        }

        task_store.update_task(task_id, status="completed" if all_ok else "completed_with_errors",
                               result=final_summary)

        return {"ok": all_ok, "pipeline": final_summary}

    def resume_pipeline(self, pipeline_id: str, task: Dict[str, Any], task_store: "TaskStore") -> Dict[str, Any]:
        state = self.checkpoints.load(pipeline_id)
        if not state:
            return {"ok": False, "error": f"Pipeline {pipeline_id} not found"}

        incomplete = [s for s in state.steps if s.get("status") not in (StepStatus.COMPLETED, StepStatus.SKIPPED)]
        if not incomplete:
            return {"ok": True, "message": "Pipeline already completed", "pipeline_id": pipeline_id}

        state.status = "running"
        self.checkpoints.save(state)

        prior_results = [s for s in state.steps if s.get("status") == StepStatus.COMPLETED and s.get("result")]
        all_ok = True

        for idx, step in enumerate(state.steps):
            state.current_step_index = idx
            if step.get("status") == StepStatus.COMPLETED:
                continue

            step["status"] = StepStatus.PENDING
            step["error"] = ""
            result = self._execute_step(task, step, prior_results, state)

            if result.get("ok"):
                prior_results.append(step)
            else:
                all_ok = False

        state.status = "completed" if all_ok else "completed_with_errors"
        self.checkpoints.save(state)

        final = {
            "pipeline_id": pipeline_id,
            "resumed": True,
            "total_steps": len(state.steps),
            "completed_steps": sum(1 for s in state.steps if s.get("status") == StepStatus.COMPLETED),
            "failed_steps": sum(1 for s in state.steps if s.get("status") == StepStatus.FAILED),
        }

        task_store.update_task(state.task_id, status=state.status, result=final)
        return {"ok": all_ok, "pipeline": final}


class HostingerClient:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.cfg = config.get("hostinger", {})

    def _token(self) -> str:
        token = self.cfg.get("api_token", "")
        if token:
            return token
        env_name = self.cfg.get("api_token_env", "HOSTINGER_API_TOKEN")
        return os.environ.get(env_name, "")

    def _base_url(self) -> str:
        return self.cfg.get("base_url", "https://developers.hostinger.com").rstrip("/")

    def _request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.cfg.get("enabled", True):
            return {"ok": False, "error": "Hostinger integration disabled in config"}

        token = self._token()
        if not token:
            return {
                "ok": False,
                "error": "Missing Hostinger API token. Set HOSTINGER_API_TOKEN or hostinger.api_token",
            }

        url = f"{self._base_url()}{path}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.request(method, url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            return {"ok": True, "data": response.json()}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "url": url}

    def list_vps(self) -> Dict[str, Any]:
        return self._request("GET", "/api/vps/v1/virtual-machines")

    def get_vps(self, vm_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/api/vps/v1/virtual-machines/{vm_id}")

    def get_actions(self, vm_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/api/vps/v1/virtual-machines/{vm_id}/actions")

    def get_metrics(self, vm_id: str, date_from: str, date_to: str) -> Dict[str, Any]:
        params = {
            "date_from": date_from,
            "date_to": date_to,
        }
        return self._request("GET", f"/api/vps/v1/virtual-machines/{vm_id}/metrics", params=params)


class VastAIClient:
    """Manage Vast.ai GPU instances for AI model training from within the IDE."""

    BASE = "https://console.vast.ai/api/v0"

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config

    def _cfg(self) -> Dict[str, Any]:
        return self.config.get("vastai", {})

    def _api_key(self) -> str:
        key = self._cfg().get("api_key", "")
        if key:
            return key
        env_name = self._cfg().get("api_key_env", "VASTAI_API_KEY")
        return os.environ.get(env_name, "")

    def _headers(self) -> Dict[str, str]:
        return {"Accept": "application/json", "Content-Type": "application/json"}

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        key = self._api_key()
        if not key:
            return {"ok": False, "error": "Vast.ai API key not configured. Set VASTAI_API_KEY or vastai.api_key in config."}
        url = f"{self.BASE}{path}"
        merged_params = dict(params or {})
        merged_params["api_key"] = key
        try:
            resp = requests.get(url, params=merged_params, headers=self._headers(), timeout=30)
            resp.raise_for_status()
            return {"ok": True, "data": resp.json()}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _put(self, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        key = self._api_key()
        if not key:
            return {"ok": False, "error": "Vast.ai API key not configured."}
        url = f"{self.BASE}{path}"
        try:
            resp = requests.put(f"{url}?api_key={key}", json=body or {}, headers=self._headers(), timeout=60)
            resp.raise_for_status()
            return {"ok": True, "data": resp.json() if resp.text.strip() else {}}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _delete(self, path: str) -> Dict[str, Any]:
        key = self._api_key()
        if not key:
            return {"ok": False, "error": "Vast.ai API key not configured."}
        url = f"{self.BASE}{path}"
        try:
            resp = requests.delete(f"{url}?api_key={key}", headers=self._headers(), timeout=30)
            resp.raise_for_status()
            return {"ok": True, "data": resp.json() if resp.text.strip() else {}}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _post(self, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        key = self._api_key()
        if not key:
            return {"ok": False, "error": "Vast.ai API key not configured."}
        url = f"{self.BASE}{path}"
        try:
            resp = requests.post(f"{url}?api_key={key}", json=body or {}, headers=self._headers(), timeout=60)
            resp.raise_for_status()
            return {"ok": True, "data": resp.json() if resp.text.strip() else {}}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def search_offers(
        self,
        gpu_name: str = "",
        num_gpus: int = 1,
        min_ram: float = 0,
        sort: str = "dph_total",
        limit: int = 10,
    ) -> Dict[str, Any]:
        query: Dict[str, Any] = {
            "verified": {"eq": True},
            "rentable": {"eq": True},
            "num_gpus": {"eq": num_gpus},
            "order": [[sort, "asc"]],
            "limit": limit,
            "type": "on-demand",
        }
        if gpu_name:
            query["gpu_name"] = {"eq": gpu_name}
        if min_ram > 0:
            query["gpu_ram"] = {"gte": min_ram}
        return self._get("/bundles", params={"q": json.dumps(query)})

    def list_instances(self) -> Dict[str, Any]:
        return self._get("/instances", params={"owner": "me"})

    def get_instance(self, instance_id: str) -> Dict[str, Any]:
        return self._get(f"/instances/{instance_id}")

    def create_instance(
        self,
        offer_id: str,
        image: str = "pytorch/pytorch:2.2.0-cuda12.1-cudnn8-devel",
        disk_gb: float = 40,
        onstart_cmd: str = "",
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "client_id": "me",
            "image": image,
            "disk": disk_gb,
            "runtype": "ssh",
        }
        if onstart_cmd:
            body["onstart"] = onstart_cmd
        return self._put(f"/asks/{offer_id}/", body=body)

    def destroy_instance(self, instance_id: str) -> Dict[str, Any]:
        return self._delete(f"/instances/{instance_id}/")

    def execute_command(self, instance_id: str, command: str) -> Dict[str, Any]:
        return self._put(f"/instances/{instance_id}/", body={"onstart": command})

    def get_logs(self, instance_id: str, tail: int = 100) -> Dict[str, Any]:
        key = self._api_key()
        if not key:
            return {"ok": False, "error": "Vast.ai API key not configured."}
        url = f"https://console.vast.ai/api/v0/instances/{instance_id}/logs"
        try:
            resp = requests.get(url, params={"api_key": key, "tail": tail}, headers=self._headers(), timeout=30)
            resp.raise_for_status()
            return {"ok": True, "logs": resp.text}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def start_training(
        self,
        instance_id: str,
        model_name: str = "titan-custom",
        base_model: str = "Qwen/Qwen2.5-7B",
        dataset_path: str = "/workspace/data",
        epochs: int = 3,
        batch_size: int = 2,
        learning_rate: float = 2e-5,
        max_seq_length: int = 4096,
        use_lora: bool = False,
        lora_rank: int = 16,
    ) -> Dict[str, Any]:
        lora_flag = ""
        if use_lora:
            lora_flag = f"--use_lora --lora_r {lora_rank} --lora_alpha {lora_rank * 2}"

        train_script = (
            f"cd /workspace && "
            f"pip install -q transformers datasets accelerate peft bitsandbytes trl wandb && "
            f"python -c \""
            f"from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer;"
            f"from datasets import load_from_disk;"
            f"import torch;"
            f"model = AutoModelForCausalLM.from_pretrained('{base_model}', torch_dtype=torch.bfloat16, device_map='auto');"
            f"tokenizer = AutoTokenizer.from_pretrained('{base_model}');"
            f"dataset = load_from_disk('{dataset_path}');"
            f"args = TrainingArguments("
            f"output_dir='/workspace/output/{model_name}',"
            f"num_train_epochs={epochs},"
            f"per_device_train_batch_size={batch_size},"
            f"learning_rate={learning_rate},"
            f"bf16=True,"
            f"gradient_checkpointing=True,"
            f"save_strategy='epoch',"
            f"logging_steps=10,"
            f"max_grad_norm=1.0,"
            f");"
            f"trainer = Trainer(model=model, args=args, train_dataset=dataset, tokenizer=tokenizer);"
            f"trainer.train();"
            f"trainer.save_model('/workspace/output/{model_name}/final');"
            f"print('TRAINING COMPLETE: {model_name}');"
            f"\""
        )

        return self.execute_command(instance_id, train_script)


class SmartCommandRouter:
    """Routes natural-language user prompts to the correct IDE action.
    Designed for zero-code-knowledge users who just describe what they want."""

    PATTERNS: List[Tuple[str, str, str]] = [
        (r"(?:scan|check|audit|analyze)\b.*(?:system|code|stack|app|module)", "scan_full_stack", "Running a full system scan..."),
        (r"(?:upgrade|update|migration|readiness)\b", "upgrade_readiness", "Checking upgrade readiness..."),
        (r"(?:fix|patch|repair|debug|solve)\b.*(?:code|bug|error|file|module)", "agentic_code_fix", "Starting AI-powered code fix..."),
        (r"(?:research|find out|look up|search for|learn about)\b", "agentic_research", "Launching AI research pipeline..."),
        (r"(?:train|fine.?tune|training|lora|finetune)\b.*(?:model|ai|llm|gpu)", "vastai_training", "Setting up GPU training..."),
        (r"(?:gpu|vast|instance|rent|cloud)\b.*(?:list|show|search|find|status)", "vastai_list", "Listing GPU instances..."),
        (r"(?:scrape|crawl|discover|dork|web.*search)\b", "scraper_discover", "Starting web discovery..."),
        (r"(?:service|daemon|systemctl|redis|ollama|xray|ntfy)\b.*(?:start|stop|restart|status|list)", "service_control", "Opening service control panel..."),
        (r"(?:verify|verification|self-test|run tests|test suite)\b", "run_verification", "Running verification tools..."),
        (r"(?:reboot|restart\s+system|restart\s+server)\b", "reboot_system", "Reboot requires confirmation in System tab."),
        (r"(?:edit|modify|change|write|create)\b.*(?:file|code|script|config)", "safe_edit", "Opening file editor..."),
        (r"(?:deploy|host|publish|launch|start)\b.*(?:app|server|service|site)", "deploy", "Preparing deployment..."),
        (r"(?:vps|server|hostinger)\b.*(?:status|info|list|metrics)", "hostinger_vps", "Checking VPS status..."),
        (r"(?:git|commit|push|branch|status)\b", "git_status", "Checking git status..."),
        (r"(?:ask|chat|help|explain|how|what|why)\b", "ai_chat", "Connecting to AI assistant..."),
    ]

    @classmethod
    def route(cls, user_input: str) -> Dict[str, Any]:
        text = user_input.strip().lower()
        if not text:
            return {
                "action": "ai_chat",
                "message": "What would you like to do? Just describe it in plain English.",
                "routed": False,
            }

        for pattern, action, message in cls.PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return {"action": action, "message": message, "routed": True, "query": user_input}

        return {
            "action": "ai_chat",
            "message": "I'll ask the AI assistant to help with that.",
            "routed": True,
            "query": user_input,
        }

    @classmethod
    def get_suggestions(cls) -> List[Dict[str, str]]:
        return [
            {"prompt": "Scan my entire system for issues", "icon": "search", "category": "System"},
            {"prompt": "Fix bugs in core/titan_api.py", "icon": "wrench", "category": "Code"},
            {"prompt": "Train a custom AI model on GPU", "icon": "cpu", "category": "Training"},
            {"prompt": "Search the web for OPSEC best practices", "icon": "globe", "category": "Research"},
            {"prompt": "Check my VPS server status", "icon": "server", "category": "Infrastructure"},
            {"prompt": "Run Titan verification scripts", "icon": "shield", "category": "Verification"},
            {"prompt": "Restart ollama service", "icon": "power", "category": "Operations"},
            {"prompt": "Research latest Python security patterns", "icon": "book", "category": "Research"},
            {"prompt": "Show available GPU instances for rent", "icon": "gpu", "category": "Training"},
            {"prompt": "Crawl example.com for documentation", "icon": "spider", "category": "Scraper"},
            {"prompt": "Check if my system is ready for upgrade", "icon": "upload", "category": "System"},
            {"prompt": "Edit the dev hub configuration", "icon": "settings", "category": "System"},
        ]


class SystemOpsManager:
    def __init__(self, titan_root: Path, config: Dict[str, Any]) -> None:
        self.titan_root = titan_root.resolve()
        self.config = config

    def _cfg(self) -> Dict[str, Any]:
        return self.config.get("ops", {})

    def is_scan_path_allowed(self, path: Path) -> bool:
        roots_raw = self._cfg().get("scan_allow_roots", [str(self.titan_root), "/etc", "/usr/local", "/var", "/home"])
        resolved = path.resolve()
        for raw_root in roots_raw:
            root = Path(str(raw_root)).resolve()
            try:
                resolved.relative_to(root)
                return True
            except Exception:
                continue
        return False

    def _service_allowed(self, service_name: str) -> bool:
        allowlist = self._cfg().get("service_allowlist", [])
        if not isinstance(allowlist, list) or not allowlist:
            return False
        for pattern in allowlist:
            if fnmatch.fnmatch(service_name, str(pattern)):
                return True
        return False

    def _run_process(self, command: List[str], timeout: int = 180, cwd: Optional[Path] = None) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                command,
                cwd=str(cwd or self.titan_root),
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout,
            )
            return {
                "ok": result.returncode == 0,
                "command": command,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except Exception as exc:
            return {"ok": False, "command": command, "error": str(exc)}

    def list_services(self, filter_text: str = "", limit: int = 120) -> Dict[str, Any]:
        result = self._run_process(
            ["systemctl", "list-units", "--type=service", "--all", "--no-legend", "--no-pager"],
            timeout=60,
        )
        if not result.get("ok"):
            return result

        needle = filter_text.strip().lower()
        services: List[Dict[str, Any]] = []
        for line in str(result.get("stdout", "")).splitlines():
            parts = line.split(None, 4)
            if len(parts) < 5:
                continue
            name, load, active, sub, description = parts
            if needle and needle not in name.lower() and needle not in description.lower():
                continue
            services.append(
                {
                    "name": name,
                    "load": load,
                    "active": active,
                    "sub": sub,
                    "description": description,
                    "manageable": self._service_allowed(name),
                }
            )
            if len(services) >= limit:
                break

        return {"ok": True, "services": services, "count": len(services)}

    def service_action(self, service_name: str, action: str) -> Dict[str, Any]:
        service = service_name.strip()
        verb = action.strip().lower()
        if not service:
            return {"ok": False, "error": "service is required"}
        if verb not in {"start", "stop", "restart", "status"}:
            return {"ok": False, "error": f"Unsupported service action: {verb}"}
        if not self._service_allowed(service):
            return {"ok": False, "error": f"Service not in allowlist: {service}"}

        if verb == "status":
            details = self._run_process(["systemctl", "status", service, "--no-pager", "--lines=40"], timeout=60)
            active = self._run_process(["systemctl", "is-active", service], timeout=20)
            return {
                "ok": details.get("ok", False),
                "service": service,
                "action": verb,
                "is_active": str(active.get("stdout", "")).strip(),
                "details": details,
            }

        action_result = self._run_process(["systemctl", verb, service], timeout=60)
        active = self._run_process(["systemctl", "is-active", service], timeout=20)
        return {
            "ok": action_result.get("ok", False),
            "service": service,
            "action": verb,
            "is_active": str(active.get("stdout", "")).strip(),
            "result": action_result,
        }

    def run_verification(self, script_path: str, args: Optional[List[str]] = None) -> Dict[str, Any]:
        requested = script_path.strip()
        if not requested:
            return {"ok": False, "error": "script_path is required"}

        allow_raw = self._cfg().get(
            "verification_scripts",
            [
                "/opt/titan/vps_verify_real.sh",
                "/opt/titan/core/titan_master_verify.py",
                "/opt/titan/core/verify_deep_identity.py",
            ],
        )
        allowed: Set[Path] = set()
        for item in allow_raw:
            p = Path(str(item).strip())
            if not p.is_absolute():
                p = (self.titan_root / p).resolve()
            else:
                p = p.resolve()
            allowed.add(p)

        target = Path(os.path.expanduser(requested))
        if not target.is_absolute():
            target = (self.titan_root / target).resolve()
        else:
            target = target.resolve()

        if target not in allowed:
            return {
                "ok": False,
                "error": f"Verification script not allowlisted: {target}",
                "allowed": [str(item) for item in sorted(allowed)],
            }
        if not target.exists():
            return {"ok": False, "error": f"Verification script not found: {target}"}

        cmd: List[str]
        if target.suffix.lower() == ".py":
            cmd = ["python3", str(target)]
        elif target.suffix.lower() == ".sh":
            cmd = ["bash", str(target)]
        else:
            cmd = [str(target)]

        if isinstance(args, list):
            cmd.extend([str(item) for item in args if str(item).strip()])

        result = self._run_process(cmd, timeout=1200, cwd=self.titan_root)
        result["script"] = str(target)
        return result

    def run_test_command(self, command_key: str, extra_args: Optional[List[str]] = None) -> Dict[str, Any]:
        key = command_key.strip()
        if not key:
            return {"ok": False, "error": "command_key is required"}

        command_map: Dict[str, List[str]] = {
            "test_runner": ["python3", "-m", "testing.test_runner"],
            "titan_master_verify": ["python3", "core/titan_master_verify.py"],
            "verify_deep_identity": ["python3", "core/verify_deep_identity.py"],
        }

        cfg_commands = self._cfg().get("test_commands", {})
        if isinstance(cfg_commands, dict):
            for name, value in cfg_commands.items():
                if isinstance(value, list):
                    parsed = [str(item) for item in value if str(item).strip()]
                    if parsed:
                        command_map[str(name)] = parsed
                elif isinstance(value, str):
                    parsed = shlex.split(value)
                    if parsed:
                        command_map[str(name)] = parsed

        if key not in command_map:
            return {"ok": False, "error": f"Unknown test command: {key}", "available": sorted(command_map.keys())}

        command = list(command_map[key])
        if isinstance(extra_args, list):
            command.extend([str(item) for item in extra_args if str(item).strip()])

        result = self._run_process(command, timeout=1200, cwd=self.titan_root)
        result["command_key"] = key
        return result

    def get_model_assignments(self) -> Dict[str, Any]:
        llm_cfg_path = self.titan_root / "config" / "llm_config.json"
        llm_cfg = load_json(llm_cfg_path, {})
        if not isinstance(llm_cfg, dict):
            return {"ok": False, "error": "Invalid llm_config.json format"}

        task_routing = llm_cfg.get("task_routing", {})
        if not isinstance(task_routing, dict):
            return {"ok": False, "error": "task_routing missing in llm_config.json"}

        provider_usage: Dict[str, int] = {}
        task_routes_sample: Dict[str, Any] = {}
        task_count = 0

        for task_name, routes in task_routing.items():
            if str(task_name).startswith("_") or not isinstance(routes, list):
                continue
            task_count += 1
            normalized = []
            for route in routes:
                if not isinstance(route, dict):
                    continue
                provider = str(route.get("provider", ""))
                model = str(route.get("model", ""))
                if provider:
                    provider_usage[provider] = provider_usage.get(provider, 0) + 1
                normalized.append({"provider": provider, "model": model})
            if len(task_routes_sample) < 25:
                task_routes_sample[str(task_name)] = normalized[:5]

        return {
            "ok": True,
            "llm_config_path": str(llm_cfg_path),
            "task_route_count": task_count,
            "provider_usage": provider_usage,
            "task_routes_sample": task_routes_sample,
        }

    def request_reboot(self, confirm_text: str) -> Dict[str, Any]:
        if not bool(self._cfg().get("allow_reboot", False)):
            return {"ok": False, "error": "Reboot is disabled in config (ops.allow_reboot=false)"}
        if confirm_text.strip() != "REBOOT_TITAN_OS":
            return {"ok": False, "error": "Invalid confirmation text. Expected: REBOOT_TITAN_OS"}

        result = self._run_process(["shutdown", "-r", "+1", "TITAN Dev Hub requested reboot"], timeout=20, cwd=self.titan_root)
        if result.get("ok"):
            result["message"] = "Reboot scheduled in 1 minute. Use 'shutdown -c' to cancel."
        return result


class TaskExecutor:
    def __init__(
        self,
        scanner: TitanScanner,
        editor: SafeSystemEditor,
        research: ResearchClient,
        hostinger: HostingerClient,
    ) -> None:
        self.scanner = scanner
        self.editor = editor
        self.research = research
        self.hostinger = hostinger

    def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        task_type = task.get("task_type", "")
        payload = task.get("payload", {}) or {}

        if task_type == "scan_full_stack":
            return self.scanner.scan(system_scan=bool(payload.get("system_scan", False)))

        if task_type == "upgrade_readiness":
            scan = self.scanner.scan(system_scan=True)
            vps = self.hostinger.list_vps()
            return {
                "scan": scan,
                "hostinger_vps": vps,
                "summary": {
                    "syntax_errors": scan.get("totals", {}).get("syntax_errors", 0),
                    "api_routes_count": scan.get("api_routes_count", 0),
                    "hostinger_ok": vps.get("ok", False),
                },
            }

        if task_type == "research":
            return self.research.search(str(payload.get("query", "")), max_results=int(payload.get("max_results", 5)))

        if task_type == "hostinger_vps_inventory":
            return self.hostinger.list_vps()

        if task_type == "safe_edit":
            path = str(payload.get("path", ""))
            content = str(payload.get("content", ""))
            actor = str(payload.get("actor", "task-agent"))
            reason = str(payload.get("reason", f"task:{task.get('id', '')}"))
            system_mode = bool(payload.get("system_mode", False))
            ok, message, backup = self.editor.write_file(
                path,
                content,
                actor=actor,
                reason=reason,
                system_mode=system_mode,
            )
            return {"ok": ok, "message": message, "backup": backup}

        if task_type == "git_status":
            return self._git_status()

        return {"ok": False, "error": f"Unsupported task_type: {task_type}"}

    def _git_status(self) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                ["git", "status", "--short"],
                cwd=str(self.scanner.titan_root),
                capture_output=True,
                text=True,
                check=False,
            )
            return {
                "ok": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}


def sanitize_config_for_api(config: Dict[str, Any]) -> Dict[str, Any]:
    redacted = json.loads(json.dumps(config))
    for provider in redacted.get("providers", {}).values():
        if "api_key" in provider and provider["api_key"]:
            provider["api_key"] = "***redacted***"
    hostinger_cfg = redacted.get("hostinger", {})
    if hostinger_cfg.get("api_token"):
        hostinger_cfg["api_token"] = "***redacted***"
    auth_cfg = redacted.get("auth", {})
    if auth_cfg.get("api_token"):
        auth_cfg["api_token"] = "***redacted***"
    vastai_cfg = redacted.get("vastai", {})
    if vastai_cfg.get("api_key"):
        vastai_cfg["api_key"] = "***redacted***"
    return redacted


def build_index_html(default_provider: str) -> str:
    safe_default_provider = json.dumps(default_provider)
    html = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"/>
<meta name="theme-color" content="#080e1a"/>
<title>TITAN Dev Hub</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{
--bg:#080e1a;--s1:#0d1526;--s2:#131d33;--s3:#1a2744;
--bdr:#243356;--text:#e4eaf6;--dim:#8899b8;--acc:#22d68a;
--blue:#4d9fff;--purple:#a78bfa;--warn:#ffbe55;--err:#ff6070;
--r:10px;--font:"Inter",system-ui,-apple-system,sans-serif;
}
html,body{height:100%;background:var(--bg);color:var(--text);font-family:var(--font);font-size:13px;overflow-x:hidden}
a{color:var(--blue);text-decoration:none}

/* ── header ── */
.hdr{position:sticky;top:0;z-index:90;display:flex;align-items:center;gap:10px;padding:10px 16px;
 background:rgba(8,14,26,.94);backdrop-filter:blur(8px);border-bottom:1px solid var(--bdr)}
.hdr .logo{font-weight:700;font-size:15px;white-space:nowrap}
.hdr .logo span{color:var(--acc)}
.hdr .spacer{flex:1}
.pill{display:inline-block;padding:2px 9px;border:1px solid var(--bdr);border-radius:99px;font-size:10px;color:var(--dim)}
.pill.g{border-color:var(--acc);color:var(--acc)}.pill.r{border-color:var(--err);color:var(--err)}

/* ── smart command bar ── */
.cmd-wrap{padding:12px 16px;background:linear-gradient(135deg,#0e1a30 0%,#0b1222 100%);border-bottom:1px solid var(--bdr)}
.cmd-bar{display:flex;gap:8px;max-width:900px;margin:0 auto}
.cmd-bar input{flex:1;background:var(--s1);border:1px solid var(--bdr);border-radius:var(--r);padding:12px 16px;color:var(--text);font-size:14px;outline:none;transition:border .2s}
.cmd-bar input:focus{border-color:var(--blue)}
.cmd-bar input::placeholder{color:var(--dim)}
.cmd-bar button{background:linear-gradient(135deg,#1b6b47,#18905e);border:none;border-radius:var(--r);color:#fff;font-weight:600;padding:0 22px;cursor:pointer;font-size:13px;white-space:nowrap}
.cmd-bar button:hover{filter:brightness(1.15)}
.cmd-hint{text-align:center;padding:6px 0 2px;color:var(--dim);font-size:11px}

/* ── suggestions ── */
.sugg-row{display:flex;gap:8px;padding:4px 16px 10px;overflow-x:auto;max-width:100%}
.sugg-chip{flex:0 0 auto;background:var(--s2);border:1px solid var(--bdr);border-radius:20px;padding:6px 14px;font-size:11px;color:var(--dim);cursor:pointer;white-space:nowrap;transition:all .15s}
.sugg-chip:hover{background:var(--s3);color:var(--text);border-color:var(--blue)}

/* ── nav tabs ── */
.nav{display:flex;gap:4px;padding:8px 16px;background:var(--s1);border-bottom:1px solid var(--bdr);overflow-x:auto}
.nav button{background:transparent;border:1px solid transparent;border-radius:8px;padding:8px 14px;color:var(--dim);cursor:pointer;font-size:12px;font-weight:600;white-space:nowrap;transition:all .15s}
.nav button.on{color:var(--text);background:var(--s2);border-color:var(--bdr)}
.nav button:hover{color:var(--text)}

/* ── panels ── */
.panel{display:none;padding:12px 16px;animation:fadeUp .2s ease}
.panel.on{display:block}
@keyframes fadeUp{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}

/* ── grid + card ── */
.g2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.card{background:var(--s2);border:1px solid var(--bdr);border-radius:var(--r);padding:14px}
.card.w2{grid-column:span 2}
.card h3{font-size:13px;font-weight:700;color:var(--acc);margin-bottom:8px;display:flex;align-items:center;gap:6px}
.card h3 .ico{width:16px;height:16px;border-radius:4px;display:inline-flex;align-items:center;justify-content:center;font-size:10px}
.card p.d{font-size:11px;color:var(--dim);margin-bottom:10px;line-height:1.5}

/* ── form ── */
input,select,textarea{width:100%;background:var(--s1);border:1px solid var(--bdr);color:var(--text);border-radius:8px;padding:9px 10px;margin-bottom:6px;font-size:12px;font-family:inherit;outline:none;transition:border .2s}
input:focus,select:focus,textarea:focus{border-color:var(--blue)}
textarea{min-height:100px;font-family:"Cascadia Code",Consolas,monospace;resize:vertical}
label.sm{display:block;font-size:11px;color:var(--dim);margin:2px 0 4px}
.r2{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.r3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px}

/* ── buttons ── */
.b{display:inline-flex;align-items:center;gap:4px;background:var(--s3);border:1px solid var(--bdr);border-radius:8px;padding:8px 14px;color:var(--text);cursor:pointer;font-size:12px;font-weight:500;margin:0 4px 6px 0;transition:all .15s}
.b:hover{filter:brightness(1.12);transform:translateY(-1px)}
.b.p{background:linear-gradient(135deg,#1a5e3f,#187a50);border-color:#2a8a60;color:#fff}
.b.w{background:#4a3c1e;border-color:#6e5a2a}
.b.danger{background:#4a1e1e;border-color:#7a2e2e}

/* ── output ── */
.out{white-space:pre-wrap;word-break:break-word;max-height:280px;overflow:auto;border:1px solid var(--bdr);background:var(--bg);color:var(--dim);border-radius:8px;padding:10px;font-size:11px;font-family:"Cascadia Code",Consolas,monospace;margin-top:6px}

.hid{display:none}

/* ── status dot ── */
.dot{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:4px}
.dot.g{background:var(--acc)}.dot.y{background:var(--warn)}.dot.r{background:var(--err)}

/* ── mobile ── */
@media(max-width:768px){
  .hdr{padding:8px 12px;gap:6px}
  .hdr .logo{font-size:13px}
  .cmd-bar input{font-size:13px;padding:10px 12px}
  .cmd-bar button{padding:0 14px;font-size:12px}
  .sugg-row{padding:4px 12px 8px}
  .nav{padding:6px 10px;gap:2px}
  .nav button{padding:7px 10px;font-size:11px}
  .panel{padding:10px 10px}
  .g2{grid-template-columns:1fr}
  .card.w2{grid-column:span 1}
  .r2,.r3{grid-template-columns:1fr}
  .b{width:100%;justify-content:center;margin-right:0}
  .out{max-height:200px}
  textarea{min-height:120px}
}
</style>
</head>
<body>

<div class="hdr">
  <div class="logo"><span>TITAN</span> Dev Hub</div>
  <div class="spacer"></div>
  <span class="pill">Dual AI</span>
  <span class="pill">GPU Training</span>
  <span id="health" class="pill">...</span>
</div>

<div class="cmd-wrap">
  <div class="cmd-bar">
    <input id="smartCmd" placeholder="Tell me what you want to do... (e.g. scan my system, train a model, fix a bug)" autocomplete="off"/>
    <button onclick="runSmartCommand()">Go</button>
  </div>
  <div class="cmd-hint">Just type in plain English. No coding knowledge needed.</div>
</div>
<div class="sugg-row" id="suggRow"></div>

<div class="nav">
  <button class="on" onclick="tab('pCmd',this)">Command Center</button>
  <button onclick="tab('pAi',this)">AI Chat</button>
  <button onclick="tab('pTrain',this)">GPU Training</button>
  <button onclick="tab('pScrape',this)">Web Scraper</button>
  <button onclick="tab('pSys',this)">System</button>
  <button onclick="tab('pApi',this)">API Connectors</button>
</div>

<!-- ═══ COMMAND CENTER ═══ -->
<div id="pCmd" class="panel on">
 <div class="g2">
  <div class="card">
   <h3>Quick Actions</h3>
   <p class="d">One-click actions for common tasks. Results appear in the output below.</p>
   <div class="r2">
    <button class="b p" onclick="quickAction('scan')">Full System Scan</button>
    <button class="b p" onclick="quickAction('git')">Git Status</button>
   </div>
   <div class="r2">
    <button class="b" onclick="quickAction('vps')">VPS Status</button>
    <button class="b" onclick="quickAction('upgrade')">Upgrade Check</button>
   </div>
   <div class="r2">
    <button class="b" onclick="quickAction('gpu')">GPU Instances</button>
    <button class="b" onclick="quickAction('providers')">AI Providers</button>
   </div>
   <div id="quickOut" class="out">Ready. Use the smart bar above or click a quick action.</div>
  </div>
  <div class="card">
   <h3>Pipeline Tasks</h3>
   <p class="d">Multi-step AI pipelines with auto-retry, checkpoints, and chain-of-thought reasoning.</p>
   <input id="taskTitle" placeholder="Task title (e.g. Audit and fix titan_api.py)"/>
   <select id="taskType">
    <option value="scan_full_stack">Full Stack Scan</option>
    <option value="upgrade_readiness">Upgrade Readiness</option>
    <option value="agentic_code_fix">AI Code Fix</option>
    <option value="agentic_research">AI Research</option>
    <option value="research">Quick Research</option>
    <option value="hostinger_vps_inventory">VPS Inventory</option>
    <option value="git_status">Git Status</option>
   </select>
   <textarea id="taskPayload" placeholder='Optional JSON: {"query":"...", "path":"core/module.py"}'></textarea>
   <div class="r2">
    <button class="b p" onclick="createAndRunTask()">Create + Run</button>
    <button class="b" onclick="reloadTasks()">Refresh</button>
   </div>
   <div id="tasksOut" class="out">No tasks yet.</div>
  </div>
  <div class="card w2">
   <h3>Pipeline Monitor</h3>
   <button class="b" onclick="reloadPipelines()">Refresh</button>
   <div id="pipeOut" class="out">No pipelines.</div>
  </div>
 </div>
</div>

<!-- ═══ AI CHAT ═══ -->
<div id="pAi" class="panel">
 <div class="g2">
  <div class="card w2">
   <h3>Dual Provider AI Chat</h3>
   <p class="d">Use single provider or ensemble mode (Windsurf + Copilot simultaneously, then synthesize the best answer).</p>
   <div class="r2">
    <div>
     <label class="sm">Mode</label>
     <select id="aiMode" onchange="togEns()">
      <option value="single">Single Provider</option>
      <option value="ensemble">Ensemble (Windsurf + Copilot)</option>
     </select>
    </div>
    <div>
     <label class="sm">Reasoning style</label>
     <input id="reasoningHint" placeholder="e.g. step-by-step, concise, code-focused"/>
    </div>
   </div>
   <div id="singleFields">
    <div class="r3">
     <div><label class="sm">Provider</label>
      <select id="singleProvider">
       <option value="ollama">Ollama (local)</option>
       <option value="windsurf">Windsurf</option>
       <option value="copilot">GitHub Copilot</option>
       <option value="openai_compatible">OpenAI Compatible</option>
      </select>
     </div>
     <div><label class="sm">Model override</label><input id="singleModel" placeholder="optional"/></div>
     <div><label class="sm">API key</label><input id="singleApiKey" type="password" placeholder="optional for Ollama"/></div>
    </div>
   </div>
   <div id="ensFields" class="hid">
    <div class="r2">
     <div>
      <label class="sm"><input id="ensWind" type="checkbox" checked/> Windsurf</label>
      <input id="ensWindModel" placeholder="Model"/>
      <input id="ensWindKey" type="password" placeholder="API key"/>
     </div>
     <div>
      <label class="sm"><input id="ensCop" type="checkbox" checked/> GitHub Copilot</label>
      <input id="ensCopModel" placeholder="Model"/>
      <input id="ensCopKey" type="password" placeholder="API key"/>
     </div>
    </div>
    <input id="ensSynth" placeholder="Synthesis model (optional)"/>
   </div>
   <textarea id="aiPrompt" placeholder="Ask anything..."></textarea>
   <textarea id="aiCtx" placeholder="Optional context..." style="min-height:60px"></textarea>
   <button class="b p" onclick="runAi()">Send to AI</button>
   <div id="aiOut" class="out">No response yet.</div>
  </div>
 </div>
</div>

<!-- ═══ GPU TRAINING ═══ -->
<div id="pTrain" class="panel">
 <div class="g2">
  <div class="card">
   <h3>Search GPU Offers</h3>
   <p class="d">Find available Vast.ai GPU instances for model training. Sorted by price.</p>
   <div class="r2">
    <div><label class="sm">GPU type</label><input id="gpuName" placeholder="e.g. RTX_4090, H100_SXM"/></div>
    <div><label class="sm">Min VRAM (GB)</label><input id="gpuRam" type="number" value="24"/></div>
   </div>
   <div class="r2">
    <div><label class="sm">Num GPUs</label><input id="gpuNum" type="number" value="1" min="1" max="8"/></div>
    <div><label class="sm">Max results</label><input id="gpuLimit" type="number" value="8" min="1" max="25"/></div>
   </div>
   <button class="b p" onclick="searchGpus()">Search Offers</button>
   <div id="gpuSearchOut" class="out">No search yet.</div>
  </div>
  <div class="card">
   <h3>My Instances</h3>
   <p class="d">View, manage, and monitor your rented GPU instances.</p>
   <button class="b" onclick="listInstances()">Refresh Instances</button>
   <div id="gpuInstOut" class="out">No instances loaded.</div>
   <h3 style="margin-top:12px">Rent New Instance</h3>
   <div class="r2">
    <div><label class="sm">Offer ID</label><input id="rentOffer" placeholder="From search results"/></div>
    <div><label class="sm">Disk (GB)</label><input id="rentDisk" type="number" value="40"/></div>
   </div>
   <input id="rentImage" placeholder="Docker image (default: pytorch/pytorch:2.2.0-cuda12.1-cudnn8-devel)"/>
   <div class="r2">
    <button class="b p" onclick="rentInstance()">Rent Instance</button>
    <button class="b danger" onclick="destroyInstancePrompt()">Destroy Instance</button>
   </div>
  </div>
  <div class="card w2">
   <h3>Start Training Job</h3>
   <p class="d">Launch fine-tuning on a rented GPU instance. Supports full fine-tune and LoRA.</p>
   <div class="r3">
    <div><label class="sm">Instance ID</label><input id="trainInst" placeholder="Instance ID"/></div>
    <div><label class="sm">Model name</label><input id="trainName" value="titan-custom"/></div>
    <div><label class="sm">Base model</label><input id="trainBase" value="Qwen/Qwen2.5-7B"/></div>
   </div>
   <div class="r3">
    <div><label class="sm">Epochs</label><input id="trainEpochs" type="number" value="3"/></div>
    <div><label class="sm">Batch size</label><input id="trainBatch" type="number" value="2"/></div>
    <div><label class="sm">Learning rate</label><input id="trainLR" value="2e-5"/></div>
   </div>
   <div class="r2">
    <div><label class="sm">Dataset path</label><input id="trainData" value="/workspace/data"/></div>
    <div><label class="sm"><input id="trainLora" type="checkbox"/> Use LoRA (rank 16)</label></div>
   </div>
   <button class="b p" onclick="startTraining()">Start Training</button>
   <button class="b" onclick="getLogs()">View Logs</button>
   <div id="trainOut" class="out">No training job started.</div>
  </div>
 </div>
</div>

<!-- ═══ WEB SCRAPER ═══ -->
<div id="pScrape" class="panel">
 <div class="g2">
  <div class="card">
   <h3>Operator Search</h3>
   <p class="d">Use Google Dork-style operators to find content not indexed by standard search.</p>
   <input id="scrapeQ" placeholder="Base search query"/>
   <div class="r3">
    <input id="opSite" placeholder="site:"/>
    <input id="opFile" placeholder="filetype:"/>
    <input id="opTitle" placeholder="intitle:"/>
   </div>
   <div class="r2">
    <input id="opUrl" placeholder="inurl:"/>
    <input id="opExt" placeholder="ext:"/>
   </div>
   <div class="r2">
    <input id="scrapeMax" type="number" min="1" max="25" value="8"/>
    <button class="b p" onclick="doSearch()">Search</button>
   </div>
   <div id="scrSearchOut" class="out">No search results.</div>
  </div>
  <div class="card">
   <h3>Deep Crawler</h3>
   <p class="d">Crawl from a URL, following links to discover content. For authorized use only.</p>
   <input id="crawlUrl" placeholder="https://example.com"/>
   <div class="r3">
    <div><label class="sm">Depth</label><input id="crawlD" type="number" min="0" max="4" value="1"/></div>
    <div><label class="sm">Max pages</label><input id="crawlP" type="number" min="1" max="50" value="10"/></div>
    <div><label class="sm"><input id="crawlSame" type="checkbox" checked/> Same domain</label></div>
   </div>
   <button class="b p" onclick="doCrawl()">Crawl</button>
   <button class="b w" onclick="doDiscover()">Discover (search + crawl)</button>
   <div id="scrCrawlOut" class="out">No crawl results.</div>
  </div>
 </div>
</div>

<!-- ═══ SYSTEM ═══ -->
<div id="pSys" class="panel">
 <div class="g2">
  <div class="card">
   <h3>Infrastructure + Scanning</h3>
   <button class="b" onclick="loadVps()">Hostinger VPS</button>
   <button class="b" onclick="doScan(false)">Quick Scan</button>
   <button class="b" onclick="doScan(true)">Full Scan</button>
   <label class="sm">Custom scan paths (one per line)</label>
   <textarea id="scanPaths" style="min-height:70px" placeholder="/opt/titan\n/etc\n/usr/local"></textarea>
   <div class="r2">
    <div><label class="sm">Scan depth</label><input id="scanDepth" type="number" min="1" max="20" value="8"/></div>
    <div><label class="sm">Max files</label><input id="scanMaxFiles" type="number" min="100" max="50000" value="8000"/></div>
   </div>
   <button class="b" onclick="scanCustomPaths()">Scan Custom Paths</button>
   <textarea id="resQ" placeholder="Web research query" style="min-height:60px"></textarea>
   <button class="b" onclick="doResearch()">Research</button>
   <div id="sysOut" class="out">Ready.</div>
  </div>
  <div class="card">
   <h3>Verification + AI Assignments</h3>
   <label class="sm">Verification script</label>
   <select id="verifyScript">
    <option value="/opt/titan/vps_verify_real.sh">/opt/titan/vps_verify_real.sh</option>
    <option value="/opt/titan/core/titan_master_verify.py">/opt/titan/core/titan_master_verify.py</option>
    <option value="/opt/titan/core/verify_deep_identity.py">/opt/titan/core/verify_deep_identity.py</option>
   </select>
   <button class="b" onclick="runVerification()">Run Verification</button>
   <label class="sm">Test command</label>
   <select id="testCommandKey">
    <option value="test_runner">test_runner</option>
    <option value="titan_master_verify">titan_master_verify</option>
    <option value="verify_deep_identity">verify_deep_identity</option>
   </select>
   <button class="b" onclick="runTestCommand()">Run Tests</button>
   <button class="b" onclick="loadModelAssignments()">Show AI Model Assignments</button>
   <div id="verifyOut" class="out">No verification actions yet.</div>
  </div>
  <div class="card">
   <h3>Service Control + Reboot</h3>
   <div class="r2">
    <input id="svcFilter" placeholder="Service filter (optional)"/>
    <button class="b" onclick="listServices()">List Services</button>
   </div>
   <input id="svcName" placeholder="Service name (e.g. ollama, redis-server, xray)"/>
   <div class="r2">
    <button class="b" onclick="svcAction('status')">Status</button>
    <button class="b" onclick="svcAction('restart')">Restart</button>
   </div>
   <div class="r2">
    <button class="b" onclick="svcAction('start')">Start</button>
    <button class="b" onclick="svcAction('stop')">Stop</button>
   </div>
   <label class="sm">Type REBOOT_TITAN_OS to schedule reboot (1 minute delay)</label>
   <input id="rebootConfirm" placeholder="REBOOT_TITAN_OS"/>
   <button class="b danger" onclick="requestReboot()">Schedule Reboot</button>
   <div id="svcOut" class="out">No service actions yet.</div>
  </div>
  <div class="card w2">
   <h3>Safe File Editor</h3>
   <p class="d">Edit any file with automatic backups and syntax validation.</p>
   <div class="r2">
    <input id="fPath" placeholder="File path (relative or absolute)"/>
    <div><label class="sm"><input id="fSys" type="checkbox"/> System mode</label></div>
   </div>
   <div class="r2">
    <button class="b" onclick="loadF()">Load</button>
    <button class="b p" onclick="saveF()">Save with Backup</button>
   </div>
   <textarea id="fContent" style="min-height:200px" placeholder="File content will appear here..."></textarea>
   <div id="fOut" class="out">No file loaded.</div>
  </div>
 </div>
</div>

<!-- ═══ API CONNECTORS ═══ -->
<div id="pApi" class="panel">
 <div class="card w2">
  <h3>External API Connectors &amp; Port Manager</h3>
  <p class="d">24 connectors: search engines, AI providers, self-hosted services, and infrastructure. Configure API keys, test connectivity, and scan ports.</p>
  <div class="r2" style="margin-bottom:10px">
   <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
    <input id="apiSearch" placeholder="Filter connectors..." style="width:180px" oninput="renderApiGrid()"/>
    <select id="apiCatFilter" onchange="renderApiGrid()">
     <option value="all">All Categories</option>
     <option value="search">Search</option>
     <option value="ai">AI Providers</option>
     <option value="infra">Infrastructure</option>
     <option value="storage">Storage</option>
     <option value="scraper">Scraper Tools</option>
     <option value="hosting">Hosting / Cloud</option>
     <option value="data">Data / OSINT</option>
    </select>
    <button class="b p" onclick="loadApiEnvStatus()">Refresh Status</button>
    <button class="b" onclick="testAllConnectors()">Test All</button>
    <button class="b" onclick="loadPortScan()">Port Scan</button>
    <button class="b" onclick="loadEnvEditor()">View titan.env</button>
   </div>
  </div>
  <div id="apiGrid" class="g2" style="gap:12px;margin-bottom:12px"></div>
  <h4 style="margin:10px 0 4px">Master Output</h4>
  <div id="apiMasterOut" class="out" style="min-height:120px">Click Test All, Port Scan, or View titan.env to see results here.</div>
 </div>
</div>

<script>
const DP=__DEFAULT_PROVIDER__;
function J(o){return JSON.stringify(o,null,2)}
function P(t){try{return JSON.parse(t||'{}')}catch{return{}}}
async function A(u,m='GET',b=null){
 const o={method:m,headers:{'Content-Type':'application/json'}};
 if(b!==null)o.body=JSON.stringify(b);
 try{const r=await fetch(u,o);const t=await r.text();try{return JSON.parse(t)}catch{return{ok:false,raw:t,status:r.status}}}
 catch(e){return{ok:false,error:e.message}}
}
function tab(id,btn){
 document.querySelectorAll('.panel').forEach(p=>p.classList.remove('on'));
 document.querySelectorAll('.nav button').forEach(b=>b.classList.remove('on'));
 const el=document.getElementById(id);if(el)el.classList.add('on');
 if(btn)btn.classList.add('on');
}
function togEns(){
 const m=document.getElementById('aiMode').value;
 document.getElementById('singleFields').classList.toggle('hid',m!=='single');
 document.getElementById('ensFields').classList.toggle('hid',m!=='ensemble');
}

/* ── smart command ── */
async function runSmartCommand(){
 const cmd=document.getElementById('smartCmd').value.trim();
 if(!cmd)return;
 const out=document.getElementById('quickOut');
 out.textContent='Processing: '+cmd+'...';
 tab('pCmd',document.querySelector('.nav button'));
 const route=await A('/api/smart-command','POST',{command:cmd});
 if(!route.ok){out.textContent=J(route);return}
 out.textContent=route.message+'\n';
 const action=route.action;
 if(action==='scan_full_stack'){const d=await A('/api/scan/full','POST',{system_scan:false});out.textContent+=J(d)}
 else if(action==='upgrade_readiness'){const d=await A('/api/scan/full','POST',{system_scan:true});out.textContent+=J(d)}
 else if(action==='git_status'){const d=await A('/api/git/status');out.textContent+=J(d)}
 else if(action==='hostinger_vps'){const d=await A('/api/hostinger/vps');out.textContent+=J(d)}
 else if(action==='vastai_list'){tab('pTrain',document.querySelectorAll('.nav button')[2]);listInstances()}
 else if(action==='vastai_training'){tab('pTrain',document.querySelectorAll('.nav button')[2]);out.textContent+='Switch to GPU Training tab to configure.'}
 else if(action==='scraper_discover'){tab('pScrape',document.querySelectorAll('.nav button')[3]);document.getElementById('scrapeQ').value=cmd}
 else if(action==='service_control'||action==='run_verification'||action==='reboot_system'||action==='deploy'){
  tab('pSys',document.querySelectorAll('.nav button')[4]);
  document.getElementById('sysOut').textContent='Routed command: '+cmd+'\nUse Service/Verification controls in this tab.';
 }
 else if(action==='safe_edit'){tab('pSys',document.querySelectorAll('.nav button')[4])}
 else if(action==='ai_chat'){
  tab('pAi',document.querySelectorAll('.nav button')[1]);
  document.getElementById('aiPrompt').value=cmd;
  runAi();
 }
 else if(action==='agentic_code_fix'||action==='agentic_research'){
  document.getElementById('taskTitle').value=cmd;
  document.getElementById('taskType').value=action;
  createAndRunTask();
 }
 else{const d=await A('/api/ai/chat','POST',{prompt:cmd,mode:'single',provider:DP});out.textContent+=J(d)}
}
document.getElementById('smartCmd').addEventListener('keydown',e=>{if(e.key==='Enter')runSmartCommand()});

/* ── suggestions ── */
async function loadSuggestions(){
 const d=await A('/api/smart-command/suggestions');
 const row=document.getElementById('suggRow');
 if(!d.ok||!d.suggestions)return;
 row.innerHTML='';
 for(const s of d.suggestions){
  const c=document.createElement('div');c.className='sugg-chip';c.textContent=s.prompt;
  c.onclick=()=>{document.getElementById('smartCmd').value=s.prompt;runSmartCommand()};
  row.appendChild(c);
 }
}

/* ── quick actions ── */
async function quickAction(type){
 const out=document.getElementById('quickOut');
 out.textContent='Running...';
 if(type==='scan'){out.textContent=J(await A('/api/scan/full','POST',{system_scan:false}))}
 else if(type==='git'){out.textContent=J(await A('/api/git/status'))}
 else if(type==='vps'){out.textContent=J(await A('/api/hostinger/vps'))}
 else if(type==='upgrade'){out.textContent=J(await A('/api/scan/full','POST',{system_scan:true}))}
 else if(type==='gpu'){tab('pTrain',document.querySelectorAll('.nav button')[2]);listInstances()}
 else if(type==='providers'){out.textContent=J(await A('/api/ai/providers'))}
}

/* ── AI chat ── */
async function runAi(){
 const out=document.getElementById('aiOut');out.textContent='Thinking...';
 const prompt=document.getElementById('aiPrompt').value;
 const ctx=[document.getElementById('aiCtx').value,
  document.getElementById('reasoningHint').value?'Reasoning: '+document.getElementById('reasoningHint').value:''].filter(Boolean).join('\n\n');
 const mode=document.getElementById('aiMode').value;
 if(mode==='single'){
  const d=await A('/api/ai/chat','POST',{mode:'single',provider:document.getElementById('singleProvider').value,
   model:document.getElementById('singleModel').value,api_key:document.getElementById('singleApiKey').value,prompt,context:ctx});
  out.textContent=d.ok?(d.response||J(d)):J(d);return;
 }
 const provs=[];
 if(document.getElementById('ensWind').checked)provs.push('windsurf');
 if(document.getElementById('ensCop').checked)provs.push('copilot');
 const d=await A('/api/ai/chat','POST',{mode:'ensemble',prompt,context:ctx,providers:provs,
  provider_api_keys:{windsurf:document.getElementById('ensWindKey').value,copilot:document.getElementById('ensCopKey').value},
  provider_models:{windsurf:document.getElementById('ensWindModel').value,copilot:document.getElementById('ensCopModel').value},
  synthesis_model:document.getElementById('ensSynth').value});
 if(d.ok&&d.mode==='ensemble'){
  let t='Ensemble: '+(d.providers||[]).join(', ')+' | Synthesized: '+(d.synthesized?'yes':'fallback')+'\n\n'+(d.response||'');
  if(Array.isArray(d.responses)){for(const r of d.responses)t+='\n\n['+(r.provider||'?')+'] '+(r.ok?(r.response||'').slice(0,800):(r.error||'err'))}
  out.textContent=t;return;
 }
 out.textContent=J(d);
}

/* ── tasks ── */
async function createAndRunTask(){
 const pay=P(document.getElementById('taskPayload').value);
 const c=await A('/api/tasks','POST',{title:document.getElementById('taskTitle').value||'Pipeline task',task_type:document.getElementById('taskType').value,payload:pay});
 if(!c.ok){document.getElementById('tasksOut').textContent=J(c);return}
 const r=await A('/api/tasks/'+c.task.id+'/run','POST',{background:true});
 document.getElementById('tasksOut').textContent=J(r);
 setTimeout(reloadTasks,1200);setTimeout(reloadPipelines,1200);
}
async function reloadTasks(){
 const d=await A('/api/tasks');if(!d.tasks){document.getElementById('tasksOut').textContent=J(d);return}
 document.getElementById('tasksOut').textContent=d.tasks.slice(-15).reverse().map(t=>'['+t.status+'] '+t.id+' | '+t.task_type+' | '+t.title).join('\n');
}
async function reloadPipelines(){
 const d=await A('/api/pipelines');if(!d.pipelines||!d.pipelines.length){document.getElementById('pipeOut').textContent='No pipelines.';return}
 document.getElementById('pipeOut').textContent=d.pipelines.slice(-15).reverse().map(p=>{
  const pct=p.total_steps>0?Math.round((p.current_step_index+1)/p.total_steps*100):0;
  return '['+p.status+'] '+p.pipeline_id+' | '+p.task_title+' | '+(p.current_step_index+1)+'/'+p.total_steps+' ('+pct+'%)';
 }).join('\n');
}
async function viewPipeline(id){document.getElementById('pipeOut').textContent=J(await A('/api/pipelines/'+id))}
async function resumePipeline(id){document.getElementById('pipeOut').textContent=J(await A('/api/pipelines/'+id+'/resume','POST',{background:true}));setTimeout(reloadPipelines,1500)}

/* ── GPU / Vast.ai ── */
async function searchGpus(){
 const out=document.getElementById('gpuSearchOut');out.textContent='Searching...';
 const d=await A('/api/vastai/search','POST',{gpu_name:document.getElementById('gpuName').value,
  num_gpus:Number(document.getElementById('gpuNum').value||1),
  min_ram:Number(document.getElementById('gpuRam').value||0),
  limit:Number(document.getElementById('gpuLimit').value||8)});
 if(d.ok&&d.data&&d.data.offers){
  const offers=d.data.offers.slice(0,15);
  let t='Found '+offers.length+' offers:\n\n';
  for(const o of offers)t+='ID:'+o.id+' | '+o.gpu_name+' x'+o.num_gpus+' | '+(o.gpu_ram/1024).toFixed(0)+'GB | $'+o.dph_total.toFixed(3)+'/hr | '+o.reliability.toFixed(1)+'%\n';
  out.textContent=t;
 } else out.textContent=J(d);
}
async function listInstances(){
 const out=document.getElementById('gpuInstOut');out.textContent='Loading...';
 const d=await A('/api/vastai/instances');
 if(d.ok&&d.data&&d.data.instances){
  const insts=d.data.instances;
  if(!insts.length){out.textContent='No active instances.';return}
  let t='';for(const i of insts)t+='ID:'+i.id+' | '+i.gpu_name+' | '+(i.actual_status||i.status_msg||'unknown')+' | $'+(i.dph_total||0).toFixed(3)+'/hr\n';
  out.textContent=t;
 } else out.textContent=J(d);
}
async function rentInstance(){
 const offer=document.getElementById('rentOffer').value.trim();
 if(!offer){alert('Enter an offer ID from search results');return}
 const d=await A('/api/vastai/create','POST',{offer_id:offer,disk_gb:Number(document.getElementById('rentDisk').value||40),
  image:document.getElementById('rentImage').value||undefined});
 document.getElementById('gpuInstOut').textContent=J(d);setTimeout(listInstances,3000);
}
function destroyInstancePrompt(){
 const id=prompt('Enter instance ID to destroy:');if(!id)return;
 A('/api/vastai/instances/'+id,'DELETE').then(d=>{document.getElementById('gpuInstOut').textContent=J(d);setTimeout(listInstances,2000)});
}
async function startTraining(){
 const out=document.getElementById('trainOut');out.textContent='Starting training...';
 const d=await A('/api/vastai/train','POST',{instance_id:document.getElementById('trainInst').value,
  model_name:document.getElementById('trainName').value,base_model:document.getElementById('trainBase').value,
  dataset_path:document.getElementById('trainData').value,epochs:Number(document.getElementById('trainEpochs').value||3),
  batch_size:Number(document.getElementById('trainBatch').value||2),learning_rate:parseFloat(document.getElementById('trainLR').value||'2e-5'),
  use_lora:document.getElementById('trainLora').checked,lora_rank:16});
 out.textContent=J(d);
}
async function getLogs(){
 const id=document.getElementById('trainInst').value.trim();
 if(!id){document.getElementById('trainOut').textContent='Enter instance ID first.';return}
 const d=await A('/api/vastai/instances/'+id+'/logs');
 document.getElementById('trainOut').textContent=d.ok?(d.logs||'No logs yet.'):J(d);
}

/* ── scraper ── */
function ops(){
 const f={site:document.getElementById('opSite').value,filetype:document.getElementById('opFile').value,
  intitle:document.getElementById('opTitle').value,inurl:document.getElementById('opUrl').value,ext:document.getElementById('opExt').value};
 const o={};for(const[k,v]of Object.entries(f))if(v&&v.trim())o[k]=v.trim();return o;
}
async function doSearch(){
 const out=document.getElementById('scrSearchOut');out.textContent='Searching...';
 out.textContent=J(await A('/api/scraper/search','POST',{query:document.getElementById('scrapeQ').value,operators:ops(),max_results:Number(document.getElementById('scrapeMax').value||8)}));
}
async function doCrawl(){
 const out=document.getElementById('scrCrawlOut');out.textContent='Crawling...';
 out.textContent=J(await A('/api/scraper/crawl','POST',{start_url:document.getElementById('crawlUrl').value,
  max_depth:Number(document.getElementById('crawlD').value||1),max_pages:Number(document.getElementById('crawlP').value||10),
  same_domain:document.getElementById('crawlSame').checked}));
}
async function doDiscover(){
 const out=document.getElementById('scrCrawlOut');out.textContent='Discovering...';
 out.textContent=J(await A('/api/scraper/discover','POST',{query:document.getElementById('scrapeQ').value,operators:ops(),
  max_results:Number(document.getElementById('scrapeMax').value||5),crawl_depth:Number(document.getElementById('crawlD').value||1),
  crawl_pages_per_seed:Number(document.getElementById('crawlP').value||4),same_domain:document.getElementById('crawlSame').checked}));
}

/* ── system ── */
async function doScan(s){document.getElementById('sysOut').textContent='Scanning...';document.getElementById('sysOut').textContent=J(await A('/api/scan/full','POST',{system_scan:s}))}
async function scanCustomPaths(){
 const out=document.getElementById('sysOut');
 const raw=document.getElementById('scanPaths').value||'';
 const paths=raw.split('\n').map(x=>x.trim()).filter(Boolean);
 if(!paths.length){out.textContent='Enter at least one path.';return}
 out.textContent='Scanning custom paths...';
 const d=await A('/api/scan/paths','POST',{paths,max_depth:Number(document.getElementById('scanDepth').value||8),max_files:Number(document.getElementById('scanMaxFiles').value||8000)});
 out.textContent=J(d);
}
async function loadVps(){document.getElementById('sysOut').textContent=J(await A('/api/hostinger/vps'))}
async function doResearch(){const q=document.getElementById('resQ').value;document.getElementById('sysOut').textContent=J(await A('/api/research/web','POST',{query:q,max_results:6}))}
async function runVerification(){
 const out=document.getElementById('verifyOut');
 out.textContent='Running verification...';
 const d=await A('/api/ops/verify','POST',{script_path:document.getElementById('verifyScript').value});
 out.textContent=J(d);
}
async function runTestCommand(){
 const out=document.getElementById('verifyOut');
 out.textContent='Running test command...';
 const d=await A('/api/ops/tests/run','POST',{command_key:document.getElementById('testCommandKey').value});
 out.textContent=J(d);
}
async function loadModelAssignments(){
 const out=document.getElementById('verifyOut');
 out.textContent='Loading AI model assignments...';
 const d=await A('/api/ops/ai-model-assignments');
 out.textContent=J(d);
}
async function listServices(){
 const out=document.getElementById('svcOut');
 out.textContent='Listing services...';
 const filter=encodeURIComponent(document.getElementById('svcFilter').value||'');
 const d=await A('/api/ops/services?filter='+filter);
 out.textContent=J(d);
}
async function svcAction(action){
 const out=document.getElementById('svcOut');
 const service=(document.getElementById('svcName').value||'').trim();
 if(!service){out.textContent='Enter a service name first.';return}
 out.textContent='Running '+action+' on '+service+'...';
 const d=await A('/api/ops/services/action','POST',{service,action});
 out.textContent=J(d);
}
async function requestReboot(){
 const out=document.getElementById('svcOut');
 out.textContent='Submitting reboot request...';
 const d=await A('/api/ops/reboot','POST',{confirm:document.getElementById('rebootConfirm').value||''});
 out.textContent=J(d);
}
async function loadF(){
 const p=encodeURIComponent(document.getElementById('fPath').value);
 const s=document.getElementById('fSys').checked?'&system_mode=true':'';
 const d=await A('/api/file?path='+p+s);
 if(d.ok)document.getElementById('fContent').value=d.content;
 document.getElementById('fOut').textContent=J(d);
}
async function saveF(){
 const d=await A('/api/file/save','POST',{path:document.getElementById('fPath').value,
  content:document.getElementById('fContent').value,reason:'IDE save',actor:'web-user',
  system_mode:document.getElementById('fSys').checked});
 document.getElementById('fOut').textContent=J(d);
}

/* ── api connectors ── */
const API_REGISTRY=[
 {id:'serpapi',name:'SerpAPI',desc:'Google Search API',env:'SERPAPI_KEY',url:'https://serpapi.com',test_path:'/account',port:443,category:'search'},
 {id:'serper',name:'Serper.dev',desc:'Google Search (cheap)',env:'SERPER_API_KEY',url:'https://google.serper.dev',test_path:'/search',port:443,category:'search'},
 {id:'searxng',name:'SearXNG',desc:'Self-hosted metasearch',env:'TITAN_SEARXNG_URL',url:'http://localhost:8080',test_path:'/search?q=test&format=json',port:8080,category:'search'},
 {id:'ollama',name:'Ollama',desc:'Local LLM inference',env:'',url:'http://localhost:11434',test_path:'/api/tags',port:11434,category:'ai'},
 {id:'openai',name:'OpenAI',desc:'GPT-4 / GPT-4o API',env:'OPENAI_API_KEY',url:'https://api.openai.com',test_path:'/v1/models',port:443,category:'ai'},
 {id:'anthropic',name:'Anthropic',desc:'Claude 3 / Claude Opus',env:'ANTHROPIC_API_KEY',url:'https://api.anthropic.com',test_path:'/v1/models',port:443,category:'ai'},
 {id:'windsurf',name:'Windsurf',desc:'Windsurf AI API',env:'WINDSURF_API_KEY',url:'',test_path:'/v1/models',port:443,category:'ai'},
 {id:'copilot',name:'GitHub Copilot',desc:'Copilot Chat API',env:'GITHUB_COPILOT_TOKEN',url:'https://api.githubcopilot.com',test_path:'/models',port:443,category:'ai'},
 {id:'redis',name:'Redis',desc:'In-memory cache / pub-sub',env:'',url:'redis://localhost:6379',test_path:'',port:6379,category:'infra'},
 {id:'ntfy',name:'Ntfy',desc:'Push notifications',env:'TITAN_NTFY_URL',url:'http://localhost:8084',test_path:'/v1/health',port:8084,category:'infra'},
 {id:'uptime_kuma',name:'Uptime Kuma',desc:'Service monitoring',env:'TITAN_UPTIME_KUMA_URL',url:'http://localhost:3001',test_path:'/',port:3001,category:'infra'},
 {id:'n8n',name:'n8n',desc:'Workflow automation',env:'TITAN_N8N_URL',url:'http://localhost:5678',test_path:'/healthz',port:5678,category:'infra'},
 {id:'changedetection',name:'Changedetection.io',desc:'Site change monitor',env:'TITAN_CHANGEDET_URL',url:'http://localhost:5000',test_path:'/api/v1/watch',port:5000,category:'infra'},
 {id:'grafana',name:'Grafana',desc:'Metrics dashboard',env:'',url:'http://localhost:3000',test_path:'/api/health',port:3000,category:'infra'},
 {id:'prometheus',name:'Prometheus',desc:'Metrics scraper',env:'',url:'http://localhost:9090',test_path:'/-/healthy',port:9090,category:'infra'},
 {id:'minio',name:'MinIO',desc:'S3-compatible storage',env:'MINIO_ACCESS_KEY',url:'http://localhost:9000',test_path:'/minio/health/live',port:9000,category:'storage'},
 {id:'webhook',name:'Titan Webhook Hub',desc:'Titan webhook receiver (Flask)',env:'TITAN_WEBHOOK_PORT',url:'http://localhost:9300',test_path:'/health',port:9300,category:'infra'},
 {id:'flaresolverr',name:'FlareSolverr',desc:'Cloudflare bypass proxy',env:'TITAN_FLARESOLVERR_URL',url:'http://localhost:8191',test_path:'/v1',port:8191,category:'scraper'},
 {id:'playwright',name:'Playwright',desc:'Headless browser automation',env:'',url:'http://localhost:9222',test_path:'/json',port:9222,category:'scraper'},
 {id:'hostinger',name:'Hostinger API',desc:'VPS / domain management',env:'HOSTINGER_API_TOKEN',url:'https://developers.hostinger.com',test_path:'/api/vps/v1/virtual-machines',port:443,category:'hosting'},
 {id:'vastai',name:'Vast.ai',desc:'On-demand GPU cloud',env:'VASTAI_API_KEY',url:'https://console.vast.ai',test_path:'/api/v0/instances',port:443,category:'hosting'},
 {id:'maxmind',name:'MaxMind GeoIP',desc:'Offline geo DB (GeoLite2)',env:'MAXMIND_LICENSE_KEY',url:'https://download.maxmind.com',test_path:'',port:443,category:'data'},
 {id:'wappalyzer',name:'Wappalyzer',desc:'Tech stack detector',env:'WAPPALYZER_API_KEY',url:'https://api.wappalyzer.com',test_path:'/v2/technologies',port:443,category:'data'},
];
const API_CATS=['all','search','ai','infra','storage','scraper','hosting','data'];

let apiEnvCache={};

function renderApiGrid(){
 const cat=document.getElementById('apiCatFilter').value||'all';
 const q=(document.getElementById('apiSearch').value||'').toLowerCase();
 const list=API_REGISTRY.filter(a=>(cat==='all'||a.category===cat)&&(!q||(a.name+a.desc+a.env).toLowerCase().includes(q)));
 const grid=document.getElementById('apiGrid');
 grid.innerHTML=list.map(a=>{
  const envVal=apiEnvCache[a.env]||'';
  const configured=envVal&&envVal!=='not_set';
  const statusDot=configured?'<span style="color:#22c55e">●</span>':'<span style="color:#ef4444">○</span>';
  return `<div class="card" style="min-width:220px;max-width:340px">
   <div style="display:flex;justify-content:space-between;align-items:center">
    <b>${a.name}</b>${statusDot}
   </div>
   <p class="d" style="margin:4px 0 8px">${a.desc}</p>
   <div class="sm" style="color:#64748b;margin-bottom:6px">Category: ${a.category} | Port: ${a.port}</div>
   ${a.env?`<div class="sm" style="color:#64748b">ENV: <code>${a.env}</code></div>
   <div style="display:flex;gap:4px;margin:6px 0">
    <input id="env_${a.id}" type="password" value="${envVal&&envVal!=='not_set'?'*'.repeat(12):''}" placeholder="Paste API key / URL" style="flex:1;font-size:11px"/>
    <button class="b" style="padding:4px 8px;font-size:11px" onclick="saveApiKey('${a.id}','${a.env}')">Save</button>
   </div>`:'<div class="sm" style="color:#22c55e;margin:6px 0">No API key needed</div>'}
   <div style="display:flex;gap:4px;flex-wrap:wrap">
    <button class="b" style="font-size:11px;padding:4px 8px" onclick="testConnector('${a.id}')">Test</button>
    <button class="b" style="font-size:11px;padding:4px 8px" onclick="showConnectorInfo('${a.id}')">Info</button>
    ${a.port&&a.port!==443?`<button class="b" style="font-size:11px;padding:4px 8px" onclick="checkPort('${a.id}',${a.port})">Port ${a.port}</button>`:''}
   </div>
   <div id="apiStatus_${a.id}" class="out" style="min-height:30px;margin-top:6px;font-size:11px"></div>
  </div>`;
 }).join('');
}

async function loadApiEnvStatus(){
 const keys=API_REGISTRY.map(a=>a.env).filter(Boolean);
 const d=await A('/api/connectors/env-status','POST',{keys});
 if(d.ok)apiEnvCache=d.values||{};
 renderApiGrid();
}

async function saveApiKey(connId,envKey){
 const val=document.getElementById('env_'+connId).value.trim();
 if(!val){document.getElementById('apiStatus_'+connId).textContent='Enter a value first.';return}
 const d=await A('/api/connectors/set-env','POST',{key:envKey,value:val});
 document.getElementById('apiStatus_'+connId).textContent=d.ok?'Saved to titan.env':'Error: '+d.error;
 if(d.ok){apiEnvCache[envKey]=val;document.getElementById('env_'+connId).value='*'.repeat(12);}
}

async function testConnector(connId){
 const out=document.getElementById('apiStatus_'+connId);
 out.textContent='Testing...';
 const d=await A('/api/connectors/test','POST',{connector_id:connId});
 if(d.ok){
  const r=d.result;
  out.textContent=(r.reachable?'ONLINE':'OFFLINE')+' | '+r.latency_ms+'ms'+(r.message?' | '+r.message:'');
  out.style.color=r.reachable?'#22c55e':'#ef4444';
 } else out.textContent='Error: '+d.error;
}

async function checkPort(connId,port){
 const out=document.getElementById('apiStatus_'+connId);
 out.textContent='Checking port '+port+'...';
 const d=await A('/api/connectors/port-check','POST',{port});
 out.textContent=d.ok?('Port '+port+': '+(d.open?'OPEN':'CLOSED')+' | '+d.latency_ms+'ms'):'Error: '+d.error;
 out.style.color=d.ok&&d.open?'#22c55e':'#ef4444';
}

function showConnectorInfo(connId){
 const a=API_REGISTRY.find(x=>x.id===connId);
 if(!a)return;
 const out=document.getElementById('apiStatus_'+connId);
 out.style.color='';
 out.textContent='Name: '+a.name+'\nURL: '+a.url+'\nENV: '+(a.env||'none')+'\nPort: '+a.port+'\nTest: '+a.test_path;
}

async function testAllConnectors(){
 const out=document.getElementById('apiMasterOut');
 out.textContent='Testing all connectors...\n';
 for(const a of API_REGISTRY){
  const d=await A('/api/connectors/test','POST',{connector_id:a.id});
  const r=d.ok?d.result:{reachable:false,latency_ms:0,message:d.error||'unavailable'};
  out.textContent+=(r.reachable?'[ONLINE]':'[OFFLINE]')+' '+a.name.padEnd(22)+' '+r.latency_ms+'ms'+(r.message?' '+r.message:'')+'\n';
 }
}

async function loadPortScan(){
 const out=document.getElementById('apiMasterOut');
 out.textContent='Scanning all known ports...\n';
 const ports=API_REGISTRY.filter(a=>a.port&&a.port!==443).map(a=>({name:a.name,port:a.port}));
 for(const p of ports){
  const d=await A('/api/connectors/port-check','POST',{port:p.port});
  const open=d.ok?d.open:false;
  out.textContent+=(open?'[OPEN]  ':'[CLOSED]')+' '+String(p.port).padEnd(6)+' '+p.name+'\n';
 }
}

async function loadEnvEditor(){
 const out=document.getElementById('apiMasterOut');
 out.textContent='Loading titan.env...';
 const d=await A('/api/connectors/env-list');
 if(!d.ok){out.textContent='Error: '+d.error;return}
 let txt='# TITAN Environment — '+Object.keys(d.vars).length+' vars loaded\n\n';
 for(const[k,v]of Object.entries(d.vars))txt+=k+'='+((['KEY','SECRET','TOKEN','PASSWORD','UUID'].some(s=>k.includes(s)))?'*'.repeat(Math.min(v.length,16)):v)+'\n';
 out.textContent=txt;
}

/* ── health ── */
async function refreshHealth(){
 const h=await A('/api/health');const el=document.getElementById('health');
 el.textContent=h.ok?'Online':'Offline';el.className='pill '+(h.ok?'g':'r');
}

/* ── init ── */
document.getElementById('singleProvider').value=DP||'ollama';
togEns();refreshHealth();loadSuggestions();reloadTasks();reloadPipelines();loadApiEnvStatus();
setInterval(refreshHealth,30000);
window.viewPipeline=viewPipeline;window.resumePipeline=resumePipeline;
</script>
</body>
</html>
"""
    return html.replace("__DEFAULT_PROVIDER__", safe_default_provider)


def create_app(
    titan_root: Path,
    config: Dict[str, Any],
    task_store: TaskStore,
    scanner: TitanScanner,
    editor: SafeSystemEditor,
    ai_client: AIClient,
    research_client: ResearchClient,
    hostinger_client: HostingerClient,
    scraper_client: Optional[WebScraperClient] = None,
    vastai_client: Optional[VastAIClient] = None,
    system_ops: Optional[SystemOpsManager] = None,
    pipeline_engine: Optional[AgenticPipelineEngine] = None,
    checkpoint_store: Optional[CheckpointStore] = None,
) -> Flask:
    app = Flask(__name__)
    executor = TaskExecutor(scanner, editor, research_client, hostinger_client)
    ops_manager = system_ops or SystemOpsManager(titan_root, config)

    def expected_token() -> str:
        auth_cfg = config.get("auth", {})
        if auth_cfg.get("api_token"):
            return str(auth_cfg.get("api_token"))
        env_name = auth_cfg.get("api_token_env", "TITAN_DEV_HUB_TOKEN")
        return os.environ.get(env_name, "")

    def token_required() -> bool:
        return bool(config.get("auth", {}).get("require_token", False))

    def require_token(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            if not token_required():
                return func(*args, **kwargs)
            provided = request.headers.get("X-Titan-Token", "") or request.args.get("token", "")
            expected = expected_token()
            if not expected or provided != expected:
                return jsonify({"ok": False, "error": "Unauthorized"}), 401
            return func(*args, **kwargs)

        return wrapped

    PIPELINE_TASK_TYPES = {
        "scan_full_stack", "upgrade_readiness", "agentic_code_fix",
        "agentic_research",
    }

    def run_task(task_id: str) -> Dict[str, Any]:
        task = task_store.get_task(task_id)
        if not task:
            return {"ok": False, "error": f"Task not found: {task_id}"}

        task_type = task.get("task_type", "")
        use_pipeline = bool(
            pipeline_engine
            and task_type in PIPELINE_TASK_TYPES
            and not task.get("payload", {}).get("simple_mode", False)
        )

        task_store.update_task(task_id, status="running", error="")
        try:
            if use_pipeline:
                result = pipeline_engine.run_pipeline(task, task_store)
            else:
                result = executor.run(task)
                task_store.update_task(task_id, status="completed", result=result)
                result = {"ok": True, "task_id": task_id, "result": result}
            return result
        except Exception as exc:
            LOG.error("Task %s failed: %s", task_id, traceback.format_exc())
            task_store.update_task(task_id, status="failed", error=str(exc))
            return {"ok": False, "task_id": task_id, "error": str(exc)}

    @app.get("/")
    def index() -> Response:
        provider = config.get("ai", {}).get("default_provider", "ollama")
        return Response(build_index_html(provider), mimetype="text/html")

    @app.get("/api/health")
    @require_token
    def health() -> Any:
        return jsonify(
            {
                "ok": True,
                "service": "titan-dev-hub",
                "timestamp": utc_now(),
                "titan_root": str(titan_root),
            }
        )

    @app.get("/api/config")
    @require_token
    def get_config() -> Any:
        return jsonify({"ok": True, "config": sanitize_config_for_api(config)})

    @app.get("/api/files")
    @require_token
    def list_files_route() -> Any:
        root = request.args.get("root", "apps")
        limit = int(request.args.get("limit", "400"))
        files = editor.list_files(root, limit=limit)
        return jsonify({"ok": True, "root": root, "files": files})

    @app.get("/api/file")
    @require_token
    def read_file_route() -> Any:
        path = request.args.get("path", "")
        if not path:
            return jsonify({"ok": False, "error": "path is required"}), 400
        system_mode = request.args.get("system_mode", "false").lower() == "true"
        ok, content_or_error = editor.read_file(path, system_mode=system_mode)
        if not ok:
            return jsonify({"ok": False, "error": content_or_error}), 400
        return jsonify({"ok": True, "path": path, "content": content_or_error})

    @app.post("/api/file/save")
    @require_token
    def write_file_route() -> Any:
        payload = request.get_json(silent=True) or {}
        path = str(payload.get("path", "")).strip()
        if not path:
            return jsonify({"ok": False, "error": "path is required"}), 400
        content = str(payload.get("content", ""))
        actor = str(payload.get("actor", "web-user"))
        reason = str(payload.get("reason", "manual edit"))
        system_mode = bool(payload.get("system_mode", False))

        ok, message, backup = editor.write_file(
            path,
            content,
            actor=actor,
            reason=reason,
            system_mode=system_mode,
        )
        status = 200 if ok else 400
        return jsonify({"ok": ok, "message": message, "backup": backup}), status

    @app.post("/api/scan/full")
    @require_token
    def scan_full_route() -> Any:
        payload = request.get_json(silent=True) or {}
        system_scan = bool(payload.get("system_scan", False))
        data = scanner.scan(system_scan=system_scan)
        return jsonify({"ok": True, "scan": data})

    @app.post("/api/scan/paths")
    @require_token
    def scan_paths_route() -> Any:
        payload = request.get_json(silent=True) or {}
        raw_paths = payload.get("paths", [])
        if isinstance(raw_paths, str):
            raw_paths = [raw_paths]
        if not isinstance(raw_paths, list):
            return jsonify({"ok": False, "error": "paths must be a list or string"}), 400

        requested: List[str] = []
        for item in raw_paths:
            text = str(item).strip()
            if text and text not in requested:
                requested.append(text)
        if not requested:
            return jsonify({"ok": False, "error": "At least one path is required"}), 400

        approved: List[str] = []
        denied: List[str] = []
        for raw in requested[:25]:
            candidate = Path(os.path.expanduser(raw))
            if not candidate.is_absolute():
                candidate = (titan_root / candidate).resolve()
            else:
                candidate = candidate.resolve()
            if ops_manager.is_scan_path_allowed(candidate):
                approved.append(str(candidate))
            else:
                denied.append(str(candidate))

        if not approved:
            return jsonify({"ok": False, "error": "All requested scan paths are outside allowed scan roots", "denied_paths": denied}), 403

        ops_cfg = config.get("ops", {})
        try:
            max_files = int(payload.get("max_files", ops_cfg.get("max_scan_files_per_request", 8000)))
        except Exception:
            max_files = int(ops_cfg.get("max_scan_files_per_request", 8000))
        try:
            max_depth = int(payload.get("max_depth", ops_cfg.get("scan_max_depth", 8)))
        except Exception:
            max_depth = int(ops_cfg.get("scan_max_depth", 8))

        max_files = max(100, min(max_files, 50000))
        max_depth = max(1, min(max_depth, 20))

        result = scanner.scan_paths(raw_paths=approved, max_files=max_files, max_depth=max_depth)
        result["denied_paths"] = denied
        return jsonify({"ok": True, "scan": result})

    @app.get("/api/ops/services")
    @require_token
    def list_services_route() -> Any:
        filter_text = str(request.args.get("filter", ""))
        try:
            limit = max(1, min(int(request.args.get("limit", "120")), 300))
        except Exception:
            limit = 120
        result = ops_manager.list_services(filter_text=filter_text, limit=limit)
        return jsonify(result), 200 if result.get("ok") else 400

    @app.post("/api/ops/services/action")
    @require_token
    def service_action_route() -> Any:
        payload = request.get_json(silent=True) or {}
        service_name = str(payload.get("service", ""))
        action = str(payload.get("action", "status"))
        result = ops_manager.service_action(service_name, action)
        return jsonify(result), 200 if result.get("ok") else 400

    @app.get("/api/ops/ai-model-assignments")
    @require_token
    def model_assignment_route() -> Any:
        result = ops_manager.get_model_assignments()
        return jsonify(result), 200 if result.get("ok") else 400

    @app.post("/api/ops/verify")
    @require_token
    def run_verification_route() -> Any:
        payload = request.get_json(silent=True) or {}
        script_path = str(payload.get("script_path", ""))
        args = payload.get("args", [])
        if not isinstance(args, list):
            args = []
        result = ops_manager.run_verification(script_path=script_path, args=args)
        return jsonify(result), 200 if result.get("ok") else 400

    @app.post("/api/ops/tests/run")
    @require_token
    def run_tests_route() -> Any:
        payload = request.get_json(silent=True) or {}
        command_key = str(payload.get("command_key", ""))
        args = payload.get("args", [])
        if not isinstance(args, list):
            args = []
        result = ops_manager.run_test_command(command_key=command_key, extra_args=args)
        return jsonify(result), 200 if result.get("ok") else 400

    @app.post("/api/ops/reboot")
    @require_token
    def reboot_route() -> Any:
        payload = request.get_json(silent=True) or {}
        confirm = str(payload.get("confirm", ""))
        result = ops_manager.request_reboot(confirm_text=confirm)
        return jsonify(result), 200 if result.get("ok") else 400

    @app.get("/api/tasks")
    @require_token
    def list_tasks_route() -> Any:
        return jsonify({"ok": True, "tasks": task_store.list_tasks()})

    @app.post("/api/tasks")
    @require_token
    def create_task_route() -> Any:
        payload = request.get_json(silent=True) or {}
        title = str(payload.get("title", "Untitled task"))
        task_type = str(payload.get("task_type", "scan_full_stack"))
        priority = str(payload.get("priority", "medium"))
        description = str(payload.get("description", ""))
        task_payload = payload.get("payload", {}) or {}

        task = HubTask(
            id=uuid.uuid4().hex[:12],
            title=title,
            task_type=task_type,
            priority=priority,
            description=description,
            payload=task_payload,
            agent=assign_agent(task_type, title),
        )
        created = task_store.create_task(task)
        return jsonify({"ok": True, "task": created})

    @app.post("/api/tasks/<task_id>/run")
    @require_token
    def run_task_route(task_id: str) -> Any:
        payload = request.get_json(silent=True) or {}
        background = bool(payload.get("background", False))

        if not task_store.get_task(task_id):
            return jsonify({"ok": False, "error": "Task not found"}), 404

        if background:
            thread = threading.Thread(target=run_task, args=(task_id,), daemon=True)
            thread.start()
            return jsonify({"ok": True, "task_id": task_id, "status": "scheduled"})

        result = run_task(task_id)
        status = 200 if result.get("ok") else 500
        return jsonify(result), status

    @app.get("/api/ai/providers")
    @require_token
    def ai_providers_route() -> Any:
        providers = config.get("providers", {})
        return jsonify(
            {
                "ok": True,
                "default_provider": config.get("ai", {}).get("default_provider", "ollama"),
                "parallel_defaults": config.get("ai", {}).get("parallel_providers", ["windsurf", "copilot"]),
                "reasoning_boost": bool(config.get("ai", {}).get("reasoning_boost", True)),
                "providers": list(providers.keys()),
            }
        )

    @app.post("/api/ai/chat")
    @require_token
    def ai_chat_route() -> Any:
        payload = request.get_json(silent=True) or {}
        prompt = str(payload.get("prompt", "")).strip()
        if not prompt:
            return jsonify({"ok": False, "error": "prompt is required"}), 400

        provider = str(payload.get("provider", "")).strip() or None
        context = str(payload.get("context", ""))
        api_key = str(payload.get("api_key", ""))
        model = str(payload.get("model", ""))
        mode = str(payload.get("mode", "single"))
        synthesis_model = str(payload.get("synthesis_model", ""))

        providers_payload = payload.get("providers", [])
        providers = None
        if isinstance(providers_payload, list):
            providers = [str(item).strip() for item in providers_payload if str(item).strip()]

        provider_api_keys = payload.get("provider_api_keys", {})
        if not isinstance(provider_api_keys, dict):
            provider_api_keys = {}

        provider_models = payload.get("provider_models", {})
        if not isinstance(provider_models, dict):
            provider_models = {}

        result = ai_client.chat(
            prompt=prompt,
            provider=provider,
            context=context,
            api_key=api_key,
            model=model,
            mode=mode,
            providers=providers,
            provider_api_keys=provider_api_keys,
            provider_models=provider_models,
            synthesis_model=synthesis_model,
        )
        status = 200 if result.get("ok") else 400
        return jsonify(result), status

    @app.post("/api/ai/ensemble")
    @require_token
    def ai_ensemble_route() -> Any:
        payload = request.get_json(silent=True) or {}
        prompt = str(payload.get("prompt", "")).strip()
        if not prompt:
            return jsonify({"ok": False, "error": "prompt is required"}), 400

        providers_payload = payload.get("providers", [])
        providers = [str(item).strip() for item in providers_payload if str(item).strip()] if isinstance(providers_payload, list) else None
        provider_api_keys = payload.get("provider_api_keys", {})
        provider_models = payload.get("provider_models", {})

        if not isinstance(provider_api_keys, dict):
            provider_api_keys = {}
        if not isinstance(provider_models, dict):
            provider_models = {}

        result = ai_client.ensemble_chat(
            prompt=prompt,
            providers=providers,
            context=str(payload.get("context", "")),
            provider_api_keys=provider_api_keys,
            provider_models=provider_models,
            synthesis_model=str(payload.get("synthesis_model", "")),
        )
        status = 200 if result.get("ok") else 400
        return jsonify(result), status

    @app.post("/api/research/web")
    @require_token
    def research_route() -> Any:
        payload = request.get_json(silent=True) or {}
        query = str(payload.get("query", "")).strip()
        max_results = int(payload.get("max_results", 5))
        result = research_client.search(query=query, max_results=max_results)
        status = 200 if result.get("ok") else 400
        return jsonify(result), status

    @app.post("/api/scraper/search")
    @require_token
    def scraper_search_route() -> Any:
        if not scraper_client:
            return jsonify({"ok": False, "error": "Scraper client not available"}), 503

        payload = request.get_json(silent=True) or {}
        query = str(payload.get("query", "")).strip()
        operators = payload.get("operators", {})
        if not isinstance(operators, dict):
            operators = {}
        try:
            max_results = max(1, min(int(payload.get("max_results", 8)), 25))
        except Exception:
            max_results = 8

        result = scraper_client.search(query=query, operators=operators, max_results=max_results)
        status = 200 if result.get("ok") else 400
        return jsonify(result), status

    @app.post("/api/scraper/crawl")
    @require_token
    def scraper_crawl_route() -> Any:
        if not scraper_client:
            return jsonify({"ok": False, "error": "Scraper client not available"}), 503

        payload = request.get_json(silent=True) or {}
        start_url = str(payload.get("start_url", "")).strip()
        try:
            max_depth = max(0, min(int(payload.get("max_depth", 1)), 4))
        except Exception:
            max_depth = 1
        try:
            max_pages = max(1, min(int(payload.get("max_pages", 10)), 50))
        except Exception:
            max_pages = 10
        same_domain = bool(payload.get("same_domain", True))

        result = scraper_client.crawl(
            start_url=start_url,
            max_depth=max_depth,
            max_pages=max_pages,
            same_domain=same_domain,
        )
        status = 200 if result.get("ok") else 400
        return jsonify(result), status

    @app.post("/api/scraper/discover")
    @require_token
    def scraper_discover_route() -> Any:
        if not scraper_client:
            return jsonify({"ok": False, "error": "Scraper client not available"}), 503

        payload = request.get_json(silent=True) or {}
        query = str(payload.get("query", "")).strip()
        operators = payload.get("operators", {})
        if not isinstance(operators, dict):
            operators = {}

        try:
            max_results = max(1, min(int(payload.get("max_results", 5)), 15))
        except Exception:
            max_results = 5
        try:
            crawl_depth = max(0, min(int(payload.get("crawl_depth", 1)), 3))
        except Exception:
            crawl_depth = 1
        try:
            crawl_pages_per_seed = max(1, min(int(payload.get("crawl_pages_per_seed", 4)), 20))
        except Exception:
            crawl_pages_per_seed = 4

        result = scraper_client.discover(
            query=query,
            operators=operators,
            max_results=max_results,
            crawl_depth=crawl_depth,
            crawl_pages_per_seed=crawl_pages_per_seed,
            same_domain=bool(payload.get("same_domain", True)),
        )
        status = 200 if result.get("ok") else 400
        return jsonify(result), status

    @app.get("/api/git/status")
    @require_token
    def git_status_route() -> Any:
        result = TaskExecutor(scanner, editor, research_client, hostinger_client)._git_status()
        status = 200 if result.get("ok") else 500
        return jsonify(result), status

    @app.get("/api/hostinger/vps")
    @require_token
    def hostinger_vps_route() -> Any:
        result = hostinger_client.list_vps()
        status = 200 if result.get("ok") else 400
        return jsonify(result), status

    @app.get("/api/hostinger/vps/<vm_id>")
    @require_token
    def hostinger_vm_route(vm_id: str) -> Any:
        result = hostinger_client.get_vps(vm_id)
        status = 200 if result.get("ok") else 400
        return jsonify(result), status

    @app.get("/api/hostinger/vps/<vm_id>/actions")
    @require_token
    def hostinger_actions_route(vm_id: str) -> Any:
        result = hostinger_client.get_actions(vm_id)
        status = 200 if result.get("ok") else 400
        return jsonify(result), status

    @app.get("/api/hostinger/vps/<vm_id>/metrics")
    @require_token
    def hostinger_metrics_route(vm_id: str) -> Any:
        date_from = request.args.get("date_from", "")
        date_to = request.args.get("date_to", "")
        if not date_from or not date_to:
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "date_from and date_to query params are required (ISO-8601)",
                    }
                ),
                400,
            )

        result = hostinger_client.get_metrics(vm_id, date_from=date_from, date_to=date_to)
        status = 200 if result.get("ok") else 400
        return jsonify(result), status

    @app.get("/api/pipelines")
    @require_token
    def list_pipelines_route() -> Any:
        if not checkpoint_store:
            return jsonify({"ok": False, "error": "Pipeline engine not available"}), 503
        return jsonify({"ok": True, "pipelines": checkpoint_store.list_pipelines()})

    @app.get("/api/pipelines/<pipeline_id>")
    @require_token
    def get_pipeline_route(pipeline_id: str) -> Any:
        if not checkpoint_store:
            return jsonify({"ok": False, "error": "Pipeline engine not available"}), 503
        state = checkpoint_store.load(pipeline_id)
        if not state:
            return jsonify({"ok": False, "error": "Pipeline not found"}), 404
        return jsonify({"ok": True, "pipeline": asdict(state)})

    @app.post("/api/pipelines/<pipeline_id>/resume")
    @require_token
    def resume_pipeline_route(pipeline_id: str) -> Any:
        if not pipeline_engine or not checkpoint_store:
            return jsonify({"ok": False, "error": "Pipeline engine not available"}), 503
        state = checkpoint_store.load(pipeline_id)
        if not state:
            return jsonify({"ok": False, "error": "Pipeline not found"}), 404
        task = task_store.get_task(state.task_id)
        if not task:
            return jsonify({"ok": False, "error": f"Task {state.task_id} not found"}), 404

        payload = request.get_json(silent=True) or {}
        if bool(payload.get("background", True)):
            thread = threading.Thread(
                target=pipeline_engine.resume_pipeline,
                args=(pipeline_id, task, task_store),
                daemon=True,
            )
            thread.start()
            return jsonify({"ok": True, "pipeline_id": pipeline_id, "status": "resuming"})

        result = pipeline_engine.resume_pipeline(pipeline_id, task, task_store)
        return jsonify(result), 200 if result.get("ok") else 500

    @app.post("/api/smart-command")
    @require_token
    def smart_command_route() -> Any:
        payload = request.get_json(silent=True) or {}
        user_input = str(payload.get("command", "")).strip()
        result = SmartCommandRouter.route(user_input)
        return jsonify({"ok": True, **result})

    @app.get("/api/smart-command/suggestions")
    @require_token
    def smart_suggestions_route() -> Any:
        return jsonify({"ok": True, "suggestions": SmartCommandRouter.get_suggestions()})

    @app.get("/api/vastai/instances")
    @require_token
    def vastai_instances_route() -> Any:
        if not vastai_client:
            return jsonify({"ok": False, "error": "Vast.ai client not available"}), 503
        return jsonify(vastai_client.list_instances())

    @app.get("/api/vastai/instances/<instance_id>")
    @require_token
    def vastai_instance_detail_route(instance_id: str) -> Any:
        if not vastai_client:
            return jsonify({"ok": False, "error": "Vast.ai client not available"}), 503
        return jsonify(vastai_client.get_instance(instance_id))

    @app.post("/api/vastai/search")
    @require_token
    def vastai_search_route() -> Any:
        if not vastai_client:
            return jsonify({"ok": False, "error": "Vast.ai client not available"}), 503
        payload = request.get_json(silent=True) or {}
        result = vastai_client.search_offers(
            gpu_name=str(payload.get("gpu_name", "")),
            num_gpus=int(payload.get("num_gpus", 1)),
            min_ram=float(payload.get("min_ram", 0)),
            sort=str(payload.get("sort", "dph_total")),
            limit=int(payload.get("limit", 10)),
        )
        return jsonify(result)

    @app.post("/api/vastai/create")
    @require_token
    def vastai_create_route() -> Any:
        if not vastai_client:
            return jsonify({"ok": False, "error": "Vast.ai client not available"}), 503
        payload = request.get_json(silent=True) or {}
        offer_id = str(payload.get("offer_id", ""))
        if not offer_id:
            return jsonify({"ok": False, "error": "offer_id is required"}), 400
        result = vastai_client.create_instance(
            offer_id=offer_id,
            image=str(payload.get("image", "pytorch/pytorch:2.2.0-cuda12.1-cudnn8-devel")),
            disk_gb=float(payload.get("disk_gb", 40)),
            onstart_cmd=str(payload.get("onstart_cmd", "")),
        )
        return jsonify(result)

    @app.delete("/api/vastai/instances/<instance_id>")
    @require_token
    def vastai_destroy_route(instance_id: str) -> Any:
        if not vastai_client:
            return jsonify({"ok": False, "error": "Vast.ai client not available"}), 503
        return jsonify(vastai_client.destroy_instance(instance_id))

    @app.get("/api/vastai/instances/<instance_id>/logs")
    @require_token
    def vastai_logs_route(instance_id: str) -> Any:
        if not vastai_client:
            return jsonify({"ok": False, "error": "Vast.ai client not available"}), 503
        tail = int(request.args.get("tail", "100"))
        return jsonify(vastai_client.get_logs(instance_id, tail=tail))

    @app.post("/api/vastai/train")
    @require_token
    def vastai_train_route() -> Any:
        if not vastai_client:
            return jsonify({"ok": False, "error": "Vast.ai client not available"}), 503
        payload = request.get_json(silent=True) or {}
        instance_id = str(payload.get("instance_id", ""))
        if not instance_id:
            return jsonify({"ok": False, "error": "instance_id is required"}), 400
        result = vastai_client.start_training(
            instance_id=instance_id,
            model_name=str(payload.get("model_name", "titan-custom")),
            base_model=str(payload.get("base_model", "Qwen/Qwen2.5-7B")),
            dataset_path=str(payload.get("dataset_path", "/workspace/data")),
            epochs=int(payload.get("epochs", 3)),
            batch_size=int(payload.get("batch_size", 2)),
            learning_rate=float(payload.get("learning_rate", 2e-5)),
            max_seq_length=int(payload.get("max_seq_length", 4096)),
            use_lora=bool(payload.get("use_lora", False)),
            lora_rank=int(payload.get("lora_rank", 16)),
        )
        return jsonify(result)

    # ─── API CONNECTOR ROUTES ─────────────────────────────────────────────────

    _CONNECTOR_REGISTRY: Dict[str, Dict[str, Any]] = {
        "serpapi":         {"url": "https://serpapi.com/account",            "env": "SERPAPI_KEY",           "auth_header": "Authorization", "auth_prefix": "Bearer "},
        "serper":          {"url": "https://google.serper.dev/search",       "env": "SERPER_API_KEY",        "auth_header": "X-API-KEY",     "auth_prefix": ""},
        "searxng":         {"url_env": "TITAN_SEARXNG_URL",                  "url_suffix": "/search?q=test&format=json", "env": "", "auth_header": "", "auth_prefix": ""},
        "ollama":          {"url": "http://127.0.0.1:11434/api/tags",        "env": "",                      "auth_header": "", "auth_prefix": ""},
        "openai":          {"url": "https://api.openai.com/v1/models",       "env": "OPENAI_API_KEY",        "auth_header": "Authorization", "auth_prefix": "Bearer "},
        "anthropic":       {"url": "https://api.anthropic.com/v1/models",    "env": "ANTHROPIC_API_KEY",     "auth_header": "x-api-key",     "auth_prefix": ""},
        "windsurf":        {"url_env": "WINDSURF_ENDPOINT",                  "url_suffix": "/v1/models",     "env": "WINDSURF_API_KEY",      "auth_header": "Authorization", "auth_prefix": "Bearer "},
        "copilot":         {"url": "https://api.githubcopilot.com/models",   "env": "GITHUB_COPILOT_TOKEN",  "auth_header": "Authorization", "auth_prefix": "Bearer "},
        "redis":           {"tcp": "127.0.0.1:6379",                        "env": ""},
        "ntfy":            {"url_env": "TITAN_NTFY_URL",  "url_fallback": "http://127.0.0.1:8084/v1/health", "env": "", "auth_header": "", "auth_prefix": ""},
        "uptime_kuma":     {"url_env": "TITAN_UPTIME_KUMA_URL", "url_fallback": "http://127.0.0.1:3001/",    "env": "", "auth_header": "", "auth_prefix": ""},
        "n8n":             {"url_env": "TITAN_N8N_URL", "url_fallback": "http://127.0.0.1:5678/healthz",     "env": "", "auth_header": "", "auth_prefix": ""},
        "changedetection": {"url_env": "TITAN_CHANGEDET_URL", "url_fallback": "http://127.0.0.1:5000/api/v1/watch", "env": "", "auth_header": "", "auth_prefix": ""},
        "grafana":         {"url": "http://127.0.0.1:3000/api/health",      "env": "",                      "auth_header": "", "auth_prefix": ""},
        "prometheus":      {"url": "http://127.0.0.1:9090/-/healthy",       "env": "",                      "auth_header": "", "auth_prefix": ""},
        "minio":           {"url": "http://127.0.0.1:9000/minio/health/live","env": "MINIO_ACCESS_KEY",      "auth_header": "", "auth_prefix": ""},
        "webhook":         {"url": "http://127.0.0.1:9300/health",          "env": "",                      "auth_header": "", "auth_prefix": ""},
        "flaresolverr":    {"url_env": "TITAN_FLARESOLVERR_URL", "url_fallback": "http://127.0.0.1:8191/v1", "env": "", "auth_header": "", "auth_prefix": ""},
        "playwright":      {"url": "http://127.0.0.1:9222/json",            "env": "",                      "auth_header": "", "auth_prefix": ""},
        "hostinger":       {"url": "https://developers.hostinger.com/api/vps/v1/virtual-machines", "env": "HOSTINGER_API_TOKEN", "auth_header": "Authorization", "auth_prefix": "Bearer "},
        "vastai":          {"url": "https://console.vast.ai/api/v0/instances/", "env": "VASTAI_API_KEY",     "auth_header": "Authorization", "auth_prefix": "Bearer "},
        "maxmind":         {"url": "https://geoip.maxmind.com/geoip/v2.1/city/8.8.8.8", "env": "MAXMIND_LICENSE_KEY", "auth_header": "", "auth_prefix": ""},
        "wappalyzer":      {"url": "https://api.wappalyzer.com/v2/technologies/?url=https://stripe.com", "env": "WAPPALYZER_API_KEY", "auth_header": "x-api-key", "auth_prefix": ""},
    }

    _TITAN_ENV_PATH = Path("/opt/titan/config/titan.env")

    def _read_titan_env() -> Dict[str, str]:
        """Read titan.env key=value pairs."""
        env: Dict[str, str] = {}
        if _TITAN_ENV_PATH.exists():
            for line in _TITAN_ENV_PATH.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    if line.startswith("export "):
                        line = line[7:]
                    k, _, v = line.partition("=")
                    k, v = k.strip(), v.strip().strip('"').strip("'")
                    if k:
                        env[k] = v
        return env

    def _write_env_key(key: str, value: str) -> bool:
        """Write or update a key in titan.env, creating the file if needed."""
        try:
            _TITAN_ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
            lines: List[str] = []
            if _TITAN_ENV_PATH.exists():
                lines = _TITAN_ENV_PATH.read_text(encoding="utf-8").splitlines()
            found = False
            new_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("export "):
                    stripped = stripped[7:]
                if "=" in stripped and stripped.split("=", 1)[0].strip() == key:
                    new_lines.append(f"{key}={value}")
                    found = True
                else:
                    new_lines.append(line)
            if not found:
                new_lines.append(f"{key}={value}")
            _TITAN_ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            os.environ[key] = value
            return True
        except Exception:
            return False

    @app.post("/api/connectors/env-status")
    @require_token
    def connector_env_status_route() -> Any:
        payload = request.get_json(silent=True) or {}
        keys = payload.get("keys", [])
        env = _read_titan_env()
        values: Dict[str, str] = {}
        for k in keys:
            if not k:
                continue
            v = os.environ.get(k, env.get(k, ""))
            values[k] = v if v else "not_set"
        return jsonify({"ok": True, "values": values})

    @app.post("/api/connectors/set-env")
    @require_token
    def connector_set_env_route() -> Any:
        payload = request.get_json(silent=True) or {}
        key = str(payload.get("key", "")).strip()
        value = str(payload.get("value", "")).strip()
        if not key:
            return jsonify({"ok": False, "error": "key is required"}), 400
        if not value:
            return jsonify({"ok": False, "error": "value is required"}), 400
        ok = _write_env_key(key, value)
        return jsonify({"ok": ok, "key": key, "error": None if ok else "Write failed"})

    @app.get("/api/connectors/env-list")
    @require_token
    def connector_env_list_route() -> Any:
        env = _read_titan_env()
        merged: Dict[str, str] = {}
        for k, v in os.environ.items():
            if k.startswith("TITAN_") or k in {
                "SERPAPI_KEY", "SERPER_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
                "WINDSURF_API_KEY", "GITHUB_COPILOT_TOKEN", "HOSTINGER_API_TOKEN",
                "VASTAI_API_KEY", "MAXMIND_LICENSE_KEY", "WAPPALYZER_API_KEY",
                "MINIO_ACCESS_KEY", "OPENROUTER_API_KEY",
            }:
                merged[k] = v
        for k, v in env.items():
            if k not in merged:
                merged[k] = v
        return jsonify({"ok": True, "vars": dict(sorted(merged.items()))})

    @app.post("/api/connectors/test")
    @require_token
    def connector_test_route() -> Any:
        payload = request.get_json(silent=True) or {}
        connector_id = str(payload.get("connector_id", "")).strip()
        if connector_id not in _CONNECTOR_REGISTRY:
            return jsonify({"ok": False, "error": f"Unknown connector: {connector_id}"}), 400

        cfg = _CONNECTOR_REGISTRY[connector_id]
        start = time.time()

        # TCP-only connectors (Redis)
        if "tcp" in cfg:
            import socket
            host, port_str = cfg["tcp"].rsplit(":", 1)
            port = int(port_str)
            try:
                with socket.create_connection((host, port), timeout=3):
                    latency = int((time.time() - start) * 1000)
                    return jsonify({"ok": True, "result": {"reachable": True, "latency_ms": latency, "message": f"TCP {host}:{port} open"}})
            except Exception as exc:
                return jsonify({"ok": True, "result": {"reachable": False, "latency_ms": 0, "message": str(exc)}})

        # Resolve URL
        url = cfg.get("url", "")
        if not url and "url_env" in cfg:
            base = os.environ.get(cfg["url_env"], "").strip()
            if not base:
                base = cfg.get("url_fallback", "")
            url = base.rstrip("/") + cfg.get("url_suffix", "")
        if not url:
            return jsonify({"ok": True, "result": {"reachable": False, "latency_ms": 0, "message": "No URL configured"}})

        # Build headers
        headers: Dict[str, str] = {"User-Agent": "TITAN-DevHub/4.0"}
        env_key = cfg.get("env", "")
        if env_key:
            token = os.environ.get(env_key, _read_titan_env().get(env_key, ""))
            if token and token not in ("not_set", "REPLACE_WITH"):
                auth_header = cfg.get("auth_header", "Authorization")
                auth_prefix = cfg.get("auth_prefix", "Bearer ")
                if auth_header:
                    headers[auth_header] = auth_prefix + token

        try:
            resp = requests.get(url, headers=headers, timeout=6, allow_redirects=True)
            latency = int((time.time() - start) * 1000)
            reachable = resp.status_code < 500
            return jsonify({"ok": True, "result": {"reachable": reachable, "latency_ms": latency, "message": f"HTTP {resp.status_code}"}})
        except requests.exceptions.ConnectionError:
            return jsonify({"ok": True, "result": {"reachable": False, "latency_ms": 0, "message": "Connection refused"}})
        except requests.exceptions.Timeout:
            return jsonify({"ok": True, "result": {"reachable": False, "latency_ms": 6000, "message": "Timeout"}})
        except Exception as exc:
            return jsonify({"ok": True, "result": {"reachable": False, "latency_ms": 0, "message": str(exc)[:80]}})

    @app.post("/api/connectors/port-check")
    @require_token
    def connector_port_check_route() -> Any:
        import socket
        payload = request.get_json(silent=True) or {}
        port = int(payload.get("port", 0))
        host = str(payload.get("host", "127.0.0.1"))
        if not port:
            return jsonify({"ok": False, "error": "port is required"}), 400
        start = time.time()
        try:
            with socket.create_connection((host, port), timeout=2):
                latency = int((time.time() - start) * 1000)
                return jsonify({"ok": True, "open": True, "port": port, "host": host, "latency_ms": latency})
        except (ConnectionRefusedError, OSError):
            return jsonify({"ok": True, "open": False, "port": port, "host": host, "latency_ms": 0})
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)})

    return app


def run_cli(scanner: TitanScanner, store: TaskStore, executor: TaskExecutor) -> int:
    print("TITAN Dev Hub CLI")
    print("Commands: help, scan, tasks, create, run <id>, quit")

    while True:
        try:
            command = input("devhub> ").strip()
        except EOFError:
            print()
            return 0

        if not command:
            continue
        if command in {"quit", "exit"}:
            return 0
        if command == "help":
            print("scan                 -> run quick stack scan")
            print("tasks                -> list tasks")
            print("create               -> create scan_full_stack task")
            print("run <id>             -> execute task")
            print("quit                 -> exit")
            continue

        if command == "scan":
            print(json.dumps(scanner.scan(system_scan=False), indent=2))
            continue

        if command == "tasks":
            print(json.dumps(store.list_tasks(), indent=2))
            continue

        if command == "create":
            task = HubTask(
                id=uuid.uuid4().hex[:12],
                title="CLI scan task",
                task_type="scan_full_stack",
                agent="analyst",
            )
            created = store.create_task(task)
            print("Created:", created["id"])
            continue

        if command.startswith("run "):
            task_id = command.split(" ", 1)[1].strip()
            task = store.get_task(task_id)
            if not task:
                print(f"Task not found: {task_id}")
                continue
            store.update_task(task_id, status="running")
            result = executor.run(task)
            store.update_task(task_id, status="completed", result=result)
            print(json.dumps(result, indent=2))
            continue

        print("Unknown command. Use: help")


def load_config(config_path: Path) -> Dict[str, Any]:
    if not config_path.exists():
        save_json(config_path, DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)

    user_cfg = load_json(config_path, {})
    if not isinstance(user_cfg, dict):
        return dict(DEFAULT_CONFIG)
    return deep_merge(DEFAULT_CONFIG, user_cfg)


def detect_titan_root() -> Path:
    from_env = os.environ.get("TITAN_ROOT", "").strip()
    if from_env:
        return Path(from_env).resolve()
    return Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TITAN Dev Hub - Agentic IDE")
    parser.add_argument("--host", default=None, help="Host to bind")
    parser.add_argument("--port", type=int, default=None, help="Port to bind")
    parser.add_argument("--config", default=None, help="Path to dev_hub config JSON")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--cli", action="store_true", help="Run CLI mode")
    parser.add_argument("--gui", action="store_true", help="Run web GUI mode (default)")
    parser.add_argument("--session", default="", help="Optional session identifier (compat)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    titan_root = detect_titan_root()
    config_path = Path(args.config).resolve() if args.config else titan_root / "config" / "dev_hub_config.json"
    config = load_config(config_path)

    if args.host:
        config.setdefault("service", {})["host"] = args.host
    if args.port:
        config.setdefault("service", {})["port"] = args.port
    if args.debug:
        config.setdefault("service", {})["debug"] = True

    task_store = TaskStore(titan_root / "state" / "dev_hub_tasks.json")
    scanner = TitanScanner(titan_root, config)
    editor = SafeSystemEditor(titan_root, config)
    ai_client = AIClient(config)
    research_client = ResearchClient()
    scraper_client = WebScraperClient(config)
    hostinger_client = HostingerClient(config)
    vastai_client = VastAIClient(config)
    system_ops = SystemOpsManager(titan_root, config)
    executor = TaskExecutor(scanner, editor, research_client, hostinger_client)

    checkpoint_store = CheckpointStore(titan_root / "state" / "pipelines")
    pipeline_engine = AgenticPipelineEngine(
        ai_client=ai_client,
        scanner=scanner,
        editor=editor,
        research_client=research_client,
        hostinger_client=hostinger_client,
        checkpoint_store=checkpoint_store,
        config=config,
    )

    if args.cli:
        return run_cli(scanner, task_store, executor)

    app = create_app(
        titan_root=titan_root,
        config=config,
        task_store=task_store,
        scanner=scanner,
        editor=editor,
        ai_client=ai_client,
        research_client=research_client,
        scraper_client=scraper_client,
        hostinger_client=hostinger_client,
        vastai_client=vastai_client,
        system_ops=system_ops,
        pipeline_engine=pipeline_engine,
        checkpoint_store=checkpoint_store,
    )

    host = config.get("service", {}).get("host", "0.0.0.0")
    port = int(config.get("service", {}).get("port", 8877))
    debug_mode = bool(config.get("service", {}).get("debug", False))

    LOG.info("Starting TITAN Dev Hub IDE on %s:%s (root=%s)", host, port, titan_root)
    app.run(host=host, port=port, debug=debug_mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
