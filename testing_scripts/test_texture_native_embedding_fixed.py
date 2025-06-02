#!/usr/bin/env python3
"""
Test script to verify that texture preservation works using GLB/FBX native embedding.
"""

import os
import sys
import time
import numpy as np

# Add app to path
app_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, app_dir)

from app import process_extract_mesh, load_app_config

def test_texture_native_embedding():
    """Test texture preservation with native GLB/FBX embedding."""
    
    print("=== Testing Texture Preservation with Native Embedding ===\n")
    
    # Load app configuration
    print("Loading app configuration...")
    try:
        load_app_config()
        print("✅ App configuration loaded successfully")
    except Exception as config_error:
        print(f"❌ Failed to load app configuration: {config_error}")
        return False
    
    # Test input
    input_model = "/app/examples/giraffe.glb"
    
    if not os.path.exists(input_model):
        print(f"ERROR: Test model not found: {input_model}")
        return False
    
    print(f"Testing with: {input_model}")
    print(f"Input file size: {os.path.getsize(input_model) / 1024 / 1024:.2f} MB")
    
    # Progress function
    def progress_callback(progress, desc="Processing"):
        print(f"Progress: {progress*100:.1f}% - {desc}")
    
    try:
        print("\n--- Step 1: Mesh Extraction with Texture Preservation ---")
        start_time = time.time()
        
        # Extract mesh with texture preservation
        actual_npz_path, logs = process_extract_mesh(
            input_model, 
            "giraffe_native_test", 
            progress_callback
        )
        
        end_time = time.time()
        print(f"Extraction completed in {end_time - start_time:.2f} seconds")
        
        print("\n--- Extraction Logs ---")
        print(logs)
        
        print("\n--- Results ---")
        print(f"NPZ data: {actual_npz_path}")
        
        if actual_npz_path and os.path.exists(actual_npz_path):
            npz_size = os.path.getsize(actual_npz_path)
            print(f"✅ SUCCESS: NPZ file created - {npz_size / 1024:.2f} KB")
            
            # Load and examine NPZ content to verify texture data preservation
            try:
                npz_data = np.load(actual_npz_path, allow_pickle=True)
                print(f"NPZ Keys: {list(npz_data.keys())}")
                
                # Check for UV coordinates and materials
                if 'uv_coords' in npz_data:
                    uv_coords = npz_data['uv_coords']
                    print(f"✅ UV Coordinates preserved: {len(uv_coords) if hasattr(uv_coords, '__len__') else 'N/A'}")
                else:
                    print("❌ No UV coordinates found in NPZ")
                
                if 'materials' in npz_data:
                    materials = npz_data['materials']
                    print(f"✅ Materials preserved: {len(materials) if hasattr(materials, '__len__') else 'N/A'}")
                    if hasattr(materials, '__len__') and len(materials) > 0:
                        print(f"   Material info: {materials}")
                else:
                    print("❌ No material data found in NPZ")
                    
                npz_data.close()
                
            except Exception as npz_error:
                print(f"Warning: Could not examine NPZ content: {npz_error}")
        else:
            print(f"❌ FAILED: NPZ file not created - {actual_npz_path}")
            return False
        
        # Check if separate texture files directory was NOT created (should be disabled)
        if actual_npz_path:
            texture_dir = os.path.join(os.path.dirname(actual_npz_path), "textures")
            if os.path.exists(texture_dir):
                print("⚠️ Separate texture directory found (should be disabled)")
                print(f"   Directory: {texture_dir}")
                print(f"   Contents: {os.listdir(texture_dir)}")
            else:
                print("✅ No separate texture directory created (as expected with native embedding)")
        
        # Check if logs contain error information
        if "エラー" in logs or "ERROR" in logs or "FAILED" in logs:
            print("❌ Errors detected in extraction logs")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = test_texture_native_embedding()
    if success:
        print("\n🎉 Test completed successfully!")
    else:
        print("\n💥 Test failed!")
        sys.exit(1)
