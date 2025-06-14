"""
Step4 Module - 固定ディレクトリ + 統一命名規則対応
原流処理互換のマージ処理
"""

import sys
import subprocess
import shutil
from pathlib import Path
from typing import Tuple, Dict, Any
import logging

sys.path.append('/app')

class Step4Merge:
    """固定ディレクトリ + 統一命名規則対応のStep4"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
    
    def merge_skeleton_skinning(self, model_name: str, skeleton_files: Dict[str, str], skinning_files: Dict[str, str]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        固定ディレクトリ + 統一命名規則対応のマージ処理
        
        Args:
            model_name: モデル名
            skeleton_files: Step2の出力ファイル辞書
            skinning_files: Step3の出力ファイル辞書
            
        Returns:
            (success, logs, output_files)
        """
        logs = ""
        
        try:
            # 入力ファイル確認
            source_fbx = skeleton_files.get("skeleton_fbx")  # スケルトンFBX
            target_fbx = skinning_files.get("skinned_fbx")   # スキニングFBX
            
            if not source_fbx or not Path(source_fbx).exists():
                return False, f"スケルトンFBXファイル不存在: {source_fbx}\n", {}
            
            if not target_fbx or not Path(target_fbx).exists():
                return False, f"スキニングFBXファイル不存在: {target_fbx}\n", {}
            
            # 原流処理互換実行
            success, merge_logs = self._execute_original_merge(source_fbx, target_fbx, model_name)
            logs += merge_logs
            
            if not success:
                return False, logs, {}
            
            # 出力ファイル処理
            return self._handle_output_files(model_name, logs)
            
        except Exception as e:
            error_msg = f"Step4実行エラー: {e}"
            return False, error_msg, {}
    
    def _execute_original_merge(self, source_fbx: str, target_fbx: str, model_name: str) -> Tuple[bool, str]:
        """原流処理merge.sh互換実行"""
        logs = ""
        
        # 出力ファイルパス定義
        output_fbx = self.output_dir / f"{model_name}_merged.fbx"
        
        # src.inference.merge実行 (原流処理)
        cmd = [
            sys.executable, "-m", "src.inference.merge",
            "--source", source_fbx,
            "--target", target_fbx,
            "--output", str(output_fbx)
        ]
        
        logs += f"実行コマンド: {' '.join(cmd)}\n"
        
        try:
            result = subprocess.run(
                cmd,
                cwd="/app",
                capture_output=True,
                text=True,
                timeout=600,  # 10分
                check=True
            )
            
            logs += "merge実行成功\n"
            if result.stdout:
                logs += f"stdout: {result.stdout}\n"
            
            return True, logs
            
        except subprocess.CalledProcessError as e:
            logs += f"merge実行失敗: {e}\n"
            if e.stderr:
                logs += f"stderr: {e.stderr}\n"
            return False, logs
        except subprocess.TimeoutExpired:
            logs += "merge実行タイムアウト (10分)\n"
            return False, logs
    
    def _handle_output_files(self, model_name: str, logs: str) -> Tuple[bool, str, Dict[str, Any]]:
        """出力ファイル処理と統一命名規則対応"""
        
        # 統一命名規則出力ファイル確認
        merged_fbx = self.output_dir / f"{model_name}_merged.fbx"
        
        if not merged_fbx.exists():
            return False, logs + f"マージ出力ファイル不存在: {merged_fbx}\n", {}
        
        # ファイルサイズ確認
        fbx_size = merged_fbx.stat().st_size
        
        logs += f"✅ Step4完了\n"
        logs += f"マージ済みFBX: {merged_fbx} ({fbx_size:,} bytes)\n"
        
        return True, logs, {
            "merged_fbx": str(merged_fbx)  # 統一命名規則
        }

# 外部インターフェース
def merge_skeleton_skinning_step4(model_name: str, skeleton_files: Dict[str, str], skinning_files: Dict[str, str], output_dir: str) -> Tuple[bool, str, Dict[str, Any]]:
    """Step4外部インターフェース - 統一命名規則対応"""
    try:
        step4 = Step4Merge(Path(output_dir))
        return step4.merge_skeleton_skinning(model_name, skeleton_files, skinning_files)
    except Exception as e:
        return False, f"Step4外部インターフェースエラー: {e}", {}
