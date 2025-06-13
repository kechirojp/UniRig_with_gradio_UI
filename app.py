"""
UniRig MVP - Internal Microservice Frontend Application
内部マイクロサービス対応フロントエンド - UI とデータ受け渡しのみ

基本理念:
1. UIとファイル管理のみ（処理ロジックは内部モジュール）
2. 各ステップは独立した実行モジュールとして分離
3. シンプルなデータ受け渡しインターフェース
4. 最小限のコードで最大の効果

アーキテクチャ:
app.py (UI + データ受け渡し)
├── step_modules.step1_extract (独立実行機能) - メッシュ抽出
├── step_modules.step2_skeleton (独立実行機能) - スケルトン生成  
├── step_modules.step3_skinning (独立実行機能) - スキニング適用
└── step_modules.step4_texture (独立実行機能) - テクスチャ統合
"""
import gradio as gr
import os
import shutil
import json
import time
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import subprocess
import socket
import sys

# ステップモジュールのインポート
from step_modules.step0_asset_preservation import Step0FileTransfer
from step_modules.step1_extract import Step1Extract
from step_modules.step2_skeleton import Step2Skeleton
from step_modules.step3_skinning import Step3Skinning # 標準的なスキニング
from step_modules.step3_skinning_unirig import Step3UniRigSkinning # UniRig独自のスキニング
from step_modules.step4_texture import Step4Texture
from step_modules.step4_merge import Step4Merge  # 新Step4: マージ特化
from step_modules.step5_blender_integration import Step5BlenderIntegration  # 新Step5

# 定数
PIPELINE_BASE_DIR = Path("/app/pipeline_work")
MAX_LOG_FILES = 10
MAX_LOG_SIZE_MB = 5

# --- グローバル設定 ---
PIPELINE_DIR = Path("/app/pipeline_work/")
MAX_FILENAME_LENGTH = 50 # UI表示用ファイル名の最大長
DEFAULT_MODEL_NAME = "default_model"

STEP_SUBDIR_NAMES = {
    "step0_asset_preservation": "00_asset_preservation",
    "step1_extract": "01_extracted_mesh",
    "step2_skeleton": "02_skeleton",
    "step3_skinning": "03_skinning",
    "step4_merge": "04_merge",
    "step5_blender_integration": "05_blender_integration",  # 新追加
    "output": "output", # Final output if distinct
}

# --- ロガー設定 ---
# グローバルロガーの初期化
app_logger = logging.getLogger("UniRigApp")
if not app_logger.handlers:
    app_logger.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO) # コンソールはINFO以上
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    app_logger.addHandler(console_handler)

