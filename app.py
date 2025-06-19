"""
🎯 UniRig WebUI完全版 - src/pipeline統合・決め打ちディレクトリ戦略完全適用

改修完了 (2025年6月14日 - 最終統合版):
1. src/pipeline統合によるコード重複解消
2. 決め打ちディレクトリ戦略完全適用 
3. 原流処理互換性100%確保
4. エラー処理・検証システム強化
5. クロスプラットフォーム完全対応
"""
import gradio as gr
import os
import shutil
import time
import logging
import subprocess
import socket
import sys
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

# 🎯 決め打ちディレクトリ管理クラス（メインの施策）
from fixed_directory_manager import FixedDirectoryManager

# 🔧 統一パイプラインオーケストレーター（完全版）
from unified_pipeline_orchestrator import UnifiedPipelineOrchestrator

# 🔧 中間データクリーンアップツール
from cleanup_intermediate_data import IntermediateDataCleaner

# 🔧 src/pipeline統合クラス
from src.pipeline.unified_extract import UnifiedExtractor
from src.pipeline.unified_skinning import UnifiedSkinningOrchestrator

# 🔧 step_modules統合クラス
# Step1, Step2 imports will be done dynamically within functions to avoid conflicts
from src.pipeline.unified_merge import UnifiedMergeOrchestrator
from src.pipeline.unified_blender import UnifiedBlenderOrchestrator
from src.pipeline.pipeline_error_analyzer import PipelineErrorAnalyzer

# 🔧 step_modules統合クラス
from step_modules.step0_asset_preservation import Step0AssetPreservation

# 定数
PIPELINE_BASE_DIR = Path("/app/pipeline_work")
DEFAULT_MODEL_NAME = "default_model"

# --- グローバルロガー設定 ---
app_logger = logging.getLogger("UniRigApp")
if not app_logger.handlers:
    app_logger.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    app_logger.addHandler(console_handler)

# --- シンプルFileManagerクラス ---
# --- ユーティリティ関数 ---
def extract_model_name_from_file(file_path: str) -> str:
    """アップロードファイルからモデル名を抽出"""
    if not file_path:
        return DEFAULT_MODEL_NAME
    
    filename = Path(file_path).stem  # 拡張子を除いたファイル名
    # ファイルシステム互換性のためサニタイズ
    sanitized = filename.replace(" ", "_").replace(":", "_").replace("/", "_")
    return sanitized if sanitized else DEFAULT_MODEL_NAME

