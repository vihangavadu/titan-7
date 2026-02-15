# BROWSER & EXTENSION — Complete Technical Analysis

## Camoufox Anti-Detect Browser + Ghost Motor Human Augmentation

**Version:** 7.0.2 | **Authority:** Dva.12

---

## Table of Contents

1. [Overview](#1-overview)
2. [Camoufox Browser](#2-camoufox-browser)
3. [Ghost Motor Extension — Architecture](#3-ghost-motor-extension--architecture)
4. [Ghost Motor — Core Augmentation (V6.0)](#4-ghost-motor--core-augmentation-v60)
5. [Ghost Motor — BioCatch Evasion (V7.0)](#5-ghost-motor--biocatch-evasion-v70)
6. [Ghost Motor — ThreatMetrix Session Continuity (V7.0)](#6-ghost-motor--threatmetrix-session-continuity-v70)
7. [Ghost Motor V6 Python Engine (DMTG)](#7-ghost-motor-v6-python-engine-dmtg)
8. [V7.0 Evasion Profiles](#8-v70-evasion-profiles)
9. [Runtime Configuration API](#9-runtime-configuration-api)
10. [How They Work Together](#10-how-they-work-together)

---

## 1. Overview

TITAN's browser layer consists of two components:

1. **Camoufox** — A hardened Firefox fork that defeats browser fingerprinting at the application level
2. **Ghost Motor** — A browser extension (JS) + Python engine that defeats behavioral biometrics

Together, they ensure that the browser appears to be a normal Firefox instance operated by a real human, defeating both static fingerprinting and dynamic behavioral analysis.

---

## 2. Camoufox Browser

### 2.1 What Is Camoufox

Camoufox is an open-source anti-detect browser based on Firefox. TITAN uses it as the primary browser because:

- Firefox has a smaller fingerprint surface than Chromium
- Camoufox patches Firefox internals to prevent fingerprint leaks
- It supports profile loading from Genesis Engine output
- It integrates with the Ghost Motor extension

### 2.2 Installation

```bash
pip install camoufox[geoip]
```

### 2.3 Anti-Fingerprint Protections

| Protection | What It Does | What It Defeats |
|-----------|-------------|-----------------|
| **WebDriver Flag Removal** | Removes `navigator.webdriver = true` | Selenium/Puppeteer detection |
| **Canvas Fingerprint Noise** | Adds deterministic noise to canvas reads | Canvas fingerprinting (FingerprintJS) |
| **WebGL Fingerprint Noise** | Randomizes WebGL renderer/vendor strings | WebGL fingerprinting |
| **Font Enumeration Block** | Limits font enumeration to common fonts | Font-based fingerprinting |
| **WebRTC IP Leak Prevention** | Blocks WebRTC from leaking real IP | IP leak detection |
| **Timezone Spoofing** | Matches timezone to proxy location | Timezone mismatch detection |
| **Locale Spoofing** | Matches language/locale to proxy location | Locale mismatch detection |
| **User-Agent Rotation** | Rotates UA string per profile | UA-based tracking |
| **Screen Resolution Spoofing** | Reports hardware profile screen size | Screen fingerprinting |

### 2.4 Launch Command

```bash
titan-browser \
    --profile /opt/titan/profiles/titan_a1b2c3d4e5f6 \
    --target amazon.com \
    --proxy socks5://user:pass@proxy.example.com:1080
```

**Parameters:**
- `--profile` — Path to Genesis-generated profile directory
- `--target` — Target domain (loads target-specific settings)
- `--proxy` — SOCKS5 proxy for IP masking

### 2.5 Profile Loading

When launched with a profile, Camoufox:
1. Loads cookies from the profile's SQLite database
2. Loads browsing history
3. Loads localStorage entries
4. Applies hardware fingerprint from `hardware_profile.json`
5. Loads the Ghost Motor extension from `/opt/titan/extensions/ghost_motor/`

---

## 3. Ghost Motor Extension — Architecture

### 3.1 Manifest

```json
{
    "manifest_version": 3,
    "name": "Ghost Motor",
    "version": "5.2.0",
    "description": "Human input augmentation",
    "permissions": [],
    "host_permissions": ["<all_urls>"],
    "content_scripts": [{
        "matches": ["<all_urls>"],
        "js": ["ghost_motor.js"],
        "run_at": "document_start",
        "all_frames": true
    }]
}
```

**Key Design Decisions:**
- **MV3** — Uses Manifest V3 for modern browser compatibility
- **No permissions** — Requires zero special permissions (no storage, no tabs)
- **`document_start`** — Injects before any page scripts run, ensuring all events are captured
- **`all_frames: true`** — Augments input in iframes too (payment forms are often iframed)
- **Content script only** — No background service worker needed

### 3.2 IIFE Structure

The entire extension is wrapped in an Immediately Invoked Function Expression:
```javascript
(function() {
    'use strict';
    // ... all code ...
})();
```

This prevents any variable leakage to the page's global scope, making the extension harder to detect.

### 3.3 Initialization Flow

```
Page Load (document_start)
       │
       ▼
Check document.readyState
       │
       ├── "loading" ──► Wait for DOMContentLoaded
       └── "interactive"/"complete" ──► Initialize immediately
       │
       ▼
initialize()
       │
       ├── Register mousemove listener (capture, passive)
       ├── Register keydown listener (capture, passive)
       ├── Register keyup listener (capture, passive)
       ├── Register wheel listener (capture, passive)
       ├── Patch MouseEvent constructor
       ├── Patch getBoundingClientRect
       ├── Patch addEventListener (click timing)
       ├── Register BioCatch cursor lag detector
       ├── Start BioCatch element displacement observer
       ├── Start ThreatMetrix session continuity tracking
       └── Set window.__ghostMotorActive = true
```

---

## 4. Ghost Motor — Core Augmentation (V6.0)

### 4.1 Configuration Object

```javascript
const CONFIG = {
    mouse: {
        enabled: true,
        smoothingFactor: 0.15,       // Bezier curve intensity
        microTremorAmplitude: 1.5,   // Pixels of hand shake
        microTremorFrequency: 8,     // Hz
        overshootProbability: 0.12,  // 12% chance on fast moves
        overshootDistance: 8,        // Max overshoot pixels
        minSpeedForOvershoot: 500,   // px/s threshold
    },
    keyboard: {
        enabled: true,
        dwellTimeBase: 85,           // ms key held down
        dwellTimeVariance: 25,       // ±ms variance
        flightTimeBase: 110,         // ms between keys
        flightTimeVariance: 40,      // ±ms variance
    },
    scroll: {
        enabled: true,
        smoothingFactor: 0.2,
        momentumDecay: 0.92,         // Inertial decay factor
    }
};
```

### 4.2 Micro-Tremor Generation

**Purpose:** Simulates natural hand shake. Real humans cannot hold a mouse perfectly still — there is always 1-3px of involuntary movement.

**Implementation:** Multi-sine Perlin-like noise using three overlapping sine waves at different frequencies:

```javascript
tremor.x = sin(phase * 1.0) * 0.5 +    // Low frequency component
           sin(phase * 2.3) * 0.3 +      // Medium frequency
           sin(phase * 4.1) * 0.2;        // High frequency

tremor.y = sin(phase * 1.1 + 0.5) * 0.5 +
           sin(phase * 2.7 + 0.3) * 0.3 +
           sin(phase * 3.9 + 0.7) * 0.2;
```

- **Amplitude:** 1.5 pixels (configurable 0-5)
- **Frequency:** 8 Hz (matches physiological hand tremor)
- **Phase offset:** Y-axis has different phase offsets to prevent circular patterns

### 4.3 Bezier Curve Smoothing

**Purpose:** Real mouse movements follow curved paths, not straight lines. Behavioral biometrics detect perfectly straight cursor paths as bot indicators.

**Implementation:** Cubic Bezier curves with perpendicular offset:

```
P0 (start) ──── P1 (30% + perpendicular offset) ──── P2 (70% + half offset) ──── P3 (end)
```

- Control points are placed at 30% and 70% of the path
- Perpendicular offset creates natural curvature
- Offset magnitude = `distance * smoothingFactor * random(-0.5, 0.5)`

### 4.4 Overshoot Simulation

**Purpose:** When moving fast to a target, humans often overshoot slightly and correct. Bots land perfectly on target every time.

**Trigger:** Speed > 500 px/s AND random < 12%

**Implementation:**
1. Calculate overshoot position in direction of movement
2. Add angle variance (±0.15 radians)
3. Magnitude = min(8px, speed * 0.01)
4. Correction happens naturally on next mouse event

### 4.5 Keyboard Timing Augmentation

**Purpose:** Bots type at perfectly consistent speeds. Humans have variable key hold times (dwell) and inter-key gaps (flight).

| Parameter | Base | Variance | Effective Range |
|-----------|------|----------|-----------------|
| **Dwell Time** | 85ms | ±25ms | 60-110ms |
| **Flight Time** | 110ms | ±40ms | 70-150ms |

Each keypress stores its down-time and expected dwell for timing analysis.

### 4.6 Scroll Momentum

**Purpose:** Real scroll events have inertia — the scroll continues briefly after the user stops scrolling. Bots produce discrete, instant scroll jumps.

**Implementation:** Exponential decay momentum tracking:
```javascript
momentum = momentum * 0.92 + deltaY * 0.08
```

### 4.7 Click Timing Variance

**Purpose:** Bots process click events with zero delay. Humans have 1-5ms of processing latency.

**Implementation:** Wraps all `addEventListener('click', ...)` calls:
- 0-2ms delay: Execute immediately
- 2-5ms delay: Execute via `setTimeout`

### 4.8 API Patching

| Patched API | Modification | Purpose |
|-------------|-------------|---------|
| `MouseEvent` constructor | Tremor offset injection point | Synthetic events carry tremor |
| `Element.getBoundingClientRect()` | Preserved (tremor applied elsewhere) | Click position imprecision |
| `EventTarget.addEventListener()` | Click timing variance wrapper | Natural click latency |

---

## 5. Ghost Motor — BioCatch Evasion (V7.0)

### 5.1 Cursor Lag Detection

**What BioCatch Does:** BioCatch briefly desyncs the visible cursor position from the actual position (by injecting CSS transforms or moving the cursor via JavaScript). It then measures the user's reaction time and correction pattern. Bots don't react because they track logical position, not visual position.

**Ghost Motor Response:**

```
Monitor: screenX/screenY vs lastKnownCursorPos
       │
       ▼
Calculate drift = sqrt((actualX - expectedX)² + (actualY - expectedY)²)
       │
       ▼
drift > 50px AND not already responding?
       │
       ├── YES ──► Wait 150-400ms (human reaction time)
       │           │
       │           ▼
       │           Apply micro-adjustment (±1.5px random offset)
       │           │
       │           ▼
       │           Reset detection flag
       │
       └── NO ──► Update lastKnownCursorPos, continue
```

**Key Parameters:**
- **Detection threshold:** 50px drift
- **Reaction delay:** 150-400ms (uniformly random)
- **Correction magnitude:** ±1.5px (subtle, not a snap-to)
- **Debounce:** Only one response per lag event

### 5.2 Element Displacement Detection

**What BioCatch Does:** During hover over buttons/links, BioCatch shifts the element 2-8px by modifying its `style` or `class` attributes. It measures whether the user naturally adjusts their cursor to follow the element (human) or continues clicking at the original position (bot).

**Ghost Motor Response:**

```
MutationObserver watches: document.body (subtree, attributes)
       │
       ▼
Attribute change on button/a/input[type="submit"]?
       │
       ├── style changed ──► Trigger correction
       └── class changed ──► Trigger correction
       │
       ▼
Wait 100-250ms (human visual processing time)
       │
       ▼
Apply tremor-overlaid micro-correction to mouse offset
(tremor.x * 0.5, tremor.y * 0.5)
```

**Observer Configuration:**
```javascript
observer.observe(document.body, {
    attributes: true,
    subtree: true,
    attributeFilter: ['style', 'class']
});
```

---

## 6. Ghost Motor — ThreatMetrix Session Continuity (V7.0)

### 6.1 What ThreatMetrix Detects

ThreatMetrix (LexisNexis) builds a behavioral profile throughout the session. If behavioral patterns change mid-session (e.g., different typing speed, different mouse precision), it flags the session as potentially compromised (operator handoff detected).

### 6.2 Session Tracking

Ghost Motor maintains a `window.__titanSession` object:

```javascript
{
    startTime: Date.now(),
    mouseEventCount: 0,        // Total mouse events
    keyEventCount: 0,          // Total key events
    scrollEventCount: 0,       // Total scroll events
    avgMouseSpeed: 0,          // Running average
    avgTypingInterval: 0,      // Running average
    lastKeyTime: 0,            // Last keydown timestamp
    typingIntervals: [],       // Rolling window (last 50)
    consistencyScore: 1.0      // 0.0-1.0 consistency metric
}
```

**Typing Interval Tracking:**
- Records time between consecutive keydown events
- Ignores gaps > 2000ms (pauses between words/thoughts)
- Maintains rolling window of last 50 intervals
- Used to ensure typing rhythm stays consistent throughout session

---

## 7. Ghost Motor V6 Python Engine (DMTG)

**Module:** `ghost_motor_v6.py` | **Lines:** 731 | **Path:** `/opt/titan/core/ghost_motor_v6.py`

### 7.1 Why Diffusion > GAN

The V5.2 Ghost Motor used GAN-generated trajectories. V6 replaces this with **Diffusion Model Trajectory Generation (DMTG)** because:

| Problem | GAN | DMTG |
|---------|-----|------|
| **Mode Collapse** | After 100+ clicks, patterns repeat | Each trajectory mathematically unique |
| **Entropy** | Statistical entropy drops below human threshold | Fractal variability preserved at all scales |
| **Diversity** | Limited trajectory shapes | Infinite variation between same endpoints |

**Reference:** arXiv:2410.18233v1 — DMTG Paper

### 7.2 DMTG Architecture

```
1. Initialize with Gaussian noise (N random points)
2. Reverse diffusion conditioned on start/end points
3. Inject biological entropy (σ_t) at each step
4. Apply motor inertia smoothing
5. Output trajectory indistinguishable from human hand
```

### 7.3 Configuration

```python
@dataclass
class TrajectoryConfig:
    num_diffusion_steps: int = 50        # Denoising steps
    noise_schedule: str = "cosine"       # "linear", "cosine", "quadratic"
    entropy_scale: float = 1.0           # 0.5 (precise) to 2.0 (chaotic)
    micro_tremor_amplitude: float = 1.5  # Pixels of hand shake
    overshoot_probability: float = 0.12  # Chance of target overshoot
    overshoot_max_distance: float = 8.0  # Max overshoot pixels
    correction_probability: float = 0.08 # Mid-path direction changes
    min_duration_ms: int = 100           # Minimum trajectory time
    max_duration_ms: int = 800           # Maximum trajectory time
    persona: PersonaType = CASUAL        # Behavioral persona
```

### 7.4 Persona Types

| Persona | Precision | Entropy | Use Case |
|---------|-----------|---------|----------|
| **GAMER** | High | Low | Gaming platforms (Steam, Epic) |
| **CASUAL** | Medium | Medium | General e-commerce |
| **ELDERLY** | Low | High | Retiree archetype profiles |
| **PROFESSIONAL** | High | Medium | Business/professional targets |

### 7.5 Trajectory Point Structure

```python
@dataclass
class TrajectoryPoint:
    x: float           # X coordinate
    y: float           # Y coordinate
    timestamp: float   # Time offset in seconds
    velocity: float    # Instantaneous velocity (px/s)
    acceleration: float # Instantaneous acceleration (px/s²)
```

### 7.6 Dependencies

- **Required:** `numpy`
- **Optional:** `scipy` (for spline interpolation and Gaussian filtering)
- **Optional:** `onnxruntime` (for pre-trained DMTG model inference)

Graceful fallback when optional dependencies are missing.

---

## 8. V7.0 Evasion Profiles

### 8.1 Forter Safe Parameters

11 behavioral parameters that pass Forter's analysis:

```python
FORTER_SAFE_PARAMS = {
    "mouse_speed_mean": (180, 420),      # px/s
    "mouse_speed_std": (60, 150),        # px/s
    "click_precision_mean": (2.5, 8.0),  # px from center
    "scroll_speed_mean": (200, 600),     # px/s
    "typing_speed_mean": (4.0, 8.5),     # chars/s
    "typing_speed_std": (1.0, 3.0),      # chars/s
    "dwell_time_mean": (70, 120),        # ms
    "flight_time_mean": (80, 180),       # ms
    "pause_frequency": (0.05, 0.15),     # pauses per char
    "correction_rate": (0.02, 0.08),     # backspace rate
    "session_duration_min": (120, 600),  # seconds
}
```

### 8.2 BioCatch Evasion Guide

```python
BIOCATCH_EVASION = {
    "cursor_lag_response": "150-400ms delayed micro-adjustment (3px)",
    "displaced_element": "100-250ms correction with tremor overlay",
    "cognitive_tells": "Vary pause duration 0.5-3s on payment fields",
    "mobile_evasion": "Touch pressure variance 0.3-0.8, hold time 80-200ms",
}
```

### 8.3 ThreatMetrix Session Rules

```python
THREATMETRIX_SESSION_RULES = {
    "min_session_duration": 120,       # seconds
    "min_mouse_events": 200,           # before checkout
    "min_key_events": 50,              # before checkout
    "behavioral_consistency": 0.85,    # min consistency score
}
```

### 8.4 Warmup Browsing Patterns

Three target-specific warmup sequences:

**Best Buy Warmup:**
```
1. Google search "best buy laptop deals" (15-30s)
2. Click organic result (not ad)
3. Browse 2-3 product pages (45-90s each)
4. Add item to cart
5. Continue shopping (30-60s)
6. Return to cart
7. Proceed to checkout
```

**General E-Commerce Warmup:**
```
1. Direct navigation to target
2. Browse homepage (30-60s)
3. Use search function
4. View 3-5 products (30-60s each)
5. Read reviews on 1-2 products
6. Add to cart
7. Continue browsing briefly
8. Checkout
```

**Forter Trust Building:**
```
1. Visit target site 2-3 days before operation
2. Browse products, add to wishlist
3. Return next day, browse more
4. On operation day, go directly to saved items
5. Natural checkout flow
```

---

## 9. Runtime Configuration API

The extension exposes `window.__ghostMotorConfig` for runtime adjustment:

| Method | Args | Range | Description |
|--------|------|-------|-------------|
| `get()` | — | — | Returns copy of current CONFIG |
| `setMouseEnabled(bool)` | `true/false` | — | Enable/disable mouse augmentation |
| `setKeyboardEnabled(bool)` | `true/false` | — | Enable/disable keyboard augmentation |
| `setTremorAmplitude(float)` | `0-5` | Clamped | Set hand shake intensity |
| `setSmoothingFactor(float)` | `0-0.5` | Clamped | Set Bezier curve intensity |
| `setOvershootProbability(float)` | `0-0.5` | Clamped | Set overshoot chance |

**Usage from browser console:**
```javascript
// Reduce tremor for precise clicking
window.__ghostMotorConfig.setTremorAmplitude(0.8);

// Increase overshoot for more human-like behavior
window.__ghostMotorConfig.setOvershootProbability(0.2);

// Check current settings
console.log(window.__ghostMotorConfig.get());
```

**Global State Variables:**

| Variable | Type | Description |
|----------|------|-------------|
| `window.__ghostMotorActive` | `boolean` | Whether Ghost Motor is initialized |
| `window.__titanMouseOffset` | `{x, y}` | Current tremor offset |
| `window.__titanKeyTimes` | `Object` | Key timing data per key code |
| `window.__titanScrollMomentum` | `number` | Current scroll momentum |
| `window.__titanSession` | `Object` | Session continuity metrics |

---

## 10. How They Work Together

### 10.1 Full Stack Integration

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 0: Hardware Shield (Kernel)                               │
│ - CPU/GPU/Memory spoofing at Ring 0                             │
│ - Undetectable by any userspace application                     │
├─────────────────────────────────────────────────────────────────┤
│ Layer 0: Network Shield (eBPF)                                  │
│ - TCP fingerprint modification (TTL, window size, timestamps)   │
│ - QUIC redirection to userspace proxy                           │
├─────────────────────────────────────────────────────────────────┤
│ Layer 1: Camoufox Browser                                       │
│ - Canvas/WebGL/Font fingerprint protection                      │
│ - WebRTC leak prevention                                        │
│ - Timezone/locale spoofing                                      │
│ - Genesis profile loaded (cookies, history, localStorage)       │
├─────────────────────────────────────────────────────────────────┤
│ Layer 2: Ghost Motor Extension (JS)                             │
│ - Micro-tremor injection (hand shake)                           │
│ - Bezier curve smoothing (natural paths)                        │
│ - Overshoot simulation (targeting error)                        │
│ - Keyboard timing variance (natural typing)                     │
│ - BioCatch invisible challenge response                         │
│ - ThreatMetrix session continuity                               │
├─────────────────────────────────────────────────────────────────┤
│ Layer 2: Ghost Motor V6 Python (DMTG)                           │
│ - Diffusion-based trajectory generation                         │
│ - Persona-specific movement profiles                            │
│ - Forter/BioCatch/ThreatMetrix evasion parameters               │
│ - Warmup browsing pattern guidance                              │
├─────────────────────────────────────────────────────────────────┤
│ Layer 7: Human Operator                                         │
│ - Manual browsing with augmented input                          │
│ - All decisions are human                                       │
│ - Ghost Motor makes human input look MORE human                 │
└─────────────────────────────────────────────────────────────────┘
```

### 10.2 What Each Component Defeats

| Defensive System | Defeated By |
|-----------------|-------------|
| Browser fingerprinting (FingerprintJS, CreepJS) | Camoufox + Hardware Shield |
| Canvas/WebGL fingerprinting | Camoufox + Fingerprint Injector |
| TCP/IP fingerprinting (p0f, JA3/JA4) | Network Shield + QUIC Proxy |
| Behavioral biometrics (BioCatch) | Ghost Motor Extension + DMTG |
| Session analysis (ThreatMetrix) | Ghost Motor Session Continuity |
| Fraud scoring (Forter, Sift) | Ghost Motor Safe Params + Warmup |
| Device fingerprinting (Stripe Radar) | Genesis aged cookies + Hardware Shield |
| Bot detection (reCAPTCHA, hCaptcha) | Human operator + Ghost Motor augmentation |

---

**End of Browser & Extension Analysis** | **TITAN V7.0 SINGULARITY**
