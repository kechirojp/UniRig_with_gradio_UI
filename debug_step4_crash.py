#!/usr/bin/env python3
"""
Step 4 SIGSEGVクラッシュ調査用デバッグスクリプト
==============================================

目的:
- Step 4のマージ処理でSIGSEGV（-11）が発生する原因を特定
- どの処理段階でクラッシュしているかを詳細に調査
- 出力ファイルは生成されているため、Blender終了時の問題と推測

調査ポイント:
1. Blenderプロセスの初期化
2. ファイル読み込み処理
3. KDTree処理
4. マージ処理
5. FBX出力処理
6. Blender終了処理
"""

import sys
import os
import subprocess
import traceback
from pathlib import Path

def test_step4_components():
    """Step 4の各コンポーネントを段階的にテスト"""
    
    print("🔍 Step 4 SIGSEGVクラッシュ調査開始")
    print("=" * 50)
    
    # テスト用パラメータ
    model_name = "bird"
    base_dir = Path("/app/pipeline_work") / model_name
    
    skeleton_fbx = base_dir / "02_skeleton" / f"{model_name}.fbx"
    skinned_fbx = base_dir / "03_skinning" / f"{model_name}_skinned.fbx"
    original_file = "/app/input.glb"  # オリジナルファイル
    output_dir = base_dir / "04_merge"
    
    print(f"📁 入力ファイル確認:")
    print(f"   スケルトン: {skeleton_fbx} ({'存在' if skeleton_fbx.exists() else '不存在'})")
    print(f"   スキニング: {skinned_fbx} ({'存在' if skinned_fbx.exists() else '不存在'})")
    print(f"   オリジナル: {original_file} ({'存在' if Path(original_file).exists() else '不存在'})")
    print(f"   出力Dir: {output_dir}")
    
    # Step 1: merge.pyを直接実行してみる
    print("\n🧪 テスト1: merge.py直接実行")
    try:
        cmd = [
            "python", "-m", "src.inference.merge",
            "--source", str(skeleton_fbx),
            "--target", str(original_file),
            "--output", str(output_dir / f"{model_name}_debug_merged.fbx")
        ]
        
        print(f"実行コマンド: {' '.join(cmd)}")
        
        # プロセス実行（詳細ログ付き）
        result = subprocess.run(
            cmd,
            cwd="/app",
            capture_output=True,
            text=True,
            timeout=300
        )
        
        print(f"終了コード: {result.returncode}")
        print(f"標準出力:\n{result.stdout}")
        if result.stderr:
            print(f"標準エラー:\n{result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("❌ タイムアウト（300秒）")
    except Exception as e:
        print(f"❌ 実行エラー: {e}")
        traceback.print_exc()
    
    # Step 2: Blenderのヘルスチェック
    print("\n🧪 テスト2: Blenderヘルスチェック")
    try:
        result = subprocess.run(
            ["blender", "--version"],
            capture_output=True,
            text=True,
            timeout=30
        )
        print(f"Blenderバージョン: {result.stdout.strip()}")
        
        # 簡単なBlenderスクリプト実行テスト
        test_script = """
import bpy
print("Blender Python環境正常")
print(f"Blender version: {bpy.app.version}")
bpy.ops.wm.quit_blender()
"""
        
        result = subprocess.run(
            ["blender", "--background", "--python-expr", test_script],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"Blender Python実行結果: {result.returncode}")
        if result.stdout:
            print(f"出力: {result.stdout}")
        if result.stderr:
            print(f"エラー: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Blenderテストエラー: {e}")
    
    # Step 3: ファイルサイズ・内容確認
    print("\n🧪 テスト3: 生成されたマージファイル確認")
    output_file = output_dir / f"{model_name}_merged.fbx"
    if output_file.exists():
        size_mb = output_file.stat().st_size / (1024 * 1024)
        print(f"📄 {output_file}")
        print(f"   サイズ: {size_mb:.2f} MB")
        
        # ファイルのバイナリ署名確認（FBXファイルの妥当性）
        with open(output_file, 'rb') as f:
            header = f.read(32)
            print(f"   ヘッダー: {header[:16].hex()}")
            try:
                # FBXファイルの識別子確認
                if b'Kaydara' in header or b'FBX' in header:
                    print("   ✅ 有効なFBXファイル形式")
                else:
                    print("   ⚠️ FBXファイル形式が不明")
            except:
                print("   ⚠️ ヘッダー解析失敗")
    else:
        print("❌ マージ出力ファイルが見つかりません")
    
    # Step 4: メモリ使用量確認
    print("\n🧪 テスト4: システムリソース確認")
    try:
        result = subprocess.run(["free", "-h"], capture_output=True, text=True)
        print("メモリ使用量:")
        print(result.stdout)
        
        result = subprocess.run(["df", "-h", "/app"], capture_output=True, text=True)
        print("ディスク使用量:")
        print(result.stdout)
        
    except Exception as e:
        print(f"❌ リソース確認エラー: {e}")

if __name__ == "__main__":
    test_step4_components()
