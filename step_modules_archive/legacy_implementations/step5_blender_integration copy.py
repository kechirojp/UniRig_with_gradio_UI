"""
Step5 Module - 固定ディレクトリ + 統一命名規則対応
Blender統合・最終出力処理
"""

import sys
import shutil
from pathlib import Path
from typing import Tuple, Dict, Any
import logging

sys.path.append('/app')

class Step5BlenderIntegration:
    """固定ディレクトリ + 統一命名規則対応のStep5"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
    
    def integrate_final_output(self, model_name: str, original_file: Path, merged_file: Path) -> Tuple[bool, str, Dict[str, Any]]:
        """
        固定ディレクトリ + 統一命名規則対応の最終出力統合
        
        Args:
            model_name: モデル名
            original_file: オリジナル3Dモデルファイル
            merged_file: Step4のマージ済みFBX
            
        Returns:
            (success, logs, output_files)
        """
        logs = ""
        
        try:
            # 入力ファイル確認
            if not original_file.exists():
                return False, f"オリジナルファイル不存在: {original_file}\n", {}
            
            if not merged_file.exists():
                return False, f"マージ済みファイル不存在: {merged_file}\n", {}
            
            # 現在は単純コピーで最終出力を作成
            # 将来的にはBlenderスクリプトでUV/マテリアル統合を実装
            success, integration_logs = self._create_final_output(model_name, merged_file)
            logs += integration_logs
            
            if not success:
                return False, logs, {}
            
            # 出力ファイル処理
            return self._handle_output_files(model_name, logs)
            
        except Exception as e:
            error_msg = f"Step5実行エラー: {e}"
            return False, error_msg, {}
    
    def _create_final_output(self, model_name: str, merged_file: Path) -> Tuple[bool, str]:
        """最終出力ファイル作成"""
        logs = ""
        
        try:
            # 統一命名規則最終出力ファイル
            final_fbx = self.output_dir / f"{model_name}_rigged.fbx"
            
            # 現在は単純コピー
            # TODO: Blenderスクリプトでオリジナルアセット情報統合
            if not final_fbx.exists():
                shutil.copy2(merged_file, final_fbx)
                logs += f"最終FBXファイル作成: {final_fbx}\n"
            
            # テクスチャフォルダも作成（将来的な拡張用）
            texture_dir = self.output_dir / f"{model_name}_final.fbm"
            texture_dir.mkdir(exist_ok=True)
            logs += f"テクスチャディレクトリ作成: {texture_dir}\n"
            
            return True, logs
            
        except Exception as e:
            return False, f"最終出力作成エラー: {e}\n"
    
    def _handle_output_files(self, model_name: str, logs: str) -> Tuple[bool, str, Dict[str, Any]]:
        """出力ファイル処理と統一命名規則対応"""
        
        # 統一命名規則最終出力ファイル確認
        final_fbx = self.output_dir / f"{model_name}_rigged.fbx"
        texture_dir = self.output_dir / f"{model_name}_final.fbm"
        
        if not final_fbx.exists():
            return False, logs + f"最終出力ファイル不存在: {final_fbx}\n", {}
        
        # ファイルサイズ確認
        fbx_size = final_fbx.stat().st_size
        
        logs += f"[OK] Step5完了\n"
        logs += f"最終リギング済みFBX: {final_fbx} ({fbx_size:,} bytes)\n"
        logs += f"テクスチャディレクトリ: {texture_dir}\n"
        
        return True, logs, {
            "final_fbx": str(final_fbx),      # ユーザー向け最終成果物
            "texture_dir": str(texture_dir)   # テクスチャディレクトリ
        }

# 外部インターフェース
def integrate_final_output_step5(model_name: str, original_file_path: str, merged_file_path: str, output_dir: str) -> Tuple[bool, str, Dict[str, Any]]:
    """Step5外部インターフェース - 統一命名規則対応"""
    try:
        step5 = Step5BlenderIntegration(Path(output_dir))
        return step5.integrate_final_output(model_name, Path(original_file_path), Path(merged_file_path))
    except Exception as e:
        return False, f"Step5外部インターフェースエラー: {e}", {}
