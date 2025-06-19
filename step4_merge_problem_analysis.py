#!/usr/bin/env python3
"""
Step4のマージ処理問題の核心分析

transfer関数の動作フロー分析:
1. source(skeleton.fbx)からアーマチュアを読み込み
2. process_mesh()でBlenderシーンからメッシュ情報取得
3. get_skin()でBlenderシーンからスキン情報取得
4. merge()でtarget(skinned.fbx)を新たに読み込み

問題: process_mesh()とget_skin()がsource(skeleton)のデータを使用している
解決: target(skinned)のデータを確実に使用する必要がある
"""

import sys
import os
from pathlib import Path

def analyze_step4_merge_logic():
    """Step4マージロジックの問題分析"""
    
    print("🔍 Step4 マージロジック問題分析")
    print("=" * 50)
    
    print("📋 transfer関数の動作フロー:")
    print("1. source(skeleton.fbx) → Blenderに読み込み → アーマチュア取得")
    print("2. process_mesh() → 現在のBlenderシーンからメッシュ取得")
    print("3. get_skin() → 現在のBlenderシーンからスキン取得")
    print("4. merge(target=skinned.fbx) → targetを新たに読み込み")
    print()
    
    print("🚨 問題発見:")
    print("- Step 2, 3でsource(skeleton)のデータを使用")
    print("- target(skinned)のスキンウェイト情報が無視される")
    print("- 結果: スキニング処理結果が反映されない")
    print()
    
    # 実際のファイルサイズで確認
    skeleton_file = "/app/pipeline_work/bird/02_skeleton/skeleton.fbx"
    skinned_file = "/app/pipeline_work/bird/03_skinning/bird_skinned.fbx"
    merged_file = "/app/pipeline_work/bird/04_merge/bird_merged.fbx"
    
    print("📊 ファイルサイズ比較:")
    
    if os.path.exists(skeleton_file):
        size = os.path.getsize(skeleton_file)
        print(f"  Skeleton FBX: {size:,} bytes")
    
    if os.path.exists(skinned_file):
        size = os.path.getsize(skinned_file)
        print(f"  Skinned FBX:  {size:,} bytes ← スキンウェイト含む")
    
    if os.path.exists(merged_file):
        size = os.path.getsize(merged_file)
        print(f"  Merged FBX:   {size:,} bytes")
    
    print()
    
    print("🔧 解決方法:")
    print("Option 1: transfer関数を修正")
    print("  - sourceとtargetの役割を逆転")
    print("  - target(skinned)からメッシュ・スキン情報取得")
    print("  - source(skeleton)からアーマチュア情報のみ取得")
    print()
    
    print("Option 2: Step4の呼び出し方を修正")
    print("  - source=skinned.fbx, target=skeleton.fbx として呼び出し")
    print("  - 現在のtransfer関数ロジックに合わせる")
    print()
    
    print("🎯 推奨解決策: Option 2 (呼び出し方修正)")
    print("  理由: 既存のmerge.pyロジックを変更せず安全")
    print("  変更箇所: step4_merge.pyの呼び出し部分のみ")
    
    return True

def propose_step4_fix():
    """Step4修正提案"""
    
    print("\n" + "=" * 50)
    print("🛠️  Step4修正提案")
    print("=" * 50)
    
    print("📄 現在のStep4呼び出し:")
    print("  source = skeleton.fbx")
    print("  target = skinned.fbx")
    print("  → skeleton.fbxからメッシュ・スキン取得（問題）")
    print()
    
    print("🔧 修正後のStep4呼び出し:")
    print("  source = skinned.fbx   ← スキンウェイト情報源")
    print("  target = skeleton.fbx  ← アーマチュア情報源")
    print("  → skinned.fbxからメッシュ・スキン取得（正解）")
    print()
    
    print("📝 実装手順:")
    print("1. /app/step_modules/step4_merge.py を修正")
    print("2. _execute_merge_with_transfer() の引数順序変更")
    print("3. source=skinned_fbx, target=skeleton_fbx に変更")
    print("4. 動作確認")
    
    return True

if __name__ == "__main__":
    analyze_step4_merge_logic()
    propose_step4_fix()
    print("\n✅ Step4問題分析完了")
