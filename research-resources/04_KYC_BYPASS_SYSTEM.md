# KYC Bypass System — Virtual Camera, Document Injection & Liveness Evasion

## Core Modules: `kyc_core.py` (620 lines), `kyc_enhanced.py`

KYC (Know Your Customer) verification is the process where platforms verify a user's identity through document photos and live selfies. TITAN's KYC system defeats this using virtual cameras, neural face reenactment, and provider-specific bypass strategies.

---

## How KYC Verification Works (What We're Defeating)

1. **Document capture**: User holds ID document in front of camera → platform reads text via OCR
2. **Selfie capture**: User takes a live selfie → platform compares face to document photo
3. **Liveness detection**: User performs actions (blink, smile, turn head) → proves they're not a photo
4. **3D depth check**: Some providers use depth sensors to detect flat images vs real faces

### Major KYC Providers and Their Techniques

| Provider | Document Flow | Liveness | Virtual Camera Detection | Difficulty |
|----------|--------------|----------|------------------------|------------|
| **Jumio** | Front → Back → Selfie | Blink, Smile | Yes (checks device list) | Hard |
| **Onfido** | Front → Selfie → Video | Head turn, Speech | Moderate | Medium |
| **Veriff** | Front → Back → Live video | Multiple gestures | Yes (WebRTC checks) | Hard |
| **Sumsub** | Front → Selfie | Blink | Minimal | Easy |
| **Persona** | Front → Back → Selfie | Hold still | No | Easy |
| **Stripe Identity** | Front → Selfie | Blink | Moderate | Medium |
| **Plaid IDV** | Front → Selfie | None | No | Easy |
| **Au10tix** | Front → Back → Selfie → Video | 3D depth, Gestures | Yes | Extreme |

---

## TITAN's KYC Architecture

### Layer 1: Virtual Camera (`v4l2loopback`)

**Technique**: Linux kernel module `v4l2loopback` creates a virtual video device (`/dev/video2`) that appears as a real webcam to any application. FFmpeg pipes video content to this device.

```
Source Image/Video → FFmpeg → v4l2loopback → /dev/video2 → Browser WebRTC → KYC Provider
```

**Setup**:
```bash
modprobe v4l2loopback devices=1 video_nr=2 card_label='Integrated Camera' exclusive_caps=1
```

The virtual camera appears as "Integrated Camera" — matching common laptop webcam names. KYC providers that check the device name see a normal webcam.

### Layer 2: Document Injection

For the document capture phase, TITAN streams a static image of the ID document to the virtual camera:

```python
def stream_image(self, image_path: str) -> bool:
    cmd = [
        "ffmpeg",
        "-loop", "1",        # Loop single image
        "-re",               # Real-time rate
        "-i", image_path,    # Source document image
        "-vf", f"scale={width}:{height}",
        "-f", "v4l2",
        "-pix_fmt", "yuv420p",
        "-r", "30",          # 30 FPS
        "/dev/video2"        # Virtual camera device
    ]
```

The document image is pre-processed to:
- Match expected resolution (1280x720 or 1920x1080)
- Add subtle camera noise (real cameras have noise)
- Apply slight perspective distortion (hand-held angle)
- Add realistic lighting variation

### Layer 3: Neural Face Reenactment

For the selfie/liveness phase, TITAN uses **LivePortrait** or similar neural reenactment models to animate a static face photo:

```python
def start_reenactment(self, config: ReenactmentConfig) -> bool:
    """
    Animate a static face image with:
    1. Source image (ID photo or face photo)
    2. Motion driving video (pre-recorded head movements)
    3. Output to virtual camera at 30 FPS
    
    GUI sliders control:
    - Head rotation intensity (0.0-1.0)
    - Expression intensity (0.0-1.0)
    - Blink frequency (natural: every 3-5 seconds)
    - Micro-movements (subtle head sway)
    """
```

**How reenactment works**:
1. Extract facial landmarks from source image (68-point mesh)
2. Extract motion parameters from driving video (rotation, expression, gaze)
3. Apply motion to source face using neural warping network
4. Render output frame at 30 FPS
5. Pipe to virtual camera via FFmpeg

### Layer 4: Liveness Challenge Response

