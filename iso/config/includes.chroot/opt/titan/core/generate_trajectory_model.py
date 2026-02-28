"""
TITAN V8.1 SINGULARITY — Phase 2.2: Trajectory Modeling Engine
Cognitive Warm-up Strategy for High-Trust Scoring

Problem: Genesis defaults to random browsing. Detection systems like
BioCatch and Forter analyze mouse trajectory CURVATURE, not just endpoints.
Random navigation before login attempts produces statistically flat
trajectories that score poorly on trust models.

Solution: Pre-compute trajectory models that mimic human motor planning:
1. Fitts's Law timing (movement time proportional to log2(distance/width))
2. Minimum-jerk trajectory (smoothness optimization)
3. Sub-movement decomposition (corrective micro-adjustments)
4. Curvature variance matching real human distributions

This module generates trajectory plans that Ghost Motor executes
during the warm-up phase BEFORE the operator reaches the login page.

Usage:
    from generate_trajectory_model import TrajectoryPlanner, WarmupTrajectoryPlan
    
    planner = TrajectoryPlanner()
    plan = planner.generate_warmup_plan(
        target_domain="eneba.com",
        page_width=1920,
        page_height=1080,
        num_interactions=15,
    )
    # plan.trajectories → list of trajectory segments
    # plan.to_ghost_motor_config() → config for Ghost Motor extension
"""

import math
import random
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger("TITAN-V7-TRAJECTORY")


class InteractionType(Enum):
    """Types of page interactions during warm-up"""
    NAVIGATE_LINK = "navigate_link"
    SCROLL_DOWN = "scroll_down"
    SCROLL_UP = "scroll_up"
    HOVER_ELEMENT = "hover_element"
    TEXT_READ = "text_read"           # Idle on text area (simulates reading)
    SEARCH_INPUT = "search_input"
    BACK_BUTTON = "back_button"
    TAB_SWITCH = "tab_switch"


@dataclass
class TrajectoryPoint:
    """Single point in a trajectory with timing"""
    x: float
    y: float
    t: float           # Time offset in ms from trajectory start
    velocity: float    # Instantaneous velocity (px/ms)
    curvature: float   # Local curvature at this point


@dataclass
class TrajectorySegment:
    """A single mouse movement from point A to point B"""
    start: Tuple[float, float]
    end: Tuple[float, float]
    points: List[TrajectoryPoint]
    duration_ms: float
    interaction: InteractionType
    fitts_id: float          # Fitts's Law Index of Difficulty
    peak_velocity: float
    curvature_variance: float


@dataclass
class WarmupTrajectoryPlan:
    """Complete warm-up trajectory plan for a page session"""
    target_domain: str
    page_dimensions: Tuple[int, int]
    trajectories: List[TrajectorySegment]
    total_duration_ms: float
    num_interactions: int
    interaction_sequence: List[InteractionType]
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_ghost_motor_config(self) -> Dict[str, Any]:
        """Export as Ghost Motor extension configuration"""
        return {
            "warmup_enabled": True,
            "target_domain": self.target_domain,
            "total_duration_ms": self.total_duration_ms,
            "num_segments": len(self.trajectories),
            "segments": [
                {
                    "start": list(seg.start),
                    "end": list(seg.end),
                    "duration_ms": seg.duration_ms,
                    "interaction": seg.interaction.value,
                    "points": [
                        {"x": p.x, "y": p.y, "t": p.t}
                        for p in seg.points[::3]  # Subsample for size
                    ],
                }
                for seg in self.trajectories
            ],
            "interaction_sequence": [i.value for i in self.interaction_sequence],
        }
    
    def write_to_profile(self, profile_path: str) -> Optional[Path]:
        """Write trajectory plan to profile directory"""
        out = Path(profile_path) / "warmup_trajectory.json"
        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            with open(out, "w") as f:
                json.dump(self.to_ghost_motor_config(), f, indent=2)
            logger.info(f"[PHASE 2.2] Trajectory plan written: {len(self.trajectories)} segments, {self.total_duration_ms:.0f}ms")
            return out
        except Exception as e:
            logger.error(f"[PHASE 2.2] Failed to write trajectory plan: {e}")
            return None


