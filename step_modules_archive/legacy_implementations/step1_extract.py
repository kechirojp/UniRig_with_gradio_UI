"""
Step 1 Module - メッシュ抽出
独立した実行機能として、3Dモデルからメッシュデータを抽出

責務: 3Dモデルファイル → メッシュNPZファイル
入力: 3Dモデルファイルパス (.glb, .fbx, .obj, .vrm等)
出力: メッシュデータファイルパス (.npz)
"""

import os
import sys
import logging
import subprocess
import yaml # Not strictly used in current logic, but kept for potential future config use
from pathlib import Path
from typing import Tuple, Dict, Optional, Any
import json
import numpy as np # Not strictly used in current logic, but kept for potential future npz handling
import time
import shutil

# UniRig実行パス設定
sys.path.append('/app')

# Default logger setup if no logger is provided
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class Step1Extract:
    """Step 1: メッシュ抽出モジュール"""
    
    def __init__(self, output_dir: Path, logger_instance: Optional[logging.Logger] = None):
        self.output_dir = output_dir # This is the step-specific output dir, e.g., /app/pipeline_work/model_name/01_extracted_mesh/
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger_instance if logger_instance else logging.getLogger(__name__)
    
    def _find_output_npz(self, output_dir: Path, model_name: str) -> Optional[Path]:
        """
        生成されたNPZファイルを複数パターンで検索
        
        Args:
            output_dir: 出力ディレクトリ
            model_name: モデル名
            
        Returns:
            見つかったNPZファイルパス（見つからない場合はNone）
        """
        search_patterns = [
            output_dir / "raw_data.npz",                    # 直接出力
            output_dir / model_name / "raw_data.npz",       # サブディレクトリ内
            output_dir / f"{model_name}.npz",               # モデル名.npz
            output_dir / f"{model_name}_mesh.npz"           # モデル名_mesh.npz
        ]
        
        for npz_path in search_patterns:
            if npz_path.exists():
                self.logger.info(f"NPZファイル発見: {npz_path}")
                return npz_path
        
        self.logger.warning(f"NPZファイルが見つかりません。検索パターン: {[str(p) for p in search_patterns]}")
        return None

    def extract_mesh(self, input_file_path: Path, model_name: str, preserve_textures_in_step1: bool = False) -> Tuple[bool, str, Dict[str, Any]]:
        """
        実際のメッシュ抽出の実行 (UniRig src.data.extract使用)
        
        Args:
            input_file_path: 入力3Dモデルファイルパス (絶対パス)
            model_name: モデル名（出力ファイル名に使用）
            preserve_textures_in_step1: このステップでテクスチャ情報を別途保存するか。
                                     Step0でアセット保存が行われるため、通常はFalse。
            
        Returns:
            (success, logs, output_files dict)
        """
        logs = ""
        try:
            self.logger.info(f"Step 1 開始: 入力 '{input_file_path}', モデル名 '{model_name}'")
            
            if not input_file_path.exists():
                error_msg = f"[FAIL] 入力ファイルが見つかりません: {input_file_path}"
                self.logger.error(error_msg)
                return False, error_msg, {}
            
            # 入力ファイルをこのステップの作業ディレクトリにコピー (src.data.extract が特定の場所を期待する場合があるため)
            # また、入力ファイル名にモデル名を含めることで、デバッグ時の識別を容易にする
            persistent_input_file = self.output_dir / f"{model_name}{input_file_path.suffix}"
            if not persistent_input_file.exists() or persistent_input_file.stat().st_mtime < input_file_path.stat().st_mtime:
                shutil.copy2(input_file_path, persistent_input_file)
                logs += f"📋 入力ファイル '{input_file_path.name}' を作業ディレクトリにコピー: '{persistent_input_file}'\\n"
            else:
                logs += f"📋 入力ファイル '{persistent_input_file.name}' は作業ディレクトリに既に存在します。\\n"

            # 出力ファイルパス定義 (UniRigのコアスクリプトが期待する固定名)
            # これらのファイルは self.output_dir (例: /app/pipeline_work/model_name/01_extracted_mesh/) に生成される
            output_npz_path = self.output_dir / "raw_data.npz"
            output_datalist_path = self.output_dir / "inference_datalist.txt"
            
            # UniRigの src.data.extract スクリプト用の設定ファイルパス
            # この設定ファイルはリポジトリの固定パスにあると仮定
            config_file_path = Path("/app/configs/data/quick_inference.yaml") # 指示書に基づき修正
            if not config_file_path.exists():
                # Fallback or default config if specific one not found
                # For now, let's assume it must exist or try a more generic one if specified in docs.
                # Based on original script, it was /app/configs/extract_config.yaml
                # The original instructions mention configs/data/quick_inference.yaml for extract.sh
                # Let's stick to quick_inference.yaml as per the more detailed original script context.
                alt_config_path = Path("/app/configs/extract_config.yaml")
                if alt_config_path.exists():
                    config_file_path = alt_config_path
                    logs += f"⚠️ メイン設定ファイル {config_file_path} が見つかりません。代替 {alt_config_path} を使用します。\\n"
                else:
                    error_msg = f"[FAIL] 設定ファイルが見つかりません: {config_file_path} および {alt_config_path}"
                    self.logger.error(error_msg)
                    return False, error_msg, {}
            
            logs += f"🔍 メッシュ抽出開始: '{persistent_input_file.name}' を使用\\n"
            logs += f"⚙️ 設定ファイル: '{config_file_path}'\\n"
            logs += f"[FILE] 出力先ディレクトリ (メッシュ抽出): '{self.output_dir}'\\n"
            
            # UniRig src.data.extract 実行コマンド（全必須パラメータ提供）
            cmd = [
                sys.executable, "-m", "src.data.extract",
                "--config", str(config_file_path),
                "--require_suffix", ".glb,.fbx,.obj,.vrm",     # 受け入れるファイル拡張子
                "--faces_target_count", "8000",             # 目標面数（デフォルト）
                "--num_runs", "1",                          # 実行回数（単一ファイル処理）
                "--force_override", "true",                 # 既存ファイル上書き許可
                "--id", "0",                                # プロセスID（単一実行）
                "--time", str(int(time.time())),           # タイムスタンプ
                "--input", str(persistent_input_file),      # 入力ファイル（単一ファイル）
                "--output_dir", str(self.output_dir)        # このステップの出力ディレクトリ
            ]
            
            logs += f"🚀 実行コマンド: {' '.join(cmd)}\\n"
            
            env = os.environ.copy()
            env['PYTHONPATH'] = f"/app:{env.get('PYTHONPATH', '')}"
            # env['GRADIO'] = '1' # GRADIO環境変数はsrc.data.extractに影響しない可能性が高いのでコメントアウト
            
            start_time = time.time()
            result = subprocess.run(
                cmd,
                cwd="/app", # UniRigスクリプトは /app からの相対パスを期待することがある
                env=env,
                capture_output=True,
                text=True,
                timeout=300 # 5分タイムアウト
            )
            execution_time = time.time() - start_time
            logs += f"⏱️ 抽出スクリプト実行時間: {execution_time:.2f}秒\\n"
            
            # 🔧 Critical Fix: return codeに関係なくNPZファイル検索を実行
            # return code -11でもraw_data.npzが生成される場合があるため
            actual_npz_path = self._find_output_npz(self.output_dir, model_name)
            
            if result.returncode == 0:
                logs += "[OK] UniRig抽出プロセス正常終了\\n"
            else:
                logs += f"⚠️ UniRig抽出プロセス終了 (return code: {result.returncode})\\n"
                logs += f"STDOUT: {result.stdout}\\n"
                logs += f"STDERR: {result.stderr}\\n"
            
            # NPZファイルが見つかった場合は成功として処理
            if actual_npz_path:
                file_size = actual_npz_path.stat().st_size
                logs += f"📊 NPZファイル発見: '{actual_npz_path}' ({file_size:,} bytes)\\n"
                
                # inference_datalist.txt生成（原流処理互換性のため）
                datalist_content = str(actual_npz_path)
                with open(output_datalist_path, 'w', encoding='utf-8') as f:
                    f.write(datalist_content)
                logs += f"📄 inference_datalist.txt生成: '{output_datalist_path}'\\n"
                
                output_files: Dict[str, Any] = {
                    "extracted_npz": str(actual_npz_path), # Step2が期待するキー名
                    "datalist_txt": str(output_datalist_path),  # 原流処理互換
                    "model_name": model_name,
                    "persistent_input_path_in_step_dir": str(persistent_input_file) # このステップ内で使用した入力ファイルパス
                }
                if output_datalist_path.exists():
                    logs += f"📋 データリスト生成: '{output_datalist_path.name}'\\n"
                    output_files["datalist"] = str(output_datalist_path)
                else:
                    logs += f"⚠️ データリストファイル '{output_datalist_path.name}' は生成されませんでした。\\n"
                    output_files["datalist"] = None

                # テクスチャ保存処理 (Step0が主担当だが、フォールバックまたは追加情報として)
                if preserve_textures_in_step1:
                    texture_info = self._preserve_texture_metadata_in_step1(persistent_input_file, model_name)
                    output_files.update(texture_info)
                    logs += f"🎨 (Step1) テクスチャメタデータ保存試行完了。結果: {texture_info.get('texture_metadata')}\\n"
                
                logs += "[OK] Step 1: メッシュ抽出完了\\n"
                return True, logs, output_files
            else:
                error_msg = f"[FAIL] NPZファイルが見つかりません。検索パターン:\\n"
                error_msg += f"- {self.output_dir / 'raw_data.npz'}\\n"
                error_msg += f"- {self.output_dir / model_name / 'raw_data.npz'}\\n"
                error_msg += f"- {self.output_dir / f'{model_name}.npz'}\\n"
                if result.returncode != 0:
                    error_msg += f"Return code: {result.returncode}\\n"
                    error_msg += f"STDOUT:\\n{result.stdout}\\nSTDERR:\\n{result.stderr}"
                logs += error_msg
                self.logger.error(error_msg)
                return False, logs, {}
                
        except subprocess.TimeoutExpired:
            error_msg = "[FAIL] タイムアウト: メッシュ抽出処理が5分を超過しました"
            logs += error_msg + "\\n"
            self.logger.error(error_msg)
            return False, logs, {}
        except Exception as e:
            error_msg = f"[FAIL] Step 1 実行エラー: {type(e).__name__} - {e}"
            logs += error_msg + "\\n"
            self.logger.error(error_msg, exc_info=True)
            return False, logs, {}
    
    def _preserve_texture_metadata_in_step1(self, source_model_file: Path, model_name: str) -> Dict[str, Optional[str]]:
        """
        このステップ内でテクスチャメタデータを保存する（主にStep0の補完またはデバッグ用）。
        Step0がアセット保存の主担当。
        """
        try:
            # テクスチャメタデータ用のディレクトリ (self.output_dir 内)
            step1_texture_metadata_dir = self.output_dir / "step1_texture_info"
            step1_texture_metadata_dir.mkdir(exist_ok=True)
            
            metadata_file_path = step1_texture_metadata_dir / f"{model_name}_step1_texture_metadata.json"
            
            metadata = {
                "model_name": model_name,
                "source_model_in_step1_dir": str(source_model_file),
                "preserved_at_step1": time.time(),
                "info": "This metadata is a supplementary record from Step1. Primary asset preservation is handled by Step0."
                # ここにBlenderなどを使って実際のテクスチャ情報を抽出するロジックを追加可能
            }
            
            with open(metadata_file_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"(Step1) テクスチャメタデータを保存しました: {metadata_file_path}")
            return {
                "step1_texture_metadata": str(metadata_file_path),
                "step1_texture_info_dir": str(step1_texture_metadata_dir)
            }
        except Exception as e:
            self.logger.warning(f"(Step1) テクスチャメタデータ保存エラー: {e}", exc_info=True)
            return {"step1_texture_metadata": None, "step1_texture_info_dir": None}

