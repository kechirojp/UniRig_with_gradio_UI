#!/usr/bin/env python3
"""
Test script for Gradio mesh extraction functionality
"""
import requests
import json
import os

def test_gradio_mesh_extraction():
    print("Testing Gradio mesh extraction functionality...")
    
    # Test file path
    test_model = "/app/examples/bird.glb"
    
    if not os.path.exists(test_model):
        print(f"Test model not found: {test_model}")
        return False
    
    # First, upload the file to Gradio
    print("Uploading model file to Gradio...")
    try:
        with open(test_model, 'rb') as f:
            files = {'file': f}
            upload_response = requests.post('http://localhost:7861/upload', files=files)
        
        if upload_response.status_code != 200:
            print(f"Failed to upload file: {upload_response.status_code}")
            return False
            
        file_info = upload_response.json()
        uploaded_file_path = file_info[0]  # Get the file path from response
        print(f"File uploaded successfully: {uploaded_file_path}")
        
        # Now test the mesh extraction function
        print("Testing mesh extraction...")
        
        # Call the mesh extraction API
        data = {
            "data": [uploaded_file_path],  # The uploaded file path
            "fn_index": 1  # Assuming this is the mesh extraction function index
        }
        
        extract_response = requests.post('http://localhost:7861/api/predict', json=data)
        
        if extract_response.status_code == 200:
            result = extract_response.json()
            print(f"Mesh extraction response: {result}")
            
            # Check if there's data in the response indicating success
            if result.get('data'):
                print("✅ SUCCESS: Mesh extraction completed successfully!")
                return True
            else:
                print("❌ FAILED: No data returned from mesh extraction")
                return False
        else:
            print(f"❌ FAILED: Mesh extraction API call failed: {extract_response.status_code}")
            print(f"Response: {extract_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: Exception during test: {e}")
        return False

if __name__ == "__main__":
    success = test_gradio_mesh_extraction()
    print(f"Test result: {'PASS' if success else 'FAIL'}")
