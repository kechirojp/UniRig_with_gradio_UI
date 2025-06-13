#!/usr/bin/env python3
"""
あなたのBlender 4.2コードを完全に忠実に再現したStep5
2つの独立したFBXファイル間でのデータ統合
"""

import subprocess
import os
from pathlib import Path

class Step5TrueFBXMerge:
    """あなたのパターンを完全再現"""
    
    def __init__(self, output_dir: str = "/app/test_step5_true_fbx_merge"):
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
            
            # Step3: あなたの手法で2つのFBXを統合
            fbx_merged = self.output_dir / f"{model_name}_merged_final.fbx"
            return self._merge_fbx_models(str(fbx_stripped), str(fbx_with_data), str(fbx_merged))
            
        except Exception as e:
            print(f"❌ エラー: {e}")
            return False
    
    def _glb_to_fbx_with_data(self, input_glb: str, output_fbx: str) -> bool:
        """GLBファイルを完全データ保持でFBXに変換"""
        
        blender_script = '''
import bpy

# シーンクリア
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

print("=== GLB → FBX (完全データ保持) ===")

# GLBインポート
bpy.ops.import_scene.gltf(filepath="{}")
print("GLBインポート完了: " + str("{}")[-50:])

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
    filepath="{}",
    use_selection=False,
    object_types={{'MESH', 'ARMATURE'}},
    use_mesh_modifiers=True,
    add_leaf_bones=False,
    bake_anim=False,
    path_mode='COPY',
    embed_textures=False
)

print("FBX出力完了: " + str("{}")[-50:])
'''.format(input_glb, input_glb, output_fbx, output_fbx)
        
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
        
        blender_script = '''
import bpy

# シーンクリア
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

print("=== FBXストリップ処理 ===")

# FBXインポート
bpy.ops.import_scene.fbx(filepath="{}")
print("FBXインポート完了: " + str("{}")[-50:])

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
    filepath="{}",
    use_selection=False,
    object_types={{'MESH', 'ARMATURE'}},
    use_mesh_modifiers=True,
    add_leaf_bones=False,
    bake_anim=False
)

print("ストリップFBX出力完了: " + str("{}")[-50:])
'''.format(input_fbx, input_fbx, output_fbx, output_fbx)
        
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
        
        blender_script = '''
import bpy

def merge_fbx_models(model1_path, model2_path, output_path):
    """
    GitHubで学習したUV転送パターンを完全適用 (Blender 4.2対応版)
    model1_path: スケルトンとスキンウェイトを持つFBXファイル
    model2_path: UV、マテリアル、テクスチャを持つFBXファイル  
    output_path: 出力FBXファイルのパス
    """
    
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
    """GitHubで学習した直接UV座標コピー方式 (Blender 4.2対応)"""
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
            print("UV転送中: " + uv_layer.name)'''.format(model1_path, model2_path, output_path)
            
            # ★ GitHubパターン: 新しいUVレイヤーを作成 ★
            new_uv_layer = target_mesh.data.uv_layers.new(name=uv_layer.name)
            
            # ★ GitHubパターン: UVデータを直接コピー ★
            source_loops = len(source_mesh.data.loops)
            target_loops = len(target_mesh.data.loops)
            
            print(f"ループ数 - ソース: {{source_loops}}, ターゲット: {{target_loops}}")
            
            # 安全な範囲でUV座標をコピー
            copy_count = min(source_loops, target_loops)
            for loop_idx in range(copy_count):
                new_uv_layer.data[loop_idx].uv = uv_layer.data[loop_idx].uv
            
            uv_transfer_count += 1
            print(f"UV転送完了: {{uv_layer.name}} ({{copy_count}}個のUV座標)")
        
        print(f"★ GitHubパターンUV転送成功: {{uv_transfer_count}}個のUVレイヤー")
        return True
        
    except Exception as e:
        print(f"GitHubパターンUV転送エラー: {{e}}")
        import traceback
        traceback.print_exc()
        return False

def transfer_materials(source_mesh, target_mesh):
    """マテリアル転送 (Blender 4.2対応)"""
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
                print(f"マテリアル転送: {{material.name}}")
        
        print(f"マテリアル転送完了: {{material_count}}個")
        return True
        
    except Exception as e:
        print(f"マテリアル転送エラー: {{e}}")
        return False