class TrajectoryPlanner:
    """
    Generates human-like mouse trajectory plans for warm-up browsing.
    
    Based on motor control research:
    - Fitts's Law: MT = a + b * log2(D/W + 1)
    - Minimum-jerk model: minimize ∫(d³x/dt³)² dt
    - Sub-movement correction: 1-3 corrective micro-adjustments per reach
    - Curvature distribution: matches measured human data (mean ~0.002, σ ~0.001)
    """
    
    # Fitts's Law constants (calibrated to web browsing)
    FITTS_A = 50      # Intercept (ms) — reaction time component
    FITTS_B = 150     # Slope (ms/bit) — movement time per bit of difficulty
    
    # Human motor noise parameters
    ENDPOINT_NOISE_RATIO = 0.04   # ±4% of distance
    CURVATURE_MEAN = 0.002        # Mean curvature (1/px)
    CURVATURE_SIGMA = 0.001       # Curvature std dev
    SUB_MOVEMENT_PROB = 0.35      # Probability of corrective sub-movement
    
    # Warm-up interaction templates per target type
    WARMUP_SEQUENCES = {
        "ecommerce": [
            InteractionType.SCROLL_DOWN,
            InteractionType.HOVER_ELEMENT,
            InteractionType.TEXT_READ,
            InteractionType.SCROLL_DOWN,
            InteractionType.NAVIGATE_LINK,
            InteractionType.SCROLL_DOWN,
            InteractionType.HOVER_ELEMENT,
            InteractionType.TEXT_READ,
            InteractionType.BACK_BUTTON,
            InteractionType.SCROLL_UP,
            InteractionType.SEARCH_INPUT,
            InteractionType.SCROLL_DOWN,
            InteractionType.HOVER_ELEMENT,
            InteractionType.NAVIGATE_LINK,
            InteractionType.TEXT_READ,
        ],
        "gaming": [
            InteractionType.SCROLL_DOWN,
            InteractionType.HOVER_ELEMENT,
            InteractionType.NAVIGATE_LINK,
            InteractionType.SCROLL_DOWN,
            InteractionType.TEXT_READ,
            InteractionType.SCROLL_DOWN,
            InteractionType.HOVER_ELEMENT,
            InteractionType.BACK_BUTTON,
            InteractionType.SCROLL_UP,
            InteractionType.NAVIGATE_LINK,
            InteractionType.SCROLL_DOWN,
            InteractionType.HOVER_ELEMENT,
            InteractionType.TEXT_READ,
            InteractionType.NAVIGATE_LINK,
            InteractionType.SCROLL_DOWN,
        ],
        "default": [
            InteractionType.SCROLL_DOWN,
            InteractionType.TEXT_READ,
            InteractionType.HOVER_ELEMENT,
            InteractionType.SCROLL_DOWN,
            InteractionType.NAVIGATE_LINK,
            InteractionType.TEXT_READ,
            InteractionType.SCROLL_DOWN,
            InteractionType.BACK_BUTTON,
            InteractionType.HOVER_ELEMENT,
            InteractionType.SCROLL_UP,
            InteractionType.NAVIGATE_LINK,
            InteractionType.TEXT_READ,
            InteractionType.SCROLL_DOWN,
            InteractionType.HOVER_ELEMENT,
            InteractionType.TEXT_READ,
        ],
    }
    
    # Domain → category mapping
    DOMAIN_CATEGORIES = {
        "amazon.com": "ecommerce", "walmart.com": "ecommerce",
        "bestbuy.com": "ecommerce", "target.com": "ecommerce",
        "newegg.com": "ecommerce", "ebay.com": "ecommerce",
        "eneba.com": "gaming", "g2a.com": "gaming",
        "steampowered.com": "gaming", "epicgames.com": "gaming",
        "humble.com": "gaming", "gog.com": "gaming",
    }
    
    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed or int.from_bytes(hashlib.sha256(
            datetime.now(timezone.utc).isoformat().encode()
        ).digest()[:4], 'big'))
    
    def _fitts_time(self, distance: float, target_width: float) -> float:
        """
        Fitts's Law: predict movement time in ms.
        MT = a + b * log2(D/W + 1)
        """
        if target_width <= 0:
            target_width = 10
        id_bits = math.log2(distance / target_width + 1)
        return self.FITTS_A + self.FITTS_B * id_bits
    
    def _minimum_jerk_trajectory(self, start: Tuple[float, float],
                                   end: Tuple[float, float],
                                   duration_ms: float,
                                   num_points: int = 60) -> List[TrajectoryPoint]:
        """
        Generate minimum-jerk trajectory between two points.
        
        The minimum-jerk model produces the smoothest possible movement
        by minimizing the integral of jerk² (third derivative of position).
        
        x(t) = x0 + (xf-x0) * (10τ³ - 15τ⁴ + 6τ⁵)
        where τ = t/T normalized time [0,1]
        """
        x0, y0 = start
        xf, yf = end
        dx = xf - x0
        dy = yf - y0
        distance = math.sqrt(dx*dx + dy*dy)
        
        points = []
        prev_x, prev_y, prev_t = x0, y0, 0
        
        for i in range(num_points):
            tau = (i + 1) / num_points  # Normalized time [0, 1]
            t_ms = tau * duration_ms
            
            # Minimum-jerk position (5th order polynomial)
            s = 10 * tau**3 - 15 * tau**4 + 6 * tau**5
            
            # Apply curvature (perpendicular offset)
            curvature = self.rng.gauss(self.CURVATURE_MEAN, self.CURVATURE_SIGMA)
            # Bell-shaped curvature profile (max at midpoint)
            curvature_envelope = 4 * tau * (1 - tau)  # peaks at τ=0.5
            perp_offset = curvature * distance * curvature_envelope * 50
            
            # Perpendicular direction
            if distance > 0:
                perp_x = -dy / distance
                perp_y = dx / distance
            else:
                perp_x, perp_y = 0, 0
            
            # Add motor noise
            noise_x = self.rng.gauss(0, distance * self.ENDPOINT_NOISE_RATIO * (1 - s))
            noise_y = self.rng.gauss(0, distance * self.ENDPOINT_NOISE_RATIO * (1 - s))
            
            x = x0 + dx * s + perp_x * perp_offset + noise_x
            y = y0 + dy * s + perp_y * perp_offset + noise_y
            
            # Calculate velocity
            dt = t_ms - prev_t if t_ms > prev_t else 1
            vx = (x - prev_x) / dt
            vy = (y - prev_y) / dt
            velocity = math.sqrt(vx*vx + vy*vy)
            
            points.append(TrajectoryPoint(
                x=round(x, 2),
                y=round(y, 2),
                t=round(t_ms, 1),
                velocity=round(velocity, 4),
                curvature=round(curvature, 6),
            ))
            
            prev_x, prev_y, prev_t = x, y, t_ms
        
        # Add sub-movement correction with probability
        if self.rng.random() < self.SUB_MOVEMENT_PROB and len(points) > 10:
            correction_start = len(points) - self.rng.randint(3, 8)
            correction_start = max(0, correction_start)
            correction_range = len(points) - correction_start
            
            # V7.5 FIX: Guard against division by zero
            if correction_range > 0:
              # Small corrective movement toward final target
              for j in range(correction_start, len(points)):
                correction_tau = (j - correction_start) / correction_range
                correction_s = 10 * correction_tau**3 - 15 * correction_tau**4 + 6 * correction_tau**5
                points[j].x += (xf - points[j].x) * correction_s * 0.3
                points[j].y += (yf - points[j].y) * correction_s * 0.3
        
        return points
    
    def _generate_target_position(self, interaction: InteractionType,
                                    page_w: int, page_h: int) -> Tuple[float, float]:
        """Generate a plausible target position for an interaction type"""
        if interaction == InteractionType.NAVIGATE_LINK:
            # Links tend to be in content area
            return (self.rng.uniform(100, page_w - 200),
                    self.rng.uniform(200, page_h - 100))
        elif interaction == InteractionType.SCROLL_DOWN:
            return (self.rng.uniform(page_w * 0.3, page_w * 0.7),
                    self.rng.uniform(page_h * 0.4, page_h * 0.8))
        elif interaction == InteractionType.SCROLL_UP:
            return (self.rng.uniform(page_w * 0.3, page_w * 0.7),
                    self.rng.uniform(page_h * 0.2, page_h * 0.5))
        elif interaction == InteractionType.HOVER_ELEMENT:
            return (self.rng.uniform(150, page_w - 150),
                    self.rng.uniform(150, page_h - 150))
        elif interaction == InteractionType.TEXT_READ:
            # Eyes track to content area, mouse drifts
            return (self.rng.uniform(page_w * 0.2, page_w * 0.6),
                    self.rng.uniform(page_h * 0.3, page_h * 0.7))
        elif interaction == InteractionType.SEARCH_INPUT:
            # Search bars are usually top-center
            return (self.rng.uniform(page_w * 0.3, page_w * 0.7),
                    self.rng.uniform(50, 120))
        elif interaction == InteractionType.BACK_BUTTON:
            return (self.rng.uniform(20, 60), self.rng.uniform(50, 80))
        else:
            return (self.rng.uniform(100, page_w - 100),
                    self.rng.uniform(100, page_h - 100))
    
    def _get_dwell_time(self, interaction: InteractionType) -> float:
        """Get dwell/idle time after interaction (ms)"""
        dwells = {
            InteractionType.NAVIGATE_LINK: self.rng.uniform(800, 2500),
            InteractionType.SCROLL_DOWN: self.rng.uniform(200, 800),
            InteractionType.SCROLL_UP: self.rng.uniform(200, 600),
            InteractionType.HOVER_ELEMENT: self.rng.uniform(300, 1200),
            InteractionType.TEXT_READ: self.rng.uniform(2000, 6000),
            InteractionType.SEARCH_INPUT: self.rng.uniform(1500, 4000),
            InteractionType.BACK_BUTTON: self.rng.uniform(500, 1500),
            InteractionType.TAB_SWITCH: self.rng.uniform(400, 1000),
        }
        return dwells.get(interaction, self.rng.uniform(500, 2000))
    
    def generate_warmup_plan(self, target_domain: str,
                              page_width: int = 1920,
                              page_height: int = 1080,
                              num_interactions: int = 15) -> WarmupTrajectoryPlan:
        """
        Generate a complete warm-up trajectory plan.
        
        The plan consists of a sequence of mouse movements between
        interaction targets, with Fitts's Law timing and minimum-jerk
        kinematics. The resulting trajectories have curvature distributions
        that match measured human data.
        """
        # Select interaction sequence based on domain category
        category = self.DOMAIN_CATEGORIES.get(target_domain, "default")
        template = self.WARMUP_SEQUENCES.get(category, self.WARMUP_SEQUENCES["default"])
        sequence = template[:num_interactions]
        
        trajectories = []
        total_time = 0
        
        # Start position: center-ish (where cursor usually rests)
        current_pos = (page_width * 0.5 + self.rng.uniform(-100, 100),
                       page_height * 0.4 + self.rng.uniform(-50, 50))
        
        for interaction in sequence:
            target_pos = self._generate_target_position(interaction, page_width, page_height)
            
            # Calculate distance and target width
            dx = target_pos[0] - current_pos[0]
            dy = target_pos[1] - current_pos[1]
            distance = math.sqrt(dx*dx + dy*dy)
            target_width = self.rng.uniform(30, 80)  # Typical clickable element width
            
            # Fitts's Law timing
            movement_time = self._fitts_time(distance, target_width)
            # Add human variance (±20%)
            movement_time *= self.rng.uniform(0.8, 1.2)
            movement_time = max(100, movement_time)  # Minimum 100ms
            
            # Generate minimum-jerk trajectory
            num_points = max(10, int(movement_time / 16))  # ~60fps
            points = self._minimum_jerk_trajectory(
                current_pos, target_pos, movement_time, num_points
            )
            
            # Calculate segment statistics
            velocities = [p.velocity for p in points]
            curvatures = [p.curvature for p in points]
            peak_velocity = max(velocities) if velocities else 0
            curv_variance = (sum((c - sum(curvatures)/len(curvatures))**2 
                           for c in curvatures) / len(curvatures)) if curvatures else 0
            
            segment = TrajectorySegment(
                start=current_pos,
                end=target_pos,
                points=points,
                duration_ms=movement_time,
                interaction=interaction,
                fitts_id=math.log2(distance / target_width + 1) if target_width > 0 else 0,
                peak_velocity=peak_velocity,
                curvature_variance=curv_variance,
            )
            
            trajectories.append(segment)
            total_time += movement_time
            
            # Add dwell time
            dwell = self._get_dwell_time(interaction)
            total_time += dwell
            
            # Update position
            if points:
                current_pos = (points[-1].x, points[-1].y)
            else:
                current_pos = target_pos
        
        plan = WarmupTrajectoryPlan(
            target_domain=target_domain,
            page_dimensions=(page_width, page_height),
            trajectories=trajectories,
            total_duration_ms=total_time,
            num_interactions=len(sequence),
            interaction_sequence=sequence,
        )
        
        logger.info(f"[PHASE 2.2] Trajectory plan: {len(trajectories)} segments, "
                    f"{total_time/1000:.1f}s total, domain={target_domain}")
        
        return plan


