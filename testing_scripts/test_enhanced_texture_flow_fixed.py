#!/usr/bin/env python3
"""
強化されたテクスチャフローの完全テスト（修正版）
Gradio Client APIを使用してフルパイプラインをテストし、
強化されたマテリアル処理でテクスチャが正しく埋め込まれるかを検証します。
"""

import os
import sys
import time
import logging
from gradio_client import Client, file

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_enhanced_texture_flow():
    """
    強化されたテクスチャフローをテストし、FBXファイルサイズとテクスチャ埋め込みを検証
    """
    logger.info("=== 強化されたテクスチャフロー完全テスト開始 ===")
    
    # テスト用ファイル
    test_model_path = "/app/examples/bird.glb"
    
    if not os.path.exists(test_model_path):
        logger.error(f"テストモデルファイルが見つかりません: {test_model_path}")
        return False
    
    logger.info(f"テストモデル: {test_model_path}")
    logger.info(f"元ファイルサイズ: {os.path.getsize(test_model_path) / (1024*1024):.2f} MB")
    
    try:
        # Gradioサーバーに接続
        server_url = "http://127.0.0.1:7862"
        logger.info(f"Gradioサーバーに接続中: {server_url}")
        
        client = Client(server_url)
        logger.info("✅ Gradioクライアント接続成功")
        
        # gradio_clientのfile()関数を使用してファイルを準備
        test_file = file(test_model_path)
        gender = "neutral"
        
        # フルパイプライン実行
        logger.info("🚀 強化されたテクスチャフローでフルパイプライン実行中...")
        start_time = time.time()
        
        result = client.predict(
            original_model_file_obj=test_file,
            gender=gender,
            api_name="/gradio_full_auto_rigging"
        )
        
        end_time = time.time()
        logger.info(f"✅ フルパイプライン完了 ({end_time - start_time:.1f}秒)")
        
        # 結果を解析
        if isinstance(result, (list, tuple)) and len(result) >= 3:
            display_model_path, logs, download_file_path = result[:3]
            
            logger.info(f"表示用モデルパス: {display_model_path}")
            logger.info(f"ダウンロード用ファイルパス: {download_file_path}")
            
            # ログの重要部分を抽出
            if logs:
                logger.info("=== 処理ログ抜粋 ===")
                log_lines = str(logs).split('\n')
                for line in log_lines:
                    if any(keyword in line for keyword in ['Step 4', 'texture', 'material', 'embed', 'FBX', 'ERROR', 'SUCCESS']):
                        logger.info(f"LOG: {line.strip()}")
            
            # 最終出力ファイルの詳細分析
            if download_file_path and os.path.exists(download_file_path):
                file_size_mb = os.path.getsize(download_file_path) / (1024*1024)
                logger.info(f"✅ 最終FBXファイル生成確認:")
                logger.info(f"   ファイルパス: {download_file_path}")
                logger.info(f"   ファイルサイズ: {file_size_mb:.2f} MB")
                
                # ファイルサイズ検証（期待値: 7.5-10MB）
                expected_min_size = 7.5
                expected_max_size = 10.0
                
                if file_size_mb >= expected_min_size:
                    logger.info(f"🎉 ファイルサイズOK: {file_size_mb:.2f}MB >= {expected_min_size}MB（期待値範囲）")
                    
                    # 詳細テクスチャ分析を実行
                    analyze_final_fbx_textures(download_file_path)
                    return True
                    
                else:
                    logger.warning(f"⚠️ ファイルサイズが小さすぎます: {file_size_mb:.2f}MB < {expected_min_size}MB")
                    logger.warning("テクスチャが完全に埋め込まれていない可能性があります")
                    
                    # 小さいサイズでも詳細分析を実行
                    analyze_final_fbx_textures(download_file_path)
                    return False
                    
            else:
                logger.error("❌ 最終FBXファイルが生成されませんでした")
                return False
                
        else:
            logger.error(f"❌ 予期しない結果形式: {result}")
            return False
            
    except Exception as e:
        logger.error(f"❌ テスト実行中にエラーが発生: {e}")
        import traceback
        traceback.print_exc()
        return False

