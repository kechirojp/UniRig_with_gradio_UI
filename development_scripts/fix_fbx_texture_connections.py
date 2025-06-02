#!/usr/bin/env python3
"""
FBXファイルのテクスチャ接続問題を修正するスクリプト
既存のFBXファイルを読み込んで、テクスチャ接続を修正し、再エクスポート
"""
import bpy
import os

def clear_scene():
    """シーンをクリア"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # マテリアルをクリア
    for material in bpy.data.materials:
        bpy.data.materials.remove(material, do_unlink=True)
    
    # テクスチャをクリア
    for texture in bpy.data.textures:
        bpy.data.textures.remove(texture, do_unlink=True)
    
    # 画像をクリア
    for image in bpy.data.images:
        if image.users == 0 or image.name not in ['Render Result', 'Viewer Node']:
            bpy.data.images.remove(image, do_unlink=True)

def fix_material_connections(material):
    """マテリアルのテクスチャ接続を修正"""
    if not material.use_nodes or not material.node_tree:
        return False
    
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    
    print(f"🔧 Fixing material: {material.name}")
    
    # Principled BSDFノードを見つける
    principled_node = None
    for node in nodes:
        if node.type == 'BSDF_PRINCIPLED':
            principled_node = node
            break
    
    if not principled_node:
        print(f"❌ No Principled BSDF found in {material.name}")
        return False
    
    # 利用可能なテクスチャノードを特定
    texture_nodes = []
    for node in nodes:
        if node.type == 'TEX_IMAGE' and node.image:
            image_name = node.image.name.lower()
            color_space = node.image.colorspace_settings.name
            
            texture_info = {
                'node': node,
                'name': node.image.name,
                'color_space': color_space,
                'type': 'unknown'
            }
            
            # テクスチャタイプを判定
            if (color_space == 'sRGB' or 
                any(pattern in image_name for pattern in ['col', 'bc', 'base', 'diffuse', 'albedo'])):
                texture_info['type'] = 'base_color'
            elif (color_space == 'Non-Color' and 
                  any(pattern in image_name for pattern in ['nrml', 'normal', '_n', 'norm'])):
                texture_info['type'] = 'normal'
            elif (color_space == 'Non-Color' and 
                  any(pattern in image_name for pattern in ['gloss', 'rough', '_r', 'metallic'])):
                texture_info['type'] = 'roughness'
            
            texture_nodes.append(texture_info)
    
    print(f"📋 Found {len(texture_nodes)} texture nodes:")
    for tex in texture_nodes:
        print(f"   - {tex['name']} ({tex['type']}) - {tex['color_space']}")
    
    # 各テクスチャタイプに対して接続を修正
    changes_made = False
    
    # Base Color接続を修正
    base_color_textures = [tex for tex in texture_nodes if tex['type'] == 'base_color']
    if base_color_textures:
        base_texture = base_color_textures[0]
        
        # 既存の接続をクリア
        for link in list(principled_node.inputs['Base Color'].links):
            links.remove(link)
        
        # 直接接続
        links.new(base_texture['node'].outputs['Color'], principled_node.inputs['Base Color'])
        print(f"✅ Connected {base_texture['name']} to Base Color (direct)")
        changes_made = True
    
    # Normal接続を修正
    normal_textures = [tex for tex in texture_nodes if tex['type'] == 'normal']
    if normal_textures:
        normal_texture = normal_textures[0]
        
        # Normal Map nodeを見つけるか作成
        normal_map_node = None
        for node in nodes:
            if node.type == 'NORMAL_MAP':
                normal_map_node = node
                break
        
        if not normal_map_node:
            normal_map_node = nodes.new(type='ShaderNodeNormalMap')
            normal_map_node.location = (principled_node.location.x - 200, principled_node.location.y)
        
        # 接続をクリアして再接続
        for link in list(normal_map_node.inputs['Color'].links):
            links.remove(link)
        for link in list(principled_node.inputs['Normal'].links):
            links.remove(link)
        
        # 新しい接続
        links.new(normal_texture['node'].outputs['Color'], normal_map_node.inputs['Color'])
        links.new(normal_map_node.outputs['Normal'], principled_node.inputs['Normal'])
        print(f"✅ Connected {normal_texture['name']} to Normal via Normal Map")
        changes_made = True
    
    # Roughness接続を修正
    roughness_textures = [tex for tex in texture_nodes if tex['type'] == 'roughness']
    if roughness_textures:
        roughness_texture = roughness_textures[0]
        
        # Separate Color nodeを見つけるか作成
        separate_node = None
        for node in nodes:
            if node.type == 'SEPARATE_COLOR':
                separate_node = node
                break
        
        if not separate_node:
            separate_node = nodes.new(type='ShaderNodeSeparateColor')
            separate_node.location = (principled_node.location.x - 200, principled_node.location.y - 200)
        
        # 接続をクリアして再接続
        for link in list(separate_node.inputs['Color'].links):
            links.remove(link)
        for link in list(principled_node.inputs['Roughness'].links):
            links.remove(link)
        
        # 新しい接続
        links.new(roughness_texture['node'].outputs['Color'], separate_node.inputs['Color'])
        links.new(separate_node.outputs['Green'], principled_node.inputs['Roughness'])
        print(f"✅ Connected {roughness_texture['name']} to Roughness (Green channel)")
        changes_made = True
    
    return changes_made

def fix_fbx_texture_connections(input_fbx_path, output_fbx_path):
    """FBXファイルのテクスチャ接続を修正"""
    print(f"🔧 Fixing FBX texture connections")
    print(f"   Input: {input_fbx_path}")
    print(f"   Output: {output_fbx_path}")
    
    if not os.path.exists(input_fbx_path):
        print(f"❌ Input file not found: {input_fbx_path}")
        return False
    
    # シーンをクリア
    clear_scene()
    
    try:
        # FBXファイルを読み込み
        print("📥 Loading FBX file...")
        bpy.ops.import_scene.fbx(filepath=input_fbx_path)
        print("✅ FBX file loaded successfully")
        
        # すべてのマテリアルの接続を修正
        total_changes = 0
        for material in bpy.data.materials:
            if fix_material_connections(material):
                total_changes += 1
        
        print(f"🔧 Fixed {total_changes} materials")
        
        # 画像をパック
        print("📦 Packing images...")
        for img in bpy.data.images:
            if img.name not in ['Render Result', 'Viewer Node']:
                try:
                    if not (hasattr(img, 'packed_file') and img.packed_file):
                        img.pack()
                        print(f"   ✅ Packed: {img.name}")
                except Exception as e:
                    print(f"   ❌ Failed to pack {img.name}: {e}")
        
        # 修正されたFBXをエクスポート
        print("📤 Exporting fixed FBX...")
        bpy.ops.export_scene.fbx(
            filepath=output_fbx_path,
            use_selection=False,
            add_leaf_bones=True,
            path_mode='COPY',
            embed_textures=True,
            use_mesh_modifiers=True,
            use_custom_props=True,
            mesh_smooth_type='OFF',
            use_tspace=True,
            bake_anim=False
        )
        
        print(f"✅ Fixed FBX exported to: {output_fbx_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error fixing FBX: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🔧 FBXファイル テクスチャ接続修正ツール")
    print("=" * 60)
    
    input_fbx = "/app/fbx_analysis/merged_for_analysis.fbx"
    output_fbx = "/app/fbx_analysis/merged_fixed.fbx"
    
    print(f"入力FBX: {input_fbx}")
    print(f"出力FBX: {output_fbx}")
    print(f"入力ファイル存在: {os.path.exists(input_fbx)}")
    
    if os.path.exists(input_fbx):
        success = fix_fbx_texture_connections(input_fbx, output_fbx)
        if success:
            print(f"\n🎉 FBXファイルの修正が完了しました!")
            print(f"修正されたファイル: {output_fbx}")
            if os.path.exists(output_fbx):
                size = os.path.getsize(output_fbx)
                print(f"ファイルサイズ: {size:,} bytes")
        else:
            print(f"\n❌ FBXファイルの修正に失敗しました")
    else:
        print(f"\n❌ 入力ファイルが見つかりません: {input_fbx}")

if __name__ == "__main__":
    main()
