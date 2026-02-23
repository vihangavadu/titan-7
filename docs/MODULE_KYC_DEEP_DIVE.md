# MODULE 3: KYC CONTROLLER — Complete Technical Reference

## The Mask: Virtual Camera & Identity Verification Bypass

**Module:** `kyc_core.py` | **Lines:** 624 | **Path:** `/opt/titan/core/kyc_core.py`  
**Version:** 8.1.0 | **Authority:** Dva.12

---

## Table of Contents

1. [Purpose & Philosophy](#1-purpose--philosophy)
2. [System Architecture](#2-system-architecture)
3. [Classes & Data Structures](#3-classes--data-structures)
4. [Virtual Camera Setup](#4-virtual-camera-setup)
5. [Streaming Modes](#5-streaming-modes)
6. [Neural Reenactment Engine](#6-neural-reenactment-engine)
7. [Motion Presets](#7-motion-presets)
8. [Real-Time Parameter Control](#8-real-time-parameter-control)
9. [Integrity Shield](#9-integrity-shield)
10. [Integration Points](#10-integration-points)
11. [API Reference](#11-api-reference)

---

## 1. Purpose & Philosophy

KYC Controller is **The Mask** — a system-level virtual camera controller that defeats identity verification (KYC) checks. It creates a virtual webcam device (`/dev/video2`) that any application sees as a real camera, then streams AI-generated video of a synthetic face performing liveness actions (blinking, smiling, head turns).

**Key Principle:** The KYC Controller operates at the **system level**, not the browser level. It uses Linux's `v4l2loopback` kernel module to create a virtual camera device that is indistinguishable from a real webcam. Any application — browser, Zoom, Telegram, native KYC apps — sees it as a legitimate camera.

**Why This Works:**
- KYC systems expect a webcam feed showing a live person
- v4l2loopback creates a device at `/dev/video2` that reports as "Integrated Webcam"
- Neural reenactment (LivePortrait) animates a static ID photo with realistic motion
- The KYC system sees a "live person" performing requested actions
- The Integrity Shield hides evidence of virtual camera from detection

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        KYC GUI App                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────────────┐  │
│  │ Source    │  │ Motion   │  │ Parameter Sliders            │  │
│  │ Image    │  │ Preset   │  │ Head Rotation | Expression   │  │
│  │ Selector │  │ Dropdown │  │ Blink Freq   | Micro-Move    │  │
│  └────┬─────┘  └────┬─────┘  └──────────────┬───────────────┘  │
│       │              │                       │                  │
└───────┼──────────────┼───────────────────────┼──────────────────┘
        │              │                       │
        ▼              ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    KYCController (Python)                        │
│                                                                 │
│  ┌──────────────────┐    ┌──────────────────────────────────┐   │
│  │ ReenactmentConfig │───►│ LivePortrait / Simulation Engine │   │
│  │ - source_image    │    │ - Extract motion from driving   │   │
│  │ - motion_type     │    │ - Apply to source face          │   │
│  │ - head_rotation   │    │ - Output raw frames             │   │
│  │ - expression      │    └──────────────┬───────────────────┘   │
│  │ - blink_freq      │                   │                      │
│  │ - micro_movement  │                   ▼                      │
│  └──────────────────┘    ┌──────────────────────────────────┐   │
│                          │ Named Pipe (/tmp/titan_reenact)   │   │
│                          └──────────────┬───────────────────┘   │
│                                         │                      │
│                                         ▼                      │
│                          ┌──────────────────────────────────┐   │
│                          │ ffmpeg (rawvideo → v4l2)          │   │
│                          │ -f rawvideo -pix_fmt rgb24        │   │
│                          │ -s 1280x720 -r 30                 │   │
│                          │ → /dev/video2                     │   │
│                          └──────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    v4l2loopback (Kernel Module)                  │
│                                                                 │
│  /dev/video2  →  "Integrated Webcam"  →  exclusive_caps=1       │
│                                                                 │
│  Any application sees this as a real USB webcam                 │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────┐
                    │  Target Application       │
                    │  (Browser / Zoom / KYC)   │
                    │  Reads /dev/video2 feed   │
                    └───────────────────────────┘
```

---

## 3. Classes & Data Structures

### 3.1 Enums

#### `CameraState`
```python
class CameraState(Enum):
    STOPPED = "stopped"      # No streaming active
    STREAMING = "streaming"  # Actively streaming to virtual camera
    PAUSED = "paused"        # Stream paused (black frames)
    ERROR = "error"          # Error state
```

#### `MotionType`
```python
class MotionType(Enum):
    NEUTRAL = "neutral"          # Subtle idle movement
    BLINK = "blink"              # Single eye blink
    BLINK_TWICE = "blink_twice"  # Two consecutive blinks
    SMILE = "smile"              # Natural smile
    HEAD_LEFT = "head_left"      # Turn head left
    HEAD_RIGHT = "head_right"    # Turn head right
    HEAD_NOD = "head_nod"        # Nodding motion
    LOOK_UP = "look_up"          # Look upward
    LOOK_DOWN = "look_down"      # Look downward
```

### 3.2 Dataclasses

#### `ReenactmentConfig`
```python
@dataclass
class ReenactmentConfig:
    source_image: str                    # Path to ID photo or generated face
    motion_type: MotionType = NEUTRAL    # Which motion to perform
    output_fps: int = 30                 # Frame rate
    output_resolution: tuple = (1280, 720)  # Output size
    loop: bool = True                    # Loop the motion continuously
    
    # GUI slider parameters
    head_rotation_intensity: float = 1.0  # 0.0 - 2.0
    expression_intensity: float = 1.0     # 0.0 - 2.0
    blink_frequency: float = 0.3          # Blinks per second
    micro_movement: float = 0.1           # Subtle head sway
```

#### `VirtualCameraConfig`
```python
@dataclass
class VirtualCameraConfig:
    device_path: str = "/dev/video2"       # Virtual camera device
    device_name: str = "Integrated Webcam" # Spoofed device name
    width: int = 1280                      # Resolution width
    height: int = 720                      # Resolution height
    fps: int = 30                          # Frame rate
    pixel_format: str = "yuyv422"          # V4L2 pixel format
```

---

## 4. Virtual Camera Setup

### 4.1 v4l2loopback Module Loading

```bash
modprobe v4l2loopback \
    devices=1 \
    video_nr=2 \
    card_label='Integrated Webcam' \
    exclusive_caps=1
```

**Parameters:**
- `devices=1` — Create one virtual camera
- `video_nr=2` — Assign to `/dev/video2` (avoids conflict with real cameras at 0/1)
- `card_label='Integrated Webcam'` — Spoofed device name (matches common laptop webcams)
- `exclusive_caps=1` — Report as output-only device (required for some apps)

### 4.2 Setup Flow

```
setup_virtual_camera()
       │
       ▼
Check lsmod for v4l2loopback
       │
       ├── Not loaded ──► modprobe v4l2loopback (with params)
       │
       └── Already loaded ──► Skip
       │
       ▼
Verify /dev/video2 exists
       │
       ├── Exists ──► Return True
       └── Missing ──► Error callback, Return False
```

---

## 5. Streaming Modes

### 5.1 Video File Streaming

```python
controller.stream_video("/path/to/video.mp4", loop=True)
```

Streams a pre-recorded video file to the virtual camera using ffmpeg:

```bash
ffmpeg -re -stream_loop -1 -i video.mp4 \
    -vf scale=1280:720 \
    -f v4l2 -pix_fmt yuyv422 -r 30 \
    /dev/video2
```

**Use Case:** Pre-recorded KYC verification videos, document display.

### 5.2 Static Image Streaming

```python
controller.stream_image("/path/to/id_photo.jpg")
```

Streams a static image continuously:

```bash
ffmpeg -loop 1 -re -i photo.jpg \
    -vf scale=1280:720 \
    -f v4l2 -pix_fmt yuyv422 -r 30 \
    /dev/video2
```

**Use Case:** Document verification where the KYC system needs to see an ID card.

### 5.3 Neural Reenactment Streaming

```python
config = ReenactmentConfig(
    source_image="/path/to/face.jpg",
    motion_type=MotionType.BLINK_TWICE,
    head_rotation_intensity=0.8,
    expression_intensity=1.2
)
controller.start_reenactment(config)
```

**Use Case:** Live face verification with liveness detection. The AI animates a static photo to perform requested actions.

---

## 6. Neural Reenactment Engine

### 7.0.3 LivePortrait Integration

When the LivePortrait model is installed at `/opt/titan/models/liveportrait/`, the engine uses real neural reenactment:

```bash
python3 -m liveportrait.inference \
    --source face.jpg \
    --driving motion_blink.mp4 \
    --output /tmp/titan_reenact_pipe \
    --head_rotation 0.8 \
    --expression 1.2 \
    --fps 30
```

**Pipeline:**
1. Load source face image (ID photo)
2. Extract motion keypoints from driving video (motion preset)
3. Apply motion to source face using neural network
4. Output raw RGB frames to named pipe
5. ffmpeg reads pipe and streams to v4l2loopback

### 7.0.3 Simulation Fallback

When LivePortrait is not installed, the engine falls back to streaming the motion driving video directly through ffmpeg. This is less convincing but functional for testing.

### 6.3 Motion Assets

Motion driving videos are stored at `/opt/titan/assets/motions/`:

| File | Motion | Duration |
|------|--------|----------|
| `neutral.mp4` | Subtle idle movement, breathing | Continuous |
| `blink.mp4` | Single natural eye blink | 2s |
| `blink_twice.mp4` | Two consecutive blinks | 3s |
| `smile.mp4` | Natural smile expression | 2s |
| `head_left.mp4` | Turn head to the left | 3s |
| `head_right.mp4` | Turn head to the right | 3s |
| `head_nod.mp4` | Nodding motion | 3s |
| `look_up.mp4` | Look upward | 2s |
| `look_down.mp4` | Look downward | 2s |

Also supports `.pkl` format (LivePortrait serialized motion data) for higher fidelity.

### 6.4 Reenactment Loop

The reenactment runs in a background thread (`_reenactment_loop`):

```
1. Create named pipe at /tmp/titan_reenact_pipe
2. Start ffmpeg reading from pipe → /dev/video2
3. Start LivePortrait inference writing to pipe
4. Monitor for stop event or process exit
5. If loop=True and process exits, restart
6. On stop: terminate all processes, remove pipe
```

---

## 7. Motion Presets

Each preset is available in the GUI dropdown:

| Preset | Name | Description | Duration | Common KYC Use |
|--------|------|-------------|----------|----------------|
| `NEUTRAL` | Neutral | Subtle idle movement, natural breathing | Continuous | Default state |
| `BLINK` | Single Blink | Natural single eye blink | 2s | Basic liveness |
| `BLINK_TWICE` | Blink Twice | Two consecutive blinks | 3s | **Most common liveness check** |
| `SMILE` | Smile | Natural smile expression | 2s | Expression check |
| `HEAD_LEFT` | Turn Head Left | Turn head to the left | 3s | Profile angle check |
| `HEAD_RIGHT` | Turn Head Right | Turn head to the right | 3s | Profile angle check |
| `HEAD_NOD` | Nod Yes/No | Nodding motion | 3s | Action verification |
| `LOOK_UP` | Look Up | Look upward | 2s | Gaze tracking |
| `LOOK_DOWN` | Look Down | Look downward | 2s | Gaze tracking |

---

## 8. Real-Time Parameter Control

The GUI provides sliders that update reenactment parameters in real-time:

```python
controller.update_reenactment_params(
    head_rotation=0.8,    # 0.0 (still) to 2.0 (exaggerated)
    expression=1.2,       # 0.0 (neutral) to 2.0 (exaggerated)
    blink_freq=0.3,       # Blinks per second (0.2-0.5 is natural)
    micro_movement=0.15   # Subtle head sway amplitude
)
```

| Parameter | Range | Default | Natural Range | Notes |
|-----------|-------|---------|---------------|-------|
| `head_rotation_intensity` | 0.0 - 2.0 | 1.0 | 0.7 - 1.3 | How far the head turns |
| `expression_intensity` | 0.0 - 2.0 | 1.0 | 0.8 - 1.2 | How strong expressions are |
| `blink_frequency` | 0.0 - 1.0 | 0.3 | 0.2 - 0.5 | Blinks per second |
| `micro_movement` | 0.0 - 0.5 | 0.1 | 0.05 - 0.2 | Subtle head sway |

**Communication:** In production, parameters are sent to the reenactment engine via IPC (shared memory or socket). The engine adjusts output in real-time without restarting.

---

## 9. Integrity Shield

### 9.1 Purpose

Some KYC applications detect virtual cameras by checking for:
- `v4l2loopback` kernel module in `lsmod`
- Virtual camera devices in `/dev/`
- Screen recording software
- Root/jailbreak indicators

### 9.2 Implementation

`IntegrityShield` provides an `LD_PRELOAD` shared library (`/opt/titan/lib/integrity_shield.so`) that intercepts system calls to hide virtual camera evidence.

```python
class IntegrityShield:
    SHIELD_LIB_PATH = Path("/opt/titan/lib/integrity_shield.so")
```

### 9.3 Environment Variables

| Variable | Value | Effect |
|----------|-------|--------|
| `LD_PRELOAD` | `/opt/titan/lib/integrity_shield.so` | Intercept system calls |
| `TITAN_HIDE_VIRTUAL_CAM` | `1` | Hide virtual camera from device enumeration |
| `TITAN_HIDE_V4L2LOOPBACK` | `1` | Hide v4l2loopback from module listing |

### 9.4 Usage

```python
# Check availability
if IntegrityShield.is_available():
    # Get env vars for manual use
    env = IntegrityShield.get_env_vars()
    
    # Or launch a process with shield
    process = IntegrityShield.launch_with_shield(
        ["firefox", "--url", "https://kyc-site.com"]
    )
```

---

## 10. Integration Points

### 10.1 With Browser

The virtual camera is system-level — when the operator opens a KYC page in the hardened browser, the browser's `getUserMedia()` API sees `/dev/video2` as "Integrated Webcam" and streams the reenacted video.

### 10.2 With Genesis Engine

Genesis profiles can include KYC-ready metadata:
- Pre-generated face images matching the persona
- Document images (ID cards) for document verification steps

### 10.3 With Handover Protocol

The handover document includes KYC status:
- Whether KYC is required for the target
- Which motion presets to prepare
- Recommended reenactment parameters

### 10.4 Stream Control

| Method | Effect |
|--------|--------|
| `stop_stream()` | Terminates all ffmpeg/reenactment processes |
| `pause_stream()` | Sends SIGSTOP to ffmpeg (black frames) |
| `resume_stream()` | Sends SIGCONT to ffmpeg (resumes) |
| `cleanup()` | Stops stream, optionally unloads v4l2loopback |

### 10.5 Camera Discovery

```python
cameras = controller.get_available_cameras()
# Returns list of all /dev/video* devices with names and virtual status
# [{"device": "/dev/video0", "name": "HD Webcam", "is_virtual": False},
#  {"device": "/dev/video2", "name": "Integrated Webcam", "is_virtual": True}]
```

---

## 11. API Reference

### KYCController

```python
controller = KYCController(config=VirtualCameraConfig())
```

| Method | Args | Returns | Description |
|--------|------|---------|-------------|
| `setup_virtual_camera()` | — | `bool` | Load v4l2loopback, verify device |
| `stream_video(path, loop)` | `str, bool` | `bool` | Stream video file to virtual cam |
| `stream_image(path)` | `str` | `bool` | Stream static image to virtual cam |
| `start_reenactment(config)` | `ReenactmentConfig` | `bool` | Start neural reenactment |
| `update_reenactment_params(...)` | `float` kwargs | `None` | Update params in real-time |
| `stop_stream()` | — | `None` | Stop all streaming |
| `pause_stream()` | — | `None` | Pause stream (SIGSTOP) |
| `resume_stream()` | — | `None` | Resume stream (SIGCONT) |
| `get_available_cameras()` | — | `List[Dict]` | List all video devices |
| `get_available_motions()` | — | `List[Dict]` | List motion presets |
| `cleanup()` | — | `None` | Full cleanup |

**Callbacks:**
- `on_state_change: Callable[[CameraState], None]` — Called when state changes
- `on_error: Callable[[str], None]` — Called on error with message

### IntegrityShield

| Method | Returns | Description |
|--------|---------|-------------|
| `is_available()` | `bool` | Check if shield library exists |
| `get_env_vars()` | `Dict[str, str]` | Get LD_PRELOAD env vars |
| `launch_with_shield(cmd)` | `Popen` | Launch process with shield active |

---

## 12. V7.0.3 Additions — Ambient Lighting Normalization (GAP-5 Fix)

### 12.1 Problem

Synthetic face injection is detectable when ambient lighting in the synthetic video doesn't match the real environment. Tier-1 KYC systems (Veriff, Au10tix) analyze luminance discontinuity between face and background.

### 12.2 Solution — Two-Stage Pipeline

**File:** `camera_injector.py` — `CameraInjector` class

**Stage 1: `_sample_ambient_luminance(background_device)`**
- Captures single frame from real background camera via `ffprobe`
- Extracts average luminance (Y), blue chrominance (U), red chrominance (V)
- Returns `{"y_mean": float, "u_mean": float, "v_mean": float}`
- Executes in <50ms to avoid injection delay

**Stage 2: `_build_ambient_filter(ambient_data)`**
- Computes brightness offset: `(ambient_Y - 128) / 256` → FFmpeg `eq=brightness`
- Computes contrast scaling from luminance range
- Computes color temperature shift from U/V chrominance → `colorchannelmixer`
- Returns FFmpeg filter string appended to injection pipeline

**Result:** Synthetic face brightness and color temperature track the real room. If operator turns on a lamp, injected face brightens accordingly.

### 12.3 Integration

The ambient filter is applied in the FFmpeg pipeline between the neural reenactment output and the v4l2loopback device:

```
LivePortrait output → Named pipe → ffmpeg [ambient_filter + noise + compression] → /dev/video2
```

---

> **Full Technical Reference:** See [`docs/TITAN_OS_TECHNICAL_REPORT.md`](TITAN_OS_TECHNICAL_REPORT.md) — Section 12 (KYC Deep Dive) for complete documentation.

**End of KYC Controller Deep Dive** | **TITAN V7.0.3 SINGULARITY**

