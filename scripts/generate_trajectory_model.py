#!/usr/bin/env python3
"""
LUCID EMPIRE :: TRAJECTORY MODEL GENERATOR (No ONNX required)
==============================================================
Creates a serialized numpy model for mouse trajectory generation.

This is a fallback for when ONNX is not available or has issues.
The biometric_mimicry module will be updated to use this format.
"""

import numpy as np
import pickle
import os
from pathlib import Path

def generate_bezier_weights(num_points: int = 20):
    """Generate Bézier curve weights for trajectory interpolation"""
    t_values = np.linspace(0, 1, num_points).astype(np.float32)
    
    # Cubic Bézier basis functions
    weights = np.zeros((num_points, 4), dtype=np.float32)
    for i, t in enumerate(t_values):
        weights[i, 0] = (1 - t) ** 3  # Start point
        weights[i, 1] = 3 * t * (1 - t) ** 2  # Control 1
        weights[i, 2] = 3 * t ** 2 * (1 - t)  # Control 2
        weights[i, 3] = t ** 3  # End point
    
    return weights


def generate_trajectory(start_x, start_y, end_x, end_y, weights, 
                       randomness=0.15, tremor_amplitude=0.5):
    """
    Generate a human-like mouse trajectory.
    
    Args:
        start_x, start_y: Starting coordinates
        end_x, end_y: Target coordinates
        weights: Bézier weights matrix [num_points, 4]
        randomness: Control point randomization factor
        tremor_amplitude: Hand tremor simulation
    
    Returns:
        trajectory: Array of (x, y) points
    """
    num_points = weights.shape[0]
    
    # Generate randomized control points
    dx = end_x - start_x
    dy = end_y - start_y
    distance = np.sqrt(dx**2 + dy**2)
    
    # Control points with natural curve offset
    offset = distance * randomness
    angle = np.arctan2(dy, dx)
    
    ctrl1_x = start_x + dx * 0.3 + np.random.uniform(-offset, offset)
    ctrl1_y = start_y + dy * 0.3 + np.random.uniform(-offset, offset)
    
    ctrl2_x = start_x + dx * 0.7 + np.random.uniform(-offset, offset)
    ctrl2_y = start_y + dy * 0.7 + np.random.uniform(-offset, offset)
    
    # Control point matrix
    control_x = np.array([start_x, ctrl1_x, ctrl2_x, end_x], dtype=np.float32)
    control_y = np.array([start_y, ctrl1_y, ctrl2_y, end_y], dtype=np.float32)
    
    # Apply Bézier weights
    trajectory_x = weights @ control_x
    trajectory_y = weights @ control_y
    
    # Add hand tremor (10-12 Hz noise)
    if tremor_amplitude > 0:
        t = np.linspace(0, 1, num_points)
        tremor_x = np.sin(t * 12 * 2 * np.pi) * np.random.uniform(0.3, 1.0) * tremor_amplitude
        tremor_y = np.cos(t * 11 * 2 * np.pi) * np.random.uniform(0.3, 1.0) * tremor_amplitude
        
        trajectory_x += tremor_x
        trajectory_y += tremor_y
    
    # Combine into trajectory
    trajectory = np.stack([trajectory_x, trajectory_y], axis=1)
    
    return trajectory


def create_model(output_path: str = "assets/models/ghost_motor_v5.pkl"):
    """Create and save the trajectory model"""
    
    # Generate weights
    weights = generate_bezier_weights(num_points=20)
    
    # Model parameters (no function references - can't be pickled across modules)
    model = {
        'version': '7.0.0',
        'name': 'ghost_motor',
        'type': 'bezier_trajectory',
        'num_points': 20,
        'weights': weights,
        'default_randomness': 0.15,
        'default_tremor': 0.5,
    }
    
    # Save model
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    
    with open(output_path, 'wb') as f:
        pickle.dump(model, f)
    
    print(f"✓ Model saved to: {output_path}")
    print(f"  Type: Bézier trajectory generator")
    print(f"  Points: 20")
    
    return output_path


def test_model(model_path: str):
    """Test the model"""
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    
    print(f"\n✓ Model loaded: {model['name']} v{model['version']}")
    
    # Test trajectory generation
    trajectory = generate_trajectory(
        100, 100, 500, 400,
        model['weights'],
        model['default_randomness'],
        model['default_tremor']
    )
    
    print(f"  Test trajectory (100,100) → (500,400):")
    print(f"    First: ({trajectory[0][0]:.1f}, {trajectory[0][1]:.1f})")
    print(f"    Middle: ({trajectory[10][0]:.1f}, {trajectory[10][1]:.1f})")
    print(f"    Last: ({trajectory[-1][0]:.1f}, {trajectory[-1][1]:.1f})")
    
    return trajectory


if __name__ == "__main__":
    print("=" * 60)
    print("LUCID EMPIRE :: TRAJECTORY MODEL GENERATOR")
    print("=" * 60)
    print()
    
    model_path = "assets/models/ghost_motor_v5.pkl"
    
    create_model(model_path)
    print()
    test_model(model_path)
    
    print()
    print("=" * 60)
    print("Model ready for use")
    print("=" * 60)
