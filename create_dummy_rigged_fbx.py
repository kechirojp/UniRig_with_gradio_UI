#!/usr/bin/env python3
"""
Blenderでダミーリギング済みFBXファイルを作成するスクリプト
"""

import bpy
import sys
from pathlib import Path

def create_dummy_rigged_fbx():
    """
    bird.glbを読み込んでダミーリギングを追加し、FBXで出力
    """
    print("🔄 ダミーリギング済みFBXファイル作成開始...")
    
    # シーンをクリア
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # bird.glbを読み込み
    bird_glb_path = "/app/examples/bird.glb"
    bpy.ops.import_scene.gltf(filepath=bird_glb_path)
    
    # インポートされたメッシュオブジェクトを取得
    mesh_objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    if not mesh_objects:
        print("[FAIL] メッシュオブジェクトが見つかりません")
        return False
    
    bird_mesh = mesh_objects[0]
    bird_mesh.name = "bird_rigged"
    
    print(f"[OK] メッシュオブジェクト読み込み: {bird_mesh.name}")
    print(f"   頂点数: {len(bird_mesh.data.vertices)}")
    
    # ダミーアーマチュア作成
    bpy.ops.object.armature_add(enter_editmode=False, align='WORLD', location=(0, 0, 0))
    armature = bpy.context.object
    armature.name = "bird_armature"
    
    # アーマチュアを編集モードにして骨を追加
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='EDIT')
    
    # 骨を追加
    bpy.ops.armature.extrude_move(
        ARMATURE_OT_extrude={"forked": False},
        TRANSFORM_OT_translate={"value": (0, 0, 0.5)}
    )
    bpy.ops.armature.extrude_move(
        ARMATURE_OT_extrude={"forked": False},
        TRANSFORM_OT_translate={"value": (0, 0, 0.5)}
    )
    
    bpy.ops.object.mode_set(mode='OBJECT')
    
    print(f"[OK] アーマチュア作成: {armature.name} (3本の骨)")
    
    # メッシュにダミー頂点グループを追加
    bpy.context.view_layer.objects.active = bird_mesh
    
    # 既存の頂点グループをクリア
    bird_mesh.vertex_groups.clear()
    
    # ダミー頂点グループ作成
    bone_names = ["Bone", "Bone.001", "Bone.002"]
    vertex_count = len(bird_mesh.data.vertices)
    
    for i, bone_name in enumerate(bone_names):
        vg = bird_mesh.vertex_groups.new(name=bone_name)
        # 簡単なウェイト割り当て
        for v_idx in range(0, vertex_count, 3):
            if v_idx + i < vertex_count:
                vg.add([v_idx + i], 1.0, 'REPLACE')
    
    print(f"[OK] 頂点グループ作成: {bone_names}")
    
    # メッシュをアーマチュアの子に設定
    bird_mesh.parent = armature
    bird_mesh.parent_type = 'OBJECT'
    
    # アーマチュアモディファイア追加
    armature_mod = bird_mesh.modifiers.new(name="Armature", type='ARMATURE')
    armature_mod.object = armature
    
    print("[OK] 親子関係・アーマチュアモディファイア設定完了")
    
    # FBXで出力
    output_path = "/tmp/bird_rigged_dummy.fbx"
    
    # メッシュとアーマチュアを選択
    bpy.ops.object.select_all(action='DESELECT')
    bird_mesh.select_set(True)
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    
    # FBXエクスポート
    bpy.ops.export_scene.fbx(
        filepath=output_path,
        use_selection=True,
        global_scale=1.0,
        apply_unit_scale=True,
        axis_up='Y',
        axis_forward='-Z',
        bake_anim=False
    )
    
    print(f"[OK] ダミーリギング済みFBX出力: {output_path}")
    
    # ファイルサイズ確認
    output_file = Path(output_path)
    if output_file.exists():
        file_size = output_file.stat().st_size
        print(f"   ファイルサイズ: {file_size:,} bytes")
        return True
    else:
        print("[FAIL] 出力ファイルが作成されませんでした")
        return False

if __name__ == "__main__":
    try:
        success = create_dummy_rigged_fbx()
        if success:
            print("🎉 ダミーリギング済みFBX作成完了!")
        else:
            print("[FAIL] FBX作成失敗")
            sys.exit(1)
    except Exception as e:
        print(f"[FAIL] エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