# --- FileManagerクラス ---
class FileManager:
    def __init__(self, model_name: str):
        if not model_name:
            app_logger.warning("FileManager初期化: model_nameが空です。デフォルト名を使用します。")
            model_name = DEFAULT_MODEL_NAME
        self.model_name = self._sanitize_model_name(model_name)
        self.base_model_dir = PIPELINE_DIR / self.model_name
        self.state_file_path = self.base_model_dir / "pipeline_state.json"
        
        self.base_model_dir.mkdir(parents=True, exist_ok=True)
        self._setup_model_specific_logging()

    def _sanitize_model_name(self, model_name: str) -> str:
        """モデル名をサニタイズ（ファイルシステム互換にする）"""
        # ここではシンプルにアンダースコアに置換する例
        return model_name.replace(" ", "_").replace(":", "_").replace("/", "_")

    def _setup_model_specific_logging(self):
        # app_logger にモデル固有のファイルハンドラを追加
        # 既存のハンドラをすべて削除してから追加する（重複防止）
        # for handler in app_logger.handlers[:]:
        #     if isinstance(handler, logging.FileHandler) and self.model_name in handler.baseFilename:
        #         app_logger.removeHandler(handler)
        #         handler.close()
        
        log_file = self.get_log_file_path()
        model_file_handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        model_file_handler.setFormatter(formatter)
        model_file_handler.setLevel(logging.DEBUG)
        # app_logger.addHandler(model_file_handler) # グローバルロガーにハンドラを追加
        # self.model_logger = app_logger # このインスタンス用のロガー参照 (実質グローバル)
        # 代わりに、このFileManagerインスタンス専用のロガーを作成することも検討できる
        self.model_specific_logger = logging.getLogger(f"UniRigApp.{self.model_name}")
        self.model_specific_logger.setLevel(logging.DEBUG)
        if not any(isinstance(h, logging.FileHandler) and h.baseFilename == str(log_file) for h in self.model_specific_logger.handlers):
            self.model_specific_logger.addHandler(model_file_handler)
        if not any(isinstance(h, logging.StreamHandler) for h in self.model_specific_logger.handlers): # stdoutも追加
            stdout_handler = logging.StreamHandler(sys.stdout)
            stdout_handler.setFormatter(formatter)
            stdout_handler.setLevel(logging.INFO) # コンソールはINFO以上
            self.model_specific_logger.addHandler(stdout_handler)
        self.model_specific_logger.propagate = False # グローバルロガーへの伝播を防ぐ


    def get_log_file_path(self) -> Path:
        return self.base_model_dir / f"{self.model_name}_pipeline.log"

    def get_model_dir(self) -> Path:
        self.base_model_dir.mkdir(parents=True, exist_ok=True)
        return self.base_model_dir

    def get_step_output_dir(self, step_key: str) -> Path:
        subdir_name = STEP_SUBDIR_NAMES.get(step_key)
        if not subdir_name:
            self.model_specific_logger.error(f"未知のステップキーです: {step_key}")
            raise ValueError(f"Unknown step key: {step_key}")
        step_dir = self.base_model_dir / subdir_name
        step_dir.mkdir(parents=True, exist_ok=True)
        return step_dir

    def save_uploaded_file(self, uploaded_file_path: str) -> Path:
        """アップロードされたファイルをモデルディレクトリのルートに保存する"""
        original_path = Path(uploaded_file_path)
        target_path = self.base_model_dir / original_path.name
        
        # ファイルが既に存在する場合、上書きする前にログを出すか、バージョン管理を検討
        if target_path.exists():
            self.model_specific_logger.warning(f"アップロードされたファイルは既に存在します。上書きします: {target_path}")
        
        shutil.copy(original_path, target_path)
        self.model_specific_logger.info(f"アップロードされたファイルを保存しました: {target_path}")
        return target_path # 保存先のパスを返す

    def get_uploaded_file_path(self, original_filename: str) -> Path:
        """モデルディレクトリに保存された元のアップロードファイルのパスを取得する"""
        return self.base_model_dir / original_filename

    def update_pipeline_state(self, new_state: dict):
        current_state = self.load_pipeline_state()
        current_state.update(new_state)
        try:
            with open(self.state_file_path, 'w') as f:
                json.dump(current_state, f, indent=4)
            self.model_specific_logger.info(f"パイプライン状態を更新しました: {self.state_file_path}")
        except IOError as e:
            self.model_specific_logger.error(f"パイプライン状態ファイルの書き込みに失敗しました: {e}", exc_info=True)


    def load_pipeline_state(self) -> dict:
        if self.state_file_path.exists():
            try:
                with open(self.state_file_path, 'r') as f:
                    return json.load(f)
            except (IOError, json.JSONDecodeError) as e:
                self.model_specific_logger.error(f"パイプライン状態ファイルの読み込みに失敗しました: {e}", exc_info=True)
                return {} # エラー時は空のdictを返す
        return {}

    def reset_pipeline_state(self):
        """パイプラインの状態をリセットし、関連ディレクトリをクリーンアップする"""
        self.model_specific_logger.info(f"パイプライン状態をリセットします: {self.model_name}")
        
        # 既存のモデル固有ログハンドラを閉じて削除
        if hasattr(self, 'model_specific_logger'):
            for handler in self.model_specific_logger.handlers[:]:
                if isinstance(handler, logging.FileHandler):
                    handler.close()
                    self.model_specific_logger.removeHandler(handler)

        # ディレクトリを削除する前に、ファイルが開かれていないことを確認する
        # (特にログファイル)
        time.sleep(0.1) # ハンドラが閉じるのを少し待つ

        if self.base_model_dir.exists():
            try:
                shutil.rmtree(self.base_model_dir)
                self.model_specific_logger.info(f"モデルディレクトリを削除しました: {self.base_model_dir}")
            except OSError as e:
                self.model_specific_logger.error(f"モデルディレクトリの削除に失敗しました: {e}. ファイルが使用中の可能性があります。", exc_info=True)
                # フォールバックとして、stateファイルだけでも削除を試みる
                if self.state_file_path.exists():
                    try:
                        self.state_file_path.unlink()
                        self.model_specific_logger.info("pipeline_state.json のみを削除しました。")
                    except OSError as e_state:
                         self.model_specific_logger.error(f"pipeline_state.json の削除にも失敗しました: {e_state}", exc_info=True)

        self.base_model_dir.mkdir(parents=True, exist_ok=True) # ディレクトリを再作成
        self._setup_model_specific_logging() # 新しいログファイルで再設定
        self.update_pipeline_state({}) # 空の状態でstateファイルを作成

    def mark_step_complete(self, step_key: str, result: dict):
        """ステップの完了状態と出力ファイルを記録する"""
        # result は { "status": "success/error", "message": "...", "outputs": {"file_key": "path"}, "error": "..." } のような形式を期待
        self.update_pipeline_state({step_key: result})
        if result.get("status") == "success":
            self.model_specific_logger.info(f"ステップ {step_key} 正常完了: {result.get('message', '')}")
        else:
            self.model_specific_logger.error(f"ステップ {step_key} 失敗: {result.get('message', '')} 詳細: {result.get('error', '')}")


    def get_step_files(self, step_key: str) -> dict:
        """指定されたステップの出力ファイル情報を取得する"""
        state = self.load_pipeline_state()
        step_info = state.get(step_key, {})
        return step_info.get("outputs", {})

    def get_step_output_file_path(self, step_key: str, file_key: str) -> Path:
        """指定されたステップの特定の出力ファイルの絶対パスを取得する"""
        files = self.get_step_files(step_key)
        file_path_str = files.get(file_key)
        if file_path_str:
            return Path(file_path_str)
        self.model_specific_logger.warning(f"ファイルが見つかりません: ステップ '{step_key}', ファイルキー '{file_key}'")
        return None

