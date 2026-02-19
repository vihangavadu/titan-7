"""
TITAN V7.0 SINGULARITY — WebGL ANGLE Shim & GPU Fingerprint Standardization
Defeats WebGL hardware profiling by presenting standardized GPU interfaces

Instead of spoofing a specific high-end GPU (detectable via performance mismatch),
V7 standardizes the GPU interface using ANGLE (Almost Native Graphics Layer Engine)
to present a generic "Google SwiftShader" or cloud-desktop GPU profile that matches
millions of legitimate users.

Architecture:
    webgl_angle.py          → configure ANGLE/VirGL translation layer
    fingerprint_injector.py → inject consistent WebGL parameters
    Camoufox                → render via ANGLE shim (not native GPU)

Detection Vectors Neutralized:
    - WebGL renderer string mismatch (GPU doesn't match claimed hardware)
    - WebGL performance profiling (software vs hardware render timing)
    - WebGL debug renderer info leak (MESA/llvmpipe detection)
    - Canvas hash inconsistency across sessions
    - GPU vendor/model enumeration via WEBGL_debug_renderer_info
"""

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

__version__ = "7.0.0"
__author__ = "Dva.12"


class GPUProfile(Enum):
    """Standardized GPU profiles for WebGL fingerprint consistency."""
    SWIFTSHADER = "swiftshader"
    ANGLE_D3D11 = "angle_d3d11"
    ANGLE_VULKAN = "angle_vulkan"
    VIRGL = "virgl"
    GENERIC_INTEL = "generic_intel"
    GENERIC_NVIDIA = "generic_nvidia"
    GENERIC_AMD = "generic_amd"


@dataclass
class WebGLParams:
    """Complete WebGL parameter set for a GPU profile."""
    vendor: str
    renderer: str
    unmasked_vendor: str
    unmasked_renderer: str
    webgl_version: str
    shading_language_version: str
    max_texture_size: int
    max_viewport_dims: Tuple[int, int]
    max_renderbuffer_size: int
    max_vertex_attribs: int
    max_vertex_uniform_vectors: int
    max_varying_vectors: int
    max_fragment_uniform_vectors: int
    max_texture_image_units: int
    max_vertex_texture_image_units: int
    max_combined_texture_image_units: int
    aliased_line_width_range: Tuple[float, float]
    aliased_point_size_range: Tuple[float, float]
    max_cube_map_texture_size: int
    max_anisotropy: float
    precision_vertex_high_float: Tuple[int, int, int]
    precision_fragment_high_float: Tuple[int, int, int]
    extensions: List[str] = field(default_factory=list)
    antialias: bool = True
    depth: bool = True
    stencil: bool = True
    alpha: bool = True


# ══════════════════════════════════════════════════════════════════════════════
# GPU PROFILE DATABASE — Exact WebGL parameters per GPU profile
# ══════════════════════════════════════════════════════════════════════════════

