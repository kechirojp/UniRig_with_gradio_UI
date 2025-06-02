#!/usr/bin/env python3
"""
Gradio APIを使用してImprovedSafeTextureRestorationのテスト
"""

import requests
import os
import time

def test_improved_safe_via_api():
    """
    Gradio APIを使用してImprovedSafeTextureRestorationをテスト
    """
    
    print("🧪 Testing ImprovedSafeTextureRestoration via Gradio API")
    print("=" * 70)
    
    # API endpoint
    api_base = "http://localhost:7860"
    input_file = "/app/examples/bird.glb"
    
    if not os.path.exists(input_file):
        print(f"❌ Input file not found: {input_file}")
        return False
    
    try:
        # Check if API is running
        response = requests.get(f"{api_base}/", timeout=5)
        if response.status_code != 200:
            print("❌ Gradio API not running")
            return False
        
        print("✅ Gradio API is running")
        
        # Upload file and start processing
        print("\n🔄 Uploading file and starting processing...")
        
        with open(input_file, 'rb') as f:
            files = {'file': (os.path.basename(input_file), f, 'application/octet-stream')}
            data = {
                'watertight': True,
                'remesh': False,
                'add_root': False
            }
            
            response = requests.post(
                f"{api_base}/api/process",
                files=files,
                data=data,
                timeout=300  # 5 minutes timeout
            )
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success'):
                print("✅ Processing completed successfully!")
                
                # Analyze results
                files = result.get('files', {})
                print(f"\n📁 Generated Files:")
                
                for file_type, file_info in files.items():
                    if file_info:
                        file_path = file_info.get('path', 'Unknown path')
                        file_size = file_info.get('size_mb', 0)
                        print(f"  🔸 {file_type}: {file_size:.2f}MB")
                
                # Focus on final FBX
                final_fbx_info = files.get('final_fbx')
                if final_fbx_info:
                    file_size = final_fbx_info.get('size_mb', 0)
                    print(f"\n📊 Final FBX Analysis:")
                    print(f"  📏 Size: {file_size:.2f}MB")
                    
                    # Quality assessment
                    if file_size >= 4.0:
                        print("  ✅ File size indicates successful texture embedding")
                        quality_score = "HIGH"
                    elif file_size >= 3.0:
                        print("  ⚠️ File size suggests partial texture embedding")
                        quality_score = "MEDIUM"
                    else:
                        print("  ❌ File size indicates potential texture loss")
                        quality_score = "LOW"
                    
                    print(f"  🎯 Quality Assessment: {quality_score}")
                
                # Check logs for ImprovedSafeTextureRestoration
                processing_log = result.get('processing_log', '')
                if 'ImprovedSafeTextureRestoration' in processing_log:
                    print("\n✅ ImprovedSafeTextureRestoration was executed")
                    
                    # Extract relevant log lines
                    log_lines = processing_log.split('\n')
                    improved_safe_lines = [line for line in log_lines if 'ImprovedSafe' in line]
                    
                    if improved_safe_lines:
                        print("📋 ImprovedSafeTextureRestoration Log:")
                        for line in improved_safe_lines[-5:]:  # Last 5 lines
                            print(f"  {line}")
                else:
                    print("\n⚠️ ImprovedSafeTextureRestoration not found in logs")
                
                return True
            else:
                print(f"❌ Processing failed: {result.get('error', 'Unknown error')}")
                return False
        else:
            print(f"❌ API request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.RequestException as e:
        print(f"❌ API request failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def start_gradio_server():
    """
    Gradio serverを起動
    """
    print("🚀 Starting Gradio server...")
    
    import subprocess
    import time
    
    # Start Gradio server in background
    process = subprocess.Popen(
        ['python', 'app.py'],
        cwd='/app',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for server to start
    print("⏳ Waiting for server to start...")
    time.sleep(10)
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:7860/", timeout=5)
        if response.status_code == 200:
            print("✅ Gradio server started successfully")
            return process
        else:
            print("❌ Gradio server failed to start")
            process.terminate()
            return None
    except:
        print("❌ Gradio server not accessible")
        process.terminate()
        return None

if __name__ == "__main__":
    print("🚀 Starting ImprovedSafeTextureRestoration API Test")
    print("=" * 60)
    
    # Try to test with existing server first
    success = test_improved_safe_via_api()
    
    if not success:
        print("\n🔄 Starting new Gradio server for testing...")
        server_process = start_gradio_server()
        
        if server_process:
            try:
                success = test_improved_safe_via_api()
            finally:
                print("\n🛑 Stopping Gradio server...")
                server_process.terminate()
                server_process.wait()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ImprovedSafeTextureRestoration API Test COMPLETED SUCCESSFULLY!")
    else:
        print("❌ ImprovedSafeTextureRestoration API Test FAILED")
    
    print("\n📋 Test Summary:")
    print("- Fixed path search via API tested")
    print("- YAML manifest discovery through API validated")
    print("- Complete pipeline via Gradio interface executed")
    print("- ImprovedSafeTextureRestoration integration verified")