# --- パイプラインステップ関数 ---
def call_step0_preserve_assets(model_name: str, progress: gr.Progress):
    progress(0.05, desc="ステップ0: アセット情報保存中...")
    file_manager = FileManager(model_name)
    pipeline_state = file_manager.load_pipeline_state()
    original_filename = pipeline_state.get("original_filename")

    if not original_filename:
        error_msg = "ステップ0エラー: 元のアップロードファイル名がstateから取得できませんでした。"
        file_manager.model_specific_logger.error(error_msg)
        file_manager.mark_step_complete("step0_asset_preservation", {"status": "error", "message": error_msg, "error": error_msg})
        return False, error_msg, None, f"エラー: {error_msg}"

    input_file_path = file_manager.get_uploaded_file_path(original_filename)
    if not input_file_path.exists():
        error_msg = f"ステップ0エラー: 元のアップロードファイルが見つかりません: {input_file_path}"
        file_manager.model_specific_logger.error(error_msg)
        file_manager.mark_step_complete("step0_asset_preservation", {"status": "error", "message": error_msg, "error": error_msg})
        return False, error_msg, None, f"エラー: {error_msg}"

    output_dir_step0 = file_manager.get_step_output_dir("step0_asset_preservation")
    
    try:
        step0_processor = Step0FileTransfer(
            model_name=model_name,
            input_file=str(input_file_path),
            output_dir=str(output_dir_step0),
            logger_instance=file_manager.model_specific_logger
        )
        success, logs, outputs = step0_processor.transfer_file()

        status = "success" if success else "error"
        message = logs if logs else ("正常完了" if success else "エラー発生")
        file_manager.mark_step_complete("step0_asset_preservation", {"status": status, "message": message, "outputs": outputs, "error": "" if success else message})
        ui_message = f"ステップ0: {message}"
        return success, message, outputs.get("asset_metadata_json") if outputs else None, ui_message
    except Exception as e:
        error_msg = f"Step 0 内部モジュール呼び出しエラー: {e}"
        file_manager.model_specific_logger.error(error_msg, exc_info=True)
        file_manager.mark_step_complete("step0_asset_preservation", {"status": "error", "message": error_msg, "error": str(e)})
        return False, error_msg, None, f"エラー: {error_msg}"


def call_step1_extract_mesh(model_name: str, progress: gr.Progress):
    progress(0.15, desc="ステップ1: メッシュ抽出中...")
    file_manager = FileManager(model_name)
    pipeline_state = file_manager.load_pipeline_state()
    original_filename = pipeline_state.get("original_filename")

    if not original_filename:
        error_msg = "ステップ1エラー: 元のアップロードファイル名がstateから取得できませんでした。"
        file_manager.model_specific_logger.error(error_msg)
        file_manager.mark_step_complete("step1_extract", {"status": "error", "message": error_msg, "error": error_msg})
        return False, error_msg, None, f"エラー: {error_msg}"

    input_file_path = file_manager.get_uploaded_file_path(original_filename)
    if not input_file_path.exists():
        error_msg = f"ステップ1エラー: 元のアップロードファイルが見つかりません: {input_file_path}"
        file_manager.model_specific_logger.error(error_msg)
        file_manager.mark_step_complete("step1_extract", {"status": "error", "message": error_msg, "error": error_msg})
        return False, error_msg, None, f"エラー: {error_msg}"

    output_dir_step1 = file_manager.get_step_output_dir("step1_extract")
    
    try:
        step1_processor = Step1Extract(
            output_dir=Path(output_dir_step1),
            logger_instance=file_manager.model_specific_logger
        )
        success, logs, outputs = step1_processor.extract_mesh(
            input_file_path=Path(input_file_path),
            model_name=model_name,
            preserve_textures_in_step1=False
        )
        status = "success" if success else "error"
        message = logs if logs else ("正常完了" if success else "エラー発生")
        file_manager.mark_step_complete("step1_extract", {"status": status, "message": message, "outputs": outputs, "error": "" if success else message})
        ui_message = f"ステップ1: {message}"
        extracted_npz_path = outputs.get("extracted_npz") if outputs else None
        return success, message, extracted_npz_path, ui_message
    except Exception as e:
        error_msg = f"Step 1 内部モジュール呼び出しエラー: {e}"
        file_manager.model_specific_logger.error(error_msg, exc_info=True)
        file_manager.mark_step_complete("step1_extract", {"status": "error", "message": error_msg, "error": str(e)})
        return False, error_msg, None, f"エラー: {error_msg}"


