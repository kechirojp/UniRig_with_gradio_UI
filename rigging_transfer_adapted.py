"""
Step5用リギング移植スクリプト（simple_rigging_transfer_v2.py基盤）
===
目的:
- ソースファイル: pipeline_work/bird/04_merge/bird_merged.fbx（リギング済み）
- ターゲットファイル: pipeline_work/bird/00_asset_preservation/bird.glb（UV・マテリアル・テクスチャ保持）
- 出力: ターゲットファイル形式でリギング統合済みファイル

実行方法:
    blender --background --python rigging_transfer_adapted.py -- source_fbx target_file output_file
"""

import bpy
import sys
import bmesh
from pathlib import Path
from mathutils import Vector


def main():
    """メイン実行関数"""
    print("=== Step5 リギング移植処理開始 ===")
    
    # コマンドライン引数解析
    try:
        argv = sys.argv
        if "--" in argv:
            argv = argv[argv.index("--") + 1:]
        
        if len(argv) < 3:
            print("❌ 引数不足: source_fbx target_file output_file")
            sys.exit(1)
        
        source_fbx = Path(argv[0])      # リギング済みFBX
        target_file = Path(argv[1])     # UV・マテリアル・テクスチャ保持ファイル
        output_file = Path(argv[2])     # 出力ファイル
        
        print(f"ソースFBX: {source_fbx}")
        print(f"ターゲットファイル: {target_file}")
        print(f"出力ファイル: {output_file}")
        
        # リギング移植実行
        success = transfer_rigging_dynamic(source_fbx, target_file, output_file)
        
        if success:
            print("\n🎉 Step5 リギング移植完了！")
            print("SUCCESS")  # Step5が検出するキーワード
        else:
            print("\n❌ Step5 リギング移植失敗")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def transfer_rigging_dynamic(source_fbx: Path, target_file: Path, output_file: Path) -> bool:
    """
    動的リギング移植処理（simple_rigging_transfer_v2.py基盤）
    
    Args:
        source_fbx: Step4出力のリギング済みFBX
        target_file: 元アセット（UV・マテリアル・テクスチャ保持）
        output_file: 最終出力ファイル
    """
    print("=== 動的リギング移植開始 ===")
    
    try:
        # シーンクリア
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        
        # 1. ソースFBX読み込み（リギング情報源）
        print(f"\n--- Step 1: ソースFBX読み込み ---")
        print(f"読み込み中: {source_fbx}")
        
        if not source_fbx.exists():
            print(f"❌ ソースFBXが存在しません: {source_fbx}")
            return False
        
        bpy.ops.import_scene.fbx(filepath=str(source_fbx))
        
        # ソースオブジェクト特定
        source_mesh = None
        source_armature = None
        
        for obj in bpy.context.scene.objects:
            if obj.type == 'MESH' and obj.vertex_groups:
                source_mesh = obj
                print(f"ソースメッシュ: {obj.name}")
            elif obj.type == 'ARMATURE':
                source_armature = obj
                print(f"ソースアーマチュア: {obj.name}")
        
        if not source_mesh or not source_armature:
            print(f"❌ ソースオブジェクト不足: mesh={source_mesh}, armature={source_armature}")
            return False
        
        # 2. ターゲットファイル読み込み（アセット情報源）
        print(f"\n--- Step 2: ターゲットファイル読み込み ---")
        print(f"読み込み中: {target_file}")
        
        if not target_file.exists():
            print(f"❌ ターゲットファイルが存在しません: {target_file}")
            return False
        
        # ファイル形式に応じた読み込み
        target_ext = target_file.suffix.lower()
        if target_ext == '.fbx':
            bpy.ops.import_scene.fbx(filepath=str(target_file))
        elif target_ext == '.glb' or target_ext == '.gltf':
            bpy.ops.import_scene.gltf(filepath=str(target_file))
        elif target_ext == '.obj':
            bpy.ops.import_scene.obj(filepath=str(target_file))
        else:
            print(f"❌ 未対応ファイル形式: {target_ext}")
            return False
        
        # ターゲットメッシュ特定（新しく追加されたオブジェクト）
        target_mesh = None
        for obj in bpy.context.scene.objects:
            if obj.type == 'MESH' and obj != source_mesh:
                target_mesh = obj
                print(f"ターゲットメッシュ: {obj.name}")
                break
        
        if not target_mesh:
            print("❌ ターゲットメッシュが見つかりません")
            return False
        
        # 3. リギング情報移植（相対位置関係保持）
        print(f"\n--- Step 3: リギング情報移植 ---")
        
        # 新規アーマチュア作成
        armature_data = source_armature.data.copy()
        armature_data.name = f"{target_mesh.name}_Armature_Data"
        
        target_armature = bpy.data.objects.new(f"{target_mesh.name}_Armature", armature_data)
        bpy.context.collection.objects.link(target_armature)
        
        # 相対位置関係保持
        source_relative_pos = source_armature.location - source_mesh.location
        target_armature.location = target_mesh.location + source_relative_pos
        target_armature.rotation_euler = source_armature.rotation_euler.copy()
        target_armature.scale = source_armature.scale.copy()
        
        print(f"新規アーマチュア作成: {target_armature.name}")
        print(f"相対オフセット: {source_relative_pos}")
        
        # 4. 頂点グループ転送
        print(f"\n--- Step 4: 頂点グループ転送 ---")
        
        # 既存頂点グループクリア
        target_mesh.vertex_groups.clear()
        
        # 完全同一メッシュ前提での直接転送
        transferred_groups = 0
        total_weights = 0
        
        # メッシュデータが同一かチェック
        if len(source_mesh.data.vertices) != len(target_mesh.data.vertices):
            print(f"⚠️ 頂点数が異なります: source={len(source_mesh.data.vertices)}, target={len(target_mesh.data.vertices)}")
            print("最近傍マッチング方式を適用します")
            
            # 最近傍マッチング方式
            success = transfer_weights_by_proximity(source_mesh, target_mesh)
            if not success:
                print("❌ 最近傍マッチング失敗")
                return False
        else:
            # 完全同一メッシュ方式
            for source_vg in source_mesh.vertex_groups:
                target_vg = target_mesh.vertex_groups.new(name=source_vg.name)
                
                for vert_idx in range(len(source_mesh.data.vertices)):
                    try:
                        weight = source_vg.weight(vert_idx)
                        if weight > 0.0:
                            target_vg.add([vert_idx], weight, 'REPLACE')
                            total_weights += 1
                    except RuntimeError:
                        pass
                
                transferred_groups += 1
        
        print(f"頂点グループ転送完了: {transferred_groups}個のグループ、{total_weights}個のウェイト")
        
        # 5. アーマチュアモディファイア設定
        print(f"\n--- Step 5: アーマチュアモディファイア設定 ---")
        
        # 既存モディファイア削除
        for mod in list(target_mesh.modifiers):
            if mod.type == 'ARMATURE':
                target_mesh.modifiers.remove(mod)
        
        # 新規モディファイア追加
        armature_mod = target_mesh.modifiers.new(name="Armature", type='ARMATURE')
        armature_mod.object = target_armature
        armature_mod.use_vertex_groups = True
        armature_mod.use_bone_envelopes = False
        
        print(f"アーマチュアモディファイア設定完了")
        
        # 6. 親子関係設定
        print(f"\n--- Step 6: 親子関係設定 ---")
        
        # 既存親子関係解除
        if target_mesh.parent:
            target_mesh.parent = None
        if target_armature.parent:
            target_armature.parent = None
        
        # 親子関係設定: target_mesh（親）→ target_armature（子）
        target_armature.parent = target_mesh
        target_armature.parent_type = 'OBJECT'
        target_armature.parent_bone = ""
        target_armature.matrix_parent_inverse.identity()
        
        print(f"親子関係設定完了: {target_mesh.name} → {target_armature.name}")
        
        # 7. 不要オブジェクト削除
        print(f"\n--- Step 7: クリーンアップ ---")
        
        # ソースオブジェクト削除
        objects_to_delete = [source_mesh, source_armature]
        for obj in objects_to_delete:
            if obj and obj.name in bpy.data.objects:
                bpy.data.objects.remove(obj, do_unlink=True)
        
        # 最終選択状態設定
        bpy.ops.object.select_all(action='DESELECT')
        target_mesh.select_set(True)
        target_armature.select_set(True)
        bpy.context.view_layer.objects.active = target_mesh
        
        # 8. 出力ファイル書き出し
        print(f"\n--- Step 8: 出力ファイル書き出し ---")
        
        output_ext = output_file.suffix.lower()
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        if output_ext == '.fbx':
            bpy.ops.export_scene.fbx(
                filepath=str(output_file),
                use_selection=True,
                add_leaf_bones=True,
                bake_anim=False,
                embed_textures=True,
                path_mode='COPY'
            )
        elif output_ext == '.glb':
            bpy.ops.export_scene.gltf(
                filepath=str(output_file),
                use_selection=True,
                export_format='GLB',
                export_materials='EXPORT'
            )
        elif output_ext == '.gltf':
            bpy.ops.export_scene.gltf(
                filepath=str(output_file),
                use_selection=True,
                export_format='GLTF_SEPARATE',
                export_materials='EXPORT'
            )
        else:
            print(f"❌ 未対応出力形式: {output_ext}")
            return False
        
        if not output_file.exists():
            print(f"❌ 出力ファイル作成失敗: {output_file}")
            return False
        
        file_size = output_file.stat().st_size
        print(f"出力ファイル作成成功: {output_file}")
        print(f"ファイルサイズ: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
        
        return True
        
    except Exception as e:
        print(f"❌ リギング移植エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def transfer_weights_by_proximity(source_mesh, target_mesh) -> bool:
    """最近傍マッチングによるウェイト転送"""
    try:
        from scipy.spatial import cKDTree
        import numpy as np
        
        # ソース頂点座標取得
        source_verts = [v.co for v in source_mesh.data.vertices]
        target_verts = [v.co for v in target_mesh.data.vertices]
        
        # KDTree構築
        tree = cKDTree(source_verts)
        
        # 頂点グループ作成
        for source_vg in source_mesh.vertex_groups:
            target_vg = target_mesh.vertex_groups.new(name=source_vg.name)
            
            for target_idx, target_vert in enumerate(target_verts):
                # 最近傍ソース頂点検索
                distance, source_idx = tree.query(target_vert)
                
                try:
                    weight = source_vg.weight(source_idx)
                    if weight > 0.0:
                        target_vg.add([target_idx], weight, 'REPLACE')
                except RuntimeError:
                    pass
        
        return True
        
    except ImportError:
        print("❌ scipy未インストール、基本マッチング方式を使用")
        # 基本的な距離ベースマッチング
        return transfer_weights_basic_proximity(source_mesh, target_mesh)
    except Exception as e:
        print(f"❌ 最近傍マッチングエラー: {e}")
        return False


def transfer_weights_basic_proximity(source_mesh, target_mesh) -> bool:
    """基本的な距離ベースウェイト転送"""
    try:
        source_verts = [(i, v.co) for i, v in enumerate(source_mesh.data.vertices)]
        target_verts = [v.co for v in target_mesh.data.vertices]
        
        for source_vg in source_mesh.vertex_groups:
            target_vg = target_mesh.vertex_groups.new(name=source_vg.name)
            
            for target_idx, target_co in enumerate(target_verts):
                # 最短距離ソース頂点検索
                min_distance = float('inf')
                closest_source_idx = 0
                
                for source_idx, source_co in source_verts:
                    distance = (target_co - source_co).length
                    if distance < min_distance:
                        min_distance = distance
                        closest_source_idx = source_idx
                
                try:
                    weight = source_vg.weight(closest_source_idx)
                    if weight > 0.0:
                        target_vg.add([target_idx], weight, 'REPLACE')
                except RuntimeError:
                    pass
        
        return True
        
    except Exception as e:
        print(f"❌ 基本距離マッチングエラー: {e}")
        return False


if __name__ == "__main__":
    main()
