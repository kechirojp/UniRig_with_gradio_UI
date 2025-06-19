#!/usr/bin/env python3
"""
修正されたStep4の出力をBlenderで詳細分析
バーテックスグループの存在確認
"""

import sys
import os
import subprocess
import tempfile

def analyze_fixed_step4_output():
    """修正されたStep4出力の詳細分析"""
    
    print("🔍 修正されたStep4出力の詳細分析")
    print("=" * 50)
    
    # 分析対象ファイル
    files_to_analyze = {
        "元のスキニング済み": "/app/pipeline_work/bird/03_skinning/bird_skinned.fbx",
        "修正前マージ": "/app/pipeline_work/bird/04_merge/bird_merged.fbx.backup",
        "修正後マージ": "/app/pipeline_work/bird/04_merge/bird_merged.fbx"
    }
    
    # ファイル存在確認
    for name, path in files_to_analyze.items():
        if os.path.exists(path):
            size = os.path.getsize(path)
            print(f"✅ {name}: {size:,} bytes")
        else:
            print(f"❌ {name}: ファイル不存在 - {path}")
    
    print()
    
    # Blenderスクリプトで詳細分析
    blender_analysis_script = f'''
import bpy
import sys
import os  # 🔧 追加: osモジュールのインポート

def clean_scene():
    """Blenderシーンクリア"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    for collection in bpy.data.collections:
        bpy.data.collections.remove(collection)
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    for armature in bpy.data.armatures:
        bpy.data.armatures.remove(armature)

def analyze_fbx_file(file_path, file_name):
    """FBXファイルの詳細分析"""
    print(f"\\n📋 {{file_name}} 分析:")
    print(f"ファイル: {{file_path}}")
    
    if not os.path.exists(file_path):
        print("❌ ファイル不存在")
        return
    
    try:
        clean_scene()
        
        # FBXファイル読み込み
        bpy.ops.import_scene.fbx(filepath=file_path)
        
        print(f"📊 読み込み後のシーン状態:")
        print(f"  Objects: {{len(bpy.data.objects)}}")
        print(f"  Meshes: {{len(bpy.data.meshes)}}")
        print(f"  Armatures: {{len(bpy.data.armatures)}}")
        
        # オブジェクト詳細分析
        mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
        armature_objects = [obj for obj in bpy.data.objects if obj.type == 'ARMATURE']
        
        print(f"\\n🎯 メッシュオブジェクト ({{len(mesh_objects)}}個):")
        for i, obj in enumerate(mesh_objects):
            print(f"  Mesh {{i+1}}: {{obj.name}}")
            print(f"    - Vertices: {{len(obj.data.vertices)}}")
            print(f"    - Vertex Groups: {{len(obj.vertex_groups)}}")
            
            # バーテックスグループの詳細
            if obj.vertex_groups:
                print(f"    - Vertex Group Names:")
                for vg in obj.vertex_groups:
                    print(f"      - {{vg.name}}")
            else:
                print(f"    - ⚠️  バーテックスグループなし")
            
            # 親子関係確認
            if obj.parent:
                print(f"    - Parent: {{obj.parent.name}} ({{obj.parent.type}})")
            else:
                print(f"    - Parent: なし")
        
        print(f"\\n🦴 アーマチュアオブジェクト ({{len(armature_objects)}}個):")
        for i, obj in enumerate(armature_objects):
            print(f"  Armature {{i+1}}: {{obj.name}}")
            print(f"    - Bones: {{len(obj.data.bones)}}")
            if obj.data.bones:
                bone_names = [bone.name for bone in obj.data.bones]
                print(f"    - Bone Names: {{', '.join(bone_names[:5])}}")
                if len(bone_names) > 5:
                    print(f"      ... and {{len(bone_names)-5}} more")
        
    except Exception as e:
        print(f"❌ 分析エラー: {{e}}")

# ファイル分析実行
files = {{
    "元のスキニング済み": "{files_to_analyze['元のスキニング済み']}",
    "修正後マージ": "{files_to_analyze['修正後マージ']}"
}}

for name, path in files.items():
    if os.path.exists(path):
        analyze_fbx_file(path, name)
    else:
        print(f"\\n❌ {{name}}: ファイル不存在")

print("\\n✅ 分析完了")
'''
    
    # Blenderで分析実行
    print("🔍 Blenderでの詳細分析実行中...")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(blender_analysis_script)
        script_path = f.name
    
    try:
        cmd = ["blender", "--background", "--python", script_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        print("📋 分析結果:")
        print(result.stdout)
        
        if result.stderr:
            print("⚠️  エラー出力:")
            print(result.stderr)
        
        return result.returncode == 0
        
    finally:
        os.unlink(script_path)

if __name__ == "__main__":
    success = analyze_fixed_step4_output()
    if success:
        print("✅ Step4出力分析完了")
    else:
        print("❌ Step4出力分析失敗")
