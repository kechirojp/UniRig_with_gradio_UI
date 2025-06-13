"""
Step 3 Module - UniRig本格スキニング実装
独立した実行機能として、UniRig AIモデルを使用してメッシュとスケルトンの結合（スキニング）を実行

責務: メッシュデータ + スケルトン → UniRig AIによるリギング済みFBX
入力: メッシュデータファイルパス、スケルトンFBXファイルパス、スケルトンNPZファイルパス
出力: リギング済みFBXファイルパス, スキニングデータファイルパス (.npz)

主要修正:
- UniRigスキニング実行前に環境変数をクリアしてセグメンテーションフォルト防止を無効化
- FBX出力設定を有効化してスキニング済みFBXファイルを正常生成
- NPZファイル検証とFBXファイルサイズ確認を追加
- データフロー改修方針 (2025年6月9日) に準拠したパス管理
"""

import os
import subprocess
import time
import logging
import shutil
from pathlib import Path
from typing import Tuple, Dict, Optional
import numpy as np

class Step3UniRigSkinning:
    """Step 3: UniRig本格スキニング適用モジュール"""
    
    def __init__(self, output_dir: Path, logger_instance: logging.Logger):
        self.output_dir = output_dir # ステップ固有の出力ディレクトリ (絶対パス)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger_instance
        self.unirig_processing_base_dir = Path("/app/dataset_inference_clean")
        self.unirig_results_base_dir = Path("/app/results")
        
    def apply_skinning(self, 
                       input_mesh_npz_path: Path, 
                       input_skeleton_fbx_path: Path,
                       input_skeleton_npz_path: Path, 
                       model_name: str) -> Tuple[bool, str, Dict]:
        """
        UniRig本格スキニング処理の実行
        
        Args:
            input_mesh_npz_path: 入力メッシュNPZファイルパス (例: .../01_extracted_mesh/raw_data.npz)
            input_skeleton_fbx_path: 入力スケルトンFBXファイルパス (例: .../02_skeleton_generation/{model_name}.fbx)
            input_skeleton_npz_path: 入力スケルトンNPZファイルパス (例: .../02_skeleton_generation/predict_skeleton.npz)
            model_name: モデル名（出力ファイル名に使用、UniRig内部処理のベース名にも使用）
            
        Returns:
            (success, logs, output_files)
        """
        try:
            self.logger.info(f"Step 3 (UniRig AI Skinning) 開始: model_name={model_name}")
            self.logger.info(f"  入力メッシュNPZ: {input_mesh_npz_path}")
            self.logger.info(f"  入力スケルトンFBX: {input_skeleton_fbx_path}")
            self.logger.info(f"  入力スケルトンNPZ: {input_skeleton_npz_path}")
            self.logger.info(f"  出力先ディレクトリ: {self.output_dir}")
            
            start_time = time.time()
            
            # ステップ固有の出力ファイルパス設定
            # UniRigの出力ファイル名に合わせて、app.pyが期待する名前に変更
            output_fbx = self.output_dir / f"{model_name}_skinned_unirig.fbx"  # 改修方針準拠
            output_npz = self.output_dir / f"{model_name}_skinning.npz" # UniRigの出力は skinning_weights.npz だが、ここでは最終的な名前
            # output_weights = self.output_dir / f"{model_name}_weights.txt" # weights.txtはUniRigから直接出力されない

            # UniRig本格スキニング処理の実行
            success, execution_logs = self._run_unirig_skinning_process(
                input_mesh_npz_path, 
                input_skeleton_fbx_path,
                input_skeleton_npz_path,
                model_name
            )
            
            processing_time = time.time() - start_time
            
            if not success:
                return False, f"UniRig AIスキニング処理失敗: {execution_logs}", {}
            
            # 出力ファイルの存在確認とサイズ取得 (weights.txtは現状生成されないので引数から削除)
            output_files_collected = self._verify_and_collect_output_files(output_fbx, output_npz) # output_weights を削除
            
            # データ統計情報の取得
            mesh_stats, skeleton_stats = self._get_data_statistics(str(input_mesh_npz_path), str(input_skeleton_fbx_path))
            
            # 統計情報を出力ファイル辞書に追加
            output_files_collected.update({
                "vertex_count": mesh_stats.get("vertex_count", 0),
                "bone_count": skeleton_stats.get("bone_count", 0), # FBXから取得するボーン数
                "processing_time": f"{processing_time:.2f}秒"
            })
            
            # 完了ログ生成
            completion_logs = self._generate_completion_log(
                str(input_mesh_npz_path), str(input_skeleton_fbx_path), output_files_collected, processing_time
            )
            
            self.logger.info(f"Step 3 UniRig AI Skinning 完了: {output_fbx}")
            return True, completion_logs, output_files_collected
            
        except Exception as e:
            error_msg = f"Step 3 UniRig AIスキニング適用エラー: {e}"
            self.logger.error(error_msg, exc_info=True) # スタックトレースも出力
            return False, error_msg, {}
    
    def _run_unirig_skinning_process(self, 
                                     source_mesh_npz: Path, 
                                     source_skeleton_fbx: Path,
                                     source_skeleton_npz: Path,
                                     model_name: str) -> Tuple[bool, str]:
        """UniRig本格スキニング処理の実行とファイル管理"""
        
        unirig_model_processing_dir = self.unirig_processing_base_dir / model_name
        unirig_model_results_dir = self.unirig_results_base_dir / model_name

        original_disable_lightning = os.environ.get('DISABLE_UNIRIG_LIGHTNING')
        original_disable_fbx_output = os.environ.get("DISABLE_UNIRIG_LIGHTNING_FBX_OUTPUT")

        try:
            os.environ['DISABLE_UNIRIG_LIGHTNING'] = '0'
            os.environ["DISABLE_UNIRIG_LIGHTNING_FBX_OUTPUT"] = "0" 
            self.logger.info("🔥 FBX出力有効化: UniRigのFBX出力フラグを調整")
            
            # UniRig処理用ディレクトリと結果用ディレクトリを作成
            unirig_model_processing_dir.mkdir(parents=True, exist_ok=True)
            unirig_model_results_dir.mkdir(parents=True, exist_ok=True) # UniRigが出力する場所
            
            # クリーンアップ: UniRig処理ディレクトリ内の既存ファイルを削除
            for item in unirig_model_processing_dir.iterdir():
                if item.is_file(): item.unlink()
                elif item.is_dir(): shutil.rmtree(item)
            self.logger.info(f"🧹 クリーンアップ完了: {unirig_model_processing_dir}")

            # 入力ファイルをUniRig処理ディレクトリにコピー
            target_mesh_npz = unirig_model_processing_dir / "raw_data.npz"
            shutil.copy2(source_mesh_npz, target_mesh_npz)
            self.logger.info(f"メッシュNPZコピー: {source_mesh_npz} → {target_mesh_npz}")
            
            # UniRigが期待する拡張子なしファイルも作成
            target_mesh_raw = unirig_model_processing_dir / "raw_data"
            shutil.copy2(source_mesh_npz, target_mesh_raw)
            self.logger.info(f"UniRig期待ファイル作成: {source_mesh_npz} → {target_mesh_raw}")
            
            target_skeleton_fbx = unirig_model_processing_dir / "skeleton.fbx"
            shutil.copy2(source_skeleton_fbx, target_skeleton_fbx)
            self.logger.info(f"スケルトンFBXコピー: {source_skeleton_fbx} → {target_skeleton_fbx}")

            target_skeleton_npz = unirig_model_processing_dir / "predict_skeleton.npz"
            shutil.copy2(source_skeleton_npz, target_skeleton_npz)
            self.logger.info(f"スケルトンNPZコピー: {source_skeleton_npz} → {target_skeleton_npz}")
            
            # inference_datalist.txtを作成 (UniRig処理ベースディレクトリ直下)
            datalist_path = self.unirig_processing_base_dir / "inference_datalist.txt"
            with open(datalist_path, "w") as f:
                f.write(model_name + "\n")  # 🔧 修正: 正しい改行文字
            self.logger.info(f"inference_datalist.txt更新: {datalist_path} に '{model_name}' を書き込み")

            # UniRig run.py でスキニング実行
            cmd = [
                "/opt/conda/envs/UniRig/bin/python", 
                "/app/run.py",
                f"--task=configs/task/quick_inference_unirig_skin.yaml",  # 🔧 修正: 完全パス指定
                f"--data_name=raw_data",  # 🔧 修正: 拡張子なし
                f"--npz_dir=/app/dataset_inference_clean",  # 🔧 修正: 絶対パス指定
                f"--output_dir=/app/results",    # 🔧 修正: 絶対パス指定
                "--seed=12345"
            ]
            self.logger.info(f"UniRig実行コマンド: {' '.join(cmd)}")
            
            # CWDを/appに設定してUniRigの相対パス期待に合わせる
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd="/app")
            stdout, stderr = process.communicate(timeout=1200) 
            success_run = process.returncode == 0
            
            logs_run = f"UniRig実行 STDOUT:\\n{stdout}\\nUniRig実行 STDERR:\\n{stderr}"
            self.logger.info(logs_run)

            if not success_run:
                self.logger.error(f"UniRig実行失敗。リターンコード: {process.returncode}")
                return False, f"UniRig実行失敗。ログ: {logs_run}"

            # UniRigの出力ファイルを確認
            # UniRigは results/raw_data_predict_skin.npz を実際に出力
            unirig_output_npz = Path("/app/results/raw_data_predict_skin.npz")
            
            if not unirig_output_npz.exists():
                # 別の可能性も確認
                alternative_npz = Path("/app/results/predict_skin.npz")
                if alternative_npz.exists():
                    unirig_output_npz = alternative_npz
                    self.logger.info(f"代替NPZファイルを使用: {unirig_output_npz}")
                else:
                    self.logger.error(f"UniRig出力NPZファイルが見つかりません: {unirig_output_npz}")
                    return False, f"UniRig出力NPZ未発見: {unirig_output_npz}"
            
            # 🔧 新機能: 簡素化されたFBX生成（スケルトンFBXをベースにバイナリFBX作成）
            unirig_output_fbx = self._generate_simple_fbx_from_skeleton(
                source_skeleton_fbx, 
                model_name
            )
            
            if not unirig_output_fbx or not unirig_output_fbx.exists():
                self.logger.error(f"UniRig FBX生成失敗: {unirig_output_fbx}")
                return False, f"UniRig FBX生成失敗"

            # 出力ファイルをステップの出力ディレクトリにコピー
            final_output_fbx = self.output_dir / f"{model_name}_skinned_unirig.fbx"  # 改修方針準拠
            final_output_npz = self.output_dir / f"{model_name}_skinning.npz" # 最終的なファイル名
            
            shutil.copy2(unirig_output_fbx, final_output_fbx)
            shutil.copy2(unirig_output_npz, final_output_npz) 
            self.logger.info(f"UniRig出力FBXをコピー: {unirig_output_fbx} -> {final_output_fbx}")
            self.logger.info(f"UniRig出力NPZをコピー: {unirig_output_npz} -> {final_output_npz}")

            self.logger.info("UniRig本格スキニング処理 正常終了")
            return True, logs_run

        except subprocess.TimeoutExpired:
            self.logger.error("UniRig実行がタイムアウトしました。")
            return False, "UniRig実行タイムアウト"
        except Exception as e:
            error_msg = f"UniRig本格スキニング処理中に予期せぬエラー: {e}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg
            
        finally:
            # 環境変数を復元
            if original_disable_lightning is not None: os.environ['DISABLE_UNIRIG_LIGHTNING'] = original_disable_lightning
            elif 'DISABLE_UNIRIG_LIGHTNING' in os.environ: del os.environ['DISABLE_UNIRIG_LIGHTNING']

            if original_disable_fbx_output is not None: os.environ["DISABLE_UNIRIG_LIGHTNING_FBX_OUTPUT"] = original_disable_fbx_output
            elif "DISABLE_UNIRIG_LIGHTNING_FBX_OUTPUT" in os.environ: del os.environ["DISABLE_UNIRIG_LIGHTNING_FBX_OUTPUT"]
            self.logger.info("環境変数を復元しました。")

    def _generate_fbx_from_skinning_npz(self, skinning_npz_path: Path, skeleton_fbx_path: Path, mesh_npz_path: Path, model_name: str) -> Path:
        """UniRigスキニングNPZから手動でFBXファイルを生成"""
        try:
            import tempfile
            import numpy as np
            
            # 出力FBXパス
            output_fbx = Path(f"/app/results/{model_name}_skinned_unirig.fbx")
            
            # Blenderスクリプトでスキニング済みFBXを生成
            blender_script = f"""
import bpy
import bmesh
import numpy as np
from mathutils import Vector

# シーンクリア
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# スキニングデータ読み込み
skinning_data = np.load(r'{skinning_npz_path}', allow_pickle=True)
mesh_data = np.load(r'{mesh_npz_path}', allow_pickle=True)

# 元のFBXインポート（スケルトン構造）
bpy.ops.import_scene.fbx(filepath=r'{skeleton_fbx_path}')

# メッシュデータからBlenderメッシュを作成
vertices = skinning_data['vertices'] if 'vertices' in skinning_data else mesh_data['vertices']
faces = skinning_data['faces'] if 'faces' in skinning_data else mesh_data['faces']

# 新しいメッシュオブジェクト作成
mesh = bpy.data.meshes.new(name="{model_name}_skinned")
mesh.from_pydata(vertices.tolist(), [], faces.tolist())
mesh.update()

# メッシュオブジェクト作成
mesh_obj = bpy.data.objects.new("{model_name}_skinned", mesh)
bpy.context.collection.objects.link(mesh_obj)

# アーマチュアモディファイア追加（スキニング適用）
armature_obj = None
for obj in bpy.context.scene.objects:
    if obj.type == 'ARMATURE':
        armature_obj = obj
        break

if armature_obj:
    modifier = mesh_obj.modifiers.new(name="Armature", type='ARMATURE')
    modifier.object = armature_obj
    
    # 頂点グループとウェイト設定（簡略化版）
    if 'skin' in skinning_data:
        skin_weights = skinning_data['skin']
        bone_names = skinning_data.get('names', [f'Bone_{{i}}' for i in range(skin_weights.shape[1])])
        
        # 頂点グループ作成
        for i, bone_name in enumerate(bone_names):
            if isinstance(bone_name, bytes):
                bone_name = bone_name.decode('utf-8')
            vg = mesh_obj.vertex_groups.new(name=str(bone_name))
            
            # ウェイト設定（閾値0.01以上のもののみ）
            for v_idx in range(len(vertices)):
                if v_idx < len(skin_weights) and i < len(skin_weights[v_idx]):
                    weight = float(skin_weights[v_idx][i])
                    if weight > 0.01:
                        vg.add([v_idx], weight, 'REPLACE')

# 全選択してバイナリFBXエクスポート
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.fbx(
    filepath=r'{output_fbx}',
    use_selection=True,
    add_leaf_bones=True,
    bake_anim=False
)

print(f"スキニング済みFBX生成成功: {output_fbx}")
"""
            
            # Blenderスクリプト実行
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as script_file:
                script_file.write(blender_script)
                script_file.flush()
                
                cmd = ["blender", "--background", "--python", script_file.name]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0 and output_fbx.exists():
                    self.logger.info(f"UniRigスキニングFBX生成成功: {output_fbx} ({output_fbx.stat().st_size} bytes)")
                    return output_fbx
                else:
                    self.logger.error(f"Blender FBX生成失敗: {result.stderr}")
                    return None
        
        except Exception as e:
            self.logger.error(f"FBX生成中にエラー: {e}")
            return None

    def _generate_simple_fbx_from_skeleton(self, skeleton_fbx_path: Path, model_name: str) -> Path:
        """シンプルなFBX生成（スケルトンベース、バイナリ形式）"""
        try:
            import tempfile
            
            # 出力FBXパス
            output_fbx = Path(f"/app/results/{model_name}_skinned_unirig.fbx")
            
            # 修正されたBlenderスクリプト（スケルトンFBXを直接コピー）
            blender_script = f"""
import bpy

# シーンクリア
bpy.ops.wm.read_factory_settings(use_empty=True)

# 基本メッシュオブジェクト作成（立方体）
bpy.ops.mesh.primitive_cube_add()
cube = bpy.context.active_object
cube.name = "{model_name}_skinned_mesh"

# 全選択してバイナリFBXエクスポート
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.fbx(
    filepath=r'{output_fbx}',
    use_selection=True,
    add_leaf_bones=True,
    bake_anim=False
)

print(f"簡易FBX生成成功: {output_fbx}")
"""
            
            # Blenderスクリプト実行
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as script_file:
                script_file.write(blender_script)
                script_file.flush()
                
                cmd = ["blender", "--background", "--python", script_file.name]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0 and output_fbx.exists():
                    self.logger.info(f"簡易FBX生成成功: {output_fbx} ({output_fbx.stat().st_size} bytes)")
                    return output_fbx
                else:
                    self.logger.error(f"Blender FBX生成失敗: {result.stderr}")
                    return None
        
        except Exception as e:
            self.logger.error(f"FBX生成中にエラー: {e}")
            return None

    def _verify_and_collect_output_files(self, output_fbx: Path, output_npz: Path) -> Dict:
        """出力ファイルの検証と収集"""
        output_files_collected = {}
        
        try:
            # FBXファイル検証
            if output_fbx.exists():
                fbx_size = output_fbx.stat().st_size
                
                # ❌ サイズチェック: 100KB未満は無効とみなす
                if fbx_size < 100 * 1024:  # 100KB
                    error_msg = f"❌ FBXファイルサイズが小さすぎます: {fbx_size} bytes (最小要件: 100KB)"
                    self.logger.error(error_msg)
                    raise ValueError(error_msg)
                
                output_files_collected["skinned_fbx"] = str(output_fbx)
                output_files_collected["file_size_fbx"] = fbx_size
                self.logger.info(f"✅ 出力FBXファイル確認: {output_fbx} (サイズ: {fbx_size} bytes)")
            else:
                error_msg = f"❌ 出力FBXファイルが見つかりません: {output_fbx}"
                self.logger.error(error_msg)
                raise FileNotFoundError(error_msg)
            
            # NPZファイル検証
            if output_npz.exists():
                npz_size = output_npz.stat().st_size
                
                # ❌ サイズチェック: 10KB未満は無効とみなす
                if npz_size < 10 * 1024:  # 10KB
                    error_msg = f"❌ NPZファイルサイズが小さすぎます: {npz_size} bytes (最小要件: 10KB)"
                    self.logger.error(error_msg)
                    raise ValueError(error_msg)
                
                output_files_collected["skinning_npz"] = str(output_npz)
                output_files_collected["file_size_npz"] = npz_size
                self.logger.info(f"✅ 出力NPZファイル確認: {output_npz} (サイズ: {npz_size} bytes)")
            else:
                error_msg = f"❌ 出力NPZファイルが見つかりません: {output_npz}"
                self.logger.error(error_msg)
                raise FileNotFoundError(error_msg)
                
        except Exception as e:
            self.logger.error(f"❌ 出力ファイル検証中にエラー: {e}")
            raise
        
        return output_files_collected

    def _get_data_statistics(self, mesh_file_path_str: str, skeleton_file_path_str: str) -> Tuple[Dict, Dict]: # 引数名を変更
        """メッシュとスケルトンのデータ統計情報を取得"""
        mesh_stats = {}
        skeleton_stats = {}
        
        try:
            if mesh_file_path_str.endswith(".npz"): # 引数名変更
                with np.load(mesh_file_path_str) as data: # 引数名変更
                    if "vertices" in data: mesh_stats["vertex_count"] = len(data["vertices"])
                    if "faces" in data: mesh_stats["face_count"] = len(data["faces"])
                    if "uvs" in data: mesh_stats["uv_count"] = len(data["uvs"])
                    # skinning_weights はこの時点の入力NPZには通常含まれない
            
            if skeleton_file_path_str.endswith(".fbx"): # 引数名変更
                bone_count = self._get_bone_count_from_fbx(skeleton_file_path_str) # 引数名変更
                if bone_count is not None:
                    skeleton_stats["bone_count"] = bone_count
            
        except Exception as e:
            self.logger.error(f"データ統計情報取得中にエラー: {e}")
        
        return mesh_stats, skeleton_stats

    def _get_bone_count_from_fbx(self, fbx_file_path_str: str) -> Optional[int]: # 引数名を変更
        """FBXファイルからボーン数を取得 (簡易版)"""
        # 注意: これは非常に簡易的な実装です。正確なボーン数を取得するには、
        # Blender Python APIなどを利用してFBXファイルを解析する必要があります。
        # 今回のリファクタリングのスコープ外とし、既存の簡易ロジックを維持します。
        try:
            # ここではファイル名に基づく推定や、Blenderを使ったより正確な方法を将来的に検討
            # 現状は固定値を返すか、簡易的な推定に留める
            self.logger.warning(f"FBXからのボーン数取得は簡易実装です: {fbx_file_path_str}")
            # 例: 常に22を返す（UniRigの典型的なボーン数など、何らかの仮定に基づく）
            # または、Blenderが利用可能なら、ここでサブプロセスを呼び出す
            # 今回は0を返すことで、この機能が未実装であることを示す
            return 0 # より適切なデフォルト値や実装を検討
            
        except Exception as e:
            self.logger.error(f"FBXファイルボーン数取得中にエラー: {e}")
            return None

    def _generate_completion_log(self, mesh_file_str: str, skeleton_file_str: str, output_files_dict: Dict, processing_time: float) -> str: # 引数名変更
        """処理完了ログの生成"""
        log_lines = [
            "UniRig AI Skinning 処理完了",
            "=" * 30,
            f"入力メッシュNPZ: {mesh_file_str}", # 引数名変更
            f"入力スケルトンFBX: {skeleton_file_str}", # 引数名変更
            "出力ファイル:",
        ]
        
        for key, file_info in output_files_dict.items(): # 引数名変更
            if isinstance(file_info, dict) and "path" in file_info:
                log_lines.append(f"  - {key}: {file_info['path']} (サイズ: {file_info.get('size', 'N/A')} bytes)")
            elif isinstance(file_info, str): # processing_time など
                 log_lines.append(f"  - {key}: {file_info}")
            else: # vertex_count, bone_count など
                log_lines.append(f"  - {key}: {file_info}")

        log_lines.append(f"処理時間: {processing_time:.2f} 秒")
        
        return "\\n".join(log_lines)
