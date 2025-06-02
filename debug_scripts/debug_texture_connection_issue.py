#!/usr/bin/env python3
"""
テクスチャ接続問題の詳細デバッグスクリプト
入力モデルと出力モデルの接続構造を詳細比較
"""
import bpy
import os
import sys

def clean_scene():
    """シーンを完全にクリア"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    
    for collection in bpy.data.collections:
        bpy.data.collections.remove(collection)
    
    for material in bpy.data.materials:
        bpy.data.materials.remove(material)
    
    for image in bpy.data.images:
        if image.name not in ['Render Result', 'Viewer Node']:
            bpy.data.images.remove(image)

def analyze_texture_connections(model_path, model_label):
    """テクスチャ接続構造を詳細分析"""
    print(f"\n{'='*80}")
    print(f"🔍 {model_label} の詳細テクスチャ接続分析")
    print(f"ファイル: {os.path.basename(model_path)}")
    print(f"{'='*80}")
    
    # シーンをクリーンアップ
    clean_scene()
    
    # ファイルの存在確認
    if not os.path.exists(model_path):
        print(f"❌ ファイルが見つかりません: {model_path}")
        return
    
    # ファイルをロード
    try:
        if model_path.endswith('.glb') or model_path.endswith('.gltf'):
            bpy.ops.import_scene.gltf(filepath=model_path, import_pack_images=True)
        elif model_path.endswith('.fbx'):
            bpy.ops.import_scene.fbx(filepath=model_path, use_image_search=True)
        else:
            print(f"❌ サポートされていないファイル形式")
            return
        
        print(f"✅ ファイルのインポートに成功")
    except Exception as e:
        print(f"❌ ファイルのインポートに失敗: {e}")
        return
    
    # 基本統計
    print(f"\n📊 基本統計:")
    print(f"  マテリアル数: {len(bpy.data.materials)}")
    print(f"  画像数: {len([img for img in bpy.data.images if img.name not in ['Render Result', 'Viewer Node']])}")
    
    # 各画像の詳細情報
    print(f"\n🖼️ 画像データ詳細:")
    for i, img in enumerate(bpy.data.images):
        if img.name in ['Render Result', 'Viewer Node']:
            continue
        print(f"  画像 {i+1}: {img.name}")
        print(f"    カラースペース: {img.colorspace_settings.name}")
        
        # テクスチャタイプの推定
        texture_type = "不明"
        if 'col' in img.name.lower() or 'bc' in img.name.lower() or 'base' in img.name.lower():
            texture_type = "ベースカラー"
        elif 'nrml' in img.name.lower() or 'normal' in img.name.lower() or '_n' in img.name.lower():
            texture_type = "ノーマルマップ"
        elif 'gloss' in img.name.lower() or 'rough' in img.name.lower() or '_r' in img.name.lower():
            texture_type = "ラフネス"
        print(f"    推定タイプ: {texture_type}")
    
    # 各マテリアルの詳細分析
    print(f"\n🎨 マテリアル接続構造分析:")
    for i, mat in enumerate(bpy.data.materials):
        print(f"\n📋 マテリアル {i+1}: {mat.name}")
        
        if not mat.use_nodes or not mat.node_tree:
            print(f"  ノードベースではありません")
            continue
        
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        
        # ノード統計
        texture_nodes = [node for node in nodes if node.type == 'TEX_IMAGE']
        principled_nodes = [node for node in nodes if node.type == 'BSDF_PRINCIPLED']
        normal_map_nodes = [node for node in nodes if node.type == 'NORMAL_MAP']
        mix_nodes = [node for node in nodes if node.type == 'MIX']
        separate_color_nodes = [node for node in nodes if node.type == 'SEPARATE_COLOR']
        
        print(f"  📊 ノード統計:")
        print(f"    テクスチャノード: {len(texture_nodes)}")
        print(f"    Principled BSDF: {len(principled_nodes)}")
        print(f"    Normal Map: {len(normal_map_nodes)}")
        print(f"    Mix: {len(mix_nodes)}")
        print(f"    Separate Color: {len(separate_color_nodes)}")
        
        # Principled BSDFの接続状況を詳細分析
        if principled_nodes:
            principled_node = principled_nodes[0]
            print(f"\n  🔗 Principled BSDF接続詳細:")
            
            # Base Color接続の詳細追跡
            base_color_input = principled_node.inputs.get('Base Color')
            if base_color_input and base_color_input.links:
                from_node = base_color_input.links[0].from_node
                from_socket = base_color_input.links[0].from_socket
                print(f"    ✅ Base Color: {from_node.name}.{from_socket.name}")
                
                # さらに上流を追跡
                if from_node.type == 'MIX' and from_node.inputs:
                    print(f"      └─ Mix ノード詳細:")
                    for mix_input in from_node.inputs:
                        if mix_input.links:
                            mix_from = mix_input.links[0].from_node
                            print(f"        {mix_input.name}: {mix_from.name} ({mix_from.type})")
                            if mix_from.type == 'TEX_IMAGE' and hasattr(mix_from, 'image') and mix_from.image:
                                print(f"          テクスチャ: {mix_from.image.name}")
            else:
                default_color = base_color_input.default_value if base_color_input else "不明"
                print(f"    ❌ Base Color: 未接続 (デフォルト: {default_color})")
            
            # Normal接続の詳細追跡
            normal_input = principled_node.inputs.get('Normal')
            if normal_input and normal_input.links:
                from_node = normal_input.links[0].from_node
                from_socket = normal_input.links[0].from_socket
                print(f"    ✅ Normal: {from_node.name}.{from_socket.name}")
                
                # Normal Mapノードの上流を追跡
                if from_node.type == 'NORMAL_MAP':
                    color_input = from_node.inputs.get('Color')
                    if color_input and color_input.links:
                        tex_node = color_input.links[0].from_node
                        print(f"      └─ Normal Map ← {tex_node.name} ({tex_node.type})")
                        if tex_node.type == 'TEX_IMAGE' and hasattr(tex_node, 'image') and tex_node.image:
                            print(f"          テクスチャ: {tex_node.image.name}")
            else:
                print(f"    ❌ Normal: 未接続")
            
            # Roughness接続の詳細追跡
            roughness_input = principled_node.inputs.get('Roughness')
            if roughness_input and roughness_input.links:
                from_node = roughness_input.links[0].from_node
                from_socket = roughness_input.links[0].from_socket
                print(f"    ✅ Roughness: {from_node.name}.{from_socket.name}")
                
                # Separate Colorノードの上流を追跡
                if from_node.type == 'SEPARATE_COLOR':
                    color_input = from_node.inputs.get('Color')
                    if color_input and color_input.links:
                        tex_node = color_input.links[0].from_node
                        print(f"      └─ Separate Color ← {tex_node.name} ({tex_node.type})")
                        if tex_node.type == 'TEX_IMAGE' and hasattr(tex_node, 'image') and tex_node.image:
                            print(f"          テクスチャ: {tex_node.image.name}")
            else:
                default_roughness = roughness_input.default_value if roughness_input else "不明"
                print(f"    ❌ Roughness: 未接続 (デフォルト: {default_roughness})")
        
        # 使用されていないテクスチャノードを検出
        print(f"\n  🚫 未使用テクスチャノード:")
        for tex_node in texture_nodes:
            if not any(output.links for output in tex_node.outputs):
                texture_name = tex_node.image.name if hasattr(tex_node, 'image') and tex_node.image else "なし"
                print(f"    ❌ {tex_node.name} (テクスチャ: {texture_name})")
    
    print(f"\n{'='*80}")

def main():
    """メイン実行関数"""
    # 入力モデルと出力モデルを比較
    input_model = "/app/examples/bird.glb"
    output_model = "/app/test_texture_preservation_final/merged_final.glb"
    
    # 引数からファイルパスを取得
    if len(sys.argv) > 2:
        input_model = sys.argv[1]
        output_model = sys.argv[2]
    
    print("🔍 テクスチャ接続問題デバッグ分析開始")
    print(f"入力モデル: {input_model}")
    print(f"出力モデル: {output_model}")
    
    # 両モデルを分析
    if os.path.exists(input_model):
        analyze_texture_connections(input_model, "入力モデル")
    else:
        print(f"❌ 入力モデルが見つかりません: {input_model}")
    
    if os.path.exists(output_model):
        analyze_texture_connections(output_model, "出力モデル")
    else:
        print(f"❌ 出力モデルが見つかりません: {output_model}")
    
    print(f"\n🎯 テクスチャ接続問題デバッグ分析完了")

if __name__ == "__main__":
    main()
