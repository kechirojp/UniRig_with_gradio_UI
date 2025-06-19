#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step4 merge.py内のget_skin関数の動作を詳細デバッグ
"""

import subprocess
import tempfile
import os
from pathlib import Path

def main():
    # Step3のskinned_fbxからスキンウェイト抽出をテスト
    skinned_fbx_path = "/app/pipeline_work/bird/03_skinning/bird_skinned.fbx"
    
    print("Step4 get_skin関数デバッグ開始...")
    print(f"検証対象: {skinned_fbx_path}")
    
    if not Path(skinned_fbx_path).exists():
        print(f"ファイルが存在しません: {skinned_fbx_path}")
        return False
    
    # merge.pyのget_skin関数と同等の処理をBlenderで実行
    blender_script = f'''
import bpy
import numpy as np
import sys

# 新しいシーンをクリア  
bpy.ops.wm.read_factory_settings(use_empty=True)

try:
    print("Step3 skinned_fbx読み込み開始...")
    bpy.ops.import_scene.fbx(filepath="{skinned_fbx_path}")
    print("✅ Step3 skinned_fbx読み込み成功")
    
    # get_skin関数相当の処理
    meshes = []
    for v in bpy.data.objects:
        if v.type == 'MESH':
            meshes.append(v)
    print(f"メッシュオブジェクト数: {{len(meshes)}}")
    
    # アーマチュア取得
    armatures = []
    for v in bpy.data.objects:
        if v.type == 'ARMATURE':
            armatures.append(v)
    print(f"アーマチュア数: {{len(armatures)}}")
    
    if not armatures:
        print("❌ アーマチュアが見つかりません")
        sys.exit(1)
    
    armature = armatures[0]
    print(f"使用するアーマチュア: {{armature.name}}")
    
    # ボーン情報取得
    arranged_bones = [bone for bone in armature.data.bones]
    print(f"ボーン数: {{len(arranged_bones)}}")
    
    # インデックス作成
    index = {{}}
    for (id, pbone) in enumerate(arranged_bones):
        index[pbone.name] = id
    
    # 各メッシュのスキンウェイト抽出
    for mesh_obj in meshes:
        print(f"\\n--- メッシュ: {{mesh_obj.name}} ---")
        print(f"頂点数: {{len(mesh_obj.data.vertices)}}")
        print(f"頂点グループ数: {{len(mesh_obj.vertex_groups)}}")
        
        # 頂点グループ名の確認
        obj_group_names = [g.name for g in mesh_obj.vertex_groups]
        print(f"頂点グループ名 (最初の10個): {{obj_group_names[:10]}}")
        
        # スキンウェイト行列の構築
        total_vertices = len(mesh_obj.data.vertices)
        total_bones = len(arranged_bones)
        skin_weight = np.zeros((total_vertices, total_bones))
        
        # 各ボーンのウェイト情報抽出
        bones_with_weights = 0
        for bone in arranged_bones:
            if bone.name not in obj_group_names:
                continue
            
            bones_with_weights += 1
            gidx = mesh_obj.vertex_groups[bone.name].index
            
            # ウェイト情報の取得
            obj_verts = mesh_obj.data.vertices
            bone_verts = [v for v in obj_verts if gidx in [g.group for g in v.groups]]
            
            for v in bone_verts:
                which = [id for id in range(len(v.groups)) if v.groups[id].group==gidx]
                if which:
                    w = v.groups[which[0]].weight
                    skin_weight[v.index, index[bone.name]] = w
        
        print(f"ウェイト情報を持つボーン数: {{bones_with_weights}}")
        
        # スキンウェイト行列の統計
        non_zero_weights = np.count_nonzero(skin_weight)
        total_weights = skin_weight.size
        print(f"非ゼロウェイト数: {{non_zero_weights}} / {{total_weights}}")
        print(f"ウェイト充填率: {{non_zero_weights/total_weights*100:.2f}}%")
        
        # 行ごと（頂点ごと）のウェイト合計確認
        row_sums = np.sum(skin_weight, axis=1)
        vertices_with_weights = np.count_nonzero(row_sums)
        print(f"ウェイトを持つ頂点数: {{vertices_with_weights}} / {{total_vertices}}")
        print(f"頂点ウェイト率: {{vertices_with_weights/total_vertices*100:.2f}}%")
        
        # サンプルウェイト表示
        if vertices_with_weights > 0:
            max_weight_vertex = np.argmax(row_sums)
            max_weight_sum = row_sums[max_weight_vertex]
            print(f"最大ウェイト合計: 頂点{{max_weight_vertex}} = {{max_weight_sum:.4f}}")
        
        if non_zero_weights > 0:
            print("✅ スキンウェイト抽出成功")
        else:
            print("❌ スキンウェイト抽出失敗")
    
except Exception as e:
    print(f"エラー: {{e}}")
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
        
        print("\\n--- get_skin デバッグ結果 ---")
        if result.returncode == 0:
            print("✅ デバッグ成功")
            # 重要な出力行を抽出
            lines = result.stdout.split('\\n')
            important_lines = []
            for line in lines:
                if any(keyword in line for keyword in [
                    "skinned_fbx読み込み", "メッシュオブジェクト数", "ボーン数", "頂点グループ数",
                    "ウェイト情報を持つボーン数", "非ゼロウェイト数", "ウェイト充填率", "頂点ウェイト率",
                    "最大ウェイト合計", "スキンウェイト抽出"
                ]):
                    important_lines.append(line)
            
            for line in important_lines:
                print(line)
        else:
            print("❌ デバッグ失敗")
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
