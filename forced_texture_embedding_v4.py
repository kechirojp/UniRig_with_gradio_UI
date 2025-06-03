#!/usr/bin/env python3
"""
Forced Texture Embedding v4
テクスチャの強制埋め込みによる確実なFBX生成システム

Priority 1対応: 確実なテクスチャ埋め込み
"""

import os
import sys
import json
import shutil
import subprocess
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

class ForcedTextureEmbeddingV4:
    """
    Forced Texture Embedding v4
    
    4段階強制埋め込みプロセス:
    1. COLLECT: 全テクスチャファイルの収集と検証
    2. PACK: Blender内でテクスチャの強制パッキング
    3. VERIFY: パッキング状態の確認と検証
    4. EXPORT: 強制埋め込み設定でのFBX出力
    """
    
    def __init__(self, working_dir: str, model_name: str):
        self.working_dir = working_dir
        self.model_name = model_name
        
        # 作業ディレクトリ設定
        self.forced_embed_dir = os.path.join(working_dir, "11_forced_embedding", model_name)
        self.collect_dir = os.path.join(self.forced_embed_dir, "01_collect")
        self.pack_dir = os.path.join(self.forced_embed_dir, "02_pack")
        self.verify_dir = os.path.join(self.forced_embed_dir, "03_verify")
        self.export_dir = os.path.join(self.forced_embed_dir, "04_export")
        
        # ディレクトリ作成
        for dir_path in [self.collect_dir, self.pack_dir, self.verify_dir, self.export_dir]:
            os.makedirs(dir_path, exist_ok=True)
        
        self.processing_logs = []
    
    def log(self, message: str, prefix: str = "INFO"):
        """ログメッセージの記録"""
        formatted_msg = f"[{prefix}] {message}"
        self.processing_logs.append(formatted_msg)
        print(formatted_msg)
    
    def execute_forced_embedding(self, input_fbx_path: str) -> Tuple[bool, Optional[str], Dict]:
        """
        強制テクスチャ埋め込み実行
        
        Args:
            input_fbx_path: 入力FBXファイルパス
            
        Returns:
            Tuple[bool, str, dict]: (成功フラグ, 最終FBXパス, レポート)
        """
        self.log("=== Forced Texture Embedding v4 開始 ===")
        self.log(f"入力FBX: {input_fbx_path}")
        
        try:
            # Step 1: 全テクスチャファイルの収集と検証
            collect_result = self._step1_collect_all_textures(input_fbx_path)
            if not collect_result['success']:
                return False, None, {'error': collect_result['error']}
            
            # Step 2: Blender内でテクスチャの強制パッキング
            pack_result = self._step2_force_pack_textures(collect_result)
            if not pack_result['success']:
                return False, None, {'error': pack_result['error']}
            
            # Step 3: パッキング状態の確認と検証
            verify_result = self._step3_verify_packing(pack_result)
            if not verify_result['success']:
                return False, None, {'error': verify_result['error']}
            
            # Step 4: 強制埋め込み設定でのFBX出力
            export_result = self._step4_force_export_fbx(verify_result)
            if not export_result['success']:
                return False, None, {'error': export_result['error']}
            
            # 最終レポート生成
            final_report = self._generate_final_report(export_result)
            
            self.log("✅ Forced Texture Embedding v4 完了")
            return True, export_result['final_fbx_path'], final_report
            
        except Exception as e:
            error_msg = f"Forced Embedding実行エラー: {str(e)}"
            self.log(f"❌ {error_msg}")
            return False, None, {'error': error_msg}
    
    def _step1_collect_all_textures(self, input_fbx_path: str) -> Dict:
        """
        Step 1: 全テクスチャファイルの収集と検証
        """
        self.log("Step 1: 全テクスチャファイルの収集と検証", "COLLECT")
        
        try:
            # 元のテクスチャディレクトリから収集
            original_texture_dir = os.path.join(
                self.working_dir, "01_extracted_mesh", self.model_name, "textures"
            )
            
            collected_textures = {}
            if os.path.exists(original_texture_dir):
                for filename in os.listdir(original_texture_dir):
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                        source_path = os.path.join(original_texture_dir, filename)
                        target_path = os.path.join(self.collect_dir, filename)
                        
                        # テクスチャファイルをコピー
                        shutil.copy2(source_path, target_path)
                        
                        # テクスチャタイプ判定
                        texture_type = self._determine_texture_type(filename)
                        collected_textures[texture_type] = {
                            'filename': filename,
                            'source_path': source_path,
                            'collected_path': target_path,
                            'size_mb': os.path.getsize(target_path) / (1024 * 1024)
                        }
                        
                        self.log(f"テクスチャ収集: {filename} ({texture_type}, {collected_textures[texture_type]['size_mb']:.2f}MB)")
            
            # 必要なテクスチャの確認
            expected_types = {'baseColor', 'normal', 'metallicRoughness'}
            missing_types = expected_types - set(collected_textures.keys())
            
            if missing_types:
                self.log(f"⚠️  欠損テクスチャタイプ: {', '.join(missing_types)}")
            
            result = {
                'success': True,
                'collected_textures': collected_textures,
                'missing_types': list(missing_types),
                'input_fbx_path': input_fbx_path
            }
            
            self.log(f"✅ Step 1完了: {len(collected_textures)}テクスチャ収集")
            return result
            
        except Exception as e:
            error_msg = f"Step 1エラー: {str(e)}"
            self.log(f"❌ {error_msg}")
            return {'success': False, 'error': error_msg}
    
    def _step2_force_pack_textures(self, collect_result: Dict) -> Dict:
        """
        Step 2: Blender内でテクスチャの強制パッキング
        """
        self.log("Step 2: Blender内でテクスチャの強制パッキング", "PACK")
        
        try:
            input_fbx = collect_result['input_fbx_path']
            collected_textures = collect_result['collected_textures']
            
            # 強制パッキングスクリプト生成
            pack_script = self._generate_force_pack_script(input_fbx, collected_textures)
            pack_blend_path = os.path.join(self.pack_dir, f"{self.model_name}_packed.blend")
            
            # Blenderスクリプト実行
            script_result = self._execute_blender_script(pack_script, "force_pack")
            
            if script_result['success'] and os.path.exists(pack_blend_path):
                result = {
                    'success': True,
                    'packed_blend_path': pack_blend_path,
                    'textures_packed': len(collected_textures),
                    **collect_result
                }
                
                self.log(f"✅ Step 2完了: {len(collected_textures)}テクスチャパッキング")
                return result
            else:
                return {'success': False, 'error': 'Force packing failed'}
                
        except Exception as e:
            error_msg = f"Step 2エラー: {str(e)}"
            self.log(f"❌ {error_msg}")
            return {'success': False, 'error': error_msg}
    
    def _step3_verify_packing(self, pack_result: Dict) -> Dict:
        """
        Step 3: パッキング状態の確認と検証
        """
        self.log("Step 3: パッキング状態の確認と検証", "VERIFY")
        
        try:
            packed_blend = pack_result['packed_blend_path']
            
            # パッキング検証スクリプト生成
            verify_script = self._generate_verify_script(packed_blend)
            verification_report_path = os.path.join(self.verify_dir, "packing_verification.json")
            
            # Blenderスクリプト実行
            script_result = self._execute_blender_script(verify_script, "verify_packing")
            
            if script_result['success'] and os.path.exists(verification_report_path):
                with open(verification_report_path, 'r', encoding='utf-8') as f:
                    verification_data = json.load(f)
                
                # パッキング状態の評価
                packed_images = verification_data.get('packed_images', 0)
                total_images = verification_data.get('total_images', 0)
                total_packed_size_mb = verification_data.get('total_packed_size_mb', 0)
                
                packing_success = packed_images == total_images and total_packed_size_mb > 5.0
                
                result = {
                    'success': True,
                    'verification_data': verification_data,
                    'packing_success': packing_success,
                    'packed_images': packed_images,
                    'total_packed_size_mb': total_packed_size_mb,
                    **pack_result
                }
                
                if packing_success:
                    self.log(f"✅ Step 3完了: パッキング検証成功 ({packed_images}/{total_images}, {total_packed_size_mb:.2f}MB)")
                else:
                    self.log(f"⚠️  Step 3完了: パッキング不完全 ({packed_images}/{total_images}, {total_packed_size_mb:.2f}MB)")
                
                return result
            else:
                return {'success': False, 'error': 'Packing verification failed'}
                
        except Exception as e:
            error_msg = f"Step 3エラー: {str(e)}"
            self.log(f"❌ {error_msg}")
            return {'success': False, 'error': error_msg}
    
    def _step4_force_export_fbx(self, verify_result: Dict) -> Dict:
        """
        Step 4: 強制埋め込み設定でのFBX出力
        """
        self.log("Step 4: 強制埋め込み設定でのFBX出力", "EXPORT")
        
        try:
            packed_blend = verify_result['packed_blend_path']
            
            # 最終FBXパス設定
            final_fbx_path = os.path.join(
                self.working_dir, "08_final_output", self.model_name,
                f"{self.model_name}_forced_embedded_final.fbx"
            )
            
            os.makedirs(os.path.dirname(final_fbx_path), exist_ok=True)
            
            # 強制エクスポートスクリプト生成
            export_script = self._generate_force_export_script(packed_blend, final_fbx_path)
            
            # Blenderスクリプト実行
            script_result = self._execute_blender_script(export_script, "force_export")
            
            if script_result['success'] and os.path.exists(final_fbx_path):
                final_size_mb = os.path.getsize(final_fbx_path) / (1024 * 1024)
                
                result = {
                    'success': True,
                    'final_fbx_path': final_fbx_path,
                    'final_size_mb': final_size_mb,
                    **verify_result
                }
                
                self.log(f"✅ Step 4完了: 最終FBX生成 ({final_size_mb:.2f}MB)")
                return result
            else:
                return {'success': False, 'error': 'Force export failed'}
                
        except Exception as e:
            error_msg = f"Step 4エラー: {str(e)}"
            self.log(f"❌ {error_msg}")
            return {'success': False, 'error': error_msg}
    
    def _determine_texture_type(self, filename: str) -> str:
        """ファイル名からテクスチャタイプを判定"""
        filename_lower = filename.lower()
        
        if 'basecolor' in filename_lower or 'diffuse' in filename_lower or '_bc.' in filename_lower:
            return 'baseColor'
        elif 'normal' in filename_lower or '_n.' in filename_lower or 'nrml' in filename_lower:
            return 'normal'
        elif 'metallic' in filename_lower or 'roughness' in filename_lower or '_r.' in filename_lower:
            return 'metallicRoughness'
        elif 'gloss' in filename_lower:
            return 'roughness'
        else:
            return 'unknown'
    
    def _generate_force_pack_script(self, input_fbx: str, collected_textures: Dict) -> str:
        """強制パッキングスクリプト生成"""
        pack_blend_path = os.path.join(self.pack_dir, f"{self.model_name}_packed.blend")
        
        return f'''
import bpy
import os

# FBX読み込み
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath="{input_fbx}")

# 収集されたテクスチャ情報
collected_textures = {collected_textures}

print("=== 強制テクスチャパッキング開始 ===")

# 既存画像の削除（クリーンスタート）
for img in list(bpy.data.images):
    if img.name != 'Render Result' and img.name != 'Viewer Node':
        bpy.data.images.remove(img)

# テクスチャの強制読み込みとパッキング
loaded_images = {{}}
for texture_type, texture_info in collected_textures.items():
    texture_path = texture_info['collected_path']
    filename = texture_info['filename']
    
    if os.path.exists(texture_path):
        # テクスチャを読み込み
        img = bpy.data.images.load(texture_path)
        img.name = filename
        
        # 強制パッキング
        img.pack()
        
        # カラースペース設定
        if texture_type == 'normal':
            img.colorspace_settings.name = 'Non-Color'
        elif texture_type == 'metallicRoughness':
            img.colorspace_settings.name = 'Non-Color'
        else:
            img.colorspace_settings.name = 'sRGB'
        
        loaded_images[texture_type] = img
        packed_size_mb = len(img.packed_file.data) / (1024 * 1024) if img.packed_file else 0
        print(f"パッキング完了: {{filename}} ({{texture_type}}, {{packed_size_mb:.2f}}MB)")

# マテリアルの完全再構築
for mat in bpy.data.materials:
    if mat.use_nodes:
        # 既存ノードを全削除
        mat.node_tree.nodes.clear()
        
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        
        # 基本ノード作成
        principled = nodes.new(type='ShaderNodeBsdfPrincipled')
        output = nodes.new(type='ShaderNodeOutputMaterial')
        principled.location = (0, 0)
        output.location = (300, 0)
        links.new(principled.outputs['BSDF'], output.inputs['Surface'])
        
        # テクスチャノードの作成と接続
        y_offset = 300
        
        # Base Colorテクスチャ
        if 'baseColor' in loaded_images:
            base_tex = nodes.new(type='ShaderNodeTexImage')
            base_tex.image = loaded_images['baseColor']
            base_tex.location = (-400, y_offset)
            links.new(base_tex.outputs['Color'], principled.inputs['Base Color'])
            y_offset -= 300
        
        # Normalテクスチャ
        if 'normal' in loaded_images:
            normal_tex = nodes.new(type='ShaderNodeTexImage')
            normal_tex.image = loaded_images['normal']
            normal_tex.location = (-400, y_offset)
            
            normal_map = nodes.new(type='ShaderNodeNormalMap')
            normal_map.location = (-200, y_offset)
            links.new(normal_tex.outputs['Color'], normal_map.inputs['Color'])
            links.new(normal_map.outputs['Normal'], principled.inputs['Normal'])
            y_offset -= 300
        
        # Metallic/Roughnessテクスチャ
        if 'metallicRoughness' in loaded_images:
            mr_tex = nodes.new(type='ShaderNodeTexImage')
            mr_tex.image = loaded_images['metallicRoughness']
            mr_tex.location = (-400, y_offset)
            
            separate = nodes.new(type='ShaderNodeSeparateRGB')
            separate.location = (-200, y_offset)
            links.new(mr_tex.outputs['Color'], separate.inputs['Image'])
            links.new(separate.outputs['R'], principled.inputs['Metallic'])
            links.new(separate.outputs['G'], principled.inputs['Roughness'])

# Blendファイル保存
bpy.ops.wm.save_as_mainfile(filepath="{pack_blend_path}")

print("=== 強制パッキング完了 ===")
print(f"Blendファイル保存: {pack_blend_path}")
'''
    
    def _generate_verify_script(self, packed_blend: str) -> str:
        """パッキング検証スクリプト生成"""
        verification_report_path = os.path.join(self.verify_dir, "packing_verification.json")
        
        return f'''
import bpy
import json

# Blendファイル読み込み
bpy.ops.wm.open_mainfile(filepath="{packed_blend}")

verification_data = {{
    "total_images": 0,
    "packed_images": 0,
    "total_packed_size_mb": 0,
    "images": []
}}

print("=== パッキング状態検証 ===")

# 全画像の検証
for img in bpy.data.images:
    if img.name not in ['Render Result', 'Viewer Node']:
        img_data = {{
            "name": img.name,
            "packed": img.packed_file is not None,
            "size": list(img.size) if hasattr(img, 'size') else None
        }}
        
        verification_data["total_images"] += 1
        
        if img.packed_file:
            packed_size_mb = len(img.packed_file.data) / (1024 * 1024)
            img_data["packed_size_mb"] = packed_size_mb
            verification_data["packed_images"] += 1
            verification_data["total_packed_size_mb"] += packed_size_mb
            print(f"✅ パック済み: {{img.name}} ({{packed_size_mb:.2f}}MB)")
        else:
            img_data["packed_size_mb"] = 0
            print(f"❌ 未パック: {{img.name}}")
        
        verification_data["images"].append(img_data)

print(f"\\n検証結果: {{verification_data['packed_images']}}/{{verification_data['total_images']}} パック済み")
print(f"総パックサイズ: {{verification_data['total_packed_size_mb']:.2f}}MB")

# 結果保存
with open("{verification_report_path}", 'w', encoding='utf-8') as f:
    json.dump(verification_data, f, indent=2, ensure_ascii=False)

print("検証完了")
'''
    
    def _generate_force_export_script(self, packed_blend: str, final_fbx_path: str) -> str:
        """強制エクスポートスクリプト生成"""
        return f'''
import bpy

# Blendファイル読み込み
bpy.ops.wm.open_mainfile(filepath="{packed_blend}")

print("=== 強制FBXエクスポート開始 ===")

# パッキング状態の最終確認
total_packed_size = 0
for img in bpy.data.images:
    if img.packed_file:
        packed_size_mb = len(img.packed_file.data) / (1024 * 1024)
        total_packed_size += packed_size_mb
        print(f"確認: {{img.name}} パック済み ({{packed_size_mb:.2f}}MB)")

print(f"総パックサイズ: {{total_packed_size:.2f}}MB")

# 強制埋め込み設定でFBXエクスポート
bpy.ops.export_scene.fbx(
    filepath="{final_fbx_path}",
    embed_textures=True,
    use_selection=False,
    global_scale=1.0,
    apply_scale_options='FBX_SCALE_NONE',
    mesh_smooth_type='FACE',
    use_mesh_modifiers=True,
    use_armature_deform_only=True,
    add_leaf_bones=False,
    path_mode='COPY'
)

print(f"FBXエクスポート完了: {final_fbx_path}")
'''
    
    def _execute_blender_script(self, script_content: str, script_name: str) -> Dict:
        """Blenderスクリプト実行"""
        try:
            script_file = os.path.join(self.forced_embed_dir, f"{script_name}.py")
            with open(script_file, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            cmd = ['blender', '--background', '--python', script_file]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd='/app')
            
            if result.returncode == 0:
                return {'success': True, 'output': result.stdout}
            else:
                return {'success': False, 'error': result.stderr}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _generate_final_report(self, export_result: Dict) -> Dict:
        """最終レポート生成"""
        return {
            'method': 'Forced Texture Embedding v4',
            'textures_collected': len(export_result.get('collected_textures', {})),
            'textures_packed': export_result.get('textures_packed', 0),
            'packed_images': export_result.get('packed_images', 0),
            'total_packed_size_mb': export_result.get('total_packed_size_mb', 0),
            'packing_success': export_result.get('packing_success', False),
            'final_fbx_path': export_result.get('final_fbx_path'),
            'final_size_mb': export_result.get('final_size_mb'),
            'processing_logs': self.processing_logs,
            'success': True
        }

if __name__ == "__main__":
    # テスト実行
    working_dir = "/app/pipeline_work"
    model_name = "bird_final_test"
    
    forced_embed = ForcedTextureEmbeddingV4(working_dir, model_name)
    
    # テスト対象FBX（元の問題のあるファイル）
    test_fbx = "/app/pipeline_work/08_final_output/bird_final_test/bird_final_test_final_textured_rigged.fbx"
    
    if os.path.exists(test_fbx):
        success, final_fbx, report = forced_embed.execute_forced_embedding(test_fbx)
        
        print(f"\n=== Forced Embedding v4 結果 ===")
        print(f"成功: {success}")
        print(f"最終FBX: {final_fbx}")
        print(f"レポート: {json.dumps(report, indent=2, ensure_ascii=False)}")
    else:
        print(f"テストFBXファイルが見つかりません: {test_fbx}")
