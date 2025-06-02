#!/usr/bin/env python3
"""
Test skeleton generation to debug ARWriter NPZ export
"""

import os
import sys
import subprocess
import tempfile

# Add the src directory to Python path
sys.path.insert(0, '/app')

def test_skeleton_generation():
    print("=== Testing Skeleton Generation with ARWriter Debug ===")
    
    # Check if we have any extracted mesh data
    test_mesh_paths = [
        "/app/test_env/test_outputs/01_extracted_mesh/bird/raw_data.npz",
        "/app/pipeline_work/01_extracted_mesh/bird/raw_data.npz", 
        "/app/pipeline_work/01_extracted_mesh/giraffe/raw_data.npz"
    ]
    
    # Find an existing extracted mesh
    extracted_npz_path = None
    for path in test_mesh_paths:
        if os.path.exists(path):
            extracted_npz_path = path
            print(f"✅ Found extracted mesh: {extracted_npz_path}")
            break
    
    if not extracted_npz_path:
        print("❌ No extracted mesh found. Creating a test one...")
        # Use the uploaded bird model that should exist
        test_model_path = "/app/test_env/uploads/bird.glb"
        if not os.path.exists(test_model_path):
            print("❌ No test model found. Cannot continue.")
            return False
            
        # Extract mesh first
        from src.data.extract import process_mesh_for_rigging
        temp_dir = "/app/test_env/temp_skeleton_test"
        os.makedirs(temp_dir, exist_ok=True)
        extracted_npz_path = os.path.join(temp_dir, "raw_data.npz")
        
        print(f"Extracting mesh from {test_model_path}...")
        try:
            process_mesh_for_rigging(test_model_path, extracted_npz_path)
            print(f"✅ Mesh extracted to: {extracted_npz_path}")
        except Exception as e:
            print(f"❌ Mesh extraction failed: {e}")
            return False
    
    if not os.path.exists(extracted_npz_path):
        print(f"❌ Extracted NPZ path does not exist: {extracted_npz_path}")
        return False
    
    # Run skeleton generation
    npz_directory = os.path.dirname(os.path.abspath(extracted_npz_path))
    output_dir = os.path.join("/app/test_env", "skeleton_debug_output")
    os.makedirs(output_dir, exist_ok=True)
    
    task_config_path = "/app/configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml"
    
    cmd = [
        sys.executable, "/app/run.py",
        "--task", task_config_path,
        "--input_dir", npz_directory,
        "--output_dir", output_dir,
        "--npz_dir", npz_directory,
        "--seed", "42"
    ]
    
    print(f"Running skeleton generation command:")
    print(f"  {' '.join(cmd)}")
    print(f"Input directory: {npz_directory}")
    print(f"Output directory: {output_dir}")
    
    try:
        # Run the command with output capture
        result = subprocess.run(
            cmd, 
            cwd="/app",
            capture_output=True, 
            text=True, 
            timeout=300  # 5 minute timeout
        )
        
        print(f"Return code: {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")
        
        # Check for output files
        expected_npz = os.path.join(output_dir, npz_directory.replace("/app/", ""), "predict_skeleton.npz")
        expected_fbx = os.path.join(output_dir, npz_directory.replace("/app/", ""), "skeleton.fbx")
        
        print(f"\nChecking for output files:")
        print(f"Expected NPZ: {expected_npz}")
        print(f"Expected FBX: {expected_fbx}")
        
        # Search in the entire output directory
        print(f"\nSearching output directory for any files:")
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                full_path = os.path.join(root, file)
                size = os.path.getsize(full_path)
                print(f"  {full_path} ({size} bytes)")
                
                # Check if this is a skeleton NPZ file
                if file == "predict_skeleton.npz":
                    print(f"🎯 Found skeleton NPZ: {full_path}")
                    # Check contents
                    try:
                        from src.data.raw_data import RawData
                        skeleton_data = RawData.load(full_path)
                        print(f"   UV coords: {hasattr(skeleton_data, 'uv_coords') and skeleton_data.uv_coords is not None}")
                        if hasattr(skeleton_data, 'uv_coords') and skeleton_data.uv_coords is not None:
                            print(f"   UV coords length: {len(skeleton_data.uv_coords)}")
                        print(f"   Materials: {hasattr(skeleton_data, 'materials') and skeleton_data.materials is not None}")
                        if hasattr(skeleton_data, 'materials') and skeleton_data.materials is not None:
                            print(f"   Materials length: {len(skeleton_data.materials)}")
                    except Exception as e:
                        print(f"   ❌ Error reading skeleton NPZ: {e}")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ Skeleton generation timed out")
        return False
    except Exception as e:
        print(f"❌ Error running skeleton generation: {e}")
        return False

if __name__ == "__main__":
    success = test_skeleton_generation()
    if success:
        print("✅ Skeleton generation test completed")
    else:
        print("❌ Skeleton generation test failed")
