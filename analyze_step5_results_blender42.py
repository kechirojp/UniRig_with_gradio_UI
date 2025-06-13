#!/usr/bin/env python3
"""
Step5結果のBlender 4.2分析スクリプト
final.fbxが294KBと軽量すぎる問題を調査
"""

import subprocess
import sys
from pathlib import Path

def analyze_fbx_with_blender(fbx_path: str, output_name: str):
    """Blender 4.2でFBXファイルを分析"""
    
    blender_script = f'''
import bpy
import os

print("=== Blender 4.2 FBX分析: {output_name} ===")
print("ファイルパス: {fbx_path}")
print("ファイルサイズ: {Path(fbx_path).stat().st_size / 1024:.1f}KB")

# シーンクリア
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

try:
    # FBXインポート
    bpy.ops.import_scene.fbx(filepath="{fbx_path}")
    print("✅ FBXインポート成功")
    
    # オブジェクト分析
    objects = list(bpy.context.scene.objects)
    print(f"オブジェクト数: {{len(objects)}}")
    
    meshes = [obj for obj in objects if obj.type == 'MESH']
    armatures = [obj for obj in objects if obj.type == 'ARMATURE']
    
    print(f"メッシュ数: {{len(meshes)}}")
    print(f"アーマチュア数: {{len(armatures)}}")
    
    # メッシュ詳細分析
    for i, mesh_obj in enumerate(meshes):
        mesh_data = mesh_obj.data
        print(f"\\nメッシュ {{i+1}}: {{mesh_obj.name}}")
        print(f"  頂点数: {{len(mesh_data.vertices)}}")
        print(f"  面数: {{len(mesh_data.polygons)}}")
        print(f"  UVレイヤー数: {{len(mesh_data.uv_layers)}}")
        print(f"  マテリアル数: {{len(mesh_data.materials)}}")
        
        # UVレイヤー詳細
        for j, uv_layer in enumerate(mesh_data.uv_layers):
            print(f"    UV {{j+1}}: {{uv_layer.name}}")
        
        # マテリアル詳細
        for j, material in enumerate(mesh_data.materials):
            if material:
                print(f"    マテリアル {{j+1}}: {{material.name}}")
                print(f"      ノード使用: {{material.use_nodes}}")
                
                if material.use_nodes and material.node_tree:
                    nodes = material.node_tree.nodes
                    print(f"      ノード数: {{len(nodes)}}")
                    
                    # Image Textureノード検出
                    tex_nodes = [n for n in nodes if n.type == 'TEX_IMAGE']
                    print(f"      テクスチャノード数: {{len(tex_nodes)}}")
                    
                    for k, tex_node in enumerate(tex_nodes):
                        if tex_node.image:
                            img = tex_node.image
                            print(f"        テクスチャ {{k+1}}: {{img.name}} ({{img.size[0]}}x{{img.size[1]}})")
                        else:
                            print(f"        テクスチャ {{k+1}}: 画像なし")
            else:
                print(f"    マテリアル {{j+1}}: None")
    
    # アーマチュア分析
    for i, armature_obj in enumerate(armatures):
        armature_data = armature_obj.data
        print(f"\\nアーマチュア {{i+1}}: {{armature_obj.name}}")
        print(f"  ボーン数: {{len(armature_data.bones)}}")
    
    # 画像データ分析
    images = list(bpy.data.images)
    print(f"\\n画像データ数: {{len(images)}}")
    for i, img in enumerate(images):
        if img.name not in ['Render Result', 'Viewer Node']:
            print(f"  画像 {{i+1}}: {{img.name}} ({{img.size[0]}}x{{img.size[1]}})")
            print(f"    ファイルパス: {{img.filepath}}")
            print(f"    カラースペース: {{img.colorspace_settings.name}}")

except Exception as e:
    print(f"❌ FBX分析エラー: {{e}}")
    import traceback
    traceback.print_exc()

print("\\n=== 分析完了 ===")
'''
    
    # Blender実行
    cmd = ["blender", "--background", "--python-expr", blender_script]
    
    print(f"🔍 {output_name}を分析中...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    
    if result.returncode == 0:
        print(result.stdout)
    else:
        print(f"❌ エラー: {result.stderr}")
    
    return result.returncode == 0

def main():
    """メイン分析実行"""
    
    base_dir = Path("/app/test_step5_output")
    
    files_to_analyze = [
        (base_dir / "test_bird_final.fbx", "Final FBX (294KB)"),
        (base_dir / "test_bird_stripped.fbx", "Stripped FBX (377KB)"),
    ]
    
    print("🎯 Step5結果分析 - Blender 4.2")
    print("=" * 50)
    
    for fbx_path, description in files_to_analyze:
        if fbx_path.exists():
            analyze_fbx_with_blender(str(fbx_path), description)
            print("\\n" + "=" * 50 + "\\n")
        else:
            print(f"❌ ファイルが見つかりません: {fbx_path}")
    
    # Blendファイルの分析
    print("📋 Blendファイル情報:")
    for blend_file in ["test_bird_model1.blend", "test_bird_model2.blend"]:
        blend_path = base_dir / blend_file
        if blend_path.exists():
            size_kb = blend_path.stat().st_size / 1024
            print(f"  {blend_file}: {size_kb:.1f}KB")

if __name__ == "__main__":
    main()
