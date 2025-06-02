#!/usr/bin/env python
"""
FBXエクスポート修正の簡易テスト
yamlなどの依存関係を避けて直接テスト
"""
import bpy
import os

def prepare_material_for_fbx_export_standalone(material):
    """
    FBXエクスポート用にマテリアルを準備する（スタンドアロン版）
    """
    if not material.use_nodes or not material.node_tree:
        return
    
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    
    print(f"DEBUG: Preparing material '{material.name}' for FBX export")
    
    # Principled BSDFノードを見つける
    principled_node = None
    for node in nodes:
        if node.type == 'BSDF_PRINCIPLED':
            principled_node = node
            break
    
    if not principled_node:
        print(f"DEBUG: No Principled BSDF found in material '{material.name}'")
        return
    
    # テクスチャノードを特定
    base_color_texture = None
    normal_texture = None
    roughness_texture = None
    
    for node in nodes:
        if node.type == 'TEX_IMAGE' and node.image:
            image_name = node.image.name.lower()
            color_space = node.image.colorspace_settings.name
            
            # Base color texture
            if (color_space == 'sRGB' or 
                any(pattern in image_name for pattern in ['col', 'bc', 'base', 'diffuse', 'albedo'])):
                base_color_texture = node
                print(f"DEBUG: Found base color texture: {node.image.name}")
            # Normal texture
            elif (color_space == 'Non-Color' and 
                  any(pattern in image_name for pattern in ['nrml', 'normal', '_n', 'norm'])):
                normal_texture = node
                print(f"DEBUG: Found normal texture: {node.image.name}")
            # Roughness texture
            elif (color_space == 'Non-Color' and 
                  any(pattern in image_name for pattern in ['gloss', 'rough', '_r', 'metallic'])):
                roughness_texture = node
                print(f"DEBUG: Found roughness texture: {node.image.name}")
    
    # Base Colorの直接接続（Mix nodeをバイパス）
    if base_color_texture:
        # 既存の接続をクリア
        for link in list(principled_node.inputs['Base Color'].links):
            links.remove(link)
        
        # 直接接続
        links.new(base_color_texture.outputs['Color'], principled_node.inputs['Base Color'])
        print(f"DEBUG: Direct connection: {base_color_texture.image.name} → Base Color")
    
    # Normal mapは保持（Normal Map nodeを経由）
    if normal_texture:
        # Normal Map nodeを探す
        normal_map_node = None
        for node in nodes:
            if node.type == 'NORMAL_MAP':
                normal_map_node = node
                break
        
        if normal_map_node:
            # 接続を確認・復元
            if not normal_map_node.inputs['Color'].links:
                links.new(normal_texture.outputs['Color'], normal_map_node.inputs['Color'])
            if not principled_node.inputs['Normal'].links:
                links.new(normal_map_node.outputs['Normal'], principled_node.inputs['Normal'])
            print(f"DEBUG: Normal map connection maintained: {normal_texture.image.name} → Normal")
    
    # Roughnessの接続処理
    if roughness_texture:
        # 既存の接続をクリア
        for link in list(principled_node.inputs['Roughness'].links):
            links.remove(link)
        
        # Roughnessテクスチャを直接接続（通常はGreenチャンネル）
        # FBX互換性のため、直接接続を試行
        links.new(roughness_texture.outputs['Color'], principled_node.inputs['Roughness'])
        print(f"DEBUG: Direct roughness connection: {roughness_texture.image.name} → Roughness")
    
    print(f"DEBUG: Material '{material.name}' prepared for FBX export")

