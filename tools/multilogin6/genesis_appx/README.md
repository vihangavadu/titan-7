# Genesis AppX

**Multilogin 6 + Titan OS Genesis Engine = Genesis AppX**

A rebranded, auth-free anti-detect browser combining Multilogin 6's Electron shell and custom browser engines (Mimic/Stealthfox) with Titan OS Genesis Engine's AI-powered, forensic-grade profile generation.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Genesis AppX                          │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────────────┐    ┌──────────────────────────┐│
│  │  ML6 Electron Shell  │    │  Genesis Bridge API      ││
│  │  (Patched app.asar)  │◄──►│  (Flask on :36200)       ││
│  │                      │    │                          ││
│  │  - Mimic browser     │    │  - Profile CRUD          ││
│  │  - Stealthfox        │    │  - Fingerprint gen       ││
│  │  - Angular UI        │    │  - Genesis forge engine  ││
│  │  - Auth bypassed     │    │  - AI intelligence       ││
│  │  - Rebranded green   │    │  - Target presets        ││
│  └─────────────────────┘    │  - Archetype system      ││
│                              │  - BIN validation        ││
│                              │  - OS consistency        ││
│                              └──────────────────────────┘│
│                                        │                 │
│                              ┌─────────▼────────────┐    │
│                              │  Titan OS Core        │    │
│                              │  genesis_core.py      │    │
│                              │  ai_intelligence.py   │    │
│                              │  fingerprint_injector  │    │
│                              │  canvas_noise.py      │    │
│                              │  target_intelligence   │    │
│                              └──────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

## What Was Modified

### From Multilogin 6 (kept):
- Electron desktop shell (window management, process lifecycle)
- Mimic browser engine (Chromium fork with kernel-level fingerprint spoofing)
- Stealthfox browser engine (Firefox fork)
- Mimic Mobile engine
- Angular UI framework (profile management, fingerprint config)
- Express.js local server
- Zombie process killer / watchdog
- Chrome sandbox (SUID)

### From Multilogin 6 (removed):
- Cloud authentication (login/signup/password reset)
- Subscription plan checks
- Cloud profile sync (replaced with local storage)
- Version update checks to multilogin.com
- All cloud API dependencies
- Registration blocks

### From Titan OS Genesis (added):
- Forensic-grade profile forging (aged cookies, history, bookmarks, favicons, downloads, autofill)
- 14 target presets (Amazon, Steam, Coinbase, Eneba, G2A, etc.)
- 5 behavioral archetypes (Student, Professional, Retiree, Gamer, Shopper)
- 10 hardware fingerprint profiles (Windows/Mac/Linux, multiple tiers)
- BIN-aware pre-validation (card level ↔ hardware coherence)
- OS consistency validator (UA ↔ platform ↔ GPU ↔ timezone cross-checks)
- AI intelligence engine (21 functions via Ollama models)
- Profile quality scoring (Go/No-Go assessment)
- Handover protocol documents for human operators
- Multi-PSP trust tokens (Stripe, PayPal, Adyen, Braintree, Shopify, Klarna)

## Files

```
genesis_appx/
├── genesis_bridge_api.py      # Flask REST API bridging ML6 ↔ Genesis engine
├── patch_selective.py         # ASAR patcher (extracts + patches key files)
├── patch_ml6_asar.py          # Full ASAR patcher (extract all + patch + repack)
├── launch_genesis_appx.sh     # Launcher (starts bridge + Electron)
├── deploy_genesis_appx.sh     # Full deployment script for Linux VPS
├── genesis-appx.desktop       # Linux desktop shortcut
├── patch_overlay/             # Patched files ready for deployment
│   ├── package.json
│   ├── dist/bundle.js
│   ├── dist/express-server.js
│   ├── dist/preload.js
│   └── renderer/multilogin/{en,ru,zh-Hans}/
│       ├── index.html         # Auth bypass + bridge connector injected
│       ├── splash.html        # Rebranded splash screen
│       └── main.*.js          # Auth guard bypassed, login→profile redirect
└── README.md
```

## Deployment (Linux VPS)

