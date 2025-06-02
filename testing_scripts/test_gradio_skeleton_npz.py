#!/usr/bin/env python3
"""
Test NPZ file detection in Gradio skeleton generation process
"""

import os
import sys
import numpy as np
import gradio as gr
from gradio_client import Client

# Add the app directory to Python path
sys.path.append('/app')

def test_gradio_skeleton_generation():
    """Test skeleton generation through Gradio interface to verify NPZ detection"""
    
    # Connect to the local Gradio app
    try:
        client = Client("http://localhost:7861", verbose=True)
        print("✓ Successfully connected to Gradio app")
    except Exception as e:
        print(f"✗ Failed to connect to Gradio app: {e}")
        return False

    # Use an existing example file
    test_file = "/app/examples/bird.glb"
    if not os.path.exists(test_file):
        print(f"✗ Test file not found: {test_file}")
        return False
    
    print(f"✓ Using test file: {test_file}")

    try:
        # Step 1: Extract mesh (equivalent to gradio_extract_mesh)
        print("\n--- Step 1: Mesh Extraction ---")
        extraction_result = client.predict(
            uploaded_file=test_file,
            model_name="bird_gradio_test",
            api_name="/extract_mesh"
        )
        
        print(f"Extraction result type: {type(extraction_result)}")
        print(f"Extraction result: {extraction_result}")
        
        # The result should be a tuple: (logs, raw_data_npz_path, model_name)
        if isinstance(extraction_result, (list, tuple)) and len(extraction_result) >= 3:
            logs, raw_data_npz_path, model_name = extraction_result[0], extraction_result[1], extraction_result[2]
            print(f"✓ Mesh extraction logs: {logs[:200]}...")
            print(f"✓ NPZ path from extraction: {raw_data_npz_path}")
            print(f"✓ Model name: {model_name}")
            
            if raw_data_npz_path and os.path.exists(raw_data_npz_path):
                print(f"✓ NPZ file exists: {raw_data_npz_path}")
                file_size = os.path.getsize(raw_data_npz_path)
                print(f"✓ NPZ file size: {file_size} bytes")
            else:
                print(f"✗ NPZ file not found: {raw_data_npz_path}")
                return False
        else:
            print(f"✗ Unexpected extraction result format: {extraction_result}")
            return False

        # Step 2: Generate skeleton (equivalent to gradio_generate_skeleton)
        print("\n--- Step 2: Skeleton Generation ---")
        skeleton_result = client.predict(
            raw_data_npz_path_from_state=raw_data_npz_path,
            model_name_from_state=model_name,
            gender="unknown",
            api_name="/generate_skeleton"
        )
        
        print(f"Skeleton result type: {type(skeleton_result)}")
        print(f"Skeleton result length: {len(skeleton_result) if isinstance(skeleton_result, (list, tuple)) else 'Not a list/tuple'}")
        
        # The result should be a tuple with multiple elements
        if isinstance(skeleton_result, (list, tuple)) and len(skeleton_result) >= 7:
            (skeleton_model_display, logs_output, skeleton_fbx_download, 
             skeleton_txt_download, skeleton_npz_download, 
             skeleton_fbx_path_state, skeleton_npz_path_state) = skeleton_result
            
            print(f"\n--- Skeleton Generation Results ---")
            print(f"Display model: {skeleton_model_display}")
            print(f"FBX download: {skeleton_fbx_download}")
            print(f"TXT download: {skeleton_txt_download}")
            print(f"NPZ download: {skeleton_npz_download}")
            print(f"FBX path state: {skeleton_fbx_path_state}")
            print(f"NPZ path state: {skeleton_npz_path_state}")
            
            print(f"\n--- Skeleton Generation Logs ---")
            print(logs_output)
            
            # Check if NPZ file was found and returned
            if skeleton_npz_path_state and os.path.exists(skeleton_npz_path_state):
                file_size = os.path.getsize(skeleton_npz_path_state)
                print(f"✓ Skeleton NPZ file found: {skeleton_npz_path_state}")
                print(f"✓ Skeleton NPZ file size: {file_size} bytes")
                return True
            else:
                print(f"✗ Skeleton NPZ file not found: {skeleton_npz_path_state}")
                return False
        else:
            print(f"✗ Unexpected skeleton result format or length: {len(skeleton_result) if isinstance(skeleton_result, (list, tuple)) else 'Not a list/tuple'}")
            return False
            
    except Exception as e:
        print(f"✗ Error during Gradio testing: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=== Testing Gradio Skeleton Generation with NPZ Detection ===")
    
    # Wait a bit for Gradio to be fully ready
    import time
    print("Waiting for Gradio to be ready...")
    time.sleep(3)
    
    success = test_gradio_skeleton_generation()
    
    if success:
        print("\n✅ SUCCESS: Gradio skeleton generation with NPZ detection works correctly!")
    else:
        print("\n❌ FAILURE: There are issues with Gradio skeleton generation or NPZ detection.")
    
    return success

if __name__ == "__main__":
    main()
