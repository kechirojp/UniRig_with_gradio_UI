"""
Step 4 Module - スケルトン・スキンウェイトマージ（特化機能）
MICROSERVICE_GUIDE.md (2025年6月10日改訂) に基づく実装

責務:
- Step1、Step2、Step3の出力ファイルを統合
- スケルトンとスキンウェイトのマージに専念
- テクスチャ処理は除外（Step5に移譲）

データフロー:
- 入力: Step1・Step2・Step3の出力ファイル
- 出力: マージ済みFBXファイルパス
- 処理: `launch/inference/merge.sh` の機能を活用したマージ処理

設計方針:
- 機能特化: マージ処理のみに焦点
- 軽量化: テクスチャ統合機能を廃止
- 独立性: 他ステップとの環境汚染なし
"""

import os
import logging
import subprocess
import time
from pathlib import Path
from typing import Tuple, Dict, Optional, Any
import shutil
import traceback

logger = logging.getLogger(__name__)

class Step4Merge:
    """
    Step 4: スケルトン・スキンウェイトマージ（特化機能）
    
    新設計: マージ処理に特化した軽量実装
    - テクスチャ処理機能を完全廃止
    - launch/inference/merge.shの核心機能のみを活用
    - Step1-Step3の出力を統合してマージ済みFBXを生成
    """
    
    def __init__(self, output_dir: Path, logger_instance: Optional[logging.Logger] = None):
        """
        Step4初期化
        
        Args:
            output_dir: このステップの出力ディレクトリ（絶対パス）
            logger_instance: ロガーインスタンス
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger_instance if logger_instance else logging.getLogger(__name__)
        
    def merge_skeleton_skinning(self, 
                               model_name: str, 
                               step1_files: Dict[str, Any], 
                               step2_files: Dict[str, Any], 
                               step3_files: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        スケルトン・スキンウェイトマージの実行
        
        Args:
            model_name: モデル識別名
            step1_files: Step1出力ファイル辞書
            step2_files: Step2出力ファイル辞書  
            step3_files: Step3出力ファイル辞書
            
        Returns:
            (success, logs, output_files)
        """
        logs = ""
        
        try:
            self.logger.info(f"Step 4 開始: マージ処理 - {model_name}")
            
            # 入力ファイルの検証
            required_files = self._validate_input_files(step1_files, step2_files, step3_files)
            if not required_files['valid']:
                error_msg = f"❌ 入力ファイル検証失敗: {required_files['error']}"
                self.logger.error(error_msg)
                return False, error_msg, {}
            
            logs += f"✅ 入力ファイル検証完了\n"
            logs += f"📁 Step1メッシュ: {Path(required_files['mesh_npz']).name}\n"
            logs += f"🦴 Step2スケルトン: {Path(required_files['skeleton_fbx']).name}\n"
            logs += f"🎭 Step3スキニング: {Path(required_files['skinned_fbx']).name}\n"
            
            # 出力ファイルパス定義
            output_fbx_path = self.output_dir / f"{model_name}_merged.fbx"
            
            # マージ処理の実行
            success, merge_logs = self._execute_merge_process(
                skeleton_fbx=required_files['skeleton_fbx'],
                skinned_fbx=required_files['skinned_fbx'],
                output_path=output_fbx_path
            )
            
            logs += merge_logs
            
            if success and output_fbx_path.exists():
                file_size = output_fbx_path.stat().st_size
                logs += f"✅ マージ完了: {output_fbx_path.name} ({file_size:,} bytes)\n"
                
                output_files = {
                    "merged_fbx": str(output_fbx_path),
                    "model_name": model_name
                }
                
                return True, logs, output_files
            else:
                error_msg = f"❌ マージ処理失敗: 出力ファイルが生成されませんでした"
                logs += error_msg
                return False, logs, {}
                
        except Exception as e:
            error_msg = f"❌ Step 4 エラー: {str(e)}\n{traceback.format_exc()}"
            self.logger.error(error_msg)
            return False, error_msg, {}
    
    def _validate_input_files(self, step1_files: Dict, step2_files: Dict, step3_files: Dict) -> Dict[str, Any]:
        """
        入力ファイルの存在確認と検証
        
        Args:
            step1_files: Step1出力ファイル辞書
            step2_files: Step2出力ファイル辞書
            step3_files: Step3出力ファイル辞書
            
        Returns:
            検証結果辞書
        """
        try:
            # Step1からメッシュNPZファイル
            mesh_npz = step1_files.get('extracted_npz')
            if not mesh_npz or not Path(mesh_npz).exists():
                return {'valid': False, 'error': f"Step1メッシュファイルが見つかりません: {mesh_npz}"}
            
            # Step2からスケルトンFBXファイル
            skeleton_fbx = step2_files.get('skeleton_fbx')
            if not skeleton_fbx or not Path(skeleton_fbx).exists():
                return {'valid': False, 'error': f"Step2スケルトンファイルが見つかりません: {skeleton_fbx}"}
            
            # Step3からスキニング済みFBXファイル
            skinned_fbx = step3_files.get('skinned_fbx')
            if not skinned_fbx or not Path(skinned_fbx).exists():
                return {'valid': False, 'error': f"Step3スキニングファイルが見つかりません: {skinned_fbx}"}
            
            return {
                'valid': True,
                'mesh_npz': mesh_npz,
                'skeleton_fbx': skeleton_fbx,
                'skinned_fbx': skinned_fbx
            }
            
        except Exception as e:
            return {'valid': False, 'error': f"入力ファイル検証エラー: {str(e)}"}
    
    def _execute_merge_process(self, skeleton_fbx: str, skinned_fbx: str, output_path: Path) -> Tuple[bool, str]:
        """
        マージ処理の実行（launch/inference/merge.shの核心機能を活用）
        
        Args:
            skeleton_fbx: スケルトンFBXファイルパス
            skinned_fbx: スキニング済みFBXファイルパス
            output_path: 出力ファイルパス
            
        Returns:
            (success, logs)
        """
        logs = ""
        
        try:
            # merge.shスクリプトの存在確認
            merge_script = Path("/app/launch/inference/merge.sh")
            if not merge_script.exists():
                return False, f"❌ マージスクリプトが見つかりません: {merge_script}\n"
            
            logs += f"🚀 マージスクリプト実行: {merge_script.name}\n"
            logs += f"📥 スケルトン入力: {Path(skeleton_fbx).name}\n"
            logs += f"📥 スキニング入力: {Path(skinned_fbx).name}\n"
            logs += f"📤 マージ出力: {output_path.name}\n"
            
            # merge.shの実行
            cmd = [
                str(merge_script),
                skeleton_fbx,  # source (スケルトン)
                skinned_fbx,   # target (スキニング済み)
                str(output_path)  # output
            ]
            
            start_time = time.time()
            result = subprocess.run(
                cmd,
                cwd="/app",
                capture_output=True,
                text=True,
                timeout=300  # 5分タイムアウト
            )
            execution_time = time.time() - start_time
            
            logs += f"⏱️ マージ実行時間: {execution_time:.2f}秒\n"
            
            if result.returncode == 0:
                logs += f"✅ マージスクリプト正常終了\n"
                if result.stdout:
                    logs += f"📋 STDOUT: {result.stdout}\n"
                return True, logs
            else:
                logs += f"❌ マージスクリプト失敗 (リターンコード: {result.returncode})\n"
                if result.stderr:
                    logs += f"📋 STDERR: {result.stderr}\n"
                if result.stdout:
                    logs += f"📋 STDOUT: {result.stdout}\n"
                return False, logs
                
        except subprocess.TimeoutExpired:
            return False, logs + f"❌ マージ処理タイムアウト (300秒)\n"
        except Exception as e:
            return False, logs + f"❌ マージ処理エラー: {str(e)}\n"
    
    def _run_command(self, cmd: list, timeout: int = 300) -> Tuple[bool, str]:
        """
        安全なコマンド実行
        
        Args:
            cmd: 実行コマンドリスト
            timeout: タイムアウト秒数
            
        Returns:
            (success, output)
        """
        try:
            result = subprocess.run(
                cmd,
                cwd="/app",
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, f"コマンド失敗 (リターンコード: {result.returncode})\nSTDERR: {result.stderr}\nSTDOUT: {result.stdout}"
                
        except subprocess.TimeoutExpired:
            return False, f"コマンドタイムアウト ({timeout}秒)"
        except Exception as e:
            return False, f"コマンド実行エラー: {str(e)}"


# 互換性のための旧インターフェース（非推奨）
def merge_textures(model_name: str, skinned_file: str, original_file: str) -> Tuple[bool, str, Dict]:
    """
    旧インターフェース互換性のための関数（非推奨）
    
    Note: 新しいmerge_skeleton_skinning()を使用してください
    """
    logger.warning("旧インターフェース merge_textures() は非推奨です。merge_skeleton_skinning() を使用してください。")
    
    # 簡易的な実装（完全な互換性は保証されません）
    output_dir = Path("/tmp/step4_legacy")
    step4 = Step4Merge(output_dir)
    
    # 簡易的なファイル辞書を作成
    step1_files = {"extracted_npz": ""}  # 不明
    step2_files = {"skeleton_fbx": ""}   # 不明
    step3_files = {"skinned_fbx": skinned_file}
    
    return step4.merge_skeleton_skinning(model_name, step1_files, step2_files, step3_files)
