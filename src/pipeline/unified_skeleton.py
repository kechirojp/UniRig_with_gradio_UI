"""
🎯 UniRig統一スケルトン生成器 - Shell Script完全置き換え版
クロスプラットフォーム完全対応、統一命名規則準拠

元のgenerate_skeleton.shの全機能をPythonで再実装
- Windows/Mac/Linux完全対応
- 統一命名規則準拠
- 2段階処理 (前処理 + AI推論)
- Shell Script依存完全排除
"""

import os
import sys
import subprocess
import time
import logging
import shutil
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
import platform

class UnifiedSkeletonGenerator:
    """🎯 統一スケルトン生成器 (Shell Script置き換え)"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.platform = platform.system().lower()
        self.python_exec = self._detect_python_executable()
        
    def _detect_python_executable(self) -> str:
        """プラットフォーム別Python実行ファイル自動検出"""
        if self.platform == "windows":
            candidates = ["python", "python.exe", "python3", "python3.exe"]
        else:
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
                    return candidate
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
                
        return "python3" if self.platform != "windows" else "python"
    
    def generate_skeleton(self,
                         input_npz: str,
                         output_dir: str,
                         model_name: str,
                         skeleton_task: str = "configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml",
                         config: str = "configs/data/quick_inference.yaml",
                         seed: int = 12345,
                         force_override: bool = False,
                         faces_target_count: int = 50000
                         ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        🎯 統一スケルトン生成実行 (generate_skeleton.sh完全置き換え)
        
        Args:
            input_npz: 入力メッシュNPZファイル
            output_dir: 出力ディレクトリ
            model_name: モデル名 (統一命名規則用)
            skeleton_task: スケルトンタスク設定ファイル
            config: データ設定ファイル
            seed: ランダムシード
            force_override: 強制上書き
            faces_target_count: ターゲット面数
            
        Returns:
            (success, logs, output_files) - 統一命名規則準拠
        """
        
        start_time = time.time()
        logs = f"🎯 統一スケルトン生成開始: {model_name}\n"
        
        try:
            # 入力NPZ存在確認
            input_path = Path(input_npz)
            if not input_path.exists():
                error_msg = f"❌ 入力NPZファイルが見つかりません: {input_npz}"
                self.logger.error(error_msg)
                return False, logs + error_msg, {}
            
            # 出力ディレクトリ作成
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # 🎯 Phase 1: 前処理 (extract相当)
            logs += "📋 Phase 1: 前処理実行...\n"
            extract_success, extract_logs = self._run_extract_phase(
                input_npz, output_dir, config, force_override, faces_target_count
            )
            logs += extract_logs
            
            if not extract_success:
                return False, logs + "❌ 前処理段階で失敗", {}
            
            # 🎯 Phase 2: AI推論 (run.py相当)
            logs += "🧠 Phase 2: AI推論実行...\n"
            inference_success, inference_logs = self._run_inference_phase(
                output_dir, model_name, skeleton_task, seed
            )
            logs += inference_logs
            
            if not inference_success:
                return False, logs + "❌ AI推論段階で失敗", {}
            
            # 🎯 統一命名規則適用
            execution_time = time.time() - start_time
            output_files = self._apply_unified_naming(output_dir, model_name, execution_time)
            
            logs += f"✅ 統一スケルトン生成完了 ({execution_time:.2f}秒)\n"
            self.logger.info(f"✅ スケルトン生成完了: {model_name}")
            
            return True, logs, output_files
            
        except Exception as e:
            error_msg = f"❌ スケルトン生成中に予期せぬエラー: {type(e).__name__} - {e}"
            logs += error_msg + "\n"
            self.logger.error(error_msg, exc_info=True)
            return False, logs, {}
    
    def _run_extract_phase(self, input_npz: str, output_dir: str, config: str, 
                          force_override: bool, faces_target_count: int) -> Tuple[bool, str]:
        """Phase 1: 前処理実行"""
        cmd_args = [
            self.python_exec,
            "-m", "src.data.extract",
            f"--config={config}",
            f"--force_override={str(force_override).lower()}",
            f"--num_runs=1",
            f"--target_count={faces_target_count}",
            "--id=0",
            f"--input={input_npz}",
            f"--output_dir={output_dir}"
        ]
        
        try:
            result = subprocess.run(cmd_args, capture_output=True, text=True, 
                                  timeout=300, cwd="/app")
            
            if result.returncode == 0:
                return True, f"✅ 前処理成功\n{result.stdout}\n"
            else:
                return False, f"❌ 前処理失敗: {result.stderr}\n"
                
        except subprocess.TimeoutExpired:
            return False, "❌ 前処理タイムアウト (300秒)\n"
        except Exception as e:
            return False, f"❌ 前処理エラー: {e}\n"
    
    def _run_inference_phase(self, output_dir: str, model_name: str, 
                           skeleton_task: str, seed: int) -> Tuple[bool, str]:
        """Phase 2: AI推論実行"""
        cmd_args = [
            self.python_exec,
            "run.py",
            f"--task={skeleton_task}",
            f"--seed={seed}",
            f"--output_dir={output_dir}",
            f"--model_name={model_name}"  # 統一命名規則対応
        ]
        
        try:
            result = subprocess.run(cmd_args, capture_output=True, text=True, 
                                  timeout=600, cwd="/app")
            
            if result.returncode == 0:
                return True, f"✅ AI推論成功\n{result.stdout}\n"
            else:
                return False, f"❌ AI推論失敗: {result.stderr}\n"
                
        except subprocess.TimeoutExpired:
            return False, "❌ AI推論タイムアウト (600秒)\n"
        except Exception as e:
            return False, f"❌ AI推論エラー: {e}\n"
    
    def _apply_unified_naming(self, output_dir: str, model_name: str, 
                            execution_time: float) -> Dict[str, Any]:
        """統一命名規則適用 (決め打ちディレクトリ戦略準拠)"""
        output_path = Path(output_dir)
        
        # 🎯 決め打ちディレクトリ戦略準拠の統一ファイル名
        # 原流互換: {model_name}.fbx, predict_skeleton.npz (固定名維持)
        skeleton_fbx = output_path / f"{model_name}.fbx"  # サフィックスなし (原流期待値)
        skeleton_npz = output_path / "predict_skeleton.npz"  # 固定名 (原流期待値)
        
        # 原流処理出力確認と検証
        if skeleton_fbx.exists() and skeleton_npz.exists():
            self.logger.info(f"📁 原流互換ファイル確認済み: {skeleton_fbx.name}, {skeleton_npz.name}")
        else:
            # フォールバック検索 (原流処理出力パターン)
            fallback_patterns = {
                "skeleton.fbx": skeleton_fbx,
                "skeleton_model.fbx": skeleton_fbx,
                f"{model_name}_skeleton.fbx": skeleton_fbx
            }
            
            for pattern_name, target_path in fallback_patterns.items():
                pattern_path = output_path / pattern_name
                if pattern_path.exists() and not target_path.exists():
                    shutil.copy2(pattern_path, target_path)
                    self.logger.warning(f"📁 フォールバック適用: {pattern_name} → {target_path.name}")
        
        # 出力ファイル情報構築 (原流互換性優先)
        output_files = {
            "skeleton_fbx": str(skeleton_fbx) if skeleton_fbx.exists() else None,
            "skeleton_npz": str(skeleton_npz) if skeleton_npz.exists() else None,
            "file_size_fbx": skeleton_fbx.stat().st_size if skeleton_fbx.exists() else 0,
            "file_size_npz": skeleton_npz.stat().st_size if skeleton_npz.exists() else 0,
            "execution_time_seconds": round(execution_time, 2)
        }
        
        return output_files

    def generate_skeleton_unified(self, model_name: str, gender: str, extracted_file: str, output_dir: str) -> Tuple[bool, str]:
        """統一スケルトン生成メソッド（app.py統合用）"""
        try:
            self.logger.info(f"統合スケルトン生成開始: {model_name} (性別: {gender})")
            
            # 入力ファイル検証
            extracted_path = Path(extracted_file)
            if not extracted_path.exists():
                return False, f"入力ファイルが存在しません: {extracted_file}"
            
            # 出力ディレクトリ作成
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # デフォルト設定で原流処理相当実行
            success, logs, output_files = self.generate_skeleton(
                input_npz=extracted_file,
                output_dir=output_dir,
                model_name=model_name,
                skeleton_task="configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml",
                config="configs/data/quick_inference.yaml",
                seed=42,
                force_override=True,
                faces_target_count=50000
            )
            
            if success:
                # 期待出力確認 (決め打ちディレクトリ戦略準拠)
                expected_fbx = output_path / f"{model_name}.fbx"
                expected_npz = output_path / "predict_skeleton.npz"
                
                output_check = []
                if expected_fbx.exists():
                    file_size = expected_fbx.stat().st_size / (1024 * 1024)
                    output_check.append(f"✅ スケルトンFBX: {expected_fbx} ({file_size:.2f} MB)")
                else:
                    output_check.append(f"⚠️ スケルトンFBX未作成: {expected_fbx}")
                
                if expected_npz.exists():
                    file_size = expected_npz.stat().st_size / (1024 * 1024)
                    output_check.append(f"✅ スケルトンNPZ: {expected_npz} ({file_size:.2f} MB)")
                else:
                    output_check.append(f"⚠️ スケルトンNPZ未作成: {expected_npz}")
                
                logs += "\n期待出力確認:\n" + "\n".join(output_check)
            
            return success, logs
            
        except Exception as e:
            self.logger.error(f"統合スケルトン生成エラー: {e}", exc_info=True)
            return False, f"統合スケルトン生成エラー: {str(e)}"