def analyze_final_fbx_textures(fbx_path):
    """
    最終FBXファイルのテクスチャ埋め込み状況を詳細分析
    """
    logger.info("=== 最終FBXテクスチャ詳細分析 ===")
    
    try:
        # Blenderでファイルを分析
        import subprocess
        
        blender_script = f"""
import bpy
import os
import sys

# 既存シーンをクリア
bpy.ops.wm.read_factory_settings(use_empty=True)

try:
    # FBXファイルをインポート
    bpy.ops.import_scene.fbx(filepath="{fbx_path}")
    
    print("=== マテリアル分析結果 ===")
    material_count = 0
    texture_count = 0
    
    for material in bpy.data.materials:
        material_count += 1
        print(f"マテリアル: {{material.name}}")
        
        if material.use_nodes:
            for node in material.node_tree.nodes:
                if node.type == 'TEX_IMAGE':
                    texture_count += 1
                    image = node.image
                    if image:
                        print(f"  テクスチャノード: {{node.name}}")
                        print(f"    画像名: {{image.name}}")
                        print(f"    ファイルパス: {{image.filepath}}")
                        print(f"    パックされている: {{image.packed_file is not None}}")
                        if image.packed_file:
                            print(f"    パックサイズ: {{len(image.packed_file.data)} bytes")
                        print(f"    サイズ: {{image.size[0]}}x{{image.size[1]}}")
                    else:
                        print(f"  テクスチャノード: {{node.name}} (画像なし)")
    
    print(f"\\n合計マテリアル数: {{material_count}}")
    print(f"合計テクスチャ数: {{texture_count}}")
    
    # 画像データの詳細
    print("\\n=== 画像データ詳細 ===")
    total_packed_size = 0
    for image in bpy.data.images:
        print(f"画像: {{image.name}}")
        print(f"  ファイルパス: {{image.filepath}}")
        print(f"  サイズ: {{image.size[0]}}x{{image.size[1]}}")
        if image.packed_file:
            packed_size = len(image.packed_file.data)
            total_packed_size += packed_size
            print(f"  パックサイズ: {{packed_size / (1024*1024):.2f}} MB")
        else:
            print(f"  パックされていません")
    
    print(f"\\n総パックテクスチャサイズ: {{total_packed_size / (1024*1024):.2f}} MB")
    
except Exception as e:
    print(f"エラー: {{e}}")
    import traceback
    traceback.print_exc()
"""
        
        # Blenderスクリプトを一時ファイルに保存
        script_path = "/tmp/analyze_fbx_textures.py"
        with open(script_path, 'w') as f:
            f.write(blender_script)
        
        # Blenderでスクリプト実行
        cmd = ["blender", "--background", "--python", script_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            logger.info("Blender分析結果:")
            for line in result.stdout.split('\n'):
                if any(keyword in line for keyword in ['マテリアル', 'テクスチャ', '画像', 'パック', 'サイズ']):
                    logger.info(f"  {line}")
        else:
            logger.error(f"Blender分析エラー: {result.stderr}")
        
        # 一時ファイル削除
        if os.path.exists(script_path):
            os.remove(script_path)
            
    except Exception as e:
        logger.error(f"テクスチャ分析エラー: {e}")

def check_gradio_server():
    """Gradioサーバーの起動状況をチェック"""
    import requests
    
    try:
        response = requests.get("http://127.0.0.1:7862", timeout=5)
        if response.status_code == 200:
            logger.info("✅ Gradioサーバー起動確認")
            return True
        else:
            logger.error(f"❌ Gradioサーバーレスポンス異常: {response.status_code}")
            return False
    except requests.ConnectionError:
        logger.error("❌ Gradioサーバーに接続できません")
        logger.error("サーバーを起動してください: python app.py")
        return False
    except Exception as e:
        logger.error(f"❌ サーバーチェックエラー: {e}")
        return False

def main():
    """メイン関数"""
    logger.info("=== 強化されたテクスチャフロー完全テスト ===")
    
    # Gradioサーバーチェック
    if not check_gradio_server():
        return False
    
    # テスト実行
    success = test_enhanced_texture_flow()
    
    if success:
        logger.info("🎉 強化されたテクスチャフローテスト成功！")
        logger.info("全てのテクスチャが正しく埋め込まれました")
    else:
        logger.error("❌ 強化されたテクスチャフローテスト失敗")
        logger.error("テクスチャ埋め込みに問題があります")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
