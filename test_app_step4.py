#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app.py経由でのStep4実行テスト
目的: 正しくskinned_fbxがsourceとして使用されるかを確認
"""

import sys
sys.path.append('/app')

from app import execute_step4
import logging

# ロガー設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_step4_execution():
    model_name = "bird"
    
    print("=== app.py経由でのStep4実行テスト ===")
    print(f"モデル名: {model_name}")
    
    # Step4実行
    success, logs = execute_step4(model_name)
    
    print(f"\n--- 実行結果 ---")
    print(f"成功: {success}")
    print(f"ログ:\n{logs}")
    
    if success:
        # 出力ファイル確認
        from pathlib import Path
        output_file = Path(f"/app/pipeline_work/{model_name}/04_merge/{model_name}_merged.fbx")
        if output_file.exists():
            file_size = output_file.stat().st_size / (1024*1024)
            print(f"\n✅ 出力ファイル確認: {output_file} ({file_size:.2f} MB)")
        else:
            print(f"\n❌ 出力ファイルが見つかりません: {output_file}")
    
    return success

if __name__ == "__main__":
    success = test_step4_execution()
    print(f"\n=== テスト完了: {'成功' if success else '失敗'} ===")
