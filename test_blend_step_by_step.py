#!/usr/bin/env python3
"""
Blendベース復元システム - 段階テスト版
まず基本的な.blend変換をテストしてから段階的に機能追加
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Blender Python API
try:
    import bpy
    print("✅ Blenderモジュールインポート成功")
except ImportError:
    print("❌ ERROR: Blenderモジュールがインポートできません")
    sys.exit(1)

def safe_clear_scene():
    """安全なシーンクリア"""
    try:
        # オブジェクトモードに変更
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # 全オブジェクト選択・削除
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        
        print("✅ シーンクリア完了")
        return True
    except Exception as e:
        print(f"❌ シーンクリアエラー: {e}")
        return False

def test_original_to_blend_conversion(original_file: str, output_blend: str) -> bool:
    """ステップ1のテスト: オリジナル → .blend変換"""
    try:
        print(f"\n🔄 オリジナル→.blend変換テスト")
        print(f"入力: {original_file}")
        print(f"出力: {output_blend}")
        
        safe_clear_scene()
        
        # ファイル存在確認
        if not Path(original_file).exists():
            print(f"❌ 入力ファイルが存在しません: {original_file}")
            return False
        
        # GLBファイルをインポート
        file_ext = Path(original_file).suffix.lower()
        if file_ext == '.glb' or file_ext == '.gltf':
            bpy.ops.import_scene.gltf(filepath=original_file)
            print("✅ GLBインポート成功")
        elif file_ext == '.fbx':
            bpy.ops.import_scene.fbx(filepath=original_file)
            print("✅ FBXインポート成功")
        else:
            print(f"❌ サポートされていないファイル形式: {file_ext}")
            return False
        
        # インポート内容を詳細確認
        print("\n📊 インポート内容詳細:")
        
        # メッシュオブジェクト確認
        mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
        print(f"メッシュオブジェクト数: {len(mesh_objects)}")
        
        for obj in mesh_objects:
            mesh = obj.data
            print(f"\n  🔸 メッシュ: {obj.name}")
            print(f"     頂点数: {len(mesh.vertices)}")
            print(f"     面数: {len(mesh.polygons)}")
            print(f"     UVレイヤー数: {len(mesh.uv_layers)}")
            print(f"     マテリアル数: {len(mesh.materials)}")
            
            # UVレイヤー詳細
            for i, uv_layer in enumerate(mesh.uv_layers):
                print(f"       UV[{i}]: {uv_layer.name} (active: {uv_layer.active})")
            
            # マテリアル詳細
            for i, material in enumerate(mesh.materials):
                if material:
                    print(f"       マテリアル[{i}]: {material.name}")
                    if material.use_nodes and material.node_tree:
                        texture_nodes = [node for node in material.node_tree.nodes if node.type == 'TEX_IMAGE']
                        print(f"         テクスチャノード数: {len(texture_nodes)}")
        
        # マテリアル総数確認
        print(f"\n全マテリアル数: {len(bpy.data.materials)}")
        for material in bpy.data.materials:
            print(f"  - {material.name}")
        
        # テクスチャ（イメージ）総数確認
        print(f"\n全イメージ数: {len(bpy.data.images)}")
        for image in bpy.data.images:
            print(f"  - {image.name}: {image.size[0]}x{image.size[1]}")
        
        # .blendファイルとして保存
        output_dir = Path(output_blend).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        bpy.ops.wm.save_as_mainfile(filepath=output_blend)
        print(f"\n✅ .blend保存完了: {output_blend}")
        
        # 保存ファイルサイズ確認
        if os.path.exists(output_blend):
            file_size = os.path.getsize(output_blend)
            print(f"   ファイルサイズ: {file_size:,} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ オリジナル→.blend変換エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_blend_file_loading(blend_file: str) -> bool:
    """保存された.blendファイルの読み込みテスト"""
    try:
        print(f"\n🔄 .blend読み込みテスト")
        print(f"対象: {blend_file}")
        
        if not Path(blend_file).exists():
            print(f"❌ .blendファイルが存在しません: {blend_file}")
            return False
        
        # .blendファイルを開く
        bpy.ops.wm.open_mainfile(filepath=blend_file)
        print("✅ .blendファイル読み込み成功")
        
        # 読み込み内容確認
        print("\n📊 読み込み内容確認:")
        
        mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
        print(f"メッシュオブジェクト数: {len(mesh_objects)}")
        
        for obj in mesh_objects:
            mesh = obj.data
            print(f"  - {obj.name}: 頂点{len(mesh.vertices)}, UV{len(mesh.uv_layers)}, マテリアル{len(mesh.materials)}")
        
        print(f"全マテリアル数: {len(bpy.data.materials)}")
        print(f"全イメージ数: {len(bpy.data.images)}")
        
        return True
        
    except Exception as e:
        print(f"❌ .blend読み込みエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_fbx_export_from_blend(blend_file: str, output_fbx: str) -> bool:
    """
    .blendファイルから最終FBXエクスポートのテスト
    """
    try:
        print(f"\n🔄 .blend → FBXエクスポートテスト")
        print(f"入力: {blend_file}")
        print(f"出力: {output_fbx}")
        
        # .blendファイルを開く
        if not test_blend_file_loading(blend_file):
            return False
        
        # FBXエクスポート
        bpy.ops.export_scene.fbx(
            filepath=output_fbx,
            use_selection=False,
            global_scale=1.0,
            apply_unit_scale=True,
            bake_space_transform=False,
            object_types={'MESH'},  # まずはメッシュのみ
            use_mesh_modifiers=True,
            mesh_smooth_type='OFF',
            use_tspace=True,
            path_mode='AUTO',
            embed_textures=True,
            axis_forward='-Y',
            axis_up='Z'
        )
        
        # 出力確認
        if os.path.exists(output_fbx):
            file_size = os.path.getsize(output_fbx)
            print(f"✅ FBXエクスポート成功: {output_fbx}")
            print(f"   ファイルサイズ: {file_size:,} bytes")
            return True
        else:
            print(f"❌ FBXファイルが生成されませんでした: {output_fbx}")
            return False
        
    except Exception as e:
        print(f"❌ FBXエクスポートエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """段階的テスト実行"""
    print("🎯 Blendベースシステム - 段階テスト")
    
    # テスト設定
    test_file = "/app/examples/bird.glb"
    output_dir = "/app/pipeline_work/blend_test"
    
    if not Path(test_file).exists():
        print(f"❌ テストファイルが存在しません: {test_file}")
        return
    
    # 出力パス
    blend_file = f"{output_dir}/bird_original.blend"
    fbx_file = f"{output_dir}/bird_from_blend.fbx"
    
    # 段階1: オリジナル → .blend変換テスト
    print("\n" + "="*60)
    print("🧪 段階1: オリジナル → .blend変換テスト")
    print("="*60)
    
    if test_original_to_blend_conversion(test_file, blend_file):
        print("✅ 段階1成功")
    else:
        print("❌ 段階1失敗")
        return
    
    # 段階2: .blend読み込みテスト
    print("\n" + "="*60)
    print("🧪 段階2: .blend読み込みテスト")
    print("="*60)
    
    if test_blend_file_loading(blend_file):
        print("✅ 段階2成功")
    else:
        print("❌ 段階2失敗")
        return
    
    # 段階3: .blend → FBXエクスポートテスト
    print("\n" + "="*60)
    print("🧪 段階3: .blend → FBXエクスポートテスト")
    print("="*60)
    
    if test_fbx_export_from_blend(blend_file, fbx_file):
        print("✅ 段階3成功")
    else:
        print("❌ 段階3失敗")
        return
    
    print("\n" + "="*60)
    print("🎉 全段階テスト成功！")
    print("="*60)
    print(f"生成ファイル:")
    print(f"  .blend: {blend_file}")
    print(f"  .fbx: {fbx_file}")

if __name__ == "__main__":
    main()
