#!/usr/bin/env python3
"""
Step2修正版テスト - Blenderクラッシュ対応確認
"""

import sys
sys.path.append('/app')
from step_modules.step2_skeleton_old_02 import execute_step2
from pathlib import Path
import logging

def main():
    # ログ設定
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('Test')
    
    print('Step2テスト実行開始...')
    
    try:
        result, logs, files = execute_step2(
            original_file=Path('/app/examples/bird.glb'),
            model_name='bird_test',
            step_output_dir=Path('/app/pipeline_work/bird_test/02_skeleton'),
            logger=logger,
            gender='neutral'
        )
        
        print(f'Result: {result}')
        print(f'Logs: {logs}')
        print(f'Files: {files}')
        
        if result:
            print("✅ Step2テスト成功！")
        else:
            print("❌ Step2テスト失敗")
            
    except Exception as e:
        print(f"❌ テスト実行エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
