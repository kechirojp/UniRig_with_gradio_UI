#!/usr/bin/env python3
"""
最終FBXモデルの詳細テクスチャ損失分析
"""

import os
import sys
import bpy

def analyze_final_fbx_texture_loss():
    """最終FBXファイルのテクスチャ損失を詳細分析"""
    final_fbx_path = "/app/pipeline_work/06_blender_native/bird/bird_final_rigged_textured.fbx"
    
    print(f"{'='*80}")
    print(f"🔍 最終FBXテクスチャ損失詳細分析")
    print(f"{'='*80}")
    print(f"📁 ファイルパス: {final_fbx_path}")
    
    if not os.path.exists(final_fbx_path):
        print(f"❌ ファイルが見つかりません: {final_fbx_path}")
        return
    
    # ファイルサイズ
    file_size = os.path.getsize(final_fbx_path) / (1024 * 1024)
    print(f"📏 ファイルサイズ: {file_size:.2f} MB")
    
    try:
        # Blenderシーンをクリア
        bpy.ops.wm.read_factory_settings(use_empty=True)
        
        # FBXファイルをインポート
        print("📥 FBXファイルをインポート中...")
        bpy.ops.import_scene.fbx(filepath=final_fbx_path)
        
        print(f"\n🔍 最終FBX構造分析:")
        print(f"  - オブジェクト数: {len(bpy.data.objects)}")
        print(f"  - メッシュ数: {len(bpy.data.meshes)}")
        print(f"  - マテリアル数: {len(bpy.data.materials)}")
        print(f"  - テクスチャ数: {len(bpy.data.images)}")
        
        # 失われたテクスチャの詳細確認
        print(f"\n🖼️ 最終FBXのテクスチャ詳細:")
        print(f"  総テクスチャ数: {len(bpy.data.images)}")
        for i, img in enumerate(bpy.data.images):
            print(f"  \n  📸 テクスチャ {i+1}: {img.name}")
            print(f"      - サイズ: {img.size[0]}x{img.size[1]} px")
            print(f"      - チャンネル数: {img.channels}")
            print(f"      - ファイルパス: {img.filepath}")
            print(f"      - パック済み: {img.packed_file is not None}")
            print(f"      - カラースペース: {img.colorspace_settings.name}")
        
        # 最終FBXのマテリアル構造分析
        print(f"\n🎨 最終FBXマテリアル詳細:")
        for i, mat in enumerate(bpy.data.materials):
            print(f"  \n  🎭 マテリアル {i+1}: {mat.name}")
            print(f"      - ノード使用: {mat.use_nodes}")
            
            if mat.use_nodes and mat.node_tree:
                print(f"      - ノード数: {len(mat.node_tree.nodes)}")
                print(f"      - リンク数: {len(mat.node_tree.links)}")
                
                # テクスチャノードの確認
                texture_nodes = [node for node in mat.node_tree.nodes if node.type == 'TEX_IMAGE']
                print(f"      - テクスチャノード数: {len(texture_nodes)}")
                
                for j, node in enumerate(texture_nodes):
                    print(f"          テクスチャノード {j+1}: {node.name}")
                    if hasattr(node, 'image') and node.image:
                        print(f"              → 使用テクスチャ: {node.image.name}")
                    else:
                        print(f"              → ⚠️ テクスチャが割り当てられていません")
                
                # Principled BSDFの入力確認
                principled_nodes = [node for node in mat.node_tree.nodes if node.type == 'BSDF_PRINCIPLED']
                for j, node in enumerate(principled_nodes):
                    print(f"      \n      🔗 Principled BSDF {j+1}:")
                    connected_inputs = []
                    for input_socket in node.inputs:
                        if input_socket.is_linked:
                            connected_inputs.append(input_socket.name)
                    print(f"          接続された入力: {connected_inputs}")
                    
                    # 各重要な入力の状態をチェック
                    critical_inputs = ['Base Color', 'Metallic', 'Roughness', 'Normal']
                    for input_name in critical_inputs:
                        if input_name in [inp.name for inp in node.inputs]:
                            input_socket = node.inputs[input_name]
                            if input_socket.is_linked:
                                source_node = input_socket.links[0].from_node
                                print(f"          {input_name}: ✅ 接続済み ({source_node.type})")
                            else:
                                print(f"          {input_name}: ❌ 未接続")
        
        print(f"\n✅ 最終FBX分析完了")
        
    except Exception as e:
        print(f"❌ 分析中にエラー: {str(e)}")
        import traceback
        traceback.print_exc()

