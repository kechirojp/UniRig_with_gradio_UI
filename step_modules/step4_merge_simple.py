"""
Step 4 Module - シンプルスケルトン・スキニングマージ
原UniRig互換の最小実装

データフロー改修方針 (2025年6月10日) 準拠:
- Step0依存削除: アセット保存データを使用しない
- 責務特化: スケルトン・スキニングマージに専念
- ディレクトリ構造: /app/pipeline_work/{model_name}/04_merge/
- ファイル命名規則: {model_name}_merged.fbx

入力: skinned_fbx(Step3出力), original_model(元モデル)
出力: /app/pipeline_work/{model_name}/04_merge/{model_name}_merged.fbx
"""

import os
import logging
import subprocess
import time
from pathlib import Path
from typing import Tuple, Dict
import shutil
import traceback

logger = logging.getLogger(__name__)

class Step4SimpleMerge:
    """
    Step 4: シンプルスケルトン・スキニングマージ
    
    新設計方針:
    - Step0アセット保存データは使用しない
    - スケルトン・スキニングマージに特化
    - 原UniRig互換の最小実装
    """
    
    def __init__(self, model_name: str, output_dir: str):
        """
        Step4初期化
        
        Args:
            model_name: モデル名
            output_dir: 出力ディレクトリ
        """
        self.model_name = model_name
        self.output_dir = Path(output_dir)
        self.logger = logging.getLogger(__name__)
        
        # ディレクトリ作成
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 出力ファイル
        self.merged_fbx = self.output_dir / f"{model_name}_merged.fbx"
        
    def merge_skeleton_skinning(self, skinned_fbx: str, original_model: str) -> Tuple[bool, str, Dict]:
        """
        シンプルスケルトン・スキニングマージ処理
        
        Args:
            skinned_fbx: Step3出力のスキニング済みFBXファイルパス
            original_model: 元モデルファイルパス
            
        Returns:
            success: 処理成功フラグ
            logs: 処理ログメッセージ
            output_files: 出力ファイル辞書
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"=== Step 4: {self.model_name} スケルトン・スキニングマージ開始 ===")
            self.logger.info(f"元モデル: {original_model}")
            self.logger.info(f"スキニング済み: {skinned_fbx}")
            
            # 原UniRigのmerge.transfer()関数を直接呼び出し
            success = self._execute_native_merge(
                source=original_model,    # 元モデル
                target=skinned_fbx,       # スキニング済みモデル
                output=str(self.merged_fbx)
            )
            
            if not success:
                return False, "スケルトン・スキニングマージ処理失敗", {}
            
            # 処理時間計算
            processing_time = time.time() - start_time
            
            # ファイルサイズ取得
            file_size_mb = self.merged_fbx.stat().st_size / (1024 * 1024)
            
            # 出力ファイル辞書
            output_files = {
                "merged_fbx": str(self.merged_fbx)
            }
            
            success_log = f"Step 4 スケルトン・スキニングマージ完了: {self.merged_fbx} ({file_size_mb:.1f}MB, {processing_time:.1f}秒)"
            self.logger.info(success_log)
            
            return True, success_log, output_files
            
        except Exception as e:
            error_msg = f"Step 4 スケルトン・スキニングマージエラー: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            
            return False, error_msg, {}
    
    def _execute_native_merge(self, source: str, target: str, output: str) -> bool:
        """原UniRigのmerge.transfer()関数を直接実行"""
        try:
            self.logger.info("原UniRig merge.transfer() 実行開始")
            
            # src.inference.merge.transfer を直接呼び出し
            import sys
            sys.path.append("/app")
            from src.inference.merge import transfer
            
            # transfer関数実行
            transfer(
                source=source,      # 元モデル
                target=target,      # スキニング済みモデル
                output=output,      # 最終出力パス
                add_root=False      # ルートボーン追加なし
            )
            
            # 出力ファイル確認
            if Path(output).exists():
                file_size = Path(output).stat().st_size
                self.logger.info(f"merge.transfer() 成功: {output} ({file_size} bytes)")
                return True
            else:
                self.logger.error(f"merge.transfer() 出力ファイル未生成: {output}")
                return False
                
        except Exception as e:
            self.logger.error(f"merge.transfer() 実行エラー: {e}")
            self.logger.error(traceback.format_exc())
            return False

# UNIRIG_PIPELINE_DATAFLOW.md準拠のモジュール実行インターフェース
def execute_step4_simple(model_name: str, skinned_fbx: str, original_model: str, 
                         output_dir: str) -> Tuple[bool, str, Dict]:
    """
    Step 4シンプル実行インターフェース
    
    Args:
        model_name: モデル名
        skinned_fbx: Step3出力のスキニング済みFBXパス
        original_model: 元モデルファイルパス
        output_dir: 出力ディレクトリ
    
    Returns:
        success: 処理成功フラグ
        logs: 処理ログ
        output_files: 出力ファイル辞書
    """
    try:
        step4 = Step4SimpleMerge(model_name, output_dir)
        return step4.merge_skeleton_skinning(skinned_fbx, original_model)
    except Exception as e:
        error_msg = f"Step 4シンプル実行失敗: {str(e)}"
        logger.error(error_msg)
        return False, error_msg, {}

if __name__ == "__main__":
    # テスト用実行
    import sys
    if len(sys.argv) >= 5:
        model_name = sys.argv[1]
        skinned_fbx = sys.argv[2]
        original_model = sys.argv[3]
        output_dir = sys.argv[4]
        
        success, logs, output_files = execute_step4_simple(
            model_name, skinned_fbx, original_model, output_dir
        )
        
        print(f"成功: {success}")
        print(f"ログ: {logs}")
        print(f"出力ファイル: {output_files}")
    else:
        print("使用法: python step4_merge_simple.py <model_name> <skinned_fbx> <original_model> <output_dir>")
