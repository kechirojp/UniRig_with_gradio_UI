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
from step_modules.step0_asset_preservation import Step0AssetPreservation
from step_modules.step1_extract import Step1Extract
from step_modules.step2_skeleton import Step2Skeleton
from step_modules.step3_skinning import Step3Skinning # 標準的なスキニング
from step_modules.step3_skinning_unirig import Step3UniRigSkinning # UniRig独自のスキニング
from step_modules.step4_texture import Step4Texture
from step_modules.step4_texture_v2 import Step4TextureV2

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
        step0_processor = Step0AssetPreservation(
            model_name=model_name,
            input_file=str(input_file_path),
            output_dir=str(output_dir_step0),
            logger_instance=file_manager.model_specific_logger
        )
        success, logs, outputs = step0_processor.preserve_assets()

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
            original_model_path = file_manager.get_uploaded_file_path(original_filename)
            skeleton_dir_path = file_manager.get_step_output_dir("step2_skeleton") # Step2の出力ディレクトリ
            success, logs, outputs = step3_processor.apply_skinning(
                model_name=model_name,
                original_model_path=original_model_path,
                skeleton_dir=skeleton_dir_path, # NPZとFBXが含まれるディレクトリ
                # unirig_core_output_dir はモジュール内で output_dir をベースに設定される
            )
        else: # Standard (or other types)
            step3_processor = Step3Skinning(
                output_dir=Path(output_dir_step3),
                logger_instance=file_manager.model_specific_logger
            )
            success, logs, outputs = step3_processor.apply_skinning(
                model_name=model_name,
                mesh_file_path=mesh_file_path,
                skeleton_fbx_path=skeleton_fbx_path,
                skeleton_npz_path=skeleton_npz_path # 標準スキニングはNPZファイルパスを期待
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

def call_step4_merge_textures(model_name: str, use_v2_texture_merge: bool, progress: gr.Progress):
    progress(0.85, desc="ステップ4: テクスチャ統合中...")
    file_manager = FileManager(model_name)
    pipeline_state = file_manager.load_pipeline_state()
    original_filename = pipeline_state.get("original_filename")

    step0_outputs = pipeline_state.get("step0_asset_preservation", {}).get("outputs", {})
    asset_metadata_path_str = step0_outputs.get("asset_metadata_json")

    step3_outputs = pipeline_state.get("step3_skinning", {}).get("outputs", {})
    skinned_fbx_path_str = step3_outputs.get("skinned_fbx")

    if not all([asset_metadata_path_str, skinned_fbx_path_str, original_filename]):
        missing = []
        if not asset_metadata_path_str: missing.append("アセットメタデータJSON(Step0)")
        if not skinned_fbx_path_str: missing.append("スキニング済みFBX(Step3)")
        if not original_filename: missing.append("元のモデルファイル名")
        error_msg = f"ステップ4エラー: 必要な入力情報が見つかりません ({', '.join(missing)})。"
        file_manager.model_specific_logger.error(error_msg)
        file_manager.mark_step_complete("step4_texture", {"status": "error", "message": error_msg, "error": error_msg})
        return False, error_msg, None, f"エラー: {error_msg}"

    asset_metadata_path = Path(asset_metadata_path_str)
    skinned_fbx_path = Path(skinned_fbx_path_str)
    original_model_path = file_manager.get_uploaded_file_path(original_filename)

    if not asset_metadata_path.exists():
        error_msg = f"ステップ4エラー: アセットメタデータファイルが見つかりません: {asset_metadata_path}"
        file_manager.model_specific_logger.error(error_msg)
        file_manager.mark_step_complete("step4_texture", {"status": "error", "message": error_msg, "error": error_msg})
        return False, error_msg, None, f"エラー: {error_msg}"
    if not skinned_fbx_path.exists():
        error_msg = f"ステップ4エラー: スキニング済みFBXファイルが見つかりません: {skinned_fbx_path}"
        file_manager.model_specific_logger.error(error_msg)
        file_manager.mark_step_complete("step4_texture", {"status": "error", "message": error_msg, "error": error_msg})
        return False, error_msg, None, f"エラー: {error_msg}"
    if not original_model_path.exists():
        error_msg = f"ステップ4エラー: 元のモデルファイルが見つかりません: {original_model_path}"
        file_manager.model_specific_logger.error(error_msg)
        file_manager.mark_step_complete("step4_texture", {"status": "error", "message": error_msg, "error": error_msg})
        return False, error_msg, None, f"エラー: {error_msg}"

    output_dir_step4 = file_manager.get_step_output_dir("step4_texture") # または "04_merge"

    try:
        if use_v2_texture_merge:
            step4_processor = Step4TextureV2(
                output_dir=Path(output_dir_step4),
                logger_instance=file_manager.model_specific_logger
            )
        else:
            step4_processor = Step4Texture(
                output_dir=Path(output_dir_step4),
                logger_instance=file_manager.model_specific_logger
            )
        
        success, logs, outputs = step4_processor.merge_textures(
            model_name=model_name,
            skinned_fbx_path=skinned_fbx_path,
            asset_metadata_path=asset_metadata_path,
            original_model_path=original_model_path
        )
        
        status = "success" if success else "error"
        message = logs if logs else ("正常完了" if success else "エラー発生")
        file_manager.mark_step_complete("step4_texture", {"status": status, "message": message, "outputs": outputs, "error": "" if success else message})
        ui_message = f"ステップ4 (v2: {use_v2_texture_merge}): {message}"
        final_fbx_path = outputs.get("final_fbx") if outputs else None
        return success, message, final_fbx_path, ui_message
    except Exception as e:
        error_msg = f"Step 4 (v2: {use_v2_texture_merge}) 内部モジュール呼び出しエラー: {e}"
        file_manager.model_specific_logger.error(error_msg, exc_info=True)
        file_manager.mark_step_complete("step4_texture", {"status": "error", "message": error_msg, "error": str(e)})
        return False, error_msg, None, f"エラー: {error_msg}"

# --- ポートチェック関数 ---
def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return False
        except socket.error:
            return True

def check_port_periodically(port: int, interval: int = 2, max_checks: int = 5):
    """指定されたポートが使用可能になるまで定期的にチェックする"""
    # app_logger.info(f"ポート {port} のチェックを開始します...")
    # for i in range(max_checks):
    #     if not is_port_in_use(port):
    #         app_logger.info(f"ポート {port} は利用可能です。")
    #         return True
    #     app_logger.info(f"ポート {port} は使用中です。 ({i+1}/{max_checks}) {interval}秒後に再試行します...")
    #     time.sleep(interval)
    # app_logger.error(f"ポート {port} はタイムアウト後も使用中です。Gradioの起動に失敗する可能性があります。")
    # return False
    # この機能はGradioがshare=Trueの場合に外部からアクセスする際に問題になることがあるため、
    # ローカル実行では必須ではないかもしれない。一旦無効化または簡略化。
    if is_port_in_use(port):
        app_logger.warning(f"ポート {port} は既に使用中です。Gradioの起動に影響する可能性があります。")
        return False
    app_logger.info(f"ポート {port} は利用可能です。")
    return True

# --- メインパイプライン実行関数 ---
def call_pipeline(uploaded_file, gender, use_step4_v2, progress=gr.Progress(track_tqdm=True)):
    if uploaded_file is None:
        yield "エラー: ファイルがアップロードされていません。", "", "", "", "", "", "", "", gr.Button(interactive=True)
        return

    original_filename_full = Path(uploaded_file.name).name
    model_name_base = Path(original_filename_full).stem
    model_name = FileManager(model_name_base).model_name # サニタイズされたモデル名を取得

    file_manager = FileManager(model_name)
    file_manager.reset_pipeline_state() # パイプライン開始時に状態をリセット
    file_manager.model_specific_logger.info(f"パイプライン開始: モデル名='{model_name}', 元ファイル名='{original_filename_full}'")

    # アップロードされたファイルをFileManager経由で保存
    try:
        saved_uploaded_file_path = file_manager.save_uploaded_file(uploaded_file.name)
        file_manager.model_specific_logger.info(f"入力ファイルを処理準備完了: {saved_uploaded_file_path}")
        # 元のファイル名をstateに保存
        file_manager.update_pipeline_state({"original_filename": original_filename_full})
    except Exception as e:
        error_msg = f"ファイルアップロード処理エラー: {e}"
        file_manager.model_specific_logger.error(error_msg, exc_info=True)
        yield error_msg, "", "", "", "", "", "", "", gr.Button(interactive=True)
        return

    # UI出力用変数の初期化
    log_output = f"パイプライン開始: {model_name}\n"
    step0_status, step1_status, step2_status, step3_status, step4_status = ["待機中"] * 5
    final_fbx_path_ui = ""
    log_file_path_ui = str(file_manager.get_log_file_path()) # ログファイルのパスをUIに表示

    yield (
        log_output, step0_status, step1_status, step2_status, step3_status, step4_status,
        final_fbx_path_ui, log_file_path_ui, gr.Button(interactive=False)
    )

    # Step 0: Asset Preservation
    s0_success, s0_log, s0_metadata_path, s0_ui_msg = call_step0_preserve_assets(model_name, progress)
    log_output += f"{s0_ui_msg}\n"
    step0_status = "成功" if s0_success else "失敗"
    yield log_output, step0_status, step1_status, step2_status, step3_status, step4_status, final_fbx_path_ui, log_file_path_ui, gr.Button(interactive=False)
    if not s0_success:
        log_output += "ステップ0でエラーが発生したため、パイプラインを停止します。\n"
        yield log_output, step0_status, step1_status, step2_status, step3_status, step4_status, final_fbx_path_ui, log_file_path_ui, gr.Button(interactive=True)
        return

    # Step 1: Extract Mesh
    s1_success, s1_log, s1_npz_path, s1_ui_msg = call_step1_extract_mesh(model_name, progress)
    log_output += f"{s1_ui_msg}\n"
    step1_status = "成功" if s1_success else "失敗"
    yield log_output, step0_status, step1_status, step2_status, step3_status, step4_status, final_fbx_path_ui, log_file_path_ui, gr.Button(interactive=False)
    if not s1_success:
        log_output += "ステップ1でエラーが発生したため、パイプラインを停止します。\n"
        yield log_output, step0_status, step1_status, step2_status, step3_status, step4_status, final_fbx_path_ui, log_file_path_ui, gr.Button(interactive=True)
        return

    # Step 2: Generate Skeleton
    s2_success, s2_log, s2_fbx_path, s2_npz_path, s2_ui_msg = call_step2_generate_skeleton(model_name, gender, progress)
    log_output += f"{s2_ui_msg}\n"
    step2_status = "成功" if s2_success else "失敗"
    yield log_output, step0_status, step1_status, step2_status, step3_status, step4_status, final_fbx_path_ui, log_file_path_ui, gr.Button(interactive=False)
    if not s2_success:
        log_output += "ステップ2でエラーが発生したため、パイプラインを停止します。\n"
        yield log_output, step0_status, step1_status, step2_status, step3_status, step4_status, final_fbx_path_ui, log_file_path_ui, gr.Button(interactive=True)
        return

    # Step 3: Apply Skinning
    s3_success, s3_log, s3_skinned_fbx_path, s3_ui_msg = call_step3_apply_skinning(model_name, progress)
    log_output += f"{s3_ui_msg}\n"
    step3_status = "成功" if s3_success else "失敗"
    yield log_output, step0_status, step1_status, step2_status, step3_status, step4_status, final_fbx_path_ui, log_file_path_ui, gr.Button(interactive=False)
    if not s3_success:
        log_output += "ステップ3でエラーが発生したため、パイプラインを停止します。\n"
        yield log_output, step0_status, step1_status, step2_status, step3_status, step4_status, final_fbx_path_ui, log_file_path_ui, gr.Button(interactive=True)
        return

    # Step 4: Merge Textures
    s4_success, s4_log, s4_final_fbx_path, s4_ui_msg = call_step4_merge_textures(model_name, use_step4_v2, progress)
    log_output += f"{s4_ui_msg}\n"
    step4_status = "成功" if s4_success else "失敗"
    if s4_success and s4_final_fbx_path:
        final_fbx_path_ui = str(s4_final_fbx_path)
        log_output += f"最終出力ファイル: {final_fbx_path_ui}\n"
    
    log_output += "パイプライン完了。\n"
    yield log_output, step0_status, step1_status, step2_status, step3_status, step4_status, final_fbx_path_ui, log_file_path_ui, gr.Button(interactive=True)

# --- Gradio UI ---
if __name__ == "__main__":
    # グローバルロガー設定 (app.py実行時に一度だけ行う)
    app_logger = logging.getLogger("UniRigApp")
    app_logger.setLevel(logging.DEBUG) # グローバルロガーのレベル
    app_logger.handlers = [] # 既存のハンドラをクリア (再実行時の重複防止)
    
    # stdoutハンドラをグローバルロガーに追加
    global_stdout_handler = logging.StreamHandler(sys.stdout)
    global_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    global_stdout_handler.setFormatter(global_formatter)
    global_stdout_handler.setLevel(logging.INFO) # コンソールはINFO以上
    app_logger.addHandler(global_stdout_handler)
    app_logger.propagate = False # 親ロガーへの伝播はしない

    app_logger.info("アプリケーションロガーを初期化しました。")

    # ポートが利用可能か確認
    gradio_port = 7861 # 変更: ポート番号を7861に変更
    # check_port_periodically(gradio_port) # 起動前にチェック

    with gr.Blocks(theme=gr.themes.Soft()) as demo:
        gr.Markdown("# UniRig 自動リギングシステム (データフロー改修版)")
        
        with gr.Row():
            with gr.Column(scale=1):
                file_input = gr.File(label="3Dモデルファイル (FBX, GLB, etc.)", type="filepath")
                gender_dropdown = gr.Dropdown(label="性別 (スケルトン生成用)", choices=["neutral", "male", "female"], value="neutral")
                use_step4_v2_checkbox = gr.Checkbox(label="Step4: テクスチャ統合 v2 を使用 (推奨)", value=True)
                run_button = gr.Button("パイプライン実行", variant="primary", interactive=True)
            
            with gr.Column(scale=2):
                gr.Markdown("### パイプライン進捗")
                log_output_textbox = gr.Textbox(label="ログ出力", lines=15, max_lines=30, autoscroll=True, show_copy_button=True)
                
                with gr.Row():
                    step0_status_textbox = gr.Textbox(label="Step0: アセット保存", value="待機中", interactive=False)
                    step1_status_textbox = gr.Textbox(label="Step1: メッシュ抽出", value="待機中", interactive=False)
                with gr.Row():
                    step2_status_textbox = gr.Textbox(label="Step2: スケルトン生成", value="待機中", interactive=False)
                    step3_status_textbox = gr.Textbox(label="Step3: スキニング", value="待機中", interactive=False)
                with gr.Row():
                    step4_status_textbox = gr.Textbox(label="Step4: テクスチャ統合", value="待機中", interactive=False)

                final_fbx_path_textbox = gr.Textbox(label="最終FBXファイルパス", value="", interactive=False, show_copy_button=True)
                log_file_path_textbox = gr.Textbox(label="モデル別ログファイルパス", value="", interactive=False, show_copy_button=True)

        run_button.click(
            fn=call_pipeline,
            inputs=[file_input, gender_dropdown, use_step4_v2_checkbox],
            outputs=[
                log_output_textbox, 
                step0_status_textbox, step1_status_textbox, step2_status_textbox, 
                step3_status_textbox, step4_status_textbox,
                final_fbx_path_textbox, log_file_path_textbox,
                run_button # ボタンのインタラクティブ状態を更新
            ]
        )

    app_logger.info(f"Gradioアプリケーションをポート {gradio_port} で起動します。")
    # demo.queue().launch(share=True, server_port=gradio_port, prevent_thread_lock=True)
    # prevent_thread_lock=True はGradioのバージョンによっては不要/エラーになる可能性あり
    # share=True は外部公開用。ローカルテストでは不要な場合も。
    demo.queue().launch(server_port=gradio_port)
    app_logger.info("Gradioアプリケーションが終了しました。")
