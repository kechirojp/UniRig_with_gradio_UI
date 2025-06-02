#!/usr/bin/env python3
"""
テクスチャ保存・復元システムの修正版テスト
FBXインポート時のコンテキストエラー修正を確認
"""

import os
import sys
import requests
import time
import json
import logging

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Gradio APIのベースURL
API_BASE = "http://localhost:7861"

def test_texture_preservation_pipeline():
    """テクスチャ保存・復元パイプラインの完全テスト"""
    
    # テスト用FBXファイルのパス
    test_fbx_path = "/app/pipeline_work/test_models/character.fbx"
    
    # テスト用FBXファイルが存在しない場合は作成
    if not os.path.exists(test_fbx_path):
        logger.info("テスト用FBXファイルが見つかりません。簡単なテストファイルを作成します...")
        create_test_fbx(test_fbx_path)
    
    # ステップ1: メッシュ抽出とテクスチャ保存
    logger.info("=== ステップ1: メッシュ抽出とテクスチャ保存 ===")
    
    try:
        with open(test_fbx_path, 'rb') as f:
            files = {'file': ('character.fbx', f, 'application/octet-stream')}
            
            response = requests.post(
                f"{API_BASE}/api/extract_mesh",
                files=files,
                timeout=120
            )
        
        if response.status_code != 200:
            logger.error(f"メッシュ抽出API失敗: {response.status_code}")
            logger.error(f"レスポンス: {response.text}")
            return False
        
        result = response.json()
        if not result.get('success'):
            logger.error(f"メッシュ抽出失敗: {result.get('error')}")
            return False
        
        # 抽出されたファイルの確認
        extracted_mesh_path = result.get('extracted_mesh_path')
        texture_data_path = result.get('texture_data_path')
        
        logger.info(f"メッシュ抽出成功: {extracted_mesh_path}")
        logger.info(f"テクスチャデータ保存: {texture_data_path}")
        
        # ファイルの存在確認
        if extracted_mesh_path and os.path.exists(extracted_mesh_path):
            logger.info(f"✓ 抽出メッシュファイル確認: {os.path.getsize(extracted_mesh_path)} bytes")
        else:
            logger.warning("✗ 抽出メッシュファイルが見つかりません")
        
        if texture_data_path and os.path.exists(texture_data_path):
            logger.info(f"✓ テクスチャデータディレクトリ確認: {texture_data_path}")
            
            # テクスチャメタデータファイルの確認
            metadata_file = os.path.join(texture_data_path, "texture_metadata.json")
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                logger.info(f"✓ テクスチャメタデータ: {len(metadata.get('textures', {}))} テクスチャ")
                logger.info(f"✓ マテリアル数: {len(metadata.get('materials', {}))}")
            else:
                logger.warning("✗ テクスチャメタデータファイルが見つかりません")
        else:
            logger.warning("✗ テクスチャデータディレクトリが見つかりません")
        
    except Exception as e:
        logger.error(f"メッシュ抽出中にエラー: {e}")
        return False
    
    # ステップ2: 自動リギング
    logger.info("\n=== ステップ2: 自動リギング ===")
    
    try:
        with open(extracted_mesh_path, 'rb') as f:
            files = {'file': ('extracted_mesh.obj', f, 'application/octet-stream')}
            
            response = requests.post(
                f"{API_BASE}/api/auto_rigging",
                files=files,
                timeout=300
            )
        
        if response.status_code != 200:
            logger.error(f"自動リギングAPI失敗: {response.status_code}")
            logger.error(f"レスポンス: {response.text}")
            return False
        
        result = response.json()
        if not result.get('success'):
            logger.error(f"自動リギング失敗: {result.get('error')}")
            return False
        
        rigged_fbx_path = result.get('rigged_fbx_path')
        logger.info(f"自動リギング成功: {rigged_fbx_path}")
        
        if rigged_fbx_path and os.path.exists(rigged_fbx_path):
            logger.info(f"✓ リギング済みFBXファイル確認: {os.path.getsize(rigged_fbx_path)} bytes")
        else:
            logger.warning("✗ リギング済みFBXファイルが見つかりません")
            return False
        
    except Exception as e:
        logger.error(f"自動リギング中にエラー: {e}")
        return False
    
    # ステップ3: テクスチャ適用（修正版テスト）
    logger.info("\n=== ステップ3: テクスチャ適用（修正版） ===")
    
    try:
        with open(rigged_fbx_path, 'rb') as f:
            files = {'rigged_file': ('rigged_character.fbx', f, 'application/octet-stream')}
            data = {'texture_data_path': texture_data_path}
            
            response = requests.post(
                f"{API_BASE}/api/apply_textures",
                files=files,
                data=data,
                timeout=120
            )
        
        if response.status_code != 200:
            logger.error(f"テクスチャ適用API失敗: {response.status_code}")
            logger.error(f"レスポンス: {response.text}")
            return False
        
        result = response.json()
        if not result.get('success'):
            logger.error(f"テクスチャ適用失敗: {result.get('error')}")
            
            # エラーの詳細を確認
            error_msg = result.get('error', '')
            if 'Context missing active object' in error_msg:
                logger.error("❌ FBXインポート時のコンテキストエラーが発生しました")
                logger.error("修正が必要です")
                return False
            elif 'Segmentation fault' in error_msg:
                logger.error("❌ セグメンテーションフォルトが発生しました")
                return False
            else:
                logger.error(f"❌ その他のエラー: {error_msg}")
                return False
        
        final_fbx_path = result.get('final_fbx_path')
        logger.info(f"✅ テクスチャ適用成功: {final_fbx_path}")
        
        if final_fbx_path and os.path.exists(final_fbx_path):
            file_size = os.path.getsize(final_fbx_path)
            logger.info(f"✓ 最終FBXファイル確認: {file_size} bytes")
            
            if file_size > 1024:  # 1KB以上なら成功とみなす
                logger.info("🎉 テクスチャ保存・復元パイプライン完全成功！")
                return True
            else:
                logger.warning("⚠️ 出力ファイルサイズが小さすぎます")
                return False
        else:
            logger.warning("✗ 最終FBXファイルが見つかりません")
            return False
        
    except Exception as e:
        logger.error(f"テクスチャ適用中にエラー: {e}")
        return False

