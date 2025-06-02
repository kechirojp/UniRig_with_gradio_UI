#!/usr/bin/env python3
"""
FBXマテリアル保持問題の詳細デバッグ
エクスポート前後でのマテリアル状態を詳細に比較
"""

import os
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_fbx_material_preservation():
    """FBXエクスポート/インポート時のマテリアル保持問題をデバッグ"""
    
    try:
        import bpy
        
        # テスト用のシンプルなマテリアル付きメッシュを作成
        def create_test_mesh_with_material():
            """テスト用のマテリアル付きメッシュを作成"""
            
            # Blenderシーンをクリア
            bpy.ops.wm.read_factory_settings(use_empty=True)
            
            # キューブメッシュを作成
            bpy.ops.mesh.primitive_cube_add()
            cube = bpy.context.active_object
            cube.name = "TestCube"
            
            # マテリアルを作成
            material = bpy.data.materials.new(name="TestMaterial")
            material.use_nodes = True
            
            # ノードツリーを取得
            nodes = material.node_tree.nodes
            links = material.node_tree.links
            
            # 既存ノードをクリア
            nodes.clear()
            
            # Principled BSDFノードを作成
            principled = nodes.new(type='ShaderNodeBsdfPrincipled')
            principled.location = (0, 0)
            
            # Material Outputノードを作成
            output = nodes.new(type='ShaderNodeOutputMaterial')
            output.location = (300, 0)
            
            # Principled BSDFをMaterial Outputに接続
            links.new(principled.outputs['BSDF'], output.inputs['Surface'])
            
            # テスト用のカラーを設定
            principled.inputs['Base Color'].default_value = (0.8, 0.2, 0.2, 1.0)  # 赤色
            principled.inputs['Roughness'].default_value = 0.5
            principled.inputs['Metallic'].default_value = 0.0
            
            # マテリアルをメッシュに適用
            if cube.data.materials:
                cube.data.materials[0] = material
            else:
                cube.data.materials.append(material)
            
            logger.info("テスト用メッシュとマテリアルを作成しました")
            return cube, material
        
        def analyze_material_state(prefix=""):
            """現在のマテリアル状態を分析"""
            
            result = {
                'objects': len([obj for obj in bpy.data.objects if obj.type == 'MESH']),
                'materials': len(bpy.data.materials),
                'images': len([img for img in bpy.data.images if img.name not in ['Render Result', 'Viewer Node']]),
                'material_details': []
            }
            
            for material in bpy.data.materials:
                mat_info = {
                    'name': material.name,
                    'use_nodes': material.use_nodes,
                    'nodes': 0,
                    'links': 0,
                    'connected_textures': 0
                }
                
                if material.use_nodes and material.node_tree:
                    mat_info['nodes'] = len(material.node_tree.nodes)
                    mat_info['links'] = len(material.node_tree.links)
                    
                    # テクスチャノードの数を数える
                    for node in material.node_tree.nodes:
                        if node.type == 'TEX_IMAGE' and node.image:
                            mat_info['connected_textures'] += 1
                
                result['material_details'].append(mat_info)
            
            logger.info(f"{prefix}マテリアル状態: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return result
        
        def test_fbx_export_import():
            """FBXエクスポート/インポートテスト"""
            
            # ステップ1: テストメッシュを作成
            logger.info("=== ステップ1: テストメッシュとマテリアル作成 ===")
            cube, material = create_test_mesh_with_material()
            export_state = analyze_material_state("エクスポート前: ")
            
            # ステップ2: FBXエクスポート（現在の設定）
            logger.info("=== ステップ2: FBXエクスポート ===")
            export_path = "/app/debug_material_test.fbx"
            
            # 現在のmerge.pyと同じ設定でエクスポート
            bpy.ops.export_scene.fbx(
                filepath=export_path, 
                use_selection=False,  # Export all objects
                add_leaf_bones=True,
                # Texture embedding settings
                path_mode='COPY',  # Copy textures to output directory
                embed_textures=True,  # Embed textures in FBX
                # Material settings
                use_mesh_modifiers=True,
                use_custom_props=True,
                # Texture coordinate settings
                mesh_smooth_type='OFF',  # Keep original smoothing
                use_tspace=True,  # Use tangent space for normal maps
                # Animation settings (if needed)
                bake_anim=False
            )
            
            logger.info(f"FBXエクスポート完了: {export_path}")
            
            # ステップ3: FBXインポート
            logger.info("=== ステップ3: FBXインポート ===")
            bpy.ops.wm.read_factory_settings(use_empty=True)  # シーンをクリア
            
            bpy.ops.import_scene.fbx(filepath=export_path)
            import_state = analyze_material_state("インポート後: ")
            
            # ステップ4: 比較分析
            logger.info("=== ステップ4: エクスポート/インポート比較 ===")
            
            logger.info("エクスポート前:")
            logger.info(f"  マテリアル数: {export_state['materials']}")
            logger.info(f"  画像数: {export_state['images']}")
            
            logger.info("インポート後:")
            logger.info(f"  マテリアル数: {import_state['materials']}")
            logger.info(f"  画像数: {import_state['images']}")
            
            # 詳細な差異分析
            if export_state['materials'] != import_state['materials']:
                logger.warning("⚠️ マテリアル数が変化しました！")
            
            if export_state['images'] != import_state['images']:
                logger.warning("⚠️ 画像数が変化しました！")
            
            return export_state, import_state
        
        def test_alternative_fbx_settings():
            """別のFBXエクスポート設定でテスト"""
            
            logger.info("=== 別のFBXエクスポート設定でテスト ===")
            
            # テストメッシュを再作成
            cube, material = create_test_mesh_with_material()
            
            # より詳細な設定でエクスポート
            export_path_alt = "/app/debug_material_test_alt.fbx"
            
            bpy.ops.export_scene.fbx(
                filepath=export_path_alt,
                use_selection=False,
                # Object types
                object_types={'MESH', 'ARMATURE'},
                # Transform
                axis_forward='-Z',
                axis_up='Y',
                # Geometry
                use_mesh_modifiers=True,
                # Materials and textures
                path_mode='COPY',
                embed_textures=True,
                # Animation
                bake_anim=False,
                # Advanced options
                use_custom_props=True,
                add_leaf_bones=False,
                primary_bone_axis='Y',
                secondary_bone_axis='X',
                # Armature options (if applicable)
                armature_nodetype='NULL',
                # Additional options
                use_tspace=True,
                mesh_smooth_type='OFF'
            )
            
            logger.info(f"代替設定でFBXエクスポート完了: {export_path_alt}")
            
            # インポートしてテスト
            bpy.ops.wm.read_factory_settings(use_empty=True)
            bpy.ops.import_scene.fbx(filepath=export_path_alt)
            alt_import_state = analyze_material_state("代替設定インポート後: ")
            
            return alt_import_state
        
        # メインテスト実行
        logger.info("FBXマテリアル保持問題のデバッグを開始します...")
        
        # 標準設定でのテスト
        export_state, import_state = test_fbx_export_import()
        
        # 代替設定でのテスト
        alt_import_state = test_alternative_fbx_settings()
        
        logger.info("=== 最終結果まとめ ===")
        logger.info("標準設定:")
        logger.info(f"  エクスポート前マテリアル: {export_state['materials']}")
        logger.info(f"  インポート後マテリアル: {import_state['materials']}")
        
        logger.info("代替設定:")
        logger.info(f"  インポート後マテリアル: {alt_import_state['materials']}")
        
        # ファイルサイズも確認
        if os.path.exists("/app/debug_material_test.fbx"):
            size = os.path.getsize("/app/debug_material_test.fbx")
            logger.info(f"標準設定FBXサイズ: {size / 1024:.2f} KB")
        
        if os.path.exists("/app/debug_material_test_alt.fbx"):
            size = os.path.getsize("/app/debug_material_test_alt.fbx")
            logger.info(f"代替設定FBXサイズ: {size / 1024:.2f} KB")
        
    except Exception as e:
        logger.error(f"デバッグ中にエラーが発生しました: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    debug_fbx_material_preservation()