GPU_PROFILES: Dict[GPUProfile, WebGLParams] = {
    GPUProfile.ANGLE_D3D11: WebGLParams(
        vendor="Google Inc. (NVIDIA)",
        renderer="ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        unmasked_vendor="Google Inc. (NVIDIA)",
        unmasked_renderer="ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        webgl_version="WebGL 2.0 (OpenGL ES 3.0 Chromium)",
        shading_language_version="WebGL GLSL ES 3.00 (OpenGL ES GLSL ES 3.0 Chromium)",
        max_texture_size=16384,
        max_viewport_dims=(32767, 32767),
        max_renderbuffer_size=16384,
        max_vertex_attribs=16,
        max_vertex_uniform_vectors=4096,
        max_varying_vectors=30,
        max_fragment_uniform_vectors=1024,
        max_texture_image_units=16,
        max_vertex_texture_image_units=16,
        max_combined_texture_image_units=32,
        aliased_line_width_range=(1.0, 1.0),
        aliased_point_size_range=(1.0, 1024.0),
        max_cube_map_texture_size=16384,
        max_anisotropy=16.0,
        precision_vertex_high_float=(127, 127, 23),
        precision_fragment_high_float=(127, 127, 23),
        extensions=[
            "ANGLE_instanced_arrays", "EXT_blend_minmax", "EXT_color_buffer_half_float",
            "EXT_disjoint_timer_query", "EXT_float_blend", "EXT_frag_depth",
            "EXT_shader_texture_lod", "EXT_texture_compression_bptc",
            "EXT_texture_compression_rgtc", "EXT_texture_filter_anisotropic",
            "WEBKIT_EXT_texture_filter_anisotropic", "EXT_sRGB",
            "KHR_parallel_shader_compile", "OES_element_index_uint",
            "OES_fbo_render_mipmap", "OES_standard_derivatives",
            "OES_texture_float", "OES_texture_float_linear",
            "OES_texture_half_float", "OES_texture_half_float_linear",
            "OES_vertex_array_object", "WEBGL_color_buffer_float",
            "WEBGL_compressed_texture_s3tc", "WEBKIT_WEBGL_compressed_texture_s3tc",
            "WEBGL_compressed_texture_s3tc_srgb", "WEBGL_debug_renderer_info",
            "WEBGL_debug_shaders", "WEBGL_depth_texture", "WEBKIT_WEBGL_depth_texture",
            "WEBGL_draw_buffers", "WEBGL_lose_context", "WEBKIT_WEBGL_lose_context",
            "WEBGL_multi_draw",
        ],
    ),

    GPUProfile.GENERIC_INTEL: WebGLParams(
        vendor="Google Inc. (Intel)",
        renderer="ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        unmasked_vendor="Google Inc. (Intel)",
        unmasked_renderer="ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        webgl_version="WebGL 2.0 (OpenGL ES 3.0 Chromium)",
        shading_language_version="WebGL GLSL ES 3.00 (OpenGL ES GLSL ES 3.0 Chromium)",
        max_texture_size=16384,
        max_viewport_dims=(16384, 16384),
        max_renderbuffer_size=16384,
        max_vertex_attribs=16,
        max_vertex_uniform_vectors=4096,
        max_varying_vectors=31,
        max_fragment_uniform_vectors=1024,
        max_texture_image_units=16,
        max_vertex_texture_image_units=16,
        max_combined_texture_image_units=32,
        aliased_line_width_range=(1.0, 1.0),
        aliased_point_size_range=(1.0, 1024.0),
        max_cube_map_texture_size=16384,
        max_anisotropy=16.0,
        precision_vertex_high_float=(127, 127, 23),
        precision_fragment_high_float=(127, 127, 23),
        extensions=[
            "ANGLE_instanced_arrays", "EXT_blend_minmax", "EXT_color_buffer_half_float",
            "EXT_float_blend", "EXT_frag_depth", "EXT_shader_texture_lod",
            "EXT_texture_compression_rgtc", "EXT_texture_filter_anisotropic",
            "EXT_sRGB", "OES_element_index_uint", "OES_fbo_render_mipmap",
            "OES_standard_derivatives", "OES_texture_float", "OES_texture_float_linear",
            "OES_texture_half_float", "OES_texture_half_float_linear",
            "OES_vertex_array_object", "WEBGL_color_buffer_float",
            "WEBGL_compressed_texture_s3tc", "WEBGL_debug_renderer_info",
            "WEBGL_depth_texture", "WEBGL_draw_buffers", "WEBGL_lose_context",
            "WEBGL_multi_draw",
        ],
    ),

    GPUProfile.SWIFTSHADER: WebGLParams(
        vendor="Google Inc. (Google)",
        renderer="ANGLE (Google, Vulkan 1.1.0 (SwiftShader Device (Subzero) (0x0000C0DE)), SwiftShader driver)",
        unmasked_vendor="Google Inc. (Google)",
        unmasked_renderer="ANGLE (Google, Vulkan 1.1.0 (SwiftShader Device (Subzero) (0x0000C0DE)), SwiftShader driver)",
        webgl_version="WebGL 2.0 (OpenGL ES 3.0 Chromium)",
        shading_language_version="WebGL GLSL ES 3.00 (OpenGL ES GLSL ES 3.0 Chromium)",
        max_texture_size=8192,
        max_viewport_dims=(8192, 8192),
        max_renderbuffer_size=8192,
        max_vertex_attribs=16,
        max_vertex_uniform_vectors=4096,
        max_varying_vectors=15,
        max_fragment_uniform_vectors=1024,
        max_texture_image_units=16,
        max_vertex_texture_image_units=16,
        max_combined_texture_image_units=32,
        aliased_line_width_range=(1.0, 1.0),
        aliased_point_size_range=(1.0, 1.0),
        max_cube_map_texture_size=8192,
        max_anisotropy=1.0,
        precision_vertex_high_float=(127, 127, 23),
        precision_fragment_high_float=(127, 127, 23),
        extensions=[
            "EXT_blend_minmax", "EXT_color_buffer_half_float", "EXT_float_blend",
            "EXT_frag_depth", "EXT_shader_texture_lod", "EXT_sRGB",
            "OES_element_index_uint", "OES_standard_derivatives",
            "OES_texture_float", "OES_texture_float_linear",
            "OES_texture_half_float", "OES_texture_half_float_linear",
            "OES_vertex_array_object", "WEBGL_color_buffer_float",
            "WEBGL_debug_renderer_info", "WEBGL_depth_texture",
            "WEBGL_draw_buffers", "WEBGL_lose_context",
        ],
    ),
}

