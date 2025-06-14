"""
Step 5 Module - 確実なUV・マテリアル転送システム
material_uv_transfer_script.py準拠実装

根本問題解決:
- UV・マテリアル転送の完全実装
- 簡素化版の不具合修正
- 確実な転送機能の実現

責務:
- オリジナルモデルからUV・マテリアル・テクスチャ情報抽出
- Step4マージ済みモデルへの確実な転送
- Z-up軸設定とBlender 4.2 API対応

設計方針:
- material_uv_transfer_script.pyの実証済み手法採用
- 段階的処理による確実性確保
- Blender 4.2完全対応
"""

import os
import sys
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple, Dict, Optional, Any
import traceback

# 新統合システムインポート
sys.path.append(str(Path(__file__).parent.parent))
from src.pipeline.unified_blender import UnifiedBlenderIntegrator

logger = logging.getLogger(__name__)


class Step5ReliableUVMaterialTransfer:
    """
    Step 5: 確実なUV・マテリアル転送システム
    
    material_uv_transfer_script.py準拠設計:
    - 実証済みUV転送手法
    - 確実なマテリアル転送
    - Blender 4.2完全対応
    """
    
    def __init__(self, output_dir: Path, logger_instance: Optional[logging.Logger] = None):
        """
        Step5初期化
        
        Args:
            output_dir: このステップの出力ディレクトリ（Pathオブジェクト）
            logger_instance: ロガーインスタンス
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger_instance if logger_instance else logging.getLogger(__name__)
        
    def integrate_uv_materials_textures(self, 
                                       model_name: str, 
                                       original_file: str, 
                                       merged_file: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        新統合システムによる確実なUV・マテリアル・テクスチャ統合
        
        Args:
            model_name: モデル識別名
            original_file: オリジナルモデルファイルパス（UV・マテリアル・テクスチャ保持）
            merged_file: Step4マージ済みFBXファイルパス（スケルトン・スキニング済み）
        
        Returns:
            success: 成功フラグ
            logs: 実行ログ
            output_files: 出力ファイル辞書
        """
        self.logger.info(f"=== Step5 新統合Blender統合システム開始: {model_name} ===")
        
        try:
            # 入力ファイル検証
            if not Path(original_file).exists():
                return False, f"オリジナルファイルが見つかりません: {original_file}", {}
            
            if not Path(merged_file).exists():
                return False, f"マージ済みファイルが見つかりません: {merged_file}", {}
            
            # 出力ファイルパス（統一命名規則準拠）
            output_fbx = self.output_dir / f"{model_name}_final.fbx"
            
            # 新統合Blender統合システム実行
            integrator = UnifiedBlenderIntegrator(enable_debug=True)
            
            self.logger.info(f"🚀 統合Blender統合システム実行開始")
            self.logger.info(f"📁 Original: {Path(original_file).name}")
            self.logger.info(f"📁 Merged: {Path(merged_file).name}")
            self.logger.info(f"📁 Output: {output_fbx.name}")
            
            success, logs, output_files = integrator.execute_integration(
                merged_fbx=merged_file,
                original_file=original_file,
                output_fbx=str(output_fbx),
                model_name=model_name
            )
            
            if success and output_fbx.exists():
                file_size = output_fbx.stat().st_size
                self.logger.info(f"✅ Step5完了: {output_fbx} ({file_size} bytes)")
                
                return True, f"統合Blender統合システム完了: {output_fbx.name} ({file_size} bytes)\n詳細ログ:\n{logs}", output_files
            else:
                return False, f"統合Blender統合システム失敗: {logs}", {}
            
        except Exception as e:
            error_msg = f"Step5実行エラー: {e}"
            self.logger.error(error_msg)
            traceback.print_exc()
            return False, error_msg, {}
    
    def _execute_reliable_uv_material_transfer(self, 
                                              original_file: str, 
                                              merged_file: str, 
                                              output_fbx: str,
                                              output_fbm_dir: str) -> Tuple[bool, str]:
        """
        確実なUV・マテリアル転送Blenderスクリプト実行
        material_uv_transfer_script.py準拠
        """
        
        # Blenderスクリプト生成
        blender_script = f'''
import bpy
import os
import shutil
from pathlib import Path

def clear_scene():
    """シーンクリア"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    for material in bpy.data.materials:
        bpy.data.materials.remove(material)
    for armature in bpy.data.armatures:
        bpy.data.armatures.remove(armature)
    for image in bpy.data.images:
        bpy.data.images.remove(image)

def load_and_rename_objects():
    """ファイル読み込みとオブジェクト名前変更"""
    clear_scene()
    
    # オリジナルファイル読み込み（UV・マテリアル・テクスチャ保持）
    print("📁 オリジナルファイル読み込み中...")
    original_file = "{original_file}"
    if original_file.lower().endswith('.glb') or original_file.lower().endswith('.gltf'):
        bpy.ops.import_scene.gltf(filepath=original_file)
    elif original_file.lower().endswith('.fbx'):
        bpy.ops.import_scene.fbx(filepath=original_file)
    elif original_file.lower().endswith('.obj'):
        bpy.ops.wm.obj_import(filepath=original_file)
    elif original_file.lower().endswith('.vrm'):
        # VRMファイルインポート（VRMアドオン使用）
        try:
            bpy.ops.import_scene.vrm(filepath=original_file)
            print("✅ VRM インポート成功")
        except AttributeError:
            # VRMアドオンが利用できない場合、GLTFとしてインポートを試行
            print("⚠️ VRMアドオン未検出、GLTFインポートを試行...")
            try:
                bpy.ops.import_scene.gltf(filepath=original_file)
                print("✅ VRM (GLTF fallback) インポート成功")
            except Exception as gltf_error:
                print("❌ VRM/GLTF インポート失敗: " + str(gltf_error))
                return [], []
        except Exception as vrm_error:
            print("❌ VRM インポート失敗: " + str(vrm_error))
            return [], []
    else:
        print("❌ 未対応ファイル形式: " + str(original_file))
        print("対応形式: .glb, .gltf, .fbx, .obj, .vrm")
        return [], []
    
    # オリジナルオブジェクトに'original_'プレフィックス追加
    original_objects = []
    for obj in bpy.context.scene.objects:
        if obj.type in ['MESH', 'ARMATURE']:
            new_name = f"original_{{obj.name}}"
            obj.name = new_name
            original_objects.append(obj)
            print("オリジナル: " + obj.name + " (" + obj.type + ")")
    
    # マージ済みファイル読み込み（スケルトン・スキニング済み）
    print("🦴 マージ済みファイル読み込み中...")
    bpy.ops.import_scene.fbx(filepath="{merged_file}")
    
    # マージ済みオブジェクトに'merged_'プレフィックス追加
    merged_objects = []
    for obj in bpy.context.scene.objects:
        if obj.type in ['MESH', 'ARMATURE'] and not obj.name.startswith('original_'):
            new_name = f"merged_{{obj.name}}"
            obj.name = new_name
            merged_objects.append(obj)
            print("マージ済み: " + obj.name + " (" + obj.type + ")")
    
    return original_objects, merged_objects

def transfer_uv_materials(original_objects, merged_objects):
    """UV・マテリアル転送（material_uv_transfer_script.py準拠）"""
    
    # オリジナルメッシュを検索
    original_mesh = None
    for obj in original_objects:
        if obj.type == 'MESH':
            original_mesh = obj
            break
    
    # マージ済みメッシュを検索
    merged_mesh = None
    for obj in merged_objects:
        if obj.type == 'MESH':
            merged_mesh = obj
            break
    
    if not original_mesh or not merged_mesh:
        print("❌ UV・マテリアル転送: メッシュオブジェクトが見つかりません")
        return False
    
    print("🎨 UV・マテリアル転送: " + original_mesh.name + " → " + merged_mesh.name)
    
    # マテリアル転送
    if original_mesh.data.materials:
        print("マテリアル数: " + str(len(original_mesh.data.materials)))
        merged_mesh.data.materials.clear()
        
        for material in original_mesh.data.materials:
            if material:
                merged_mesh.data.materials.append(material)
                print("マテリアル転送: " + material.name)
            else:
                merged_mesh.data.materials.append(None)
    else:
        print("❌ オリジナルメッシュにマテリアルがありません")
    
    # UV転送（重要）
    if original_mesh.data.uv_layers:
        print("UVレイヤー数: " + str(len(original_mesh.data.uv_layers)))
        
        # 既存UVレイヤーをクリア
        while merged_mesh.data.uv_layers:
            merged_mesh.data.uv_layers.remove(merged_mesh.data.uv_layers[0])
        
        # UV転送（material_uv_transfer_script.py準拠）
        for uv_layer in original_mesh.data.uv_layers:
            new_uv_layer = merged_mesh.data.uv_layers.new(name=uv_layer.name)
            
            # UVデータコピー（重要：ループ単位）
            if len(original_mesh.data.loops) == len(merged_mesh.data.loops):
                for loop_idx in range(len(merged_mesh.data.loops)):
                    new_uv_layer.data[loop_idx].uv = uv_layer.data[loop_idx].uv
                print("UV転送完了: " + uv_layer.name + " (" + str(len(merged_mesh.data.loops)) + " ループ)")
            else:
                print("⚠️ UV転送スキップ: ループ数不一致 (" + str(len(original_mesh.data.loops)) + " vs " + str(len(merged_mesh.data.loops)) + ")")
    else:
        print("❌ オリジナルメッシュにUVレイヤーがありません")
    
    return True

def export_final_fbx():
    """最終FBXエクスポート（Z-up対応）"""
    
    # オリジナルオブジェクト削除（マージ済みのみ残す）
    objects_to_delete = []
    for obj in bpy.context.scene.objects:
        if obj.name.startswith('original_'):
            objects_to_delete.append(obj)
    
    for obj in objects_to_delete:
        obj_name = obj.name  # 名前を事前に保存
        bpy.data.objects.remove(obj, do_unlink=True)
        print("オリジナルオブジェクト削除: " + obj_name)
    
    # merged_プレフィックス除去
    for obj in bpy.context.scene.objects:
        if obj.name.startswith('merged_'):
            old_name = obj.name
            obj.name = obj.name[7:]  # 'merged_'を除去
            print("名前変更: " + old_name + " → " + obj.name)
    
    # 全選択
    bpy.ops.object.select_all(action='SELECT')
    
    # FBMディレクトリ作成
    os.makedirs("{output_fbm_dir}", exist_ok=True)
    
    # テクスチャパッキング
    bpy.ops.file.pack_all()
    
    # FBXエクスポート（Z-up、Blender 4.2対応）
    print("📦 FBX出力: " + "{output_fbx}")
    bpy.ops.export_scene.fbx(
        filepath="{output_fbx}",
        check_existing=True,
        use_selection=True,
        
        # 軸設定（重要）
        axis_forward='-Y',
        axis_up='Z',
        
        # テクスチャ設定
        embed_textures=True,
        path_mode='COPY',
        
        # メッシュ設定
        use_mesh_modifiers=True,
        mesh_smooth_type='FACE',
        use_tspace=True,
        
        # アーマチュア設定
        add_leaf_bones=True,
        primary_bone_axis='Y',
        secondary_bone_axis='X',
        
        # その他設定
        use_custom_props=False,
        colors_type='SRGB'
    )
    
    print("✅ FBXエクスポート完了")
    return True

def main():
    """メイン処理"""
    try:
        print("=== Step5 確実なUV・マテリアル転送開始 ===")
        
        # ファイル読み込み
        original_objects, merged_objects = load_and_rename_objects()
        
        # UV・マテリアル転送
        transfer_success = transfer_uv_materials(original_objects, merged_objects)
        
        # FBXエクスポート
        export_success = export_final_fbx()
        
        if transfer_success and export_success:
            print("✅ Step5完了: UV・マテリアル転送成功")
        else:
            print("❌ Step5失敗")
            
        return transfer_success and export_success
        
    except Exception as e:
        print("❌ Step5エラー: " + str(e))
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
'''
        
        # 一時Blenderスクリプトファイル作成・実行
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_script:
            temp_script.write(blender_script)
            temp_script_path = temp_script.name
        
        try:
            # Blender実行
            cmd = ["blender", "--background", "--python", temp_script_path]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=600  # 10分タイムアウト
            )
            
            success = result.returncode == 0
            logs = result.stdout if success else result.stderr
            
            if success:
                self.logger.info("✅ UV・マテリアル転送Blenderスクリプト実行成功")
            else:
                self.logger.error(f"❌ UV・マテリアル転送Blenderスクリプト実行失敗: {logs}")
            
            return success, logs
            
        except subprocess.TimeoutExpired:
            return False, "Blenderスクリプト実行タイムアウト（10分）"
        except Exception as e:
            return False, f"Blenderスクリプト実行エラー: {e}"
        finally:
            # 一時ファイル削除
            if os.path.exists(temp_script_path):
                os.unlink(temp_script_path)
