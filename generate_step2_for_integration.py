#!/usr/bin/env python3
"""
Step2スケルトン生成実行スクリプト
Step3→Step4連携テスト用の前提条件準備
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, '/app')
sys.path.insert(0, '/app/src')

from step_modules.step2_skeleton import Step2Skeleton

def generate_skeleton_for_integration_test():
    """Step2スケルトン生成実行"""
    
    # ロガー設定
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # テスト設定
    model_name = "bird"
    test_input_file = Path("/app/examples/bird.glb")
    step2_output_dir = Path(f"/app/pipeline_work/{model_name}/02_skeleton")
    
    if not test_input_file.exists():
        print(f"❌ テストファイルが存在しません: {test_input_file}")
        return False
    
    print(f"🔥 Step2スケルトン生成開始: {model_name}")
    print(f"📁 入力ファイル: {test_input_file}")
    print(f"📁 出力ディレクトリ: {step2_output_dir}")
    
    # Step2インスタンス作成
    step2 = Step2Skeleton(step2_output_dir, logger)
    
    # Step2実行
    success, logs, output_files = step2.generate_skeleton(
        test_input_file, model_name, "neutral"
    )
    
    print(f"\nStep2実行結果: {'✅成功' if success else '❌失敗'}")
    print(f"実行ログ:\n{logs}")
    
    # 出力ファイル確認
    print("\n=== Step2出力ファイル確認 ===")
    for key, value in output_files.items():
        if value and Path(value).exists():
            file_size = Path(value).stat().st_size
            print(f"✅ {key}: {value} ({file_size:,} bytes)")
        else:
            print(f"❌ {key}: {value} (不存在)")
    
    # 必要なファイルの存在確認
    skeleton_fbx = output_files.get('skeleton_fbx', '')
    skeleton_npz = output_files.get('skeleton_npz', '')
    
    files_ready = (skeleton_fbx and Path(skeleton_fbx).exists() and 
                   skeleton_npz and Path(skeleton_npz).exists())
    
    print(f"\n🎯 Step2完了状態: {'✅準備完了' if files_ready else '❌不完全'}")
    
    if files_ready:
        print("🔥 Step3→Step4連携テストの前提条件が整いました！")
        print("📝 次のステップ: test_step3_step4_integration.py を実行してください。")
    else:
        print("⚠️ Step2が完了していないため、Step3→Step4連携テストに影響する可能性があります。")
    
    return files_ready

if __name__ == "__main__":
    success = generate_skeleton_for_integration_test()
    if success:
        print("\n✅ Step2スケルトン生成が完了しました。")
    else:
        print("\n❌ Step2スケルトン生成で問題が発生しました。")
