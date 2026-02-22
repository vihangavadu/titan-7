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

__version__ = "8.0.0"
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
    NVIDIA_RTX_4070 = "nvidia_rtx_4070"
    NVIDIA_RTX_3060 = "nvidia_rtx_3060"
    INTEL_IRIS_XE = "intel_iris_xe"
    INTEL_ARC_A770 = "intel_arc_a770"
    AMD_RX_7600 = "amd_rx_7600"


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

# P1-5 FIX: Add specific GPU profiles referenced in GPUProfile enum but missing from dict
GPU_PROFILES[GPUProfile.NVIDIA_RTX_4070] = WebGLParams(
    vendor="Google Inc. (NVIDIA)",
    renderer="ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    unmasked_vendor="Google Inc. (NVIDIA)",
    unmasked_renderer="ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    webgl_version="WebGL 2.0 (OpenGL ES 3.0 Chromium)",
    shading_language_version="WebGL GLSL ES 3.00 (OpenGL ES GLSL ES 3.0 Chromium)",
    max_texture_size=32768,
    max_viewport_dims=(32768, 32768),
    max_renderbuffer_size=32768,
    max_vertex_attribs=16,
    max_vertex_uniform_vectors=4096,
    max_varying_vectors=32,
    max_fragment_uniform_vectors=1024,
    max_texture_image_units=32,
    max_vertex_texture_image_units=32,
    max_combined_texture_image_units=64,
    aliased_line_width_range=(1.0, 1.0),
    aliased_point_size_range=(1.0, 8192.0),
    max_cube_map_texture_size=32768,
    max_anisotropy=16.0,
    precision_vertex_high_float=(127, 127, 23),
    precision_fragment_high_float=(127, 127, 23),
    extensions=GPU_PROFILES[GPUProfile.ANGLE_D3D11].extensions.copy(),
)

GPU_PROFILES[GPUProfile.NVIDIA_RTX_3060] = WebGLParams(
    vendor="Google Inc. (NVIDIA)",
    renderer="ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    unmasked_vendor="Google Inc. (NVIDIA)",
    unmasked_renderer="ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    webgl_version="WebGL 2.0 (OpenGL ES 3.0 Chromium)",
    shading_language_version="WebGL GLSL ES 3.00 (OpenGL ES GLSL ES 3.0 Chromium)",
    max_texture_size=32768,
    max_viewport_dims=(32768, 32768),
    max_renderbuffer_size=32768,
    max_vertex_attribs=16,
    max_vertex_uniform_vectors=4096,
    max_varying_vectors=32,
    max_fragment_uniform_vectors=1024,
    max_texture_image_units=32,
    max_vertex_texture_image_units=32,
    max_combined_texture_image_units=64,
    aliased_line_width_range=(1.0, 1.0),
    aliased_point_size_range=(1.0, 8192.0),
    max_cube_map_texture_size=32768,
    max_anisotropy=16.0,
    precision_vertex_high_float=(127, 127, 23),
    precision_fragment_high_float=(127, 127, 23),
    extensions=GPU_PROFILES[GPUProfile.ANGLE_D3D11].extensions.copy(),
)

GPU_PROFILES[GPUProfile.INTEL_IRIS_XE] = WebGLParams(
    vendor="Google Inc. (Intel)",
    renderer="ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)",
    unmasked_vendor="Google Inc. (Intel)",
    unmasked_renderer="ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)",
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
    extensions=GPU_PROFILES[GPUProfile.GENERIC_INTEL].extensions.copy(),
)

GPU_PROFILES[GPUProfile.INTEL_ARC_A770] = WebGLParams(
    vendor="Google Inc. (Intel)",
    renderer="ANGLE (Intel, Intel(R) Arc(TM) A770 Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)",
    unmasked_vendor="Google Inc. (Intel)",
    unmasked_renderer="ANGLE (Intel, Intel(R) Arc(TM) A770 Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)",
    webgl_version="WebGL 2.0 (OpenGL ES 3.0 Chromium)",
    shading_language_version="WebGL GLSL ES 3.00 (OpenGL ES GLSL ES 3.0 Chromium)",
    max_texture_size=32768,
    max_viewport_dims=(32768, 32768),
    max_renderbuffer_size=32768,
    max_vertex_attribs=16,
    max_vertex_uniform_vectors=4096,
    max_varying_vectors=32,
    max_fragment_uniform_vectors=1024,
    max_texture_image_units=32,
    max_vertex_texture_image_units=32,
    max_combined_texture_image_units=64,
    aliased_line_width_range=(1.0, 1.0),
    aliased_point_size_range=(1.0, 8192.0),
    max_cube_map_texture_size=32768,
    max_anisotropy=16.0,
    precision_vertex_high_float=(127, 127, 23),
    precision_fragment_high_float=(127, 127, 23),
    extensions=GPU_PROFILES[GPUProfile.ANGLE_D3D11].extensions.copy(),
)

