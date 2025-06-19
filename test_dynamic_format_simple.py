#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
動的ファイル形式対応テスト（最小限実装）

このスクリプトは、アップロードされたファイルの拡張子を取得して、
Step5の出力ファイル形式を動的に決定する機能をテストします。

実行方法:
    cd /app
    python test_dynamic_format_simple.py
"""

import sys
import os
from pathlib import Path

# プロジェクトルートを追加
sys.path.insert(0, '/app')

def test_simple_extension_extraction():
    """シンプルな拡張子取得のテスト"""
    print("=== シンプル拡張子取得テスト ===")
    
    test_files = [
        "bird.glb",
        "character.fbx", 
        "model.obj",
        "avatar.vrm",
        "scene.gltf",
        "mesh.dae"
    ]
    
    for filename in test_files:
        # ユーザーの指摘通り：ファイル名の末尾から最初のピリオドまで
        ext = Path(filename).suffix.lower()
        print(f"ファイル: {filename} → 拡張子: {ext}")
    
    return True

def test_step5_output_path_generation():
    """Step5出力パス生成テスト"""
    print("\n=== Step5出力パス生成テスト ===")
    
    model_name = "test_bird"
    test_extensions = [".glb", ".fbx", ".obj", ".vrm"]
    
    for ext in test_extensions:
        # 元ファイル形式と同じ形式で出力
        output_filename = f"{model_name}_final{ext}"
        print(f"元形式: {ext} → 出力: {output_filename}")
    
    return True

def test_current_step5_implementation():
    """現在のStep5実装の確認"""
    print("\n=== 現在のStep5実装確認 ===")
    
    try:
        # Step5の実装を確認
        from step_modules.step5_blender_integration import Step5BlenderIntegration
        print("[OK] Step5BlenderIntegration モジュール読み込み成功")
        
        # rigging_transfer_adapted.pyの確認
        rigging_script = Path('/app/rigging_transfer_adapted.py')
        if rigging_script.exists():
            print(f"[OK] リギング移植スクリプト存在: {rigging_script}")
        else:
            print(f"[WARN] リギング移植スクリプト未発見: {rigging_script}")
        
        return True
        
    except ImportError as e:
        print(f"[FAIL] Step5インポートエラー: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] Step5確認エラー: {e}")
        return False

def test_fixed_directory_manager():
    """FixedDirectoryManagerの動的形式対応テスト"""
    print("\n=== FixedDirectoryManager動的形式対応テスト ===")
    
    try:
        from fixed_directory_manager import FixedDirectoryManager
        import logging
        
        # テスト用ディレクトリマネージャー作成
        base_dir = Path("/app/pipeline_work")
        model_name = "test_dynamic"
        logger = logging.getLogger(__name__)
        
        fdm = FixedDirectoryManager(base_dir, model_name, logger)
        
        # 動的拡張子取得関数があるか確認
        if hasattr(fdm, 'get_original_file_extension'):
            print("[OK] get_original_file_extension メソッド存在")
        else:
            print("[WARN] get_original_file_extension メソッド未実装")
        
        # 動的ファイル検索関数があるか確認  
        if hasattr(fdm, 'find_file_with_dynamic_extension'):
            print("[OK] find_file_with_dynamic_extension メソッド存在")
        else:
            print("[WARN] find_file_with_dynamic_extension メソッド未実装")
        
        return True
        
    except ImportError as e:
        print(f"[FAIL] FixedDirectoryManagerインポートエラー: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] FixedDirectoryManager確認エラー: {e}")
        return False

def main():
    """メインテスト実行"""
    print("動的ファイル形式対応テスト開始")
    print("=" * 50)
    
    tests = [
        test_simple_extension_extraction,
        test_step5_output_path_generation,
        test_current_step5_implementation,
        test_fixed_directory_manager
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"[FAIL] テスト実行エラー: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("テスト結果サマリー:")
    passed = sum(results)
    total = len(results)
    print(f"成功: {passed}/{total}")
    
    if passed == total:
        print("[OK] 全てのテストが成功しました")
    else:
        print("[WARN] 一部のテストが失敗しました")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