def execute_step1(
    input_file_path: Path, 
    model_name: str, 
    step_output_dir: Path, 
    logger_instance: logging.Logger,
    preserve_textures_in_step1: bool = False
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Step 1: 3Dモデルからメッシュデータを抽出します。

    Args:
        input_file_path: 入力3Dモデルファイルパス (絶対パス)
        model_name: モデル名
        step_output_dir: このステップ専用の出力ディレクトリパス (絶対パス)
        logger_instance: app.pyから渡されるロガーインスタンス
        preserve_textures_in_step1: Step1内で追加のテクスチャ保存を行うか

    Returns:
        success: 成功フラグ (True/False)
        logs: 実行ログメッセージ
        output_files: 出力ファイル辞書
    """
    try:
        extractor = Step1Extract(output_dir=step_output_dir, logger_instance=logger_instance)
        return extractor.extract_mesh(input_file_path, model_name, preserve_textures_in_step1)
    except Exception as e:
        error_message = f"Step 1 実行準備中に予期せぬエラーが発生: {type(e).__name__} - {e}"
        logger_instance.error(error_message, exc_info=True)
        return False, error_message, {}

if __name__ == '__main__':
    # --- Step1単体テスト ---
    # 実際のパイプラインではapp.pyから呼び出されます
    
    import json
    
    test_logger = logging.getLogger("Step1Extract_Test")
    test_logger.setLevel(logging.INFO)
    test_handler = logging.StreamHandler(sys.stdout)
    test_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    test_logger.addHandler(test_handler)
    test_logger.propagate = False

    test_model_name = "test_bird_step1"
    pipeline_base_dir = Path("/app/pipeline_work")
    step_output_dir = pipeline_base_dir / test_model_name / "01_extracted_mesh"
    
    # テスト用入力ファイル (実際のファイルが必要)
    test_input_file = Path("/app/examples/bird.glb")
    
    if not test_input_file.exists():
        test_logger.error(f"テスト用入力ファイルが見つかりません: {test_input_file}")
        test_logger.error("実際のStep1-Step2連携テストにはapp.pyを使用してください")
        exit(1)

    test_logger.info(f"--- Step1Extract 単体テスト開始 ---")
    test_logger.info(f"入力: {test_input_file}")
    test_logger.info(f"出力: {step_output_dir}")

    success, logs, files = execute_step1(
        input_file_path=test_input_file,
        model_name=test_model_name,
        step_output_dir=step_output_dir,
        logger_instance=test_logger,
        preserve_textures_in_step1=False
    )
    
    test_logger.info(f"結果: {'成功' if success else '失敗'}")
    if success:
        test_logger.info(f"出力ファイル: {json.dumps(files, indent=2)}")
    else:
        test_logger.error(f"エラーログ: {logs}")

    test_logger.info("--- Step1Extract 単体テスト完了 ---")