def call_step2_generate_skeleton(model_name: str, gender: str, progress: gr.Progress):
    progress(0.3, desc="ステップ2: スケルトン生成中...")
    file_manager = FileManager(model_name)
    pipeline_state = file_manager.load_pipeline_state()
    original_filename = pipeline_state.get("original_filename") # FBXコピー元特定のため

    step1_outputs = pipeline_state.get("step1_extract", {}).get("outputs", {})
    input_npz_path_str = step1_outputs.get("extracted_npz")

    if not input_npz_path_str:
        error_msg = "ステップ2エラー: Step1からの入力NPZファイルパスが見つかりません。"
        file_manager.model_specific_logger.error(error_msg)
        file_manager.mark_step_complete("step2_skeleton", {"status": "error", "message": error_msg, "error": error_msg})
        return False, error_msg, None, None, f"エラー: {error_msg}"
    
    input_npz_path = Path(input_npz_path_str)
    if not input_npz_path.exists():
        error_msg = f"ステップ2エラー: 入力NPZファイルが見つかりません: {input_npz_path}"
        file_manager.model_specific_logger.error(error_msg)
        file_manager.mark_step_complete("step2_skeleton", {"status": "error", "message": error_msg, "error": error_msg})
        return False, error_msg, None, None, f"エラー: {error_msg}"

    # Step1が入力ファイルを自身の出力ディレクトリにコピーしたパスを特定
    # Step1Extract.extract_mesh内で persistent_input_file = self.output_dir / f"{model_name}{input_file_path.suffix}" として保存
    original_model_copied_by_step1_path = file_manager.get_step_output_dir("step1_extract") / f"{model_name}{Path(original_filename).suffix}"
    if not original_model_copied_by_step1_path.exists():
        # Fallback: 元のアップロードファイルパスを直接使用 (Step1のコピーが失敗した場合など)
        original_model_copied_by_step1_path = file_manager.get_uploaded_file_path(original_filename)
        if not original_model_copied_by_step1_path.exists():
            error_msg = f"ステップ2エラー: FBXコピー元のファイルが見つかりません: {original_model_copied_by_step1_path} および元のアップロード場所"
            file_manager.model_specific_logger.error(error_msg)
            file_manager.mark_step_complete("step2_skeleton", {"status": "error", "message": error_msg, "error": error_msg})
            return False, error_msg, None, None, f"エラー: {error_msg}"


    output_dir_step2 = file_manager.get_step_output_dir("step2_skeleton")

    try:
        step2_processor = Step2Skeleton(
            output_dir=Path(output_dir_step2),
            logger_instance=file_manager.model_specific_logger
        )
        success, logs, outputs = step2_processor.generate_skeleton(
            input_npz_path=input_npz_path,
            model_name=model_name,
            original_model_file_for_fbx_copy=original_model_copied_by_step1_path,
            gender=gender
        )
        status = "success" if success else "error"
        message = logs if logs else ("正常完了" if success else "エラー発生")
        file_manager.mark_step_complete("step2_skeleton", {"status": status, "message": message, "outputs": outputs, "error": "" if success else message})
        ui_message = f"ステップ2: {message}"
        skeleton_fbx_path = outputs.get("skeleton_fbx") if outputs else None
        skeleton_npz_path = outputs.get("skeleton_npz") if outputs else None
        return success, message, skeleton_fbx_path, skeleton_npz_path, ui_message
    except Exception as e:
        error_msg = f"Step 2 内部モジュール呼び出しエラー: {e}"
        file_manager.model_specific_logger.error(error_msg, exc_info=True)
        file_manager.mark_step_complete("step2_skeleton", {"status": "error", "message": error_msg, "error": str(e)})
        return False, error_msg, None, None, f"エラー: {error_msg}"

