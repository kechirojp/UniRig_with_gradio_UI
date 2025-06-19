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
            'final_fbx': '{model_name}_final.fbx',     # 最終成果物（統一）
            # 'final_output': '{model_name}_final{ext}', # 動的拡張子対応は別途処理
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
            'skinned_fbx': ['{model_name}_skinned.fbx', '{model_name}_skinned_unirig.fbx', 'result_fbx.fbx', 'skinned_model.fbx'],
            'skinning_npz': ['predict_skin.npz', '{model_name}_skinning.npz'],
        },
        'step4': {
            'merged_fbx': ['{model_name}_textured.fbx', '{model_name}_merged.fbx'],
        },
        'step5': {
            'rigged_fbx': ['{model_name}_final.fbx'],
            'final_fbx': ['{model_name}_final.fbx'],
            # 'final_output': ['{model_name}_final{ext}', '{model_name}_final.fbx', '{model_name}_rigged.fbx'],  # 動的拡張子対応は別途処理
        }
    }
    
    def get_unified_file_name(self, model_name: str, step: str, file_type: str, ext: str = None) -> str:
        """統一命名規則に基づくファイル名生成（動的拡張子対応）"""
        pattern = self.NAMING_PATTERNS.get(step, {}).get(file_type)
        if pattern:
            try:
                if '{ext}' in pattern and ext:
                    return pattern.format(model_name=model_name, ext=ext)
                else:
                    return pattern.format(model_name=model_name)
            except KeyError:
                # フォーマット失敗時はextなしで再試行
                return pattern.format(model_name=model_name)
        else:
            raise ValueError(f"未定義の統一命名パターン: {step}/{file_type}")
    
    def get_legacy_file_names(self, model_name: str, step: str, file_type: str, ext: str = None) -> List[str]:
        """レガシー命名パターンリスト取得（動的拡張子対応）"""
        patterns = self.LEGACY_PATTERNS.get(step, {}).get(file_type, [])
        result = []
        for pattern in patterns:
            try:
                if '{ext}' in pattern and ext:
                    result.append(pattern.format(model_name=model_name, ext=ext))
                else:
                    result.append(pattern.format(model_name=model_name))
            except KeyError:
                # フォーマット失敗時はextなしで再試行
                try:
                    result.append(pattern.format(model_name=model_name))
                except KeyError:
                    # それでも失敗する場合はスキップ
                    continue
        return result

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
    
    def get_unified_file_path(self, step: str, file_type: str, ext: str = None) -> Path:
        """統一命名規則に基づくファイルパス取得（動的拡張子対応）"""
        step_dir = self.get_step_dir(step)
        unified_name = self.naming.get_unified_file_name(self.model_name, step, file_type, ext)
        return step_dir / unified_name
    
    def find_file_with_fallback(self, step: str, file_type: str, ext: str = None) -> Optional[Path]:
        """統一命名規則ファイル + レガシーファイルのフォールバック検索（動的拡張子対応）"""
        step_dir = self.get_step_dir(step)
        
        # 1. 統一命名規則ファイル検索
        unified_path = self.get_unified_file_path(step, file_type, ext)
        if unified_path.exists():
            self.logger.info(f"[OK] 統一ファイル発見: {unified_path}")
            return unified_path
        
        # 2. レガシー命名規則ファイル検索（フォールバック）
        legacy_names = self.naming.get_legacy_file_names(self.model_name, step, file_type, ext)
        for legacy_name in legacy_names:
            legacy_path = step_dir / legacy_name
            if legacy_path.exists():
                self.logger.warning(f"⚠️ レガシーファイル使用: {legacy_path}")
                return legacy_path
        
        self.logger.error(f"[FAIL] ファイル未発見: {step}/{file_type} in {step_dir}")
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
        
        # Step5検証: 最終出力確認（動的形式対応）
        step5_output = self.find_file_with_dynamic_extension("step5", "final_output")
        validation_results["step5_fbx"] = step5_output is not None
        
        return validation_results

    def get_pipeline_completion_status(self) -> Dict[str, bool]:
        """パイプライン完了状況の詳細取得 (統一命名規則対応)"""
        validation = self.validate_pipeline_integrity()
        
        # 各ステップの完了状況（ブール値で返す）
        step0_completed, _, _ = self.check_step_completion("step0")  # タプルから最初の要素を取得
        status = {
            "step0": step0_completed,
            "step1": validation["step1_mesh"],
            "step2": validation["step2_fbx"] and validation["step2_npz"],
            "step3": validation["step3_fbx"],
            "step4": validation["step4_fbx"],
            "step5": validation["step5_fbx"]
        }
        
        return status

    def get_user_download_files(self) -> Dict[str, Optional[Path]]:
        """ユーザー向けダウンロード可能ファイル一覧"""
        download_files = {}
        
        # 最終成果物（最優先・動的形式対応）
        final_output = self.find_file_with_dynamic_extension("step5", "final_output")
        if final_output:
            download_files["final_rigged_model"] = final_output
        
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
                "skeleton_fbx": step_dir / f"{self.model_name}_skeleton.fbx",
                "skeleton_npz": step_dir / "predict_skeleton.npz",
                "mesh_for_skeleton": step_dir / "mesh_for_skeleton" / "raw_data.npz"  # Step2専用メッシュ
            }
        elif step == "step3":
            return {
                "skinned_fbx": step_dir / f"{self.model_name}_skinned.fbx",
                "skinning_npz": step_dir / "skinning_data.npz"
            }
        elif step == "step4":
            return {
                "merged_fbx": step_dir / f"{self.model_name}_merged.fbx"
            }
        elif step == "step5":
            # 動的ファイル形式対応: オリジナルファイルの拡張子を検索
            original_file = self.find_original_model_file()
            if original_file:
                original_ext = original_file.suffix.lower()
                final_output = step_dir / f"{self.model_name}_final{original_ext}"
            else:
                # デフォルトはFBX
                final_output = step_dir / f"{self.model_name}_final.fbx"
            
            return {
                "final_output": final_output,               # 動的形式対応
                "final_fbx": step_dir / f"{self.model_name}_final.fbx",  # 後方互換性維持
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
        # 検索対象の拡張子（より具体的な順序で）
        supported_extensions = ['.glb', '.gltf', '.fbx', '.obj', '.vrm', '.dae', '.ply']
        
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
                    self.logger.info(f"[OK] オリジナルファイル発見: {candidate}")
                    return candidate
        
        # モデル名での検索が失敗した場合、ディレクトリ内の3Dファイルを検索
        for search_dir in search_paths:
            if not search_dir.exists():
                continue
                
            for ext in supported_extensions:
                # ディレクトリ内の該当拡張子ファイルを検索
                for candidate in search_dir.glob(f"*{ext}"):
                    if candidate.is_file():
                        self.logger.info(f"[OK] 3Dファイル発見: {candidate}")
                        return candidate
        
        # 最後の手段: dataset_inference_clean内の全3Dファイル検索
        dataset_dir = Path("/app/dataset_inference_clean")
        if dataset_dir.exists():
            for file_path in dataset_dir.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                    self.logger.info(f"[OK] dataset内3Dファイル発見: {file_path}")
                    return file_path
        
        self.logger.error(f"[FAIL] オリジナルファイルが見つかりません: {self.model_name}")
        return None

    def get_original_file_extension(self) -> str:
        """
        アップロードされたファイルの拡張子を取得（シンプル実装）
        
        Returns:
            str: 元のファイル拡張子（例: '.glb', '.fbx', '.obj'）
                見つからない場合は '.fbx' をデフォルトとして返す
        """
        # 最もシンプルな方法: オリジナルファイルを検索して拡張子取得
        original_file = self.find_original_model_file()
        if original_file:
            # ユーザーの指摘通り：ファイル名の末尾から最初のピリオドまで
            ext = original_file.suffix.lower()
            self.logger.info(f"[OK] オリジナルファイルから形式取得: {ext}")
            return ext
        
        # デフォルト（FBX）
        self.logger.warning("ファイル形式が特定できません。デフォルトとして .fbx を使用")
        return '.fbx'

    def get_step5_output_path_with_original_extension(self) -> Path:
        """
        Step5の最終出力パス（元ファイル形式を維持）
        
        Returns:
            Path: 元のファイル形式での最終出力パス
        """
        original_ext = self.get_original_file_extension()
        step5_dir = self.get_step_dir('step5')
        return step5_dir / f"{self.model_name}_final{original_ext}"

    def find_file_with_dynamic_extension(self, step: str, file_type: str) -> Optional[Path]:
        """動的拡張子対応のファイル検索（Step5専用）"""
        if step == 'step5' and file_type in ['final_output', 'final_fbx']:
            # Step5ディレクトリで様々な拡張子を検索
            step_dir = self.get_step_dir(step)
            base_name = f"{self.model_name}_final"
            
            # 一般的な3D形式を検索
            supported_extensions = ['.glb', '.gltf', '.fbx', '.obj', '.dae', '.ply']
            
            for ext in supported_extensions:
                candidate_path = step_dir / f"{base_name}{ext}"
                if candidate_path.exists():
                    self.logger.info(f"[OK] 動的形式ファイル発見: {candidate_path}")
                    return candidate_path
        
        # final_outputが見つからない場合はNoneを返す（エラーを避ける）
        return None
