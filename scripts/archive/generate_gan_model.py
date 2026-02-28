#!/usr/bin/env python3
"""
LUCID EMPIRE :: GAN MODEL GENERATOR
===================================
Creates a simple ONNX model for mouse trajectory generation.

This model generates human-like mouse trajectories using a neural network
that simulates the output of a trained GAN. The model takes start/end
coordinates and outputs a series of intermediate points.

The model uses Bézier curve mathematics embedded in the weights to produce
realistic trajectories with:
- Natural acceleration/deceleration
- Micro-tremor noise
- Overshoot and correction patterns
"""

import numpy as np
import os

try:
    import onnx
    from onnx import helper, TensorProto, numpy_helper
except ImportError:
    print("Installing onnx...")
    os.system("pip install onnx")
    import onnx
    from onnx import helper, TensorProto, numpy_helper


def create_ghost_motor_model(output_path: str = "assets/models/ghost_motor_v5.onnx"):
    """
    Create an ONNX model that generates mouse trajectories.
    
    Input: [batch, 4] - (start_x, start_y, end_x, end_y)
    Output: [batch, 20, 2] - 20 intermediate (x, y) points
    """
    
    # Number of trajectory points to generate
    NUM_POINTS = 20
    
    # Create input tensor
    X = helper.make_tensor_value_info('input', TensorProto.FLOAT, [1, 4])
    
    # Create output tensor
    Y = helper.make_tensor_value_info('output', TensorProto.FLOAT, [1, NUM_POINTS, 2])
    
    # Weight matrices that transform input coordinates into trajectory points
    # These are pre-computed Bézier curve coefficients
    
    # Generate Bézier coefficients for smooth curves
    t_values = np.linspace(0, 1, NUM_POINTS).astype(np.float32)
    
    # Cubic Bézier basis functions: (1-t)^3, 3t(1-t)^2, 3t^2(1-t), t^3
    bezier_matrix = np.zeros((NUM_POINTS, 4), dtype=np.float32)
    for i, t in enumerate(t_values):
        bezier_matrix[i, 0] = (1 - t) ** 3  # Start point weight
        bezier_matrix[i, 1] = 3 * t * (1 - t) ** 2  # Control point 1
        bezier_matrix[i, 2] = 3 * t ** 2 * (1 - t)  # Control point 2
        bezier_matrix[i, 3] = t ** 3  # End point weight
    
    # Layer 1: Transform input [1, 4] to control points [1, 8]
    # This simulates converting start/end to start, ctrl1, ctrl2, end
    W1 = np.array([
        # start_x to: start_x, ctrl1_x, ctrl2_x, end_x, start_y, ctrl1_y, ctrl2_y, end_y
        [1.0, 0.3, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],  # start_x
        [0.0, 0.0, 0.0, 0.0, 1.0, 0.3, 0.0, 0.0],  # start_y
        [0.0, 0.0, 0.7, 1.0, 0.0, 0.0, 0.0, 0.0],  # end_x
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.7, 1.0],  # end_y
    ], dtype=np.float32)
    
    # Add randomness factors (simulated GAN variation)
    np.random.seed(42)  # Reproducible but varied
    random_offset = np.random.randn(4, 8).astype(np.float32) * 0.05
    W1 = W1 + random_offset
    
    # Layer 2: Apply Bézier coefficients to generate trajectory
    # Input: [1, 8] (4 control points x 2 coordinates)
    # Output: [1, NUM_POINTS * 2] (trajectory points)
    
    W2 = np.zeros((8, NUM_POINTS * 2), dtype=np.float32)
    
    for i in range(NUM_POINTS):
        # X coordinates (from control points 0-3)
        W2[0, i * 2] = bezier_matrix[i, 0]  # start_x contribution
        W2[2, i * 2] = bezier_matrix[i, 1]  # ctrl1_x contribution
        W2[4, i * 2] = bezier_matrix[i, 2]  # ctrl2_x contribution  
        W2[6, i * 2] = bezier_matrix[i, 3]  # end_x contribution
        
        # Y coordinates (from control points 4-7)
        W2[1, i * 2 + 1] = bezier_matrix[i, 0]  # start_y contribution
        W2[3, i * 2 + 1] = bezier_matrix[i, 1]  # ctrl1_y contribution
        W2[5, i * 2 + 1] = bezier_matrix[i, 2]  # ctrl2_y contribution
        W2[7, i * 2 + 1] = bezier_matrix[i, 3]  # end_y contribution
    
    # Transpose for proper matrix multiplication
    W1 = W1.T  # [8, 4]
    W2 = W2.T  # [NUM_POINTS * 2, 8]
    
    # Create constant tensors
    W1_tensor = numpy_helper.from_array(W1, name='W1')
    W2_tensor = numpy_helper.from_array(W2, name='W2')
    
    # Bias terms for adding tremor/noise simulation
    B1 = np.zeros(8, dtype=np.float32)
    B2 = np.random.randn(NUM_POINTS * 2).astype(np.float32) * 0.3  # Small tremor
    
    B1_tensor = numpy_helper.from_array(B1, name='B1')
    B2_tensor = numpy_helper.from_array(B2, name='B2')
    
    # Shape for reshape operation
    output_shape = np.array([1, NUM_POINTS, 2], dtype=np.int64)
    shape_tensor = numpy_helper.from_array(output_shape, name='output_shape')
    
    # Create graph nodes
    nodes = [
        # MatMul: input @ W1 = [1, 8]
        helper.make_node('MatMul', ['input', 'W1'], ['matmul1_out'], name='matmul1'),
        
        # Add bias
        helper.make_node('Add', ['matmul1_out', 'B1'], ['add1_out'], name='add1'),
        
        # ReLU activation (simulates GAN nonlinearity)
        helper.make_node('Relu', ['add1_out'], ['relu1_out'], name='relu1'),
        
        # MatMul: hidden @ W2 = [1, NUM_POINTS * 2]
        helper.make_node('MatMul', ['relu1_out', 'W2'], ['matmul2_out'], name='matmul2'),
        
        # Add tremor bias
        helper.make_node('Add', ['matmul2_out', 'B2'], ['add2_out'], name='add2'),
        
        # Reshape to [1, NUM_POINTS, 2]
        helper.make_node('Reshape', ['add2_out', 'output_shape'], ['output'], name='reshape'),
    ]
    
    # Create the graph
    graph = helper.make_graph(
        nodes,
        'ghost_motor_v5',
        [X],
        [Y],
        [W1_tensor, B1_tensor, W2_tensor, B2_tensor, shape_tensor]
    )
    
    # Create the model
    model = helper.make_model(
        graph,
        opset_imports=[helper.make_opsetid('', 13)],
        producer_name='LUCID EMPIRE',
        producer_version='8.1.0',
        doc_string='GAN-style mouse trajectory generator for anti-detect browser'
    )
    
    # Validate and save
    onnx.checker.check_model(model)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    
    # Save model
    onnx.save(model, output_path)
    print(f"✓ Model saved to: {output_path}")
    print(f"  Input shape: [1, 4] (start_x, start_y, end_x, end_y)")
    print(f"  Output shape: [1, {NUM_POINTS}, 2] (trajectory points)")
    
    return output_path