def call_step3_apply_skinning(model_name: str, skinning_type: str, progress: gr.Progress):
    progress(0.6, desc="ステップ3: スキニング適用中...")
    file_manager = FileManager(model_name)
    pipeline_state = file_manager.load_pipeline_state()
    original_filename = pipeline_state.get("original_filename") # UniRig Skinningで必要

    step1_outputs = pipeline_state.get("step1_extract", {}).get("outputs", {})
    mesh_file_path_str = step1_outputs.get("extracted_npz")

    step2_outputs = pipeline_state.get("step2_skeleton", {}).get("outputs", {})
    skeleton_fbx_path_str = step2_outputs.get("skeleton_fbx")
    skeleton_npz_path_str = step2_outputs.get("skeleton_npz")

    if not all([mesh_file_path_str, skeleton_fbx_path_str, skeleton_npz_path_str]):
        missing = []
        if not mesh_file_path_str: missing.append("メッシュNPZ(Step1)")
        if not skeleton_fbx_path_str: missing.append("スケルトンFBX(Step2)")
        if not skeleton_npz_path_str: missing.append("スケルトンNPZ(Step2)")
        error_msg = f"ステップ3エラー: 必要な入力ファイルパスが見つかりません ({', '.join(missing)})。"
        file_manager.model_specific_logger.error(error_msg)
        file_manager.mark_step_complete("step3_skinning", {"status": "error", "message": error_msg, "error": error_msg})
        return False, error_msg, None, f"エラー: {error_msg}"

    mesh_file_path = Path(mesh_file_path_str)
    skeleton_fbx_path = Path(skeleton_fbx_path_str)
    skeleton_npz_path = Path(skeleton_npz_path_str)

    if not mesh_file_path.exists():
        error_msg = f"ステップ3エラー: メッシュNPZファイルが見つかりません: {mesh_file_path}"
        file_manager.model_specific_logger.error(error_msg)
        file_manager.mark_step_complete("step3_skinning", {"status": "error", "message": error_msg, "error": error_msg})
        return False, error_msg, None, f"エラー: {error_msg}"
    if not skeleton_fbx_path.exists():
        error_msg = f"ステップ3エラー: スケルトンFBXファイルが見つかりません: {skeleton_fbx_path}"
        file_manager.model_specific_logger.error(error_msg)
        file_manager.mark_step_complete("step3_skinning", {"status": "error", "message": error_msg, "error": error_msg})
        return False, error_msg, None, f"エラー: {error_msg}"
    # skeleton_npz_path はUniRig Skinningではディレクトリ渡しなので、ファイル存在チェックはモジュール内部で行う

    output_dir_step3 = file_manager.get_step_output_dir("step3_skinning")

    try:
        if skinning_type == "UniRig Core":
            step3_processor = Step3UniRigSkinning(
                output_dir=Path(output_dir_step3),
                logger_instance=file_manager.model_specific_logger
            )
            # 正しい引数でUniRigスキニングを呼び出し
            success, logs, outputs = step3_processor.apply_skinning(
                input_mesh_npz_path=mesh_file_path,
                input_skeleton_fbx_path=skeleton_fbx_path,
                input_skeleton_npz_path=skeleton_npz_path,
                model_name=model_name
            )
        else: # Standard (or other types)
            step3_processor = Step3Skinning(
                output_dir=Path(output_dir_step3),
                logger_instance=file_manager.model_specific_logger
            )
            success, logs, outputs = step3_processor.apply_skinning(
                input_mesh_npz_path=mesh_file_path,
                input_skeleton_fbx_path=skeleton_fbx_path,
                input_skeleton_npz_path=skeleton_npz_path,
                model_name=model_name
            )
        
        status = "success" if success else "error"
        message = logs if logs else ("正常完了" if success else "エラー発生")
        file_manager.mark_step_complete("step3_skinning", {"status": status, "message": message, "outputs": outputs, "error": "" if success else message})
        ui_message = f"ステップ3 ({skinning_type}): {message}"
        skinned_fbx_path = outputs.get("skinned_fbx") if outputs else None
        return success, message, skinned_fbx_path, ui_message
    except Exception as e:
        error_msg = f"Step 3 ({skinning_type}) 内部モジュール呼び出しエラー: {e}"
        file_manager.model_specific_logger.error(error_msg, exc_info=True)
        file_manager.mark_step_complete("step3_skinning", {"status": "error", "message": error_msg, "error": str(e)})
        return False, error_msg, None, f"エラー: {error_msg}"

