#!/usr/bin/env python3
"""
修正されたテクスチャ保存システムのテスト
ノードタイプ認識エラーが修正されているかを検証します。
"""

import os
import sys
import logging
import shutil
import json

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_fixed_texture_integration():
    """修正されたテクスチャ統合システムをテスト"""
    logger.info("=== 修正されたテクスチャ統合システムのテスト ===")
    
    # 作業ディレクトリの設定
    work_dir = "/app/pipeline_work"
    bird_dir = os.path.join(work_dir, "06_final_output", "bird")
    rigged_fbx = os.path.join(bird_dir, "bird_final.fbx")
    texture_data_dir = os.path.join(work_dir, "05_texture_preservation", "bird")
    output_fbx = os.path.join(bird_dir, "bird_final_textures_fixed.fbx")
    
    # ファイル存在確認
    if not os.path.exists(rigged_fbx):
        logger.error(f"リギング済みFBXが見つかりません: {rigged_fbx}")
        return False
    
    if not os.path.exists(texture_data_dir):
        logger.error(f"テクスチャデータディレクトリが見つかりません: {texture_data_dir}")
        return False
    
    # ファイルサイズを記録
    rigged_size = os.path.getsize(rigged_fbx) / (1024 * 1024)  # MB
    logger.info(f"入力FBXサイズ: {rigged_size:.2f} MB")
    
    # テクスチャファイルサイズを確認
    texture_dir = os.path.join(texture_data_dir, "extracted_textures")
    if os.path.exists(texture_dir):
        texture_files = os.listdir(texture_dir)
        total_texture_size = sum(
            os.path.getsize(os.path.join(texture_dir, f)) 
            for f in texture_files if os.path.isfile(os.path.join(texture_dir, f))
        ) / (1024 * 1024)
        logger.info(f"テクスチャファイル: {len(texture_files)} 個, 合計サイズ: {total_texture_size:.2f} MB")
    
    try:
        # Python環境でBlenderを実行
        logger.info("Blenderプロセスでテクスチャ統合を実行...")
        
        # テスト用スクリプトを作成
        test_script = f"""
import sys
sys.path.append('/app')

import bpy
from texture_preservation_system import TexturePreservationSystem

# テクスチャ保存システムを初期化
system = TexturePreservationSystem()

# テクスチャ統合を実行
success = system.apply_texture_to_rigged_model(
    rigged_fbx_path="{rigged_fbx}",
    texture_data_dir="{texture_data_dir}",
    output_fbx_path="{output_fbx}"
)

print(f"テクスチャ統合結果: {{success}}")

# 結果をファイルに記録
import json
result = {{
    "success": success,
    "output_exists": os.path.exists("{output_fbx}"),
    "output_size": os.path.getsize("{output_fbx}") if os.path.exists("{output_fbx}") else 0
}}

with open("/app/texture_integration_result.json", "w") as f:
    json.dump(result, f, indent=2)
"""
        
        # スクリプトをファイルに保存
        script_path = "/app/test_texture_integration_fixed.py"
        with open(script_path, 'w') as f:
            f.write(test_script)
        
        # Blenderでスクリプトを実行
        import subprocess
        cmd = f"cd /app && blender --background --python {script_path}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        
        logger.info("Blender実行完了")
        if result.stdout:
            logger.info("Blender出力:")
            for line in result.stdout.split('\n')[-20:]:  # 最後の20行のみ表示
                if line.strip():
                    logger.info(f"  {line}")
        
        if result.stderr:
            logger.warning("Blenderエラー:")
            for line in result.stderr.split('\n')[-10:]:  # 最後の10行のみ表示
                if line.strip():
                    logger.warning(f"  {line}")
        
        # 結果を確認
        result_file = "/app/texture_integration_result.json"
        if os.path.exists(result_file):
            with open(result_file, 'r') as f:
                integration_result = json.load(f)
            
            logger.info(f"統合結果: {integration_result}")
            
            if integration_result["success"] and integration_result["output_exists"]:
                output_size = integration_result["output_size"] / (1024 * 1024)
                size_increase = output_size - rigged_size
                
                logger.info(f"✅ テクスチャ統合成功!")
                logger.info(f"出力FBXサイズ: {output_size:.2f} MB")
                logger.info(f"サイズ増加: +{size_increase:.2f} MB")
                
                if size_increase > 1.0:  # 1MB以上の増加があれば、テクスチャが埋め込まれた可能性
                    logger.info("✅ テクスチャが正常に埋め込まれた可能性があります")
                else:
                    logger.warning("⚠️ サイズ増加が少ないため、テクスチャ埋め込みが不完全な可能性があります")
                
                return True
            else:
                logger.error("❌ テクスチャ統合に失敗")
                return False
        else:
            logger.error("❌ 結果ファイルが生成されませんでした")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("❌ Blender実行がタイムアウトしました")
        return False
    except Exception as e:
        logger.error(f"❌ テスト実行中にエラー: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def verify_node_type_mapping():
    """ノードタイプマッピングが正しく読み込まれるかを確認"""
    logger.info("=== ノードタイプマッピング検証 ===")
    
    mapping_file = "/app/detected_node_types.json"
    if not os.path.exists(mapping_file):
        logger.error(f"ノードタイプマッピングファイルが見つかりません: {mapping_file}")
        return False
    
    try:
        with open(mapping_file, 'r') as f:
            data = json.load(f)
        
        mapping = data.get("normalized_mapping", {})
        logger.info("検出されたノードタイプマッピング:")
        for normalized, actual in mapping.items():
            logger.info(f"  {normalized} -> {actual}")
        
        # 重要なノードタイプが含まれているかチェック
        required_types = ['BSDF_PRINCIPLED', 'TEX_IMAGE', 'OUTPUT_MATERIAL']
        missing_types = [t for t in required_types if t not in mapping]
        
        if missing_types:
            logger.warning(f"必須ノードタイプが不足: {missing_types}")
            return False
        else:
            logger.info("✅ 必須ノードタイプがすべて含まれています")
            return True
            
    except Exception as e:
        logger.error(f"ノードタイプマッピング検証エラー: {e}")
        return False

if __name__ == "__main__":
    logger.info("修正されたテクスチャ保存システムのテスト開始")
    
    # 1. ノードタイプマッピング検証
    mapping_ok = verify_node_type_mapping()
    
    # 2. テクスチャ統合テスト
    if mapping_ok:
        integration_ok = test_fixed_texture_integration()
        
        if integration_ok:
            logger.info("🎉 全てのテストが成功しました!")
            logger.info("テクスチャ保存システムの修正が完了しました。")
        else:
            logger.error("💥 テクスチャ統合テストに失敗しました。")
    else:
        logger.error("💥 ノードタイプマッピング検証に失敗しました。")
    
    logger.info("テスト完了")
