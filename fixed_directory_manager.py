#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
固定ディレクトリ管理クラス - 統一命名規則対応（整流実装）
2025年6月14日改修 - 統一命名規則とフォールバック機能実装

目的: 統一ファイル命名規則に基づく予測可能なファイル配置と
     既存ファイルとの互換性保持
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, List
import shutil

class UnifiedNamingConvention:
    """統一ファイル命名規則の実装"""
    
    NAMING_PATTERNS = {
        'step1': {
            'mesh_npz': '{model_name}_mesh.npz',
        },
        'step2': {
            'skeleton_fbx': '{model_name}_skeleton.fbx',
            'skeleton_npz': '{model_name}_skeleton.npz',
        },
        'step3': {
            'skinned_fbx': '{model_name}_skinned.fbx',
            'skinning_npz': '{model_name}_skinning.npz',
        },
        'step4': {
            'merged_fbx': '{model_name}_merged.fbx',
        },
        'step5': {
            'rigged_fbx': '{model_name}_rigged.fbx',  # 最終成果物
        }
    }
    
    # レガシー命名パターン（フォールバック用）
    LEGACY_PATTERNS = {
        'step1': {
            'mesh_npz': ['raw_data.npz'],
        },
        'step2': {
            'skeleton_fbx': ['{model_name}.fbx', 'skeleton.fbx', 'skeleton_model.fbx'],
            'skeleton_npz': ['predict_skeleton.npz'],
        },
        'step3': {
            'skinned_fbx': ['{model_name}_skinned_unirig.fbx', 'result_fbx.fbx', 'skinned_model.fbx'],
            'skinning_npz': ['predict_skin.npz', '{model_name}_skinning.npz'],
        },
        'step4': {
            'merged_fbx': ['{model_name}_textured.fbx', '{model_name}_merged.fbx'],
        },
        'step5': {
            'rigged_fbx': ['{model_name}_final.fbx', '{model_name}_rigged.fbx'],
        }
    }
    
    def get_unified_file_name(self, model_name: str, step: str, file_type: str) -> str:
        """統一命名規則に基づくファイル名生成"""
        pattern = self.NAMING_PATTERNS.get(step, {}).get(file_type)
        if pattern:
            return pattern.format(model_name=model_name)
        else:
            raise ValueError(f"未定義の統一命名パターン: {step}/{file_type}")
    
    def get_legacy_file_names(self, model_name: str, step: str, file_type: str) -> List[str]:
        """レガシー命名パターンリスト取得"""
        patterns = self.LEGACY_PATTERNS.get(step, {}).get(file_type, [])
        return [pattern.format(model_name=model_name) for pattern in patterns]

