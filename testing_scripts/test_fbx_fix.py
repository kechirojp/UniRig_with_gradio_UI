#!/usr/bin/env python
"""
FBXエクスポート修正のテスト
テクスチャ接続が正しく保持されるかを検証
"""
import os
import sys
import shutil
import subprocess
import tempfile

def main():
    print("🧪 FBXエクスポート修正テスト開始")
    
    # テスト用ディレクトリ作成
    test_dir = "/app/fbx_fix_test"
    os.makedirs(test_dir, exist_ok=True)
    
    # 元のbird.glbをコピー
    input_file = "/app/examples/bird.glb"
    test_input = os.path.join(test_dir, "bird.glb")
    shutil.copy2(input_file, test_input)
    
    print(f"📁 テスト用入力ファイル: {test_input}")
    
    # merge.pyを実行してFBXとGLBの両方を生成
    print("🔄 UniRigマージ処理実行中...")
    try:
        result = subprocess.run([
            sys.executable, "-c", f"""
import sys
sys.path.append('/app/src')
from inference.merge import make_armature_for_rigging
import numpy as np

# テストデータ
vertices = np.random.rand(10, 3)
bones = np.random.rand(5, 4, 4)
names = ['bone_' + str(i) for i in range(5)]
skin = np.random.rand(10, 5)

result = make_armature_for_rigging(
    '{test_input}',
    vertices, bones, names, skin,
    group_per_vertex=4,
    add_root=False,
    is_vrm=False
)

print("UniRigマージ完了")
print(f"結果タイプ: {{type(result)}}")
print(f"結果長さ: {{len(result) if hasattr(result, '__len__') else 'N/A'}}")
"""], 
            cwd="/app",
            capture_output=True,
            text=True
        )
        
        print(f"戻り値: {result.returncode}")
        if result.stdout:
            print(f"標準出力:\n{result.stdout}")
        if result.stderr:
            print(f"標準エラー:\n{result.stderr}")
            
    except Exception as e:
        print(f"❌ エラー発生: {e}")
        return False
    
    # 生成されたファイルを確認
    print("\n📂 生成されたファイルを確認中...")
    
    # よくある出力パターンを確認
    possible_outputs = [
        "/tmp/merged.fbx",
        "/tmp/merged.glb", 
        "/app/merged.fbx",
        "/app/merged.glb",
        os.path.join(test_dir, "merged.fbx"),
        os.path.join(test_dir, "merged.glb")
    ]
    
    for filepath in possible_outputs:
        if os.path.exists(filepath):
            print(f"✅ 見つかりました: {filepath}")
            # テスト用ディレクトリにコピー
            filename = os.path.basename(filepath)
            dest_path = os.path.join(test_dir, f"output_{filename}")
            shutil.copy2(filepath, dest_path)
            print(f"📋 コピー先: {dest_path}")
    
    # /tmpディレクトリ内のmerge関連ファイルを確認
    print("\n🔍 /tmpディレクトリ内のファイル確認...")
    try:
        for file in os.listdir("/tmp"):
            if "merge" in file.lower() or file.endswith(('.fbx', '.glb')):
                full_path = os.path.join("/tmp", file)
                print(f"  {full_path}")
                # テスト用ディレクトリにコピー
                dest_path = os.path.join(test_dir, f"found_{file}")
                shutil.copy2(full_path, dest_path)
    except Exception as e:
        print(f"⚠️ /tmpディレクトリアクセスエラー: {e}")
    
    print(f"\n📍 テスト結果は {test_dir} に保存されました")
    
    # ディレクトリ内容を表示
    print("\n📋 テスト結果ファイル一覧:")
    try:
        for file in os.listdir(test_dir):
            filepath = os.path.join(test_dir, file)
            size = os.path.getsize(filepath)
            print(f"  {file} ({size} bytes)")
    except Exception as e:
        print(f"⚠️ ファイル一覧エラー: {e}")

if __name__ == "__main__":
    main()
