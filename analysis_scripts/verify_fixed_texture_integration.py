#!/usr/bin/env python3
"""
修正されたテクスチャ統合システムの最終検証
生成されたFBXファイルをBlenderで確認します。
"""

import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("=== 修正されたテクスチャ統合システムの最終検証 ===")
    
    try:
        import bpy
        
        # ファイルパス
        fixed_fbx = "/app/pipeline_work/06_final_output/bird/bird_final_textures_fixed.fbx"
        
        if not os.path.exists(fixed_fbx):
            logger.error(f"修正されたFBXファイルが見つかりません: {fixed_fbx}")
            return
        
        file_size = os.path.getsize(fixed_fbx) / (1024 * 1024)
        logger.info(f"修正されたFBXファイルサイズ: {file_size:.2f} MB")
        
        # Blenderシーンをクリア
        bpy.ops.wm.read_factory_settings(use_empty=True)
        
        # FBXをインポート
        logger.info("修正されたFBXをインポート中...")
        bpy.ops.import_scene.fbx(filepath=fixed_fbx)
        
        # インポート結果を確認
        objects = list(bpy.data.objects)
        meshes = [obj for obj in objects if obj.type == 'MESH']
        armatures = [obj for obj in objects if obj.type == 'ARMATURE']
        materials = list(bpy.data.materials)
        images = list(bpy.data.images)
        
        logger.info(f"インポート結果:")
        logger.info(f"  オブジェクト数: {len(objects)}")
        logger.info(f"  メッシュ数: {len(meshes)}")
        logger.info(f"  アーマチュア数: {len(armatures)}")
        logger.info(f"  マテリアル数: {len(materials)}")
        logger.info(f"  画像数: {len(images)}")
        
        # マテリアル詳細を確認
        for i, material in enumerate(materials):
            logger.info(f"マテリアル {i+1}: {material.name}")
            
            if material.use_nodes:
                nodes = list(material.node_tree.nodes)
                links = list(material.node_tree.links)
                logger.info(f"  ノード数: {len(nodes)}")
                logger.info(f"  リンク数: {len(links)}")
                
                # 重要なノードタイプをチェック
                principled_nodes = [n for n in nodes if n.type == 'BSDF_PRINCIPLED']
                image_nodes = [n for n in nodes if n.type == 'TEX_IMAGE']
                
                logger.info(f"  Principled BSDFノード: {len(principled_nodes)}")
                logger.info(f"  Image Textureノード: {len(image_nodes)}")
                
                # Image Textureノードの詳細
                for img_node in image_nodes:
                    if img_node.image:
                        logger.info(f"    画像ノード: {img_node.name} -> {img_node.image.name}")
                        logger.info(f"      画像サイズ: {img_node.image.size[0]}x{img_node.image.size[1]}")
                        logger.info(f"      ソース: {img_node.image.source}")
                        if hasattr(img_node.image, 'packed_file') and img_node.image.packed_file:
                            packed_size = len(img_node.image.packed_file.data) / 1024
                            logger.info(f"      埋め込みサイズ: {packed_size:.1f} KB")
                        else:
                            logger.info(f"      ファイルパス: {img_node.image.filepath}")
                    else:
                        logger.info(f"    画像ノード: {img_node.name} -> 画像未設定")
            
        # 画像の詳細
        logger.info("画像詳細:")
        for i, image in enumerate(images):
            logger.info(f"  画像 {i+1}: {image.name}")
            logger.info(f"    サイズ: {image.size[0]}x{image.size[1]}")
            logger.info(f"    ソース: {image.source}")
            if hasattr(image, 'packed_file') and image.packed_file:
                packed_size = len(image.packed_file.data) / 1024
                logger.info(f"    ✅ 埋め込み済み: {packed_size:.1f} KB")
            elif image.filepath:
                logger.info(f"    ファイル参照: {image.filepath}")
            else:
                logger.info(f"    ⚠️ ソース不明")
        
        # 成功判定
        embedded_images = [img for img in images if hasattr(img, 'packed_file') and img.packed_file]
        success = len(embedded_images) > 0 and len(materials) > 0
        
        if success:
            logger.info("✅ テクスチャ統合成功!")
            logger.info(f"✅ {len(embedded_images)} 個の画像が正常に埋め込まれました")
            logger.info(f"✅ {len(materials)} 個のマテリアルが復元されました")
        else:
            logger.warning("⚠️ テクスチャ埋め込みが不完全です")
            
    except Exception as e:
        logger.error(f"検証中にエラー: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()
