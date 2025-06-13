#!/usr/bin/env python3
"""
app.py経由でStep3 UniRigスキニングをテスト
目的: 実際のapp.pyとの連携確認

修正内容確認:
1. app.pyのシグネチャ修正を確認
2. 正常なデータフローを確認
"""

import logging
import sys
from pathlib import Path

# プロジェクトルートを追加
sys.path.append('/app')

# app.pyから直接インポート
from app import call_step3_apply_skinning, FileManager

def setup_logging():
    """テスト用ログ設定"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s:%(name)s:%(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    return logging.getLogger("app_test")

def main():
    logger = setup_logging()
    logger.info("=== app.py経由Step3 UniRigスキニング連携テスト開始 ===")
    
    # FileManagerでStep2出力ファイルパスを取得
    file_manager = FileManager("/app/pipeline_work")
    model_name = "bird"
    
    # Step2出力ファイル
    skeleton_fbx_path = file_manager.get_step_output_dir("step2_skeleton") / f"{model_name}.fbx"
    skeleton_npz_path = file_manager.get_step_output_dir("step2_skeleton") / "predict_skeleton.npz"
    mesh_npz_path = file_manager.get_step_output_dir("step1_extract") / "raw_data.npz"
    
    logger.info(f"入力メッシュNPZ: {mesh_npz_path}")
    logger.info(f"入力スケルトンFBX: {skeleton_fbx_path}")
    logger.info(f"入力スケルトンNPZ: {skeleton_npz_path}")
    
    # ファイル存在確認
    for file_path in [mesh_npz_path, skeleton_fbx_path, skeleton_npz_path]:
        if not file_path.exists():
            logger.error(f"必要ファイルが見つかりません: {file_path}")
            return
        logger.info(f"✅ ファイル確認: {file_path} ({file_path.stat().st_size} bytes)")
    
    # app.py経由でStep3実行
    try:
        logger.info("🚀 app.py経由でStep3 UniRigスキニング実行...")
        
        # 実際のapp.py関数を呼び出し
        pipeline_state = {}  # 簡易状態
        status, message, outputs = call_step3_apply_skinning(
            file_manager, model_name, "dummy_original.fbx", "UniRig Core", pipeline_state
        )
        
        logger.info(f"実行結果: {'成功' if status else '失敗'}")
        logger.info(f"メッセージ: {message}")
        logger.info(f"出力ファイル: {outputs}")
        
        if status:
            logger.info("🎉 app.py経由Step3 UniRigスキニング連携テスト成功！")
        else:
            logger.error("❌ app.py経由Step3 UniRigスキニング連携テスト失敗")
            
    except Exception as e:
        logger.error(f"テスト実行中にエラー: {e}", exc_info=True)

if __name__ == "__main__":
    main()
