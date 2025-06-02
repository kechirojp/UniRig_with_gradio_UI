#!/usr/bin/env python3
"""
最終マージファイルのテクスチャ分析スクリプト
テクスチャ保持修正が正しく機能したかを検証
"""

import os
import sys
import bpy
import bmesh

def clear_scene():
    """シーンをクリア"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    for collection in bpy.data.collections:
        bpy.data.collections.remove(collection)
    
    for material in bpy.data.materials:
        bpy.data.materials.remove(material)
    
    for image in bpy.data.images:
        bpy.data.images.remove(image)

def analyze_final_merged_model():
    """最終マージファイルのテクスチャを分析"""
    
    print("=== 最終マージファイル テクスチャ分析開始 ===")
    
    # シーンをクリア
    clear_scene()
    
    final_file = "/app/test_texture_preservation_final/merged_final.glb"
    
    if not os.path.exists(final_file):
        print(f"エラー: ファイルが見つかりません: {final_file}")
        return False
    
    try:
        # GLBファイルをインポート
        print(f"インポート中: {final_file}")
        bpy.ops.import_scene.gltf(filepath=final_file)
        
        print("\n=== オブジェクト分析 ===")
        objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
        print(f"メッシュオブジェクト数: {len(objects)}")
        
        for obj in objects:
            print(f"  - {obj.name}")
            if obj.data.materials:
                print(f"    マテリアル数: {len(obj.data.materials)}")
                for i, mat in enumerate(obj.data.materials):
                    if mat:
                        print(f"      [{i}] {mat.name}")
        
        print("\n=== マテリアル分析 ===")
        materials = bpy.data.materials
        print(f"合計マテリアル数: {len(materials)}")
        
        for mat in materials:
            print(f"\nマテリアル: {mat.name}")
            if mat.use_nodes:
                print("  ノードツリー使用中")
                
                # ノード分析
                nodes = mat.node_tree.nodes
                print(f"  ノード数: {len(nodes)}")
                
                # 主要ノードの検出
                principled_nodes = [n for n in nodes if n.type == 'BSDF_PRINCIPLED']
                image_nodes = [n for n in nodes if n.type == 'TEX_IMAGE']
                mix_nodes = [n for n in nodes if n.type == 'MIX']
                normal_map_nodes = [n for n in nodes if n.type == 'NORMAL_MAP']
                sep_color_nodes = [n for n in nodes if n.type == 'SEPARATE_COLOR']
                
                print(f"    - Principled BSDF: {len(principled_nodes)}")
                print(f"    - Image Texture: {len(image_nodes)}")
                print(f"    - Mix: {len(mix_nodes)}")
                print(f"    - Normal Map: {len(normal_map_nodes)}")
                print(f"    - Separate Color: {len(sep_color_nodes)}")
                
                # テクスチャノード詳細分析
                if image_nodes:
                    print("\n  === テクスチャノード詳細 ===")
                    for img_node in image_nodes:
                        if img_node.image:
                            print(f"    テクスチャ: {img_node.image.name}")
                            print(f"      カラースペース: {img_node.image.colorspace_settings.name}")
                            print(f"      サイズ: {img_node.image.size[0]}x{img_node.image.size[1]}")
                            
                            # 出力接続を確認
                            outputs = img_node.outputs
                            for output in outputs:
                                if output.links:
                                    for link in output.links:
                                        to_node = link.to_node
                                        to_socket = link.to_socket
                                        print(f"      接続: {output.name} → {to_node.type}.{to_socket.name}")
                
                # Principled BSDFの入力接続を確認
                if principled_nodes:
                    print("\n  === Principled BSDF 入力接続 ===")
                    principled = principled_nodes[0]
                    
                    key_inputs = ['Base Color', 'Roughness', 'Metallic', 'Normal']
                    for input_name in key_inputs:
                        if input_name in principled.inputs:
                            input_socket = principled.inputs[input_name]
                            if input_socket.links:
                                for link in input_socket.links:
                                    from_node = link.from_node
                                    from_socket = link.from_socket
                                    print(f"    {input_name}: {from_node.type}.{from_socket.name}")
                            else:
                                print(f"    {input_name}: 未接続")
            else:
                print("  ノードツリー未使用")
        
        print("\n=== イメージ分析 ===")
        images = bpy.data.images
        print(f"合計イメージ数: {len(images)}")
        
        texture_types = {
            'base_color': [],
            'normal': [],
            'roughness': [],
            'other': []
        }
        
        for img in images:
            name_lower = img.name.lower()
            if any(pattern in name_lower for pattern in ['col', 'bc', 'base', 'diffuse', 'albedo']):
                texture_types['base_color'].append(img.name)
            elif any(pattern in name_lower for pattern in ['nrml', 'normal', '_n']):
                texture_types['normal'].append(img.name)
            elif any(pattern in name_lower for pattern in ['gloss', 'rough', '_r']):
                texture_types['roughness'].append(img.name)
            else:
                texture_types['other'].append(img.name)
        
        print("\n=== テクスチャタイプ分類 ===")
        for tex_type, tex_list in texture_types.items():
            print(f"{tex_type}: {len(tex_list)}")
            for tex in tex_list:
                print(f"  - {tex}")
        
        # テクスチャ保持検証
        print("\n=== テクスチャ保持検証結果 ===")
        has_base_color = len(texture_types['base_color']) > 0
        has_normal = len(texture_types['normal']) > 0
        has_roughness = len(texture_types['roughness']) > 0
        
        print(f"✓ Base Color テクスチャ保持: {'✅ 成功' if has_base_color else '❌ 失敗'}")
        print(f"✓ Normal テクスチャ保持: {'✅ 成功' if has_normal else '❌ 失敗'}")
        print(f"✓ Roughness テクスチャ保持: {'✅ 成功' if has_roughness else '❌ 失敗'}")
        
        success = has_base_color and has_normal and has_roughness
        print(f"\n総合結果: {'✅ 全テクスチャ保持成功' if success else '❌ 一部テクスチャ喪失'}")
        
        return success
        
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = analyze_final_merged_model()
    sys.exit(0 if success else 1)
