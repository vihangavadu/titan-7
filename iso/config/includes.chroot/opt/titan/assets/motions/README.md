# KYC Motion Assets

This directory contains motion driving videos for the KYC neural reenactment engine.

## Required Files

Place the following motion video files here for liveness challenge bypass:

| Filename | Description | Duration |
|----------|-------------|----------|
| `neutral.mp4` | Subtle idle movement, natural breathing | 10s loop |
| `blink.mp4` | Single natural eye blink | 2s |
| `blink_twice.mp4` | Two consecutive blinks | 3s |
| `smile.mp4` | Natural smile expression | 3s |
| `head_left.mp4` | Turn head left | 3s |
| `head_right.mp4` | Turn head right | 3s |
| `head_nod.mp4` | Nod head up and down | 3s |
| `look_up.mp4` | Look upward | 2s |
| `look_down.mp4` | Look downward | 2s |

## Video Specifications

- **Resolution:** 512x512 or 1024x1024 (square)
- **Format:** MP4 (H.264)
- **FPS:** 30
- **Background:** Neutral, well-lit
- **Subject:** Front-facing, centered

## Alternative: LivePortrait Motion Data

If using LivePortrait model, you can also use `.pkl` motion data files:
- `neutral.pkl`
- `blink.pkl`
- etc.

## Generating Motion Videos

Motion videos should be recorded from a real person performing the actions naturally.
Alternatively, use AI-generated motion data from LivePortrait or similar models.

## Usage

The KYC module (`kyc_core.py`) will automatically load these assets when performing
neural reenactment for liveness challenges.

```python
from kyc_core import KYCController, ReenactmentConfig, MotionType

controller = KYCController()
controller.setup_virtual_camera()

config = ReenactmentConfig(
    source_image="/path/to/id_photo.jpg",
    motion_type=MotionType.BLINK_TWICE
)
controller.start_reenactment(config)
```
