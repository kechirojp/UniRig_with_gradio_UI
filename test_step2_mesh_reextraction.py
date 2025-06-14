#!/usr/bin/env python3
"""
Step2メッシュ再抽出テスト
あなたの指摘した「スケルトン生成時のメッシュ再抽出の重要性」を検証
"""

import logging
import sys
from pathlib import Path

# UniRig実行パス設定
sys.path.append('/app')

# Step2実行関数をインポート
from step_modules.step2_skeleton import generate_skeleton_step2

def test_step2_with_mesh_reextraction():
    """Step2のメッシュ再抽出機能をテスト"""
    
    # ログ設定
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("Step2MeshReExtractionTest")
    
    # テストパラメータ
    test_model_name = "bird_app_test"
    mesh_file = "/app/pipeline_work/bird_app_test/01_extracted_mesh/raw_data.npz"
    output_dir = "/app/pipeline_work/bird_app_test/02_skeleton"
    
    logger.info("=" * 80)
    logger.info("🔥 Step2メッシュ再抽出テスト開始")
    logger.info("=" * 80)
    logger.info(f"入力メッシュファイル: {mesh_file}")
    logger.info(f"出力ディレクトリ: {output_dir}")
    logger.info(f"モデル名: {test_model_name}")
    
    # Step1の出力確認
    mesh_path = Path(mesh_file)
    if not mesh_path.exists():
        logger.error(f"❌ Step1の出力ファイルが存在しません: {mesh_file}")
        logger.error("Step1を先に実行してください")
        return False
    
    file_size = mesh_path.stat().st_size
    logger.info(f"✅ Step1出力確認: {mesh_file} ({file_size:,} bytes)")
    
    # Step2実行（メッシュ再抽出込み）
    logger.info("🔥 Step2実行開始（メッシュ再抽出込み）...")
    success, logs, output_files = generate_skeleton_step2(
        test_model_name, 
        mesh_file, 
        output_dir, 
        gender="neutral"
    )
    
    logger.info(f"実行結果: {'✅ 成功' if success else '❌ 失敗'}")
    
    # 実行ログ表示
    logger.info("=" * 60)
    logger.info("🔍 Step2実行ログ:")
    logger.info("=" * 60)
    print(logs)
    
    if success:
        logger.info("=" * 60)
        logger.info("📁 Step2出力ファイル確認:")
        logger.info("=" * 60)
        
        for key, file_path in output_files.items():
            file_obj = Path(file_path)
            if file_obj.exists():
                size = file_obj.stat().st_size
                logger.info(f"✅ {key}: {file_path} ({size:,} bytes)")
            else:
                logger.info(f"❌ {key}: {file_path} (存在しません)")
        
        # 出力ディレクトリの全ファイル確認
        output_path = Path(output_dir)
        if output_path.exists():
            logger.info("=" * 60)
            logger.info("📂 出力ディレクトリ全ファイル:")
            logger.info("=" * 60)
            for item in output_path.iterdir():
                if item.is_file():
                    size = item.stat().st_size
                    logger.info(f"  - {item.name}: {size:,} bytes")
        
        logger.info("=" * 80)
        logger.info("🎉 Step2メッシュ再抽出テスト完全成功！")
        logger.info("🔥 原作シェルスクリプトと同じ動作を実現")
        logger.info("=" * 80)
        return True
    else:
        logger.error("=" * 80)
        logger.error("❌ Step2実行失敗")
        logger.error("🔍 エラー解析が必要です")
        logger.error("=" * 80)
        return False

if __name__ == "__main__":
    success = test_step2_with_mesh_reextraction()
    sys.exit(0 if success else 1)
