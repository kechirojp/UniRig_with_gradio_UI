#!/usr/bin/env python3
"""
Step5 修正版: Data Transfer Modifierを使用したBlender 4.2対応
真のUV・マテリアル復元実装
"""

import subprocess
from pathlib import Path
import shutil

def step5_with_data_transfer_modifier():
    """Data Transfer Modifierを使用した正しいデータ転送"""
    
    # 入力ファイル
    input_glb = "/app/examples/bird.glb"  
    output_dir = Path("/app/test_step5_data_transfer_fix")
    output_dir.mkdir(exist_ok=True)
    
    print("🔧 Step5 Data Transfer Modifier版開始")
    
    # Step 1: GLB → Blender with full data
    model1_blend = output_dir / "Model1_with_data.blend"
    
    blender_script_step1 = f'''
import bpy

# シーンクリア
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

print("Step 1: GLBインポートとデータ保持Blenderファイル作成")

# GLBインポート
bpy.ops.import_scene.gltf(filepath="{input_glb}")

# インポート結果確認
meshes = [obj for obj in bpy.data.objects if obj.type == 'MESH']
print(f"インポートされたメッシュ数: {{len(meshes)}}")

for mesh in meshes:
    print(f"メッシュ: {{mesh.name}}")
    print(f"  頂点数: {{len(mesh.data.vertices)}}")
    print(f"  UVレイヤー数: {{len(mesh.data.uv_layers)}}")
    print(f"  マテリアル数: {{len(mesh.data.materials)}}")

# Blendファイル保存
bpy.ops.wm.save_as_mainfile(filepath="{model1_blend}")
print(f"データ保持版保存完了: {model1_blend}")
'''
    
    cmd1 = ["blender", "--background", "--python-expr", blender_script_step1]
    result1 = subprocess.run(cmd1, capture_output=True, text=True, timeout=120)
    
    if result1.returncode != 0:
        print(f"❌ Step1失敗: {result1.stderr}")
        return False
    
    print("✅ Step1完了: データ保持版作成")
    print(result1.stdout)
    
    # Step 2: Model1 → ストリップ版作成
    model2_blend = output_dir / "Model2_stripped.blend"
    
    blender_script_step2 = f'''
import bpy

# Model1読み込み
bpy.ops.wm.open_mainfile(filepath="{model1_blend}")

print("Step 2: ストリップ版作成（UV・マテリアル削除）")

meshes = [obj for obj in bpy.data.objects if obj.type == 'MESH']
print(f"処理対象メッシュ数: {{len(meshes)}}")

for mesh in meshes:
    print(f"ストリップ処理: {{mesh.name}}")
    
    # UVマップ削除
    while mesh.data.uv_layers:
        mesh.data.uv_layers.remove(mesh.data.uv_layers[0])
    
    # マテリアル削除
    mesh.data.materials.clear()
    
    print(f"  UVレイヤー数: {{len(mesh.data.uv_layers)}} (削除後)")
    print(f"  マテリアル数: {{len(mesh.data.materials)}} (削除後)")

# ストリップ版保存
bpy.ops.wm.save_as_mainfile(filepath="{model2_blend}")
print(f"ストリップ版保存完了: {model2_blend}")
'''
    
    cmd2 = ["blender", "--background", "--python-expr", blender_script_step2]
    result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=120)
    
    if result2.returncode != 0:
        print(f"❌ Step2失敗: {result2.stderr}")
        return False
    
    print("✅ Step2完了: ストリップ版作成")
    print(result2.stdout)
    
    # Step 3: Data Transfer Modifierによる復元
    final_fbx = output_dir / "Final_with_data_transfer.fbx"
    
    blender_script_step3 = f'''
import bpy

print("Step 3: Data Transfer Modifierによるデータ復元")

# ストリップ版を読み込み（ターゲット）
bpy.ops.wm.open_mainfile(filepath="{model2_blend}")

target_meshes = [obj for obj in bpy.data.objects if obj.type == 'MESH']
if target_meshes:
    target_mesh = target_meshes[0]
    target_mesh.name = "Target"
    print(f"ターゲットメッシュ: {{target_mesh.name}}")
    print(f"  UVレイヤー数: {{len(target_mesh.data.uv_layers)}} (復元前)")
    print(f"  マテリアル数: {{len(target_mesh.data.materials)}} (復元前)")

# ソースメッシュをインポート（Model1から）
bpy.ops.wm.append(filepath="{model1_blend}", directory="{model1_blend}/Object", filename="SK_tucano_bird.001")

# ソースメッシュを特定
source_meshes = [obj for obj in bpy.data.objects if obj.type == 'MESH' and obj != target_mesh]
if source_meshes:
    source_mesh = source_meshes[0]
    source_mesh.name = "Source"
    print(f"ソースメッシュ: {{source_mesh.name}}")
    print(f"  UVレイヤー数: {{len(source_mesh.data.uv_layers)}}")
    print(f"  マテリアル数: {{len(source_mesh.data.materials)}}")

    # ターゲットを選択してアクティブに
    bpy.context.view_layer.objects.active = target_mesh
    target_mesh.select_set(True)
    source_mesh.select_set(False)

    # Data Transfer Modifier追加
    print("Data Transfer Modifier追加開始...")
    
    # UV転送用modifier
    uv_modifier = target_mesh.modifiers.new(name="DataTransfer_UV", type='DATA_TRANSFER')
    uv_modifier.object = source_mesh
    uv_modifier.use_loop_data = True
    uv_modifier.data_types_loops = {{'UV'}}
    uv_modifier.loop_mapping = 'POLYINTERP_NEAREST'
    
    print("UV転送modifier設定完了")
    
    # Modifierを適用
    bpy.context.view_layer.objects.active = target_mesh
    bpy.ops.object.modifier_apply(modifier="DataTransfer_UV")
    print("UV転送modifier適用完了")
    
    # マテリアル転送（手動）
    print("マテリアル転送開始...")
    for slot in source_mesh.data.materials:
        if slot:
            target_mesh.data.materials.append(slot)
    
    print(f"復元後の状態:")
    print(f"  UVレイヤー数: {{len(target_mesh.data.uv_layers)}}")
    print(f"  マテリアル数: {{len(target_mesh.data.materials)}}")
    
    # ソースメッシュを削除
    bpy.data.objects.remove(source_mesh, do_unlink=True)
    
    # ターゲットのみを選択してFBXエクスポート
    bpy.ops.object.select_all(action='DESELECT')
    target_mesh.select_set(True)
    
    print("FBXエクスポート開始...")
    bpy.ops.export_scene.fbx(
        filepath="{final_fbx}",
        use_selection=True,
        add_leaf_bones=True,
        bake_anim=False
    )
    print(f"FBXエクスポート完了: {final_fbx}")
else:
    print("❌ メッシュが見つかりません")
'''
    
    cmd3 = ["blender", "--background", "--python-expr", blender_script_step3]
    result3 = subprocess.run(cmd3, capture_output=True, text=True, timeout=120)
    
    if result3.returncode != 0:
        print(f"❌ Step3失敗: {result3.stderr}")
        return False
    
    print("✅ Step3完了: Data Transfer Modifier復元")
    print(result3.stdout)
    
    # 結果確認
    if final_fbx.exists():
        size_mb = final_fbx.stat().st_size / (1024 * 1024)
        print(f"📊 最終FBXサイズ: {size_mb:.2f}MB")
        return True
    else:
        print("❌ 最終FBXが生成されませんでした")
        return False

if __name__ == "__main__":
    success = step5_with_data_transfer_modifier()
    if success:
        print("🎉 Step5 Data Transfer Modifier版テスト成功")
    else:
        print("❌ Step5 Data Transfer Modifier版テスト失敗")