def execute_complete_pipeline(uploaded_file_info, gender: str, auto_cleanup: bool = False) -> tuple[bool, str]:
    """一気通貫パイプライン実行（詳細ログ版）"""
    if not uploaded_file_info:
        return False, "アップロードファイルが指定されていません"
    
    # ファイル名からモデル名を自動取得
    model_name = extract_model_name_from_file(uploaded_file_info.name)
    input_file_path = uploaded_file_info.name
    
    app_logger.info(f"一気通貫パイプライン開始: {model_name}")
    
    # 詳細ログの初期化
    detailed_logs = []
    detailed_logs.append(f"📊 パイプライン詳細ログ")
    detailed_logs.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    try:
        # 事前システム検証
        detailed_logs.append(f"🔍 システム検証開始...")
        error_analyzer = PipelineErrorAnalyzer(app_logger)
        system_check = error_analyzer.validate_system_requirements()
        if not system_check["valid"]:
            detailed_logs.append(f"[FAIL] システム検証失敗: {system_check['message']}")
            return False, "\n".join(detailed_logs)
        detailed_logs.append(f"[OK] システム検証完了")
        
        # ファイル保存 (決め打ちディレクトリ戦略)
        detailed_logs.append(f"[FILE] ディレクトリ構造作成中...")
        fdm = FixedDirectoryManager(PIPELINE_BASE_DIR, model_name, app_logger)
        fdm.create_all_directories()
        
        # ファイル保存
        original_filename = Path(input_file_path).name
        target_path = fdm.model_dir / original_filename
        file_size = Path(input_file_path).stat().st_size / (1024 * 1024)  # MB
        shutil.copy(input_file_path, target_path)
        app_logger.info(f"ファイル保存: {target_path}")
        detailed_logs.append(f"[OK] ファイル保存完了: {original_filename} ({file_size:.2f}MB)")
        detailed_logs.append(f"[DIR] 保存先: {target_path}")
        
        # Step 0: アセット保存
        detailed_logs.append(f"")
        detailed_logs.append(f"🔧 Step 0: アセット保存開始")
        detailed_logs.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        app_logger.info(f"Step 0 開始: {model_name}")
        success, step_logs = execute_step0(model_name, str(target_path))
        if not success:
            error_report = error_analyzer.diagnose_execution_error(
                Exception(step_logs), "step0"
            )
            detailed_logs.append(f"[FAIL] Step 0 失敗: {step_logs}")
            detailed_logs.append(f"💡 解決策: {error_report.get('suggested_solution', '不明')}")
            return False, "\n".join(detailed_logs)
        detailed_logs.append(f"[OK] Step 0 完了")
        detailed_logs.append(f"📋 詳細: {step_logs}")
        
        # Step 1: メッシュ抽出
        detailed_logs.append(f"")
        detailed_logs.append(f"🔧 Step 1: メッシュ抽出開始")
        detailed_logs.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        app_logger.info(f"Step 1 開始: {model_name}")
        success, step_logs = execute_step1_wrapper(model_name, str(target_path))
        if not success:
            error_report = error_analyzer.diagnose_execution_error(
                Exception(step_logs), "step1"
            )
            detailed_logs.append(f"[FAIL] Step 1 失敗: {step_logs}")
            detailed_logs.append(f"💡 解決策: {error_report.get('suggested_solution', '不明')}")
            return False, "\n".join(detailed_logs)
        detailed_logs.append(f"[OK] Step 1 完了")
        detailed_logs.append(f"📋 詳細: {step_logs}")
        
        # Step 2: スケルトン生成
        detailed_logs.append(f"")
        detailed_logs.append(f"🔧 Step 2: スケルトン生成開始")
        detailed_logs.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        app_logger.info(f"Step 2 開始: {model_name}")
        success, step_logs = execute_step2(model_name, gender)
        if not success:
            error_report = error_analyzer.diagnose_execution_error(
                Exception(step_logs), "step2"
            )
            detailed_logs.append(f"[FAIL] Step 2 失敗: {step_logs}")
            detailed_logs.append(f"💡 解決策: {error_report.get('suggested_solution', '不明')}")
            return False, "\n".join(detailed_logs)
        detailed_logs.append(f"[OK] Step 2 完了")
        detailed_logs.append(f"📋 詳細: {step_logs}")
        
        # Step 3: スキニング
        detailed_logs.append(f"")
        detailed_logs.append(f"🔧 Step 3: スキニング適用開始")
        detailed_logs.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        app_logger.info(f"Step 3 開始: {model_name}")
        success, step_logs = execute_step3(model_name)
        if not success:
            error_report = error_analyzer.diagnose_execution_error(
                Exception(step_logs), "step3"
            )
            detailed_logs.append(f"[FAIL] Step 3 失敗: {step_logs}")
            detailed_logs.append(f"💡 解決策: {error_report.get('suggested_solution', '不明')}")
            return False, "\n".join(detailed_logs)
        detailed_logs.append(f"[OK] Step 3 完了")
        detailed_logs.append(f"📋 詳細: {step_logs}")
        
        # Step 4: マージ
        detailed_logs.append(f"")
        detailed_logs.append(f"🔧 Step 4: マージ処理開始")
        detailed_logs.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        app_logger.info(f"Step 4 開始: {model_name}")
        success, step_logs = execute_step4(model_name)
        if not success:
            error_report = error_analyzer.diagnose_execution_error(
                Exception(step_logs), "step4"
            )
            detailed_logs.append(f"[FAIL] Step 4 失敗: {step_logs}")
            detailed_logs.append(f"💡 解決策: {error_report.get('suggested_solution', '不明')}")
            return False, "\n".join(detailed_logs)
        detailed_logs.append(f"[OK] Step 4 完了")
        detailed_logs.append(f"📋 詳細: {step_logs}")
        
        # Step 5: 最終統合
        detailed_logs.append(f"")
        detailed_logs.append(f"🔧 Step 5: 最終統合開始")
        detailed_logs.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        app_logger.info(f"Step 5 開始: {model_name}")
        success, step_logs = execute_step5(model_name)
        if not success:
            error_report = error_analyzer.diagnose_execution_error(
                Exception(step_logs), "step5"
            )
            detailed_logs.append(f"[FAIL] Step 5 失敗: {step_logs}")
            detailed_logs.append(f"💡 解決策: {error_report.get('suggested_solution', '不明')}")
            return False, "\n".join(detailed_logs)
        detailed_logs.append(f"[OK] Step 5 完了")
        detailed_logs.append(f"📋 詳細: {step_logs}")
        
        # 最終検証
        detailed_logs.append(f"")
        detailed_logs.append(f"🔍 最終検証開始")
        detailed_logs.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        final_check = fdm.get_pipeline_completion_status()
        completion_rate = sum(final_check.values()) / len(final_check) * 100
        
        detailed_logs.append(f"📊 完了率: {completion_rate:.1f}%")
        for step, completed in final_check.items():
            status = "[OK]" if completed else "[FAIL]"
            detailed_logs.append(f"   {step}: {status}")
            detailed_logs.append(f"  {status} {step}: {'完了' if completed else '未完了'}")
        
        final_output_files = fdm.get_expected_files('step5')
        final_output = final_output_files.get('final_output') or final_output_files.get('final_fbx')
        
        if final_output and final_output.exists():
            file_size = final_output.stat().st_size / (1024 * 1024)  # MB
            detailed_logs.append(f"[FILE] 最終出力: {final_output}")
            detailed_logs.append(f"[SIZE] ファイルサイズ: {file_size:.2f}MB")
            detailed_logs.append(f"[FORMAT] 形式: {final_output.suffix.upper()}")
        else:
            detailed_logs.append(f"[WARN] 最終出力ファイルが見つかりません")
        
        app_logger.info(f"一気通貫パイプライン完了: {model_name} ({completion_rate:.1f}%)")
        
        # 自動クリーンアップ実行（オプション）
        if auto_cleanup and completion_rate >= 100.0:
            detailed_logs.append(f"")
            detailed_logs.append(f"🧹 自動クリーンアップ開始")
            detailed_logs.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
            try:
                cleaner = IntermediateDataCleaner(logger_instance=app_logger)
                cleanup_success, cleanup_message = cleaner.cleanup_specific_model(model_name, create_backup=False)
                
                if cleanup_success:
                    detailed_logs.append(f"[OK] 自動クリーンアップ完了: {cleanup_message}")
                    app_logger.info(f"自動クリーンアップ完了: {model_name}")
                else:
                    detailed_logs.append(f"⚠️ 自動クリーンアップ失敗: {cleanup_message}")
                    app_logger.warning(f"自動クリーンアップ失敗: {model_name} - {cleanup_message}")
                    
            except Exception as cleanup_error:
                detailed_logs.append(f"[FAIL] 自動クリーンアップエラー: {str(cleanup_error)}")
                app_logger.error(f"自動クリーンアップエラー: {cleanup_error}")
        
        return True, "\n".join(detailed_logs)
        
    except Exception as e:
        error_report = error_analyzer.diagnose_execution_error(e, "pipeline")
        app_logger.error(f"一気通貫パイプラインエラー: {e}", exc_info=True)
        detailed_logs.append(f"")
        detailed_logs.append(f"[FAIL] 致命的エラー発生")
        detailed_logs.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        detailed_logs.append(f"🐛 エラー詳細: {str(e)}")
        detailed_logs.append(f"💡 解決策: {error_report.get('suggested_solution', '不明')}")
        return False, "\n".join(detailed_logs)

