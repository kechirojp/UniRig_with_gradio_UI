#!/usr/bin/env python3
"""
テクスチャ復元機能の最終テスト
正しいGradio APIエンドポイントを使用してテクスチャ適用をテスト
"""

import requests
import json
import os
import time
import shutil
from pathlib import Path

def test_texture_restoration():
    """テクスチャ復元機能をテスト"""
    
    # 設定
    api_base_url = "http://localhost:7861"
    
    # テストファイルパス
    test_files_dir = "/app/examples"
    texture_output_dir = "/tmp/texture_test_output"
    
    print("=== テクスチャ復元機能テスト開始 ===")
    
    # 1. 利用可能なテストファイルを確認
    print("\n1. 利用可能なテストファイルを確認中...")
    if not os.path.exists(test_files_dir):
        print(f"エラー: テストファイルディレクトリが見つかりません: {test_files_dir}")
        return False
    
    # GLBファイルを探す
    glb_files = [f for f in os.listdir(test_files_dir) if f.endswith('.glb')]
    if not glb_files:
        print("エラー: GLBファイルが見つかりません")
        return False
    
    test_glb_file = os.path.join(test_files_dir, glb_files[0])
    print(f"テストファイル: {test_glb_file}")
    
    # 2. 既存のテクスチャメタデータが存在するか確認
    print("\n2. 既存のテクスチャメタデータを確認中...")
    metadata_path = os.path.join(texture_output_dir, "texture_metadata.json")
    
    if not os.path.exists(metadata_path):
        print("テクスチャメタデータが見つかりません。まず抽出を実行します...")
        
        # テクスチャ抽出を実行
        success = extract_textures_direct(test_glb_file, texture_output_dir)
        if not success:
            print("テクスチャ抽出に失敗しました")
            return False
    
    # 3. メタデータを読み込み
    print("\n3. テクスチャメタデータを読み込み中...")
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            texture_metadata = json.load(f)
        
        print(f"メタデータ読み込み成功:")
        print(f"  - テクスチャ数: {len(texture_metadata.get('textures', {}))}")
        print(f"  - マテリアル数: {len(texture_metadata.get('materials', {}))}")
        print(f"  - メッシュ-マテリアル対応数: {len(texture_metadata.get('mesh_materials', {}))}")
        
    except Exception as e:
        print(f"メタデータ読み込みエラー: {e}")
        return False
    
    # 4. リギング済みFBXファイルを作成（テスト用のダミー）
    print("\n4. テスト用リギング済みFBXファイルを準備中...")
    rigged_fbx_path = os.path.join(texture_output_dir, "test_rigged_model.fbx")
    
    # 元のGLBファイルをFBXとしてコピー（実際のリギング処理の代わり）
    try:
        shutil.copy2(test_glb_file, rigged_fbx_path)
        print(f"テスト用FBXファイル作成: {rigged_fbx_path}")
    except Exception as e:
        print(f"テスト用FBXファイル作成失敗: {e}")
        return False
    
    # 5. Gradio APIを使用してテクスチャ適用をテスト
    print("\n5. Gradio APIでテクスチャ適用をテスト中...")
    
    try:
        # run_merge_model_with_textures_step APIを使用
        api_endpoint = f"{api_base_url}/gradio_api/run/run_merge_model_with_textures_step"
        
        # APIに送信するデータを準備
        files = {}
        data = {
            "data": [
                rigged_fbx_path,  # リギング済みFBXファイル
                texture_output_dir,  # テクスチャデータディレクトリ  
                os.path.join(texture_output_dir, "final_textured_model.fbx")  # 出力ファイルパス
            ]
        }
        
        print(f"API呼び出し: {api_endpoint}")
        print(f"送信データ: {data}")
        
        # APIリクエストを送信
        response = requests.post(
            api_endpoint,
            json=data,
            timeout=300  # 5分のタイムアウト
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"API応答成功: {result}")
            
            # 結果を解析
            if result.get("data"):
                output_data = result["data"]
                print(f"テクスチャ適用結果:")
                for i, item in enumerate(output_data):
                    print(f"  結果{i}: {item}")
                
                # 出力ファイルの存在確認
                output_file = os.path.join(texture_output_dir, "final_textured_model.fbx")
                if os.path.exists(output_file):
                    file_size = os.path.getsize(output_file)
                    print(f"✅ 出力ファイル生成成功: {output_file} ({file_size} bytes)")
                    return True
                else:
                    print("⚠️ 出力ファイルが生成されませんでした")
                    return False
            else:
                print("⚠️ API応答にデータが含まれていません")
                return False
        else:
            print(f"❌ API呼び出し失敗: {response.status_code}")
            print(f"エラー内容: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ API呼び出しがタイムアウトしました")
        return False
    except Exception as e:
        print(f"❌ API呼び出しエラー: {e}")
        return False

def extract_textures_direct(glb_file: str, output_dir: str) -> bool:
    """直接テクスチャ抽出を実行"""
    print(f"テクスチャ抽出を実行: {glb_file} -> {output_dir}")
    
    try:
        # extract_texture_subprocess.pyを使用
        import subprocess
        
        cmd = [
            "python3", "/app/extract_texture_subprocess.py",
            glb_file, output_dir
        ]
        
        print(f"サブプロセス実行: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120  # 2分のタイムアウト
        )
        
        if result.returncode == 0:
            print("✅ テクスチャ抽出成功")
            print(f"出力: {result.stdout}")
            return True
        else:
            print(f"❌ テクスチャ抽出失敗: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ テクスチャ抽出がタイムアウトしました")
        return False
    except Exception as e:
        print(f"❌ テクスチャ抽出エラー: {e}")
        return False

def check_api_health():
    """API健全性チェック"""
    try:
        response = requests.get("http://localhost:7861", timeout=10)
        if response.status_code == 200:
            print("✅ Gradioアプリケーションは正常に動作しています")
            return True
        else:
            print(f"⚠️ Gradioアプリケーションの応答が異常: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Gradioアプリケーションにアクセスできません: {e}")
        return False

if __name__ == "__main__":
    print("テクスチャ復元機能テスト開始")
    
    # API健全性チェック
    if not check_api_health():
        print("Gradioアプリケーションが利用できません。テストを中止します。")
        exit(1)
    
    # テクスチャ復元テスト実行
    success = test_texture_restoration()
    
    if success:
        print("\n🎉 テクスチャ復元機能テスト成功！")
        print("テクスチャ保存・復元システムは正常に動作しています。")
    else:
        print("\n❌ テクスチャ復元機能テストに問題が発生しました。")
        print("ログを確認して問題を調査してください。")
    
    exit(0 if success else 1)
