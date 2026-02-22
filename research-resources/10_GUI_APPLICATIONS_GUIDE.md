# GUI Applications Guide — All 6 Apps, Every Tab, Every Feature

## Overview

TITAN V7.0.3 ships with 6 PyQt6 GUI applications, all using a dark cyberpunk theme with JetBrains Mono font. Each app is launched from desktop shortcuts or command line.

---

## 1. Unified Operation Center (`app_unified.py` — 3163 lines)

**The main command center that integrates all TITAN subsystems into a single interface.**

Launch: `python3 /opt/titan/apps/app_unified.py`

### Features (24 tab sections, 109 buttons, 17 groups)

- **Profile Management**: Create, load, delete browser profiles
- **Genesis Integration**: Forge profiles with target selection, persona config, age settings
- **Cerberus Integration**: Card validation, BIN lookup, risk scoring
- **Target Selection**: Browse 50+ merchant presets with difficulty ratings
- **Proxy Configuration**: Set residential proxy with geo-targeting
- **Kill Switch Controls**: Arm/disarm with threshold configuration
- **Preflight Validation**: Run all system checks before operation
- **Transaction Monitor**: Real-time fraud score display
- **Hardware Shield Status**: Kernel module status and profile selection
- **Font/Audio/Timezone Status**: Environment hardening verification
- **Purchase History**: Configure synthetic purchase history injection
- **3DS Strategy**: View and configure 3D Secure approach
- **VPN/Network Status**: Proxy and VPN connection status
- **Handover Protocol**: Automated → Manual transition controls
- **System Logs**: Real-time log viewer for all modules

### Splash Screen
On launch, displays a branded cyberpunk splash screen for 2 seconds while modules initialize.

---

## 2. Genesis App (`app_genesis.py` — 584 lines)

**Dedicated profile forging interface with detailed configuration options.**

Launch: `python3 /opt/titan/apps/app_genesis.py`

### Main Interface (single page, 15 buttons, 7 groups)

#### Profile Configuration Group
- **Target dropdown**: Select from 50+ merchant presets (Amazon, Steam, Nike, etc.)
- **Persona name**: Full name for the identity
- **Persona email**: Email address
- **Billing address**: Street, city, state, ZIP, country
- **Phone number**: With area code matching billing ZIP

#### Profile Settings Group
- **Age slider**: 30-900 days (default: 90)
- **Browser selection**: Firefox (recommended) or Chromium
- **Hardware profile**: US Windows Desktop, US Windows Laptop, UK Windows Desktop
- **History density**: 0.5x to 3.0x multiplier
- **Archetype selection**: Student, Professional, Gamer, Parent, Elderly

#### Actions
- **Forge Profile**: Generate complete browser profile
- **Forge with Integration**: Generate with location spoofing + commerce tokens
- **Quick Forge**: Use defaults for rapid profile generation
- **View Profile**: Open profile directory in file manager

#### Status Display
- Progress bar during generation
- Profile statistics (history count, cookie count, size)
- Profile path for browser launch command

---

## 3. Cerberus App (`app_cerberus.py` — 1441 lines, 4 tabs)

**Transaction intelligence with card validation, BIN analysis, and target discovery.**

Launch: `python3 /opt/titan/apps/app_cerberus.py`

### Tab 1: Validate
- **Card number input**: With real-time Luhn validation indicator
- **Validate button**: Runs full validation pipeline
- **Results display**:
  - Card network (Visa/MC/Amex/Discover)
  - BIN data (bank, type, level, country)
  - Risk score (0-100 with color coding)
  - AVS recommendation
  - Recommended targets for this card

### Tab 2: BIN Intelligence
- **BIN search**: Enter 6-8 digit BIN prefix
- **BIN database**: Lookup bank, card type, level, country
- **Card quality grading**: A+ through F with success probability
- **Bank tier classification**: Tier 1 (Chase, Citi) through Tier 4
- **Historical decline rates**: Per-BIN range statistics
- **AVS support level**: Full, partial, or none

### Tab 3: Target Discovery
- **Merchant browser**: Scrollable list of 50+ targets
- **Category filter**: Electronics, Gaming, Fashion, Digital, Luxury
- **Difficulty filter**: Easy, Medium, Hard, Extreme
- **Per-target details**:
  - Antifraud systems used
  - 3DS likelihood percentage
  - Velocity limits
  - Guest checkout availability
  - Browser preference
  - Operator notes and tips

### Tab 4: Card Quality
- **Comprehensive scoring**: Multi-factor card quality assessment
- **OSINT verification**: Cross-reference cardholder data
- **Geo-match analysis**: Card country vs target merchant country
- **Success probability**: Estimated success rate for this card + target combination

---

## 4. KYC App (`app_kyc.py` — 1172 lines, 3 tabs)

**Identity verification bypass with virtual camera and document injection.**

