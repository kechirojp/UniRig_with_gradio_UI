#!/usr/bin/env python3
"""
FBX出力ファイルのマテリアル構造を詳細に分析するスクリプト
入力モデルと出力FBXの接続構造の違いを特定する
"""
import bpy
import os
import sys

def clear_scene():
    """シーンをクリア"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # マテリアルをクリア
    for material in bpy.data.materials:
        bpy.data.materials.remove(material, do_unlink=True)
    
    # テクスチャをクリア
    for texture in bpy.data.textures:
        bpy.data.textures.remove(texture, do_unlink=True)
    
    # 画像をクリア
    for image in bpy.data.images:
        if image.users == 0 or image.name not in ['Render Result', 'Viewer Node']:
            bpy.data.images.remove(image, do_unlink=True)

def analyze_material_nodes(material, material_name):
    """マテリアルのノード構造を詳細に分析"""
    print(f"\n🔍 マテリアル '{material_name}' の詳細分析:")
    print("=" * 60)
    
    if not material.use_nodes:
        print("❌ ノードが有効になっていません")
        return
    
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    
    print(f"📊 ノード数: {len(nodes)}")
    print(f"🔗 リンク数: {len(links)}")
    
    # 各ノードの詳細情報
    print("\n📋 ノード一覧:")
    for i, node in enumerate(nodes):
        print(f"  {i+1}. {node.name} ({node.type})")
        if node.type == 'TEX_IMAGE':
            if node.image:
                print(f"     📁 画像: {node.image.name}")
                print(f"     🎨 カラースペース: {node.image.colorspace_settings.name}")
                print(f"     📏 サイズ: {node.image.size[0]}x{node.image.size[1]}")
            else:
                print("     ❌ 画像が設定されていません")
        elif node.type == 'BSDF_PRINCIPLED':
            print(f"     🎨 Base Color: {node.inputs['Base Color'].default_value[:3]}")
            print(f"     ⚡ Metallic: {node.inputs['Metallic'].default_value}")
            print(f"     🪨 Roughness: {node.inputs['Roughness'].default_value}")
        elif node.type == 'NORMAL_MAP':
            print(f"     💪 Strength: {node.inputs['Strength'].default_value}")
        elif node.type == 'MIX':
            print(f"     🔀 Blend Type: {node.blend_type}")
            print(f"     🎚️ Factor: {node.inputs['Fac'].default_value}")
        elif node.type == 'SEPARATE_COLOR':
            print(f"     🌈 Mode: {node.mode}")
    
    # 接続の詳細分析
    print("\n🔗 接続構造の詳細:")
    for i, link in enumerate(links):
        from_node = link.from_node
        to_node = link.to_node
        from_socket = link.from_socket
        to_socket = link.to_socket
        
        print(f"  {i+1}. {from_node.name}[{from_socket.name}] → {to_node.name}[{to_socket.name}]")
        
        # 特定の重要な接続をハイライト
        if to_node.type == 'BSDF_PRINCIPLED':
            if to_socket.name == 'Base Color':
                print("     🎨 ベースカラー接続!")
            elif to_socket.name == 'Roughness':
                print("     🪨 ラフネス接続!")
            elif to_socket.name == 'Normal':
                print("     📐 ノーマル接続!")
            elif to_socket.name == 'Metallic':
                print("     ⚡ メタリック接続!")
    
    # テクスチャからPrincipled BSDFへのパスを追跡
    print("\n🛤️ テクスチャからPrincipled BSDFへのパス:")
    principled_nodes = [n for n in nodes if n.type == 'BSDF_PRINCIPLED']
    texture_nodes = [n for n in nodes if n.type == 'TEX_IMAGE']
    
    for texture_node in texture_nodes:
        if texture_node.image:
            print(f"\n📸 テクスチャ: {texture_node.image.name}")
            # このテクスチャがどのように接続されているかを追跡
            for principled in principled_nodes:
                paths = find_connection_paths(texture_node, principled, material.node_tree)
                for path in paths:
                    print(f"  📍 パス: {' → '.join(path)}")

def find_connection_paths(start_node, end_node, node_tree, current_path=None, visited=None):
    """ノード間の接続パスを再帰的に探索"""
    if current_path is None:
        current_path = [start_node.name]
    if visited is None:
        visited = set()
    
    if start_node == end_node:
        return [current_path]
    
    if start_node in visited:
        return []
    
    visited.add(start_node)
    paths = []
    
    # 出力ソケットから次のノードを探索
    for output in start_node.outputs:
        for link in output.links:
            next_node = link.to_node
            if next_node not in visited:
                new_path = current_path + [next_node.name]
                paths.extend(find_connection_paths(next_node, end_node, node_tree, new_path, visited.copy()))
    
    return paths

def analyze_fbx_file(fbx_path):
    """FBXファイルを読み込んで分析"""
    print(f"\n🔍 FBXファイル分析: {fbx_path}")
    print("=" * 80)
    
    if not os.path.exists(fbx_path):
        print(f"❌ ファイルが見つかりません: {fbx_path}")
        return
    
    # シーンをクリア
    clear_scene()
    
    try:
        # FBXファイルを読み込み
        bpy.ops.import_scene.fbx(filepath=fbx_path)
        print("✅ FBXファイルの読み込み成功")
        
        # オブジェクトとマテリアルを分析
        print(f"\n📦 インポートされたオブジェクト数: {len(bpy.context.scene.objects)}")
        
        for obj in bpy.context.scene.objects:
            print(f"\n🎯 オブジェクト: {obj.name} ({obj.type})")
            
            if obj.type == 'MESH' and obj.data.materials:
                print(f"   📝 マテリアル数: {len(obj.data.materials)}")
                
                for i, material in enumerate(obj.data.materials):
                    if material:
                        analyze_material_nodes(material, f"{obj.name}_Material_{i}")
                    else:
                        print(f"   ❌ マテリアルスロット {i} が空です")
    
    except Exception as e:
        print(f"❌ FBX読み込みエラー: {e}")

def analyze_glb_file(glb_path):
    """GLBファイルを読み込んで分析（比較用）"""
    print(f"\n🔍 GLBファイル分析: {glb_path}")
    print("=" * 80)
    
    if not os.path.exists(glb_path):
        print(f"❌ ファイルが見つかりません: {glb_path}")
        return
    
    # シーンをクリア
    clear_scene()
    
    try:
        # GLBファイルを読み込み
        bpy.ops.import_scene.gltf(filepath=glb_path)
        print("✅ GLBファイルの読み込み成功")
        
        # オブジェクトとマテリアルを分析
        print(f"\n📦 インポートされたオブジェクト数: {len(bpy.context.scene.objects)}")
        
        for obj in bpy.context.scene.objects:
            print(f"\n🎯 オブジェクト: {obj.name} ({obj.type})")
            
            if obj.type == 'MESH' and obj.data.materials:
                print(f"   📝 マテリアル数: {len(obj.data.materials)}")
                
                for i, material in enumerate(obj.data.materials):
                    if material:
                        analyze_material_nodes(material, f"{obj.name}_Material_{i}")
                    else:
                        print(f"   ❌ マテリアルスロット {i} が空です")
    
    except Exception as e:
        print(f"❌ GLB読み込みエラー: {e}")

def main():
    print("🔍 FBX出力構造の詳細分析")
    print("=" * 80)
    
    # 最新のテスト出力ディレクトリを確認
    test_dir = "/app/test_texture_preservation_final"
    
    # GLBファイル（期待される構造）
    merged_glb = os.path.join(test_dir, "merged_final.glb")
    
    # FBXファイルのパスを推測（通常の出力場所）
    possible_fbx_paths = [
        "/app/outputs/merged_model.fbx",
        "/app/results/merged_model.fbx", 
        "/app/pipeline_work/merged_model.fbx",
        "/app/test_texture_preservation_final/merged_final.fbx"
    ]
    
    print("📁 利用可能なファイルを確認中...")
    
    # GLBファイルを分析（参照用）
    if os.path.exists(merged_glb):
        print(f"\n✅ 参照GLBファイル発見: {merged_glb}")
        analyze_glb_file(merged_glb)
    
    # FBXファイルを探して分析
    fbx_found = False
    for fbx_path in possible_fbx_paths:
        if os.path.exists(fbx_path):
            print(f"\n✅ FBXファイル発見: {fbx_path}")
            analyze_fbx_file(fbx_path)
            fbx_found = True
            break
    
    if not fbx_found:
        print("\n❌ FBXファイルが見つかりません")
        print("📋 確認した場所:")
        for path in possible_fbx_paths:
            print(f"   - {path}")
        
        # 出力ディレクトリの内容を確認
        output_dirs = ["/app/outputs", "/app/results", "/app/pipeline_work"]
        for output_dir in output_dirs:
            if os.path.exists(output_dir):
                print(f"\n📂 {output_dir} の内容:")
                try:
                    files = os.listdir(output_dir)
                    for file in files:
                        if file.endswith(('.fbx', '.glb', '.gltf')):
                            print(f"   📄 {file}")
                except Exception as e:
                    print(f"   ❌ ディレクトリ読み込みエラー: {e}")

if __name__ == "__main__":
    main()