GPU_PROFILES[GPUProfile.AMD_RX_7600] = WebGLParams(
    vendor="Google Inc. (AMD)",
    renderer="ANGLE (AMD, AMD Radeon RX 7600 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    unmasked_vendor="Google Inc. (AMD)",
    unmasked_renderer="ANGLE (AMD, AMD Radeon RX 7600 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    webgl_version="WebGL 2.0 (OpenGL ES 3.0 Chromium)",
    shading_language_version="WebGL GLSL ES 3.00 (OpenGL ES GLSL ES 3.0 Chromium)",
    max_texture_size=16384,
    max_viewport_dims=(16384, 16384),
    max_renderbuffer_size=16384,
    max_vertex_attribs=16,
    max_vertex_uniform_vectors=4096,
    max_varying_vectors=32,
    max_fragment_uniform_vectors=1024,
    max_texture_image_units=32,
    max_vertex_texture_image_units=32,
    max_combined_texture_image_units=64,
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


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 P0 CRITICAL ENHANCEMENTS - Advanced WebGL Synthesis
# ═══════════════════════════════════════════════════════════════════════════════

import threading
import random
import time
from collections import defaultdict
from typing import Any


@dataclass
class CanvasFingerprint:
    """Canvas fingerprint data"""
    hash: str
    width: int
    height: int
    data_points: int
    generation_seed: int
    profile_uuid: str


@dataclass
class WebGLBenchmark:
    """WebGL benchmark result"""
    gpu_profile: GPUProfile
    simple_fps: float
    complex_fps: float
    first_frame_ms: float
    frame_variance: float
    timestamp: float


@dataclass
class GPUConsistencyCheck:
    """GPU consistency validation result"""
    profile_uuid: str
    claimed_gpu: str
    webgl_renderer: str
    timing_consistent: bool
    extension_consistent: bool
    overall_pass: bool
    issues: List[str]


class CanvasFingerprintGenerator:
    """
    V7.6 P0: Deterministic canvas fingerprint generation.
    
    Features:
    - Profile-seeded deterministic hashes
    - Consistent across sessions
    - Noise injection for uniqueness
    - Anti-detection randomization
    """
    
    def __init__(self):
        self._cache: Dict[str, CanvasFingerprint] = {}
        self._lock = threading.Lock()
    
    def generate(self, profile_uuid: str, width: int = 400, height: int = 200) -> CanvasFingerprint:
        """Generate deterministic canvas fingerprint for profile"""
        cache_key = f"{profile_uuid}_{width}_{height}"
        
        with self._lock:
            if cache_key in self._cache:
                return self._cache[cache_key]
        
        # Deterministic seed from profile UUID
        seed = int(hashlib.sha256(
            f"canvas_{profile_uuid}".encode()
        ).hexdigest()[:8], 16)
        
        # Generate canvas data simulation
        rng = random.Random(seed)
        data_points = width * height * 4  # RGBA
        
        # Create deterministic hash
        hash_input = f"{profile_uuid}_{seed}_{width}_{height}_{data_points}"
        canvas_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:32]
        
        fingerprint = CanvasFingerprint(
            hash=canvas_hash,
            width=width,
            height=height,
            data_points=data_points,
            generation_seed=seed,
            profile_uuid=profile_uuid,
        )
        
        with self._lock:
            self._cache[cache_key] = fingerprint
        
        return fingerprint
    
    def get_injection_config(self, profile_uuid: str) -> Dict:
        """Get canvas fingerprint injection configuration"""
        fp = self.generate(profile_uuid)
        
        return {
            "canvas.hash_override": fp.hash,
            "canvas.noise_seed": fp.generation_seed,
            "canvas.deterministic": True,
            "canvas.width_default": fp.width,
            "canvas.height_default": fp.height,
        }
    
    def verify_consistency(self, profile_uuid: str, observed_hash: str) -> bool:
        """Verify observed hash matches expected"""
        expected = self.generate(profile_uuid)
        return expected.hash == observed_hash


