#!/usr/bin/env python3
"""
Gradio APIの正しい呼び出し方法でテクスチャ保存・復元システムをテスト
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

def test_gradio_api_direct():
    """Gradio APIを直接呼び出してテスト"""
    
    # テスト用FBXファイルのパス
    test_fbx_path = "/app/pipeline_work/test_models/character.fbx"
    
    # テスト用FBXファイルが存在しない場合は作成
    if not os.path.exists(test_fbx_path):
        logger.info("テスト用FBXファイルが見つかりません。簡単なテストファイルを作成します...")
        create_test_fbx(test_fbx_path)
    
    logger.info("=== Gradio API直接呼び出しテスト ===")
    
    try:
        # Gradio APIの正しい呼び出し方法
        with open(test_fbx_path, 'rb') as f:
            files = {
                'data': ('character.fbx', f, 'application/octet-stream')
            }
            
            # APIエンドポイントのパラメータを正しく設定
            data = {
                'fn_index': 0,  # フルパイプライン関数のインデックス
                'data': [
                    {
                        'path': test_fbx_path,
                        'url': None,
                        'size': None,
                        'orig_name': 'character.fbx',
                        'mime_type': 'application/octet-stream',
                        'is_stream': False,
                        'meta': {'_type': 'gradio.FileData'}
                    },
                    'female'  # gender parameter
                ]
            }
            
            logger.info("フルパイプライン実行中...")
            response = requests.post(
                f"{API_BASE}/gradio_api/run/run_full_auto_rigging",
                json=data,
                timeout=600
            )
        
        if response.status_code != 200:
            logger.error(f"API失敗: {response.status_code}")
            logger.error(f"レスポンス: {response.text}")
            return False
        
        result = response.json()
        logger.info("API呼び出し完了！結果を確認中...")
        
        # 結果の分析
        if 'data' not in result:
            logger.error("予期しない応答形式です")
            logger.error(f"Response: {result}")
            return False
        
        data = result['data']
        if not data or len(data) < 2:
            logger.error("応答データが不十分です")
            return False
        
        # パイプラインログを確認
        pipeline_log = data[1] if len(data) > 1 else ""
        
        logger.info("=== パイプライン実行結果 ===")
        
        if pipeline_log:
            logger.info("📋 パイプラインログ:")
            log_lines = pipeline_log.split('\n')
            for line in log_lines[-30:]:  # 最後の30行を表示
                if line.strip():
                    logger.info(f"   {line}")
            
            # テクスチャ関連のキーワードをチェック
            texture_success_keywords = [
                "テクスチャ抽出成功",
                "テクスチャ保存完了", 
                "テクスチャ適用成功",
                "texture_metadata.json",
                "BlenderObjectEncoder"
            ]
            
            texture_error_keywords = [
                "Context missing active object",
                "Segmentation fault",
                "テクスチャ抽出失敗",
                "テクスチャ適用失敗"
            ]
            
            success_count = 0
            error_count = 0
            
            for keyword in texture_success_keywords:
                if keyword in pipeline_log:
                    logger.info(f"✓ 成功確認: {keyword}")
                    success_count += 1
            
            for keyword in texture_error_keywords:
                if keyword in pipeline_log:
                    logger.error(f"❌ エラー検出: {keyword}")
                    error_count += 1
            
            # 結果判定
            if error_count == 0 and success_count > 0:
                logger.info("🎉 テクスチャ保存・復元システム修正成功！")
                logger.info("✅ FBXインポート時のコンテキストエラーが修正されました")
                return True
            elif error_count == 0:
                logger.warning("⚠️ エラーは検出されませんでしたが、成功の確認もできませんでした")
                return False
            else:
                logger.error("❌ まだエラーが残っています")
                return False
        else:
            logger.warning("パイプラインログが取得できませんでした")
            return False
        
    except requests.exceptions.Timeout:
        logger.error("❌ タイムアウトエラー: パイプライン実行が時間切れです")
        return False
    except Exception as e:
        logger.error(f"❌ API呼び出し中にエラー: {e}")
        return False

def create_test_fbx(output_path):
    """簡単なテスト用FBXファイルを作成"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # より詳細なBlenderスクリプトで、テクスチャ付きのモデルを作成
    blender_script = f"""
import bpy
import bmesh
import os

# シーンをクリア
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# キューブを作成
bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 1))
cube = bpy.context.active_object
cube.name = "TestCharacter"

# UVマップを追加
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.uv.unwrap()
bpy.ops.object.mode_set(mode='OBJECT')

# マテリアルを作成
material = bpy.data.materials.new(name="TestMaterial")
material.use_nodes = True
cube.data.materials.append(material)

# ノードツリーを設定
nodes = material.node_tree.nodes
links = material.node_tree.links

# デフォルトのPrincipled BSDFノードを取得
principled = nodes.get("Principled BSDF")
if principled:
    # カラーテクスチャノードを追加
    tex_node = nodes.new(type='ShaderNodeTexImage')
    tex_node.location = (-400, 0)
    
    # 簡単なテクスチャ画像を作成
    test_image = bpy.data.images.new("TestTexture", 256, 256)
    # 画像にピクセルデータを設定（赤色）
    pixels = [1.0, 0.0, 0.0, 1.0] * (256 * 256)
    test_image.pixels = pixels
    tex_node.image = test_image
    
    # テクスチャをBase Colorに接続
    links.new(tex_node.outputs['Color'], principled.inputs['Base Color'])

# FBXとして保存
bpy.ops.export_scene.fbx(
    filepath="{output_path}",
    use_selection=False,
    global_scale=1.0,
    use_mesh_modifiers=True,
    embed_textures=True
)

print("テスト用FBXファイルを作成しました")
"""
    
    # Blenderでスクリプトを実行
    import subprocess
    script_path = "/tmp/create_test_fbx_texture.py"
    with open(script_path, 'w') as f:
        f.write(blender_script)
    
    try:
        result = subprocess.run(
            ['blender', '--background', '--python', script_path], 
            check=True, 
            capture_output=True, 
            text=True
        )
        logger.info(f"テスト用FBXファイルを作成しました: {output_path}")
        if os.path.exists(output_path):
            logger.info(f"ファイルサイズ: {os.path.getsize(output_path)} bytes")
    except subprocess.CalledProcessError as e:
        logger.warning(f"Blenderでのテスト用FBX作成に失敗: {e}")
        # フォールバック: 簡単なダミーファイルを作成
        with open(output_path, 'wb') as f:
            # より大きなダミーファイルを作成（FBXらしく見せるため）
            fbx_header = b'FBX\\x00\\x1a\\x00'
            dummy_content = b'A' * 10000  # 10KB のダミーデータ
            f.write(fbx_header + dummy_content)
        logger.info(f"フォールバックでダミーFBXファイルを作成: {output_path}")

def main():
    """メイン実行関数"""
    logger.info("=== Gradio API直接呼び出しによるテクスチャシステムテスト ===")
    
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
    
    # APIテスト実行
    success = test_gradio_api_direct()
    
    if success:
        logger.info("\n🎉 全てのテストが正常に完了しました！")
        logger.info("✅ FBXインポート時のコンテキストエラーは修正されました")
        logger.info("✅ テクスチャ保存・復元システムが正常に動作しています")
    else:
        logger.error("\n❌ テストが失敗しました")
        logger.error("さらなる修正が必要です")

if __name__ == "__main__":
    main()
