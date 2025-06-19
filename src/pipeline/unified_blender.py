#!/usr/bin/env python3
"""
UniRig統合Blender統合システム - クロスプラットフォーム対応

本モジュールは以下を実現します：
1. Blenderスクリプトの安全な実行
2. UV・マテリアル・テクスチャ統合
3. 最終FBXエクスポートの自動化
4. Blender 4.2完全API対応
5. メモリ安全性の確保

統一命名規則:
- 入力: {model_name}_merged.fbx, {model_name}_original.{ext}
- 出力: {model_name}_final.fbx (最終統合ファイル)
"""

import os
import sys
import argparse
import subprocess
import logging
import tempfile
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

# UniRigプロジェクトルートを追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

class UnifiedBlenderIntegrator:
    """統一Blender統合システム"""
    
    def __init__(self, enable_debug: bool = False):
        """
        Args:
            enable_debug: デバッグログ有効化
        """
        self.logger = self._setup_logger(enable_debug)
        self.blender_executable = self._find_blender_executable()
        
    def _setup_logger(self, enable_debug: bool) -> logging.Logger:
        """ロガー設定"""
        logger = logging.getLogger('UnifiedBlenderIntegrator')
        logger.setLevel(logging.DEBUG if enable_debug else logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '[%(asctime)s] %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _find_blender_executable(self) -> Optional[str]:
        """Blender実行可能ファイル検索"""
        possible_paths = [
            'blender',  # PATH環境変数内
            '/usr/bin/blender',  # Linux標準
            '/Applications/Blender.app/Contents/MacOS/Blender',  # macOS
            'C:\\Program Files\\Blender Foundation\\Blender 4.2\\blender.exe',  # Windows
            'C:\\Program Files\\Blender Foundation\\Blender\\blender.exe',  # Windows一般
        ]
        
        for path in possible_paths:
            try:
                result = subprocess.run([path, '--version'], capture_output=True, timeout=10)
                if result.returncode == 0:
                    self.logger.info(f"Found Blender executable: {path}")
                    return path
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        
        self.logger.warning("Blender executable not found in standard locations")
        return None
    
    def _create_blender_script(self, merged_fbx: str, original_file: str, output_fbx: str, model_name: str) -> str:
        """Blenderスクリプト生成"""
        script = f'''
import bpy
import bmesh
import sys
from pathutils import Path

# 🎯 UniRig統合Blender統合スクリプト
# Blender 4.2完全対応・メモリ安全性確保

def clean_scene():
    """シーンクリーンアップ"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # 全データクリーンアップ
    for collection in bpy.data.collections:
        bpy.data.collections.remove(collection)
    
    print("Scene cleaned successfully")

def safe_import_fbx(file_path: str) -> bool:
    """安全なFBXインポート"""
    try:
        bpy.ops.import_scene.fbx(
            filepath=file_path,
            use_image_search=True,
            use_alpha_decals=False,
            use_anim=True,
            use_custom_props=True,
            use_custom_props_enum_as_string=True,
            ignore_leaf_bones=False,
            force_connect_children=False,
            automatic_bone_orientation=False,
            primary_bone_axis='Y',
            secondary_bone_axis='X',
            use_prepost_rot=True,
            axis_forward='-Y',
            axis_up='Z'
        )
        print(f"Successfully imported: {{file_path}}")
        return True
    except Exception as e:
        print(f"Failed to import FBX: {{e}}")
        return False

def transfer_uv_coordinates_github_pattern(source_mesh, target_mesh):
    """
    GitHubパターンによるUV座標直接転送
    参照: kechirojp/Blender_Scripts-Personal-Library
    """
    if source_mesh.data.uv_layers:
        source_uv_layer = source_mesh.data.uv_layers[0]
        
        # ターゲットメッシュに新規UVレイヤー作成
        if len(target_mesh.data.uv_layers) == 0:
            target_mesh.data.uv_layers.new()
        target_uv_layer = target_mesh.data.uv_layers[0]
        
        # ループ単位での直接UV転送
        transfer_count = 0
        for loop_idx in range(len(target_mesh.data.loops)):
            if loop_idx < len(source_mesh.data.loops):
                target_uv_layer.data[loop_idx].uv = source_uv_layer.data[loop_idx].uv
                transfer_count += 1
        
        print(f"UV transfer completed: {{transfer_count}} coordinates")
        return True
    return False

def restore_materials_with_textures(source_obj, target_obj):
    """マテリアルとテクスチャの完全復元"""
    for slot_idx, material_slot in enumerate(source_obj.material_slots):
        if material_slot.material:
            source_material = material_slot.material
            
            # 新規マテリアル作成
            new_material = bpy.data.materials.new(name=source_material.name)
            new_material.use_nodes = True
            
            # マテリアルノードツリー復元
            nodes = new_material.node_tree.nodes
            links = new_material.node_tree.links
            
            # Principled BSDF設定
            bsdf = nodes.get("Principled BSDF")
            if bsdf:
                bsdf.inputs["Base Color"].default_value = source_material.diffuse_color
                
                # テクスチャノード追加
                for node in source_material.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image:
                        new_tex_node = nodes.new(type='ShaderNodeTexImage')
                        new_tex_node.image = node.image
                        links.new(new_tex_node.outputs["Color"], bsdf.inputs["Base Color"])
            
            # ターゲットオブジェクトにマテリアル適用
            target_obj.data.materials.append(new_material)
    
    print("Materials restored successfully")

def export_fbx_with_texture_packing(output_path: str):
    """テクスチャ統合FBXエクスポート"""
    try:
        # テクスチャパッキング
        bpy.ops.file.pack_all()
        
        # Blender 4.2対応FBXエクスポート
        bpy.ops.export_scene.fbx(
            filepath=output_path,
            check_existing=True,
            use_selection=False,
            
            # テクスチャ関連設定
            embed_textures=True,
            path_mode='COPY',
            
            # メッシュ設定
            use_mesh_modifiers=True,
            mesh_smooth_type='FACE',
            use_tspace=True,
            
            # マテリアル設定
            use_custom_props=False,
            colors_type='SRGB',
            
            # アーマチュア設定
            add_leaf_bones=True,
            primary_bone_axis='Y',
            secondary_bone_axis='X',
            
            # 軸設定
            axis_forward='-Y',
            axis_up='Z'
        )
        print(f"FBX exported successfully: {{output_path}}")
        return True
    except Exception as e:
        print(f"FBX export failed: {{e}}")
        return False

def main():
    """メイン統合処理"""
    merged_fbx = "{merged_fbx}"
    original_file = "{original_file}"
    output_fbx = "{output_fbx}"
    model_name = "{model_name}"
    
    print(f"Starting Blender integration for model: {{model_name}}")
    print(f"Merged FBX: {{merged_fbx}}")
    print(f"Original file: {{original_file}}")
    print(f"Output FBX: {{output_fbx}}")
    
    # シーンクリーンアップ
    clean_scene()
    
    # マージ済みFBXインポート
    if not safe_import_fbx(merged_fbx):
        print("ERROR: Failed to import merged FBX")
        sys.exit(1)
    
    merged_objects = list(bpy.context.selected_objects)
    if not merged_objects:
        print("ERROR: No objects found in merged FBX")
        sys.exit(1)
    
    # 元ファイルインポート
    if not safe_import_fbx(original_file):
        print("ERROR: Failed to import original file")
        sys.exit(1)
    
    original_objects = [obj for obj in bpy.context.selected_objects if obj not in merged_objects]
    
    # UV・マテリアル統合処理
    if original_objects and merged_objects:
        # メッシュオブジェクトのみ処理
        original_mesh = next((obj for obj in original_objects if obj.type == 'MESH'), None)
        merged_mesh = next((obj for obj in merged_objects if obj.type == 'MESH'), None)
        
        if original_mesh and merged_mesh:
            # UV座標転送
            if transfer_uv_coordinates_github_pattern(original_mesh, merged_mesh):
                print("UV coordinates transferred successfully")
            
            # マテリアル復元
            restore_materials_with_textures(original_mesh, merged_mesh)
            
            # マージ済みオブジェクトのみ選択
            bpy.ops.object.select_all(action='DESELECT')
            for obj in merged_objects:
                obj.select_set(True)
            
            # 最終FBXエクスポート
            if export_fbx_with_texture_packing(output_fbx):
                print("Integration completed successfully")
                sys.exit(0)
            else:
                print("ERROR: FBX export failed")
                sys.exit(1)
        else:
            print("ERROR: Required mesh objects not found")
            sys.exit(1)
    else:
        print("ERROR: Required objects not found")
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
        return script
    
    def _execute_blender_script(self, script: str, timeout: int = 1800) -> Tuple[bool, str]:
        """Blenderスクリプト実行"""
        if not self.blender_executable:
            return False, "Blender executable not found"
        
        try:
            # 一時スクリプトファイル作成
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_script:
                temp_script.write(script)
                temp_script_path = temp_script.name
            
            # Blenderバックグラウンド実行
            cmd = [
                self.blender_executable,
                '--background',
                '--python', temp_script_path
            ]
            
            self.logger.info(f"Executing Blender script: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            # 一時ファイル削除
            os.unlink(temp_script_path)
            
            if result.returncode == 0:
                self.logger.info("Blender script executed successfully")
                return True, result.stdout
            else:
                self.logger.error(f"Blender script failed with code {result.returncode}")
                self.logger.error(f"STDERR: {result.stderr}")
                return False, result.stderr
                
        except subprocess.TimeoutExpired:
            self.logger.error("ERROR: Blender script timeout (30 minutes)")
            if 'temp_script_path' in locals():
                os.unlink(temp_script_path)
            return False, "Script timeout"
        except Exception as e:
            self.logger.error(f"ERROR: Blender script execution failed: {e}")
            if 'temp_script_path' in locals():
                os.unlink(temp_script_path)
            return False, str(e)
    
    def execute_integration(self, merged_fbx: str, original_file: str, output_fbx: str, model_name: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        統合Blender統合実行
        
        Args:
            merged_fbx: マージ済みFBXファイルパス
            original_file: 元ファイルパス（UV・マテリアル・テクスチャ参照用）
            output_fbx: 最終出力FBXファイルパス
            model_name: モデル名（統一命名規則用）
        
        Returns:
            (success, logs, output_files): 実行結果
        """
        self.logger.info(f"Starting Blender integration for model: {model_name}")
        self.logger.info(f"Merged FBX: {merged_fbx}")
        self.logger.info(f"Original file: {original_file}")
        self.logger.info(f"Output FBX: {output_fbx}")
        
        # 入力ファイル存在チェック
        if not Path(merged_fbx).exists():
            return False, f"Merged FBX file not found: {merged_fbx}", {}
        
        if not Path(original_file).exists():
            return False, f"Original file not found: {original_file}", {}
        
        # 出力ディレクトリ作成
        output_dir = Path(output_fbx).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Blenderスクリプト生成
        script = self._create_blender_script(merged_fbx, original_file, output_fbx, model_name)
        
        # Blenderスクリプト実行
        success, logs = self._execute_blender_script(script)
        if not success:
            return False, f"Blender integration failed: {logs}", {}
        
        # 出力ファイル検証
        if not Path(output_fbx).exists():
            return False, f"Output FBX file not created: {output_fbx}", {}
        
        # ファイルサイズチェック
        file_size = Path(output_fbx).stat().st_size
        if file_size < 1024:  # 1KB未満は異常
            return False, f"Output file suspiciously small: {file_size} bytes", {}
        
        # 成功
        result_files = {
            "final_fbx": output_fbx
        }
        
        success_log = (
            f"Blender integration completed successfully\n"
            f"Generated final FBX file: {output_fbx} ({file_size} bytes)\n"
            f"Blender logs: {logs}"
        )
        
        return True, success_log, result_files
    
    def integrate_with_blender_unified(self, model_name: str, original_file: str, merged_file: str, output_dir: str) -> Tuple[bool, str]:
        """統合Blender統合メソッド（app.py統合用）"""
        try:
            self.logger.info(f"統合Blender統合処理開始: {model_name}")
            
            # 入力ファイル検証
            original_path = Path(original_file)
            merged_path = Path(merged_file)
            
            if not original_path.exists():
                return False, f"オリジナルファイルが存在しません: {original_file}"
            if not merged_path.exists():
                return False, f"マージファイルが存在しません: {merged_file}"
            
            # 出力ディレクトリ作成
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # 出力ファイルパス決定 (決め打ちディレクトリ戦略準拠)
            output_file = output_path / f"{model_name}_final.fbx"
            
            # 統合Blender処理実行
            success, logs, output_files = self.execute_integration(
                merged_fbx=merged_file,
                original_file=original_file,
                output_fbx=str(output_file),
                model_name=model_name
            )
            
            if success:
                # 期待出力確認
                if output_file.exists():
                    file_size = output_file.stat().st_size / (1024 * 1024)
                    logs += f"\n✅ 最終統合出力確認: {output_file} ({file_size:.2f} MB)"
                    
                    # テクスチャフォルダ確認
                    texture_folder = output_path / f"{model_name}_final.fbm"
                    if texture_folder.exists():
                        texture_count = len(list(texture_folder.glob("*")))
                        logs += f"\n✅ テクスチャフォルダ: {texture_folder} ({texture_count}個のファイル)"
                else:
                    return False, f"最終統合出力が生成されませんでした: {output_file}"
            
            return success, logs
            
        except Exception as e:
            self.logger.error(f"統合Blender統合処理エラー: {e}", exc_info=True)
            return False, f"統合Blender統合処理エラー: {str(e)}"

# オーケストレーター統合エイリアス
class UnifiedBlenderOrchestrator(UnifiedBlenderIntegrator):
    """app.py統合用エイリアス"""
    pass

def main():
    """CLIエントリーポイント"""
    parser = argparse.ArgumentParser(
        description="UniRig統合Blender統合システム",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python -m src.pipeline.unified_blender --merged merged.fbx --original original.glb --output final.fbx --model_name bird

統一命名規則:
  入力: {model_name}_merged.fbx, {model_name}_original.{ext}
  出力: {model_name}_final.fbx (最終統合ファイル)
        """
    )
    
    parser.add_argument('--merged', required=True, help='マージ済みFBXファイルパス')
    parser.add_argument('--original', required=True, help='元ファイルパス（UV・マテリアル・テクスチャ参照用）')
    parser.add_argument('--output', required=True, help='最終出力FBXファイルパス')
    parser.add_argument('--model_name', required=True, help='モデル名（統一命名規則用）')
    parser.add_argument('--debug', action='store_true', help='デバッグログ有効化')
    
    args = parser.parse_args()
    
    # Blender統合実行
    integrator = UnifiedBlenderIntegrator(enable_debug=args.debug)
    success, logs, output_files = integrator.execute_integration(
        merged_fbx=args.merged,
        original_file=args.original,
        output_fbx=args.output,
        model_name=args.model_name
    )
    
    # 結果出力
    print("\n" + "="*60)
    print("UniRig統合Blender統合システム実行結果:")
    print("="*60)
    print(f"実行状態: {'成功' if success else '失敗'}")
    print(f"出力ファイル: {output_files}")
    print("\n実行ログ:")
    print(logs)
    print("="*60)
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
