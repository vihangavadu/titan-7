# Titan OS Development Skill

## Purpose
This skill gives you full control over the Titan OS platform running on this VPS.
You can scan the codebase, run AI pipelines, control services, edit files safely,
and trigger Oh-My-OpenCode style discipline agent orchestration — all via the
Titan Dev Hub API at http://localhost:8877.

---

## Dev Hub API Reference
Base URL: `http://localhost:8877`  
All responses: `{ ok: true|false, ...data }`

### Discipline Agents (OmO-style)

| Endpoint | Method | Body | Description |
|---|---|---|---|
| `/api/agents/ultrawork` | POST | `{task, context}` | Sisyphus decomposes → parallel subtasks |
| `/api/agents/prometheus/interview` | POST | `{message, history}` | Prometheus planning interview turn |
| `/api/agents/start-work` | POST | `{plan, context}` | Execute a Prometheus plan |
| `/api/agents/single` | POST | `{agent, prompt, context}` | Invoke one agent directly |
| `/api/agents/profiles` | GET | — | List agents and their models |
| `/api/agents/sessions` | GET | — | List past work sessions |
| `/api/agents/sessions/<id>` | GET | — | Get full session detail |

### System Operations

| Endpoint | Method | Body | Description |
|---|---|---|---|
| `/api/scan/full` | POST | `{}` | Scan all Python modules for syntax errors |
| `/api/scan/paths` | POST | `{paths}` | Scan specific paths |
| `/api/ops/services` | GET | — | List systemd services |
| `/api/ops/services/action` | POST | `{service, action}` | start/stop/restart/status |
| `/api/ops/verify` | POST | `{script}` | Run verification script |
| `/api/ops/ai-model-assignments` | GET | — | Show LLM task routing |
| `/api/ops/reboot` | POST | — | Reboot (if allowed in config) |

### File Operations

| Endpoint | Method | Body/Query | Description |
|---|---|---|---|
| `/api/files` | GET | `?root=<dir>` | List files in directory |
| `/api/file` | GET | `?path=<path>` | Read a file |
| `/api/file/save` | POST | `{path, content}` | Write with backup + syntax check |

### AI Chat

| Endpoint | Method | Body | Description |
|---|---|---|---|
| `/api/ai/chat` | POST | `{prompt, provider, context, mode}` | Single or ensemble AI chat |
| `/api/ai/ensemble` | POST | `{prompt, providers, context}` | Multi-provider synthesis |
| `/api/ai/providers` | GET | — | List configured AI providers |

### Infrastructure

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Service health check |
| `/api/config` | GET | Current config (redacted) |
| `/api/git/status` | GET | Git status |
| `/api/hostinger/vps` | GET | VPS list via Hostinger API |
| `/api/tasks` | GET | List agentic tasks |
| `/api/pipelines` | GET | List pipeline executions |

---

## Discipline Agents

| Agent | Role | Model | When to use |
|---|---|---|---|
| **Sisyphus** | Orchestrator | deepseek-r1:8b | Decompose large tasks, drive to completion |
| **Prometheus** | Planner | deepseek-r1:8b | Interview-driven planning before coding |
| **Hephaestus** | Deep Worker | qwen2.5:7b | Complex implementations, codebase exploration |
| **Atlas** | Executor | mistral:7b | Specific well-defined subtasks |

---

## Titan OS Structure

```
/root/workspace/titan-7/
├── iso/config/includes.chroot/opt/titan/
│   ├── apps/
│   │   ├── titan_dev_hub.py       ← Web IDE (port 8877)
│   │   └── *.py                   ← Other app modules
│   ├── core/                      ← 115+ core modules
│   │   ├── titan_api.py           ← 59 REST endpoints
│   │   ├── integration_bridge.py  ← 69 subsystems
│   │   └── titan_session.py       ← Redis pub/sub
│   └── config/
│       ├── llm_config.json        ← AI task routing (57 tasks)
│       └── titan.env              ← Environment variables
└── src/
    ├── apps/                      ← PyQt5 desktop apps
    └── android/                   ← Android KYC console
```

---

## Key Services

| Service | Port | Description |
|---|---|---|
| titan-dev-hub | 8877 | This Web IDE |
| ollama | 11434 | Local LLM inference |
| redis-server | 6379 | Session/cache |
| xray | — | Network proxy |
| ntfy | 8084 | Push notifications |

---

## Ollama Models

| Model | Role |
|---|---|
| deepseek-r1:8b | Deep reasoning (Sisyphus, Prometheus) |
| qwen2.5:7b | Structured analysis (Hephaestus) |
| mistral:7b | Fast execution (Atlas) |
| titan-strategist | Custom fine-tuned strategist |
| titan-analyst | Custom fine-tuned analyst |
| titan-fast | Custom fine-tuned operator |

---

## Operating Instructions

1. **Editing files**: Always use `/api/file/save` — it creates backups and validates Python syntax
2. **After editing `titan_dev_hub.py`**: Run `systemctl restart titan-dev-hub`
3. **After major changes**: Run `/api/scan/full` to verify no syntax errors introduced
4. **Complex tasks**: Use `/api/agents/ultrawork` — Sisyphus will handle orchestration
5. **Planning first**: Use Prometheus interview mode when requirements are unclear
6. **Service control**: Use `/api/ops/services/action` with the service allowlist
7. **Verification**: Run `/api/ops/verify` with one of the pre-configured verification scripts

---

## Example: ultrawork via curl

```bash
curl -X POST http://localhost:8877/api/agents/ultrawork \
  -H 'Content-Type: application/json' \
  -d '{"task": "Add a rate limiter to the titan API", "context": "Titan root: /opt/titan"}'
```

## Example: Prometheus interview

```bash
# Turn 1: describe your goal
curl -X POST http://localhost:8877/api/agents/prometheus/interview \
  -H 'Content-Type: application/json' \
  -d '{"message": "I want to add Redis caching to the scan endpoint", "history": []}'

# Turn 2: answer the question (pass history back)
curl -X POST http://localhost:8877/api/agents/prometheus/interview \
  -H 'Content-Type: application/json' \
  -d '{"message": "Cache for 5 minutes, invalidate on file save", "history": [...]}'
```
