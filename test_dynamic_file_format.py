#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
動的ファイル形式対応テスト
元ファイル形式を維持したStep5出力機能のテスト
"""

import sys
import json
from pathlib import Path

# プロジェクトルートを追加
sys.path.insert(0, '/app')

def test_dynamic_file_format():
    """動的ファイル形式対応のテスト"""
    print("=== 動的ファイル形式対応テスト ===")
    
    try:
        from fixed_directory_manager import FixedDirectoryManager
        import logging
        
        # テスト用ロガー作成
        logger = logging.getLogger(__name__)
        
        # テストケース1: GLBファイルでテスト
        print("\n1. GLBファイル形式テスト")
        
        # テスト用ディレクトリ構造作成
        test_base_dir = Path("/app/test_pipeline_work")
        test_model_name = "test_bird"
        
        fdm = FixedDirectoryManager(test_base_dir, test_model_name, logger)
        fdm.create_all_directories()
        
        # Step0メタデータ作成（GLB形式）
        step0_dir = fdm.get_step_dir('step0')
        metadata = {
            "model_name": test_model_name,
            "file_extension": ".glb",
            "original_file": "/app/uploads/test_bird.glb"
        }
        
        metadata_file = step0_dir / f"{test_model_name}_asset_metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"[SETUP] メタデータ作成: {metadata_file}")
        
        # 元ファイル形式取得テスト
        original_ext = fdm.get_original_file_extension()
        print(f"[TEST] 取得した元ファイル形式: {original_ext}")
        
        expected_ext = ".glb"
        if original_ext == expected_ext:
            print(f"[OK] 元ファイル形式取得成功: {original_ext}")
        else:
            print(f"[FAIL] 元ファイル形式取得失敗: 期待={expected_ext}, 実際={original_ext}")
            return False
        
        # Step5出力パス生成テスト
        step5_output_path = fdm.get_step5_output_path_with_original_extension()
        expected_path = step0_dir.parent / "05_blender_integration" / f"{test_model_name}_final.glb"
        
        print(f"[TEST] Step5出力パス: {step5_output_path}")
        print(f"[TEST] 期待されるパス: {expected_path}")
        
        if step5_output_path == expected_path:
            print(f"[OK] Step5出力パス生成成功")
        else:
            print(f"[FAIL] Step5出力パス生成失敗")
            return False
        
        # テストケース2: FBXファイルでテスト
        print("\n2. FBXファイル形式テスト")
        
        # メタデータ更新（FBX形式）
        metadata["file_extension"] = ".fbx"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        original_ext = fdm.get_original_file_extension()
        if original_ext == ".fbx":
            print(f"[OK] FBX形式取得成功: {original_ext}")
        else:
            print(f"[FAIL] FBX形式取得失敗: {original_ext}")
            return False
        
        # テストケース3: 動的ファイル検索テスト
        print("\n3. 動的ファイル検索テスト")
        
        # テスト用Step5ファイル作成
        step5_dir = fdm.get_step_dir('step5')
        test_fbx_file = step5_dir / f"{test_model_name}_final.fbx"
        test_glb_file = step5_dir / f"{test_model_name}_final.glb"
        
        # FBXファイル作成
        test_fbx_file.write_text("test fbx content")
        
        # GLB形式で検索
        metadata["file_extension"] = ".glb"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        found_file = fdm.find_file_with_dynamic_extension("step5", "final_output")
        if found_file:
            print(f"[WARN] GLB形式要求だがFBXファイルを検出: {found_file}")
        
        # GLBファイル作成
        test_glb_file.write_text("test glb content")
        
        found_file = fdm.find_file_with_dynamic_extension("step5", "final_output")
        if found_file and found_file.name.endswith('.glb'):
            print(f"[OK] GLB形式ファイル検索成功: {found_file}")
        else:
            print(f"[FAIL] GLB形式ファイル検索失敗: {found_file}")
            return False
        
        print("\n[SUCCESS] 全ての動的ファイル形式テストが成功しました！")
        return True
        
    except Exception as e:
        print(f"[ERROR] テスト実行エラー: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # クリーンアップ
        try:
            import shutil
            if test_base_dir.exists():
                shutil.rmtree(test_base_dir)
                print(f"[CLEANUP] テストディレクトリ削除: {test_base_dir}")
        except:
            pass

if __name__ == "__main__":
    success = test_dynamic_file_format()
    sys.exit(0 if success else 1)
