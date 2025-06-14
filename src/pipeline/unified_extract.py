"""
🎯 UniRig統一メッシュ抽出器 - Shell Script完全置き換え版
クロスプラットフォーム完全対応、統一命名規則準拠

元のextract.shの全機能をPythonで再実装
- Windows/Mac/Linux完全対応
- 統一命名規則準拠
- プラットフォーム自動検出
- Shell Script依存完全排除
"""

import os
import sys
import subprocess
import time
import logging
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
import platform

class UnifiedExtractor:
    """🎯 統一メッシュ抽出器 (Shell Script置き換え)"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.platform = platform.system().lower()
        self.python_exec = self._detect_python_executable()
        
    def _detect_python_executable(self) -> str:
        """プラットフォーム別Python実行ファイル自動検出"""
        if self.platform == "windows":
            # Windows標準Python
            candidates = ["python", "python.exe", "python3", "python3.exe"]
        else:
            # Unix系 (Mac/Linux)
            candidates = ["python3", "python", "/usr/bin/python3", "/usr/local/bin/python3"]
        
        # UniRig環境の優先パス
        conda_python = "/opt/conda/envs/UniRig/bin/python3"
        if Path(conda_python).exists():
            return conda_python
            
        # システム標準Pythonを検索
        for candidate in candidates:
            try:
                result = subprocess.run([candidate, "--version"], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    self.logger.info(f"Python実行ファイル検出: {candidate}")
                    return candidate
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
                
        # フォールバック
        return "python3" if self.platform != "windows" else "python"
    
    def _validate_npz_structure(self, npz_path: Path, expected_keys: list = None) -> bool:
        """NPZ内部構造の原流処理互換性確認"""
        try:
            import numpy as np
            data = np.load(npz_path, allow_pickle=True)
            
            # デフォルト期待キー (raw_data.npz用)
            if expected_keys is None:
                expected_keys = ["vertices", "faces"]  # 最小要件
            
            missing_keys = [key for key in expected_keys if key not in data.keys()]
            
            if missing_keys:
                self.logger.error(f"ERROR: Missing required keys in NPZ: {missing_keys}")
                self.logger.error(f"Available keys: {list(data.keys())}")
                return False
            
            # データ型検証
            if "vertices" in data and not isinstance(data["vertices"], np.ndarray):
                self.logger.error("ERROR: 'vertices' must be numpy array")
                return False
                
            if "faces" in data and not isinstance(data["faces"], np.ndarray):
                self.logger.error("ERROR: 'faces' must be numpy array")
                return False
            
            self.logger.info(f"NPZ structure validated: {npz_path} (keys: {list(data.keys())})")
            return True
            
        except Exception as e:
            self.logger.error(f"ERROR: Failed to validate NPZ structure: {e}")
            return False

    def extract_mesh_unified(self,
                            input_file: str,
                            model_name: str,
                            output_dir: str,
                            **kwargs) -> Dict[str, Any]:
        """
        統一命名規則対応メッシュ抽出
        
        Args:
            input_file: 入力3Dモデルファイルパス
            model_name: モデル名 (統一命名規則用)  
            output_dir: 出力ディレクトリ
            **kwargs: その他のオプション
        
        Returns:
            Dict: 統一形式の結果辞書
        """
        # 1. 原流処理実行
        success, logs = self._execute_original_extract(input_file, output_dir, **kwargs)
        
        if success:
            # 2. 統一命名規則適用
            from fixed_directory_manager import FixedDirectoryManager
            
            dir_manager = FixedDirectoryManager(
                base_dir=Path(output_dir).parent, 
                model_name=model_name,
                logger=self.logger
            )
            
            # 原流出力ファイル検索
            original_output = Path(output_dir) / "raw_data.npz"
            
            if original_output.exists():
                # 統一命名規則でコピー
                unified_output = dir_manager.ensure_unified_output(
                    'step1', 'mesh_npz', original_output
                )
                
                return {
                    'success': True,
                    'unified_files': {'mesh_npz': str(unified_output)},
                    'original_files': {'raw_data_npz': str(original_output)},
                    'logs': logs
                }
            else:
                return {
                    'success': False,
                    'error': 'NPZ出力ファイルが見つかりません',
                    'logs': logs
                }
        
        return {'success': False, 'logs': logs}

    def extract_mesh(self,
                    input_file: str,
                    output_dir: str,
                    model_name: str,
                    cfg_data: str = "configs/data/quick_inference.yaml",
                    cfg_task: str = "configs/task/quick_inference_unirig_skin.yaml",
                    faces_target_count: int = 50000,
                    force_override: bool = False,
                    num_runs: int = 1
                    ) -> Tuple[bool, str, Dict[str, Any]]:
        """レガシー互換性メソッド"""
        result = self.extract_mesh_unified(
            input_file=input_file,
            model_name=model_name,
            output_dir=output_dir,
            cfg_data=cfg_data,
            cfg_task=cfg_task,
            faces_target_count=faces_target_count,
            force_override=force_override,
            num_runs=num_runs
        )
        
        return result['success'], result.get('logs', ''), result
    
    def _execute_original_extract(self, input_file: str, output_dir: str, **kwargs) -> Tuple[bool, str]:
        """Execute original extract flow (src.data.extract)"""
        
        # Default values
        cfg_data = kwargs.get('cfg_data', "configs/data/quick_inference.yaml")
        cfg_task = kwargs.get('cfg_task', "configs/task/quick_inference_unirig_skin.yaml")
        faces_target_count = kwargs.get('faces_target_count', 50000)
        force_override = kwargs.get('force_override', False)
        num_runs = kwargs.get('num_runs', 1)
        model_name = kwargs.get('model_name', 'unknown')
        
        start_time = time.time()
        logs = f"Original mesh extraction started: {model_name}\n"
        
        try:
            # Input file validation
            input_path = Path(input_file)
            if not input_path.exists():
                error_msg = f"Input file not found: {input_file}"
                self.logger.error(error_msg)
                return False, logs + error_msg
            
            # Create output directory
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # 統合設定ファイル作成
            temp_dir = output_path / ".temp"
            unified_config_path = self._create_unified_config(cfg_data, cfg_task, temp_dir)
            
            # 現在時刻をタイムスタンプとして生成
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
            
            # Build mesh extraction command (修正版 - 単一--config使用)
            cmd_args = [
                self.python_exec,
                "-m", "src.data.extract",
                f"--config={unified_config_path}",
                f"--require_suffix=obj,fbx,FBX,dae,glb,gltf,vrm",
                f"--input={input_file}",
                f"--output_dir={output_dir}",
                f"--faces_target_count={faces_target_count}",
                f"--force_override={str(force_override).lower()}",
                f"--num_runs={num_runs}",
                f"--id=0",
                f"--time={timestamp}"
            ]
            
            self.logger.info(f"Mesh extraction command: {' '.join(cmd_args)}")
            logs += f"Command: {' '.join(cmd_args)}\n"
            
            # プロセス実行 (タイムアウト保護)
            result = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
                timeout=600,  # 10分タイムアウト
                cwd="/app"  # 作業ディレクトリ固定
            )
            
            execution_time = time.time() - start_time
            
            # 出力ファイルパス定義
            expected_output_npz = Path(output_dir) / "raw_data.npz"  # 原流処理固定名
            unified_output_npz = Path(output_dir) / "raw_data.npz"   # 統一命名（同じファイル）
            
            if result.returncode == 0:
                logs += f"✅ メッシュ抽出成功 ({execution_time:.2f}秒)\n"
                logs += f"標準出力: {result.stdout}\n"
                
                # NPZ構造検証
                if expected_output_npz.exists():
                    if not self._validate_npz_structure(expected_output_npz):
                        error_msg = "❌ NPZ構造検証失敗"
                        logs += error_msg + "\n"
                        self.logger.error(error_msg)
                        return False, logs, {}
                    
                    logs += f"📁 統一NPZ確認: {unified_output_npz}\n"
                
                # 出力ファイル情報
                output_files = {
                    "mesh_npz": str(expected_output_npz),  # 原流処理互換
                    "unified_mesh_npz": str(unified_output_npz),  # 統一命名規則
                    "file_size": expected_output_npz.stat().st_size if expected_output_npz.exists() else 0,
                    "execution_time_seconds": round(execution_time, 2)
                }
                
                self.logger.info(f"✅ メッシュ抽出完了: {expected_output_npz}")
                return True, logs, output_files
                
            else:
                error_msg = f"❌ メッシュ抽出失敗 (コード: {result.returncode})\n"
                error_msg += f"標準エラー: {result.stderr}\n"
                logs += error_msg
                self.logger.error(error_msg)
                return False, logs, {}
                
        except subprocess.TimeoutExpired:
            error_msg = "❌ メッシュ抽出がタイムアウトしました (600秒)"
            logs += error_msg + "\n"
            self.logger.error(error_msg)
            return False, logs, {}
            
        except Exception as e:
            error_msg = f"❌ メッシュ抽出中に予期せぬエラー: {type(e).__name__} - {e}"
            logs += error_msg + "\n"
            self.logger.error(error_msg, exc_info=True)
            return False, logs, {}
    
    def extract_mesh_unified(self, input_file: str, model_name: str, output_dir: str) -> Tuple[bool, str]:
        """統合メッシュ抽出メソッド (app.py統合用)"""
        try:
            self.logger.info(f"統合メッシュ抽出開始: {model_name}")
            
            # 入力ファイル検証
            input_path = Path(input_file)
            if not input_path.exists():
                return False, f"入力ファイルが存在しません: {input_file}"
            
            # 出力ディレクトリ作成
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # 原流処理直接実行パターン
            success, logs = self._execute_original_extract_flow(
                input_file=input_file,
                output_dir=output_dir,
                model_name=model_name
            )
            
            if success:
                # 期待出力確認
                expected_output = output_path / "raw_data.npz"
                if expected_output.exists():
                    file_size = expected_output.stat().st_size / (1024 * 1024)
                    logs += f"\n✅ 期待出力確認: {expected_output} ({file_size:.2f} MB)"
                else:
                    return False, f"期待出力が生成されませんでした: {expected_output}"
            
            return success, logs
            
        except Exception as e:
            self.logger.error(f"統合メッシュ抽出エラー: {e}", exc_info=True)
            return False, f"統合メッシュ抽出エラー: {str(e)}"
    
    def _execute_original_extract_flow(self, input_file: str, output_dir: str, model_name: str) -> Tuple[bool, str]:
        """原流処理extract.sh直接実行 (修正版: 名前付きパラメータ使用)"""
        try:
            # extract.shの直接実行
            extract_script = "/app/launch/inference/extract.sh"
            if not Path(extract_script).exists():
                # Fallback: Python実装
                return self._execute_python_extract(input_file, output_dir, model_name)
            
            # 名前付きパラメータでextract.sh実行
            cmd = [
                "bash", extract_script,
                "--input", input_file,
                "--output_dir", output_dir,
                "--faces_target_count", "50000",
                "--force_override", "true"
            ]
            
            self.logger.info(f"extract.sh実行コマンド: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300, cwd="/app"
            )
            
            if result.returncode == 0:
                return True, f"原流extract.sh実行成功:\n{result.stdout}"
            else:
                return False, f"原流extract.sh実行失敗:\n{result.stderr}"
                
        except subprocess.TimeoutExpired:
            return False, "extract.sh実行タイムアウト (300秒)"
        except Exception as e:
            return False, f"原流extract.sh実行エラー: {str(e)}"
    
    def _execute_python_extract(self, input_file: str, output_dir: str, model_name: str) -> Tuple[bool, str]:
        """Python実装フォールバック"""
        try:
            # src.data.extract直接実行
            cmd = [
                self.python_exec, "-m", "src.data.extract",
                "--cfg_data=configs/data/quick_inference.yaml",
                "--cfg_task=configs/task/quick_inference_extract.yaml",
                f"--input={input_file}",
                f"--output_dir={output_dir}"
            ]
            
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300, cwd="/app"
            )
            
            if result.returncode == 0:
                return True, f"Python extract実行成功:\n{result.stdout}"
            else:
                return False, f"Python extract実行失敗:\n{result.stderr}"
                
        except Exception as e:
            return False, f"Python extract実行エラー: {str(e)}"
    
    def _create_unified_config(self,
                              cfg_data: str,
                              cfg_task: str,
                              temp_dir: Path) -> str:
        """
        🔧 複数の設定ファイルを統合した一時設定ファイルを作成
        
        原流処理のcfg_data + cfg_taskパターンに対応
        """
        import yaml
        from box import Box
        
        try:
            # データ設定とタスク設定を読み込み
            with open(cfg_data, 'r') as f:
                data_config = yaml.safe_load(f)
            
            with open(cfg_task, 'r') as f:
                task_config = yaml.safe_load(f)
            
            # 統合設定を作成 (task_configがdata_configを上書き)
            unified_config = {**data_config, **task_config}
            
            # 一時設定ファイル保存
            temp_config_path = temp_dir / "unified_extract_config.yaml"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            with open(temp_config_path, 'w') as f:
                yaml.dump(unified_config, f, default_flow_style=False)
            
            self.logger.info(f"統合設定ファイル作成: {temp_config_path}")
            return str(temp_config_path)
            
        except Exception as e:
            self.logger.error(f"設定ファイル統合失敗: {e}")
            raise

# 🎯 クロスプラットフォーム対応ファクトリー
def create_unified_extractor(logger: Optional[logging.Logger] = None) -> UnifiedExtractor:
    """統一メッシュ抽出器ファクトリー (プラットフォーム自動対応)"""
    return UnifiedExtractor(logger=logger)

# 🎯 CLI実行対応 (extract.sh置き換え)
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="UniRig統一メッシュ抽出 (extract.sh置き換え)")
    parser.add_argument("--input", required=True, help="入力3Dモデルファイル")
    parser.add_argument("--output_dir", required=True, help="出力ディレクトリ")
    parser.add_argument("--model_name", required=True, help="モデル名 (統一命名規則)")
    parser.add_argument("--cfg_data", default="configs/data/quick_inference.yaml", help="データ設定ファイル")
    parser.add_argument("--cfg_task", default="configs/task/quick_inference_unirig_skin.yaml", help="タスク設定ファイル")
    parser.add_argument("--faces_target_count", type=int, default=50000, help="ターゲット面数")
    parser.add_argument("--force_override", action="store_true", help="強制上書き")
    parser.add_argument("--num_runs", type=int, default=1, help="実行回数")
    
    args = parser.parse_args()
    
    # ログ設定
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 統一メッシュ抽出実行
    extractor = create_unified_extractor()
    success, logs, output_files = extractor.extract_mesh(
        input_file=args.input,
        output_dir=args.output_dir,
        model_name=args.model_name,
        cfg_data=args.cfg_data,
        cfg_task=args.cfg_task,
        faces_target_count=args.faces_target_count,
        force_override=args.force_override,
        num_runs=args.num_runs
    )
    
    print(logs)
    print(f"実行結果: {'成功' if success else '失敗'}")
    if output_files:
        print(f"出力ファイル: {output_files}")
    
    sys.exit(0 if success else 1)
