#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step5 Blender正規フロー 簡易テスト
正しいマテリアル・テクスチャ復元フロー実装

フロー:
1. 3Dモデルをインポート→Blenderファイル化→モデル1
2. モデル1を別名保存→UV/マテリアル/テクスチャ削除→モデル2  
3. モデル2をモデル1のUV/マテリアル/テクスチャで復元
4. モデル2をFBX化
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Tuple, Dict

class Step5BlenderFlowTest:
    """Step5 Blender正規フロー テストクラス"""
    
    def __init__(self, test_model_path: str):
        self.test_model_path = Path(test_model_path)
        self.test_name = f"test_{self.test_model_path.stem}"
        # test_step5_outputディレクトリを作業ディレクトリとして使用
        self.temp_dir = Path("/app/test_step5_output")
        self.temp_dir.mkdir(exist_ok=True)
        
        print(f"📁 テスト作業ディレクトリ: {self.temp_dir}")
    
    def run_complete_test(self) -> bool:
        """完全テストフロー実行"""
        try:
            print("🚀 Step5 Blender正規フロー テスト開始")
            
            # ステップ1: 3Dモデルインポート→Blenderファイル化（モデル1）
            print("\n📋 ステップ1: 3Dモデルインポート→Blenderファイル化（モデル1）")
            model1_blend = self._step1_import_to_blend()
            
            # ステップ2: モデル1別名保存→UV/マテリアル/テクスチャ削除（モデル2）
            print("\n🔧 ステップ2: UV/マテリアル/テクスチャ削除（モデル2）")
            model2_blend = self._step2_create_stripped_model(model1_blend)
            
            # ステップ3: モデル2をモデル1のデータで復元
            print("\n🎨 ステップ3: マテリアル・テクスチャ復元")
            success = self._step3_restore_materials(model1_blend, model2_blend)
            
            # ステップ4: モデル2をFBX化
            print("\n📦 ステップ4: モデル2をFBX化")
            final_fbx = self._step4_export_fbx(model2_blend)
            
            # 結果検証
            print("\n🔍 結果検証")
            self._verify_results()
            
            return success
            
        except Exception as e:
            print(f"❌ テスト実行エラー: {e}")
            return False
        finally:
            self._cleanup()
    
    def _step1_import_to_blend(self) -> str:
        """ステップ1: 3DモデルをインポートしてBlenderファイル化（モデル1）"""
        
        model1_blend_path = self.temp_dir / f"{self.test_name}_model1.blend"
        
        # Blenderスクリプト作成（f-string回避）
        blender_script = """
import bpy

# 新しいシーンを作成
bpy.ops.wm.read_homefile(use_empty=True)
print("新しいシーンを作成")

# GLBファイルを読み込み
bpy.ops.import_scene.gltf(filepath="{input_path}")
print("GLBファイルを読み込み: {input_name}")

# データ状態確認
mesh_count = len([obj for obj in bpy.data.objects if obj.type == 'MESH'])
material_count = len(bpy.data.materials)
image_count = len(bpy.data.images)

print("インポート結果:")
print("  - メッシュ数: " + str(mesh_count))
print("  - マテリアル数: " + str(material_count))
print("  - 画像数: " + str(image_count))

# UVマップ情報確認
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        uv_count = len(obj.data.uv_layers)
        print("  - UV (" + obj.name + "): " + str(uv_count) + "個")

# モデル1として保存
bpy.ops.wm.save_as_mainfile(filepath="{model1_path}")
print("モデル1をBlendファイルに保存: {model1_name}")
""".format(
            input_path=str(self.test_model_path),
            input_name=self.test_model_path.name,
            model1_path=str(model1_blend_path),
            model1_name=model1_blend_path.name
        )
        
        # Blender実行
        cmd = ["blender", "--background", "--python-expr", blender_script]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            raise RuntimeError(f"モデル1作成失敗: {result.stderr}")
        
        print(f"  ✅ モデル1作成完了: {model1_blend_path.name}")
        return str(model1_blend_path)
    
    def _step2_create_stripped_model(self, model1_blend: str) -> str:
        """ステップ2: モデル1をストリップしてモデル2作成"""
        
        model2_blend_path = self.temp_dir / f"{self.test_name}_model2.blend"
        
        # Blenderスクリプト作成（f-string回避）
        blender_script = """
import bpy

# モデル1を読み込み
bpy.ops.wm.open_mainfile(filepath="{model1_path}")
print("モデル1を読み込み: {model1_name}")

# 画像・マテリアル・UVを削除してストリップ
# 全画像削除
for image in list(bpy.data.images):
    if image.name != "Render Result" and image.name != "Viewer Node":
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

print("UV/マテリアル/テクスチャ削除完了")

# ストリップ後状態確認
mesh_count = len([obj for obj in bpy.data.objects if obj.type == 'MESH'])
material_count = len(bpy.data.materials) 
image_count = len(bpy.data.images)

print("ストリップ後状態:")
print("  - メッシュ数: " + str(mesh_count))
print("  - マテリアル数: " + str(material_count))
print("  - 画像数: " + str(image_count))

# モデル2として別名保存
bpy.ops.wm.save_as_mainfile(filepath="{model2_path}")
print("モデル2をBlendファイルに保存: {model2_name}")
""".format(
            model1_path=model1_blend,
            model1_name=Path(model1_blend).name,
            model2_path=str(model2_blend_path),
            model2_name=model2_blend_path.name
        )
        
        # Blender実行
        cmd = ["blender", "--background", "--python-expr", blender_script]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            raise RuntimeError(f"モデル2作成失敗: {result.stderr}")
        
        print(f"  ✅ モデル2作成完了: {model2_blend_path.name}")
        return str(model2_blend_path)
    
    def _step3_restore_materials(self, model1_blend: str, model2_blend: str) -> bool:
        """ステップ3: モデル2をモデル1のUV/マテリアル/テクスチャで復元"""
        
        # Blenderスクリプト作成（f-string完全回避）
        blender_script = """
import bpy
import bmesh
import os
from mathutils import Vector

print("=== ステップ3: マテリアル・テクスチャ復元開始 ===")

# Phase 1: モデル1（ソース）からデータ取得
print("Phase 1: モデル1からデータ取得")
bpy.ops.wm.open_mainfile(filepath="{model1_path}")

# ソースデータ収集
source_data = {{"materials": {{}}, "images": {{}}, "uv_data": {{}}, "material_assignments": {{}}}}

# マテリアル情報収集
for material in bpy.data.materials:
    mat_data = {{"name": material.name, "use_nodes": material.use_nodes, 
                "diffuse_color": list(material.diffuse_color), "nodes": {{}}, "links": []}}
    
    if material.use_nodes and material.node_tree:
        # ノード情報を収集
        for node in material.node_tree.nodes:
            node_data = {{"name": node.name, "type": node.type, 
                         "location": list(node.location), "properties": {{}}}}
            
            # Image Textureノードの場合
            if node.type == 'TEX_IMAGE' and node.image:
                node_data['image_name'] = node.image.name
            
            # Principled BSDFノードの場合
            if node.type == 'BSDF_PRINCIPLED':
                try:
                    node_data['properties']['base_color'] = list(node.inputs['Base Color'].default_value)
                    node_data['properties']['metallic'] = node.inputs['Metallic'].default_value
                    node_data['properties']['roughness'] = node.inputs['Roughness'].default_value
                except:
                    pass
            
            mat_data['nodes'][node.name] = node_data
        
        # リンク情報を収集
        for link in material.node_tree.links:
            mat_data['links'].append({{"from_node": link.from_node.name, "from_socket": link.from_socket.name,
                                     "to_node": link.to_node.name, "to_socket": link.to_socket.name}})
    
    source_data['materials'][material.name] = mat_data
    print("  収集マテリアル: " + material.name + " (ノード数: " + str(len(mat_data['nodes'])) + ")")

# 画像情報収集
for image in bpy.data.images:
    img_data = {{"name": image.name, "filepath": image.filepath, "size": list(image.size),
                "colorspace": image.colorspace_settings.name if hasattr(image, 'colorspace_settings') else 'sRGB'}}
    source_data['images'][image.name] = img_data
    print("  収集画像: " + image.name + " (" + str(image.size[0]) + "x" + str(image.size[1]) + ")")

# UV情報とマテリアル割り当て収集
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        # UV座標データを収集
        uv_layers_data = {{}}
        for uv_layer in obj.data.uv_layers:
            uv_coords = []
            for loop in obj.data.loops:
                uv = uv_layer.data[loop.index].uv
                uv_coords.append([uv.x, uv.y])
            uv_layers_data[uv_layer.name] = uv_coords
        
        source_data['uv_data'][obj.name] = uv_layers_data
        
        # マテリアル割り当て情報
        source_data['material_assignments'][obj.name] = [mat.name for mat in obj.data.materials if mat]
        
        uv_coord_count = len(uv_coords) if 'uv_coords' in locals() and uv_coords else 0
        print("  収集UV (" + obj.name + "): " + str(list(uv_layers_data.keys())) + " (座標数: " + str(uv_coord_count) + ")")

print("ソースデータ収集完了: マテリアル " + str(len(source_data['materials'])) + "個, 画像 " + str(len(source_data['images'])) + "個")

# Phase 2: モデル2（ターゲット）にデータ適用
print("\\nPhase 2: モデル2にデータ適用")
bpy.ops.wm.open_mainfile(filepath="{model2_path}")

restored_count = {{"materials": 0, "images": 0, "uvs": 0, "assignments": 0}}

# 画像復元
print("画像復元開始...")
for img_name, img_data in source_data['images'].items():
    try:
        if img_data['filepath'] and os.path.exists(img_data['filepath']):
            # 実際の画像ファイルを読み込み
            new_image = bpy.data.images.load(img_data['filepath'])
            new_image.name = img_name
            new_image.colorspace_settings.name = img_data['colorspace']
            print("  復元画像: " + img_name + " (" + img_data['filepath'] + ")")
        else:
            # ファイルが見つからない場合は空の画像を作成
            new_image = bpy.data.images.new(name=img_name, width=img_data['size'][0] or 512, 
                                          height=img_data['size'][1] or 512)
            print("  作成画像: " + img_name + " (元ファイル不明)")
        
        restored_count['images'] += 1
    except Exception as e:
        print("  画像復元エラー (" + img_name + "): " + str(e))

# マテリアル復元
print("マテリアル復元開始...")
for mat_name, mat_data in source_data['materials'].items():
    try:
        # 新しいマテリアル作成
        new_material = bpy.data.materials.new(name=mat_name)
        new_material.use_nodes = mat_data['use_nodes']
        new_material.diffuse_color = mat_data['diffuse_color']
        
        if mat_data['use_nodes']:
            # ノードツリーを構築
            node_tree = new_material.node_tree
            node_tree.nodes.clear()  # 既存ノードをクリア
            
            # ノードを再作成
            created_nodes = {{}}
            for node_name, node_data in mat_data['nodes'].items():
                try:
                    new_node = node_tree.nodes.new(type=node_data['type'])
                    new_node.name = node_name
                    new_node.location = node_data['location']
                    
                    # Image Textureノードの場合、画像を割り当て
                    if node_data['type'] == 'TEX_IMAGE' and 'image_name' in node_data:
                        if node_data['image_name'] in bpy.data.images:
                            new_node.image = bpy.data.images[node_data['image_name']]
                    
                    # Principled BSDFノードのプロパティ復元
                    if node_data['type'] == 'BSDF_PRINCIPLED' and 'properties' in node_data:
                        props = node_data['properties']
                        if 'base_color' in props:
                            new_node.inputs['Base Color'].default_value = props['base_color']
                        if 'metallic' in props:
                            new_node.inputs['Metallic'].default_value = props['metallic']
                        if 'roughness' in props:
                            new_node.inputs['Roughness'].default_value = props['roughness']
                    
                    created_nodes[node_name] = new_node
                except Exception as e:
                    print("    ノード作成エラー (" + node_name + "): " + str(e))
            
            # ノード間のリンクを復元
            for link_data in mat_data['links']:
                try:
                    from_node = created_nodes[link_data['from_node']]
                    to_node = created_nodes[link_data['to_node']]
                    node_tree.links.new(from_node.outputs[link_data['from_socket']], 
                                      to_node.inputs[link_data['to_socket']])
                except Exception as e:
                    print("    リンク作成エラー: " + str(e))
        
        restored_count['materials'] += 1
        print("  復元マテリアル: " + mat_name + " (ノード数: " + str(len(mat_data['nodes'])) + ")")
    except Exception as e:
        print("  マテリアル復元エラー (" + mat_name + "): " + str(e))

# UV座標復元
print("UV座標復元開始...")
for obj in bpy.data.objects:
    if obj.type == 'MESH' and obj.name in source_data['uv_data']:
        try:
            # 編集モードに入る
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            
            # bmeshを使用してUV座標を復元
            bm = bmesh.from_mesh(obj.data)
            
            for uv_layer_name, uv_coords in source_data['uv_data'][obj.name].items():
                # UVレイヤーを作成または取得
                if uv_layer_name not in obj.data.uv_layers:
                    obj.data.uv_layers.new(name=uv_layer_name)
                
                uv_layer = bm.loops.layers.uv.get(uv_layer_name)
                if not uv_layer:
                    uv_layer = bm.loops.layers.uv.new(uv_layer_name)
                
                # UV座標を設定
                for i, face in enumerate(bm.faces):
                    for j, loop in enumerate(face.loops):
                        coord_index = i * len(face.loops) + j
                        if coord_index < len(uv_coords):
                            loop[uv_layer].uv = Vector(uv_coords[coord_index])
            
            # メッシュを更新
            bmesh.update_edit_mesh(obj.data)
            bpy.ops.object.mode_set(mode='OBJECT')
            
            restored_count['uvs'] += len(source_data['uv_data'][obj.name])
            print("  復元UV (" + obj.name + "): " + str(list(source_data['uv_data'][obj.name].keys())))
        except Exception as e:
            print("  UV復元エラー (" + obj.name + "): " + str(e))
            # エラーが発生した場合は確実にオブジェクトモードに戻る
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except:
                pass

# マテリアル割り当て復元
print("マテリアル割り当て復元開始...")
for obj in bpy.data.objects:
    if obj.type == 'MESH' and obj.name in source_data['material_assignments']:
        try:
            # 既存のマテリアルスロットをクリア
            obj.data.materials.clear()
            
            # マテリアルを再割り当て
            for mat_name in source_data['material_assignments'][obj.name]:
                if mat_name in bpy.data.materials:
                    obj.data.materials.append(bpy.data.materials[mat_name])
                    restored_count['assignments'] += 1
            
            print("  マテリアル割り当て (" + obj.name + "): " + str(source_data['material_assignments'][obj.name]))
        except Exception as e:
            print("  マテリアル割り当てエラー (" + obj.name + "): " + str(e))

# 復元結果保存
bpy.ops.wm.save_mainfile(filepath="{model2_blend}")

print("\\n=== 復元完了 ===")
print("復元マテリアル: " + str(restored_count['materials']) + "個, 復元画像: " + str(restored_count['images']) + "個")
print("復元UV: " + str(restored_count['uvs']) + "個, マテリアル割り当て: " + str(restored_count['assignments']) + "個")

# 成功判定
total_restored = sum(restored_count.values())
if total_restored > 0:
    print("✅ 復元処理成功")
else:
    print("❌ 復元処理失敗")
    exit(1)
""".format(
            model1_path=model1_blend,
            model2_path=model2_blend,
            model2_blend=model2_blend
        )
        
        # Blender実行
        cmd = ["blender", "--background", "--python-expr", blender_script]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        success = result.returncode == 0
        
        if success:
            print(f"  ✅ マテリアル・テクスチャ復元完了")
        else:
            print(f"  ❌ 復元失敗: {result.stderr}")
        
        print(f"  📄 復元ログ:")
        for line in result.stdout.split('\n'):
            if line.strip():
                print(f"    {line}")
        
        return success
    
    def _step4_export_fbx(self, model2_blend: str) -> str:
        """ステップ4: モデル2をFBX化"""
        
        final_fbx_path = self.temp_dir / f"{self.test_name}_final.fbx"
        
        # Blenderスクリプト作成（f-string回避）
        blender_script = """
import bpy

# モデル2を読み込み
bpy.ops.wm.open_mainfile(filepath="{model2_blend}")
print("モデル2を読み込みました")

# エクスポート前状態確認
mesh_count = len([obj for obj in bpy.data.objects if obj.type == 'MESH'])
material_count = len(bpy.data.materials)
armature_count = len([obj for obj in bpy.data.objects if obj.type == 'ARMATURE'])

print("エクスポート前状態:")
print("  - メッシュ数: " + str(mesh_count))
print("  - マテリアル数: " + str(material_count))
print("  - アーマチュア数: " + str(armature_count))

# 全オブジェクト選択
bpy.ops.object.select_all(action='SELECT')

# FBXエクスポート
try:
    bpy.ops.export_scene.fbx(
        filepath="{final_fbx_path}",
        use_selection=True,
        object_types={{'ARMATURE', 'MESH'}},
        add_leaf_bones=True,
        bake_anim=False,
        embed_textures=False
    )
    print("FBXエクスポート完了: {final_fbx_name}")
except Exception as e:
    print("FBXエクスポートエラー: " + str(e))
    exit(1)
""".format(
            model2_blend=model2_blend,
            final_fbx_path=str(final_fbx_path),
            final_fbx_name=final_fbx_path.name
        )
        
        # Blender実行
        cmd = ["blender", "--background", "--python-expr", blender_script]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            raise RuntimeError(f"FBXエクスポート失敗: {result.stderr}")
        
        print(f"  ✅ FBXエクスポート完了: {final_fbx_path.name}")
        return str(final_fbx_path)
    
    def _verify_results(self):
        """結果検証"""
        
        print(f"  🔍 最終結果検証:")
        
        # 生成ファイル確認
        model1_blend = self.temp_dir / f"{self.test_name}_model1.blend"
        model2_blend = self.temp_dir / f"{self.test_name}_model2.blend"
        final_fbx = self.temp_dir / f"{self.test_name}_final.fbx"
        
        files_status = [
            ("モデル1 (Blend)", model1_blend),
            ("モデル2 (Blend)", model2_blend),
            ("最終FBX", final_fbx)
        ]
        
        for file_desc, file_path in files_status:
            if file_path.exists():
                size_mb = file_path.stat().st_size / (1024 * 1024)
                print(f"    ✅ {file_desc}: {file_path.name} ({size_mb:.1f}MB)")
            else:
                print(f"    ❌ {file_desc}: 生成されませんでした")
    
    def _cleanup(self):
        """クリーンアップ（出力ディレクトリは保持）"""
        try:
            print(f"📁 出力結果保持: {self.temp_dir}")
            print(f"   結果確認のため、{self.temp_dir} の内容は保持されます")
        except Exception as e:
            print(f"⚠️ クリーンアップ警告: {e}")