def create_test_fbx(output_path):
    """簡単なテスト用FBXファイルを作成"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Blenderスクリプトで簡単なキューブを作成
    blender_script = f"""
import bpy
import bmesh

# シーンをクリア
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# キューブを作成
bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 1))
cube = bpy.context.active_object
cube.name = "TestCube"

# 簡単なマテリアルを作成
material = bpy.data.materials.new(name="TestMaterial")
material.use_nodes = True
cube.data.materials.append(material)

# FBXとして保存
bpy.ops.export_scene.fbx(
    filepath="{output_path}",
    use_selection=False,
    global_scale=1.0
)
"""
    
    # Blenderでスクリプトを実行
    import subprocess
    script_path = "/tmp/create_test_fbx.py"
    with open(script_path, 'w') as f:
        f.write(blender_script)
    
    try:
        subprocess.run(['blender', '--background', '--python', script_path], 
                      check=True, capture_output=True)
        logger.info(f"テスト用FBXファイルを作成しました: {output_path}")
    except subprocess.CalledProcessError as e:
        logger.warning(f"テスト用FBX作成に失敗: {e}")
        # フォールバック: 空のファイルを作成
        with open(output_path, 'wb') as f:
            f.write(b"dummy_fbx_content")

def main():
    """メイン実行関数"""
    logger.info("=== テクスチャ保存・復元システム修正版テスト開始 ===")
    
    # APIサーバーの応答確認
    try:
        response = requests.get(f"{API_BASE}/", timeout=10)
        if response.status_code == 200:
            logger.info("✓ Gradio APIサーバーに接続成功")
        else:
            logger.error(f"✗ APIサーバー応答エラー: {response.status_code}")
            return
    except requests.exceptions.RequestException as e:
        logger.error(f"✗ APIサーバーに接続できません: {e}")
        logger.info("アプリケーションが起動していることを確認してください")
        return
    
    # パイプラインテスト実行
    success = test_texture_preservation_pipeline()
    
    if success:
        logger.info("\n🎉 全てのテストが正常に完了しました！")
        logger.info("FBXインポート時のコンテキストエラーは修正されました。")
    else:
        logger.error("\n❌ テストが失敗しました。")
        logger.error("さらなる修正が必要です。")

if __name__ == "__main__":
    main()