Launch: `python3 /opt/titan/apps/app_kyc.py`

### Tab 1: Camera
- **Source image loader**: Browse for face photo (JPEG/PNG)
- **Image preview**: Shows loaded face image
- **Reenactment controls**:
  - Head rotation intensity slider (0.0-1.0)
  - Expression intensity slider (0.0-1.0)
  - Blink frequency slider
  - Micro-movement intensity slider
- **Motion type selector**: Neutral, Blink, Smile, Head Turn, Nod
- **Stream controls**: Start Stream, Stop Stream, Start Reenactment
- **Document mode**: Switch between selfie and document streaming
- **Camera list**: Available virtual and real cameras

### Tab 2: Documents
- **KYC Provider selector**: Jumio, Onfido, Veriff, Sumsub, Persona, Stripe Identity, Plaid IDV, Au10tix
- **Provider intelligence display**:
  - Document flow (front → back → selfie)
  - Liveness challenges required
  - Virtual camera detection capability
  - 3D depth check capability
  - Bypass difficulty rating
  - Operator notes
- **Document asset loaders**:
  - Front image (Browse button)
  - Back image (Browse button)
  - Face photo (Browse button)
- **Document type selector**: Driver's License, Passport, State ID, National ID, Residence Permit
- **Action buttons**:
  - Inject Front: Stream front document to virtual camera
  - Inject Back: Stream back document to virtual camera
  - Start Selfie Feed: Begin face reenactment
  - Create Full Session: Automated full KYC flow
- **Liveness challenge buttons** (9 challenges):
  - Hold Still, Blink, Blink Twice, Smile
  - Turn Left, Turn Right, Nod Yes
  - Look Up, Look Down
- **Document injection log**: Real-time operation log

### Tab 3: Mobile Sync
- **Waydroid status**: Android container initialization state
- **Mobile persona config**:
  - Device model: Pixel 7, Pixel 8 Pro, Galaxy S24, Galaxy A54, OnePlus 12
  - Android version: 14, 13, 12
  - Locale: en_US, en_GB, en_CA, de_DE, fr_FR
- **Target mobile apps** (checkable list):
  - Chrome Mobile, Gmail, Google Maps
  - Amazon Shopping, eBay, PayPal
  - Steam, Eneba
- **Action buttons**:
  - Initialize Waydroid
  - Sync Cookies (desktop → mobile)
  - Start Background Activity
  - Stop
- **Mobile sync log**: Real-time operation log

---

## 5. Bug Reporter App (`app_bug_reporter.py` — 1119 lines, 4 tabs)

**System diagnostics and bug reporting tool that tests all 49 core modules.**

Launch: `python3 /opt/titan/apps/app_bug_reporter.py`

### Tab 1: System Status
- Module health check for all 49 core modules
- Import test results (pass/fail per module)
- System information (OS, kernel, Python version)
- Dependency check (PyQt6, FastAPI, Camoufox, etc.)

### Tab 2: Bug Report
- Bug description input
- Severity selector (Critical, High, Medium, Low)
- Steps to reproduce
- Expected vs actual behavior
- Auto-attach system diagnostics
- Submit report

### Tab 3: Module Inspector
- Browse all core modules
- View module docstrings and classes
- Test individual module imports
- View module dependencies

### Tab 4: Logs
- Real-time log viewer
- Filter by module
- Filter by severity
- Export logs

---

## 6. Mission Control (`titan_mission_control.py`)

**Lightweight system tray application for quick access to common operations.**

Launch: `python3 /opt/titan/apps/titan_mission_control.py`

### Features
- System tray icon with status indicator
- Quick-launch menu for all apps
- Kill switch arm/disarm toggle
- Proxy status indicator
- Hardware shield status
- One-click panic button

---

## Common UI Elements

### Dark Cyberpunk Theme
All apps share a consistent dark theme:
- **Background**: `rgb(10, 14, 23)` (near-black with blue tint)
- **Text**: `rgb(200, 210, 220)` (soft white)
- **Accent colors**: Purple (`#9c27b0`), Cyan (`#00bcd4`), Orange (`#ff6b35`)
- **Buttons**: Rounded corners, gradient backgrounds, bold text
- **Font**: JetBrains Mono (monospace, developer aesthetic)

### Window Icons
Each app has a programmatically generated hex-shaped icon with a unique accent color:
- Unified: Cyan (`#00bcd4`)
- Genesis: Green (`#4caf50`)
- Cerberus: Red (`#f44336`)
- KYC: Purple (`#9c27b0`)
- Bug Reporter: Orange (`#ff9800`)

### Desktop Shortcuts
13 `.desktop` files on the XFCE desktop:
- Titan Operation Center
- Titan Genesis
- Titan Cerberus
- Titan KYC
- Titan Browser
- Titan Bug Reporter
- Edit API Keys
