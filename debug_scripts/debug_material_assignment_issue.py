#!/usr/bin/env python3
"""
FBXマテリアル保持問題の根本原因特定とフィックス
マテリアル割り当て失敗の原因を調査し、解決策を実装
"""

import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_material_assignment_issue():
    """マテリアル割り当て問題の根本原因を特定"""
    
    try:
        import bpy
        
        # 現在のテクスチャ統合システムを使用してテストケースを作成
        test_fbx = "/app/pipeline_work/06_final_output/bird/bird_final_textures_fixed.fbx"
        
        def test_direct_material_assignment():
            """直接的なマテリアル割り当てテスト"""
            
            logger.info("=== 直接的なマテリアル割り当てテスト ===")
            
            # ファクトリーリセット
            bpy.ops.wm.read_factory_settings(use_empty=True)
            
            # シンプルなキューブメッシュを作成
            bpy.ops.mesh.primitive_cube_add()
            cube = bpy.context.active_object
            cube.name = "TestCube"
            
            # マテリアルを作成
            material = bpy.data.materials.new(name="TestMaterial")
            material.use_nodes = True
            
            # マテリアルをメッシュに割り当て - 方法1: material_slots.append
            logger.info("方法1: material_slots.append でマテリアル割り当て")
            cube.data.materials.append(material)
            
            logger.info(f"キューブのマテリアル数: {len(cube.data.materials)}")
            logger.info(f"マテリアルスロット数: {len(cube.material_slots)}")
            
            # FBXエクスポート
            export_path_1 = "/app/debug_material_assignment_test1.fbx"
            bpy.ops.export_scene.fbx(filepath=export_path_1, embed_textures=True)
            
            # FBXインポートして確認
            bpy.ops.wm.read_factory_settings(use_empty=True)
            bpy.ops.import_scene.fbx(filepath=export_path_1)
            
            materials_after_import_1 = len(bpy.data.materials)
            logger.info(f"方法1 - インポート後のマテリアル数: {materials_after_import_1}")
            
            return materials_after_import_1
        
        def test_material_slot_assignment():
            """マテリアルスロット経由での割り当てテスト"""
            
            logger.info("=== マテリアルスロット経由での割り当てテスト ===")
            
            # ファクトリーリセット
            bpy.ops.wm.read_factory_settings(use_empty=True)
            
            # シンプルなキューブメッシュを作成
            bpy.ops.mesh.primitive_cube_add()
            cube = bpy.context.active_object
            cube.name = "TestCube"
            
            # マテリアルを作成
            material = bpy.data.materials.new(name="TestMaterial")
            material.use_nodes = True
            
            # マテリアルをメッシュに割り当て - 方法2: material_slots
            logger.info("方法2: material_slots経由でマテリアル割り当て")
            
            # まずマテリアルスロットを作成
            cube.data.materials.append(None)  # 空のスロットを作成
            cube.material_slots[0].material = material  # スロットにマテリアルを割り当て
            
            logger.info(f"キューブのマテリアル数: {len(cube.data.materials)}")
            logger.info(f"マテリアルスロット数: {len(cube.material_slots)}")
            
            # FBXエクスポート
            export_path_2 = "/app/debug_material_assignment_test2.fbx"
            bpy.ops.export_scene.fbx(filepath=export_path_2, embed_textures=True)
            
            # FBXインポートして確認
            bpy.ops.wm.read_factory_settings(use_empty=True)
            bpy.ops.import_scene.fbx(filepath=export_path_2)
            
            materials_after_import_2 = len(bpy.data.materials)
            logger.info(f"方法2 - インポート後のマテリアル数: {materials_after_import_2}")
            
            return materials_after_import_2
        
        def test_complex_texture_material():
            """複雑なテクスチャ付きマテリアルのテスト"""
            
            logger.info("=== 複雑なテクスチャ付きマテリアルテスト ===")
            
            # ファクトリーリセット
            bpy.ops.wm.read_factory_settings(use_empty=True)
            
            # シンプルなキューブメッシュを作成
            bpy.ops.mesh.primitive_cube_add()
            cube = bpy.context.active_object
            cube.name = "TestCube"
            
            # マテリアルを作成
            material = bpy.data.materials.new(name="ComplexMaterial")
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
            
            # テクスチャイメージを作成
            image = bpy.data.images.new("TestTexture", 512, 512)
            
            # テクスチャノードを作成
            tex_node = nodes.new(type='ShaderNodeTexImage')
            tex_node.image = image
            tex_node.location = (-300, 0)
            
            # 接続を作成
            links.new(tex_node.outputs['Color'], principled.inputs['Base Color'])
            links.new(principled.outputs['BSDF'], output.inputs['Surface'])
            
            # マテリアルをメッシュに割り当て
            cube.data.materials.append(material)
            
            logger.info(f"複雑マテリアル - ノード数: {len(nodes)}")
            logger.info(f"複雑マテリアル - リンク数: {len(links)}")
            logger.info(f"複雑マテリアル - 画像数: {len(bpy.data.images) - 2}")  # Render Result, Viewer Node除く
            
            # FBXエクスポート
            export_path_3 = "/app/debug_material_assignment_test3.fbx"
            
            # 画像をパック
            image.pack()
            logger.info("画像をパックしました")
            
            bpy.ops.export_scene.fbx(
                filepath=export_path_3, 
                embed_textures=True,
                path_mode='COPY'
            )
            
            # FBXインポートして確認
            bpy.ops.wm.read_factory_settings(use_empty=True)
            bpy.ops.import_scene.fbx(filepath=export_path_3)
            
            materials_after_import_3 = len(bpy.data.materials)
            images_after_import_3 = len([img for img in bpy.data.images if img.name not in ['Render Result', 'Viewer Node']])
            
            logger.info(f"方法3 - インポート後のマテリアル数: {materials_after_import_3}")
            logger.info(f"方法3 - インポート後の画像数: {images_after_import_3}")
            
            return materials_after_import_3, images_after_import_3
        
        def test_real_texture_system():
            """実際のテクスチャシステムを模擬したテスト"""
            
            logger.info("=== 実際のテクスチャシステム模擬テスト ===")
            
            # texture_preservation_system.pyの処理を模擬
            from texture_preservation_system import TexturePreservationSystem
            
            # 元のFBXファイルが存在する場合のテスト
            if os.path.exists(test_fbx):
                logger.info(f"実際のFBXファイルをテスト: {test_fbx}")
                
                # インポート
                bpy.ops.wm.read_factory_settings(use_empty=True)
                bpy.ops.import_scene.fbx(filepath=test_fbx)
                
                # 現在の状態を確認
                materials_before = len(bpy.data.materials)
                images_before = len([img for img in bpy.data.images if img.name not in ['Render Result', 'Viewer Node']])
                
                logger.info(f"インポート直後 - マテリアル数: {materials_before}")
                logger.info(f"インポート直後 - 画像数: {images_before}")
                
                # メッシュオブジェクトを確認
                mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
                logger.info(f"メッシュオブジェクト数: {len(mesh_objects)}")
                
                for obj in mesh_objects:
                    logger.info(f"メッシュ '{obj.name}':")
                    logger.info(f"  マテリアルスロット数: {len(obj.material_slots)}")
                    for i, slot in enumerate(obj.material_slots):
                        logger.info(f"    スロット {i}: {slot.material.name if slot.material else 'None'}")
                
                # FBX再エクスポート（現在のmerge.pyと同じ設定）
                reexport_path = "/app/debug_real_texture_system_test.fbx"
                
                bpy.ops.export_scene.fbx(
                    filepath=reexport_path, 
                    use_selection=False,
                    add_leaf_bones=True,
                    path_mode='COPY',
                    embed_textures=True,
                    use_mesh_modifiers=True,
                    use_custom_props=True,
                    mesh_smooth_type='OFF',
                    use_tspace=True,
                    bake_anim=False
                )
                
                # 再インポートして確認
                bpy.ops.wm.read_factory_settings(use_empty=True)
                bpy.ops.import_scene.fbx(filepath=reexport_path)
                
                materials_after = len(bpy.data.materials)
                images_after = len([img for img in bpy.data.images if img.name not in ['Render Result', 'Viewer Node']])
                
                logger.info(f"再エクスポート後 - マテリアル数: {materials_after}")
                logger.info(f"再エクスポート後 - 画像数: {images_after}")
                
                return materials_before, materials_after, images_before, images_after
            else:
                logger.warning(f"テスト対象ファイルが見つかりません: {test_fbx}")
                return 0, 0, 0, 0
        
        # テスト実行
        logger.info("FBXマテリアル割り当て問題の根本原因調査を開始...")
        
        # 1. 基本的なマテリアル割り当てテスト
        result1 = test_direct_material_assignment()
        
        # 2. マテリアルスロット経由テスト
        result2 = test_material_slot_assignment()
        
        # 3. 複雑なテクスチャ付きマテリアルテスト
        result3 = test_complex_texture_material()
        
        # 4. 実際のテクスチャシステムテスト
        real_before_mat, real_after_mat, real_before_img, real_after_img = test_real_texture_system()
        
        # 結果まとめ
        logger.info("=== テスト結果まとめ ===")
        logger.info(f"1. 基本マテリアル割り当て: {result1} マテリアル")
        logger.info(f"2. スロット経由割り当て: {result2} マテリアル")
        logger.info(f"3. 複雑テクスチャマテリアル: {result3[0]} マテリアル, {result3[1]} 画像")
        logger.info(f"4. 実際のテクスチャシステム: {real_before_mat}→{real_after_mat} マテリアル, {real_before_img}→{real_after_img} 画像")
        
        # 問題の特定
        if result1 == 0 and result2 == 0:
            logger.error("❌ 基本的なマテリアル割り当てが機能していません - Blenderまたはエクスポート設定の問題")
        elif result1 > 0 and result2 > 0:
            logger.info("✅ 基本的なマテリアル割り当ては機能しています")
            
            if result3[0] == 0:
                logger.error("❌ テクスチャ付きマテリアルでエクスポートが失敗 - テクスチャ埋め込み問題")
            else:
                logger.info("✅ テクスチャ付きマテリアルも機能しています")
                
                if real_after_mat == 0:
                    logger.error("❌ 実際のテクスチャシステムでマテリアルが失われています - merge.py の make_armature 関数に問題")
                else:
                    logger.info("✅ 実際のテクスチャシステムでもマテリアルが保持されています")
        
        # ファイルサイズ確認
        for i, path in enumerate([
            "/app/debug_material_assignment_test1.fbx",
            "/app/debug_material_assignment_test2.fbx", 
            "/app/debug_material_assignment_test3.fbx",
            "/app/debug_real_texture_system_test.fbx"
        ], 1):
            if os.path.exists(path):
                size = os.path.getsize(path) / 1024
                logger.info(f"テスト{i}ファイルサイズ: {size:.2f} KB")
        
    except Exception as e:
        logger.error(f"デバッグ中にエラーが発生しました: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    debug_material_assignment_issue()
