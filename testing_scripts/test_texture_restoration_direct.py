#!/usr/bin/env python3
"""
テクスチャ復元機能の直接テスト
TexturePreservationSystemを直接使用してテクスチャ適用をテスト
"""

import sys
import os
import json
import shutil
from pathlib import Path

# Blenderパスを追加
sys.path.append('/usr/local/blender')

# TexturePreservationSystemをインポート
sys.path.append('/app')

def test_texture_restoration_direct():
    """テクスチャ復元機能を直接テスト"""
    
    # 設定
    test_files_dir = "/app/examples"
    texture_output_dir = "/tmp/texture_test_output"
    
    print("=== テクスチャ復元機能直接テスト開始 ===")
    
    # 1. 利用可能なテストファイルを確認
    print("\n1. 利用可能なテストファイルを確認中...")
    if not os.path.exists(test_files_dir):
        print(f"エラー: テストファイルディレクトリが見つかりません: {test_files_dir}")
        return False
    
    # GLBファイルを探す
    glb_files = [f for f in os.listdir(test_files_dir) if f.endswith('.glb')]
    if not glb_files:
        print("エラー: GLBファイルが見つかりません")
        return False
    
    test_glb_file = os.path.join(test_files_dir, glb_files[0])
    print(f"テストファイル: {test_glb_file}")
    
    # 2. 既存のテクスチャメタデータが存在するか確認
    print("\n2. 既存のテクスチャメタデータを確認中...")
    metadata_path = os.path.join(texture_output_dir, "texture_metadata.json")
    
    if not os.path.exists(metadata_path):
        print("テクスチャメタデータが見つかりません。まず抽出を実行します...")
        return False
    
    # 3. メタデータを読み込み
    print("\n3. テクスチャメタデータを読み込み中...")
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            texture_metadata = json.load(f)
        
        print(f"メタデータ読み込み成功:")
        print(f"  - テクスチャ数: {len(texture_metadata.get('textures', {}))}")
        print(f"  - マテリアル数: {len(texture_metadata.get('materials', {}))}")
        print(f"  - メッシュ-マテリアル対応数: {len(texture_metadata.get('mesh_materials', {}))}")
        
    except Exception as e:
        print(f"メタデータ読み込みエラー: {e}")
        return False
    
    # 4. リギング済みFBXファイルを作成（テスト用のダミー）
    print("\n4. テスト用リギング済みFBXファイルを準備中...")
    rigged_fbx_path = os.path.join(texture_output_dir, "test_rigged_model.fbx")
    
    # 元のGLBファイルをFBXとしてコピー（実際のリギング処理の代わり）
    try:
        shutil.copy2(test_glb_file, rigged_fbx_path)
        print(f"テスト用FBXファイル作成: {rigged_fbx_path}")
    except Exception as e:
        print(f"テスト用FBXファイル作成失敗: {e}")
        return False
    
    # 5. TexturePreservationSystemを直接使用してテクスチャ適用をテスト
    print("\n5. TexturePreservationSystemでテクスチャ適用をテスト中...")
    
    try:
        # サブプロセスでBlenderベースの処理を実行
        import subprocess
        
        # テクスチャ適用スクリプトを作成
        apply_script_path = os.path.join(texture_output_dir, "apply_textures.py")
        
        apply_script_content = f'''
import sys
import os
import bpy

# パスを追加
sys.path.append('/app')

try:
    from texture_preservation_system import TexturePreservationSystem
    
    # TexturePreservationSystemインスタンス作成
    texture_system = TexturePreservationSystem()
    
    # テクスチャ適用実行
    rigged_fbx_path = "{rigged_fbx_path}"
    texture_data_dir = "{texture_output_dir}"
    output_fbx_path = "{os.path.join(texture_output_dir, 'final_textured_model.fbx')}"
    
    print("テクスチャ適用開始...")
    print(f"入力FBX: {{rigged_fbx_path}}")
    print(f"テクスチャディレクトリ: {{texture_data_dir}}")
    print(f"出力FBX: {{output_fbx_path}}")
    
    # テクスチャ適用実行
    success = texture_system.apply_texture_to_rigged_model(
        rigged_fbx_path, texture_data_dir, output_fbx_path
    )
    
    if success:
        print("✅ テクスチャ適用成功")
        print(f"出力ファイル: {{output_fbx_path}}")
    else:
        print("❌ テクスチャ適用失敗")
    
    # 結果をファイルに出力
    result_file = "{os.path.join(texture_output_dir, 'apply_result.txt')}"
    with open(result_file, 'w') as f:
        f.write(f"success={{success}}\\n")
        f.write(f"output_file={{output_fbx_path}}\\n")

except Exception as e:
    print(f"エラー: {{e}}")
    import traceback
    traceback.print_exc()
    
    # エラー結果をファイルに出力
    result_file = "{os.path.join(texture_output_dir, 'apply_result.txt')}"
    with open(result_file, 'w') as f:
        f.write(f"success=False\\n")
        f.write(f"error={{str(e)}}\\n")
'''
        
        with open(apply_script_path, 'w') as f:
            f.write(apply_script_content)
        
        print(f"テクスチャ適用スクリプト作成: {apply_script_path}")
        
        # Blenderでスクリプトを実行
        cmd = [
            "/usr/local/bin/blender",
            "--background",
            "--python", apply_script_path
        ]
        
        print(f"Blenderサブプロセス実行: {' '.join(cmd[:3])} ...")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5分のタイムアウト
            cwd="/app"
        )
        
        print(f"サブプロセス終了コード: {result.returncode}")
        if result.stdout:
            print(f"標準出力: {result.stdout}")
        if result.stderr:
            print(f"標準エラー: {result.stderr}")
        
        # 結果ファイルを確認
        result_file = os.path.join(texture_output_dir, 'apply_result.txt')
        if os.path.exists(result_file):
            with open(result_file, 'r') as f:
                result_content = f.read()
            print(f"処理結果: {result_content}")
            
            # 成功判定
            if "success=True" in result_content:
                # 出力ファイルの存在確認
                output_file = os.path.join(texture_output_dir, "final_textured_model.fbx")
                if os.path.exists(output_file):
                    file_size = os.path.getsize(output_file)
                    print(f"✅ 出力ファイル生成成功: {output_file} ({file_size} bytes)")
                    return True
                else:
                    print("⚠️ 処理は成功したが出力ファイルが見つかりません")
                    return False
            else:
                print("❌ テクスチャ適用処理が失敗しました")
                return False
        else:
            print("⚠️ 結果ファイルが生成されませんでした")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ テクスチャ適用処理がタイムアウトしました")
        return False
    except Exception as e:
        print(f"❌ テクスチャ適用処理エラー: {e}")
        return False

if __name__ == "__main__":
    print("テクスチャ復元機能直接テスト開始")
    
    # テクスチャ復元テスト実行
    success = test_texture_restoration_direct()
    
    if success:
        print("\n🎉 テクスチャ復元機能直接テスト成功！")
        print("テクスチャ保存・復元システムは正常に動作しています。")
    else:
        print("\n❌ テクスチャ復元機能直接テストに問題が発生しました。")
        print("ログを確認して問題を調査してください。")
    
    exit(0 if success else 1)