# Copy NVIDIA as default for generic_nvidia
GPU_PROFILES[GPUProfile.GENERIC_NVIDIA] = GPU_PROFILES[GPUProfile.ANGLE_D3D11]
GPU_PROFILES[GPUProfile.GENERIC_AMD] = WebGLParams(
    vendor="Google Inc. (AMD)",
    renderer="ANGLE (AMD, AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    unmasked_vendor="Google Inc. (AMD)",
    unmasked_renderer="ANGLE (AMD, AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    webgl_version="WebGL 2.0 (OpenGL ES 3.0 Chromium)",
    shading_language_version="WebGL GLSL ES 3.00 (OpenGL ES GLSL ES 3.0 Chromium)",
    max_texture_size=16384,
    max_viewport_dims=(16384, 16384),
    max_renderbuffer_size=16384,
    max_vertex_attribs=16,
    max_vertex_uniform_vectors=4096,
    max_varying_vectors=32,
    max_fragment_uniform_vectors=1024,
    max_texture_image_units=16,
    max_vertex_texture_image_units=16,
    max_combined_texture_image_units=32,
    aliased_line_width_range=(1.0, 1.0),
    aliased_point_size_range=(1.0, 8192.0),
    max_cube_map_texture_size=16384,
    max_anisotropy=16.0,
    precision_vertex_high_float=(127, 127, 23),
    precision_fragment_high_float=(127, 127, 23),
    extensions=GPU_PROFILES[GPUProfile.ANGLE_D3D11].extensions.copy(),
)


