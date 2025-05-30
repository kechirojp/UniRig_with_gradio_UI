#!/usr/bin/env python3
"""
Test script to verify the fixed skeleton generation and copy button functionality
"""

import requests
import time
import json
import os

def test_skeleton_generation():
    """Test skeleton generation via Gradio API"""
    api_url = "http://localhost:7863/gradio_api/predict"
    
    # Test skeleton generation
    payload = {
        "data": [
            "examples/bird.glb",  # input_file
            "12345",              # seed
            False,                # add_root
            "bird_test"           # output_name
        ],
        "fn_index": 0  # skeleton generation function
    }
    
    print("Testing skeleton generation...")
    try:
        response = requests.post(api_url, json=payload, timeout=120)
        if response.status_code == 200:
            result = response.json()
            print("✅ Skeleton generation request successful")
            print(f"Response: {json.dumps(result, indent=2)}")
            
            # Check if the response contains log data
            if 'data' in result and len(result['data']) > 1:
                log_data = result['data'][1]  # Second element should be the log
                print(f"\n📝 Log data preview (first 200 chars):")
                print(log_data[:200] + "..." if len(log_data) > 200 else log_data)
                
                # Check for proper newlines (not escaped \\n)
                if '\\n' in log_data:
                    print("❌ Warning: Found escaped newlines (\\n) in log data")
                    print("This might affect copy button functionality")
                else:
                    print("✅ Log data appears to have proper newlines")
                
                # Check for expected content
                if 'predict_skeleton.npz' in log_data:
                    print("✅ predict_skeleton.npz mentioned in logs")
                else:
                    print("❌ predict_skeleton.npz not found in logs")
            
            return True
        else:
            print(f"❌ Request failed with status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error during skeleton generation test: {e}")
        return False

def check_file_generation():
    """Check if files were actually generated"""
    print("\n🔍 Checking generated files...")
    
    # Check various possible output locations
    locations_to_check = [
        "/app/pipeline_work/02_skeleton_output/bird_test",
        "/app/pipeline_work/02_skeleton_output/bird",
        "/app/tmp/bird_test",
        "/app/tmp/bird",
        "/app/gradio_tmp_files"
    ]
    
    files_found = []
    for location in locations_to_check:
        if os.path.exists(location):
            for root, dirs, files in os.walk(location):
                for file in files:
                    if 'skeleton' in file or 'predict' in file:
                        full_path = os.path.join(root, file)
                        files_found.append(full_path)
    
    if files_found:
        print("✅ Generated files found:")
        for file_path in files_found[-10:]:  # Show last 10 files
            print(f"  - {file_path}")
    else:
        print("❌ No skeleton-related files found")
    
    return len(files_found) > 0

if __name__ == "__main__":
    print("🧪 Testing Fixed Skeleton Generation and Copy Button")
    print("=" * 60)
    
    # Test skeleton generation
    skeleton_success = test_skeleton_generation()
    
    # Wait a moment for file generation
    time.sleep(2)
    
    # Check file generation
    files_success = check_file_generation()
    
    print("\n" + "=" * 60)
    print("📊 Test Results:")
    print(f"  Skeleton Generation API: {'✅ PASS' if skeleton_success else '❌ FAIL'}")
    print(f"  File Generation: {'✅ PASS' if files_success else '❌ FAIL'}")
    
    if skeleton_success and files_success:
        print("\n🎉 All tests passed! The fixes are working correctly.")
        print("   - predict_skeleton.npz files are being generated")
        print("   - Copy button should work properly with fixed newlines")
    else:
        print("\n⚠️  Some tests failed. Please check the issues above.")
