#!/usr/bin/env python3

import bpy
import os
import sys

def analyze_specific_fbx(fbx_path):
    """特定のFBXファイルを詳細に分析"""
    print(f"=== FBXファイル詳細分析: {fbx_path} ===")
    
    if not os.path.exists(fbx_path):
        print(f"ファイルが存在しません: {fbx_path}")
        return False
    
    file_size = os.path.getsize(fbx_path)
    print(f"ファイルサイズ: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
    
    try:
        # シーンをクリア
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        
        # マテリアルとテクスチャをクリア
        for material in bpy.data.materials:
            bpy.data.materials.remove(material)
        for image in bpy.data.images:
            bpy.data.images.remove(image)
        
        # FBXファイルをインポート
        bpy.ops.import_scene.fbx(filepath=fbx_path)
        
        # インポートされたオブジェクトを分析
        print(f"\n=== インポートされたオブジェクト ({len(bpy.data.objects)}個) ===")
        for obj in bpy.data.objects:
            print(f"オブジェクト: {obj.name} (タイプ: {obj.type})")
            if obj.type == 'MESH':
                mesh = obj.data
                print(f"  - 頂点数: {len(mesh.vertices)}")
                print(f"  - 面数: {len(mesh.polygons)}")
                print(f"  - マテリアル数: {len(mesh.materials)}")
                
                # マテリアルの詳細分析
                for i, material in enumerate(mesh.materials):
                    if material:
                        print(f"    マテリアル[{i}]: {material.name}")
                        analyze_material_detailed(material, i)
            
            elif obj.type == 'ARMATURE':
                armature = obj.data
                print(f"  - ボーン数: {len(armature.bones)}")
        
        # 全マテリアルを分析
        print(f"\n=== 全マテリアル ({len(bpy.data.materials)}個) ===")
        for material in bpy.data.materials:
            analyze_material_detailed(material)
        
        # 全画像を分析
        print(f"\n=== 全画像 ({len(bpy.data.images)}個) ===")
        for image in bpy.data.images:
            analyze_image_detailed(image)
        
        return True
        
    except Exception as e:
        print(f"FBXファイルの読み込みエラー: {e}")
        return False

def analyze_material_detailed(material, index=None):
    """マテリアルの詳細分析"""
    if index is not None:
        print(f"    マテリアル[{index}]: {material.name}")
    else:
        print(f"マテリアル: {material.name}")
    
    print(f"      - use_nodes: {material.use_nodes}")
    
    if material.use_nodes and material.node_tree:
        print(f"      - ノードベースマテリアル")
        tree = material.node_tree
        print(f"      - ノード数: {len(tree.nodes)}")
        
        for node in tree.nodes:
            print(f"        ノード: {node.name} (タイプ: {node.type})")
            if node.type == 'TEX_IMAGE':
                if node.image:
                    print(f"          - 画像: {node.image.name}")
                    print(f"          - ソース: {node.image.source}")
                    if hasattr(node.image, 'filepath'):
                        print(f"          - パス: {node.image.filepath}")
                    if hasattr(node.image, 'packed_file') and node.image.packed_file:
                        print(f"          - パック済み: {node.image.packed_file.size:,} bytes")
                else:
                    print(f"          - 画像: なし")
            elif node.type == 'BSDF_PRINCIPLED':
                print(f"          - Principled BSDF ノード")
                # 入力の接続状況を確認
                for input_socket in node.inputs:
                    if input_socket.links:
                        print(f"            入力 '{input_socket.name}': 接続あり ({len(input_socket.links)})")
                    else:
                        print(f"            入力 '{input_socket.name}': 接続なし")
    else:
        print(f"      - 従来型マテリアル")
        
    # マテリアルプロパティも確認
    if hasattr(material, 'diffuse_color'):
        print(f"      - Diffuse Color: {material.diffuse_color[:3]}")

def analyze_image_detailed(image):
    """画像の詳細分析"""
    print(f"画像: {image.name}")
    print(f"  - ソース: {image.source}")
    print(f"  - サイズ: {image.size[0]}x{image.size[1]} pixels" if image.size[0] > 0 else "  - サイズ: 不明")
    print(f"  - チャンネル数: {image.channels}")
    print(f"  - 深度: {image.depth}")
    
    if hasattr(image, 'filepath') and image.filepath:
        print(f"  - ファイルパス: {image.filepath}")
    
    if hasattr(image, 'packed_file') and image.packed_file:
        print(f"  - パック済み: サイズ {image.packed_file.size:,} bytes")
    else:
        print(f"  - パック済み: なし")
    
    if hasattr(image, 'colorspace_settings'):
        print(f"  - カラースペース: {image.colorspace_settings.name}")

def main():
    """メイン関数"""
    # 特定のFBXファイルを分析
    fbx_path = "/app/pipeline_work/06_final_output/bird/bird_final.fbx"
    
    if os.path.exists(fbx_path):
        success = analyze_specific_fbx(fbx_path)
        if success:
            print("\n✓ FBX分析完了")
        else:
            print("\n✗ FBX分析失敗")
    else:
        print(f"ファイルが存在しません: {fbx_path}")

if __name__ == "__main__":
    main()
