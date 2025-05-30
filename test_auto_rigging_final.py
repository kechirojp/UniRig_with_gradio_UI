#!/usr/bin/env python3
"""
Final test for the complete auto-rigging pipeline
"""

import requests
import json
import time
import os
from pathlib import Path

def test_auto_rigging():
    """Test the complete auto-rigging functionality via API calls."""
    
    base_url = "http://127.0.0.1:7861"
    
    # Find a test model
    test_model_path = "./examples/bird.glb"
    if not os.path.exists(test_model_path):
        print(f"Test model not found: {test_model_path}")
        # Try to find any GLB file
        glb_files = list(Path(".").rglob("*.glb"))
        if glb_files:
            test_model_path = str(glb_files[0])
            print(f"Using alternative test model: {test_model_path}")
        else:
            print("No GLB files found for testing")
            return False
    
    print(f"Testing auto-rigging with: {test_model_path}")
    
    try:
        # Upload the model file
        with open(test_model_path, 'rb') as f:
            files = {'files': (os.path.basename(test_model_path), f, 'application/octet-stream')}
            upload_response = requests.post(f"{base_url}/upload", files=files)
            
        if upload_response.status_code == 200:
            upload_data = upload_response.json()
            print(f"File uploaded successfully: {upload_data}")
            
            # Get the uploaded file path
            uploaded_files = upload_data.get('files', [])
            if not uploaded_files:
                print("No files in upload response")
                return False
                
            uploaded_file_path = uploaded_files[0]
            print(f"Uploaded file path: {uploaded_file_path}")
            
            # Call the auto-rigging function
            print("Starting auto-rigging process...")
            
            # Prepare the API call data
            api_data = {
                "data": [
                    uploaded_file_path,  # original_model_path
                    None,                # motion_sequence_path
                    None,                # person_measurements_path
                    "unisex"            # gender
                ],
                "fn_index": 0,  # This should correspond to process_full_auto_rigging
                "session_hash": "test_session"
            }
            
            # Make the API call
            response = requests.post(f"{base_url}/api/predict", json=api_data)
            
            if response.status_code == 200:
                result = response.json()
                print(f"Auto-rigging completed successfully!")
                print(f"Response: {json.dumps(result, indent=2)}")
                
                # Check the outputs
                data = result.get('data', [])
                if len(data) >= 4:
                    final_rigged_model = data[0]
                    progress_logs = data[1]
                    preview_model = data[2]
                    download_files = data[3]
                    
                    print(f"\nResults:")
                    print(f"Final rigged model: {final_rigged_model}")
                    print(f"Preview model: {preview_model}")
                    print(f"Download files: {download_files}")
                    print(f"\nProgress logs:")
                    print(progress_logs)
                    
                    # Verify files exist
                    if final_rigged_model and os.path.exists(final_rigged_model):
                        print(f"✅ Final rigged model exists: {final_rigged_model}")
                        file_size = os.path.getsize(final_rigged_model)
                        print(f"   File size: {file_size} bytes")
                        return True
                    else:
                        print(f"❌ Final rigged model not found: {final_rigged_model}")
                        return False
                else:
                    print(f"❌ Unexpected response format: {result}")
                    return False
            else:
                print(f"❌ API call failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        else:
            print(f"❌ File upload failed: {upload_response.status_code}")
            print(f"Response: {upload_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🎯 Testing complete auto-rigging pipeline...")
    success = test_auto_rigging()
    
    if success:
        print("\n🎉 Auto-rigging test completed successfully!")
    else:
        print("\n❌ Auto-rigging test failed!")
