"""
Step2 Module - 固定ディレクトリ + 統一命名規則対応
原流処理互換のスケルトン生成
"""

import sys
import subprocess
import shutil
from pathlib import Path
from typing import Tuple, Dict, Any
import logging

sys.path.append('/app')

class Step2Skeleton:
    """固定ディレクトリ + 統一命名規則対応のStep2"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
    
    def generate_skeleton(self, model_name: str, mesh_file: Path, gender: str = "neutral") -> Tuple[bool, str, Dict[str, Any]]:
        """
        固定ディレクトリ + 統一命名規則対応のスケルトン生成
        
        Args:
            model_name: モデル名
            mesh_file: Step1で生成されたraw_data.npz
            gender: 性別 (neutral/male/female)
            
        Returns:
            (success, logs, output_files)
        """
        logs = ""
        
        try:
            # 前提条件確認
            if not mesh_file.exists():
                return False, f"入力メッシュファイル不存在: {mesh_file}\n", {}
            
            # 原流処理互換実行
            success, skeleton_logs = self._execute_original_skeleton(mesh_file, gender)
            logs += skeleton_logs
            
            if not success:
                return False, logs, {}
            
            # 出力ファイル処理
            return self._handle_output_files(model_name, logs)
            
        except Exception as e:
            error_msg = f"Step2実行エラー: {e}"
            return False, error_msg, {}
    
    def _execute_original_skeleton(self, mesh_file: Path, gender: str) -> Tuple[bool, str]:
        """原流処理generate_skeleton.sh互換実行（メッシュ再抽出含む）"""
        logs = ""
        
        # 設定ファイル確認
        task_config = Path("/app/configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml")
        data_config = Path("/app/configs/data/quick_inference.yaml")
        
        if not task_config.exists():
            return False, f"タスク設定ファイル不存在: {task_config}\n"
        if not data_config.exists():
            return False, f"データ設定ファイル不存在: {data_config}\n"
        
        # 🔥 原作シェルスクリプト互換: スケルトン生成用にメッシュ再抽出
        logs += "🔥 原作互換: スケルトン生成用メッシュ再抽出開始\n"
        
        # 1. メッシュ再抽出 (原作のgenerate_skeleton.sh第1段階)
        import time as time_module
        time_str = time_module.strftime("%Y_%m_%d_%H_%M_%S")
        
        extract_cmd = [
            sys.executable, "-m", "src.data.extract",
            "--config", str(data_config),
            "--force_override", "true",
            "--num_runs", "1",
            "--target_count", "50000",
            "--faces_target_count", "50000",
            "--require_suffix", "obj,fbx,FBX,dae,glb,gltf,vrm",
            "--time", time_str,
            "--id", "0",
            "--output_dir", str(self.output_dir)
        ]
        
        # 元のメッシュファイルからinput情報を推定
        if mesh_file.parent.name.endswith("_extracted_mesh"):
            # /app/pipeline_work/{model_name}/01_extracted_mesh/raw_data.npz
            # → 元のinput_dirは /app/pipeline_work/{model_name}/00_preserved_assets/
            model_name = mesh_file.parent.parent.name
            input_dir = mesh_file.parent.parent / "00_asset_preservation"
            if input_dir.exists():
                extract_cmd.extend(["--input_dir", str(input_dir)])
                logs += f"入力ディレクトリ推定: {input_dir}\n"
            else:
                # フォールバック: 元のアップロードファイルを探す
                potential_input = mesh_file.parent.parent / "uploaded_model"
                if potential_input.exists():
                    # uploaded_modelディレクトリ内のファイルを探す
                    input_files = list(potential_input.glob("*"))
                    if input_files:
                        extract_cmd.extend(["--input", str(input_files[0])])
                        logs += f"入力ファイル推定: {input_files[0]}\n"
                else:
                    logs += f"⚠️ 入力ファイル/ディレクトリが見つかりません\n"
        
        logs += f"メッシュ再抽出コマンド: {' '.join(extract_cmd)}\n"
        
        try:
            extract_result = subprocess.run(
                extract_cmd,
                cwd="/app",
                capture_output=True,
                text=True,
                timeout=600,  # 10分
                check=True
            )
            
            logs += "✅ メッシュ再抽出成功\n"
            if extract_result.stdout:
                logs += f"再抽出stdout: {extract_result.stdout}\n"
                
        except subprocess.CalledProcessError as e:
            logs += f"❌ メッシュ再抽出失敗: {e}\n"
            if e.stderr:
                logs += f"再抽出stderr: {e.stderr}\n"
            return False, logs
        except subprocess.TimeoutExpired:
            logs += "❌ メッシュ再抽出タイムアウト (10分)\n"
            return False, logs
        
        # 2. スケルトン生成 (原作のgenerate_skeleton.sh第2段階)
        logs += "🔥 原作互換: スケルトン生成開始\n"
        
        skeleton_cmd = [
            sys.executable, "run.py",
            "--task", str(task_config),
            "--npz_dir", str(self.output_dir),
            "--output_dir", str(self.output_dir)
        ]
        
        logs += f"スケルトン生成コマンド: {' '.join(skeleton_cmd)}\n"
        
        try:
            skeleton_result = subprocess.run(
                skeleton_cmd,
                cwd="/app",
                capture_output=True,
                text=True,
                timeout=1200,  # 20分
                check=True
            )
            
            logs += "✅ スケルトン生成成功\n"
            if skeleton_result.stdout:
                logs += f"スケルトン生成stdout: {skeleton_result.stdout}\n"
            
            return True, logs
            
        except subprocess.CalledProcessError as e:
            logs += f"❌ スケルトン生成失敗: {e}\n"
            if e.stderr:
                logs += f"スケルトン生成stderr: {e.stderr}\n"
            return False, logs
        except subprocess.TimeoutExpired:
            logs += "❌ スケルトン生成タイムアウト (20分)\n"
            return False, logs
    
    def _handle_output_files(self, model_name: str, logs: str) -> Tuple[bool, str, Dict[str, Any]]:
        """出力ファイル処理と統一命名規則対応（決め打ちディレクトリ戦略）"""
        
        # run.pyは--output_dirを無視して--npz_dirに出力するため、ファイルを検索・移動
        input_dir = Path(f"/app/pipeline_work/{model_name}/01_extracted_mesh")  # 実際の出力場所
        
        # 実際の出力ファイルを検索
        actual_predict_skeleton = input_dir / "predict_skeleton.npz"
        actual_skeleton_fbx = input_dir / "skeleton.fbx"
        
        if not actual_predict_skeleton.exists():
            return False, logs + f"❌ 実際の出力不存在: {actual_predict_skeleton}\n", {}
        
        if not actual_skeleton_fbx.exists():
            return False, logs + f"❌ 実際の出力不存在: {actual_skeleton_fbx}\n", {}
        
        logs += f"✅ 実際の出力ファイル発見:\n"
        logs += f"  - NPZ: {actual_predict_skeleton}\n"
        logs += f"  - FBX: {actual_skeleton_fbx}\n"
        
        # 決め打ちディレクトリの期待場所に移動
        target_predict_skeleton = self.output_dir / "predict_skeleton.npz"
        target_skeleton_fbx = self.output_dir / "skeleton.fbx"
        
        # ファイル移動
        shutil.move(str(actual_predict_skeleton), str(target_predict_skeleton))
        shutil.move(str(actual_skeleton_fbx), str(target_skeleton_fbx))
        
        logs += f"✅ 決め打ちディレクトリに移動完了:\n"
        logs += f"  - NPZ: {target_predict_skeleton}\n"
        logs += f"  - FBX: {target_skeleton_fbx}\n"
        
        # 統一命名規則ファイル作成
        unified_skeleton_npz = self.output_dir / f"{model_name}_skeleton.npz"
        unified_skeleton_fbx = self.output_dir / f"{model_name}_skeleton.fbx"
        
        # NPZファイルコピー
        if not unified_skeleton_npz.exists():
            shutil.copy2(target_predict_skeleton, unified_skeleton_npz)
            logs += f"✅ 統一命名NPZ作成: {unified_skeleton_npz}\n"
        
        # FBXファイルコピー（原流処理互換のため、{model_name}.fbxも作成）
        original_compat_fbx = self.output_dir / f"{model_name}.fbx"
        if not original_compat_fbx.exists():
            shutil.copy2(target_skeleton_fbx, original_compat_fbx)
            logs += f"✅ 原流処理互換FBX作成: {original_compat_fbx}\n"
        
        if not unified_skeleton_fbx.exists():
            shutil.copy2(target_skeleton_fbx, unified_skeleton_fbx)
            logs += f"✅ 統一命名FBX作成: {unified_skeleton_fbx}\n"
        
        # 不要なファイルをクリーンアップ
        cleanup_files = [
            input_dir / "skeleton.obj",
            input_dir / "skeleton_pred.txt"
        ]
        
        for cleanup_file in cleanup_files:
            if cleanup_file.exists():
                try:
                    cleanup_file.unlink()
                    logs += f"✅ クリーンアップ: {cleanup_file}\n"
                except Exception as e:
                    logs += f"⚠️ クリーンアップ失敗 (無視): {cleanup_file} - {e}\n"
        
        # ファイルサイズ確認
        npz_size = target_predict_skeleton.stat().st_size
        fbx_size = target_skeleton_fbx.stat().st_size
        
        logs += f"✅ Step2完了（決め打ちディレクトリ戦略）\n"
        logs += f"原流処理NPZ: {target_predict_skeleton} ({npz_size:,} bytes)\n"
        logs += f"原流処理FBX: {target_skeleton_fbx} ({fbx_size:,} bytes)\n"
        logs += f"統一命名NPZ: {unified_skeleton_npz}\n"
        logs += f"統一命名FBX: {unified_skeleton_fbx}\n"
        
        return True, logs, {
            "skeleton_npz": str(target_predict_skeleton),      # 原流処理互換
            "skeleton_fbx": str(original_compat_fbx),          # 原流処理互換 ({model_name}.fbx)
            "unified_skeleton_npz": str(unified_skeleton_npz), # 統一命名規則
            "unified_skeleton_fbx": str(unified_skeleton_fbx)  # 統一命名規則
        }

# 外部インターフェース
def generate_skeleton_step2(model_name: str, mesh_file_path: str, output_dir: str, gender: str = "neutral") -> Tuple[bool, str, Dict[str, Any]]:
    """Step2外部インターフェース - 統一命名規則対応"""
    try:
        step2 = Step2Skeleton(Path(output_dir))
        return step2.generate_skeleton(model_name, Path(mesh_file_path), gender)
    except Exception as e:
        return False, f"Step2外部インターフェースエラー: {e}", {}
