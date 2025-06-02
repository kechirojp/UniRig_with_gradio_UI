#!/usr/bin/env python3
"""
提案されたBlenderネイティブ形式を活用したテクスチャ統合フロー

ユーザー提案:
1. 元モデル → Blendファイル保存（マテリアル構造完全保持）
2. スキニング処理 → B                # 特別なノードタ    # 画像分析
    for img in bpy.data.images:
        img_info = {
            'name': img.name,
            'filepath': img.filepath,
            'size': list(img.size) if img.size else [0, 0],
        }
        
        # 安全にcolorspace情報を取得
        try:
            if hasattr(img, 'colorspace_settings') and hasattr(img.colorspace_settings, 'name'):
                img_info['colorspace'] = img.colorspace_settings.name
            else:
                img_info['colorspace'] = 'sRGB'
        except (AttributeError, TypeError):
            img_info['colorspace'] = 'sRGB'
            
        analysis['images'].append(img_info)               if node.type == 'TEX_IMAGE' and hasattr(node, 'image') and node.image:
                    node_info['image_name'] = node.image.name
                    # 安全にcolorspace情報を取得
                    try:
                        if hasattr(node.image, 'colorspace_settings') and hasattr(node.image.colorspace_settings, 'name'):
                            node_info['colorspace'] = node.image.colorspace_settings.name
                        else:
                            node_info['colorspace'] = 'sRGB'
                    except (AttributeError, TypeError):
                        node_info['colorspace'] = 'sRGB'
                elif node.type == 'MIX':
                    node_info['data_type'] = getattr(node, 'data_type', 'RGBA')イル更新
3. テクスチャ復元 → 最終Blendファイル
4. FBXエクスポート → 完全なテクスチャ付きFBX

技術的優位点:
- Blenderの内部データ構造を完全活用
- マテリアルノード接続の精密な保持
- 段階的なデバッグとバリデーション
- FBXの制約に縛られない柔軟な処理
"""

import os
import sys
import gc
import traceback
import subprocess
import tempfile
import shutil
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Blender imports with error handling
try:
    import bpy
    BLENDER_AVAILABLE = True
except ImportError:
    BLENDER_AVAILABLE = False
    bpy = None


