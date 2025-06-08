#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 3 スキニングモジュール デバッグ用テストスクリプト（一時的）
確認後削除予定 - プロジェクトルールに従う
"""

import os
import sys
import logging
import traceback
from pathlib import Path
import numpy as np

# パスの追加
sys.path.append('/app')

# ログ設定
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_data_loading():
    """データ読み込みの詳細デバッグ"""
    print("=== データ読み込み詳細デバッグ ===")
    
    # 1. メッシュファイルの詳細確認
    mesh_file = "/app/pipeline_work/01_extracted_mesh/raw_data.npz"
    print(f"\n1. メッシュファイル分析: {mesh_file}")
    print(f"   存在: {os.path.exists(mesh_file)}")
    
    if os.path.exists(mesh_file):
        try:
            mesh_data = np.load(mesh_file)
            print(f"   キー: {list(mesh_data.keys())}")
            for key in mesh_data.keys():
                value = mesh_data[key]
                print(f"     {key}: shape={value.shape}, dtype={value.dtype}")
                if key == "vertices":
                    print(f"       最初の3頂点: {value[:3]}")
                elif key == "faces":
                    print(f"       最初の3面: {value[:3]}")
        except Exception as e:
            print(f"   メッシュ読み込みエラー: {e}")
            traceback.print_exc()
    
    # 2. スケルトンファイルの詳細確認
    skeleton_file = "/app/pipeline_work/02_skeleton/bird_skeleton.fbx"
    skeleton_npz = "/app/pipeline_work/02_skeleton/bird_skeleton.npz"
    
    print(f"\n2. スケルトンファイル分析:")
    print(f"   FBX: {skeleton_file} (存在: {os.path.exists(skeleton_file)})")
    print(f"   NPZ: {skeleton_npz} (存在: {os.path.exists(skeleton_npz)})")
    
    if os.path.exists(skeleton_npz):
        try:
            skeleton_data = np.load(skeleton_npz, allow_pickle=True)
            print(f"   キー: {list(skeleton_data.keys())}")
            for key in skeleton_data.keys():
                value = skeleton_data[key]
                print(f"     {key}: type={type(value)}")
                if isinstance(value, np.ndarray):
                    print(f"       shape={value.shape}, dtype={value.dtype}")
                    if key == "bone_names":
                        print(f"       bone_names type: {type(value)}")
                        print(f"       bone_names content: {value}")
                        print(f"       hasattr tolist: {hasattr(value, 'tolist')}")
                        if hasattr(value, 'tolist'):
                            try:
                                converted = value.tolist()
                                print(f"       tolist() 成功: {converted[:5]}")
                            except Exception as e:
                                print(f"       tolist() エラー: {e}")
                else:
                    print(f"       値: {value}")
        except Exception as e:
            print(f"   スケルトン読み込みエラー: {e}")
            traceback.print_exc()

def debug_step3_execution():
    """Step 3 実行の詳細デバッグ"""
    print("\n=== Step 3 実行詳細デバッグ ===")
    
    try:
        from step_modules.step3_skinning import Step3Skinning
        
        # テスト用ディレクトリ
        output_dir = "/app/temp_test_step3"
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # ファイルパス
        mesh_file = "/app/pipeline_work/01_extracted_mesh/raw_data.npz"
        skeleton_file = "/app/pipeline_work/02_skeleton/bird_skeleton.fbx"
        
        # Step 3 インスタンス作成
        step3 = Step3Skinning(output_dir)
        
        print("Step 3 インスタンス作成成功")
        
        # 個別メソッドテスト
        print("\n--- _load_mesh_data テスト ---")
        mesh_data = step3._load_mesh_data(mesh_file)
        if mesh_data:
            print(f"メッシュデータ読み込み成功:")
            for key, value in mesh_data.items():
                if hasattr(value, 'shape'):
                    print(f"  {key}: shape={value.shape}")
                else:
                    print(f"  {key}: {type(value)}")
        else:
            print("メッシュデータ読み込み失敗")
        
        print("\n--- _load_skeleton_data テスト ---")
        skeleton_data = step3._load_skeleton_data(skeleton_file)
        if skeleton_data:
            print(f"スケルトンデータ読み込み成功:")
            for key, value in skeleton_data.items():
                if hasattr(value, 'shape'):
                    print(f"  {key}: shape={value.shape}")
                else:
                    print(f"  {key}: {type(value)} = {value}")
        else:
            print("スケルトンデータ読み込み失敗")
        
        # 完全実行テスト
        if mesh_data and skeleton_data:
            print("\n--- 完全実行テスト ---")
            success, logs, output_files = step3.apply_skinning(
                mesh_file=mesh_file,
                skeleton_file=skeleton_file,
                model_name="debug_bird"
            )
            
            print(f"実行結果: {success}")
            print(f"ログ:\n{logs}")
            print(f"出力ファイル: {output_files}")
            
            return success
        else:
            print("データ読み込み失敗のため、完全実行をスキップ")
            return False
            
    except Exception as e:
        print(f"Step 3 実行エラー: {e}")
        traceback.print_exc()
        return False

def debug_app_integration():
    """app.py との統合デバッグ"""
    print("\n=== app.py 統合デバッグ ===")
    
    try:
        # app.pyから直接実行
        import importlib.util
        spec = importlib.util.spec_from_file_location("app", "/app/app.py")
        app_module = importlib.util.module_from_spec(spec)
        
        # app.pyの関数を確認
        print("app.py モジュール読み込み成功")
        
        # Step 3 関連の関数があるか確認
        if hasattr(app_module, 'run_step'):
            print("run_step 関数が存在します")
        else:
            print("run_step 関数が見つかりません")
        
        # 実際のapp.pyの実行ではなく、構文チェックのみ
        with open('/app/app.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 構文エラーチェック
        try:
            compile(content, '/app/app.py', 'exec')
            print("app.py 構文チェック: 正常")
        except SyntaxError as e:
            print(f"app.py 構文エラー: {e}")
            print(f"  行 {e.lineno}: {e.text}")
        
        return True
        
    except Exception as e:
        print(f"app.py 統合エラー: {e}")
        traceback.print_exc()
        return False

def debug_pipeline_files():
    """パイプラインファイルの状態確認"""
    print("\n=== パイプラインファイル状態確認 ===")
    
    pipeline_files = [
        "/app/pipeline_work/00_asset_preservation/bird",
        "/app/pipeline_work/01_extracted_mesh/raw_data.npz",
        "/app/pipeline_work/02_skeleton/bird_skeleton.fbx",
        "/app/pipeline_work/02_skeleton/bird_skeleton.npz",
        "/app/pipeline_work/03_skinning/bird_skinned.fbx",
        "/app/pipeline_work/03_skinning/bird_skinning.npz",
        "/app/pipeline_work/04_merge/bird_final.fbx"
    ]
    
    for file_path in pipeline_files:
        exists = os.path.exists(file_path)
        if exists:
            if os.path.isfile(file_path):
                size = os.path.getsize(file_path)
                print(f"✓ {file_path} ({size} bytes)")
            else:
                print(f"✓ {file_path} (ディレクトリ)")
        else:
            print(f"✗ {file_path} (存在しない)")
    
    return True

def main():
    """メイン実行"""
    print("Step 3 スキニングモジュール 詳細デバッグテスト")
    print("=" * 60)
    
    # 各デバッグテストを実行
    tests = [
        ("データ読み込み", debug_data_loading),
        ("Step 3 実行", debug_step3_execution),
        ("app.py 統合", debug_app_integration),
        ("パイプラインファイル", debug_pipeline_files)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"{test_name} 完了: {'成功' if result else '失敗'}")
        except Exception as e:
            print(f"{test_name} 例外エラー: {e}")
            results.append((test_name, False))
    
    # 結果まとめ
    print("\n" + "=" * 60)
    print("デバッグテスト結果:")
    for test_name, result in results:
        status = "✓" if result else "✗"
        print(f"  {status} {test_name}")
    
    all_passed = all(result for _, result in results)
    print(f"\n総合結果: {'すべて成功' if all_passed else '一部失敗'}")
    
    print(f"\n注意: このテストファイルは確認後削除してください")
    print(f"削除コマンド: rm /app/temp_debug_step3.py")

if __name__ == "__main__":
    main()
