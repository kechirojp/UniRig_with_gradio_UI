#!/usr/bin/env python3
"""
Direct auto-rigging test using local file path
"""

import requests
import json
import time
import os

def test_auto_rigging_direct():
    """Test auto-rigging with direct file path."""
    
    base_url = "http://127.0.0.1:7860"
    test_model = "/app/examples/bird.glb"
    
    if not os.path.exists(test_model):
        print(f"Test model not found: {test_model}")
        return False
    
    print(f"Testing auto-rigging with: {test_model}")
    
    try:
        # Call auto-rigging function directly with file path
        api_data = {
            "data": [test_model, "neutral"],
            "fn_index": 0,  # process_full_auto_rigging should be the first function
            "session_hash": "test_direct"
        }
        
        print("Calling auto-rigging API...")
        response = requests.post(f"{base_url}/api/predict", json=api_data, timeout=300)
        
        if response.status_code == 200:
            result = response.json()
            print("\n=== API Response Status ===")
            print(f"Success: {response.status_code}")
            
            # Extract data from the response
            data = result.get('data', [])
            print(f"Response data length: {len(data)}")
            
            if len(data) >= 2:
                final_model = data[0]
                logs = data[1]
                
                print("\n=== DEBUG LOGS ===")
                print(logs)
                print("=== END LOGS ===")
                
                print(f"\nFinal model path: {final_model}")
                
                if final_model and final_model != "None" and final_model is not None:
                    print("✅ Auto-rigging succeeded!")
                    
                    # Check if the file actually exists
                    if os.path.exists(final_model):
                        file_size = os.path.getsize(final_model)
                        print(f"✅ Final model file exists: {file_size} bytes")
                        return True
                    else:
                        print(f"❌ Final model file doesn't exist: {final_model}")
                        return False
                else:
                    print("❌ Auto-rigging failed - no final model returned")
                    return False
            else:
                print(f"❌ Unexpected response format")
                print(f"Full response: {json.dumps(result, indent=2)}")
                return False
        else:
            print(f"❌ API call failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔍 Testing auto-rigging with direct file path...")
    success = test_auto_rigging_direct()
    
    if success:
        print("\n🎉 Direct test completed successfully!")
    else:
        print("\n❌ Direct test failed!")
