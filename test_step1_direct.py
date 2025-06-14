#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
テスト用パイプライン実行スクリプト
固定ファイルでStep1の実行をテスト
"""

import sys
sys.path.append('/app')

from pathlib import Path
import logging
from fixed_directory_manager import FixedDirectoryManager
from src.pipeline.unified_extract import UnifiedExtractor

def test_step1_direct():
    """Step1を直接テスト"""
    
    # ロガー設定
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("test_step1")
    
    # テストパラメータ
    model_name = "bird"
    input_file = "/app/examples/bird.glb"
    base_dir = Path("/app/pipeline_work")
    
    print(f"=== Step1直接テスト開始 ===")
    print(f"モデル名: {model_name}")
    print(f"入力ファイル: {input_file}")
    print(f"ベースディレクトリ: {base_dir}")
    
    # FixedDirectoryManager初期化
    fdm = FixedDirectoryManager(base_dir, model_name, logger)
    
    # ディレクトリ作成
    success = fdm.create_all_directories()
    if not success:
        print("❌ ディレクトリ作成失敗")
        return False
    
    print("✅ ディレクトリ作成完了")
    
    # UnifiedExtractor初期化
    extractor = UnifiedExtractor(logger)
    
    # Step1実行
    result = extractor.execute(
        model_name=model_name,
        input_file=input_file,
        directory_manager=fdm
    )
    
    print(f"=== Step1実行結果 ===")
    print(f"成功: {result.get('success', False)}")
    print(f"統一ファイル: {result.get('unified_files', {})}")
    print(f"原流ファイル: {result.get('original_files', {})}")
    
    if 'logs' in result:
        print(f"ログ:\n{result['logs']}")
    
    if 'error' in result:
        print(f"❌ エラー: {result['error']}")
    
    return result.get('success', False)

if __name__ == "__main__":
    success = test_step1_direct()
    exit(0 if success else 1)
