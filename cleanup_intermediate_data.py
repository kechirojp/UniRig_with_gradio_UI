#!/usr/bin/env python3
"""
UniRig 中間データクリーンアップツール

このスクリプトは、app.pyが生成する中間データディレクトリ（pipeline_work）を削除します。
パイプライン実行完了後に手動またはスケジュールで実行することを想定しています。
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Tuple, List, Dict, Any
import time
import argparse

# デフォルト設定
PIPELINE_BASE_DIR = Path("/app/pipeline_work")
DATASET_INFERENCE_DIR = Path("/app/dataset_inference_clean")  # UniRig処理用ディレクトリ
BACKUP_DIR = Path("/app/pipeline_backups")  # 削除前にバックアップを作成する場合

# ロガー設定
logger = logging.getLogger("UniRigCleanup")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class IntermediateDataCleaner:
    """中間データクリーンアップクラス"""
    
    def __init__(self, pipeline_base_dir: Path = PIPELINE_BASE_DIR, 
                 dataset_inference_dir: Path = DATASET_INFERENCE_DIR,
                 backup_dir: Path = BACKUP_DIR, logger_instance: logging.Logger = logger):
        self.pipeline_base_dir = pipeline_base_dir
        self.dataset_inference_dir = dataset_inference_dir
        self.backup_dir = backup_dir
        self.logger = logger_instance
    
    def analyze_intermediate_data(self) -> Dict[str, Any]:
        """中間データの分析を行う"""
        analysis = {
            "pipeline_dir_exists": False,
            "dataset_inference_dir_exists": False,
            "total_size_mb": 0,
            "model_directories": [],
            "dataset_inference_models": [],
            "step_directories": {},
            "file_count": 0,
            "can_cleanup": False
        }
        
        if not self.pipeline_base_dir.exists():
            self.logger.info(f"パイプラインディレクトリが存在しません: {self.pipeline_base_dir}")
        else:
            analysis["pipeline_dir_exists"] = True
        
        if not self.dataset_inference_dir.exists():
            self.logger.info(f"UniRig処理ディレクトリが存在しません: {self.dataset_inference_dir}")
        else:
            analysis["dataset_inference_dir_exists"] = True
        
        if not analysis["pipeline_dir_exists"] and not analysis["dataset_inference_dir_exists"]:
            return analysis
        
        analysis["pipeline_dir_exists"] = True
        
        try:
            # ディレクトリサイズ計算（pipeline_work + dataset_inference_clean）
            total_size = 0
            file_count = 0
            
            # pipeline_work の分析
            if analysis["pipeline_dir_exists"]:
                for root, dirs, files in os.walk(self.pipeline_base_dir):
                    for file in files:
                        file_path = Path(root) / file
                        try:
                            size = file_path.stat().st_size
                            total_size += size
                            file_count += 1
                        except (OSError, IOError):
                            continue
            
            # dataset_inference_clean の分析
            if analysis["dataset_inference_dir_exists"]:
                for root, dirs, files in os.walk(self.dataset_inference_dir):
                    for file in files:
                        file_path = Path(root) / file
                        try:
                            size = file_path.stat().st_size
                            total_size += size
                            file_count += 1
                        except (OSError, IOError):
                            continue
            
            analysis["total_size_mb"] = total_size / (1024 * 1024)
            analysis["file_count"] = file_count
            
            # pipeline_work モデルディレクトリの検出
            model_dirs = []
            if analysis["pipeline_dir_exists"]:
                for item in self.pipeline_base_dir.iterdir():
                    if item.is_dir():
                        model_dirs.append({
                            "name": item.name,
                            "path": str(item),
                            "type": "pipeline_work",
                            "last_modified": time.ctime(item.stat().st_mtime)
                        })
            analysis["model_directories"] = model_dirs
            
            # dataset_inference_clean モデルディレクトリの検出
            dataset_models = []
            if analysis["dataset_inference_dir_exists"]:
                for item in self.dataset_inference_dir.iterdir():
                    if item.is_dir():
                        dataset_models.append({
                            "name": item.name,
                            "path": str(item),
                            "type": "dataset_inference",
                            "last_modified": time.ctime(item.stat().st_mtime)
                        })
            analysis["dataset_inference_models"] = dataset_models
            
            # ステップディレクトリの検出（pipeline_workのみ）
            step_counts = {}
            for model_dir in model_dirs:
                model_path = Path(model_dir["path"])
                steps = []
                for step_dir in model_path.iterdir():
                    if step_dir.is_dir() and step_dir.name.startswith(("0", "step")):
                        steps.append(step_dir.name)
                step_counts[model_dir["name"]] = steps
            
            analysis["step_directories"] = step_counts
            analysis["can_cleanup"] = analysis["pipeline_dir_exists"] or analysis["dataset_inference_dir_exists"]
            
        except Exception as e:
            self.logger.error(f"中間データ分析エラー: {e}")
            analysis["error"] = str(e)
        
        return analysis
    
    def create_backup(self, backup_name: str = None) -> Tuple[bool, str]:
        """中間データのバックアップを作成"""
        if not self.pipeline_base_dir.exists():
            return False, "中間データディレクトリが存在しません"
        
        try:
            if backup_name is None:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                backup_name = f"pipeline_work_backup_{timestamp}"
            
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = self.backup_dir / backup_name
            
            self.logger.info(f"バックアップ作成中: {backup_path}")
            shutil.copytree(self.pipeline_base_dir, backup_path)
            
            backup_size = sum(f.stat().st_size for f in backup_path.rglob('*') if f.is_file()) / (1024 * 1024)
            self.logger.info(f"バックアップ完了: {backup_path} ({backup_size:.2f}MB)")
            
            return True, f"バックアップ作成完了: {backup_path}"
            
        except Exception as e:
            self.logger.error(f"バックアップ作成エラー: {e}")
            return False, f"バックアップ作成失敗: {str(e)}"
    
    def create_backup_both_dirs(self, backup_name: str = None) -> Tuple[bool, str]:
        """pipeline_work と dataset_inference_clean の両方をバックアップ"""
        try:
            if backup_name is None:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                backup_name = f"intermediate_data_backup_{timestamp}"
            
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = self.backup_dir / backup_name
            backup_path.mkdir(exist_ok=True)
            
            backup_size = 0
            
            # pipeline_work のバックアップ
            if self.pipeline_base_dir.exists():
                pipeline_backup = backup_path / "pipeline_work"
                self.logger.info(f"pipeline_work バックアップ中: {pipeline_backup}")
                shutil.copytree(self.pipeline_base_dir, pipeline_backup)
                backup_size += sum(f.stat().st_size for f in pipeline_backup.rglob('*') if f.is_file())
            
            # dataset_inference_clean のバックアップ
            if self.dataset_inference_dir.exists():
                dataset_backup = backup_path / "dataset_inference_clean"
                self.logger.info(f"dataset_inference_clean バックアップ中: {dataset_backup}")
                shutil.copytree(self.dataset_inference_dir, dataset_backup)
                backup_size += sum(f.stat().st_size for f in dataset_backup.rglob('*') if f.is_file())
            
            backup_size_mb = backup_size / (1024 * 1024)
            self.logger.info(f"バックアップ完了: {backup_path} ({backup_size_mb:.2f}MB)")
            
            return True, f"バックアップ作成完了: {backup_path}"
            
        except Exception as e:
            self.logger.error(f"バックアップ作成エラー: {e}")
            return False, f"バックアップ作成失敗: {str(e)}"
    
    def cleanup_intermediate_data(self, create_backup: bool = False, 
                                  backup_name: str = None) -> Tuple[bool, str]:
        """中間データのクリーンアップを実行（pipeline_work + dataset_inference_clean）"""
        # 分析
        analysis = self.analyze_intermediate_data()
        if not analysis["can_cleanup"]:
            return False, "中間データの分析に失敗したため、削除を中止します"
        
        if not analysis["pipeline_dir_exists"] and not analysis["dataset_inference_dir_exists"]:
            return True, "中間データディレクトリが存在しないため、削除は不要です"
        
        self.logger.info(f"削除対象: pipeline_work + dataset_inference_clean ({analysis['total_size_mb']:.2f}MB, {analysis['file_count']}ファイル)")
        
        try:
            # バックアップ作成（オプション）
            if create_backup:
                backup_success, backup_msg = self.create_backup_both_dirs(backup_name)
                if not backup_success:
                    return False, f"バックアップ作成失敗により削除を中止: {backup_msg}"
                self.logger.info(backup_msg)
            
            deleted_dirs = []
            
            # pipeline_work削除
            if analysis["pipeline_dir_exists"]:
                self.logger.info(f"pipeline_work削除開始: {self.pipeline_base_dir}")
                shutil.rmtree(self.pipeline_base_dir)
                deleted_dirs.append("pipeline_work")
            
            # dataset_inference_clean削除
            if analysis["dataset_inference_dir_exists"]:
                self.logger.info(f"dataset_inference_clean削除開始: {self.dataset_inference_dir}")
                shutil.rmtree(self.dataset_inference_dir)
                deleted_dirs.append("dataset_inference_clean")
            
            # 削除確認
            still_exists = []
            if self.pipeline_base_dir.exists():
                still_exists.append("pipeline_work")
            if self.dataset_inference_dir.exists():
                still_exists.append("dataset_inference_clean")
            
            if still_exists:
                return False, f"削除後もディレクトリが存在します: {', '.join(still_exists)}"
            
            message = f"中間データ削除完了: {analysis['total_size_mb']:.2f}MB, {analysis['file_count']}ファイル削除"
            self.logger.info(message)
            return True, message
            
        except Exception as e:
            self.logger.error(f"中間データ削除エラー: {e}")
            return False, f"削除エラー: {str(e)}"
    
    def cleanup_specific_model(self, model_name: str, create_backup: bool = False) -> Tuple[bool, str]:
        """特定のモデルの中間データのみを削除（pipeline_work + dataset_inference_clean）"""
        pipeline_model_path = self.pipeline_base_dir / model_name
        dataset_model_path = self.dataset_inference_dir / model_name
        
        if not pipeline_model_path.exists() and not dataset_model_path.exists():
            return True, f"モデル '{model_name}' の中間データが存在しないため、削除は不要です"
        
        try:
            # サイズ計算
            total_size = 0
            file_count = 0
            
            if pipeline_model_path.exists():
                total_size += sum(f.stat().st_size for f in pipeline_model_path.rglob('*') if f.is_file())
                file_count += len(list(pipeline_model_path.rglob('*')))
            
            if dataset_model_path.exists():
                total_size += sum(f.stat().st_size for f in dataset_model_path.rglob('*') if f.is_file())
                file_count += len(list(dataset_model_path.rglob('*')))
            
            # バックアップ作成（オプション）
            if create_backup:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                backup_name = f"{model_name}_backup_{timestamp}"
                backup_path = self.backup_dir / backup_name
                self.backup_dir.mkdir(parents=True, exist_ok=True)
                
                if pipeline_model_path.exists():
                    pipeline_backup = backup_path / "pipeline_work"
                    shutil.copytree(pipeline_model_path, pipeline_backup)
                
                if dataset_model_path.exists():
                    dataset_backup = backup_path / "dataset_inference_clean"
                    shutil.copytree(dataset_model_path, dataset_backup)
                
                self.logger.info(f"モデルバックアップ作成: {backup_path}")
            
            # 削除実行
            deleted_dirs = []
            
            if pipeline_model_path.exists():
                self.logger.info(f"pipeline_work/{model_name} 削除開始: {pipeline_model_path}")
                shutil.rmtree(pipeline_model_path)
                deleted_dirs.append("pipeline_work")
            
            if dataset_model_path.exists():
                self.logger.info(f"dataset_inference_clean/{model_name} 削除開始: {dataset_model_path}")
                shutil.rmtree(dataset_model_path)
                deleted_dirs.append("dataset_inference_clean")
            
            message = f"モデル '{model_name}' の中間データ削除完了: {total_size/(1024*1024):.2f}MB, {file_count}ファイル削除 (対象: {', '.join(deleted_dirs)})"
            self.logger.info(message)
            return True, message
            
        except Exception as e:
            self.logger.error(f"モデル中間データ削除エラー: {e}")
            return False, f"削除エラー: {str(e)}"


def main():
    """メイン関数 - コマンドライン実行用"""
    parser = argparse.ArgumentParser(description="UniRig 中間データクリーンアップツール")
    parser.add_argument("--analyze", action="store_true", help="中間データの分析のみ実行")
    parser.add_argument("--backup", action="store_true", help="削除前にバックアップを作成")
    parser.add_argument("--backup-name", type=str, help="バックアップ名を指定")
    parser.add_argument("--model", type=str, help="特定のモデルのみ削除")
    parser.add_argument("--force", action="store_true", help="確認なしで削除実行")
    
    args = parser.parse_args()
    
    cleaner = IntermediateDataCleaner()
    
    # 分析実行
    analysis = cleaner.analyze_intermediate_data()
    
    print("🔍 UniRig 中間データ分析結果")
    print("=" * 50)
    
    if not analysis["pipeline_dir_exists"]:
        print("[OK] 中間データディレクトリは存在しません")
        return
    
    print(f"[DIR] ディレクトリ: {PIPELINE_BASE_DIR}")
    print(f"[SIZE] 総サイズ: {analysis['total_size_mb']:.2f}MB")
    print(f"📄 ファイル数: {analysis['file_count']:,}個")
    print(f"[FILE] モデル数: {len(analysis['model_directories'])}個")
    
    if analysis["model_directories"]:
        print("\n📋 モデル一覧:")
        for model in analysis["model_directories"]:
            steps = analysis["step_directories"].get(model["name"], [])
            print(f"  • {model['name']} (ステップ: {', '.join(steps)})")
    
    # 分析のみの場合は終了
    if args.analyze:
        return
    
    # 削除実行
    if not args.force:
        if analysis["total_size_mb"] > 0:
            response = input(f"\n❓ {analysis['total_size_mb']:.2f}MBのデータを削除しますか？ (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print("削除を中止しました")
                return
        else:
            print("削除対象のデータがありません")
            return
    
    # 削除実行
    if args.model:
        success, message = cleaner.cleanup_specific_model(args.model, args.backup)
    else:
        success, message = cleaner.cleanup_intermediate_data(args.backup, args.backup_name)
    
    if success:
        print(f"[OK] {message}")
    else:
        print(f"[FAIL] {message}")


if __name__ == "__main__":
    main()
