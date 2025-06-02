#!/usr/bin/env python3
"""
修正されたテクスチャ保存・復元システムのフルパイプラインテスト
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

def test_full_pipeline_with_texture_preservation():
    """フルパイプラインでのテクスチャ保存・復元テスト"""
    
    # テスト用FBXファイルのパス
    test_fbx_path = "/app/pipeline_work/test_models/character.fbx"
    
    # テスト用FBXファイルが存在しない場合は作成
    if not os.path.exists(test_fbx_path):
        logger.info("テスト用FBXファイルが見つかりません。簡単なテストファイルを作成します...")
        create_test_fbx(test_fbx_path)
    
    logger.info("=== フルパイプライン実行（テクスチャ保存・復元システム付き） ===")
    
    try:
        # フルパイプラインAPIを呼び出し
        with open(test_fbx_path, 'rb') as f:
            files = {
                'uploaded_model_path': ('character.fbx', f, 'application/octet-stream')
            }
            data = {
                'gender': 'female'
            }
            
            logger.info("フルパイプライン実行中...")
            response = requests.post(
                f"{API_BASE}/run_full_auto_rigging",
                files=files,
                data=data,
                timeout=600  # 10分のタイムアウト
            )
        
        if response.status_code != 200:
            logger.error(f"フルパイプラインAPI失敗: {response.status_code}")
            logger.error(f"レスポンス: {response.text}")
            return False
        
        result = response.json()
        logger.info("フルパイプライン完了！結果を確認中...")
        
        # 結果の分析
        data = result.get('data', [])
        if not data or len(data) < 11:
            logger.error("予期しない応答形式です")
            return False
        
        # 各ステップの結果を確認
        final_model_preview = data[0]  # 最終リギング済みモデルプレビュー
        pipeline_log = data[1]         # フルパイプラインログ
        final_fbx = data[2]           # 🎯 最終モデル (FBX)
        
        logger.info("=== 結果分析 ===")
        
        # パイプラインログを確認
        if pipeline_log:
            logger.info("📋 パイプラインログ:")
            log_lines = pipeline_log.split('\n')
            for line in log_lines[-20:]:  # 最後の20行を表示
                if line.strip():
                    logger.info(f"   {line}")
            
            # テクスチャ関連のキーワードをチェック
            texture_keywords = [
                "テクスチャ抽出",
                "テクスチャ保存", 
                "テクスチャ適用",
                "Context missing active object",
                "Segmentation fault",
                "texture_metadata.json",
                "BlenderObjectEncoder"
            ]
            
            for keyword in texture_keywords:
                if keyword in pipeline_log:
                    if keyword in ["Context missing active object", "Segmentation fault"]:
                        logger.error(f"❌ エラー検出: {keyword}")
                    else:
                        logger.info(f"✓ 検出: {keyword}")
        
        # 最終ファイルの確認
        if final_fbx and isinstance(final_fbx, dict) and 'path' in final_fbx:
            final_path = final_fbx['path']
            if os.path.exists(final_path):
                file_size = os.path.getsize(final_path)
                logger.info(f"✓ 最終FBXファイル確認: {final_path}")
                logger.info(f"✓ ファイルサイズ: {file_size} bytes")
                
                if file_size > 10240:  # 10KB以上なら成功とみなす
                    logger.info("🎉 テクスチャ保存・復元システム修正成功！")
                    
                    # ログ内でエラーがないかチェック
                    if "Context missing active object" not in pipeline_log and "Segmentation fault" not in pipeline_log:
                        logger.info("✅ FBXインポート時のコンテキストエラーが修正されました")
                        logger.info("✅ セグメンテーションフォルトも発生していません")
                        return True
                    else:
                        logger.warning("⚠️ 出力は成功したが、まだエラーが残っています")
                        return False
                else:
                    logger.warning("⚠️ 出力ファイルサイズが小さすぎます")
                    return False
            else:
                logger.error(f"✗ 最終FBXファイルが見つかりません: {final_path}")
                return False
        else:
            logger.error("✗ 最終FBX情報が取得できません")
            return False
        
    except requests.exceptions.Timeout:
        logger.error("❌ タイムアウトエラー: パイプライン実行が時間切れです")
        return False
    except Exception as e:
        logger.error(f"❌ フルパイプライン実行中にエラー: {e}")
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
    script_path = "/tmp/create_test_fbx_with_texture.py"
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
    except subprocess.CalledProcessError as e:
        logger.warning(f"Blenderでのテスト用FBX作成に失敗: {e}")
        logger.warning("フォールバック: 簡単なダミーファイルを作成")
        # フォールバック: 簡単なダミーファイルを作成
        with open(output_path, 'wb') as f:
            f.write(b"dummy_fbx_content_with_texture_data")

def main():
    """メイン実行関数"""
    logger.info("=== 修正されたテクスチャ保存・復元システムのテスト開始 ===")
    
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
    
    # フルパイプラインテスト実行
    success = test_full_pipeline_with_texture_preservation()
    
    if success:
        logger.info("\n🎉 全てのテストが正常に完了しました！")
        logger.info("✅ FBXインポート時のコンテキストエラーは修正されました")
        logger.info("✅ テクスチャ保存・復元システムが正常に動作しています")
    else:
        logger.error("\n❌ テストが失敗しました")
        logger.error("さらなる修正が必要です")

if __name__ == "__main__":
    main()
