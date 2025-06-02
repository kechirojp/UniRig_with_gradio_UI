#!/usr/bin/env python3
"""
アップロードされたモデルのマテリアル構造とテクスチャアサインメントを詳細に分析する
"""

import bpy
import os
import sys

def analyze_model_materials(file_path):
    """アップロードされたモデルのマテリアル構造を分析"""
    
    # 既存のメッシュオブジェクトをクリア
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # モデルをインポート
    print(f"=== モデル分析: {file_path} ===")
    
    if file_path.endswith('.glb') or file_path.endswith('.gltf'):
        bpy.ops.import_scene.gltf(filepath=file_path)
    elif file_path.endswith('.fbx'):
        bpy.ops.import_scene.fbx(filepath=file_path)
    else:
        print(f"サポートされていないファイル形式: {file_path}")
        return
    
    print(f"インポート完了: {file_path}")
    
    # 全マテリアルを分析
    print(f"\n=== マテリアル分析 (総数: {len(bpy.data.materials)}) ===")
    
    for i, material in enumerate(bpy.data.materials):
        print(f"\n--- マテリアル {i+1}: {material.name} ---")
        
        if not material.use_nodes:
            print("  ノードベースマテリアルではありません")
            continue
            
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        
        print(f"  ノード数: {len(nodes)}")
        print(f"  リンク数: {len(links)}")
        
        # 全ノードの詳細情報
        print("\n  === ノード詳細 ===")
        for node in nodes:
            print(f"    ノード: {node.name} (タイプ: {node.type})")
            
            if node.type == 'TEX_IMAGE':
                image = node.image
                if image:
                    print(f"      テクスチャファイル: {image.name}")
                    print(f"      ファイルパス: {image.filepath}")
                    print(f"      色空間: {image.colorspace_settings.name}")
                    print(f"      サイズ: {image.size[0]}x{image.size[1]}")
                    
                    # テクスチャファイル名からタイプを推測
                    name_lower = image.name.lower()
                    if any(keyword in name_lower for keyword in ['col', 'bc', 'base', 'diffuse', 'albedo']):
                        tex_type = "ベースカラー"
                    elif any(keyword in name_lower for keyword in ['nrml', 'normal', '_n']):
                        tex_type = "ノーマルマップ"
                    elif any(keyword in name_lower for keyword in ['gloss', 'rough', '_r']):
                        tex_type = "ラフネス"
                    elif any(keyword in name_lower for keyword in ['metal', '_m']):
                        tex_type = "メタリック"
                    else:
                        tex_type = "不明"
                    print(f"      推測タイプ: {tex_type}")
                else:
                    print("      テクスチャファイルが設定されていません")
            
            elif node.type == 'BSDF_PRINCIPLED':
                print("      === Principled BSDF 入力値 ===")
                for input_socket in node.inputs:
                    if hasattr(input_socket, 'default_value'):
                        if hasattr(input_socket.default_value, '__len__') and len(input_socket.default_value) > 1:
                            # ベクターまたはカラー値
                            print(f"        {input_socket.name}: {list(input_socket.default_value)}")
                        else:
                            # スカラー値
                            print(f"        {input_socket.name}: {input_socket.default_value}")
        
        # 接続情報の詳細
        print("\n  === 接続詳細 ===")
        for link in links:
            from_node = link.from_node
            to_node = link.to_node
            from_socket = link.from_socket
            to_socket = link.to_socket
            
            print(f"    {from_node.name}[{from_socket.name}] → {to_node.name}[{to_socket.name}]")
            
            # テクスチャノードの場合、詳細情報を追加
            if from_node.type == 'TEX_IMAGE' and from_node.image:
                print(f"      テクスチャ: {from_node.image.name}")
                print(f"      色空間: {from_node.image.colorspace_settings.name}")
    
    # 全テクスチャファイルのリスト
    print(f"\n=== 全テクスチャファイル (総数: {len(bpy.data.images)}) ===")
    for i, image in enumerate(bpy.data.images):
        print(f"  {i+1}: {image.name}")
        print(f"      ファイルパス: {image.filepath}")
        print(f"      色空間: {image.colorspace_settings.name}")
        print(f"      サイズ: {image.size[0]}x{image.size[1]}")
        print(f"      ユーザー数: {image.users}")

def main():
    # テストファイルのパスリスト
    test_files = [
        "/app/examples/bird.glb",  # オリジナルファイル
        "/app/pipeline_work/bird_mesh.glb",  # メッシュ抽出後
        "/app/pipeline_work/bird_with_armature.glb",  # アーマチュア追加後
    ]
    
    for file_path in test_files:
        if os.path.exists(file_path):
            print(f"\n{'='*80}")
            analyze_model_materials(file_path)
            print(f"{'='*80}")
        else:
            print(f"ファイルが見つかりません: {file_path}")

if __name__ == "__main__":
    main()
