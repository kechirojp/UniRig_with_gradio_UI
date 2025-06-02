#!/usr/bin/env python3

import os
import sys
import struct
import zipfile
from pathlib import Path

def analyze_fbx_structure(fbx_path):
    """FBXファイルの構造とテクスチャ情報を分析"""
    print(f"=== FBXファイル分析: {fbx_path} ===")
    
    # ファイルサイズ確認
    file_size = os.path.getsize(fbx_path)
    print(f"ファイルサイズ: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
    
    # FBXヘッダー分析
    with open(fbx_path, 'rb') as f:
        # FBXマジックバイト確認
        magic = f.read(20)
        print(f"FBXマジックバイト: {magic[:20]}")
        
        # FBXバージョン
        f.seek(23)
        version_bytes = f.read(4)
        if len(version_bytes) == 4:
            version = struct.unpack('<I', version_bytes)[0]
            print(f"FBXバージョン: {version}")
        
        # ファイル内容をテキストとして読み取り（部分的）
        f.seek(0)
        content = f.read(min(file_size, 100000))  # 最初の100KBのみ
        content_str = content.decode('latin-1', errors='ignore')
        
        # テクスチャ関連キーワードを検索
        texture_keywords = [
            'Texture', 'texture', 'TEXTURE',
            'Material', 'material', 'MATERIAL',
            'Image', 'image', 'IMAGE',
            'DiffuseColor', 'BaseColor', 'Albedo',
            '.png', '.jpg', '.jpeg', '.bmp', '.tga',
            'Connections', 'connections',
            'Video', 'video'
        ]
        
        print("\n=== テクスチャ関連情報 ===")
        texture_found = False
        for keyword in texture_keywords:
            count = content_str.count(keyword)
            if count > 0:
                print(f"'{keyword}': {count}回出現")
                texture_found = True
        
        if not texture_found:
            print("テクスチャ関連の情報が見つかりませんでした")
        
        # マテリアル関連情報
        print("\n=== マテリアル関連情報 ===")
        material_keywords = ['ShadingModel', 'Lambert', 'Phong', 'Standard']
        for keyword in material_keywords:
            count = content_str.count(keyword)
            if count > 0:
                print(f"'{keyword}': {count}回出現")
        
        # メッシュ情報
        print("\n=== メッシュ情報 ===")
        mesh_keywords = ['Geometry', 'Vertices', 'PolygonVertexIndex', 'Normals']
        for keyword in mesh_keywords:
            count = content_str.count(keyword)
            if count > 0:
                print(f"'{keyword}': {count}回出現")
        
        # アーマチュア/スケルトン情報
        print("\n=== スケルトン情報 ===")
        skeleton_keywords = ['Armature', 'Bone', 'Deformer', 'Cluster', 'Skin']
        for keyword in skeleton_keywords:
            count = content_str.count(keyword)
            if count > 0:
                print(f"'{keyword}': {count}回出現")

def analyze_directory_textures(directory):
    """ディレクトリ内のテクスチャファイルを確認"""
    print(f"\n=== ディレクトリ内テクスチャ確認: {directory} ===")
    
    texture_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.tga', '.tiff']
    texture_files = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if any(file.lower().endswith(ext) for ext in texture_extensions):
                file_path = os.path.join(root, file)
                file_size = os.path.getsize(file_path)
                texture_files.append((file_path, file_size))
    
    if texture_files:
        print(f"テクスチャファイルが{len(texture_files)}個見つかりました:")
        for file_path, file_size in texture_files:
            print(f"  {file_path}: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    else:
        print("テクスチャファイルが見つかりませんでした")

def main():
    # 最新のFBXファイルを分析
    fbx_files = [
        "/app/pipeline_work/03_skinning_output/bird/skinned_model.fbx",
        "/app/pipeline_work/01_extracted_mesh/bird/skeleton.fbx"
    ]
    
    for fbx_path in fbx_files:
        if os.path.exists(fbx_path):
            analyze_fbx_structure(fbx_path)
            print("\n" + "="*60 + "\n")
    
    # 関連ディレクトリのテクスチャファイルを確認
    directories = [
        "/app/pipeline_work/03_skinning_output/bird",
        "/app/pipeline_work/01_extracted_mesh/bird",
        "/tmp/test_texture_extraction"
    ]
    
    for directory in directories:
        if os.path.exists(directory):
            analyze_directory_textures(directory)

if __name__ == "__main__":
    main()