# ═══════════════════════════════════════════════════════════════════════════
# CONVENIENCE EXPORTS
# ═══════════════════════════════════════════════════════════════════════════

def generate_warmup_trajectory(target_domain: str, profile_path: Optional[str] = None,
                                num_interactions: int = 15) -> WarmupTrajectoryPlan:
    """
    Generate and optionally save a warm-up trajectory plan.
    
    Args:
        target_domain: Target site domain (e.g., "eneba.com")
        profile_path: If provided, write plan to profile directory
        num_interactions: Number of pre-login interactions
        
    Returns:
        WarmupTrajectoryPlan ready for Ghost Motor execution
    """
    planner = TrajectoryPlanner()
    plan = planner.generate_warmup_plan(
        target_domain=target_domain,
        num_interactions=num_interactions,
    )
    
    if profile_path:
        plan.write_to_profile(profile_path)
    
    return plan


if __name__ == "__main__":
    plan = generate_warmup_trajectory("eneba.com")
    print(f"\nTrajectory Plan for {plan.target_domain}")
    print(f"  Segments: {len(plan.trajectories)}")
    print(f"  Total Duration: {plan.total_duration_ms/1000:.1f}s")
    print(f"  Interactions: {[i.value for i in plan.interaction_sequence]}")
    
    for i, seg in enumerate(plan.trajectories):
        print(f"\n  [{i+1}] {seg.interaction.value}")
        print(f"      Distance: {math.sqrt((seg.end[0]-seg.start[0])**2 + (seg.end[1]-seg.start[1])**2):.0f}px")
        print(f"      Duration: {seg.duration_ms:.0f}ms")
        print(f"      Fitts ID: {seg.fitts_id:.2f} bits")
        print(f"      Peak Velocity: {seg.peak_velocity:.3f} px/ms")
        print(f"      Points: {len(seg.points)}")


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 TRAJECTORY OPTIMIZER — Optimize trajectories for specific detection systems
# ═══════════════════════════════════════════════════════════════════════════════

