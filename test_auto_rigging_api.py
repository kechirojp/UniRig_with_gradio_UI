#!/usr/bin/env python3
"""
自動リギング機能のAPIテスト
"""
import requests
import json
import os
import time

# Gradio APIエンドポイント
BASE_URL = "http://127.0.0.1:7860"
API_ENDPOINT = f"{BASE_URL}/gradio_api/gradio_full_auto_rigging"

def test_auto_rigging():
    """自動リギング機能をテスト"""
    
    # テスト用モデルファイル
    test_model_path = "/app/examples/tira.glb"
    
    if not os.path.exists(test_model_path):
        print(f"❌ テストモデルが見つかりません: {test_model_path}")
        return False
    
    print(f"🎯 自動リギングテスト開始")
    print(f"📁 テストモデル: {test_model_path}")
    print(f"🌐 APIエンドポイント: {API_ENDPOINT}")
    
    # まずファイルをアップロード
    files = {
        'files': ('tira.glb', open(test_model_path, 'rb'), 'model/gltf-binary')
    }
    
    try:
        # ファイルアップロード
        print("📤 ファイルをアップロード中...")
        upload_response = requests.post(f"{BASE_URL}/upload", files=files)
        
        if upload_response.status_code != 200:
            print(f"❌ ファイルアップロードエラー: {upload_response.status_code}")
            print(f"   レスポンス: {upload_response.text}")
            return False
        
        upload_data = upload_response.json()
        file_path = upload_data[0]  # アップロードされたファイルのパス
        print(f"✅ ファイルアップロード成功: {file_path}")
        
        # APIリクエストデータ
        request_data = {
            "data": [
                {
                    "path": file_path,
                    "url": f"{BASE_URL}/file={file_path}",
                    "orig_name": "tira.glb",
                    "meta": {"_type": "gradio.FileData"}
                },
                "neutral"  # gender parameter
            ]
        }
        
        # 自動リギングAPI呼び出し
        print("🚀 自動リギング処理開始...")
        response = requests.post(
            API_ENDPOINT,
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            print(f"❌ APIエラー: {response.status_code}")
            print(f"   レスポンス: {response.text}")
            return False
        
        result = response.json()
        print(f"✅ API呼び出し成功")
        print(f"📊 レスポンス: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        return True
        
    except Exception as e:
        print(f"❌ エラーが発生: {str(e)}")
        return False
    
    finally:
        # ファイルハンドルを閉じる
        files['files'][1].close()

if __name__ == "__main__":
    success = test_auto_rigging()
    if success:
        print("\n🎉 自動リギングテスト完了！")
    else:
        print("\n💥 自動リギングテストに失敗")
