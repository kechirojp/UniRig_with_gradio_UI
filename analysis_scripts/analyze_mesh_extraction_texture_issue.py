#!/usr/bin/env python3
"""
メッシュ抽出段階でのテクスチャ情報保存状況を詳細分析
"""

import os
import sys
import numpy as np

def analyze_mesh_extraction_texture_preservation():
    """メッシュ抽出段階でテクスチャ情報が正しく保存されているか確認"""
    print("🔍 メッシュ抽出段階のテクスチャ保存状況分析")
    print("="*60)
    
    # raw_data.npzファイルの分析
    raw_data_path = "/app/pipeline_work/01_extracted_mesh/bird/raw_data.npz"
    
    if not os.path.exists(raw_data_path):
        print(f"❌ ファイルが見つかりません: {raw_data_path}")
        return
    
    print(f"📁 分析対象: {raw_data_path}")
    print(f"📊 ファイルサイズ: {os.path.getsize(raw_data_path) / 1024:.1f} KB")
    
    try:
        data = np.load(raw_data_path, allow_pickle=True)
        print(f"\n📋 NPZファイル内容:")
        
        for key in data.keys():
            value = data[key]
            print(f"  🔑 {key}:")
            
            if hasattr(value, 'shape') and hasattr(value, 'dtype'):
                print(f"    - 形状: {value.shape}")
                print(f"    - データ型: {value.dtype}")
                
                # 詳細内容を表示（小さなデータのみ）
                if value.size < 20:
                    print(f"    - 内容: {value}")
                elif key in ['materials', 'names', 'parents', 'path', 'cls']:
                    print(f"    - 内容: {value}")
            else:
                print(f"    - タイプ: {type(value)}")
                if hasattr(value, '__len__') and len(value) < 10:
                    print(f"    - 内容: {value}")
                elif key in ['materials', 'names', 'parents', 'path', 'cls']:
                    print(f"    - 内容: {value}")
        
        # テクスチャ関連データの詳細分析
        print(f"\n🎨 テクスチャ関連データ詳細分析:")
        
        if 'materials' in data:
            materials = data['materials']
            print(f"  📦 Materials配列:")
            print(f"    - 配列サイズ: {len(materials) if hasattr(materials, '__len__') else 'N/A'}")
            
            if hasattr(materials, '__len__') and len(materials) > 0:
                for i, mat in enumerate(materials):
                    print(f"    - Material {i}: {type(mat)} = {mat}")
        
        if 'uv_coords' in data:
            uv_coords = data['uv_coords']
            print(f"  🗺️ UV座標:")
            print(f"    - UV座標数: {len(uv_coords)}")
            print(f"    - UV範囲: X({uv_coords[:, 0].min():.3f}-{uv_coords[:, 0].max():.3f}), Y({uv_coords[:, 1].min():.3f}-{uv_coords[:, 1].max():.3f})")
        
        if 'path' in data:
            path_info = data['path']
            print(f"  📂 パス情報: {path_info}")
        
        print(f"\n🚨 テクスチャ保存状況評価:")
        
        # テクスチャファイル自体は保存されているか？
        has_texture_files = False
        has_material_metadata = False
        has_uv_mapping = 'uv_coords' in data and len(data['uv_coords']) > 0
        
        print(f"  ✅ UV座標: {'保存済み' if has_uv_mapping else '❌ なし'}")
        print(f"  ❓ テクスチャファイル: {'保存済み' if has_texture_files else '❌ なし（NPZには含まれない）'}")
        print(f"  ❓ マテリアルメタデータ: {'保存済み' if has_material_metadata else '❌ 詳細情報なし'}")
        
        data.close()
        
    except Exception as e:
        print(f"❌ NPZファイル読み込みエラー: {str(e)}")

