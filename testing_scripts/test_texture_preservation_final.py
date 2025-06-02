#!/usr/bin/env python3
"""
テクスチャ保持修正の検証スクリプト
実際にパイプラインを実行してテクスチャが保持されるかテスト
"""

import os
import sys
import shutil
import time
import subprocess

def mock_progress(value, desc=""):
    """プログレス用のモック関数"""
    print(f"Progress: {desc}")

def test_texture_preservation():
    """テクスチャ保持機能をテスト"""
    
    print("=== テクスチャ保持修正検証開始 ===")
    
    # 設定とパスの準備
    input_file = "/app/examples/bird.glb"
    output_dir = "/app/test_texture_preservation_final"
    
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        sys.path.append('/app')
        from app import gradio_full_auto_rigging, load_app_config
        
        print("アプリケーション設定を初期化中...")
        load_app_config("/app/configs/app_config.yaml")
        
        print("フルパイプライン実行中...")
        start_time = time.time()
        
        result = gradio_full_auto_rigging(
            uploaded_model_path=input_file,
            gender="neutral",
            progress=mock_progress
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"\n=== パイプライン実行完了 (実行時間: {execution_time:.2f}秒) ===")
        
        if result and len(result) >= 11:
            # 結果ファイルをすべて保存
            merged_glb = result[0]          # final_display_path (merged GLB for display)
            logs = result[1]                # logs
            merged_fbx = result[2]          # final_merged_fbx_path (merged FBX for download)
            skeleton_glb = result[4]        # skeleton_display_path
            skeleton_fbx = result[5]        # skeleton_fbx_path
            skinned_glb = result[8]         # skinned_display_path
            
            print(f"マージ済み GLB (表示用): {merged_glb}")
            print(f"マージ済み FBX (ダウンロード用): {merged_fbx}")
            print(f"スケルトン GLB: {skeleton_glb}")
            print(f"スケルトン FBX: {skeleton_fbx}")
            print(f"スキニング GLB: {skinned_glb}")
            
            # ファイルをバックアップ
            if skeleton_glb and os.path.exists(skeleton_glb):
                skeleton_backup = os.path.join(output_dir, "skeleton.glb")
                shutil.copy2(skeleton_glb, skeleton_backup)
                print(f"✓ スケルトンファイル保存: {skeleton_backup}")
                
            if skinned_glb and os.path.exists(skinned_glb):
                skinned_backup = os.path.join(output_dir, "skinned.glb")
                shutil.copy2(skinned_glb, skinned_backup)
                print(f"✓ スキニングファイル保存: {skinned_backup}")
                
            if merged_glb and os.path.exists(merged_glb):
                merged_backup = os.path.join(output_dir, "merged_final.glb")
                shutil.copy2(merged_glb, merged_backup)
                print(f"✓ 最終マージファイル保存: {merged_backup}")
                
                # 最終マージファイルのテクスチャ分析を実行
                analyze_texture_preservation(input_file, merged_backup)
                return True
            else:
                print("❌ 最終マージファイルが見つかりません")
                return False
        else:
            print(f"❌ 予期しない結果: {result}")
            return False
            
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return False

def analyze_texture_preservation(original_file, final_file):
    """テクスチャ保持状況を分析"""
    
    print(f"\n=== テクスチャ保持分析 ===")
    print(f"オリジナルファイル: {original_file}")
    print(f"最終ファイル: {final_file}")
    
    analyze_script = f"""
import bpy
import os

def analyze_model(file_path, model_name):
    # 既存のメッシュオブジェクトをクリア
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # モデルをインポート
    bpy.ops.import_scene.gltf(filepath=file_path)
    
    print(f"\\n=== {{model_name}} の分析 ===")
    
    # テクスチャファイルのリスト
    textures = [img for img in bpy.data.images if img.name not in ['Render Result', 'Viewer Node']]
    print(f"テクスチャ数: {{len(textures)}}")
    
    for tex in textures:
        print(f"  テクスチャ: {{tex.name}} (色空間: {{tex.colorspace_settings.name}})")
    
    # マテリアル分析
    materials = [mat for mat in bpy.data.materials if mat.use_nodes]
    print(f"ノードベースマテリアル数: {{len(materials)}}")
    
    for mat in materials:
        print(f"\\n  マテリアル: {{mat.name}}")
        nodes = mat.node_tree.nodes
        
        # Principled BSDBの接続確認
        principled_nodes = [n for n in nodes if n.type == 'BSDF_PRINCIPLED']
        if principled_nodes:
            principled = principled_nodes[0]
            
            # Base Color接続
            base_color_links = principled.inputs['Base Color'].links
            if base_color_links:
                from_node = base_color_links[0].from_node
                print(f"    Base Color: {{from_node.name}} ({{from_node.type}})")
                if from_node.type == 'TEX_IMAGE' and from_node.image:
                    print(f"      → テクスチャ: {{from_node.image.name}}")
                elif from_node.type == 'MIX':
                    print(f"      → Mix経由接続")
            else:
                print(f"    Base Color: 接続なし")
            
            # Normal接続
            normal_links = principled.inputs['Normal'].links
            if normal_links:
                from_node = normal_links[0].from_node
                print(f"    Normal: {{from_node.name}} ({{from_node.type}})")
            else:
                print(f"    Normal: 接続なし")
            
            # Roughness接続
            roughness_links = principled.inputs['Roughness'].links
            if roughness_links:
                from_node = roughness_links[0].from_node
                print(f"    Roughness: {{from_node.name}} ({{from_node.type}})")
            else:
                print(f"    Roughness: 接続なし")

# 分析実行
analyze_model('{original_file}', 'オリジナル')
analyze_model('{final_file}', '最終出力')
"""
    
    script_path = "/tmp/analyze_texture_preservation.py"
    with open(script_path, 'w') as f:
        f.write(analyze_script)
    
    try:
        result = subprocess.run([
            "blender", "--background", "--python", script_path
        ], capture_output=True, text=True, timeout=120)
        
        print("=== 分析結果 ===")
        print(result.stdout)
        
        if result.stderr:
            print("=== 分析エラー ===")
            print(result.stderr)
            
    except Exception as e:
        print(f"分析実行エラー: {e}")
    
    # 一時ファイルを削除
    if os.path.exists(script_path):
        os.remove(script_path)

def main():
    success = test_texture_preservation()
    
    if success:
        print("\n✅ テクスチャ保持修正のテストが正常に完了しました")
    else:
        print("\n❌ テクスチャ保持修正のテストでエラーが発生しました")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
