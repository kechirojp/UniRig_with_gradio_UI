#!/usr/bin/env python3
"""
元の鳥モデルの完全分析 - 全テクスチャマップとマテリアル構造の詳細確認
"""

import os
import sys
import json

# Blenderがシステムにある場合のみインポート
try:
    import bpy
    BLENDER_AVAILABLE = True
except ImportError:
    BLENDER_AVAILABLE = False
    print("Blender Python API not available - skipping Blender analysis")

def analyze_original_bird_model():
    """元の鳥モデル（GLB）の完全分析"""
    original_model_path = "/app/examples/bird.glb"
    
    print(f"{'='*80}")
    print(f"🔍 元の鳥モデル完全分析")
    print(f"{'='*80}")
    print(f"📁 ファイルパス: {original_model_path}")
    
    if not os.path.exists(original_model_path):
        print(f"❌ ファイルが見つかりません: {original_model_path}")
        return
    
    # ファイルサイズ
    file_size = os.path.getsize(original_model_path) / (1024 * 1024)
    print(f"📏 ファイルサイズ: {file_size:.2f} MB")
    
    if not BLENDER_AVAILABLE:
        print("⚠️ Blender Python APIが利用できないため、詳細分析をスキップします")
        return
    
    try:
        # Blenderシーンをクリア
        bpy.ops.wm.read_factory_settings(use_empty=True)
        
        # GLBファイルをインポート
        print("📥 GLBファイルをインポート中...")
        bpy.ops.import_scene.gltf(filepath=original_model_path)
        
        print(f"\n🔍 基本構造分析:")
        print(f"  - オブジェクト数: {len(bpy.data.objects)}")
        print(f"  - メッシュ数: {len(bpy.data.meshes)}")
        print(f"  - マテリアル数: {len(bpy.data.materials)}")
        print(f"  - テクスチャ数: {len(bpy.data.images)}")
        print(f"  - カメラ数: {len(bpy.data.cameras)}")
        print(f"  - ライト数: {len(bpy.data.lights)}")
        
        # 全テクスチャ画像の詳細分析
        print(f"\n🖼️ 全テクスチャ画像詳細:")
        print(f"  総テクスチャ数: {len(bpy.data.images)}")
        for i, img in enumerate(bpy.data.images):
            print(f"  \n  📸 テクスチャ {i+1}: {img.name}")
            print(f"      - サイズ: {img.size[0]}x{img.size[1]} px")
            print(f"      - チャンネル数: {img.channels}")
            print(f"      - 深度: {img.depth}")
            print(f"      - ファイルパス: {img.filepath}")
            print(f"      - パック済み: {img.packed_file is not None}")
            print(f"      - カラースペース: {img.colorspace_settings.name}")
            print(f"      - ファイル形式: {img.file_format}")
            if hasattr(img, 'alpha_mode'):
                print(f"      - アルファモード: {img.alpha_mode}")
        
        # 全マテリアルの詳細分析
        print(f"\n🎨 全マテリアル詳細:")
        for i, mat in enumerate(bpy.data.materials):
            print(f"  \n  🎭 マテリアル {i+1}: {mat.name}")
            print(f"      - ノード使用: {mat.use_nodes}")
            print(f"      - ベースカラー: {mat.diffuse_color}")
            print(f"      - メタリック: {mat.metallic}")
            print(f"      - 粗さ: {mat.roughness}")
            
            if mat.use_nodes and mat.node_tree:
                print(f"      - ノード数: {len(mat.node_tree.nodes)}")
                print(f"      - リンク数: {len(mat.node_tree.links)}")
                
                # 各ノードの詳細
                print(f"      \n      🔗 ノード構造:")
                for j, node in enumerate(mat.node_tree.nodes):
                    print(f"          ノード {j+1}: {node.type} ({node.name})")
                    if node.type == 'TEX_IMAGE' and hasattr(node, 'image') and node.image:
                        print(f"              → 使用テクスチャ: {node.image.name}")
                        print(f"              → テクスチャサイズ: {node.image.size[0]}x{node.image.size[1]}")
                    elif node.type == 'BSDF_PRINCIPLED':
                        # Principled BSDFの各入力を確認
                        inputs = [input.name for input in node.inputs if input.is_linked]
                        print(f"              → 接続された入力: {inputs}")
                
                # リンク構造の詳細
                print(f"      \n      🔗 ノード接続:")
                for link in mat.node_tree.links:
                    from_node = link.from_node.name
                    from_socket = link.from_socket.name
                    to_node = link.to_node.name
                    to_socket = link.to_socket.name
                    print(f"          {from_node}.{from_socket} → {to_node}.{to_socket}")
        
        # メッシュオブジェクトの詳細（UVマッピング含む）
        mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
        print(f"\n🎨 メッシュオブジェクト詳細:")
        for i, obj in enumerate(mesh_objects):
            mesh = obj.data
            print(f"  \n  🧊 メッシュ {i+1}: {obj.name}")
            print(f"      - 頂点数: {len(mesh.vertices)}")
            print(f"      - 面数: {len(mesh.polygons)}")
            print(f"      - エッジ数: {len(mesh.edges)}")
            print(f"      - UVレイヤー数: {len(mesh.uv_layers)}")
            print(f"      - マテリアルスロット数: {len(obj.material_slots)}")
            
            # UVレイヤーの詳細
            for j, uv_layer in enumerate(mesh.uv_layers):
                print(f"      - UVレイヤー {j+1}: {uv_layer.name}")
                print(f"          - アクティブ: {uv_layer.active}")
                print(f"          - レンダリング用: {uv_layer.active_render}")
            
            # マテリアル割り当ての詳細
            for j, slot in enumerate(obj.material_slots):
                if slot.material:
                    print(f"      - マテリアルスロット {j+1}: {slot.material.name}")
        
        # GLTFファイル特有の情報
        print(f"\n📋 GLTF特有情報:")
        
        # アーマチュア確認
        armatures = [obj for obj in bpy.data.objects if obj.type == 'ARMATURE']
        print(f"  - アーマチュア数: {len(armatures)}")
        
        # アニメーション確認
        print(f"  - アニメーション数: {len(bpy.data.actions)}")
        
        print(f"\n✅ 元の鳥モデル分析完了")
        
    except Exception as e:
        print(f"❌ 分析中にエラー: {str(e)}")
        import traceback
        traceback.print_exc()

