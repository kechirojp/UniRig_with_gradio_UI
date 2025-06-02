#!/usr/bin/env python3
"""
Test script for direct mesh extraction function call
"""
import sys
import os

# Add the app directory to the path
sys.path.insert(0, '/app')

from app import process_extract_mesh

def test_direct_mesh_extraction():
    print("Testing direct mesh extraction function...")
    
    test_model = "/app/examples/bird.glb"
    model_name = "bird_test"
    
    if not os.path.exists(test_model):
        print(f"Test model not found: {test_model}")
        return False
    
    try:
        print(f"Calling process_extract_mesh with model: {test_model}")
        
        # Create a simple progress function
        def progress_fn(value, desc=""):
            print(f"Progress: {value:.2%} - {desc}")
        
        # Call the mesh extraction function
        result = process_extract_mesh(test_model, model_name, progress_fn)
        
        if result:
            extracted_path, logs = result
            print(f"✅ SUCCESS: Mesh extraction completed!")
            print(f"Extracted NPZ path: {extracted_path}")
            print(f"Process logs: {logs}")
            
            # Check if the output file exists
            if extracted_path and os.path.exists(extracted_path):
                file_size = os.path.getsize(extracted_path)
                print(f"Output file size: {file_size} bytes")
                return True
            else:
                print(f"❌ Output file not found: {extracted_path}")
                return False
        else:
            print("❌ FAILED: No result returned from mesh extraction")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: Exception during mesh extraction: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_direct_mesh_extraction()
    print(f"Test result: {'PASS' if success else 'FAIL'}")