# --- ステップ実行関数群（src/pipeline統合版） ---
def execute_step0(model_name: str, input_file_path: str) -> tuple[bool, str]:
    """Step0: アセット保存実行（決め打ちディレクトリ戦略）"""
    try:
        fdm = FixedDirectoryManager(PIPELINE_BASE_DIR, model_name, app_logger)
        
        # 入力ファイル存在確認
        if not Path(input_file_path).exists():
            return False, f"入力ファイルが存在しません: {input_file_path}"
        
        step0 = Step0AssetPreservation(model_name, input_file_path, fdm.get_step_dir('step0'), app_logger)
        success, logs, files = step0.preserve_assets()
        
        # 期待出力ファイルの検証
        expected = fdm.get_expected_files("step0")
        created_files = []
        for key, path in expected.items():
            if path.exists():
                created_files.append(f"{key}: {path}")
        
        final_logs = logs + f"\n作成ファイル: {len(created_files)}個\n" + "\n".join(created_files)
        return success, final_logs
    except Exception as e:
        return False, f"Step0 エラー: {str(e)}"

def execute_step1_wrapper(model_name: str, input_file_path: str) -> tuple[bool, str]:
    """Step1ラッパー: step_modulesのexecute_step1を使用"""
    try:
        fdm = FixedDirectoryManager(PIPELINE_BASE_DIR, model_name, app_logger)
        
        # 事前検証
        error_analyzer = PipelineErrorAnalyzer(app_logger)
        validation_result = error_analyzer.validate_input_requirements("step1", {
            "input_file": input_file_path,
            "model_name": model_name
        })
        
        if not validation_result["valid"]:
            return False, f"Step1 事前検証失敗: {validation_result['message']}"
        
        # step_modules/step1_extract.pyを使用
        from step_modules.step1_extract import execute_step1
        
        output_dir = fdm.get_step_dir('step1')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        success, logs, output_files = execute_step1(
            input_file_path=Path(input_file_path),
            model_name=model_name,
            step_output_dir=output_dir,
            logger_instance=app_logger
        )
        
        # 期待出力確認
        expected = fdm.get_expected_files("step1")
        if expected["raw_data_npz"].exists():
            logs += f"\n[OK] 期待出力確認: {expected['raw_data_npz']} (存在)"
            file_size = expected["raw_data_npz"].stat().st_size
            logs += f"\n[OK] ファイルサイズ: {file_size:,} bytes"
        else:
            logs += f"\n[FAIL] 期待出力未作成: {expected['raw_data_npz']}"
        
        return success, logs
    except Exception as e:
        app_logger.error(f"Step1実行エラー: {e}", exc_info=True)
        return False, f"Step1 エラー: {str(e)}"

def execute_step2(model_name: str, gender: str) -> tuple[bool, str]:
    """Step2: スケルトン生成実行（メッシュ再抽出を含む）
    
    重要: メッシュ再抽出の知見に基づき、原流generate_skeleton.shと同じ処理順序を実行:
    1. スケルトン生成前に必ずメッシュを再抽出
    2. AI推論特化パラメータを使用（--require_suffix, --faces_target_count=4000, --time=8）
    3. 専用前処理（ar_post_process.py）を適用
    """
    try:
        fdm = FixedDirectoryManager(PIPELINE_BASE_DIR, model_name, app_logger)
        
        # 【重要】オリジナルファイルの検索（メッシュ再抽出のため）
        app_logger.info(f"Step2: メッシュ再抽出によるスケルトン生成開始 - {model_name}")
        
        # オリジナルファイルを検索
        original_file = fdm.find_original_model_file()
        if not original_file:
            return False, "Step2: オリジナルモデルファイルが見つかりません（メッシュ再抽出に必要）"
        
        app_logger.info(f"Step2: オリジナルファイル発見: {original_file}")
        
        # Step2専用出力ディレクトリ
        output_dir = fdm.get_step_dir('step2')
        
        # step_modules/step2_skeletonを使用（最新版）
        from step_modules.step2_skeleton import Step2Skeleton
        
        step2_module = Step2Skeleton(output_dir, app_logger)
        
        # 【重要】メッシュ再抽出を含むスケルトン生成実行
        success, skeleton_logs, output_files = step2_module.generate_skeleton(
            original_file=original_file,
            model_name=model_name,
            gender=gender
        )
        
        # 期待出力確認
        expected = fdm.get_expected_files("step2")
        output_check = []
        for key, path in expected.items():
            if path.exists():
                output_check.append(f"✓ {key}: {path}")
            else:
                output_check.append(f"✗ {key}: {path}")
        
        # 詳細ログの統合
        combined_logs = f"""Step2完了ログ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【スケルトン生成＋メッシュ再抽出フェーズ】
{skeleton_logs}

【出力ファイル検証】
{chr(10).join(output_check)}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        
        return success, combined_logs
        
    except Exception as e:
        app_logger.error(f"Step2実行エラー: {e}", exc_info=True)
        return False, f"Step2 エラー: {str(e)}"


def execute_mesh_reextraction_for_skeleton(original_file: Path, model_name: str) -> tuple[bool, str]:
    """
    スケルトン生成専用のメッシュ再抽出
    
    重要: 原流generate_skeleton.shと完全に同じパラメータを使用
    - --require_suffix: 厳密な命名規則適用
    - --faces_target_count=4000: AI推論最適化された面数
    - --time=8: タイムスタンプ付与
    - --post_process_script=post_process/ar_post_process.py: 専用前処理
    """
    app_logger.info(f"スケルトン生成用メッシュ再抽出開始: {original_file}")
    
    try:
        # 出力ディレクトリ（dataset_inference_clean/）
        output_dir = Path("/app/dataset_inference_clean")
        
        # 原流generate_skeleton.shと同じパラメータでメッシュ抽出実行
        cmd = [
            "python", "-m", "src.data.extract",
            "--input", str(original_file),
            "--output", str(output_dir),
            "--name", model_name,
            "--require_suffix",           # 厳密な命名規則
            "--faces_target_count", "4000",  # AI推論最適化
            "--time", "8",                # タイムスタンプ
            "--post_process_script", "post_process/ar_post_process.py"  # 専用前処理
        ]
        
        app_logger.info(f"メッシュ再抽出コマンド: {' '.join(cmd)}")
        
        # コマンド実行
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd="/app",
            timeout=300  # 5分タイムアウト
        )
        
        if result.returncode == 0:
            # 再抽出されたファイルの確認
            reextracted_mesh = output_dir / "raw_data.npz"
            if reextracted_mesh.exists():
                file_size = reextracted_mesh.stat().st_size
                success_log = f"""[OK] スケルトン生成用メッシュ再抽出成功
