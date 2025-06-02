#!/usr/bin/env python3
"""
テクスチャ保持の確認スクリプト
出力されたFBXおよびGLBファイルのテクスチャ情報を検証します
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
        bpy.data.materials.remove(material)

def analyze_texture_info(file_path, file_type):
    """ファイルのテクスチャ情報を分析"""
    print(f"\n{'='*60}")
    print(f"分析中: {file_path}")
    print(f"ファイル形式: {file_type}")
    print(f"{'='*60}")
    
    if not os.path.exists(file_path):
        print(f"❌ ファイルが見つかりません: {file_path}")
        return
    
    file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
    print(f"📁 ファイルサイズ: {file_size:.2f} MB")
    
    clear_scene()
    
    try:
        # ファイルをインポート
        if file_type == "FBX":
            bpy.ops.import_scene.fbx(filepath=file_path)
        elif file_type == "GLB":
            bpy.ops.import_scene.gltf(filepath=file_path)
        else:
            print(f"❌ サポートされていないファイル形式: {file_type}")
            return
        
        print(f"✅ ファイルのインポートに成功")
        
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
                
                # テクスチャノードを検索
                texture_nodes = [node for node in node_tree.nodes if node.type == 'TEX_IMAGE']
                print(f"  🖼️  テクスチャノード数: {len(texture_nodes)}")
                
                for j, tex_node in enumerate(texture_nodes):
                    print(f"    テクスチャノード {j+1}: {tex_node.name}")
                    if tex_node.image:
                        print(f"      画像: {tex_node.image.name}")
                        print(f"      ファイルパス: {tex_node.image.filepath}")
                        print(f"      画像サイズ: {tex_node.image.size[0]} x {tex_node.image.size[1]} px")
                        image_count += 1
                    else:
                        print(f"      ❌ 画像が関連付けられていません")
                    texture_count += 1
                
                # プリンシプルBSDFノードを検索
                principled_nodes = [node for node in node_tree.nodes if node.type == 'BSDF_PRINCIPLED']
                for principled in principled_nodes:
                    print(f"  🔗 プリンシプルBSDFノード: {principled.name}")
                    
                    # 主要な入力を確認
                    inputs_to_check = ['Base Color', 'Normal', 'Roughness', 'Metallic', 'Specular']
                    for input_name in inputs_to_check:
                        if input_name in principled.inputs:
                            input_socket = principled.inputs[input_name]
                            if input_socket.is_linked:
                                linked_node = input_socket.links[0].from_node
                                print(f"    {input_name}: 接続済み ({linked_node.type})")
                            else:
                                print(f"    {input_name}: 未接続")
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
        
        print(f"\n📊 要約:")
        print(f"  テクスチャノード総数: {texture_count}")
        print(f"  画像総数: {image_count}")
        print(f"  マテリアル総数: {len(materials)}")
        
        # テクスチャが見つからない場合の警告
        if texture_count == 0:
            print(f"⚠️  警告: テクスチャノードが見つかりませんでした")
        if image_count == 0:
            print(f"⚠️  警告: 画像が見つかりませんでした")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """メイン処理"""
    print("🔍 UniRig出力ファイルのテクスチャ検証")
    print("="*60)
    
    output_dir = "/app/test_merge_debug_output"
    
    # FBXファイルを分析
    fbx_path = os.path.join(output_dir, "final_rigged_model.fbx")
    analyze_texture_info(fbx_path, "FBX")
    
    # GLBファイルを分析
    glb_path = os.path.join(output_dir, "final_rigged_model.glb")
    analyze_texture_info(glb_path, "GLB")
    
    # 元のインプットファイルと比較
    print(f"\n{'='*60}")
    print("元のファイルとの比較")
    print(f"{'='*60}")
    
    # テスト入力ファイルを確認
    test_files = [
        "/app/examples/meshes/model_normalized.obj",
        "/app/examples/meshes/giraffe_t_pose.glb",
        "/app/test_current_status/giraffe_t_pose.glb"
    ]
    
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"\n🔍 元ファイルの確認: {test_file}")
            if test_file.endswith('.glb'):
                analyze_texture_info(test_file, "GLB")
            elif test_file.endswith('.obj'):
                analyze_texture_info(test_file, "OBJ")
            break
    else:
        print("⚠️  元のテストファイルが見つかりませんでした")

if __name__ == "__main__":
    main()
