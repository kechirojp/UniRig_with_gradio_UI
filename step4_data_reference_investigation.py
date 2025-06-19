#!/usr/bin/env python3
"""
Step4のマージ処理が実際にどのデータを参照しているか詳細調査

重要な調査ポイント:
1. transfer関数がどのファイルからデータを読み込んでいるか
2. process_mesh()とget_skin()が参照しているBlenderシーンの状態
3. sourceファイルとtargetファイルのどちらのデータが実際に使用されているか
"""

import sys
import os
import subprocess
import tempfile
from pathlib import Path

def investigate_step4_data_reference():
    """Step4の内部データ参照を詳細調査"""
    
    print("🔍 Step4 マージ処理の内部データ参照調査開始")
    print("=" * 60)
    
    # 調査対象ファイル
    source_file = "/app/pipeline_work/bird/02_skeleton/skeleton.fbx"
    target_file = "/app/pipeline_work/bird/03_skinning/bird_skinned.fbx"
    output_file = "/tmp/debug_merge_data_reference.fbx"
    
    print(f"📄 Source(skeleton): {source_file}")
    print(f"📄 Target(skinned):  {target_file}")
    print(f"📄 Output:           {output_file}")
    print()
    
    # ファイル存在確認
    if not os.path.exists(source_file):
        print(f"❌ Source file not found: {source_file}")
        return False
    if not os.path.exists(target_file):
        print(f"❌ Target file not found: {target_file}")
        return False
    
    print("✅ 入力ファイル存在確認完了")
    print()
    
    # Blenderスクリプトで詳細調査
    blender_investigation_script = f'''
import bpy
import sys
import os
sys.path.append('/app')

from src.inference.merge import load, process_mesh, get_skin, get_arranged_bones, process_armature

def clean_scene():
    """Blenderシーンを完全にクリア"""
    for collection in bpy.data.collections:
        bpy.data.collections.remove(collection)
    for obj in bpy.data.objects:
        bpy.data.objects.remove(obj)
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    for armature in bpy.data.armatures:
        bpy.data.armatures.remove(armature)

def investigate_data_sources():
    """データソースの詳細調査"""
    
    print("🔍 Blender内部でのデータ参照調査")
    print("=" * 50)
    
    # 1. 初期状態確認
    print("📊 初期Blenderシーン状態:")
    print(f"  - Objects: {{len(bpy.data.objects)}}")
    print(f"  - Meshes: {{len(bpy.data.meshes)}}")
    print(f"  - Armatures: {{len(bpy.data.armatures)}}")
    print()
    
    # 2. Sourceファイル読み込み（スケルトン）
    print("📥 Step 1: Source(skeleton)ファイル読み込み")
    source_file = "{source_file}"
    try:
        clean_scene()
        armature = load(filepath=source_file, return_armature=True)
        print(f"✅ Sourceファイル読み込み成功: {{armature.name if armature else 'None'}}")
        
        # シーン状態確認
        print("📊 Source読み込み後のシーン状態:")
        print(f"  - Objects: {{len(bpy.data.objects)}}")
        print(f"  - Meshes: {{len(bpy.data.meshes)}}")
        print(f"  - Armatures: {{len(bpy.data.armatures)}}")
        
        # メッシュとスキンデータ確認
        if bpy.data.objects:
            for obj in bpy.data.objects:
                print(f"  - Object: {{obj.name}} (type: {{obj.type}})")
                if obj.type == 'MESH':
                    print(f"    - Vertices: {{len(obj.data.vertices)}}")
                    print(f"    - Vertex Groups: {{len(obj.vertex_groups)}}")
                    for vg in obj.vertex_groups:
                        print(f"      - Group: {{vg.name}}")
        
        # process_mesh()の結果確認
        try:
            vertices, faces = process_mesh()
            print(f"📐 process_mesh() 結果:")
            print(f"  - Vertices: {{vertices.shape if hasattr(vertices, 'shape') else 'N/A'}}")
            print(f"  - Faces: {{faces.shape if hasattr(faces, 'shape') else 'N/A'}}")
        except Exception as e:
            print(f"❌ process_mesh() エラー: {{e}}")
        
        # get_skin()の結果確認
        try:
            arranged_bones = get_arranged_bones(armature) if armature else []
            skin = get_skin(arranged_bones)
            print(f"🦴 get_skin() 結果:")
            print(f"  - Arranged bones: {{len(arranged_bones)}}")
            print(f"  - Skin shape: {{skin.shape if hasattr(skin, 'shape') else 'N/A'}}")
        except Exception as e:
            print(f"❌ get_skin() エラー: {{e}}")
        
    except Exception as e:
        print(f"❌ Sourceファイル読み込みエラー: {{e}}")
    
    print()
    
    # 3. Targetファイル読み込み（スキンド）
    print("📥 Step 2: Target(skinned)ファイル読み込み")
    target_file = "{target_file}"
    try:
        clean_scene()
        load(filepath=target_file)  # return_armature=Falseでロード
        print("✅ Targetファイル読み込み成功")
        
        # シーン状態確認
        print("📊 Target読み込み後のシーン状態:")
        print(f"  - Objects: {{len(bpy.data.objects)}}")
        print(f"  - Meshes: {{len(bpy.data.meshes)}}")
        print(f"  - Armatures: {{len(bpy.data.armatures)}}")
        
        # メッシュとスキンデータ確認
        if bpy.data.objects:
            for obj in bpy.data.objects:
                print(f"  - Object: {{obj.name}} (type: {{obj.type}})")
                if obj.type == 'MESH':
                    print(f"    - Vertices: {{len(obj.data.vertices)}}")
                    print(f"    - Vertex Groups: {{len(obj.vertex_groups)}}")
                    for vg in obj.vertex_groups:
                        print(f"      - Group: {{vg.name}}")
        
        # process_mesh()の結果確認（targetファイル読み込み後）
        try:
            vertices, faces = process_mesh()
            print(f"📐 process_mesh() 結果 (Target読み込み後):")
            print(f"  - Vertices: {{vertices.shape if hasattr(vertices, 'shape') else 'N/A'}}")
            print(f"  - Faces: {{faces.shape if hasattr(faces, 'shape') else 'N/A'}}")
        except Exception as e:
            print(f"❌ process_mesh() エラー: {{e}}")
            
    except Exception as e:
        print(f"❌ Targetファイル読み込みエラー: {{e}}")
    
    print()
    
    # 4. transfer関数の実際の動作シミュレーション
    print("🔄 Step 3: transfer関数動作シミュレーション")
    try:
        clean_scene()
        
        # transfer関数の動作をステップバイステップで実行
        print("  4.1: Source(skeleton)からアーマチュア読み込み")
        armature = load(filepath=source_file, return_armature=True)
        
        print("  4.2: Target(skinned)読み込み前のprocess_mesh()")
        vertices_before_target, faces_before_target = process_mesh()
        arranged_bones_before = get_arranged_bones(armature) if armature else []
        skin_before_target = get_skin(arranged_bones_before)
        
        print(f"    - Vertices (Target読み込み前): {{vertices_before_target.shape if hasattr(vertices_before_target, 'shape') else 'N/A'}}")
        print(f"    - Skin (Target読み込み前): {{skin_before_target.shape if hasattr(skin_before_target, 'shape') else 'N/A'}}")
        
        # ここが重要: merge関数の中でtargetファイルがロードされる
        # しかし、vertices と skin は既にsourceファイルから取得済み！
        
        print("  ⚠️  重要な発見:")
        print("    - vertices と skin は Source(skeleton) ファイルから取得")
        print("    - Target(skinned) ファイルは merge() 関数内でロードされるが、")
        print("      その時点で vertices と skin は既に決定済み")
        print("    - つまり、スキニング済みのウェイト情報が使用されていない可能性")
        
    except Exception as e:
        print(f"❌ transfer動作シミュレーションエラー: {{e}}")

# 調査実行
investigate_data_sources()
'''
    
    # Blenderで調査実行
    print("🔍 Blenderでの内部データ参照調査実行中...")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(blender_investigation_script)
        script_path = f.name
    
    try:
        cmd = ["blender", "--background", "--python", script_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        print("📋 調査結果:")
        print(result.stdout)
        
        if result.stderr:
            print("⚠️  エラー出力:")
            print(result.stderr)
        
        return result.returncode == 0
        
    finally:
        os.unlink(script_path)

if __name__ == "__main__":
    success = investigate_step4_data_reference()
    if success:
        print("✅ Step4内部データ参照調査完了")
    else:
        print("❌ Step4内部データ参照調査失敗")