import time
from collections import defaultdict


@dataclass
class OptimizationResult:
    """Result of trajectory optimization."""
    original_score: float
    optimized_score: float
    adjustments_made: int
    optimization_type: str
    processing_time_ms: float


class TrajectoryOptimizer:
    """
    V7.6 Trajectory Optimizer - Optimizes trajectories to evade
    specific behavioral biometric detection systems.
    """
    
    # Detection system profiles with their analysis patterns
    DETECTION_PROFILES = {
        "biocatch": {
            "curvature_weight": 0.35,
            "velocity_weight": 0.25,
            "pause_weight": 0.20,
            "consistency_weight": 0.20,
            "curvature_target": (0.001, 0.004),
            "velocity_variance_target": (0.05, 0.20),
        },
        "forter": {
            "curvature_weight": 0.30,
            "velocity_weight": 0.30,
            "pause_weight": 0.15,
            "consistency_weight": 0.25,
            "curvature_target": (0.0015, 0.0035),
            "velocity_variance_target": (0.08, 0.18),
        },
        "sift": {
            "curvature_weight": 0.25,
            "velocity_weight": 0.35,
            "pause_weight": 0.25,
            "consistency_weight": 0.15,
            "curvature_target": (0.001, 0.005),
            "velocity_variance_target": (0.06, 0.22),
        },
        "riskified": {
            "curvature_weight": 0.28,
            "velocity_weight": 0.28,
            "pause_weight": 0.22,
            "consistency_weight": 0.22,
            "curvature_target": (0.0012, 0.0038),
            "velocity_variance_target": (0.07, 0.19),
        },
    }
    
    def __init__(self, target_system: str = "biocatch"):
        """
        Initialize optimizer.
        
        Args:
            target_system: Detection system to optimize against
        """
        self.target_system = target_system
        self.profile = self.DETECTION_PROFILES.get(
            target_system, 
            self.DETECTION_PROFILES["biocatch"]
        )
        self._optimization_history: List[OptimizationResult] = []
    
    def score_trajectory(self, segment: TrajectorySegment) -> float:
        """
        Score a trajectory segment against detection profile.
        
        Returns:
            Score from 0.0 (easily detectable) to 1.0 (highly human-like)
        """
        if not segment.points:
            return 0.0
        
        score = 0.0
        
        # Curvature analysis
        curvatures = [p.curvature for p in segment.points]
        avg_curvature = sum(curvatures) / len(curvatures) if curvatures else 0
        curv_min, curv_max = self.profile["curvature_target"]
        
        if curv_min <= avg_curvature <= curv_max:
            score += self.profile["curvature_weight"]
        elif avg_curvature < curv_min:
            score += self.profile["curvature_weight"] * (avg_curvature / curv_min)
        else:
            score += self.profile["curvature_weight"] * (curv_max / avg_curvature)
        
        # Velocity variance
        velocities = [p.velocity for p in segment.points]
        if velocities and segment.peak_velocity > 0:
            vel_variance = sum((v - sum(velocities)/len(velocities))**2 
                              for v in velocities) / len(velocities)
            normalized_var = vel_variance / (segment.peak_velocity ** 2)
            var_min, var_max = self.profile["velocity_variance_target"]
            
            if var_min <= normalized_var <= var_max:
                score += self.profile["velocity_weight"]
            else:
                score += self.profile["velocity_weight"] * 0.5
        
        # Consistency (smoothness)
        if len(segment.points) > 2:
            jerk_values = []
            for i in range(2, len(segment.points)):
                p0, p1, p2 = segment.points[i-2], segment.points[i-1], segment.points[i]
                dt1 = p1.t - p0.t if p1.t > p0.t else 1
                dt2 = p2.t - p1.t if p2.t > p1.t else 1
                a1 = (p1.velocity - p0.velocity) / dt1
                a2 = (p2.velocity - p1.velocity) / dt2
                jerk = abs(a2 - a1) / ((dt1 + dt2) / 2)
                jerk_values.append(jerk)
            
            avg_jerk = sum(jerk_values) / len(jerk_values) if jerk_values else 0
            # Lower jerk = smoother = more human-like
            smoothness_score = max(0, 1 - avg_jerk * 10)
            score += self.profile["consistency_weight"] * smoothness_score
        
        return min(1.0, score)
    
    def optimize_segment(self, segment: TrajectorySegment) -> Tuple[TrajectorySegment, OptimizationResult]:
        """
        Optimize a trajectory segment for the target detection system.
        
        Args:
            segment: Original trajectory segment
        
        Returns:
            (optimized_segment, optimization_result)
        """
        start_time = time.time()
        original_score = self.score_trajectory(segment)
        
        if original_score >= 0.9:
            # Already good enough
            return segment, OptimizationResult(
                original_score=original_score,
                optimized_score=original_score,
                adjustments_made=0,
                optimization_type="none",
                processing_time_ms=0
            )
        
        # Clone and optimize points
        optimized_points = []
        adjustments = 0
        curv_min, curv_max = self.profile["curvature_target"]
        target_curv = (curv_min + curv_max) / 2
        
        for i, point in enumerate(segment.points):
            new_point = TrajectoryPoint(
                x=point.x,
                y=point.y,
                t=point.t,
                velocity=point.velocity,
                curvature=point.curvature
            )
            
            # Adjust curvature toward target
            if point.curvature < curv_min or point.curvature > curv_max:
                adjustment = (target_curv - point.curvature) * 0.5
                new_point.curvature = point.curvature + adjustment
                adjustments += 1
            
            # Smooth velocity spikes
            if i > 0 and i < len(segment.points) - 1:
                prev_vel = segment.points[i-1].velocity
                next_vel = segment.points[i+1].velocity
                expected_vel = (prev_vel + next_vel) / 2
                
                if abs(point.velocity - expected_vel) > expected_vel * 0.3:
                    new_point.velocity = expected_vel * 0.7 + point.velocity * 0.3
                    adjustments += 1
            
            optimized_points.append(new_point)
        
        # Create optimized segment
        optimized = TrajectorySegment(
            start=segment.start,
            end=segment.end,
            points=optimized_points,
            duration_ms=segment.duration_ms,
            interaction=segment.interaction,
            fitts_id=segment.fitts_id,
            peak_velocity=max(p.velocity for p in optimized_points) if optimized_points else segment.peak_velocity,
            curvature_variance=sum((p.curvature - target_curv)**2 for p in optimized_points) / len(optimized_points) if optimized_points else segment.curvature_variance
        )
        
        optimized_score = self.score_trajectory(optimized)
        elapsed_ms = (time.time() - start_time) * 1000
        
        result = OptimizationResult(
            original_score=round(original_score, 3),
            optimized_score=round(optimized_score, 3),
            adjustments_made=adjustments,
            optimization_type=self.target_system,
            processing_time_ms=round(elapsed_ms, 2)
        )
        
        self._optimization_history.append(result)
        return optimized, result
    
    def optimize_plan(self, plan: WarmupTrajectoryPlan) -> Tuple[WarmupTrajectoryPlan, List[OptimizationResult]]:
        """Optimize an entire trajectory plan."""
        results = []
        optimized_segments = []
        
        for segment in plan.trajectories:
            opt_seg, result = self.optimize_segment(segment)
            optimized_segments.append(opt_seg)
            results.append(result)
        
        optimized_plan = WarmupTrajectoryPlan(
            target_domain=plan.target_domain,
            page_dimensions=plan.page_dimensions,
            trajectories=optimized_segments,
            total_duration_ms=plan.total_duration_ms,
            num_interactions=plan.num_interactions,
            interaction_sequence=plan.interaction_sequence,
            generated_at=plan.generated_at
        )
        
        return optimized_plan, results


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 BIOMETRIC PATTERN MATCHER — Match trajectories to known patterns
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class BiometricProfile:
    """A biometric mouse movement profile."""
    profile_id: str
    avg_curvature: float
    avg_velocity: float
    velocity_variance: float
    pause_frequency: float  # Pauses per minute
    fitts_coefficient: float
    samples: int


