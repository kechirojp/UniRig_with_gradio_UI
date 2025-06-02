#!/usr/bin/env python3
"""
Simple auto-rigging test with debug information
"""

import requests
import json
import time
import os

def test_auto_rigging_debug():
    """Test auto-rigging with debug information."""
    
    base_url = "http://127.0.0.1:7860"
    test_model = "/app/examples/bird.glb"
    
    if not os.path.exists(test_model):
        print(f"Test model not found: {test_model}")
        return False
    
    print(f"Testing auto-rigging with: {test_model}")
    
    try:
        # Upload the file first
        with open(test_model, 'rb') as f:
            files = {'files': (os.path.basename(test_model), f, 'application/octet-stream')}
            upload_response = requests.post(f"{base_url}/upload", files=files, timeout=30)
        
        if upload_response.status_code != 200:
            print(f"Upload failed: {upload_response.status_code}")
            print(upload_response.text)
            return False
            
        upload_data = upload_response.json()
        uploaded_file_path = upload_data['files'][0]
        print(f"File uploaded: {uploaded_file_path}")
        
        # Call auto-rigging function
        api_data = {
            "data": [uploaded_file_path, "neutral"],
            "fn_index": 0,  # process_full_auto_rigging
            "session_hash": "test_debug"
        }
        
        print("Calling auto-rigging API...")
        response = requests.post(f"{base_url}/api/predict", json=api_data, timeout=300)
        
        if response.status_code == 200:
            result = response.json()
            print("\n=== API Response ===")
            
            # Extract logs from the response
            data = result.get('data', [])
            if len(data) >= 2:
                logs = data[1]  # Second element should be logs
                print("=== DEBUG LOGS ===")
                print(logs)
                print("=== END LOGS ===")
                
                final_model = data[0]
                print(f"\nFinal model path: {final_model}")
                
                if final_model and final_model != "None":
                    print("✅ Auto-rigging succeeded!")
                    return True
                else:
                    print("❌ Auto-rigging failed - no final model")
                    return False
            else:
                print(f"❌ Unexpected response format: {result}")
                return False
        else:
            print(f"❌ API call failed: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔍 Testing auto-rigging with debug information...")
    success = test_auto_rigging_debug()
    
    if success:
        print("\n🎉 Debug test completed successfully!")
    else:
        print("\n❌ Debug test failed!")
