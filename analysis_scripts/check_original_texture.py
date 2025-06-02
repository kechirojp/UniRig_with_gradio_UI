#!/usr/bin/env python3
"""
元のキリンモデルのテクスチャ情報を確認
"""

import bpy
import os

def clear_scene():
    """シーンをクリア"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # マテリアルをクリア
    for material in bpy.data.materials:
        bpy.data.materials.remove(material)

def analyze_original_giraffe():
    """元のキリンモデルを分析"""
    print("🔍 元のキリンモデルのテクスチャ分析")
    print("="*60)
    
    giraffe_path = "/app/examples/giraffe.glb"
    
    if not os.path.exists(giraffe_path):
        print(f"❌ ファイルが見つかりません: {giraffe_path}")
        return
    
    file_size = os.path.getsize(giraffe_path) / (1024 * 1024)  # MB
    print(f"📁 ファイルサイズ: {file_size:.2f} MB")
    
    clear_scene()
    
    try:
        # GLBファイルをインポート
        bpy.ops.import_scene.gltf(filepath=giraffe_path)
        print("✅ ファイルのインポートに成功")
        
        # オブジェクト情報を取得
        objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
        print(f"🔍 メッシュオブジェクト数: {len(objects)}")
        
        # マテリアル情報を取得
        materials = list(bpy.data.materials)
        print(f"🎨 マテリアル数: {len(materials)}")
        
        texture_count = 0
        image_count = 0
        
        for i, material in enumerate(materials):
            print(f"\n📋 マテリアル {i+1}: {material.name}")
            
            if material.use_nodes:
                print(f"  ノードベースマテリアル: はい")
                node_tree = material.node_tree
                
                # すべてのノードタイプを確認
                print(f"  ノード総数: {len(node_tree.nodes)}")
                for node in node_tree.nodes:
                    print(f"    - {node.type}: {node.name}")
                
                # テクスチャノードを検索
                texture_nodes = [node for node in node_tree.nodes if node.type == 'TEX_IMAGE']
                print(f"  🖼️  テクスチャノード数: {len(texture_nodes)}")
                
                for j, tex_node in enumerate(texture_nodes):
                    print(f"    テクスチャノード {j+1}: {tex_node.name}")
                    if tex_node.image:
                        print(f"      画像: {tex_node.image.name}")
                        print(f"      ファイルパス: {tex_node.image.filepath}")
                        print(f"      画像サイズ: {tex_node.image.size[0]} x {tex_node.image.size[1]} px")
                        print(f"      パック済み: {'はい' if tex_node.image.packed_file else 'いいえ'}")
                        if tex_node.image.packed_file:
                            print(f"      パックサイズ: {len(tex_node.image.packed_file.data) / 1024:.1f} KB")
                        image_count += 1
                    else:
                        print(f"      ❌ 画像が関連付けられていません")
                    texture_count += 1
                
                # プリンシプルBSDFノードを検索
                principled_nodes = [node for node in node_tree.nodes if node.type == 'BSDF_PRINCIPLED']
                for principled in principled_nodes:
                    print(f"  🔗 プリンシプルBSDFノード: {principled.name}")
                    
                    # すべての入力を確認
                    for input_socket in principled.inputs:
                        if input_socket.is_linked:
                            linked_node = input_socket.links[0].from_node
                            print(f"    {input_socket.name}: 接続済み ({linked_node.type}: {linked_node.name})")
                        elif hasattr(input_socket, 'default_value') and input_socket.default_value != input_socket.bl_rna.properties['default_value'].default:
                            print(f"    {input_socket.name}: デフォルト値変更 ({input_socket.default_value})")
            else:
                print(f"  ノードベースマテリアル: いいえ")
        
        # オブジェクトのマテリアル割り当てを確認
        for obj in objects:
            print(f"\n🔷 オブジェクト: {obj.name}")
            print(f"  マテリアルスロット数: {len(obj.material_slots)}")
            for i, slot in enumerate(obj.material_slots):
                if slot.material:
                    print(f"    スロット {i+1}: {slot.material.name}")
                else:
                    print(f"    スロット {i+1}: マテリアルなし")
        
        # 画像データブロックを確認
        images = list(bpy.data.images)
        print(f"\n🖼️  画像データブロック数: {len(images)}")
        for i, img in enumerate(images):
            if img.name not in ['Render Result', 'Viewer Node']:  # デフォルト画像を除外
                print(f"  画像 {i+1}: {img.name}")
                print(f"    ファイルパス: {img.filepath}")
                print(f"    サイズ: {img.size[0]} x {img.size[1]} px")
                print(f"    パック済み: {'はい' if img.packed_file else 'いいえ'}")
                if img.packed_file:
                    print(f"    パックサイズ: {len(img.packed_file.data) / 1024:.1f} KB")
        
        print(f"\n📊 要約:")
        print(f"  テクスチャノード総数: {texture_count}")
        print(f"  画像総数: {image_count}")
        print(f"  マテリアル総数: {len(materials)}")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_original_giraffe()
