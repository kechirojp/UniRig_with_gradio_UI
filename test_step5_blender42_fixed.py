#!/usr/bin/env python3
"""
Step5 Blender 4.2互換性修正版テストスクリプト
- Blender 4.2の正式APIに対応
- ノードタイプとbmesh APIの修正
- f-string内エスケープ問題の解決
"""

import subprocess
import sys
import json
from pathlib import Path
import tempfile
import os

def test_step5_blender42_flow():
    """Step5の正規フロー（Blender 4.2対応版）"""
    print("=== Step5 Blender 4.2正規フローテスト開始 ===")
    
    # テスト用ファイルパス設定
    test_input = "/app/examples/bird.glb"  # 7.7MB GLBファイル
    test_output_dir = Path("/app/test_step5_blender42_output")
    test_output_dir.mkdir(exist_ok=True)
    
    if not Path(test_input).exists():
        print(f"エラー: テスト用ファイルが見つかりません: {test_input}")
        return False
    
    print(f"テスト入力: {test_input}")
    print(f"出力ディレクトリ: {test_output_dir}")
    
    # Blender 4.2対応のスクリプトを作成
    blender_script_content = """
import bpy
import bmesh
import json
import os
from mathutils import Vector

# 出力パス設定
OUTPUT_DIR = "{output_dir}"
MODEL1_BLEND = os.path.join(OUTPUT_DIR, "test_bird_model1.blend")
MODEL2_BLEND = os.path.join(OUTPUT_DIR, "test_bird_model2.blend")
FINAL_FBX = os.path.join(OUTPUT_DIR, "test_bird_final.fbx")
SOURCE_DATA_JSON = os.path.join(OUTPUT_DIR, "source_data.json")

print("=== Blender 4.2 Step5正規フロー開始 ===")

# ステップ1: 3Dモデルインポート→Blenderファイル化（モデル1）
print("ステップ1: 3Dモデルインポート開始...")
bpy.ops.wm.read_factory_settings(use_empty=True)

try:
    bpy.ops.import_scene.gltf(filepath="{input_file}")
    print(f"  GLTFインポート成功: {input_file}")
except Exception as e:
    print(f"  GLTFインポートエラー: {{e}}")
    exit(1)

# モデル1として保存
bpy.ops.wm.save_as_mainfile(filepath=MODEL1_BLEND)
print(f"  モデル1保存完了: {{MODEL1_BLEND}}")

# ステップ2: ソースデータ収集と保存
print("ステップ2: ソースデータ収集開始...")
source_data = {{"materials": {{}}, "images": {{}}, "uv_data": {{}}, "material_assignments": {{}}}}

# マテリアル情報収集（Blender 4.2対応）
for material in bpy.data.materials:
    mat_data = {{"name": material.name, "use_nodes": material.use_nodes, 
                "diffuse_color": list(material.diffuse_color), "nodes": {{}}, "links": []}}
    
    if material.use_nodes:
        for node in material.node_tree.nodes:
            # Blender 4.2対応ノードタイプ処理
            node_data = {{"type": node.bl_idname, "location": list(node.location), "properties": {{}}}}
            
            # Image Textureノードの場合
            if node.bl_idname == 'ShaderNodeTexImage':
                if node.image:
                    node_data['image_name'] = node.image.name
            
            # Principled BSDFノードの場合（Blender 4.2対応）
            elif node.bl_idname == 'ShaderNodeBsdfPrincipled':
                try:
                    # Blender 4.2でのソケット名を確認して設定
                    if 'Base Color' in node.inputs:
                        node_data['properties']['base_color'] = list(node.inputs['Base Color'].default_value)
                    if 'Metallic' in node.inputs:
                        node_data['properties']['metallic'] = node.inputs['Metallic'].default_value
                    if 'Roughness' in node.inputs:
                        node_data['properties']['roughness'] = node.inputs['Roughness'].default_value
                except Exception as e:
                    print(f"    Principled BSDFプロパティ収集エラー: {{e}}")
            
            mat_data['nodes'][node.name] = node_data
        
        # リンク情報を収集
        for link in material.node_tree.links:
            mat_data['links'].append({{"from_node": link.from_node.name, "from_socket": link.from_socket.name,
                                     "to_node": link.to_node.name, "to_socket": link.to_socket.name}})
    
    source_data['materials'][material.name] = mat_data
    print(f"  収集マテリアル: {{material.name}} (ノード数: {{len(mat_data['nodes'])}})")

# 画像情報収集
for image in bpy.data.images:
    img_data = {{"name": image.name, "filepath": image.filepath, "size": list(image.size),
                "colorspace": image.colorspace_settings.name if hasattr(image, 'colorspace_settings') else 'sRGB'}}
    source_data['images'][image.name] = img_data
    print(f"  収集画像: {{image.name}} ({{image.size[0]}}x{{image.size[1]}})")

# UV情報とマテリアル割り当て収集
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        # UV座標データを実際に収集
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
        
        print(f"  収集UV ({{obj.name}}): {{list(uv_layers_data.keys())}} (座標数: {{len(uv_coords) if uv_coords else 0}})")

# ソースデータをJSONファイルに保存
with open(SOURCE_DATA_JSON, 'w') as f:
    json.dump(source_data, f, indent=2)
print(f"ソースデータ保存完了: {{SOURCE_DATA_JSON}}")

# ステップ3: モデル1別名保存→UV/マテリアル/テクスチャ削除（モデル2）
print("ステップ3: UV/マテリアル/テクスチャ削除開始...")

# 全マテリアルを削除
for material in list(bpy.data.materials):
    bpy.data.materials.remove(material)
print(f"  削除マテリアル数: {{len(source_data['materials'])}}")

# 全画像を削除
for image in list(bpy.data.images):
    bpy.data.images.remove(image)
print(f"  削除画像数: {{len(source_data['images'])}}")

# UVマップを削除
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        for uv_layer in list(obj.data.uv_layers):
            obj.data.uv_layers.remove(uv_layer)
        print(f"  削除UV ({{obj.name}}): {{len(source_data['uv_data'].get(obj.name, {{}}))}}")

# モデル2として保存
bpy.ops.wm.save_as_mainfile(filepath=MODEL2_BLEND)
print(f"ストリップ版モデル2保存完了: {{MODEL2_BLEND}}")

# ステップ4: モデル2をモデル1のUV/マテリアル/テクスチャで復元
print("ステップ4: UV/マテリアル/テクスチャ復元開始...")
restored_count = {{"materials": 0, "images": 0, "uvs": 0}}

# 画像復元
print("画像復元開始...")
for img_name, img_data in source_data['images'].items():
    try:
        if img_data['filepath'] and os.path.exists(img_data['filepath']):
            new_image = bpy.data.images.load(img_data['filepath'])
            new_image.name = img_name
            print(f"  復元画像: {{img_name}} ({{img_data['filepath']}})")
        else:
            # ファイルが見つからない場合は空の画像を作成
            new_image = bpy.data.images.new(name=img_name, width=img_data['size'][0] or 512, 
                                          height=img_data['size'][1] or 512)
            print(f"  作成画像: {{img_name}} (元ファイル不明)")
        
        restored_count['images'] += 1
    except Exception as e:
        print(f"  画像復元エラー ({{img_name}}): {{e}}")

# マテリアル復元（Blender 4.2対応）
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
            
            # ノードを再作成（Blender 4.2対応）
            created_nodes = {{}}
            for node_name, node_data in mat_data['nodes'].items():
                try:
                    new_node = node_tree.nodes.new(type=node_data['type'])
                    new_node.name = node_name
                    new_node.location = node_data['location']
                    
                    # Image Textureノードの場合、画像を割り当て
                    if node_data['type'] == 'ShaderNodeTexImage' and 'image_name' in node_data:
                        if node_data['image_name'] in bpy.data.images:
                            new_node.image = bpy.data.images[node_data['image_name']]
                    
                    # Principled BSDFノードのプロパティ復元（Blender 4.2対応）
                    if node_data['type'] == 'ShaderNodeBsdfPrincipled' and 'properties' in node_data:
                        props = node_data['properties']
                        try:
                            if 'base_color' in props and 'Base Color' in new_node.inputs:
                                new_node.inputs['Base Color'].default_value = props['base_color']
                            if 'metallic' in props and 'Metallic' in new_node.inputs:
                                new_node.inputs['Metallic'].default_value = props['metallic']
                            if 'roughness' in props and 'Roughness' in new_node.inputs:
                                new_node.inputs['Roughness'].default_value = props['roughness']
                        except Exception as e:
                            print(f"    プロパティ設定エラー: {{e}}")
                    
                    created_nodes[node_name] = new_node
                except Exception as e:
                    print(f"    ノード作成エラー ({{node_name}}): {{e}}")
            
            # ノード間のリンクを復元
            for link_data in mat_data['links']:
                try:
                    from_node = created_nodes[link_data['from_node']]
                    to_node = created_nodes[link_data['to_node']]
                    node_tree.links.new(from_node.outputs[link_data['from_socket']], 
                                      to_node.inputs[link_data['to_socket']])
                except Exception as e:
                    print(f"    リンク作成エラー: {{e}}")
        
        restored_count['materials'] += 1
        print(f"  復元マテリアル: {{mat_name}} (ノード数: {{len(mat_data['nodes'])}})")
    except Exception as e:
        print(f"  マテリアル復元エラー ({{mat_name}}): {{e}}")

# UV座標復元（Blender 4.2対応）
print("UV座標復元開始...")
for obj in bpy.data.objects:
    if obj.type == 'MESH' and obj.name in source_data['uv_data']:
        try:
            # 編集モードに入る
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            
            # bmeshを使用してUV座標を復元（Blender 4.2対応）
            bm = bmesh.from_mesh(obj.data)  # Blender 4.2では引数なし
            
            for uv_layer_name, uv_coords in source_data['uv_data'][obj.name].items():
                # UVレイヤーを作成または取得
                if uv_layer_name not in obj.data.uv_layers:
                    obj.data.uv_layers.new(name=uv_layer_name)
                
                uv_layer = bm.loops.layers.uv.get(uv_layer_name)
                if not uv_layer:
                    uv_layer = bm.loops.layers.uv.new(uv_layer_name)
                
                # UV座標を設定
                coord_index = 0
                for face in bm.faces:
                    for loop in face.loops:
                        if coord_index < len(uv_coords):
                            loop[uv_layer].uv = Vector(uv_coords[coord_index])
                            coord_index += 1
            
            # メッシュを更新（Blender 4.2対応）
            bmesh.update_edit_mesh(obj.data)
            bpy.ops.object.mode_set(mode='OBJECT')
            
            restored_count['uvs'] += len(source_data['uv_data'][obj.name])
            print(f"  復元UV ({{obj.name}}): {{list(source_data['uv_data'][obj.name].keys())}}")
        except Exception as e:
            print(f"  UV復元エラー ({{obj.name}}): {{e}}")

# マテリアル割り当て復元
print("マテリアル割り当て復元開始...")
for obj in bpy.data.objects:
    if obj.type == 'MESH' and obj.name in source_data['material_assignments']:
        try:
            # 既存のマテリアルスロットをクリア
            obj.data.materials.clear()
            
            # マテリアルを割り当て
            for mat_name in source_data['material_assignments'][obj.name]:
                if mat_name in bpy.data.materials:
                    obj.data.materials.append(bpy.data.materials[mat_name])
            
            print(f"  復元マテリアル割り当て ({{obj.name}}): {{source_data['material_assignments'][obj.name]}}")
        except Exception as e:
            print(f"  マテリアル割り当てエラー ({{obj.name}}): {{e}}")

print(f"復元完了 - マテリアル:{{restored_count['materials']}}, 画像:{{restored_count['images']}}, UV:{{restored_count['uvs']}}")

# ステップ5: モデル2をFBX化（バイナリ出力）
print("ステップ5: FBX出力開始...")
try:
    # Blender 4.2対応FBXエクスポート（use_asciiパラメータ削除）
    bpy.ops.export_scene.fbx(
        filepath=FINAL_FBX,
        use_selection=False,
        global_scale=1.0,
        apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_NONE',
        bake_space_transform=False,
        object_types={{'ARMATURE', 'MESH'}},
        use_mesh_modifiers=True,
        mesh_smooth_type='OFF',
        use_subsurf=False,
        use_mesh_edges=False,
        use_tspace=False,
        use_triangles=False,
        use_custom_props=False,
        add_leaf_bones=True,
        primary_bone_axis='Y',
        secondary_bone_axis='X',
        use_armature_deform_only=False,
        bake_anim=False,
        path_mode='AUTO',
        embed_textures=False,
        batch_mode='OFF',
        use_metadata=True,
        axis_forward='-Y',
        axis_up='Z'
        # use_ascii=False  # Blender 4.2で削除されたパラメータ
    )
    print(f"FBX出力成功: {{FINAL_FBX}}")
except Exception as e:
    print(f"FBX出力エラー: {{e}}")

print("=== Blender 4.2 Step5正規フロー完了 ===")
""".format(
        output_dir=str(test_output_dir).replace('\\', '/'),
        input_file=test_input.replace('\\', '/')
    )
    
    # 一時スクリプトファイル作成
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp_script:
        tmp_script.write(blender_script_content)
        script_path = tmp_script.name
    
    try:
        # Blenderをバックグラウンドで実行
        print("Blender 4.2実行開始...")
        cmd = [
            "blender", "--background", "--python", script_path
        ]
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=180,  # 3分タイムアウト
            cwd="/app"
        )
        
        print(f"Blender実行結果 - 終了コード: {result.returncode}")
        if result.stdout:
            print("=== Blender標準出力 ===")
            print(result.stdout)
        if result.stderr:
            print("=== Blenderエラー出力 ===")
            print(result.stderr)
        
        # 結果ファイルを確認
        success = True
        expected_files = [
            test_output_dir / "test_bird_model1.blend",
            test_output_dir / "test_bird_model2.blend", 
            test_output_dir / "test_bird_final.fbx",
            test_output_dir / "source_data.json"
        ]
        
        print("\n=== 生成ファイル確認 ===")
        for file_path in expected_files:
            if file_path.exists():
                size_mb = file_path.stat().st_size / (1024 * 1024)
                print(f"✓ {file_path.name}: {size_mb:.2f}MB")
            else:
                print(f"✗ {file_path.name}: ファイルなし")
                success = False
        
        if success:
            print("\n✅ Step5 Blender 4.2正規フロー成功!")
        else:
            print("\n❌ Step5 Blender 4.2正規フロー失敗 - 一部ファイルが生成されませんでした")
        
        return success
        
    except subprocess.TimeoutExpired:
        print("❌ Blender実行がタイムアウトしました（3分）")
        return False
    except Exception as e:
        print(f"❌ Blender実行エラー: {e}")
        return False
    finally:
        # 一時ファイル削除
        if os.path.exists(script_path):
            os.unlink(script_path)

if __name__ == "__main__":
    try:
        success = test_step5_blender42_flow()
        exit_code = 0 if success else 1
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️ ユーザーによって中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
        sys.exit(1)