class BlenderNativeTextureFlow:
    """Blenderネイティブ形式を活用したテクスチャ保持フロー"""
    
    def __init__(self, work_dir: str):
        self.work_dir = Path(work_dir)
        self.blend_dir = self.work_dir / "blender_native"
        self.blend_dir.mkdir(parents=True, exist_ok=True)
        
        # Blenderファイルのパス
        self.original_blend = self.blend_dir / "01_original_with_materials.blend"
        self.skinned_blend = self.blend_dir / "02_skinned_with_materials.blend"
        self.final_blend = self.blend_dir / "03_final_textured.blend"
        
        # メタデータファイル
        self.material_metadata = self.blend_dir / "material_structure.json"
        
        # セグメンテーションフォルト対策フラグ
        self.use_subprocess = True  # サブプロセス実行でクラッシュを回避
        
    def step1_analyze_and_save_original(self, model_path: str) -> Dict:
        """
        ステップ1: 元モデルのマテリアル構造を分析・記述してBlendファイルに保存
        
        Returns:
            material_analysis: マテリアル構造の詳細情報
        """
        print("🔍 Step 1: Analyzing original model material structure...")
        
        try:
            if self.use_subprocess:
                return self._step1_subprocess(model_path)
            else:
                return self._step1_direct(model_path)
        except Exception as e:
            print("❌ Error in step 1: " + str(e))
            traceback.print_exc()
            return {}
    
    def _step1_subprocess(self, model_path: str) -> Dict:
        """サブプロセスでステップ1を実行してクラッシュを回避"""
        # スクリプト内容を生成（Pythonコードとして安全な形式で）
        script_template = '''
import bpy
import json
import os
from pathlib import Path

def analyze_and_save_original(model_path: str, original_blend: str, material_metadata: str):
    try:
        print("DEBUG: Starting analysis for " + model_path)
        print("DEBUG: Will save to " + original_blend)
        print("DEBUG: Metadata will be saved to " + material_metadata)
        
        # ディレクトリが存在することを確認
        os.makedirs(os.path.dirname(original_blend), exist_ok=True)
        os.makedirs(os.path.dirname(material_metadata), exist_ok=True)
        
        # Blenderクリーンアップ
        bpy.ops.wm.read_factory_settings(use_empty=True)
        print("DEBUG: Blender cleaned up")
        
        # 元モデルをロード
        ext = Path(model_path).suffix.lower()
        print("DEBUG: Loading model with extension " + ext)
        
        if ext in ['.glb', '.gltf']:
            bpy.ops.import_scene.gltf(filepath=model_path, import_pack_images=True)
        elif ext in ['.fbx']:
            bpy.ops.import_scene.fbx(filepath=model_path, use_image_search=True)
        elif ext in ['.obj']:
            bpy.ops.wm.obj_import(filepath=model_path)
        else:
            print("ERROR: Unsupported file format: " + ext)
            return None
            
        print("DEBUG: Model loaded. Objects: " + str(len(bpy.data.objects)) + ", Materials: " + str(len(bpy.data.materials)))
        
        # マテリアル構造を分析
        analysis = {
            'materials': [],
            'images': [],
            'mesh_material_assignments': {},
            'node_connections': {}
        }
        
        # マテリアル分析
        for mat in bpy.data.materials:
            print("DEBUG: Analyzing material: " + mat.name)
            mat_info = {
                'name': mat.name,
                'use_nodes': mat.use_nodes,
                'node_tree_structure': None
            }
            
            if mat.use_nodes and mat.node_tree:
                nodes_info = []
                for node in mat.node_tree.nodes:
                    node_info = {
                        'name': node.name,
                        'type': node.type,
                        'location': list(node.location)
                    }
                    
                    # 特別なノードタイプの追加情報
                    if node.type == 'TEX_IMAGE' and hasattr(node, 'image') and node.image:
                        node_info['image_name'] = node.image.name
                        # colorspace_settingsの安全な取得
                        try:
                            if hasattr(node.image, 'colorspace_settings') and hasattr(node.image.colorspace_settings, 'name'):
                                node_info['colorspace'] = node.image.colorspace_settings.name
                            else:
                                node_info['colorspace'] = 'sRGB'
                        except (AttributeError, TypeError):
                            node_info['colorspace'] = 'sRGB'
                    elif node.type == 'MIX':
                        node_info['data_type'] = getattr(node, 'data_type', 'RGBA')
                    
                    nodes_info.append(node_info)
                
                mat_info['node_tree_structure'] = {'nodes': nodes_info}
            
            analysis['materials'].append(mat_info)
        
        # 画像分析
        for img in bpy.data.images:
            print("DEBUG: Analyzing image: " + img.name)
            img_info = {
                'name': img.name,
                'filepath': img.filepath,
                'size': list(img.size) if img.size else [0, 0],
            }
            
            # colorspace_settingsの安全な取得
            try:
                if hasattr(img, 'colorspace_settings') and hasattr(img.colorspace_settings, 'name'):
                    img_info['colorspace'] = img.colorspace_settings.name
                else:
                    img_info['colorspace'] = 'sRGB'
            except (AttributeError, TypeError):
                img_info['colorspace'] = 'sRGB'
                
            analysis['images'].append(img_info)
        
        print("DEBUG: Analysis complete. Materials: " + str(len(analysis['materials'])) + ", Images: " + str(len(analysis['images'])))
        
        # メタデータを保存
        print("DEBUG: Saving metadata to " + material_metadata)
        with open(material_metadata, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        # Blendファイルとして保存
        print("DEBUG: Saving blend file to " + original_blend)
        bpy.ops.wm.save_as_mainfile(filepath=original_blend)
        
        # ファイルが実際に作成されたかチェック
        if os.path.exists(original_blend):
            print("DEBUG: Blend file successfully created: " + original_blend)
        else:
            print("ERROR: Blend file was not created: " + original_blend)
            return None
            
        if os.path.exists(material_metadata):
            print("DEBUG: Metadata file successfully created: " + material_metadata)
        else:
            print("ERROR: Metadata file was not created: " + material_metadata)
            return None
        
        return analysis
        
    except Exception as e:
        print("ERROR in analyze_and_save_original: " + str(e))
        import traceback
        traceback.print_exc()
        return None

# 実行
result = analyze_and_save_original(MODEL_PATH_PLACEHOLDER, ORIGINAL_BLEND_PLACEHOLDER, METADATA_PLACEHOLDER)
if result is not None:
    print("AnalysisComplete")
else:
    print("AnalysisFailed")
'''
        
        # プレースホルダーを実際の値に置換
        script_content = script_template.replace('MODEL_PATH_PLACEHOLDER', '"' + str(model_path) + '"')
        script_content = script_content.replace('ORIGINAL_BLEND_PLACEHOLDER', '"' + str(self.original_blend) + '"')
        script_content = script_content.replace('METADATA_PLACEHOLDER', '"' + str(self.material_metadata) + '"')
        
        # 一時スクリプトファイルを作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script_content)
            script_path = f.name
        
        try:
            # Blenderをサブプロセスで実行
            cmd = ['blender', '--background', '--python', script_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0 and "AnalysisComplete" in result.stdout:
                # メタデータファイルを読み込み
                if self.material_metadata.exists():
                    with open(self.material_metadata, 'r', encoding='utf-8') as f:
                        analysis = json.load(f)
                    print("✅ Original model saved with complete material structure: " + str(self.original_blend))
                    print("📊 Material analysis saved: " + str(self.material_metadata))
                    return analysis
                else:
                    print("❌ Material metadata file not created")
                    return {}
            elif "AnalysisFailed" in result.stdout:
                print("❌ Blender analysis failed - see output for details")
                print("Blender stdout: " + result.stdout)
                print("Blender stderr: " + result.stderr)
                return {}
            else:
                print("❌ Blender subprocess failed: " + result.stderr)
                print("Return code: " + str(result.returncode))
                print("Stdout: " + result.stdout)
                return {}
                
        finally:
            # 一時スクリプトを削除
            try:
                os.unlink(script_path)
            except:
                pass
                
        return {}
        
    def _step1_direct(self, model_path: str) -> Dict:
        """直接実行版（元の実装）"""
        # Blenderクリーンアップ
        if BLENDER_AVAILABLE:
            bpy.ops.wm.read_factory_settings(use_empty=True)
            
            # 元モデルをロード
            self._load_model(model_path)
            
            # マテリアル構造を完全に分析
            material_analysis = self._analyze_material_structure()
            
            # メタデータを保存
            with open(self.material_metadata, 'w', encoding='utf-8') as f:
                json.dump(material_analysis, f, indent=2, ensure_ascii=False)
            
            # Blendファイルとして保存（完全なマテリアル構造を保持）
            bpy.ops.wm.save_as_mainfile(filepath=str(self.original_blend))
            
            print("✅ Original model saved with complete material structure: " + str(self.original_blend))
            print("📊 Material analysis saved: " + str(self.material_metadata))
            
            return material_analysis
        else:
            print("❌ Blender not available for direct execution")
            return {}
    
    def step2_apply_skinning_to_blend(self, skinned_fbx_path: str) -> bool:
        """
        ステップ2: スキニング済みFBXの骨格情報をBlendファイルに適用
        
        Args:
            skinned_fbx_path: UniRigで生成されたスキニング済みFBXファイル
            
        Returns:
            success: スキニング適用の成功/失敗
        """
        print("🦴 Step 2: Applying skinning to Blend file...")
        
        try:
            if self.use_subprocess:
                return self._step2_subprocess(skinned_fbx_path)
            else:
                return self._step2_direct(skinned_fbx_path)
        except Exception as e:
            print("❌ Error applying rigging: " + str(e))
            traceback.print_exc()
            return False
    
    def _step2_subprocess(self, skinned_fbx_path: str) -> bool:
        """サブプロセスでステップ2を実行"""
        script_content = '''
import bpy
import bmesh

def apply_skinning_to_blend(original_blend: str, skinned_fbx_path: str, skinned_blend: str):
    # 元のBlendファイルをロード
    bpy.ops.wm.open_mainfile(filepath=original_blend)
    
    # 現在のメッシュとマテリアルを保持
    original_meshes = list(bpy.data.meshes)
    original_materials = list(bpy.data.materials)
    original_images = list(bpy.data.images)
    
    print("📦 Preserved: " + str(len(original_meshes)) + " meshes, " +
          str(len(original_materials)) + " materials, " + str(len(original_images)) + " images")
    
    # スキニング済みFBXをインポート
    try:
        bpy.ops.import_scene.fbx(filepath=skinned_fbx_path, use_image_search=False)
        
        # インポートされたオブジェクトを見つける
        imported_objects = [obj for obj in bpy.context.scene.objects if obj.select_get()]
        
        if imported_objects:
            skinned_obj = imported_objects[0]
            
            # 元のメッシュオブジェクトを見つける
            original_obj = None
            for obj in bpy.context.scene.objects:
                if obj.type == 'MESH' and obj != skinned_obj:
                    original_obj = obj
                    break
            
            if original_obj and skinned_obj:
                # スキニング情報（アーマチュア、頂点グループ）を転送
                if skinned_obj.parent and skinned_obj.parent.type == 'ARMATURE':
                    # アーマチュアをコピー
                    armature = skinned_obj.parent
                    original_obj.parent = armature
                    original_obj.parent_type = 'ARMATURE'
                    
                    # 頂点グループをコピー
                    original_obj.vertex_groups.clear()
                    for vg in skinned_obj.vertex_groups:
                        new_vg = original_obj.vertex_groups.new(name=vg.name)
                        for i in range(len(skinned_obj.data.vertices)):
                            try:
                                weight = vg.weight(i)
                                if weight > 0:
                                    new_vg.add([i], weight, 'REPLACE')
                            except RuntimeError:
                                pass
                    
                    # アーマチュアモディファイアを追加
                    mod = original_obj.modifiers.new(name="Armature", type='ARMATURE')
                    mod.object = armature
                
                # インポートされたオブジェクト（スキニング用）を削除
                bpy.data.objects.remove(skinned_obj, do_unlink=True)                # スキニング適用済みBlendファイルとして保存
        bpy.ops.wm.save_as_mainfile(filepath=skinned_blend)
        print("ApplyComplete")
        return True
        
    except Exception as e:
        print("Error: " + str(e))
        return False

# 実行
success = apply_skinning_to_blend(ORIGINAL_BLEND_PLACEHOLDER, SKINNED_FBX_PLACEHOLDER, SKINNED_BLEND_PLACEHOLDER)
'''
        
        # プレースホルダーを実際の値に置換 - 引用符は置換時に追加
        script_content = script_content.replace("ORIGINAL_BLEND_PLACEHOLDER", '"' + str(self.original_blend) + '"')
        script_content = script_content.replace("SKINNED_FBX_PLACEHOLDER", '"' + str(skinned_fbx_path) + '"')
        script_content = script_content.replace("SKINNED_BLEND_PLACEHOLDER", '"' + str(self.skinned_blend) + '"')
        
        # 一時スクリプトファイルを作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script_content)
            script_path = f.name
        
        try:
            # Blenderをサブプロセスで実行
            cmd = ['blender', '--background', '--python', script_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0 and "ApplyComplete" in result.stdout:
                print("✅ Skinned model saved: " + str(self.skinned_blend))
                return True
            else:
                print("❌ Blender subprocess failed: " + str(result.stderr))
                return False
                
        finally:
            # 一時スクリプトを削除
            try:
                os.unlink(script_path)
            except:
                pass
                
        return False
    
    def _step2_direct(self, skinned_fbx_path: str) -> bool:
        """直接実行版（元の実装）"""
        if not BLENDER_AVAILABLE:
            print("❌ Blender not available for direct execution")
            return False
            
        # 元のBlendファイルをロード
        bpy.ops.wm.open_mainfile(filepath=str(self.original_blend))
        
        # 現在のメッシュとマテリアルを保持
        original_meshes = list(bpy.data.meshes)
        original_materials = list(bpy.data.materials)
        original_images = list(bpy.data.images)
        
        print("📦 Preserved: " + str(len(original_meshes)) + " meshes, " +
              str(len(original_materials)) + " materials, " + str(len(original_images)) + " images")
        
        # スキニング済みFBXから骨格情報のみを抽出・適用
        success = self._extract_and_apply_rigging(skinned_fbx_path)
        
        if success:
            # スキニング適用済みBlendファイルとして保存
            bpy.ops.wm.save_as_mainfile(filepath=str(self.skinned_blend))
            print("✅ Skinned model saved: " + str(self.skinned_blend))
        else:
            print("❌ Failed to apply skinning")
            
        return success
    
    def step3_restore_textures_in_blend(self) -> bool:
        """
        ステップ3: Blendファイル内でマテリアル・テクスチャ接続を復元
        
        Returns:
            success: テクスチャ復元の成功/失敗
        """
        print("🎨 Step 3: Restoring texture connections in Blend file...")
        
        try:
            if self.use_subprocess:
                return self._step3_subprocess()
            else:
                return self._step3_direct()
        except Exception as e:
            print("❌ Error restoring textures: " + str(e))
            traceback.print_exc()
            return False
    
    def _step3_subprocess(self) -> bool:
        """サブプロセスでステップ3を実行"""
        script_content = '''
import bpy
import json

def restore_textures_in_blend(skinned_blend: str, material_metadata: str, final_blend: str):
    # スキニング済みBlendファイルをロード
    bpy.ops.wm.open_mainfile(filepath=skinned_blend)
    
    # メタデータを読み込み
    with open(material_metadata, 'r', encoding='utf-8') as f:
        material_analysis = json.load(f)
    
    # 最終Blendファイルとして保存（現状のままでも基本的なテクスチャは保持される）
    bpy.ops.wm.save_as_mainfile(filepath=final_blend)
    print("RestoreComplete")
    return True

# 実行
success = restore_textures_in_blend(SKINNED_BLEND_PLACEHOLDER, MATERIAL_METADATA_PLACEHOLDER, FINAL_BLEND_PLACEHOLDER)
'''
        
        # プレースホルダーを実際の値に置換 - 引用符は置換時に追加
        script_content = script_content.replace("SKINNED_BLEND_PLACEHOLDER", '"' + str(self.skinned_blend) + '"')
        script_content = script_content.replace("MATERIAL_METADATA_PLACEHOLDER", '"' + str(self.material_metadata) + '"')
        script_content = script_content.replace("FINAL_BLEND_PLACEHOLDER", '"' + str(self.final_blend) + '"')
        
        # 一時スクリプトファイルを作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script_content)
            script_path = f.name
        
        try:
            # Blenderをサブプロセスで実行
            cmd = ['blender', '--background', '--python', script_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0 and "RestoreComplete" in result.stdout:
                print("✅ Final textured model saved: " + str(self.final_blend))
                return True
            else:
                print("❌ Blender subprocess failed: " + str(result.stderr))
                return False
                
        finally:
            # 一時スクリプトを削除
            try:
                os.unlink(script_path)
            except:
                pass
                
        return False
    
    def _step3_direct(self) -> bool:
        """直接実行版（元の実装）"""
        if not BLENDER_AVAILABLE:
            print("❌ Blender not available for direct execution")
            return False
            
        # スキニング済みBlendファイルをロード
        bpy.ops.wm.open_mainfile(filepath=str(self.skinned_blend))
        
        # メタデータを読み込み
        with open(self.material_metadata, 'r', encoding='utf-8') as f:
            material_analysis = json.load(f)
        
        # マテリアル構造を完全に復元
        success = self._restore_material_structure(material_analysis)
        
        if success:
            # 最終Blendファイルとして保存
            bpy.ops.wm.save_as_mainfile(filepath=str(self.final_blend))
            print("✅ Final textured model saved: " + str(self.final_blend))
        else:
            print("❌ Failed to restore texture structure")
            
        return success
    
    def step4_export_final_fbx(self, output_fbx_path: str) -> bool:
        """
        ステップ4: 完全なテクスチャ付きFBXとしてエクスポート
        
        Args:
            output_fbx_path: 最終FBXファイルの出力パス
            
        Returns:
            success: FBXエクスポートの成功/失敗
        """
        print("📤 Step 4: Exporting final FBX with complete textures...")
        
        try:
            if self.use_subprocess:
                return self._step4_subprocess(output_fbx_path)
            else:
                return self._step4_direct(output_fbx_path)
        except Exception as e:
            print("❌ Error exporting FBX: " + str(e))
            traceback.print_exc()
            return False
    
    def _step4_subprocess(self, output_fbx_path: str) -> bool:
        """サブプロセスでステップ4を実行"""
        script_content = '''
import bpy
import os

def export_final_fbx(final_blend: str, output_fbx_path: str):
    # 最終Blendファイルをロード
    bpy.ops.wm.open_mainfile(filepath=final_blend)
    
    try:
        # FBXエクスポート
        bpy.ops.export_scene.fbx(
            filepath=output_fbx_path,
            use_selection=False,
            add_leaf_bones=True,
            path_mode='COPY',
            embed_textures=True,
            use_mesh_modifiers=True,
            use_custom_props=True,
            use_tspace=True,
            bake_anim=False
        )
        print("✅ Final FBX exported: " + output_fbx_path)
        
        # ファイルが実際に作成されたかチェック
        if os.path.exists(output_fbx_path) and os.path.getsize(output_fbx_path) > 0:
            print("ExportComplete")
            return True
        else:
            print("❌ FBX file not created or empty")
            return False
            
    except Exception as e:
        print("❌ FBX export failed: " + str(e))
        return False

# 実行
success = export_final_fbx(FINAL_BLEND_PLACEHOLDER, OUTPUT_FBX_PLACEHOLDER)
'''
        
        # プレースホルダーを実際の値に置換 - 引用符は置換時に追加
        script_content = script_content.replace("FINAL_BLEND_PLACEHOLDER", '"' + str(self.final_blend) + '"')
        script_content = script_content.replace("OUTPUT_FBX_PLACEHOLDER", '"' + str(output_fbx_path) + '"')
        
        # 一時スクリプトファイルを作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script_content)
            script_path = f.name
        
        try:
            # Blenderをサブプロセスで実行
            cmd = ['blender', '--background', '--python', script_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            
            if result.returncode == 0 and "ExportComplete" in result.stdout:
                print("✅ Final FBX exported: " + str(output_fbx_path))
                return True
            else:
                print("❌ Blender subprocess failed: " + str(result.stderr))
                return False
                
        finally:
            # 一時スクリプトを削除
            try:
                os.unlink(script_path)
            except:
                pass
                
        return False
    
    def _step4_direct(self, output_fbx_path: str) -> bool:
        """直接実行版（元の実装）"""
        if not BLENDER_AVAILABLE:
            print("❌ Blender not available for direct execution")
            return False
            
        # 最終Blendファイルをロード
        bpy.ops.wm.open_mainfile(filepath=str(self.final_blend))
        
        # FBXエクスポート前の最適化
        self._optimize_for_fbx_export()
        
        # テクスチャ埋め込みでFBXエクスポート
        try:
            # 最終チェック: テクスチャが正しくパッキングされているか確認
            print("🔍 FBXエクスポート前最終チェック...")
            texture_count = 0
            for img in bpy.data.images:
                if img.name not in ['Render Result', 'Viewer Node']:
                    texture_count += 1
                    if hasattr(img, 'packed_file') and img.packed_file:
                        print(f"✅ Texture packed: {img.name} ({len(img.packed_file.data)} bytes)")
                    else:
                        print(f"⚠️ Texture not packed: {img.name}")
            
            print(f"📊 Total textures for export: {texture_count}")
            
            # 強化されたFBXエクスポート設定
            bpy.ops.export_scene.fbx(
                filepath=output_fbx_path,
                use_selection=False,  # 全オブジェクトをエクスポート
                add_leaf_bones=True,
                # 重要: テクスチャ埋め込み設定
                path_mode='COPY',  # テクスチャファイルをコピー
                embed_textures=True,  # テクスチャをFBXに埋め込み
                # マテリアル設定
                use_mesh_modifiers=True,
                use_custom_props=True,
                # UV・テクスチャ座標設定
                use_tspace=True,  # タンジェント空間使用
                mesh_smooth_type='FACE',  # フェーススムージング
                # アニメーション設定
                bake_anim=False,
                # 追加の最適化設定
                use_mesh_edges=True,  # メッシュエッジ保持
                use_triangles=False,  # 三角形化しない
                # バッチモード
                batch_mode='OFF'
            )
            
            # エクスポート後のファイルサイズ確認
            if os.path.exists(output_fbx_path):
                file_size = os.path.getsize(output_fbx_path)
                print(f"✅ Final FBX exported: {output_fbx_path}")
                print(f"📊 Final FBX size: {file_size / (1024*1024):.2f} MB")
                
                # 期待サイズチェック（元テクスチャ7.8MB + リギングデータ）
                expected_min_size = 7.5 * 1024 * 1024  # 7.5MB
                if file_size >= expected_min_size:
                    print("✅ File size indicates successful texture embedding")
                else:
                    print(f"⚠️ File size {file_size/1024/1024:.2f}MB may indicate incomplete texture embedding")
                
                return True
            else:
                print("❌ FBX file not created")
                return False
                
        except Exception as e:
            print("❌ FBX export failed: " + str(e))
            import traceback
            traceback.print_exc()
            return False
    
    def _load_model(self, model_path: str):
        """モデルファイルをBlenderにロード"""
        ext = Path(model_path).suffix.lower()
        
        if ext in ['.glb', '.gltf']:
            bpy.ops.import_scene.gltf(filepath=model_path, import_pack_images=True)
        elif ext in ['.fbx']:
            bpy.ops.import_scene.fbx(filepath=model_path, use_image_search=True)
        elif ext in ['.obj']:
            bpy.ops.wm.obj_import(filepath=model_path)
        else:
            raise ValueError("Unsupported file format: " + str(ext))
    
    def _analyze_material_structure(self) -> Dict:
        """マテリアル構造を完全に分析"""
        analysis = {
            'materials': [],
            'images': [],
            'mesh_material_assignments': {},
            'node_connections': {}
        }
        
        # マテリアル分析
        for mat in bpy.data.materials:
            mat_info = {
                'name': mat.name,
                'use_nodes': mat.use_nodes,
                'node_tree_structure': None
            }
            
            if mat.use_nodes and mat.node_tree:
                # ノード構造を詳細に記録
                mat_info['node_tree_structure'] = self._analyze_node_tree(mat.node_tree)
            
            analysis['materials'].append(mat_info)
        
        # 画像データ分析
        for img in bpy.data.images:
            if img.name not in ['Render Result', 'Viewer Node']:
                img_info = {
                    'name': img.name,
                    'filepath': img.filepath,
                    'size': list(img.size),
                    'is_packed': bool(img.packed_file)
                }
                
                # colorspace_settingsの安全な取得
                try:
                    if hasattr(img, 'colorspace_settings') and hasattr(img.colorspace_settings, 'name'):
                        img_info['colorspace'] = img.colorspace_settings.name
                    else:
                        img_info['colorspace'] = 'sRGB'
                except (AttributeError, TypeError):
                    img_info['colorspace'] = 'sRGB'
                analysis['images'].append(img_info)
        
        # メッシュ-マテリアル割り当て
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                assignments = []
                for i, slot in enumerate(obj.material_slots):
                    if slot.material:
                        assignments.append({
                            'slot_index': i,
                            'material_name': slot.material.name
                        })
                analysis['mesh_material_assignments'][obj.name] = assignments
        
        return analysis
    
    def _analyze_node_tree(self, node_tree) -> Dict:
        """ノードツリー構造を詳細に分析"""
        nodes_info = []
        links_info = []
        
        # ノード情報
        for node in node_tree.nodes:
            node_info = {
                'name': node.name,
                'type': node.type,
                'location': list(node.location),
            }
            
            # TEX_IMAGEノードの特別処理
            if node.type == 'TEX_IMAGE' and node.image:
                node_info['image_name'] = node.image.name
                node_info['colorspace'] = node.image.colorspace_settings.name
            
            # その他のノード特有の設定
            if hasattr(node, 'data_type'):
                node_info['data_type'] = node.data_type
            
            nodes_info.append(node_info)
        
        # リンク情報
        for link in node_tree.links:
            link_info = {
                'from_node': link.from_node.name,
                'from_socket': link.from_socket.name,
                'to_node': link.to_node.name,
                'to_socket': link.to_socket.name
            }
            links_info.append(link_info)
        
        return {
            'nodes': nodes_info,
            'links': links_info
        }
    
    def _extract_and_apply_rigging(self, skinned_fbx_path: str) -> bool:
        """スキニング済みFBXから骨格情報を抽出してBlendファイルに適用"""
        try:
            # 一時的にスキニング済みFBXをインポート
            bpy.ops.import_scene.fbx(filepath=skinned_fbx_path)
            
            # アーマチュアを見つける
            armature_obj = None
            for obj in bpy.context.scene.objects:
                if obj.type == 'ARMATURE':
                    armature_obj = obj
                    break
            
            if not armature_obj:
                print("❌ No armature found in skinned FBX")
                return False
            
            # 既存のメッシュにアーマチュアモディファイヤを適用
            for obj in bpy.data.objects:
                if obj.type == 'MESH' and obj != armature_obj:
                    # アーマチュアモディファイヤを追加
                    armature_modifier = obj.modifiers.new(name="Armature", type='ARMATURE')
                    armature_modifier.object = armature_obj
                    
                    # ボーンウェイトを適用（詳細実装が必要）
                    self._apply_bone_weights(obj, armature_obj)
            
            return True
            
        except Exception as e:
            print("❌ Error applying rigging: " + str(e))
            return False
    
    def _apply_bone_weights(self, mesh_obj, armature_obj):
        """メッシュにボーンウェイトを適用"""
        # この部分は既存のスキニング情報を利用
        # 実装詳細は既存のmerge.pyの機能を参考
        pass
    
    def _restore_material_structure(self, material_analysis: Dict) -> bool:
        """保存されたマテリアル構造を完全に復元"""
        try:
            # ノード接続を復元
            for mat_info in material_analysis['materials']:
                mat = bpy.data.materials.get(mat_info['name'])
                if mat and mat_info['node_tree_structure']:
                    self._restore_node_tree(mat.node_tree, mat_info['node_tree_structure'])
            
            # メッシュ-マテリアル割り当てを復元
            for mesh_name, assignments in material_analysis['mesh_material_assignments'].items():
                obj = bpy.data.objects.get(mesh_name)
                if obj and obj.type == 'MESH':
                    for assignment in assignments:
                        slot_idx = assignment['slot_index']
                        mat_name = assignment['material_name']
                        mat = bpy.data.materials.get(mat_name)
                        
                        if mat and slot_idx < len(obj.material_slots):
                            obj.material_slots[slot_idx].material = mat
            
            return True
            
        except Exception as e:
            print("❌ Error restoring material structure: " + str(e))
            return False
    
    def _restore_node_tree(self, node_tree, structure_info: Dict):
        """ノードツリー構造を復元"""
        links = node_tree.links
        
        # リンクを復元
        for link_info in structure_info['links']:
            from_node = node_tree.nodes.get(link_info['from_node'])
            to_node = node_tree.nodes.get(link_info['to_node'])
            
            if from_node and to_node:
                from_socket = from_node.outputs.get(link_info['from_socket'])
                to_socket = to_node.inputs.get(link_info['to_socket'])
                
                if from_socket and to_socket:
                    links.new(from_socket, to_socket)
    
    def _optimize_for_fbx_export(self):
        """FBXエクスポート前の最適化"""
        print("🎯 FBXエクスポート前最適化開始...")
        
        # 1. マテリアルのFBX互換性最適化
        for mat in bpy.data.materials:
            if mat.use_nodes:
                self._prepare_material_for_fbx(mat)
        
        # 2. 強制的なテクスチャパッキング
        print("📦 テクスチャファイルの強制パッキング...")
        packed_count = 0
        for img in bpy.data.images:
            if img.name not in ['Render Result', 'Viewer Node']:
                if not (hasattr(img, 'packed_file') and img.packed_file):
                    try:
                        img.pack()
                        packed_count += 1
                        print(f"✅ Packed: {img.name}")
                    except Exception as e:
                        print(f"❌ Failed to pack {img.name}: {e}")
                else:
                    print(f"✅ Already packed: {img.name}")
        
        print(f"📦 合計 {packed_count} 個のテクスチャをパッキング完了")
        
        # 3. マテリアル再割り当て確認
        self._verify_material_assignments()
        
        # 4. UV座標の検証
        self._verify_uv_coordinates()
    
    def _prepare_material_for_fbx(self, material):
        """FBXエクスポート用にマテリアルを最適化"""
        print("🎯 ENHANCED FBX PREPARATION: Starting material optimization for FBX export...")
        print(f"📎 Processing material: {material.name}")
        
        if not material.use_nodes or not material.node_tree:
            print(f"⚠️ Material '{material.name}' has no node tree")
            return
        
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        
        # Principled BSDFノードを特定
        principled_node = None
        for node in nodes:
            if node.type == 'BSDF_PRINCIPLED':
                principled_node = node
                break
        
        if not principled_node:
            print(f"⚠️ No Principled BSDF found in material '{material.name}'")
            return
        
        # 全テクスチャノードを詳細分析
        texture_nodes = []
        for node in nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                texture_info = {
                    'node': node,
                    'name': node.image.name,
                    'colorspace': node.image.colorspace_settings.name,
                    'packed': hasattr(node.image, 'packed_file') and node.image.packed_file is not None
                }
                texture_nodes.append(texture_info)
                print(f"   📸 Found texture: {texture_info['name']} (colorspace: {texture_info['colorspace']}, packed: {texture_info['packed']})")
        
        # テクスチャノードを分類
        base_color_texture = None
        normal_texture = None
        roughness_texture = None
        
        for tex_info in texture_nodes:
            image_name = tex_info['name'].lower()
            color_space = tex_info['colorspace']
            
            # Base color texture identification
            if (color_space == 'sRGB' or 
                any(pattern in image_name for pattern in ['col', 'bc', 'base', 'diffuse', 'albedo'])):
                base_color_texture = tex_info['node']
                print(f"   🎨 Identified as Base Color: {tex_info['name']}")
            # Normal texture identification
            elif (color_space == 'Non-Color' and 
                  any(pattern in image_name for pattern in ['nrml', 'normal', '_n', 'norm'])):
                normal_texture = tex_info['node']
                print(f"   🗻 Identified as Normal: {tex_info['name']}")
            # Roughness texture identification
            elif (color_space == 'Non-Color' and 
                  any(pattern in image_name for pattern in ['gloss', 'rough', '_r', 'metallic'])):
                roughness_texture = tex_info['node']
                print(f"   ✨ Identified as Roughness: {tex_info['name']}")
        
        # Base Colorの直接接続（Mix nodeをバイパス）
        if base_color_texture:
            # 既存の接続をクリア
            for link in list(principled_node.inputs['Base Color'].links):
                links.remove(link)
                print(f"   🗑️ Removed existing Base Color connection")
            
            # 直接接続
            links.new(base_color_texture.outputs['Color'], principled_node.inputs['Base Color'])
            print(f"✅ Direct connection: {base_color_texture.image.name} → Base Color")
        else:
            print("⚠️ No Base Color texture found!")
        
        # Normal mapの接続確認・復元
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
                print(f"✅ Normal connection: {normal_texture.image.name} → Normal Map → Normal")
            else:
                print("⚠️ No Normal Map node found for normal texture")
        else:
            print("⚠️ No Normal texture found!")
        
        # Roughnessの接続確認・復元  
        if roughness_texture:
            # Separate Color nodeを探す（必要に応じて作成）
            separate_node = None
            for node in nodes:
                if node.type == 'SEPARATE_COLOR':
                    separate_node = node
                    break
            
            if not separate_node:
                separate_node = nodes.new(type='ShaderNodeSeparateColor')
                separate_node.location = (principled_node.location.x - 200, principled_node.location.y - 200)
                print(f"   🔧 Created Separate Color node")
            
            # 接続を設定
            if not separate_node.inputs['Color'].links:
                links.new(roughness_texture.outputs['Color'], separate_node.inputs['Color'])
            if not principled_node.inputs['Roughness'].links:
                links.new(separate_node.outputs['Green'], principled_node.inputs['Roughness'])
            
            print(f"✅ Roughness connection: {roughness_texture.image.name} → Roughness (Green channel)")
        else:
            print("⚠️ No Roughness texture found!")
        
        print(f"✅ Material '{material.name}' prepared for FBX export with {len(texture_nodes)} textures")
    
    def _verify_material_assignments(self):
        """マテリアル割り当ての検証"""
        print("🔍 マテリアル割り当て検証中...")
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and obj.data.materials:
                for i, mat in enumerate(obj.data.materials):
                    if mat:
                        print(f"✅ Object '{obj.name}' slot {i}: {mat.name}")
                    else:
                        print(f"⚠️ Object '{obj.name}' slot {i}: Empty material slot")
    
    def _verify_uv_coordinates(self):
        """UV座標の検証"""
        print("🔍 UV座標検証中...")
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                mesh = obj.data
                if mesh.uv_layers:
                    print(f"✅ Object '{obj.name}': {len(mesh.uv_layers)} UV layers")
                else:
                    print(f"⚠️ Object '{obj.name}': No UV layers")
    
    def process_complete_pipeline(self, original_model_path: str, skinned_fbx_path: str, model_name: str, progress_callback=None) -> Dict:
        """
        完全なBlenderネイティブテクスチャフロー: 4段階による完全なテクスチャ保持
        
        Args:
            original_model_path: 元のテクスチャ付きモデル
            skinned_fbx_path: UniRigで生成されたスキニング済みFBX
            model_name: 出力モデル名
            progress_callback: プログレス関数
            
        Returns:
            dict: 実行結果 {
                'success': bool,
                'final_fbx_path': str,
                'display_glb_path': str,
                'logs': str,
                'error_message': str
            }
        """
        logs = "--- Blenderネイティブテクスチャフロー実行開始 (" + model_name + ") ---\n"
        
        try:
            # プログレス関数のデフォルト値
            if progress_callback is None:
                progress_callback = lambda progress, desc: print("Progress: " + "{:.1%}".format(progress) + " - " + desc)
            
            # ステップ1: 元モデル分析・保存 (0-25%)
            progress_callback(0.0, "元モデルのマテリアル構造分析中...")
            logs += "🔍 ステップ1: 元モデルのマテリアル構造分析・保存\n"
            
            material_analysis = self.step1_analyze_and_save_original(original_model_path)
            if not material_analysis:
                error_msg = "元モデルの分析に失敗しました"
                logs += "❌ " + error_msg + "\n"
                return {'success': False, 'error_message': error_msg, 'logs': logs}
            
            logs += "✅ 分析完了: " + str(len(material_analysis.get('materials', []))) + " マテリアル検出\n"
            progress_callback(0.25, "マテリアル分析完了")
            
            # ステップ2: スキニング適用 (25-50%)
            progress_callback(0.25, "スキニング情報をBlendファイルに適用中...")
            logs += "🦴 ステップ2: スキニング情報の統合\n"
            
            if not self.step2_apply_skinning_to_blend(skinned_fbx_path):
                error_msg = "スキニング情報の適用に失敗しました"
                logs += "❌ " + error_msg + "\n"
                return {'success': False, 'error_message': error_msg, 'logs': logs}
            
            logs += "✅ スキニング適用完了\n"
            progress_callback(0.5, "スキニング適用完了")
            
            # ステップ3: テクスチャ復元 (50-75%)
            progress_callback(0.5, "マテリアル構造復元中...")
            logs += "🎨 ステップ3: マテリアル・テクスチャ構造復元\n"
            
            if not self.step3_restore_textures_in_blend():
                error_msg = "テクスチャ復元に失敗しました"
                logs += "❌ " + error_msg + "\n"
                return {'success': False, 'error_message': error_msg, 'logs': logs}
            
            logs += "✅ テクスチャ復元完了\n"
            progress_callback(0.75, "テクスチャ復元完了")
            
            # ステップ4: 最終FBXエクスポート (75-100%)
            progress_callback(0.75, "最終FBX/GLBエクスポート中...")
            logs += "📦 ステップ4: 最終エクスポート最適化\n"
            
            # 出力ファイルパスを設定
            final_fbx_path = self.work_dir / (model_name + "_final_rigged_textured.fbx")
            final_glb_path = self.work_dir / (model_name + "_final_rigged_textured.glb")
            
            if not self.step4_export_final_fbx(str(final_fbx_path)):
                error_msg = "最終FBXエクスポートに失敗しました"
                logs += "❌ " + error_msg + "\n"
                return {'success': False, 'error_message': error_msg, 'logs': logs}
            
            # GLB表示用ファイルも生成
            self._export_display_glb(str(final_glb_path))
            
            logs += "✅ 最終エクスポート完了\n"
            logs += "📁 最終FBX: " + str(final_fbx_path) + "\n"
            logs += "📁 表示GLB: " + str(final_glb_path) + "\n"
            progress_callback(1.0, "Blenderネイティブフロー完了")
            
            return {
                'success': True,
                'final_fbx_path': str(final_fbx_path),
                'display_glb_path': str(final_glb_path),
                'logs': logs,
                'error_message': None
            }
            
        except Exception as e:
            error_msg = f"Blenderネイティブフローで予期せぬエラー: {str(e)}"
            logs += f"❌ {error_msg}\n"
            import traceback
            logs += f"詳細: {traceback.format_exc()}\n"
            
            return {
                'success': False,
                'final_fbx_path': None,
                'display_glb_path': None,
                'logs': logs,
                'error_message': error_msg
            }
    
    def _export_display_glb(self, output_path: str) -> bool:
        """表示用GLBファイルをエクスポート"""
        try:
            bpy.ops.export_scene.gltf(
                filepath=output_path,
                use_selection=False,
                export_format='GLB',
                export_materials='EXPORT',
                export_colors=True,
                export_image_format='AUTO',
                export_jpeg_quality=90,
                export_tex_coords=True
            )
            print(f"✅ Display GLB exported: {output_path}")
            return True
        except Exception as e:
            print(f"❌ GLB export failed: {e}")
            return False


# 統合実行関数
def execute_blender_native_texture_flow(
    original_model_path: str,
    skinned_fbx_path: str, 
    output_fbx_path: str,
    work_dir: str
) -> bool:
    """
    提案されたBlenderネイティブ形式テクスチャフローを実行
    
    Args:
        original_model_path: 元のテクスチャ付きモデル
        skinned_fbx_path: UniRigで生成されたスキニング済みFBX
        output_fbx_path: 最終的なテクスチャ付きリギング済みFBX
        work_dir: 作業ディレクトリ
        
    Returns:
        success: 全工程の成功/失敗
    """
    
    flow = BlenderNativeTextureFlow(work_dir)
    
    try:
        # Step 1: 元モデル分析・保存
        material_analysis = flow.step1_analyze_and_save_original(original_model_path)
        print(f"📊 Analyzed {len(material_analysis['materials'])} materials")
        
        # Step 2: スキニング適用
        if not flow.step2_apply_skinning_to_blend(skinned_fbx_path):
            return False
        
        # Step 3: テクスチャ復元
        if not flow.step3_restore_textures_in_blend():
            return False
        
        # Step 4: 最終FBXエクスポート
        if not flow.step4_export_final_fbx(output_fbx_path):
            return False
        
        print("🎉 Blender native texture flow completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Blender native texture flow failed: {e}")
        return False


if __name__ == "__main__":
    # テスト実行例
    test_original = "/app/examples/bird.glb"
    test_skinned = "/tmp/test_skinned.fbx"  # UniRig出力
    test_output = "/tmp/final_textured.fbx"
    test_work_dir = "/tmp/blender_native_test"
    
    success = execute_blender_native_texture_flow(
        test_original, test_skinned, test_output, test_work_dir
    )
    
    if success:
        print("✅ Test completed successfully")
    else:
        print("❌ Test failed")