def call_step4_merge_skeleton_skinning(model_name: str, progress: gr.Progress):
    """Step 4: スケルトン・スキンウェイトマージ（特化機能）"""
    progress(0.75, desc="ステップ4: スケルトン・スキンウェイトマージ中...")
    file_manager = FileManager(model_name)
    pipeline_state = file_manager.load_pipeline_state()
    
    # 入力ファイルの検証
    step1_outputs = pipeline_state.get("step1_extract", {}).get("outputs", {})
    step2_outputs = pipeline_state.get("step2_skeleton", {}).get("outputs", {})
    step3_outputs = pipeline_state.get("step3_skinning", {}).get("outputs", {})
    
    if not all([step1_outputs, step2_outputs, step3_outputs]):
        error_msg = "Step 4エラー: 前のステップの出力が不足しています"
        file_manager.model_specific_logger.error(error_msg)
        file_manager.mark_step_complete("step4_merge", {"status": "error", "message": error_msg, "error": error_msg})
        return False, error_msg, None, f"エラー: {error_msg}"
    
    output_dir_step4 = file_manager.get_step_output_dir("step4_merge")
    
    try:
        # 新Step4Merge: スケルトン・スキンウェイトマージ特化実行
        step4_processor = Step4Merge(
            output_dir=output_dir_step4,
            logger_instance=file_manager.model_specific_logger
        )
        
        success, logs, outputs = step4_processor.merge_skeleton_skinning(
            model_name=model_name,
            step1_files=step1_outputs,
            step2_files=step2_outputs,
            step3_files=step3_outputs
        )
        
        status = "success" if success else "error"
        message = logs if logs else ("正常完了" if success else "エラー発生")
        file_manager.mark_step_complete("step4_merge", {"status": status, "message": message, "outputs": outputs, "error": "" if success else message})
        ui_message = f"ステップ4 (マージ): {message}"
        merged_fbx_path = outputs.get("merged_fbx") if outputs else None
        return success, message, merged_fbx_path, ui_message
    except Exception as e:
        error_msg = f"Step 4 (マージ) 内部モジュール呼び出しエラー: {e}"
        file_manager.model_specific_logger.error(error_msg, exc_info=True)
        file_manager.mark_step_complete("step4_merge", {"status": "error", "message": error_msg, "error": str(e)})
        return False, error_msg, None, f"エラー: {error_msg}"

def call_step5_blender_integration(model_name: str, progress: gr.Progress):
    """Step 5: Blender統合・最終FBX出力（新設）"""
    progress(0.9, desc="ステップ5: Blender統合・最終出力中...")
    file_manager = FileManager(model_name)
    pipeline_state = file_manager.load_pipeline_state()
    
    # 入力ファイルの検証
    original_filename = pipeline_state.get("original_filename")
    step4_outputs = pipeline_state.get("step4_merge", {}).get("outputs", {})
    
    if not original_filename or not step4_outputs:
        error_msg = "Step 5エラー: 元モデルまたはStep4出力が不足しています"
        file_manager.model_specific_logger.error(error_msg)
        file_manager.mark_step_complete("step5_blender_integration", {"status": "error", "message": error_msg, "error": error_msg})
        return False, error_msg, None, f"エラー: {error_msg}"
    
    original_file_path = file_manager.get_uploaded_file_path(original_filename)
    merged_fbx_path = step4_outputs.get("merged_fbx")
    
    if not original_file_path.exists() or not merged_fbx_path or not Path(merged_fbx_path).exists():
        error_msg = f"Step 5エラー: 必要なファイルが見つかりません - 元: {original_file_path}, マージ: {merged_fbx_path}"
        file_manager.model_specific_logger.error(error_msg)
        file_manager.mark_step_complete("step5_blender_integration", {"status": "error", "message": error_msg, "error": error_msg})
        return False, error_msg, None, f"エラー: {error_msg}"
    
    output_dir_step5 = file_manager.get_step_output_dir("step5_blender_integration")
    
    try:
        # Step5BlenderIntegration の実行
        step5_processor = Step5BlenderIntegration(
            model_name=model_name,
            output_dir=str(output_dir_step5)
        )
        
        success, logs, outputs = step5_processor.integrate_and_export(
            original_model=str(original_file_path),
            merged_fbx=merged_fbx_path
        )
        
        status = "success" if success else "error"
        message = logs if logs else ("正常完了" if success else "エラー発生")
        file_manager.mark_step_complete("step5_blender_integration", {"status": status, "message": message, "outputs": outputs, "error": "" if success else message})
        ui_message = f"ステップ5 (Blender統合): {message}"
        final_fbx_path = outputs.get("final_fbx") if outputs else None
        return success, message, final_fbx_path, ui_message
    except Exception as e:
        error_msg = f"Step 5 (Blender統合) 内部モジュール呼び出しエラー: {e}"
        file_manager.model_specific_logger.error(error_msg, exc_info=True)
        file_manager.mark_step_complete("step5_blender_integration", {"status": "error", "message": error_msg, "error": str(e)})
        return False, error_msg, None, f"エラー: {error_msg}"

# --- ポートチェック関数 ---