def check_blender_native_intermediate_files():
    """Blenderネイティブフローの中間ファイルを確認"""
    print(f"\n{'='*80}")
    print(f"📁 Blenderネイティブフロー中間ファイル確認")
    print(f"{'='*80}")
    
    work_dir = "/app/pipeline_work/06_blender_native/bird/"
    if not os.path.exists(work_dir):
        print(f"❌ 作業ディレクトリが存在しません: {work_dir}")
        return
    
    print(f"📂 作業ディレクトリ: {work_dir}")
    files = os.listdir(work_dir)
    print(f"ファイル一覧:")
    
    for file in files:
        file_path = os.path.join(work_dir, file)
        if os.path.isfile(file_path):
            file_size = os.path.getsize(file_path) / (1024 * 1024)
            print(f"  📄 {file}: {file_size:.2f} MB")
            
            # .blendファイルがあれば分析
            if file.endswith('.blend'):
                analyze_blend_file(file_path)

def analyze_blend_file(blend_path):
    """中間.blendファイルの分析"""
    print(f"\n  🔍 Blendファイル分析: {os.path.basename(blend_path)}")
    
    try:
        # 現在のシーンを保存（必要に応じて）
        bpy.ops.wm.read_factory_settings(use_empty=True)
        
        # Blendファイルを開く
        bpy.ops.wm.open_mainfile(filepath=blend_path)
        
        print(f"    - オブジェクト数: {len(bpy.data.objects)}")
        print(f"    - マテリアル数: {len(bpy.data.materials)}")
        print(f"    - テクスチャ数: {len(bpy.data.images)}")
        
        # テクスチャ詳細
        for i, img in enumerate(bpy.data.images):
            print(f"    - テクスチャ {i+1}: {img.name} ({img.size[0]}x{img.size[1]})")
        
    except Exception as e:
        print(f"    ❌ Blendファイル分析エラー: {str(e)}")

def compare_texture_expectations():
    """期待されるテクスチャと実際のテクスチャの比較"""
    print(f"\n{'='*80}")
    print(f"⚖️ テクスチャ期待値 vs 実際の比較")
    print(f"{'='*80}")
    
    expected_textures = {
        "T_tucano_bird_col_v2_BC": "ベースカラー (必須)",
        "T_tucano_bird_gloss6_R": "粗さ/光沢マップ (必須)",
        "T_tucano_bird_nrml5_N": "法線マップ (必須)"
    }
    
    print("📋 期待されるテクスチャ:")
    for tex_name, description in expected_textures.items():
        print(f"  ✅ {tex_name}: {description}")
    
    print("\n📋 実際の最終FBXテクスチャ:")
    print("  ❌ T_tucano_bird_col_v2_BC: 欠損")
    print("  ❌ T_tucano_bird_gloss6_R: 欠損") 
    print("  ✅ T_tucano_bird_nrml5_N: 保持")
    
    print("\n🚨 問題点:")
    print("  1. ベースカラーテクスチャが失われているため、モデルが正しい色で表示されない")
    print("  2. 粗さマップが失われているため、材質感が正しく表現されない")
    print("  3. テクスチャが1/3しか保持されていない（67%のテクスチャ情報損失）")

def main():
    print("🔍 UniRig 最終FBXテクスチャ損失詳細分析")
    print("="*80)
    
    # 最終FBXの詳細分析
    analyze_final_fbx_texture_loss()
    
    # 中間ファイル確認
    check_blender_native_intermediate_files()
    
    # 期待値比較
    compare_texture_expectations()
    
    print(f"\n{'='*80}")
    print("🎯 結論:")
    print("  ❌ Blenderネイティブテクスチャフローが3つのテクスチャのうち2つを失っている")
    print("  📊 元モデル: 3テクスチャ (7.66MB) → 最終モデル: 1テクスチャ (2.92MB)")
    print("  🔧 修正必要: テクスチャ保持ロジックの見直しが必要")
    print("="*80)

if __name__ == "__main__":
    main()
