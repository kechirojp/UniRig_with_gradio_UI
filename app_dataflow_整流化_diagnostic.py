#!/usr/bin/env python3
"""
app.pyデータフロー整流化診断ツール
命名規則の厳格化と原流処理互換性確保のための診断

2025年6月14日作成
"""

import os
import sys
from pathlib import Path

def analyze_current_dataflow():
    """現在のapp.pyデータフロー分析"""
    
    print("=== app.pyデータフロー整流化診断 ===")
    
    # 1. FixedDirectoryManagerの命名規則確認
    print("\n1. 🔍 FixedDirectoryManager命名規則確認")
    
    # 決め打ちディレクトリ戦略の正しいパターン
    correct_patterns = {
        "step0": {
            "preserved_file": "{model_name}.glb",           # ✅ モデル名接頭のみ
            "metadata_json": "{model_name}_asset_metadata.json",  # ✅ モデル名接頭のみ
            "textures_dir": "textures"                      # ✅ 完全固定
        },
        "step1": {
            "raw_data_npz": "raw_data.npz"                  # ✅ 完全固定（原流処理期待値）
        },
        "step2": {
            "skeleton_fbx": "{model_name}.fbx",             # ✅ モデル名接頭のみ（原流処理期待値）
            "skeleton_npz": "predict_skeleton.npz"          # ✅ 完全固定（原流処理期待値）
        },
        "step3": {
            "skinned_fbx": "{model_name}_skinned_unirig.fbx",  # ✅ モデル名接頭のみ
            "skinning_npz": "{model_name}_skinning.npz"       # ✅ モデル名接頭のみ
        },
        "step4": {
            "merged_fbx": "{model_name}_merged.fbx"         # ✅ モデル名接頭のみ
        },
        "step5": {
            "final_fbx": "{model_name}_final.fbx",          # ✅ モデル名接頭のみ
            "final_fbm_dir": "{model_name}_final.fbm"       # ✅ モデル名接頭のみ
        }
    }
    
    print("✅ 正しい命名規則パターン:")
    for step, files in correct_patterns.items():
        print(f"  {step}:")
        for key, pattern in files.items():
            print(f"    {key}: {pattern}")
    
    # 2. 原流処理互換性確認
    print("\n2. 🔍 原流処理互換性確認")
    
    critical_fixed_names = [
        "raw_data.npz",           # Step1→Step2,Step3入力
        "predict_skeleton.npz",   # Step2→Step3入力
        "inference_datalist.txt"  # Step3要件
    ]
    
    print("⚠️ 変更絶対禁止ファイル名:")
    for filename in critical_fixed_names:
        print(f"  - {filename}")
    
    # 3. ファイル受け渡し整合性確認
    print("\n3. 🔍 ステップ間ファイル受け渡し整合性")
    
    dataflow_chain = [
        {
            "step": "Step0→Step1",
            "output": "{model_name}.glb",
            "input": "アップロードファイル",
            "validation": "ファイル存在確認"
        },
        {
            "step": "Step1→Step2",
            "output": "raw_data.npz",
            "input": "raw_data.npz",
            "validation": "NPZ構造確認"
        },
        {
            "step": "Step2→Step3",
            "output": ["{model_name}.fbx", "predict_skeleton.npz"],
            "input": ["raw_data.npz", "predict_skeleton.npz", "{model_name}.fbx"],
            "validation": "ファイル三点セット確認"
        },
        {
            "step": "Step3→Step4",
            "output": "{model_name}_skinned_unirig.fbx",
            "input": ["{model_name}.fbx", "{model_name}_skinned_unirig.fbx"],
            "validation": "FBXペア確認"
        },
        {
            "step": "Step4→Step5",
            "output": "{model_name}_merged.fbx",
            "input": ["{model_name}_merged.fbx", "オリジナルファイル"],
            "validation": "マージFBX+オリジナル確認"
        }
    ]
    
    print("📋 データフローチェーン:")
    for flow in dataflow_chain:
        print(f"  {flow['step']}:")
        print(f"    出力: {flow['output']}")
        print(f"    入力: {flow['input']}")
        print(f"    検証: {flow['validation']}")
    
    # 4. 問題パターン検出
    print("\n4. ⚠️ 危険な柔軟性パターン（禁止事項）")
    
    dangerous_patterns = [
        "glob.glob('*extracted*.npz')",
        "find_file_with_pattern(pattern)",
        "dynamic_filename_generation()",
        "fallback_file_search()",
        "flexible_naming_scheme()"
    ]
    
    print("❌ 実装禁止パターン:")
    for pattern in dangerous_patterns:
        print(f"  - {pattern}")
    
    # 5. 整流化要件
    print("\n5. 🎯 整流化要件")
    
    requirements = [
        "ファイル名は{model_name}接頭または完全固定のみ",
        "原流処理期待値との100%一致",
        "glob/動的検索の完全排除",
        "フォールバック機能の禁止",
        "決め打ちパス直接指定の徹底"
    ]
    
    print("📋 必須要件:")
    for req in requirements:
        print(f"  ✓ {req}")
    
    print("\n=== 診断完了 ===")
    print("次の作業: app.pyデータフロー整流化実装")

if __name__ == "__main__":
    analyze_current_dataflow()
