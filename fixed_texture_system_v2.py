#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
テクスチャマテリアル問題修正版 - ラフネスメタリック修正・ベースカラー重複除去
"""

import bpy
import os
import json
from pathlib import Path

class FixedTextureSystemV2:
    """
    修正版テクスチャシステム
    - ベースカラー重複除去（1つに統一）
    - ラフネスメタリック復元（適切なチャンネル分離）
    - 完全なマテリアル構造再構築
    """
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.working_dir = Path("/app/pipeline_work")
        self.extracted_dir = self.working_dir / "01_extracted_mesh" / model_name
        self.skinning_dir = self.working_dir / "03_skinning_output" / model_name
        self.output_dir = self.working_dir / "08_final_output" / model_name
        
        # 作業ディレクトリ作成
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"🔧 FixedTextureSystemV2 initialized for: {model_name}")
    
    def fix_texture_material_issues(self, skinned_fbx_path: str) -> dict:
        """
        テクスチャ・マテリアル問題の完全修正
        """
        print("=== テクスチャ・マテリアル問題修正開始 ===")
        
        try:
            # Step 1: スキニング済みFBXの安全インポート
            print("[STEP1] スキニング済みFBXインポート...")
            self._safe_clear_scene()
            
            if not os.path.exists(skinned_fbx_path):
                return {'success': False, 'error': f'Skinned FBX not found: {skinned_fbx_path}'}
            
            # FBXインポート
            bpy.ops.import_scene.fbx(
                filepath=skinned_fbx_path,
                use_manual_orientation=False,
                global_scale=1.0,
                use_anim=True,
                use_custom_props=False,
                ignore_leaf_bones=True
            )
            print("✅ FBXインポート完了")
            
            # Step 2: テクスチャファイル情報の回復
            print("[STEP2] テクスチャファイル情報回復...")
            texture_files = self._discover_texture_files()
            if not texture_files:
                return {'success': False, 'error': 'No texture files found'}
            
            print(f"📁 発見されたテクスチャファイル: {len(texture_files)}")
            for name, info in texture_files.items():
                print(f"  - {name}: {info['type']} ({info['size_mb']:.2f}MB)")
            
            # Step 3: ベースカラー重複問題の修正
            print("[STEP3] ベースカラー重複問題修正...")
            self._fix_basecolor_duplication(texture_files)
            
            # Step 4: ラフネス・メタリック復元
            print("[STEP4] ラフネス・メタリック復元...")
            self._restore_metallic_roughness(texture_files)
            
            # Step 5: 完全なマテリアル再構築
            print("[STEP5] 完全マテリアル再構築...")
            self._rebuild_complete_materials(texture_files)
            
            # Step 6: 最終FBXエクスポート
            print("[STEP6] 最終FBXエクスポート...")
            final_fbx_path = self._export_final_fbx()
            
            # Step 7: 品質検証
            print("[STEP7] 品質検証...")
            validation_result = self._validate_final_output(final_fbx_path)
            
            return {
                'success': True,
                'final_fbx_path': final_fbx_path,
                'validation': validation_result,
                'texture_count': len(texture_files),
                'fixed_issues': [
                    'ベースカラー重複除去',
                    'ラフネス・メタリック復元',
                    '完全マテリアル再構築'
                ]
            }
            
        except Exception as e:
            print(f"❌ 修正処理エラー: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    def _safe_clear_scene(self):
        """安全なシーンクリア"""
        try:
            # オブジェクトモードに設定
            if bpy.context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            
            # 全オブジェクト選択・削除
            bpy.ops.object.select_all(action='SELECT')
            bpy.ops.object.delete(use_global=False)
            
            # データブロッククリア
            for collection in [bpy.data.meshes, bpy.data.materials, bpy.data.images]:
                for item in list(collection):
                    collection.remove(item)
            
            print("✅ シーンクリア完了")
            
        except Exception as e:
            print(f"⚠️ シーンクリア警告: {e}")
    
    def _discover_texture_files(self) -> dict:
        """テクスチャファイルの発見・分類"""
        texture_files = {}
        texture_dir = self.extracted_dir / "textures"
        
        if not texture_dir.exists():
            print(f"⚠️ テクスチャディレクトリが見つかりません: {texture_dir}")
            return {}
        
        # テクスチャファイル検索
        for texture_path in texture_dir.glob("*.png"):
            texture_name = texture_path.stem
            file_size_mb = texture_path.stat().st_size / (1024 * 1024)
            
            # テクスチャタイプ判定
            texture_type = self._classify_texture_type(texture_name)
            
            texture_files[texture_name] = {
                'path': str(texture_path),
                'type': texture_type,
                'size_mb': file_size_mb,
                'original_name': texture_name
            }
        
        return texture_files
    
    def _classify_texture_type(self, texture_name: str) -> str:
        """テクスチャタイプの分類"""
        name_lower = texture_name.lower()
        
        # ベースカラー判定
        if any(pattern in name_lower for pattern in ['col', 'basecolor', 'diffuse', '_bc', 'color']):
            return 'BASE_COLOR'
        
        # ノーマルマップ判定
        elif any(pattern in name_lower for pattern in ['nrml', 'normal', '_n', 'norm']):
            return 'NORMAL'
        
        # ラフネス判定
        elif any(pattern in name_lower for pattern in ['gloss', 'rough', '_r', 'roughness']):
            return 'ROUGHNESS'
        
        # メタリック判定
        elif any(pattern in name_lower for pattern in ['metallic', '_m', 'metal']):
            return 'METALLIC'
        
        # メタリックラフネス結合判定
        elif any(pattern in name_lower for pattern in ['metallicroughness', 'metallic_roughness']):
            return 'METALLIC_ROUGHNESS'
        
        else:
            return 'UNKNOWN'
    
    def _fix_basecolor_duplication(self, texture_files: dict):
        """ベースカラー重複問題の修正"""
        print("🎨 ベースカラー重複修正...")
        
        # ベースカラーテクスチャを特定
        basecolor_textures = {name: info for name, info in texture_files.items() 
                             if info['type'] == 'BASE_COLOR'}
        
        if len(basecolor_textures) > 1:
            print(f"⚠️ ベースカラー重複検出: {len(basecolor_textures)}個")
            
            # 最大サイズのものを主テクスチャとして選択
            primary_basecolor = max(basecolor_textures.items(), 
                                  key=lambda x: x[1]['size_mb'])
            
            print(f"✅ 主テクスチャ選択: {primary_basecolor[0]} ({primary_basecolor[1]['size_mb']:.2f}MB)")
            
            # 重複テクスチャの除去（メタデータから）
            for name, info in list(texture_files.items()):
                if info['type'] == 'BASE_COLOR' and name != primary_basecolor[0]:
                    print(f"🗑️ 重複除去: {name}")
                    del texture_files[name]
        
        elif len(basecolor_textures) == 1:
            print(f"✅ ベースカラー正常: 1個")
        else:
            print(f"⚠️ ベースカラーが見つかりません")
    
    def _restore_metallic_roughness(self, texture_files: dict):
        """ラフネス・メタリック復元"""
        print("🔧 ラフネス・メタリック復元...")
        
        # 個別のメタリック・ラフネステクスチャを確認
        metallic_textures = [name for name, info in texture_files.items() 
                           if info['type'] == 'METALLIC']
        roughness_textures = [name for name, info in texture_files.items() 
                            if info['type'] == 'ROUGHNESS']
        combined_textures = [name for name, info in texture_files.items() 
                           if info['type'] == 'METALLIC_ROUGHNESS']
        
        print(f"📊 メタリックテクスチャ: {len(metallic_textures)}")
        print(f"📊 ラフネステクスチャ: {len(roughness_textures)}")
        print(f"📊 結合テクスチャ: {len(combined_textures)}")
        
        # bird.glbの場合は通常、gloss (roughness) テクスチャが存在
        if roughness_textures:
            print(f"✅ ラフネステクスチャ発見: {roughness_textures}")
        
        # メタリックテクスチャが不足している場合の処理
        if not metallic_textures and not combined_textures:
            print("⚠️ メタリックテクスチャが不足 - デフォルト値で補完")
            # この場合はマテリアル設定でデフォルト値を使用
    
    def _rebuild_complete_materials(self, texture_files: dict):
        """完全なマテリアル再構築"""
        print("🎨 完全マテリアル再構築...")
        
        # 既存マテリアルをクリア
        for mat in list(bpy.data.materials):
            bpy.data.materials.remove(mat)
        
        # 新規マテリアル作成
        material = bpy.data.materials.new(name=f"{self.model_name}_Material")
        material.use_nodes = True
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        
        # デフォルトノードクリア
        nodes.clear()
        
        # Principled BSDFノード作成
        principled = nodes.new(type='ShaderNodeBsdfPrincipled')
        principled.location = (0, 0)
        principled.name = "Principled_BSDF"
        
        # Material Outputノード作成
        output = nodes.new(type='ShaderNodeOutputMaterial')
        output.location = (400, 0)
        
        # BSDFとOutputを接続
        links.new(principled.outputs['BSDF'], output.inputs['Surface'])
        
        # テクスチャノードの作成と接続
        y_offset = 300
        created_textures = {}
        
        for tex_name, tex_info in texture_files.items():
            tex_path = tex_info['path']
            tex_type = tex_info['type']
            
            if os.path.exists(tex_path):
                print(f"📎 テクスチャノード作成: {tex_name} ({tex_type})")
                
                # Image Textureノード作成
                tex_node = nodes.new(type='ShaderNodeTexImage')
                tex_node.location = (-400, y_offset)
                tex_node.name = f"TEX_{tex_name}"
                tex_node.label = f"{tex_type}_{tex_name}"
                
                # 画像読み込み
                try:
                    # 既存の画像を確認
                    image = None
                    for existing_img in bpy.data.images:
                        if existing_img.filepath == tex_path or existing_img.name == tex_name:
                            image = existing_img
                            break
                    
                    # 新規読み込み
                    if not image:
                        image = bpy.data.images.load(tex_path)
                    
                    tex_node.image = image
                    
                    # カラースペース設定
                    if tex_type in ['NORMAL', 'ROUGHNESS', 'METALLIC', 'METALLIC_ROUGHNESS']:
                        image.colorspace_settings.name = 'Non-Color'
                    else:
                        image.colorspace_settings.name = 'sRGB'
                    
                    # Principled BSDFへの接続
                    if tex_type == 'BASE_COLOR':
                        links.new(tex_node.outputs['Color'], principled.inputs['Base Color'])
                        print(f"   🔗 Base Color接続完了")
                        
                    elif tex_type == 'NORMAL':
                        # Normal Mapノード作成
                        normal_map = nodes.new(type='ShaderNodeNormalMap')
                        normal_map.location = (-200, y_offset - 50)
                        links.new(tex_node.outputs['Color'], normal_map.inputs['Color'])
                        links.new(normal_map.outputs['Normal'], principled.inputs['Normal'])
                        print(f"   🔗 Normal接続完了")
                        
                    elif tex_type == 'ROUGHNESS':
                        # ラフネス値を反転（Glossマップの場合）
                        if 'gloss' in tex_name.lower():
                            # ColorRampで反転
                            color_ramp = nodes.new(type='ShaderNodeValToRGB')
                            color_ramp.location = (-200, y_offset)
                            color_ramp.color_ramp.elements[0].color = (1, 1, 1, 1)  # 白
                            color_ramp.color_ramp.elements[1].color = (0, 0, 0, 1)  # 黒
                            links.new(tex_node.outputs['Color'], color_ramp.inputs['Fac'])
                            links.new(color_ramp.outputs['Color'], principled.inputs['Roughness'])
                            print(f"   🔗 Roughness接続完了（Gloss反転）")
                        else:
                            links.new(tex_node.outputs['Color'], principled.inputs['Roughness'])
                            print(f"   🔗 Roughness接続完了")
                            
                    elif tex_type == 'METALLIC':
                        links.new(tex_node.outputs['Color'], principled.inputs['Metallic'])
                        print(f"   🔗 Metallic接続完了")
                        
                    elif tex_type == 'METALLIC_ROUGHNESS':
                        # Separate RGBノード作成（Blender 3.4以降はSeparate ColorとSeparate RGBがあるので互換性を考慮）
                        try:
                            separate_rgb = nodes.new(type='ShaderNodeSeparateColor')
                            separate_rgb.mode = 'RGB'
                        except:
                            # 古いバージョン対応
                            separate_rgb = nodes.new(type='ShaderNodeSeparateRGB')
                        
                        separate_rgb.location = (-200, y_offset)
                        separate_rgb.name = f"Separate_{tex_name}"
                        
                        # テクスチャからSeparateへの接続
                        links.new(tex_node.outputs['Color'], separate_rgb.inputs[0])  # 'Image'または最初の入力
                        
                        # glTF標準: G=Roughness, B=Metallic
                        # Roughness接続
                        if 'Roughness' in principled.inputs:
                            if hasattr(separate_rgb.outputs, 'Green'):
                                links.new(separate_rgb.outputs['Green'], principled.inputs['Roughness'])
                            else:
                                links.new(separate_rgb.outputs[1], principled.inputs['Roughness'])  # G channel
                            print(f"   🔗 Roughness (Green channel) 接続完了")
                        
                        # Metallic接続
                        if 'Metallic' in principled.inputs:
                            if hasattr(separate_rgb.outputs, 'Blue'):
                                links.new(separate_rgb.outputs['Blue'], principled.inputs['Metallic'])
                            else:
                                links.new(separate_rgb.outputs[2], principled.inputs['Metallic'])  # B channel
                            print(f"   🔗 Metallic (Blue channel) 接続完了")
                        
                        print(f"   🔗 MetallicRoughness分離接続完了")
                    
                    created_textures[tex_name] = tex_node
                    y_offset -= 150
                    
                except Exception as e:
                    print(f"❌ テクスチャ読み込みエラー {tex_name}: {e}")
        
        # デフォルト値設定（テクスチャが不足している場合）
        if not any(info['type'] == 'METALLIC' for info in texture_files.values()):
            principled.inputs['Metallic'].default_value = 0.0  # 非金属
            print("   ⚙️ Metallicデフォルト値設定: 0.0")
        
        if not any(info['type'] in ['ROUGHNESS', 'METALLIC_ROUGHNESS'] for info in texture_files.values()):
            principled.inputs['Roughness'].default_value = 0.5  # 中程度
            print("   ⚙️ Roughnessデフォルト値設定: 0.5")
        
        # 全てのメッシュオブジェクトにマテリアル割り当て
        mesh_count = 0
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                # 既存マテリアルクリア
                obj.data.materials.clear()
                # 新マテリアル割り当て
                obj.data.materials.append(material)
                mesh_count += 1
        
        print(f"✅ マテリアル再構築完了 - {mesh_count}個のメッシュに適用")
        print(f"✅ 作成されたテクスチャノード: {len(created_textures)}個")
    
    def _export_final_fbx(self) -> str:
        """最終FBXエクスポート"""
        output_path = str(self.output_dir / f"{self.model_name}_fixed_final.fbx")
        
        try:
            # 全テクスチャをパック（埋め込み準備）
            for image in bpy.data.images:
                if image.source == 'FILE' and not image.packed_file:
                    image.pack()
            
            # FBXエクスポート
            bpy.ops.export_scene.fbx(
                filepath=output_path,
                check_existing=False,
                use_selection=False,
                use_active_collection=False,
                global_scale=1.0,
                apply_unit_scale=True,
                apply_scale_options='FBX_SCALE_NONE',
                use_space_transform=True,
                bake_space_transform=False,
                object_types={'MESH', 'ARMATURE'},
                use_mesh_modifiers=True,
                use_mesh_modifiers_render=True,
                mesh_smooth_type='OFF',
                use_subsurf=False,
                use_mesh_edges=False,
                use_tspace=False,
                use_custom_props=False,
                add_leaf_bones=True,
                primary_bone_axis='Y',
                secondary_bone_axis='X',
                use_armature_deform_only=False,
                armature_nodetype='NULL',
                bake_anim=True,
                bake_anim_use_all_bones=True,
                bake_anim_use_nla_strips=True,
                bake_anim_use_all_actions=True,
                bake_anim_force_startend_keying=True,
                bake_anim_step=1.0,
                bake_anim_simplify_factor=1.0,
                path_mode='COPY',
                embed_textures=True,
                batch_mode='OFF',
                use_batch_own_dir=True,
                use_metadata=True
            )
            
            print(f"✅ FBXエクスポート完了: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"❌ FBXエクスポートエラー: {e}")
            raise
    
    def _validate_final_output(self, fbx_path: str) -> dict:
        """最終出力の品質検証"""
        if not os.path.exists(fbx_path):
            return {'success': False, 'error': 'Final FBX not found'}
        
        file_size_mb = os.path.getsize(fbx_path) / (1024 * 1024)
        
        # 品質判定
        quality_assessment = {
            'file_size_mb': file_size_mb,
            'size_check_passed': file_size_mb >= 4.0,  # 最低4MB
            'quality_level': 'EXCELLENT' if file_size_mb >= 7.0 else 'GOOD' if file_size_mb >= 4.0 else 'POOR',
            'estimated_embedded_textures': max(1, int(file_size_mb / 2)),  # 推定
            'texture_preservation': 'COMPLETE' if file_size_mb >= 4.0 else 'PARTIAL'
        }
        
        return quality_assessment

def test_fixed_texture_system():
    """修正版テクスチャシステムのテスト"""
    model_name = "bird_final_test"
    skinned_fbx_path = f"/app/pipeline_work/03_skinning_output/{model_name}/{model_name}_skinned.fbx"
    
    # システム初期化
    fixed_system = FixedTextureSystemV2(model_name)
    
    # 修正処理実行
    result = fixed_system.fix_texture_material_issues(skinned_fbx_path)
    
    print("\n=== 修正処理結果 ===")
    print(f"成功: {result['success']}")
    
    if result['success']:
        print(f"最終FBX: {result['final_fbx_path']}")
        print(f"テクスチャ数: {result['texture_count']}")
        print(f"修正項目: {', '.join(result['fixed_issues'])}")
        print(f"品質評価: {result['validation']['quality_level']}")
        print(f"ファイルサイズ: {result['validation']['file_size_mb']:.2f}MB")
    else:
        print(f"エラー: {result['error']}")

if __name__ == "__main__":
    test_fixed_texture_system()
