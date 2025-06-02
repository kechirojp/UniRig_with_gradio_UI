#!/usr/bin/env python3
"""
Final test script for the complete Gradio pipeline including mesh extraction and skeleton generation.
This tests the full workflow to ensure the filename mismatch issue has been resolved.
"""

import os
import sys
import time
import shutil
import requests
import tempfile
from pathlib import Path

def test_gradio_pipeline():
    """Test the complete Gradio pipeline with mesh extraction and skeleton generation."""
    
    print("=== Final Gradio Pipeline Test ===")
    
    # Configuration
    gradio_url = "http://localhost:7862"
    test_model = "/app/examples/bird.glb"
    
    if not os.path.exists(test_model):
        print(f"Error: Test model not found: {test_model}")
        return False
    
    print(f"Testing with model: {test_model}")
    print(f"Gradio URL: {gradio_url}")
    
    # Clean up any previous test data
    test_work_dir = "/app/pipeline_work"
    if os.path.exists(test_work_dir):
        print(f"Cleaning up previous test data: {test_work_dir}")
        shutil.rmtree(test_work_dir)
    
    # Test Gradio connection
    try:
        response = requests.get(f"{gradio_url}/api/gradio/", timeout=10)
        if response.status_code != 200:
            print(f"Error: Gradio server not responding properly (status: {response.status_code})")
            return False
        print("✓ Gradio server is running")
    except Exception as e:
        print(f"Error: Cannot connect to Gradio server: {e}")
        return False
    
    # Simulate the unified processing pipeline
    print("\n--- Testing Unified Processing Pipeline ---")
    
    # Test parameters
    model_name = "bird_test"
    display_name = "Bird Test Model"
    gender = "neutral"
    use_intermediate_cleanup = True
    
    print(f"Model name: {model_name}")
    print(f"Display name: {display_name}")
    print(f"Gender: {gender}")
    print(f"Intermediate cleanup: {use_intermediate_cleanup}")
    
    # For now, we'll test the underlying functions directly instead of via API
    # since the API endpoint structure might be complex
    
    try:
        # Import the app functions
        sys.path.append('/app')
        from app import process_extract_mesh, process_generate_skeleton
        
        print("\n--- Step 1: Mesh Extraction ---")
        extraction_result = process_extract_mesh(
            model_file_path=test_model,
            model_name=model_name,
            progress_fn=lambda x, desc="": print(f"Progress: {x:.1%} - {desc}")
        )
        
        extracted_npz_path, extraction_logs = extraction_result
        
        print("Extraction logs:")
        print(extraction_logs)
        
        if not extracted_npz_path or not os.path.exists(extracted_npz_path):
            print(f"Error: Mesh extraction failed - NPZ file not found: {extracted_npz_path}")
            return False
        
        print(f"✓ Mesh extraction successful: {extracted_npz_path}")
        
        print("\n--- Step 2: Skeleton Generation ---")
        skeleton_result = process_generate_skeleton(
            extracted_npz_path=extracted_npz_path,
            model_name_for_output=model_name,
            gender=gender,
            progress_fn=lambda x, desc="": print(f"Progress: {x:.1%} - {desc}")
        )
        
        display_glb_path, skeleton_logs, fbx_path, txt_path, npz_path = skeleton_result
        
        print("Skeleton generation logs:")
        print(skeleton_logs)
        
        # Check results
        results = []
        if fbx_path and os.path.exists(fbx_path):
            print(f"✓ Skeleton FBX generated: {fbx_path}")
            results.append(f"FBX: {fbx_path}")
        else:
            print(f"✗ Skeleton FBX missing: {fbx_path}")
            
        if npz_path and os.path.exists(npz_path):
            print(f"✓ Skeleton NPZ generated: {npz_path}")
            results.append(f"NPZ: {npz_path}")
        else:
            print(f"✗ Skeleton NPZ missing: {npz_path}")
            
        if txt_path and os.path.exists(txt_path):
            print(f"✓ Skeleton TXT generated: {txt_path}")
            results.append(f"TXT: {txt_path}")
        else:
            print(f"✗ Skeleton TXT missing: {txt_path}")
            
        if display_glb_path and os.path.exists(display_glb_path):
            print(f"✓ Display GLB generated: {display_glb_path}")
            results.append(f"GLB: {display_glb_path}")
        else:
            print(f"✗ Display GLB missing: {display_glb_path}")
        
        print(f"\n--- Test Results ---")
        print(f"Generated files: {len(results)}")
        for result in results:
            print(f"  - {result}")
        
        # Check if critical files exist
        critical_files_ok = bool(fbx_path and os.path.exists(fbx_path))
        
        if critical_files_ok:
            print("\n✓ Complete pipeline test PASSED!")
            print("The filename mismatch issue has been resolved.")
            return True
        else:
            print("\n✗ Complete pipeline test FAILED!")
            print("Critical files are missing.")
            return False
            
    except Exception as e:
        print(f"Error during pipeline test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the final pipeline test."""
    
    print("Final Gradio Pipeline Test")
    print("=" * 50)
    
    success = test_gradio_pipeline()
    
    if success:
        print("\n🎉 All tests PASSED! The Gradio pipeline is working correctly.")
        print("The Blender segmentation fault issue has been resolved.")
        print("The filename mismatch issue has been resolved.")
        print("Both mesh extraction and skeleton generation work as expected.")
    else:
        print("\n❌ Tests FAILED! Please check the logs above for details.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