def analyze_texture_directory():
    """テクスチャディレクトリの確認"""
    print(f"\n{'='*80}")
    print(f"📁 テクスチャディレクトリ分析")
    print(f"{'='*80}")
    
    texture_dirs = [
        "/app/examples/",
        "/app/pipeline_work/06_blender_native/bird/",
        "/app/pipeline_work/06_blender_native/bird/textures/",
        "/app/pipeline_work/01_extracted_mesh/bird/",
    ]
    
    for texture_dir in texture_dirs:
        print(f"\n📂 ディレクトリ: {texture_dir}")
        if os.path.exists(texture_dir):
            files = os.listdir(texture_dir)
            texture_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.tga', '.exr', '.hdr'))]
            print(f"  - 全ファイル数: {len(files)}")
            print(f"  - テクスチャファイル数: {len(texture_files)}")
            
            for tex_file in texture_files:
                tex_path = os.path.join(texture_dir, tex_file)
                file_size = os.path.getsize(tex_path) / 1024  # KB
                print(f"    📸 {tex_file}: {file_size:.1f} KB")
        else:
            print(f"  ❌ ディレクトリが存在しません")

def compare_original_vs_final():
    """元モデルと最終モデルのテクスチャ比較"""
    print(f"\n{'='*80}")
    print(f"⚖️ 元モデル vs 最終モデル比較")
    print(f"{'='*80}")
    
    original_path = "/app/examples/bird.glb"
    final_path = "/app/pipeline_work/06_blender_native/bird/bird_final_rigged_textured.fbx"
    
    if os.path.exists(original_path):
        orig_size = os.path.getsize(original_path) / (1024 * 1024)
        print(f"📁 元モデル: {orig_size:.2f} MB")
    else:
        print(f"❌ 元モデルが見つかりません: {original_path}")
    
    if os.path.exists(final_path):
        final_size = os.path.getsize(final_path) / (1024 * 1024)
        print(f"📁 最終モデル: {final_size:.2f} MB")
        print(f"📊 サイズ比率: {(final_size/orig_size)*100:.1f}%" if os.path.exists(original_path) else "")
    else:
        print(f"❌ 最終モデルが見つかりません: {final_path}")
    
    # テクスチャ数の予想差異
    expected_textures = [
        "ベースカラー (Diffuse/Albedo)",
        "法線マップ (Normal Map)", 
        "粗さマップ (Roughness)",
        "メタリックマップ (Metallic)",
        "アンビエントオクルージョン (AO)",
        "エミッション (Emission)"
    ]
    
    print(f"\n📋 期待されるテクスチャタイプ:")
    for i, tex_type in enumerate(expected_textures, 1):
        print(f"  {i}. {tex_type}")

def main():
    print("🎯 UniRig 鳥モデル完全テクスチャ分析")
    print("="*80)
    
    # 元モデルの完全分析
    analyze_original_bird_model()
    
    # テクスチャディレクトリ分析
    analyze_texture_directory()
    
    # 比較分析
    compare_original_vs_final()
    
    print(f"\n{'='*80}")
    print("🎯 分析結果サマリー:")
    print("  1. 元の鳥モデルに実際に含まれるテクスチャ数の確認")
    print("  2. Blenderネイティブフローでの保持状況検証")
    print("  3. 最終FBXでのテクスチャ欠損箇所の特定")
    print("  4. プレビュー失敗の原因調査")
    print("="*80)

if __name__ == "__main__":
    main()