class FixedDirectoryManager:
    """決め打ちディレクトリ管理クラス - 統一命名規則対応"""
    
    def __init__(self, base_dir: Path, model_name: str, logger: Optional[logging.Logger] = None):
        """
        固定ディレクトリ管理クラス初期化
        
        Args:
            base_dir: ベースディレクトリ (/app/pipeline_work)
            model_name: モデル名
            logger: ロガーインスタンス
        """
        self.base_dir = Path(base_dir)
        self.model_name = model_name
        self.model_dir = self.base_dir / model_name
        self.logger = logger if logger else logging.getLogger(__name__)
        self.naming = UnifiedNamingConvention()
        
        # 決め打ちステップディレクトリ定義 (固定仕様)
        self.step_dirs = {
            "step0": "00_asset_preservation",
            "step1": "01_extracted_mesh", 
            "step2": "02_skeleton",
            "step3": "03_skinning",
            "step4": "04_merge",
            "step5": "05_blender_integration"
        }
    
    def get_step_dir(self, step: str) -> Path:
        """ステップディレクトリパス取得"""
        if step not in self.step_dirs:
            raise ValueError(f"未知のステップ: {step}")
        return self.model_dir / self.step_dirs[step]
    
    def create_all_directories(self):
        """全ステップディレクトリを作成"""
        try:
            # モデルディレクトリ作成
            self.model_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"モデルディレクトリ作成: {self.model_dir}")
            
            # 各ステップディレクトリ作成
            for step, dir_name in self.step_dirs.items():
                step_dir = self.model_dir / dir_name
                step_dir.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"ステップディレクトリ作成: {step_dir}")
            
            return True
        except Exception as e:
            self.logger.error(f"ディレクトリ作成エラー: {e}")
            return False
    
    def setup_directories(self):
        """ディレクトリセットアップ（create_all_directoriesのエイリアス）"""
        return self.create_all_directories()
    
    def get_unified_file_path(self, step: str, file_type: str) -> Path:
        """統一命名規則に基づくファイルパス取得"""
        step_dir = self.get_step_dir(step)
        unified_name = self.naming.get_unified_file_name(self.model_name, step, file_type)
        return step_dir / unified_name
    
    def find_file_with_fallback(self, step: str, file_type: str) -> Optional[Path]:
        """統一命名規則ファイル + レガシーファイルのフォールバック検索"""
        step_dir = self.get_step_dir(step)
        
        # 1. 統一命名規則ファイル検索
        unified_path = self.get_unified_file_path(step, file_type)
        if unified_path.exists():
            self.logger.info(f"✅ 統一ファイル発見: {unified_path}")
            return unified_path
        
        # 2. レガシー命名規則ファイル検索（フォールバック）
        legacy_names = self.naming.get_legacy_file_names(self.model_name, step, file_type)
        for legacy_name in legacy_names:
            legacy_path = step_dir / legacy_name
            if legacy_path.exists():
                self.logger.warning(f"⚠️ レガシーファイル使用: {legacy_path}")
                return legacy_path
        
        self.logger.error(f"❌ ファイル未発見: {step}/{file_type} in {step_dir}")
        return None
    
    def ensure_unified_output(self, step: str, file_type: str, 
                             original_file: Path) -> Path:
        """原流処理出力を統一命名規則にリネーム/コピー"""
        unified_path = self.get_unified_file_path(step, file_type)
        
        if original_file.exists() and original_file != unified_path:
            # 統一名でのコピー/リネーム
            unified_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original_file, unified_path)
            self.logger.info(f"🔄 統一命名規則適用: {original_file} → {unified_path}")
        
        return unified_path

    def validate_pipeline_integrity(self) -> Dict[str, bool]:
        """パイプライン完全性検証 (統一命名規則 + フォールバック対応)"""
        validation_results = {}
        
        # Step1検証: メッシュファイル存在確認
        step1_mesh = self.find_file_with_fallback("step1", "mesh_npz")
        validation_results["step1_mesh"] = step1_mesh is not None
        
        # Step2検証: スケルトンファイル確認
        step2_fbx = self.find_file_with_fallback("step2", "skeleton_fbx")
        step2_npz = self.find_file_with_fallback("step2", "skeleton_npz")
        validation_results["step2_fbx"] = step2_fbx is not None
        validation_results["step2_npz"] = step2_npz is not None
        
        # Step3検証: スキニング済みFBX確認
        step3_fbx = self.find_file_with_fallback("step3", "skinned_fbx")
        validation_results["step3_fbx"] = step3_fbx is not None
        
        # Step4検証: マージ済みFBX確認
        step4_fbx = self.find_file_with_fallback("step4", "merged_fbx")
        validation_results["step4_fbx"] = step4_fbx is not None
        
        # Step5検証: 最終FBX確認
        step5_fbx = self.find_file_with_fallback("step5", "rigged_fbx")
        validation_results["step5_fbx"] = step5_fbx is not None
        
        return validation_results

    def get_pipeline_completion_status(self) -> Dict[str, str]:
        """パイプライン完了状況の詳細取得 (統一命名規則対応)"""
        status = {}
        validation = self.validate_pipeline_integrity()
        
        # 各ステップの状況判定
        status["step0"] = "✅ 完了" if self.check_step_completion("step0") else "⏸️ 未実行"
        status["step1"] = "✅ 完了" if validation["step1_mesh"] else "⏸️ 未実行"
        status["step2"] = "✅ 完了" if validation["step2_fbx"] and validation["step2_npz"] else "⏸️ 未実行"
        status["step3"] = "✅ 完了" if validation["step3_fbx"] else "⏸️ 未実行"
        status["step4"] = "✅ 完了" if validation["step4_fbx"] else "⏸️ 未実行"
        status["step5"] = "✅ 完了" if validation["step5_fbx"] else "⏸️ 未実行"
        
        # 全体進捗計算
        completed_steps = sum(1 for s in status.values() if "✅" in s)
        total_steps = len(status)
        progress = f"{completed_steps}/{total_steps} ({(completed_steps/total_steps)*100:.1f}%)"
        status["overall_progress"] = progress
        
        return status

    def get_user_download_files(self) -> Dict[str, Optional[Path]]:
        """ユーザー向けダウンロード可能ファイル一覧"""
        download_files = {}
        
        # 最終成果物（最優先）
        rigged_fbx = self.find_file_with_fallback("step5", "rigged_fbx")
        if rigged_fbx:
            download_files["final_rigged_model"] = rigged_fbx
        
        # 中間成果物（必要に応じて）
        skeleton_fbx = self.find_file_with_fallback("step2", "skeleton_fbx")
        if skeleton_fbx:
            download_files["skeleton_only"] = skeleton_fbx
        
        skinned_fbx = self.find_file_with_fallback("step3", "skinned_fbx")
        if skinned_fbx:
            download_files["skinned_model"] = skinned_fbx
        
        merged_fbx = self.find_file_with_fallback("step4", "merged_fbx")
        if merged_fbx:
            download_files["merged_model"] = merged_fbx
        
        return download_files

    def validate_step_inputs(self, step: str) -> Tuple[bool, str, Dict[str, Path]]:
        """
        ステップ入力ファイルの検証
        
        Args:
            step: ステップ名
            
        Returns:
            valid: 検証結果
            message: 検証メッセージ
            available_files: 利用可能ファイル辞書
        """
        input_files = self.get_step_input_files(step)
        available_files = {}
        missing_files = []
        
        for key, path in input_files.items():
            if path.exists():
                available_files[key] = path
            else:
                missing_files.append(f"{key}: {path}")
        
        if missing_files:
            message = f"不足ファイル: {', '.join(missing_files)}"
            return False, message, available_files
        else:
            return True, "入力ファイル検証完了", available_files
    
    def check_step_completion(self, step: str) -> Tuple[bool, List[str], List[str]]:
        """
        ステップ完了状態をファイル存在で判定 (JSONなし)
        
        Args:
            step: ステップ名
            
        Returns:
            completed: 完了フラグ
            existing_files: 存在するファイルリスト
            missing_files: 不足ファイルリスト
        """
        expected = self.get_expected_files(step)
        existing_files = []
        missing_files = []
        
        for key, path in expected.items():
            if path.exists():
                existing_files.append(f"{key}: {path.name}")
            else:
                missing_files.append(f"{key}: {path.name}")
        
        completed = len(missing_files) == 0
        return completed, existing_files, missing_files
    
    def get_step_input_files(self, step: str) -> Dict[str, Path]:
        """
        ステップの入力ファイルを取得 (決め打ち依存関係)
        
        Args:
            step: ステップ名
            
        Returns:
            入力ファイル辞書
        """
        input_files = {}
        
        if step == "step0":
            # Step0: 元ファイルが入力
            input_files["input_file"] = self.model_dir / f"{self.model_name}.glb"
        
        elif step == "step1":
            # Step1: 元ファイルが入力
            input_files["input_file"] = self.model_dir / f"{self.model_name}.glb"
        
        elif step == "step2":
            # Step2: Step1の出力が入力
            step1_files = self.get_expected_files("step1")
            input_files["raw_data_npz"] = step1_files["raw_data_npz"]
        
        elif step == "step3":
            # Step3: Step1とStep2の出力が入力
            step1_files = self.get_expected_files("step1")
            step2_files = self.get_expected_files("step2")
            input_files["raw_data_npz"] = step1_files["raw_data_npz"]
            input_files["skeleton_fbx"] = step2_files["skeleton_fbx"]
            input_files["skeleton_npz"] = step2_files["skeleton_npz"]
        
        elif step == "step4":
            # Step4: Step2とStep3の出力が入力
            step2_files = self.get_expected_files("step2")
            step3_files = self.get_expected_files("step3")
            input_files["skeleton_fbx"] = step2_files["skeleton_fbx"]
            input_files["skinned_fbx"] = step3_files["skinned_fbx"]
        
        elif step == "step5":
            # Step5: Step4の出力と元ファイルが入力
            step4_files = self.get_expected_files("step4")
            input_files["merged_fbx"] = step4_files["merged_fbx"]
            input_files["original_file"] = self.model_dir / f"{self.model_name}.glb"
        
        return input_files
    
    def get_expected_files(self, step: str) -> Dict[str, Path]:
        """各ステップの期待出力ファイル辞書を取得"""
        step_dir = self.get_step_dir(step)
        
        if step == "step0":
            return {
                "asset_metadata_json": step_dir / f"{self.model_name}_asset_metadata.json",
                "asset_metadata_blender_json": step_dir / f"{self.model_name}_asset_metadata_blender.json",
                "textures_dir": step_dir / "textures",
                "original_file": step_dir / f"{self.model_name}.glb"
            }
        elif step == "step1":
            return {
                "raw_data_npz": step_dir / "raw_data.npz"
            }
        elif step == "step2":
            return {
                "skeleton_fbx": step_dir / f"{self.model_name}.fbx",
                "skeleton_npz": step_dir / "predict_skeleton.npz",
                "mesh_for_skeleton": step_dir / "mesh_for_skeleton" / "raw_data.npz"  # Step2専用メッシュ
            }
        elif step == "step3":
            return {
                "skinned_fbx": step_dir / f"{self.model_name}_skinned_unirig.fbx",
                "skinning_npz": step_dir / "skinning_data.npz"
            }
        elif step == "step4":
            return {
                "merged_fbx": step_dir / f"{self.model_name}_merged.fbx"
            }
        elif step == "step5":
            return {
                "final_fbx": step_dir / f"{self.model_name}_final.fbx",
                "textures_dir": step_dir / f"{self.model_name}_final.fbm"
            }
        else:
            return {}
    
    def find_original_model_file(self) -> Optional[Path]:
        """
        オリジナルモデルファイルを検索
        
        メッシュ再抽出のために、アップロードされたオリジナルファイルを検索します。
        複数の場所と拡張子を対象に検索を行います。
        
        Returns:
            Optional[Path]: 見つかったオリジナルファイルのパス、または None
        """
        # 検索対象の拡張子
        supported_extensions = ['.glb', '.gltf', '.fbx', '.obj', '.dae', '.ply']
        
        # 検索対象ディレクトリ（優先度順）
        search_paths = [
            # 1. Step0のアセット保存ディレクトリ
            self.get_step_dir('step0'),
            # 2. モデル専用ディレクトリ
            self.model_dir,
            # 3. パイプライン作業ディレクトリ直下
            self.base_dir,
            # 4. dataset_inference_clean（一時保存場所）
            Path("/app/dataset_inference_clean"),
            # 5. アプリケーションルート
            Path("/app")
        ]
        
        self.logger.info(f"オリジナルファイル検索開始: {self.model_name}")
        
        # モデル名での検索
        for search_dir in search_paths:
            if not search_dir.exists():
                continue
                
            self.logger.debug(f"検索ディレクトリ: {search_dir}")
            
            for ext in supported_extensions:
                # モデル名 + 拡張子のパターン
                candidate = search_dir / f"{self.model_name}{ext}"
                if candidate.exists():
                    self.logger.info(f"✅ オリジナルファイル発見: {candidate}")
                    return candidate
        
        # モデル名での検索が失敗した場合、ディレクトリ内の3Dファイルを検索
        for search_dir in search_paths:
            if not search_dir.exists():
                continue
                
            for ext in supported_extensions:
                # ディレクトリ内の該当拡張子ファイルを検索
                for candidate in search_dir.glob(f"*{ext}"):
                    if candidate.is_file():
                        self.logger.info(f"✅ 3Dファイル発見: {candidate}")
                        return candidate
        
        # 最後の手段: dataset_inference_clean内の全3Dファイル検索
        dataset_dir = Path("/app/dataset_inference_clean")
        if dataset_dir.exists():
            for file_path in dataset_dir.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                    self.logger.info(f"✅ dataset内3Dファイル発見: {file_path}")
                    return file_path
        
        self.logger.error(f"❌ オリジナルファイルが見つかりません: {self.model_name}")
        return None
