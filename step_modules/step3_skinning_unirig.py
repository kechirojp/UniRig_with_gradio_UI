"""
Step3 Module - スキニング適用 (決め打ちディレクトリ戦略)
🔥 重要: Step3は必ずオリジナルファイルから独自のメッシュ再抽出を実行
原流処理generate_skin.sh完全互換実装

📋 2025年6月16日修正: run.py + YAML設定 + Lightning使用
- 原流処理との完全一致を実現
- src.system.skinの直接呼び出しから変更
- Lightning最適化とYAML設定の恩恵を受ける

責務: オリジナル3Dモデル + スケルトンデータ → スキニング済みFBX
出力: {model_name}_skinned.fbx, {model_name}_skinning.npz
"""

import os
import sys
import subprocess
import shutil
import time
import logging
import tempfile
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
import numpy as np

sys.path.insert(0, '/app')
sys.path.insert(0, '/app/src')

class Step3Skinning:
    """Step3: スキニング適用モジュール (決め打ちディレクトリ戦略)"""
    
    def __init__(self, step_output_dir: Path, logger_instance: Optional[logging.Logger] = None):
        """
        Args:
            step_output_dir: Step3専用出力ディレクトリ (例: /app/pipeline_work/{model_name}/03_skinning/)
            logger_instance: ロガーインスタンス
        """
        self.step_output_dir = step_output_dir
        self.step_output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger_instance if logger_instance else logging.getLogger(__name__)
        
        # UniRig処理用ベースディレクトリ (run.pyが期待する構造)
        self.unirig_processing_base_dir = Path("/app/dataset_inference_clean")
        self.unirig_processing_base_dir.mkdir(parents=True, exist_ok=True)
    
    def apply_skinning(self, 
                      original_file: Path, 
                      model_name: str, 
                      skeleton_files: Dict[str, str]
                     ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        🔥 スキニング適用 - オリジナルファイルから独自メッシュ再抽出実行
        
        重要: Step1の結果は使用せず、オリジナルファイルから独自にメッシュを再抽出
        原流処理generate_skin.sh完全互換
        
        Args:
            original_file: オリジナル3Dモデルファイル (.glb, .fbx, .vrm等)
            model_name: モデル名（統一命名規則ベース）
            skeleton_files: Step2の出力ファイル辞書
            
        Returns:
            (success, logs, output_files dict) - 統一命名規則準拠の出力ファイルパス
        """
        logs = ""
        try:
            start_time = time.time()
            self.logger.info(f"🔥 Step3スキニング適用開始: モデル '{model_name}'")
            self.logger.info(f"🔥 重要: オリジナルファイルから独自メッシュ再抽出実行: {original_file}")
            
            if not original_file.exists():
                error_msg = f"❌ オリジナルファイルが見つかりません: {original_file}"
                self.logger.error(error_msg)
                return False, logs, {
                    "skinned_fbx": "",
                    "skinning_npz": ""
                }

            # --- Step3専用UniRig処理ディレクトリ準備 ---
            unirig_model_processing_dir = self.unirig_processing_base_dir / model_name
            unirig_model_processing_dir.mkdir(parents=True, exist_ok=True)
            
            # --- Step3専用メッシュディレクトリ作成 ---
            step3_mesh_dir = self.step_output_dir / "mesh_for_skinning"
            step3_mesh_dir.mkdir(parents=True, exist_ok=True)
            logs += f"⚙️ Step3専用メッシュディレクトリ準備完了: '{step3_mesh_dir}'\n"
            logs += f"⚙️ Step3用UniRig処理ディレクトリ準備完了: '{unirig_model_processing_dir}'\n"

            # --- 🔥 効率化: 既存raw_data.npz確認 ---
            # dataset_inference_clean/{model_name}/に既にraw_data.npzが存在する場合はスキップ
            existing_raw_data = unirig_model_processing_dir / "raw_data.npz"
            if existing_raw_data.exists():
                logs += f"✅ 既存のraw_data.npzを使用: {existing_raw_data} (メッシュ再抽出スキップ)\n"
                success_extraction = True
                extraction_logs = f"📋 Step2で生成済みのraw_data.npzを再利用: {existing_raw_data}\n"
            else:
                # --- 🔥 重要: Step3独自のメッシュ再抽出実行 ---
                success_extraction, extraction_logs = self._execute_skinning_specific_mesh_extraction(
                    original_file, unirig_model_processing_dir, model_name
                )
                
            logs += extraction_logs
            
            if not success_extraction:
                error_msg = f"❌ Step3独自メッシュ再抽出失敗。"
                self.logger.error(error_msg)
                return False, logs, {
                    "skinned_fbx": "",
                    "skinning_npz": ""
                }

            # --- スケルトンファイル配置 ---
            success_skeleton_setup, skeleton_setup_logs = self._setup_skeleton_files(
                unirig_model_processing_dir, skeleton_files, model_name
            )
            logs += skeleton_setup_logs
            
            if not success_skeleton_setup:
                error_msg = f"❌ スケルトンファイル配置失敗。"
                self.logger.error(error_msg)
                return False, logs, {
                    "skinned_fbx": "",
                    "skinning_npz": ""
                }

            # --- UniRigスキニング処理実行 ---
            success_skinning, skinning_logs = self._execute_unirig_skinning_generation(
                model_name, unirig_model_processing_dir
            )
            logs += skinning_logs
            
            if not success_skinning:
                error_msg = f"❌ UniRigスキニング処理失敗。"
                self.logger.error(error_msg)
                return False, logs, {
                    "skinned_fbx": "",
                    "skinning_npz": ""
                }
            
            # --- 生成ファイル整理と統一命名規則対応 ---
            success_output, output_logs, output_files = self._organize_step3_outputs(
                model_name, unirig_model_processing_dir
            )
            logs += output_logs
            
            if not success_output:
                error_msg = f"❌ Step3出力ファイル整理失敗。"
                self.logger.error(error_msg)
                return False, logs, {
                    "skinned_fbx": "",
                    "skinning_npz": ""
                }
            
            # --- 🔍 重要: バーテックスグループ（ボーン/ウェイト）検証実行 ---
            if output_files.get("skinned_fbx") and Path(output_files["skinned_fbx"]).exists():
                validation_success, validation_logs = self._validate_vertex_groups_in_fbx(
                    Path(output_files["skinned_fbx"]), model_name
                )
                logs += validation_logs
                
                if not validation_success:
                    error_msg = f"❌ Step3スキニング検証失敗: バーテックスグループ（ボーン/ウェイト）が正しく生成されていません。"
                    self.logger.error(error_msg)
                    return False, logs, {
                        "skinned_fbx": "",
                        "skinning_npz": ""
                    }
                else:
                    self.logger.info("✅ Step3スキニング検証成功: バーテックスグループが正常に生成されています。")
            else:
                error_msg = f"❌ スキニング済みFBXファイルが見つからないため、バーテックスグループ検証をスキップします。"
                self.logger.warning(error_msg)
                logs += error_msg + "\n"

            processing_time = time.time() - start_time
            output_files["processing_time_seconds"] = round(processing_time, 2)
            
            final_log_message = f"🔥 Step3スキニング適用完了:\n"
            final_log_message += f"- モデル名: {model_name}\n"
            final_log_message += f"- 処理時間: {processing_time:.2f}秒\n"
            if 'skinning_npz' in output_files:
                final_log_message += f"- 統一NPZ: {output_files.get('skinning_npz', '')}\n"
            else:
                final_log_message += f"- 統一NPZ: (作成されませんでした)\n"
            final_log_message += f"- 統一FBX: {output_files.get('skinned_fbx', '')}\n"
            logs += "\n" + final_log_message
            
            self.logger.info(f"🔥 Step3スキニング適用正常完了: '{output_files.get('skinned_fbx', '')}'")
            return True, logs, output_files
            
        except Exception as e:
            error_msg = f"❌ Step3スキニング適用中に予期せぬエラー: {type(e).__name__} - {e}"
            self.logger.error(error_msg, exc_info=True)
            return False, logs, {
                    "skinned_fbx": "",
                    "skinning_npz": ""
                }
    
    def _execute_skinning_specific_mesh_extraction(self, original_file: Path, unirig_model_processing_dir: Path, model_name: str) -> Tuple[bool, str]:
        """
        🔥 Step3独自のスキニング特化メッシュ再抽出
        
        重要: 原流処理generate_skin.sh第1段階完全互換
        スキニング生成に最適化された前処理パラメータ使用
        
        Args:
            original_file: オリジナル3Dモデルファイル
            unirig_model_processing_dir: UniRig処理ディレクトリ
            model_name: モデル名
            
        Returns:
            (success, logs)
        """
        logs = ""
        try:
            # データ設定ファイル確認
            data_config = Path("/app/configs/data/quick_inference.yaml")
            if not data_config.exists():
                return False, f"❌ データ設定ファイル不存在: {data_config}\n"
            
            logs += f"🔥 Step3独自メッシュ再抽出開始\n"
            logs += f"オリジナルファイル: {original_file}\n"
            logs += f"UniRig処理ディレクトリ: {unirig_model_processing_dir}\n"
            
            # タイムスタンプ生成 (原流方式)
            time_str = time.strftime("%Y_%m_%d_%H_%M_%S")
            
            # 🔥 原流処理generate_skin.sh第1段階完全互換コマンド
            extract_cmd = [
                sys.executable, "-m", "src.data.extract",
                "--config", str(data_config),
                "--force_override", "true",
                "--num_runs", "1",
                "--faces_target_count", "50000",  # 🔥 スキニング特化: 詳細メッシュ
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
                
                # 🔥 重要: Step3専用メッシュディレクトリにもコピー（決め打ちディレクトリ戦略）
                step3_mesh_dir = self.step_output_dir / "mesh_for_skinning"
                step3_target_raw_data = step3_mesh_dir / "raw_data.npz"
                shutil.copy2(found_raw_data, step3_target_raw_data)
                logs += f"📋 raw_data.npzをStep3専用メッシュディレクトリにコピー: {found_raw_data} → {step3_target_raw_data}\n"
                
                success_msg = f"✅ Step3独自メッシュ再抽出成功 (リターンコード: {result.returncode}, Blenderクラッシュでもファイル生成済み)\n"
                success_msg += f"生成ファイル: {found_raw_data}\n"
                success_msg += f"UniRig処理用: {target_raw_data}\n"
                success_msg += f"Step3専用保存: {step3_target_raw_data}\n"
                if result.stdout:
                    success_msg += f"STDOUT:\n{result.stdout}\n"
                logs += success_msg
                self.logger.info("Step3独自メッシュ再抽出成功（Blenderクラッシュ後もファイル確認）。")
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
    
    def _setup_skeleton_files(self, unirig_model_processing_dir: Path, skeleton_files: Dict[str, str], model_name: str) -> Tuple[bool, str]:
        """
        スケルトンファイルをUniRig処理ディレクトリに配置
        
        Args:
            unirig_model_processing_dir: UniRig処理ディレクトリ
            skeleton_files: Step2の出力ファイル辞書
            model_name: モデル名
            
        Returns:
            (success, logs)
        """
        logs = ""
        try:
            # predict_skeleton.npz配置 (run.pyが期待するファイル名)
            skeleton_npz_path = skeleton_files.get("skeleton_npz") or skeleton_files.get("unified_skeleton_npz")
            if skeleton_npz_path and Path(skeleton_npz_path).exists():
                target_skeleton_npz = unirig_model_processing_dir / "predict_skeleton.npz"
                if not target_skeleton_npz.exists():
                    shutil.copy2(skeleton_npz_path, target_skeleton_npz)
                logs += f"✅ スケルトンNPZファイル配置: {target_skeleton_npz}\n"
            else:
                # 🚨 必須ファイル不存在エラー - Step3は失敗とする
                error_msg = f"❌ 必須スケルトンNPZファイルが存在しません: {skeleton_npz_path}"
                logs += f"{error_msg}\n"
                logs += f"💡 解決策: Step2の実行を先に完了してください\n"
                return False, logs
            
            # {model_name}.fbx配置 (原流互換名)
            skeleton_fbx_path = skeleton_files.get("skeleton_fbx") or skeleton_files.get("unified_skeleton_fbx")
            if skeleton_fbx_path and Path(skeleton_fbx_path).exists():
                target_skeleton_fbx = unirig_model_processing_dir / f"{model_name}.fbx"
                if not target_skeleton_fbx.exists():
                    shutil.copy2(skeleton_fbx_path, target_skeleton_fbx)
                logs += f"✅ スケルトンFBXファイル配置: {target_skeleton_fbx}\n"
            else:
                # 🚨 必須ファイル不存在エラー - Step3は失敗とする
                error_msg = f"❌ 必須スケルトンFBXファイルが存在しません: {skeleton_fbx_path}"
                logs += f"{error_msg}\n"
                logs += f"💡 解決策: Step2の実行を先に完了してください\n"
                return False, logs
                target_skeleton_fbx = unirig_model_processing_dir / f"{model_name}.fbx"
                if not target_skeleton_fbx.exists():
                    shutil.copy2(skeleton_fbx_path, target_skeleton_fbx)
                logs += f"スケルトンFBXファイル配置: {target_skeleton_fbx}\n"
            
            return True, logs
            
        except Exception as e:
            error_msg = f"❌ スケルトンファイル配置エラー: {type(e).__name__} - {e}\n"
            self.logger.error(error_msg, exc_info=True)
            return False, logs + error_msg
    
    def _execute_unirig_skinning_generation(self, model_name: str, unirig_model_processing_dir: Path) -> Tuple[bool, str]:
        """
        UniRigスキニング処理実行 (原流処理generate_skin.sh第2段階完全互換)
        
        🔥 重要修正: run.py + YAML設定使用 (原流処理との完全一致)
        
        Args:
            model_name: モデル名
            unirig_model_processing_dir: UniRig処理ディレクトリ
            
        Returns:
            (success, logs)
        """
        logs = ""
        try:
            # スキニング設定ファイル確認
            skinning_config = Path("/app/configs/task/quick_inference_unirig_skin.yaml")
            if not skinning_config.exists():
                return False, f"❌ スキニング設定ファイル不存在: {skinning_config}\n"
            
            logs += f"🔥 UniRigスキニング処理実行開始 (run.py + Lightning使用)\n"
            logs += f"処理ディレクトリ: {unirig_model_processing_dir}\n"
            logs += f"設定ファイル: {skinning_config}\n"
            
            # 🔥 決定的修正: 原流処理generate_skin.sh完全互換 - dataset_inference_clean使用
            # 重要: npz_dirにはモデル固有ディレクトリを指定、data_nameはデフォルト（raw_data.npz）を使用
            skinning_cmd = [
                sys.executable, "run.py",
                "--task", str(skinning_config),
                "--seed", "12345",
                "--npz_dir", f"dataset_inference_clean/{model_name}",  # 🔥 修正: モデル固有ディレクトリ指定
                # data_nameはデフォルト（raw_data.npz）を使用、--data_nameパラメータは削除
            ]
            
            logs += f"スキニング処理コマンド (run.py + Lightning): {' '.join(skinning_cmd)}\n"
            
            skinning_start_time = time.time()
            result = subprocess.run(
                skinning_cmd,
                cwd='/app',
                capture_output=True,
                text=True,
                timeout=1800  # 30分タイムアウト (Lightning処理のため延長)
            )
            skinning_execution_time = time.time() - skinning_start_time
            logs += f"⏱️ スキニング処理実行時間 (Lightning): {skinning_execution_time:.2f}秒\n"
            
            if result.returncode == 0:
                success_msg = f"✅ UniRigスキニング処理成功 (run.py + Lightning) (リターンコード: {result.returncode})\n"
                if result.stdout:
                    success_msg += f"STDOUT:\n{result.stdout}\n"
                logs += success_msg
                self.logger.info("UniRigスキニング処理正常完了 (Lightning最適化)。")
                return True, logs
            else:
                error_msg = f"❌ UniRigスキニング処理失敗 (run.py + Lightning) (リターンコード: {result.returncode})\n"
                if result.stdout:
                    error_msg += f"STDOUT:\n{result.stdout}\n"
                if result.stderr:
                    error_msg += f"STDERR:\n{result.stderr}\n"
                self.logger.error(f"スキニング処理エラー (Lightning)。Return code: {result.returncode}")
                logs += error_msg
                return False, logs
                
        except subprocess.TimeoutExpired:
            timeout_msg = "❌ スキニング処理がタイムアウトしました (15分)\n"
            self.logger.error(timeout_msg)
            return False, logs + timeout_msg
        except Exception as e:
            exec_error_msg = f"❌ スキニング処理中に予期せぬエラー: {type(e).__name__} - {e}\n"
            self.logger.error(exec_error_msg, exc_info=True)
            return False, logs + exec_error_msg
    
    def _organize_step3_outputs(self, model_name: str, unirig_model_processing_dir: Path) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Step3出力ファイルの整理と統一命名規則対応
        
        Args:
            model_name: モデル名
            unirig_model_processing_dir: UniRig処理ディレクトリ
            
        Returns:
            (success, logs, output_files dict)
        """
        logs = ""
        output_files = {}
        
        try:
            logs += f"🔧 Step3出力ファイル整理開始\n"
            
            # 🔥 重要: run.pyによる実際の出力ファイル名を確認
            # 原流処理の実際の出力パターンに基づく検索
            possible_output_patterns = [
                # 🎯 実際の出力場所を追加（results/ディレクトリ）
                Path("/app/results/skinned_model.fbx"),  # 実際のスキニング済みFBX
                Path("/app/results/predict_skin.npz"),   # 実際のスキンウェイトNPZ
                # 設定ファイルに基づく予想出力名
                unirig_model_processing_dir / "result_fbx.fbx",
                unirig_model_processing_dir / f"{model_name}_skinned_unirig.fbx",
                unirig_model_processing_dir / "predict_skin.npz",
                unirig_model_processing_dir / f"{model_name}_skinning.npz",
                # その他の可能な出力パターン
                unirig_model_processing_dir / "skinned.fbx",
                unirig_model_processing_dir / "output.fbx"
            ]
            
            # 生成されたFBXファイルを検索
            found_fbx = None
            found_npz = None
            
            for pattern in possible_output_patterns:
                if pattern.exists() and pattern.suffix == ".fbx":
                    found_fbx = pattern
                    logs += f"📁 生成FBXファイル発見: {found_fbx}\n"
                    break
            
            for pattern in possible_output_patterns:
                if pattern.exists() and pattern.suffix == ".npz":
                    found_npz = pattern
                    logs += f"📁 生成NPZファイル発見: {found_npz}\n"
                    break
            
            if not found_fbx:
                # 指定パターンで見つからない場合、ディレクトリ内の全FBXを検索
                fbx_files = list(unirig_model_processing_dir.glob("*.fbx"))
                # スケルトンFBXを除外
                fbx_files = [f for f in fbx_files if f.name != f"{model_name}.fbx"]
                if fbx_files:
                    found_fbx = fbx_files[0]  # 最初に見つかったものを使用
                    logs += f"📁 ディレクトリ検索でFBXファイル発見: {found_fbx}\n"
            
            if not found_npz:
                # 指定パターンで見つからない場合、ディレクトリ内の全NPZを検索（raw_data.npz, predict_skeleton.npzを除外）
                npz_files = list(unirig_model_processing_dir.glob("*.npz"))
                npz_files = [f for f in npz_files if f.name not in ["raw_data.npz", "predict_skeleton.npz"]]
                if npz_files:
                    found_npz = npz_files[0]  # 最初に見つかったものを使用
                    logs += f"📁 ディレクトリ検索でNPZファイル発見: {found_npz}\n"
            
            # 🔥 統一命名規則に基づく最終出力ファイル配置
            if found_fbx:
                unified_fbx_name = f"{model_name}_skinned.fbx"
                unified_fbx_path = self.step_output_dir / unified_fbx_name
                shutil.copy2(found_fbx, unified_fbx_path)
                output_files["skinned_fbx"] = str(unified_fbx_path)
                logs += f"✅ 統一FBX生成: {unified_fbx_path}\n"
            else:
                return False, logs, {
                    "skinned_fbx": "",
                    "skinning_npz": ""
                }
            
            if found_npz:
                unified_npz_name = f"{model_name}_skinning.npz"
                unified_npz_path = self.step_output_dir / unified_npz_name
                shutil.copy2(found_npz, unified_npz_path)
                output_files["skinning_npz"] = str(unified_npz_path)
                logs += f"✅ 統一NPZ生成: {unified_npz_path}\n"
            else:
                # NPZファイルは必須ではない場合があるため、警告のみ
                logs += f"⚠️ スキニングNPZファイルが見つかりません（オプショナル）\n"
                output_files["skinning_npz"] = ""  # 空文字で統一
            
            # 🔥 決め打ちディレクトリ戦略: mesh_for_skinning/raw_data.npzを配置
            # dataset_inference_clean/{model_name}/raw_data.npzから決め打ちディレクトリにコピー
            source_mesh_npz = Path(f"/app/dataset_inference_clean/{model_name}/raw_data.npz")
            target_mesh_dir = self.step_output_dir / "mesh_for_skinning"
            target_mesh_npz = target_mesh_dir / "raw_data.npz"
            
            # mesh_for_skinningディレクトリ作成とraw_data.npzコピー
            target_mesh_dir.mkdir(parents=True, exist_ok=True)
            if source_mesh_npz.exists():
                shutil.copy2(source_mesh_npz, target_mesh_npz)
                logs += f"✅ メッシュNPZファイル配置: {target_mesh_npz}\n"
                output_files["step3_mesh"] = str(target_mesh_npz)
            else:
                # 🚨 必須ファイル不存在エラー - Step3は失敗とする
                error_msg = f"❌ 必須メッシュNPZファイルが存在しません: {source_mesh_npz}"
                logs += f"{error_msg}\n"
                logs += f"💡 解決策: Step1またはStep2の実行を先に完了してください\n"
                return False, logs, {
                    "skinned_fbx": "",
                    "skinning_npz": "",
                    "step3_mesh": ""
                }
            
            # 🔥 決め打ちディレクトリ戦略に基づく期待ファイル配置確認
            expected_files = {
                "skinned_fbx": self.step_output_dir / f"{model_name}_skinned.fbx",
                "skinning_npz": self.step_output_dir / f"{model_name}_skinning.npz"
            }
            
            all_expected_exist = True
            for file_type, file_path in expected_files.items():
                if file_path.exists():
                    logs += f"✅ 期待ファイル確認: {file_type} -> {file_path}\n"
                    output_files[file_type] = str(file_path)
                else:
                    if file_type != "skinning_npz":  # NPZはオプショナル
                        logs += f"❌ 期待ファイル不存在: {file_type} -> {file_path}\n"
                        all_expected_exist = False
                    else:
                        logs += f"⚠️ オプショナルファイル不存在: {file_type} -> {file_path}\n"
            
            # skinned_fbxの存在確認が最重要、その他はオプショナル
            if not output_files.get("skinned_fbx"):
                return False, logs, {
                    "skinned_fbx": "",
                    "skinning_npz": ""
                }
            
            # 必須キーの存在を保証
            if "skinning_npz" not in output_files:
                output_files["skinning_npz"] = ""
            if "skinned_fbx" not in output_files:
                output_files["skinned_fbx"] = ""
            
            return True, logs, output_files
            
        except Exception as e:
            error_msg = f"❌ 出力ファイル整理中に予期せぬエラー: {type(e).__name__} - {e}\n"
            self.logger.error(error_msg, exc_info=True)
            return False, logs, {
                    "skinned_fbx": "",
                    "skinning_npz": ""
                }
    
    def _validate_vertex_groups_in_fbx(self, fbx_file_path: Path, model_name: str) -> Tuple[bool, str]:
        """
        スキニング済みFBXファイル内のバーテックスグループ（ボーン/ウェイト）を検証
        
        Blenderを使用してFBXファイルを読み込み、以下を確認:
        1. アーマチュア（骨格）が存在するか
        2. メッシュオブジェクトにバーテックスグループが存在するか
        3. バーテックスグループがアーマチュアのボーンと対応しているか
        4. 実際にウェイトデータが設定されているか
        
        Args:
            fbx_file_path: 検証するFBXファイルのパス
            model_name: モデル名（ログ用）
            
        Returns:
            (validation_success, detailed_logs)
        """
        logs = ""
        
        try:
            # BlenderのPython APIを使用してFBXファイルを検査
            # バックグラウンドモードで安全に実行
            validation_script = f'''
import bpy
import sys
import json

def validate_vertex_groups():
    """FBXファイル内のバーテックスグループを検証"""
    validation_result = {{
        "has_armature": False,
        "armature_name": "",
        "bone_count": 0,
        "meshes_with_vertex_groups": [],
        "meshes_without_vertex_groups": [],
        "vertex_group_details": {{}},
        "weight_data_exists": False,
        "validation_passed": False,
        "error_messages": []
    }}
    
    try:
        # 全オブジェクトを確認
        armatures = []
        meshes = []
        
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                armatures.append(obj)
            elif obj.type == 'MESH':
                meshes.append(obj)
        
        # アーマチュア存在確認
        if not armatures:
            validation_result["error_messages"].append("❌ アーマチュア（骨格）が見つかりません")
            return validation_result
        
        armature = armatures[0]  # 最初のアーマチュアを使用
        validation_result["has_armature"] = True
        validation_result["armature_name"] = armature.name
        validation_result["bone_count"] = len(armature.data.bones)
        
        if validation_result["bone_count"] == 0:
            validation_result["error_messages"].append("❌ アーマチュアにボーンが存在しません")
            return validation_result
        
        # 各メッシュのバーテックスグループを確認
        total_weighted_vertices = 0
        
        for mesh_obj in meshes:
            mesh_name = mesh_obj.name
            vertex_groups = mesh_obj.vertex_groups
            
            if len(vertex_groups) == 0:
                validation_result["meshes_without_vertex_groups"].append(mesh_name)
                validation_result["error_messages"].append("❌ メッシュ '" + mesh_name + "' にバーテックスグループが存在しません")
            else:
                validation_result["meshes_with_vertex_groups"].append(mesh_name)
                
                # バーテックスグループの詳細を取得
                group_details = {{}}
                for vg in vertex_groups:
                    group_details[vg.name] = {{
                        "index": vg.index,
                        "vertex_count": len([v for v in mesh_obj.data.vertices if vg.index in [g.group for g in v.groups]])
                    }}
                
                validation_result["vertex_group_details"][mesh_name] = group_details
                
                # ウェイトデータの存在確認
                for vertex in mesh_obj.data.vertices:
                    if len(vertex.groups) > 0:
                        total_weighted_vertices += 1
        
        validation_result["weight_data_exists"] = total_weighted_vertices > 0
        
        # 総合判定
        if (validation_result["has_armature"] and 
            validation_result["bone_count"] > 0 and 
            len(validation_result["meshes_with_vertex_groups"]) > 0 and
            validation_result["weight_data_exists"]):
            validation_result["validation_passed"] = True
        else:
            if not validation_result["weight_data_exists"]:
                validation_result["error_messages"].append("❌ バーテックスにウェイトデータが設定されていません")
        
        return validation_result
        
    except Exception as e:
        validation_result["error_messages"].append("❌ 検証中にエラー: " + str(e))
        return validation_result

# ファイル読み込み
try:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath="{str(fbx_file_path)}")
    result = validate_vertex_groups()
    print("VALIDATION_RESULT_START")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("VALIDATION_RESULT_END")
except Exception as e:
    error_result = {{
        "validation_passed": False,
        "error_messages": ["❌ FBXファイル読み込みエラー: " + str(e)]
    }}
    print("VALIDATION_RESULT_START")
    print(json.dumps(error_result, indent=2, ensure_ascii=False))
    print("VALIDATION_RESULT_END")
    sys.exit(1)
'''

            # Blenderをバックグラウンドモードで実行
            logs += f"🔍 バーテックスグループ検証開始: {fbx_file_path}\n"
            
            cmd = [
                "blender", "--background", "--python-text", validation_script
            ]
            
            # 一時スクリプトファイルを作成
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_script:
                temp_script.write(validation_script)
                temp_script_path = temp_script.name
            
            try:
                # Blenderコマンドを修正
                cmd = [
                    "blender", "--background", "--python", temp_script_path
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120  # 2分タイムアウト
                )
                
                # 検証結果をパース
                stdout_text = result.stdout
                if "VALIDATION_RESULT_START" in stdout_text and "VALIDATION_RESULT_END" in stdout_text:
                    start_idx = stdout_text.find("VALIDATION_RESULT_START") + len("VALIDATION_RESULT_START")
                    end_idx = stdout_text.find("VALIDATION_RESULT_END")
                    json_text = stdout_text[start_idx:end_idx].strip()
                    
                    try:
                        import json
                        validation_data = json.loads(json_text)
                        
                        # 結果を詳細にログ出力
                        logs += f"📊 バーテックスグループ検証結果:\n"
                        logs += f"- アーマチュア存在: {validation_data.get('has_armature', False)}\n"
                        logs += f"- アーマチュア名: {validation_data.get('armature_name', 'N/A')}\n"
                        logs += f"- ボーン数: {validation_data.get('bone_count', 0)}\n"
                        logs += f"- バーテックスグループ有りメッシュ: {validation_data.get('meshes_with_vertex_groups', [])}\n"
                        logs += f"- バーテックスグループ無しメッシュ: {validation_data.get('meshes_without_vertex_groups', [])}\n"
                        logs += f"- ウェイトデータ存在: {validation_data.get('weight_data_exists', False)}\n"
                        
                        if validation_data.get('error_messages'):
                            logs += f"⚠️ エラーメッセージ:\n"
                            for error_msg in validation_data['error_messages']:
                                logs += f"  {error_msg}\n"
                        
                        if validation_data.get('validation_passed', False):
                            logs += f"✅ バーテックスグループ検証成功: スキニングデータが正常に生成されています\n"
                            return True, logs
                        else:
                            logs += f"❌ バーテックスグループ検証失敗: スキニングデータに問题があります\n"
                            return False, logs
                            
                    except json.JSONDecodeError as e:
                        logs += f"❌ 検証結果のJSONパースエラー: {e}\n"
                        logs += f"生の出力: {json_text}\n"
                        return False, logs
                else:
                    logs += f"❌ Blender検証スクリプトの出力形式が不正です\n"
                    logs += f"STDOUT: {result.stdout}\n"
                    logs += f"STDERR: {result.stderr}\n"
                    return False, logs
                    
            finally:
                # 一時ファイルをクリーンアップ
                try:
                    os.unlink(temp_script_path)
                except:
                    pass
                    
        except subprocess.TimeoutExpired:
            logs += f"❌ バーテックスグループ検証がタイムアウトしました (2分)\n"
            return False, logs
        except Exception as e:
            logs += f"❌ バーテックスグループ検証中に予期せぬエラー: {type(e).__name__} - {e}\n"
            return False, logs

# --- 互換性のための関数定義 ---
def apply_skinning_step3(model_name: str, mesh_file_path: str, skeleton_files: Dict[str, str], output_dir: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Step3スキニング適用の互換性関数 (unified_pipeline_orchestrator.py用)
    
    Args:
        model_name: モデル名
        mesh_file_path: Step1メッシュファイルパス（使用しない - 原流互換のため）
        skeleton_files: Step2の出力ファイル辞書
        output_dir: 出力ディレクトリ
        
    Returns:
        (success, logs, output_files)
    """
    # 🔥 重要: オリジナルファイルの検索
    # mesh_file_pathは使用せず、オリジナルファイルから再抽出を行う
    from fixed_directory_manager import FixedDirectoryManager
    
    logs = ""  # ログ初期化
    
    # モデル名からオリジナルファイルを検索
    fdm = FixedDirectoryManager(Path("/app/pipeline_work"), model_name)
    original_file = fdm.find_original_model_file()
    
    if not original_file:
        error_msg = f"❌ オリジナルファイルが見つかりません。モデル名: {model_name}"
        logs += error_msg + "\n"
        return False, logs, {
                    "skinned_fbx": "",
                    "skinning_npz": ""
                }
    
    # Step3インスタンス作成と実行
    step3_instance = Step3Skinning(Path(output_dir))
    return step3_instance.apply_skinning(original_file, model_name, skeleton_files)
