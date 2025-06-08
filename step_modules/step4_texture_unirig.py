"""
Step 4 UniRig 本格実装 - テクスチャ統合
UniRigのsrc.inference.mergeを使用した本格的なテクスチャ統合

責務: リギング済みFBX + オリジナルテクスチャ → 最終リギング済みFBX
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Tuple, Dict
import time

logger = logging.getLogger(__name__)

class Step4TextureUniRig:
    """Step 4: UniRig本格テクスチャ統合モジュール"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    def merge_textures(self, skinned_fbx: str, original_model: str, model_name: str) -> Tuple[bool, str, Dict]:
        """
        UniRigを使用したテクスチャ統合の実行
        
        Args:
            skinned_fbx: 入力リギング済みFBXファイルパス
            original_model: オリジナル3Dモデルファイルパス  
            model_name: モデル名（出力ファイル名に使用）
            
        Returns:
            (success, logs, output_files)
        """
        try:
            start_time = time.time()
            logger.info(f"Step 4 UniRig本格実装開始: skinned={skinned_fbx}, original={original_model} → {model_name}")
            
            # 出力ファイルパス
            output_fbx = self.output_dir / f"{model_name}_final.fbx"
            
            # 入力データの検証
            if not self._validate_input_files(skinned_fbx, original_model):
                return False, "入力ファイルの検証に失敗", {}
            
            # UniRig merge.pyを実行
            success, merge_logs = self._run_unirig_merge(
                source=original_model,
                target=skinned_fbx, 
                output=str(output_fbx)
            )
            
            if not success:
                return False, f"UniRig テクスチャマージに失敗: {merge_logs}", {}
            
            # 出力ファイル情報
            output_files = {
                "final_fbx": str(output_fbx),
                "file_size_fbx": output_fbx.stat().st_size if output_fbx.exists() else 0
            }
            
            processing_time = time.time() - start_time
            
            logs = f"""
Step 4 (UniRig本格テクスチャ統合) 完了:
- 入力リギング済みFBX: {skinned_fbx}
- オリジナルモデル: {original_model}
- 最終FBX: {output_fbx} ({output_files['file_size_fbx']} bytes)
- 処理時間: {processing_time:.2f}秒

UniRig マージ詳細:
{merge_logs}
"""
            
            logger.info(f"Step 4 UniRig本格実装完了: {output_fbx} ({output_files['file_size_fbx']} bytes)")
            return True, logs.strip(), output_files
            
        except Exception as e:
            error_msg = f"Step 4 UniRig本格テクスチャ統合エラー: {e}"
            logger.error(error_msg)
            return False, error_msg, {}
    
    def _validate_input_files(self, skinned_fbx: str, original_model: str) -> bool:
        """入力ファイルの検証"""
        try:
            skinned_path = Path(skinned_fbx)
            original_path = Path(original_model)
            
            if not skinned_path.exists():
                logger.error(f"リギング済みFBXファイルが存在しません: {skinned_fbx}")
                return False
            
            if not original_path.exists():
                logger.error(f"オリジナルモデルファイルが存在しません: {original_model}")
                return False
            
            # ファイルサイズチェック
            skinned_size = skinned_path.stat().st_size
            original_size = original_path.stat().st_size
            
            if skinned_size == 0:
                logger.error(f"リギング済みFBXファイルが空です: {skinned_fbx}")
                return False
            
            if original_size == 0:
                logger.error(f"オリジナルモデルファイルが空です: {original_model}")
                return False
            
            logger.info(f"入力ファイル検証OK: skinned={skinned_size} bytes, original={original_size} bytes")
            return True
            
        except Exception as e:
            logger.error(f"入力ファイル検証エラー: {e}")
            return False
    
    def _run_unirig_merge(self, source: str, target: str, output: str) -> Tuple[bool, str]:
        """UniRigのmerge.pyを実行"""
        try:
            # 作業ディレクトリを/appに変更
            original_cwd = os.getcwd()
            os.chdir("/app")
            
            # UniRig merge.pyコマンド構築
            cmd = [
                "python", "-m", "src.inference.merge",
                "--require_suffix=obj,fbx,FBX,dae,glb,gltf,vrm",
                "--num_runs=1",
                "--id=0",
                f"--source={source}",
                f"--target={target}",
                f"--output={output}"
            ]
            
            logger.info(f"UniRig merge実行: {' '.join(cmd)}")
            
            # サブプロセスでUniRig merge.pyを実行
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10分タイムアウト
                cwd="/app"
            )
            
            # 元の作業ディレクトリに戻す
            os.chdir(original_cwd)
            
            # 実行結果の確認
            if result.returncode == 0:
                logs = f"UniRig merge成功:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
                logger.info("UniRig merge成功")
                return True, logs
            else:
                logs = f"UniRig merge失敗 (code={result.returncode}):\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
                logger.error(f"UniRig merge失敗: code={result.returncode}")
                return False, logs
            
        except subprocess.TimeoutExpired:
            os.chdir(original_cwd)
            error_msg = "UniRig merge タイムアウト (600秒)"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            os.chdir(original_cwd)
            error_msg = f"UniRig merge実行エラー: {e}"
            logger.error(error_msg)
            return False, error_msg


def merge_textures(skinned_fbx: str, original_model: str, model_name: str, output_dir: Path) -> Tuple[bool, str, Dict]:
    """
    Step 4 UniRig本格テクスチャ統合のエントリーポイント
    """
    step4 = Step4TextureUniRig(output_dir)
    return step4.merge_textures(skinned_fbx, original_model, model_name)
