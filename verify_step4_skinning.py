#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step4出力（bird_merged.fbx）のスキンウェイト（頂点グループ）検証スクリプト
目的: Step3からStep4へのスキンウェイト転写が正しく行われているかを確認
"""

import sys
import subprocess
from pathlib import Path

def check_fbx_with_blender(fbx_path: str):
    """Blenderを使用してFBXファイルのスキンウェイト情報を検証"""
    script = f'''
import bpy
import sys

# 新しいシーンをクリア
bpy.ops.wm.read_factory_settings(use_empty=True)

try:
    # FBXファイルをインポート
    bpy.ops.import_scene.fbx(filepath="{fbx_path}")
    
    print("=== FBX Import Success ===")
    
    # シーン内のオブジェクトを確認
    print(f"Objects in scene: {{len(bpy.data.objects)}}")
    
    # メッシュオブジェクトを検索
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    print(f"Mesh objects: {{len(mesh_objects)}}")
    
    # アーマチュアオブジェクトを検索
    armature_objects = [obj for obj in bpy.data.objects if obj.type == 'ARMATURE']
    print(f"Armature objects: {{len(armature_objects)}}")
    
    # メッシュの頂点グループ（スキンウェイト）を確認
    for mesh_obj in mesh_objects:
        print(f"\\n--- Mesh: {{mesh_obj.name}} ---")
        print(f"Vertices: {{len(mesh_obj.data.vertices)}}")
        print(f"Vertex Groups: {{len(mesh_obj.vertex_groups)}}")
        
        # 頂点グループ名を出力
        if mesh_obj.vertex_groups:
            print("Vertex Group Names:")
            for vg in mesh_obj.vertex_groups:
                print(f"  - {{vg.name}}")
        else:
            print("⚠️ No vertex groups found!")
    
    # アーマチュアのボーン情報を確認
    for armature_obj in armature_objects:
        print(f"\\n--- Armature: {{armature_obj.name}} ---")
        print(f"Bones: {{len(armature_obj.data.bones)}}")
        
        # ボーン名を一部出力
        if armature_obj.data.bones:
            print("Bone Names (first 10):")
            for i, bone in enumerate(armature_obj.data.bones[:10]):
                print(f"  {{i+1}}. {{bone.name}}")
        else:
            print("⚠️ No bones found!")
    
    print("\\n=== Verification Complete ===")
    
except Exception as e:
    print(f"ERROR: {{e}}")
    sys.exit(1)
'''
    
    # Blenderをバックグラウンドモードで実行
    cmd = [
        "blender", "--background", "--python-text", script
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Timeout expired"
    except Exception as e:
        return False, "", str(e)

def main():
    fbx_path = "/app/pipeline_work/bird/04_merge/bird_merged.fbx"
    
    print("Step4出力FBX検証開始...")
    print(f"検証対象: {fbx_path}")
    
    if not Path(fbx_path).exists():
        print(f"❌ ファイルが存在しません: {fbx_path}")
        return False
    
    print(f"✅ ファイル存在確認: {Path(fbx_path).stat().st_size / (1024*1024):.2f} MB")
    
    # Blenderでの検証実行
    success, stdout, stderr = check_fbx_with_blender(fbx_path)
    
    print("\\n--- Blender検証結果 ---")
    if success:
        print("✅ Blender検証成功")
        print(stdout)
    else:
        print("❌ Blender検証失敗")
        print(f"STDERR: {stderr}")
    
    print("\\n--- Step3出力との比較参考 ---")
    step3_fbx = "/app/pipeline_work/bird/03_skinning/bird_skinned.fbx"
    if Path(step3_fbx).exists():
        step3_size = Path(step3_fbx).stat().st_size / (1024*1024)
        step4_size = Path(fbx_path).stat().st_size / (1024*1024)
        print(f"Step3 skinned FBX: {step3_size:.2f} MB")
        print(f"Step4 merged FBX:  {step4_size:.2f} MB")
        print(f"サイズ比率: {step4_size/step3_size:.2f}")
    else:
        print("Step3出力が見つかりません")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
