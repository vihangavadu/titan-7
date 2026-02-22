# Browser Fingerprint Evasion — Canvas, WebGL, Audio, Font & TLS Techniques

## Core Modules: `fingerprint_injector.py`, `webgl_angle.py`, `canvas_noise.py`, `font_sanitizer.py`, `audio_hardener.py`, `tls_parrot.py`

Browser fingerprinting is the primary method antifraud systems use to track users across sessions without cookies. TITAN defeats every known fingerprinting vector.

---

## What Is Browser Fingerprinting?

Every browser exposes dozens of measurable properties that, combined, create a unique identifier:

```
Canvas hash + WebGL renderer + Audio hash + Font list + Screen resolution +
Timezone + Language + Platform + CPU cores + RAM + GPU + Touch support +
WebRTC IPs + Battery API + Sensor APIs = UNIQUE FINGERPRINT
```

Services like FingerprintJS, ThreatMetrix, and Forter compute this fingerprint and compare it against known fraud databases. If your fingerprint matches a previously flagged session, you're blocked instantly.

---

## 1. Canvas Fingerprint (`fingerprint_injector.py`, `canvas_noise.py`)

### How Canvas Fingerprinting Works

The website draws invisible shapes/text on an HTML5 Canvas element, then reads back the pixel data. Due to differences in GPU, driver, font rendering, and anti-aliasing, every system produces a slightly different image → different hash.

```javascript
// What the antifraud script does:
const canvas = document.createElement('canvas');
const ctx = canvas.getContext('2d');
ctx.fillText('Browser fingerprint test', 10, 50);
const hash = canvas.toDataURL().hashCode(); // Unique per system
```

### TITAN's Canvas Defense

**Technique: Deterministic Noise Injection**

```python
class FingerprintInjector:
    def generate_canvas_config(self) -> Dict[str, Any]:
        """
        Generates canvas noise parameters seeded from profile UUID.
        
        Key principle: SAME profile → SAME canvas hash (consistency)
                       DIFFERENT profile → DIFFERENT canvas hash (uniqueness)
        
        This is critical because antifraud systems check if the canvas
        hash changes between sessions. If it changes, the device is
        flagged as using anti-fingerprint tools.
        """
        seed = int.from_bytes(self.profile_uuid.encode()[:8], 'big')
        rng = random.Random(seed)
        
        return {
            "noise_r": rng.uniform(-0.01, 0.01),  # Red channel noise
            "noise_g": rng.uniform(-0.01, 0.01),  # Green channel noise
            "noise_b": rng.uniform(-0.01, 0.01),  # Blue channel noise
            "noise_a": rng.uniform(-0.005, 0.005), # Alpha channel noise
        }
```

The noise is injected at the pixel level when `canvas.toDataURL()` is called. The noise values are deterministic — the same profile UUID always produces the same canvas hash, but different profiles produce different hashes. This mimics real hardware variation.

### Why Random Noise Fails

Many anti-fingerprint tools add random noise to canvas. This is detectable because:
1. The hash changes on every page load (real hardware produces consistent hashes)
2. The noise pattern doesn't match any real GPU's rendering characteristics
3. Statistical analysis reveals artificial noise distribution

TITAN's deterministic approach avoids all three detection vectors.

---

## 2. WebGL Fingerprint (`webgl_angle.py`)

### How WebGL Fingerprinting Works

WebGL exposes GPU information through:
- `WEBGL_debug_renderer_info` extension → GPU vendor and model
- Shader precision formats → GPU capability fingerprint
- Rendered 3D scene hash → GPU-specific rendering differences

```javascript
const gl = canvas.getContext('webgl');
const ext = gl.getExtension('WEBGL_debug_renderer_info');
const vendor = gl.getParameter(ext.UNMASKED_VENDOR_WEBGL);   // "Google Inc. (Intel)"
const renderer = gl.getParameter(ext.UNMASKED_RENDERER_WEBGL); // "ANGLE (Intel, Intel(R) UHD Graphics 630)"
```

### TITAN's WebGL Defense

**Technique: ANGLE Shim with Generic GPU Profile**

```python
class WebGLAngleShim:
    """
    Presents a standardized GPU profile through ANGLE (Almost Native Graphics Layer Engine).
    
    ANGLE is Google's OpenGL-to-DirectX translation layer used by Chrome on Windows.
    By reporting an ANGLE renderer, we:
    1. Hide the real GPU (which may be a virtual GPU revealing VPS)
    2. Present a common consumer GPU that matches millions of real users
    3. Maintain consistency with the hardware profile
    """
    
    GPU_PROFILES = {
        "intel_uhd_630": {
            "vendor": "Google Inc. (Intel)",
            "renderer": "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "shader_precision": {"vertex": 23, "fragment": 23},
        },
        "intel_iris_xe": {
            "vendor": "Google Inc. (Intel)",
            "renderer": "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)",
        },
        "nvidia_rtx_3060": {
            "vendor": "Google Inc. (NVIDIA)",
            "renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        },
    }
```

The GPU profile is selected to match the hardware profile's CPU generation (e.g., 13th Gen Intel CPU → Intel UHD 770 GPU).

---

## 3. Audio Fingerprint (`audio_hardener.py`)

### How Audio Fingerprinting Works

The AudioContext API creates an oscillator, processes it through compressor/analyzer nodes, and reads the output. Due to differences in audio hardware and drivers, the output varies per system.

```javascript
const ctx = new AudioContext();
const oscillator = ctx.createOscillator();
const analyser = ctx.createAnalyser();
oscillator.connect(analyser);
// Read frequency data → unique hash per audio stack
```