def cleanup_model2_objects(model2_objects):
    """モデル2の不要なオブジェクトを削除"""
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
        print(f"{{deletion_count}}個のオブジェクトを削除しました")

def export_merged_model(mesh_obj, armature_obj, output_path):
    """統合されたモデルをFBXでエクスポート (Blender 4.2対応)"""
    print(f"エクスポート開始: {{output_path}}")
    
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
        # use_ascii=False <- Blender 4.2では削除済み
    )
    
    print("エクスポート完了")

def verify_merge_result(mesh_obj):
    """統合結果の検証"""
    print("\\n=== 統合結果の検証 ===")
    
    # UVマップの確認
    if mesh_obj.data.uv_layers:
        print(f"✅ UVマップ数: {{len(mesh_obj.data.uv_layers)}}")
        for i, uv in enumerate(mesh_obj.data.uv_layers):
            print(f"  UV {{i+1}}: {{uv.name}}")
            
            # UVデータの実在性確認
            uv_data_count = len(uv.data)
            print(f"    UVデータ数: {{uv_data_count}}")
            
            # 有効なUV座標の確認
            valid_uv_count = 0
            for uv_data in uv.data:
                if uv_data.uv[0] != 0.0 or uv_data.uv[1] != 0.0:
                    valid_uv_count += 1
            print(f"    有効なUV座標: {{valid_uv_count}}")
    else:
        print("❌ 警告: UVマップが見つかりません")
    
    # マテリアルの確認
    if mesh_obj.data.materials:
        print(f"✅ マテリアル数: {{len(mesh_obj.data.materials)}}")
        for i, mat in enumerate(mesh_obj.data.materials):
            if mat:
                print(f"  マテリアル {{i+1}}: {{mat.name}}")
                if mat.use_nodes and mat.node_tree:
                    texture_count = sum(1 for node in mat.node_tree.nodes if node.type == 'TEX_IMAGE')
                    print(f"    テクスチャノード数: {{texture_count}}")
            else:
                print(f"  マテリアル {{i+1}}: None")
    else:
        print("❌ 警告: マテリアルが見つかりません")
    
    # メッシュ統計情報
    print(f"頂点数: {{len(mesh_obj.data.vertices)}}")
    print(f"面数: {{len(mesh_obj.data.polygons)}}")
    print(f"ループ数: {{len(mesh_obj.data.loops)}}")

# 実行
try:
    merge_fbx_models("{model1_path}", "{model2_path}", "{output_path}")
    
    # 結果検証
    merged_mesh = next((obj for obj in bpy.context.scene.objects if obj.type == 'MESH'), None)
    if merged_mesh:
        verify_merge_result(merged_mesh)
    
    print(f"\\n🎉 GitHubパターン適用統合完了！出力ファイル: {output_path}")
    
except Exception as e:
    print(f"\\n❌ エラーが発生しました: {{e}}")
    import traceback
    traceback.print_exc()
'''
        
        cmd = ["blender", "--background", "--python-expr", blender_script]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ FBX統合成功: {Path(output_path).name}")
            return True
        else:
            print(f"❌ FBX統合失敗: {result.stderr}")
            return False

if __name__ == "__main__":
    print("🚀 Step5 True FBX Merge テスト開始")
    
    # テスト用サンプルファイル（正しいパス）
    test_glb = "/app/examples/bird.glb"
    model_name = "bird_test"
    
    if not os.path.exists(test_glb):
        print(f"❌ エラー: テストファイルが見つかりません: {test_glb}")
        exit(1)
    
    # Step5テスト実行
    step5 = Step5TrueFBXMerge()
    success = step5.run_complete_flow(test_glb, model_name)
    
    if success:
        print("✅ Step5 True FBX Merge テスト成功！")
        
        # 出力ファイルサイズ確認
        output_dir = Path("/app/test_step5_true_fbx_merge")
        for fbx_file in output_dir.glob("*.fbx"):
            file_size = fbx_file.stat().st_size / 1024  # KB
            print(f"📁 {fbx_file.name}: {file_size:.1f}KB")
    else:
        print("❌ Step5 True FBX Merge テスト失敗")