def test_fbx_export_fix():
    print("🧪 FBXエクスポート修正の簡易テスト開始")
    
    # Blenderの初期化
    bpy.ops.wm.read_homefile(app_template="")
    
    # bird.glbを読み込み
    input_file = "/app/examples/bird.glb"
    print(f"📁 入力ファイル: {input_file}")
    
    try:
        bpy.ops.import_scene.gltf(filepath=input_file)
        print("✅ GLBファイルの読み込み成功")
    except Exception as e:
        print(f"❌ GLBファイル読み込みエラー: {e}")
        return False
    
    # 修正前のマテリアル構造を記録
    print("\n📊 修正前のマテリアル構造:")
    original_connections = {}
    for mat in bpy.data.materials:
        if mat.use_nodes and mat.node_tree:
            print(f"  マテリアル: {mat.name}")
            print(f"    ノード数: {len(mat.node_tree.nodes)}")
            
            connections = {}
            for node in mat.node_tree.nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    principled = node
                    
                    # 各入力の接続状況を記録
                    for input_name in ['Base Color', 'Normal', 'Roughness']:
                        if principled.inputs[input_name].links:
                            source = principled.inputs[input_name].links[0].from_node
                            connections[input_name] = f"{source.type} ({source.name})"
                            print(f"    {input_name} ← {source.type} ({source.name})")
                        else:
                            connections[input_name] = "未接続"
                            print(f"    {input_name} ← 未接続")
            
            original_connections[mat.name] = connections
    
    # FBXエクスポート準備を実行
    print("\n🔧 FBXエクスポート準備を実行中...")
    try:
        for mat in bpy.data.materials:
            if mat.use_nodes:
                print(f"  マテリアル '{mat.name}' を準備中...")
                prepare_material_for_fbx_export_standalone(mat)
        
        print("✅ FBXエクスポート準備完了")
    except Exception as e:
        print(f"❌ FBXエクスポート準備エラー: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 修正後のマテリアル構造を確認
    print("\n📊 修正後のマテリアル構造:")
    for mat in bpy.data.materials:
        if mat.use_nodes and mat.node_tree:
            print(f"  マテリアル: {mat.name}")
            print(f"    ノード数: {len(mat.node_tree.nodes)}")
            
            for node in mat.node_tree.nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    principled = node
                    
                    # 各入力の接続状況を確認
                    for input_name in ['Base Color', 'Normal', 'Roughness']:
                        if principled.inputs[input_name].links:
                            source = principled.inputs[input_name].links[0].from_node
                            print(f"    {input_name} ← {source.type} ({source.name})")
                        else:
                            print(f"    {input_name} ← 未接続")
    
    # テスト用ディレクトリを作成
    os.makedirs("/app/fbx_fix_test", exist_ok=True)
    
    # FBXエクスポートテスト
    print("\n💾 修正版FBXエクスポート...")
    fbx_output = "/app/fbx_fix_test/test_fixed_export.fbx"
    try:
        bpy.ops.export_scene.fbx(
            filepath=fbx_output,
            use_selection=False,
            global_scale=1.0,
            object_types={'ARMATURE', 'MESH'},
            use_mesh_modifiers=True,
            mesh_smooth_type='OFF',
            embed_textures=True,  # テクスチャを埋め込む
            path_mode='COPY',     # テクスチャをコピー
            batch_mode='OFF'
        )
        print(f"✅ FBXエクスポート成功: {fbx_output}")
        
        if os.path.exists(fbx_output):
            size = os.path.getsize(fbx_output)
            print(f"    ファイルサイズ: {size} bytes")
        
    except Exception as e:
        print(f"❌ FBXエクスポートエラー: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 比較用GLBエクスポート
    print("\n💾 比較用GLBエクスポート...")
    glb_output = "/app/fbx_fix_test/test_fixed_export.glb"
    try:
        bpy.ops.export_scene.gltf(
            filepath=glb_output,
            export_format='GLB',
            export_texcoords=True,
            export_normals=True,
            export_skins=True,
            export_animations=True
        )
        print(f"✅ GLBエクスポート成功: {glb_output}")
        
        if os.path.exists(glb_output):
            size = os.path.getsize(glb_output)
            print(f"    ファイルサイズ: {size} bytes")
        
    except Exception as e:
        print(f"❌ GLBエクスポートエラー: {e}")
    
    print("\n🎯 簡易テスト完了")
    return True

if __name__ == "__main__":
    test_fbx_export_fix()
