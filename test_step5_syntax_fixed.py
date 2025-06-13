#!/usr/bin/env python3
"""
Step5 UV復元問題修正版 - Blender 4.2 API対応
"""

import subprocess
import os
from pathlib import Path

class Step5TrueFBXMerge:
    """Blender 4.2対応FBX統合クラス"""
    
    def __init__(self, output_dir: str = "/app/test_step5_syntax_fixed"):
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
            
            # Step3: FBX統合
            fbx_merged = self.output_dir / f"{model_name}_merged_final.fbx"
            return self._merge_fbx_models(str(fbx_stripped), str(fbx_with_data), str(fbx_merged))
            
        except Exception as e:
            print(f"❌ エラー: {e}")
            return False
    
    def _glb_to_fbx_with_data(self, input_glb: str, output_fbx: str) -> bool:
        """GLBファイルを完全データ保持でFBXに変換"""
        
        blender_script = f"""
import bpy

# シーンクリア
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

print("=== GLB → FBX (完全データ保持) ===")

# GLBインポート
bpy.ops.import_scene.gltf(filepath="{input_glb}")
print("GLBインポート完了")

# データ状態確認
meshes = [obj for obj in bpy.data.objects if obj.type == 'MESH']
materials = list(bpy.data.materials)
images = [img for img in bpy.data.images if img.name not in ['Render Result', 'Viewer Node']]

print("メッシュ数: " + str(len(meshes)))
print("マテリアル数: " + str(len(materials)))
print("画像数: " + str(len(images)))

# UVマップ確認
for mesh in meshes:
    uv_count = len(mesh.data.uv_layers)
    print("UV (" + mesh.name + "): " + str(uv_count) + "個")

# FBXエクスポート (完全データ保持)
bpy.ops.export_scene.fbx(
    filepath="{output_fbx}",
    use_selection=False,
    object_types={{'MESH', 'ARMATURE'}},
    use_mesh_modifiers=True,
    add_leaf_bones=False,
    bake_anim=False,
    path_mode='COPY',
    embed_textures=False
)

print("FBX出力完了")
"""
        
        cmd = ["blender", "--background", "--python-expr", blender_script]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ GLB→FBX変換成功: {Path(output_fbx).name}")
            return True
        else:
            print(f"❌ GLB→FBX変換失敗: {result.stderr}")
            return False
    
    def _create_stripped_fbx(self, input_fbx: str, output_fbx: str) -> bool:
        """FBXからUVとマテリアルを削除してストリップ版作成"""
        
        blender_script = f"""
import bpy

# シーンクリア
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

print("=== FBXストリップ処理 ===")

# FBXインポート
bpy.ops.import_scene.fbx(filepath="{input_fbx}")
print("FBXインポート完了")

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

print("ストリップFBX出力完了")
"""
        
        cmd = ["blender", "--background", "--python-expr", blender_script]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ ストリップFBX作成成功: {Path(output_fbx).name}")
            return True
        else:
            print(f"❌ ストリップFBX作成失敗: {result.stderr}")
            return False
    
    def _merge_fbx_models(self, model1_path: str, model2_path: str, output_path: str) -> bool:
        """GitHubで学習したUV転送パターンを完全適用したBlender 4.2対応FBX統合"""
        
        blender_script = f"""
import bpy

def merge_fbx_models(model1_path, model2_path, output_path):
    # シーンをクリア
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    print("=== GitHubパターン適用FBX統合開始 ===")
    
    # モデル1（スケルトン+スキンウェイト）をインポート
    print("モデル1をインポート中: " + model1_path)
    bpy.ops.import_scene.fbx(filepath=model1_path)
    
    # インポートされたオブジェクトを記録
    model1_objects = [obj for obj in bpy.context.selected_objects]
    model1_mesh = None
    model1_armature = None
    
    for obj in model1_objects:
        if obj.type == 'MESH':
            model1_mesh = obj
        elif obj.type == 'ARMATURE':
            model1_armature = obj
    
    if not model1_mesh:
        raise Exception("モデル1にメッシュが見つかりません")
    
    print("モデル1メッシュ: " + model1_mesh.name)
    if model1_armature:
        print("モデル1アーマチュア: " + model1_armature.name)
    
    # モデル2（UV+マテリアル+テクスチャ）をインポート
    print("モデル2をインポート中: " + model2_path)
    bpy.ops.import_scene.fbx(filepath=model2_path)
    
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
    
    print("モデル2メッシュ: " + model2_mesh.name)
    
    # ★ GitHubで学習したUV転送パターンを適用 ★
    transfer_uv_data_github_pattern(model2_mesh, model1_mesh)
    
    # マテリアル転送
    transfer_materials(model2_mesh, model1_mesh)
    
    # モデル2のオブジェクトを削除
    cleanup_model2_objects(model2_objects)
    
    # 統合されたモデルをエクスポート
    export_merged_model(model1_mesh, model1_armature, output_path)
    
    print("=== GitHubパターン適用FBX統合完了 ===")

def transfer_uv_data_github_pattern(source_mesh, target_mesh):
    print("★ GitHubパターンUV転送開始...")
    
    try:
        # ソースメッシュのUVレイヤーを取得
        source_uv_layers = source_mesh.data.uv_layers
        if not source_uv_layers:
            print("警告: ソースメッシュにUVレイヤーがありません")
            return False
        
        print("ソースUVレイヤー数: " + str(len(source_uv_layers)))
        
        # ターゲットメッシュの既存UVレイヤーをクリア
        while target_mesh.data.uv_layers:
            target_mesh.data.uv_layers.remove(target_mesh.data.uv_layers[0])
        
        # 各UVレイヤーを直接コピー
        uv_transfer_count = 0
        for uv_layer in source_uv_layers:
            print("UV転送中: " + uv_layer.name)
            
            # ★ GitHubパターン: 新しいUVレイヤーを作成 ★
            new_uv_layer = target_mesh.data.uv_layers.new(name=uv_layer.name)
            
            # ★ GitHubパターン: UVデータを直接コピー ★
            source_loops = len(source_mesh.data.loops)
            target_loops = len(target_mesh.data.loops)
            
            print("ループ数 - ソース: " + str(source_loops) + ", ターゲット: " + str(target_loops))
            
            # 安全な範囲でUV座標をコピー
            copy_count = min(source_loops, target_loops)
            for loop_idx in range(copy_count):
                new_uv_layer.data[loop_idx].uv = uv_layer.data[loop_idx].uv
            
            uv_transfer_count += 1
            print("UV転送完了: " + uv_layer.name + " (" + str(copy_count) + "個のUV座標)")
        
        print("★ GitHubパターンUV転送成功: " + str(uv_transfer_count) + "個のUVレイヤー")
        return True
        
    except Exception as e:
        print("GitHubパターンUV転送エラー: " + str(e))
        import traceback
        traceback.print_exc()
        return False

def transfer_materials(source_mesh, target_mesh):
    print("マテリアル転送開始...")
    
    try:
        # ターゲットの既存マテリアルをクリア
        target_mesh.data.materials.clear()
        
        # ソースからマテリアルをコピー
        material_count = 0
        for material in source_mesh.data.materials:
            target_mesh.data.materials.append(material)
            material_count += 1
            if material:
                print("マテリアル転送: " + material.name)
        
        print("マテリアル転送完了: " + str(material_count) + "個")
        return True
        
    except Exception as e:
        print("マテリアル転送エラー: " + str(e))
        return False

def cleanup_model2_objects(model2_objects):
    print("モデル2のオブジェクトを削除中...")
    
    bpy.ops.object.select_all(action='DESELECT')
    deletion_count = 0
    for obj in model2_objects:
        # オブジェクトが存在するか確認してから選択
        if obj.name in bpy.data.objects:
            obj.select_set(True)
            deletion_count += 1
    
    if deletion_count > 0:
        bpy.ops.object.delete(use_global=False)
        print(str(deletion_count) + "個のオブジェクトを削除しました")

def export_merged_model(mesh_obj, armature_obj, output_path):
    print("エクスポート開始: " + output_path)
    
    # エクスポートするオブジェクトを選択
    bpy.ops.object.select_all(action='DESELECT')
    mesh_obj.select_set(True)
    if armature_obj:
        armature_obj.select_set(True)
    
    # Blender 4.2対応FBXエクスポート設定
    bpy.ops.export_scene.fbx(
        filepath=output_path,
        use_selection=True,
        object_types={{'MESH', 'ARMATURE'}},
        use_mesh_modifiers=True,
        add_leaf_bones=False,
        bake_anim=False,
        path_mode='COPY',
        embed_textures=False
    )
    
    print("エクスポート完了")

def verify_merge_result(mesh_obj):
    print("")
    print("=== 統合結果の検証 ===")
    
    # UVマップの確認
    if mesh_obj.data.uv_layers:
        print("✅ UVマップ数: " + str(len(mesh_obj.data.uv_layers)))
        for i, uv in enumerate(mesh_obj.data.uv_layers):
            print("  UV " + str(i+1) + ": " + uv.name)
            
            # UVデータの実在性確認
            uv_data_count = len(uv.data)
            print("    UVデータ数: " + str(uv_data_count))
            
            # 有効なUV座標の確認
            valid_uv_count = 0
            for uv_data in uv.data:
                if uv_data.uv[0] != 0.0 or uv_data.uv[1] != 0.0:
                    valid_uv_count += 1
            print("    有効なUV座標: " + str(valid_uv_count))
    else:
        print("❌ 警告: UVマップが見つかりません")
    
    # マテリアルの確認
    if mesh_obj.data.materials:
        print("✅ マテリアル数: " + str(len(mesh_obj.data.materials)))
        for i, mat in enumerate(mesh_obj.data.materials):
            if mat:
                print("  マテリアル " + str(i+1) + ": " + mat.name)
                if mat.use_nodes and mat.node_tree:
                    texture_count = sum(1 for node in mat.node_tree.nodes if node.type == 'TEX_IMAGE')
                    print("    テクスチャノード数: " + str(texture_count))
            else:
                print("  マテリアル " + str(i+1) + ": None")
    else:
        print("❌ 警告: マテリアルが見つかりません")
    
    # メッシュ統計情報
    print("頂点数: " + str(len(mesh_obj.data.vertices)))
    print("面数: " + str(len(mesh_obj.data.polygons)))
    print("ループ数: " + str(len(mesh_obj.data.loops)))

# 実行
try:
    merge_fbx_models("{model1_path}", "{model2_path}", "{output_path}")
    
    # 結果検証
    merged_mesh = next((obj for obj in bpy.context.scene.objects if obj.type == 'MESH'), None)
    if merged_mesh:
        verify_merge_result(merged_mesh)
    
    print("")
    print("🎉 GitHubパターン適用統合完了！出力ファイル: {output_path}")
    
except Exception as e:
    print("")
    print("❌ エラーが発生しました: " + str(e))
    import traceback
    traceback.print_exc()
"""
        
        cmd = ["blender", "--background", "--python-expr", blender_script]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        print("=== Blenderの実行出力 ===")
        print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print(f"✅ FBX統合成功: {Path(output_path).name}")
            return True
        else:
            print(f"❌ FBX統合失敗: return code {result.returncode}")
            return False

def main():
    """テスト実行"""
    step5 = Step5TrueFBXMerge()
    
    # テスト用ファイル設定
    input_glb = "/app/examples/bird.glb"
    model_name = "bird"
    
    print("🚀 Step5統合フロー開始")
    print(f"入力GLB: {input_glb}")
    print(f"出力ディレクトリ: {step5.output_dir}")
    
    if not Path(input_glb).exists():
        print(f"❌ 入力ファイルが見つかりません: {input_glb}")
        return False
    
    success = step5.run_complete_flow(input_glb, model_name)
    
    if success:
        print("🎉 統合完了！")
        
        # 出力ファイルのサイズ確認
        final_fbx = step5.output_dir / f"{model_name}_merged_final.fbx"
        if final_fbx.exists():
            size_mb = final_fbx.stat().st_size / (1024 * 1024)
            print(f"最終FBXファイルサイズ: {size_mb:.2f} MB")
        
        print(f"出力ディレクトリ内容:")
        for file in step5.output_dir.iterdir():
            if file.is_file():
                size_mb = file.stat().st_size / (1024 * 1024)
                print(f"  {file.name}: {size_mb:.2f} MB")
    else:
        print("❌ 統合失敗")
    
    return success

if __name__ == "__main__":
    main()
