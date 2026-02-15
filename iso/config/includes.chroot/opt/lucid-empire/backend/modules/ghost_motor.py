#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  LUCID EMPIRE v7.0.0-TITAN :: GHOST MOTOR GAN MODULE                         ║
║  GAN-Based Human Behavioral Trajectory Generation                            ║
║  Authority: Dva.12 | Classification: ZERO DETECT                             ║
╚══════════════════════════════════════════════════════════════════════════════╝

Implements GAN-inspired mouse trajectory generation for human-like movement.
Features: Variable velocity, overshoot, micro-tremors, natural curves.

Reference: Bogazici Mouse Dynamics Dataset methodology
This is a lightweight implementation that generates realistic mouse paths
without requiring a full neural network (pure mathematical simulation).
"""

import math
import random
import time
import json
from typing import List, Tuple, Dict, Optional, Generator
from dataclasses import dataclass, field
from pathlib import Path
import hashlib


@dataclass
class Point:
    """2D point with optional timestamp"""
    x: float
    y: float
    timestamp: float = 0.0
    
    def distance_to(self, other: 'Point') -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)
    
    def to_dict(self) -> Dict:
        return {"x": self.x, "y": self.y, "t": self.timestamp}


@dataclass
class TrajectoryConfig:
    """Configuration for trajectory generation"""
    
    # Base movement speed (pixels per second)
    base_speed: float = 800.0
    speed_variance: float = 0.3  # ±30% variance
    
    # Overshoot parameters
    overshoot_probability: float = 0.15
    overshoot_factor: float = 0.08  # 8% past target
    
    # Micro-tremor parameters (simulates hand tremor)
    tremor_enabled: bool = True
    tremor_amplitude: float = 0.5  # pixels
    tremor_frequency: float = 12.0  # Hz
    
    # Path curvature
    curvature_factor: float = 0.3  # How curved the path is
    
    # Acceleration/deceleration
    acceleration_curve: str = "ease_in_out"  # ease_in, ease_out, ease_in_out, linear
    
    # Points per movement
    min_points: int = 20
    max_points: int = 80
    
    # Timing
    min_movement_time: float = 0.1  # seconds
    max_movement_time: float = 1.5  # seconds
    
    # Seed for reproducibility
    seed: Optional[int] = None


class BezierCurve:
    """
    Cubic Bezier curve implementation for smooth mouse paths.
    """
    
    @staticmethod
    def cubic(t: float, p0: float, p1: float, p2: float, p3: float) -> float:
        """Calculate point on cubic Bezier curve at parameter t"""
        return (
            (1 - t)**3 * p0 +
            3 * (1 - t)**2 * t * p1 +
            3 * (1 - t) * t**2 * p2 +
            t**3 * p3
        )
    
    @classmethod
    def get_point(
        cls, 
        t: float, 
        start: Point, 
        ctrl1: Point, 
        ctrl2: Point, 
        end: Point
    ) -> Point:
        """Get point on Bezier curve at parameter t ∈ [0, 1]"""
        return Point(
            x=cls.cubic(t, start.x, ctrl1.x, ctrl2.x, end.x),
            y=cls.cubic(t, start.y, ctrl1.y, ctrl2.y, end.y)
        )


class EasingFunctions:
    """
    Easing functions for natural acceleration/deceleration.
    """
    
    @staticmethod
    def linear(t: float) -> float:
        return t
    
    @staticmethod
    def ease_in(t: float) -> float:
        """Slow start, fast end"""
        return t * t * t
    
    @staticmethod
    def ease_out(t: float) -> float:
        """Fast start, slow end"""
        return 1 - (1 - t)**3
    
    @staticmethod
    def ease_in_out(t: float) -> float:
        """Slow start and end, fast middle"""
        if t < 0.5:
            return 4 * t * t * t
        else:
            return 1 - (-2 * t + 2)**3 / 2
    
    @staticmethod
    def ease_out_back(t: float) -> float:
        """Overshoot effect"""
        c1 = 1.70158
        c3 = c1 + 1
        return 1 + c3 * (t - 1)**3 + c1 * (t - 1)**2
    
    @classmethod
    def get(cls, name: str):
        """Get easing function by name"""
        functions = {
            "linear": cls.linear,
            "ease_in": cls.ease_in,
            "ease_out": cls.ease_out,
            "ease_in_out": cls.ease_in_out,
            "ease_out_back": cls.ease_out_back,
        }
        return functions.get(name, cls.ease_in_out)


class MicroTremorGenerator:
    """
    Generates realistic micro-tremors that simulate human hand movement.
    
    Based on physiological studies of hand tremor:
    - Frequency: 8-12 Hz (physiological tremor)
    - Amplitude: 0.5-2 pixels
    """
    
    def __init__(self, amplitude: float = 0.5, frequency: float = 12.0, seed: int = None):
        self.amplitude = amplitude
        self.frequency = frequency
        self.rng = random.Random(seed)
        
        # Pre-generate some noise values
        self.noise_x = [self.rng.gauss(0, 1) for _ in range(100)]
        self.noise_y = [self.rng.gauss(0, 1) for _ in range(100)]
    
    def get_tremor(self, t: float) -> Tuple[float, float]:
        """
        Get tremor offset at time t.
        
        Returns:
            (dx, dy) tremor offset
        """
        # Composite sine waves + noise
        phase_x = 2 * math.pi * self.frequency * t
        phase_y = 2 * math.pi * self.frequency * t + math.pi / 4
        
        # Get noise component
        noise_idx = int(t * 100) % 100
        noise_x = self.noise_x[noise_idx]
        noise_y = self.noise_y[noise_idx]
        
        # Combine sinusoidal and noise components
        dx = self.amplitude * (0.7 * math.sin(phase_x) + 0.3 * noise_x)
        dy = self.amplitude * (0.7 * math.sin(phase_y) + 0.3 * noise_y)
        
        return (dx, dy)


class GhostMotorGAN:
    """
    Main trajectory generator using GAN-inspired mathematical simulation.
    
    Generates human-like mouse movements with:
    - Natural curved paths (Bezier curves)
    - Variable velocity (easing functions)
    - Overshoot and correction
    - Micro-tremors
    - Realistic timing
    """
    
    def __init__(self, config: TrajectoryConfig = None):
        self.config = config or TrajectoryConfig()
        
        if self.config.seed is not None:
            random.seed(self.config.seed)
        
        self.tremor_gen = MicroTremorGenerator(
            amplitude=self.config.tremor_amplitude,
            frequency=self.config.tremor_frequency,
            seed=self.config.seed
        )
        
        self.easing = EasingFunctions.get(self.config.acceleration_curve)
    
    def _generate_control_points(
        self, 
        start: Point, 
        end: Point
    ) -> Tuple[Point, Point]:
        """
        Generate Bezier control points for a natural curve.
        """
        distance = start.distance_to(end)
        
        # Direction vector
        dx = end.x - start.x
        dy = end.y - start.y
        
        # Perpendicular vector for curvature
        perp_x = -dy
        perp_y = dx
        
        # Normalize perpendicular
        perp_len = math.sqrt(perp_x**2 + perp_y**2)
        if perp_len > 0:
            perp_x /= perp_len
            perp_y /= perp_len
        
        # Random curvature direction and magnitude
        curve_dir = random.choice([-1, 1])
        curve_mag = random.uniform(0.1, self.config.curvature_factor) * distance
        
        # Control point 1: 1/3 along path with perpendicular offset
        ctrl1 = Point(
            x=start.x + dx * 0.33 + perp_x * curve_dir * curve_mag * random.uniform(0.5, 1.5),
            y=start.y + dy * 0.33 + perp_y * curve_dir * curve_mag * random.uniform(0.5, 1.5)
        )
        
        # Control point 2: 2/3 along path with smaller offset
        ctrl2 = Point(
            x=start.x + dx * 0.67 + perp_x * curve_dir * curve_mag * random.uniform(0.3, 0.8),
            y=start.y + dy * 0.67 + perp_y * curve_dir * curve_mag * random.uniform(0.3, 0.8)
        )
        
        return ctrl1, ctrl2
    
    def _calculate_movement_time(self, distance: float) -> float:
        """
        Calculate realistic movement time based on Fitts's Law.
        
        Fitts's Law: T = a + b * log2(1 + D/W)
        Simplified for mouse movement.
        """
        # Base time from speed
        base_time = distance / self.config.base_speed
        
        # Apply variance
        variance = random.uniform(
            1 - self.config.speed_variance,
            1 + self.config.speed_variance
        )
        time = base_time * variance
        
        # Clamp to configured range
        return max(self.config.min_movement_time, 
                   min(self.config.max_movement_time, time))
    
    def _calculate_num_points(self, distance: float, duration: float) -> int:
        """Calculate number of points based on distance and duration"""
        # Higher resolution for longer/slower movements
        base_points = int(distance / 10)  # ~1 point per 10 pixels
        time_factor = int(duration * 60)  # ~60 Hz sampling rate
        
        num_points = max(base_points, time_factor)
        
        return max(self.config.min_points, 
                   min(self.config.max_points, num_points))
    
    def generate_trajectory(
        self, 
        start: Tuple[float, float], 
        end: Tuple[float, float],
        start_time: float = None
    ) -> List[Point]:
        """
        Generate a human-like mouse trajectory from start to end.
        
        Args:
            start: Starting (x, y) coordinates
            end: Target (x, y) coordinates
            start_time: Starting timestamp (defaults to current time)
            
        Returns:
            List of Points representing the trajectory
        """
        start_point = Point(x=start[0], y=start[1])
        end_point = Point(x=end[0], y=end[1])
        
        if start_time is None:
            start_time = time.time()
        
        distance = start_point.distance_to(end_point)
        
        # Handle very short movements
        if distance < 5:
            return [
                Point(x=start[0], y=start[1], timestamp=start_time),
                Point(x=end[0], y=end[1], timestamp=start_time + 0.05)
            ]
        
        # Calculate movement parameters
        duration = self._calculate_movement_time(distance)
        num_points = self._calculate_num_points(distance, duration)
        
        # Check for overshoot
        do_overshoot = random.random() < self.config.overshoot_probability
        
        if do_overshoot:
            # Calculate overshoot point
            overshoot_dist = distance * self.config.overshoot_factor
            dx = (end_point.x - start_point.x) / distance
            dy = (end_point.y - start_point.y) / distance
            
            overshoot_point = Point(
                x=end_point.x + dx * overshoot_dist,
                y=end_point.y + dy * overshoot_dist
            )
            
            # Split trajectory: main movement + correction
            main_points = int(num_points * 0.85)
            correction_points = num_points - main_points
            
            trajectory = self._generate_segment(
                start_point, overshoot_point, 
                start_time, duration * 0.85, main_points
            )
            
            # Correction movement
            correction = self._generate_segment(
                overshoot_point, end_point,
                start_time + duration * 0.85, duration * 0.15, correction_points
            )
            
            trajectory.extend(correction[1:])  # Skip duplicate point
        else:
            trajectory = self._generate_segment(
                start_point, end_point, 
                start_time, duration, num_points
            )
        
        return trajectory
    
    def _generate_segment(
        self,
        start: Point,
        end: Point,
        start_time: float,
        duration: float,
        num_points: int
    ) -> List[Point]:
        """Generate a single segment of the trajectory"""
        
        ctrl1, ctrl2 = self._generate_control_points(start, end)
        
        trajectory = []
        
        for i in range(num_points):
            # Parameter along curve [0, 1]
            t_raw = i / (num_points - 1)
            
            # Apply easing for natural speed variation
            t_eased = self.easing(t_raw)
            
            # Get point on Bezier curve
            point = BezierCurve.get_point(t_eased, start, ctrl1, ctrl2, end)
            
            # Add micro-tremor
            if self.config.tremor_enabled:
                # Tremor decreases near start and end (grip is steadier)
                tremor_factor = math.sin(math.pi * t_raw)  # 0 at edges, 1 in middle
                tremor_x, tremor_y = self.tremor_gen.get_tremor(t_raw * duration)
                
                point.x += tremor_x * tremor_factor
                point.y += tremor_y * tremor_factor
            
            # Calculate timestamp
            point.timestamp = start_time + t_raw * duration
            
            trajectory.append(point)
        
        return trajectory
    
    def generate_click_sequence(
        self,
        position: Tuple[float, float],
        click_type: str = "single"
    ) -> Dict:
        """
        Generate realistic click timing.
        
        Args:
            position: Click position
            click_type: "single", "double", or "triple"
            
        Returns:
            Click sequence data
        """
        base_time = time.time()
        
        # Click duration (time between mousedown and mouseup)
        click_duration = random.uniform(0.05, 0.12)  # 50-120ms
        
        clicks = []
        
        if click_type == "single":
            clicks.append({
                "type": "mousedown",
                "x": position[0],
                "y": position[1],
                "timestamp": base_time,
                "button": 0
            })
            clicks.append({
                "type": "mouseup",
                "x": position[0],
                "y": position[1],
                "timestamp": base_time + click_duration,
                "button": 0
            })
            
        elif click_type == "double":
            # Double click: two clicks with 100-150ms gap
            gap = random.uniform(0.10, 0.15)
            
            for i in range(2):
                click_start = base_time + i * (click_duration + gap)
                clicks.append({
                    "type": "mousedown",
                    "x": position[0],
                    "y": position[1],
                    "timestamp": click_start,
                    "button": 0
                })
                clicks.append({
                    "type": "mouseup",
                    "x": position[0],
                    "y": position[1],
                    "timestamp": click_start + click_duration,
                    "button": 0
                })
                
        elif click_type == "triple":
            gap = random.uniform(0.08, 0.12)
            
            for i in range(3):
                click_start = base_time + i * (click_duration + gap)
                clicks.append({
                    "type": "mousedown",
                    "x": position[0],
                    "y": position[1],
                    "timestamp": click_start,
                    "button": 0
                })
                clicks.append({
                    "type": "mouseup",
                    "x": position[0],
                    "y": position[1],
                    "timestamp": click_start + click_duration,
                    "button": 0
                })
        
        return {
            "click_type": click_type,
            "events": clicks
        }


class ScrollGenerator:
    """
    Generates realistic scroll behavior.
    """
    
    def __init__(self, seed: int = None):
        self.rng = random.Random(seed)
    
    def generate_scroll(
        self,
        direction: str = "down",
        amount: int = None,
        smooth: bool = True
    ) -> List[Dict]:
        """
        Generate scroll events.
        
        Args:
            direction: "up" or "down"
            amount: Pixels to scroll (random if None)
            smooth: Whether to generate smooth scrolling
        """
        if amount is None:
            amount = self.rng.randint(100, 500)
        
        sign = -1 if direction == "up" else 1
        
        events = []
        base_time = time.time()
        
        if smooth:
            # Generate multiple small scroll events
            num_events = self.rng.randint(3, 8)
            remaining = amount
            
            for i in range(num_events):
                if i == num_events - 1:
                    delta = remaining
                else:
                    delta = self.rng.randint(20, remaining // 2)
                    remaining -= delta
                
                events.append({
                    "type": "wheel",
                    "deltaY": sign * delta,
                    "timestamp": base_time + i * self.rng.uniform(0.02, 0.05)
                })
        else:
            # Single scroll event
            events.append({
                "type": "wheel",
                "deltaY": sign * amount,
                "timestamp": base_time
            })
        
        return events


class KeyboardGenerator:
    """
    Generates realistic typing behavior.
    """
    
    # Average typing speeds (characters per minute)
    TYPING_SPEEDS = {
        "slow": 150,
        "normal": 200,
        "fast": 280,
        "expert": 400,
    }
    
    def __init__(self, speed: str = "normal", seed: int = None):
        self.cpm = self.TYPING_SPEEDS.get(speed, 200)
        self.rng = random.Random(seed)
    
    def generate_typing(self, text: str) -> List[Dict]:
        """
        Generate keystroke events for typing text.
        """
        events = []
        base_time = time.time()
        
        # Base delay between keystrokes
        base_delay = 60.0 / self.cpm
        
        current_time = base_time
        
        for char in text:
            # Keystroke delay with variance
            delay = base_delay * self.rng.uniform(0.7, 1.4)
            
            # Additional delay after punctuation/space
            if char in ' .,!?;:':
                delay *= self.rng.uniform(1.2, 2.0)
            
            # Key down
            events.append({
                "type": "keydown",
                "key": char,
                "timestamp": current_time
            })
            
            # Key press duration
            press_duration = self.rng.uniform(0.03, 0.08)
            
            # Key up
            events.append({
                "type": "keyup",
                "key": char,
                "timestamp": current_time + press_duration
            })
            
            current_time += delay
        
        return events


# ═══════════════════════════════════════════════════════════════════════════════
# UNIFIED GHOST MOTOR INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class GhostMotor:
    """
    Unified interface for all human-like input generation.
    
    This is the main class to use for generating realistic user interactions.
    """
    
    def __init__(self, profile_uuid: str = None, config: TrajectoryConfig = None):
        # Generate seed from profile UUID for consistency
        if profile_uuid:
            hash_bytes = hashlib.sha256(profile_uuid.encode()).digest()
            seed = int.from_bytes(hash_bytes[:8], 'little')
        else:
            seed = None
        
        if config is None:
            config = TrajectoryConfig(seed=seed)
        else:
            config.seed = seed
        
        self.gan = GhostMotorGAN(config)
        self.scroll = ScrollGenerator(seed)
        self.keyboard = KeyboardGenerator(seed=seed)
        self.profile_uuid = profile_uuid
    
    def move_to(
        self, 
        start: Tuple[float, float], 
        end: Tuple[float, float]
    ) -> List[Dict]:
        """
        Generate mouse movement from start to end.
        
        Returns list of mouse event dictionaries.
        """
        trajectory = self.gan.generate_trajectory(start, end)
        return [{"type": "mousemove", **p.to_dict()} for p in trajectory]
    
    def click_at(
        self,
        position: Tuple[float, float],
        click_type: str = "single"
    ) -> Dict:
        """Generate click events at position."""
        return self.gan.generate_click_sequence(position, click_type)
    
    def move_and_click(
        self,
        start: Tuple[float, float],
        target: Tuple[float, float],
        click_type: str = "single"
    ) -> List[Dict]:
        """Move to target and click."""
        events = self.move_to(start, target)
        click_events = self.click_at(target, click_type)
        events.extend(click_events["events"])
        return events
    
    def scroll(
        self,
        direction: str = "down",
        amount: int = None
    ) -> List[Dict]:
        """Generate scroll events."""
        return self.scroll.generate_scroll(direction, amount)
    
    def type_text(self, text: str) -> List[Dict]:
        """Generate typing events."""
        return self.keyboard.generate_typing(text)
    
    def export_config(self, path: Path = None) -> Dict:
        """Export Ghost Motor configuration."""
        config = {
            "profile_uuid": self.profile_uuid,
            "trajectory": {
                "base_speed": self.gan.config.base_speed,
                "overshoot_probability": self.gan.config.overshoot_probability,
                "tremor_amplitude": self.gan.config.tremor_amplitude,
                "curvature_factor": self.gan.config.curvature_factor,
            },
            "keyboard": {
                "speed_cpm": self.keyboard.cpm,
            }
        }
        
        if path:
            with open(path, 'w') as f:
                json.dump(config, f, indent=2)
        
        return config


# ═══════════════════════════════════════════════════════════════════════════════
# TESTING
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("LUCID EMPIRE - GHOST MOTOR GAN MODULE TEST")
    print("=" * 70)
    
    # Test trajectory generation
    print("\n[1] Testing Trajectory Generation...")
    gan = GhostMotorGAN(TrajectoryConfig(seed=42))
    
    trajectory = gan.generate_trajectory((100, 100), (500, 400))
    print(f"    Generated {len(trajectory)} points")
    print(f"    Start: ({trajectory[0].x:.1f}, {trajectory[0].y:.1f})")
    print(f"    End: ({trajectory[-1].x:.1f}, {trajectory[-1].y:.1f})")
    
    # Check duration
    duration = trajectory[-1].timestamp - trajectory[0].timestamp
    print(f"    Duration: {duration:.3f}s")
    
    # Test reproducibility
    print("\n[2] Testing Reproducibility...")
    gan2 = GhostMotorGAN(TrajectoryConfig(seed=42))
    trajectory2 = gan2.generate_trajectory((100, 100), (500, 400))
    
    match = all(
        p1.x == p2.x and p1.y == p2.y 
        for p1, p2 in zip(trajectory, trajectory2)
    )
    print(f"    Same seed reproduces same trajectory: {'✓ PASS' if match else '✗ FAIL'}")
    
    # Test click generation
    print("\n[3] Testing Click Generation...")
    click_data = gan.generate_click_sequence((300, 200), "double")
    print(f"    Double click events: {len(click_data['events'])}")
    for event in click_data['events']:
        print(f"      {event['type']} at {event['timestamp']:.4f}")
    
    # Test Ghost Motor interface
    print("\n[4] Testing Unified Ghost Motor Interface...")
    ghost = GhostMotor(profile_uuid="550e8400-e29b-41d4-a716-446655440000")
    
    events = ghost.move_to((0, 0), (800, 600))
    print(f"    Generated {len(events)} mouse move events")
    
    # Test keyboard
    print("\n[5] Testing Keyboard Generation...")
    typing_events = ghost.type_text("Hello World")
    print(f"    Generated {len(typing_events)} key events")
    
    # Show timing distribution
    key_times = [e['timestamp'] for e in typing_events if e['type'] == 'keydown']
    if len(key_times) > 1:
        delays = [key_times[i+1] - key_times[i] for i in range(len(key_times)-1)]
        avg_delay = sum(delays) / len(delays)
        print(f"    Average key delay: {avg_delay*1000:.1f}ms")
    
    print("\n" + "=" * 70)
    print("GHOST MOTOR GAN MODULE: OPERATIONAL")
    print("=" * 70)
