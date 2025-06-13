#!/usr/bin/env python3
"""
Step3 UniRig本格スキニング修正版テスト
目的: 今回の修正でUniRigが正常動作することを確認

修正内容:
1. raw_data ファイル（拡張子なし）の作成
2. /app からの実行によるパス解決
3. 実際のUniRig出力ファイル名（raw_data_predict_skin.npz）への対応
"""

import logging
import sys
from pathlib import Path

# プロジェクトルートを追加
sys.path.append('/app')

from step_modules.step3_skinning_unirig import Step3UniRigSkinning

def setup_logging():
    """テスト用ログ設定"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s:%(name)s:%(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    return logging.getLogger("test")

def main():
    logger = setup_logging()
    logger.info("=== Step3 UniRig本格スキニング修正版テスト開始 ===")
    
    # テスト入力ファイル（birdモデルを使用）
    input_mesh_npz = Path("/app/pipeline_work/bird/01_extracted_mesh/raw_data.npz")
    input_skeleton_fbx = Path("/app/pipeline_work/bird/02_skeleton/bird.fbx")
    input_skeleton_npz = Path("/app/pipeline_work/bird/02_skeleton/predict_skeleton.npz")
    model_name = "bird"
    
    # 出力ディレクトリ
    output_dir = Path("/app/test_step3_unirig_fixed_output")
    output_dir.mkdir(exist_ok=True)
    
    # 入力ファイル存在確認
    for file_path in [input_mesh_npz, input_skeleton_fbx, input_skeleton_npz]:
        if not file_path.exists():
            logger.error(f"入力ファイルが見つかりません: {file_path}")
            return
        logger.info(f"✅ 入力ファイル確認: {file_path} ({file_path.stat().st_size} bytes)")
    
    # Step3モジュール実行
    step3 = Step3UniRigSkinning(output_dir, logger)
    
    logger.info("🚀 Step3 UniRig本格スキニング実行開始...")
    success, logs, outputs = step3.apply_skinning(
        input_mesh_npz, 
        input_skeleton_fbx, 
        input_skeleton_npz, 
        model_name
    )
    
    logger.info(f"実行結果: {'成功' if success else '失敗'}")
    logger.info(f"ログ: {logs}")
    logger.info(f"出力ファイル: {outputs}")
    
    if success:
        logger.info("🎉 Step3 UniRig本格スキニング修正版テスト成功！")
        
        # 出力ファイル詳細確認
        for key, value in outputs.items():
            if isinstance(value, str) and Path(value).exists():
                file_size = Path(value).stat().st_size
                logger.info(f"📁 {key}: {value} ({file_size} bytes)")
            else:
                logger.info(f"📋 {key}: {value}")
    else:
        logger.error("❌ Step3 UniRig本格スキニング修正版テスト失敗")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
