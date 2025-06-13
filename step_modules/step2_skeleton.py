"""
Step 2 Module - スケルトン生成
独立した実行機能として、AIによるスケルトン構造を生成

責務: メッシュデータ → スケルトンFBX + スケルトンデータ
入力: メッシュデータファイルパス (.npz), 性別設定
出力: スケルトンFBXファイルパス, スケルトンデータファイルパス (.npz)
"""

import os
import sys
import logging
import subprocess
import time
from pathlib import Path
from typing import Tuple, Dict, Optional, Any
import json # Not strictly used, but good for potential metadata
import numpy as np
import shutil

# UniRigパッケージへのパス設定
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/src')

# Default logger setup if no logger is provided
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class Step2Skeleton:
    """Step 2: スケルトン生成モジュール"""
    
    def __init__(self, output_dir: Path, logger_instance: Optional[logging.Logger] = None):
        self.output_dir = output_dir # This is the step-specific output dir, e.g., /app/pipeline_work/model_name/02_skeleton_generated/
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger_instance if logger_instance else logging.getLogger(__name__)
        
        # UniRigのコアスクリプトが特定のベースディレクトリ構造を期待する場合がある
        # 例: dataset_inference_clean/{model_name}/raw_data.npz
        # このパスはUniRigのrun.pyや関連スクリプトの内部実装に依存する
        self.unirig_processing_base_dir = Path("/app/dataset_inference_clean") 
        self.unirig_processing_base_dir.mkdir(parents=True, exist_ok=True)
        
    def generate_skeleton(self, 
                          input_npz_path: Path, 
                          model_name: str, 
                          original_model_file_for_fbx_copy: Path, 
                          gender: str = "neutral"
                         ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        スケルトン生成の実行。
        UniRigのrun.pyを呼び出して predict_skeleton.npz を生成し、
        入力モデルファイル (FBX/GLB) を {model_name}.fbx としてコピーする。
        
        Args:
            input_npz_path: 入力メッシュNPZファイルパス (例: Step1出力の raw_data.npz の絶対パス)
            model_name: モデル名（出力ファイル名やUniRig処理ディレクトリ名に使用）
            original_model_file_for_fbx_copy: スケルトンを持たないベースFBXとしてコピーする元のモデルファイルパス
                                              (例: Step1が作業ディレクトリにコピーした入力モデルファイルの絶対パス)
            gender: 性別設定 ("male", "female", "neutral") - 現在UniRigのスクリプトでは直接使用されていない可能性あり
            
        Returns:
            (success, logs, output_files dict)
        """
        logs = ""
        try:
            start_time = time.time()
            self.logger.info(f"Step 2 開始: 入力NPZ '{input_npz_path}', モデル名 '{model_name}', 性別 '{gender}'")
            self.logger.info(f"FBXコピー元: '{original_model_file_for_fbx_copy}'")
            
            if not input_npz_path.exists():
                error_msg = f"❌ 入力メッシュNPZファイルが見つかりません: {input_npz_path}"
                self.logger.error(error_msg)
                return False, error_msg, {}
            
            if not original_model_file_for_fbx_copy.exists():
                error_msg = f"❌ FBXコピー元のファイルが見つかりません: {original_model_file_for_fbx_copy}"
                self.logger.error(error_msg)
                return False, error_msg, {}

            # --- UniRig処理用のディレクトリと入力ファイルの準備 ---
            # UniRigのrun.pyは特定のディレクトリ構造 (dataset_inference_clean/{model_name}/) を期待する
            unirig_model_processing_dir = self.unirig_processing_base_dir / model_name
            unirig_model_processing_dir.mkdir(parents=True, exist_ok=True)
            logs += f"⚙️ UniRig処理ディレクトリ準備完了: '{unirig_model_processing_dir}'\\n"

            # Step1から受け取った raw_data.npz を UniRig処理ディレクトリにコピー
            unirig_input_npz_target = unirig_model_processing_dir / "raw_data.npz"
            shutil.copy2(input_npz_path, unirig_input_npz_target)
            logs += f"📋 入力NPZ '{input_npz_path.name}' をUniRig処理ディレクトリにコピー: '{unirig_input_npz_target}'\\n"

            # --- UniRigスケルトン生成スクリプト実行 ---
            success_script, script_logs = self._run_unirig_skeleton_script(
                model_name, unirig_model_processing_dir
            )
            logs += script_logs
            
            if not success_script:
                error_msg = f"❌ UniRigスケルトン生成スクリプト実行失敗。"
                self.logger.error(error_msg + " 詳細はログ参照。")
                return False, logs, {}
            
            # --- 生成されたファイルの検証と整理 ---
            # UniRigは unirig_model_processing_dir に predict_skeleton.npz を出力するはず
            generated_npz_in_unirig_dir = unirig_model_processing_dir / "predict_skeleton.npz"
            
            if not generated_npz_in_unirig_dir.exists():
                error_msg = f"❌ UniRigが期待されるNPZファイル '{generated_npz_in_unirig_dir}' を生成しませんでした。"
                self.logger.error(error_msg)
                self._debug_list_directory_contents(unirig_model_processing_dir) # デバッグ情報
                return False, logs + error_msg + "\\n", {}
            
            logs += f"✅ UniRigがNPZファイルを生成: '{generated_npz_in_unirig_dir}'\\n"

            # 生成された predict_skeleton.npz をこのステップの出力ディレクトリにコピー
            final_output_npz = self.output_dir / "predict_skeleton.npz" # 固定名
            shutil.copy2(generated_npz_in_unirig_dir, final_output_npz)
            logs += f"📋 生成されたNPZをStep2出力ディレクトリにコピー: '{final_output_npz}'\\n"

            # original_model_file_for_fbx_copy をこのステップの出力ディレクトリに {model_name}.fbx としてコピー
            final_output_fbx = self.output_dir / f"{model_name}.fbx" # サフィックスなし
            shutil.copy2(original_model_file_for_fbx_copy, final_output_fbx)
            logs += f"📋 FBXコピー元 '{original_model_file_for_fbx_copy.name}' をStep2出力ディレクトリにコピー: '{final_output_fbx}'\\n"
            
            # ボーン階層テキストファイル生成 (final_output_npz から)
            bones_txt_path_str = self._generate_bones_txt_from_npz(final_output_npz, model_name)
            if bones_txt_path_str:
                logs += f"📄 ボーン階層テキストファイル生成: '{bones_txt_path_str}'\\n"
            else:
                logs += f"⚠️ ボーン階層テキストファイルの生成に失敗。\\n"

            processing_time = time.time() - start_time
            
            output_files: Dict[str, Any] = {
                "skeleton_fbx": str(final_output_fbx),
                "skeleton_npz": str(final_output_npz),
                "bones_txt": bones_txt_path_str,
                "bone_count": self._count_bones_in_npz_file(final_output_npz),
                "file_size_fbx": final_output_fbx.stat().st_size if final_output_fbx.exists() else 0,
                "file_size_npz": final_output_npz.stat().st_size if final_output_npz.exists() else 0,
                "processing_time_seconds": round(processing_time, 2)
            }
            
            final_log_message = f"Step 2 (スケルトン生成) 完了:\n"
            final_log_message += f"- 入力NPZ: {input_npz_path.name}\n"
            final_log_message += f"- FBXコピー元: {original_model_file_for_fbx_copy.name}\n"
            final_log_message += f"- 処理時間: {processing_time:.2f}秒\n"
            final_log_message += f"- 出力FBX: {output_files['skeleton_fbx']} ({output_files['file_size_fbx']:,} bytes)\n"
            final_log_message += f"- 出力NPZ: {output_files['skeleton_npz']} ({output_files['file_size_npz']:,} bytes)\n"
            final_log_message += f"- ボーン数 (推定): {output_files['bone_count']}\n"
            if output_files['bones_txt']:
                final_log_message += f"- ボーン階層ファイル: {output_files['bones_txt']}\n"
            logs += "\\n" + final_log_message
            
            self.logger.info(f"Step 2 正常完了。出力FBX: '{output_files['skeleton_fbx']}', 出力NPZ: '{output_files['skeleton_npz']}'")
            return True, logs, output_files
            
        except Exception as e:
            error_msg = f"❌ Step 2 スケルトン生成中に予期せぬエラー: {type(e).__name__} - {e}"
            self.logger.error(error_msg, exc_info=True)
            return False, logs + error_msg + "\\n", {}
    
    def _run_unirig_skeleton_script(self, model_name: str, unirig_model_processing_dir: Path) -> Tuple[bool, str]:
        """
        UniRigのスケルトン生成スクリプト(run.py)を実行。
        
        Args:
            model_name: モデル名 (UniRigのデータリストで使用)
            unirig_model_processing_dir: UniRigがNPZを読み書きするディレクトリ (例: /app/dataset_inference_clean/{model_name})
                                         このディレクトリには事前に raw_data.npz が配置されている必要がある。
        Returns:
            (success, logs)
        """
        logs = ""
        try:
            env = os.environ.copy()
            env['PYTHONPATH'] = '/app:/app/src' # UniRigのインポート解決のため
            # env['CUDA_VISIBLE_DEVICES'] = '0' # 必要に応じてGPU指定
            
            # UniRigの推論タスク設定ファイル (固定値を想定)
            # 指示書によると generate_skeleton.sh は quick_inference_skeleton_articulationxl_ar_256.yaml を使用
            task_config_file = "configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml"
            seed = 12345 # 固定シード
            
            # UniRigのrun.pyは、処理対象のモデル名をリストしたファイルを必要とする
            datalist_file_path = unirig_model_processing_dir / "inference_datalist.txt"
            with open(datalist_file_path, 'w') as f:
                f.write(model_name) # UniRigはモデル名 (ディレクトリ名と一致) を期待
            logs += f"ℹ️ UniRig用データリストファイル作成: '{datalist_file_path}' (内容: {model_name})\\n"

            cmd = [
                sys.executable, "run.py",
                f"--task={task_config_file}",
                f"--seed={seed}",
                f"--npz_dir={str(unirig_model_processing_dir)}",    # NPZ読み込み元 (raw_data.npz)
                f"--output_dir={str(unirig_model_processing_dir)}" # NPZ出力先 (predict_skeleton.npz)
            ]
            
            logs += f"🚀 UniRigスケルトン生成コマンド実行: {' '.join(cmd)}\\n"
            self.logger.info(f"UniRigコマンド: {' '.join(cmd)}")
            self.logger.info(f"UniRig処理ディレクトリ (CWD /app): '{unirig_model_processing_dir}'")
            
            process_start_time = time.time()
            result = subprocess.run(
                cmd,
                cwd='/app', # UniRigスクリプトは /app からの相対パス (configs/* など) を期待
                env=env,
                capture_output=True,
                text=True,
                timeout=600  # 10分タイムアウト (以前は5分だったが、複雑なモデル対応で延長)
            )
            process_execution_time = time.time() - process_start_time
            logs += f"⏱️ UniRigスクリプト実行時間: {process_execution_time:.2f}秒\\n"
            
            if result.returncode == 0:
                success_msg = f"✅ UniRigスケルトン生成スクリプト正常終了 (コード: {result.returncode})\\n"
                if result.stdout:
                    success_msg += f"STDOUT:\\n{result.stdout}\\n"
                if result.stderr: # 時々stderrにも情報が出ることがある
                    success_msg += f"STDERR (情報用):\\n{result.stderr}\\n"
                self.logger.info("UniRigスクリプト正常終了。")
                logs += success_msg
                return True, logs
            else:
                error_msg = f"❌ UniRigスケルトン生成スクリプトエラー (コード: {result.returncode})\\n"
                if result.stdout:
                    error_msg += f"STDOUT:\\n{result.stdout}\\n"
                if result.stderr:
                    error_msg += f"STDERR:\\n{result.stderr}\\n"
                self.logger.error(f"UniRigスクリプトエラー。詳細はログ参照。Return code: {result.returncode}")
                logs += error_msg
                return False, logs
                
        except subprocess.TimeoutExpired:
            timeout_msg = "❌ UniRigスケルトン生成スクリプトがタイムアウトしました (10分)"
            self.logger.error(timeout_msg)
            return False, logs + timeout_msg + "\\n"
        except Exception as e:
            exec_error_msg = f"❌ UniRigスケルトン生成スクリプト実行中に予期せぬエラー: {type(e).__name__} - {e}"
            self.logger.error(exec_error_msg, exc_info=True)
            return False, logs + exec_error_msg + "\\n"
    
    def _debug_list_directory_contents(self, directory_path: Path):
        """デバッグ用：指定されたディレクトリの内容をログに出力"""
        if directory_path.exists() and directory_path.is_dir():
            try:
                files = os.listdir(directory_path)
                self.logger.debug(f"ディレクトリ '{directory_path}' の内容: {files}")
                for item in files:
                    item_path = directory_path / item
                    if item_path.is_dir():
                        sub_files = os.listdir(item_path)
                        self.logger.debug(f"  サブディレクトリ '{item_path}' の内容: {sub_files}")
            except Exception as e:
                self.logger.error(f"ディレクトリリスト取得エラー '{directory_path}': {e}")
        else:
            self.logger.debug(f"ディレクトリが存在しないか、ディレクトリではありません: '{directory_path}'")

    def _generate_bones_txt_from_npz(self, npz_file_path: Path, model_name: str) -> Optional[str]:
        """
        指定されたNPZファイルからボーン階層テキストファイルを生成し、NPZファイルと同じディレクトリに保存。
        """
        if not npz_file_path.exists():
            self.logger.error(f"ボーン階層テキスト生成失敗: NPZファイル '{npz_file_path}' が見つかりません。")
            return None
        
        bones_txt_output_path = npz_file_path.with_name(f"{model_name}_bones.txt")
        
        try:
            data = np.load(npz_file_path, allow_pickle=True)
            bone_count = 0
            content = f"# Bone Hierarchy for {model_name}\\n"
            content += f"# Generated from: {npz_file_path.name}\\n\\n"
            
            key_details = []
            for key in data.files:
                try:
                    array_data = data[key]
                    key_details.append(f"{key}: shape={array_data.shape}, dtype={array_data.dtype}")
                    if 'joint' in key.lower() or 'bone' in key.lower():
                        if hasattr(array_data, 'shape') and len(array_data.shape) > 0:
                            bone_count = max(bone_count, array_data.shape[0])
                except Exception as e_read:
                    key_details.append(f"{key}: <読み込みエラー: {e_read}>")
            content += "\\n".join(key_details) + "\\n"
            
            if bone_count == 0: # NPZから直接的なボーン数を特定できなかった場合
                bone_count = self._estimate_bone_count_from_mesh_data(data)
                content += f"\\nEstimated bone count (from mesh data): {bone_count}\\n"
            else:
                content += f"\\nTotal bones (from joint/bone keys): {bone_count}\\n"
            
            content += f"\\nBone list (example names):\\n"
            for i in range(bone_count):
                content += f"bone_{i:02d}\\n"
            
            with open(bones_txt_output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.logger.info(f"ボーン階層テキスト生成成功: '{bones_txt_output_path}' (ボーン数: {bone_count})")
            return str(bones_txt_output_path)
            
        except Exception as e_gen:
            self.logger.error(f"ボーン階層テキスト生成中にエラー ('{npz_file_path}'): {e_gen}", exc_info=True)
            # エラー時でも、推定ボーン数でデフォルトファイルを作成試行
            try:
                estimated_bone_count = self._estimate_bone_count_from_mesh_data(np.load(npz_file_path, allow_pickle=True) if npz_file_path.exists() else None)
                fallback_content = f"# Bone Hierarchy for {model_name}\\n"
                fallback_content += f"# Generated with estimated bone count (NPZ read/parse error: {e_gen})\\n\\n"
                fallback_content += f"Total bones (estimated): {estimated_bone_count}\\n\\nBone list (example names):\\n"
                for i in range(estimated_bone_count):
                    fallback_content += f"bone_{i:02d}\\n"
                with open(bones_txt_output_path, 'w', encoding='utf-8') as f:
                    f.write(fallback_content)
                self.logger.info(f"フォールバックのボーン階層テキスト生成: '{bones_txt_output_path}' (推定ボーン数: {estimated_bone_count})")
                return str(bones_txt_output_path)
            except Exception as e_fallback:
                self.logger.error(f"フォールバックのボーン階層テキスト生成も失敗: {e_fallback}")
                return None
    
    def _count_bones_in_npz_file(self, npz_file_path: Optional[Path]) -> int:
        """NPZファイル内のボーン数をカウント (推定含む)"""
        if not npz_file_path or not npz_file_path.exists():
            return 0
        try:
            data = np.load(npz_file_path, allow_pickle=True)
            bone_count = 0
            for key in ['joints', 'bones', 'positions', 'joint_positions', 'keypoints']:
                if key in data:
                    if hasattr(data[key], 'shape') and len(data[key].shape) > 0:
                        bone_count = max(bone_count, data[key].shape[0])
                        if bone_count > 0: return bone_count # 最初に見つかった有効なキーで返す
            
            # 上記で見つからなければメッシュデータから推定
            return self._estimate_bone_count_from_mesh_data(data)
        except Exception as e:
            self.logger.error(f"NPZからのボーン数カウントエラー ('{npz_file_path}'): {e}")
            return 0 # エラー時は0を返す
    
    def _estimate_bone_count_from_mesh_data(self, npz_data: Optional[np.lib.npyio.NpzFile]) -> int:
        """NPZデータ内のメッシュ複雑度に基づいてボーン数を推定"""
        if npz_data is None:
            return 30 # デフォルト値 (人間型を想定した最小限)
        try:
            vertices = npz_data.get('vertices', npz_data.get('points', npz_data.get('v', None)))
            if vertices is None:
                self.logger.warning("NPZ内に頂点データが見つからず、ボーン数推定にデフォルト値を使用")
                return 30
            
            vertex_count = len(vertices)
            # faces = npz_data.get('faces', npz_data.get('triangles', npz_data.get('f', None)))
            # face_count = len(faces) if faces is not None else vertex_count // 2 # 簡略化

            # 頂点数に基づく単純なスケーリングルール（調整が必要）
            if vertex_count < 1000: estimated_bones = 20  # 非常に単純
            elif vertex_count < 5000: estimated_bones = 30 # 単純 (e.g., low-poly human)
            elif vertex_count < 15000: estimated_bones = 50 # 標準 (e.g., bird, standard human)
            elif vertex_count < 50000: estimated_bones = 70 # 複雑 (e.g., winged creature)
            elif vertex_count < 100000: estimated_bones = 100 # 非常に複雑 (e.g., detailed monster)
            else: estimated_bones = min(150, max(120, vertex_count // 1000)) # 超高複雑
            
            self.logger.info(f"メッシュデータからのボーン数推定: 頂点数={vertex_count} -> 推定ボーン数={estimated_bones}")
            return estimated_bones
        except Exception as e:
            self.logger.error(f"メッシュデータからのボーン数推定エラー: {e}", exc_info=True)
            return 30 # エラー時はデフォルト値

# モジュール実行関数（app.pyから呼び出される）
def execute_step2(
    input_npz_path: Path, 
    model_name: str, 
    step_output_dir: Path, 
    original_model_file_for_fbx_copy: Path,
    logger_instance: logging.Logger,
    gender: str = "neutral"
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Step 2実行のエントリーポイント。
    
    Args:
        input_npz_path: 入力メッシュNPZファイルパス (絶対パス、例: /app/pipeline_work/{model_name}/01_extracted_mesh/raw_data.npz)
        model_name: モデル名
        step_output_dir: このステップ専用の出力ディレクトリパス (絶対パス、例: /app/pipeline_work/{model_name}/02_skeleton_generated/)
        original_model_file_for_fbx_copy: FBXとしてコピーする元のモデルファイル (絶対パス、例: /app/pipeline_work/{model_name}/01_extracted_mesh/{model_name}.glb)
        logger_instance: app.pyから渡されるロガーインスタンス
        gender: 性別設定 (現在はUniRigスクリプトで明示的に使用されていない可能性が高い)
        
    Returns:
        (success, logs, output_files dict)
    """
    try:
        generator = Step2Skeleton(output_dir=step_output_dir, logger_instance=logger_instance)
        return generator.generate_skeleton(
            input_npz_path=input_npz_path,
            model_name=model_name,
            original_model_file_for_fbx_copy=original_model_file_for_fbx_copy,
            gender=gender
        )
    except Exception as e:
        error_message = f"Step 2 実行準備中に予期せぬエラーが発生: {type(e).__name__} - {e}"
        logger_instance.error(error_message, exc_info=True)
        return False, error_message, {}

if __name__ == '__main__':
    # --- テスト設定 ---
    test_logger = logging.getLogger("Step2Skeleton_Test")
    test_logger.setLevel(logging.DEBUG)
    test_handler = logging.StreamHandler(sys.stdout)
    test_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    test_logger.addHandler(test_handler)
    test_logger.propagate = False

    test_model_name = "test_bird_step2" 
    pipeline_base_dir = Path("/app/pipeline_work") # 実際のパイプラインと同じベースディレクトリ

    # --- Step1の出力物を模倣 --- (本来はStep1が生成する)
    # Step1の出力ディレクトリ (このテストではStep2がここから読み込むと仮定)
    mock_step1_output_dir = pipeline_base_dir / test_model_name / "01_extracted_mesh"
    mock_step1_output_dir.mkdir(parents=True, exist_ok=True)

    # Step1が出力するであろう raw_data.npz (ダミー)
    mock_input_npz = mock_step1_output_dir / "raw_data.npz"
    # UniRigのスケルトン生成が期待する可能性のあるキーをいくつか含める
    np.savez_compressed(mock_input_npz, 
                        vertices=np.random.rand(100,3).astype(np.float32), 
                        faces=np.random.randint(0,100,size=(150,3)).astype(np.int32),
                        v=np.random.rand(100,3).astype(np.float32), # alias for vertices
                        f=np.random.randint(0,100,size=(150,3)).astype(np.int32), # alias for faces
                        points=np.random.rand(100,3).astype(np.float32) # another alias
                       )
    test_logger.info(f"模倣したStep1 NPZ出力: '{mock_input_npz}' (存在: {mock_input_npz.exists()})")

    # Step1が作業ディレクトリにコピーしたであろう入力モデルファイル (ダミーGLB)
    mock_original_model_in_step1_dir = mock_step1_output_dir / f"{test_model_name}.glb"
    with open(mock_original_model_in_step1_dir, 'w') as f:
        f.write("dummy glb content for Step2 test")
    test_logger.info(f"模倣したStep1 FBXコピー元: '{mock_original_model_in_step1_dir}' (存在: {mock_original_model_in_step1_dir.exists()})")

    # --- Step2の出力ディレクトリ設定 ---
    step2_output_dir = pipeline_base_dir / test_model_name / "02_skeleton_generated"
    if step2_output_dir.exists():
        test_logger.info(f"既存のStep2テスト出力ディレクトリ '{step2_output_dir}' をクリーンアップします。")
        shutil.rmtree(step2_output_dir)
    step2_output_dir.mkdir(parents=True, exist_ok=True)
    test_logger.info(f"Step2 出力ディレクトリ: '{step2_output_dir}'")

    # --- UniRig処理用ディレクトリの準備 (dataset_inference_clean/{model_name}) ---
    # これはStep2Skeletonクラスのコンストラクタでも作成されるが、テスト前にクリーンにしておくと良い
    unirig_processing_dir_for_test = Path(f"/app/dataset_inference_clean/{test_model_name}")
    if unirig_processing_dir_for_test.exists():
        shutil.rmtree(unirig_processing_dir_for_test)
    # unirig_processing_dir_for_test.mkdir(parents=True, exist_ok=True) # クラス内で作成されるので不要
    test_logger.info(f"UniRig処理ディレクトリ (テスト前クリーンアップ): '{unirig_processing_dir_for_test}'")

    test_logger.info(f"--- Step2Skeleton モジュールテスト開始 ---")
    success, logs_output, files_output = execute_step2(
        input_npz_path=mock_input_npz,
        model_name=test_model_name,
        step_output_dir=step2_output_dir,
        original_model_file_for_fbx_copy=mock_original_model_in_step1_dir,
        logger_instance=test_logger,
        gender="neutral"
    )
    
    test_logger.info("\\n--- テスト実行結果 ---")
    test_logger.info(f"  成功: {success}")
    test_logger.info(f"  ログ:\\n{logs_output}")
    test_logger.info(f"  出力ファイル情報: {json.dumps(files_output, indent=2)}")

    if success:
        test_logger.info("テスト成功。生成されたファイルを確認してください:")
        # test_logger.info(f"  - FBX: \'{files_output[\"skeleton_fbx\"]}\' (存在: {Path(files_output[\"skeleton_fbx\"]).exists()})")
        # test_logger.info(f"  - NPZ: \'{files_output[\"skeleton_npz\"]}\' (存在: {Path(files_output[\"skeleton_npz\"]).exists()})")
        # test_logger.info(f"  - TXT: \'{files_output[\"bones_txt\"]}\' (存在: True)")
        test_logger.info(f"  - FBX: \'{files_output['skeleton_fbx']}\' (存在: {Path(files_output['skeleton_fbx']).exists()})")
        test_logger.info(f"  - NPZ: \'{files_output['skeleton_npz']}\' (存在: {Path(files_output['skeleton_npz']).exists()})")
        test_logger.info(f"  - TXT: \'{files_output['bones_txt']}\' (存在: True)")
        test_logger.info("テスト用のexecute_step2の実行が正常に完了しました。")
    else:
        test_logger.error("テスト失敗。ログを確認してください。")

    # クリーンアップ: テストで作成した dataset_inference_clean 内のモデルディレクトリ
    # if unirig_processing_dir_for_test.exists():
    #     shutil.rmtree(unirig_processing_dir_for_test)
    #     test_logger.info(f"クリーンアップ: UniRig処理ディレクトリ '{unirig_processing_dir_for_test}' を削除しました。")
    # Note: 出力ファイルは手動で確認・削除することを推奨するため、ここでは自動削除しない。
    # 特に失敗時は原因究明のために残しておくと良い。

    test_logger.info("--- Step2Skeleton モジュールテスト完了 ---")