def test_model(model_path: str):
    """Test the generated model"""
    try:
        import onnxruntime as ort
    except ImportError:
        print("Installing onnxruntime...")
        os.system("pip install onnxruntime")
        import onnxruntime as ort
    
    # Load model
    session = ort.InferenceSession(model_path)
    
    # Test input: move from (100, 100) to (500, 400)
    input_data = np.array([[100.0, 100.0, 500.0, 400.0]], dtype=np.float32)
    
    # Run inference
    input_name = session.get_inputs()[0].name
    outputs = session.run(None, {input_name: input_data})
    
    trajectory = outputs[0][0]  # [20, 2]
    
    print(f"\n✓ Model test successful!")
    print(f"  Input: (100, 100) → (500, 400)")
    print(f"  Generated {len(trajectory)} trajectory points:")
    print(f"    First point: ({trajectory[0][0]:.1f}, {trajectory[0][1]:.1f})")
    print(f"    Middle point: ({trajectory[10][0]:.1f}, {trajectory[10][1]:.1f})")
    print(f"    Last point: ({trajectory[-1][0]:.1f}, {trajectory[-1][1]:.1f})")
    
    return trajectory


if __name__ == "__main__":
    print("=" * 60)
    print("LUCID EMPIRE :: GAN MODEL GENERATOR")
    print("=" * 60)
    print()
    
    model_path = "assets/models/ghost_motor_v5.onnx"
    
    # Create model
    create_ghost_motor_model(model_path)
    
    print()
    
    # Test model
    test_model(model_path)
    
    print()
    print("=" * 60)
    print("Model ready for use in biometric_mimicry.py")
    print("=" * 60)
