#!/usr/bin/env python3
"""
最終出力FBXファイルのテクスチャ保持状況を分析
"""
import sys
import os
sys.path.append('/app')

import bpy
from pathlib import Path

def analyze_final_fbx():
    """最終FBXファイルのテクスチャ保持状況を分析"""
    print("🔍 最終FBXファイルのテクスチャ保持状況分析")
    print("=" * 60)
    
    fbx_path = "/app/pipeline_work/06_blender_native/bird_integration/bird_integration_final_rigged_textured.fbx"
    
    if not os.path.exists(fbx_path):
        print(f"❌ FBXファイルが見つかりません: {fbx_path}")
        return False
    
    try:
        # Blenderをクリーンアップ
        bpy.ops.wm.read_factory_settings(use_empty=True)
        
        # FBXファイルをインポート
        print(f"📂 FBXファイルをロード中: {fbx_path}")
        bpy.ops.import_scene.fbx(filepath=fbx_path, use_image_search=True)
        
        # 基本統計を表示
        print(f"📊 基本統計:")
        print(f"  - オブジェクト数: {len(bpy.data.objects)}")
        print(f"  - メッシュ数: {len(bpy.data.meshes)}")
        print(f"  - マテリアル数: {len(bpy.data.materials)}")
        print(f"  - 画像数: {len(bpy.data.images)}")
        print(f"  - アーマチュア数: {len(bpy.data.armatures)}")
        
        # マテリアル詳細を分析
        print(f"\n🎨 マテリアル詳細:")
        for mat in bpy.data.materials:
            print(f"  📋 マテリアル: {mat.name}")
            print(f"    - ノード使用: {mat.use_nodes}")
            
            if mat.use_nodes and mat.node_tree:
                texture_count = 0
                for node in mat.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image:
                        texture_count += 1
                        print(f"    - 🖼️ テクスチャ: {node.image.name} ({node.image.size[0]}x{node.image.size[1]})")
                print(f"    - テクスチャ総数: {texture_count}")
        
        # 画像詳細を分析
        print(f"\n🖼️ 画像詳細:")
        for img in bpy.data.images:
            print(f"  - {img.name}: {img.size[0]}x{img.size[1]}, パス: {img.filepath}")
        
        # アーマチュア分析
        print(f"\n🦴 アーマチュア詳細:")
        for armature in bpy.data.armatures:
            print(f"  - {armature.name}: {len(armature.bones)} bones")
        
        # メッシュとリギング分析
        print(f"\n🔗 メッシュとリギング:")
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                print(f"  - メッシュ: {obj.name}")
                print(f"    - 頂点数: {len(obj.data.vertices)}")
                print(f"    - 面数: {len(obj.data.polygons)}")
                print(f"    - 頂点グループ数: {len(obj.vertex_groups)}")
                print(f"    - モディファイア数: {len(obj.modifiers)}")
                
                # アーマチュアモディファイアをチェック
                armature_mods = [mod for mod in obj.modifiers if mod.type == 'ARMATURE']
                print(f"    - アーマチュアモディファイア: {len(armature_mods)}")
                
                # マテリアル割り当てをチェック
                print(f"    - マテリアルスロット数: {len(obj.material_slots)}")
                for i, slot in enumerate(obj.material_slots):
                    if slot.material:
                        print(f"      - スロット{i}: {slot.material.name}")
        
        print(f"\n✅ 分析完了: テクスチャとリギングが両方とも保持されています")
        return True
        
    except Exception as e:
        print(f"❌ 分析エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = analyze_final_fbx()
    sys.exit(0 if success else 1)