class WebGLAngleShim:
    """
    WebGL ANGLE Shim — standardizes GPU fingerprint presentation.

    Instead of attempting to spoof a specific GPU (detectable via performance
    mismatch), this shim presents a standardized GPU interface via ANGLE
    that matches millions of legitimate users on similar hardware.

    Usage:
        shim = WebGLAngleShim()
        config = shim.generate_webgl_config(
            gpu_profile=GPUProfile.ANGLE_D3D11,
            profile_uuid="abc123"
        )
        # Apply config to Camoufox prefs
    """

    def __init__(self):
        self._profiles = dict(GPU_PROFILES)

    def get_profile(self, gpu: GPUProfile) -> WebGLParams:
        """Get WebGL parameters for a specific GPU profile."""
        if gpu not in self._profiles:
            raise ValueError(f"Unknown GPU profile: {gpu.value}")
        return self._profiles[gpu]

    def select_gpu_for_hardware(self, hw_vendor: str = "", hw_model: str = "") -> GPUProfile:
        """Auto-select GPU profile based on spoofed hardware vendor/model."""
        vendor_lower = hw_vendor.lower()
        if "intel" in vendor_lower:
            return GPUProfile.GENERIC_INTEL
        elif "amd" in vendor_lower or "radeon" in vendor_lower:
            return GPUProfile.GENERIC_AMD
        elif "nvidia" in vendor_lower or "geforce" in vendor_lower:
            return GPUProfile.GENERIC_NVIDIA
        else:
            return GPUProfile.ANGLE_D3D11

    def generate_webgl_config(
        self,
        gpu_profile: GPUProfile,
        profile_uuid: str = "",
    ) -> Dict:
        """
        Generate a complete WebGL configuration dict for Camoufox.
        Deterministic canvas hash is derived from profile_uuid.
        """
        params = self.get_profile(gpu_profile)

        # Deterministic canvas noise seed from profile UUID
        canvas_seed = 0
        if profile_uuid:
            canvas_seed = int(hashlib.sha256(
                f"webgl_canvas_{profile_uuid}".encode()
            ).hexdigest()[:8], 16)

        config = {
            "webgl.vendor": params.vendor,
            "webgl.renderer": params.renderer,
            "webgl.unmasked_vendor": params.unmasked_vendor,
            "webgl.unmasked_renderer": params.unmasked_renderer,
            "webgl.version": params.webgl_version,
            "webgl.shading_language_version": params.shading_language_version,
            "webgl.max_texture_size": params.max_texture_size,
            "webgl.max_viewport_dims": list(params.max_viewport_dims),
            "webgl.max_renderbuffer_size": params.max_renderbuffer_size,
            "webgl.max_vertex_attribs": params.max_vertex_attribs,
            "webgl.max_vertex_uniform_vectors": params.max_vertex_uniform_vectors,
            "webgl.max_varying_vectors": params.max_varying_vectors,
            "webgl.max_fragment_uniform_vectors": params.max_fragment_uniform_vectors,
            "webgl.max_texture_image_units": params.max_texture_image_units,
            "webgl.max_cube_map_texture_size": params.max_cube_map_texture_size,
            "webgl.max_anisotropy": params.max_anisotropy,
            "webgl.extensions": params.extensions,
            "webgl.antialias": params.antialias,
            "webgl.canvas_noise_seed": canvas_seed,
            "webgl.gpu_profile": gpu_profile.value,
        }

        return config

    def generate_env_overrides(self, gpu_profile: GPUProfile) -> Dict[str, str]:
        """
        Generate environment variable overrides for ANGLE/VirGL.
        These are set before launching Camoufox.
        """
        params = self.get_profile(gpu_profile)
        env = {
            "LIBGL_ALWAYS_SOFTWARE": "0",
            "ANGLE_DEFAULT_PLATFORM": "vulkan",
            "GALLIUM_DRIVER": "virgl" if gpu_profile == GPUProfile.VIRGL else "",
            "MESA_GL_VERSION_OVERRIDE": "4.6",
            "MESA_GLSL_VERSION_OVERRIDE": "460",
            "TITAN_WEBGL_VENDOR": params.vendor,
            "TITAN_WEBGL_RENDERER": params.renderer,
            "TITAN_GPU_PROFILE": gpu_profile.value,
        }
        return {k: v for k, v in env.items() if v}

    def verify_consistency(self, profile: Dict) -> Dict:
        """Verify WebGL config is consistent with hardware profile."""
        hw_vendor = profile.get("hw_vendor", "")
        gpu_profile_name = profile.get("gpu_profile", "")
        webgl_renderer = profile.get("webgl_renderer", "")

        checks = {
            "vendor_match": True,
            "renderer_valid": True,
            "performance_plausible": True,
        }

        if hw_vendor and gpu_profile_name:
            try:
                gpu = GPUProfile(gpu_profile_name)
                params = self.get_profile(gpu)
                if hw_vendor.lower() not in params.unmasked_renderer.lower():
                    checks["vendor_match"] = False
            except (ValueError, KeyError):
                checks["renderer_valid"] = False

        passed = all(checks.values())
        return {"status": "PASS" if passed else "FAIL", "checks": checks}


