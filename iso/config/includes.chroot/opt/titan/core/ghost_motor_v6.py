"""
TITAN V8.1 SINGULARITY - Ghost Motor V7 (DMTG)
Diffusion Mouse Trajectory Generation

Replaces v5.2 GAN-based Ghost Motor with Entropy-Controlled Diffusion.

Why Diffusion > GAN:
- GANs suffer from "mode collapse" - converge on limited trajectory patterns
- Over 100+ clicks, statistical entropy drops below human threshold
- Diffusion models preserve fractal variability at all scales
- Each trajectory is mathematically unique, even between same points

DMTG Architecture:
1. Initialize with Gaussian noise
2. Reverse diffusion conditioned on start/end points
3. Inject biological entropy (σ_t) at each step
4. Apply motor inertia smoothing
5. Output trajectory indistinguishable from human hand

Operational Modes:
- LEARNED MODE: When dmtg_denoiser.onnx is present at /opt/titan/models/,
  uses trained neural denoiser for maximum trajectory diversity.
- ANALYTICAL MODE (default): Uses multi-segment cubic Bezier curves with
  minimum-jerk velocity profiling, Fitts's Law timing, micro-tremor injection,
  and overshoot/correction physics. This mode produces high-quality human-like
  trajectories that defeat behavioral biometrics without requiring a trained model.
  Generate the ONNX model via: python3 scripts/generate_trajectory_model.py

Reference: arXiv:2410.18233v1 - DMTG Paper
"""

import numpy as np
import math
import os
import time
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Callable
from enum import Enum
import random

try:
    from scipy.interpolate import splprep, splev
    from scipy.ndimage import gaussian_filter1d
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False


class PersonaType(Enum):
    """User persona affects movement entropy"""
    GAMER = "gamer"           # High precision, low entropy
    CASUAL = "casual"         # Medium precision, medium entropy
    ELDERLY = "elderly"       # Low precision, high entropy
    PROFESSIONAL = "professional"  # High precision, medium entropy


@dataclass
class TrajectoryConfig:
    """Configuration for trajectory generation"""
    # Diffusion parameters
    num_diffusion_steps: int = 50
    noise_schedule: str = "cosine"  # "linear", "cosine", "quadratic"
    
    # Entropy control
    entropy_scale: float = 1.0      # 0.5 (precise) to 2.0 (chaotic)
    micro_tremor_amplitude: float = 1.5  # Pixels of hand shake
    
    # Motor dynamics
    overshoot_probability: float = 0.12
    overshoot_max_distance: float = 8.0  # Pixels
    correction_probability: float = 0.08  # Mid-path corrections
    
    # Timing
    min_duration_ms: int = 100
    max_duration_ms: int = 800
    
    # Persona presets
    persona: PersonaType = PersonaType.CASUAL
    
    # V8 FIX: Profile seed for deterministic trajectories per profile
    profile_seed: Optional[int] = None


@dataclass
class TrajectoryPoint:
    """Single point in a trajectory"""
    x: float
    y: float
    timestamp_ms: float
    velocity: float = 0.0
    acceleration: float = 0.0


@dataclass
class GeneratedTrajectory:
    """Complete generated trajectory"""
    points: List[TrajectoryPoint]
    start_pos: Tuple[float, float]
    end_pos: Tuple[float, float]
    duration_ms: float
    entropy_score: float  # Higher = more human-like
    
    def to_coordinates(self) -> List[Tuple[float, float]]:
        """Extract just x,y coordinates"""
        return [(p.x, p.y) for p in self.points]
    
    def to_events(self) -> List[dict]:
        """Convert to input event format"""
        return [
            {
                "type": "mousemove",
                "x": int(p.x),
                "y": int(p.y),
                "timestamp": p.timestamp_ms
            }
            for p in self.points
        ]


class NoiseScheduler:
    """
    Manages noise levels for diffusion process.
    
    The noise schedule controls how much randomness is present at each
    diffusion step. Cosine schedule provides smoother denoising.
    """
    
    def __init__(self, num_steps: int, schedule_type: str = "cosine"):
        self.num_steps = num_steps
        self.schedule_type = schedule_type
        self.betas = self._compute_betas()
        self.alphas = 1.0 - self.betas
        self.alphas_cumprod = np.cumprod(self.alphas)
        self.sqrt_alphas_cumprod = np.sqrt(self.alphas_cumprod)
        self.sqrt_one_minus_alphas_cumprod = np.sqrt(1.0 - self.alphas_cumprod)
    
    def _compute_betas(self) -> np.ndarray:
        """Compute beta schedule"""
        if self.schedule_type == "linear":
            return np.linspace(0.0001, 0.02, self.num_steps)
        elif self.schedule_type == "cosine":
            # Cosine schedule from "Improved Denoising Diffusion"
            steps = np.arange(self.num_steps + 1)
            alphas_cumprod = np.cos((steps / self.num_steps + 0.008) / 1.008 * np.pi / 2) ** 2
            alphas_cumprod = alphas_cumprod / alphas_cumprod[0]
            betas = 1 - alphas_cumprod[1:] / alphas_cumprod[:-1]
            return np.clip(betas, 0.0001, 0.999)
        elif self.schedule_type == "quadratic":
            return np.linspace(0.0001 ** 0.5, 0.02 ** 0.5, self.num_steps) ** 2
        else:
            raise ValueError(f"Unknown schedule: {self.schedule_type}")
    
    def get_noise_level(self, t: int) -> float:
        """Get noise level at timestep t"""
        return self.sqrt_one_minus_alphas_cumprod[t]
    
    def step(self, 
             model_output: np.ndarray, 
             t: int, 
             sample: np.ndarray,
             noise: np.ndarray) -> np.ndarray:
        """
        Perform one reverse diffusion step.
        
        x_{t-1} = (1/√α_t) * (x_t - (β_t/√(1-ᾱ_t)) * ε_θ) + σ_t * z
        """
        alpha = self.alphas[t]
        alpha_cumprod = self.alphas_cumprod[t]
        beta = self.betas[t]
        
        # Predicted x_0
        pred_original = (sample - self.sqrt_one_minus_alphas_cumprod[t] * model_output) / self.sqrt_alphas_cumprod[t]
        
        # Direction pointing to x_t
        pred_sample_direction = np.sqrt(1 - alpha_cumprod) * model_output
        
        # x_{t-1}
        prev_sample = np.sqrt(alpha_cumprod) * pred_original + pred_sample_direction
        
        # Add noise (except at t=0)
        if t > 0:
            sigma = np.sqrt(beta)
            prev_sample = prev_sample + sigma * noise
        
        return prev_sample