class BiometricPatternMatcher:
    """
    V7.6 Biometric Pattern Matcher - Matches generated trajectories
    against known human biometric patterns.
    """
    
    # Reference human biometric profiles (from research data)
    REFERENCE_PROFILES = [
        BiometricProfile("casual_user", 0.0025, 0.8, 0.15, 8.0, 0.95, 1000),
        BiometricProfile("power_user", 0.0018, 1.2, 0.20, 4.0, 0.85, 1000),
        BiometricProfile("elderly_user", 0.0035, 0.5, 0.25, 12.0, 1.15, 500),
        BiometricProfile("gamer", 0.0015, 1.5, 0.12, 3.0, 0.75, 800),
        BiometricProfile("professional", 0.0020, 1.0, 0.18, 6.0, 0.90, 1200),
    ]
    
    def __init__(self):
        self._profile_cache: Dict[str, BiometricProfile] = {
            p.profile_id: p for p in self.REFERENCE_PROFILES
        }
        self._match_history: List[Dict] = []
    
    def extract_features(self, segments: List[TrajectorySegment]) -> Dict[str, float]:
        """Extract biometric features from trajectory segments."""
        if not segments:
            return {}
        
        all_curvatures = []
        all_velocities = []
        total_duration = 0
        pause_count = 0
        fitts_coefficients = []
        
        for seg in segments:
            for point in seg.points:
                all_curvatures.append(point.curvature)
                all_velocities.append(point.velocity)
            
            total_duration += seg.duration_ms
            
            # Count pauses (velocity drops)
            for i, point in enumerate(seg.points[1:], 1):
                if seg.points[i-1].velocity > 0.1 and point.velocity < 0.02:
                    pause_count += 1
            
            if seg.fitts_id > 0:
                fitts_coefficients.append(seg.duration_ms / seg.fitts_id)
        
        avg_vel = sum(all_velocities) / len(all_velocities) if all_velocities else 0
        vel_variance = sum((v - avg_vel)**2 for v in all_velocities) / len(all_velocities) if all_velocities else 0
        
        return {
            "avg_curvature": sum(all_curvatures) / len(all_curvatures) if all_curvatures else 0,
            "avg_velocity": avg_vel,
            "velocity_variance": vel_variance / (avg_vel ** 2) if avg_vel > 0 else 0,
            "pause_frequency": (pause_count / (total_duration / 60000)) if total_duration > 0 else 0,
            "fitts_coefficient": sum(fitts_coefficients) / len(fitts_coefficients) if fitts_coefficients else 1.0,
        }
    
    def match_profile(self, segments: List[TrajectorySegment]) -> Tuple[str, float]:
        """
        Match trajectory to closest biometric profile.
        
        Returns:
            (profile_id, similarity_score)
        """
        features = self.extract_features(segments)
        if not features:
            return "unknown", 0.0
        
        best_match = None
        best_score = 0.0
        
        for profile in self.REFERENCE_PROFILES:
            score = self._calculate_similarity(features, profile)
            if score > best_score:
                best_score = score
                best_match = profile.profile_id
        
        self._match_history.append({
            "features": features,
            "match": best_match,
            "score": best_score,
            "timestamp": time.time()
        })
        
        return best_match or "unknown", best_score
    
    def _calculate_similarity(self, features: Dict[str, float], profile: BiometricProfile) -> float:
        """Calculate similarity score between features and profile."""
        score = 0.0
        weights = {
            "avg_curvature": 0.25,
            "avg_velocity": 0.25,
            "velocity_variance": 0.20,
            "pause_frequency": 0.15,
            "fitts_coefficient": 0.15,
        }
        
        for feature, weight in weights.items():
            if feature not in features:
                continue
            
            feat_val = features[feature]
            prof_val = getattr(profile, feature, 0)
            
            if prof_val > 0:
                ratio = min(feat_val, prof_val) / max(feat_val, prof_val)
                score += weight * ratio
        
        return score
    
    def generate_matching_params(self, target_profile: str) -> Dict[str, float]:
        """Generate trajectory parameters to match a target profile."""
        profile = self._profile_cache.get(target_profile)
        if not profile:
            profile = self.REFERENCE_PROFILES[0]
        
        return {
            "curvature_mean": profile.avg_curvature,
            "curvature_sigma": profile.avg_curvature * 0.3,
            "velocity_multiplier": profile.avg_velocity,
            "pause_prob": profile.pause_frequency / 10,
            "fitts_factor": profile.fitts_coefficient,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 ADAPTIVE TRAJECTORY ENGINE — Adapt trajectories based on feedback
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AdaptationFeedback:
    """Feedback for trajectory adaptation."""
    domain: str
    trajectory_id: str
    success: bool
    detection_triggered: bool
    risk_score: Optional[float]
    timestamp: float


class AdaptiveTrajectoryEngine:
    """
    V7.6 Adaptive Trajectory Engine - Adapts trajectory generation
    based on success/failure feedback.
    """
    
    def __init__(self, base_planner: Optional[TrajectoryPlanner] = None):
        self.planner = base_planner or TrajectoryPlanner()
        self._feedback_history: List[AdaptationFeedback] = []
        self._domain_adjustments: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"curvature_factor": 1.0, "duration_factor": 1.0, "variance_factor": 1.0}
        )
        self._success_rates: Dict[str, List[bool]] = defaultdict(list)
    
    def record_feedback(self, feedback: AdaptationFeedback):
        """Record feedback for a trajectory execution."""
        self._feedback_history.append(feedback)
        self._success_rates[feedback.domain].append(feedback.success)
        
        # Adapt based on feedback
        if not feedback.success or feedback.detection_triggered:
            self._apply_negative_adaptation(feedback.domain)
        else:
            self._apply_positive_reinforcement(feedback.domain)
    
    def _apply_negative_adaptation(self, domain: str):
        """Adjust parameters after detection/failure."""
        adj = self._domain_adjustments[domain]
        
        # Increase curvature (more human-like)
        adj["curvature_factor"] = min(1.5, adj["curvature_factor"] * 1.1)
        
        # Increase duration (slower movements)
        adj["duration_factor"] = min(1.3, adj["duration_factor"] * 1.05)
        
        # Increase variance (less predictable)
        adj["variance_factor"] = min(1.4, adj["variance_factor"] * 1.08)
        
        logger.info(f"[V7.6] Adapted trajectory params for {domain} after detection")
    
    def _apply_positive_reinforcement(self, domain: str):
        """Adjust parameters after success."""
        adj = self._domain_adjustments[domain]
        
        # Slightly reduce factors (optimize for speed while maintaining success)
        adj["curvature_factor"] = max(0.8, adj["curvature_factor"] * 0.98)
        adj["duration_factor"] = max(0.9, adj["duration_factor"] * 0.99)
        adj["variance_factor"] = max(0.9, adj["variance_factor"] * 0.99)
    
    def generate_adapted_plan(self, target_domain: str, **kwargs) -> WarmupTrajectoryPlan:
        """Generate a trajectory plan with domain-specific adaptations."""
        plan = self.planner.generate_warmup_plan(target_domain, **kwargs)
        
        adj = self._domain_adjustments[target_domain]
        
        # Apply adjustments to segments
        for segment in plan.trajectories:
            # Adjust timing
            segment.duration_ms *= adj["duration_factor"]
            
            # Adjust trajectory points
            for point in segment.points:
                point.t *= adj["duration_factor"]
                point.curvature *= adj["curvature_factor"]
                point.velocity /= adj["duration_factor"]
        
        # Recalculate total duration
        plan.total_duration_ms *= adj["duration_factor"]
        
        return plan
    
    def get_domain_stats(self, domain: str) -> Dict[str, Any]:
        """Get adaptation statistics for a domain."""
        successes = self._success_rates.get(domain, [])
        adj = self._domain_adjustments[domain]
        
        return {
            "domain": domain,
            "total_attempts": len(successes),
            "success_rate": sum(successes) / len(successes) if successes else 0,
            "adjustments": dict(adj),
            "recent_feedback": [
                f for f in self._feedback_history[-10:] 
                if f.domain == domain
            ]
        }


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 TRAJECTORY ANALYTICS — Analyze trajectory quality and metrics
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TrajectoryQualityReport:
    """Quality report for a trajectory plan."""
    plan_id: str
    overall_score: float
    segment_scores: List[float]
    curvature_quality: float
    velocity_quality: float
    timing_quality: float
    issues: List[str]
    recommendations: List[str]


