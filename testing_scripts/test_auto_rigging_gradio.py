#!/usr/bin/env python3
"""
Test the complete auto-rigging pipeline using Gradio API
"""

import requests
import json
import os
import time

def test_auto_rigging():
    """
    自動リギングパイプライン全体のテスト (Gradio API版)
    """
    print("🎯 Testing complete auto-rigging pipeline with Gradio API...")
    
    # テスト用ファイル
    test_file = "./examples/bird.glb"
    if not os.path.exists(test_file):
        print(f"❌ Test file {test_file} not found!")
        return False
        
    print(f"Testing auto-rigging with: {test_file}")
    
    # APIエンドポイント
    base_url = "http://127.0.0.1:7861"
    
    try:
        # ファイルアップロード (Gradio形式)
        with open(test_file, 'rb') as f:
            files = {'files': (os.path.basename(test_file), f, 'application/octet-stream')}
            upload_response = requests.post(f"{base_url}/gradio_api/upload", files=files)
            
        if upload_response.status_code != 200:
            print(f"❌ File upload failed: {upload_response.status_code}")
            print(f"Response: {upload_response.text}")
            return False
            
        file_data = upload_response.json()
        
        # Gradio upload response は通常リストになっている
        if isinstance(file_data, list) and len(file_data) > 0:
            file_path = file_data[0]
        else:
            print("❌ Failed to get uploaded file path")
            print(f"Upload response: {file_data}")
            return False
            
        print(f"✅ File uploaded successfully: {file_path}")
        
        # 自動リギング実行 (Gradio API形式)
        auto_rigging_data = {
            "data": [
                {
                    "path": file_path,
                    "orig_name": "bird.glb",
                    "meta": {"_type": "gradio.FileData"}
                },
                "neutral"  # 性別設定
            ]
        }
        
        print("🚀 Starting auto-rigging process...")
        auto_response = requests.post(
            f"{base_url}/gradio_api/gradio_full_auto_rigging",
            json=auto_rigging_data,
            timeout=900  # 15分タイムアウト
        )
        
        if auto_response.status_code != 200:
            print(f"❌ Auto-rigging failed: {auto_response.status_code}")
            print(f"Response: {auto_response.text}")
            return False
            
        result = auto_response.json()
        print("✅ Auto-rigging completed successfully!")
        
        # 結果の確認
        if result.get('data'):
            output_model = result['data'][0]  # 3Dモデル出力
            log_output = result['data'][1]    # ログ出力
            download_file = result['data'][2] # ダウンロード用ファイル
            
            print(f"📁 Output model: {output_model}")
            print(f"📋 Process log preview:\n{log_output[:500]}...")
            print(f"💾 Download file: {download_file}")
            
            # ファイルの存在確認
            if output_model and 'path' in output_model:
                model_path = output_model['path']
                if os.path.exists(model_path):
                    file_size = os.path.getsize(model_path)
                    print(f"✅ Output model file exists: {model_path} ({file_size} bytes)")
                    return True
                else:
                    print(f"❌ Output model file not found: {model_path}")
                    return False
            else:
                print("❌ No valid output model data")
                return False
                
        else:
            print("❌ No output data received")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_auto_rigging()
    if success:
        print("\n🎉 Auto-rigging pipeline test passed!")
    else:
        print("\n❌ Auto-rigging pipeline test failed!")
