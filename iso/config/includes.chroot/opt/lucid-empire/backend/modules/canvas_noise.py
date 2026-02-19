#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  LUCID EMPIRE v7.0.0-TITAN :: CONSISTENT CANVAS NOISE MODULE                 ║
║  Deterministic Perlin Noise for Canvas Fingerprint Obfuscation               ║
║  Authority: Dva.12 | Classification: ZERO DETECT                             ║
╚══════════════════════════════════════════════════════════════════════════════╝

Implements deterministic canvas noise injection using Perlin noise algorithms.
Same profile seed = Same canvas hash across sessions (consistency is key).

Technical approach:
1. Use profile UUID as seed for PRNG
2. Generate Perlin noise grid for canvas operations
3. Apply sub-pixel modifications to canvas data
4. Ensure same seed produces identical visual output
"""

import hashlib
import math
import struct
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
import json
from pathlib import Path


class PerlinNoise:
    """
    Perlin noise generator with deterministic seeding.
    
    Used to generate consistent pseudo-random noise patterns
    that are reproducible across sessions with the same seed.
    """
    
    def __init__(self, seed: int = 0):
        """Initialize with deterministic seed"""
        self.seed = seed
        self.p = self._generate_permutation()
        
    def _generate_permutation(self) -> List[int]:
        """Generate permutation table from seed"""
        import random
        rng = random.Random(self.seed)
        
        p = list(range(256))
        rng.shuffle(p)
        
        # Duplicate for overflow
        return p + p
    
    def _fade(self, t: float) -> float:
        """Fade function for smooth interpolation"""
        return t * t * t * (t * (t * 6 - 15) + 10)
    
    def _lerp(self, a: float, b: float, t: float) -> float:
        """Linear interpolation"""
        return a + t * (b - a)
    
    def _grad(self, hash_val: int, x: float, y: float) -> float:
        """Gradient function"""
        h = hash_val & 3
        if h == 0:
            return x + y
        elif h == 1:
            return -x + y
        elif h == 2:
            return x - y
        else:
            return -x - y
    
    def noise2d(self, x: float, y: float) -> float:
        """
        Generate 2D Perlin noise value
        
        Returns value in range [-1, 1]
        """
        # Unit square coordinates
        xi = int(x) & 255
        yi = int(y) & 255
        
        # Relative coordinates in unit square
        xf = x - int(x)
        yf = y - int(y)
        
        # Fade curves
        u = self._fade(xf)
        v = self._fade(yf)
        
        # Hash coordinates
        aa = self.p[self.p[xi] + yi]
        ab = self.p[self.p[xi] + yi + 1]
        ba = self.p[self.p[xi + 1] + yi]
        bb = self.p[self.p[xi + 1] + yi + 1]
        
        # Blend results
        x1 = self._lerp(self._grad(aa, xf, yf), self._grad(ba, xf - 1, yf), u)
        x2 = self._lerp(self._grad(ab, xf, yf - 1), self._grad(bb, xf - 1, yf - 1), u)
        
        return self._lerp(x1, x2, v)
    
    def octave_noise(
        self, 
        x: float, 
        y: float, 
        octaves: int = 4, 
        persistence: float = 0.5
    ) -> float:
        """
        Generate multi-octave Perlin noise for more natural patterns
        """
        total = 0.0
        frequency = 1.0
        amplitude = 1.0
        max_value = 0.0
        
        for _ in range(octaves):
            total += self.noise2d(x * frequency, y * frequency) * amplitude
            max_value += amplitude
            amplitude *= persistence
            frequency *= 2
        
        return total / max_value


@dataclass
class CanvasNoiseConfig:
    """Configuration for canvas noise injection"""
    
    # Profile seed (derived from UUID)
    seed: int
    
    # Noise parameters
    noise_scale: float = 0.05  # Scale of noise pattern
    noise_intensity: float = 1.0  # Max pixel modification (sub-pixel, ≤1)
    octaves: int = 3
    persistence: float = 0.5
    
    # Apply to specific channels
    affect_red: bool = True
    affect_green: bool = True
    affect_blue: bool = True
    affect_alpha: bool = False  # Usually don't touch alpha
    
    # Coordinate offsets for variety
    x_offset: float = 0.0
    y_offset: float = 0.0
    
    @classmethod
    def from_profile_uuid(cls, uuid_str: str) -> 'CanvasNoiseConfig':
        """Create config from profile UUID"""
        # Generate deterministic seed from UUID
        hash_bytes = hashlib.sha256(uuid_str.encode()).digest()
        seed = struct.unpack('<Q', hash_bytes[:8])[0]
        
        # Use more hash bytes for offsets
        x_offset = struct.unpack('<f', hash_bytes[8:12])[0] % 1000
        y_offset = struct.unpack('<f', hash_bytes[12:16])[0] % 1000
        
        return cls(
            seed=seed,
            x_offset=x_offset,
            y_offset=y_offset
        )


class CanvasNoiseInjector:
    """
    Injects deterministic Perlin noise into canvas image data.
    
    Used to:
    1. Defeat canvas fingerprinting while maintaining consistency
    2. Generate unique but reproducible canvas hashes per profile
    3. Appear as natural sensor noise rather than artificial modification
    """
    
    def __init__(self, config: CanvasNoiseConfig):
        self.config = config
        self.noise_gen = PerlinNoise(config.seed)
        
    def get_pixel_modification(self, x: int, y: int) -> Tuple[float, float, float, float]:
        """
        Get RGBA modification values for a pixel position.
        
        Returns:
            (dr, dg, db, da) - modifications in range [-intensity, +intensity]
        """
        # Apply offsets for profile variety
        nx = (x + self.config.x_offset) * self.config.noise_scale
        ny = (y + self.config.y_offset) * self.config.noise_scale
        
        # Generate base noise
        base_noise = self.noise_gen.octave_noise(
            nx, ny, 
            self.config.octaves, 
            self.config.persistence
        )
        
        # Scale to intensity
        modification = base_noise * self.config.noise_intensity
        
        # Apply per-channel
        dr = modification if self.config.affect_red else 0.0
        dg = modification if self.config.affect_green else 0.0
        db = modification if self.config.affect_blue else 0.0
        da = modification if self.config.affect_alpha else 0.0
        
        # Vary each channel slightly using position-based offsets
        if self.config.affect_red:
            dr *= self.noise_gen.noise2d(nx + 100, ny) * 0.5 + 0.75
        if self.config.affect_green:
            dg *= self.noise_gen.noise2d(nx, ny + 100) * 0.5 + 0.75
        if self.config.affect_blue:
            db *= self.noise_gen.noise2d(nx + 50, ny + 50) * 0.5 + 0.75
        
        return (dr, dg, db, da)
    
    def modify_image_data(
        self, 
        data: List[int], 
        width: int, 
        height: int
    ) -> List[int]:
        """
        Modify canvas ImageData array with deterministic noise.
        
        Args:
            data: Flat RGBA array [r,g,b,a,r,g,b,a,...]
            width: Canvas width
            height: Canvas height
            
        Returns:
            Modified RGBA array
        """
        result = list(data)
        
        for y in range(height):
            for x in range(width):
                idx = (y * width + x) * 4
                
                dr, dg, db, da = self.get_pixel_modification(x, y)
                
                # Apply modifications with clamping
                result[idx] = max(0, min(255, int(result[idx] + dr)))
                result[idx + 1] = max(0, min(255, int(result[idx + 1] + dg)))
                result[idx + 2] = max(0, min(255, int(result[idx + 2] + db)))
                result[idx + 3] = max(0, min(255, int(result[idx + 3] + da)))
        
        return result
    
    def generate_noise_map(self, width: int, height: int) -> List[List[float]]:
        """
        Generate a noise map for visualization/debugging.
        
        Returns:
            2D array of noise values in range [-1, 1]
        """
        noise_map = []
        for y in range(height):
            row = []
            for x in range(width):
                nx = (x + self.config.x_offset) * self.config.noise_scale
                ny = (y + self.config.y_offset) * self.config.noise_scale
                value = self.noise_gen.octave_noise(nx, ny, self.config.octaves, self.config.persistence)
                row.append(value)
            noise_map.append(row)
        return noise_map


class CanvasHashValidator:
    """
    Validates canvas hash consistency across renders.
    
    Used in pre-flight checks to ensure the same profile
    produces the same canvas fingerprint.
    """
    
    def __init__(self, injector: CanvasNoiseInjector):
        self.injector = injector
    
    def compute_canvas_hash(self, data: List[int], width: int, height: int) -> str:
        """Compute SHA-256 hash of canvas data"""
        modified = self.injector.modify_image_data(data, width, height)
        bytes_data = bytes(modified)
        return hashlib.sha256(bytes_data).hexdigest()
    
    def validate_consistency(
        self, 
        data: List[int], 
        width: int, 
        height: int, 
        iterations: int = 5
    ) -> Tuple[bool, str]:
        """
        Validate that canvas hash is consistent across multiple renders.
        
        Args:
            data: Source image data
            width: Canvas width
            height: Canvas height
            iterations: Number of render iterations to test
            
        Returns:
            (is_consistent, message)
        """
        hashes = set()
        
        for i in range(iterations):
            hash_val = self.compute_canvas_hash(data, width, height)
            hashes.add(hash_val)
        
        if len(hashes) == 1:
            return True, f"Canvas hash consistent: {list(hashes)[0][:16]}..."
        else:
            return False, f"Canvas hash inconsistent! Got {len(hashes)} different hashes"


# ═══════════════════════════════════════════════════════════════════════════════
# WEBGL NOISE MODULE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class WebGLNoiseConfig:
    """Configuration for WebGL fingerprint noise"""
    
    seed: int
    
    # Renderer/Vendor string modifications
    vendor_noise_chars: int = 2  # Number of chars to subtly modify
    renderer_noise_chars: int = 3
    
    # Parameter value noise (as percentage)
    max_texture_noise: float = 0.01  # 1% variance
    max_viewport_noise: float = 0.005
    
    # Shader precision noise
    precision_noise: bool = True
    
    @classmethod
    def from_profile_uuid(cls, uuid_str: str) -> 'WebGLNoiseConfig':
        hash_bytes = hashlib.sha256(uuid_str.encode()).digest()
        seed = struct.unpack('<Q', hash_bytes[:8])[0]
        return cls(seed=seed)


class WebGLNoiseInjector:
    """
    Injects deterministic noise into WebGL parameters.
    """
    
    # Base Chrome WebGL parameters
    CHROME_WEBGL = {
        "vendor": "Google Inc. (NVIDIA)",
        "renderer": "ANGLE (NVIDIA, NVIDIA GeForce GTX 1080 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "version": "WebGL 2.0 (OpenGL ES 3.0 Chromium)",
        "shading_language_version": "WebGL GLSL ES 3.00 (OpenGL ES GLSL ES 3.0 Chromium)",
        "max_texture_size": 16384,
        "max_viewport_dims": [32767, 32767],
        "max_vertex_attribs": 16,
        "max_vertex_uniform_vectors": 4096,
        "max_varying_vectors": 30,
        "max_fragment_uniform_vectors": 1024,
        "max_texture_image_units": 16,
        "max_combined_texture_image_units": 32,
    }
    
    def __init__(self, config: WebGLNoiseConfig):
        self.config = config
        self.rng = self._create_rng()
    
    def _create_rng(self):
        import random
        return random.Random(self.config.seed)
    
    def get_noised_parameters(self) -> Dict:
        """Get WebGL parameters with deterministic noise applied"""
        params = dict(self.CHROME_WEBGL)
        
        # Apply numeric parameter noise
        for key in ["max_texture_size", "max_vertex_attribs", "max_vertex_uniform_vectors",
                    "max_varying_vectors", "max_fragment_uniform_vectors",
                    "max_texture_image_units", "max_combined_texture_image_units"]:
            base_val = params[key]
            noise = int(base_val * self.config.max_texture_noise * self.rng.uniform(-1, 1))
            params[key] = base_val + noise
        
        return params
    
    def get_unmasked_vendor(self) -> str:
        """Get noised unmasked vendor string"""
        return self._apply_string_noise(
            self.CHROME_WEBGL["vendor"], 
            self.config.vendor_noise_chars
        )
    
    def get_unmasked_renderer(self) -> str:
        """Get noised unmasked renderer string"""
        return self._apply_string_noise(
            self.CHROME_WEBGL["renderer"],
            self.config.renderer_noise_chars
        )
    
    def _apply_string_noise(self, s: str, num_changes: int) -> str:
        """Apply subtle character noise to string"""
        chars = list(s)
        
        # Find positions of lowercase letters (least noticeable changes)
        positions = [i for i, c in enumerate(chars) if c.islower()]
        
        if len(positions) < num_changes:
            return s
        
        # Deterministically select positions
        change_positions = self.rng.sample(positions, min(num_changes, len(positions)))
        
        for pos in change_positions:
            # Subtle character shift
            c = chars[pos]
            shift = self.rng.choice([-1, 1])
            new_c = chr(max(ord('a'), min(ord('z'), ord(c) + shift)))
            chars[pos] = new_c
        
        return ''.join(chars)


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIO CONTEXT NOISE MODULE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AudioNoiseConfig:
    """Configuration for AudioContext fingerprint noise"""
    
    seed: int
    
    # Oscillator noise (in Hz, very small)
    frequency_noise: float = 0.0001
    
    # Analyser data noise
    analyser_noise: float = 0.001
    
    # Destination channel noise
    channel_noise: bool = True
    
    @classmethod
    def from_profile_uuid(cls, uuid_str: str) -> 'AudioNoiseConfig':
        hash_bytes = hashlib.sha256(uuid_str.encode()).digest()
        seed = struct.unpack('<Q', hash_bytes[:8])[0]
        return cls(seed=seed)


class AudioNoiseInjector:
    """
    Injects deterministic noise into AudioContext operations.
    """
    
    def __init__(self, config: AudioNoiseConfig):
        self.config = config
        self.noise_gen = PerlinNoise(config.seed)
    
    def get_oscillator_noise(self, frequency: float, time: float) -> float:
        """Get noise to add to oscillator frequency"""
        noise = self.noise_gen.noise2d(frequency * 0.01, time * 0.1)
        return noise * self.config.frequency_noise
    
    def modify_analyser_data(self, data: List[float], time: float) -> List[float]:
        """Modify AnalyserNode frequency/time data"""
        result = []
        for i, val in enumerate(data):
            noise = self.noise_gen.noise2d(i * 0.1, time * 0.1) * self.config.analyser_noise
            result.append(val + noise)
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# UNIFIED FINGERPRINT NOISE MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class FingerprintNoiseManager:
    """
    Unified manager for all browser fingerprint noise injection.
    
    Ensures consistent, deterministic noise across:
    - Canvas 2D
    - WebGL
    - Audio Context
    """
    
    def __init__(self, profile_uuid: str, profile_dir: Path = None):
        self.profile_uuid = profile_uuid
        self.profile_dir = profile_dir or Path("./lucid_profile_data")
        
        # Initialize all noise injectors with same profile seed
        self.canvas_config = CanvasNoiseConfig.from_profile_uuid(profile_uuid)
        self.canvas_injector = CanvasNoiseInjector(self.canvas_config)
        self.canvas_validator = CanvasHashValidator(self.canvas_injector)
        
        self.webgl_config = WebGLNoiseConfig.from_profile_uuid(profile_uuid)
        self.webgl_injector = WebGLNoiseInjector(self.webgl_config)
        
        self.audio_config = AudioNoiseConfig.from_profile_uuid(profile_uuid)
        self.audio_injector = AudioNoiseInjector(self.audio_config)
    
    def generate_config_file(self) -> Path:
        """Generate configuration file for the browser to use"""
        config = {
            "profile_uuid": self.profile_uuid,
            "canvas": {
                "seed": self.canvas_config.seed,
                "noise_scale": self.canvas_config.noise_scale,
                "noise_intensity": self.canvas_config.noise_intensity,
                "octaves": self.canvas_config.octaves,
                "x_offset": self.canvas_config.x_offset,
                "y_offset": self.canvas_config.y_offset,
            },
            "webgl": {
                "seed": self.webgl_config.seed,
                "parameters": self.webgl_injector.get_noised_parameters(),
                "unmasked_vendor": self.webgl_injector.get_unmasked_vendor(),
                "unmasked_renderer": self.webgl_injector.get_unmasked_renderer(),
            },
            "audio": {
                "seed": self.audio_config.seed,
                "frequency_noise": self.audio_config.frequency_noise,
                "analyser_noise": self.audio_config.analyser_noise,
            }
        }
        
        config_dir = self.profile_dir / self.profile_uuid
        config_dir.mkdir(parents=True, exist_ok=True)
        
        config_path = config_dir / "fingerprint_noise_config.json"
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        return config_path
    
    def validate_all(self, test_data: Dict = None) -> Dict[str, Tuple[bool, str]]:
        """
        Validate all fingerprint noise is consistent.
        
        Returns:
            Dictionary of validation results per component
        """
        results = {}
        
        # Canvas validation
        if test_data and "canvas" in test_data:
            data = test_data["canvas"]["data"]
            width = test_data["canvas"]["width"]
            height = test_data["canvas"]["height"]
            results["canvas"] = self.canvas_validator.validate_consistency(data, width, height)
        else:
            # Use synthetic test data
            test_width, test_height = 100, 100
            test_canvas_data = [128] * (test_width * test_height * 4)
            results["canvas"] = self.canvas_validator.validate_consistency(
                test_canvas_data, test_width, test_height
            )
        
        # WebGL validation (just check config generation is deterministic)
        params1 = self.webgl_injector.get_noised_parameters()
        webgl_rng_reset = WebGLNoiseInjector(self.webgl_config)
        params2 = webgl_rng_reset.get_noised_parameters()
        
        if params1 == params2:
            results["webgl"] = (True, "WebGL parameters consistent")
        else:
            results["webgl"] = (False, "WebGL parameters inconsistent!")
        
        return results


# ═══════════════════════════════════════════════════════════════════════════════
# TESTING
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("LUCID EMPIRE - CONSISTENT CANVAS NOISE MODULE TEST")
    print("=" * 70)
    
    # Test with sample profile UUID
    test_uuid = "550e8400-e29b-41d4-a716-446655440000"
    
    # Test Perlin noise consistency
    print("\n[1] Testing Perlin Noise Consistency...")
    noise1 = PerlinNoise(seed=12345)
    noise2 = PerlinNoise(seed=12345)
    
    test_val1 = noise1.octave_noise(10.5, 20.7, 4, 0.5)
    test_val2 = noise2.octave_noise(10.5, 20.7, 4, 0.5)
    
    print(f"    Noise instance 1: {test_val1:.10f}")
    print(f"    Noise instance 2: {test_val2:.10f}")
    print(f"    Match: {'✓ PASS' if test_val1 == test_val2 else '✗ FAIL'}")
    
    # Test canvas noise injector
    print("\n[2] Testing Canvas Noise Injector...")
    config = CanvasNoiseConfig.from_profile_uuid(test_uuid)
    injector = CanvasNoiseInjector(config)
    
    # Test pixel modification consistency
    mod1 = injector.get_pixel_modification(50, 50)
    mod2 = injector.get_pixel_modification(50, 50)
    print(f"    Pixel (50,50) mod 1: {mod1}")
    print(f"    Pixel (50,50) mod 2: {mod2}")
    print(f"    Match: {'✓ PASS' if mod1 == mod2 else '✗ FAIL'}")
    
    # Test canvas hash consistency
    print("\n[3] Testing Canvas Hash Consistency...")
    validator = CanvasHashValidator(injector)
    test_data = [128] * (100 * 100 * 4)  # 100x100 gray image
    
    is_consistent, message = validator.validate_consistency(test_data, 100, 100, iterations=5)
    print(f"    {message}")
    print(f"    Result: {'✓ PASS' if is_consistent else '✗ FAIL'}")
    
    # Test WebGL noise
    print("\n[4] Testing WebGL Noise...")
    webgl_config = WebGLNoiseConfig.from_profile_uuid(test_uuid)
    webgl_injector = WebGLNoiseInjector(webgl_config)
    
    params = webgl_injector.get_noised_parameters()
    print(f"    Max Texture Size: {params['max_texture_size']}")
    print(f"    Vendor: {webgl_injector.get_unmasked_vendor()}")
    
    # Test unified manager
    print("\n[5] Testing Unified Fingerprint Manager...")
    manager = FingerprintNoiseManager(test_uuid)
    
    results = manager.validate_all()
    for component, (success, msg) in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"    {component.upper()}: {status} - {msg}")
    
    # Generate config file
    config_path = manager.generate_config_file()
    print(f"\n[6] Generated config: {config_path}")
    
    print("\n" + "=" * 70)
    print("CONSISTENT CANVAS NOISE MODULE: OPERATIONAL")
    print("=" * 70)