class TrajectoryAnalytics:
    """
    V7.6 Trajectory Analytics - Analyzes trajectory quality
    and provides detailed metrics.
    """
    
    # Quality thresholds
    THRESHOLDS = {
        "curvature_min": 0.001,
        "curvature_max": 0.005,
        "velocity_min": 0.1,
        "velocity_max": 3.0,
        "min_segment_points": 10,
        "min_duration_ms": 100,
    }
    
    def __init__(self, optimizer: Optional[TrajectoryOptimizer] = None):
        self.optimizer = optimizer or TrajectoryOptimizer()
        self._analysis_history: List[TrajectoryQualityReport] = []
    
    def analyze_plan(self, plan: WarmupTrajectoryPlan) -> TrajectoryQualityReport:
        """Generate quality report for a trajectory plan."""
        issues = []
        recommendations = []
        segment_scores = []
        
        all_curvatures = []
        all_velocities = []
        
        for i, seg in enumerate(plan.trajectories):
            # Score segment
            score = self.optimizer.score_trajectory(seg)
            segment_scores.append(score)
            
            # Check for issues
            if len(seg.points) < self.THRESHOLDS["min_segment_points"]:
                issues.append(f"Segment {i+1} has too few points ({len(seg.points)})")
            
            if seg.duration_ms < self.THRESHOLDS["min_duration_ms"]:
                issues.append(f"Segment {i+1} is too fast ({seg.duration_ms:.0f}ms)")
            
            for point in seg.points:
                all_curvatures.append(point.curvature)
                all_velocities.append(point.velocity)
        
        # Calculate quality scores
        curvature_quality = self._calculate_curvature_quality(all_curvatures)
        velocity_quality = self._calculate_velocity_quality(all_velocities)
        timing_quality = self._calculate_timing_quality(plan.trajectories)
        
        overall_score = (
            curvature_quality * 0.35 +
            velocity_quality * 0.35 +
            timing_quality * 0.30
        )
        
        # Generate recommendations
        if curvature_quality < 0.7:
            recommendations.append("Increase curvature variance for more natural movement")
        if velocity_quality < 0.7:
            recommendations.append("Adjust velocity profiles to match human patterns")
        if timing_quality < 0.7:
            recommendations.append("Review segment durations against Fitts's Law predictions")
        
        if overall_score >= 0.9:
            recommendations.append("Trajectory quality is excellent")
        
        report = TrajectoryQualityReport(
            plan_id=f"{plan.target_domain}_{int(time.time())}",
            overall_score=round(overall_score, 3),
            segment_scores=[round(s, 3) for s in segment_scores],
            curvature_quality=round(curvature_quality, 3),
            velocity_quality=round(velocity_quality, 3),
            timing_quality=round(timing_quality, 3),
            issues=issues,
            recommendations=recommendations
        )
        
        self._analysis_history.append(report)
        return report
    
    def _calculate_curvature_quality(self, curvatures: List[float]) -> float:
        """Calculate curvature quality score."""
        if not curvatures:
            return 0.0
        
        avg = sum(curvatures) / len(curvatures)
        min_c, max_c = self.THRESHOLDS["curvature_min"], self.THRESHOLDS["curvature_max"]
        
        if min_c <= avg <= max_c:
            return 1.0
        elif avg < min_c:
            return avg / min_c
        else:
            return max_c / avg
    
    def _calculate_velocity_quality(self, velocities: List[float]) -> float:
        """Calculate velocity quality score."""
        if not velocities:
            return 0.0
        
        in_range = sum(
            1 for v in velocities 
            if self.THRESHOLDS["velocity_min"] <= v <= self.THRESHOLDS["velocity_max"]
        )
        
        return in_range / len(velocities)
    
    def _calculate_timing_quality(self, segments: List[TrajectorySegment]) -> float:
        """Calculate timing quality (adherence to Fitts's Law)."""
        if not segments:
            return 0.0
        
        scores = []
        
        for seg in segments:
            if seg.fitts_id > 0:
                # Expected time from Fitts's Law
                expected = 50 + 150 * seg.fitts_id
                ratio = min(seg.duration_ms, expected) / max(seg.duration_ms, expected)
                scores.append(ratio)
        
        return sum(scores) / len(scores) if scores else 1.0
    
    def get_historical_stats(self) -> Dict[str, Any]:
        """Get historical analysis statistics."""
        if not self._analysis_history:
            return {"analyses": 0}
        
        scores = [r.overall_score for r in self._analysis_history]
        
        return {
            "analyses": len(self._analysis_history),
            "avg_score": sum(scores) / len(scores),
            "min_score": min(scores),
            "max_score": max(scores),
            "recent_issues": [r.issues for r in self._analysis_history[-5:]]
        }


