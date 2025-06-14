"""
統一パイプラインオーケストレーター
固定ディレクトリ + 統一命名規則完全対応
"""

import sys
import logging
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

# 統一Step Moduleインポート
sys.path.append('/app')
from step_modules.step1_extract import extract_mesh_step1
from step_modules.step2_skeleton import execute_step2
from step_modules.step3_skinning_unirig import apply_skinning_step3
from step_modules.step4_merge import merge_skeleton_skinning_step4
from step_modules.step5_blender_integration import integrate_final_output_step5

class UnifiedPipelineOrchestrator:
    """統一パイプラインオーケストレーター - 固定ディレクトリ + 統一命名規則"""
    
    def __init__(self, base_dir: Path = Path("/app/pipeline_work")):
        self.base_dir = base_dir
        self.logger = logging.getLogger(__name__)
    
    def process_complete_pipeline(self, input_file: Path, model_name: str, gender: str = "neutral") -> Tuple[bool, str, Dict[str, Any]]:
        """
        完全パイプライン実行 - 固定ディレクトリ + 統一命名規則
        
        Args:
            input_file: 入力3Dモデルファイル
            model_name: モデル名
            gender: 性別指定
            
        Returns:
            (success, logs, final_output_files)
        """
        logs = ""
        
        try:
            # 固定ディレクトリ構造作成
            model_dir = self.base_dir / model_name
            step_dirs = {
                "step1": model_dir / "01_extracted_mesh",
                "step2": model_dir / "02_skeleton", 
                "step3": model_dir / "03_skinning",
                "step4": model_dir / "04_merge",
                "step5": model_dir / "05_blender_integration"
            }
            
            # ディレクトリ作成
            for step_dir in step_dirs.values():
                step_dir.mkdir(parents=True, exist_ok=True)
            
            logs += f"固定ディレクトリ構造作成: {model_dir}\n"
            
            # Step1: メッシュ抽出
            success, step1_logs, step1_files = extract_mesh_step1(
                str(input_file), model_name, str(step_dirs["step1"])
            )
            logs += f"--- Step1 ---\n{step1_logs}\n"
            
            if not success:
                return False, logs, {}
            
            # Step2: スケルトン生成
            # 新しいStep2実装：オリジナルファイルから独自メッシュ再抽出実行
            success, step2_logs, step2_files = execute_step2(
                input_file, model_name, step_dirs["step2"], self.logger, gender
            )
            logs += f"--- Step2 ---\n{step2_logs}\n"
            
            if not success:
                return False, logs, {}
            
            # Step3: スキニング適用
            # Step1のメッシュファイルを使用
            mesh_file = step1_files.get("extracted_npz")
            if not mesh_file:
                return False, logs + "Step1メッシュファイル不明\n", {}
            
            success, step3_logs, step3_files = apply_skinning_step3(
                model_name, mesh_file, step2_files, str(step_dirs["step3"])
            )
            logs += f"--- Step3 ---\n{step3_logs}\n"
            
            if not success:
                return False, logs, {}
            
            # Step4: マージ処理
            success, step4_logs, step4_files = merge_skeleton_skinning_step4(
                model_name, step2_files, step3_files, str(step_dirs["step4"])
            )
            logs += f"--- Step4 ---\n{step4_logs}\n"
            
            if not success:
                return False, logs, {}
            
            # Step5: 最終統合
            merged_file = step4_files.get("merged_fbx")
            if not merged_file:
                return False, logs + "Step4出力ファイル不明\n", {}
            
            success, step5_logs, step5_files = integrate_final_output_step5(
                model_name, str(input_file), merged_file, str(step_dirs["step5"])
            )
            logs += f"--- Step5 ---\n{step5_logs}\n"
            
            if not success:
                return False, logs, {}
            
            # 最終結果確認
            final_fbx = step5_files.get("final_fbx")
            if not final_fbx or not Path(final_fbx).exists():
                return False, logs + "最終出力ファイル不存在\n", {}
            
            logs += f"🎉 統一パイプライン完了\n"
            logs += f"最終成果物: {final_fbx}\n"
            
            return True, logs, {
                "final_fbx": final_fbx,
                "model_name": model_name,
                "pipeline_dir": str(model_dir),
                "all_steps": {
                    "step1": step1_files,
                    "step2": step2_files,
                    "step3": step3_files,
                    "step4": step4_files,
                    "step5": step5_files
                }
            }
            
        except Exception as e:
            error_msg = f"統一パイプラインエラー: {e}"
            self.logger.error(error_msg, exc_info=True)
            return False, logs + error_msg, {}
    
    def get_pipeline_status(self, model_name: str) -> Dict[str, bool]:
        """パイプライン実行状況確認"""
        model_dir = self.base_dir / model_name
        
        status = {
            "step1_complete": (model_dir / "01_extracted_mesh" / "raw_data.npz").exists(),
            "step2_complete": (model_dir / "02_skeleton" / "predict_skeleton.npz").exists(),
            "step3_complete": len(list((model_dir / "03_skinning").glob("*.fbx"))) > 0,
            "step4_complete": (model_dir / "04_merge" / f"{model_name}_merged.fbx").exists(),
            "step5_complete": (model_dir / "05_blender_integration" / f"{model_name}_rigged.fbx").exists()
        }
        
        return status
    
    def get_final_output_path(self, model_name: str) -> Optional[Path]:
        """最終成果物パス取得"""
        final_fbx = self.base_dir / model_name / "05_blender_integration" / f"{model_name}_rigged.fbx"
        return final_fbx if final_fbx.exists() else None

# 外部インターフェース
def process_unified_pipeline(input_file_path: str, model_name: str, gender: str = "neutral") -> Tuple[bool, str, Dict[str, Any]]:
    """統一パイプライン外部インターフェース"""
    try:
        orchestrator = UnifiedPipelineOrchestrator()
        return orchestrator.process_complete_pipeline(Path(input_file_path), model_name, gender)
    except Exception as e:
        return False, f"統一パイプライン外部インターフェースエラー: {e}", {}
