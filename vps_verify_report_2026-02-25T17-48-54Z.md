# TITAN VPS Comprehensive Verification Report

- Timestamp: `2026-02-25T17-48-54Z`
- Host: `72.62.72.48`
- Remote root: `/opt/titan`
- Result: **PASS=27 WARN=8 FAIL=12**

## Folder parity (.github -> training)

| Folder | Local Files | Remote Files | Status | Note |
|---|---:|---:|---|---|
| `.github` | 5 | -1 | FAIL | remote missing |
| `config` | 4 | 5 | WARN | count drift (>=80% mirrored) |
| `docs` | 76 | 76 | PASS | exact match |
| `hostinger-dev` | 6 | -1 | FAIL | remote missing |
| `iso` | 159 | -1 | FAIL | remote missing |
| `modelfiles` | 4 | 4 | PASS | exact match |
| `plans` | 1 | -1 | FAIL | remote missing |
| `scripts` | 30 | 29 | WARN | count drift (>=80% mirrored) |
| `src` | 266 | 268 | WARN | count drift (>=80% mirrored) |
| `tests` | 14 | 16 | WARN | count drift (>=80% mirrored) |
| `training` | 49 | 49 | PASS | exact match |

## Critical files

- [OK] `/opt/titan/core/titan_api.py`
- [OK] `/opt/titan/core/integration_bridge.py`
- [OK] `/opt/titan/core/titan_session.py`
- [OK] `/opt/titan/core/kyc_core.py`
- [OK] `/opt/titan/core/kyc_enhanced.py`
- [OK] `/opt/titan/core/kyc_voice_engine.py`
- [OK] `/opt/titan/core/waydroid_sync.py`
- [OK] `/opt/titan/core/cockpit_daemon.py`
- [OK] `/opt/titan/apps/titan_dev_hub.py`
- [OK] `/opt/titan/apps/app_kyc.py`
- [OK] `/opt/titan/scripts/setup_waydroid_android.sh`
- [OK] `/opt/titan/scripts/deploy_android_vm.sh`

## Python syntax

- Checked: `0`
- Failed: `1`

## Services

- `redis-server`: active=`active` enabled=`enabled`
- `ollama`: active=`active` enabled=`enabled`
- `xray`: active=`active` enabled=`enabled`
- `ntfy`: active=`active` enabled=`enabled`
- `titan-dev-hub`: active=`active` enabled=`enabled`
- `titan-api`: active=`inactive` enabled=`unknown`
- `waydroid-container`: active=`inactive` enabled=`unknown`

## Tools

- [OK] `python3` /usr/bin/python3
- [OK] `pip3` /usr/bin/pip3
- [OK] `git` /usr/bin/git
- [OK] `curl` /usr/bin/curl
- [MISSING] `ffmpeg` 
- [MISSING] `node` 
- [MISSING] `npm` 
- [OK] `redis-cli` /usr/bin/redis-cli
- [OK] `ollama` /usr/local/bin/ollama
- [MISSING] `waydroid` 

## Waydroid

- Installed: `False`
- Binder nodes: ``
- `/var/lib/waydroid/images/system.img`: `False`
- `/var/lib/waydroid/images/vendor.img`: `False`

## API checks

- `http://127.0.0.1:5000/api/v1/health` -> `000`
- `http://127.0.0.1:5000/api/v1/modules` -> `000`
- `http://127.0.0.1:5000/api/v1/android/status` -> `000`
