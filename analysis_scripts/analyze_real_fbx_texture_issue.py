#!/usr/bin/env python3
"""
実際のテクスチャ付きFBXファイルでのマテリアル保持問題詳細調査
"""

import os
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_real_fbx_texture_issue():
    """実際のテクスチャ付きFBXファイルでの問題を分析"""
    
    try:
        import bpy
        
        # 実際のテクスチャ付きFBXファイルパス
        fixed_fbx = "/app/pipeline_work/06_final_output/bird/bird_final_textures_fixed.fbx"
        
        if not os.path.exists(fixed_fbx):
            logger.error(f"FBXファイルが見つかりません: {fixed_fbx}")
            return
        
        def analyze_detailed_material_state(prefix=""):
            """詳細なマテリアル状態分析"""
            
            result = {
                'scene_info': {
                    'objects': len(bpy.data.objects),
                    'mesh_objects': len([obj for obj in bpy.data.objects if obj.type == 'MESH']),
                    'materials': len(bpy.data.materials),
                    'images': len([img for img in bpy.data.images if img.name not in ['Render Result', 'Viewer Node']]),
                },
                'materials': [],
                'images': []
            }
            
            # マテリアル詳細分析
            for material in bpy.data.materials:
                mat_info = {
                    'name': material.name,
                    'use_nodes': material.use_nodes,
                    'users': material.users,
                    'node_tree_info': None
                }
                
                if material.use_nodes and material.node_tree:
                    nodes = material.node_tree.nodes
                    links = material.node_tree.links
                    
                    # ノード情報を収集
                    node_details = []
                    for node in nodes:
                        node_info = {
                            'name': node.name,
                            'type': node.type,
                            'inputs': len(node.inputs),
                            'outputs': len(node.outputs)
                        }
                        
                        # TEX_IMAGEノードの場合、画像情報も取得
                        if node.type == 'TEX_IMAGE' and hasattr(node, 'image') and node.image:
                            node_info['image'] = {
                                'name': node.image.name,
                                'size': getattr(node.image, 'size', [0, 0]),
                                'colorspace': getattr(node.image.colorspace_settings, 'name', 'Unknown'),
                                'filepath': getattr(node.image, 'filepath', ''),
                                'packed': hasattr(node.image, 'packed_file') and node.image.packed_file is not None
                            }
                        
                        node_details.append(node_info)
                    
                    # リンク情報を収集
                    link_details = []
                    for link in links:
                        link_info = {
                            'from_node': link.from_node.name,
                            'from_socket': link.from_socket.name,
                            'to_node': link.to_node.name,
                            'to_socket': link.to_socket.name
                        }
                        link_details.append(link_info)
                    
                    mat_info['node_tree_info'] = {
                        'nodes': node_details,
                        'links': link_details,
                        'node_count': len(nodes),
                        'link_count': len(links)
                    }
                
                result['materials'].append(mat_info)
            
            # 画像詳細分析
            for image in bpy.data.images:
                if image.name not in ['Render Result', 'Viewer Node']:
                    img_info = {
                        'name': image.name,
                        'size': getattr(image, 'size', [0, 0]),
                        'colorspace': getattr(image.colorspace_settings, 'name', 'Unknown'),
                        'filepath': getattr(image, 'filepath', ''),
                        'packed': hasattr(image, 'packed_file') and image.packed_file is not None,
                        'users': image.users
                    }
                    result['images'].append(img_info)
            
            logger.info(f"{prefix}詳細マテリアル状態:")
            logger.info(f"  シーン情報: {json.dumps(result['scene_info'], indent=2, ensure_ascii=False)}")
            logger.info(f"  マテリアル数: {len(result['materials'])}")
            logger.info(f"  画像数: {len(result['images'])}")
            
            # 各マテリアルの詳細をログ出力
            for i, mat in enumerate(result['materials']):
                logger.info(f"  マテリアル {i+1}: {mat['name']}")
                if mat['node_tree_info']:
                    logger.info(f"    ノード数: {mat['node_tree_info']['node_count']}")
                    logger.info(f"    リンク数: {mat['node_tree_info']['link_count']}")
                    
                    # TEX_IMAGEノードの詳細
                    tex_nodes = [n for n in mat['node_tree_info']['nodes'] if n['type'] == 'TEX_IMAGE']
                    if tex_nodes:
                        logger.info(f"    テクスチャノード数: {len(tex_nodes)}")
                        for tex_node in tex_nodes:
                            if 'image' in tex_node:
                                logger.info(f"      - {tex_node['image']['name']} ({tex_node['image']['size']}) packed:{tex_node['image']['packed']}")
            
            return result
        
        def test_fbx_reexport():
            """FBX再エクスポートテスト"""
            
            logger.info("=== FBX再エクスポートテスト ===")
            
            # 元のFBXをインポート
            logger.info("元のFBXをインポート中...")
            bpy.ops.wm.read_factory_settings(use_empty=True)
            bpy.ops.import_scene.fbx(filepath=fixed_fbx)
            
            original_state = analyze_detailed_material_state("インポート直後: ")
            
            # 画像をパック（埋め込み）
            logger.info("画像をパック（埋め込み）中...")
            packed_count = 0
            for img in bpy.data.images:
                if img.name not in ['Render Result', 'Viewer Node']:
                    if not (hasattr(img, 'packed_file') and img.packed_file):
                        try:
                            img.pack()
                            packed_count += 1
                            logger.info(f"画像をパックしました: {img.name}")
                        except Exception as e:
                            logger.warning(f"画像のパックに失敗: {img.name} - {e}")
                    else:
                        logger.info(f"画像は既にパック済み: {img.name}")
            
            logger.info(f"パックした画像数: {packed_count}")
            
            # 詳細なFBXエクスポート設定でテスト
            reexport_path = "/app/debug_reexport_test.fbx"
            
            logger.info("FBX再エクスポート実行中...")
            bpy.ops.export_scene.fbx(
                filepath=reexport_path,
                use_selection=False,
                # Object selection
                object_types={'MESH', 'ARMATURE'},
                # Transform options
                axis_forward='-Z',
                axis_up='Y',
                global_scale=1.0,
                # Geometry options  
                use_mesh_modifiers=True,
                use_mesh_edges=False,
                # Material and texture options
                path_mode='COPY',  # Copy textures
                embed_textures=True,  # Embed in FBX
                # Animation options
                bake_anim=False,
                # Advanced options
                use_custom_props=True,
                add_leaf_bones=False,
                primary_bone_axis='Y',
                secondary_bone_axis='X',
                # Texture options
                use_tspace=True,
                mesh_smooth_type='OFF'
            )
            
            logger.info(f"FBX再エクスポート完了: {reexport_path}")
            
            # 再エクスポートしたFBXをインポートしてテスト
            logger.info("再エクスポートしたFBXをインポート中...")
            bpy.ops.wm.read_factory_settings(use_empty=True)
            bpy.ops.import_scene.fbx(filepath=reexport_path)
            
            reexport_state = analyze_detailed_material_state("再エクスポート後: ")
            
            # 比較分析
            logger.info("=== 比較分析結果 ===")
            
            original_materials = original_state['scene_info']['materials']
            original_images = original_state['scene_info']['images']
            reexport_materials = reexport_state['scene_info']['materials']
            reexport_images = reexport_state['scene_info']['images']
            
            logger.info(f"マテリアル数: {original_materials} → {reexport_materials}")
            logger.info(f"画像数: {original_images} → {reexport_images}")
            
            if original_materials != reexport_materials:
                logger.error("❌ マテリアル数が変化しました！")
            else:
                logger.info("✅ マテリアル数は保持されました")
            
            if original_images != reexport_images:
                logger.error("❌ 画像数が変化しました！")
            else:
                logger.info("✅ 画像数は保持されました")
            
            # ファイルサイズ比較
            original_size = os.path.getsize(fixed_fbx) / (1024 * 1024)
            reexport_size = os.path.getsize(reexport_path) / (1024 * 1024)
            logger.info(f"ファイルサイズ: {original_size:.2f}MB → {reexport_size:.2f}MB")
            
            return original_state, reexport_state
        
        # メインテスト実行
        logger.info("実際のテクスチャ付きFBXファイルでの問題分析を開始...")
        
        if not os.path.exists(fixed_fbx):
            logger.error("テスト対象のFBXファイルが見つかりません")
            return
        
        file_size = os.path.getsize(fixed_fbx) / (1024 * 1024)
        logger.info(f"テスト対象FBXファイル: {fixed_fbx} ({file_size:.2f}MB)")
        
        # FBX再エクスポートテスト実行
        original_state, reexport_state = test_fbx_reexport()
        
        logger.info("=== 最終結論 ===")
        
        # マテリアルのテクスチャ接続状況を分析
        def analyze_texture_connections(state, label):
            logger.info(f"{label} テクスチャ接続状況:")
            for mat in state['materials']:
                if mat['node_tree_info']:
                    tex_nodes = [n for n in mat['node_tree_info']['nodes'] if n['type'] == 'TEX_IMAGE']
                    principled_nodes = [n for n in mat['node_tree_info']['nodes'] if n['type'] == 'BSDF_PRINCIPLED']
                    
                    logger.info(f"  マテリアル '{mat['name']}':")
                    logger.info(f"    TEX_IMAGEノード: {len(tex_nodes)}")
                    logger.info(f"    BSDF_PRINCIPLEDノード: {len(principled_nodes)}")
                    
                    # リンク分析
                    if mat['node_tree_info']['links']:
                        texture_links = [l for l in mat['node_tree_info']['links'] 
                                       if any(n['name'] == l['from_node'] and n['type'] == 'TEX_IMAGE' 
                                             for n in mat['node_tree_info']['nodes'])]
                        logger.info(f"    テクスチャからの接続: {len(texture_links)}")
                        for link in texture_links[:3]:  # 最初の3つを表示
                            logger.info(f"      {link['from_node']} → {link['to_node']}.{link['to_socket']}")
        
        analyze_texture_connections(original_state, "元データ")
        analyze_texture_connections(reexport_state, "再エクスポート後")
        
    except Exception as e:
        logger.error(f"分析中にエラーが発生しました: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    analyze_real_fbx_texture_issue()
