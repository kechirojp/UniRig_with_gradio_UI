#!/usr/bin/env python3
"""
birdモデルをテクスチャ付きで完全に再生成し、パイプラインの各段階を確認
"""

import os
import sys
import logging
import shutil

# プロジェクトのrootディレクトリをPATHに追加
sys.path.append('/app')
sys.path.append('/app/src')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("=== birdモデルのテクスチャ付き完全再生成 ===")
    
    # 作業ディレクトリをクリア
    work_dir = "/app/pipeline_work"
    if os.path.exists(work_dir):
        logger.info("既存の作業ディレクトリをクリア...")
        shutil.rmtree(work_dir)
    os.makedirs(work_dir, exist_ok=True)
    
    try:
        import bpy
        
        # Blenderシーンをクリア
        bpy.ops.wm.read_factory_settings(use_empty=True)
        
        # 元のbird.glbファイルを確認
        original_glb = "/app/examples/bird.glb"
        if not os.path.exists(original_glb):
            logger.error(f"元のGLBファイルが見つかりません: {original_glb}")
            return
        
        file_size = os.path.getsize(original_glb) / (1024 * 1024)
        logger.info(f"元のGLBファイルサイズ: {file_size:.2f} MB")
        
        # GLBをインポート
        logger.info("元のGLBをインポート中...")
        bpy.ops.import_scene.gltf(filepath=original_glb)
        
        # インポート結果を確認
        objects = list(bpy.data.objects)
        meshes = [obj for obj in objects if obj.type == 'MESH']
        materials = list(bpy.data.materials)
        images = list(bpy.data.images)
        
        logger.info(f"GLBインポート結果:")
        logger.info(f"  オブジェクト数: {len(objects)}")
        logger.info(f"  メッシュ数: {len(meshes)}")
        logger.info(f"  マテリアル数: {len(materials)}")
        logger.info(f"  画像数: {len(images)}")
        
        # 画像の詳細を確認
        for i, image in enumerate(images):
            logger.info(f"  画像 {i+1}: {image.name}, サイズ: {image.size[0]}x{image.size[1]}, パック: {image.packed_file is not None}")
        
        # マテリアルの詳細を確認
        for i, material in enumerate(materials):
            logger.info(f"  マテリアル {i+1}: {material.name}")
            if material.use_nodes:
                nodes = material.node_tree.nodes
                logger.info(f"    ノード数: {len(nodes)}")
                for node in nodes:
                    logger.info(f"      - {node.type}: {node.name}")
        
        # メッシュにマテリアルが割り当てられているかを確認
        for mesh_obj in meshes:
            logger.info(f"メッシュ '{mesh_obj.name}': マテリアル {[slot.material.name if slot.material else 'None' for slot in mesh_obj.material_slots]}")
        
        # 一時的にOBJとして保存（テクスチャ無し）
        temp_obj = "/app/pipeline_work/bird_temp.obj"
        logger.info(f"一時OBJファイルとして保存: {temp_obj}")
        
        # メッシュオブジェクトを選択
        bpy.ops.object.select_all(action='DESELECT')
        for obj in meshes:
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
        
        # OBJエクスポート
        bpy.ops.wm.obj_export(
            filepath=temp_obj,
            export_selected_objects=True,
            export_materials=False,  # マテリアルは後で復元
            export_triangulated_mesh=True
        )
        
        # 実際のUniRigパイプラインを実行
        logger.info("=== UniRigパイプラインの実行 ===")
        
        # パイプラインのインポート
        from app import gradio_full_auto_rigging
        
        # オートリギング実行
        logger.info("オートリギング実行中...")
        result = gradio_full_auto_rigging(
            temp_obj,
            "neutral"
        )
        
        if result and len(result) >= 3:
            logger.info("オートリギング成功!")
            
            # 結果ファイルを確認
            final_display_path = result[0]  # 最終表示モデル
            logs = result[1]  # ログ
            final_merged_fbx_path = result[2]  # 最終マージFBX
            
            logger.info(f"最終表示モデル: {final_display_path}")
            logger.info(f"最終マージFBX: {final_merged_fbx_path}")
            
            # 実際に作成されたFBXファイルを確認
            output_fbx = final_merged_fbx_path
            if output_fbx and os.path.exists(output_fbx):
                output_size = os.path.getsize(output_fbx) / (1024 * 1024)
                logger.info(f"出力FBXファイル: {output_fbx}")
                logger.info(f"出力FBXサイズ: {output_size:.2f} MB")
                
                # 出力FBXを検証
                logger.info("出力FBXを検証中...")
                bpy.ops.wm.read_factory_settings(use_empty=True)
                bpy.ops.import_scene.fbx(filepath=output_fbx)
                
                # 結果を確認
                final_objects = list(bpy.data.objects)
                final_meshes = [obj for obj in final_objects if obj.type == 'MESH']
                final_armatures = [obj for obj in final_objects if obj.type == 'ARMATURE']
                final_materials = list(bpy.data.materials)
                final_images = list(bpy.data.images)
                
                logger.info(f"最終出力結果:")
                logger.info(f"  オブジェクト数: {len(final_objects)}")
                logger.info(f"  メッシュ数: {len(final_meshes)}")
                logger.info(f"  アーマチュア数: {len(final_armatures)}")
                logger.info(f"  マテリアル数: {len(final_materials)}")
                logger.info(f"  画像数: {len(final_images)}")
                
                # マテリアルが失われていることを確認
                if len(final_materials) == 0:
                    logger.warning("⚠️ マテリアルが失われました！テクスチャ統合システムを適用します...")
                    
                    # テクスチャ統合システムをインポート
                    from texture_preservation_system import TexturePreservationSystem
                    
                    # テクスチャ統合システムの適用
                    texture_system = TexturePreservationSystem()
                    
                    # 元のGLBから必要なデータを抽出
                    logger.info("元のGLBからテクスチャデータを抽出中...")
                    bpy.ops.wm.read_factory_settings(use_empty=True)
                    bpy.ops.import_scene.gltf(filepath=original_glb)
                    
                    # テクスチャデータを保存
                    output_dir = "/app/pipeline_work/extracted_textures"
                    os.makedirs(output_dir, exist_ok=True)
                    
                    texture_system.extract_textures(output_dir)
                    
                    # FBXファイルにテクスチャを統合
                    enhanced_fbx = output_fbx.replace('.fbx', '_with_textures.fbx')
                    success = texture_system.enhance_fbx_with_textures(
                        output_fbx,
                        output_dir,
                        enhanced_fbx
                    )
                    
                    if success:
                        enhanced_size = os.path.getsize(enhanced_fbx) / (1024 * 1024)
                        logger.info(f"✅ テクスチャ統合成功: {enhanced_fbx}")
                        logger.info(f"✅ 統合後サイズ: {enhanced_size:.2f} MB")
                        
                        # 最終検証
                        logger.info("最終検証中...")
                        bpy.ops.wm.read_factory_settings(use_empty=True)
                        bpy.ops.import_scene.fbx(filepath=enhanced_fbx)
                        
                        verify_objects = list(bpy.data.objects)
                        verify_materials = list(bpy.data.materials)
                        verify_images = list(bpy.data.images)
                        
                        logger.info(f"最終検証結果:")
                        logger.info(f"  オブジェクト数: {len(verify_objects)}")
                        logger.info(f"  マテリアル数: {len(verify_materials)}")
                        logger.info(f"  画像数: {len(verify_images)}")
                        
                        if len(verify_materials) > 0 and len(verify_images) > 0:
                            logger.info("✅ テクスチャ統合システムが正常に動作しました！")
                        else:
                            logger.error("❌ テクスチャ統合システムでも問題が発生しています")
                    else:
                        logger.error("❌ テクスチャ統合に失敗しました")
                else:
                    logger.info("✅ マテリアルが正常に保持されています")
            else:
                logger.error("出力FBXファイルが見つかりません")
        else:
            logger.error(f"オートリギング失敗: 戻り値が不正です")
            
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
