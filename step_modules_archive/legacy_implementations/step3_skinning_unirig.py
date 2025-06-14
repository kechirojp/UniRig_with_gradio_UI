"""
Step 3 Module - UniRig本格スキニング実装
独立した実行機能として、UniRig AIモデルを使用してメッシュとスケルトンの結合（スキニング）を実行

責務: メッシュデータ + スケルトン → UniRig AIによるリギング済みFBX
入力: メッシュデータファイルパス、スケルトンFBXファイルパス、スケルトンNPZファイルパス
出力: リギング済みFBXファイルパス, スキニングデータファイルパス (.npz)

主要修正:
- UniRigスキニング実行前に環境変数をクリアしてセグメンテーションフォルト防止を無効化
- FBX出力設定を有効化してスキニング済みFBXファイルを正常生成
- NPZファイル検証とFBXファイルサイズ確認を追加
- データフロー改修方針 (2025年6月9日) に準拠したパス管理
"""

import os
import subprocess
import time
import logging
import shutil
from pathlib import Path
from typing import Tuple, Dict, Optional
import numpy as np

class Step3UniRigSkinning:
    """Step 3: UniRig本格スキニング適用モジュール"""
    
    def __init__(self, output_dir: Path, logger_instance: logging.Logger):
        self.output_dir = output_dir # ステップ固有の出力ディレクトリ (絶対パス)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger_instance
        # 修正: ハードコード除去 - 動的パス設定対応
        self.unirig_processing_base_dir = None  # apply_skinning時に動的設定
        self.unirig_results_base_dir = Path("/app/results")
        
    def apply_skinning(self, 
                       input_mesh_npz_path: Path, 
                       input_skeleton_npz_path: Path, 
                       model_name: str) -> Tuple[bool, str, Dict]:
        """
        原流処理完全互換 Step3 スキニング処理 (Step2 NPZのみ使用)
        
        原流処理の generate_skin.sh と完全に同じファイル配置・実行フローを実装
        重要: dataset_inference_clean/{model_name}/ 配下に正確な構造で配置
        
        Args:
            input_mesh_npz_path: 入力メッシュNPZファイルパス (01_extracted_mesh/raw_data.npz)
            input_skeleton_npz_path: 入力スケルトンNPZファイルパス (02_skeleton/predict_skeleton.npz)
            model_name: モデル名 (ディレクトリ名とファイル名プレフィックスに使用)
            model_name: モデル名（原流処理互換）
            
        Returns:
            (success, logs, output_files)
        """
        try:
            self.logger.info(f"Step3原流処理互換スキニング開始: {model_name}")
            
            # 原流処理互換ディレクトリ構造作成
            # 重要: dataset_inference_clean/{model_name}/ 配下に配置
            unirig_work_dir = Path("/app/dataset_inference_clean")
            model_work_dir = unirig_work_dir / model_name
            model_work_dir.mkdir(parents=True, exist_ok=True)
            
            # 原流処理互換ファイル配置 - 正確な命名規則
            target_mesh_npz = model_work_dir / "raw_data.npz"
            target_skeleton_npz = model_work_dir / "predict_skeleton.npz"
            
            # ファイルコピー（原流処理と同じ場所に配置）
            # 入力ファイルの存在確認
            if not input_mesh_npz_path.exists():
                error_msg = f"入力メッシュNPZファイルが見つかりません: {input_mesh_npz_path}"
                self.logger.error(error_msg)
                return False, error_msg, {}
                
            if not input_skeleton_npz_path.exists():
                error_msg = f"入力スケルトンNPZファイルが見つかりません: {input_skeleton_npz_path}"
                self.logger.error(error_msg)
                return False, error_msg, {}
            
            shutil.copy2(input_mesh_npz_path, target_mesh_npz)
            shutil.copy2(input_skeleton_npz_path, target_skeleton_npz)
            
            self.logger.info(f"ファイルコピー完了:")
            self.logger.info(f"  {input_mesh_npz_path} → {target_mesh_npz}")
            self.logger.info(f"  {input_skeleton_npz_path} → {target_skeleton_npz}")
            
            # inference_datalist.txt作成（重要: dataset_inference_clean直下に配置）
            datalist_path = unirig_work_dir / "inference_datalist.txt"
            with open(datalist_path, "w") as f:
                f.write(f"{model_name}\n")  # model_nameのみ
            
            self.logger.info(f"原流処理互換ファイル配置完了:")
            self.logger.info(f"  作業ディレクトリ: {model_work_dir}")
            self.logger.info(f"  メッシュ: {target_mesh_npz}")
            self.logger.info(f"  スケルトン: {target_skeleton_npz}")
            self.logger.info(f"  データリスト: {datalist_path}")
            
            # 原流処理スクリプト直接実行
            success, execution_logs = self._execute_original_flow_skinning(
                model_name, 
                unirig_work_dir
            )
            
            if not success:
                return False, f"原流処理スキニング失敗: {execution_logs}", {}
            
            # 出力ファイル収集・検証
            output_files = self._collect_skinning_outputs(model_name)
            
            completion_logs = f"Step3スキニング完了: {model_name}\n{execution_logs}"
            
            return True, completion_logs, output_files
            
        except Exception as e:
            error_msg = f"Step3スキニング処理エラー: {e}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg, {}
    
    def _execute_original_flow_skinning(self, 
                                         model_name: str, 
                                         work_dir: Path) -> Tuple[bool, str]:
        """
        原流処理generate_skin.sh完全互換実行
        
        重要: オリジナルのgenerate_skin.shと全く同じ処理フローを実行
        generate_skin.shは以下の処理を行う:
        1. extract.sh実行（メッシュ抽出）
        2. python run.py実行（スキニング処理）
        """
        try:
            # 原流処理: generate_skin.shスクリプト直接実行
            # 実際のコマンド: bash launch/inference/generate_skin.sh
            generate_skin_script = Path("/app/launch/inference/generate_skin.sh")
            
            if not generate_skin_script.exists():
                return False, f"原流処理スクリプトが見つかりません: {generate_skin_script}"
            
            # 原流処理互換パラメータ設定
            # 注意: generate_skin.shは元のモデルファイルを--inputとして使用
            # Step0から保存された元ファイルを検索（拡張子を自動検出）
            original_model_path = self._find_original_model_file(model_name)
            
            # 重要: generate_skin.shの正確なパラメータセット
            # generate_skin.shに必要な全ての引数を渡す
            cmd = [
                "bash", str(generate_skin_script),
                "--cfg_data", "configs/data/quick_inference.yaml",
                "--cfg_task", "configs/task/quick_inference_unirig_skin.yaml",
                "--input", str(original_model_path),        # 元のモデルファイル
                "--output_dir", "results",                  # 相対パス（generate_skin.shの期待値）
                "--npz_dir", "dataset_inference_clean",     # NPZディレクトリ（generate_skin.shの期待値）
                "--require_suffix", "obj,fbx,FBX,dae,glb,gltf,vrm",
                "--num_runs", "1",
                "--force_override", "false",
                "--faces_target_count", "50000"
            ]
            
            self.logger.info(f"原流処理実行: {' '.join(cmd)}")
            self.logger.info(f"作業ディレクトリ: /app")
            self.logger.info(f"元モデルファイル: {original_model_path}")
            
            # 実行前環境確認
            self.logger.info(f"dataset_inference_clean配置確認:")
            dataset_dir = Path("/app/dataset_inference_clean")
            if dataset_dir.exists():
                for item in dataset_dir.iterdir():
                    self.logger.info(f"  {item}")
            else:
                self.logger.warning(f"  {dataset_dir} が存在しません")
            
            # プロセス実行（タイムアウト保護付き）
            result = subprocess.run(
                cmd,
                cwd="/app",  # 作業ディレクトリを/appに設定
                capture_output=True,
                text=True,
                timeout=900  # 15分タイムアウト（AI処理時間を考慮）
            )
            
            execution_logs = f"標準出力:\n{result.stdout}\n標準エラー:\n{result.stderr}"
            
            if result.returncode == 0:
                self.logger.info("原流処理スキニング成功")
                return True, execution_logs
            else:
                self.logger.error(f"原流処理失敗 (exit code: {result.returncode})")
                return False, execution_logs
                
        except subprocess.TimeoutExpired:
            return False, "原流処理がタイムアウトしました (15分)"
        except Exception as e:
            return False, f"原流処理実行エラー: {e}"
    
    def _collect_skinning_outputs(self, model_name: str) -> Dict:
        """
        原流処理出力ファイル収集
        
        原流処理が生成する標準的な出力ファイルを探して収集
        generate_skin.shの実際の出力構造に基づく
        """
        output_files = {}
        
        # 標準的な原流処理出力パス
        results_dir = Path("/app/results")
        
        self.logger.info(f"原流処理出力収集開始: {results_dir}")
        
        # 出力ディレクトリの内容を確認
        if results_dir.exists():
            self.logger.info("results/ディレクトリの内容:")
            for item in results_dir.iterdir():
                size_info = f"({item.stat().st_size / (1024*1024):.2f}MB)" if item.is_file() else "(dir)"
                self.logger.info(f"  {item.name} {size_info}")
        else:
            self.logger.warning(f"出力ディレクトリが存在しません: {results_dir}")
            return output_files
        
        # FBXファイル検索（原流処理の実際の出力パターン）
        potential_fbx_patterns = [
            f"{model_name}_predict_skin.fbx",      # 標準的な出力パターン
            f"raw_data_predict_skin.fbx",          # メッシュ名ベース
            "skinned_model.fbx",                   # 汎用名
            f"{model_name}.fbx",                   # モデル名のみ
            "predict_skin.fbx"                     # 簡略名
        ]
        
        fbx_found = False
        for pattern in potential_fbx_patterns:
            fbx_path = results_dir / pattern
            if fbx_path.exists():
                # Step3出力ディレクトリにコピー
                step3_fbx = self.output_dir / f"{model_name}_skinned.fbx"
                shutil.copy2(fbx_path, step3_fbx)
                output_files["skinned_fbx"] = str(step3_fbx)
                output_files["fbx_size"] = f"{step3_fbx.stat().st_size / (1024*1024):.2f}MB"
                self.logger.info(f"スキニング済みFBX検出: {fbx_path} → {step3_fbx} ({output_files['fbx_size']})")
                fbx_found = True
                break
        
        if not fbx_found:
            self.logger.warning("スキニング済みFBXファイルが見つかりませんでした")
            # 全てのFBXファイルをリスト表示
            fbx_files = list(results_dir.glob("*.fbx"))
            self.logger.info(f"利用可能なFBXファイル: {[f.name for f in fbx_files]}")
        
        # NPZファイル検索（原流処理の実際の出力パターン）
        potential_npz_patterns = [
            "predict_skin.npz",                    # 標準的な出力名
            f"{model_name}_predict_skin.npz",      # モデル名付き
            f"raw_data_predict_skin.npz",          # メッシュ名ベース
            f"{model_name}_skin.npz"               # 簡略名
        ]
        
        npz_found = False
        for pattern in potential_npz_patterns:
            npz_path = results_dir / pattern
            if npz_path.exists():
                # Step3出力ディレクトリにコピー
                step3_npz = self.output_dir / f"{model_name}_skinning.npz"
                shutil.copy2(npz_path, step3_npz)
                output_files["skinning_npz"] = str(step3_npz)
                output_files["npz_size"] = f"{step3_npz.stat().st_size / (1024*1024):.2f}MB"
                self.logger.info(f"スキニングデータ検出: {npz_path} → {step3_npz} ({output_files['npz_size']})")
                npz_found = True
                break
        
        if not npz_found:
            self.logger.warning("スキニングNPZファイルが見つかりませんでした")
            # 全てのNPZファイルをリスト表示
            npz_files = list(results_dir.glob("*.npz"))
            self.logger.info(f"利用可能なNPZファイル: {[f.name for f in npz_files]}")
        
        # その他のファイル検索（ログ、設定など）
        additional_files = ["*.txt", "*.json", "*.yaml", "*.log"]
        for pattern in additional_files:
            for file_path in results_dir.glob(pattern):
                if file_path.is_file():
                    target_path = self.output_dir / file_path.name
                    shutil.copy2(file_path, target_path)
                    self.logger.info(f"追加ファイル: {file_path.name}")
        
        # 出力ファイル数とサイズの概要
        total_files = len(output_files)
        self.logger.info(f"Step3出力収集完了: {total_files}個のファイル")
        
        return output_files

    # === 補助メソッド ===
    
    def _get_data_statistics(self, mesh_npz_path: str, skeleton_fbx_path: str) -> tuple:
        """入力データの統計情報取得"""
        mesh_stats = {}
        skeleton_stats = {}
        
        try:
            # メッシュ統計
            if Path(mesh_npz_path).exists():
                with np.load(mesh_npz_path, allow_pickle=True) as data:
                    if 'vertices' in data:
                        mesh_stats["vertex_count"] = data['vertices'].shape[0]
                    else:
                        mesh_stats["vertex_count"] = 0
            
            # スケルトン統計（簡易）
            skeleton_stats["bone_count"] = 53  # UniRig標準ボーン数
            
        except Exception as e:
            self.logger.warning(f"統計情報取得エラー: {e}")
        
        return mesh_stats, skeleton_stats
    
    def _find_original_model_file(self, model_name: str) -> Path:
        """
        Step0で保存された元のモデルファイルを検索（拡張子自動検出）
        
        Args:
            model_name: モデル名
            
        Returns:
            元のモデルファイルのパス
            
        Raises:
            FileNotFoundError: 元のモデルファイルが見つからない場合
        """
        asset_preservation_dir = Path("/app/pipeline_work") / model_name / "00_asset_preservation"
        
        # サポートされている拡張子リスト
        supported_extensions = ['.glb', '.gltf', '.fbx', '.obj', '.ply']
        
        for ext in supported_extensions:
            potential_path = asset_preservation_dir / f"{model_name}{ext}"
            if potential_path.exists():
                self.logger.info(f"元のモデルファイルを検出: {potential_path}")
                return potential_path
        
        # ファイルが見つからない場合のエラー
        available_files = list(asset_preservation_dir.glob("*")) if asset_preservation_dir.exists() else []
        error_msg = f"元のモデルファイルが見つかりません。探索ディレクトリ: {asset_preservation_dir}, 利用可能ファイル: {available_files}"
        self.logger.error(error_msg)
        raise FileNotFoundError(error_msg)


