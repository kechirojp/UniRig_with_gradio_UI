#!/usr/bin/env python3

import bpy
import os
import sys
from pathlib import Path

def clear_scene():
    """シーンをクリア"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # マテリアルとテクスチャをクリア
    for material in bpy.data.materials:
        bpy.data.materials.remove(material)
    for image in bpy.data.images:
        bpy.data.images.remove(image)

def analyze_fbx_content(fbx_path):
    """FBXファイルの内容を詳細に分析"""
    print(f"=== FBXファイル詳細分析: {fbx_path} ===")
    
    if not os.path.exists(fbx_path):
        print(f"ファイルが存在しません: {fbx_path}")
        return False
    
    file_size = os.path.getsize(fbx_path)
    print(f"ファイルサイズ: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
    
    try:
        # シーンをクリア
        clear_scene()
        
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
                        analyze_material(material, i)
            
            elif obj.type == 'ARMATURE':
                armature = obj.data
                print(f"  - ボーン数: {len(armature.bones)}")
        
        # 全マテリアルを分析
        print(f"\n=== 全マテリアル ({len(bpy.data.materials)}個) ===")
        for material in bpy.data.materials:
            analyze_material(material)
        
        # 全画像を分析
        print(f"\n=== 全画像 ({len(bpy.data.images)}個) ===")
        for image in bpy.data.images:
            analyze_image(image)
        
        return True
        
    except Exception as e:
        print(f"FBXファイルの読み込みエラー: {e}")
        return False

def analyze_material(material, index=None):
    """マテリアルの詳細分析"""
    if index is not None:
        print(f"  マテリアル[{index}]: {material.name}")
    else:
        print(f"マテリアル: {material.name}")
    
    if material.use_nodes:
        print(f"    - ノードベースマテリアル")
        tree = material.node_tree
        print(f"    - ノード数: {len(tree.nodes)}")
        
        for node in tree.nodes:
            print(f"      ノード: {node.name} (タイプ: {node.type})")
            if node.type == 'TEX_IMAGE':
                if node.image:
                    print(f"        - 画像: {node.image.name}")
                    print(f"        - ソース: {node.image.source}")
                    if hasattr(node.image, 'filepath'):
                        print(f"        - パス: {node.image.filepath}")
                else:
                    print(f"        - 画像: なし")
    else:
        print(f"    - 従来型マテリアル")
        # 従来型マテリアルのテクスチャスロットを確認
        if hasattr(material, 'texture_slots'):
            for i, slot in enumerate(material.texture_slots):
                if slot and slot.texture:
                    print(f"      テクスチャスロット[{i}]: {slot.texture.name}")

def analyze_image(image):
    """画像の詳細分析"""
    print(f"画像: {image.name}")
    print(f"  - ソース: {image.source}")
    print(f"  - サイズ: {image.size[0]}x{image.size[1]} pixels" if image.size[0] > 0 else "  - サイズ: 不明")
    
    if hasattr(image, 'filepath') and image.filepath:
        print(f"  - ファイルパス: {image.filepath}")
    
    if hasattr(image, 'packed_file') and image.packed_file:
        print(f"  - パック済み: サイズ {image.packed_file.size:,} bytes")
    else:
        print(f"  - パック済み: なし")

def main():
    """メイン関数"""
    # 分析するFBXファイルのリスト
    fbx_files = [
        "/app/pipeline_work/03_skinning_output/bird/skinned_model.fbx",
        "/app/pipeline_work/01_extracted_mesh/bird/skeleton.fbx"
    ]
    
    for fbx_path in fbx_files:
        if os.path.exists(fbx_path):
            success = analyze_fbx_content(fbx_path)
            print("\n" + "="*80 + "\n")
        else:
            print(f"ファイルが存在しません: {fbx_path}")

if __name__ == "__main__":
    main()
