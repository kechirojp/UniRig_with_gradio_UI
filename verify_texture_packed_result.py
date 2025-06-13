#!/usr/bin/env python3
"""
Step5テクスチャパッキング結果検証スクリプト
最終FBXファイルのテクスチャ・UV・マテリアル状況を詳細確認
"""

import subprocess
import sys
from pathlib import Path

def verify_texture_packed_fbx(fbx_path: str):
    """テクスチャパッキング結果の詳細検証"""
    
    blender_script = f'''
import bpy

def check_texture_status():
    """テクスチャの詳細状況を確認・レポート"""
    print("=== テクスチャ状況レポート ===")
    
    total_images = 0
    packed_images = 0
    external_images = 0
    missing_images = 0
    
    for img in bpy.data.images:
        if img.type != 'IMAGE':
            continue
            
        total_images += 1
        print("📄 " + img.name)
        
        if img.packed_file:
            packed_images += 1
            print("   状態: 🟢 埋め込み済み")
            print("   サイズ: " + str(len(img.packed_file.data)) + " bytes")
        elif img.filepath:
            external_images += 1
            import os
            if os.path.exists(bpy.path.abspath(img.filepath)):
                print("   状態: 🟡 外部ファイル（存在）")
                print("   パス: " + img.filepath)
            else:
                missing_images += 1
                print("   状態: 🔴 外部ファイル（見つからない）")
                print("   パス: " + img.filepath)
        else:
            print("   状態: ⚪ 生成テクスチャ")
        
        print("   解像度: " + str(img.size[0]) + " x " + str(img.size[1]))
        print("   カラースペース: " + img.colorspace_settings.name)
    
    print("=== サマリー ===")
    print("総テクスチャ数: " + str(total_images))
    print("埋め込み済み: " + str(packed_images))
    print("外部ファイル: " + str(external_images))
    print("見つからない: " + str(missing_images))
    
    return {{
        'total': total_images,
        'packed': packed_images,
        'external': external_images,
        'missing': missing_images
    }}

def verify_uv_and_materials():
    """UV・マテリアルの検証"""
    print("")
    print("=== UV・マテリアル検証 ===")
    
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH':
            continue
            
        print("🎯 メッシュオブジェクト: " + obj.name)
        
        # UVマップの確認
        if obj.data.uv_layers:
            print("✅ UVマップ数: " + str(len(obj.data.uv_layers)))
            for i, uv in enumerate(obj.data.uv_layers):
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
        if obj.data.materials:
            print("✅ マテリアル数: " + str(len(obj.data.materials)))
            for i, mat in enumerate(obj.data.materials):
                if mat:
                    print("  マテリアル " + str(i+1) + ": " + mat.name)
                    if mat.use_nodes and mat.node_tree:
                        texture_count = sum(1 for node in mat.node_tree.nodes if node.type == 'TEX_IMAGE')
                        print("    テクスチャノード数: " + str(texture_count))
                        
                        # テクスチャノードの詳細
                        for node in mat.node_tree.nodes:
                            if node.type == 'TEX_IMAGE' and node.image:
                                print("    📸 テクスチャ: " + node.image.name)
                                if node.image.packed_file:
                                    print("      状態: 🟢 埋め込み済み")
                                else:
                                    print("      状態: 🟡 外部参照")
                else:
                    print("  マテリアル " + str(i+1) + ": None")
        else:
            print("❌ 警告: マテリアルが見つかりません")
        
        # メッシュ統計情報
        print("頂点数: " + str(len(obj.data.vertices)))
        print("面数: " + str(len(obj.data.polygons)))
        print("ループ数: " + str(len(obj.data.loops)))
        print("")

# === メイン処理 ===
print("🔍 Step5テクスチャパッキング結果検証開始")

# シーンクリア
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# テクスチャパッキング版FBXをインポート
print("📦 テクスチャパッキング版FBXインポート: {fbx_path}")
bpy.ops.import_scene.fbx(filepath="{fbx_path}")

# 詳細検証
texture_status = check_texture_status()
verify_uv_and_materials()

# 総合評価
print("=== 総合評価 ===")
if texture_status['packed'] > 0:
    print("🎉 テクスチャ埋め込み成功!")
    print("埋め込みテクスチャ数: " + str(texture_status['packed']))
else:
    print("⚠️  テクスチャ埋め込みが検出されませんでした")

if texture_status['missing'] > 0:
    print("⚠️  見つからないテクスチャ: " + str(texture_status['missing']))

print("🔍 Step5テクスチャパッキング結果検証完了")
'''
    
    cmd = ["blender", "--background", "--python-expr", blender_script]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    
    print("=== 検証結果 ===")
    print("STDOUT:", result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    return result.returncode == 0

def main():
    """検証実行"""
    fbx_path = "/app/step5_texture_packed/bird_texture_packed.fbx"
    
    print(f"🔍 テクスチャパッキング結果検証")
    print(f"対象FBX: {fbx_path}")
    
    if not Path(fbx_path).exists():
        print(f"❌ FBXファイルが見つかりません: {fbx_path}")
        return False
    
    # ファイルサイズ確認
    size_mb = Path(fbx_path).stat().st_size / (1024 * 1024)
    print(f"FBXファイルサイズ: {size_mb:.2f} MB")
    
    # 詳細検証実行
    success = verify_texture_packed_fbx(fbx_path)
    
    if success:
        print("✅ 検証完了")
    else:
        print("❌ 検証中にエラーが発生しました")
    
    return success

if __name__ == "__main__":
    main()