def main():
    """メイン実行"""
    
    # テスト用モデルファイル指定
    test_models = [
        "/app/examples/bird.glb",  # 7.7MB のbird.glbを使用
        # 他のテストモデルがあれば追加
    ]
    
    print("🧪 Step5 Blender正規フロー 簡易テスト開始")
    print("=" * 60)
    print("フロー:")
    print("  1. 3Dモデルインポート→Blenderファイル化（モデル1）")
    print("  2. モデル1別名保存→UV/マテリアル/テクスチャ削除（モデル2）")
    print("  3. モデル2をモデル1のUV/マテリアル/テクスチャで復元")
    print("  4. モデル2をFBX化")
    print("=" * 60)
    
    for model_path in test_models:
        if not Path(model_path).exists():
            print(f"⚠️ テストモデルが見つかりません: {model_path}")
            continue
        
        print(f"\n🎯 テストモデル: {Path(model_path).name}")
        print("-" * 40)
        
        # テスト実行
        test = Step5BlenderFlowTest(model_path)
        success = test.run_complete_test()
        
        if success:
            print(f"✅ {Path(model_path).name}: テスト成功")
        else:
            print(f"❌ {Path(model_path).name}: テスト失敗")
        
        print("-" * 40)
    
    print("\n🏁 Step5 Blender正規フロー テスト完了")


if __name__ == "__main__":
    main()