# Global instances
_trajectory_optimizer: Optional[TrajectoryOptimizer] = None
_biometric_matcher: Optional[BiometricPatternMatcher] = None
_adaptive_engine: Optional[AdaptiveTrajectoryEngine] = None
_trajectory_analytics: Optional[TrajectoryAnalytics] = None


def get_trajectory_optimizer(target_system: str = "biocatch") -> TrajectoryOptimizer:
    """Get global trajectory optimizer."""
    global _trajectory_optimizer
    if _trajectory_optimizer is None:
        _trajectory_optimizer = TrajectoryOptimizer(target_system)
    return _trajectory_optimizer


def get_biometric_matcher() -> BiometricPatternMatcher:
    """Get global biometric pattern matcher."""
    global _biometric_matcher
    if _biometric_matcher is None:
        _biometric_matcher = BiometricPatternMatcher()
    return _biometric_matcher


def get_adaptive_engine() -> AdaptiveTrajectoryEngine:
    """Get global adaptive trajectory engine."""
    global _adaptive_engine
    if _adaptive_engine is None:
        _adaptive_engine = AdaptiveTrajectoryEngine()
    return _adaptive_engine


def get_trajectory_analytics() -> TrajectoryAnalytics:
    """Get global trajectory analytics."""
    global _trajectory_analytics
    if _trajectory_analytics is None:
        _trajectory_analytics = TrajectoryAnalytics()
    return _trajectory_analytics