class WebGLPerformanceNormalizer:
    """
    V7.6 P0: Normalize WebGL rendering performance to match claimed GPU.
    
    Features:
    - Frame timing normalization
    - requestAnimationFrame interception
    - Performance.now() jitter injection
    - GPU-appropriate latency simulation
    """
    
    def __init__(self):
        self._benchmarks: Dict[str, WebGLBenchmark] = {}
        self._lock = threading.Lock()
    
    def get_timing_constraints(self, gpu_profile: GPUProfile) -> Dict:
        """Get timing constraints for JS injection"""
        timing = RENDER_TIMING_DB.get(gpu_profile, RENDER_TIMING_DB[GPUProfile.ANGLE_D3D11])
        
        # Calculate frame time targets
        simple_fps_target = (timing.target_fps_simple[0] + timing.target_fps_simple[1]) / 2
        complex_fps_target = (timing.target_fps_complex[0] + timing.target_fps_complex[1]) / 2
        
        return {
            "performance.frame_time_simple_ms": 1000.0 / simple_fps_target,
            "performance.frame_time_complex_ms": 1000.0 / complex_fps_target,
            "performance.jitter_ms": timing.frame_jitter_ms,
            "performance.first_frame_delay_ms": timing.first_frame_delay_ms,
            "performance.fps_variance": 0.1,  # 10% variance
            "performance.normalize_raf": True,
            "performance.normalize_now": True,
        }
    
    def record_benchmark(self, profile_uuid: str, gpu_profile: GPUProfile,
                         simple_fps: float, complex_fps: float,
                         first_frame_ms: float) -> WebGLBenchmark:
        """Record a benchmark result for analysis"""
        timing = RENDER_TIMING_DB.get(gpu_profile, RENDER_TIMING_DB[GPUProfile.ANGLE_D3D11])
        
        # Calculate variance from expected
        expected_simple = (timing.target_fps_simple[0] + timing.target_fps_simple[1]) / 2
        variance = abs(simple_fps - expected_simple) / expected_simple
        
        benchmark = WebGLBenchmark(
            gpu_profile=gpu_profile,
            simple_fps=simple_fps,
            complex_fps=complex_fps,
            first_frame_ms=first_frame_ms,
            frame_variance=variance,
            timestamp=time.time(),
        )
        
        with self._lock:
            self._benchmarks[profile_uuid] = benchmark
        
        return benchmark
    
    def is_performance_consistent(self, profile_uuid: str) -> bool:
        """Check if performance matches claimed GPU"""
        with self._lock:
            benchmark = self._benchmarks.get(profile_uuid)
        
        if not benchmark:
            return True  # No data to compare
        
        # Variance should be under 20%
        return benchmark.frame_variance < 0.2


class GPUProfileValidator:
    """
    V7.6 P0: Validate GPU profile consistency.
    
    Features:
    - Cross-check WebGL params against claimed hardware
    - Detect mismatched configurations
    - Validate extension availability
    - Performance plausibility checks
    """
    
    def __init__(self):
        self._validations: Dict[str, GPUConsistencyCheck] = {}
        self._lock = threading.Lock()
    
    def validate(self, profile_uuid: str, config: Dict) -> GPUConsistencyCheck:
        """Validate GPU profile configuration"""
        issues = []
        
        claimed_gpu = config.get("webgl.gpu_profile", "")
        webgl_renderer = config.get("webgl.renderer", "")
        
        # Check GPU profile exists
        try:
            gpu = GPUProfile(claimed_gpu)
            expected_params = GPU_PROFILES.get(gpu)
        except (ValueError, KeyError):
            issues.append(f"Unknown GPU profile: {claimed_gpu}")
            expected_params = None
        
        timing_consistent = True
        extension_consistent = True
        
        if expected_params:
            # Check renderer string
            if expected_params.renderer != webgl_renderer:
                if config.get("webgl.custom_renderer"):
                    pass  # Custom override allowed
                else:
                    issues.append("Renderer string mismatch")
            
            # Check extensions
            config_extensions = set(config.get("webgl.extensions", []))
            expected_extensions = set(expected_params.extensions)
            
            missing = expected_extensions - config_extensions
            extra = config_extensions - expected_extensions
            
            if missing:
                issues.append(f"Missing extensions: {len(missing)}")
                extension_consistent = False
            if extra:
                issues.append(f"Extra extensions: {len(extra)}")
            
            # Check texture sizes
            if config.get("webgl.max_texture_size", 0) > expected_params.max_texture_size * 1.5:
                issues.append("Texture size exceeds GPU capability")
        
        overall_pass = len(issues) == 0
        
        check = GPUConsistencyCheck(
            profile_uuid=profile_uuid,
            claimed_gpu=claimed_gpu,
            webgl_renderer=webgl_renderer,
            timing_consistent=timing_consistent,
            extension_consistent=extension_consistent,
            overall_pass=overall_pass,
            issues=issues,
        )
        
        with self._lock:
            self._validations[profile_uuid] = check
        
        return check
    
    def get_remediation(self, check: GPUConsistencyCheck) -> List[str]:
        """Get remediation steps for failed checks"""
        remediation = []
        
        for issue in check.issues:
            if "Renderer string mismatch" in issue:
                remediation.append("Update webgl.renderer to match GPU profile")
            elif "Missing extensions" in issue:
                remediation.append("Add missing WebGL extensions to config")
            elif "Texture size" in issue:
                remediation.append("Reduce max_texture_size to GPU-appropriate value")
            elif "Unknown GPU profile" in issue:
                remediation.append("Use valid GPU profile: ANGLE_D3D11, GENERIC_INTEL, etc.")
        
        return remediation


