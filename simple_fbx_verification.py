#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step4出力FBXの詳細スキンウェイト検証
"""

import subprocess
import tempfile
import os
from pathlib import Path

def main():
    fbx_path = "/app/pipeline_work/bird/04_merge/bird_merged.fbx"
    
    print("Step4出力FBX詳細検証開始...")
    print(f"検証対象: {fbx_path}")
    
    if not Path(fbx_path).exists():
        print(f"ファイルが存在しません: {fbx_path}")
        return False
    
    file_size = Path(fbx_path).stat().st_size / (1024*1024)
    print(f"ファイルサイズ: {file_size:.2f} MB")
    
    # Blender検証スクリプトを文字列として作成
    blender_script = '''
import bpy
import sys

# 新しいシーンをクリア  
bpy.ops.wm.read_factory_settings(use_empty=True)

try:
    print("FBXインポート開始...")
    bpy.ops.import_scene.fbx(filepath="''' + fbx_path + '''")
    print("FBXインポート成功")
    
    # オブジェクト集計
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    armature_objects = [obj for obj in bpy.data.objects if obj.type == 'ARMATURE']
    
    print(f"メッシュオブジェクト数: {len(mesh_objects)}")
    print(f"アーマチュアオブジェクト数: {len(armature_objects)}")
    
    # メッシュ詳細
    for i, mesh_obj in enumerate(mesh_objects):
        print(f"\\nメッシュ {i+1}: {mesh_obj.name}")
        print(f"  頂点数: {len(mesh_obj.data.vertices)}")
        print(f"  頂点グループ数: {len(mesh_obj.vertex_groups)}")
        
        if mesh_obj.vertex_groups:
            print("  頂点グループ名:")
            for j, vg in enumerate(mesh_obj.vertex_groups):
                print(f"    {j+1}. {vg.name}")
        else:
            print("  頂点グループなし")
        
        # アーマチュアモディファイア確認
        armature_mods = [mod for mod in mesh_obj.modifiers if mod.type == 'ARMATURE']
        if armature_mods:
            print(f"  アーマチュアモディファイア: {len(armature_mods)}個")
            for mod in armature_mods:
                target_name = mod.object.name if mod.object else "なし"
                print(f"    - {mod.name} -> {target_name}")
        else:
            print("  アーマチュアモディファイアなし")
    
    # アーマチュア詳細
    for i, armature_obj in enumerate(armature_objects):
        print(f"\\nアーマチュア {i+1}: {armature_obj.name}")
        print(f"  ボーン数: {len(armature_obj.data.bones)}")
        
        if armature_obj.data.bones:
            print("  ボーン名 (最初の10個):")
            for j, bone in enumerate(armature_obj.data.bones[:10]):
                parent_name = bone.parent.name if bone.parent else "ルート"
                print(f"    {j+1}. {bone.name} (親: {parent_name})")
    
    # スキニング検証サマリ
    has_mesh = len(mesh_objects) > 0
    has_armature = len(armature_objects) > 0
    has_vertex_groups = any(len(obj.vertex_groups) > 0 for obj in mesh_objects)
    has_armature_modifier = any(
        any(mod.type == 'ARMATURE' for mod in obj.modifiers) 
        for obj in mesh_objects
    )
    
    print("\\n=== スキニング検証サマリ ===")
    print(f"メッシュ存在: {'○' if has_mesh else '×'}")
    print(f"アーマチュア存在: {'○' if has_armature else '×'}")  
    print(f"頂点グループ存在: {'○' if has_vertex_groups else '×'}")
    print(f"アーマチュアモディファイア存在: {'○' if has_armature_modifier else '×'}")
    
    if has_mesh and has_armature and has_vertex_groups and has_armature_modifier:
        print("\\n🎉 スキニング検証: 完全成功!")
    else:
        print("\\n⚠️ スキニング検証: 問題検出!")
        
except Exception as e:
    print(f"エラー: {e}")
    import traceback
    traceback.print_exc()
'''
    
    # テンポラリファイルに保存
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
        temp_file.write(blender_script)
        temp_file_path = temp_file.name
    
    try:
        # Blender実行
        cmd = ["blender", "--background", "--python", temp_file_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        print("\\n--- Blender検証結果 ---")
        if result.returncode == 0:
            print("✅ 検証成功")
            # 重要な出力行を抽出
            lines = result.stdout.split('\\n')
            important_lines = []
            for line in lines:
                if any(keyword in line for keyword in [
                    "メッシュオブジェクト数", "アーマチュアオブジェクト数", "頂点数", "頂点グループ数",
                    "ボーン数", "アーマチュアモディファイア", "スキニング検証", "完全成功", "問題検出"
                ]):
                    important_lines.append(line)
            
            for line in important_lines:
                print(line)
        else:
            print("❌ 検証失敗")
            print(f"終了コード: {result.returncode}")
            if result.stderr:
                print(f"エラー: {result.stderr}")
    
    finally:
        # テンポラリファイル削除
        try:
            os.unlink(temp_file_path)
        except:
            pass
    
    return result.returncode == 0

if __name__ == "__main__":
    success = main()