# オーケストレーター統合エイリアス
class UnifiedSkeletonOrchestrator(UnifiedSkeletonGenerator):
    """app.py統合用エイリアス"""
    pass

# 🎯 クロスプラットフォーム対応ファクトリー
def create_unified_skeleton_generator(logger: Optional[logging.Logger] = None) -> UnifiedSkeletonGenerator:
    """統一スケルトン生成器ファクトリー (プラットフォーム自動対応)"""
    return UnifiedSkeletonGenerator(logger=logger)

# 🎯 CLI実行対応 (generate_skeleton.sh置き換え)
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="UniRig統一スケルトン生成 (generate_skeleton.sh置き換え)")
    parser.add_argument("--input_npz", required=True, help="入力メッシュNPZファイル")
    parser.add_argument("--output_dir", required=True, help="出力ディレクトリ")
    parser.add_argument("--model_name", required=True, help="モデル名 (統一命名規則)")
    parser.add_argument("--skeleton_task", default="configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml", help="スケルトンタスク設定")
    parser.add_argument("--config", default="configs/data/quick_inference.yaml", help="データ設定ファイル")
    parser.add_argument("--seed", type=int, default=12345, help="ランダムシード")
    parser.add_argument("--force_override", action="store_true", help="強制上書き")
    parser.add_argument("--faces_target_count", type=int, default=50000, help="ターゲット面数")
    
    args = parser.parse_args()
    
    # ログ設定
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 統一スケルトン生成実行
    generator = create_unified_skeleton_generator()
    success, logs, output_files = generator.generate_skeleton(
        input_npz=args.input_npz,
        output_dir=args.output_dir,
        model_name=args.model_name,
        skeleton_task=args.skeleton_task,
        config=args.config,
        seed=args.seed,
        force_override=args.force_override,
        faces_target_count=args.faces_target_count
    )
    
    print(logs)
    print(f"実行結果: {'成功' if success else '失敗'}")
    if output_files:
        print(f"出力ファイル: {output_files}")
    
    sys.exit(0 if success else 1)
