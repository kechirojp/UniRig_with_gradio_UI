#!/usr/bin/env python3
"""
簡略版テクスチャ統合テスト
UniRigパイプラインでテクスチャが失われる問題を特定し修正
"""

import os
import sys
import logging

# プロジェクトのrootディレクトリをPATHに追加
sys.path.append('/app')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("=== 簡略版テクスチャ統合問題診断 ===")
    
    # テスト用のシンプルなOBJファイルを作成
    test_obj = "/app/pipeline_work/simple_test.obj"
    os.makedirs("/app/pipeline_work", exist_ok=True)
    
    try:
        import bpy
        
        # Blenderシーンをクリア
        bpy.ops.wm.read_factory_settings(use_empty=True)
        
        # 元のbird.glbファイルを確認
        original_glb = "/app/examples/bird.glb"
        if not os.path.exists(original_glb):
            logger.error(f"元のGLBファイルが見つかりません: {original_glb}")
            return
        
        # GLBをインポート
        logger.info("元のGLBをインポート中...")
        bpy.ops.import_scene.gltf(filepath=original_glb)
        
        # マテリアル情報を確認
        materials = list(bpy.data.materials)
        images = list(bpy.data.images)
        
        logger.info(f"インポート結果: {len(materials)}マテリアル, {len(images)}画像")
        
        # 簡単なOBJとして保存（マテリアル無し）
        logger.info(f"簡易OBJファイルとして保存: {test_obj}")
        
        # メッシュオブジェクトを選択
        bpy.ops.object.select_all(action='DESELECT')
        meshes = [obj for obj in bpy.data.objects if obj.type == 'MESH']
        for obj in meshes:
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
        
        # OBJエクスポート
        bpy.ops.wm.obj_export(
            filepath=test_obj,
            export_selected_objects=True,
            export_materials=False,
            export_triangulated_mesh=True
        )
        
        logger.info("=== UniRigパイプライン実行 ===")
        
        # 設定をロード
        from app import load_app_config
        logger.info("アプリケーション設定をロード中...")
        load_app_config('/app/configs/app_config.yaml')
        
        # パイプラインの実行
        from app import gradio_full_auto_rigging
        
        logger.info("フルパイプライン実行中...")
        results = gradio_full_auto_rigging(test_obj, "neutral")
        
        # 結果を詳しく確認
        logger.info(f"戻り値数: {len(results)}")
        for i, result in enumerate(results):
            if isinstance(result, str) and result:
                if os.path.exists(result):
                    size = os.path.getsize(result) / (1024 * 1024)
                    logger.info(f"結果 {i}: {result} ({size:.2f} MB)")
                else:
                    logger.info(f"結果 {i}: {result} (ファイル不存在)")
            else:
                result_preview = str(result)[:100] if result else 'None'
                logger.info(f"結果 {i}: {result_preview}")
        
        # 最終FBXファイルを確認
        final_merged_fbx_path = results[2]  # full_final_model_download_accordion
        
        if final_merged_fbx_path and os.path.exists(final_merged_fbx_path):
            logger.info("✅ 最終FBXファイル生成成功")
            
            # FBXファイルのテクスチャ内容を確認
            logger.info("最終FBXファイルのテクスチャ内容を確認中...")
            bpy.ops.wm.read_factory_settings(use_empty=True)
            bpy.ops.import_scene.fbx(filepath=final_merged_fbx_path)
            
            final_objects = list(bpy.data.objects)
            final_materials = list(bpy.data.materials)
            final_images = list(bpy.data.images)
            
            logger.info(f"最終FBX結果:")
            logger.info(f"  オブジェクト数: {len(final_objects)}")
            logger.info(f"  マテリアル数: {len(final_materials)}")
            logger.info(f"  画像数: {len(final_images)}")
            
            if len(final_materials) > 0 and len(final_images) > 0:
                logger.info("✅ テクスチャ統合システムが正常に動作しています！")
                
                # 画像の詳細を確認
                for i, image in enumerate(final_images):
                    logger.info(f"  画像 {i+1}: {image.name}, サイズ: {image.size[0]}x{image.size[1]}")
                
                # マテリアルの詳細を確認
                for i, material in enumerate(final_materials):
                    logger.info(f"  マテリアル {i+1}: {material.name}")
                    if material.use_nodes:
                        nodes = material.node_tree.nodes
                        logger.info(f"    ノード数: {len(nodes)}")
                
                return True
            else:
                logger.error("❌ 最終FBXファイルにマテリアルが含まれていません")
                return False
        else:
            logger.error("❌ 最終FBXファイルが生成されませんでした")
            return False
            
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 テクスチャ統合システムは正常に動作しています！")
    else:
        print("\n❌ テクスチャ統合に問題があります")
