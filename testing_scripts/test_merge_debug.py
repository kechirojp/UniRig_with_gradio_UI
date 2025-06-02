#!/usr/bin/env python3
"""
Test merge process with detailed debugging of texture/material information.
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path

def run_merge_test():
    print("=== Merge Process Texture Debug Test ===\n")
    
    # Test files
    input_glb = "/app/examples/giraffe.glb"
    output_dir = "/app/test_merge_debug_output"
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Testing with: {input_glb}")
    print(f"Input file size: {os.path.getsize(input_glb) / 1024 / 1024:.2f} MB\n")
    
    # First, run a full pipeline to get intermediate files
    print("--- Step 1: Running full pipeline to get intermediate files ---")
    
    # Import app and run pipeline
    sys.path.insert(0, '/app')
    from app import (
        process_extract_mesh, process_generate_skeleton, 
        process_generate_skin, process_merge_model,
        load_app_config
    )
    
    # Load configuration
    load_app_config()
    from app import APP_CONFIG
    if not APP_CONFIG:
        print("❌ Failed to load app configuration")
        return
    
    model_name = "merge_debug_test"
    
    # Progress callback (dummy)
    def dummy_progress(value, desc=""):
        print(f"Progress: {value*100:.1f}% - {desc}")
    
    # Stage 1: Extract mesh
    print("\n--- Stage 1: Mesh Extraction ---")
    extracted_npz_path, extract_logs = process_extract_mesh(
        input_glb, model_name, dummy_progress
    )
    
    if extracted_npz_path:
        print(f"✅ Stage 1 success: {extracted_npz_path}")
    else:
        print("❌ Stage 1 failed")
        print(extract_logs)
        return
    
    # Stage 2: Generate skeleton
    print("\n--- Stage 2: Skeleton Generation ---")
    skeleton_display, skeleton_logs, skeleton_fbx_path, skeleton_txt_path, skeleton_npz_path = process_generate_skeleton(
        extracted_npz_path, model_name, "neutral", dummy_progress
    )
    
    if skeleton_npz_path and skeleton_fbx_path:
        print(f"✅ Stage 2 success: {skeleton_npz_path}")
        print(f"   FBX: {skeleton_fbx_path}")
    else:
        print("❌ Stage 2 failed")
        print(skeleton_logs)
        return
    
    # Stage 3: Generate skin weights
    print("\n--- Stage 3: Skin Weight Generation ---")
    skin_display_path, skin_logs, skinned_fbx_path, skinning_npz_path = process_generate_skin(
        extracted_npz_path, skeleton_fbx_path, skeleton_npz_path, model_name, dummy_progress
    )
    
    if skinning_npz_path and skinned_fbx_path:
        print(f"✅ Stage 3 success: {skinning_npz_path}")
        print(f"   FBX: {skinned_fbx_path}")
    else:
        print("❌ Stage 3 failed")
        print(skin_logs)
        return
    
    # Stage 4: Merge with detailed debugging
    print("\n--- Stage 4: Model Merging with Debug ---")
    
    final_display_glb, merge_logs, final_fbx_path = process_merge_model(
        input_glb, skinned_fbx_path, skinning_npz_path, model_name, dummy_progress
    )
    
    if final_fbx_path:
        print(f"✅ Stage 4 success: {final_fbx_path}")
        print(f"   File size: {os.path.getsize(final_fbx_path) / 1024 / 1024:.2f} MB")
        
        # Copy to output directory for inspection
        output_fbx = os.path.join(output_dir, "final_rigged_model.fbx")
        shutil.copy2(final_fbx_path, output_fbx)
        print(f"✅ Copied final model to: {output_fbx}")
        
        # Run GLB conversion for comparison
        print("\n--- Converting to GLB for texture inspection ---")
        output_glb = os.path.join(output_dir, "final_rigged_model.glb")
        
        try:
            cmd = [
                "blender", "--background", "--python", "/app/blender/fbx_to_glb_converter.py",
                "--", final_fbx_path, output_glb
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print(f"✅ GLB conversion success: {output_glb}")
                print(f"   GLB size: {os.path.getsize(output_glb) / 1024 / 1024:.2f} MB")
            else:
                print(f"❌ GLB conversion failed: {result.stderr}")
        except Exception as e:
            print(f"❌ GLB conversion error: {e}")
        
    else:
        print("❌ Stage 4 failed")
        print(merge_logs)
        return
    
    print(f"\n--- Debug output saved to: {output_dir} ---")
    
    # Analyze merge logs for texture information
    print("\n--- Merge Logs Analysis ---")
    print(merge_logs)

if __name__ == "__main__":
    run_merge_test()