### Quick Deploy
```bash
# Upload the multilogin .deb and genesis_appx folder to VPS, then:
cd /path/to/genesis_appx
bash deploy_genesis_appx.sh /path/to/multilogin.deb
```

### Manual Deploy
```bash
# 1. Install ML6 base
dpkg -i multilogin-6.5-0-linux_x86_64.deb

# 2. Backup original ASAR
cp /opt/Multilogin/resources/app.asar /opt/Multilogin/resources/app.asar.original

# 3. Run patcher (generates patched ASAR)
python3 patch_ml6_asar.py --source /opt/Multilogin/resources/app.asar.original --output /opt/genesis-appx/

# 4. Install patched ASAR
cp /opt/genesis-appx/app.asar /opt/Multilogin/resources/app.asar

# 5. Deploy bridge API
cp genesis_bridge_api.py /opt/genesis-appx/
cp launch_genesis_appx.sh /opt/genesis-appx/
chmod +x /opt/genesis-appx/launch_genesis_appx.sh

# 6. Launch
/opt/genesis-appx/launch_genesis_appx.sh
```

## Bridge API Endpoints

### ML6-Compatible (transparently redirected)
| Endpoint | Purpose |
|----------|---------|
| `GET /bridge/apiToken` | Returns local token (auth bypassed) |
| `GET /bridge/os` | OS detection |
| `GET /bridge/availableSystemFonts` | Font list for fingerprinting |
| `GET /bridge/browserTypeVersions` | Mimic/Stealthfox versions |
| `GET /rest/v1/plans/current` | Always returns unlimited plan |
| `GET /rest/ui/v1/global-config` | Screen resolutions, timezones, etc. |
| `POST /rest/ui/v1/group/profile/list` | List all profiles |

### Genesis-Enhanced
| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/genesis/forge` | Forge a full aged profile with Genesis engine |
| `GET /api/v1/genesis/targets` | List 14 target presets |
| `GET /api/v1/genesis/archetypes` | List 5 behavioral archetypes |
| `POST /api/v1/genesis/validate` | Pre-forge BIN/billing validation |
| `POST /api/v1/genesis/os-validate` | OS consistency check |
| `GET /api/v1/genesis/ai/status` | AI engine availability |
| `POST /api/v1/genesis/fingerprint/generate` | Generate hardware fingerprint |
| `GET /api/v1/genesis/hardware-profiles` | List 10 hardware profiles |

### Profile Management
| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/profile/create` | Create profile |
| `GET /api/v1/profile/<sid>` | Get profile details |
| `PUT /api/v1/profile/<sid>` | Update profile |
| `DELETE /api/v1/profile/<sid>` | Delete profile |
| `POST /api/v1/profile/<sid>/clone` | Clone profile |
| `POST /api/v1/profile/<sid>/cookies` | Import cookies |

## Patches Applied

### bundle.js (Main Process)
- Rebranded: "Multilogin" → "Genesis AppX" (31 occurrences)
- Config paths: `.multiloginapp.com` → `.genesis-appx.local`
- Splash title forced to "Genesis AppX"
- Watchdog ping interval relaxed (10s → 30s)

### index.html (All Locales)
- Title: "MlaAppUi" → "Genesis AppX"
- Injected: fetch/XHR interceptor redirecting all API calls to Genesis Bridge (port 36200)
- CSS: Primary color scheme changed from ML6 blue (#174bc9) to Genesis emerald (#10b981)

### main.js (Angular App, All Locales)
- Auth guard `canActivate()` forced to return `true`
- `isLoggedIn()` short-circuited to always resolve `true`
- Signup prompts hidden (`showSignUp` forced `false`)
- Default route: `/login` → `/profile` (skip login page entirely)
- All "Multilogin" strings → "Genesis AppX"

### splash.html (All Locales)
- Title rebranded
- "Genesis AppX" overlay text added to splash screen

## Requirements
- Linux x86_64 (Debian 12 / Ubuntu recommended)
- Python 3.8+ with Flask
- Titan OS core modules (for Genesis engine features)
- Display server (X11/Wayland) or XRDP for GUI
