#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Step4マージ処理の詳細デバッグスクリプト

src.inference.mergeの実際の処理内容と出力を詳細に確認します。
エラーハンドリングではなく、実際の処理結果を検証します。

実行方法:
    cd /app
    python debug_step4_merge_process.py
"""

import sys
import os
import subprocess
import tempfile
from pathlib import Path

# プロジェクトルートを追加
sys.path.insert(0, '/app')

def debug_step4_merge_process():
    """Step4マージ処理の詳細デバッグ"""
    print("\n=== Step4マージ処理詳細デバッグ ===")
    
    # 入力ファイル
    skeleton_fbx = Path("/app/pipeline_work/bird/02_skeleton/bird_skeleton.fbx")
    skinned_fbx = Path("/app/pipeline_work/bird/03_skinning/bird_skinned.fbx")
    
    # 一時出力ファイル
    temp_output = Path("/tmp/debug_merge_output.fbx")
    
    print(f"\n=== 入力ファイル確認 ===")
    print(f"スケルトンFBX: {skeleton_fbx} ({skeleton_fbx.stat().st_size:,} bytes)")
    print(f"スキニングFBX: {skinned_fbx} ({skinned_fbx.stat().st_size:,} bytes)")
    
    # src.inference.mergeを直接実行してみる
    print(f"\n=== src.inference.merge直接実行 ===")
    
    cmd = [
        sys.executable, "-m", "src.inference.merge",
        "--require_suffix", "obj,fbx,FBX,dae,glb,gltf,vrm",
        "--num_runs", "1",
        "--id", "0",
        "--source", str(skeleton_fbx),
        "--target", str(skinned_fbx),
        "--output", str(temp_output)
    ]
    
    print(f"実行コマンド: {' '.join(cmd)}")
    
    try:
        # 詳細な出力を取得
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd="/app"
        )
        
        print(f"\n=== 実行結果 ===")
        print(f"リターンコード: {result.returncode}")
        print(f"実行時間: 約5秒以内")
        
        print(f"\n=== 標準出力 ===")
        if result.stdout:
            print(result.stdout)
        else:
            print("(標準出力なし)")
        
        print(f"\n=== 標準エラー ===")
        if result.stderr:
            print(result.stderr)
        else:
            print("(標準エラーなし)")
        
        # 出力ファイル確認
        print(f"\n=== 出力ファイル確認 ===")
        if temp_output.exists():
            output_size = temp_output.stat().st_size
            print(f"✅ 出力ファイル生成: {temp_output}")
            print(f"   サイズ: {output_size:,} bytes")
            
            # パイプライン出力と比較
            pipeline_output = Path("/app/pipeline_work/bird/04_merge/bird_merged.fbx")
            if pipeline_output.exists():
                pipeline_size = pipeline_output.stat().st_size
                print(f"\nパイプライン出力との比較:")
                print(f"  直接実行:     {output_size:,} bytes")
                print(f"  パイプライン: {pipeline_size:,} bytes")
                
                if output_size == pipeline_size:
                    print(f"  ✅ サイズ一致: パイプラインは正常動作")
                else:
                    print(f"  ❌ サイズ不一致: パイプラインに問題あり")
        else:
            print(f"❌ 出力ファイル未生成: マージ処理が失敗")
        
        # リターンコード分析
        if result.returncode == 0:
            print(f"\n✅ src.inference.merge実行成功")
        else:
            print(f"\n❌ src.inference.merge実行失敗 (exit code: {result.returncode})")
    
    except subprocess.TimeoutExpired:
        print(f"❌ タイムアウト: マージ処理が5分以内に完了しませんでした")
    except Exception as e:
        print(f"❌ 実行エラー: {e}")
    
    # FBXファイル内容の簡易確認
    print(f"\n=== FBX内容簡易確認 ===")
    
    def check_fbx_content(fbx_path, name):
        """FBXファイルの内容を簡易確認"""
        if not fbx_path.exists():
            print(f"❌ {name}: ファイル不存在")
            return
        
        try:
            with open(fbx_path, 'rb') as f:
                content = f.read(2048)  # 最初の2KB
                
            # FBXヘッダー確認
            if content.startswith(b'Kaydara FBX Binary'):
                print(f"✅ {name}: 有効なバイナリFBX")
            elif b'FBX' in content[:100]:
                print(f"⚠️ {name}: ASCII FBX (推奨はバイナリ)")
            else:
                print(f"❌ {name}: 無効なFBXファイル")
                
            # サイズベース判定
            size = fbx_path.stat().st_size
            if size > 1000000:  # 1MB以上
                print(f"   サイズ: {size:,} bytes (大きめ - モデルデータ含有)")
            elif size > 100000:  # 100KB以上
                print(f"   サイズ: {size:,} bytes (中程度)")
            else:
                print(f"   サイズ: {size:,} bytes (小さめ - データ不足の可能性)")
                
        except Exception as e:
            print(f"❌ {name}: 読み取りエラー - {e}")
    
    check_fbx_content(skeleton_fbx, "スケルトンFBX")
    check_fbx_content(skinned_fbx, "スキニングFBX")
    if temp_output.exists():
        check_fbx_content(temp_output, "マージ出力FBX")
    
    # クリーンアップ
    if temp_output.exists():
        temp_output.unlink()
        print(f"\n🧹 一時ファイル削除: {temp_output}")
    
    print(f"\n=== デバッグ結論 ===")
    print("1. src.inference.mergeが正常に実行されているか？")
    print("2. 出力ファイルのサイズは妥当か？")
    print("3. パイプライン版と直接実行版で結果が同じか？")
    print("4. エラーメッセージに隠れた問題があるか？")

if __name__ == "__main__":
    debug_step4_merge_process()
