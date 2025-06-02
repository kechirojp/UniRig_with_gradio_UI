#!/usr/bin/env python3
"""
分析スクリプト：01_extracted_meshステップで生成された中間ファイルのテクスチャ情報を確認
"""

import bpy
import os
import sys

def analyze_extracted_mesh_fbx():
    """01_extracted_meshで生成されたskeleton.fbxを分析"""
    
    # シーンをクリア
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    fbx_path = "/app/pipeline_work/01_extracted_mesh/bird/skeleton.fbx"
    
    print(f"\n=== 01_extracted_mesh/skeleton.fbx分析 ===")
    print(f"ファイルパス: {fbx_path}")
    
    if not os.path.exists(fbx_path):
        print("❌ ファイルが存在しません")
        return
    
    # FBXファイルのサイズを確認
    file_size = os.path.getsize(fbx_path)
    print(f"ファイルサイズ: {file_size:,} バイト ({file_size/1024:.1f} KB)")
    
    try:
        # FBXをインポート
        bpy.ops.import_scene.fbx(filepath=fbx_path)
        
        # オブジェクトを確認
        objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
        print(f"メッシュオブジェクト数: {len(objects)}")
        
        for obj in objects:
            print(f"\n--- オブジェクト: {obj.name} ---")
            print(f"マテリアル数: {len(obj.data.materials)}")
            
            for i, material in enumerate(obj.data.materials):
                if material:
                    print(f"\nマテリアル[{i}]: {material.name}")
                    print(f"ノード使用: {material.use_nodes}")
                    
                    if material.use_nodes and material.node_tree:
                        nodes = material.node_tree.nodes
                        print(f"ノード数: {len(nodes)}")
                        
                        # 重要なノードを探す
                        principled = None
                        image_nodes = []
                        
                        for node in nodes:
                            print(f"  - {node.type}: {node.name}")
                            if node.type == 'BSDF_PRINCIPLED':
                                principled = node
                            elif node.type == 'TEX_IMAGE':
                                image_nodes.append(node)
                        
                        print(f"Principledノード: {'✅' if principled else '❌'}")
                        print(f"テクスチャノード数: {len(image_nodes)}")
                        
                        # テクスチャ情報を詳細確認
                        for img_node in image_nodes:
                            print(f"  テクスチャ: {img_node.name}")
                            if img_node.image:
                                print(f"    画像: {img_node.image.name}")
                                print(f"    サイズ: {img_node.image.size}")
                                print(f"    ファイルパス: {img_node.image.filepath}")
                            else:
                                print("    ❌ 画像データなし")
                        
                        # Principledノードの接続を確認
                        if principled:
                            print(f"\n  Principledノード接続状況:")
                            base_color_connected = bool(principled.inputs['Base Color'].links)
                            normal_connected = bool(principled.inputs['Normal'].links)
                            roughness_connected = bool(principled.inputs['Roughness'].links)
                            
                            print(f"    Base Color: {'✅' if base_color_connected else '❌'}")
                            print(f"    Normal: {'✅' if normal_connected else '❌'}")
                            print(f"    Roughness: {'✅' if roughness_connected else '❌'}")
                            
                            # 接続の詳細
                            if base_color_connected:
                                link = principled.inputs['Base Color'].links[0]
                                print(f"      Base Color <- {link.from_node.type}:{link.from_node.name}")
                else:
                    print(f"マテリアル[{i}]: None")
        
    except Exception as e:
        print(f"❌ エラー: {e}")

def compare_with_original():
    """元のbird.glbと比較"""
    
    # シーンをクリア
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    glb_path = "/app/examples/bird.glb"
    
    print(f"\n=== オリジナルbird.glb分析（比較用） ===")
    
    try:
        bpy.ops.import_scene.gltf(filepath=glb_path)
        
        objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
        print(f"メッシュオブジェクト数: {len(objects)}")
        
        for obj in objects:
            print(f"\n--- オブジェクト: {obj.name} ---")
            
            for i, material in enumerate(obj.data.materials):
                if material and material.use_nodes:
                    print(f"\nマテリアル[{i}]: {material.name}")
                    
                    # テクスチャノードを確認
                    image_nodes = [node for node in material.node_tree.nodes if node.type == 'TEX_IMAGE']
                    print(f"テクスチャノード数: {len(image_nodes)}")
                    
                    for img_node in image_nodes:
                        if img_node.image:
                            print(f"  テクスチャ: {img_node.image.name} ({img_node.image.size})")
    
    except Exception as e:
        print(f"❌ エラー: {e}")

if __name__ == "__main__":
    print("中間ファイルのテクスチャ情報分析開始...")
    analyze_extracted_mesh_fbx()
    compare_with_original()
    print("\n分析完了")
