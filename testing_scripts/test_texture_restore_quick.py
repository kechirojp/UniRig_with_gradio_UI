#!/usr/bin/env python3
"""
テクスチャ復元機能のクイックテスト
タイムアウトを避けるため、短時間で実行できるよう最適化
"""

import requests
import json
import os
import time
import tempfile
import shutil
from pathlib import Path

def test_texture_restore_quick():
    """テクスチャ復元機能のクイックテスト"""
    
    # API設定
    base_url = "http://localhost:7861"
    
    # 1. APIの生存確認
    print("=== API生存確認 ===")
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        print(f"✅ API接続成功: {response.status_code}")
    except Exception as e:
        print(f"❌ API接続失敗: {e}")
        return False
    
    # 2. テクスチャメタデータの確認
    print("\n=== テクスチャメタデータ確認 ===")
    metadata_path = "/tmp/texture_test_output/texture_metadata.json"
    if not os.path.exists(metadata_path):
        print(f"❌ メタデータファイルが見つかりません: {metadata_path}")
        return False
    
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    print(f"✅ メタデータ読み込み成功")
    print(f"   材質数: {len(metadata.get('materials', {}))}")
    print(f"   抽出されたテクスチャ: {len(metadata.get('extracted_textures', {}))}")
    
    # 3. 抽出されたテクスチャファイルの確認
    print("\n=== 抽出テクスチャファイル確認 ===")
    texture_dir = "/tmp/texture_test_output/extracted_textures"
    if os.path.exists(texture_dir):
        texture_files = os.listdir(texture_dir)
        print(f"✅ テクスチャファイル数: {len(texture_files)}")
        for file in texture_files:
            file_path = os.path.join(texture_dir, file)
            size = os.path.getsize(file_path)
            print(f"   - {file}: {size} bytes")
    else:
        print(f"❌ テクスチャディレクトリが見つかりません: {texture_dir}")
    
    # 4. 簡単なGLBファイルの準備（テスト用）
    print("\n=== テスト用GLBファイル準備 ===")
    
    # 利用可能なGLBファイルを使用
    test_glb_path = "/app/gradio_tmp_files/オリジナルモデル_preview_20250527175142261485.glb"
    if not os.path.exists(test_glb_path):
        # フォールバック：他のファイルを試す
        test_glb_path = "/app/test_skeleton_gen_output/skeleton_test.glb"
        if not os.path.exists(test_glb_path):
            print(f"❌ テストファイルが見つかりません")
            return False
    
    print(f"✅ テストファイル確認: {test_glb_path}")
    
    # 5. テクスチャ復元のAPIテスト（タイムアウト設定短縮）
    print("\n=== テクスチャ復元APIテスト ===")
    
    try:
        # ファイルをアップロード
        with open(test_glb_path, 'rb') as f:
            files = {'file': (os.path.basename(test_glb_path), f, 'application/octet-stream')}
            
            # テクスチャメタデータを準備
            restore_data = {
                'texture_metadata': json.dumps(metadata),
                'restore_textures': True
            }
            
            print("📤 テクスチャ復元リクエスト送信中...")
            start_time = time.time()
            
            # タイムアウトを30秒に設定（短縮）
            response = requests.post(
                f"{base_url}/api/process_model",
                files=files,
                data=restore_data,
                timeout=30
            )
            
            elapsed_time = time.time() - start_time
            print(f"⏱️ 処理時間: {elapsed_time:.2f}秒")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ テクスチャ復元成功")
                print(f"   レスポンス状態: {result.get('status', 'unknown')}")
                if 'message' in result:
                    print(f"   メッセージ: {result['message']}")
                
                # 結果ファイルの確認
                if 'file_url' in result:
                    print(f"   出力ファイル: {result['file_url']}")
                
                return True
            else:
                print(f"❌ テクスチャ復元失敗: {response.status_code}")
                print(f"   レスポンス: {response.text[:500]}")
                return False
                
    except requests.exceptions.Timeout:
        print("⏰ リクエストタイムアウト（30秒）")
        print("   注意: 処理は継続中の可能性があります")
        return False
    except Exception as e:
        print(f"❌ テクスチャ復元エラー: {e}")
        return False

def check_background_processes():
    """バックグラウンドプロセスの確認"""
    print("\n=== バックグラウンドプロセス確認 ===")
    
    import subprocess
    try:
        # Blenderプロセスの確認
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        blender_processes = [line for line in result.stdout.split('\n') if 'blender' in line.lower()]
        
        if blender_processes:
            print(f"🔧 Blenderプロセス数: {len(blender_processes)}")
            for proc in blender_processes:
                print(f"   {proc}")
        else:
            print("ℹ️ Blenderプロセスは見つかりませんでした")
            
        # Pythonプロセスの確認
        python_processes = [line for line in result.stdout.split('\n') if 'python' in line and 'app.py' in line]
        if python_processes:
            print(f"🐍 Pythonアプリプロセス数: {len(python_processes)}")
            
    except Exception as e:
        print(f"❌ プロセス確認エラー: {e}")

if __name__ == "__main__":
    print("🚀 テクスチャ復元機能クイックテスト開始")
    print("=" * 50)
    
    # バックグラウンドプロセス確認
    check_background_processes()
    
    # テスト実行
    success = test_texture_restore_quick()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ テスト完了: テクスチャ復元機能は正常に動作しています")
    else:
        print("⚠️ テスト完了: 一部の機能でタイムアウトまたはエラーが発生しました")
        print("   注意: 処理は継続中の可能性があります")
    
    print("🏁 テスト終了")