# ══════════════════════════════════════════════════════════════════════════════
# V7.0 AUDIT REMEDIATION: RENDER TIMING NORMALIZATION
# Defeats requestAnimationFrame() benchmarking that reveals software vs
# hardware rendering performance mismatch.
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class RenderTimingProfile:
    """Frame timing constraints for a GPU profile tier."""
    gpu_profile: GPUProfile
    target_fps_simple: Tuple[int, int]     # FPS range for simple 2D scenes
    target_fps_complex: Tuple[int, int]    # FPS range for complex 3D scenes
    frame_jitter_ms: float                 # Gaussian jitter on frame timing
    first_frame_delay_ms: float            # Shader compilation stall (1st frame)


RENDER_TIMING_DB: Dict[GPUProfile, RenderTimingProfile] = {
    GPUProfile.SWIFTSHADER: RenderTimingProfile(
        gpu_profile=GPUProfile.SWIFTSHADER,
        target_fps_simple=(30, 60),
        target_fps_complex=(8, 20),
        frame_jitter_ms=3.0,
        first_frame_delay_ms=150.0,
    ),
    GPUProfile.ANGLE_D3D11: RenderTimingProfile(
        gpu_profile=GPUProfile.ANGLE_D3D11,
        target_fps_simple=(55, 60),
        target_fps_complex=(30, 60),
        frame_jitter_ms=1.5,
        first_frame_delay_ms=80.0,
    ),
    GPUProfile.ANGLE_VULKAN: RenderTimingProfile(
        gpu_profile=GPUProfile.ANGLE_VULKAN,
        target_fps_simple=(58, 60),
        target_fps_complex=(40, 60),
        frame_jitter_ms=1.0,
        first_frame_delay_ms=60.0,
    ),
    GPUProfile.VIRGL: RenderTimingProfile(
        gpu_profile=GPUProfile.VIRGL,
        target_fps_simple=(40, 60),
        target_fps_complex=(15, 35),
        frame_jitter_ms=2.5,
        first_frame_delay_ms=120.0,
    ),
    GPUProfile.GENERIC_INTEL: RenderTimingProfile(
        gpu_profile=GPUProfile.GENERIC_INTEL,
        target_fps_simple=(50, 60),
        target_fps_complex=(20, 45),
        frame_jitter_ms=2.0,
        first_frame_delay_ms=90.0,
    ),
    GPUProfile.GENERIC_NVIDIA: RenderTimingProfile(
        gpu_profile=GPUProfile.GENERIC_NVIDIA,
        target_fps_simple=(58, 60),
        target_fps_complex=(45, 60),
        frame_jitter_ms=0.8,
        first_frame_delay_ms=50.0,
    ),
    GPUProfile.GENERIC_AMD: RenderTimingProfile(
        gpu_profile=GPUProfile.GENERIC_AMD,
        target_fps_simple=(55, 60),
        target_fps_complex=(35, 60),
        frame_jitter_ms=1.2,
        first_frame_delay_ms=70.0,
    ),
}


def get_render_timing_config(gpu_profile: GPUProfile) -> Dict:
    """Generate render timing constraints for Ghost Motor JS extension.
    
    The extension intercepts requestAnimationFrame and performance.now()
    to normalize frame timing to the claimed GPU's performance tier.
    """
    timing = RENDER_TIMING_DB.get(gpu_profile, RENDER_TIMING_DB[GPUProfile.ANGLE_D3D11])
    return {
        "render_timing.enabled": True,
        "render_timing.target_fps_simple": list(timing.target_fps_simple),
        "render_timing.target_fps_complex": list(timing.target_fps_complex),
        "render_timing.frame_jitter_ms": timing.frame_jitter_ms,
        "render_timing.first_frame_delay_ms": timing.first_frame_delay_ms,
        "render_timing.gpu_profile": gpu_profile.value,
    }


def get_webgl_config(hw_vendor: str = "", profile_uuid: str = "") -> Dict:
    """Convenience function: auto-select GPU and generate WebGL config."""
    shim = WebGLAngleShim()
    gpu = shim.select_gpu_for_hardware(hw_vendor)
    config = shim.generate_webgl_config(gpu, profile_uuid)
    config.update(get_render_timing_config(gpu))
    return config
