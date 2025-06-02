#!/usr/bin/env python3
"""
Test the complete auto-rigging pipeline using Gradio Client
"""

import os
import time
from gradio_client import Client, file # Import file

def test_auto_rigging():
    """
    自動リギングパイプライン全体のテスト (Gradio Client版)
    """
    print("🎯 Testing complete auto-rigging pipeline with Gradio Client...")
    
    # テスト用ファイル
    test_file_relative = "./examples/bird.glb"
    # Convert to absolute path
    test_file_absolute = os.path.abspath(test_file_relative)

    if not os.path.exists(test_file_absolute):
        print(f"❌ Test file {test_file_absolute} not found! (Original: {test_file_relative})")
        return False
        
    print(f"Testing auto-rigging with: {test_file_absolute}") # Log absolute path
    
    try:
        # Gradio Clientで接続
        client = Client("http://127.0.0.1:7861/")
        print("✅ Connected to Gradio app")
        
        # アプリの情報を確認
        try:
            info = client.view_api(print_info=False, return_format="dict")
            print(f"Available endpoints: {list(info.keys())}")
        except Exception as e:
            print(f"Could not get API info: {e}")
        
        # 自動リギング実行
        print("🚀 Starting auto-rigging process...")
        
        result = client.predict(
            original_model_file_obj=file(test_file_absolute), # Use gradio_client.file()
            gender="neutral",
            api_name="/gradio_full_auto_rigging"
        )
        
        print("✅ Auto-rigging completed successfully!")
        print(f"Result type: {type(result)}")
        print(f"Result: {result}")
        
        # 結果の確認
        if isinstance(result, (list, tuple)) and len(result) >= 3:
            output_model = result[0]  # 3Dモデル出力
            log_output = result[1]    # ログ出力
            download_file = result[2] # ダウンロード用ファイル
            
            print(f"📁 Output model: {output_model}")
            print(f"📋 Process log preview: {str(log_output)[:200]}...")
            print(f"💾 Download file: {download_file}")
            
            # ファイルの存在確認
            if output_model and hasattr(output_model, 'name'):
                model_path = output_model.name
                if os.path.exists(model_path):
                    file_size = os.path.getsize(model_path)
                    print(f"✅ Output model file exists: {model_path} ({file_size} bytes)")
                    return True
                else:
                    print(f"❌ Output model file not found: {model_path}")
                    return False
            elif isinstance(output_model, str) and os.path.exists(output_model):
                file_size = os.path.getsize(output_model)
                print(f"✅ Output model file exists: {output_model} ({file_size} bytes)")
                return True
            else:
                print(f"❌ No valid output model data: {output_model}")
                return False
                
        else:
            print(f"❌ Unexpected result format: {result}")
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
