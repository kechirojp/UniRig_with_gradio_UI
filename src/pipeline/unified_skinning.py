"""
🎯 UniRig統一スキニング生成器 - Shell Script完全置き換え版
クロスプラットフォーム完全対応、統一命名規則準拠

元のgenerate_skin.shの全機能をPythonで再実装
- Windows/Mac/Linux完全対応
- 統一命名規則準拠
- dataset_inference_clean作業ディレクトリ管理
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

class UnifiedSkinningGenerator:
    """🎯 統一スキニング生成器 (Shell Script置き換え)"""
    
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
    
    def generate_skinning(self,
                         mesh_npz: str,
                         skeleton_npz: str,
                         skeleton_fbx: str,
                         output_dir: str,
                         model_name: str,
                         cfg_data: str = "configs/data/quick_inference.yaml",
                         cfg_task: str = "configs/task/quick_inference_unirig_skin.yaml",
                         force_override: bool = False,
                         faces_target_count: int = 50000
                         ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        🎯 統一スキニング生成実行 (generate_skin.sh完全置き換え)
        
        Args:
            mesh_npz: 入力メッシュNPZファイル
            skeleton_npz: 入力スケルトンNPZファイル
            skeleton_fbx: 入力スケルトンFBXファイル
            output_dir: 出力ディレクトリ
            model_name: モデル名 (統一命名規則用)
            cfg_data: データ設定ファイル
            cfg_task: タスク設定ファイル
            force_override: 強制上書き
            faces_target_count: ターゲット面数
            
        Returns:
            (success, logs, output_files) - 統一命名規則準拠
        """
        
        start_time = time.time()
        logs = f"🎯 統一スキニング生成開始: {model_name}\n"
        
        try:
            # 入力ファイル存在確認
            for file_path, name in [(mesh_npz, "メッシュNPZ"), (skeleton_npz, "スケルトンNPZ"), (skeleton_fbx, "スケルトンFBX")]:
                if not Path(file_path).exists():
                    error_msg = f"❌ {name}ファイルが見つかりません: {file_path}"
                    self.logger.error(error_msg)
                    return False, logs + error_msg, {}
            
            # 出力ディレクトリ作成
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # 🎯 Phase 1: 原流処理互換作業ディレクトリ準備
            logs += "📋 Phase 1: 作業ディレクトリ準備...\n"
            dataset_work_dir = self._prepare_dataset_work_directory(
                mesh_npz, skeleton_npz, skeleton_fbx, model_name
            )
            logs += f"作業ディレクトリ: {dataset_work_dir}\n"
            
            # 🎯 Phase 2: 前処理 (extract相当)
            logs += "📋 Phase 2: 前処理実行...\n"
            extract_success, extract_logs = self._run_extract_phase(
                cfg_data, dataset_work_dir, force_override, faces_target_count
            )
            logs += extract_logs
            
            if not extract_success:
                return False, logs + "❌ 前処理段階で失敗", {}
            
            # 🎯 Phase 3: AI推論 (run.py相当)
            logs += "🧠 Phase 3: AI推論実行...\n"
            inference_success, inference_logs = self._run_inference_phase(
                cfg_task, dataset_work_dir, model_name
            )
            logs += inference_logs
            
            if not inference_success:
                return False, logs + "❌ AI推論段階で失敗", {}
            
            # 🎯 Phase 4: 結果回収と統一命名規則適用
            logs += "📁 Phase 4: 結果回収と統一命名...\n"
            execution_time = time.time() - start_time
            output_files = self._collect_and_apply_unified_naming(
                dataset_work_dir, output_dir, model_name, execution_time
            )
            
            logs += f"✅ 統一スキニング生成完了 ({execution_time:.2f}秒)\n"
            self.logger.info(f"✅ スキニング生成完了: {model_name}")
            
            return True, logs, output_files
            
        except Exception as e:
            error_msg = f"❌ スキニング生成中に予期せぬエラー: {type(e).__name__} - {e}"
            logs += error_msg + "\n"
            self.logger.error(error_msg, exc_info=True)
            return False, logs, {}
    
    def _prepare_dataset_work_directory(self, mesh_npz: str, skeleton_npz: str, 
                                      skeleton_fbx: str, model_name: str) -> Path:
        """原流処理互換作業ディレクトリ準備"""
        dataset_work_dir = Path("/app/dataset_inference_clean") / model_name
        dataset_work_dir.mkdir(parents=True, exist_ok=True)
        
        # 固定名でファイル配置 (原流処理互換)
        target_files = {
            "raw_data.npz": mesh_npz,
            "predict_skeleton.npz": skeleton_npz,
            f"{model_name}.fbx": skeleton_fbx
        }
        
        for target_name, source_path in target_files.items():
            target_path = dataset_work_dir / target_name
            shutil.copy2(source_path, target_path)
            self.logger.info(f"📁 ファイル配置: {source_path} → {target_path}")
        
        # inference_datalist.txt生成 (原流処理必須)
        datalist_file = dataset_work_dir / "inference_datalist.txt"
        with open(datalist_file, 'w') as f:
            f.write(f"{model_name}\n")
        
        return dataset_work_dir
    
    def _run_extract_phase(self, cfg_data: str, dataset_work_dir: Path, 
                          force_override: bool, faces_target_count: int) -> Tuple[bool, str]:
        """Phase 2: 前処理実行"""
        # 🎯 統一Extract使用 (Shell Script不要)
        from .unified_extract import create_unified_extractor
        
        extractor = create_unified_extractor(self.logger)
        
        # dataset_work_dir内のraw_data.npzを処理対象とする
        input_npz = dataset_work_dir / "raw_data.npz"
        
        success, logs, _ = extractor.extract_mesh(
            input_file=str(input_npz),
            output_dir=str(dataset_work_dir),
            model_name=dataset_work_dir.name,  # model_name
            cfg_data=cfg_data,
            force_override=force_override,
            faces_target_count=faces_target_count
        )
        
        return success, logs
    
    def _run_inference_phase(self, cfg_task: str, dataset_work_dir: Path, 
                           model_name: str) -> Tuple[bool, str]:
        """Phase 3: AI推論実行"""
        cmd_args = [
            self.python_exec,
            "run.py",
            f"--task={cfg_task}",
            "--seed=12345",
            f"--output_dir={dataset_work_dir}",
            f"--npz_dir={dataset_work_dir}",  # 原流処理互換
            f"--model_name={model_name}"  # 統一命名規則対応
        ]
        
        try:
            result = subprocess.run(cmd_args, capture_output=True, text=True, 
                                  timeout=900, cwd="/app")  # 15分タイムアウト
            
            if result.returncode == 0:
                return True, f"✅ AI推論成功\n{result.stdout}\n"
            else:
                return False, f"❌ AI推論失敗: {result.stderr}\n"
                
        except subprocess.TimeoutExpired:
            return False, "❌ AI推論タイムアウト (900秒)\n"
        except Exception as e:
            return False, f"❌ AI推論エラー: {e}\n"
    
    def _collect_and_apply_unified_naming(self, dataset_work_dir: Path, output_dir: str, 
                                        model_name: str, execution_time: float) -> Dict[str, Any]:
        """Phase 4: 結果回収と統一命名規則適用"""
        output_path = Path(output_dir)
        
        # 🎯 統一ファイル名定義
        unified_skinned_fbx = output_path / f"{model_name}_skinned.fbx"
        unified_skinning_npz = output_path / f"{model_name}_skinning.npz"
        
        # 原流処理出力から統一名への収集
        original_files = {
            "predict_skin.npz": unified_skinning_npz,
            "skinned_model.fbx": unified_skinned_fbx,
            "result_fbx.fbx": unified_skinned_fbx,
            f"{model_name}_skinned_unirig.fbx": unified_skinned_fbx,
            f"{model_name}_skinning.npz": unified_skinning_npz
        }
        
        for original_name, unified_path in original_files.items():
            original_path = dataset_work_dir / original_name
            if original_path.exists() and not unified_path.exists():
                shutil.copy2(original_path, unified_path)
                self.logger.info(f"📁 統一ファイル回収: {original_name} → {unified_path.name}")
        
        # 出力ファイル情報構築
        output_files = {
            "skinned_fbx": str(unified_skinned_fbx) if unified_skinned_fbx.exists() else None,
            "skinning_npz": str(unified_skinning_npz) if unified_skinning_npz.exists() else None,
            "file_size_fbx": unified_skinned_fbx.stat().st_size if unified_skinned_fbx.exists() else 0,
            "file_size_npz": unified_skinning_npz.stat().st_size if unified_skinning_npz.exists() else 0,
            "execution_time_seconds": round(execution_time, 2),
            "work_directory": str(dataset_work_dir)
        }
        
        return output_files

    def apply_skinning_unified(self, model_name: str, mesh_file: str, skeleton_file: str, output_dir: str) -> Tuple[bool, str]:
        """統一スキニング適用メソッド（app.py統合用）"""
        try:
            self.logger.info(f"統合スキニング適用開始: {model_name}")
            
            # 入力ファイル検証
            mesh_path = Path(mesh_file)
            skeleton_path = Path(skeleton_file)
            
            if not mesh_path.exists():
                return False, f"メッシュファイルが存在しません: {mesh_file}"
            if not skeleton_path.exists():
                return False, f"スケルトンファイルが存在しません: {skeleton_file}"
            
            # スケルトンNPZファイル検索 (決め打ちディレクトリ戦略準拠)
            skeleton_dir = skeleton_path.parent
            skeleton_npz = skeleton_dir / "predict_skeleton.npz"
            
            if not skeleton_npz.exists():
                # フォールバック検索
                skeleton_npz = skeleton_dir / f"{model_name}_skeleton.npz"
                if not skeleton_npz.exists():
                    return False, f"スケルトンNPZファイルが見つかりません: {skeleton_dir}"
            
            # 出力ディレクトリ作成
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # デフォルト設定で原流処理相当実行
            success, logs, output_files = self.generate_skinning(
                mesh_npz=mesh_file,
                skeleton_npz=str(skeleton_npz),
                skeleton_fbx=skeleton_file,
                output_dir=output_dir,
                model_name=model_name,
                cfg_data="configs/data/quick_inference.yaml",
                cfg_task="configs/task/quick_inference_unirig_skin.yaml",
                force_override=True,
                faces_target_count=50000
            )
            
            if success:
                # 期待出力確認 (決め打ちディレクトリ戦略準拠)
                expected_fbx = output_path / f"{model_name}_skinned_unirig.fbx"
                expected_npz = output_path / f"{model_name}_skinning.npz"
                
                output_check = []
                if expected_fbx.exists():
                    file_size = expected_fbx.stat().st_size / (1024 * 1024)
                    output_check.append(f"✅ スキニングFBX: {expected_fbx} ({file_size:.2f} MB)")
                else:
                    output_check.append(f"⚠️ スキニングFBX未作成: {expected_fbx}")
                
                if expected_npz.exists():
                    file_size = expected_npz.stat().st_size / (1024 * 1024)
                    output_check.append(f"✅ スキニングNPZ: {expected_npz} ({file_size:.2f} MB)")
                else:
                    output_check.append(f"⚠️ スキニングNPZ未作成: {expected_npz}")
                
                logs += "\n期待出力確認:\n" + "\n".join(output_check)
            
            return success, logs
            
        except Exception as e:
            self.logger.error(f"統合スキニング適用エラー: {e}", exc_info=True)
            return False, f"統合スキニング適用エラー: {str(e)}"

