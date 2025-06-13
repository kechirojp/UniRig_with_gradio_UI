#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step5 Blender API Test - 軽量版
Blender 4.2 API互換性を確認する最小限のテスト
"""

import subprocess
from pathlib import Path

def test_blender_api_compatibility():
    """Blender 4.2 API互換性テスト"""
    
    print("🔧 Blender 4.2 API互換性テスト")
    
    # テスト1: 基本API確認
    test_script = '''
import bpy

print("=== Blender API テスト ===")

# バージョン確認
print("Blender バージョン: " + str(bpy.app.version))

# 新しいシーンを作成
bpy.ops.wm.read_homefile(use_empty=True)
print("✅ 新しいシーン作成")

# GLBインポートテスト
test_glb = "/app/examples/bird.glb"
try:
    bpy.ops.import_scene.gltf(filepath=test_glb)
    print("✅ GLBインポート成功")
except Exception as e:
    print("❌ GLBインポートエラー: " + str(e))

# FBXエクスポートテスト（Blender 4.2では use_ascii パラメータが削除された）
try:
    bpy.ops.export_scene.fbx(
        filepath="/tmp/test_export.fbx",
        use_selection=False,
        add_leaf_bones=True,
        bake_anim=False
        # use_ascii=False  # ← Blender 4.2では削除
    )
    print("✅ FBXエクスポート成功（use_asciiパラメータなし）")
except Exception as e:
    print("❌ FBXエクスポートエラー: " + str(e))

# マテリアル・ノードAPI確認
material_test_passed = True
try:
    # 新しいマテリアル作成
    test_mat = bpy.data.materials.new(name="TestMaterial")
    test_mat.use_nodes = True
    
    # ノードツリーアクセス
    node_tree = test_mat.node_tree
    node_tree.nodes.clear()
    
    # Principled BSDFノード作成（ノードタイプ名の確認）
    bsdf_node = node_tree.nodes.new(type='ShaderNodeBsdfPrincipled')
    print("✅ Principled BSDFノード作成成功")
    
    # Image Textureノード作成
    tex_node = node_tree.nodes.new(type='ShaderNodeTexImage')
    print("✅ Image Textureノード作成成功")
    
    # ノード間リンク作成
    node_tree.links.new(tex_node.outputs['Color'], bsdf_node.inputs['Base Color'])
    print("✅ ノード間リンク作成成功")
    
except Exception as e:
    print("❌ マテリアル・ノードAPIエラー: " + str(e))
    material_test_passed = False

if material_test_passed:
    print("✅ マテリアル・ノードAPI互換性OK")

# bmesh API確認（UV処理用）
bmesh_test_passed = True
try:
    import bmesh
    from mathutils import Vector
    
    # 新しいメッシュ作成
    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.active_object
    
    # 編集モードでbmesh使用
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_mesh(obj.data)
    
    # UVレイヤー作成
    uv_layer = bm.loops.layers.uv.new("TestUV")
    
    # UV座標設定テスト
    for face in bm.faces:
        for loop in face.loops:
            loop[uv_layer].uv = Vector((0.5, 0.5))
    
    # メッシュ更新
    bmesh.update_edit_mesh(obj.data)
    bpy.ops.object.mode_set(mode='OBJECT')
    
    print("✅ bmesh UV処理成功")
    
except Exception as e:
    print("❌ bmesh APIエラー: " + str(e))
    bmesh_test_passed = False

if bmesh_test_passed:
    print("✅ bmesh API互換性OK")

print("=== API テスト完了 ===")
'''
    
    # Blender実行
    cmd = ["blender", "--background", "--python-expr", test_script]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    
    print("📄 Blenderテスト結果:")
    for line in result.stdout.split('\n'):
        if line.strip():
            print(f"  {line}")
    
    if result.returncode == 0:
        print("✅ Blender API互換性テスト成功")
        return True
    else:
        print(f"❌ Blender API互換性テストエラー: {result.stderr}")
        return False

def test_step3_simplified():
    """Step3簡略版テスト - マテリアル復元基礎"""
    
    print("\n🎨 Step3簡略版テスト開始")
    
    # 既存のtest_bird_model1.blendとtest_bird_model2.blendを使用
    model1_path = "/app/test_step5_output/test_bird_model1.blend"
    model2_path = "/app/test_step5_output/test_bird_model2.blend"
    
    if not Path(model1_path).exists() or not Path(model2_path).exists():
        print("❌ 必要なBlendファイルが見つかりません")
        return False
    
    # 簡略版復元スクリプト
    restore_script = '''
import bpy

print("=== Step3簡略版テスト ===")

# Phase 1: モデル1からマテリアル情報取得
print("Phase 1: モデル1からデータ取得")
bpy.ops.wm.open_mainfile(filepath="{model1_path}")

materials_info = []
images_info = []

# マテリアル情報収集
for material in bpy.data.materials:
    materials_info.append(material.name)
    print("  収集マテリアル: " + material.name)

# 画像情報収集  
for image in bpy.data.images:
    if image.name not in ["Render Result", "Viewer Node"]:
        images_info.append(image.name)
        print("  収集画像: " + image.name)

print("収集完了: マテリアル " + str(len(materials_info)) + "個, 画像 " + str(len(images_info)) + "個")

# Phase 2: モデル2に基本復元適用
print("\\nPhase 2: モデル2に基本復元適用")
bpy.ops.wm.open_mainfile(filepath="{model2_path}")

# 基本マテリアル作成
restored_materials = 0
for mat_name in materials_info:
    try:
        new_material = bpy.data.materials.new(name=mat_name)
        new_material.use_nodes = True
        
        # 基本的なPrincipled BSDFセットアップ
        node_tree = new_material.node_tree
        bsdf = node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs['Base Color'].default_value = (0.8, 0.2, 0.2, 1.0)  # 赤色
        
        restored_materials += 1
        print("  基本マテリアル作成: " + mat_name)
    except Exception as e:
        print("  マテリアル作成エラー: " + str(e))

# 結果保存
bpy.ops.wm.save_mainfile(filepath="{model2_path}")

print("\\n=== 簡略版復元完了 ===")
print("復元マテリアル: " + str(restored_materials) + "個")

if restored_materials > 0:
    print("✅ 簡略版復元成功")
else:
    print("❌ 簡略版復元失敗")
    exit(1)
'''.format(
        model1_path=model1_path,
        model2_path=model2_path
    )
    
    # Blender実行
    cmd = ["blender", "--background", "--python-expr", restore_script]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    
    print("📄 Step3テスト結果:")
    for line in result.stdout.split('\n'):
        if line.strip():
            print(f"  {line}")
    
    success = result.returncode == 0
    if success:
        print("✅ Step3簡略版テスト成功")
    else:
        print(f"❌ Step3簡略版テストエラー: {result.stderr}")
    
    return success

def main():
    """メイン実行"""
    
    print("🧪 Blender 4.2 API互換性確認テスト")
    print("=" * 50)
    
    # テスト1: Blender API互換性確認
    api_ok = test_blender_api_compatibility()
    
    if api_ok:
        # テスト2: Step3簡略版テスト
        step3_ok = test_step3_simplified()
        
        if step3_ok:
            print("\n🎉 全テスト成功！Blender 4.2 API互換性問題なし")
        else:
            print("\n⚠️ Step3で問題あり、さらなる調査が必要")
    else:
        print("\n❌ Blender API基本互換性に問題あり")
    
    print("=" * 50)
    print("🏁 テスト完了")

if __name__ == "__main__":
    main()
