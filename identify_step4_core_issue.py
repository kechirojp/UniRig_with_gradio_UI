#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Step4問題の核心を特定するスクリプト

RuntimeWarningの原因とマージ処理の実際の問題を特定します。

実行方法:
    cd /app
    python identify_step4_core_issue.py
"""

import sys
import os
from pathlib import Path

# プロジェクトルートを追加
sys.path.insert(0, '/app')

def identify_step4_core_issue():
    """Step4の核心的な問題を特定"""
    print("\n=== Step4問題の核心特定 ===")
    
    print("\n📋 発見された問題:")
    print("1. RuntimeWarning: invalid value encountered in divide")
    print("   → ウェイト正規化処理でゼロ除算が発生")
    print("2. vertex_group_reweight = vertex_group_reweight / vertex_group_reweight[..., :group_per_vertex].sum(axis=1)[...,None]")
    print("   → この行でゼロ除算エラー")
    
    print("\n🔍 問題の原因分析:")
    print("A. スキニングFBXのウェイトデータに問題がある可能性")
    print("B. スケルトンFBXとスキニングFBXの互換性問題")
    print("C. src.inference.mergeのウェイト処理ロジックに問題")
    
    # results/とStep3出力の実際のデータを確認
    results_skinned = Path("/app/results/skinned_model.fbx")
    step3_skinned = Path("/app/pipeline_work/bird/03_skinning/bird_skinned.fbx")
    
    print(f"\n=== データソース確認 ===")
    print(f"results/skinned_model.fbx: {results_skinned.stat().st_size:,} bytes")
    print(f"Step3/bird_skinned.fbx:    {step3_skinned.stat().st_size:,} bytes")
    
    # Step3が正しいデータを使用しているか最終確認
    if results_skinned.exists() and step3_skinned.exists():
        with open(results_skinned, 'rb') as f1, open(step3_skinned, 'rb') as f2:
            data1 = f1.read(10240)  # 最初の10KB
            data2 = f2.read(10240)
        
        if data1 == data2:
            print("✅ Step3は正確にresults/skinned_model.fbxをコピーしている")
        else:
            print("❌ Step3のコピーが不正確 - これが問題の原因")
            return
    
    print(f"\n=== 真の問題の特定 ===")
    
    # src.inference.mergeのソースコードを確認
    merge_script = Path("/app/src/inference/merge.py")
    if merge_script.exists():
        print("src.inference.merge.pyの問題箇所を確認中...")
        
        try:
            with open(merge_script, 'r') as f:
                lines = f.readlines()
            
            # 問題の行を検索
            problem_line_num = None
            for i, line in enumerate(lines):
                if "vertex_group_reweight / vertex_group_reweight" in line:
                    problem_line_num = i + 1
                    break
            
            if problem_line_num:
                print(f"❌ 問題箇所発見: merge.py:{problem_line_num}")
                print(f"   該当行: {lines[problem_line_num-1].strip()}")
                
                # 前後のコンテキスト
                start = max(0, problem_line_num - 5)
                end = min(len(lines), problem_line_num + 5)
                
                print(f"\n📋 問題箇所のコンテキスト (line {start+1}-{end}):")
                for i in range(start, end):
                    marker = ">>> " if i == problem_line_num - 1 else "    "
                    print(f"{marker}{i+1:3d}: {lines[i].rstrip()}")
        
        except Exception as e:
            print(f"❌ merge.py読み取りエラー: {e}")
    
    print(f"\n=== 推定される問題と解決策 ===")
    
    print("🎯 推定問題:")
    print("1. src.inference.mergeが期待するウェイトデータ形式と")
    print("   results/skinned_model.fbxの実際のデータ形式が不一致")
    print("2. スキニング処理(Step3)で生成されたウェイトに不正な値")
    print("   (NaN, Inf, 全て0など)が含まれている")
    print("3. ボーンの対応関係が正しく確立されていない")
    
    print(f"\n💡 解決のアプローチ:")
    print("A. results/skinned_model.fbxを直接Step4に渡す")
    print("   (Step3のコピー処理をスキップ)")
    print("B. src.inference.mergeのウェイト正規化処理を修正")
    print("   (ゼロ除算防止の条件分岐追加)")
    print("C. より詳細なウェイトデータ検証とログ出力")
    
    print(f"\n🔧 次のアクション:")
    print("1. results/skinned_model.fbxを直接Step4に渡すテスト")
    print("2. ウェイト正規化エラーの根本的修正")
    print("3. Step3の出力ファイル検出ロジック見直し")
    
    # 重要な発見の要約
    print(f"\n⚡ 重要な発見:")
    print("Step4は表面的には「成功」しているが、")
    print("実際にはウェイトの正規化処理で数値計算エラーが発生している。")
    print("これにより、出力されたFBXファイルのウェイトデータが")
    print("不正確または破損している可能性が高い。")

if __name__ == "__main__":
    identify_step4_core_issue()
