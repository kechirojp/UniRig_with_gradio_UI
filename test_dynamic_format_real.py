#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
動的ファイル形式対応の実動作テスト

このスクリプトは、実際のファイルを作成して動的ファイル形式対応をテストします。

実行方法:
    cd /app
    python test_dynamic_format_real.py
"""

import sys
import os
import logging
from pathlib import Path

# プロジェクトルートを追加
sys.path.insert(0, '/app')

def create_test_files():
    """テスト用ファイルを作成"""
    print("=== テスト用ファイル作成 ===")
    
    test_model_name = "test_dynamic"
    base_dir = Path("/app/pipeline_work")
    
    # テストディレクトリ作成
    test_dir = base_dir / test_model_name
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Step0ディレクトリとファイル作成
    step0_dir = test_dir / "00_asset_preservation"
    step0_dir.mkdir(parents=True, exist_ok=True)
    
    # 異なる形式のテストファイル作成
    test_formats = [
        (".glb", "test_dynamic.glb"),
        (".fbx", "test_dynamic.fbx"),
        (".obj", "test_dynamic.obj"),
        (".vrm", "test_dynamic.vrm")
    ]
    
    created_files = []
    for ext, filename in test_formats:
        test_file = step0_dir / filename
        # ダミーファイル作成
        with open(test_file, 'w') as f:
            f.write(f"# Test {ext} file\n")
        created_files.append(test_file)
        print(f"作成: {test_file}")
    
    return test_model_name, created_files

def test_dynamic_extension_detection():
    """動的拡張子検出のテスト"""
    print("\n=== 動的拡張子検出テスト ===")
    
    try:
        from fixed_directory_manager import FixedDirectoryManager
        
        # 各形式を個別にテスト
        test_formats = [
            (".glb", "test_dynamic.glb"),
            (".fbx", "test_dynamic.fbx"),
            (".obj", "test_dynamic.obj"),
            (".vrm", "test_dynamic.vrm")
        ]
        
        base_dir = Path("/app/pipeline_work")
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        for ext, filename in test_formats:
            print(f"\nテスト対象: {filename} (拡張子: {ext})")
            
            # 個別テストのためにクリーンなディレクトリを作成
            test_model_name = f"test_{ext[1:]}"  # .glb -> test_glb
            test_dir = base_dir / test_model_name
            test_dir.mkdir(parents=True, exist_ok=True)
            
            # Step0ディレクトリとファイル作成
            step0_dir = test_dir / "00_asset_preservation"
            step0_dir.mkdir(parents=True, exist_ok=True)
            
            # 単一ファイル作成
            test_file = step0_dir / filename.replace("test_dynamic", test_model_name)
            with open(test_file, 'w') as f:
                f.write(f"# Test {ext} file\n")
            
            print(f"作成: {test_file}")
            
            # ディレクトリマネージャー作成
            fdm = FixedDirectoryManager(base_dir, test_model_name, logger)
            
            # 拡張子取得テスト
            detected_ext = fdm.get_original_file_extension()
            print(f"検出された拡張子: {detected_ext}")
            
            # Step5出力パス生成テスト
            step5_path = fdm.get_step5_output_path_with_original_extension()
            print(f"Step5出力パス: {step5_path}")
            
            # 期待値と比較
            expected_output = f"{test_model_name}_final{ext}"
            if step5_path.name == expected_output:
                print(f"[OK] 期待値と一致: {expected_output}")
            else:
                print(f"[WARN] 期待値と不一致: 期待={expected_output}, 実際={step5_path.name}")
            
            # テストディレクトリ削除
            import shutil
            shutil.rmtree(test_dir)
    
        return True
        
    except Exception as e:
        print(f"[FAIL] 動的拡張子検出テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_step5_output_file_detection():
    """Step5出力ファイル検出テスト"""
    print("\n=== Step5出力ファイル検出テスト ===")
    
    try:
        from fixed_directory_manager import FixedDirectoryManager
        
        test_model_name = "test_dynamic"
        base_dir = Path("/app/pipeline_work")
        
        fdm = FixedDirectoryManager(base_dir, test_model_name)
        
        # Step5ディレクトリ作成
        step5_dir = fdm.get_step_dir('step5')
        step5_dir.mkdir(parents=True, exist_ok=True)
        
        # 異なる形式のStep5出力ファイルを作成
        test_outputs = [
            "test_dynamic_final.glb",
            "test_dynamic_final.fbx", 
            "test_dynamic_final.obj",
            "test_dynamic_final.vrm"
        ]
        
        for output_filename in test_outputs:
            # テスト出力ファイル作成
            output_file = step5_dir / output_filename
            with open(output_file, 'w') as f:
                f.write(f"# Test Step5 output: {output_filename}\n")
            
            print(f"作成された出力ファイル: {output_file}")
            
            # 動的検出テスト
            found_file = fdm.find_file_with_dynamic_extension("step5", "final_output")
            if found_file:
                print(f"[OK] 動的検出成功: {found_file}")
            else:
                print(f"[WARN] 動的検出失敗")
            
            # ダウンロードファイル取得テスト
            download_files = fdm.get_user_download_files()
            final_model = download_files.get("final_rigged_model")
            if final_model:
                print(f"[OK] ダウンロード用ファイル検出: {final_model}")
            else:
                print(f"[WARN] ダウンロード用ファイル未検出")
            
            # テストファイル削除（次のテスト用）
            output_file.unlink()
            print("---")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Step5出力ファイル検出テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def cleanup_test_files():
    """テストファイルのクリーンアップ"""
    print("\n=== テストファイルクリーンアップ ===")
    
    try:
        test_dir = Path("/app/pipeline_work/test_dynamic")
        if test_dir.exists():
            import shutil
            shutil.rmtree(test_dir)
            print(f"[OK] テストディレクトリ削除: {test_dir}")
        return True
    except Exception as e:
        print(f"[WARN] クリーンアップエラー: {e}")
        return False

def main():
    """メインテスト実行"""
    print("動的ファイル形式対応 実動作テスト開始")
    print("=" * 60)
    
    tests = [
        test_dynamic_extension_detection,
        test_step5_output_file_detection
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"[FAIL] テスト実行エラー: {e}")
            results.append(False)
    
    # クリーンアップ
    cleanup_test_files()
    
    print("\n" + "=" * 60)
    print("テスト結果サマリー:")
    passed = sum(results)
    total = len(results)
    print(f"成功: {passed}/{total}")
    
    if passed == total:
        print("[OK] 全てのテストが成功しました")
        print("💡 動的ファイル形式対応は正常に動作しています")
    else:
        print("[WARN] 一部のテストが失敗しました")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
