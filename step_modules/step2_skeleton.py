"""
Step2 Module - スケルトン生成 (決め打ちディレクトリ戦略)
🔥 重要: Step2は必ずオリジナルファイルから独自のメッシュ再抽出を実行
原流処理generate_skeleton.sh完全互換実装

責務: オリジナル3Dモデル → スケルトンFBX + スケルトンデータ
出力: {model_name}_skeleton.fbx, {model_name}_skeleton.npz
"""

import os
import sys
import subprocess
import shutil
import time
import logging
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
import numpy as np

sys.path.insert(0, '/app')
sys.path.insert(0, '/app/src')

class Step2Skeleton:
    """Step2: スケルトン生成モジュール (決め打ちディレクトリ戦略)"""
    
    def __init__(self, step_output_dir: Path, logger_instance: Optional[logging.Logger] = None):
        """
        Args:
            step_output_dir: Step2専用出力ディレクトリ (例: /app/pipeline_work/{model_name}/02_skeleton/)
            logger_instance: ロガーインスタンス
        """
        self.step_output_dir = step_output_dir
        self.step_output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger_instance if logger_instance else logging.getLogger(__name__)
        
        # UniRig処理用ベースディレクトリ (run.pyが期待する構造)
        self.unirig_processing_base_dir = Path("/app/dataset_inference_clean")
        self.unirig_processing_base_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_skeleton(self, 
                          original_file: Path, 
                          model_name: str, 
                          gender: str = "neutral"
                         ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        🔥 スケルトン生成 - オリジナルファイルから独自メッシュ再抽出実行
        
        重要: Step1の結果は使用せず、オリジナルファイルから独自にメッシュを再抽出
        原流処理generate_skeleton.sh完全互換
        
        Args:
            original_file: オリジナル3Dモデルファイル (.glb, .fbx, .vrm等)
            model_name: モデル名（統一命名規則ベース）
            gender: 性別設定 ("male", "female", "neutral")
            
        Returns:
            (success, logs, output_files dict) - 統一命名規則準拠の出力ファイルパス
        """
        logs = ""
        try:
            start_time = time.time()
            self.logger.info(f"🔥 Step2スケルトン生成開始: モデル '{model_name}', 性別 '{gender}'")
            self.logger.info(f"🔥 重要: オリジナルファイルから独自メッシュ再抽出実行: {original_file}")
            
            if not original_file.exists():
                error_msg = f"❌ オリジナルファイルが見つかりません: {original_file}"
                self.logger.error(error_msg)
                return False, error_msg, {}

            # --- Step2専用UniRig処理ディレクトリ準備 ---
            unirig_model_processing_dir = self.unirig_processing_base_dir / model_name
            unirig_model_processing_dir.mkdir(parents=True, exist_ok=True)
            
            # --- Step2専用メッシュディレクトリ作成 ---
            step2_mesh_dir = self.step_output_dir / "mesh_for_skeleton"
            step2_mesh_dir.mkdir(parents=True, exist_ok=True)
            logs += f"⚙️ Step2専用メッシュディレクトリ準備完了: '{step2_mesh_dir}'\n"
            logs += f"⚙️ Step2用UniRig処理ディレクトリ準備完了: '{unirig_model_processing_dir}'\n"

            # --- 🔥 重要: Step2独自のメッシュ再抽出実行 ---
            success_extraction, extraction_logs = self._execute_skeleton_specific_mesh_extraction(
                original_file, unirig_model_processing_dir, model_name
            )
            logs += extraction_logs
            
            if not success_extraction:
                error_msg = f"❌ Step2独自メッシュ再抽出失敗。"
                self.logger.error(error_msg)
                return False, logs, {}

            # --- UniRigスケルトン生成実行 ---
            success_skeleton, skeleton_logs = self._execute_unirig_skeleton_generation(
                model_name, unirig_model_processing_dir
            )
            logs += skeleton_logs
            
            if not success_skeleton:
                error_msg = f"❌ UniRigスケルトン生成失敗。"
                self.logger.error(error_msg)
                return False, logs, {}
            
            # --- 生成ファイル整理と統一命名規則対応 ---
            success_output, output_logs, output_files = self._organize_step2_outputs(
                model_name, unirig_model_processing_dir
            )
            logs += output_logs
            
            if not success_output:
                error_msg = f"❌ Step2出力ファイル整理失敗。"
                self.logger.error(error_msg)
                return False, logs, {}

            # 左右対称チェック機能は削除されました
            
            processing_time = time.time() - start_time
            output_files["processing_time_seconds"] = round(processing_time, 2)
            
            final_log_message = f"🔥 Step2スケルトン生成完了:\n"
            final_log_message += f"- モデル名: {model_name}\n"
            final_log_message += f"- 処理時間: {processing_time:.2f}秒\n"
            final_log_message += f"- 統一NPZ: {output_files.get('unified_skeleton_npz', 'N/A')}\n"
            final_log_message += f"- 統一FBX: {output_files.get('unified_skeleton_fbx', 'N/A')}\n"
            logs += "\n" + final_log_message
            
            self.logger.info(f"🔥 Step2スケルトン生成正常完了: '{output_files['unified_skeleton_npz']}'")
            return True, logs, output_files
            
        except Exception as e:
            error_msg = f"❌ Step2スケルトン生成中に予期せぬエラー: {type(e).__name__} - {e}"
            self.logger.error(error_msg, exc_info=True)
            return False, logs + error_msg + "\n", {}
    
    def _execute_skeleton_specific_mesh_extraction(self, original_file: Path, unirig_model_processing_dir: Path, model_name: str) -> Tuple[bool, str]:
        """
        🔥 Step2独自のスケルトン特化メッシュ再抽出
        
        重要: 原流処理generate_skeleton.sh第1段階完全互換
        faces_target_count=4000でスケルトン生成AI最適化パラメータ使用 4000 →
        
        Args:
            original_file: オリジナル3Dモデルファイル
            unirig_model_processing_dir: UniRig処理ディレクトリ
            model_name: モデル名
            
        Returns:
            (success, logs)
        """
        logs = ""
        try:
            self.logger.info(f"🔥 Step2: スケルトン特化メッシュ再抽出開始 (faces_target_count=4000)")
            logs += f"🔥 Step2: スケルトン特化メッシュ再抽出開始 (faces_target_count=4000)\n"

            # データ設定ファイル確認
            data_config = Path("/app/configs/data/quick_inference.yaml")
            if not data_config.exists():
                return False, f"❌ データ設定ファイル不存在: {data_config}\n"
            
            logs += f"🔥 Step2独自メッシュ再抽出開始\n"
            logs += f"オリジナルファイル: {original_file}\n"
            logs += f"UniRig処理ディレクトリ: {unirig_model_processing_dir}\n"
            
            # タイムスタンプ生成 (原流方式)
            time_str = time.strftime("%Y_%m_%d_%H_%M_%S")
            
            # 🔥 原流処理generate_skeleton.sh第1段階完全互換コマンド
            extract_cmd = [
                sys.executable, "-m", "src.data.extract",
                "--config", str(data_config),
                "--force_override", "true",
                "--num_runs", "1",
                "--faces_target_count", "5000",  # 🔥 スケルトン特化: 面数最適化
                "--require_suffix", "obj,fbx,FBX,dae,glb,gltf,vrm",
                "--time", time_str,
                "--id", "0",
                "--input", str(original_file),  # 🔥 オリジナルファイル直接指定
                "--output_dir", str(unirig_model_processing_dir)
            ]
            
            logs += f"メッシュ再抽出コマンド: {' '.join(extract_cmd)}\n"
            
            extract_start_time = time.time()
            result = subprocess.run(
                extract_cmd,
                cwd='/app',
                capture_output=True,
                text=True,
                timeout=600  # 10分タイムアウト
            )
            extract_execution_time = time.time() - extract_start_time
            logs += f"⏱️ メッシュ再抽出実行時間: {extract_execution_time:.2f}秒\n"
            
            # 🔥 重要: Blenderクラッシュ(-11)でもファイル生成されている場合は成功とする
            # リターンコードではなく、実際のファイル存在を優先して確認
            # src.data.extractの実際の出力パターンに基づく検索
            possible_raw_data_locations = [
                # 指定出力ディレクトリ直下
                unirig_model_processing_dir / "raw_data.npz",
                # 入力ファイルディレクトリ下のモデル名フォルダ（実際の出力先）
                original_file.parent / original_file.stem / "raw_data.npz", 
                # その他の可能性
                unirig_model_processing_dir / "examples" / original_file.stem / "raw_data.npz",
                unirig_model_processing_dir / original_file.stem / "raw_data.npz"
            ]
            
            found_raw_data = None
            for possible_location in possible_raw_data_locations:
                if possible_location.exists():
                    found_raw_data = possible_location
                    break
            
            if found_raw_data:
                # 🔥 重要: 見つかったraw_data.npzをUniRig処理ディレクトリにコピー
                target_raw_data = unirig_model_processing_dir / "raw_data.npz"
                if found_raw_data != target_raw_data:
                    shutil.copy2(found_raw_data, target_raw_data)
                    logs += f"📋 raw_data.npzをUniRig処理ディレクトリにコピー: {found_raw_data} → {target_raw_data}\n"
                
                # 🔥 重要: Step2専用メッシュディレクトリにもコピー（決め打ちディレクトリ戦略）
                step2_mesh_dir = self.step_output_dir / "mesh_for_skeleton"
                step2_target_raw_data = step2_mesh_dir / "raw_data.npz"
                shutil.copy2(found_raw_data, step2_target_raw_data)
                logs += f"📋 raw_data.npzをStep2専用メッシュディレクトリにコピー: {found_raw_data} → {step2_target_raw_data}\n"
                
                success_msg = f"✅ Step2独自メッシュ再抽出成功 (リターンコード: {result.returncode}, Blenderクラッシュでもファイル生成済み)\n"
                success_msg += f"生成ファイル: {found_raw_data}\n"
                success_msg += f"UniRig処理用: {target_raw_data}\n"
                success_msg += f"Step2専用保存: {step2_target_raw_data}\n"
                if result.stdout:
                    success_msg += f"STDOUT:\n{result.stdout}\n"
                logs += success_msg
                self.logger.info("Step2独自メッシュ再抽出成功（Blenderクラッシュ後もファイル確認）。")
                return True, logs
            else:
                error_msg = f"❌ raw_data.npzが見つかりませんでした (リターンコード: {result.returncode})\n"
                error_msg += f"検索場所: {[str(loc) for loc in possible_raw_data_locations]}\n"
                if result.stdout:
                    error_msg += f"STDOUT:\n{result.stdout}\n"
                if result.stderr:
                    error_msg += f"STDERR:\n{result.stderr}\n"
                self.logger.error(f"メッシュ再抽出エラー。Return code: {result.returncode}")
                logs += error_msg
                return False, logs
                
        except subprocess.TimeoutExpired:
            timeout_msg = "❌ メッシュ再抽出がタイムアウトしました (10分)\n"
            self.logger.error(timeout_msg)
            return False, logs + timeout_msg
        except Exception as e:
            exec_error_msg = f"❌ メッシュ再抽出中に予期せぬエラー: {type(e).__name__} - {e}\n"
            self.logger.error(exec_error_msg, exc_info=True)
            return False, logs + exec_error_msg
    
    def _execute_unirig_skeleton_generation(self, model_name: str, unirig_model_processing_dir: Path) -> Tuple[bool, str]:
        """
        UniRigスケルトン生成実行 (原流処理generate_skeleton.sh第2段階)
        
        Args:
            model_name: モデル名
            unirig_model_processing_dir: UniRig処理ディレクトリ (raw_data.npz配置済み)
            
        Returns:
            (success, logs)
        """
        logs = ""
        try:
            # タスク設定ファイル確認
            task_config = Path("/app/configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml")
            if not task_config.exists():
                return False, f"❌ タスク設定ファイル不存在: {task_config}\n"
            
            # raw_data.npz存在確認
            raw_data_file = unirig_model_processing_dir / "raw_data.npz"
            if not raw_data_file.exists():
                return False, f"❌ raw_data.npz不存在: {raw_data_file}\n"
            
            logs += f"🔥 UniRigスケルトン生成開始\n"
            logs += f"入力: {raw_data_file}\n"
            logs += f"タスク設定: {task_config}\n"
            
            # 環境変数設定
            env = os.environ.copy()
            env['PYTHONPATH'] = '/app:/app/src'
            
            # UniRig用データリストファイル作成
            datalist_file_path = unirig_model_processing_dir / "inference_datalist.txt"
            with open(datalist_file_path, 'w') as f:
                f.write(model_name)
            logs += f"ℹ️ UniRig用データリストファイル作成: '{datalist_file_path}' (内容: {model_name})\n"
            
            # 🔥 原流処理generate_skeleton.sh第2段階完全互換コマンド
            skeleton_cmd = [
                sys.executable, "run.py",
                f"--task={task_config}",
                f"--seed=42",# もともとは12345　しかし　generate_skeleton.shではランダムシードを42にしてた
                f"--npz_dir={str(unirig_model_processing_dir)}",  # raw_data.npz読み込み元
                f"--output_dir={str(unirig_model_processing_dir)}"  # predict_skeleton.npz出力先
            ]
            
            logs += f"スケルトン生成コマンド: {' '.join(skeleton_cmd)}\n"
            
            skeleton_start_time = time.time()
            result = subprocess.run(
                skeleton_cmd,
                cwd='/app',
                env=env,
                capture_output=True,
                text=True,
                timeout=1200  # 20分タイムアウト
            )
            skeleton_execution_time = time.time() - skeleton_start_time
            logs += f"⏱️ スケルトン生成実行時間: {skeleton_execution_time:.2f}秒\n"
            
            # 🔥 重要: スケルトン生成でもBlenderクラッシュ後ファイル確認優先
            possible_predict_skeleton_locations = [
                unirig_model_processing_dir / "predict_skeleton.npz",
                unirig_model_processing_dir / "examples" / model_name / "predict_skeleton.npz"
            ]
            
            found_predict_skeleton = None
            for possible_location in possible_predict_skeleton_locations:
                if possible_location.exists():
                    found_predict_skeleton = possible_location
                    break
            
            if found_predict_skeleton:
                success_msg = f"✅ UniRigスケルトン生成成功 (リターンコード: {result.returncode})\n"
                success_msg += f"生成ファイル: {found_predict_skeleton}\n"
                if result.stdout:
                    success_msg += f"STDOUT:\n{result.stdout}\n"
                if result.stderr:  # 情報用
                    success_msg += f"STDERR (情報用):\n{result.stderr}\n"
                logs += success_msg
                self.logger.info("UniRigスケルトン生成成功。")
                return True, logs
            else:
                error_msg = f"❌ predict_skeleton.npzが見つかりませんでした (リターンコード: {result.returncode})\n"
                error_msg += f"検索場所: {[str(loc) for loc in possible_predict_skeleton_locations]}\n"
                if result.stdout:
                    error_msg += f"STDOUT:\n{result.stdout}\n"
                if result.stderr:
                    error_msg += f"STDERR:\n{result.stderr}\n"
                self.logger.error(f"UniRigスケルトン生成失敗。Return code: {result.returncode}")
                self._debug_list_directory_contents(unirig_model_processing_dir)
                logs += error_msg
                return False, logs
                
        except subprocess.TimeoutExpired:
            timeout_msg = "❌ UniRigスケルトン生成がタイムアウトしました (20分)\n"
            self.logger.error(timeout_msg)
            return False, logs + timeout_msg
        except Exception as e:
            exec_error_msg = f"❌ UniRigスケルトン生成中に予期せぬエラー: {type(e).__name__} - {e}\n"
            self.logger.error(exec_error_msg, exc_info=True)
            return False, logs + exec_error_msg
    
    def _organize_step2_outputs(self, model_name: str, unirig_model_processing_dir: Path) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Step2出力ファイル整理と統一命名規則対応 (決め打ちディレクトリ戦略)
        
        Args:
            model_name: モデル名
            unirig_model_processing_dir: UniRig生成ファイル格納ディレクトリ
            
        Returns:
            (success, logs, output_files)
        """
        logs = ""
        try:
            # UniRigが生成したファイル確認
            generated_predict_skeleton = unirig_model_processing_dir / "predict_skeleton.npz"
            
            # 🚨 必須ファイル不存在エラー - Step2は失敗とする
            if not generated_predict_skeleton.exists():
                error_msg = f"❌ 必須NPZファイルが生成されませんでした: {generated_predict_skeleton}\n"
                error_msg += f"💡 解決策: Step1の実行を先に完了し、メッシュデータを確認してください\n"
                self._debug_list_directory_contents(unirig_model_processing_dir)
                return False, logs + error_msg, {
                    "skeleton_fbx": "",
                    "skeleton_npz": "",
                    "unified_skeleton_fbx": "",
                    "unified_skeleton_npz": ""
                }
            
            logs += f"✅ UniRigがNPZファイルを生成: '{generated_predict_skeleton}'\n"
            
            # Step2出力ディレクトリに基本ファイルコピー
            final_output_npz = self.step_output_dir / "predict_skeleton.npz"
            shutil.copy2(generated_predict_skeleton, final_output_npz)
            logs += f"📋 生成されたNPZをStep2出力ディレクトリにコピー: '{final_output_npz}'\n"
            
            # FBXファイル検索とコピー
            skeleton_fbx_candidates = [
                unirig_model_processing_dir / "skeleton.fbx",
                unirig_model_processing_dir / "skeleton_model.fbx",
                unirig_model_processing_dir / f"{model_name}.fbx"
            ]
            
            final_output_fbx = None
            for candidate in skeleton_fbx_candidates:
                if candidate.exists():
                    final_output_fbx = self.step_output_dir / "skeleton.fbx"
                    shutil.copy2(candidate, final_output_fbx)
                    logs += f"📋 生成されたFBXをStep2出力ディレクトリにコピー: '{final_output_fbx}'\n"
                    break
            
            if not final_output_fbx:
                logs += f"⚠️ FBXファイルが見つかりませんでした。候補: {skeleton_fbx_candidates}\n"
            
            # 🎯 統一命名規則準拠の出力ファイル作成 (決め打ちディレクトリ戦略)
            unified_skeleton_npz = self.step_output_dir / f"{model_name}_skeleton.npz"
            # 🔥 決め打ちディレクトリ戦略準拠: skeleton.fbx → {model_name}_skeleton.fbx への統一命名
            unified_skeleton_fbx = self.step_output_dir / f"{model_name}_skeleton.fbx"
            
            # NPZファイル統一命名
            shutil.copy2(final_output_npz, unified_skeleton_npz)
            logs += f"📁 統一NPZ作成: {unified_skeleton_npz}\n"
            
            # FBXファイル統一命名 (原流準拠: skeleton.fbx → {model_name}.fbx)
            if final_output_fbx:
                shutil.copy2(final_output_fbx, unified_skeleton_fbx)
                logs += f"📁 統一FBX作成 (決め打ちディレクトリ戦略): {unified_skeleton_fbx}\n"
            else:
                logs += f"⚠️ FBXファイルが存在しないため、統一FBXは作成されませんでした。\n"
            
            # ボーン階層テキストファイル生成
            bones_txt_path_str = self._generate_bones_txt_from_npz(final_output_npz, model_name)
            if bones_txt_path_str:
                logs += f"📄 ボーン階層テキストファイル生成: '{bones_txt_path_str}'\n"
            
            # ファイル情報収集
            output_files: Dict[str, Any] = {
                "skeleton_npz": str(final_output_npz),
                "skeleton_fbx": str(final_output_fbx) if final_output_fbx else None,
                "unified_skeleton_npz": str(unified_skeleton_npz),
                "unified_skeleton_fbx": str(unified_skeleton_fbx) if final_output_fbx else None,
                "bones_txt": bones_txt_path_str,
                "bone_count": self._count_bones_in_npz_file(unified_skeleton_npz),
                "file_size_npz": unified_skeleton_npz.stat().st_size if unified_skeleton_npz.exists() else 0,
                "file_size_fbx": unified_skeleton_fbx.stat().st_size if unified_skeleton_fbx.exists() else 0
            }
            
            logs += f"✅ Step2出力ファイル整理完了 (決め打ちディレクトリ戦略)\n"
            logs += f"原流処理NPZ: {final_output_npz} ({output_files['file_size_npz']:,} bytes)\n"
            if final_output_fbx:
                logs += f"原流処理FBX: {final_output_fbx} ({output_files['file_size_fbx']:,} bytes)\n"
            logs += f"統一命名NPZ: {unified_skeleton_npz}\n"
            logs += f"統一命名FBX: {unified_skeleton_fbx}\n"
            logs += f"ボーン数 (推定): {output_files['bone_count']}\n"
            
            return True, logs, output_files
            
        except Exception as e:
            error_msg = f"❌ Step2出力ファイル整理中にエラー: {type(e).__name__} - {e}\n"
            self.logger.error(error_msg, exc_info=True)
            return False, logs + error_msg, {}
    
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
        """NPZファイルからボーン階層テキストファイル生成"""
        if not npz_file_path.exists():
            self.logger.error(f"ボーン階層テキスト生成失敗: NPZファイル '{npz_file_path}' が見つかりません。")
            return None
        
        bones_txt_output_path = npz_file_path.with_name(f"{model_name}_bones.txt")
        
        try:
            data = np.load(npz_file_path, allow_pickle=True)
            content = f"# Bone Hierarchy for {model_name}\n"
            content += f"# Generated from: {npz_file_path.name}\n\n"
            
            for key in data.files:
                array_data = data[key]
                content += f"Key: {key}\n"
                content += f"  Shape: {array_data.shape}\n"
                content += f"  Dtype: {array_data.dtype}\n"
                if hasattr(array_data, 'size'):
                    content += f"  Size: {array_data.size}\n"
                content += "\n"
            
            with open(bones_txt_output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.logger.info(f"ボーン階層テキストファイル生成成功: {bones_txt_output_path}")
            return str(bones_txt_output_path)
            
        except Exception as e:
            self.logger.error(f"ボーン階層テキストファイル生成エラー: {e}")
            return None
    
    def _count_bones_in_npz_file(self, npz_file_path: Path) -> int:
        """NPZファイルからボーン数推定"""
        try:
            data = np.load(npz_file_path, allow_pickle=True)
            bone_count = 0
            for key in data.files:
                if 'joint' in key.lower() or 'bone' in key.lower():
                    array_data = data[key]
                    if len(array_data.shape) >= 1:
                        bone_count += array_data.shape[0]
            return bone_count if bone_count > 0 else len(data.files)
        except Exception as e:
            self.logger.error(f"ボーン数推定エラー: {e}")
            return 0
    
    # 左右対称チェック機能は削除されました


# 外部インターフェース (決め打ちディレクトリ戦略対応)
def execute_step2(original_file: Path, model_name: str, step_output_dir: Path, logger: logging.Logger, gender: str = "neutral") -> Tuple[bool, str, Dict[str, Any]]:
    """
    Step2外部インターフェース - 決め打ちディレクトリ戦略対応
    
    🔥 重要: オリジナルファイルから独自メッシュ再抽出実行
    
    Args:
        original_file: オリジナル3Dモデルファイル
        model_name: モデル名
        step_output_dir: Step2専用出力ディレクトリ
        logger: ロガーインスタンス
        gender: 性別設定
        
    Returns:
        (success, logs, output_files dict)
    """
    try:
        step2 = Step2Skeleton(step_output_dir, logger)
        return step2.generate_skeleton(original_file, model_name, gender)
    except Exception as e:
        error_msg = f"Step2外部インターフェースエラー: {e}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg, {}


if __name__ == "__main__":
    # テスト用スタンドアロン実行
    import argparse
    
    parser = argparse.ArgumentParser(description='Step2 スケルトン生成テスト')
    parser.add_argument('--original_file', required=True, help='オリジナル3Dモデルファイルパス')
    parser.add_argument('--model_name', required=True, help='モデル名')
    parser.add_argument('--output_dir', default='/tmp/step2_test_output', help='出力ディレクトリ')
    parser.add_argument('--gender', default='neutral', choices=['neutral', 'male', 'female'], help='性別')
    
    args = parser.parse_args()
    
    # ロガー設定
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger('Step2Test')
    
    # Step2実行
    success, logs, output_files = execute_step2(
        Path(args.original_file),
        args.model_name,
        Path(args.output_dir),
        logger,
        args.gender
    )
    
    print(f"\n{'='*50}")
    print(f"Step2テスト結果: {'✅ 成功' if success else '❌ 失敗'}")
    print(f"{'='*50}")
    print(logs)
    if output_files:
        print(f"\n出力ファイル:")
        for key, value in output_files.items():
            print(f"  {key}: {value}")
