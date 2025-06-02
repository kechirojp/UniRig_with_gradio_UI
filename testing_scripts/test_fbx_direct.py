#!/usr/bin/env python
"""
FBXエクスポート修正の直接テスト
"""
import sys
import os
import bpy
import numpy as np

# UniRigのソースパスを追加
sys.path.insert(0, '/app/src')
sys.path.insert(0, '/app')

def test_fbx_export_fix():
    print("🧪 FBXエクスポート修正の直接テスト開始")
    
    # Blenderの初期化
    bpy.ops.wm.read_homefile(app_template="")
    
    # bird.glbを読み込み
    input_file = "/app/examples/bird.glb"
    print(f"📁 入力ファイル: {input_file}")
    
    try:
        bpy.ops.import_scene.gltf(filepath=input_file)
        print("✅ GLBファイルの読み込み成功")
    except Exception as e:
        print(f"❌ GLBファイル読み込みエラー: {e}")
        return False
    
    # マテリアル情報を確認
    print("\n📊 読み込み後のマテリアル情報:")
    for mat in bpy.data.materials:
        print(f"  マテリアル: {mat.name}")
        if mat.use_nodes and mat.node_tree:
            texture_count = 0
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    texture_count += 1
                    print(f"    テクスチャ: {node.image.name}")
            print(f"    テクスチャ数: {texture_count}")
    
    # FBXエクスポート準備関数をテスト
    try:
        from src.inference.merge import prepare_material_for_fbx_export
        print("\n🔧 FBXエクスポート準備を実行中...")
        
        for mat in bpy.data.materials:
            if mat.use_nodes:
                print(f"  マテリアル '{mat.name}' を準備中...")
                prepare_material_for_fbx_export(mat)
        
        print("✅ FBXエクスポート準備完了")
        
    except Exception as e:
        print(f"❌ FBXエクスポート準備エラー: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 準備後のマテリアル構造を確認
    print("\n📊 準備後のマテリアル構造:")
    for mat in bpy.data.materials:
        if mat.use_nodes and mat.node_tree:
            print(f"  マテリアル: {mat.name}")
            print(f"    ノード数: {len(mat.node_tree.nodes)}")
            
            # Principled BSDFの接続を確認
            for node in mat.node_tree.nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    principled = node
                    
                    # Base Color接続
                    if principled.inputs['Base Color'].links:
                        source = principled.inputs['Base Color'].links[0].from_node
                        print(f"    Base Color ← {source.type} ({source.name})")
                    
                    # Normal接続
                    if principled.inputs['Normal'].links:
                        source = principled.inputs['Normal'].links[0].from_node
                        print(f"    Normal ← {source.type} ({source.name})")
                    
                    # Roughness接続
                    if principled.inputs['Roughness'].links:
                        source = principled.inputs['Roughness'].links[0].from_node
                        print(f"    Roughness ← {source.type} ({source.name})")
    
    # FBXエクスポートテスト
    print("\n💾 FBXエクスポートテスト...")
    fbx_output = "/app/fbx_fix_test/test_fixed_export.fbx"
    try:
        bpy.ops.export_scene.fbx(
            filepath=fbx_output,
            use_selection=False,
            global_scale=1.0,
            apply_unit_scale=True,
            apply_scale_options='FBX_SCALE_NONE',
            bake_space_transform=False,
            object_types={'ARMATURE', 'MESH'},
            use_mesh_modifiers=True,
            use_mesh_modifiers_render=True,
            mesh_smooth_type='OFF',
            use_subsurf=False,
            use_mesh_edges=False,
            use_tspace=False,
            use_custom_props=False,
            add_leaf_bones=True,
            primary_bone_axis='Y',
            secondary_bone_axis='X',
            use_armature_deform_only=False,
            armature_nodetype='NULL',
            bake_anim=True,
            bake_anim_use_all_bones=True,
            bake_anim_use_nla_strips=True,
            bake_anim_use_all_actions=True,
            bake_anim_force_startend_keying=True,
            bake_anim_step=1.0,
            bake_anim_simplify_factor=1.0,
            path_mode='AUTO',
            embed_textures=False,
            batch_mode='OFF',
            use_batch_own_dir=True,
            use_metadata=True
        )
        print(f"✅ FBXエクスポート成功: {fbx_output}")
        
        # ファイルサイズを確認
        if os.path.exists(fbx_output):
            size = os.path.getsize(fbx_output)
            print(f"    ファイルサイズ: {size} bytes")
        
    except Exception as e:
        print(f"❌ FBXエクスポートエラー: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # GLBエクスポートも比較用に実行
    print("\n💾 比較用GLBエクスポート...")
    glb_output = "/app/fbx_fix_test/test_fixed_export.glb"
    try:
        bpy.ops.export_scene.gltf(
            filepath=glb_output,
            export_format='GLB',
            export_draco_mesh_compression_enable=False,
            export_draco_mesh_compression_level=6,
            export_draco_position_quantization=14,
            export_draco_normal_quantization=10,
            export_draco_texcoord_quantization=12,
            export_draco_color_quantization=10,
            export_draco_generic_quantization=12,
            export_tangents=False,
            export_normals=True,
            export_force_indices=False,
            export_texcoords=True,
            export_colors=True,
            use_mesh_edges=False,
            use_mesh_vertices=False,
            export_cameras=False,
            export_selected=False,
            use_selection=False,
            use_visible=False,
            use_renderable=False,
            use_active_collection=False,
            export_extras=False,
            export_yup=True,
            export_apply=False,
            export_animations=True,
            export_frame_range=True,
            export_frame_step=1,
            export_force_sampling=True,
            export_nla_strips=True,
            export_def_bones=False,
            export_current_frame=False,
            export_skins=True,
            export_all_influences=False,
            export_morph=True,
            export_morph_normal=True,
            export_morph_tangent=False,
            export_lights=False,
            export_displacement=False,
            will_save_settings=False,
            filter_glob="*.glb;*.gltf"
        )
        print(f"✅ GLBエクスポート成功: {glb_output}")
        
        # ファイルサイズを確認
        if os.path.exists(glb_output):
            size = os.path.getsize(glb_output)
            print(f"    ファイルサイズ: {size} bytes")
        
    except Exception as e:
        print(f"❌ GLBエクスポートエラー: {e}")
    
    print("\n🎯 テスト完了")
    return True

if __name__ == "__main__":
    test_fbx_export_fix()