def is_port_available(port: int) -> bool:
    """指定されたポートが利用可能かどうかを確認する"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('', port))
            return True
        except OSError:
            return False

def find_available_port(start_port: int = 7860, max_attempts: int = 10) -> int:
    """利用可能なポートを検索する"""
    for i in range(max_attempts):
        port = start_port + i
        if is_port_available(port):
            return port
    raise RuntimeError(f"利用可能なポートが見つかりません (範囲: {start_port}-{start_port + max_attempts - 1})")

# --- フルパイプライン実行関数 ---
def call_full_pipeline(uploaded_file_path: str, gender: str, model_name: str, progress: gr.Progress):
    """
    6ステップフルパイプライン実行: 
    Step0 → Step1 → Step2 → Step3 → Step4 → Step5
    """
    if not uploaded_file_path:
        return None, "エラー: ファイルがアップロードされていません。", None, "ファイルをアップロードしてください。"
    
    try:
        progress(0.0, desc="パイプライン初期化中...")
        
        # ファイルマネージャー初期化
        file_manager = FileManager(model_name)
        file_manager.reset_pipeline_state()
        
        # アップロードファイル保存
        uploaded_path = Path(uploaded_file_path)
        saved_path = file_manager.save_uploaded_file(uploaded_path, uploaded_path.name)
        
        logs = f"=== UniRig 6ステップフルパイプライン実行開始 ===\n"
        logs += f"📁 モデル名: {model_name}\n"
        logs += f"📂 入力ファイル: {uploaded_file_path}\n\n"
        
        # Step 0: ファイル転送
        progress(0.05, desc="ステップ0: ファイル転送中...")
        success_0, message_0, _, ui_msg_0 = call_step0_preserve_assets(model_name, progress)
        logs += f"Step 0: {message_0}\n"
        if not success_0:
            return None, logs, None, ui_msg_0
        
        # Step 1: メッシュ抽出
        progress(0.2, desc="ステップ1: メッシュ抽出中...")
        success_1, message_1, _, ui_msg_1 = call_step1_extract_mesh(model_name, progress)
        logs += f"Step 1: {message_1}\n"
        if not success_1:
            return None, logs, None, ui_msg_1
        
        # Step 2: スケルトン生成
        progress(0.35, desc="ステップ2: スケルトン生成中...")
        success_2, message_2, _, _, ui_msg_2 = call_step2_generate_skeleton(model_name, gender, progress)
        logs += f"Step 2: {message_2}\n"
        if not success_2:
            return None, logs, None, ui_msg_2
        
        # Step 3: スキニング適用
        progress(0.55, desc="ステップ3: スキニング適用中...")
        success_3, message_3, _, ui_msg_3 = call_step3_apply_skinning(model_name, "unirig", progress)
        logs += f"Step 3: {message_3}\n"
        if not success_3:
            return None, logs, None, ui_msg_3
        
        # Step 4: マージ処理
        progress(0.75, desc="ステップ4: マージ処理中...")
        success_4, message_4, _, ui_msg_4 = call_step4_merge_skeleton_skinning(model_name, progress)
        logs += f"Step 4: {message_4}\n"
        if not success_4:
            return None, logs, None, ui_msg_4
        
        # Step 5: Blender統合・最終出力
        progress(0.9, desc="ステップ5: Blender統合・最終出力中...")
        success_5, message_5, final_path, ui_msg_5 = call_step5_blender_integration(model_name, progress)
        logs += f"Step 5: {message_5}\n"
        
        if success_5 and final_path:
            logs += f"\n🎉 === 6ステップフルパイプライン実行完了 ===\n"
            logs += f"✅ 最終出力: {final_path}\n"
            progress(1.0, desc="フルパイプライン完了!")
            return final_path, logs, final_path, "フルパイプライン実行完了!"
        else:
            return None, logs, None, ui_msg_5
            
    except Exception as e:
        error_msg = f"フルパイプライン実行エラー: {str(e)}"
        app_logger.error(error_msg, exc_info=True)
        return None, f"{logs}\n❌ {error_msg}", None, error_msg

# --- Gradioインターフェース構築 ---
def build_gradio_interface():
    """6ステップパイプライン対応のGradioインターフェースを構築"""
    
    with gr.Blocks(title="UniRig 6ステップ自動リギングシステム", theme=gr.themes.Base()) as demo:
        
        # 状態変数
        s_model_name = gr.State()
        s_final_path = gr.State()
        
        gr.Markdown("# UniRig 6ステップ自動リギングシステム")
        gr.Markdown("""
        3Dモデル（FBX、OBJ、GLB/GLTF、PLYなど）をアップロードし、6ステップの自動リギング処理を実行します。
        
        **6ステップ処理フロー:**
        1. **Step 0**: ファイル転送・初期設定
        2. **Step 1**: メッシュ抽出
        3. **Step 2**: スケルトン生成
        4. **Step 3**: スキニング適用
        5. **Step 4**: マージ処理
        6. **Step 5**: Blender統合・最終出力
        """)
        
        with gr.Tab("フルパイプライン実行"):
            gr.Markdown("## 🚀 ワンクリック6ステップ自動リギング")
            
            with gr.Row():
                with gr.Column(scale=1):
                    # 入力コントロール
                    input_model_upload = gr.File(
                        label="3Dモデルをアップロード", 
                        file_types=[".fbx", ".obj", ".glb", ".gltf", ".ply"], 
                        type="filepath"
                    )
                    model_name_input = gr.Textbox(
                        label="モデル名",
                        placeholder="モデル名を入力（ファイル名から自動設定）",
                        value=""
                    )
                    gender_dropdown = gr.Dropdown(
                        label="性別（スケルトン生成用）", 
                        choices=["female", "male", "neutral"], 
                        value="female"
                    )
                    pipeline_button = gr.Button(
                        "🎯 6ステップフルパイプライン実行", 
                        variant="primary", 
                        size="lg"
                    )
                
                with gr.Column(scale=2):
                    # 結果表示
                    final_model_display = gr.Model3D(
                        label="最終リギング済みモデルプレビュー", 
                        interactive=False, 
                        camera_position=(0, 2.5, 3.5)
                    )
            
            # ログ表示
            pipeline_logs = gr.Textbox(
                label="フルパイプラインログ", 
                lines=15, 
                interactive=False, 
                show_copy_button=True
            )
            
            # ダウンロードボタン
            final_model_download = gr.DownloadButton(
                label="🎯 最終モデル (FBX)", 
                interactive=True, 
                visible=False
            )
            
        with gr.Tab("ステップ詳細とヘルプ"):
            gr.Markdown("""
            ## 📋 各ステップの詳細
            
            ### Step 0: ファイル転送・初期設定
            - アップロードされたファイルを内部作業ディレクトリに転送
            - パイプライン状態の初期化
            
            ### Step 1: メッシュ抽出  
            - 3Dモデルから頂点・面情報を抽出
            - NPZ形式でメッシュデータを保存
            
            ### Step 2: スケルトン生成
            - AIを用いた最適な骨格構造の予測
            - FBXとNPZ形式でスケルトンデータを出力
            
            ### Step 3: スキニング適用
            - メッシュと骨格の自動バインディング
            - 頂点ウェイトの自動計算
            
            ### Step 4: マージ処理
            - スケルトンとスキニングデータの統合
            - 中間形式での統合処理
            
            ### Step 5: Blender統合・最終出力
            - Blenderを使用した最終品質調整
            - 高品質FBXファイルの生成
            
            ## 💡 使用方法
            1. 3Dモデルファイルをアップロード
            2. モデル名を入力（自動入力されます）
            3. 性別を選択
            4. 「フルパイプライン実行」をクリック
            5. 処理完了後、最終モデルをダウンロード
            
            ## ⚠️ 注意事項
            - 処理時間: 5-15分程度（モデルサイズによる）
            - サポート形式: FBX, OBJ, GLB, GLTF, PLY
            - GPU環境推奨（CPU処理も可能）
            """)
        
        # イベントハンドラー
        def handle_upload(file_path):
            """ファイルアップロード時の処理"""
            if file_path:
                filename = Path(file_path).stem
                return filename, filename  # model_name_input, s_model_name
            return "", ""
        
        def handle_pipeline_execution(file_path, gender, model_name, progress=gr.Progress()):
            """フルパイプライン実行ハンドラー"""
            if not file_path:
                return None, "エラー: ファイルがアップロードされていません。", None, None, gr.DownloadButton(visible=False)
            
            if not model_name.strip():
                model_name = Path(file_path).stem
            
            final_path, logs, download_path, ui_msg = call_full_pipeline(file_path, gender, model_name, progress)
            
            if final_path:
                return (
                    final_path,  # final_model_display
                    logs,        # pipeline_logs  
                    download_path, # s_final_path
                    ui_msg,      # UI status
                    gr.DownloadButton(label="🎯 最終モデル (FBX)", value=download_path, visible=True)
                )
            else:
                return (
                    None,        # final_model_display
                    logs,        # pipeline_logs
                    None,        # s_final_path
                    ui_msg,      # UI status
                    gr.DownloadButton(visible=False)
                )
        
        # イベント設定
        input_model_upload.change(
            fn=handle_upload,
            inputs=[input_model_upload],
            outputs=[model_name_input, s_model_name]
        )
        
        pipeline_button.click(
            fn=handle_pipeline_execution,
            inputs=[input_model_upload, gender_dropdown, model_name_input],
            outputs=[
                final_model_display,
                pipeline_logs,
                s_final_path,
                gr.State(),  # UI状態用（表示されない）
                final_model_download
            ]
        )
        
        demo.queue()
    
    return demo

# --- メイン実行部分 ---
if __name__ == "__main__":
    app_logger.info("UniRig 6ステップパイプラインアプリケーション開始")
    
    # ポート確認
    try:
        port = find_available_port(7860)
        app_logger.info(f"利用可能ポート: {port}")
    except RuntimeError as e:
        app_logger.error(f"ポート確認エラー: {e}")
        sys.exit(1)
    
    # Gradioインターフェース構築
    try:
        demo = build_gradio_interface()
        app_logger.info("Gradioインターフェース構築完了")
        
        # サーバー起動
        demo.launch(
            server_name="0.0.0.0",
            server_port=port,
            share=False,
            inbrowser=True,
            debug=True,
            show_error=True
        )
        
    except Exception as e:
        app_logger.error(f"アプリケーション起動エラー: {e}", exc_info=True)
        sys.exit(1)
