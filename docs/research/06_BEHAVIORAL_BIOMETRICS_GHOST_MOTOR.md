# Behavioral Biometrics — Ghost Motor Diffusion Engine

## Core Module: `ghost_motor_v6.py` (944 lines)

Ghost Motor is TITAN's behavioral biometrics simulation engine. It generates human-like mouse movements, keyboard dynamics, and scroll patterns that defeat behavioral analysis systems like BioCatch, Forter Behavioral, ThreatMetrix Session Profiling, and Sardine.

---

## Why Behavioral Biometrics Matter

Modern antifraud systems don't just check WHAT you do — they check HOW you do it:

| Signal | What It Reveals | Bot Indicator |
|--------|----------------|---------------|
| Mouse velocity | Human mice accelerate/decelerate smoothly | Bots move at constant speed |
| Mouse curvature | Humans follow curved Bézier paths | Bots move in straight lines |
| Click precision | Humans overshoot then correct | Bots click exact pixel coordinates |
| Key hold time | Humans hold keys 50-150ms | Bots have 0ms or constant hold time |
| Inter-key interval | Humans type 100-300ms between keys | Bots type at constant intervals |
| Scroll behavior | Humans scroll with momentum and pauses | Bots scroll exact pixel amounts |
| Idle patterns | Humans pause to read, think, decide | Bots never pause or pause at fixed intervals |
| Session rhythm | Humans have variable pace throughout session | Bots maintain constant pace |

**BioCatch** alone analyzes 2,000+ behavioral parameters per session. A single anomaly can flag the session.

---

## Ghost Motor Architecture

### Diffusion Model Approach

Ghost Motor uses a **diffusion-based trajectory generation** model (inspired by motion diffusion models in computer graphics). Instead of scripting mouse movements with simple Bézier curves, it:

1. **Samples from a learned distribution** of human mouse trajectories
2. **Adds persona-specific noise** (Student types fast and sloppy, Elderly types slow and careful)
3. **Injects micro-corrections** (overshoot → correct, a distinctly human pattern)
4. **Applies fatigue modeling** (movements get slightly less precise over time)

```python
class GhostMotorDiffusion:
    """
    Diffusion-based human behavior synthesis engine.
    
    Generates trajectories that pass BioCatch, Forter, and ThreatMetrix
    behavioral analysis by modeling:
    
    1. Mouse movement dynamics (velocity, acceleration, jerk profiles)
    2. Keyboard timing distributions (per-key dwell and flight times)
    3. Scroll behavior (momentum, direction changes, reading pauses)
    4. Cognitive delays (thinking time before actions)
    5. Error patterns (typos, corrections, hesitations)
    6. Session-level rhythm (warm-up, peak, fatigue phases)
    """
```

### Persona Types

Each persona has distinct behavioral characteristics:

| Persona | Mouse Speed | Typing Speed | Error Rate | Scroll Style | Cognitive Delay |
|---------|------------|-------------|-----------|-------------|----------------|
| **Student** | Fast, imprecise | 60-80 WPM | 5-8% | Quick flicks | Short (200-400ms) |
| **Professional** | Moderate, precise | 50-70 WPM | 2-4% | Smooth, measured | Medium (300-600ms) |
| **Elderly** | Slow, careful | 20-35 WPM | 8-12% | Slow, deliberate | Long (500-1200ms) |
| **Gamer** | Very fast, precise | 70-90 WPM | 3-5% | Fast with momentum | Very short (100-250ms) |
| **Casual** | Variable | 40-55 WPM | 4-7% | Natural | Variable (300-800ms) |

---

## Mouse Movement Generation

### Trajectory Components

Each mouse movement from point A to point B consists of:

1. **Ballistic phase**: Fast initial movement toward target (70% of distance)
2. **Correction phase**: Slower approach with micro-adjustments (25% of distance)
3. **Final positioning**: Very slow precise movement to exact target (5% of distance)

```python
def generate_mouse_trajectory(self, start, end, persona):
    """
    Generate a human-like mouse trajectory using diffusion sampling.
    
    The trajectory includes:
    - Bézier curve base path (not straight line)
    - Velocity profile: slow start → fast middle → slow end
    - Gaussian noise on each point (σ = 1-3 pixels)
    - Overshoot probability: 15-30% (moves past target, then corrects)
    - Micro-pause probability: 5-10% (brief hesitation mid-movement)
    """
```

### Velocity Profile

Real human mouse movements follow a bell-shaped velocity curve:

```
Velocity
  ↑
  │        ╭──────╮
  │       ╱        ╲
  │      ╱          ╲
  │     ╱            ╲
  │    ╱              ╲
  │───╱                ╲───
  └──────────────────────→ Time
     Start            End
```

Bots typically have constant velocity (flat line) or instant teleportation (spike). Ghost Motor replicates the natural bell curve with per-persona variation.

### Overshoot and Correction

In 15-30% of movements, the cursor intentionally overshoots the target by 5-15 pixels, then corrects back. This is a distinctly human pattern that BioCatch specifically looks for:

```
Target: (500, 300)
Actual path: ... → (508, 297) → (503, 299) → (500, 300)
                    ↑ overshoot   ↑ correction  ↑ final
```

---

## Keyboard Dynamics

### Per-Key Timing Model

Ghost Motor maintains timing distributions for each key:

```python
KEY_TIMING = {
    # key: (mean_dwell_ms, std_dwell, mean_flight_ms, std_flight)
    'a': (95, 15, 120, 25),
    'b': (105, 18, 140, 30),
    'space': (80, 12, 100, 20),
    'shift': (110, 20, 90, 15),
    'enter': (120, 25, 150, 35),
    # ... all keys
}
```

- **Dwell time**: How long the key is held down (50-150ms for most keys)
- **Flight time**: Time between releasing one key and pressing the next (80-200ms)

### Typing Patterns

1. **Burst typing**: 3-5 characters typed quickly, then brief pause (word boundary)
2. **Hesitation**: Longer pause before uncommon words or numbers
3. **Backspace patterns**: Occasional typo → backspace → retype (2-5% of characters)
4. **Shift timing**: Shift held slightly before the character key
5. **Number row**: Slower typing for numbers (less muscle memory)

### Form Filling Simulation

When filling a checkout form, Ghost Motor simulates realistic form interaction:

```
1. Click name field (mouse movement + click)
2. Pause 200-500ms (reading the label)
3. Type first name (burst typing)
4. Tab to next field (or click)
5. Pause 100-300ms
6. Type last name
7. Tab to address field
8. Longer pause 500-1000ms (looking at card/address)
9. Type address (slower, checking each character)
10. ... continue with natural rhythm
```

---

## Scroll Behavior

### Natural Scroll Patterns

```python
def generate_scroll_sequence(self, page_height, reading_sections):
    """
    Generate realistic scroll behavior:
    
    1. Initial fast scroll to content area
    2. Slow scroll while reading (50-100px per scroll event)
    3. Pause at interesting content (1-5 seconds)
    4. Occasional scroll-up (re-reading something)
    5. Fast scroll to bottom (skip to checkout)
    6. Momentum decay (scroll slows naturally)
    """
```

### Reading Detection Evasion

Antifraud systems measure "time on page" and "scroll depth" to determine if the user actually read the page. Ghost Motor ensures:

- Product pages: 15-45 seconds with 60-80% scroll depth
- Checkout pages: 30-90 seconds with full scroll
- Cart pages: 10-20 seconds with review scrolling

---

## Anti-BioCatch Specific Measures

BioCatch is the most sophisticated behavioral biometrics system. Ghost Motor specifically counters:

| BioCatch Signal | Ghost Motor Counter |
|----------------|-------------------|
| Mouse movement entropy | Controlled randomness matching human entropy range |
| Click accuracy distribution | Intentional overshoot/correction patterns |
| Typing rhythm consistency | Per-session rhythm variation with fatigue |
| Cognitive response time | Persona-appropriate thinking delays |
| Device interaction patterns | Touch/mouse distinction (always mouse on desktop) |
| Session behavioral drift | Gradual fatigue modeling over session duration |
| Copy-paste detection | Never copy-paste card numbers (always type) |
| Tab switching patterns | Natural tab switches during checkout |

### Forter Behavioral Parameters

Forter tracks these specific parameters (from `FORTER_SAFE_PARAMS` in ghost_motor_v6.py):

```python
FORTER_SAFE_PARAMS = {
    "mouse_speed_mean": (180, 450),      # pixels/second
    "mouse_speed_std": (50, 150),
    "click_accuracy_mean": (2, 8),        # pixels from center
    "typing_speed_mean": (150, 350),      # ms between keys
    "scroll_speed_mean": (200, 600),      # pixels/second
    "idle_time_mean": (2000, 8000),       # ms between actions
    "session_duration_mean": (120, 600),  # seconds
}
```

Ghost Motor ensures all behavioral parameters fall within these "safe" ranges that match genuine human users.

---

## Browser Extension: Ghost Motor (`/opt/titan/extensions/ghost_motor/`)

The Ghost Motor browser extension injects behavioral simulation directly into the browser:

- **`manifest.json`**: Extension manifest with content script permissions
- **`ghost_motor.js`**: Content script that intercepts and humanizes all mouse/keyboard/scroll events

The extension modifies event timestamps, adds micro-noise to coordinates, and ensures all JavaScript-visible behavioral signals match human patterns.

---

## Warmup Browsing Patterns

Before the actual operation, Ghost Motor generates a "warmup" browsing session:

```python
WARMUP_BROWSING_PATTERNS = [
    {"action": "google_search", "query": "best deals electronics", "duration": 15},
    {"action": "visit_site", "url": "target_domain", "duration": 30},
    {"action": "browse_products", "count": 3, "duration": 45},
    {"action": "add_to_cart", "duration": 10},
    {"action": "continue_shopping", "duration": 20},
    {"action": "return_to_cart", "duration": 5},
    {"action": "proceed_checkout", "duration": 0},
]
```

This warmup session establishes a natural browsing pattern before the purchase, making the checkout look like a natural conclusion to a browsing session rather than a direct-to-checkout bot pattern.
