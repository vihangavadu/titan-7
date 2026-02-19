# DEVELOPER UPDATE GUIDE — Safe Modifications Without Fracturing

## How to Update TITAN Without Breaking It

**Version:** 7.0.3 | **Authority:** Dva.12

---

## Table of Contents

1. [Architecture Rules](#1-architecture-rules)
2. [Module Dependency Map](#2-module-dependency-map)
3. [The Golden Rules](#3-the-golden-rules)
4. [Adding a New Target](#4-adding-a-new-target)
5. [Adding a New Antifraud Profile](#5-adding-a-new-antifraud-profile)
6. [Updating Ghost Motor Parameters](#6-updating-ghost-motor-parameters)
7. [Adding New Cerberus BINs](#7-adding-new-cerberus-bins)
8. [Adding a New Core Module](#8-adding-a-new-core-module)
9. [Updating the Browser Extension](#9-updating-the-browser-extension)
10. [Updating Kernel/eBPF Modules](#10-updating-kernelebpf-modules)
11. [Version Bumping](#11-version-bumping)
12. [Testing Checklist](#12-testing-checklist)
13. [Common Mistakes & How to Avoid Them](#13-common-mistakes--how-to-avoid-them)
14. [File Ownership Map](#14-file-ownership-map)

---

## 1. Architecture Rules

TITAN uses an **additive architecture** — new features are layered on top of existing ones without modifying the core behavior. This is the single most important principle for safe updates.

### The Layer Model

```
SAFE TO MODIFY (Top layers — no downstream dependencies)
─────────────────────────────────────────────────────────
  Layer 7: Operator guides, playbooks, documentation
  Layer 6: GUI apps (app_genesis.py, app_cerberus.py, app_kyc.py)
  Layer 5: Intelligence data (target_intelligence.py constants)

MODIFY WITH CARE (Middle layers — have both upstream and downstream deps)
─────────────────────────────────────────────────────────
  Layer 4: Integration (preflight_validator.py, handover_protocol.py)
  Layer 3: Core engines (genesis_core.py, cerberus_core.py, kyc_core.py)

DO NOT MODIFY WITHOUT FULL AUDIT (Bottom layers — everything depends on these)
─────────────────────────────────────────────────────────
  Layer 2: Ghost Motor (ghost_motor.js, ghost_motor_v6.py)
  Layer 1: Browser (Camoufox configuration)
  Layer 0: Kernel/eBPF (hardware_shield_v6.c, network_shield_v6.c)
```

### Dependency Direction

Dependencies flow **downward only**. Upper layers import from lower layers. Lower layers NEVER import from upper layers.

```
GUI Apps ──► Core Engines ──► Support Modules ──► System
   │              │                  │
   │              │                  └── proxy_manager, fingerprint_injector
   │              │
   │              └── genesis_core, cerberus_core, kyc_core
   │
   └── app_genesis, app_cerberus, app_kyc, app_unified
```

---

## 2. Module Dependency Map

### Who imports what:

| Module | Imports From | Imported By |
|--------|-------------|-------------|
| `__init__.py` | ALL modules | External consumers |
| `genesis_core.py` | stdlib only | `app_genesis.py`, `handover_protocol.py`, `preflight_validator.py` |
| `cerberus_core.py` | stdlib, aiohttp | `app_cerberus.py`, `handover_protocol.py`, `preflight_validator.py` |
| `kyc_core.py` | stdlib only | `app_kyc.py` |
| `target_intelligence.py` | stdlib only | `preflight_validator.py`, `handover_protocol.py`, `genesis_core.py` |
| `ghost_motor_v6.py` | numpy, scipy (optional), onnxruntime (optional) | `__init__.py` |
| `preflight_validator.py` | `target_intelligence`, `cerberus_core` | `app_unified.py` |
| `three_ds_strategy.py` | stdlib only | `preflight_validator.py` |
| `handover_protocol.py` | `target_intelligence` | `app_unified.py` |
| `cognitive_core.py` | aiohttp | `integration_bridge.py` |
| `integration_bridge.py` | `cognitive_core` | `app_unified.py` |
| `proxy_manager.py` | aiohttp | `preflight_validator.py` |
| `fingerprint_injector.py` | stdlib only | `genesis_core.py` |
| `referrer_warmup.py` | stdlib only | `app_unified.py` |
| `quic_proxy.py` | stdlib only | `__init__.py` |

### Critical Rule: No Circular Imports

If module A imports from module B, module B must NEVER import from module A. Violating this causes `ImportError` at startup and breaks the entire system.

---

## 3. The Golden Rules

### Rule 1: NEVER Rename Existing Functions or Classes

```python
# ❌ WRONG — breaks all callers
class CardValidator:  # was CerberusValidator
    pass

# ✅ RIGHT — add alias if you want a new name
class CerberusValidator:
    pass
CardValidator = CerberusValidator  # alias for backward compat
```

### Rule 2: NEVER Remove Existing Parameters

```python
# ❌ WRONG — breaks callers passing this arg
def forge_profile(self, config):  # removed 'target' param
    pass

# ✅ RIGHT — add new params with defaults
def forge_profile(self, config, new_feature=None):
    pass
```

### Rule 3: ALWAYS Add to `__init__.py` Exports

When you add a new class, function, or constant that should be public:

1. Add the import statement in the appropriate section
2. Add the name to `__all__`
3. Add a comment indicating which version introduced it

```python
# V6.3 New Feature
from .new_module import NewClass, new_function

__all__ = [
    # ... existing exports ...
    # V6.3 New Feature
    'NewClass', 'new_function',
]
```

### Rule 4: ALWAYS Use Additive Data Structures

```python
# ❌ WRONG — replaces existing data
TARGET_PRESETS = {
    "new_target": TargetPreset(...)
}

# ✅ RIGHT — add to existing data
TARGET_PRESETS["new_target"] = TargetPreset(...)

# ✅ ALSO RIGHT — add in the dict definition alongside existing entries
TARGET_PRESETS: Dict[str, TargetPreset] = {
    "amazon_us": TargetPreset(...),  # existing
    "new_target": TargetPreset(...), # new
}
```

### Rule 5: NEVER Modify Dataclass Field Order

```python
# ❌ WRONG — breaks positional construction
@dataclass
class ValidationResult:
    new_field: str        # inserted before existing fields
    card: CardAsset
    status: CardStatus

# ✅ RIGHT — add new fields at the END with defaults
@dataclass
class ValidationResult:
    card: CardAsset
    status: CardStatus
    # ... existing fields ...
    new_field: Optional[str] = None  # added at end with default
```

### Rule 6: Test Imports After Every Change

```bash
python3 -c "from core import *; print(__version__)"
```

If this fails, you broke something. Fix it before committing.

---

## 4. Adding a New Target

**Difficulty:** Easy | **Risk:** Low | **Files:** 1-2

### Step 1: Add Target Preset to Genesis

In `genesis_core.py`, add to the `TARGET_PRESETS` dictionary:

```python
TARGET_PRESETS["new_target_id"] = TargetPreset(
    name="new_target_id",
    category=TargetCategory.ECOMMERCE,  # or GAMING, CRYPTO, etc.
    domain="newtarget.com",
    display_name="New Target - Description",
    recommended_age_days=60,
    trust_anchors=["google.com"],
    required_cookies=["session_cookie_name"],
    browser_preference="firefox",  # or "chromium"
    notes="Any operator notes"
)
```

### Step 2: Add Target Intelligence (Optional but Recommended)

In `target_intelligence.py`, add to the `TARGET_DATABASE`:

```python
"new_target_id": {
    "name": "New Target",
    "domain": "newtarget.com",
    "fraud_engine": "forter",        # or seon, riskified, etc.
    "psp": "stripe",                 # payment processor
    "3ds_rate": 0.15,                # 0.0-1.0
    "friction": "medium",            # low, medium, high
    "playbook": "Standard checkout flow, watch for...",
}
```

### Step 3: Test

```bash
python3 -c "
from core.genesis_core import TARGET_PRESETS
print(TARGET_PRESETS['new_target_id'].display_name)
"
```

---

## 5. Adding a New Antifraud Profile

**Difficulty:** Easy | **Risk:** Low | **Files:** 1

In `target_intelligence.py`, add to `ANTIFRAUD_PROFILES`:

```python
ANTIFRAUD_PROFILES["new_system"] = AntifraudSystemProfile(
    name="New System",
    vendor="Vendor Name",
    detection_methods=["method1", "method2"],
    evasion_strategies=["strategy1", "strategy2"],
    risk_level="HIGH",  # LOW, MEDIUM, HIGH, CRITICAL
    notes="Additional context"
)
```

No other files need modification — `target_intelligence.py` is a data-only module.

---

## 6. Updating Ghost Motor Parameters

**Difficulty:** Medium | **Risk:** Medium | **Files:** 1-2

### Browser Extension (`ghost_motor.js`)

Modify the `CONFIG` object at the top of the file. All parameters are self-contained.

**Safe to change:**
- `microTremorAmplitude` (0.5-3.0 recommended)
- `microTremorFrequency` (6-12 Hz recommended)
- `overshootProbability` (0.05-0.20 recommended)
- `dwellTimeBase` and variance
- `flightTimeBase` and variance

**Do NOT change:**
- Function names (they're referenced by `initialize()`)
- Event listener types (capture, passive flags)
- The IIFE wrapper structure
- `window.__ghostMotorConfig` API surface

### Python Engine (`ghost_motor_v6.py`)

Add new evasion profiles as module-level constants:

```python
NEW_EVASION_PROFILE = {
    "param1": (min_val, max_val),
    "param2": (min_val, max_val),
}

def get_new_evasion_profile():
    """Get new evasion profile parameters"""
    return NEW_EVASION_PROFILE
```

Then export in `__init__.py`:
```python
from .ghost_motor_V7.0.3 import get_new_evasion_profile, NEW_EVASION_PROFILE
```

---

## 7. Adding New Cerberus BINs

**Difficulty:** Easy | **Risk:** Low | **Files:** 1

### Add to BIN Database

In `cerberus_core.py`, add to `CerberusValidator.BIN_DATABASE`:

```python
'123456': {'bank': 'Bank Name', 'country': 'US', 'type': 'credit', 'level': 'platinum'},
```

### Add to High-Risk BINs (if applicable)

```python
HIGH_RISK_BINS = {
    # ... existing ...
    '123456',  # New high-risk BIN - reason
}
```

### Add Country Risk (if new country)

```python
COUNTRY_RISK = {
    # ... existing ...
    'XX': 1.2,  # New country
}
```

---

## 8. Adding a New Core Module

**Difficulty:** Hard | **Risk:** High | **Files:** 2+

### Step 1: Create the Module

Create `new_module.py` in `/opt/titan/core/`:

```python
"""
TITAN V6.X SOVEREIGN - New Module Name
Description of what this module does

V6.X Updates:
- What's new
"""

# imports...

class NewModuleClass:
    """Docstring"""
    pass

def new_module_function():
    """Docstring"""
    pass
```

### Step 2: Update `__init__.py`

```python
# V6.X New Module
from .new_module import NewModuleClass, new_module_function

__all__ = [
    # ... existing ...
    # V6.X New Module
    'NewModuleClass', 'new_module_function',
]
```

### Step 3: Test Import Chain

```bash
python3 -c "from core import NewModuleClass; print('OK')"
```

### Step 4: Update Documentation

Add entry to the master documentation in the modules table.

---

## 9. Updating the Browser Extension

**Difficulty:** Medium | **Risk:** High | **Files:** 1-2

### Rules for Extension Updates

1. **NEVER change the manifest structure** — MV3 content script injection is fragile
2. **NEVER remove existing event listeners** — other code depends on them
3. **Add new features BEFORE the `initialize()` function**
4. **Wire new features INTO `initialize()`** — don't create separate init paths
5. **Test in a real browser** — extension errors are silent

### Adding a New Evasion Feature

```javascript
// ═══════════════════════════════════════════════════════════════
// NEW FEATURE NAME
// Description of what this defeats
// ═══════════════════════════════════════════════════════════════

function newFeatureFunction() {
    // implementation
}

// Then in initialize():
function initialize() {
    // ... existing listeners ...
    
    // New feature
    newFeatureFunction();
    
    // ... rest of init ...
}
```

### Version Bump

Update `manifest.json` version:
```json
{
    "version": "7.0.0"
}
```

---

## 10. Updating Kernel/eBPF Modules

**Difficulty:** Expert | **Risk:** Critical | **Files:** C source + build scripts

### ⚠️ WARNING

Kernel module changes can:
- Prevent the system from booting
- Cause kernel panics
- Break all userspace applications

### Rules

1. **Always test in a VM first** — never test kernel changes on production
2. **Keep the existing DKMS structure** — don't change build paths
3. **Maintain backward compatibility** — new Netlink commands, don't change existing ones
4. **Update the DKMS version** in `dkms.conf`

### Build & Test

```bash
# Build kernel module
cd titan/hardware_shield
make clean && make

# Test load
sudo insmod titan_hw.ko

# Verify
lsmod | grep titan_hw
dmesg | tail -20

# If it works, update DKMS
sudo dkms add .
sudo dkms build titan_hw/7.0.3
sudo dkms install titan_hw/7.0.3
```

---

## 11. Version Bumping

When releasing a new version, update these files:

| File | What to Update |
|------|---------------|
| `core/__init__.py` | `__version__ = "6.X.0"` |
| `extensions/ghost_motor/manifest.json` | `"version": "6.X.0"` |
| `README.md` | Version references, feature list |
| `docs/CHANGELOG.md` | New version entry with all changes |
| `scripts/build_iso.sh` | ISO filename version |

### Version Numbering

```
6.X.Y
│ │ └── Patch: Bug fixes, BIN updates, doc updates
│ └──── Minor: New features, new targets, new evasion profiles
└────── Major: Architecture changes, new modules, breaking changes
```

---

## 12. Testing Checklist

### After ANY Change

```bash
# 1. Import test — must pass
python3 -c "from core import *; print(f'TITAN v{__version__} - {len(__all__)} exports')"

# 2. Module-specific test
python3 -c "from core.MODULE_NAME import CLASS_NAME; print('OK')"

# 3. No syntax errors in changed files
python3 -m py_compile /opt/titan/core/CHANGED_FILE.py
```

### After Core Engine Changes

```bash
# Test Genesis
python3 -c "
from core.genesis_core import GenesisEngine, TARGET_PRESETS
engine = GenesisEngine('/tmp/test_profiles')
print(f'Targets: {len(TARGET_PRESETS)}')
print('Genesis OK')
"

# Test Cerberus
python3 -c "
from core.cerberus_core import CerberusValidator, CardAsset
card = CardAsset('4242424242424242', 12, 2025, '123')
print(f'BIN: {card.bin}, Type: {card.card_type.value}, Luhn: {card.is_valid_luhn}')
print('Cerberus OK')
"

# Test KYC
python3 -c "
from core.kyc_core import KYCController, KYCController
motions = KYCController.get_available_motions()
print(f'Motions: {len(motions)}')
print('KYC OK')
"
```

### After Extension Changes

1. Load extension in Firefox: `about:debugging` → Load Temporary Add-on
2. Open browser console (F12) → Check for errors
3. Verify `window.__ghostMotorActive === true`
4. Verify `window.__ghostMotorConfig.get()` returns valid config
5. Move mouse — verify no console errors

### Before ISO Build

```bash
# Full integration test
sudo bash scripts/build_iso.sh  # full ISO build
# Or build and test in VM
```

---

## 13. Common Mistakes & How to Avoid Them

### Mistake 1: Circular Import

**Symptom:** `ImportError: cannot import name 'X' from partially initialized module`

**Cause:** Module A imports from Module B, and Module B imports from Module A.

**Fix:** Move shared types to a separate `types.py` module, or use late imports inside functions.

### Mistake 2: Breaking `__init__.py`

**Symptom:** `from core import *` fails

**Cause:** Added import for a module that doesn't exist, or has a syntax error.

**Fix:** Always test `python3 -c "from core import *"` after editing `__init__.py`.

### Mistake 3: Changing Dataclass Field Order

**Symptom:** `TypeError: __init__() got multiple values for argument`

**Cause:** Existing code constructs dataclasses positionally.

**Fix:** Only add new fields at the END with default values.

### Mistake 4: Modifying Constants That Are Referenced Elsewhere

**Symptom:** KeyError, AttributeError, or wrong behavior

**Cause:** Renaming a key in `TARGET_PRESETS`, `ANTIFRAUD_PROFILES`, etc.

**Fix:** Never rename keys. Add new ones, deprecate old ones with comments.

### Mistake 5: Extension Breaks Silently

**Symptom:** Ghost Motor stops working but no visible error

**Cause:** JavaScript error in content script — content scripts fail silently.

**Fix:** Always test in browser with console open. Check `window.__ghostMotorActive`.

### Mistake 6: Forgetting to Export New Symbols

**Symptom:** `ImportError: cannot import name 'NewThing' from 'core'`

**Cause:** Added class/function but didn't add to `__init__.py`.

**Fix:** Always update both the import statement AND `__all__` list.

---

## 14. File Ownership Map

### Files You Can Freely Modify (Low Risk)

| File | What You Can Do |
|------|----------------|
| `target_intelligence.py` | Add targets, antifraud profiles, processor profiles |
| `docs/*.md` | Update documentation |
| `OPERATOR_GUIDE.md` | Update operator instructions |
| Any `*_GUIDE` constant | Add/update guide content |

### Files to Modify Carefully (Medium Risk)

| File | Rules |
|------|-------|
| `genesis_core.py` | Add presets/archetypes, don't change forge_profile() signature |
| `cerberus_core.py` | Add BINs/constants, don't change validate() signature |
| `ghost_motor_v6.py` | Add evasion profiles, don't change trajectory generation |
| `handover_protocol.py` | Add guides/checklists, don't change HandoverPhase enum |
| `preflight_validator.py` | Add checks, don't remove existing checks |
| `three_ds_strategy.py` | Add strategies, don't change get_3ds_strategy() return format |
| `__init__.py` | Add exports, NEVER remove existing exports |

### Files to Modify Only With Full Testing (High Risk)

| File | Why It's Risky |
|------|---------------|
| `ghost_motor.js` | Silent failures, affects all page interactions |
| `kyc_core.py` | System-level (kernel module, ffmpeg processes) |
| `cognitive_core.py` | Cloud Brain connectivity |
| `integration_bridge.py` | Legacy module compatibility |
| `proxy_manager.py` | Network connectivity |

### Files to NEVER Modify Without Expert Review (Critical Risk)

| File | Why |
|------|-----|
| `hardware_shield_v6.c` | Kernel module — can crash system |
| `network_shield_v6.c` | eBPF — can break all networking |
| `build_iso.sh` | ISO build — can produce unbootable image |
| `manifest.json` | Extension loading — wrong format = extension won't load |

---

## Quick Reference: Update Workflow

```
1. Identify what you're changing (target? BIN? evasion? module?)
2. Check the File Ownership Map above
3. Make changes following the Golden Rules
4. Run import test: python3 -c "from core import *"
5. Run module-specific test
6. Update __init__.py if needed
7. Update CHANGELOG.md
8. Update version if it's a release
9. Test in VM before deploying to production
```

---

**End of Developer Update Guide** | **TITAN V7.0 SINGULARITY**

