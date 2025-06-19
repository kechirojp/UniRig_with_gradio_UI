#!/usr/bin/env python3
"""
🔍 UniRig パイプラインファイル検証テスト
命名規則の柔軟性とファイル数の検証機能をテスト

2025年6月14日作成
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any

# プロジェクトルートを追加
sys.path.insert(0, '/app')

# 必要なモジュールをインポート
from fixed_directory_manager import FixedDirectoryManager

def setup_test_logger() -> logging.Logger:
    """テスト用ロガー設定"""
    logger = logging.getLogger("pipeline_file_validation_test")
    logger.setLevel(logging.DEBUG)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger

def test_file_generation_patterns():
    """ファイル生成パターンのテスト"""
    logger = setup_test_logger()
    logger.info("🔍 ファイル生成パターンテスト開始")
    
    test_model = "test_bird"
    pipeline_base = Path("/app/pipeline_work")
    
    # テスト用FixedDirectoryManager
    fdm = FixedDirectoryManager(pipeline_base, test_model, logger)
    
    results = {}
    
    # 各ステップの期待ファイル確認
    for step in ["step0", "step1", "step2", "step3", "step4", "step5"]:
        try:
            expected_files = fdm.get_expected_files(step)
            step_dir = fdm.get_step_dir(step)
            
            logger.info(f"[FILE] {step} 期待ファイル:")
            for key, path in expected_files.items():
                exists = path.exists() if hasattr(path, 'exists') else False
                logger.info(f"  {key}: {path} (存在: {exists})")
            
            results[step] = {
                "expected_files": expected_files,
                "step_dir": step_dir,
                "dir_exists": step_dir.exists()
            }
            
        except Exception as e:
            logger.error(f"[FAIL] {step} エラー: {e}")
            results[step] = {"error": str(e)}
    
    return results

def test_file_pattern_flexibility():
    """ファイルパターンの柔軟性テスト"""
    logger = setup_test_logger()
    logger.info("🔄 ファイルパターン柔軟性テスト開始")
    
    # テストファイルパターン
    test_patterns = {
        "step1": [
            "raw_data.npz",           # 標準
            "extracted_mesh.npz",     # 変則1
            "mesh_output.npz"         # 変則2
        ],
        "step2": [
            "test_bird.fbx",          # 標準 {model_name}.fbx
            "skeleton.fbx",           # 原流処理出力
            "test_bird_skeleton.fbx"  # 変則
        ],
        "step3": [
            "test_bird_skinned_unirig.fbx",  # 標準
            "result_fbx.fbx",                # 原流処理出力
            "test_bird_skinned.fbx"          # 変則
        ]
    }
    
    logger.info("📋 想定されるファイルパターン:")
    for step, patterns in test_patterns.items():
        logger.info(f"  {step}:")
        for pattern in patterns:
            logger.info(f"    - {pattern}")
    
    return test_patterns

def test_step_input_validation():
    """ステップ入力検証機能のテスト"""
    logger = setup_test_logger()
    logger.info("[OK] ステップ入力検証テスト開始")
    
    test_model = "test_bird"
    pipeline_base = Path("/app/pipeline_work")
    fdm = FixedDirectoryManager(pipeline_base, test_model, logger)
    
    validation_results = {}
    
    # 各ステップの入力検証
    for step in ["step2", "step3", "step4", "step5"]:
        try:
            # fdm.validate_step_inputsメソッドが存在するかチェック
            if hasattr(fdm, 'validate_step_inputs'):
                valid, message, available_files = fdm.validate_step_inputs(step)
                validation_results[step] = {
                    "valid": valid,
                    "message": message,
                    "available_files": available_files if valid else {}
                }
                logger.info(f"📊 {step} 入力検証: {'成功' if valid else '失敗'}")
                if not valid:
                    logger.warning(f"  メッセージ: {message}")
                else:
                    logger.info(f"  利用可能ファイル: {len(available_files)}個")
            else:
                validation_results[step] = {"error": "validate_step_inputsメソッドが存在しません"}
                logger.error(f"[FAIL] {step}: validate_step_inputsメソッドが見つかりません")
                
        except Exception as e:
            validation_results[step] = {"error": str(e)}
            logger.error(f"[FAIL] {step} 検証エラー: {e}")
    
    return validation_results

def test_file_count_verification():
    """ファイル数検証機能のテスト"""
    logger = setup_test_logger()
    logger.info("🔢 ファイル数検証テスト開始")
    
    # 各ステップで期待されるファイル数
    expected_counts = {
        "step0": 3,  # preserved_file, metadata_json, textures_dir
        "step1": 1,  # raw_data_npz
        "step2": 2,  # skeleton_fbx, skeleton_npz
        "step3": 2,  # skinned_fbx, skinning_npz
        "step4": 1,  # merged_fbx
        "step5": 2   # final_fbx, final_fbm_dir
    }
    
    test_model = "test_bird"
    pipeline_base = Path("/app/pipeline_work")
    fdm = FixedDirectoryManager(pipeline_base, test_model, logger)
    
    count_results = {}
    
    for step, expected_count in expected_counts.items():
        try:
            expected_files = fdm.get_expected_files(step)
            actual_count = len(expected_files)
            
            count_results[step] = {
                "expected_count": expected_count,
                "actual_count": actual_count,
                "match": expected_count == actual_count,
                "files": list(expected_files.keys())
            }
            
            status = "[OK]" if expected_count == actual_count else "⚠️"
            logger.info(f"{status} {step}: 期待{expected_count}個 vs 実際{actual_count}個")
            
        except Exception as e:
            count_results[step] = {"error": str(e)}
            logger.error(f"[FAIL] {step} カウントエラー: {e}")
    
    return count_results

def test_flexible_file_search():
    """柔軟なファイル検索機能のテスト"""
    logger = setup_test_logger()
    logger.info("🔍 柔軟ファイル検索テスト開始")
    
    # テスト用ディレクトリとファイル作成
    test_model = "test_bird"
    pipeline_base = Path("/app/pipeline_work")
    test_dir = pipeline_base / test_model / "01_extracted_mesh"
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # テストファイル作成
    test_files = [
        "raw_data.npz",
        "extracted_mesh.npz", 
        "mesh_output.npz",
        "other_file.txt"
    ]
    
    for file_name in test_files:
        test_file = test_dir / file_name
        test_file.write_text("test data")
    
    # NPZファイル検索テスト
    npz_files = list(test_dir.glob("*.npz"))
    logger.info(f"[FILE] {test_dir} 内のNPZファイル:")
    for npz_file in npz_files:
        logger.info(f"  - {npz_file.name}")
    
    # 柔軟な検索パターンテスト
    search_patterns = [
        "*raw_data*.npz",
        "*mesh*.npz", 
        "*.npz"
    ]
    
    search_results = {}
    for pattern in search_patterns:
        matches = list(test_dir.glob(pattern))
        search_results[pattern] = [m.name for m in matches]
        logger.info(f"🔍 パターン '{pattern}': {len(matches)}個のマッチ")
        for match in matches:
            logger.info(f"  - {match.name}")
    
    # テストファイル削除
    for file_name in test_files:
        test_file = test_dir / file_name
        if test_file.exists():
            test_file.unlink()
    
    return search_results

def analyze_app_py_file_handling():
    """app.pyのファイル処理方式を分析"""
    logger = setup_test_logger()
    logger.info("📋 app.pyファイル処理分析開始")
    
    app_py_path = Path("/app/app.py")
    
    if not app_py_path.exists():
        logger.error("[FAIL] app.pyが見つかりません")
        return {"error": "app.py not found"}
    
    # app.pyからファイル処理関連のコードを抽出
    with open(app_py_path, 'r', encoding='utf-8') as f:
        app_content = f.read()
    
    # 重要なパターンを検索
    important_patterns = [
        "get_expected_files",
        "validate_step_inputs",
        "exists()",
        ".glob(",
        "raw_data.npz",
        "predict_skeleton.npz",
        "_skinned_unirig.fbx",
        "_merged.fbx",
        "_final.fbx"
    ]
    
    pattern_analysis = {}
    for pattern in important_patterns:
        count = app_content.count(pattern)
        pattern_analysis[pattern] = count
        logger.info(f"🔍 '{pattern}': {count}回使用")
    
    # ステップ実行関数の分析
    step_functions = [
        "execute_step0",
        "execute_step1", 
        "execute_step2",
        "execute_step3",
        "execute_step4",
        "execute_step5"
    ]
    
    function_analysis = {}
    for func in step_functions:
        if func in app_content:
            # 関数定義の場所を見つける
            lines = app_content.split('\n')
            for i, line in enumerate(lines):
                if f"def {func}" in line:
                    function_analysis[func] = {
                        "found": True,
                        "line": i + 1,
                        "definition": line.strip()
                    }
                    logger.info(f"[OK] {func}: 行{i+1}で定義")
                    break
        else:
            function_analysis[func] = {"found": False}
            logger.warning(f"⚠️ {func}: 定義が見つかりません")
    
    return {
        "pattern_analysis": pattern_analysis,
        "function_analysis": function_analysis
    }

def main():
    """メインテスト実行"""
    logger = setup_test_logger()
    logger.info("🚀 UniRig パイプラインファイル検証テスト開始")
    
    print("="*80)
    print("🔍 UniRig パイプラインファイル検証テスト")
    print("="*80)
    
    # 1. ファイル生成パターンテスト
    print("\n1️⃣ ファイル生成パターンテスト")
    file_patterns = test_file_generation_patterns()
    
    # 2. ファイルパターン柔軟性テスト
    print("\n2️⃣ ファイルパターン柔軟性テスト")
    pattern_flexibility = test_file_pattern_flexibility()
    
    # 3. ステップ入力検証テスト
    print("\n3️⃣ ステップ入力検証テスト")
    input_validation = test_step_input_validation()
    
    # 4. ファイル数検証テスト
    print("\n4️⃣ ファイル数検証テスト")
    count_verification = test_file_count_verification()
    
    # 5. 柔軟ファイル検索テスト
    print("\n5️⃣ 柔軟ファイル検索テスト")
    flexible_search = test_flexible_file_search()
    
    # 6. app.pyファイル処理分析
    print("\n6️⃣ app.pyファイル処理分析")
    app_analysis = analyze_app_py_file_handling()
    
    # 総括レポート
    print("\n" + "="*80)
    print("📊 総括レポート")
    print("="*80)
    
    logger.info("[OK] 全テスト完了")
    
    # 重要な発見事項をまとめる
    print("\n🔍 重要な発見事項:")
    
    # ファイル数の整合性チェック
    print("\n📊 ファイル数整合性:")
    for step, result in count_verification.items():
        if "error" not in result:
            status = "[OK]" if result["match"] else "⚠️"
            print(f"  {status} {step}: {result['actual_count']}個のファイル")
    
    # app.pyでの重要パターン使用状況
    print("\n📋 app.py重要パターン使用状況:")
    if "pattern_analysis" in app_analysis:
        for pattern, count in app_analysis["pattern_analysis"].items():
            if count > 0:
                print(f"  [OK] {pattern}: {count}回使用")
    
    # 推奨事項
    print("\n💡 推奨事項:")
    print("  1. ファイル存在確認にglob()パターンマッチングを活用")
    print("  2. 命名規則の変化に対応する柔軟な検索機能")
    print("  3. ファイル数の期待値検証システム")
    print("  4. エラー時の詳細な診断情報提供")
    
    return {
        "file_patterns": file_patterns,
        "pattern_flexibility": pattern_flexibility,
        "input_validation": input_validation,
        "count_verification": count_verification,
        "flexible_search": flexible_search,
        "app_analysis": app_analysis
    }

if __name__ == "__main__":
    main()