# オーケストレーター統合エイリアス
class UnifiedSkinningOrchestrator(UnifiedSkinningGenerator):
    """app.py統合用エイリアス"""
    pass

# 🎯 クロスプラットフォーム対応ファクトリー
def create_unified_skinning_generator(logger: Optional[logging.Logger] = None) -> UnifiedSkinningGenerator:
    """統一スキニング生成器ファクトリー (プラットフォーム自動対応)"""
    return UnifiedSkinningGenerator(logger=logger)

# 🎯 CLI実行対応 (generate_skin.sh置き換え)
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="UniRig統一スキニング生成 (generate_skin.sh置き換え)")
    parser.add_argument("--mesh_npz", required=True, help="入力メッシュNPZファイル")
    parser.add_argument("--skeleton_npz", required=True, help="入力スケルトンNPZファイル")
    parser.add_argument("--skeleton_fbx", required=True, help="入力スケルトンFBXファイル")
    parser.add_argument("--output_dir", required=True, help="出力ディレクトリ")
    parser.add_argument("--model_name", required=True, help="モデル名 (統一命名規則)")
    parser.add_argument("--cfg_data", default="configs/data/quick_inference.yaml", help="データ設定ファイル")
    parser.add_argument("--cfg_task", default="configs/task/quick_inference_unirig_skin.yaml", help="タスク設定ファイル")
    parser.add_argument("--force_override", action="store_true", help="強制上書き")
    parser.add_argument("--faces_target_count", type=int, default=50000, help="ターゲット面数")
    
    args = parser.parse_args()
    
    # ログ設定
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 統一スキニング生成実行
    generator = create_unified_skinning_generator()
    success, logs, output_files = generator.generate_skinning(
        mesh_npz=args.mesh_npz,
        skeleton_npz=args.skeleton_npz,
        skeleton_fbx=args.skeleton_fbx,
        output_dir=args.output_dir,
        model_name=args.model_name,
        cfg_data=args.cfg_data,
        cfg_task=args.cfg_task,
        force_override=args.force_override,
        faces_target_count=args.faces_target_count
    )
    
    print(logs)
    print(f"実行結果: {'成功' if success else '失敗'}")
    if output_files:
        print(f"出力ファイル: {output_files}")
    
    sys.exit(0 if success else 1)
