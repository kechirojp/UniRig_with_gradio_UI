#!/usr/bin/env python3
"""
修正されたテクスチャ保存システムのテスト
FBXインポート時のコンテキストエラーが解決されたかを確認
"""

import os
import sys
import requests
import json
import time
from pathlib import Path

def test_texture_preservation():
    """テクスチャ保存・復元システムのテスト"""
    print("🔄 修正されたテクスチャ保存システムのテストを開始...")
    
    # テストファイルのパス
    test_model_path = "/tmp/gradio/8aba700572958052db58d410c2a2cf5076be360d5074b8a44a0e9fdf9f92dfba/bird.glb"
    
    # テストファイルが存在するか確認
    if not os.path.exists(test_model_path):
        print(f"❌ テストファイルが見つかりません: {test_model_path}")
        
        # 代替のテストファイルを探す
        gradio_tmp_dirs = [d for d in os.listdir("/tmp/gradio") if os.path.isdir(f"/tmp/gradio/{d}")]
        for tmp_dir in gradio_tmp_dirs:
            potential_path = f"/tmp/gradio/{tmp_dir}/bird.glb"
            if os.path.exists(potential_path):
                test_model_path = potential_path
                print(f"✅ 代替テストファイルを発見: {test_model_path}")
                break
        else:
            print("❌ 利用可能なテストファイルが見つかりませんでした")
            return False
    
    try:
        # Gradio APIクライアントを使用してテスト
        print("📡 Gradio APIに接続中...")
        
        api_url = "http://localhost:7861"
        
        # API呼び出し用のファイルアップロード
        with open(test_model_path, 'rb') as f:
            files = {'file': f}
            
            # リクエストデータ
            data = {
                'data': json.dumps([test_model_path])  # ファイルパスを直接指定
            }
            
            print(f"🚀 フルパイプラインを実行中...")
            print(f"   入力ファイル: {test_model_path}")
            
            # 直接APIエンドポイントを呼び出し
            response = requests.post(
                f"{api_url}/api/run_full_auto_rigging",
                data=data,
                timeout=300  # 5分のタイムアウト
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ API呼び出し成功")
                print(f"   レスポンス: {result}")
                
                # テクスチャ関連のログを確認
                if 'output' in result:
                    output_data = result['output']
                    if any('texture' in str(item).lower() for item in output_data if item):
                        print("✅ テクスチャ処理が実行されました")
                        return True
                    else:
                        print("⚠️  テクスチャ処理の実行が確認できませんでした")
                        return False
                else:
                    print("⚠️  出力データの形式が期待と異なります")
                    return False
                    
            else:
                print(f"❌ API呼び出し失敗: {response.status_code}")
                print(f"   エラー内容: {response.text}")
                return False
                
    except requests.exceptions.Timeout:
        print("❌ API呼び出しがタイムアウトしました")
        return False
    except Exception as e:
        print(f"❌ テスト実行中にエラー: {e}")
        return False

def check_app_logs():
    """アプリケーションのログを確認"""
    print("\n📋 アプリケーションログの確認...")
    
    try:
        # 最新のログファイルを探す
        log_files = [
            "/app/output_log.txt",
            "/app/fbx_test_output.log"
        ]
        
        for log_file in log_files:
            if os.path.exists(log_file):
                print(f"\n📄 {log_file} の最新ログ:")
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    # 最新の20行を表示
                    for line in lines[-20:]:
                        print(f"   {line.strip()}")
                break
        else:
            print("   ログファイルが見つかりませんでした")
            
    except Exception as e:
        print(f"   ログ確認中にエラー: {e}")

def main():
    """メイン関数"""
    print("=" * 60)
    print("🧪 修正されたテクスチャ保存システムのテスト")
    print("=" * 60)
    
    # アプリケーションが起動しているか確認
    try:
        response = requests.get("http://localhost:7860", timeout=5)
        if response.status_code == 200:
            print("✅ アプリケーションが正常に起動しています")
        else:
            print("❌ アプリケーションの応答が正常ではありません")
            return
    except:
        print("❌ アプリケーションに接続できません")
        return
    
    # テスト実行
    success = test_texture_preservation()
    
    # ログ確認
    check_app_logs()
    
    # 結果報告
    print("\n" + "=" * 60)
    if success:
        print("🎉 テクスチャ保存システムのテストが成功しました！")
        print("✅ FBXインポート時のコンテキストエラーが解決されました")
    else:
        print("❌ テクスチャ保存システムのテストに失敗しました")
        print("🔧 さらなる修正が必要です")
    print("=" * 60)

if __name__ == "__main__":
    main()
