#!/usr/bin/env python3
"""
Step5 True FBX Merge の結果を詳細分析
問題: UVマップとマテリアルの転送が失敗している
"""

import subprocess
from pathlib import Path

def analyze_fbx_file(fbx_path: str, name: str):
    """FBXファイルの詳細分析"""
    
    print(f"\n🔍 {name} の詳細分析")
    print("=" * 50)
    
    blender_script = f'''
import bpy

# シーンクリア
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

print(f"=== {name} の内容分析 ===")

# FBXインポート
bpy.ops.import_scene.fbx(filepath="{fbx_path}")

# メッシュオブジェクトの詳細分析
meshes = [obj for obj in bpy.data.objects if obj.type == 'MESH']
print(f"メッシュ数: {{len(meshes)}}")

for mesh in meshes:
    print(f"\\nメッシュ: {{mesh.name}}")
    print(f"  頂点数: {{len(mesh.data.vertices)}}")
    print(f"  面数: {{len(mesh.data.polygons)}}")
    
    # UVマップ詳細
    uv_layers = mesh.data.uv_layers
    print(f"  UVレイヤー数: {{len(uv_layers)}}")
    for i, uv_layer in enumerate(uv_layers):
        print(f"    UV[{{i}}]: {{uv_layer.name}}")
    
    # マテリアル詳細
    materials = mesh.data.materials
    print(f"  マテリアル数: {{len(materials)}}")
    for i, material in enumerate(materials):
        if material:
            print(f"    Material[{{i}}]: {{material.name}}")
            
            # マテリアルノード詳細
            if material.use_nodes and material.node_tree:
                nodes = material.node_tree.nodes
                texture_nodes = [n for n in nodes if n.type == 'TEX_IMAGE']
                print(f"      テクスチャノード数: {{len(texture_nodes)}}")
                for j, tex_node in enumerate(texture_nodes):
                    if tex_node.image:
                        print(f"        テクスチャ[{{j}}]: {{tex_node.image.name}}")
                    else:
                        print(f"        テクスチャ[{{j}}]: <画像なし>")
        else:
            print(f"    Material[{{i}}]: <None>")

# 全体のマテリアルとテクスチャ
print(f"\\n=== 全体統計 ===")
materials = list(bpy.data.materials)
images = [img for img in bpy.data.images if img.name not in ['Render Result', 'Viewer Node']]

print(f"総マテリアル数: {{len(materials)}}")
print(f"総画像数: {{len(images)}}")

if materials:
    print("マテリアル一覧:")
    for mat in materials:
        print(f"  - {{mat.name}}")

if images:
    print("画像一覧:")
    for img in images:
        print(f"  - {{img.name}} ({{img.size[0]}}x{{img.size[1]}})")
'''
    
    cmd = ["blender", "--background", "--python-expr", blender_script]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    
    if result.returncode == 0:
        print(result.stdout)
    else:
        print(f"❌ 分析失敗: {result.stderr}")

def main():
    """メイン分析実行"""
    
    base_dir = Path("/app/test_step5_true_fbx_merge")
    
    # 各ファイルを詳細分析
    files_to_analyze = [
        ("test_bird_with_data.fbx", "オリジナルデータ保持FBX"),
        ("test_bird_stripped.fbx", "ストリップ済みFBX"),
        ("test_bird_merged_final.fbx", "統合後FBX")
    ]
    
    for filename, description in files_to_analyze:
        filepath = base_dir / filename
        if filepath.exists():
            analyze_fbx_file(str(filepath), description)
        else:
            print(f"❌ ファイルが存在しません: {filepath}")
    
    # ファイルサイズ比較
    print(f"\n📊 ファイルサイズ比較")
    print("=" * 50)
    
    for filename, description in files_to_analyze:
        filepath = base_dir / filename
        if filepath.exists():
            size_mb = filepath.stat().st_size / (1024 * 1024)
            print(f"{description}: {size_mb:.2f}MB ({filepath.name})")

if __name__ == "__main__":
    main()
