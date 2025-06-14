#!/usr/bin/env python3
"""
Step1とapp.pyの統合テスト
決め打ちディレクトリ戦略の完全動作確認
"""

import logging
import sys
from pathlib import Path

# UniRig実行パス設定
sys.path.append('/app')

# app.pyからStep1実行関数をインポート
from app import execute_step1_wrapper

def test_step1_integration():
    """Step1とapp.pyの統合テスト"""
    
    # ログ設定
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("Step1IntegrationTest")
    
    # テストパラメータ
    test_model_name = "bird_app_test"
    test_input_file = "/app/examples/bird.glb"
    
    logger.info("=" * 60)
    logger.info("Step1 ⇔ app.py 統合テスト開始")
    logger.info("=" * 60)
    logger.info(f"入力ファイル: {test_input_file}")
    logger.info(f"モデル名: {test_model_name}")
    
    # Step1実行
    success, logs = execute_step1_wrapper(test_model_name, test_input_file)
    
    logger.info(f"実行結果: {'✅ 成功' if success else '❌ 失敗'}")
    logger.info("実行ログ:")
    print(logs)
    
    if success:
        # 出力ファイル確認
        expected_output_dir = Path(f"/app/pipeline_work/{test_model_name}/01_extracted_mesh")
        expected_file = expected_output_dir / "raw_data.npz"
        
        if expected_file.exists():
            file_size = expected_file.stat().st_size
            logger.info(f"✅ 期待出力ファイル確認成功: {expected_file}")
            logger.info(f"✅ ファイルサイズ: {file_size:,} bytes")
            
            # ディレクトリ内容表示
            logger.info(f"✅ 出力ディレクトリ内容:")
            for item in expected_output_dir.iterdir():
                if item.is_file():
                    size = item.stat().st_size
                    logger.info(f"  - {item.name}: {size:,} bytes")
            
            logger.info("=" * 60)
            logger.info("🎉 Step1統合テスト完全成功！")
            logger.info("=" * 60)
            return True
        else:
            logger.error(f"❌ 期待出力ファイル不存在: {expected_file}")
            return False
    else:
        logger.error("❌ Step1実行失敗")
        return False

if __name__ == "__main__":
    success = test_step1_integration()
    sys.exit(0 if success else 1)
