# 07 — App: KYC Studio

## Overview

**File:** `src/apps/app_kyc.py`
**Color Theme:** Purple (#9c27b0)
**Tabs:** 4
**Modules Wired:** 10
**Purpose:** Virtual camera control, document injection, mobile device sync, and voice verification for KYC (Know Your Customer) challenges.

The KYC Studio handles identity verification challenges that require camera feeds, document uploads, liveness detection responses, and voice verification. It streams an animated face to any application requesting webcam access — not just the browser, but also Zoom, Telegram, or native apps.

---

## Tab 1: CAMERA — Virtual Camera & Face Reenactment

### What This Tab Does
The operator loads a face image, selects a motion type, adjusts animation parameters, and streams the animated face to a virtual camera device.

### Layout
```
┌─────────────────────────────────────────────────────────┐
│  VERIFICATION COMPLIANCE MODULE                          │
├──────────────────────┬──────────────────────────────────┤
│                      │ KYC Provider: [Onfido ▼]         │
│   [Face Image]       │ Motion: [Blink Twice ▼]          │
│                      │                                  │
│                      │ Head Rotation: ────●──────        │
│   [Load Image]       │ Expression:    ──────●────        │
│                      │ Blink Freq:    ────●──────        │
│                      │ Micro Movement: ──●────────       │
├──────────────────────┴──────────────────────────────────┤
│  Camera: /dev/video2 (Integrated Webcam)                 │
│  Status: STREAMING                                       │
│  [ START STREAM ]  [ STOP ]  [ Preview ]                │
│  Available Cameras:                                      │
│  • /dev/video0 - Real Webcam                            │
│  • /dev/video2 - Integrated Webcam (Virtual) ✓          │
└─────────────────────────────────────────────────────────┘
```

### Features

**Source Image Loading**
- "Load Image" button opens file picker for face photo (JPG/PNG)
- Image preview panel (250x300px) shows loaded face
- Supports: ID photos, generated faces, passport scans
- Image is used as the base for all face reenactment

**KYC Provider Selection**
- Dropdown with 8 supported providers:
  - Onfido, Jumio, Veriff, Sumsub, Persona, Stripe Identity, Plaid IDV, Au10tix
- Each provider has different liveness challenge sequences
- Selection configures timing and motion parameters for that provider

**Motion Type Selection**
- Dropdown populated from `KYCController.get_available_motions()`:
  - **Blink Twice** — natural double blink
  - **Smile** — gradual smile with cheek movement
  - **Head Turn Left/Right** — smooth head rotation
  - **Nod** — up/down head movement
  - **Eyebrow Raise** — subtle eyebrow lift
- Each motion has description and recommended parameters

**Fine-Tune Sliders**
- **Head Rotation** (0-2.0x): Controls amplitude of head movements. Default 1.0x.
- **Expression Intensity** (0-2.0x): How pronounced facial expressions are. Default 1.0x.
- **Blink Frequency** (0-2.0x): How often the face blinks. Default 1.0x.
- **Micro Movement** (0-2.0x): Subtle involuntary face movements that add realism.

**Camera Control**
- Camera device selector showing all `/dev/video*` devices
- v4l2loopback virtual camera automatically detected
- "Start Stream" → `StreamWorker` background thread starts reenactment
- "Stop" → stops streaming, releases camera device
- "Preview" → shows current camera output in UI
- Status indicator: IDLE → STREAMING → STOPPED

**Background Worker**
- `StreamWorker(QThread)` handles camera streaming without blocking UI
- Sets up virtual camera via `KYCController.setup_virtual_camera()`
- Starts reenactment via `KYCController.start_reenactment(config)`
- Emits `state_changed` and `error` signals for UI updates

### What the Operator Inputs
| Input | Description | Example |
|-------|-------------|---------|
| Face Image | Photo of the face to animate | `/path/to/face.jpg` |
| KYC Provider | Target verification platform | "Veriff" |
| Motion Type | Liveness challenge motion | "Blink Twice" |
| Head Rotation | Movement amplitude | 1.0x |
| Expression | Expression intensity | 0.8x |
| Blink Rate | Blink frequency | 1.2x |

### What the Operator Gets
| Output | Description |
|--------|-------------|
| Live Camera Stream | Animated face on `/dev/video2` |
| Camera Status | STREAMING / IDLE / ERROR |
| Preview | Real-time view of camera output |

---

## Tab 2: DOCUMENTS — Document Injection & Provider Intelligence

### What This Tab Does
Manages document assets (ID cards, passports, driver's licenses) and provides provider-specific intelligence for document verification challenges.

### Features

**Document Asset Management**
- Upload document images (front, back)
- Document type selector: Passport, Driver's License, National ID, Utility Bill
- `DocumentAsset` metadata: document type, country, expiration date

**Provider Intelligence**
- `KYC_PROVIDER_PROFILES` database shows per-provider requirements:
  - Which document types each provider accepts
  - Photo quality requirements (resolution, lighting, glare)
  - MRZ (Machine Readable Zone) requirements for passports
  - Barcode/chip reading requirements
  - Liveness challenge sequences after document submission

**Enhanced KYC Session**
- `KYCEnhancedController.create_session(provider, config)` — optimized session
- `KYCSessionConfig` — provider-tuned parameters
- Automatic timing adjustment for each provider's expected user behavior
- Challenge prediction: what the provider will ask next

**Deep Identity Verification**
- `DeepIdentityVerifier` — analyzes verification system vulnerabilities
- `IdentityConfig` — identity document details
- Cross-reference vulnerability analysis
- Provider-specific bypass strategies

**ToF Depth Synthesis**
- `ToFDepthSynthesizer` — generates 3D depth maps from 2D face photos
- Defeats structured light / Time-of-Flight liveness cameras
- `generate_depth_map(face_image, sensor)` — sensor-specific depth
- `synthesize_ir_pattern()` — creates IR dot projection pattern
- Sensor profiles: Apple TrueDepth, Intel RealSense, Microsoft Kinect

### What the Operator Inputs
| Input | Description | Example |
|-------|-------------|---------|
| Document Image | ID/passport photo | `/path/to/passport.jpg` |
| Document Type | Type of document | "Passport" |
| Country | Issuing country | "United States" |
| Provider | KYC platform | "Onfido" |

### What the Operator Gets
| Output | Description |
|--------|-------------|
| Provider Profile | Requirements and challenge sequence |
| Depth Map | 3D depth data matching face geometry |
| IR Pattern | Infrared dot projection for liveness |
| Session Config | Optimized timing for selected provider |

---

## Tab 3: MOBILE SYNC — Waydroid Android Emulation

### What This Tab Does
Manages mobile device sync for KYC flows that require a mobile app (banking apps, authenticator apps, SMS verification).

### Features

**Waydroid Integration**
- `WaydroidSyncEngine` manages Android emulator running on Linux
- Waydroid runs full Android in a container using the Linux kernel
- Provides mobile browser and native app capabilities

**Mobile Persona**
- `MobilePersona` — mobile device identity configuration
- Device model (Samsung Galaxy S23, iPhone 15 via user-agent)
- Android version, screen resolution
- IMEI, carrier information

**Session Sync**
- Syncs KYC verification state between desktop browser and mobile
- Transfers session cookies and tokens
- Handles SMS code forwarding
- 2FA authenticator code generation

**Sync Configuration**
- `SyncConfig` — parameters for desktop-mobile sync
- Bluetooth pairing emulation
- WiFi Direct simulation
- QR code session transfer

### What the Operator Inputs
| Input | Description | Example |
|-------|-------------|---------|
| Device Model | Mobile device to emulate | "Samsung Galaxy S23" |
| Android Version | OS version | "14" |
| Carrier | Mobile carrier | "T-Mobile" |

### What the Operator Gets
| Output | Description |
|--------|-------------|
| Android Instance | Running Waydroid container |
| Sync Status | Desktop ↔ Mobile sync active |
| SMS Forwarding | Incoming verification codes |

---

## Tab 4: VOICE — Speech Synthesis & Video Recording

### What This Tab Does
Handles voice verification challenges where the KYC provider requires the user to speak a phrase.

### Features

**Voice Synthesis**
- `KYCVoiceEngine.synthesize(text, voice_profile)` — generates natural speech
- Text input field for the required phrase
- Real-time audio preview before streaming

**Voice Profile Configuration**
- `VoiceProfile` settings:
  - Gender: Male / Female
  - Accent: American, British, Australian, etc.
  - Speaking rate: Slow / Normal / Fast
  - Pitch: Low / Medium / High
- Profile should match the persona's demographics

**Lip-Sync Video**
- `SpeechVideoConfig` — combines voice with face animation
- Generates video where lip movements match the spoken words
- Output to virtual camera simultaneously with audio
- Synchronized audio + video stream

**AI Behavioral Modeling**
- `CognitiveEngine` / `BehaviorProfile` from `cognitive_core.py`
- Models natural speaking behavior (pauses, um/uh, breathing)
- Adjusts speaking pattern to match persona age and background
- `get_forter_safe_params()` — ensures behavioral patterns pass checks

### What the Operator Inputs
| Input | Description | Example |
|-------|-------------|---------|
| Spoken Text | Phrase to speak | "Seven three nine" |
| Voice Gender | Male or female | "Male" |
| Accent | Regional accent | "American" |
| Speaking Rate | Speed of speech | "Normal" |

### What the Operator Gets
| Output | Description |
|--------|-------------|
| Audio Stream | Natural speech output |
| Video Stream | Lip-synced face animation |
| Combined Output | Audio + video on virtual camera |

---

## Module Wiring Summary

| Tab | Modules Used |
|-----|-------------|
| CAMERA | kyc_core (KYCController, ReenactmentConfig, VirtualCameraConfig, IntegrityShield) |
| DOCUMENTS | kyc_enhanced, verify_deep_identity, tof_depth_synthesis |
| MOBILE SYNC | waydroid_sync |
| VOICE | kyc_voice_engine, cognitive_core, ghost_motor_v6, ai_intelligence_engine |

**Total: 10 modules wired into KYC Studio**

---

*Next: [08 — App: Admin Panel](08_APP_ADMIN_PANEL.md)*
