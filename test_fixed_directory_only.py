#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UniRig 固定ディレクトリ確認テスト
決め打ちの固定ディレクトリに正しい統一命名規則でファイルが存在するかのみを確認
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append('/app')

def test_fixed_directory_file_existence():
    """固定ディレクトリにファイルが存在するかのみを確認"""
    print("🔍 固定ディレクトリファイル存在確認テスト")
    
    model_name = "bird"
    base_dir = Path(f"/app/pipeline_work/{model_name}")
    
    # 期待されるファイル一覧（固定ディレクトリ + 統一命名規則）
    expected_files = {
        "Step1 - メッシュ抽出": base_dir / "01_extracted_mesh" / f"{model_name}_mesh.npz",
        "Step1 - raw_data": base_dir / "01_extracted_mesh" / "raw_data.npz",
        "Step2 - スケルトンFBX": base_dir / "02_skeleton" / f"{model_name}_skeleton.fbx",
        "Step2 - スケルトンNPZ": base_dir / "02_skeleton" / f"{model_name}_skeleton.npz",
        "Step3 - スキニングFBX": base_dir / "03_skinning" / f"{model_name}_skinned.fbx",
        "Step4 - マージFBX": base_dir / "04_merge" / f"{model_name}_merged.fbx",
        "Step5 - 最終FBX": base_dir / "05_blender_integration" / f"{model_name}_final.fbx",
    }
    
    print(f"モデル名: {model_name}")
    print(f"ベースディレクトリ: {base_dir}")
    print()
    
    # ファイル存在確認
    results = {}
    for step_name, file_path in expected_files.items():
        exists = file_path.exists()
        results[step_name] = exists
        
        status = "✅" if exists else "❌"
        size_info = ""
        if exists:
            size = file_path.stat().st_size
            size_info = f" ({size:,} bytes)"
        
        print(f"{status} {step_name}: {file_path}{size_info}")
    
    # サマリー
    print()
    total_files = len(expected_files)
    existing_files = sum(1 for exists in results.values() if exists)
    
    print(f"📊 ファイル存在状況: {existing_files}/{total_files}")
    
    if existing_files == 0:
        print("⚠️ パイプライン未実行 - app.pyでパイプラインを実行してください")
    elif existing_files == total_files:
        print("🎉 全ファイル存在 - パイプライン完全実行済み")
    else:
        print(f"🔄 パイプライン部分実行済み - Step{existing_files + 1}を実行してください")
    
    return results

def main():
    """メインテスト実行"""
    print("🎯 UniRig 固定ディレクトリファイル存在確認")
    print("=" * 60)
    
    try:
        results = test_fixed_directory_file_existence()
        
        # 結果に基づいてexitコード決定
        existing_count = sum(1 for exists in results.values() if exists)
        if existing_count > 0:
            print("\n✅ 少なくとも一部のファイルが存在します")
            return True
        else:
            print("\n❌ ファイルが存在しません")
            return False
            
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
