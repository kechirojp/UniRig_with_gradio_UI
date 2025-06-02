#!/usr/bin/env python3
"""
テクスチャ統合プロセスの詳細デバッグ
マテリアル再構築からFBXエクスポートまでの各ステップを詳細に確認します。
"""

import os
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("=== テクスチャ統合プロセスの詳細デバッグ ===")
    
    try:
        import bpy
        import sys
        sys.path.append('/app')
        from texture_preservation_system import TexturePreservationSystem
        
        # ファイルパス
        rigged_fbx = "/app/pipeline_work/06_final_output/bird/bird_final.fbx"
        texture_data_dir = "/app/pipeline_work/05_texture_preservation/bird"
        
        # テクスチャメタデータを確認
        metadata_path = os.path.join(texture_data_dir, "texture_metadata.json")
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                texture_data = json.load(f)
            
            logger.info("テクスチャメタデータ:")
            logger.info(f"  テクスチャ数: {len(texture_data.get('textures', {}))}")
            logger.info(f"  マテリアル数: {len(texture_data.get('materials', {}))}")
            logger.info(f"  メッシュ-マテリアル対応: {len(texture_data.get('mesh_materials', {}))}")
            
            # マテリアル詳細
            for mat_name, mat_info in texture_data.get('materials', {}).items():
                logger.info(f"マテリアル: {mat_name}")
                logger.info(f"  ノード数: {len(mat_info.get('nodes', {}))}")
                logger.info(f"  リンク数: {len(mat_info.get('links', []))}")
        
        # Blenderシーンをクリア
        bpy.ops.wm.read_factory_settings(use_empty=True)
        
        # システムを初期化
        system = TexturePreservationSystem()
        
        logger.info("1. FBXインポートテスト")
        
        # FBXインポートを試行
        try:
            bpy.ops.import_scene.fbx(filepath=rigged_fbx)
            logger.info("✅ FBXインポート成功")
            
            objects = list(bpy.data.objects)
            meshes = [obj for obj in objects if obj.type == 'MESH']
            armatures = [obj for obj in objects if obj.type == 'ARMATURE']
            
            logger.info(f"インポート後:")
            logger.info(f"  オブジェクト数: {len(objects)}")
            logger.info(f"  メッシュ数: {len(meshes)}")
            logger.info(f"  アーマチュア数: {len(armatures)}")
            logger.info(f"  既存マテリアル数: {len(list(bpy.data.materials))}")
            
        except Exception as e:
            logger.error(f"❌ FBXインポート失敗: {e}")
            return
        
        logger.info("2. テクスチャ画像読み込みテスト")
        
        # テクスチャ画像を読み込み
        loaded_images = {}
        texture_dir = os.path.join(texture_data_dir, "extracted_textures")
        
        if os.path.exists(texture_dir):
            for texture_name, texture_info in texture_data.get("textures", {}).items():
                texture_path = os.path.join(texture_dir, texture_info["filename"])
                if os.path.exists(texture_path):
                    try:
                        image = bpy.data.images.load(texture_path)
                        loaded_images[texture_name] = image
                        logger.info(f"✅ テクスチャ読み込み: {texture_name} ({image.size[0]}x{image.size[1]})")
                    except Exception as e:
                        logger.warning(f"❌ テクスチャ読み込み失敗: {texture_name} - {e}")
        
        logger.info(f"読み込み済み画像数: {len(loaded_images)}")
        
        logger.info("3. マテリアル再構築テスト")
        
        # マテリアル再構築をテスト
        created_materials = 0
        for material_name, material_info in texture_data.get("materials", {}).items():
            try:
                system._rebuild_material(material_name, material_info, loaded_images)
                
                # 再構築されたマテリアルを確認
                if material_name in bpy.data.materials:
                    material = bpy.data.materials[material_name]
                    created_materials += 1
                    
                    if material.use_nodes:
                        nodes = list(material.node_tree.nodes)
                        links = list(material.node_tree.links)
                        image_nodes = [n for n in nodes if n.type == 'TEX_IMAGE' and n.image]
                        
                        logger.info(f"✅ マテリアル再構築: {material_name}")
                        logger.info(f"  ノード数: {len(nodes)}")
                        logger.info(f"  リンク数: {len(links)}")
                        logger.info(f"  画像付きノード数: {len(image_nodes)}")
                        
                        for img_node in image_nodes:
                            logger.info(f"    画像ノード: {img_node.image.name}")
                    else:
                        logger.warning(f"⚠️ マテリアル {material_name} はノードを使用していません")
                else:
                    logger.warning(f"❌ マテリアル {material_name} が作成されませんでした")
                    
            except Exception as e:
                logger.error(f"❌ マテリアル再構築失敗: {material_name} - {e}")
        
        logger.info(f"作成されたマテリアル数: {created_materials}")
        
        logger.info("4. メッシュ-マテリアル割り当てテスト")
        
        # メッシュにマテリアルを割り当て
        try:
            system._assign_materials_to_meshes(texture_data.get("mesh_materials", {}))
            
            # 割り当て結果を確認
            for obj in bpy.data.objects:
                if obj.type == 'MESH':
                    materials = [slot.material.name if slot.material else "None" for slot in obj.material_slots]
                    logger.info(f"メッシュ {obj.name}: マテリアル {materials}")
                    
        except Exception as e:
            logger.error(f"❌ マテリアル割り当て失敗: {e}")
        
        logger.info("5. FBXエクスポート前の状態確認")
        
        final_materials = list(bpy.data.materials)
        final_images = list(bpy.data.images)
        
        logger.info(f"エクスポート前の状態:")
        logger.info(f"  マテリアル数: {len(final_materials)}")
        logger.info(f"  画像数: {len(final_images)}")
        
        for material in final_materials:
            if material.use_nodes:
                image_nodes = [n for n in material.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image]
                logger.info(f"  マテリアル {material.name}: {len(image_nodes)} 個の画像ノード")
        
        logger.info("6. テストFBXエクスポート")
        
        # テスト用のFBXエクスポート
        test_output = "/app/debug_texture_export.fbx"
        
        try:
            bpy.ops.export_scene.fbx(
                filepath=test_output,
                use_selection=False,
                embed_textures=True,
                path_mode='COPY'
            )
            
            logger.info(f"✅ テストFBXエクスポート成功: {test_output}")
            
            # エクスポートされたファイルサイズを確認
            if os.path.exists(test_output):
                size = os.path.getsize(test_output) / (1024 * 1024)
                logger.info(f"エクスポートファイルサイズ: {size:.2f} MB")
            
        except Exception as e:
            logger.error(f"❌ テストFBXエクスポート失敗: {e}")
        
        logger.info("7. エクスポートされたFBXの検証")
        
        # エクスポートされたFBXを新しいシーンで確認
        if os.path.exists(test_output):
            try:
                bpy.ops.wm.read_factory_settings(use_empty=True)
                bpy.ops.import_scene.fbx(filepath=test_output)
                
                verify_materials = list(bpy.data.materials)
                verify_images = list(bpy.data.images)
                
                logger.info(f"検証結果:")
                logger.info(f"  インポートされたマテリアル数: {len(verify_materials)}")
                logger.info(f"  インポートされた画像数: {len(verify_images)}")
                
                for image in verify_images:
                    if hasattr(image, 'packed_file') and image.packed_file:
                        size = len(image.packed_file.data) / 1024
                        logger.info(f"  ✅ 埋め込み画像: {image.name} ({size:.1f} KB)")
                    else:
                        logger.info(f"  ⚠️ 参照画像: {image.name} - {image.filepath}")
                
            except Exception as e:
                logger.error(f"❌ 検証用FBXインポート失敗: {e}")
        
    except Exception as e:
        logger.error(f"デバッグ中にエラー: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()
