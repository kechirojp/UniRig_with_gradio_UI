#!/usr/bin/env python3
"""
完全データフロー検証スクリプト
修正されたStep1〜Step4のデータフロー整合性を確認
"""

import os
import sys
import shutil
from pathlib import Path
import time
import logging

# プロジェクトルートを追加
sys.path.insert(0, "/app")

# 各ステップモジュールのインポート
from step_modules.step1_extract import Step1MeshExtraction
from step_modules.step2_skeleton import Step2SkeletonGeneration
from step_modules.step3_skinning import Step3SkinningApplication
from step_modules.step4_texture import Step4TextureIntegration

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def clean_test_environment():
    """テスト環境のクリーンアップ"""
    test_dirs = [
        "/app/test_complete_dataflow_output",
        "/app/dataset_inference_clean/test_dataflow_bird"
    ]
    
    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
            logger.info(f"クリーンアップ: {test_dir}")

def setup_test_environment():
    """テスト環境の準備"""
    output_dir = Path("/app/test_complete_dataflow_output")
    output_dir.mkdir(exist_ok=True)
    return output_dir

def test_complete_dataflow():
    """完全データフロー検証"""
    logger.info("=" * 80)
    logger.info("完全データフロー検証開始")
    logger.info("=" * 80)
    
    # 環境準備
    clean_test_environment()
    output_dir = setup_test_environment()
    
    # テストモデル
    input_file = "/app/examples/bird.glb"
    model_name = "test_dataflow_bird"
    
    # ファイル存在確認
    if not os.path.exists(input_file):
        logger.error(f"テストモデルが見つかりません: {input_file}")
        return False
    
    logger.info(f"テストモデル: {input_file}")
    logger.info(f"モデル名: {model_name}")
    logger.info(f"出力ディレクトリ: {output_dir}")
    
    # Step 1: メッシュ抽出
    logger.info("\n" + "=" * 50)
    logger.info("Step 1: メッシュ抽出")
    logger.info("=" * 50)
    
    step1 = Step1MeshExtraction(output_dir)
    step1_success, step1_logs, step1_files = step1.extract_mesh(input_file, model_name)
    
    logger.info(f"Step 1 結果: {step1_success}")
    logger.info(f"Step 1 ログ: {step1_logs}")
    logger.info(f"Step 1 ファイル: {step1_files}")
    
    if not step1_success:
        logger.error("Step 1 失敗")
        return False
    
    # Step 2: スケルトン生成
    logger.info("\n" + "=" * 50)
    logger.info("Step 2: スケルトン生成")
    logger.info("=" * 50)
    
    step2 = Step2SkeletonGeneration(output_dir)
    step2_success, step2_logs, step2_files = step2.generate_skeleton(
        step1_files["extracted_npz"], model_name, "neutral"
    )
    
    logger.info(f"Step 2 結果: {step2_success}")
    logger.info(f"Step 2 ログ: {step2_logs}")
    logger.info(f"Step 2 ファイル: {step2_files}")
    
    if not step2_success:
        logger.error("Step 2 失敗")
        return False
    
    # Step 3: スキニング適用
    logger.info("\n" + "=" * 50)
    logger.info("Step 3: スキニング適用")
    logger.info("=" * 50)
    
    step3 = Step3SkinningApplication(output_dir)
    step3_success, step3_logs, step3_files = step3.apply_skinning(
        step1_files["extracted_npz"],
        step2_files["skeleton_fbx"],
        model_name
    )
    
    logger.info(f"Step 3 結果: {step3_success}")
    logger.info(f"Step 3 ログ: {step3_logs}")
    logger.info(f"Step 3 ファイル: {step3_files}")
    
    if not step3_success:
        logger.error("Step 3 失敗")
        return False
    
    # Step 4: テクスチャ統合
    logger.info("\n" + "=" * 50)
    logger.info("Step 4: テクスチャ統合")
    logger.info("=" * 50)
    
    step4 = Step4TextureIntegration(output_dir)
    step4_success, step4_logs, step4_files = step4.merge_textures(
        model_name,
        step3_files["skinned_fbx"],
        input_file
    )
    
    logger.info(f"Step 4 結果: {step4_success}")
    logger.info(f"Step 4 ログ: {step4_logs}")
    logger.info(f"Step 4 ファイル: {step4_files}")
    
    if not step4_success:
        logger.error("Step 4 失敗")
        return False
    
    # 完全検証結果
    logger.info("\n" + "=" * 80)
    logger.info("完全データフロー検証結果")
    logger.info("=" * 80)
    
    logger.info("✅ 全ステップ成功!")
    
    # ファイルサイズ情報
    logger.info("\nファイルサイズ情報:")
    for step_name, files in [
        ("Step 1", step1_files),
        ("Step 2", step2_files), 
        ("Step 3", step3_files),
        ("Step 4", step4_files)
    ]:
        logger.info(f"\n{step_name}:")
        for key, filepath in files.items():
            if os.path.exists(filepath):
                size = os.path.getsize(filepath)
                logger.info(f"  {key}: {filepath} ({size:,} bytes)")
            else:
                logger.warning(f"  {key}: {filepath} (ファイル未発見)")
    
    # データフロー整合性チェック
    logger.info("\nデータフロー整合性チェック:")
    
    # Step2出力ファイル名確認
    step2_fbx = Path(step2_files["skeleton_fbx"])
    step2_npz = Path(step2_files["skeleton_npz"])
    
    logger.info(f"Step2 FBXファイル名: {step2_fbx.name}")
    logger.info(f"Step2 NPZファイル名: {step2_npz.name}")
    
    # 大元フロー互換性確認
    expected_fbx_name = f"{model_name}.fbx"
    expected_npz_name = "predict_skeleton.npz"
    
    if step2_fbx.name == expected_fbx_name:
        logger.info(f"✅ Step2 FBXファイル名正常: {expected_fbx_name}")
    else:
        logger.error(f"❌ Step2 FBXファイル名不整合: 期待値={expected_fbx_name}, 実際={step2_fbx.name}")
    
    if step2_npz.name == expected_npz_name:
        logger.info(f"✅ Step2 NPZファイル名正常: {expected_npz_name}")
    else:
        logger.error(f"❌ Step2 NPZファイル名不整合: 期待値={expected_npz_name}, 実際={step2_npz.name}")
    
    return True

if __name__ == "__main__":
    try:
        success = test_complete_dataflow()
        if success:
            logger.info("\n🎉 完全データフロー検証成功!")
        else:
            logger.error("\n💥 完全データフロー検証失敗!")
            sys.exit(1)
    except Exception as e:
        logger.error(f"検証中にエラー発生: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
