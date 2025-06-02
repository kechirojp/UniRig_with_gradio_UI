#!/usr/bin/env python3
# Test merge model process only

import os
import sys
import yaml
from box import Box

# Add the current directory to Python path for imports
sys.path.insert(0, '/app')

from app import load_app_config, process_merge_model

def test_merge_model():
    print("=== Testing Merge Model Process ===")
    
    # Load configuration
    load_app_config('/app/configs/app_config.yaml')
    
    # Define test inputs - using bird example
    model_name = "bird"
    original_model_path = "/app/examples/bird.glb"
    
    # These paths should exist from previous skeleton and skinning steps
    skinned_fbx_path = "/app/pipeline_work/03_skinning_output/bird/skinned_model.fbx"
    skinning_npz_path = "/app/pipeline_work/03_skinning_output/bird/predict_skin.npz"
    
    print(f"Testing with:")
    print(f"  Original model: {original_model_path}")
    print(f"  Skinned FBX: {skinned_fbx_path}")
    print(f"  Skinning NPZ: {skinning_npz_path}")
    
    # Check if input files exist
    print(f"\nFile existence check:")
    print(f"  Original model exists: {os.path.exists(original_model_path)}")
    print(f"  Skinned FBX exists: {os.path.exists(skinned_fbx_path)}")
    print(f"  Skinning NPZ exists: {os.path.exists(skinning_npz_path)}")
    
    if not os.path.exists(skinned_fbx_path):
        print("ERROR: Skinned FBX file not found. Please run skinning step first.")
        return False
        
    if not os.path.exists(skinning_npz_path):
        print("ERROR: Skinning NPZ file not found. Please run skinning step first.")
        return False
    
    # Create dummy progress function
    def dummy_progress(progress, desc=""):
        print(f"Progress: {progress:.2f} - {desc}")
    
    try:
        print(f"\n=== Starting merge process ===")
        
        display_glb_path, logs, final_fbx_path = process_merge_model(
            original_model_path=original_model_path,
            skinned_fbx_path=skinned_fbx_path,
            skinning_npz_path=skinning_npz_path,
            model_name_for_output=model_name,
            progress_fn=dummy_progress
        )
        
        print(f"\n=== Merge Results ===")
        print(f"Display GLB path: {display_glb_path}")
        print(f"Final FBX path: {final_fbx_path}")
        print(f"\n=== Process Logs ===")
        print(logs)
        
        if final_fbx_path and os.path.exists(final_fbx_path):
            file_size = os.path.getsize(final_fbx_path)
            print(f"\n✓ SUCCESS: Final FBX created successfully!")
            print(f"  File: {final_fbx_path}")
            print(f"  Size: {file_size} bytes")
            return True
        else:
            print(f"\n✗ FAILED: Final FBX not created or empty")
            return False
            
    except Exception as e:
        print(f"\n✗ ERROR during merge process: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_merge_model()
    if success:
        print("\n🎉 Merge test completed successfully!")
    else:
        print("\n❌ Merge test failed!")
    
    sys.exit(0 if success else 1)
