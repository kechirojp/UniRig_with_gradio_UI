"""
Step 5 Module - 簡素化Blender統合 & 最終FBX出力
確実なUV・マテリアル転送に特化

【設計原理】
1. 場合分けの廃止 - 混乱回避
2. 確実なUV・マテリアル転送に集中
3. シンプルなZ-up変換
4. 明確なエラーメッセージ

【データフロー】
- 入力: original_model (Step0保存), merged_fbx (Step4出力)  
- 出力: {model_name}_final.fbx (完全統合版)

【責務】
- オリジナルモデルのUV・マテリアル・テクスチャ情報を取得
- Step4マージ済みモデルにUV・マテリアル情報を適用
- Z-up軸設定で最終FBXエクスポート
"""

import os
import logging
import subprocess
import time
from pathlib import Path
from typing import Tuple, Dict, Optional
import shutil
import traceback

logger = logging.getLogger(__name__)

class Step5SimplifiedBlenderIntegration:
    """
    Step 5: 簡素化Blender統合システム
    
    確実なUV・マテリアル転送に特化した設計:
    - 複雑な場合分けを廃止
    - UV・マテリアル転送に集中
    - 明確なエラーハンドリング
    - Z-up変換の確実な実行
    """
    
    def __init__(self, output_dir: Path, logger_instance: Optional[logging.Logger] = None):
        """
        Step5初期化
        
        Args:
            output_dir: このステップの出力ディレクトリ（Pathオブジェクト）
            logger_instance: ロガーインスタンス
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger_instance if logger_instance else logging.getLogger(__name__)
        
    def integrate_final_model(self, model_name: str, original_file: str, merged_file: str) -> Tuple[bool, str, Dict[str, str]]:
        """
        最終モデル統合処理（簡素化版）
        
        Args:
            model_name: モデル識別名
            original_file: オリジナルモデルファイルパス（UV・マテリアル・テクスチャ源）
            merged_file: Step4マージ済みFBXファイルパス（ボーン・スキンウェイト源）
        
        Returns:
            success: 成功フラグ
            logs: 実行ログ
            output_files: 出力ファイル辞書
        """
        start_time = time.time()
        
        try:
            # 入力ファイル確認
            if not Path(original_file).exists():
                return False, f"オリジナルファイルが見つかりません: {original_file}", {}
                
            if not Path(merged_file).exists():
                return False, f"マージ済みファイルが見つかりません: {merged_file}", {}
            
            # 出力パス設定
            final_fbx_path = self.output_dir / f"{model_name}_final.fbx"
            
            self.logger.info(f"Step5統合開始: {model_name}")
            self.logger.info(f"オリジナル: {original_file}")
            self.logger.info(f"マージ済み: {merged_file}")
            
            # Blenderスクリプトによる統合処理
            success = self._execute_blender_integration(
                original_file=original_file,
                merged_file=merged_file,
                output_file=str(final_fbx_path)
            )
            
            if success and final_fbx_path.exists():
                elapsed_time = time.time() - start_time
                file_size_mb = final_fbx_path.stat().st_size / (1024 * 1024)
                
                self.logger.info(f"✅ Step5統合完了: {final_fbx_path} ({file_size_mb:.1f}MB, {elapsed_time:.1f}秒)")
                
                return True, f"Step5統合完了: {model_name} ({file_size_mb:.1f}MB, {elapsed_time:.1f}秒)", {
                    "final_fbx": str(final_fbx_path)
                }
            else:
                return False, "Blender統合処理に失敗しました", {}
                
        except Exception as e:
            self.logger.error(f"Step5統合エラー: {e}")
            return False, f"Step5統合エラー: {str(e)}", {}
    
    def _execute_blender_integration(self, original_file: str, merged_file: str, output_file: str) -> bool:
        """
        Blender統合処理の実行
        
        Args:
            original_file: オリジナルモデルファイル（UV・マテリアル源）
            merged_file: マージ済みモデルファイル（ボーン・スキンウェイト源）
            output_file: 出力ファイルパス
        
        Returns:
            success: 実行成功フラグ
        """
        try:
            # ⭐ 修正: 安全なファイルベーススクリプト実行
            # Blenderスクリプトファイル作成
            script_file = self.output_dir / f"{Path(output_file).stem}_integration_script.py"
            
            blender_script_content = self._generate_integration_script(
                original_file=original_file,
                merged_file=merged_file,
                output_file=output_file
            )
            
            # スクリプトファイルを安全に書き込み
            with open(script_file, 'w', encoding='utf-8') as f:
                f.write(blender_script_content)
            
            # ⭐ 修正: --python（ファイル指定）を使用（--python-textは禁止）
            cmd = [
                "blender", "--background", "--python", str(script_file)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5分タイムアウト
                cwd="/app"
            )
            
            # ⭐ 追加: スクリプトファイルを自動削除（セキュリティ）
            try:
                script_file.unlink()  # 使用後削除
            except Exception:
                pass  # 削除エラーは無視
            
            if result.returncode == 0:
                self.logger.info("Blender統合処理成功")
                return True
            else:
                self.logger.error(f"Blender統合エラー: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("Blender統合処理タイムアウト")
            return False
        except Exception as e:
            self.logger.error(f"Blender統合例外: {e}")
            return False
    
    def _generate_integration_script(self, original_file: str, merged_file: str, output_file: str) -> str:
        """
        Blender統合スクリプト生成
        
        UV・マテリアル・テクスチャの確実な転送を実行
        """
        script = f'''
import bpy
import bmesh
from mathutils import Vector
import os

def clear_scene():
    """シーンクリア"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # データブロッククリア
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    for material in bpy.data.materials:
        bpy.data.materials.remove(material)
    for image in bpy.data.images:
        bpy.data.images.remove(image)

