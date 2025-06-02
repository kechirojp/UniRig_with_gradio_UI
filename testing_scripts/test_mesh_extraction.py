#!/usr/bin/env python3
"""
Test script for mesh extraction functionality
"""
import os
import sys

# Test the mesh extraction directly
def test_mesh_extraction():
    print("Testing mesh extraction functionality...")
    
    # Use an existing model file for testing
    test_model_path = "/app/examples/bird.glb"
    if not os.path.exists(test_model_path):
        print(f"Test model not found: {test_model_path}")
        return False
    
    print(f"Using test model: {test_model_path}")
    
    # Test the extract.py script with the model
    import subprocess
    try:
        result = subprocess.run([
            sys.executable, "/app/src/data/extract.py",
            "--input_path", test_model_path,
            "--output_dir", "/tmp/test_extraction",
            "--target_count", "1000"
        ], capture_output=True, text=True, timeout=60)
        
        print(f"Extract script return code: {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")
        
        # Check if output was created
        output_file = "/tmp/test_extraction/bird/raw_data.npz"
        if os.path.exists(output_file):
            print(f"SUCCESS: Output file created: {output_file}")
            # Check file size
            size = os.path.getsize(output_file)
            print(f"Output file size: {size} bytes")
            return True
        else:
            print(f"ERROR: Output file not created: {output_file}")
            return False
            
    except subprocess.TimeoutExpired:
        print("ERROR: Extract script timed out")
        return False
    except Exception as e:
        print(f"ERROR: Exception running extract script: {e}")
        return False

if __name__ == "__main__":
    success = test_mesh_extraction()
    sys.exit(0 if success else 1)
