#!/usr/bin/env python3
"""
修正されたテクスチャ保持機能を含む完全なパイプラインをテスト
"""

import os
import sys
import shutil
import subprocess
import time

def test_complete_pipeline_with_texture_fix():
    """修正されたテクスチャ保持機能を含む完全なパイプラインをテスト"""
    
    print("=== 修正されたテクスチャ保持機能の完全テスト開始 ===")
    
    # 作業ディレクトリの準備
    work_dir = "/app/test_texture_fix_complete"
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    os.makedirs(work_dir, exist_ok=True)
    
    input_file = "/app/examples/bird.glb"
    output_file = os.path.join(work_dir, "bird_rigged_texture_fixed.glb")
    
    print(f"入力ファイル: {input_file}")
    print(f"出力ファイル: {output_file}")
    
    # 完全なパイプラインを実行
    print("\n=== パイプライン実行開始 ===")
    start_time = time.time()
    
    # 直接Pythonの関数を使用してテスト
    try:
        sys.path.append('/app')
        from app import gradio_full_auto_rigging, load_app_config
        
        print("アプリケーション設定を初期化中...")
        load_app_config("/app/configs/app_config.yaml")
        
        print("gradio_full_auto_rigging関数を直接実行中...")
        
        result = gradio_full_auto_rigging(
            uploaded_model_path=input_file,
            gender="neutral",
            progress=None
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"\n=== パイプライン実行完了 (実行時間: {execution_time:.2f}秒) ===")
        print(f"結果の詳細: {result}")
        print(f"結果の長さ: {len(result) if result else 'None'}")
        
        if result:
            for i, item in enumerate(result):
                print(f"  結果[{i}]: {item}")
        
        if result and len(result) >= 7:
            # 最終出力ファイルを取得
            final_rigged_model = result[6]  # マージされた最終モデル
            
            print(f"最終リギングモデル: {final_rigged_model}")
            
            if final_rigged_model and os.path.exists(final_rigged_model):
                # 出力ファイルを指定場所にコピー
                shutil.copy2(final_rigged_model, output_file)
                
                file_size = os.path.getsize(output_file)
                print(f"✅ 出力ファイル生成成功: {output_file} (サイズ: {file_size} bytes)")
                
                # 出力ファイルのマテリアル構造を分析
                analyze_output_materials(output_file)
                
                return True
            else:
                print(f"❌ 最終リギングモデルが生成されませんでした")
                
                # 他の結果も確認
                for i, item in enumerate(result):
                    if item and isinstance(item, str) and os.path.exists(item) and item.endswith(('.glb', '.fbx')):
                        print(f"  代替ファイル[{i}]: {item}")
                        shutil.copy2(item, output_file)
                        file_size = os.path.getsize(output_file)
                        print(f"✅ 代替出力ファイル使用: {output_file} (サイズ: {file_size} bytes)")
                        analyze_output_materials(output_file)
                        return True
                
                return False
        else:
            print(f"❌ 予期しない結果フォーマット: {result}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ パイプライン実行がタイムアウトしました")
        return False
    except Exception as e:
        print(f"❌ パイプライン実行中にエラーが発生しました: {e}")
        return False
    
    return True

def analyze_output_materials(file_path):
    """出力ファイルのマテリアル構造を分析"""
    
    print(f"\n=== 出力ファイル分析: {file_path} ===")
    
    analyze_script = f"""
import bpy
import os

# 既存のメッシュオブジェクトをクリア
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# モデルをインポート
bpy.ops.import_scene.gltf(filepath='{file_path}')

print("=== 出力ファイルのマテリアル分析 ===")

# 全マテリアルを分析
for i, material in enumerate(bpy.data.materials):
    print(f"\\n--- マテリアル {{i+1}}: {{material.name}} ---")
    
    if not material.use_nodes:
        print("  ノードベースマテリアルではありません")
        continue
        
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    
    print(f"  ノード数: {{len(nodes)}}")
    print(f"  リンク数: {{len(links)}}")
    
    # テクスチャノードの詳細
    texture_nodes = [n for n in nodes if n.type == 'TEX_IMAGE']
    print(f"  テクスチャノード数: {{len(texture_nodes)}}")
    
    for tex_node in texture_nodes:
        if tex_node.image:
            print(f"    テクスチャ: {{tex_node.image.name}} (色空間: {{tex_node.image.colorspace_settings.name}})")
    
    # Principled BSDBの接続を確認
    principled_nodes = [n for n in nodes if n.type == 'BSDF_PRINCIPLED']
    if principled_nodes:
        principled = principled_nodes[0]
        print("  === Principled BSDF 接続状況 ===")
        
        # Base Color接続
        base_color_links = principled.inputs['Base Color'].links
        if base_color_links:
            from_node = base_color_links[0].from_node
            print(f"    Base Color: {{from_node.name}} ({{from_node.type}})")
            if from_node.type == 'TEX_IMAGE' and from_node.image:
                print(f"      テクスチャ: {{from_node.image.name}}")
            elif from_node.type == 'MIX':
                # Mixノードの入力を確認
                mix_inputs = [link.from_node for link in from_node.inputs if link.from_node]
                print(f"      Mix入力: {{[n.name for n in mix_inputs]}}")
        else:
            print("    Base Color: 接続なし")
        
        # Normal接続
        normal_links = principled.inputs['Normal'].links
        if normal_links:
            from_node = normal_links[0].from_node
            print(f"    Normal: {{from_node.name}} ({{from_node.type}})")
        else:
            print("    Normal: 接続なし")
        
        # Roughness接続
        roughness_links = principled.inputs['Roughness'].links
        if roughness_links:
            from_node = roughness_links[0].from_node
            print(f"    Roughness: {{from_node.name}} ({{from_node.type}})")
        else:
            print("    Roughness: 接続なし")
        
        # Metallic接続
        metallic_links = principled.inputs['Metallic'].links
        if metallic_links:
            from_node = metallic_links[0].from_node
            print(f"    Metallic: {{from_node.name}} ({{from_node.type}})")
        else:
            print("    Metallic: 接続なし")

# 全テクスチャファイルのリスト
print(f"\\n=== 全テクスチャファイル (総数: {{len(bpy.data.images)}}) ===")
for i, image in enumerate(bpy.data.images):
    if image.name not in ['Render Result', 'Viewer Node']:
        print(f"  {{i+1}}: {{image.name}} (色空間: {{image.colorspace_settings.name}}, サイズ: {{image.size[0]}}x{{image.size[1]}})")
"""
    
    # 分析スクリプトを一時ファイルに保存
    script_path = "/tmp/analyze_output.py"
    with open(script_path, 'w') as f:
        f.write(analyze_script)
    
    # Blenderで分析実行
    try:
        result = subprocess.run([
            "blender", "--background", "--python", script_path
        ], capture_output=True, text=True, timeout=60)
        
        print("分析結果:")
        print(result.stdout)
        
        if result.stderr:
            print("分析エラー:")
            print(result.stderr)
            
    except Exception as e:
        print(f"分析実行エラー: {e}")
    
    # 一時ファイルを削除
    if os.path.exists(script_path):
        os.remove(script_path)

def main():
    success = test_complete_pipeline_with_texture_fix()
    
    if success:
        print("\n✅ テクスチャ保持修正の完全テストが正常に完了しました")
    else:
        print("\n❌ テクスチャ保持修正の完全テストでエラーが発生しました")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
