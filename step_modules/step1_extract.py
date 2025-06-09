"""
Step 1 Module - メッシュ抽出
独立した実行機能として、3Dモデルからメッシュデータを抽出

責務: 3Dモデルファイル → メッシュNPZファイル
入力: 3Dモデルファイルパス (.glb, .fbx, .obj等)
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
                error_msg = f"❌ 入力ファイルが見つかりません: {input_file_path}"
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
                    error_msg = f"❌ 設定ファイルが見つかりません: {config_file_path} および {alt_config_path}"
                    self.logger.error(error_msg)
                    return False, error_msg, {}
            
            logs += f"🔍 メッシュ抽出開始: '{persistent_input_file.name}' を使用\\n"
            logs += f"⚙️ 設定ファイル: '{config_file_path}'\\n"
            logs += f"📁 出力先ディレクトリ (メッシュ抽出): '{self.output_dir}'\\n"
            
            # UniRig src.data.extract 実行コマンド
            cmd = [
                sys.executable, "-m", "src.data.extract",
                "--config", str(config_file_path),
                "--model_path", str(persistent_input_file), # コピーされた永続ファイルを使用
                "--output_dir", str(self.output_dir)      # このステップの出力ディレクトリ
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
            
            if result.returncode == 0:
                logs += "✅ UniRig抽出プロセス正常終了\\n"
                if output_npz_path.exists():
                    file_size = output_npz_path.stat().st_size
                    logs += f"📊 NPZファイル生成: '{output_npz_path.name}' ({file_size:,} bytes)\\n"
                    
                    output_files: Dict[str, Any] = {
                        "extracted_npz": str(output_npz_path), # Step2が期待するキー名
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
                    
                    logs += "✅ Step 1: メッシュ抽出完了\\n"
                    return True, logs, output_files
                else:
                    error_msg = f"❌ NPZファイルが生成されませんでした: {output_npz_path}\\nSTDOUT:\\n{result.stdout}\\nSTDERR:\\n{result.stderr}"
                    logs += error_msg
                    self.logger.error(error_msg)
                    return False, logs, {}
            else:
                error_msg = f"❌ UniRig抽出プロセスエラー (コード: {result.returncode})\\nSTDOUT:\\n{result.stdout}\\nSTDERR:\\n{result.stderr}"
                logs += error_msg
                self.logger.error(error_msg)
                return False, logs, {}
                
        except subprocess.TimeoutExpired:
            error_msg = "❌ タイムアウト: メッシュ抽出処理が5分を超過しました"
            logs += error_msg + "\\n"
            self.logger.error(error_msg)
            return False, logs, {}
        except Exception as e:
            error_msg = f"❌ Step 1 実行エラー: {type(e).__name__} - {e}"
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
    # --- テスト設定 ---
    # このテストは、このスクリプトが単独で実行された場合にのみ動作します。
    # 実際のパイプラインではapp.pyから呼び出されます。
    
    # グローバルなテスト用ロガー設定
    test_logger = logging.getLogger("Step1Extract_Test")
    test_logger.setLevel(logging.DEBUG)
    test_handler = logging.StreamHandler(sys.stdout)
    test_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    test_logger.addHandler(test_handler)
    test_logger.propagate = False # 親ロガーへの伝播を防ぐ

    # テスト用の入力ファイルとモデル名
    # 注意: /app/examples/bird.glb が存在することを確認してください。
    # Dockerコンテナ内にサンプルファイルがない場合は、ローカルからコピーするか、
    # ダミーファイル作成ロジックを有効にしてください。
    test_input_model_filename = "bird.glb" # または他のテストしたいモデルファイル
    test_input_file_original_location = Path(f"/app/examples/{test_input_model_filename}")
    test_model_name = "test_bird_model" # pipeline_work/{model_name} の {model_name} に対応

    # Step0 (Asset Preservation) が作成するであろう想定の入力ファイルパス
    # このテストでは、Step0が完了し、その出力がStep1の入力になると仮定します。
    # 通常、Step0は /app/pipeline_work/{model_name}/00_asset_preservation/ にファイルを出力します。
    # Step1はその中にあるモデルファイル (例: preserved_model.glb) を入力として受け取ります。
    # ここでは簡略化のため、examplesにあるファイルを直接使いますが、
    # FileManagerによって解決されたパスが渡されることを想定しています。
    
    # このステップの出力ディレクトリ (app.pyのFileManagerが決定するパスを模倣)
    pipeline_base_dir = Path("/app/pipeline_work")
    step_specific_output_dir = pipeline_base_dir / test_model_name / "01_extracted_mesh"
    
    test_logger.info(f"--- Step1Extract モジュールテスト開始 ---")
    test_logger.info(f"テストモデル名: {test_model_name}")
    test_logger.info(f"入力ファイル (想定): {test_input_file_original_location}")
    test_logger.info(f"ステップ出力ディレクトリ: {step_specific_output_dir}")

    # テスト実行前に出力ディレクトリをクリーンアップ (任意)
    if step_specific_output_dir.exists():
        test_logger.info(f"既存のテスト出力ディレクトリ {step_specific_output_dir} をクリーンアップします。")
        try:
            shutil.rmtree(step_specific_output_dir)
        except OSError as e:
            test_logger.error(f"クリーンアップ失敗: {e}", exc_info=True)
            # クリーンアップ失敗時はテストを中止した方が良い場合もある
            # sys.exit(1) 
    step_specific_output_dir.mkdir(parents=True, exist_ok=True)

    # ダミー入力ファイルの作成 (もしexamplesにファイルがない場合)
    created_dummy_input = False
    if not test_input_file_original_location.exists():
        test_logger.warning(f"テスト用入力ファイル {test_input_file_original_location} が見つかりません。")
        test_logger.warning("代わりにダミーファイルを作成してテストを続行します。")
        # ダミーファイルは examples ディレクトリではなく、テスト用の作業ディレクトリに作成した方が良いかもしれない
        # ここでは元のパスに作成する
        test_input_file_original_location.parent.mkdir(parents=True, exist_ok=True)
        with open(test_input_file_original_location, 'w') as f:
            f.write("dummy glb data for testing Step1Extract")
        created_dummy_input = True
        test_logger.info(f"ダミー入力ファイルを作成: {test_input_file_original_location}")

    # execute_step1 関数を呼び出し
    # preserve_textures_in_step1 は通常Falseだが、テストのためにTrueにしてみることも可能
    success, logs, files = execute_step1(
        input_file_path=test_input_file_original_location,
        model_name=test_model_name,
        step_output_dir=step_specific_output_dir,
        logger_instance=test_logger,
        preserve_textures_in_step1=True 
    )
    
    test_logger.info("\\n--- テスト実行結果 ---")
    test_logger.info(f"  成功: {success}")
    test_logger.info(f"  ログ:\\n{logs}") # ログは複数行になることがあるので改行して表示
    test_logger.info(f"  出力ファイル情報: {json.dumps(files, indent=2)}")

    if success:
        test_logger.info("テスト成功。生成されたファイルを確認してください。")
        expected_npz = step_specific_output_dir / "raw_data.npz"
        if expected_npz.exists():
            test_logger.info(f"  ✅ NPZファイル '{expected_npz}' が期待通り生成されました。")
        else:
            test_logger.error(f"  ❌ NPZファイル '{expected_npz}' が見つかりません。")
    else:
        test_logger.error("テスト失敗。ログを確認してください。")

    # クリーンアップ (生成されたダミー入力ファイルのみ)
    # 出力ディレクトリは手動で確認・削除することを推奨
    if created_dummy_input and test_input_file_original_location.exists():
        try:
            os.remove(test_input_file_original_location)
            test_logger.info(f"クリーンアップ: ダミー入力ファイル {test_input_file_original_location} を削除しました。")
        except OSError as e:
            test_logger.error(f"ダミー入力ファイルの削除に失敗: {e}")
            
    test_logger.info("--- Step1Extract モジュールテスト完了 ---")
