# TITAN VPS Comprehensive Verification Report

- Timestamp: `2026-02-25T20-35-15Z`
- Host: `72.62.72.48`
- Remote root: `/opt/titan`
- Result: **PASS=51 WARN=16 FAIL=0**

## Folder parity (.github -> training)

| Folder | Local Files | Remote Files | Status | Note |
|---|---:|---:|---|---|
| `.github` | 5 | 5 | PASS | exact match |
| `config` | 4 | 9 | WARN | count drift (>=80% mirrored) |
| `docs` | 76 | 76 | PASS | exact match |
| `hostinger-dev` | 6 | 7 | WARN | count drift (>=80% mirrored) |
| `iso` | 159 | 191 | WARN | count drift (>=80% mirrored) |
| `modelfiles` | 4 | 6 | WARN | count drift (>=80% mirrored) |
| `plans` | 1 | 1 | PASS | exact match |
| `scripts` | 35 | 50 | WARN | count drift (>=80% mirrored) |
| `src` | 266 | 426 | WARN | count drift (>=80% mirrored) |
| `tests` | 14 | 28 | WARN | count drift (>=80% mirrored) |
| `training` | 49 | 76 | WARN | count drift (>=80% mirrored) |

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
- [OK] `/opt/titan/apps/titan_launcher.py`
- [OK] `/opt/titan/apps/app_unified.py`
- [OK] `/opt/titan/apps/app_genesis.py`
- [OK] `/opt/titan/apps/app_cerberus.py`
- [OK] `/opt/titan/scripts/setup_waydroid_android.sh`
- [OK] `/opt/titan/scripts/deploy_android_vm.sh`

## Python syntax

- Checked: `417`
- Failed: `0`

## Services

- `redis-server` (required): active=`active` enabled=`enabled`
- `ollama` (required): active=`active` enabled=`enabled`
- `xray` (required): active=`active` enabled=`enabled`
- `ntfy` (required): active=`active` enabled=`enabled`
- `titan-dev-hub` (required): active=`active` enabled=`enabled`
- `titan-api` (required): active=`active` enabled=`enabled`
- `xrdp` (required): active=`active` enabled=`enabled`
- `lightdm` (optional): active=`failed` enabled=`enabled`
- `lucid-console` (optional): active=`inactive` enabled=`enabled`
- `lucid-ebpf` (optional): active=`active` enabled=`enabled`
- `lucid-titan` (optional): active=`active` enabled=`enabled`
- `titan-dns` (optional): active=`active` enabled=`enabled`
- `titan-first-boot` (optional): active=`inactive` enabled=`enabled`
- `titan-patch-bridge` (optional): active=`active` enabled=`enabled`
- `waydroid-container` (optional): active=`active` enabled=`enabled`
- `titan-waydroid` (optional): active=`inactive` enabled=`disabled`

## Tools

- [OK] `python3` /usr/bin/python3
- [OK] `pip3` /usr/bin/pip3
- [OK] `git` /usr/bin/git
- [OK] `curl` /usr/bin/curl
- [OK] `ffmpeg` /usr/bin/ffmpeg
- [OK] `node` /usr/bin/node
- [OK] `npm` /usr/bin/npm
- [OK] `redis-cli` /usr/bin/redis-cli
- [OK] `ollama` /usr/local/bin/ollama
- [OK] `waydroid` /usr/bin/waydroid
- [OK] `xrdp` /usr/sbin/xrdp
- [OK] `Xvnc` /usr/bin/Xvnc

## Waydroid

- Installed: `True`
- Binder nodes: `/dev/binder`
- `/var/lib/waydroid/images/system.img`: `False`
- `/var/lib/waydroid/images/vendor.img`: `False`

## GUI + XRDP

- XRDP binary installed: `True`
- XRDP startwm exists: `True`
- XRDP XFCE wiring: `True`
- Desktop user present (`user`): `True`
- XRDP listener count (:3389): `1`

## API checks

- `http://127.0.0.1:5000/api/v1/health` -> `000`
- `http://127.0.0.1:5000/api/v1/modules` -> `000`
- `http://127.0.0.1:5000/api/v1/android/status` -> `000`
- `http://127.0.0.1:8877/api/health` -> `200`