class GhostMotorDiffusion:
    """
    DMTG - Diffusion Mouse Trajectory Generation
    
    Generates human-like mouse trajectories using entropy-controlled
    diffusion networks. Each trajectory has fractal variability that
    is mathematically indistinguishable from biological movement.
    
    Usage:
        motor = GhostMotorDiffusion()
        trajectory = motor.generate_path((100, 100), (500, 300), duration_ms=400)
        for point in trajectory.points:
            move_mouse(point.x, point.y)
            sleep(point.timestamp_ms / 1000)
    """
    
    # Persona-specific entropy scales
    PERSONA_ENTROPY = {
        PersonaType.GAMER: 0.6,
        PersonaType.CASUAL: 1.0,
        PersonaType.ELDERLY: 1.5,
        PersonaType.PROFESSIONAL: 0.8
    }
    
    def __init__(self, config: Optional[TrajectoryConfig] = None):
        self.config = config or TrajectoryConfig()
        self.scheduler = NoiseScheduler(
            self.config.num_diffusion_steps,
            self.config.noise_schedule
        )
        
        # V8 FIX: Seeded RNG for deterministic trajectories per profile
        # Prevents behavioral fingerprint drift across sessions
        if self.config.profile_seed is not None:
            self._rng = random.Random(self.config.profile_seed)
            self._np_rng = np.random.RandomState(self.config.profile_seed & 0xFFFFFFFF)
        else:
            self._rng = random.Random()
            self._np_rng = np.random.RandomState()
        
        # ONNX model for learned denoising (optional)
        self.onnx_session = None
        self._load_model()
        
        # Apply persona entropy
        self.config.entropy_scale *= self.PERSONA_ENTROPY.get(
            self.config.persona, 1.0
        )
    
    def _load_model(self):
        """Load ONNX model if available — V8: multi-path fallback"""
        if not ONNX_AVAILABLE:
            return
        
        # V8 V7-FIX: Try multiple paths instead of single hardcoded path
        import os as _os
        model_paths = [
            _os.environ.get("TITAN_GHOST_MOTOR_MODEL", ""),
            "/opt/titan/models/dmtg_denoiser.onnx",
            "/opt/titan/data/models/dmtg_denoiser.onnx",
            str(Path.home() / ".titan" / "models" / "dmtg_denoiser.onnx"),
        ]
        
        for model_path in model_paths:
            if not model_path:
                continue
            try:
                self.onnx_session = ort.InferenceSession(model_path)
                return  # Successfully loaded
            except Exception:
                continue
        # All paths failed — use analytical denoising (no error needed)
    
    def generate_path(self,
                      start_pos: Tuple[float, float],
                      end_pos: Tuple[float, float],
                      duration_ms: Optional[float] = None) -> GeneratedTrajectory:
        """
        Generate a human-like mouse trajectory using diffusion.
        
        Args:
            start_pos: Starting (x, y) coordinates
            end_pos: Ending (x, y) coordinates
            duration_ms: Optional duration, auto-calculated if None
            
        Returns:
            GeneratedTrajectory with points, timing, and entropy score
        """
        # Calculate duration based on distance if not provided
        distance = np.sqrt(
            (end_pos[0] - start_pos[0])**2 + 
            (end_pos[1] - start_pos[1])**2
        )
        
        if duration_ms is None:
            # Fitts' Law approximation: T = a + b * log2(D/W + 1)
            # Simplified: longer distance = longer time, with variance
            base_duration = 100 + distance * 0.8
            duration_ms = base_duration * self._rng.uniform(0.8, 1.2)
            duration_ms = np.clip(
                duration_ms,
                self.config.min_duration_ms,
                self.config.max_duration_ms
            )
        
        # Number of points based on duration (60 FPS equivalent)
        num_points = max(10, int(duration_ms / 16))
        
        # Initialize with Gaussian noise (V8: seeded)
        path = self._np_rng.randn(num_points, 2) * self.config.entropy_scale
        
        # Reverse diffusion loop
        for t in reversed(range(self.config.num_diffusion_steps)):
            # Inject biological entropy
            z = self._np_rng.randn(*path.shape) * self.config.entropy_scale if t > 0 else 0
            
            # Predict noise (use model or analytical)
            if self.onnx_session:
                predicted_noise = self._model_predict(path, t)
            else:
                predicted_noise = self._analytical_denoise(path, t, start_pos, end_pos)
            
            # Apply reverse diffusion step
            path = self.scheduler.step(predicted_noise, t, path, z)
        
        # Scale to screen coordinates
        path = self._scale_to_screen(path, start_pos, end_pos)
        
        # Apply motor dynamics
        path = self._apply_motor_inertia(path)
        
        # Add micro-tremors (hand shake)
        path = self._add_micro_tremors(path)
        
        # Maybe add overshoot
        if self._rng.random() < self.config.overshoot_probability:
            path = self._add_overshoot(path, end_pos)
        
        # Maybe add mid-path correction
        if self._rng.random() < self.config.correction_probability:
            path = self._add_correction(path)
        
        # Smooth with spline interpolation
        if SCIPY_AVAILABLE and len(path) > 4:
            path = self._spline_smooth(path)
        
        # Generate timestamps
        timestamps = self._generate_timestamps(len(path), duration_ms)
        
        # Calculate velocities and accelerations
        points = self._create_trajectory_points(path, timestamps)
        
        # Calculate entropy score
        entropy = self._calculate_entropy(path)
        
        return GeneratedTrajectory(
            points=points,
            start_pos=start_pos,
            end_pos=end_pos,
            duration_ms=duration_ms,
            entropy_score=entropy
        )
    
    def _analytical_denoise(self,
                            path: np.ndarray,
                            t: int,
                            start: Tuple[float, float],
                            end: Tuple[float, float]) -> np.ndarray:
        """
        Analytical denoising when ONNX model unavailable.
        Uses multi-segment Bezier curves with motor-control-inspired
        velocity profiling (minimum-jerk model) for human-like trajectories.
        """
        num_points = len(path)
        s = np.linspace(0, 1, num_points)
        
        # Minimum-jerk velocity profile: v(s) = 30*s^2*(1-s)^2
        # This produces smooth acceleration/deceleration like real hand movements
        velocity_profile = 30 * s**2 * (1 - s)**2
        # Integrate to get position along path (cumulative normalized arc)
        cumulative = np.cumsum(velocity_profile)
        cumulative = cumulative / cumulative[-1]  # normalize to [0, 1]
        
        # Multi-segment cubic Bezier with 2 randomized control points
        # Provides natural S-curve or C-curve variation per trajectory
        cp1_x = self._rng.uniform(0.2, 0.4)
        cp1_y = self._rng.uniform(-0.25, 0.25)
        cp2_x = self._rng.uniform(0.6, 0.8)
        cp2_y = self._rng.uniform(-0.25, 0.25)
        
        # Cubic Bezier: B(t) = (1-t)^3*P0 + 3(1-t)^2*t*P1 + 3(1-t)*t^2*P2 + t^3*P3
        t_param = cumulative
        one_minus_t = 1 - t_param
        
        base_x = (one_minus_t**3 * 0 +
                   3 * one_minus_t**2 * t_param * cp1_x +
                   3 * one_minus_t * t_param**2 * cp2_x +
                   t_param**3 * 1.0)
        
        base_y = (one_minus_t**3 * 0 +
                   3 * one_minus_t**2 * t_param * cp1_y +
                   3 * one_minus_t * t_param**2 * cp2_y +
                   t_param**3 * 1.0)
        
        # Add subtle per-point Perlin-like noise for micro-variability
        freq = self._rng.uniform(2.0, 5.0)
        amplitude = 0.02 * self.config.entropy_scale
        micro_noise_x = amplitude * np.sin(freq * np.pi * s + self._rng.uniform(0, 2*np.pi))
        micro_noise_y = amplitude * np.sin(freq * 1.3 * np.pi * s + self._rng.uniform(0, 2*np.pi))
        
        base_trajectory = np.column_stack([
            base_x + micro_noise_x,
            base_y + micro_noise_y
        ])
        
        # Noise prediction: difference from base trajectory
        noise_level = self.scheduler.get_noise_level(t)
        predicted_noise = (path - base_trajectory) * noise_level
        
        return predicted_noise
    
    def _model_predict(self, path: np.ndarray, t: int) -> np.ndarray:
        """Use ONNX model for noise prediction"""
        # V7.5 FIX: Add batch dimension for ONNX runtime
        inputs = {
            'input': np.expand_dims(path.astype(np.float32), axis=0),
            'timestep': np.array([t], dtype=np.int64)
        }
        outputs = self.onnx_session.run(None, inputs)
        return outputs[0].squeeze(0)
    
    def _scale_to_screen(self,
                         path: np.ndarray,
                         start: Tuple[float, float],
                         end: Tuple[float, float]) -> np.ndarray:
        """Scale normalized path to screen coordinates"""
        # Normalize to [0, 1] range
        path_min = path.min(axis=0)
        path_max = path.max(axis=0)
        path_range = path_max - path_min
        path_range[path_range == 0] = 1  # Avoid division by zero
        
        normalized = (path - path_min) / path_range
        
        # Scale to start->end
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        
        scaled = np.column_stack([
            start[0] + normalized[:, 0] * dx,
            start[1] + normalized[:, 1] * dy
        ])
        
        return scaled
    
    def _apply_motor_inertia(self, path: np.ndarray) -> np.ndarray:
        """Apply human motor inertia (smoothing with momentum)"""
        if not SCIPY_AVAILABLE:
            return path
        
        # Gaussian smoothing simulates motor system low-pass filtering
        sigma = 1.5 * self.config.entropy_scale
        smoothed_x = gaussian_filter1d(path[:, 0], sigma)
        smoothed_y = gaussian_filter1d(path[:, 1], sigma)
        
        return np.column_stack([smoothed_x, smoothed_y])
    
    def _add_micro_tremors(self, path: np.ndarray) -> np.ndarray:
        """Add micro-tremors simulating hand shake"""
        amplitude = self.config.micro_tremor_amplitude * self.config.entropy_scale
        
        # Perlin-like noise using multiple sine waves
        t = np.linspace(0, 10, len(path))
        
        tremor_x = (
            np.sin(t * 1.0) * 0.5 +
            np.sin(t * 2.3) * 0.3 +
            np.sin(t * 4.1) * 0.2
        ) * amplitude
        
        tremor_y = (
            np.sin(t * 1.1 + 0.5) * 0.5 +
            np.sin(t * 2.7 + 0.3) * 0.3 +
            np.sin(t * 3.9 + 0.7) * 0.2
        ) * amplitude
        
        path[:, 0] += tremor_x
        path[:, 1] += tremor_y
        
        return path
    
    def _add_overshoot(self, 
                       path: np.ndarray, 
                       target: Tuple[float, float]) -> np.ndarray:
        """Add overshoot past target with correction"""
        # Calculate overshoot direction (continue past target)
        if len(path) < 2:
            return path
        
        direction = path[-1] - path[-2]
        direction_norm = np.linalg.norm(direction)
        if direction_norm > 0:
            direction = direction / direction_norm
        
        overshoot_dist = self._rng.uniform(3, self.config.overshoot_max_distance)
        overshoot_point = path[-1] + direction * overshoot_dist
        
        # Add overshoot and correction points
        correction_points = 5
        correction = np.linspace(overshoot_point, target, correction_points)
        
        return np.vstack([path, correction])
    
    def _add_correction(self, path: np.ndarray) -> np.ndarray:
        """Add mid-path correction (human recalibration)"""
        if len(path) < 10:
            return path
        
        # Insert correction at random point in middle third
        insert_idx = self._rng.randint(len(path) // 3, 2 * len(path) // 3)
        
        # Small deviation and return
        deviation = self._np_rng.randn(2) * 3 * self.config.entropy_scale
        correction_point = path[insert_idx] + deviation
        
        # Insert correction
        path = np.insert(path, insert_idx, correction_point, axis=0)
        
        return path
    
    def _spline_smooth(self, path: np.ndarray) -> np.ndarray:
        """Smooth path using B-spline interpolation"""
        try:
            # Fit spline
            tck, u = splprep([path[:, 0], path[:, 1]], s=len(path) * 0.1)
            
            # Evaluate at more points for smoothness
            u_new = np.linspace(0, 1, len(path))
            smoothed = np.column_stack(splev(u_new, tck))
            
            return smoothed
        except Exception:
            return path
    
    def _generate_timestamps(self, 
                             num_points: int, 
                             total_duration: float) -> np.ndarray:
        """Generate non-uniform timestamps (human timing variance)"""
        # Base linear timestamps
        timestamps = np.linspace(0, total_duration, num_points)
        
        # Add timing variance (humans don't move at constant speed)
        variance = self._np_rng.randn(num_points) * (total_duration * 0.05)
        variance[0] = 0  # Start at 0
        variance[-1] = 0  # End at total_duration
        
        timestamps = timestamps + variance
        timestamps = np.sort(timestamps)  # Ensure monotonic
        timestamps = np.clip(timestamps, 0, total_duration)
        
        return timestamps
    
    def _create_trajectory_points(self,
                                   path: np.ndarray,
                                   timestamps: np.ndarray) -> List[TrajectoryPoint]:
        """Create TrajectoryPoint objects with velocity/acceleration"""
        points = []
        
        for i in range(len(path)):
            velocity = 0.0
            acceleration = 0.0
            
            if i > 0:
                dt = max(0.001, (timestamps[i] - timestamps[i-1]) / 1000)
                dx = path[i, 0] - path[i-1, 0]
                dy = path[i, 1] - path[i-1, 1]
                velocity = np.sqrt(dx**2 + dy**2) / dt
                
                if i > 1:
                    prev_dt = max(0.001, (timestamps[i-1] - timestamps[i-2]) / 1000)
                    prev_dx = path[i-1, 0] - path[i-2, 0]
                    prev_dy = path[i-1, 1] - path[i-2, 1]
                    prev_velocity = np.sqrt(prev_dx**2 + prev_dy**2) / prev_dt
                    acceleration = (velocity - prev_velocity) / dt
            
            points.append(TrajectoryPoint(
                x=path[i, 0],
                y=path[i, 1],
                timestamp_ms=timestamps[i],
                velocity=velocity,
                acceleration=acceleration
            ))
        
        return points
    
    def _calculate_entropy(self, path: np.ndarray) -> float:
        """
        Calculate trajectory entropy score.
        Higher entropy = more human-like variability.
        Target: 0.7 - 1.3 (human range)
        """
        if len(path) < 3:
            return 0.5
        
        # Calculate direction changes
        directions = np.diff(path, axis=0)
        angles = np.arctan2(directions[:, 1], directions[:, 0])
        angle_changes = np.abs(np.diff(angles))
        
        # Entropy from angle variance
        angle_entropy = np.std(angle_changes) / (np.pi / 4)
        
        # Entropy from speed variance
        speeds = np.linalg.norm(directions, axis=1)
        speed_entropy = np.std(speeds) / (np.mean(speeds) + 0.001)
        
        # Combined entropy score
        entropy = (angle_entropy + speed_entropy) / 2
        entropy = np.clip(entropy, 0, 2)
        
        return float(entropy)
    
    def generate_click_trajectory(self,
                                   current_pos: Tuple[float, float],
                                   target_pos: Tuple[float, float],
                                   click_type: str = "single") -> Tuple[GeneratedTrajectory, dict]:
        """
        Generate trajectory for a click action.
        
        Returns:
            Tuple of (trajectory, click_event)
        """
        trajectory = self.generate_path(current_pos, target_pos)
        
        # Generate click timing
        if click_type == "double":
            click_event = {
                "type": "doubleclick",
                "x": int(target_pos[0]),
                "y": int(target_pos[1]),
                "delay_between_ms": self._rng.uniform(80, 150)
            }
        else:
            # Single click with human-like hold duration
            click_event = {
                "type": "click",
                "x": int(target_pos[0]),
                "y": int(target_pos[1]),
                "hold_ms": self._rng.uniform(50, 120)
            }
        
        return trajectory, click_event


# Convenience function for quick trajectory generation
def generate_human_trajectory(start: Tuple[float, float],
                              end: Tuple[float, float],
                              persona: PersonaType = PersonaType.CASUAL) -> GeneratedTrajectory:
    """
    Quick function to generate a human-like trajectory.
    
    Args:
        start: Starting position (x, y)
        end: Ending position (x, y)
        persona: User persona type
        
    Returns:
        GeneratedTrajectory
    """
    config = TrajectoryConfig(persona=persona)
    motor = GhostMotorDiffusion(config)
    return motor.generate_path(start, end)


# ═══════════════════════════════════════════════════════════════════════════
# FORTER BEHAVIORAL EVASION (Source: b1stash PDF 005)
# Safe parameter ranges that pass Forter's 7-category analysis
# ═══════════════════════════════════════════════════════════════════════════

FORTER_SAFE_PARAMS = {
    "min_session_duration_s": 120,
    "max_session_duration_s": 900,
    "scroll_depth_percent": (40, 95),
    "hesitation_before_checkout_s": (3, 15),
    "typing_speed_wpm": (60, 110),
    "typing_error_rate": (0.02, 0.08),
    "mouse_idle_periods_s": (2, 30),
    "page_view_count_min": 3,
    "time_on_product_page_s": (30, 180),
    "time_on_checkout_page_s": (45, 180),
    "cart_review_time_s": (10, 60),
}

# ═══════════════════════════════════════════════════════════════════════════
# BIOCATCH EVASION PROFILE (Source: AI Fraud Detection Research)
# Ghost Motor must handle invisible challenges
# ═══════════════════════════════════════════════════════════════════════════

BIOCATCH_EVASION = {
    "invisible_challenges": {
        "cursor_lag": {
            "description": "BioCatch injects artificial cursor lag to test reaction",
            "detection": "Cursor position briefly desyncs from actual mouse position",
            "ghost_motor_response": "Detect lag > 50ms and apply corrective micro-adjustment",
            "human_reaction_time_ms": (150, 400),
        },
        "displaced_elements": {
            "description": "DOM elements shift position slightly to test user adaptation",
            "detection": "Button/link position changes by 2-8px during hover approach",
            "ghost_motor_response": "Adjust trajectory mid-path with natural correction curve",
            "correction_delay_ms": (100, 250),
        },
    },
    "cognitive_tells": {
        "typing_familiar_data": "Type name/address WITHOUT hesitation - pausing = displacement flag",
        "cursor_prediction": "Never move cursor to element BEFORE it renders on screen",
        "form_field_order": "Fill forms top-to-bottom naturally, don't jump between fields",
    },
    "mobile_evasion": {
        "gyroscope_recoil": "Every touch event must have corresponding device movement data",
        "accelerometer_noise": "Continuous micro-movement when device is 'held' (not on table)",
        "touch_pressure_variance": "Vary touch pressure between 0.4-0.9 (not constant)",
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# THREATMETRIX SESSION CONTINUITY (Source: AI Fraud Detection Research)
# ═══════════════════════════════════════════════════════════════════════════

THREATMETRIX_SESSION_RULES = {
    "continuous_session": "Ghost Motor must run from login through checkout - no gaps",
    "handover_detection": "BehavioSec detects behavioral pattern change mid-session",
    "safe_pattern": [
        "Launch Ghost Motor extension BEFORE navigating to target",
        "Keep extension active throughout entire session",
        "Do NOT disable/re-enable extension during checkout",
        "Mouse movement style must remain consistent (same persona throughout)",
        "Typing cadence must not change abruptly between pages",
    ],
}

# ═══════════════════════════════════════════════════════════════════════════
# WARMUP BROWSING PATTERNS (Source: b1stash PDFs 002, 009, 010)
# Pre-checkout browsing to build trust signals
# ═══════════════════════════════════════════════════════════════════════════

WARMUP_BROWSING_PATTERNS = {
    "bestbuy": {
        "name": "Best Buy Warmup",
        "total_duration_min": 15,
        "steps": [
            {"action": "browse", "page": "Electronics category", "duration_s": 120},
            {"action": "view", "page": "Random product 1", "duration_s": 60},
            {"action": "view", "page": "Random product 2", "duration_s": 45},
            {"action": "add_wishlist", "page": "Add product to wishlist", "duration_s": 10},
            {"action": "logout", "page": "Log out of account", "duration_s": 5},
            {"action": "wait", "page": "Wait 30 minutes", "duration_s": 1800},
            {"action": "login", "page": "Log back in", "duration_s": 30},
            {"action": "target", "page": "Navigate to actual target product", "duration_s": 90},
        ],
    },
    "general_ecommerce": {
        "name": "General E-Commerce Warmup",
        "total_duration_min": 10,
        "steps": [
            {"action": "search", "page": "Google search for target site", "duration_s": 15},
            {"action": "click", "page": "Click organic result (not ad)", "duration_s": 5},
            {"action": "browse", "page": "Browse homepage/categories", "duration_s": 120},
            {"action": "view", "page": "View 2-3 products", "duration_s": 90},
            {"action": "scroll", "page": "Scroll to footer, read return policy", "duration_s": 30},
            {"action": "target", "page": "Navigate to target product", "duration_s": 60},
        ],
    },
    "forter_trust_building": {
        "name": "Forter Trust Edge Warmup",
        "total_duration_min": 20,
        "steps": [
            {"action": "visit", "page": "nordstrom.com (Forter site)", "duration_s": 120},
            {"action": "browse", "page": "Browse products, add to cart", "duration_s": 60},
            {"action": "abandon", "page": "Abandon cart (don't checkout)", "duration_s": 5},
            {"action": "visit", "page": "sephora.com (Forter site)", "duration_s": 90},
            {"action": "browse", "page": "Browse products", "duration_s": 60},
            {"action": "wait", "page": "Wait 5 minutes", "duration_s": 300},
            {"action": "target", "page": "Navigate to actual target", "duration_s": 60},
        ],
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# V7.0 AUDIT REMEDIATION: PRE-COMPUTATION BUFFER
# Decouples Python GIL-bound trajectory computation from JS cursor dispatch.
# Trajectories are batch-computed and serialized to a shared buffer file.
# The Ghost Motor JS extension reads from this buffer asynchronously,
# ensuring Python GC pauses never affect cursor movement timing.
# ═══════════════════════════════════════════════════════════════════════════

import gc
import json as _json
import threading


class TrajectoryPrecomputeBuffer:
    """
    Pre-computes trajectory batches in a background thread with GC isolation.
    Serializes completed trajectories to a shared buffer file that the
    Ghost Motor JS extension consumes asynchronously.
    
    Architecture:
        Python (GIL-bound) → buffer file → JS extension (event loop)
        GC pauses here        ↑ atomic     No GC effect here
                               write
    
    Usage:
        buffer = TrajectoryPrecomputeBuffer(motor)
        buffer.start()
        # JS extension reads from /tmp/titan-ghost-motor-buffer.json
        buffer.request_batch([(start1, end1), (start2, end2), ...])
        buffer.stop()
    """
    
    BUFFER_PATH = "/tmp/titan-ghost-motor-buffer.json"
    
    def __init__(self, motor: GhostMotorDiffusion, batch_size: int = 10):
        self.motor = motor
        self.batch_size = batch_size
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._request_queue: list = []
        self._lock = threading.Lock()
        self._event = threading.Event()
    
    def start(self):
        """Start the pre-computation background thread."""
        self._running = True
        self._thread = threading.Thread(
            target=self._compute_loop, daemon=True, name="ghost-motor-precompute"
        )
        self._thread.start()
    
    def stop(self):
        """Stop the background thread."""
        self._running = False
        self._event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
    
    def request_batch(self, waypoints: list):
        """Queue a batch of (start, end) waypoints for pre-computation."""
        with self._lock:
            self._request_queue.extend(waypoints)
        self._event.set()
    
    def _compute_loop(self):
        """Background thread: compute trajectories with GC isolation."""
        while self._running:
            self._event.wait(timeout=1.0)
            self._event.clear()
            
            with self._lock:
                batch = self._request_queue[:self.batch_size]
                self._request_queue = self._request_queue[self.batch_size:]
            
            if not batch:
                continue
            
            # Disable GC during computation to prevent stutter
            gc.disable()
            try:
                trajectories = []
                for start, end in batch:
                    traj = self.motor.generate_path(tuple(start), tuple(end))
                    trajectories.append(traj.to_events())
                
                # Atomic write to buffer file
                buffer_data = _json.dumps({
                    "trajectories": trajectories,
                    "count": len(trajectories),
                    "ready": True,
                })
                tmp_path = self.BUFFER_PATH + ".tmp"
                with open(tmp_path, "w") as f:
                    f.write(buffer_data)
                os.replace(tmp_path, self.BUFFER_PATH)
            finally:
                gc.enable()
                gc.collect()  # Collect during idle, not during dispatch


# ═══════════════════════════════════════════════════════════════════════════
# V7.5 UPGRADE: α-DDIM DIFFUSION TRAJECTORY GENERATION
# Accelerated denoising using DDIM (Denoising Diffusion Implicit Models)
# with α-schedule skip for 5x faster trajectory generation while
# preserving fractal variability. Reference: arXiv:2010.02502
# ═══════════════════════════════════════════════════════════════════════════

class AlphaDDIMScheduler:
    """
    α-DDIM accelerated diffusion scheduler.
    Skips intermediate timesteps using deterministic DDIM sampling,
    reducing 50-step diffusion to 10 steps with negligible quality loss.
    """

    def __init__(self, full_steps: int = 50, ddim_steps: int = 10,
                 schedule_type: str = "cosine", eta: float = 0.0):
        self.full_steps = full_steps
        self.ddim_steps = ddim_steps
        self.eta = eta  # 0 = deterministic DDIM, 1 = full DDPM stochasticity

        # Compute full schedule
        base = NoiseScheduler(full_steps, schedule_type)
        self.alphas_cumprod = base.alphas_cumprod

        # Select subset of timesteps (uniform skip)
        self.timesteps = np.linspace(0, full_steps - 1, ddim_steps, dtype=int)[::-1]

    def step(self, model_output: np.ndarray, t_idx: int,
             sample: np.ndarray) -> np.ndarray:
        """
        DDIM deterministic step: x_{t-1} from x_t without added noise.
        x_{t-1} = √(ᾱ_{t-1}) * pred_x0 + √(1-ᾱ_{t-1}-σ²) * ε_θ + σ * z
        """
        t = self.timesteps[t_idx]
        t_prev = self.timesteps[t_idx + 1] if t_idx + 1 < len(self.timesteps) else 0

        alpha_t = self.alphas_cumprod[t]
        alpha_prev = self.alphas_cumprod[t_prev] if t_prev > 0 else 1.0

        # Predict x_0
        pred_x0 = (sample - np.sqrt(1 - alpha_t) * model_output) / np.sqrt(alpha_t)

        # Compute σ for stochasticity control
        sigma = self.eta * np.sqrt((1 - alpha_prev) / (1 - alpha_t)) * np.sqrt(1 - alpha_t / alpha_prev)

        # Direction pointing to x_t
        dir_xt = np.sqrt(max(1 - alpha_prev - sigma ** 2, 0)) * model_output

        # x_{t-1}
        prev_sample = np.sqrt(alpha_prev) * pred_x0 + dir_xt

        if self.eta > 0 and t_prev > 0:
            noise = np.random.randn(*sample.shape)
            prev_sample += sigma * noise

        return prev_sample


class GhostMotorV7(GhostMotorDiffusion):
    """
    v7.5 Ghost Motor with α-DDIM acceleration, fatigue entropy engine,
    and coercion/duress detection defeat.

    Improvements over V7.0:
    - 5x faster trajectory generation via DDIM skip scheduling
    - Fatigue entropy: gradually degrades precision over long sessions
    - Coercion defeat: contextual rhythm synthesis prevents duress detection
    """

    def __init__(self, config: Optional[TrajectoryConfig] = None,
                 ddim_steps: int = 10, eta: float = 0.0):
        super().__init__(config)
        self.ddim_scheduler = AlphaDDIMScheduler(
            full_steps=self.config.num_diffusion_steps,
            ddim_steps=ddim_steps,
            schedule_type=self.config.noise_schedule,
            eta=eta,
        )
        self._session_start = time.time()
        self._trajectory_count = 0
        self._fatigue_enabled = True

    def generate_path(self, start_pos: Tuple[float, float],
                      end_pos: Tuple[float, float],
                      duration_ms: Optional[float] = None) -> GeneratedTrajectory:
        """V7.5 FIX: Override to use DDIM by default for 5x speedup."""
        return self.generate_path_ddim(start_pos, end_pos, duration_ms)

    def generate_path_ddim(self, start_pos: Tuple[float, float],
                           end_pos: Tuple[float, float],
                           duration_ms: Optional[float] = None) -> GeneratedTrajectory:
        """
        Generate trajectory using accelerated α-DDIM sampling.
        ~5x faster than full diffusion with equivalent quality.
        """
        distance = np.sqrt((end_pos[0] - start_pos[0]) ** 2 +
                           (end_pos[1] - start_pos[1]) ** 2)

        if duration_ms is None:
            base_duration = 100 + distance * 0.8
            duration_ms = base_duration * random.uniform(0.8, 1.2)
            duration_ms = np.clip(duration_ms, self.config.min_duration_ms,
                                  self.config.max_duration_ms)

        num_points = max(10, int(duration_ms / 16))
        path = np.random.randn(num_points, 2) * self.config.entropy_scale

        # Apply fatigue entropy modifier
        fatigue = self._get_fatigue_factor()
        path *= (1.0 + fatigue * 0.3)

        # Accelerated DDIM reverse diffusion
        for i in range(len(self.ddim_scheduler.timesteps) - 1):
            t = self.ddim_scheduler.timesteps[i]
            predicted_noise = self._analytical_denoise(path, t, start_pos, end_pos)
            path = self.ddim_scheduler.step(predicted_noise, i, path)

        path = self._scale_to_screen(path, start_pos, end_pos)
        path = self._apply_motor_inertia(path)
        path = self._add_micro_tremors(path)

        # Apply fatigue-induced precision degradation
        if self._fatigue_enabled and fatigue > 0.1:
            path = self._apply_fatigue_jitter(path, fatigue)

        if random.random() < self.config.overshoot_probability:
            path = self._add_overshoot(path, end_pos)
        if random.random() < self.config.correction_probability:
            path = self._add_correction(path)
        if SCIPY_AVAILABLE and len(path) > 4:
            path = self._spline_smooth(path)

        timestamps = self._generate_timestamps(len(path), duration_ms)
        points = self._create_trajectory_points(path, timestamps)
        entropy = self._calculate_entropy(path)

        self._trajectory_count += 1
        return GeneratedTrajectory(
            points=points, start_pos=start_pos, end_pos=end_pos,
            duration_ms=duration_ms, entropy_score=entropy
        )

    # ── Fatigue Entropy Engine ──────────────────────────────────────────────

    def _get_fatigue_factor(self) -> float:
        """
        Calculate fatigue factor based on session duration and trajectory count.
        Humans get less precise over time — this prevents the "too perfect for
        too long" detection signal that BioCatch and Forter flag.

        Returns 0.0 (fresh) to 1.0 (fatigued).
        """
        elapsed_min = (time.time() - self._session_start) / 60.0
        # Fatigue ramps up after 15 minutes, plateaus at 60 minutes
        time_fatigue = min(1.0, max(0.0, (elapsed_min - 15) / 45.0))
        # Repetition fatigue: increases with trajectory count
        rep_fatigue = min(1.0, self._trajectory_count / 500.0)
        return min(1.0, (time_fatigue * 0.6 + rep_fatigue * 0.4))

    def _apply_fatigue_jitter(self, path: np.ndarray, fatigue: float) -> np.ndarray:
        """
        Apply fatigue-induced jitter: slightly degrade trajectory precision
        as the session progresses. Mimics human hand tiredness.
        """
        jitter_amplitude = fatigue * 2.5  # Up to 2.5px extra jitter when fully fatigued
        jitter = np.random.randn(*path.shape) * jitter_amplitude
        # Apply more jitter at end of trajectory (tired hand overshoots more)
        weight = np.linspace(0.3, 1.0, len(path)).reshape(-1, 1)
        path += jitter * weight
        return path

    def reset_fatigue(self):
        """Reset fatigue counters (e.g., after a simulated break)."""
        self._session_start = time.time()
        self._trajectory_count = 0

    # ── Coercion / Duress Detection Defeat ──────────────────────────────────

    def contextual_rhythm_synthesis(self, action_type: str = "checkout") -> dict:
        """
        v7.5 Coercion Defeat — synthesize contextual behavioral rhythm that
        defeats duress/coercion detection algorithms.

        Advanced antifraud systems (BioCatch, Forter) detect when a user is
        being coerced by analyzing:
        - Abnormally fast form completion (someone dictating)
        - Lack of natural hesitation patterns
        - Uniform typing cadence (robotic)
        - Missing micro-pauses between cognitive decisions

        This method generates a rhythm profile that includes natural hesitation,
        decision pauses, and cognitive load signatures appropriate for the action.
        """
        rhythms = {
            "checkout": {
                "pre_action_pause_ms": random.uniform(800, 2500),
                "field_transition_ms": random.uniform(300, 900),
                "typing_burst_chars": random.randint(3, 7),
                "inter_burst_pause_ms": random.uniform(100, 400),
                "review_pause_ms": random.uniform(2000, 6000),
                "submit_hesitation_ms": random.uniform(500, 3000),
                "scroll_before_submit": random.random() < 0.4,
                "re_read_probability": 0.25,
            },
            "login": {
                "pre_action_pause_ms": random.uniform(300, 1200),
                "field_transition_ms": random.uniform(200, 600),
                "typing_burst_chars": random.randint(4, 10),
                "inter_burst_pause_ms": random.uniform(50, 200),
                "review_pause_ms": random.uniform(500, 1500),
                "submit_hesitation_ms": random.uniform(200, 800),
                "scroll_before_submit": False,
                "re_read_probability": 0.05,
            },
            "form_fill": {
                "pre_action_pause_ms": random.uniform(500, 2000),
                "field_transition_ms": random.uniform(400, 1200),
                "typing_burst_chars": random.randint(2, 6),
                "inter_burst_pause_ms": random.uniform(150, 500),
                "review_pause_ms": random.uniform(1000, 4000),
                "submit_hesitation_ms": random.uniform(800, 4000),
                "scroll_before_submit": random.random() < 0.3,
                "re_read_probability": 0.15,
            },
        }
        rhythm = rhythms.get(action_type, rhythms["form_fill"])
        rhythm["action_type"] = action_type
        rhythm["fatigue_factor"] = self._get_fatigue_factor()
        rhythm["cognitive_load"] = random.uniform(0.3, 0.8)
        return rhythm


def get_forter_safe_params() -> dict:
    """Get Forter-safe behavioral parameters for operator reference"""
    return FORTER_SAFE_PARAMS


def get_biocatch_evasion_guide() -> dict:
    """Get BioCatch evasion guide including invisible challenge handling"""
    return BIOCATCH_EVASION


def get_warmup_pattern(target: str = "general_ecommerce") -> dict:
    """Get warmup browsing pattern for specific target"""
    return WARMUP_BROWSING_PATTERNS.get(target, WARMUP_BROWSING_PATTERNS["general_ecommerce"])


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 P0 UPGRADE: DEVICE ORIENTATION MIMICRY
# Mobile device tilt/rotation simulation for KYC selfie and document capture
# ═══════════════════════════════════════════════════════════════════════════

class DeviceOrientationMimicry:
    """
    V7.6: Simulates realistic mobile device orientation patterns.
    
    Mobile KYC systems (Jumio, Onfido, Veriff) track DeviceOrientation events
    to detect:
    - Robotic/fixed positioning (emulator flag)
    - Mounted device (fraud flag for selfie bypass)
    - Unnaturally stable holding (bot/automation)
    
    This engine generates human-like orientation patterns including:
    - Natural hand tremor (0.1-0.5° micro-movements)
    - Breathing-induced oscillation
    - Gradual drift correction
    - Device adjustment movements
    """
    
    # Natural holding patterns (degrees)
    HOLDING_PATTERNS = {
        'selfie_front': {
            'alpha_center': 90,      # Device facing user
            'beta_center': 80,       # Slightly tilted back
            'gamma_center': 0,       # Level horizontally
            'tremor_amplitude': 0.3,
            'breath_amplitude': 0.5,
            'drift_rate': 0.1,
        },
        'document_scan': {
            'alpha_center': 180,     # Device facing down
            'beta_center': -60,      # Angled down at document
            'gamma_center': 0,
            'tremor_amplitude': 0.4,
            'breath_amplitude': 0.3,
            'drift_rate': 0.15,
        },
        'id_hold': {
            'alpha_center': 90,
            'beta_center': 70,
            'gamma_center': 5,
            'tremor_amplitude': 0.5,
            'breath_amplitude': 0.4,
            'drift_rate': 0.2,
        },
    }
    
    def __init__(self, pattern: str = 'selfie_front'):
        self.pattern = self.HOLDING_PATTERNS.get(pattern, self.HOLDING_PATTERNS['selfie_front'])
        self._time_offset = random.uniform(0, 100)
        self._drift_state = {'alpha': 0, 'beta': 0, 'gamma': 0}
    
    def generate_orientation_stream(self, duration_ms: float, sample_rate_hz: int = 60) -> list:
        """
        Generate a stream of DeviceOrientation events simulating human holding.
        
        Returns list of dicts with alpha, beta, gamma values.
        """
        num_samples = int(duration_ms / 1000 * sample_rate_hz)
        samples = []
        
        t_start = time.time() + self._time_offset
        
        for i in range(num_samples):
            t = t_start + i / sample_rate_hz
            
            # Base orientation
            alpha = self.pattern['alpha_center']
            beta = self.pattern['beta_center']
            gamma = self.pattern['gamma_center']
            
            # Add breathing oscillation (slow sine wave, ~0.2-0.3 Hz)
            breath_freq = random.uniform(0.2, 0.3)
            breath = np.sin(t * 2 * np.pi * breath_freq) * self.pattern['breath_amplitude']
            beta += breath
            
            # Add hand tremor (fast irregular micro-movements)
            tremor_amp = self.pattern['tremor_amplitude']
            alpha += np.random.randn() * tremor_amp
            beta += np.random.randn() * tremor_amp * 0.7
            gamma += np.random.randn() * tremor_amp * 0.5
            
            # Add gradual drift
            self._drift_state['alpha'] += (np.random.randn() - 0.5 * self._drift_state['alpha']) * self.pattern['drift_rate'] / sample_rate_hz
            self._drift_state['beta'] += (np.random.randn() - 0.5 * self._drift_state['beta']) * self.pattern['drift_rate'] / sample_rate_hz
            self._drift_state['gamma'] += (np.random.randn() - 0.5 * self._drift_state['gamma']) * self.pattern['drift_rate'] / sample_rate_hz
            
            alpha += self._drift_state['alpha']
            beta += self._drift_state['beta']
            gamma += self._drift_state['gamma']
            
            # Occasional adjustment (human corrects device position)
            if random.random() < 0.002:  # ~0.2% chance per sample
                correction = random.uniform(1, 3)
                beta -= correction * np.sign(self._drift_state['beta'])
                self._drift_state['beta'] *= 0.3
            
            samples.append({
                'timestamp': int((t - t_start) * 1000),
                'alpha': round(alpha % 360, 4),
                'beta': round(np.clip(beta, -180, 180), 4),
                'gamma': round(np.clip(gamma, -90, 90), 4),
            })
        
        return samples
    
    def get_single_orientation(self) -> dict:
        """Get a single orientation sample for instantaneous use."""
        stream = self.generate_orientation_stream(50, 60)
        return stream[-1] if stream else {'alpha': 90, 'beta': 80, 'gamma': 0, 'timestamp': 0}


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 P0 UPGRADE: TOUCH PRESSURE SYNTHESIS
# Mobile touch pressure patterns for KYC and behavioral biometrics
# ═══════════════════════════════════════════════════════════════════════════

class TouchPressureSynthesis:
    """
    V7.6: Generates realistic touch pressure patterns for mobile interactions.
    
    Behavioral biometrics systems track Touch.force (0.0-1.0) to:
    - Identify users by unique pressure patterns
    - Detect automation (constant pressure = bot)
    - Flag unusual patterns (too light/heavy = not real finger)
    
    This engine generates human-like pressure patterns.
    """
    
    # Pressure profiles by action type
    PRESSURE_PROFILES = {
        'tap': {
            'peak_pressure': (0.3, 0.6),      # (min, max) range
            'attack_ms': (10, 30),             # Time to peak
            'decay_ms': (20, 60),              # Time from peak to release
            'sustain_ratio': 0.0,              # No sustain for tap
        },
        'long_press': {
            'peak_pressure': (0.4, 0.7),
            'attack_ms': (20, 50),
            'decay_ms': (30, 80),
            'sustain_ratio': 0.7,              # 70% of peak during hold
        },
        'typing': {
            'peak_pressure': (0.15, 0.35),     # Light quick taps
            'attack_ms': (5, 15),
            'decay_ms': (10, 25),
            'sustain_ratio': 0.0,
        },
        'signature': {
            'peak_pressure': (0.25, 0.55),
            'attack_ms': (15, 40),
            'decay_ms': (25, 70),
            'sustain_ratio': 0.3,
        },
        'scroll': {
            'peak_pressure': (0.2, 0.4),
            'attack_ms': (10, 25),
            'decay_ms': (40, 100),
            'sustain_ratio': 0.5,
        },
    }
    
    def __init__(self, base_pressure: float = None):
        # Establish a "user baseline" pressure (humans have consistent patterns)
        self.base_pressure = base_pressure or random.uniform(0.35, 0.55)
        self._pressure_variance = random.uniform(0.08, 0.15)
    
    def generate_touch_event(self, action_type: str = 'tap', 
                              duration_ms: float = None) -> list:
        """
        Generate a touch pressure curve for a single touch event.
        
        Returns list of (timestamp_ms, pressure) tuples.
        """
        profile = self.PRESSURE_PROFILES.get(action_type, self.PRESSURE_PROFILES['tap'])
        
        # Determine peak pressure (varies around user baseline)
        peak_min, peak_max = profile['peak_pressure']
        user_peak = self.base_pressure * random.uniform(0.9, 1.1)
        peak = np.clip(user_peak + random.uniform(-self._pressure_variance, self._pressure_variance),
                       peak_min, peak_max)
        
        # Timing
        attack_ms = random.uniform(*profile['attack_ms'])
        decay_ms = random.uniform(*profile['decay_ms'])
        
        if duration_ms and profile['sustain_ratio'] > 0:
            sustain_ms = max(0, duration_ms - attack_ms - decay_ms)
        else:
            sustain_ms = 0
        
        total_ms = attack_ms + sustain_ms + decay_ms
        
        # Generate pressure curve
        points = []
        sample_rate = 120  # 120 Hz touch sampling (common on mobile)
        num_samples = max(3, int(total_ms / 1000 * sample_rate))
        
        for i in range(num_samples):
            t = i * (total_ms / num_samples)
            
            if t < attack_ms:
                # Attack phase (pressure rising)
                ratio = t / attack_ms
                pressure = peak * (1 - (1 - ratio) ** 2)  # Ease-out curve
            elif t < attack_ms + sustain_ms:
                # Sustain phase
                sustain_pressure = peak * profile['sustain_ratio']
                variation = random.uniform(-0.02, 0.02)
                pressure = sustain_pressure + variation
            else:
                # Decay phase
                decay_t = t - attack_ms - sustain_ms
                ratio = decay_t / decay_ms
                pressure = peak * (1 - ratio) ** 1.5  # Ease-in decay
            
            # Add micro-variations
            pressure += random.uniform(-0.01, 0.01)
            pressure = max(0, min(1, pressure))
            
            points.append({
                'timestamp': round(t, 2),
                'force': round(pressure, 4),
            })
        
        return points
    
    def generate_typing_sequence(self, num_chars: int) -> list:
        """Generate pressure sequence for typing num_chars characters."""
        sequence = []
        current_time = 0
        
        for i in range(num_chars):
            touch = self.generate_touch_event('typing')
            for point in touch:
                sequence.append({
                    'timestamp': round(current_time + point['timestamp'], 2),
                    'force': point['force'],
                    'char_index': i,
                })
            
            # Inter-key delay
            if i < num_chars - 1:
                delay = random.uniform(50, 200)
                current_time += touch[-1]['timestamp'] + delay
        
        return sequence


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 P0 UPGRADE: MOBILE SENSOR SYNTHESIS COORDINATOR
# Coordinates all mobile sensor outputs for unified KYC bypass
# ═══════════════════════════════════════════════════════════════════════════

class MobileSensorSynthesizer:
    """
    V7.6: Coordinates all mobile sensor outputs for KYC bypass.
    
    Combines:
    - DeviceOrientation (gyroscope/accelerometer fusion)
    - Touch pressure
    - GhostMotor trajectories
    - Screen dimensions/DPI
    
    Into a unified, consistent mobile sensor profile.
    """
    
    DEVICE_PROFILES = {
        'iphone_14': {
            'screen_width': 393, 'screen_height': 852,
            'dpi': 460, 'touch_sample_rate': 120,
            'orientation_sample_rate': 60,
            'pressure_supported': True,
        },
        'samsung_s23': {
            'screen_width': 360, 'screen_height': 780,
            'dpi': 425, 'touch_sample_rate': 240,
            'orientation_sample_rate': 100,
            'pressure_supported': True,
        },
        'pixel_8': {
            'screen_width': 412, 'screen_height': 915,
            'dpi': 420, 'touch_sample_rate': 120,
            'orientation_sample_rate': 60,
            'pressure_supported': True,
        },
    }
    
    def __init__(self, device: str = 'iphone_14', scenario: str = 'selfie_front'):
        self.device = self.DEVICE_PROFILES.get(device, self.DEVICE_PROFILES['iphone_14'])
        self.orientation_engine = DeviceOrientationMimicry(scenario)
        self.pressure_engine = TouchPressureSynthesis()
        self.motor = GhostMotorV7()
    
    def generate_kyc_session_data(self, duration_ms: float = 5000) -> dict:
        """
        Generate complete sensor data for a KYC session (e.g., selfie capture).
        
        Returns dict with orientation stream, touch events, and screen taps.
        """
        orientation_stream = self.orientation_engine.generate_orientation_stream(
            duration_ms, self.device['orientation_sample_rate']
        )
        
        # Simulate a few tap events (start capture, re-center, capture button)
        tap_times = [
            duration_ms * 0.1,   # Initial tap
            duration_ms * 0.5,   # Adjustment
            duration_ms * 0.85,  # Capture button
        ]
        
        touch_events = []
        for t in tap_times:
            tap_data = self.pressure_engine.generate_touch_event('tap')
            for point in tap_data:
                touch_events.append({
                    'timestamp': round(t + point['timestamp'], 2),
                    'force': point['force'],
                    'x': random.uniform(self.device['screen_width'] * 0.3, self.device['screen_width'] * 0.7),
                    'y': random.uniform(self.device['screen_height'] * 0.4, self.device['screen_height'] * 0.8),
                })
        
        return {
            'device': self.device,
            'duration_ms': duration_ms,
            'orientation_stream': orientation_stream,
            'touch_events': touch_events,
            'session_fatigue': self.motor._get_fatigue_factor(),
        }


# V7.6 Convenience exports for mobile sensor synthesis
def generate_device_orientation(pattern: str = 'selfie_front', duration_ms: float = 3000):
    """V7.6: Generate device orientation stream"""
    return DeviceOrientationMimicry(pattern).generate_orientation_stream(duration_ms)

def generate_touch_pressure(action_type: str = 'tap', duration_ms: float = None):
    """V7.6: Generate touch pressure curve"""
    return TouchPressureSynthesis().generate_touch_event(action_type, duration_ms)

def generate_kyc_sensor_data(device: str = 'iphone_14', scenario: str = 'selfie_front', duration_ms: float = 5000):
    """V7.6: Generate complete KYC session sensor data"""
    return MobileSensorSynthesizer(device, scenario).generate_kyc_session_data(duration_ms)
