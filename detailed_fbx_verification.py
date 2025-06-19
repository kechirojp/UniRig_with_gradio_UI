#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
詳細なFBXスキンウェイト検証スクリプト - テンポラリスクリプトファイル方式
"""

import subprocess
import tempfile
import os
from pathlib import Path

def create_blender_verification_script(fbx_path: str) -> str:
    """Blender検証スクリプトを作成"""
    script_content = f'''
import bpy
import sys

# 新しいシーンをクリア
bpy.ops.wm.read_factory_settings(use_empty=True)

try:
    print("Starting FBX import...")
    
    # FBXファイルをインポート
    bpy.ops.import_scene.fbx(filepath="{fbx_path}")
    
    print("=== FBX Import Successful ===")
    
    # シーン内のオブジェクト数を確認
    total_objects = len(bpy.data.objects)
    print(f"Total objects in scene: {{total_objects}}")
    
    # オブジェクトタイプ別集計
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    armature_objects = [obj for obj in bpy.data.objects if obj.type == 'ARMATURE']
    empty_objects = [obj for obj in bpy.data.objects if obj.type == 'EMPTY']
    
    print(f"MESH objects: {{len(mesh_objects)}}")
    print(f"ARMATURE objects: {{len(armature_objects)}}")
    print(f"EMPTY objects: {{len(empty_objects)}}")
    
    # メッシュの詳細分析
    for i, mesh_obj in enumerate(mesh_objects):
        print(f"\\n--- MESH {{i+1}}: {{mesh_obj.name}} ---")
        print(f"  Vertices: {{len(mesh_obj.data.vertices)}}")
        print(f"  Faces: {{len(mesh_obj.data.polygons)}}")
        print(f"  Vertex Groups: {{len(mesh_obj.vertex_groups)}}")
        
        # 頂点グループ（スキンウェイト）の詳細
        if mesh_obj.vertex_groups:
            print(f"  Vertex Group Details:")
            for j, vg in enumerate(mesh_obj.vertex_groups):
                print(f"    {{j+1}}. {{vg.name}} (index: {{vg.index}})")
                
                # 頂点グループに所属する頂点数を確認
                vertex_count = 0
                for vertex in mesh_obj.data.vertices:
                    for group in vertex.groups:
                        if group.group == vg.index:
                            vertex_count += 1
                            break
                print(f"       -> Vertices affected: {{vertex_count}}")
        else:
            print("  ❌ NO VERTEX GROUPS FOUND!")
        
        # モディファイア確認
        if mesh_obj.modifiers:
            print(f"  Modifiers: {{len(mesh_obj.modifiers)}}")
            for mod in mesh_obj.modifiers:
                print(f"    - {{mod.name}} ({{mod.type}})")
                if mod.type == 'ARMATURE':
                    print(f"      Armature: {{mod.object.name if mod.object else 'None'}}")
        else:
            print("  No modifiers")
    
    # アーマチュアの詳細分析
    for i, armature_obj in enumerate(armature_objects):
        print(f"\\n--- ARMATURE {{i+1}}: {{armature_obj.name}} ---")
        print(f"  Bones: {{len(armature_obj.data.bones)}}")
        
        if armature_obj.data.bones:
            print(f"  Bone Names (first 15):")
            for j, bone in enumerate(armature_obj.data.bones[:15]):
                parent_name = bone.parent.name if bone.parent else "Root"
                print(f"    {{j+1}}. {{bone.name}} (parent: {{parent_name}})")
        else:
            print("  ❌ NO BONES FOUND!")
    
    # 重要: アーマチュアとメッシュの関連性確認
    print("\\n=== ARMATURE-MESH RELATIONSHIPS ===")
    for mesh_obj in mesh_objects:
        armature_modifiers = [mod for mod in mesh_obj.modifiers if mod.type == 'ARMATURE']
        if armature_modifiers:
            for mod in armature_modifiers:
                if mod.object:
                    print(f"Mesh '{{mesh_obj.name}}' -> Armature '{{mod.object.name}}'")
                else:
                    print(f"Mesh '{{mesh_obj.name}}' -> Armature modifier with no target!")
        else:
            print(f"Mesh '{{mesh_obj.name}}' -> NO ARMATURE MODIFIER!")
    
    print("\\n=== VERIFICATION SUMMARY ===")
    has_mesh = len(mesh_objects) > 0
    has_armature = len(armature_objects) > 0
    has_vertex_groups = any(len(obj.vertex_groups) > 0 for obj in mesh_objects)
    has_armature_modifier = any(
        any(mod.type == 'ARMATURE' for mod in obj.modifiers) 
        for obj in mesh_objects
    )
    
    print("✅ Has Mesh: {}".format(has_mesh))
    print("✅ Has Armature: {}".format(has_armature))
    vg_symbol = "✅" if has_vertex_groups else "❌"
    print("{} Has Vertex Groups: {}".format(vg_symbol, has_vertex_groups))
    am_symbol = "✅" if has_armature_modifier else "❌"  
    print("{} Has Armature Modifier: {}".format(am_symbol, has_armature_modifier))
    
    if has_mesh and has_armature and has_vertex_groups and has_armature_modifier:
        print("\\n🎉 SKINNING VERIFICATION: COMPLETE SUCCESS!")
    else:
        print("\\n⚠️ SKINNING VERIFICATION: ISSUES DETECTED!")
    
except Exception as e:
    print(f"CRITICAL ERROR: {{e}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
'''
    return script_content

def main():
    fbx_path = "/app/pipeline_work/bird/04_merge/bird_merged.fbx"
    
    print("詳細Step4出力FBX検証開始...")
    print(f"検証対象: {fbx_path}")
    
    if not Path(fbx_path).exists():
        print(f"❌ ファイルが存在しません: {fbx_path}")
        return False
    
    file_size = Path(fbx_path).stat().st_size / (1024*1024)
    print(f"✅ ファイル存在確認: {file_size:.2f} MB")
    
    # テンポラリスクリプトファイルを作成
    script_content = create_blender_verification_script(fbx_path)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_script:
        temp_script.write(script_content)
        temp_script_path = temp_script.name
    
    try:
        # Blenderで実行
        cmd = ["blender", "--background", "--python", temp_script_path]
        
        print("\\nBlender詳細検証実行中...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        print("\\n--- Blender詳細検証結果 ---")
        if result.returncode == 0:
            print("✅ Blender検証成功")
            # 重要な行を抽出して表示
            lines = result.stdout.split('\\n')
            for line in lines:
                if any(keyword in line for keyword in [
                    "MESH objects:", "ARMATURE objects:", "Vertices:", "Vertex Groups:",
                    "Bones:", "ARMATURE-MESH", "VERIFICATION SUMMARY", "SKINNING VERIFICATION",
                    "Has Vertex Groups", "Has Armature Modifier"
                ]):
                    print(line)
        else:
            print("❌ Blender検証失敗")
            print(f"Return code: {result.returncode}")
            print(f"STDERR: {result.stderr}")
    
    finally:
        # テンポラリファイルを削除
        try:
            os.unlink(temp_script_path)
        except:
            pass
    
    return result.returncode == 0

if __name__ == "__main__":
    success = main()
    print("\\n検証完了")
