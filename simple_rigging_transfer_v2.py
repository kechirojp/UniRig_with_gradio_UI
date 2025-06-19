"""
Blender リギング移植スクリプト v3 (相対位置関係保持版)
===
核心理解:
- 相対位置関係の保持: ソースメッシュとソースアーマチュアの相対的な位置関係をそのまま維持
- ウェイトベースバインディング: 頂点グループが持つウェイト情報を基にした正確なバインディング
- 絶対位置は無関係: 原点合わせなどは不要、相対関係が全て

実行方法:
    python simple_rigging_transfer_v2.py
    
または Blender内で直接実行:
    exec(open('/app/simple_rigging_transfer_v2.py').read())
"""

import bpy

def main():
    """メイン実行関数"""
    print("=== 相対位置関係保持＋ウェイトベースバインディング リギング移植スクリプト ===")
    
    try:
        # Objectモードに切り替え
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # 選択解除
        bpy.ops.object.select_all(action='DESELECT')
        
        # リギング移植実行
        success = transfer_rigging_relative_position()
        
        if success:
            print("\n🎉 リギング移植完了！")
            print("相対位置関係とウェイトベースバインディングによる正確な移植が完了しました。")
        else:
            print("\n❌ リギング移植失敗")
            
    except Exception as e:
        print(f"\n💥 エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

def transfer_rigging_relative_position():
    """
    相対位置関係保持＋ウェイトベースバインディング によるリギング移植
    
    核心理解:
    - ソースメッシュとアーマチュアの相対位置関係をそのまま維持
    - 頂点グループウェイト情報の正確な転送
    - 絶対位置は無関係、相対関係が全て
    
    前提:
    - ソース: SK_tucano_bird.001 + Armature
    - ターゲット: SK_tucano_bird.002（アーマチュアなし）
    
    目標:
    - SK_tucano_bird.002（親）→ Armature_SK_tucano_bird.002（子）
    """
    print("=== 相対位置関係保持＋ウェイトベースバインディング開始 ===")
    
    # 必要オブジェクト取得
    source_mesh = bpy.data.objects.get('SK_tucano_bird.001')
    source_armature = bpy.data.objects.get('Armature')
    target_mesh = bpy.data.objects.get('SK_tucano_bird.002')
    
    if not all([source_mesh, source_armature, target_mesh]):
        print("❌ 必要なオブジェクトが見つかりません")
        print(f"source_mesh: {source_mesh}")
        print(f"source_armature: {source_armature}")
        print(f"target_mesh: {target_mesh}")
        return False
    
    print(f"✅ オブジェクト確認完了")
    print(f"  ソースメッシュ: {source_mesh.name}")
    print(f"  ソースアーマチュア: {source_armature.name}")
    print(f"  ターゲットメッシュ: {target_mesh.name}")
    
    # Step 1: 新規アーマチュア作成（相対位置関係保持）
    print("\n--- Step 1: 新規アーマチュア作成 ---")
    
    # 既存のターゲットアーマチュアがあれば削除
    existing_target_armature = bpy.data.objects.get('Armature_SK_tucano_bird.002')
    if existing_target_armature:
        print(f"既存ターゲットアーマチュア削除: {existing_target_armature.name}")
        bpy.data.objects.remove(existing_target_armature, do_unlink=True)
    
    # ソースアーマチュアのデータをコピー
    armature_data = source_armature.data.copy()
    armature_data.name = "Armature_SK_tucano_bird.002_Data"
    
    # 新規アーマチュアオブジェクト作成
    target_armature = bpy.data.objects.new("Armature_SK_tucano_bird.002", armature_data)
    bpy.context.collection.objects.link(target_armature)
    
    # 相対位置関係保持：ソースの相対位置をターゲットに適用
    source_relative_pos = source_armature.location - source_mesh.location
    target_armature.location = target_mesh.location + source_relative_pos
    
    # 回転・スケール情報も保持
    target_armature.rotation_euler = source_armature.rotation_euler.copy()
    target_armature.scale = source_armature.scale.copy()
    
    print(f"✅ 新規アーマチュア作成完了: {target_armature.name}")
    print(f"  位置: {target_armature.location}")
    print(f"  相対オフセット: {source_relative_pos}")
    
    # Step 2: 頂点グループ完全転送
    print("\n--- Step 2: 頂点グループ完全転送 ---")
    
    # 既存頂点グループクリア
    target_mesh.vertex_groups.clear()
    
    # 完全同一メッシュ前提での直接転送
    transferred_groups = 0
    total_weights = 0
    
    for source_vg in source_mesh.vertex_groups:
        target_vg = target_mesh.vertex_groups.new(name=source_vg.name)
        
        # 直接インデックス転送
        for vert_idx in range(len(source_mesh.data.vertices)):
            try:
                weight = source_vg.weight(vert_idx)
                if weight > 0.0:
                    target_vg.add([vert_idx], weight, 'REPLACE')
                    total_weights += 1
            except RuntimeError:
                # ウェイトが存在しない頂点はスキップ
                pass
        
        transferred_groups += 1
    
    print(f"✅ 頂点グループ転送完了: {transferred_groups}個のグループ、{total_weights}個のウェイト")
    
    # Step 3: アーマチュアモディファイア設定
    print("\n--- Step 3: アーマチュアモディファイア設定 ---")
    
    # 既存アーマチュアモディファイア削除
    for mod in list(target_mesh.modifiers):
        if mod.type == 'ARMATURE':
            target_mesh.modifiers.remove(mod)
            print(f"既存モディファイア削除: {mod.name}")
    
    # 新規アーマチュアモディファイア作成
    armature_mod = target_mesh.modifiers.new(name="Armature", type='ARMATURE')
    armature_mod.object = target_armature
    armature_mod.use_vertex_groups = True
    armature_mod.use_bone_envelopes = False
    
    print(f"✅ アーマチュアモディファイア設定完了: {target_armature.name}")
    
    # Step 4: 親子関係設定
    print("\n--- Step 4: 親子関係設定 ---")
    
    # 既存親子関係解除
    if target_mesh.parent:
        target_mesh.parent = None
    if target_armature.parent:
        target_armature.parent = None
    
    # 最終要件：SK_tucano_bird.002（親）→ Armature_SK_tucano_bird.002（子）
    target_armature.parent = target_mesh
    target_armature.parent_type = 'OBJECT'
    target_armature.parent_bone = ""
    target_armature.matrix_parent_inverse.identity()
    
    print(f"✅ 親子関係設定完了:")
    print(f"  親: {target_mesh.name}")
    print(f"  子: {target_armature.name}")
    
    # Step 5: 検証
    print("\n--- Step 5: 検証 ---")
    
    # 頂点グループ確認
    vg_count = len(target_mesh.vertex_groups)
    print(f"  頂点グループ数: {vg_count}")
    
    # アーマチュアモディファイア確認
    armature_mods = [mod for mod in target_mesh.modifiers if mod.type == 'ARMATURE']
    print(f"  アーマチュアモディファイア数: {len(armature_mods)}")
    
    if armature_mods:
        print(f"  参照アーマチュア: {armature_mods[0].object.name}")
    
    # 親子関係確認
    print(f"  親子関係: {target_armature.parent.name if target_armature.parent else 'なし'}")
    
    # 相対位置確認
    current_relative_pos = target_armature.location - target_mesh.location
    print(f"  現在の相対位置: {current_relative_pos}")
    print(f"  元の相対位置: {source_relative_pos}")
    
    if vg_count > 0 and len(armature_mods) > 0 and target_armature.parent == target_mesh:
        print("\n🎉 相対位置関係保持＋ウェイトベースバインディング完了！")
        return True
    else:
        print("\n❌ 移植失敗")
        return False


if __name__ == "__main__":
    main()



