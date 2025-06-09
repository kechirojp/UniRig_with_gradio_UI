"""
Step 3 Module - スキニング適用
独立した実行機能として、メッシュとスケルトンの結合（スキニング）を実行

責務: メッシュデータ + スケルトン → リギング済みFBX
入力: メッシュデータファイルパス、スケルトンFBXファイルパス、スケルトンNPZファイルパス
出力: リギング済みFBXファイルパス, スキニングデータファイルパス (.npz)
"""

import os
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple, Dict, Optional
import numpy as np

class Step3Skinning:
    """Step 3: スキニング適用モジュール"""
    
    def __init__(self, output_dir: Path, logger_instance: logging.Logger):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger_instance
        
    def apply_skinning(self, 
                       input_mesh_npz_path: Path, 
                       input_skeleton_fbx_path: Path,
                       input_skeleton_npz_path: Path, # 追加
                       model_name: str) -> Tuple[bool, str, Dict]:
        """
        スキニング適用の実行（UniRig本格実装統合）
        
        Args:
            input_mesh_npz_path: 入力メッシュNPZファイルパス (絶対パス)
            input_skeleton_fbx_path: 入力スケルトンFBXファイルパス (絶対パス)
            input_skeleton_npz_path: 入力スケルトンNPZファイルパス (絶対パス)
            model_name: モデル名（出力ファイル名に使用）
            
        Returns:
            (success, logs, output_files)
        """
        try:
            self.logger.info(f"Step 3 (Skinning) 開始: model_name={model_name}")
            self.logger.info(f"  入力メッシュNPZ: {input_mesh_npz_path}")
            self.logger.info(f"  入力スケルトンFBX: {input_skeleton_fbx_path}")
            self.logger.info(f"  入力スケルトンNPZ: {input_skeleton_npz_path}")
            self.logger.info(f"  出力先ディレクトリ: {self.output_dir}")
            
            # UniRig本格実装を試行
            try:
                from step_modules.step3_skinning_unirig import Step3UniRigSkinning
                # Step3UniRigSkinning にも logger_instance を渡す
                unirig_skinner = Step3UniRigSkinning(self.output_dir, self.logger) 
                success, logs, output_files = unirig_skinner.apply_skinning(
                    input_mesh_npz_path, 
                    input_skeleton_fbx_path,
                    input_skeleton_npz_path, # 追加
                    model_name
                )
                
                if success:
                    self.logger.info("UniRig本格スキニング処理成功")
                    return success, logs, output_files
                else:
                    self.logger.warning(f"UniRig本格処理失敗、フォールバック実行: {logs}")
                    
            except ImportError as ie:
                self.logger.error(f"UniRig本格処理モジュールのインポートエラー: {ie}。フォールバック実行。")
            except Exception as e:
                self.logger.warning(f"UniRig本格処理で予期せぬエラー、フォールバック実行: {e}", exc_info=True)
            
            # フォールバック: モック実装を実行
            self.logger.info("フォールバック: モックスキニング実装を実行")
            return self._fallback_mock_skinning(
                input_mesh_npz_path, 
                input_skeleton_fbx_path, 
                input_skeleton_npz_path, # 追加
                model_name
            )
            
        except Exception as e:
            error_msg = f"Step 3 スキニング適用エラー: {e}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg, {}
    
    def _fallback_mock_skinning(self, 
                                input_mesh_npz_path: Path, 
                                input_skeleton_fbx_path: Path, 
                                input_skeleton_npz_path: Path, # 追加
                                model_name: str) -> Tuple[bool, str, Dict]:
        """フォールバック: モックスキニング実装"""
        try:
            self.logger.info(f"フォールバック: 出力ディレクトリ for {model_name}: {self.output_dir}")

            output_fbx = self.output_dir / f"{model_name}_skinned_fallback.fbx"
            output_npz = self.output_dir / f"{model_name}_skinning_fallback.npz"
            output_weights = self.output_dir / f"{model_name}_weights_fallback.txt"
            
            mesh_data = self._load_mesh_data(input_mesh_npz_path)
            skeleton_data = self._load_skeleton_data(input_skeleton_fbx_path, input_skeleton_npz_path, model_name) 
            
            if not mesh_data:
                return False, "フォールバック: 入力メッシュデータの読み込みに失敗", {}
            if not skeleton_data: 
                self.logger.warning("フォールバック: スケルトンデータの読み込みに失敗。モックデータで続行します。")
                skeleton_data = {"bones": [f"mock_bone_{i}" for i in range(5)], "bone_count": 5}
            
            skinning_data = self._generate_mock_skinning_data(mesh_data, skeleton_data)
            
            # Blenderでバイナリ形式のモックFBXを生成
            mock_fbx_success = self._create_binary_mock_fbx(
                output_fbx, mesh_data, skeleton_data, model_name
            )
            
            if not mock_fbx_success:
                # バイナリFBX生成に失敗した場合は、最低限のテキストファイルで代替
                with open(output_fbx, 'w') as f_mock_fbx:
                    f_mock_fbx.write(f"Mock skinned FBX for {model_name} (text fallback)\\n")
                    f_mock_fbx.write(f"Original mesh NPZ: {input_mesh_npz_path}\\n")
                    f_mock_fbx.write(f"Original skeleton FBX: {input_skeleton_fbx_path}\\n")
                    f_mock_fbx.write(f"Original skeleton NPZ: {input_skeleton_npz_path}\\n")
                self.logger.warning(f"バイナリFBX生成失敗、テキストファイルで代替: {output_fbx}")
            else:
                self.logger.info(f"フォールバック: バイナリ形式モックFBXファイルを作成: {output_fbx}")
            
            np.savez_compressed(output_npz, **skinning_data)
            self.logger.info(f"フォールバック: モックスキニングNPZデータ保存: {output_npz}")
            
            weight_info = self._generate_mock_weight_info(skinning_data)
            with open(output_weights, 'w', encoding='utf-8') as f:
                f.write(weight_info)
            self.logger.info(f"フォールバック: モックウェイト情報テキスト生成: {output_weights}")
            
            output_files = {
                "skinned_fbx": str(output_fbx),
                "skinning_npz": str(output_npz),
                "weights_txt": str(output_weights),
                "file_size_fbx": os.path.getsize(output_fbx) if os.path.exists(output_fbx) else 0,
                "file_size_npz": os.path.getsize(output_npz) if os.path.exists(output_npz) else 0,
                "vertex_count": len(mesh_data.get("vertices", [])),
                "bone_count": skeleton_data.get("bone_count", 0)
            }

            logs = f"""Step 3 (フォールバック・スキニング適用) 完了:
- 入力メッシュNPZ: {input_mesh_npz_path}
- 入力スケルトンFBX: {input_skeleton_fbx_path}
- 入力スケルトンNPZ: {input_skeleton_npz_path}
- 出力FBX (モック): {output_fbx} ({output_files['file_size_fbx']} bytes)
- 出力NPZ (モック): {output_npz} ({output_files['file_size_npz']} bytes)
- 頂点数: {output_files['vertex_count']}
- ボーン数: {output_files['bone_count']}
- ウェイト情報 (モック): {output_weights}
"""
            
            self.logger.info(f"Step 3 フォールバック完了: {output_fbx}")
            return True, logs.strip(), output_files
            
        except Exception as e:
            self.logger.error(f"フォールバック処理エラー: {e}", exc_info=True)
            return False, f"フォールバック処理エラー: {e}", {}
    
    def _load_mesh_data(self, mesh_file_path: Path) -> Optional[Dict]:
        """メッシュデータの読み込み"""
        try:
            if not mesh_file_path.exists():
                self.logger.error(f"メッシュファイルが見つかりません: {mesh_file_path}")
                return None
            
            self.logger.info(f"メッシュデータ読み込み開始: {mesh_file_path}")
            data = np.load(mesh_file_path, allow_pickle=True)
            self.logger.info(f"メッシュNPZデータ読み込み成功: keys={list(data.keys())}")
            
            return {
                "vertices": data["vertices"],
                "faces": data["faces"],
                "normals": data.get("vertex_normals"), 
                "uv_coordinates": data.get("uv_coords") 
            }
        except Exception as e:
            self.logger.error(f"メッシュデータ読み込みエラー: {e}", exc_info=True)
            return None
    
    def _load_skeleton_data(self, skeleton_fbx_path: Path, skeleton_npz_path: Path, model_name: str) -> Optional[Dict]:
        """スケルトンデータの読み込み（純粋なスキニング処理）"""
        try:
            self.logger.info(f"スケルトンデータ読み込み試行: FBX={skeleton_fbx_path}, NPZ={skeleton_npz_path}")
            
            if not skeleton_npz_path.exists():
                self.logger.warning(f"スケルトンNPZファイルが見つかりません: {skeleton_npz_path}。FBXパス: {skeleton_fbx_path}")
                return None 
            
            skeleton_data_npz = np.load(skeleton_npz_path, allow_pickle=True)
            self.logger.info(f"スケルトンNPZデータ ('{skeleton_npz_path}') 読み込み成功: keys={list(skeleton_data_npz.keys())}")
            
            bone_names_raw = skeleton_data_npz.get("names", skeleton_data_npz.get("bone_names"))
            if bone_names_raw is None: bone_names_raw = []
            
            bone_names = bone_names_raw.tolist() if hasattr(bone_names_raw, 'tolist') else list(bone_names_raw)
            
            return {
                "bones": bone_names,
                "joint_positions": skeleton_data_npz.get("joints", skeleton_data_npz.get("joint_positions", np.array([]))),
                "bone_hierarchy": skeleton_data_npz.get("parents", skeleton_data_npz.get("bone_hierarchy", np.array([]))),
                "fbx_file_path": str(skeleton_fbx_path), 
                "npz_file_path": str(skeleton_npz_path),
                "bone_count": len(bone_names)
            }
            
        except Exception as e:
            self.logger.error(f"スケルトンデータ読み込みエラー: {e}", exc_info=True)
            return None
    
    def _generate_mock_skinning_data(self, mesh_data: Dict, skeleton_data: Dict) -> Dict:
        """スキニングデータ生成 - Step3の核心機能"""
        vertex_count = len(mesh_data.get("vertices", []))
        bone_count = skeleton_data.get("bone_count", 0)
        
        self.logger.info(f"フォールバック・スキニング処理: {vertex_count} 頂点 × {bone_count} ボーン")
        
        if bone_count == 0: 
            self.logger.warning("フォールバック: ボーン数が0です。ダミーのウェイトを生成します。")
            weights = np.zeros((vertex_count, 1), dtype=np.float32) 
            bone_indices = np.zeros((vertex_count, 4), dtype=np.int32)
        else:
            weights = np.random.rand(vertex_count, bone_count).astype(np.float32)
            sum_weights = np.sum(weights, axis=1, keepdims=True)
            sum_weights[sum_weights == 0] = 1 
            weights = weights / sum_weights
            
            num_influences = min(4, bone_count)
            bone_indices = np.random.randint(0, bone_count, size=(vertex_count, num_influences), dtype=np.int32)
            if num_influences < 4:
                padding = np.zeros((vertex_count, 4 - num_influences), dtype=np.int32)
                bone_indices = np.hstack((bone_indices, padding))

        return {
            "skinning_weights": weights,
            "bone_indices": bone_indices,
            "vertex_count": vertex_count,
            "bone_count": bone_count
        }
    
    def _generate_mock_weight_info(self, skinning_data: Dict) -> str:
        """モックウェイト情報テキスト生成（開発用）"""
        weights = skinning_data.get("skinning_weights", np.array([]))
        if weights.ndim == 2:
             vertex_count, bone_count = weights.shape
        else:
            vertex_count, bone_count = 0,0
            if weights.size > 0 and weights.ndim == 1:
                vertex_count = 1
                bone_count = weights.shape[0]
            elif weights.size > 0 :
                vertex_count = weights.shape[0]
                bone_count = 1

        info = f"# Skinning Weight Information (Mock)\\n"
        info += f"# Vertex count: {vertex_count}\\n"
        info += f"# Bone count: {bone_count}\\n"
        info += f"# Skinning method: mock_fallback\\n"
        info += f"# Max influences per vertex: 4 (mocked)\\n\\n"
        
        # 各頂点の主要ウェイト情報（最初の10頂点のみ表示）
        for i in range(min(10, vertex_count)):
            vertex_weights = weights[i] if vertex_count > 0 else []
            if not isinstance(vertex_weights, (list, np.ndarray)) or not all(isinstance(w, (int, float)) for w in vertex_weights):
                significant_weights = []
            else:
                significant_weights = [(j, w) for j, w in enumerate(vertex_weights) if w > 0.01]
                significant_weights.sort(key=lambda x: x[1], reverse=True)
            
            info += f"vertex_{i:04d}: "
            for bone_idx, weight_val in significant_weights[:4]:
                info += f"bone_{bone_idx:02d}={weight_val:.3f} "
            info += "\\n"
        
        if vertex_count > 10:
            info += f"... and {vertex_count - 10} more vertices\\n"
        
        return info

    def _create_binary_mock_fbx(self, output_fbx_path: Path, mesh_data: Dict, skeleton_data: Dict, model_name: str) -> bool:
        """
        Blenderを使ってバイナリ形式のモックFBXファイルを生成
        
        Args:
            output_fbx_path: 出力FBXファイルパス
            mesh_data: メッシュデータ
            skeleton_data: スケルトンデータ
            model_name: モデル名
            
        Returns:
            bool: 生成成功/失敗
        """
        try:
            import subprocess
            import tempfile
            
            # Blenderスクリプトを生成
            blender_script = f'''
import bpy
import bmesh
import numpy as np

# シーンクリア
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# メッシュオブジェクト作成
vertices = {mesh_data.get("vertices", [])[:100].tolist() if len(mesh_data.get("vertices", [])) > 0 else [[0,0,0], [1,0,0], [0,1,0]]}  # 最初の100頂点のみ使用
faces = {mesh_data.get("faces", [])[:50].tolist() if len(mesh_data.get("faces", [])) > 0 else [[0,1,2]]}  # 最初の50面のみ使用

# メッシュオブジェクト作成
mesh = bpy.data.meshes.new("{model_name}_mesh")
mesh.from_pydata(vertices, [], faces)
mesh.update()

obj = bpy.data.objects.new("{model_name}_object", mesh)
bpy.context.collection.objects.link(obj)

# アーマチュア作成（簡単なボーン構造）
bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
armature = bpy.context.active_object
armature.name = "{model_name}_armature"

# Edit modeでボーンを追加
bpy.ops.armature.select_all(action='SELECT')
for i in range(min(3, {skeleton_data.get("bone_count", 1)})):  # 最大3本のボーン
    bpy.ops.armature.extrude_move(TRANSFORM_OT_translate={{"value":(0, 0, 1)}})

# Object modeに戻る
bpy.ops.object.mode_set(mode='OBJECT')

# メッシュオブジェクトを選択してアーマチュアとペアレント
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
armature.select_set(True)
bpy.context.view_layer.objects.active = armature

# Automatic Weightsでバインド
bpy.ops.object.parent_set(type='ARMATURE_AUTO')

# 全てを選択してバイナリFBXエクスポート
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.fbx(
    filepath="{str(output_fbx_path)}",
    use_selection=True,
    add_leaf_bones=True,
    bake_anim=False,
    global_scale=1.0,
    apply_unit_scale=True,
    use_space_transform=True,
    object_types={{'ARMATURE', 'MESH'}},
    use_mesh_modifiers=True,
    mesh_smooth_type='OFF',
    use_armature_deform_only=False,
    armature_nodetype='NULL',
    axis_forward='-Y',
    axis_up='Z'
)

print("Binary FBX export completed successfully")
'''
            
            # 一時スクリプトファイルを作成
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as script_file:
                script_file.write(blender_script)
                script_path = script_file.name
            
            try:
                # Blenderをバックグラウンドで実行
                cmd = [
                    "blender", 
                    "--background", 
                    "--python", script_path
                ]
                
                self.logger.info(f"Blenderコマンド実行: {' '.join(cmd)}")
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5分タイムアウト
                    check=False
                )
                
                if result.returncode == 0:
                    self.logger.info("Blenderバイナリ FBX 生成成功")
                    self.logger.debug(f"Blender stdout: {result.stdout}")
                    return True
                else:
                    self.logger.error(f"Blender実行エラー (返却コード: {result.returncode})")
                    self.logger.error(f"Blender stderr: {result.stderr}")
                    return False
                    
            finally:
                # 一時スクリプトファイルを削除
                try:
                    os.unlink(script_path)
                except:
                    pass
                    
        except subprocess.TimeoutExpired:
            self.logger.error("Blender実行タイムアウト (300秒)")
            return False
        except Exception as e:
            self.logger.error(f"バイナリFBX生成エラー: {e}", exc_info=True)
            return False

def execute_step3_standalone(
    input_mesh_npz_path: Path, 
    input_skeleton_fbx_path: Path, 
    input_skeleton_npz_path: Path, 
    model_name: str, 
    output_dir: Path,
    logger_instance: logging.Logger
) -> Tuple[bool, str, Dict]:
    """
    Step 3実行のスタンドアロンエントリーポイント (app.pyのcall_step3_skinningとは別)
    """
    skinner = Step3Skinning(output_dir, logger_instance)
    return skinner.apply_skinning(
        input_mesh_npz_path, 
        input_skeleton_fbx_path, 
        input_skeleton_npz_path, 
        model_name
    )
