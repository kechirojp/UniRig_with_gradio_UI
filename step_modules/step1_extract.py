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
        生成されたNPZファイルを検索（原流処理互換 + 統一命名規則対応）
        
        Args:
            output_dir: 出力ディレクトリ
            model_name: モデル名
            
        Returns:
            見つかったNPZファイルパス（見つからない場合はNone）
        """
        # 原流処理互換: raw_data.npz（固定名）
        raw_data_npz = output_dir / "raw_data.npz"
        if raw_data_npz.exists():
            return raw_data_npz
            
        # 統一命名規則: {model_name}_mesh.npz（バックアップ検索）
        unified_mesh_npz = output_dir / f"{model_name}_mesh.npz"
        if unified_mesh_npz.exists():
            return unified_mesh_npz
            
        # ファイルが見つからない場合
        self.logger.warning(f"NPZファイルが見つかりません: {output_dir}")
        return None

    def _create_unified_naming_copy(self, original_npz: Path, model_name: str) -> Path:
        """
        原流処理互換ファイルから統一命名規則ファイルをコピー作成
        
        Args:
            original_npz: 原流処理で生成されたraw_data.npz
            model_name: モデル名
            
        Returns:
            統一命名規則ファイルパス ({model_name}_mesh.npz)
        """
        unified_path = original_npz.parent / f"{model_name}_mesh.npz"
        
        if not unified_path.exists():
            shutil.copy2(original_npz, unified_path)
            self.logger.info(f"統一命名規則ファイル作成: {unified_path}")
        
        return unified_path

    def extract_mesh(self, input_file_path: Path, model_name: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        固定ディレクトリ + 統一命名規則対応のメッシュ抽出
        
        Args:
            input_file_path: 入力3Dモデルファイルパス
            model_name: モデル名
            
        Returns:
            (success, logs, output_files)
        """
        logs = ""
        try:
            self.logger.info(f"Step1開始: {input_file_path} → {model_name}")
            
            if not input_file_path.exists():
                error_msg = f"入力ファイル不存在: {input_file_path}"
                return False, error_msg, {}
            
            # 原流処理互換実行
            success, extract_logs = self._execute_original_extract(input_file_path, model_name)
            logs += extract_logs
            
            if not success:
                return False, logs, {}
            
            # 出力ファイル確認と統一命名規則対応
            return self._handle_output_files(model_name, logs)
            
        except Exception as e:
            error_msg = f"Step1実行エラー: {e}"
            self.logger.error(error_msg)
            return False, error_msg, {}

    def _execute_original_extract(self, input_file: Path, model_name: str) -> Tuple[bool, str]:
        """
        原流処理extract.sh互換実行（決め打ちディレクトリ戦略対応）
        
        --output_dir引数により、設定ファイルのoutput_dataset_dirを直接上書きして
        決め打ちディレクトリに出力
        """
        logs = ""
        
        # ベース設定ファイル使用（動的生成不要）
        config_file = Path("/app/configs/data/quick_inference.yaml")
        if not config_file.exists():
            return False, f"設定ファイル不存在: {config_file}\n"
        
        logs += f"設定ファイル: {config_file}\n"
        
        # 原流処理互換コマンド実行（決め打ちディレクトリに直接出力）
        cmd = [
            sys.executable, "-m", "src.data.extract",
            "--config", str(config_file),
            "--require_suffix", "obj,fbx,FBX,dae,glb,gltf,vrm",
            "--faces_target_count", "50000",
            "--num_runs", "1",
            "--force_override", "true",
            "--id", "0",
            "--time", time.strftime("%Y_%m_%d_%H_%M_%S"),
            "--input", str(input_file),
            "--output_dir", str(self.output_dir)
        ]
        
        logs += f"実行コマンド: {' '.join(cmd)}\n"
        logs += f"決め打ち出力ディレクトリ: {self.output_dir}\n"
        
        try:
            result = subprocess.run(
                cmd,
                cwd="/app",
                capture_output=True,
                text=True,
                timeout=600
            )
            
            logs += f"extract実行完了（return code: {result.returncode}）\n"
            logs += f"stdout: {result.stdout}\n"
            if result.stderr:
                logs += f"stderr: {result.stderr}\n"
            
            # Segmentation Faultでもファイルが生成されている可能性があるので確認
            # src.data.extractの出力場所を包括的に検索
            search_locations = [
                # 決め打ちディレクトリ直接出力（理想）
                self.output_dir / "raw_data.npz",
                # get_files関数のサブディレクトリ作成パターン
                self.output_dir / input_file.stem / "raw_data.npz",
                # 入力ファイルと同じディレクトリへの出力パターン（実際の動作）
                input_file.parent / input_file.stem / "raw_data.npz",
                # その他の一般的な出力場所
                Path("/app/dataset_inference_clean/raw_data.npz"),
                Path(f"/app/examples/{model_name}/raw_data.npz"),
                Path(f"/app/pipeline_work/{model_name}/raw_data.npz"),
                Path(f"/app/pipeline_work/{model_name}/{model_name}/raw_data.npz")
            ]
            
            found_file = None
            for location in search_locations:
                if location.exists():
                    found_file = location
                    logs += f"✅ raw_data.npz発見: {found_file}\n"
                    break
            
            if found_file:
                # 決め打ちディレクトリの正しい場所に移動
                target_file = self.output_dir / "raw_data.npz"
                
                if found_file != target_file:
                    # ファイルを決め打ちディレクトリに移動
                    shutil.move(str(found_file), str(target_file))
                    logs += f"✅ 決め打ちディレクトリに移動: {target_file}\n"
                    
                    # 空のサブディレクトリがあれば削除
                    if found_file.parent != self.output_dir and found_file.parent.exists():
                        try:
                            if not list(found_file.parent.iterdir()):  # ディレクトリが空の場合
                                found_file.parent.rmdir()
                                logs += f"空のサブディレクトリクリーンアップ: {found_file.parent}\n"
                        except Exception as e:
                            logs += f"サブディレクトリクリーンアップ失敗 (無視): {e}\n"
                
                file_size = target_file.stat().st_size
                logs += f"✅ 決め打ちディレクトリ出力完了: {target_file} ({file_size:,} bytes)\n"
                return True, logs
            else:
                logs += f"❌ raw_data.npzがどこにも見つかりません\n"
                logs += f"検索場所: {[str(loc) for loc in search_locations]}\n"
                return False, logs
            
        except subprocess.CalledProcessError as e:
            logs += f"extract実行失敗: {e}\n"
            logs += f"stderr: {e.stderr}\n"
            return False, logs
        except subprocess.TimeoutExpired:
            logs += "extract実行タイムアウト (600秒)\n"
            return False, logs
        except Exception as e:
            logs += f"extract実行中に予期しないエラー: {e}\n"
            return False, logs
        finally:
            # クリーンアップは不要（設定ファイル生成していない）
            pass

    def _handle_output_files(self, model_name: str, logs: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        出力ファイル処理と統一命名規則対応（決め打ちディレクトリ戦略）
        """
        # 決め打ちディレクトリ直接出力確認 (固定名: raw_data.npz)
        raw_data_npz = self.output_dir / "raw_data.npz"
        
        if not raw_data_npz.exists():
            return False, logs + f"❌ 決め打ちディレクトリ出力不存在: {raw_data_npz}\n", {}
        
        # 統一命名規則ファイル作成
        unified_mesh_npz = self._create_unified_naming_copy(raw_data_npz, model_name)
        
        # ファイルサイズ確認
        raw_size = raw_data_npz.stat().st_size
        unified_size = unified_mesh_npz.stat().st_size
        
        logs += f"✅ Step1完了（決め打ちディレクトリ戦略）\n"
        logs += f"原流処理出力: {raw_data_npz} ({raw_size:,} bytes)\n"
        logs += f"統一命名出力: {unified_mesh_npz} ({unified_size:,} bytes)\n"
        
        return True, logs, {
            "extracted_npz": str(raw_data_npz),  # 原流処理互換
            "unified_mesh_npz": str(unified_mesh_npz)  # 統一命名規則
        }

def execute_step1(
    input_file_path: Path, 
    model_name: str, 
    step_output_dir: Path, 
    logger_instance: logging.Logger
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
        return extractor.extract_mesh(input_file_path, model_name)
    except Exception as e:
        error_message = f"Step 1 実行準備中に予期せぬエラーが発生: {type(e).__name__} - {e}"
        logger_instance.error(error_message, exc_info=True)
        return False, error_message, {}

# 外部インターフェース（統一命名規則対応）
def extract_mesh_step1(input_file_path: str, model_name: str, output_dir: str) -> Tuple[bool, str, Dict[str, Any]]:
    """Step1外部インターフェース - 統一命名規則対応"""
    try:
        step1 = Step1Extract(
            output_dir=Path(output_dir),
            logger_instance=None
        )
        return step1.extract_mesh(Path(input_file_path), model_name)
    except Exception as e:
        return False, f"Step1外部インターフェースエラー: {e}", {}

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
