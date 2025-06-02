#!/usr/bin/env python3
"""
元のモデルファイルのマテリアル構造とテクスチャ割り当てを詳細に分析するスクリプト
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

def analyze_material_structure(model_path):
    """モデルのマテリアル構造を詳細に分析"""
    print(f"\n{'='*80}")
    print(f"📊 元モデルファイルの詳細分析: {os.path.basename(model_path)}")
    print(f"ファイルパス: {model_path}")
    print(f"{'='*80}")
    
    # シーンをクリーンアップ
    clean_scene()
    
    # ファイルの存在確認
    if not os.path.exists(model_path):
        print(f"❌ ファイルが見つかりません: {model_path}")
        return
    
    # ファイルサイズ確認
    file_size = os.path.getsize(model_path) / (1024 * 1024)  # MB
    print(f"📁 ファイルサイズ: {file_size:.2f} MB")
    
    # ファイルをロード
    try:
        if model_path.endswith('.glb') or model_path.endswith('.gltf'):
            bpy.ops.import_scene.gltf(filepath=model_path, import_pack_images=True)
        elif model_path.endswith('.fbx'):
            bpy.ops.import_scene.fbx(filepath=model_path, use_image_search=True)
        elif model_path.endswith('.obj'):
            bpy.ops.wm.obj_import(filepath=model_path)
        else:
            print(f"❌ サポートされていないファイル形式: {model_path}")
            return
        
        print(f"✅ ファイルのインポートに成功")
    except Exception as e:
        print(f"❌ ファイルのインポートに失敗: {e}")
        return
    
    # 基本統計
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    print(f"\n📈 基本統計:")
    print(f"  メッシュオブジェクト数: {len(mesh_objects)}")
    print(f"  マテリアル数: {len(bpy.data.materials)}")
    print(f"  画像数: {len([img for img in bpy.data.images if img.name not in ['Render Result', 'Viewer Node']])}")
    
    # 各画像の詳細情報
    print(f"\n🖼️  画像データブロック詳細:")
    for i, img in enumerate(bpy.data.images):
        if img.name in ['Render Result', 'Viewer Node']:
            continue
        print(f"  画像 {i+1}: {img.name}")
        print(f"    ファイルパス: {img.filepath}")
        print(f"    サイズ: {img.size[0]} x {img.size[1]} px")
        print(f"    カラースペース: {img.colorspace_settings.name}")
        if hasattr(img, 'packed_file') and img.packed_file:
            print(f"    パック済み: はい ({len(img.packed_file.data)} bytes)")
        else:
            print(f"    パック済み: いいえ")
        
        # ファイルの実在確認
        if img.filepath and os.path.exists(bpy.path.abspath(img.filepath)):
            print(f"    ファイル存在: はい")
        elif img.filepath:
            print(f"    ファイル存在: いいえ ({bpy.path.abspath(img.filepath)})")
        else:
            print(f"    ファイル存在: パスなし")
    
    # 各マテリアルの詳細分析
    print(f"\n🎨 マテリアル詳細分析:")
    for i, mat in enumerate(bpy.data.materials):
        print(f"\n📋 マテリアル {i+1}: {mat.name}")
        print(f"  ノードベースマテリアル: {'はい' if mat.use_nodes else 'いいえ'}")
        
        if mat.use_nodes and mat.node_tree:
            # ノード統計
            texture_nodes = [node for node in mat.node_tree.nodes if node.type == 'TEX_IMAGE']
            principled_nodes = [node for node in mat.node_tree.nodes if node.type == 'BSDF_PRINCIPLED']
            normal_map_nodes = [node for node in mat.node_tree.nodes if node.type == 'NORMAL_MAP']
            
            print(f"  ノード統計:")
            print(f"    テクスチャノード数: {len(texture_nodes)}")
            print(f"    Principled BSDFノード数: {len(principled_nodes)}")
            print(f"    Normal Mapノード数: {len(normal_map_nodes)}")
            
            # テクスチャノードの詳細
            if texture_nodes:
                print(f"  🖼️  テクスチャノード詳細:")
                for j, tex_node in enumerate(texture_nodes):
                    print(f"    テクスチャノード {j+1}: {tex_node.name}")
                    if tex_node.image:
                        print(f"      画像: {tex_node.image.name}")
                        print(f"      ファイルパス: {tex_node.image.filepath}")
                        print(f"      画像サイズ: {tex_node.image.size[0]} x {tex_node.image.size[1]} px")
                        print(f"      カラースペース: {tex_node.image.colorspace_settings.name}")
                        
                        # 出力接続の詳細分析
                        print(f"      出力接続:")
                        for output in tex_node.outputs:
                            if output.links:
                                for link in output.links:
                                    to_node = link.to_node
                                    to_socket = link.to_socket
                                    print(f"        {output.name} → {to_node.name}.{to_socket.name}")
                            else:
                                print(f"        {output.name} → 未接続")
                    else:
                        print(f"      画像: なし")
            
            # Principled BSDFノードの接続状況
            if principled_nodes:
                print(f"  🔗 Principled BSDF接続状況:")
                for j, principled_node in enumerate(principled_nodes):
                    print(f"    Principled BSDF {j+1}: {principled_node.name}")
                    
                    # 主要な入力ソケットをチェック
                    important_inputs = ['Base Color', 'Metallic', 'Roughness', 'Normal', 'Alpha']
                    for input_name in important_inputs:
                        if input_name in principled_node.inputs:
                            input_socket = principled_node.inputs[input_name]
                            if input_socket.links:
                                from_node = input_socket.links[0].from_node
                                from_socket = input_socket.links[0].from_socket
                                print(f"      {input_name}: 接続済み ({from_node.name}.{from_socket.name})")
                            else:
                                # デフォルト値を表示
                                if hasattr(input_socket, 'default_value'):
                                    if isinstance(input_socket.default_value, (list, tuple)):
                                        if len(input_socket.default_value) >= 3:
                                            print(f"      {input_name}: 未接続 (デフォルト: R{input_socket.default_value[0]:.3f} G{input_socket.default_value[1]:.3f} B{input_socket.default_value[2]:.3f})")
                                        else:
                                            print(f"      {input_name}: 未接続 (デフォルト: {input_socket.default_value})")
                                    else:
                                        print(f"      {input_name}: 未接続 (デフォルト: {input_socket.default_value})")
                                else:
                                    print(f"      {input_name}: 未接続")
    
    # メッシュオブジェクトとマテリアル割り当て
    print(f"\n🔷 メッシュオブジェクトとマテリアル割り当て:")
    for i, obj in enumerate(mesh_objects):
        print(f"  オブジェクト {i+1}: {obj.name}")
        print(f"    頂点数: {len(obj.data.vertices)}")
        print(f"    面数: {len(obj.data.polygons)}")
        print(f"    マテリアルスロット数: {len(obj.material_slots)}")
        
        for j, mat_slot in enumerate(obj.material_slots):
            if mat_slot.material:
                print(f"      スロット {j+1}: {mat_slot.material.name}")
            else:
                print(f"      スロット {j+1}: なし")
    
    print(f"\n{'='*80}")
    print(f"📊 分析完了")
    print(f"{'='*80}\n")

def main():
    """メイン実行関数"""
    # テストモデルのパスリスト
    test_models = [
        "/app/assets/bird.glb",
        "/app/assets/tira.glb", 
        "/app/assets/giraffe.glb",
        "/app/assets/tripo_carrot.glb"
    ]
    
    # 引数からファイルパスを取得
    if len(sys.argv) > 1:
        model_path = sys.argv[1]
        if os.path.exists(model_path):
            test_models = [model_path]
        else:
            print(f"❌ 指定されたファイルが見つかりません: {model_path}")
            return
    
    # 各モデルを分析
    for model_path in test_models:
        if os.path.exists(model_path):
            analyze_material_structure(model_path)
        else:
            print(f"⚠️  ファイルが見つかりません、スキップ: {model_path}")

if __name__ == "__main__":
    main()
