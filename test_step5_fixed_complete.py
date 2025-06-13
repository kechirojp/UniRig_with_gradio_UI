#!/usr/bin/env python3
"""
Step5 修正版: Blenderスクリプト内で全ての関数を定義
GitHubパターンによるUV転送を含む完全なFBX統合
"""

import subprocess
import os
from pathlib import Path

class Step5FixedComplete:
    """修正版Step5 - Blenderスクリプト内完結"""
    
    def __init__(self, output_dir: str = "/app/test_step5_fixed_complete"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    def run_complete_flow(self, input_glb: str, model_name: str) -> bool:
        """完全なFBX統合フロー"""
        
        try:
            # Step1: GLB → FBX (完全データ保持)
            fbx_with_data = self.output_dir / f"{model_name}_with_data.fbx"
            if not self._glb_to_fbx_with_data(input_glb, str(fbx_with_data)):
                return False
            
            # Step2: ストリップFBX作成 (UVとマテリアル削除)
            fbx_stripped = self.output_dir / f"{model_name}_stripped.fbx"
            if not self._create_stripped_fbx(str(fbx_with_data), str(fbx_stripped)):
                return False
            
            # Step3: GitHubパターンで2つのFBXを統合
            fbx_merged = self.output_dir / f"{model_name}_merged_final.fbx"
            return self._merge_fbx_models_github_pattern(str(fbx_stripped), str(fbx_with_data), str(fbx_merged))
            
        except Exception as e:
            print(f"❌ エラー: {e}")
            return False
    
    def _glb_to_fbx_with_data(self, input_glb: str, output_fbx: str) -> bool:
        """GLBファイルを完全データ保持でFBXに変換"""
        
        blender_script = f'''
import bpy

# シーンクリア
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

print("=== GLB → FBX (完全データ保持) ===")

# GLBインポート
bpy.ops.import_scene.gltf(filepath="{input_glb}")
print(f"GLBインポート完了: {Path(input_glb).name}")

# データ保持確認
mesh_count = len([obj for obj in bpy.data.objects if obj.type == 'MESH'])
material_count = len(bpy.data.materials)
image_count = len([img for img in bpy.data.images if img.name not in ['Render Result', 'Viewer Node']])

print(f"メッシュ数: {{mesh_count}}")
print(f"マテリアル数: {{material_count}}")
print(f"画像数: {{image_count}}")

# UVマップ確認
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        uv_count = len(obj.data.uv_layers)
        print(f"{{obj.name}} UVレイヤー数: {{uv_count}}")

# FBXエクスポート (完全データ保持)
bpy.ops.export_scene.fbx(
    filepath="{output_fbx}",
    use_selection=False,
    object_types={{'MESH', 'ARMATURE', 'LIGHT', 'CAMERA'}},
    use_mesh_modifiers=True,
    add_leaf_bones=False,
    bake_anim=False,
    embed_textures=False
)

print(f"完全データFBX出力完了: {Path(output_fbx).name}")
'''
        
        cmd = ["blender", "--background", "--python-expr", blender_script]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ 完全データFBX作成成功: {Path(output_fbx).name}")
            return True
        else:
            print(f"❌ 完全データFBX作成失敗: {result.stderr}")
            return False
    
    def _create_stripped_fbx(self, input_fbx: str, output_fbx: str) -> bool:
        """FBXからUVとマテリアルを削除したストリップ版を作成"""
        
        blender_script = f'''
import bpy

# シーンクリア
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

print("=== FBXストリップ処理 ===")

# FBXインポート
bpy.ops.import_scene.fbx(filepath="{input_fbx}")
print(f"FBXインポート完了: {Path(input_fbx).name}")

# 全画像削除
for image in list(bpy.data.images):
    if image.name not in ['Render Result', 'Viewer Node']:
        bpy.data.images.remove(image)
        
# 全マテリアル削除
for material in list(bpy.data.materials):
    bpy.data.materials.remove(material)

# 各メッシュのUVマップ削除とマテリアル割り当て解除
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        # マテリアル割り当て解除
        obj.data.materials.clear()
        
        # UVマップ削除
        while obj.data.uv_layers:
            obj.data.uv_layers.remove(obj.data.uv_layers[0])

print("ストリップ処理完了")

# ストリップFBXエクスポート
bpy.ops.export_scene.fbx(
    filepath="{output_fbx}",
    use_selection=False,
    object_types={{'MESH', 'ARMATURE'}},
    use_mesh_modifiers=True,
    add_leaf_bones=False,
    bake_anim=False
)

print(f"ストリップFBX出力完了: {Path(output_fbx).name}")
'''
        
        cmd = ["blender", "--background", "--python-expr", blender_script]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ ストリップFBX作成成功: {Path(output_fbx).name}")
            return True
        else:
            print(f"❌ ストリップFBX作成失敗: {result.stderr}")
            return False
    
    def _merge_fbx_models_github_pattern(self, stripped_fbx: str, data_fbx: str, output_fbx: str) -> bool:
        """GitHubパターンによる2つのFBXファイルの統合"""
        
        blender_script = f'''
import bpy
from pathlib import Path

# 全ての必要な関数をBlenderスクリプト内で定義

def transfer_uv_data_github_pattern(target_mesh, source_mesh):
    """GitHubで学習した直接UV座標コピー方式 (Blender 4.2対応)"""
    print("★ GitHubパターンUV転送開始...")
    
    try:
        # ソースメッシュのUVレイヤーを取得
        source_uv_layers = source_mesh.data.uv_layers
        if not source_uv_layers:
            print("警告: ソースメッシュにUVレイヤーがありません")
            return False
        
        print(f"ソースUVレイヤー数: {{len(source_uv_layers)}}")
        
        # ターゲットメッシュの既存UVレイヤーをクリア
        while target_mesh.data.uv_layers:
            target_mesh.data.uv_layers.remove(target_mesh.data.uv_layers[0])
        
        # 各UVレイヤーを直接コピー
        uv_transfer_count = 0
        for uv_layer in source_uv_layers:
            print(f"UV転送中: {{uv_layer.name}}")
            
            # 新しいUVレイヤーを作成
            new_uv_layer = target_mesh.data.uv_layers.new(name=uv_layer.name)
            
            # メッシュのデータ更新
            target_mesh.data.update()
            source_mesh.data.update()
            
            # ★ GitHubパターン: 直接UV座標をコピー ★
            # ループ数の確認
            source_loop_count = len(source_mesh.data.loops)
            target_loop_count = len(target_mesh.data.loops)
            copy_count = min(source_loop_count, target_loop_count)
            
            print(f"ソースループ数: {{source_loop_count}}, ターゲットループ数: {{target_loop_count}}")
            print(f"コピー対象ループ数: {{copy_count}}")
            
            # UV座標の直接コピー
            for loop_idx in range(copy_count):
                new_uv_layer.data[loop_idx].uv = uv_layer.data[loop_idx].uv
            
            uv_transfer_count += 1
            print(f"UV転送完了: {{uv_layer.name}} ({{copy_count}}個のUV座標)")
        
        print(f"✅ GitHubパターンUV転送成功: {{uv_transfer_count}}個のUVレイヤー")
        return True
        
    except Exception as e:
        print(f"❌ GitHubパターンUV転送エラー: {{e}}")
        return False

def transfer_materials(target_mesh, source_mesh):
    """マテリアル転送"""
    print("マテリアル転送開始...")
    
    try:
        # ソースメッシュのマテリアルをターゲットにコピー
        target_mesh.data.materials.clear()
        for material in source_mesh.data.materials:
            target_mesh.data.materials.append(material)
        
        print(f"✅ マテリアル転送成功: {{len(source_mesh.data.materials)}}個")
        return True
    except Exception as e:
        print(f"❌ マテリアル転送エラー: {{e}}")
        return False

def cleanup_model_objects(objects_to_remove):
    """不要なオブジェクトを削除"""
    for obj in objects_to_remove:
        if obj.name in bpy.data.objects:
            bpy.data.objects.remove(obj, do_unlink=True)

def export_merged_model(mesh_obj, armature_obj, output_path):
    """統合されたモデルをエクスポート"""
    print("統合モデルエクスポート開始...")
    
    # 全てのオブジェクトの選択を解除
    bpy.ops.object.select_all(action='DESELECT')
    
    # メッシュとアーマチュアを選択
    mesh_obj.select_set(True)
    if armature_obj:
        armature_obj.select_set(True)
    
    # アクティブオブジェクトを設定
    bpy.context.view_layer.objects.active = mesh_obj
    
    # FBXエクスポート
    bpy.ops.export_scene.fbx(
        filepath=output_path,
        use_selection=True,
        object_types={{'MESH', 'ARMATURE'}},
        use_mesh_modifiers=True,
        add_leaf_bones=False,
        bake_anim=False,
        embed_textures=False
    )
    
    print(f"✅ 統合モデルエクスポート完了: {{Path(output_path).name}}")

# メイン処理開始
print("=== GitHubパターン適用FBX統合開始 ===")

# シーンクリア
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# モデル1 (完全データ) をインポート
print("モデル1 (完全データ) インポート...")
bpy.ops.import_scene.fbx(filepath="{data_fbx}")
model1_objects = list(bpy.context.scene.objects)

model1_mesh = None
model1_armature = None
for obj in model1_objects:
    if obj.type == 'MESH':
        model1_mesh = obj
    elif obj.type == 'ARMATURE':
        model1_armature = obj

if not model1_mesh:
    raise Exception("モデル1にメッシュが見つかりません")

print(f"モデル1メッシュ: {{model1_mesh.name}}")
if model1_armature:
    print(f"モデル1アーマチュア: {{model1_armature.name}}")

# モデル2 (ストリップ) をインポート
print("モデル2 (ストリップ) インポート...")
bpy.ops.import_scene.fbx(filepath="{stripped_fbx}")

# 新しくインポートされたオブジェクトを特定
all_objects = set(bpy.context.scene.objects)
model1_object_set = set(model1_objects)
model2_objects = list(all_objects - model1_object_set)

model2_mesh = None
for obj in model2_objects:
    if obj.type == 'MESH':
        model2_mesh = obj
        break

if not model2_mesh:
    raise Exception("モデル2にメッシュが見つかりません")

print(f"モデル2メッシュ: {{model2_mesh.name}}")

# ★ GitHubで学習したUV転送パターンを適用 ★
transfer_uv_data_github_pattern(model1_mesh, model2_mesh)

# マテリアル転送
transfer_materials(model1_mesh, model2_mesh)

# モデル2のオブジェクトを削除
cleanup_model_objects(model2_objects)

# 統合されたモデルをエクスポート
export_merged_model(model1_mesh, model1_armature, "{output_fbx}")

print("=== GitHubパターン適用FBX統合完了 ===")
'''
        
        cmd = ["blender", "--background", "--python-expr", blender_script]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ GitHubパターンFBX統合成功: {Path(output_fbx).name}")
            return True
        else:
            print(f"❌ GitHubパターンFBX統合失敗: {result.stderr}")
            print(f"stdout: {result.stdout}")
            return False

def main():
    """テスト実行"""
    print("=== Step5 修正版完全テスト開始 ===")
    
    step5 = Step5FixedComplete()
    input_glb = "/app/bird.glb"
    model_name = "bird"
    
    if not Path(input_glb).exists():
        print(f"❌ 入力ファイルが見つかりません: {input_glb}")
        return False
    
    success = step5.run_complete_flow(input_glb, model_name)
    
    if success:
        print("✅ Step5修正版テスト完了!")
        
        # 結果ファイルサイズ確認
        output_dir = Path("/app/test_step5_fixed_complete")
        for fbx_file in output_dir.glob("*.fbx"):
            size_mb = fbx_file.stat().st_size / 1024 / 1024
            print(f"📁 {fbx_file.name}: {size_mb:.1f}MB")
    else:
        print("❌ Step5修正版テスト失敗")
    
    return success

if __name__ == "__main__":
    main()
