#!/usr/bin/env python3
"""
Blender 4.2でのデータ転送問題の詳細調査
なぜUVマップとマテリアル転送が失敗するのかを解明
"""

import subprocess
from pathlib import Path

def debug_data_transfer():
    """Blender 4.2のデータ転送機能を詳細調査"""
    
    output_dir = Path("/app/test_step5_debug")
    output_dir.mkdir(exist_ok=True)
    
    # テスト用の2つのFBXファイルパス
    model1_path = "/app/test_step5_true_fbx_merge/test_bird_stripped.fbx"
    model2_path = "/app/test_step5_true_fbx_merge/test_bird_with_data.fbx"
    
    blender_script = f'''
import bpy

print("=== Blender 4.2 データ転送 詳細調査 ===")

# シーンクリア
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# モデル1（ストリップ版）をインポート
print("\\n--- モデル1（ストリップ版）インポート ---")
bpy.ops.import_scene.fbx(filepath="{model1_path}")

model1_objects = list(bpy.context.selected_objects)
model1_mesh = None
for obj in model1_objects:
    if obj.type == 'MESH':
        model1_mesh = obj
        break

print(f"モデル1メッシュ: {{model1_mesh.name if model1_mesh else 'なし'}}")
if model1_mesh:
    print(f"  UVレイヤー数: {{len(model1_mesh.data.uv_layers)}}")
    print(f"  マテリアル数: {{len(model1_mesh.data.materials)}}")

# モデル2（完全データ版）をインポート
print("\\n--- モデル2（完全データ版）インポート ---")
bpy.ops.import_scene.fbx(filepath="{model2_path}")

all_objects = set(bpy.context.scene.objects)
model1_object_set = set(model1_objects)
model2_objects = list(all_objects - model1_object_set)

model2_mesh = None
for obj in model2_objects:
    if obj.type == 'MESH':
        model2_mesh = obj
        break

print(f"モデル2メッシュ: {{model2_mesh.name if model2_mesh else 'なし'}}")
if model2_mesh:
    print(f"  UVレイヤー数: {{len(model2_mesh.data.uv_layers)}}")
    print(f"  マテリアル数: {{len(model2_mesh.data.materials)}}")

if not model1_mesh or not model2_mesh:
    print("❌ メッシュが見つかりません")
    exit(1)

# 転送前の状態確認
print("\\n--- 転送前の状態 ---")
print(f"model1_mesh UVレイヤー: {{len(model1_mesh.data.uv_layers)}}")
print(f"model1_mesh マテリアル: {{len(model1_mesh.data.materials)}}")
print(f"model2_mesh UVレイヤー: {{len(model2_mesh.data.uv_layers)}}")
print(f"model2_mesh マテリアル: {{len(model2_mesh.data.materials)}}")

# 利用可能なmake_links_dataのオプションを確認
print("\\n--- 利用可能なmake_links_dataオプション確認 ---")
bpy.ops.object.select_all(action='DESELECT')
model2_mesh.select_set(True)
model1_mesh.select_set(True)
bpy.context.view_layer.objects.active = model1_mesh

# 各オプションを試してみる
transfer_options = ['OBDATA', 'MATERIAL', 'ANIMATION', 'GROUPS', 'DUPLICOLLECTION', 'FONTS', 'MODIFIERS', 'EFFECTS']

for option in transfer_options:
    try:
        print(f"\\n🔍 {{option}} オプションをテスト...")
        bpy.ops.object.make_links_data(type=option)
        print(f"  ✅ {{option}}: 成功")
        
        # 結果確認
        print(f"  結果 - model1_mesh UVレイヤー: {{len(model1_mesh.data.uv_layers)}}")
        print(f"  結果 - model1_mesh マテリアル: {{len(model1_mesh.data.materials)}}")
        
    except Exception as e:
        print(f"  ❌ {{option}}: 失敗 - {{e}}")

# 手動データ転送を試す
print("\\n--- 手動データ転送テスト ---")
try:
    # 手動マテリアル転送
    print("手動マテリアル転送開始...")
    model1_mesh.data.materials.clear()
    for material in model2_mesh.data.materials:
        if material:
            model1_mesh.data.materials.append(material)
    print(f"手動マテリアル転送後: {{len(model1_mesh.data.materials)}}個")
    
    # 手動UV転送は複雑なので基本的な情報のみ確認
    print("手動UV転送準備...")
    if model2_mesh.data.uv_layers:
        print(f"転送元UVレイヤー: {{[uv.name for uv in model2_mesh.data.uv_layers]}}")
        
        # UVレイヤーを新規作成
        if len(model1_mesh.data.uv_layers) == 0:
            uv_layer = model1_mesh.data.uv_layers.new(name="TransferredUV")
            print(f"新しいUVレイヤー作成: {{uv_layer.name}}")
        
        print(f"手動UV処理後: {{len(model1_mesh.data.uv_layers)}}個")
    
except Exception as e:
    print(f"手動転送エラー: {{e}}")

# 最終状態確認
print("\\n--- 最終状態 ---")
print(f"model1_mesh UVレイヤー: {{len(model1_mesh.data.uv_layers)}}")
print(f"model1_mesh マテリアル: {{len(model1_mesh.data.materials)}}")

print("\\n=== 調査完了 ===")
'''
    
    cmd = ["blender", "--background", "--python-expr", blender_script]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    
    print("🔍 Blender 4.2 データ転送詳細調査結果")
    print("=" * 50)
    print(result.stdout)
    
    if result.stderr:
        print("\n⚠️ エラー出力:")
        print(result.stderr)

if __name__ == "__main__":
    debug_data_transfer()