When the KYC provider asks the user to perform specific actions, TITAN responds with pre-mapped motions:

| Challenge | Motion Type | Implementation |
|-----------|------------|----------------|
| "Hold still" | Neutral with micro-sway | Minimal head movement, natural breathing motion |
| "Blink" | Single blink | Eyelid close/open over 200ms |
| "Blink twice" | Double blink | Two blinks with 500ms gap |
| "Smile" | Mouth corners up | Expression blend from neutral to smile |
| "Turn left" | Head yaw -30° | Smooth rotation over 1 second |
| "Turn right" | Head yaw +30° | Smooth rotation over 1 second |
| "Nod yes" | Head pitch oscillation | Up-down motion, 2 cycles |
| "Look up" | Head pitch +20° | Smooth upward tilt |
| "Look down" | Head pitch -20° | Smooth downward tilt |

### Layer 5: Provider-Specific Profiles

Each KYC provider has a detailed bypass profile stored in `KYC_PROVIDER_PROFILES`:

```python
KYC_PROVIDER_PROFILES = {
    KYCProvider.JUMIO: {
        "name": "Jumio",
        "document_flow": ["front", "back", "selfie"],
        "liveness_challenges": [LivenessChallenge.BLINK, LivenessChallenge.SMILE],
        "checks_virtual_camera": True,
        "uses_3d_depth": False,
        "bypass_difficulty": "hard",
        "notes": "Checks USB device list for virtual cameras. Use v4l2loopback with realistic device name."
    },
    # ... profiles for all 8 providers
}
```

---

## Document Asset Preparation

### Required Assets Per Operation

| Asset | Format | Resolution | Notes |
|-------|--------|-----------|-------|
| ID Front | JPEG/PNG | 1280x720+ | Clear, well-lit, slight angle |
| ID Back | JPEG/PNG | 1280x720+ | Same lighting as front |
| Face Photo | JPEG/PNG | 512x512+ | Neutral expression, front-facing |
| Driving Video | MP4 | 512x512 | Pre-recorded head movements |

### Image Processing Pipeline

1. **Noise injection**: Add camera sensor noise (Gaussian, σ=2-5)
2. **JPEG artifacts**: Compress to 85% quality (real camera output)
3. **Lighting normalization**: Match ambient lighting across document and selfie
4. **Perspective warp**: Slight 3D rotation to simulate hand-held capture
5. **Resolution matching**: Scale to provider's expected input resolution

---

## Waydroid Mobile Sync

### Module: `waydroid_sync.py`

Some KYC providers require mobile verification. TITAN integrates with **Waydroid** (Android container on Linux) to:

1. **Run Android apps**: Chrome Mobile, banking apps, verification apps
2. **Sync cookies**: Desktop browser cookies → mobile Chrome
3. **Mobile persona**: Realistic device model, Android version, IMEI
4. **Background activity**: Simulate app opens, notifications, browsing

### Mobile Persona Configuration

```python
@dataclass
class MobilePersona:
    device_model: str      # "Pixel 7", "Samsung Galaxy S24"
    android_version: str   # "14", "13"
    locale: str           # "en_US"
    carrier: str          # "T-Mobile", "Verizon"
    imei: str             # Generated valid IMEI
    build_fingerprint: str # Matches real device
```

---

## GUI: KYC App (`app_kyc.py` — 1172 lines, 3 tabs)

### Tab 1: Camera
- Virtual camera setup and status
- Source image loading (face photo)
- Reenactment controls (intensity sliders)
- Motion type selection (neutral, blink, smile, etc.)
- Stream start/stop
- Camera device list

### Tab 2: Documents
- KYC provider selection (8 providers with intelligence profiles)
- Provider info display (document flow, challenges, difficulty)
- Document asset loading (front, back, face)
- Document injection buttons
- Selfie feed activation
- Full session creation
- Liveness challenge response buttons (9 challenges)

### Tab 3: Mobile Sync
- Waydroid Android container initialization
- Mobile persona configuration (device, Android version, locale)
- Target app selection (Chrome, Gmail, Maps, Amazon, etc.)
- Cookie sync (desktop → mobile)
- Background activity generation
