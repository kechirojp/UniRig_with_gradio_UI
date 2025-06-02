#!/usr/bin/env python3
"""Direct test of the mesh extraction function."""

import sys
import os
sys.path.append('/app')

from app import process_extract_mesh, load_app_config

def test_direct_mesh_extraction():
    """Test mesh extraction function directly."""
    print("Testing mesh extraction function directly...")
    
    # Load app config
    load_app_config()
    
    # Test parameters
    model_path = "/app/examples/bird.glb" 
    model_name = "bird_direct_test"
    
    if not os.path.exists(model_path):
        print(f"Error: Test model file not found: {model_path}")
        return False
    
    print(f"Testing with model: {model_path}")
    print(f"Model name: {model_name}")
    
    try:
        # Mock progress function
        def progress_fn(value, desc=""):
            print(f"Progress: {value:.1%} - {desc}")
        
        # Call the mesh extraction function
        result_path, logs = process_extract_mesh(
            original_model_path=model_path,
            model_name_for_output=model_name,
            progress_fn=progress_fn
        )
        
        print("\n=== MESH EXTRACTION LOGS ===")
        print(logs)
        print("=============================\n")
        
        # Check result
        if result_path and os.path.exists(result_path):
            file_size = os.path.getsize(result_path)
            print(f"✓ Success! NPZ file created: {result_path} ({file_size} bytes)")
            
            # Check datalist file
            output_dir = os.path.dirname(result_path)
            datalist_path = os.path.join(output_dir, "inference_datalist.txt")
            if os.path.exists(datalist_path):
                print(f"✓ Datalist file also created: {datalist_path}")
                with open(datalist_path, 'r') as f:
                    print(f"Datalist content: {f.read().strip()}")
            
            return True
        else:
            print("✗ Failed: NPZ file was not created")
            return False
            
    except Exception as e:
        print(f"✗ Error during mesh extraction test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_direct_mesh_extraction()
    exit(0 if success else 1)