[FILE] 出力ファイル: {reextracted_mesh}
📊 ファイルサイズ: {file_size:,} bytes
🎯 使用パラメータ: 原流generate_skeleton.sh互換
   - require_suffix: 有効
   - faces_target_count: 4000
   - time: 8
   - post_process_script: ar_post_process.py

📝 標準出力:
{result.stdout}"""
                app_logger.info("スケルトン生成用メッシュ再抽出完了")
                return True, success_log
            else:
                return False, f"再抽出ファイル生成失敗: raw_data.npzが見つかりません"
        else:
            error_log = f"""[FAIL] スケルトン生成用メッシュ再抽出失敗
🚨 終了コード: {result.returncode}
📝 標準エラー:
{result.stderr}

📝 標準出力:
{result.stdout}"""
            return False, error_log
            
    except subprocess.TimeoutExpired:
        return False, "メッシュ再抽出がタイムアウトしました（5分制限）"
    except Exception as e:
        return False, f"メッシュ再抽出エラー: {str(e)}"

def execute_step3(model_name: str) -> tuple[bool, str]:
    """Step3: スキニング実行（原流互換版）
    
    重要: 原流generate_skin.shと同じ処理順序:
    1. スキニング生成前に必ずメッシュを再抽出
    2. Step2の出力 (predict_skeleton.npz) と併用
    3. dataset_inference_clean/ ディレクトリで処理実行
    """
    try:
        fdm = FixedDirectoryManager(PIPELINE_BASE_DIR, model_name, app_logger)
        
        # 【重要】オリジナルファイルの検索（スキニング用メッシュ再抽出のため）
        # Note: 詳細ログはstep_modules側で出力される
        
        # オリジナルファイルを検索
        original_file = fdm.find_original_model_file()
        if not original_file:
            return False, "Step3: オリジナルモデルファイルが見つかりません（スキニング用メッシュ再抽出に必要）"
        
        app_logger.info(f"Step3: オリジナルファイル発見: {original_file}")
        
        # Step2の出力ファイル検索
        step2_files = fdm.get_expected_files("step2")
        skeleton_npz = step2_files["skeleton_npz"]
        skeleton_fbx = step2_files["skeleton_fbx"]
        
        if not skeleton_npz.exists():
            return False, f"Step3: predict_skeleton.npzが見つかりません: {skeleton_npz}"
        if not skeleton_fbx.exists():
            return False, f"Step3: スケルトンFBXが見つかりません: {skeleton_fbx}"
        
        # Step3専用出力ディレクトリ
        output_dir = fdm.get_step_dir('step3')
        
        # step_modules/step3_skinning_unirigを使用（最新版）
        from step_modules.step3_skinning_unirig import Step3Skinning
        
        step3_module = Step3Skinning(output_dir)
        
        # Step2の出力ファイル辞書を準備
        skeleton_files = {
            "skeleton_npz": str(skeleton_npz),
            "skeleton_fbx": str(skeleton_fbx)
        }
        
        # 【重要】オリジナルファイルとStep2出力を使用してスキニング実行
        # この内部で原流と同様にメッシュ再抽出が実行される
        success, logs, output_files = step3_module.apply_skinning(
            model_name=model_name,
            original_file=original_file,  # オリジナルファイル
            skeleton_files=skeleton_files
        )
        
        # 期待出力確認
        expected = fdm.get_expected_files("step3")
        if expected["skinned_fbx"].exists():
            logs += f"\n[OK] 期待出力確認: {expected['skinned_fbx']} (存在)\n"
        else:
            logs += f"\n⚠️ 期待出力未作成: {expected['skinned_fbx']}\n"
        
        return success, logs
    except Exception as e:
        app_logger.error(f"Step3実行エラー: {e}", exc_info=True)
        return False, f"Step3 エラー: {str(e)}"

def execute_step4(model_name: str) -> tuple[bool, str]:
    """Step4: 3つのデータソース統合マージ（KDTreeマッチング技術）
    
    最新知見による本質的定義:
    - オリジナルメッシュ（ユーザーアップロード）+ AIスキニング（Step3出力）の統合
    - Step3出力（skinned_fbx）にスキンウェイト情報が含まれているため、これをsourceに使用
    - KDTree最近傍マッチングによる頂点数差異吸収システム
    - オリジナルメッシュをtargetとして、スキンウェイト情報を正確に転写
    """
    try:
        fdm = FixedDirectoryManager(PIPELINE_BASE_DIR, model_name, app_logger)
        
        # 入力検証（3つのデータソース確認）
        valid, message, available_files = fdm.validate_step_inputs("step4")
        if not valid:
            return False, f"Step4 入力検証失敗（3つのデータソース統合に必要）: {message}"
        
        # 【重要修正】データソース1: AIスキニング（Step3出力）- source引数として使用
        # Step3で生成されたskinned_fbxには正しいスキンウェイト情報が含まれている
        skinned_fbx = available_files.get("skinned_fbx")
        if not skinned_fbx or not Path(skinned_fbx).exists():
            return False, "Step4 エラー: スキニング済みFBX（Step3出力）が見つかりません（スキンウェイト転写に必要）"
        
        # データソース2: オリジナルメッシュ（ユーザーアップロード）- target引数として使用
        # 重要: model_dirに保存されているオリジナルファイルを取得
        original_files = list(fdm.model_dir.glob("*"))
        original_file = None
        for f in original_files:
            if f.suffix.lower() in ['.glb', '.fbx', '.obj', '.dae', '.gltf']:
                original_file = str(f)
                break
        
        if not original_file:
            return False, "Step4 エラー: オリジナルメッシュファイルが見つかりません（3つのデータソース統合に必要）"
        
        app_logger.info(f"Step4: スキンウェイト転写処理 - source: {skinned_fbx}, target: {original_file}")
        
        # unified_merge使用（3つのデータソース統合処理）
        merge_orchestrator = UnifiedMergeOrchestrator(app_logger)
        output_dir = fdm.get_step_dir('step4')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 【修正】重要な技術的発見: skinned_fbx（Step3出力）をsourceに使用
        success, logs = merge_orchestrator.merge_skeleton_skinning_unified(
            model_name=model_name,
            skinned_fbx=str(skinned_fbx),   # source: AIスキニング（Step3出力・スキンウェイト付き）
            original_file=original_file,    # target: オリジナルメッシュ（ユーザーアップロード）
            output_dir=str(output_dir)
        )
        
        # 期待出力確認
        expected = fdm.get_expected_files("step4")
        if expected["merged_fbx"].exists():
            logs += f"\n期待出力確認: {expected['merged_fbx']} (存在)"
        else:
            logs += f"\n⚠️ 期待出力未作成: {expected['merged_fbx']}"
        
        return success, logs
    except Exception as e:
        app_logger.error(f"Step4実行エラー: {e}", exc_info=True)
        return False, f"Step4 エラー: {str(e)}"

def execute_step5(model_name: str) -> tuple[bool, str]:
    """Step5: リギング移植対応最終統合実行"""
    try:
        fdm = FixedDirectoryManager(PIPELINE_BASE_DIR, model_name, app_logger)
        
        # 入力検証
        valid, message, available_files = fdm.validate_step_inputs("step5")
        if not valid:
            return False, f"Step5 入力検証失敗: {message}"
        
        merged_fbx = available_files["merged_fbx"]
        original_file = available_files.get("original_file")
        
        if not original_file:
            return False, "Step5: オリジナルファイルが見つかりません"
        
        # Step5Blenderバージョンを使用（リギング移植対応）
        from step_modules.step5_blender_integration import Step5BlenderIntegration
        output_dir = fdm.get_step_dir('step5')
        
        step5 = Step5BlenderIntegration(output_dir)
        success, logs, output_files = step5.integrate_final_output(
            model_name=model_name,
            original_file=Path(original_file),    # アセット情報源（テクスチャ・UV・マテリアル）
            rigged_file=Path(merged_fbx)          # リギング情報源（ボーン・スキン）
        )
        
        # 出力ファイル確認
        if success and output_files.get("final_output"):
            final_output = Path(output_files["final_output"])
            if final_output.exists():
                logs += f"\n✅ 最終出力確認: {final_output} (存在、{output_files.get('size_mb', 0):.2f} MB)"
            else:
                logs += f"\n⚠️ 最終出力未作成: {final_output}"
                success = False
        
        return success, logs
    except Exception as e:
        app_logger.error(f"Step5実行エラー: {e}", exc_info=True)
        return False, f"Step5 エラー: {str(e)}"

# --- Gradio UI（改良版） ---
def create_simple_ui():
    """改良されたGradio UI作成（src/pipeline統合版）"""
    
    with gr.Blocks(title="UniRig WebUI - 完全版") as demo:
        gr.Markdown("# 🎯 UniRig WebUI - 完全統合版")
        gr.Markdown("**src/pipeline統合・決め打ちディレクトリ戦略完全適用・エラー予防システム搭載**")
        
        with gr.Row():
            with gr.Column():
                # アップロード
                uploaded_file = gr.File(
                    label="3Dモデルファイル (.glb, .fbx, .obj, .vrm)",
                    file_types=[".glb", ".fbx", ".obj", ".vrm", ".dae", ".gltf"]
                )
                model_name_input = gr.Textbox(
                    label="モデル名 (自動取得)", 
                    value="", 
                    placeholder="アップロード時に自動設定", 
                    interactive=False
                )
                gender_input = gr.Radio(
                    ["neutral", "male", "female"], 
                    label="性別", 
                    value="neutral"
                )
                
                # パイプライン完了後の自動クリーンアップオプション
                auto_cleanup_checkbox = gr.Checkbox(
                    label="🧹 パイプライン完了後に中間データを自動削除",
                    value=False,
                    info="最終出力作成後、中間データを自動的に削除してディスク容量を節約"
                )
                
                # 一気通貫処理ボタン
                with gr.Row():
                    complete_pipeline_btn = gr.Button(
                        "🚀 一気通貫実行 (全ステップ自動)", 
                        variant="primary", 
                        size="lg"
                    )
                
                # ダウンロードセクション
                gr.Markdown("### 📥 結果ダウンロード")
                download_btn = gr.Button("📥 リギング済モデルダウンロード", variant="secondary")
                download_file = gr.File(
                    label="ダウンロードファイル", 
                    visible=True,
                    interactive=False,  # ダウンロード専用
                    file_count="single"  # 単一ファイル
                )
                
                gr.Markdown("---")
                gr.Markdown("### 🔧 個別ステップ実行（デバッグ用）")
                
                # ステップ実行ボタン
                with gr.Row():
                    step0_btn = gr.Button("Step 0: アセット保存", size="sm")
                    step1_btn = gr.Button("Step 1: メッシュ抽出", size="sm")
                    step2_btn = gr.Button("Step 2: スケルトン生成", size="sm")
                with gr.Row():
                    step3_btn = gr.Button("Step 3: スキニング", size="sm")
                    step4_btn = gr.Button("Step 4: 3つのデータソース統合マージ", size="sm")
                    step5_btn = gr.Button("Step 5: 最終統合", size="sm")
                
                with gr.Row():
                    reset_btn = gr.Button("🔄 リセット", variant="secondary", size="sm")
                    refresh_btn = gr.Button("📊 状態更新", variant="secondary", size="sm")
                
                # 中間データクリーンアップセクション
                gr.Markdown("---")
                gr.Markdown("### 🧹 中間データ管理")
                
                with gr.Row():
                    analyze_data_btn = gr.Button("📊 データ分析", variant="secondary", size="sm")
                    cleanup_model_btn = gr.Button("🧹 このモデルのデータ削除", variant="secondary", size="sm")
                    cleanup_all_btn = gr.Button("🗑️ 全中間データ削除", variant="stop", size="sm")
                
                with gr.Row():
                    backup_checkbox = gr.Checkbox(
                        label="削除前にバックアップを作成", 
                        value=False
                    )
                
            with gr.Column():
                # 状態表示
                status_display = gr.Textbox(
                    label="📊 パイプライン状態", 
                    lines=15, 
                    interactive=False,
                    placeholder="モデルをアップロードして状態更新ボタンを押してください",
                    max_lines=20
                )
                log_display = gr.Textbox(
                    label="📋 実行ログ", 
                    lines=15, 
                    interactive=False,
                    placeholder="実行ログがここに表示されます",
                    max_lines=25
                )
        
        # --- イベントハンドラー ---
        def handle_upload(uploaded_file_info):
            if not uploaded_file_info:
                return "", "アップロードファイルが指定されていません"
            
            try:
                # ファイル名からモデル名を自動取得
                model_name = extract_model_name_from_file(uploaded_file_info.name)
                fdm = FixedDirectoryManager(PIPELINE_BASE_DIR, model_name, app_logger)
                fdm.create_all_directories()
                
                # ファイル保存
                original_filename = Path(uploaded_file_info.name).name
                target_path = fdm.model_dir / original_filename
                shutil.copy(uploaded_file_info.name, target_path)
                
                # ファイル情報取得
                file_size = target_path.stat().st_size / (1024 * 1024)  # MB
                
                return model_name, f"[OK] アップロード完了\\n[FILE] ファイル: {original_filename}\\n[SIZE] サイズ: {file_size:.2f} MB\\n[TAG] モデル名: {model_name}\\n[DIR] 保存先: {target_path}"
            except Exception as e:
                return "", f"[FAIL] アップロードエラー: {str(e)}"
        
        def get_status(model_name):
            """詳細なパイプライン状態表示"""
            if not model_name:
                return "⚠️ モデル名が指定されていません"
            
            try:
                fdm = FixedDirectoryManager(PIPELINE_BASE_DIR, model_name, app_logger)
                
                # 状態詳細の構築
                status_lines = []
                status_lines.append(f"📊 UniRig パイプライン状態レポート")
                status_lines.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                status_lines.append(f"[TAG] モデル名: {model_name}")
                status_lines.append(f"[FILE] 作業ディレクトリ: {fdm.model_dir}")
                status_lines.append(f"⏰ 更新時刻: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                status_lines.append(f"")
                
                # 完了率計算（ブール値対応）
                completion_status = fdm.get_pipeline_completion_status()
                completed_steps = sum(1 for status in completion_status.values() if status)
                total_steps = len(completion_status)
                completion_rate = completed_steps / total_steps * 100
                
                status_lines.append(f"🏁 全体進捗: {completed_steps}/{total_steps} ステップ完了 ({completion_rate:.1f}%)")
                status_lines.append(f"")
                
                # 各ステップの詳細状態
                step_details = {
                    'step0': '🔧 Step 0: アセット保存',
                    'step1': '🔧 Step 1: メッシュ抽出', 
                    'step2': '🔧 Step 2: スケルトン生成',
                    'step3': '🔧 Step 3: スキニング適用',
                    'step4': '🔧 Step 4: 3つのデータソース統合マージ（KDTree技術）',
                    'step5': '🔧 Step 5: 最終統合'
                }
                
                status_lines.append(f"� ステップ別詳細状態:")
                status_lines.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                
                for step_id, step_name in step_details.items():
                    is_completed = completion_status.get(step_id, False)
                    status_icon = "[OK]" if is_completed else "[WAIT]"
                    status_text = "完了" if is_completed else "未実行"
                    
                    status_lines.append(f"{status_icon} {step_name}: {status_text}")
                    
                    # 期待ファイルの存在確認
                    try:
                        expected_files = fdm.get_expected_files(step_id)
                        for file_key, file_path in expected_files.items():
                            if file_path.exists():
                                file_size = file_path.stat().st_size / (1024 * 1024)  # MB
                                status_lines.append(f"    [FILE] {file_key}: {file_path.name} ({file_size:.2f}MB)")
                            else:
                                status_lines.append(f"    [FAIL] {file_key}: 未作成")
                    except Exception as e:
                        status_lines.append(f"    ⚠️ ファイル状態確認エラー: {str(e)}")
                    
                    status_lines.append(f"")
                
                # ディスク使用量
                if fdm.model_dir.exists():
                    total_size = sum(f.stat().st_size for f in fdm.model_dir.rglob('*') if f.is_file())
                    total_size_mb = total_size / (1024 * 1024)
                    status_lines.append(f"💾 総ディスク使用量: {total_size_mb:.2f}MB")
                
                # 最終出力の状態（動的形式対応）
                step5_files = fdm.get_expected_files("step5")
                final_output = step5_files.get("final_output") or step5_files.get("final_fbx")
                if final_output and final_output.exists():
                    final_size = final_output.stat().st_size / (1024 * 1024)
                    status_lines.append(f"🎯 最終出力: {final_output.name} ({final_size:.2f}MB)")
                else:
                    status_lines.append(f"🎯 最終出力: 未生成")
                
                return "\n".join(status_lines)
                
            except Exception as e:
                return f"[FAIL] 状態取得エラー: {str(e)}\n詳細: {type(e).__name__}"
        
        def handle_download(model_name):
            """
            Gradio 5.31.0対応のダウンロード処理
            直接ファイルパスを返すシンプルなアプローチ
            """
            if not model_name:
                return None, "⚠️ モデル名が指定されていません"
            
            try:
                fdm = FixedDirectoryManager(PIPELINE_BASE_DIR, model_name, app_logger)
                
                # 動的形式対応: find_file_with_dynamic_extensionを使用
                final_output = fdm.find_file_with_dynamic_extension("step5", "final_output")
                
                if final_output and final_output.exists():
                    # Gradio 5.31.0: str型パスを返す（必須）
                    return str(final_output), f"[OK] ダウンロード準備完了: {final_output.name}"
                else:
                    return None, f"[FAIL] 最終出力ファイルが見つかりません"
            except Exception as e:
                app_logger.error(f"ダウンロードエラー: {e}")
                return None, f"[FAIL] ダウンロードエラー: {str(e)}"
        def handle_complete_pipeline(uploaded_file_info, gender, auto_cleanup):
            """一気通貫処理ハンドラー（詳細ログ表示版）"""
            if not uploaded_file_info:
                return "[FAIL] アップロードファイルが指定されていません", None, ""
            
            # 開始ログ
            model_name = extract_model_name_from_file(uploaded_file_info.name)
            start_log = f"""🚀 一気通貫パイプライン開始
