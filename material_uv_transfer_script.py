import bpy

def transfer_materials_and_uvmaps(source_name, target_name):
    """
    ソースオブジェクトのマテリアルとUVマップをターゲットオブジェクトに移植する
    
    Args:
        source_name (str): ソースオブジェクト名
        target_name (str): ターゲットオブジェクト名
    """
    # ソースオブジェクトとターゲットオブジェクトを取得
    source_obj = bpy.data.objects.get(source_name)
    target_obj = bpy.data.objects.get(target_name)

    if source_obj and target_obj:
        print(f"ソースオブジェクト '{source_obj.name}' を確認")
        print(f"ターゲットオブジェクト '{target_obj.name}' を確認")
        
        # 成功フラグ
        material_success = False
        uv_success = False
        
        # マテリアルの移植（ソースにマテリアルがある場合）
        if source_obj.data.materials:
            print(f"ソースオブジェクトのマテリアル数: {len(source_obj.data.materials)}")
            print(f"ターゲットオブジェクトの既存マテリアル数: {len(target_obj.data.materials)}")
            
            # ターゲットオブジェクトの既存マテリアルをクリア（上書き）
            target_obj.data.materials.clear()
            print("ターゲットオブジェクトの既存マテリアルをクリアしました")
            
            # ソースオブジェクトの各マテリアルをターゲットオブジェクトに追加
            for material in source_obj.data.materials:
                if material:
                    target_obj.data.materials.append(material)
                    print(f"マテリアル '{material.name}' を {target_obj.name} に追加しました")
                else:
                    target_obj.data.materials.append(None)
                    print("空のマテリアルスロットを追加しました")
            
            print(f"マテリアル移植完了: {source_obj.name} → {target_obj.name}")
            material_success = True
        else:
            print(f"ソースオブジェクト '{source_obj.name}' にマテリアルがありません")
            # マテリアルがなくてもUVマップの処理は続行
        
        # UVマップの移植（ソースにUVマップがある場合）
        if source_obj.data.uv_layers:
            print(f"ソースオブジェクトのUVマップ数: {len(source_obj.data.uv_layers)}")
            print(f"ターゲットオブジェクトの既存UVマップ数: {len(target_obj.data.uv_layers)}")
            
            # ターゲットオブジェクトの既存UVマップをクリア（上書き）
            while target_obj.data.uv_layers:
                target_obj.data.uv_layers.remove(target_obj.data.uv_layers[0])
            print("ターゲットオブジェクトの既存UVマップをクリアしました")
            
            # アクティブなUVマップを記録
            active_uv_name = None
            if source_obj.data.uv_layers.active:
                active_uv_name = source_obj.data.uv_layers.active.name
            
            # ソースオブジェクトの各UVマップをターゲットオブジェクトにコピー
            for uv_layer in source_obj.data.uv_layers:
                # 新しいUVマップを作成
                new_uv_layer = target_obj.data.uv_layers.new(name=uv_layer.name)
                
                # UVデータをコピー
                for loop_idx in range(len(target_obj.data.loops)):
                    if loop_idx < len(source_obj.data.loops):
                        new_uv_layer.data[loop_idx].uv = uv_layer.data[loop_idx].uv
                    
                print(f"UVマップ '{uv_layer.name}' を {target_obj.name} に追加しました")
            
            # アクティブUVマップを設定
            if active_uv_name and target_obj.data.uv_layers.get(active_uv_name):
                target_obj.data.uv_layers.active = target_obj.data.uv_layers[active_uv_name]
                print(f"アクティブUVマップを '{active_uv_name}' に設定しました")
            
            print(f"UVマップ移植完了: {source_obj.name} → {target_obj.name}")
            uv_success = True
        else:
            print(f"ソースオブジェクト '{source_obj.name}' にUVマップがありません")
        
        # 結果の判定
        if material_success or uv_success:
            return True
        else:
            print("マテリアルもUVマップも移植するものがありませんでした")
            return False
    else:
        if not source_obj:
            print(f"エラー: {source_name} オブジェクトが見つかりません")
        if not target_obj:
            print(f"エラー: {target_name} オブジェクトが見つかりません")
        return False

# メイン実行部分
if __name__ == "__main__":
    # bear_boyのマテリアルとUVマップをbear_boy.001に移植
    success = transfer_materials_and_uvmaps("bear_boy", "bear_boy.001")
    
    if success:
        print("[OK] マテリアルとUVマップの移植が正常に完了しました")
    else:
        print("[FAIL] マテリアルとUVマップの移植に失敗しました")

# FBXエクスポート時に自動的にテクスチャを埋め込み
bpy.ops.export_scene.fbx(
    filepath="d:/output_with_textures.fbx",
    embed_textures=True,      # FBXファイル内にテクスチャを埋め込み
    path_mode='COPY',         # テクスチャファイルも出力フォルダにコピー
    use_selection=False,
    use_mesh_modifiers=True
)