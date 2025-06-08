#!/usr/bin/env python3
"""
Step4シンプル検証 - 大元フロー直接実行
"""

import os
import subprocess
import sys
from pathlib import Path

def test_direct_merge_sh():
    """merge.shを直接実行してStep4の動作を確認"""
    
    print("🧪 Step4大元フロー（merge.sh）直接実行テスト")
    
    # 現在利用可能なデータ
    step3_skinned_fbx = "/app/pipeline_work/03_skinning/bird_skinned.fbx"
    original_model = "/app/examples/skeleton/bird.fbx"  # FBX形式で試行 
    output_dir = Path("/app/test_step4_direct")
    output_dir.mkdir(exist_ok=True)
    output_fbx = output_dir / "bird_final.fbx"
    
    # 入力データ確認
    print("\n📋 入力データ確認:")
    print(f"  - リギング済みFBX（target）: {step3_skinned_fbx}")
    print(f"    存在: {os.path.exists(step3_skinned_fbx)}")
    if os.path.exists(step3_skinned_fbx):
        print(f"    サイズ: {os.path.getsize(step3_skinned_fbx)} bytes")
    
    print(f"  - オリジナルモデル（source）: {original_model}")
    print(f"    存在: {os.path.exists(original_model)}")
    if os.path.exists(original_model):
        print(f"    サイズ: {os.path.getsize(original_model)} bytes")
    
    # merge.sh実行
    print("\n🚀 merge.sh実行:")
    merge_script = "/app/launch/inference/merge.sh"
    cmd = [
        "bash", merge_script,
        "--source", original_model,      # オリジナルモデル（テクスチャ付き）
        "--target", step3_skinned_fbx,   # リギング済みモデル（テクスチャなし）
        "--output", str(output_fbx),     # 最終出力ファイル
        "--require_suffix", "obj,fbx,FBX,dae,glb,gltf,vrm"
    ]
    
    print(f"実行コマンド: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10分タイムアウト
            cwd="/app"
        )
        
        print(f"\n📊 実行結果:")
        print(f"  戻り値: {result.returncode}")
        print(f"  標準出力:\n{result.stdout}")
        if result.stderr:
            print(f"  標準エラー:\n{result.stderr}")
        
        # 出力ファイル確認
        if output_fbx.exists():
            file_size = output_fbx.stat().st_size
            print(f"\n✅ 出力FBX生成成功:")
            print(f"  - ファイル: {output_fbx}")
            print(f"  - サイズ: {file_size} bytes ({file_size/1024:.1f}KB)")
            
            # 品質評価
            if file_size > 100000:  # 100KB以上
                print(f"  - 品質評価: 良好")
            elif file_size > 20000:  # 20KB以上
                print(f"  - 品質評価: 普通")
            else:
                print(f"  - 品質評価: 問題あり（小さすぎ）")
        else:
            print(f"\n❌ 出力FBXファイルが生成されませんでした")
            
    except subprocess.TimeoutExpired:
        print("\n❌ 実行タイムアウト（10分超過）")
    except Exception as e:
        print(f"\n❌ 実行エラー: {e}")

if __name__ == "__main__":
    test_direct_merge_sh()