### TITAN's Audio Defense

```python
class AudioHardener:
    """
    Masks the Linux audio stack (PulseAudio/PipeWire) to present
    Windows-consistent AudioContext output.
    
    Key parameters spoofed:
    - Sample rate: 44100 Hz (Windows default vs Linux's 48000 Hz)
    - Channel count: 2 (stereo)
    - Max channel count: 2
    - Base latency: 0.01 (Windows WASAPI typical)
    - Output latency: 0.02
    """
    
    WINDOWS_AUDIO_PROFILE = {
        "sample_rate": 44100,
        "channel_count": 2,
        "max_channel_count": 2,
        "base_latency": 0.01,
        "output_latency": 0.02,
        "state": "running",
    }
```

Additionally, the audio output is modified with profile-specific noise (same deterministic seeding as canvas) to produce a unique but consistent audio fingerprint.

---

## 4. Font Enumeration Defense (`font_sanitizer.py`)

### How Font Fingerprinting Works

Websites measure the rendered width of text in various fonts. If a font is installed, the text renders at a specific width; if not, it falls back to a default font with a different width. By testing hundreds of fonts, the site determines which fonts are installed → OS identification.

**Linux-specific fonts that leak OS identity:**
- Liberation Sans/Serif/Mono
- DejaVu Sans/Serif/Mono
- Noto Sans/Serif
- Ubuntu (font family)
- Cantarell
- Droid Sans
- FreeSans/FreeSerif

If ANY of these fonts are detected, the site knows you're on Linux (not Windows).

### TITAN's Font Defense

**Technique: fontconfig rejectfont + Windows font substitution**

```xml
<!-- /etc/fonts/local.conf -->
<fontconfig>
  <!-- Reject ALL Linux-specific font families -->
  <rejectfont>
    <glob>/usr/share/fonts/truetype/liberation/*</glob>
    <glob>/usr/share/fonts/truetype/dejavu/*</glob>
    <glob>/usr/share/fonts/truetype/noto/*</glob>
    <glob>/usr/share/fonts/truetype/ubuntu/*</glob>
    <glob>/usr/share/fonts/truetype/droid/*</glob>
    <glob>/usr/share/fonts/truetype/freefont/*</glob>
  </rejectfont>
  
  <!-- Substitute with Windows equivalents -->
  <alias>
    <family>Liberation Sans</family>
    <prefer><family>Arial</family></prefer>
  </alias>
  <alias>
    <family>Liberation Serif</family>
    <prefer><family>Times New Roman</family></prefer>
  </alias>
</fontconfig>
```

**Verification**: `fc-list` shows 0 Linux-specific fonts. Browser font enumeration sees only Windows-compatible fonts.

---

## 5. TLS Fingerprint Parroting (`tls_parrot.py`)

### How TLS Fingerprinting Works (JA3/JA4)

When a browser establishes an HTTPS connection, the TLS ClientHello message contains:
- Supported cipher suites (in specific order)
- TLS extensions (in specific order)
- Supported groups (elliptic curves)
- Signature algorithms

The **JA3 hash** is an MD5 of these parameters. Every browser version produces a unique JA3 hash. A Linux Firefox has a different JA3 than Windows Firefox, even at the same version.

### TITAN's TLS Defense

**Technique: Camoufox TLS parroting**

Camoufox (the hardened Firefox fork) is compiled with a modified TLS stack that exactly replicates the ClientHello of Chrome on Windows 11:

```
JA3 target: Chrome 120 on Windows 11
Cipher suites: TLS_AES_128_GCM_SHA256, TLS_AES_256_GCM_SHA384, TLS_CHACHA20_POLY1305_SHA256, ...
Extensions: server_name, extended_master_secret, renegotiation_info, ...
ALPN: h2, http/1.1
```

This means network-level observers (CDN, WAF, antifraud) see a TLS fingerprint identical to millions of real Chrome users on Windows.

### JA4 (Next-Generation TLS Fingerprint)

JA4 adds:
- TLS version
- SNI presence
- Number of cipher suites
- Number of extensions
- ALPN protocol
- Signature algorithms hash

TITAN's Camoufox also matches JA4 fingerprints for the target browser profile.

---

## 6. Camoufox Browser

Camoufox is the browser that ties all fingerprint defenses together. It's a Firefox fork with:

- **No `navigator.webdriver`**: The #1 bot detection flag is removed at compile time
- **Spoofed `navigator` properties**: `platform`, `oscpu`, `userAgent`, `hardwareConcurrency`, `deviceMemory`
- **Canvas noise injection**: Built-in deterministic noise
- **WebGL ANGLE reporting**: Reports configured GPU profile
- **Font restriction**: Respects fontconfig rejectfont rules
- **Audio spoofing**: Modified AudioContext output
- **WebRTC protection**: Prevents IP leak through WebRTC
- **Timezone override**: JavaScript `Date` and `Intl` APIs match configured timezone
- **Language/locale override**: `navigator.language`, `navigator.languages`, `Accept-Language` header

### Camoufox vs Antidetect Browsers

| Feature | Camoufox | Multilogin | GoLogin | Dolphin |
|---------|----------|------------|---------|---------|
| Open source | Yes | No | No | No |
| Fingerprint consistency | Deterministic | Random per session | Random | Semi-random |
| TLS parroting | Yes (JA3/JA4) | Partial | No | Partial |
| Font sanitization | OS-level | Browser-level | Browser-level | Browser-level |
| Kernel integration | Yes (HW shield) | No | No | No |
| Cost | Free | $99/mo | $49/mo | $89/mo |
