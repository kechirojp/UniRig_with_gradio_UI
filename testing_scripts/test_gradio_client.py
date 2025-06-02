#!/usr/bin/env python3
"""
Gradio Clientを使用した自動リギング機能のテスト
"""
from gradio_client import Client
import os
import time

def test_auto_rigging_with_client():
    """Gradio Clientを使用して自動リギング機能をテスト"""
    
    # テスト用モデルファイル
    test_model_path = "/app/examples/bird.glb"
    
    if not os.path.exists(test_model_path):
        print(f"❌ テストモデルが見つかりません: {test_model_path}")
        return False
    
    print(f"🎯 自動リギングテスト開始")
    print(f"📁 テストモデル: {test_model_path}")
    
    try:
        # Gradio Clientを初期化
        print("🔗 Gradio Clientに接続中...")
        client = Client("http://127.0.0.1:7862")
        
        # 利用可能なAPIエンドポイントを確認
        print("📋 利用可能なAPIエンドポイント:")
        for i, endpoint in enumerate(client.endpoints):
            print(f"  {i}: {endpoint}")
        
        # 自動リギング処理を実行
        print("🚀 自動リギング処理開始...")
        
        # ファイルをGradio形式でアップロード
        from gradio_client import handle_file
        uploaded_file = handle_file(test_model_path)
        
        result = client.predict(
            uploaded_model_path=uploaded_file,    # Gradio形式のファイル
            gender="neutral",                     # 性別パラメータ
            api_name="/run_full_auto_rigging"
        )
        
        print(f"✅ 処理完了")
        print(f"📊 結果: {result}")
        
        # 結果の詳細を表示
        if isinstance(result, (list, tuple)) and len(result) > 0:
            for i, item in enumerate(result):
                print(f"  結果 {i}: {item}")
                if isinstance(item, str) and os.path.exists(item):
                    print(f"    ファイルサイズ: {os.path.getsize(item)} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ エラーが発生: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_auto_rigging_with_client()
    if success:
        print("\n🎉 自動リギングテスト完了！")
    else:
        print("\n💥 自動リギングテストに失敗")
