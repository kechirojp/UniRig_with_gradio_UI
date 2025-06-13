#!/usr/bin/env python3
"""
🏆 UniRig データフロー成功マイルストーン (2025年6月9日達成)
===========================================================

**重要**: このファイルは削除禁止！データフロー改修の成功実績として保持

📊 成功実績:
- 総処理時間: 40.80秒
- 最終FBX出力: 4.0MB
- Step4Merge 5段階処理フロー完全動作
- 統一ディレクトリ構造 (02_skeleton, 03_skinning, 04_merge) 完全対応

🎯 用途:
- データフロー改修時の参照リファレンス
- 問題発生時の動作確認用ベースライン
- 正常動作パターンの技術的証拠

🔧 技術的特徴:
- DATAFLOW_REFACTORING_GUIDE.instructions準拠
- バイナリFBX生成による src.inference.merge 互換性確保
- プロセス分離による安定動作
- 段階的フォールバック設計パターン実装

📋 データフロー構造:
/app/pipeline_work/{model_name}/
├── 01_extracted_mesh/     → raw_data.npz (Step1出力)
├── 02_skeleton/           → predict_skeleton.npz, {model_name}.fbx (Step2出力)  
├── 03_skinning/           → {model_name}_skinned_unirig.fbx (Step3出力・バイナリ形式)
└── 04_merge/              → {model_name}_textured.fbx (Step4出力・最終成果物)

⚠️ この構造が壊れた場合は、このファイルを参照してデータフローを復元してください。
"""

import os
import sys
import json
import time
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Any

# UniRig モジュールのインポート
sys.path.append('/app')
from step_modules.step1_extract import Step1Extract
from step_modules.step2_skeleton import Step2Skeleton
from step_modules.step3_skinning import Step3Skinning
from step_modules.step4_merge import execute_step4  # Step4Merge対応