def load_original_model():
    """オリジナルモデル読み込み（UV・マテリアル源）"""
    original_path = "{original_file}"
    print(f"オリジナルモデル読み込み: {{original_path}}")
    
    if original_path.endswith('.glb') or original_path.endswith('.gltf'):
        bpy.ops.import_scene.gltf(filepath=original_path)
    elif original_path.endswith('.vrm'):
        # VRMファイルもglTFベースなのでgltfインポーターを使用
        bpy.ops.import_scene.gltf(filepath=original_path)
    elif original_path.endswith('.fbx'):
        bpy.ops.import_scene.fbx(filepath=original_path)
    elif original_path.endswith('.obj'):
        bpy.ops.wm.obj_import(filepath=original_path)
    else:
        raise ValueError(f"サポートされていないファイル形式: {{original_path}}")
    
    # オリジナルオブジェクト取得
    original_objects = []
    for obj in bpy.context.selected_objects:
        if obj.type == 'MESH':
            original_objects.append(obj)
            obj.name = obj.name + "_original"
    
    return original_objects

def load_merged_model():
    """マージ済みモデル読み込み（ボーン・スキンウェイト源）"""
    merged_path = "{merged_file}"
    print(f"マージ済みモデル読み込み: {{merged_path}}")
    
    bpy.ops.import_scene.fbx(filepath=merged_path)
    
    # マージ済みオブジェクト取得
    merged_objects = []
    armature_object = None
    
    for obj in bpy.context.selected_objects:
        if obj.type == 'MESH':
            merged_objects.append(obj)
            obj.name = obj.name + "_merged"
        elif obj.type == 'ARMATURE':
            armature_object = obj
    
    return merged_objects, armature_object

def transfer_uv_materials(original_objects, merged_objects):
    """UV・マテリアル転送"""
    print("UV・マテリアル転送開始")
    
    for merged_obj in merged_objects:
        # 対応するオリジナルオブジェクト検索
        original_obj = None
        for orig_obj in original_objects:
            if orig_obj.data.vertices and merged_obj.data.vertices:
                if len(orig_obj.data.vertices) == len(merged_obj.data.vertices):
                    original_obj = orig_obj
                    break
        
        if not original_obj:
            print(f"対応するオリジナルオブジェクトが見つかりません: {{merged_obj.name}}")
            continue
        
        print(f"転送実行: {{original_obj.name}} → {{merged_obj.name}}")
        
        # マテリアルクリア
        merged_obj.data.materials.clear()
        
        # マテリアル転送
        for material in original_obj.data.materials:
            if material:
                merged_obj.data.materials.append(material)
        
        # UV転送
        if original_obj.data.uv_layers and len(original_obj.data.uv_layers) > 0:
            # 既存UVレイヤークリア
            merged_obj.data.uv_layers.clear()
            
            # 新規UVレイヤー作成
            merged_uv = merged_obj.data.uv_layers.new()
            original_uv = original_obj.data.uv_layers[0]
            
            # UV座標転送
            for loop_idx in range(len(merged_obj.data.loops)):
                if loop_idx < len(original_obj.data.loops):
                    merged_uv.data[loop_idx].uv = original_uv.data[loop_idx].uv
        
        print(f"転送完了: {{merged_obj.name}}")

def export_final_fbx():
    """最終FBXエクスポート"""
    output_path = "{output_file}"
    print(f"最終FBXエクスポート: {{output_path}}")
    
    # オリジナルオブジェクト削除（マージ済みのみ残す）
    for obj in list(bpy.data.objects):
        if "_original" in obj.name:
            bpy.data.objects.remove(obj, do_unlink=True)
    
    # 全選択
    bpy.ops.object.select_all(action='SELECT')
    
    # FBXエクスポート（Z-up設定）
    bpy.ops.export_scene.fbx(
        filepath=output_path,
        use_selection=True,
        add_leaf_bones=True,
        mesh_smooth_type='FACE',
        use_tspace=True,
        embed_textures=True,
        path_mode='COPY',
        axis_forward='-Y',
        axis_up='Z'
    )
    
    print(f"エクスポート完了: {{output_path}}")

def main():
    """メイン処理"""
    try:
        print("=== Step5 Blender統合処理開始 ===")
        
        # シーンクリア
        clear_scene()
        
        # オリジナルモデル読み込み
        original_objects = load_original_model()
        print(f"オリジナルオブジェクト数: {{len(original_objects)}}")
        
        # マージ済みモデル読み込み
        merged_objects, armature = load_merged_model()
        print(f"マージ済みオブジェクト数: {{len(merged_objects)}}")
        
        # UV・マテリアル転送
        transfer_uv_materials(original_objects, merged_objects)
        
        # 最終FBXエクスポート
        export_final_fbx()
        
        print("=== Step5 Blender統合処理完了 ===")
        
    except Exception as e:
        print(f"エラー: {{e}}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()
'''
        return script
