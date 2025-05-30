#!/usr/bin/env python3
"""
Test script to verify the skeleton generation fix for predict_skeleton.npz
"""

import requests
import json
import os
import time
from pathlib import Path

def test_skeleton_generation():
    """Test skeleton generation via Gradio API"""
    
    # Gradio API endpoint
    api_url = "http://localhost:7863"
    
    # Test with bird model
    test_file = "/app/examples/bird.glb"
    
    print("🧪 Testing skeleton generation fix...")
    print(f"📁 Input file: {test_file}")
    
    # Check if test file exists
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return False
        
    # Upload file and generate skeleton
    try:
        with open(test_file, 'rb') as f:
            files = {'file': f}
            
            # First, upload the file
            print("📤 Uploading file...")
            upload_response = requests.post(f"{api_url}/upload", files=files)
            
            if upload_response.status_code == 200:
                print("✅ File uploaded successfully")
                
                # Get the uploaded file path
                upload_data = upload_response.json()
                print(f"📍 Upload response: {upload_data}")
                
                # Trigger skeleton generation via API
                print("🦴 Triggering skeleton generation...")
                
                # Use direct API call to the gradio generate skeleton function
                generate_data = {
                    "data": [test_file]  # Pass the original file path
                }
                
                generate_response = requests.post(
                    f"{api_url}/api/predict", 
                    json=generate_data
                )
                
                if generate_response.status_code == 200:
                    print("✅ Skeleton generation request sent successfully")
                    result = generate_response.json()
                    print(f"📊 Generation result: {result}")
                    
                    # Wait a bit for processing
                    time.sleep(5)
                    
                    # Check for output files
                    output_dir = "/app/pipeline_work/02_skeleton_output/bird"
                    print(f"🔍 Checking output directory: {output_dir}")
                    
                    if os.path.exists(output_dir):
                        files = os.listdir(output_dir)
                        print(f"📁 Files in output directory: {files}")
                        
                        # Check for predict_skeleton.npz
                        npz_file = os.path.join(output_dir, "predict_skeleton.npz")
                        if os.path.exists(npz_file):
                            print("✅ predict_skeleton.npz file found!")
                            print(f"📏 File size: {os.path.getsize(npz_file)} bytes")
                            return True
                        else:
                            print("❌ predict_skeleton.npz file not found")
                            print("🔍 Available files:")
                            for file in files:
                                file_path = os.path.join(output_dir, file)
                                size = os.path.getsize(file_path)
                                print(f"   - {file} ({size} bytes)")
                            return False
                    else:
                        print(f"❌ Output directory not found: {output_dir}")
                        return False
                        
                else:
                    print(f"❌ Skeleton generation failed: {generate_response.status_code}")
                    print(f"📜 Response: {generate_response.text}")
                    return False
                    
            else:
                print(f"❌ File upload failed: {upload_response.status_code}")
                print(f"📜 Response: {upload_response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        return False

def test_direct_pipeline():
    """Test the skeleton generation pipeline directly"""
    
    print("\n🧪 Testing direct pipeline call...")
    
    # Test input
    input_file = "/app/examples/bird.glb"
    output_dir = "/app/pipeline_work/02_skeleton_output/bird"
    
    # Clear previous output
    if os.path.exists(output_dir):
        import shutil
        shutil.rmtree(output_dir)
        
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Import and call the Gradio function directly
        import sys
        sys.path.append('/app')
        from app import gradio_generate_skeleton
        
        # Prepare test parameters
        raw_data_npz_path = "/app/pipeline_work/01_mesh_extraction_output/bird/raw_data.npz"
        model_name = "bird" 
        gender = "unspecified"
        
        print("📞 Calling gradio_generate_skeleton function...")
        print(f"   - raw_data_npz_path: {raw_data_npz_path}")
        print(f"   - model_name: {model_name}")
        print(f"   - gender: {gender}")
        
        # Check if the input NPZ file exists
        if not os.path.exists(raw_data_npz_path):
            print(f"❌ Required input NPZ file not found: {raw_data_npz_path}")
            print("🔧 Need to generate it first by running mesh extraction...")
            
            # Try to generate it by calling the gradio mesh extraction function
            from app import gradio_extract_mesh
            print("🔧 Generating required NPZ file...")
            extract_result = gradio_extract_mesh(input_file)
            print(f"📊 Extract result: {extract_result}")
            
            # Check again
            if not os.path.exists(raw_data_npz_path):
                print(f"❌ Still cannot find required NPZ file: {raw_data_npz_path}")
                return False
        
        result = gradio_generate_skeleton(raw_data_npz_path, model_name, gender)
        
        print(f"📊 Function result: {result}")
        
        # Check output files
        print(f"🔍 Checking output directory: {output_dir}")
        if os.path.exists(output_dir):
            files = os.listdir(output_dir)
            print(f"📁 Files in output directory: {files}")
            
            # Check for predict_skeleton.npz
            npz_file = os.path.join(output_dir, "predict_skeleton.npz")
            if os.path.exists(npz_file):
                print("✅ predict_skeleton.npz file found!")
                print(f"📏 File size: {os.path.getsize(npz_file)} bytes")
                return True
            else:
                print("❌ predict_skeleton.npz file not found")
                return False
        else:
            print(f"❌ Output directory not found: {output_dir}")
            return False
            
    except Exception as e:
        print(f"❌ Error during direct pipeline test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 SKELETON GENERATION FIX TEST")
    print("=" * 60)
    
    # Test direct pipeline first
    success = test_direct_pipeline()
    
    if success:
        print("\n🎉 SUCCESS! predict_skeleton.npz file is now being generated correctly!")
    else:
        print("\n❌ FAILED! predict_skeleton.npz file is still not being generated.")
        
    print("\n" + "=" * 60)
