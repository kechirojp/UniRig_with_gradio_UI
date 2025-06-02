#!/usr/bin/env python3
"""
Test skinning process with existing bird files
"""
import os
import sys
sys.path.append('/app')

# Import and initialize config
from app import load_app_config, process_generate_skin

# Load configuration
load_app_config()

def test_skinning():
    print("=== Testing Skinning Process ===")
    
    # Input files from previous steps
    raw_data_npz_path = "/app/pipeline_work/01_extracted_mesh/bird/raw_data.npz"
    skeleton_fbx_path = "/app/pipeline_work/01_extracted_mesh/bird/skeleton.fbx"
    skeleton_npz_path = "/app/pipeline_work/01_extracted_mesh/bird/predict_skeleton.npz"
    model_name = "bird"
    
    # Check input files exist
    for path in [raw_data_npz_path, skeleton_fbx_path, skeleton_npz_path]:
        if os.path.exists(path):
            size = os.path.getsize(path)
            print(f"✓ {path} ({size} bytes)")
        else:
            print(f"✗ Missing: {path}")
            return False
    
    # Dummy progress function
    def progress_fn(value, desc=None):
        print(f"Progress: {value:.2%} - {desc}")
    
    print("\n--- Starting skinning process ---")
    
    try:
        display_glb_path, logs, skinned_fbx_path, skinning_npz_path = process_generate_skin(
            raw_data_npz_path=raw_data_npz_path,
            skeleton_fbx_path=skeleton_fbx_path,
            skeleton_npz_path=skeleton_npz_path,
            model_name_for_output=model_name,
            progress_fn=progress_fn
        )
        
        print("\n--- Results ---")
        print(f"Display GLB: {display_glb_path}")
        print(f"Skinned FBX: {skinned_fbx_path}")
        print(f"Skinning NPZ: {skinning_npz_path}")
        
        print("\n--- Process Logs ---")
        print(logs)
        
        # Check if output files were created
        success = True
        if skinned_fbx_path and os.path.exists(skinned_fbx_path):
            size = os.path.getsize(skinned_fbx_path)
            print(f"✓ Skinned FBX created: {skinned_fbx_path} ({size} bytes)")
        else:
            print(f"✗ Skinned FBX not created: {skinned_fbx_path}")
            success = False
            
        if skinning_npz_path and os.path.exists(skinning_npz_path):
            size = os.path.getsize(skinning_npz_path)
            print(f"✓ Skinning NPZ created: {skinning_npz_path} ({size} bytes)")
        else:
            print(f"✗ Skinning NPZ not created: {skinning_npz_path}")
            success = False
        
        return success
        
    except Exception as e:
        print(f"✗ Exception during skinning: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_skinning()
    print(f"\n=== Test Result: {'SUCCESS' if success else 'FAILED'} ===")
