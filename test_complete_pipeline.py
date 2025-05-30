#!/usr/bin/env python3
# Complete pipeline test: Extract -> Skeleton -> Skinning -> Merge

import os
import sys
import yaml
from box import Box

# Add the current directory to Python path for imports
sys.path.insert(0, '/app')

from app import (
    load_app_config, 
    process_extract_mesh, 
    process_generate_skeleton, 
    process_generate_skin,
    process_merge_model
)

def test_complete_pipeline():
    print("=== Testing Complete UniRig Pipeline ===")
    
    # Load configuration
    load_app_config('/app/configs/app_config.yaml')
    
    # Define test inputs
    model_name = "bird"
    original_model_path = "/app/examples/bird.glb"
    gender = "neutral"
    
    print(f"Testing complete pipeline with:")
    print(f"  Model: {model_name}")
    print(f"  Original file: {original_model_path}")
    print(f"  Gender: {gender}")
    
    # Check if input file exists
    if not os.path.exists(original_model_path):
        print(f"ERROR: Original model file not found: {original_model_path}")
        return False
    
    # Create dummy progress function
    def dummy_progress(progress, desc=""):
        print(f"Progress: {progress:.2f} - {desc}")
    
    try:
        print(f"\n=== STEP 1: Mesh Extraction ===")
        
        # Step 1: Extract mesh
        extracted_npz_path, extract_logs = process_extract_mesh(
            original_model_path=original_model_path,
            model_name_for_output=model_name,
            progress_fn=dummy_progress
        )
        
        print(f"Extract results:")
        print(f"  NPZ path: {extracted_npz_path}")
        print(f"  Logs: {extract_logs}")
        
        if not extracted_npz_path or not os.path.exists(extracted_npz_path):
            print("ERROR: Mesh extraction failed")
            return False
        
        file_size = os.path.getsize(extracted_npz_path)
        print(f"✓ Mesh extraction successful: {extracted_npz_path} ({file_size} bytes)")
        
        print(f"\n=== STEP 2: Skeleton Generation ===")
        
        # Step 2: Generate skeleton
        skeleton_results = process_generate_skeleton(
            extracted_npz_path=extracted_npz_path,
            model_name_for_output=model_name,
            gender=gender,
            progress_fn=dummy_progress
        )
        
        display_glb_path, skeleton_logs, skeleton_fbx_path, skeleton_txt_path, skeleton_npz_path = skeleton_results
        
        print(f"Skeleton results:")
        print(f"  Display GLB: {display_glb_path}")
        print(f"  FBX path: {skeleton_fbx_path}")
        print(f"  TXT path: {skeleton_txt_path}")
        print(f"  NPZ path: {skeleton_npz_path}")
        print(f"  Logs: {skeleton_logs}")
        
        if not skeleton_fbx_path or not skeleton_npz_path:
            print("ERROR: Skeleton generation failed")
            return False
        
        fbx_size = os.path.getsize(skeleton_fbx_path) if os.path.exists(skeleton_fbx_path) else 0
        npz_size = os.path.getsize(skeleton_npz_path) if os.path.exists(skeleton_npz_path) else 0
        print(f"✓ Skeleton generation successful:")
        print(f"  FBX: {skeleton_fbx_path} ({fbx_size} bytes)")
        print(f"  NPZ: {skeleton_npz_path} ({npz_size} bytes)")
        
        print(f"\n=== STEP 3: Skinning Prediction ===")
        
        # Step 3: Generate skinning
        skinning_results = process_generate_skin(
            raw_data_npz_path=extracted_npz_path,
            skeleton_fbx_path=skeleton_fbx_path,
            skeleton_npz_path=skeleton_npz_path,
            model_name_for_output=model_name,
            progress_fn=dummy_progress
        )
        
        skin_display_glb, skinning_logs, skinned_fbx_path, skinning_npz_path = skinning_results
        
        print(f"Skinning results:")
        print(f"  Display GLB: {skin_display_glb}")
        print(f"  Skinned FBX: {skinned_fbx_path}")
        print(f"  Skinning NPZ: {skinning_npz_path}")
        print(f"  Logs: {skinning_logs}")
        
        if not skinned_fbx_path or not skinning_npz_path:
            print("ERROR: Skinning prediction failed")
            return False
        
        skinned_fbx_size = os.path.getsize(skinned_fbx_path) if os.path.exists(skinned_fbx_path) else 0
        skinning_npz_size = os.path.getsize(skinning_npz_path) if os.path.exists(skinning_npz_path) else 0
        print(f"✓ Skinning prediction successful:")
        print(f"  Skinned FBX: {skinned_fbx_path} ({skinned_fbx_size} bytes)")
        print(f"  Skinning NPZ: {skinning_npz_path} ({skinning_npz_size} bytes)")
        
        print(f"\n=== STEP 4: Model Merge ===")
        
        # Step 4: Merge model
        merge_results = process_merge_model(
            original_model_path=original_model_path,
            skinned_fbx_path=skinned_fbx_path,
            skinning_npz_path=skinning_npz_path,
            model_name_for_output=model_name,
            progress_fn=dummy_progress
        )
        
        final_display_glb, merge_logs, final_fbx_path = merge_results
        
        print(f"Merge results:")
        print(f"  Final display GLB: {final_display_glb}")
        print(f"  Final FBX: {final_fbx_path}")
        print(f"  Logs: {merge_logs}")
        
        if not final_fbx_path or not os.path.exists(final_fbx_path):
            print("ERROR: Model merge failed")
            return False
        
        final_fbx_size = os.path.getsize(final_fbx_path)
        print(f"✓ Model merge successful:")
        print(f"  Final FBX: {final_fbx_path} ({final_fbx_size} bytes)")
        
        print(f"\n=== PIPELINE SUMMARY ===")
        print(f"✅ Step 1 - Mesh Extraction: {extracted_npz_path} ({file_size} bytes)")
        print(f"✅ Step 2 - Skeleton Generation: {skeleton_fbx_path} ({fbx_size} bytes)")
        print(f"✅ Step 3 - Skinning Prediction: {skinned_fbx_path} ({skinned_fbx_size} bytes)")
        print(f"✅ Step 4 - Model Merge: {final_fbx_path} ({final_fbx_size} bytes)")
        
        if final_display_glb and os.path.exists(final_display_glb):
            display_size = os.path.getsize(final_display_glb)
            print(f"🎨 Display GLB: {final_display_glb} ({display_size} bytes)")
        
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR during pipeline: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_complete_pipeline()
    if success:
        print("\n🎉 Complete pipeline test passed successfully!")
        print("🚀 UniRig is ready for production use!")
    else:
        print("\n❌ Complete pipeline test failed!")
    
    sys.exit(0 if success else 1)