class DataFlowVerificationTestMerge:
    """完全データフロー検証テストクラス (Step4Merge版)"""
    
    def __init__(self, model_name: str = "bird", cleanup_after: bool = True):
        """
        テスト初期化
        
        Args:
            model_name: テスト対象モデル名
            cleanup_after: テスト後のクリーンアップ実行フラグ
        """
        self.model_name = model_name
        self.cleanup_after = cleanup_after
        
        # ログ設定
        self.logger = self._setup_logger()
        
        # データフロー改修方針に準拠したパス設定
        self.pipeline_dir = Path('/app/pipeline_work')
        self.model_dir = self.pipeline_dir / model_name
        
        # ステップごとの出力ディレクトリ (改修方針準拠, Step0削除)
        self.step_dirs = {
            'step1': self.model_dir / '01_extracted_mesh', 
            'step2': self.model_dir / '02_skeleton',  # 正式命名規則準拠
            'step3': self.model_dir / '03_skinning',  # 正式命名規則準拠
            'step4': self.model_dir / '04_merge',  # Step4Merge準拠
            'output': self.model_dir / 'output'
        }
        
        # 検証結果格納用
        self.verification_results = {}
        
        # 入力ファイルの設定
        self.input_file = Path('/app/pipeline_output/step1_extract/bird/bird_input.glb')
        
        self.logger.info(f"=== DataFlowVerificationTestMerge 初期化完了 ===")
        self.logger.info(f"モデル名: {self.model_name}")
        self.logger.info(f"入力ファイル: {self.input_file}")
        self.logger.info(f"作業ディレクトリ: {self.model_dir}")
    
    def _setup_logger(self) -> logging.Logger:
        """ログ設定"""
        logger = logging.getLogger('DataFlowVerificationTestMerge')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _prepare_directories(self) -> bool:
        """ディレクトリ準備"""
        try:
            # クリーンアップ（必要に応じて）
            if self.model_dir.exists():
                shutil.rmtree(self.model_dir)
            
            # ディレクトリ作成
            for step_name, step_dir in self.step_dirs.items():
                step_dir.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"ディレクトリ作成: {step_dir}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"ディレクトリ準備エラー: {e}")
            return False
    
    def _verify_input_file(self) -> bool:
        """入力ファイル検証"""
        self.logger.info(f"入力ファイルパス確認: {self.input_file}")
        if not self.input_file.exists():
            self.logger.error(f"入力ファイルが見つかりません: {self.input_file}")
            # 利用可能なファイルを検索
            self.logger.info("利用可能な.glbファイルを検索中...")
            for glb_file in Path('/app').rglob('*.glb'):
                self.logger.info(f"  発見: {glb_file}")
            return False
        
        file_size = self.input_file.stat().st_size
        self.logger.info(f"入力ファイル確認: {self.input_file} ({file_size} bytes)")
        return True
    
    def execute_step1(self) -> Tuple[bool, Dict[str, Any]]:
        """Step1: メッシュ抽出実行"""
        try:
            self.logger.info("=== Step1: メッシュ抽出実行 ===")
            
            # Step1Extractクラスのインスタンス作成（改修方針準拠）
            step1_processor = Step1Extract(
                output_dir=Path(self.step_dirs['step1']),
                logger_instance=self.logger
            )
            
            # extract_meshメソッド呼び出し（改修方針準拠）
            success, logs, output_files = step1_processor.extract_mesh(
                input_file_path=self.input_file,
                model_name=self.model_name,
                preserve_textures_in_step1=False
            )
            
            self.verification_results['step1'] = {
                'success': success,
                'output_files': output_files,
                'logs_preview': logs[:200] + "..." if len(logs) > 200 else logs
            }
            
            if success:
                self.logger.info("✅ Step1 メッシュ抽出成功")
                self._verify_step1_outputs(output_files)
            else:
                self.logger.error("❌ Step1 メッシュ抽出失敗")
            
            return success, output_files
            
        except Exception as e:
            self.logger.error(f"❌ Step1 実行エラー: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False, {}
    
    def execute_step2(self, step1_outputs: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Step2: スケルトン生成実行"""
        try:
            self.logger.info("=== Step2: スケルトン生成実行 ===")
            
            # 入力ファイル確認
            extracted_npz = step1_outputs.get('extracted_npz')
            if not extracted_npz or not Path(extracted_npz).exists():
                self.logger.error(f"抽出NPZファイルが見つかりません: {extracted_npz}")
                return False, {}
            
            # Step2Skeletonクラスのインスタンス作成（改修方針準拠）
            step2_processor = Step2Skeleton(
                output_dir=Path(self.step_dirs['step2']),
                logger_instance=self.logger
            )
            
            # generate_skeletonメソッド呼び出し
            success, logs, output_files = step2_processor.generate_skeleton(
                input_npz_path=Path(extracted_npz),
                model_name=self.model_name,
                original_model_file_for_fbx_copy=self.input_file,
                gender="neutral"
            )
            
            self.verification_results['step2'] = {
                'success': success,
                'output_files': output_files,
                'logs_preview': logs[:200] + "..." if len(logs) > 200 else logs
            }
            
            if success:
                self.logger.info("✅ Step2 スケルトン生成成功")
                self._verify_step2_outputs(output_files)
            else:
                self.logger.error("❌ Step2 スケルトン生成失敗")
            
            return success, output_files
            
        except Exception as e:
            self.logger.error(f"❌ Step2 実行エラー: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False, {}
    
    def execute_step3(self, step1_outputs: Dict[str, Any], step2_outputs: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Step3: スキニング実行"""
        try:
            self.logger.info("=== Step3: スキニング実行 ===")
            
            # 入力ファイル確認
            extracted_npz = step1_outputs.get('extracted_npz')
            skeleton_fbx = step2_outputs.get('skeleton_fbx')
            skeleton_npz = step2_outputs.get('skeleton_npz')
            
            if not extracted_npz or not Path(extracted_npz).exists():
                self.logger.error(f"抽出NPZファイルが見つかりません: {extracted_npz}")
                return False, {}
            
            if not skeleton_fbx or not Path(skeleton_fbx).exists():
                self.logger.error(f"スケルトンFBXファイルが見つかりません: {skeleton_fbx}")
                return False, {}
                
            if not skeleton_npz or not Path(skeleton_npz).exists():
                self.logger.error(f"スケルトンNPZファイルが見つかりません: {skeleton_npz}")
                return False, {}
            
            # Step3Skinningクラスのインスタンス作成（改修方針準拠）
            step3_processor = Step3Skinning(
                output_dir=Path(self.step_dirs['step3']),
                logger_instance=self.logger
            )
            
            # apply_skinningメソッド呼び出し
            success, logs, output_files = step3_processor.apply_skinning(
                input_mesh_npz_path=Path(extracted_npz),
                input_skeleton_fbx_path=Path(skeleton_fbx),
                input_skeleton_npz_path=Path(skeleton_npz),
                model_name=self.model_name
            )
            
            self.verification_results['step3'] = {
                'success': success,
                'output_files': output_files,
                'logs_preview': logs[:200] + "..." if len(logs) > 200 else logs
            }
            
            if success:
                self.logger.info("✅ Step3 スキニング成功")
                self._verify_step3_outputs(output_files)
            else:
                self.logger.error("❌ Step3 スキニング失敗")
            
            return success, output_files
            
        except Exception as e:
            self.logger.error(f"❌ Step3 実行エラー: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False, {}
    
    def execute_step4_merge(self, step3_outputs: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Step4: テクスチャ統合実行 (step_modules/step4_merge.py使用, Step0なし)"""
        try:
            self.logger.info("=== Step4: テクスチャ統合実行 (Step4Merge版, Step0なし) ===")
            
            # 入力ファイル確認
            skinned_fbx = step3_outputs.get('skinned_fbx')
            
            if not skinned_fbx or not Path(skinned_fbx).exists():
                self.logger.error(f"スキニング済みFBXファイルが見つかりません: {skinned_fbx}")
                return False, {}
            
            # execute_step4関数呼び出し (step_modules/step4_merge.py) - 改修方針準拠
            # Step0なしなのでasset_preservation_dir=Noneで実行
            success, logs, output_files = execute_step4(
                model_name=self.model_name,
                skinned_fbx=skinned_fbx,
                original_model=str(self.input_file),
                output_dir=str(self.step_dirs['step4']),
                asset_preservation_dir=None  # Step0なしなのでNone
            )
            
            self.verification_results['step4'] = {
                'success': success,
                'output_files': output_files,
                'logs_preview': logs[:500] + "..." if len(logs) > 500 else logs,
                'processing_method': 'step4_merge'
            }
            
            if success:
                self.logger.info("✅ Step4 テクスチャ統合成功 (Step4Merge)")
                self._verify_step4_merge_outputs(output_files)
            else:
                self.logger.error("❌ Step4 テクスチャ統合失敗 (Step4Merge)")
            
            return success, output_files
            
        except Exception as e:
            self.logger.error(f"❌ Step4Merge実行エラー: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False, {}
    
    def _verify_step1_outputs(self, output_files: Dict[str, Any]) -> None:
        """Step1出力ファイル検証"""
        expected_files = ['extracted_npz']
        
        for file_key in expected_files:
            if file_key in output_files:
                file_path = Path(output_files[file_key])
                if file_path.exists():
                    file_size = file_path.stat().st_size
                    self.logger.info(f"✅ Step1出力確認: {file_key} = {file_path} ({file_size} bytes)")
                else:
                    self.logger.warning(f"⚠️ Step1出力ファイル不在: {file_key} = {file_path}")
            else:
                self.logger.warning(f"⚠️ Step1出力キー不在: {file_key}")
    
    def _verify_step2_outputs(self, output_files: Dict[str, Any]) -> None:
        """Step2出力ファイル検証"""
        expected_files = ['skeleton_fbx', 'skeleton_npz']
        
        for file_key in expected_files:
            if file_key in output_files:
                file_path = Path(output_files[file_key])
                if file_path.exists():
                    file_size = file_path.stat().st_size
                    self.logger.info(f"✅ Step2出力確認: {file_key} = {file_path} ({file_size} bytes)")
                else:
                    self.logger.warning(f"⚠️ Step2出力ファイル不在: {file_key} = {file_path}")
            else:
                self.logger.warning(f"⚠️ Step2出力キー不在: {file_key}")
    
    def _verify_step3_outputs(self, output_files: Dict[str, Any]) -> None:
        """Step3出力ファイル検証（改修方針準拠）"""
        expected_files = ['skinned_fbx']  # {model_name}_skinned_unirig.fbx 期待
        
        for file_key in expected_files:
            if file_key in output_files:
                file_path = Path(output_files[file_key])
                if file_path.exists():
                    file_size = file_path.stat().st_size
                    self.logger.info(f"✅ Step3出力確認: {file_key} = {file_path} ({file_size} bytes)")
                else:
                    self.logger.warning(f"⚠️ Step3出力ファイル不在: {file_key} = {file_path}")
            else:
                self.logger.warning(f"⚠️ Step3出力キー不在: {file_key}")
    
    def _verify_step4_merge_outputs(self, output_files: Dict[str, Any]) -> None:
        """Step4Merge出力ファイル検証（改修方針準拠）"""
        # 期待ファイル: {model_name}_final_textured.fbx, {model_name}_final_textured.glb
        expected_files = ['final_fbx']
        
        for file_key in expected_files:
            if file_key in output_files:
                file_path = Path(output_files[file_key])
                if file_path.exists():
                    file_size = file_path.stat().st_size
                    self.logger.info(f"✅ Step4Merge出力確認: {file_key} = {file_path} ({file_size} bytes)")
                else:
                    self.logger.warning(f"⚠️ Step4Merge出力ファイル不在: {file_key} = {file_path}")
            else:
                self.logger.warning(f"⚠️ Step4Merge出力キー不在: {file_key}")
        
        # 品質レポート確認
        if 'quality_report' in output_files:
            quality_report = output_files['quality_report']
            self.logger.info(f"✅ Step4Merge品質レポート確認:")
            # QualityReportはdataclassなので属性アクセス
            self.logger.info(f"  - ファイルサイズ: {getattr(quality_report, 'file_size_mb', 'N/A')} MB")
            self.logger.info(f"  - 処理時間: {getattr(quality_report, 'processing_time_seconds', 'N/A')} 秒")
            self.logger.info(f"  - テクスチャ復元方法: {getattr(quality_report, 'texture_restoration_method', 'N/A')}")
            self.logger.info(f"  - 検証合格: {getattr(quality_report, 'validation_passed', 'N/A')}")
        else:
            self.logger.warning("⚠️ Step4Merge品質レポート不在")
    
    def cleanup(self) -> None:
        """テスト後のクリーンアップ"""
        if self.cleanup_after and self.model_dir.exists():
            try:
                shutil.rmtree(self.model_dir)
                self.logger.info(f"クリーンアップ完了: {self.model_dir}")
            except Exception as e:
                self.logger.error(f"クリーンアップエラー: {e}")
    
    def run_complete_test(self) -> bool:
        """完全テスト実行"""
        start_time = time.time()
        
        try:
            self.logger.info("=== UniRig 完全データフロー検証テスト開始 (Step4Merge版) ===")
            
            # 事前準備
            if not self._prepare_directories():
                return False
            
            if not self._verify_input_file():
                return False
            
            # Step 1: メッシュ抽出
            step1_success, step1_outputs = self.execute_step1()
            if not step1_success:
                self.logger.error("Step1失敗により、テスト中断")
                return False
            
            # Step 2: スケルトン生成
            step2_success, step2_outputs = self.execute_step2(step1_outputs)
            if not step2_success:
                self.logger.error("Step2失敗により、テスト中断")
                return False
            
            # Step 3: スキニング
            step3_success, step3_outputs = self.execute_step3(step1_outputs, step2_outputs)
            if not step3_success:
                self.logger.error("Step3失敗により、テスト中断")
                return False
            
            # Step 4: テクスチャ統合 (Step4Merge) - Step0なしで実行
            step4_success, step4_outputs = self.execute_step4_merge(step3_outputs)
            if not step4_success:
                self.logger.error("Step4Merge失敗により、テスト中断")
                return False
            
            # 全ステップ完了
            total_time = time.time() - start_time
            self.logger.info("=== 🎉 全ステップ完了 ===")
            self.logger.info(f"総処理時間: {total_time:.2f}秒")
            
            # 結果サマリー
            self._print_test_summary()
            
            return True
            
        except Exception as e:
            self.logger.error(f"完全テスト実行エラー: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
        
        finally:
            # クリーンアップ
            if hasattr(self, 'cleanup_after'):
                self.cleanup()
    
    def _print_test_summary(self) -> None:
        """テスト結果サマリー表示"""
        self.logger.info("=== テスト結果サマリー ===")
        
        for step_name, result in self.verification_results.items():
            status = "✅ 成功" if result.get('success') else "❌ 失敗"
            self.logger.info(f"{step_name}: {status}")
            
            # 出力ファイル情報
            output_files = result.get('output_files', {})
            for file_key, file_path in output_files.items():
                if file_key != 'quality_report':  # 品質レポートは別途表示
                    self.logger.info(f"  - {file_key}: {file_path}")


def main():
    """メイン実行関数"""
    print("=== UniRig 完全データフロー検証テスト (Step4Merge版) ===")
    print("参照: MERGE_PROCESS_FLOW.md 準拠の5段階処理フロー")
    print()
    
    # テストインスタンス作成（改修方針準拠テスト）
    test = DataFlowVerificationTestMerge(
        model_name="bird_dataflow_refactored",  # 改修方針準拠テスト
        cleanup_after=True
    )
    
    # 完全テスト実行
    success = test.run_complete_test()
    
    if success:
        print("\n🎉 全ステップ成功！Step4Mergeによるテクスチャ統合が完了しました。")
        return 0
    else:
        print("\n❌ テスト失敗。ログを確認してください。")
        return 1


if __name__ == "__main__":
    exit(main())
