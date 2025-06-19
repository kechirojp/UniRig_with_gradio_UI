#!/usr/bin/env python3
"""
Step3スケルトン入力ファイル検証テスト
Step2の出力とStep3の入力期待値の整合性確認
"""

import sys
from pathlib import Path
sys.path.insert(0, '/app')

def debug_step3_skeleton_input():
    """Step3スケルトン入力ファイルの検証"""
    print("[DEBUG] Step3 スケルトン入力ファイル検証開始")
    
    # テストモデル名
    model_name = "bird"
    
    # Step2出力ディレクトリ
    step2_output_dir = Path(f"/app/pipeline_work/{model_name}/02_skeleton/")
    
    print(f"[DEBUG] Step2出力ディレクトリ: {step2_output_dir}")
    print(f"[DEBUG] ディレクトリ存在確認: {step2_output_dir.exists()}")
    
    if step2_output_dir.exists():
        print("[DEBUG] Step2出力ファイル一覧:")
        for file in step2_output_dir.iterdir():
            print(f"  - {file.name} ({file.stat().st_size} bytes)")
    
    # Step3が期待するファイル
    expected_skeleton_fbx = step2_output_dir / f"{model_name}_skeleton.fbx"
    expected_skeleton_npz = step2_output_dir / f"{model_name}_skeleton.npz"
    
    print(f"\n[DEBUG] Step3が期待するファイル:")
    print(f"  - skeleton_fbx: {expected_skeleton_fbx}")
    print(f"    存在確認: {expected_skeleton_fbx.exists()}")
    if expected_skeleton_fbx.exists():
        print(f"    ファイルサイズ: {expected_skeleton_fbx.stat().st_size} bytes")
    
    print(f"  - skeleton_npz: {expected_skeleton_npz}")
    print(f"    存在確認: {expected_skeleton_npz.exists()}")
    if expected_skeleton_npz.exists():
        print(f"    ファイルサイズ: {expected_skeleton_npz.stat().st_size} bytes")
    
    # Step3が実際に使用するskeleton_files辞書を模擬
    skeleton_files = {}
    if expected_skeleton_fbx.exists():
        skeleton_files["skeleton_fbx"] = str(expected_skeleton_fbx)
    if expected_skeleton_npz.exists():
        skeleton_files["skeleton_npz"] = str(expected_skeleton_npz)
    
    print(f"\n[DEBUG] Step3に渡されるskeleton_files辞書:")
    for key, value in skeleton_files.items():
        print(f"  {key}: {value}")
    
    # Step3の内部処理をシミュレート
    print(f"\n[DEBUG] Step3内部処理シミュレーション:")
    skeleton_fbx_path = skeleton_files.get("skeleton_fbx") or skeleton_files.get("unified_skeleton_fbx")
    if skeleton_fbx_path:
        print(f"  skeleton_fbx_path取得成功: {skeleton_fbx_path}")
        print(f"  ファイル存在確認: {Path(skeleton_fbx_path).exists()}")
    else:
        print("  ❌ skeleton_fbx_pathが取得できません")
    
    skeleton_npz_path = skeleton_files.get("skeleton_npz") or skeleton_files.get("unified_skeleton_npz")
    if skeleton_npz_path:
        print(f"  skeleton_npz_path取得成功: {skeleton_npz_path}")
        print(f"  ファイル存在確認: {Path(skeleton_npz_path).exists()}")
    else:
        print("  ❌ skeleton_npz_pathが取得できません")

if __name__ == "__main__":
    debug_step3_skeleton_input()