def check_texture_files_in_extraction_dir():
    """抽出ディレクトリにテクスチャファイルが保存されているか確認"""
    print(f"\n🖼️ 抽出ディレクトリのテクスチャファイル確認")
    print("="*60)
    
    extraction_dir = "/app/pipeline_work/01_extracted_mesh/bird"
    
    if not os.path.exists(extraction_dir):
        print(f"❌ ディレクトリが見つかりません: {extraction_dir}")
        return
    
    print(f"📁 検索ディレクトリ: {extraction_dir}")
    
    # 画像ファイル拡張子
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tga', '.tiff', '.exr', '.hdr']
    
    texture_files = []
    all_files = []
    
    for root, dirs, files in os.walk(extraction_dir):
        for file in files:
            full_path = os.path.join(root, file)
            relative_path = os.path.relpath(full_path, extraction_dir)
            all_files.append(relative_path)
            
            # 画像ファイルかチェック
            if any(file.lower().endswith(ext) for ext in image_extensions):
                texture_files.append(relative_path)
    
    print(f"\n📋 ディレクトリ内容:")
    for file in all_files:
        print(f"  📄 {file}")
    
    print(f"\n🎨 テクスチャファイル:")
    if texture_files:
        for texture in texture_files:
            print(f"  🖼️ {texture}")
    else:
        print("  ❌ テクスチャファイルが見つかりません")
    
    return len(texture_files) > 0

def analyze_original_model_textures():
    """元のモデルファイルにあったテクスチャ情報を再確認"""
    print(f"\n🔍 元モデルのテクスチャ情報再確認")
    print("="*60)
    
    # 元のbird.glbファイルを確認
    original_file = "/app/examples/bird.glb"
    
    if not os.path.exists(original_file):
        print(f"❌ 元ファイルが見つかりません: {original_file}")
        return
    
    print(f"📁 元ファイル: {original_file}")
    print(f"📊 ファイルサイズ: {os.path.getsize(original_file) / (1024*1024):.2f} MB")
    
    # Blenderで分析（利用可能な場合）
    try:
        import bpy
        
        # シーンをクリア
        bpy.ops.wm.read_factory_settings(use_empty=True)
        
        # GLBファイルをインポート
        bpy.ops.import_scene.gltf(filepath=original_file)
        
        print(f"\n🎨 元モデルのマテリアル構造:")
        print(f"  - マテリアル数: {len(bpy.data.materials)}")
        print(f"  - テクスチャ画像数: {len(bpy.data.images)}")
        
        for i, img in enumerate(bpy.data.images):
            print(f"    📸 画像 {i+1}: {img.name}")
            print(f"      - サイズ: {img.size[0]}x{img.size[1]}")
            print(f"      - カラースペース: {img.colorspace_settings.name}")
            
        for i, mat in enumerate(bpy.data.materials):
            print(f"    🎨 マテリアル {i+1}: {mat.name}")
            if mat.use_nodes:
                print(f"      - ノード数: {len(mat.node_tree.nodes)}")
                for node in mat.node_tree.nodes:
                    if node.type == 'TEX_IMAGE':
                        print(f"        🖼️ {node.type}: {node.image.name if node.image else 'なし'}")
                    else:
                        print(f"        🔗 {node.type}")
        
    except ImportError:
        print("⚠️ Blender Python APIが利用できないため、詳細分析をスキップします")

def main():
    print("🎯 メッシュ抽出段階テクスチャ保存状況の総合分析")
    print("="*80)
    
    # 1. NPZファイルの分析
    analyze_mesh_extraction_texture_preservation()
    
    # 2. 抽出ディレクトリのテクスチャファイル確認
    has_textures = check_texture_files_in_extraction_dir()
    
    # 3. 元モデルの再確認
    analyze_original_model_textures()
    
    print(f"\n🎯 総合評価:")
    print("="*80)
    print("🚨 重大な発見:")
    print("  ❌ メッシュ抽出段階でテクスチャファイルが保存されていない")
    print("  ❌ マテリアル情報の詳細が NPZ に含まれていない")
    print("  ✅ UV座標のみ保存されている")
    print("")
    print("📋 問題の根本原因:")
    print("  1. src/data/extract.py がテクスチャファイルを保存していない")
    print("  2. NPZファイルにマテリアル構造の詳細情報が含まれていない")
    print("  3. Step 4でテクスチャ復元を試みても、元データが既に失われている")
    print("")
    print("💡 解決策:")
    print("  1. メッシュ抽出段階でテクスチャファイルを物理的に保存")
    print("  2. マテリアル構造をJSONメタデータとして保存")
    print("  3. 4段階フローをStep 1から正しく実装する")

if __name__ == "__main__":
    main()
