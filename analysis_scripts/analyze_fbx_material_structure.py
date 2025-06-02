#!/usr/bin/env python3
"""
分析用にコピーされたFBXファイルの詳細な構造分析
"""
import bpy
import os

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

def analyze_node_connections(material, material_name):
    """マテリアルのノード接続を詳細分析"""
    print(f"\n🔍 マテリアル '{material_name}' のノード接続分析:")
    print("=" * 60)
    
    if not material.use_nodes:
        print("❌ ノードが有効になっていません")
        return
    
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    
    print(f"📊 ノード数: {len(nodes)}")
    print(f"🔗 リンク数: {len(links)}")
    
    # ノード詳細
    print("\n📋 ノード詳細:")
    for i, node in enumerate(nodes):
        print(f"  {i+1}. {node.name} ({node.type})")
        if node.type == 'TEX_IMAGE':
            if node.image:
                print(f"     📁 画像: {node.image.name}")
                print(f"     🎨 カラースペース: {node.image.colorspace_settings.name}")
                print(f"     📏 サイズ: {node.image.size[0]}x{node.image.size[1]}")
                print(f"     🔌 出力接続数: {len(node.outputs[0].links)}")
                if node.outputs[0].links:
                    for link in node.outputs[0].links:
                        print(f"         → {link.to_node.name}.{link.to_socket.name}")
            else:
                print("     ❌ 画像が設定されていません")
        elif node.type == 'BSDF_PRINCIPLED':
            print(f"     🎨 Base Color input connected: {len(node.inputs['Base Color'].links) > 0}")
            print(f"     📐 Normal input connected: {len(node.inputs['Normal'].links) > 0}")
            print(f"     🪨 Roughness input connected: {len(node.inputs['Roughness'].links) > 0}")
            print(f"     ⚡ Metallic input connected: {len(node.inputs['Metallic'].links) > 0}")
            
            # 接続の詳細
            for input_name in ['Base Color', 'Normal', 'Roughness', 'Metallic']:
                if node.inputs[input_name].links:
                    for link in node.inputs[input_name].links:
                        print(f"         {input_name} ← {link.from_node.name}.{link.from_socket.name}")
        elif node.type == 'MIX':
            print(f"     🔀 Blend Type: {node.blend_type}")
            print(f"     🎚️ Factor connected: {len(node.inputs[0].links) > 0}")  # Factor is index 0 in Blender 4.x
            print(f"     📥 A input connected: {len(node.inputs[6].links) > 0}")  # A is index 6 in Blender 4.x
            print(f"     📥 B input connected: {len(node.inputs[7].links) > 0}")  # B is index 7 in Blender 4.x
        elif node.type == 'NORMAL_MAP':
            print(f"     💪 Strength: {node.inputs['Strength'].default_value}")
            print(f"     🎨 Color connected: {len(node.inputs['Color'].links) > 0}")
        elif node.type == 'SEPARATE_COLOR':
            print(f"     🌈 Mode: {node.mode}")
            print(f"     🎨 Color connected: {len(node.inputs['Color'].links) > 0}")
    
    print("\n🔗 全接続の詳細:")
    for i, link in enumerate(links):
        from_node = link.from_node
        to_node = link.to_node
        from_socket = link.from_socket
        to_socket = link.to_socket
        
        print(f"  {i+1}. {from_node.name}[{from_socket.name}] → {to_node.name}[{to_socket.name}]")
        
        # 重要な接続をハイライト
        if to_node.type == 'BSDF_PRINCIPLED':
            if to_socket.name == 'Base Color':
                print("     🎨 ベースカラー接続!")
            elif to_socket.name == 'Roughness':
                print("     🪨 ラフネス接続!")
            elif to_socket.name == 'Normal':
                print("     📐 ノーマル接続!")
            elif to_socket.name == 'Metallic':
                print("     ⚡ メタリック接続!")

def analyze_fbx_materials(fbx_path):
    """FBXファイルのマテリアル構造を分析"""
    print(f"🔍 FBXファイル分析: {fbx_path}")
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
                        analyze_node_connections(material, f"{obj.name}_Material_{i}")
                    else:
                        print(f"   ❌ マテリアルスロット {i} が空です")
    
    except Exception as e:
        print(f"❌ FBX読み込みエラー: {e}")
        import traceback
        traceback.print_exc()

def compare_with_glb(glb_path):
    """比較用にGLBファイルも分析"""
    print(f"\n\n🔍 比較用GLBファイル分析: {glb_path}")
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
                        analyze_node_connections(material, f"{obj.name}_Material_{i}_GLB")
                    else:
                        print(f"   ❌ マテリアルスロット {i} が空です")
    
    except Exception as e:
        print(f"❌ GLB読み込みエラー: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("🔍 FBX出力ファイルの詳細マテリアル分析")
    print("=" * 80)
    
    # 分析用ファイルのパス
    fbx_path = "/app/fbx_analysis/merged_for_analysis.fbx"
    glb_path = "/app/fbx_analysis/merged_for_analysis.glb"
    
    print(f"📁 分析対象ファイル:")
    print(f"   FBX: {fbx_path} (存在: {os.path.exists(fbx_path)})")
    print(f"   GLB: {glb_path} (存在: {os.path.exists(glb_path)})")
    
    if os.path.exists(fbx_path):
        analyze_fbx_materials(fbx_path)
    
    if os.path.exists(glb_path):
        compare_with_glb(glb_path)

if __name__ == "__main__":
    main()
