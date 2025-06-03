#!/usr/bin/env python3
"""
Enhanced Safe Texture Restoration v2
テクスチャ重複排除とMetallic/Roughnessテクスチャ復元システム

Priority 1対応: Safe FBX-to-Blend Texture Flow
7段階強化フロー: 重複排除 + 完全マテリアル復元
"""

import os
import sys
import json
import shutil
import subprocess
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

class EnhancedSafeTextureRestorationV2:
    """
    Enhanced Safe Texture Restoration v2
    
    7段階強化プロセス:
    1. ANALYZE: FBX構造とテクスチャ重複分析
    2. DEDUPLICATE: テクスチャ重複の排除と最適化
    3. RECOVER: 欠損マテリアル要素の復元
    4. RECONSTRUCT: 完全マテリアルノード構造の再構築
    5. OPTIMIZE: テクスチャパッキングとファイルサイズ最適化
    6. VALIDATE: 品質検証と整合性チェック
    7. EXPORT: 最適化された最終FBX出力
    """
    
    def __init__(self, working_dir: str, model_name: str, use_subprocess: bool = True):
        self.working_dir = working_dir
        self.model_name = model_name
        self.use_subprocess = use_subprocess
        
        # ディレクトリ構造の設定
        self.enhanced_dir = os.path.join(working_dir, "09_enhanced_restoration", model_name)
        self.stage_dirs = {
            'stage1_analysis': os.path.join(self.enhanced_dir, "01_analysis"),
            'stage2_deduplication': os.path.join(self.enhanced_dir, "02_deduplication"),
            'stage3_recovery': os.path.join(self.enhanced_dir, "03_recovery"),
            'stage4_reconstruction': os.path.join(self.enhanced_dir, "04_reconstruction"),
            'stage5_optimization': os.path.join(self.enhanced_dir, "05_optimization"),
            'stage6_validation': os.path.join(self.enhanced_dir, "06_validation"),
            'stage7_export': os.path.join(self.enhanced_dir, "07_final_export")
        }
        
        # ディレクトリ作成
        for stage_dir in self.stage_dirs.values():
            os.makedirs(stage_dir, exist_ok=True)
        
        # 処理状態
        self.processing_logs = []
        self.current_stage = 0
        self.total_stages = 7
        
    def log(self, message: str, stage: Optional[str] = None):
        """ログメッセージの記録"""
        if stage:
            formatted_msg = f"[{stage}] {message}"
        else:
            formatted_msg = message
        
        self.processing_logs.append(formatted_msg)
        print(formatted_msg)
        
    def execute_enhanced_restoration(self, skinned_fbx_path: str) -> Tuple[bool, Optional[str], Dict]:
        """
        7段階Enhanced Safe Texture Restoration実行
        
        Args:
            skinned_fbx_path: スキニング済みFBXファイルパス
            
        Returns:
            Tuple[bool, str, dict]: (成功フラグ, 最終FBXパス, 品質レポート)
        """
        self.log("=== Enhanced Safe Texture Restoration v2 開始 ===")
        self.log(f"入力FBX: {skinned_fbx_path}")
        
        try:
            # Stage 1: FBX構造とテクスチャ重複分析
            analysis_result = self._stage1_analyze_structure(skinned_fbx_path)
            if not analysis_result['success']:
                return False, None, {'error': analysis_result['error']}
            
            # Stage 2: テクスチャ重複の排除と最適化
            dedup_result = self._stage2_deduplicate_textures(analysis_result)
            if not dedup_result['success']:
                return False, None, {'error': dedup_result['error']}
            
            # Stage 3: 欠損マテリアル要素の復元
            recovery_result = self._stage3_recover_materials(dedup_result)
            if not recovery_result['success']:
                return False, None, {'error': recovery_result['error']}
            
            # Stage 4: 完全マテリアルノード構造の再構築
            reconstruct_result = self._stage4_reconstruct_materials(recovery_result)
            if not reconstruct_result['success']:
                return False, None, {'error': reconstruct_result['error']}
            
            # Stage 5: テクスチャパッキングとファイルサイズ最適化
            optimize_result = self._stage5_optimize_textures(reconstruct_result)
            if not optimize_result['success']:
                return False, None, {'error': optimize_result['error']}
            
            # Stage 6: 品質検証と整合性チェック
            validation_result = self._stage6_validate_quality(optimize_result)
            if not validation_result['success']:
                return False, None, {'error': validation_result['error']}
            
            # Stage 7: 最適化された最終FBX出力
            export_result = self._stage7_final_export(validation_result)
            if not export_result['success']:
                return False, None, {'error': export_result['error']}
            
            # 最終品質レポート生成
            quality_report = self._generate_final_quality_report(export_result)
            
            self.log("✅ Enhanced Safe Texture Restoration v2 完了")
            return True, export_result['final_fbx_path'], quality_report
            
        except Exception as e:
            error_msg = f"Enhanced Restoration実行エラー: {str(e)}"
            self.log(f"❌ {error_msg}")
            self.log(f"詳細: {traceback.format_exc()}")
            return False, None, {'error': error_msg}
    
    def _stage1_analyze_structure(self, skinned_fbx_path: str) -> Dict:
        """
        Stage 1: FBX構造とテクスチャ重複分析
        """
        self.current_stage = 1
        self.log("Stage 1: FBX構造とテクスチャ重複分析開始", "STAGE1")
        
        try:
            # 元のマテリアル情報の読み込み
            original_metadata_path = os.path.join(
                self.working_dir, "01_extracted_mesh", self.model_name, "materials_metadata.json"
            )
            
            original_textures = {}
            if os.path.exists(original_metadata_path):
                with open(original_metadata_path, 'r', encoding='utf-8') as f:
                    original_data = json.load(f)
                    original_textures = original_data.get('texture_files', {})
                    self.log(f"元のテクスチャ情報読み込み: {len(original_textures)} テクスチャ")
            
            # BlenderスクリプトでFBX分析実行
            analysis_script = self._generate_analysis_script(skinned_fbx_path)
            analysis_output_path = os.path.join(self.stage_dirs['stage1_analysis'], "fbx_analysis.json")
            
            script_result = self._execute_blender_script(analysis_script, "fbx_structure_analysis")
            
            if script_result['success']:
                # 分析結果の処理
                if os.path.exists(analysis_output_path):
                    with open(analysis_output_path, 'r', encoding='utf-8') as f:
                        analysis_data = json.load(f)
                    
                    # テクスチャ重複検出
                    duplicates = self._detect_texture_duplicates(analysis_data)
                    
                    # 欠損テクスチャ検出  
                    missing_textures = self._detect_missing_textures(analysis_data, original_textures)
                    
                    result = {
                        'success': True,
                        'analysis_data': analysis_data,
                        'original_textures': original_textures,
                        'duplicates': duplicates,
                        'missing_textures': missing_textures,
                        'analysis_output_path': analysis_output_path
                    }
                    
                    self.log(f"✅ Stage 1完了: 重複={len(duplicates)}, 欠損={len(missing_textures)}")
                    return result
                else:
                    return {'success': False, 'error': 'Analysis output file not found'}
            else:
                return {'success': False, 'error': script_result['error']}
                
        except Exception as e:
            error_msg = f"Stage 1エラー: {str(e)}"
            self.log(f"❌ {error_msg}")
            return {'success': False, 'error': error_msg}
    
    def _stage2_deduplicate_textures(self, analysis_result: Dict) -> Dict:
        """
        Stage 2: テクスチャ重複の排除と最適化
        """
        self.current_stage = 2
        self.log("Stage 2: テクスチャ重複の排除と最適化開始", "STAGE2")
        
        try:
            duplicates = analysis_result['duplicates']
            analysis_data = analysis_result['analysis_data']
            
            if not duplicates:
                self.log("重複テクスチャなし - Stage 2スキップ")
                return {
                    'success': True,
                    'deduplication_performed': False,
                    'analysis_data': analysis_data,
                    **analysis_result
                }
            
            # 重複除去スクリプト生成と実行
            dedup_script = self._generate_deduplication_script(analysis_data, duplicates)
            dedup_output_path = os.path.join(self.stage_dirs['stage2_deduplication'], f"{self.model_name}_deduplicated.fbx")
            
            script_result = self._execute_blender_script(dedup_script, "texture_deduplication")
            
            if script_result['success'] and os.path.exists(dedup_output_path):
                # 重複除去後のサイズ確認
                file_size_mb = os.path.getsize(dedup_output_path) / (1024 * 1024)
                
                result = {
                    'success': True,
                    'deduplication_performed': True,
                    'deduplicated_fbx_path': dedup_output_path,
                    'file_size_mb': file_size_mb,
                    'duplicates_removed': len(duplicates),
                    **analysis_result
                }
                
                self.log(f"✅ Stage 2完了: {len(duplicates)}重複除去, サイズ={file_size_mb:.2f}MB")
                return result
            else:
                return {'success': False, 'error': script_result.get('error', 'Deduplication failed')}
                
        except Exception as e:
            error_msg = f"Stage 2エラー: {str(e)}"
            self.log(f"❌ {error_msg}")
            return {'success': False, 'error': error_msg}
    
    def _stage3_recover_materials(self, dedup_result: Dict) -> Dict:
        """
        Stage 3: 欠損マテリアル要素の復元
        """
        self.current_stage = 3
        self.log("Stage 3: 欠損マテリアル要素の復元開始", "STAGE3")
        
        try:
            missing_textures = dedup_result.get('missing_textures', {})
            original_textures = dedup_result['original_textures']
            
            if not missing_textures:
                self.log("欠損テクスチャなし - Stage 3スキップ")
                return {
                    'success': True,
                    'recovery_performed': False,
                    **dedup_result
                }
            
            # 欠損テクスチャの復元
            recovered_textures = {}
            for texture_type, texture_info in missing_textures.items():
                # 元のテクスチャディレクトリから復元
                original_texture_dir = os.path.join(
                    self.working_dir, "01_extracted_mesh", self.model_name, "textures"
                )
                
                recovery_success = self._recover_texture_file(
                    texture_type, texture_info, original_texture_dir, 
                    self.stage_dirs['stage3_recovery']
                )
                
                if recovery_success:
                    recovered_textures[texture_type] = recovery_success
                    self.log(f"復元成功: {texture_type}")
                else:
                    self.log(f"復元失敗: {texture_type}")
            
            # 復元テクスチャを適用したFBX生成
            input_fbx = dedup_result.get('deduplicated_fbx_path', dedup_result.get('skinned_fbx_path'))
            recovery_script = self._generate_recovery_script(input_fbx, recovered_textures)
            recovery_output_path = os.path.join(self.stage_dirs['stage3_recovery'], f"{self.model_name}_recovered.fbx")
            
            script_result = self._execute_blender_script(recovery_script, "material_recovery")
            
            if script_result['success'] and os.path.exists(recovery_output_path):
                result = {
                    'success': True,
                    'recovery_performed': True,
                    'recovered_fbx_path': recovery_output_path,
                    'recovered_textures': recovered_textures,
                    **dedup_result
                }
                
                self.log(f"✅ Stage 3完了: {len(recovered_textures)}テクスチャ復元")
                return result
            else:
                return {'success': False, 'error': script_result.get('error', 'Recovery failed')}
                
        except Exception as e:
            error_msg = f"Stage 3エラー: {str(e)}"
            self.log(f"❌ {error_msg}")
            return {'success': False, 'error': error_msg}
    
    def _stage4_reconstruct_materials(self, recovery_result: Dict) -> Dict:
        """
        Stage 4: 完全マテリアルノード構造の再構築
        """
        self.current_stage = 4
        self.log("Stage 4: 完全マテリアルノード構造の再構築開始", "STAGE4")
        
        try:
            # 最新のFBXパス取得
            input_fbx = recovery_result.get('recovered_fbx_path') or \
                       recovery_result.get('deduplicated_fbx_path') or \
                       recovery_result.get('skinned_fbx_path')
            
            # 完全マテリアル構造の定義
            target_material_structure = self._define_target_material_structure(recovery_result)
            
            # マテリアル再構築スクリプト生成
            reconstruction_script = self._generate_reconstruction_script(input_fbx, target_material_structure)
            reconstruction_output_path = os.path.join(self.stage_dirs['stage4_reconstruction'], f"{self.model_name}_reconstructed.fbx")
            
            script_result = self._execute_blender_script(reconstruction_script, "material_reconstruction")
            
            if script_result['success'] and os.path.exists(reconstruction_output_path):
                result = {
                    'success': True,
                    'reconstructed_fbx_path': reconstruction_output_path,
                    'target_material_structure': target_material_structure,
                    **recovery_result
                }
                
                self.log("✅ Stage 4完了: マテリアル構造再構築")
                return result
            else:
                return {'success': False, 'error': script_result.get('error', 'Reconstruction failed')}
                
        except Exception as e:
            error_msg = f"Stage 4エラー: {str(e)}"
            self.log(f"❌ {error_msg}")
            return {'success': False, 'error': error_msg}
    
    def _stage5_optimize_textures(self, reconstruct_result: Dict) -> Dict:
        """
        Stage 5: テクスチャパッキングとファイルサイズ最適化
        """
        self.current_stage = 5
        self.log("Stage 5: テクスチャパッキングとファイルサイズ最適化開始", "STAGE5")
        
        try:
            input_fbx = reconstruct_result['reconstructed_fbx_path']
            
            # テクスチャ最適化スクリプト生成
            optimization_script = self._generate_optimization_script(input_fbx)
            optimization_output_path = os.path.join(self.stage_dirs['stage5_optimization'], f"{self.model_name}_optimized.fbx")
            
            script_result = self._execute_blender_script(optimization_script, "texture_optimization")
            
            if script_result['success'] and os.path.exists(optimization_output_path):
                file_size_mb = os.path.getsize(optimization_output_path) / (1024 * 1024)
                
                result = {
                    'success': True,
                    'optimized_fbx_path': optimization_output_path,
                    'optimized_file_size_mb': file_size_mb,
                    **reconstruct_result
                }
                
                self.log(f"✅ Stage 5完了: 最適化サイズ={file_size_mb:.2f}MB")
                return result
            else:
                return {'success': False, 'error': script_result.get('error', 'Optimization failed')}
                
        except Exception as e:
            error_msg = f"Stage 5エラー: {str(e)}"
            self.log(f"❌ {error_msg}")
            return {'success': False, 'error': error_msg}
    
    def _stage6_validate_quality(self, optimize_result: Dict) -> Dict:
        """
        Stage 6: 品質検証と整合性チェック
        """
        self.current_stage = 6
        self.log("Stage 6: 品質検証と整合性チェック開始", "STAGE6")
        
        try:
            optimized_fbx = optimize_result['optimized_fbx_path']
            
            # 品質検証スクリプト生成
            validation_script = self._generate_validation_script(optimized_fbx)
            validation_output_path = os.path.join(self.stage_dirs['stage6_validation'], "quality_validation.json")
            
            script_result = self._execute_blender_script(validation_script, "quality_validation")
            
            if script_result['success'] and os.path.exists(validation_output_path):
                with open(validation_output_path, 'r', encoding='utf-8') as f:
                    validation_data = json.load(f)
                
                # 品質基準チェック
                quality_score = self._calculate_quality_score(validation_data, optimize_result)
                
                result = {
                    'success': True,
                    'validation_data': validation_data,
                    'quality_score': quality_score,
                    'quality_passed': quality_score >= 0.8,  # 80%以上で合格
                    **optimize_result
                }
                
                self.log(f"✅ Stage 6完了: 品質スコア={quality_score:.2f}")
                return result
            else:
                return {'success': False, 'error': script_result.get('error', 'Validation failed')}
                
        except Exception as e:
            error_msg = f"Stage 6エラー: {str(e)}"
            self.log(f"❌ {error_msg}")
            return {'success': False, 'error': error_msg}
    
    def _stage7_final_export(self, validation_result: Dict) -> Dict:
        """
        Stage 7: 最適化された最終FBX出力
        """
        self.current_stage = 7
        self.log("Stage 7: 最適化された最終FBX出力開始", "STAGE7")
        
        try:
            validated_fbx = validation_result['optimized_fbx_path']
            
            # 最終出力パス設定
            final_output_path = os.path.join(
                self.working_dir, "08_final_output", self.model_name,
                f"{self.model_name}_enhanced_final_textured_rigged.fbx"
            )
            
            os.makedirs(os.path.dirname(final_output_path), exist_ok=True)
            
            # 最終エクスポートスクリプト生成
            export_script = self._generate_final_export_script(validated_fbx, final_output_path)
            
            script_result = self._execute_blender_script(export_script, "final_export")
            
            if script_result['success'] and os.path.exists(final_output_path):
                final_file_size_mb = os.path.getsize(final_output_path) / (1024 * 1024)
                
                result = {
                    'success': True,
                    'final_fbx_path': final_output_path,
                    'final_file_size_mb': final_file_size_mb,
                    **validation_result
                }
                
                self.log(f"✅ Stage 7完了: 最終サイズ={final_file_size_mb:.2f}MB")
                return result
            else:
                return {'success': False, 'error': script_result.get('error', 'Final export failed')}
                
        except Exception as e:
            error_msg = f"Stage 7エラー: {str(e)}"
            self.log(f"❌ {error_msg}")
            return {'success': False, 'error': error_msg}
    
    def _generate_analysis_script(self, fbx_path: str) -> str:
        """FBX構造分析用Blenderスクリプト生成"""
        output_path = os.path.join(self.stage_dirs['stage1_analysis'], "fbx_analysis.json")
        
        return f'''
import bpy
import json
import os

# FBXファイルの読み込み
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath="{fbx_path}")

analysis_data = {{
    "objects": [],
    "materials": [],
    "textures": [],
    "images": []
}}

# オブジェクト分析
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        obj_data = {{
            "name": obj.name,
            "material_slots": [slot.material.name if slot.material else None for slot in obj.material_slots]
        }}
        analysis_data["objects"].append(obj_data)

# マテリアル分析
for mat in bpy.data.materials:
    if mat.use_nodes:
        nodes_info = []
        for node in mat.node_tree.nodes:
            node_info = {{
                "name": node.name,
                "type": node.type,
                "inputs": [],
                "outputs": []
            }}
            
            # TEX_IMAGEノードの特別処理
            if node.type == 'TEX_IMAGE' and node.image:
                node_info["image_name"] = node.image.name
                node_info["image_size"] = list(node.image.size) if hasattr(node.image, 'size') else None
                node_info["packed"] = node.image.packed_file is not None
                if node.image.packed_file:
                    node_info["packed_size_mb"] = len(node.image.packed_file.data) / (1024 * 1024)
            
            nodes_info.append(node_info)
        
        mat_data = {{
            "name": mat.name,
            "nodes": nodes_info
        }}
        analysis_data["materials"].append(mat_data)

# 画像分析
for img in bpy.data.images:
    img_data = {{
        "name": img.name,
        "size": list(img.size) if hasattr(img, 'size') else None,
        "filepath": img.filepath,
        "packed": img.packed_file is not None
    }}
    if img.packed_file:
        img_data["packed_size_mb"] = len(img.packed_file.data) / (1024 * 1024)
    
    analysis_data["images"].append(img_data)

# 結果保存
with open("{output_path}", 'w', encoding='utf-8') as f:
    json.dump(analysis_data, f, indent=2, ensure_ascii=False)

print("FBX構造分析完了")
'''
    
    def _detect_texture_duplicates(self, analysis_data: Dict) -> List[Dict]:
        """テクスチャ重複検出"""
        duplicates = []
        image_map = {}
        
        for img in analysis_data.get('images', []):
            img_name = img['name']
            base_name = img_name.split('.')[0]  # .001などの拡張子を除去
            
            if base_name in image_map:
                # 重複発見
                duplicate_info = {
                    'base_name': base_name,
                    'original': image_map[base_name],
                    'duplicate': img
                }
                duplicates.append(duplicate_info)
            else:
                image_map[base_name] = img
        
        return duplicates
    
    def _detect_missing_textures(self, analysis_data: Dict, original_textures: Dict) -> Dict:
        """欠損テクスチャ検出"""
        missing = {}
        current_texture_types = set()
        
        # 現在のテクスチャタイプを収集
        for img in analysis_data.get('images', []):
            img_name = img['name'].lower()
            if 'basecolor' in img_name or 'diffuse' in img_name:
                current_texture_types.add('baseColor')
            elif 'normal' in img_name:
                current_texture_types.add('normal')
            elif 'metallic' in img_name or 'roughness' in img_name:
                current_texture_types.add('metallicRoughness')
        
        # 期待されるテクスチャタイプ
        expected_types = {'baseColor', 'normal', 'metallicRoughness'}
        
        # 欠損検出
        for expected_type in expected_types:
            if expected_type not in current_texture_types:
                if expected_type in original_textures:
                    missing[expected_type] = original_textures[expected_type]
        
        return missing
    
    def _generate_deduplication_script(self, analysis_data: Dict, duplicates: List[Dict]) -> str:
        """テクスチャ重複除去スクリプト生成"""
        output_path = os.path.join(self.stage_dirs['stage2_deduplication'], f"{self.model_name}_deduplicated.fbx")
        
        # 削除対象画像のリストを作成
        images_to_remove = [dup['duplicate']['name'] for dup in duplicates]
        
        return f'''
import bpy

# 重複画像の削除
images_to_remove = {images_to_remove}

for img_name in images_to_remove:
    if img_name in bpy.data.images:
        img = bpy.data.images[img_name]
        
        # ノードからの参照を削除
        for mat in bpy.data.materials:
            if mat.use_nodes:
                for node in mat.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image == img:
                        # 元の画像に置き換え
                        base_name = img_name.split('.')[0]
                        if base_name in bpy.data.images:
                            node.image = bpy.data.images[base_name]
        
        # 画像データを削除
        bpy.data.images.remove(img)
        print(f"重複画像削除: {{img_name}}")

# FBX出力
bpy.ops.export_scene.fbx(
    filepath="{output_path}",
    embed_textures=True,
    use_selection=False,
    global_scale=1.0
)

print("重複除去完了")
'''
    
    def _recover_texture_file(self, texture_type: str, texture_info: Dict, 
                             source_dir: str, target_dir: str) -> Optional[str]:
        """テクスチャファイルの復元"""
        try:
            # ソースファイルの検索
            source_file = None
            for filename in os.listdir(source_dir):
                if texture_type.lower() in filename.lower():
                    source_file = os.path.join(source_dir, filename)
                    break
            
            if not source_file or not os.path.exists(source_file):
                return None
            
            # ターゲットファイルパスの生成
            filename = f"{self.model_name}_{texture_type}.png"
            target_file = os.path.join(target_dir, filename)
            
            # ファイルコピー
            shutil.copy2(source_file, target_file)
            
            return target_file
            
        except Exception as e:
            self.log(f"テクスチャ復元エラー {texture_type}: {e}")
            return None
    
    def _generate_recovery_script(self, input_fbx: str, recovered_textures: Dict) -> str:
        """マテリアル復元スクリプト生成"""
        output_path = os.path.join(self.stage_dirs['stage3_recovery'], f"{self.model_name}_recovered.fbx")
        
        return f'''
import bpy
import os

# FBX読み込み
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath="{input_fbx}")

# 復元テクスチャ情報
recovered_textures = {recovered_textures}

# マテリアル処理
for mat in bpy.data.materials:
    if mat.use_nodes:
        nodes = mat.node_tree.nodes
        principled = None
        
        # Principled BSDFノードを取得
        for node in nodes:
            if node.type == 'BSDF_PRINCIPLED':
                principled = node
                break
        
        if principled:
            # 復元テクスチャを適用
            for texture_type, texture_path in recovered_textures.items():
                if os.path.exists(texture_path):
                    # 新しいImage Textureノード作成
                    tex_node = nodes.new(type='ShaderNodeTexImage')
                    tex_node.image = bpy.data.images.load(texture_path)
                    
                    # 適切な入力に接続
                    if texture_type == 'metallicRoughness':
                        # Metallic/Roughnessテクスチャの場合、Separateノードも作成
                        separate_node = nodes.new(type='ShaderNodeSeparateRGB')
                        mat.node_tree.links.new(tex_node.outputs['Color'], separate_node.inputs['Image'])
                        mat.node_tree.links.new(separate_node.outputs['R'], principled.inputs['Metallic'])
                        mat.node_tree.links.new(separate_node.outputs['G'], principled.inputs['Roughness'])
                    
                    print(f"復元テクスチャ適用: {{texture_type}}")

# FBX出力
bpy.ops.export_scene.fbx(
    filepath="{output_path}",
    embed_textures=True,
    use_selection=False,
    global_scale=1.0
)

print("マテリアル復元完了")
'''
    
    def _define_target_material_structure(self, recovery_result: Dict) -> Dict:
        """目標マテリアル構造の定義"""
        return {
            'material_name': f'M_{self.model_name}_material',
            'nodes': {
                'principled_bsdf': {
                    'type': 'BSDF_PRINCIPLED',
                    'inputs': {
                        'Base Color': 'baseColor_texture',
                        'Normal': 'normal_texture',
                        'Metallic': 'metallic_channel',
                        'Roughness': 'roughness_channel'
                    }
                },
                'baseColor_texture': {
                    'type': 'TEX_IMAGE',
                    'image': f'{self.model_name}_baseColor.png'
                },
                'normal_texture': {
                    'type': 'TEX_IMAGE',
                    'image': f'{self.model_name}_normal.png'
                },
                'metallicRoughness_texture': {
                    'type': 'TEX_IMAGE',
                    'image': f'{self.model_name}_metallicRoughness.png'
                },
                'separate_rgb': {
                    'type': 'SEPARATE_RGB',
                    'input': 'metallicRoughness_texture',
                    'outputs': {
                        'R': 'metallic_channel',
                        'G': 'roughness_channel'
                    }
                }
            }
        }
    
    def _generate_reconstruction_script(self, input_fbx: str, target_structure: Dict) -> str:
        """マテリアル再構築スクリプト生成"""
        output_path = os.path.join(self.stage_dirs['stage4_reconstruction'], f"{self.model_name}_reconstructed.fbx")
        
        return f'''
import bpy

# FBX読み込み
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath="{input_fbx}")

# 目標構造
target_structure = {target_structure}

# 既存マテリアルの完全再構築
for mat in bpy.data.materials:
    if mat.use_nodes:
        # 既存ノードを全削除
        mat.node_tree.nodes.clear()
        
        # 新しいノード構造を構築
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        
        # Principled BSDFとMaterial Outputノードを作成
        principled = nodes.new(type='ShaderNodeBsdfPrincipled')
        output = nodes.new(type='ShaderNodeOutputMaterial')
        links.new(principled.outputs['BSDF'], output.inputs['Surface'])
        
        # テクスチャノードの作成と接続
        tex_nodes = {{}}
        
        # Base Colorテクスチャ
        if '{self.model_name}_baseColor.png' in [img.name for img in bpy.data.images]:
            base_tex = nodes.new(type='ShaderNodeTexImage')
            base_tex.image = bpy.data.images['{self.model_name}_baseColor.png']
            links.new(base_tex.outputs['Color'], principled.inputs['Base Color'])
            tex_nodes['baseColor'] = base_tex
        
        # Normalテクスチャ
        if '{self.model_name}_normal.png' in [img.name for img in bpy.data.images]:
            normal_tex = nodes.new(type='ShaderNodeTexImage')
            normal_tex.image = bpy.data.images['{self.model_name}_normal.png']
            normal_tex.image.colorspace_settings.name = 'Non-Color'
            
            normal_map = nodes.new(type='ShaderNodeNormalMap')
            links.new(normal_tex.outputs['Color'], normal_map.inputs['Color'])
            links.new(normal_map.outputs['Normal'], principled.inputs['Normal'])
            tex_nodes['normal'] = normal_tex
        
        # Metallic/Roughnessテクスチャ
        if '{self.model_name}_metallicRoughness.png' in [img.name for img in bpy.data.images]:
            mr_tex = nodes.new(type='ShaderNodeTexImage')
            mr_tex.image = bpy.data.images['{self.model_name}_metallicRoughness.png']
            mr_tex.image.colorspace_settings.name = 'Non-Color'
            
            separate = nodes.new(type='ShaderNodeSeparateRGB')
            links.new(mr_tex.outputs['Color'], separate.inputs['Image'])
            links.new(separate.outputs['R'], principled.inputs['Metallic'])
            links.new(separate.outputs['G'], principled.inputs['Roughness'])
            tex_nodes['metallicRoughness'] = mr_tex
        
        # ノード位置の調整
        principled.location = (0, 0)
        output.location = (300, 0)
        
        y_offset = 0
        for node in tex_nodes.values():
            node.location = (-400, y_offset)
            y_offset -= 300

# FBX出力
bpy.ops.export_scene.fbx(
    filepath="{output_path}",
    embed_textures=True,
    use_selection=False,
    global_scale=1.0
)

print("マテリアル再構築完了")
'''
    
    def _generate_optimization_script(self, input_fbx: str) -> str:
        """テクスチャ最適化スクリプト生成"""
        output_path = os.path.join(self.stage_dirs['stage5_optimization'], f"{self.model_name}_optimized.fbx")
        
        return f'''
import bpy

# FBX読み込み
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath="{input_fbx}")

# テクスチャ最適化
for img in bpy.data.images:
    if img.packed_file:
        # テクスチャ圧縮設定
        if hasattr(img, 'use_half_precision'):
            img.use_half_precision = True
        
        # カラースペース最適化
        if 'normal' in img.name.lower():
            img.colorspace_settings.name = 'Non-Color'
        elif 'metallic' in img.name.lower() or 'roughness' in img.name.lower():
            img.colorspace_settings.name = 'Non-Color'
        else:
            img.colorspace_settings.name = 'sRGB'

# 最適化されたFBX出力
bpy.ops.export_scene.fbx(
    filepath="{output_path}",
    embed_textures=True,
    use_selection=False,
    global_scale=1.0,
    mesh_smooth_type='FACE'
)

print("テクスチャ最適化完了")
'''
    
    def _generate_validation_script(self, input_fbx: str) -> str:
        """品質検証スクリプト生成"""
        output_path = os.path.join(self.stage_dirs['stage6_validation'], "quality_validation.json")
        
        return f'''
import bpy
import json

# FBX読み込み
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath="{input_fbx}")

validation_data = {{
    "total_objects": len([obj for obj in bpy.data.objects if obj.type == 'MESH']),
    "total_materials": len(bpy.data.materials),
    "total_images": len(bpy.data.images),
    "total_embedded_size_mb": 0,
    "materials_with_textures": 0,
    "unique_textures": set(),
    "texture_types": set()
}}

# テクスチャ分析
for img in bpy.data.images:
    if img.packed_file:
        validation_data["total_embedded_size_mb"] += len(img.packed_file.data) / (1024 * 1024)
        validation_data["unique_textures"].add(img.name)
        
        # テクスチャタイプ判定
        img_name = img.name.lower()
        if 'basecolor' in img_name or 'diffuse' in img_name:
            validation_data["texture_types"].add('baseColor')
        elif 'normal' in img_name:
            validation_data["texture_types"].add('normal')
        elif 'metallic' in img_name or 'roughness' in img_name:
            validation_data["texture_types"].add('metallicRoughness')

# マテリアル分析
for mat in bpy.data.materials:
    if mat.use_nodes:
        has_textures = any(node.type == 'TEX_IMAGE' for node in mat.node_tree.nodes)
        if has_textures:
            validation_data["materials_with_textures"] += 1

# セットをリストに変換（JSON serializable）
validation_data["unique_textures"] = list(validation_data["unique_textures"])
validation_data["texture_types"] = list(validation_data["texture_types"])

# 結果保存
with open("{output_path}", 'w', encoding='utf-8') as f:
    json.dump(validation_data, f, indent=2, ensure_ascii=False)

print("品質検証完了")
'''
    
    def _calculate_quality_score(self, validation_data: Dict, optimize_result: Dict) -> float:
        """品質スコア計算"""
        score = 0.0
        
        # テクスチャタイプカバレッジ (40%)
        expected_types = {'baseColor', 'normal', 'metallicRoughness'}
        actual_types = set(validation_data.get('texture_types', []))
        type_coverage = len(actual_types & expected_types) / len(expected_types)
        score += type_coverage * 0.4
        
        # ファイルサイズ適正性 (30%)
        file_size_mb = optimize_result.get('optimized_file_size_mb', 0)
        if 7.5 <= file_size_mb <= 10.0:
            size_score = 1.0
        elif file_size_mb > 10.0:
            size_score = max(0.5, 1.0 - (file_size_mb - 10.0) / 10.0)
        else:
            size_score = file_size_mb / 7.5
        score += size_score * 0.3
        
        # テクスチャ埋め込み成功率 (20%)
        embedded_mb = validation_data.get('total_embedded_size_mb', 0)
        if embedded_mb > 5.0:
            embed_score = 1.0
        else:
            embed_score = embedded_mb / 5.0
        score += embed_score * 0.2
        
        # マテリアル構造完全性 (10%)
        materials_with_textures = validation_data.get('materials_with_textures', 0)
        total_materials = validation_data.get('total_materials', 1)
        material_score = materials_with_textures / max(total_materials, 1)
        score += material_score * 0.1
        
        return min(score, 1.0)
    
    def _generate_final_export_script(self, input_fbx: str, output_path: str) -> str:
        """最終エクスポートスクリプト生成"""
        return f'''
import bpy

# FBX読み込み
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath="{input_fbx}")

# 最終FBX出力（最高品質設定）
bpy.ops.export_scene.fbx(
    filepath="{output_path}",
    embed_textures=True,
    use_selection=False,
    global_scale=1.0,
    apply_scale_options='FBX_SCALE_NONE',
    mesh_smooth_type='FACE',
    use_mesh_modifiers=True,
    use_armature_deform_only=True,
    add_leaf_bones=False
)

print("最終エクスポート完了")
'''
    
    def _execute_blender_script(self, script_content: str, script_name: str) -> Dict:
        """Blenderスクリプト実行"""
        try:
            if self.use_subprocess:
                # サブプロセスでBlender実行
                script_file = os.path.join(self.enhanced_dir, f"{script_name}.py")
                with open(script_file, 'w', encoding='utf-8') as f:
                    f.write(script_content)
                
                cmd = ['blender', '--background', '--python', script_file]
                result = subprocess.run(cmd, capture_output=True, text=True, cwd='/app')
                
                if result.returncode == 0:
                    return {'success': True, 'output': result.stdout}
                else:
                    return {'success': False, 'error': result.stderr}
            else:
                # 直接実行
                exec(script_content)
                return {'success': True}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _generate_final_quality_report(self, export_result: Dict) -> Dict:
        """最終品質レポート生成"""
        return {
            'method': 'Enhanced Safe Texture Restoration v2',
            'total_stages': self.total_stages,
            'completed_stages': self.current_stage,
            'final_fbx_path': export_result.get('final_fbx_path'),
            'final_file_size_mb': export_result.get('final_file_size_mb'),
            'quality_score': export_result.get('quality_score'),
            'quality_passed': export_result.get('quality_passed'),
            'deduplication_performed': export_result.get('deduplication_performed', False),
            'recovery_performed': export_result.get('recovery_performed', False),
            'processing_logs': self.processing_logs,
            'success': True
        }

if __name__ == "__main__":
    # テスト実行
    working_dir = "/app/pipeline_work"
    model_name = "bird_final_test"
    
    enhanced_restoration = EnhancedSafeTextureRestorationV2(
        working_dir=working_dir,
        model_name=model_name,
        use_subprocess=True
    )
    
    # テスト対象FBX
    test_fbx = "/app/pipeline_work/08_final_output/bird_final_test/bird_final_test_final_textured_rigged.fbx"
    
    if os.path.exists(test_fbx):
        success, final_fbx, quality_report = enhanced_restoration.execute_enhanced_restoration(test_fbx)
        
        print(f"\n=== Enhanced Restoration v2 結果 ===")
        print(f"成功: {success}")
        print(f"最終FBX: {final_fbx}")
        print(f"品質レポート: {json.dumps(quality_report, indent=2, ensure_ascii=False)}")
    else:
        print(f"テストFBXファイルが見つかりません: {test_fbx}")