[FILE] モデル名: {model_name}
[DIR] ファイル: {uploaded_file_info.name}
👤 性別設定: {gender}
🧹 自動クリーンアップ: {'有効' if auto_cleanup else '無効'}
⏰ 開始時刻: {time.strftime('%Y-%m-%d %H:%M:%S')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            
            success, logs = execute_complete_pipeline(uploaded_file_info, gender, auto_cleanup)
            status_icon = "[OK]" if success else "[FAIL]"
            
            # 終了ログ
            end_log = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ 終了時刻: {time.strftime('%Y-%m-%d %H:%M:%S')}
🏁 最終結果: {status_icon} {'成功' if success else '失敗'}
"""
            
            # パイプライン成功時は自動でダウンロードファイルを設定
            download_file_path = None
            if success:
                try:
                    fdm = FixedDirectoryManager(PIPELINE_BASE_DIR, model_name, app_logger)
                    final_output = fdm.find_file_with_dynamic_extension("step5", "final_output")
                    if final_output and final_output.exists():
                        # Gradio 5.31.0: str型パスを設定（必須）
                        download_file_path = str(final_output)
                except Exception as e:
                    app_logger.error(f"ダウンロードファイル設定エラー: {e}")
            
            return f"{start_log}{logs}{end_log}", download_file_path, model_name

        def handle_cleanup_intermediate_data(model_name, create_backup=False):
            """中間データクリーンアップハンドラー"""
            try:
                cleaner = IntermediateDataCleaner(logger_instance=app_logger)
                
                if model_name:
                    # 特定のモデルのみクリーンアップ
                    success, message = cleaner.cleanup_specific_model(model_name, create_backup)
                else:
                    # 全ての中間データをクリーンアップ
                    success, message = cleaner.cleanup_intermediate_data(create_backup)
                
                status_icon = "[OK]" if success else "[FAIL]"
                return f"{status_icon} {message}"
                
            except Exception as e:
                app_logger.error(f"クリーンアップエラー: {e}", exc_info=True)
                return f"[FAIL] クリーンアップエラー: {str(e)}"
        
        def handle_analyze_intermediate_data():
            """中間データ分析ハンドラー"""
            try:
                cleaner = IntermediateDataCleaner(logger_instance=app_logger)
                analysis = cleaner.analyze_intermediate_data()
                
                if not analysis["pipeline_dir_exists"]:
                    return "[OK] 中間データディレクトリは存在しません"
                
                analysis_lines = []
                analysis_lines.append("🔍 中間データ分析結果")
                analysis_lines.append("=" * 50)
                analysis_lines.append(f"[DIR] ディレクトリ: {PIPELINE_BASE_DIR}")
                analysis_lines.append(f"[SIZE] 総サイズ: {analysis['total_size_mb']:.2f}MB")
                analysis_lines.append(f"📄 ファイル数: {analysis['file_count']:,}個")
                analysis_lines.append(f"[FILE] モデル数: {len(analysis['model_directories'])}個")
                
                if analysis["model_directories"]:
                    analysis_lines.append("")
                    analysis_lines.append("📋 モデル一覧:")
                    for model in analysis["model_directories"]:
                        steps = analysis["step_directories"].get(model["name"], [])
                        analysis_lines.append(f"  • {model['name']} (ステップ: {', '.join(steps)})")
                        analysis_lines.append(f"    最終更新: {model['last_modified']}")
                
                return "\n".join(analysis_lines)
                
            except Exception as e:
                app_logger.error(f"分析エラー: {e}", exc_info=True)
                return f"[FAIL] 分析エラー: {str(e)}"
        
        def handle_step0(uploaded_file_info, model_name):
            """Step0実行ハンドラー"""
            if not uploaded_file_info or not model_name:
                return "[FAIL] アップロードファイルまたはモデル名が指定されていません"
            
            start_log = f"""🔧 Step 0: アセット保存開始
[FILE] モデル名: {model_name}
[DIR] ファイル: {uploaded_file_info.name}
⏰ 開始時刻: {time.strftime('%Y-%m-%d %H:%M:%S')}

"""
            success, logs = execute_step0(model_name, uploaded_file_info.name)
            status_icon = "[OK]" if success else "[FAIL]"
            
            return f"{start_log}{logs}\n\n🏁 Step 0 結果: {status_icon} {'成功' if success else '失敗'}"
        
        def handle_step1(uploaded_file_info, model_name):
            """Step1実行ハンドラー"""
            if not uploaded_file_info or not model_name:
                return "[FAIL] アップロードファイルまたはモデル名が指定されていません"
            
            start_log = f"""🔧 Step 1: メッシュ抽出開始
[FILE] モデル名: {model_name}
[DIR] ファイル: {uploaded_file_info.name}
⏰ 開始時刻: {time.strftime('%Y-%m-%d %H:%M:%S')}

"""
            success, logs = execute_step1_wrapper(model_name, uploaded_file_info.name)
            status_icon = "[OK]" if success else "[FAIL]"
            
            return f"{start_log}{logs}\n\n🏁 Step 1 結果: {status_icon} {'成功' if success else '失敗'}"
        
        def handle_step2(model_name, gender):
            """Step2実行ハンドラー"""
            if not model_name:
                return "[FAIL] モデル名が指定されていません"
            
            start_log = f"""🔧 Step 2: スケルトン生成開始
[FILE] モデル名: {model_name}
👤 性別設定: {gender}
⏰ 開始時刻: {time.strftime('%Y-%m-%d %H:%M:%S')}

"""
            success, logs = execute_step2(model_name, gender)
            status_icon = "[OK]" if success else "[FAIL]"
            
            return f"{start_log}{logs}\n\n🏁 Step 2 結果: {status_icon} {'成功' if success else '失敗'}"
        
        def handle_step3(model_name):
            """Step3実行ハンドラー"""
            if not model_name:
                return "[FAIL] モデル名が指定されていません"
            
            start_log = f"""🔧 Step 3: スキニング適用開始
[FILE] モデル名: {model_name}
⏰ 開始時刻: {time.strftime('%Y-%m-%d %H:%M:%S')}

"""
            success, logs = execute_step3(model_name)
            status_icon = "[OK]" if success else "[FAIL]"
            
            return f"{start_log}{logs}\n\n🏁 Step 3 結果: {status_icon} {'成功' if success else '失敗'}"
        
        def handle_step4(model_name):
            """Step4実行ハンドラー - 3つのデータソース統合マージ"""
            if not model_name:
                return "[FAIL] モデル名が指定されていません"
            
            start_log = f"""🔧 Step 4: マージ処理開始
[FILE] モデル名: {model_name}
⏰ 開始時刻: {time.strftime('%Y-%m-%d %H:%M:%S')}

"""
            success, logs = execute_step4(model_name)
            status_icon = "[OK]" if success else "[FAIL]"
            
            return f"{start_log}{logs}\n\n🏁 Step 4 結果: {status_icon} {'成功' if success else '失敗'}"
        
        def handle_step5(uploaded_file_info, model_name):
            """Step5実行ハンドラー"""
            if not uploaded_file_info or not model_name:
                return "[FAIL] アップロードファイルまたはモデル名が指定されていません"
            
            start_log = f"""🔧 Step 5: 最終統合開始
[FILE] モデル名: {model_name}
[DIR] ファイル: {uploaded_file_info.name}
⏰ 開始時刻: {time.strftime('%Y-%m-%d %H:%M:%S')}

"""
            success, logs = execute_step5(model_name)
            status_icon = "[OK]" if success else "[FAIL]"
            
            return f"{start_log}{logs}\n\n🏁 Step 5 結果: {status_icon} {'成功' if success else '失敗'}"
        
        def handle_reset(model_name):
            """リセット実行ハンドラー"""
            if not model_name:
                return "[FAIL] モデル名が指定されていません"
            try:
                fdm = FixedDirectoryManager(PIPELINE_BASE_DIR, model_name, app_logger)
                if fdm.model_dir.exists():
                    shutil.rmtree(fdm.model_dir)
                    fdm.create_all_directories()
                return f"🔄 パイプライン状態をリセットしました: {model_name}"
            except Exception as e:
                return f"[FAIL] リセットエラー: {str(e)}"
        
        # イベント接続
        uploaded_file.change(handle_upload, [uploaded_file], [model_name_input, log_display])
        complete_pipeline_btn.click(handle_complete_pipeline, [uploaded_file, gender_input, auto_cleanup_checkbox], [log_display, download_file, model_name_input])
        download_btn.click(handle_download, [model_name_input], [download_file, log_display])
        
        step0_btn.click(handle_step0, [uploaded_file, model_name_input], log_display)
        step1_btn.click(handle_step1, [uploaded_file, model_name_input], log_display)
        step2_btn.click(handle_step2, [model_name_input, gender_input], log_display)
        step3_btn.click(handle_step3, [model_name_input], log_display)
        step4_btn.click(handle_step4, [model_name_input], log_display)
        step5_btn.click(handle_step5, [uploaded_file, model_name_input], log_display)
        
        reset_btn.click(handle_reset, [model_name_input], log_display)
        refresh_btn.click(get_status, [model_name_input], status_display)
        
        # 中間データ管理ボタンのイベント接続
        analyze_data_btn.click(
            lambda: handle_analyze_intermediate_data(),
            [],
            log_display
        )
        cleanup_model_btn.click(
            lambda model_name, create_backup: handle_cleanup_intermediate_data(model_name, create_backup) if model_name else "⚠️ モデル名が指定されていません",
            [model_name_input, backup_checkbox],
            log_display
        )
        cleanup_all_btn.click(
            lambda create_backup: handle_cleanup_intermediate_data(None, create_backup),
            [backup_checkbox],
            log_display
        )
    
    return demo

# メイン実行部分
if __name__ == "__main__":
    try:
        print("🚀 UniRig WebUI を開始しています...")
        print("📁 作業ディレクトリ:", os.getcwd())
        print("🐍 Python実行環境:", sys.executable)
        print("📦 Python版本:", sys.version.split()[0])
        
        # Gradioアプリケーションを作成
        app = create_simple_ui()
        
        # アプリケーションを起動
        print("🌐 WebUIを起動中...")
        
        # ポート設定（環境変数対応）
        preferred_port = int(os.getenv("UNIRIG_PORT", "7860"))
        
        # 利用可能なポートを検索
        import socket
        def find_available_port(start_port=preferred_port, end_port=preferred_port+10):
            for port in range(start_port, end_port + 1):
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.bind(('localhost', port))
                        return port
                except OSError:
                    continue
            return None
        
        # ブラウザ起動制御（環境変数で制御可能）
        auto_browser = os.getenv("UNIRIG_AUTO_BROWSER", "true").lower() == "true"
        
        # 利用可能なポートを探す
        available_port = find_available_port()
        if available_port is None:
            print(f"❌ 利用可能なポートが見つかりません ({preferred_port}-{preferred_port+10})")
            sys.exit(1)
        
        print(f"📡 使用ポート: {available_port}")
        print(f"🌐 アクセスURL: http://localhost:{available_port}")
        
        if auto_browser:
            print("🚀 ブラウザが自動的に開きます...")
        else:
            print("📌 ブラウザ自動起動は無効 (UNIRIG_AUTO_BROWSER=false)")
            print("🔗 手動でブラウザからアクセスしてください")
        
        app.launch(
            server_name="0.0.0.0",  # 全てのIPアドレスでアクセス可能
            server_port=available_port,  # 利用可能なポート
            share=False,            # 公開リンクは無効（ローカル使用）
            inbrowser=auto_browser, # 環境変数で制御可能なブラウザ自動起動
            show_error=True,        # エラーを表示
            debug=False             # デバッグモードは無効
        )
        
    except Exception as e:
        print(f"❌ アプリケーション起動エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
