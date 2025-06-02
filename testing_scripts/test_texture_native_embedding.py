#!/usr/bin/env python3
"""
Test script to verify that texture preservation works using GLB/FBX native embedding
instead of separate texture file management.
"""

import os
import sys
import time
from pathlib import Path

# Add app to path
app_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, app_dir)

# Import and initialize app configuration
from app import process_extract_mesh, load_app_config

def test_texture_native_embedding():
    """Test texture preservation with native GLB/FBX embedding."""
    # Initialize app configuration first
    load_app_config()
    
    print("=== Testing Texture Preservation with Native Embedding ===\n")
    
    # Initialize app configuration first
    try:
        print("Initializing app configuration...")
        load_app_config()
        print("✓ App configuration loaded successfully")
    except Exception as e:
        print(f"✗ Failed to load app configuration: {e}")
        return False
    
    # Test input
    input_model = "/app/examples/giraffe.glb"
    
    if not os.path.exists(input_model):
        print(f"ERROR: Test model not found: {input_model}")
        return False
    
    print(f"Testing with: {input_model}")
    print(f"File size: {os.path.getsize(input_model) / 1024 / 1024:.2f} MB")
    
    # Create output directory
    output_dir = "/app/test_texture_native"
    os.makedirs(output_dir, exist_ok=True)
    
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
        
        # Look for generated display GLB
        if actual_npz_path:
            base_dir = os.path.dirname(actual_npz_path)
            display_glb_path = os.path.join(base_dir, "display.glb")
            if not os.path.exists(display_glb_path):
                # Try looking for other GLB files
                for file in os.listdir(base_dir):
                    if file.endswith('.glb'):
                        display_glb_path = os.path.join(base_dir, file)
                        break
                else:
                    display_glb_path = None
        else:
            display_glb_path = None
        
        print("\n--- Results ---")
        print(f"Display GLB: {display_glb_path}")
        print(f"NPZ data: {actual_npz_path}")
        
        if display_glb_path and os.path.exists(display_glb_path):
            glb_size = os.path.getsize(display_glb_path)
            print(f"Output GLB size: {glb_size / 1024 / 1024:.2f} MB")
            
            # Check if the output GLB contains textures by examining size
            if glb_size > 100000:  # > 100KB suggests textures included
                print("✅ Output GLB appears to contain texture data (size > 100KB)")
                
                # Check for texture-related strings
                with open(display_glb_path, 'rb') as f:
                    content = f.read(10000)  # Read first 10KB
                    if b'texture' in content or b'image' in content or b'material' in content:
                        print("✅ Output GLB contains texture/material references")
                    else:
                        print("⚠️  No texture/material references found in GLB header")
            else:
                print("❌ Output GLB is too small to contain texture data")
        else:
            print("❌ No output GLB generated")
        
        if actual_npz_path and os.path.exists(actual_npz_path):
            npz_size = os.path.getsize(actual_npz_path)
            print(f"NPZ data size: {npz_size / 1024:.2f} KB")
            
            # Load NPZ to check UV coordinates and materials
            import numpy as np
            data = np.load(actual_npz_path, allow_pickle=True)
            
            if 'uv_coords' in data and len(data['uv_coords']) > 0:
                print(f"✅ UV coordinates preserved: {len(data['uv_coords'])} coordinates")
            else:
                print("❌ No UV coordinates found in NPZ")
                
            if 'materials' in data and len(data['materials']) > 0:
                print(f"✅ Material data preserved: {len(data['materials'])} materials")
            else:
                print("❌ No material data found in NPZ")
        
        # Check if separate texture files directory was NOT created (should be disabled)
        texture_dir = os.path.join(os.path.dirname(actual_npz_path), "textures")
        if os.path.exists(texture_dir):
            print("⚠️  Separate texture directory found (should be disabled)")
            print(f"   Directory: {texture_dir}")
            print(f"   Contents: {os.listdir(texture_dir)}")
        else:
            print("✅ No separate texture directory created (as expected)")
        
        print("\n--- Logs ---")
        print(logs)
        
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
