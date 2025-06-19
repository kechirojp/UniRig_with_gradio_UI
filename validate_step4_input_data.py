#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Step4入力データ検証スクリプト

Step4に渡されている入力ファイルが results/ ディレクトリの正しいファイルと
同じデータ（サイズ・内容）なのかを詳細に検証します。

実行方法:
    cd /app
    python validate_step4_input_data.py
"""

import sys
import os
from pathlib import Path

# プロジェクトルートを追加
sys.path.insert(0, '/app')

def validate_step4_input_data():
    """Step4入力データの詳細検証"""
    print("\n=== Step4入力データ検証開始 ===")
    
    # 検証対象パス
    results_dir = Path("/app/results")
    pipeline_dir = Path("/app/pipeline_work/bird")
    
    # results/ディレクトリのファイル
    results_skinned_fbx = results_dir / "skinned_model.fbx"
    results_predict_skin = results_dir / "predict_skin.npz"
    
    # Step3出力（Step4入力として使用される）
    step3_skinned_fbx = pipeline_dir / "03_skinning" / "bird_skinned.fbx"
    step3_skinning_npz = pipeline_dir / "03_skinning" / "bird_skinning.npz"
    
    # Step2出力（Step4入力として使用される）
    step2_skeleton_fbx = pipeline_dir / "02_skeleton" / "bird_skeleton.fbx"
    step2_skeleton_npz = pipeline_dir / "02_skeleton" / "bird_skeleton.npz"
    
    # Step4出力
    step4_merged_fbx = pipeline_dir / "04_merge" / "bird_merged.fbx"
    
    print("\n=== ファイル存在確認 ===")
    files_to_check = [
        ("results/skinned_model.fbx", results_skinned_fbx),
        ("results/predict_skin.npz", results_predict_skin),
        ("Step3 skinned FBX", step3_skinned_fbx),
        ("Step3 skinning NPZ", step3_skinning_npz),
        ("Step2 skeleton FBX", step2_skeleton_fbx),
        ("Step2 skeleton NPZ", step2_skeleton_npz),
        ("Step4 merged FBX", step4_merged_fbx)
    ]
    
    for name, file_path in files_to_check:
        if file_path.exists():
            size = file_path.stat().st_size
            print(f"✅ {name}: {file_path} ({size:,} bytes)")
        else:
            print(f"❌ {name}: {file_path} (存在しない)")
    
    print("\n=== サイズ比較検証 ===")
    
    # results/skinned_model.fbx vs Step3出力
    if results_skinned_fbx.exists() and step3_skinned_fbx.exists():
        results_size = results_skinned_fbx.stat().st_size
        step3_size = step3_skinned_fbx.stat().st_size
        print(f"FBXサイズ比較:")
        print(f"  results/skinned_model.fbx: {results_size:,} bytes")
        print(f"  Step3/bird_skinned.fbx:    {step3_size:,} bytes")
        if results_size == step3_size:
            print(f"  ✅ サイズ一致: Step3は正しいFBXを使用")
        else:
            print(f"  ❌ サイズ不一致: Step3が間違ったFBXを使用している可能性")
    
    # results/predict_skin.npz vs Step3出力
    if results_predict_skin.exists() and step3_skinning_npz.exists():
        results_npz_size = results_predict_skin.stat().st_size
        step3_npz_size = step3_skinning_npz.stat().st_size
        print(f"NPZサイズ比較:")
        print(f"  results/predict_skin.npz:  {results_npz_size:,} bytes")
        print(f"  Step3/bird_skinning.npz:   {step3_npz_size:,} bytes")
        if results_npz_size == step3_npz_size:
            print(f"  ✅ サイズ一致: Step3は正しいNPZを使用")
        else:
            print(f"  ❌ サイズ不一致: Step3が間違ったNPZを使用している可能性")
    
    print("\n=== Step4入力ファイル検証 ===")
    
    # Step4が実際に使用するファイルパスを模擬
    print("Step4が受け取るはずのファイル:")
    print(f"  source_fbx (skeleton): {step2_skeleton_fbx}")
    print(f"  target_fbx (skinned):  {step3_skinned_fbx}")
    
    if step2_skeleton_fbx.exists() and step3_skinned_fbx.exists():
        skeleton_size = step2_skeleton_fbx.stat().st_size
        skinned_size = step3_skinned_fbx.stat().st_size
        print(f"\nStep4入力ファイルサイズ:")
        print(f"  スケルトンFBX: {skeleton_size:,} bytes")
        print(f"  スキニングFBX: {skinned_size:,} bytes")
        
        # resultsと比較
        if results_skinned_fbx.exists():
            results_size = results_skinned_fbx.stat().st_size
            if skinned_size == results_size:
                print(f"  ✅ Step4は正しいスキニングFBXを受け取っている")
            else:
                print(f"  ❌ Step4は間違ったスキニングFBXを受け取っている")
                print(f"      期待サイズ: {results_size:,} bytes")
                print(f"      実際サイズ: {skinned_size:,} bytes")
    
    print("\n=== Step4出力検証 ===")
    if step4_merged_fbx.exists():
        merged_size = step4_merged_fbx.stat().st_size
        print(f"Step4出力ファイル: {step4_merged_fbx}")
        print(f"  サイズ: {merged_size:,} bytes")
        
        # マージ前後のサイズ比較
        if step2_skeleton_fbx.exists() and step3_skinned_fbx.exists():
            skeleton_size = step2_skeleton_fbx.stat().st_size
            skinned_size = step3_skinned_fbx.stat().st_size
            total_input_size = skeleton_size + skinned_size
            
            print(f"\nサイズ分析:")
            print(f"  入力合計: {total_input_size:,} bytes")
            print(f"  出力:     {merged_size:,} bytes")
            
            if merged_size < (total_input_size * 0.1):
                print(f"  ❌ 警告: 出力サイズが異常に小さい（マージ失敗の可能性）")
            elif merged_size > (total_input_size * 1.5):
                print(f"  ❌ 警告: 出力サイズが異常に大きい")
            else:
                print(f"  ✅ 出力サイズは妥当な範囲")
    
    print("\n=== バイナリ比較（一部）===")
    
    # ファイルの先頭バイト比較で同一性確認
    if results_skinned_fbx.exists() and step3_skinned_fbx.exists():
        try:
            with open(results_skinned_fbx, 'rb') as f1, open(step3_skinned_fbx, 'rb') as f2:
                header1 = f1.read(1024)  # 最初の1KB
                header2 = f2.read(1024)
                
            if header1 == header2:
                print(f"✅ FBXファイルヘッダー一致: Step3は正確にコピーしている")
            else:
                print(f"❌ FBXファイルヘッダー不一致: Step3のコピーが不正確")
        except Exception as e:
            print(f"❌ バイナリ比較エラー: {e}")
    
    print("\n=== 結論 ===")
    
    # 最終判定
    issues = []
    
    if not step3_skinned_fbx.exists():
        issues.append("Step3出力FBXが存在しない")
    elif results_skinned_fbx.exists():
        if results_skinned_fbx.stat().st_size != step3_skinned_fbx.stat().st_size:
            issues.append("Step3が間違ったFBXをコピーしている")
    
    if not step4_merged_fbx.exists():
        issues.append("Step4出力が存在しない")
    elif step4_merged_fbx.stat().st_size < 100000:  # 100KB未満
        issues.append("Step4出力サイズが異常に小さい")
    
    if issues:
        print("❌ 検出された問題:")
        for issue in issues:
            print(f"  - {issue}")
        print("\n💡 推奨アクション:")
        print("  1. Step3の出力ファイル検出ロジックを確認")
        print("  2. Step4のマージ処理を詳細確認")
        print("  3. src.inference.mergeの実行ログを確認")
    else:
        print("✅ データフローは正常に見えますが、詳細なエラーログを確認してください")

if __name__ == "__main__":
    validate_step4_input_data()