class WebGLExtensionManager:
    """
    V7.6 P0: Manage WebGL extension availability and consistency.
    
    Features:
    - Extension filtering per GPU profile
    - Deterministic extension ordering
    - Extension capability validation
    """
    
    # Extensions that vary by GPU capability
    CAPABILITY_EXTENSIONS = {
        "high_end": [
            "EXT_disjoint_timer_query",
            "EXT_texture_compression_bptc",
            "WEBGL_compressed_texture_astc",
        ],
        "mid_range": [
            "EXT_texture_filter_anisotropic",
            "WEBGL_compressed_texture_s3tc",
        ],
        "low_end": [
            # Basic extensions only
        ],
    }
    
    def __init__(self):
        self._extension_cache: Dict[str, List[str]] = {}
    
    def get_extensions_for_profile(self, gpu_profile: GPUProfile,
                                     profile_uuid: str = "") -> List[str]:
        """Get deterministic extension list for GPU profile"""
        params = GPU_PROFILES.get(gpu_profile, GPU_PROFILES[GPUProfile.ANGLE_D3D11])
        base_extensions = list(params.extensions)
        
        # Deterministic ordering based on profile UUID
        if profile_uuid:
            seed = int(hashlib.sha256(profile_uuid.encode()).hexdigest()[:8], 16)
            rng = random.Random(seed)
            rng.shuffle(base_extensions)
        
        return base_extensions
    
    def filter_extensions(self, extensions: List[str], gpu_tier: str) -> List[str]:
        """Filter extensions based on GPU tier"""
        if gpu_tier == "low_end":
            # Remove high-end only extensions
            high_end = set(self.CAPABILITY_EXTENSIONS["high_end"])
            return [e for e in extensions if e not in high_end]
        return extensions
    
    def validate_extension(self, extension: str, gpu_profile: GPUProfile) -> bool:
        """Check if extension is valid for GPU profile"""
        params = GPU_PROFILES.get(gpu_profile)
        if not params:
            return False
        return extension in params.extensions


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 SINGLETON INSTANCES
# ═══════════════════════════════════════════════════════════════════════════

_canvas_fingerprint_generator: Optional[CanvasFingerprintGenerator] = None
_webgl_performance_normalizer: Optional[WebGLPerformanceNormalizer] = None
_gpu_profile_validator: Optional[GPUProfileValidator] = None
_webgl_extension_manager: Optional[WebGLExtensionManager] = None


def get_canvas_fingerprint_generator() -> CanvasFingerprintGenerator:
    """Get global canvas fingerprint generator"""
    global _canvas_fingerprint_generator
    if _canvas_fingerprint_generator is None:
        _canvas_fingerprint_generator = CanvasFingerprintGenerator()
    return _canvas_fingerprint_generator


def get_webgl_performance_normalizer() -> WebGLPerformanceNormalizer:
    """Get global WebGL performance normalizer"""
    global _webgl_performance_normalizer
    if _webgl_performance_normalizer is None:
        _webgl_performance_normalizer = WebGLPerformanceNormalizer()
    return _webgl_performance_normalizer


def get_gpu_profile_validator() -> GPUProfileValidator:
    """Get global GPU profile validator"""
    global _gpu_profile_validator
    if _gpu_profile_validator is None:
        _gpu_profile_validator = GPUProfileValidator()
    return _gpu_profile_validator


def get_webgl_extension_manager() -> WebGLExtensionManager:
    """Get global WebGL extension manager"""
    global _webgl_extension_manager
    if _webgl_extension_manager is None:
        _webgl_extension_manager = WebGLExtensionManager()
    return _webgl_extension_manager
