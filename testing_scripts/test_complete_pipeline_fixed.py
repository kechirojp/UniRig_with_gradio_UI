#!/usr/bin/env python3
"""
Test the complete pipeline with the fixed merge.py script
"""

import os
import sys
import time
import requests
import json
from pathlib import Path

def test_complete_pipeline_fixed():
    """Test the complete pipeline with the fixed merge script."""
    
    print("🚀 完全パイプラインテスト開始（merge.py修正版）")
    print("=" * 50)
    
    # Check if Gradio server is running
    try:
        response = requests.get("http://localhost:7860/", timeout=5)
        print("✅ Gradioサーバーが実行中です")
    except requests.exceptions.RequestException:
        print("❌ エラー: Gradioサーバーが実行されていません")
        print("まず 'python app.py' を実行してサーバーを起動してください")
        return False
    
    # Test file path
    test_file = "/app/examples/bird.glb"
    if not os.path.exists(test_file):
        print(f"❌ エラー: テストファイルが見つかりません: {test_file}")
        return False
    
    print(f"📁 テストファイル: {test_file}")
    print(f"   ファイルサイズ: {os.path.getsize(test_file):,} bytes")
    
    # Clean up previous test outputs
    output_dirs = [
        "/app/pipeline_work/01_extracted_mesh/bird",
        "/app/pipeline_work/02_skeleton_output/bird", 
        "/app/pipeline_work/03_skinning_output/bird",
        "/app/pipeline_work/04_final_rigged_model/bird"
    ]
    
    for output_dir in output_dirs:
        if os.path.exists(output_dir):
            import shutil
            shutil.rmtree(output_dir)
            print(f"🧹 クリーンアップ: {output_dir}")
    
    # Prepare API request
    url = "http://localhost:7860/api/run_full_auto_rigging"
    
    # Upload the file first
    files = {'data': open(test_file, 'rb')}
    upload_response = requests.post("http://localhost:7860/upload", files=files)
    
    if upload_response.status_code != 200:
        print(f"❌ ファイルアップロードエラー: {upload_response.status_code}")
        return False
    
    uploaded_file_path = upload_response.json()['files'][0]
    print(f"✅ ファイルアップロード成功: {uploaded_file_path}")
    
    # API request payload
    payload = {
        "data": [
            uploaded_file_path,  # uploaded_model_path
            "neutral"           # gender
        ]
    }
    
    print("\n🔄 フル自動リギング処理開始...")
    print(f"リクエストURL: {url}")
    print(f"ペイロード: {json.dumps(payload, indent=2)}")
    
    start_time = time.time()
    
    try:
        response = requests.post(url, json=payload, timeout=300)  # 5分タイムアウト
        elapsed_time = time.time() - start_time
        
        print(f"\n⏱️  処理時間: {elapsed_time:.1f}秒")
        print(f"📊 レスポンスステータス: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            print("\n🎉 フル自動リギング成功!")
            print("=" * 50)
            
            # Check the response data
            data = result.get('data', [])
            if len(data) >= 11:
                final_model_display = data[0]
                logs = data[1] 
                final_model_download = data[2]
                
                print(f"📱 最終モデル表示: {final_model_display}")
                print(f"📥 最終モデルダウンロード: {final_model_download}")
                
                if final_model_download:
                    print("✅ 最終マージ済みFBXファイルが正常に生成されました!")
                    
                    # Check if the output file actually exists
                    expected_output = "/app/pipeline_work/04_final_rigged_model/bird/final_rigged_model.fbx"
                    if os.path.exists(expected_output):
                        file_size = os.path.getsize(expected_output)
                        print(f"✅ 最終ファイル確認: {expected_output}")
                        print(f"   ファイルサイズ: {file_size:,} bytes")
                        return True
                    else:
                        print(f"❌ 期待されるファイルが見つかりません: {expected_output}")
                        return False
                else:
                    print("❌ 最終モデルダウンロードパスが空です")
                    print("\n📋 処理ログ:")
                    if logs:
                        print(logs)
                    return False
            else:
                print(f"❌ 期待されるレスポンスデータが不足しています（取得: {len(data)}, 期待: 11+）")
                return False
        else:
            print(f"❌ APIエラー: {response.status_code}")
            print(f"レスポンス: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ エラー: リクエストタイムアウト (5分)")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ リクエストエラー: {e}")
        return False

def main():
    """Run the complete pipeline test."""
    success = test_complete_pipeline_fixed()
    
    if success:
        print("\n🎊 完全パイプラインテスト成功!")
        print("merge.pyの修正が正常に動作しています。")
    else:
        print("\n💥 完全パイプラインテスト失敗")
        
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
