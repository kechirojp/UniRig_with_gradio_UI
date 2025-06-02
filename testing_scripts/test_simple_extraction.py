#!/usr/bin/env python3
"""Simple test of mesh extraction with minimal dependencies."""

import os
import subprocess
import sys

def test_mesh_extraction_simple():
    """Test mesh extraction in a simple way."""
    print("=== Simple Mesh Extraction Test ===")
    
    # Parameters
    model_path = "/app/examples/bird.glb"
    output_dir = "/tmp/test_simple_extraction"
    config_path = "/app/configs/extract_config.yaml"
    
    print(f"Model: {model_path}")
    print(f"Output: {output_dir}")
    print(f"Config: {config_path}")
    
    # Check input file exists
    if not os.path.exists(model_path):
        print(f"✗ Model file not found: {model_path}")
        return False
    
    if not os.path.exists(config_path):
        print(f"✗ Config file not found: {config_path}")
        return False
    
    # Clean output directory
    if os.path.exists(output_dir):
        subprocess.run(["rm", "-rf", output_dir], check=True)
    
    # Run extraction
    cmd = [
        sys.executable, "-m", "src.data.extract",
        "--config", config_path,
        "--model_path", model_path, 
        "--output_dir", output_dir
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    
    try:
        # Set environment
        env = os.environ.copy()
        env['PYTHONPATH'] = f"/app:{env.get('PYTHONPATH', '')}"
        
        result = subprocess.run(
            cmd, 
            cwd="/app",
            env=env,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        print(f"Return code: {result.returncode}")
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        # Check output
        npz_path = os.path.join(output_dir, "raw_data.npz")
        datalist_path = os.path.join(output_dir, "inference_datalist.txt")
        
        if os.path.exists(npz_path):
            file_size = os.path.getsize(npz_path)
            print(f"✓ NPZ file created: {npz_path} ({file_size} bytes)")
            
            if os.path.exists(datalist_path):
                print(f"✓ Datalist created: {datalist_path}")
                with open(datalist_path, 'r') as f:
                    print(f"Datalist content: {f.read().strip()}")
            
            return True
        else:
            print(f"✗ NPZ file not found: {npz_path}")
            return False
            
    except subprocess.TimeoutExpired:
        print("✗ Command timed out")
        return False
    except Exception as e:
        print(f"✗ Error running command: {e}")
        return False

if __name__ == "__main__":
    success = test_mesh_extraction_simple()
    print(f"\nTest result: {'PASS' if success else 'FAIL'}")
    exit(0 if success else 1)
