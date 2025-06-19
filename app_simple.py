"""
UniRig MVP - Simplified Pipeline Application
シンプル化されたパイプライン - ファイルベース状態管理

基本理念:
1. JSONファイル状態管理を廃止
2. ファイルの存在確認のみで状態判定
3. 固定ディレクトリ構造
4. 大幅にシンプル化されたコード
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

# ステップモジュールのインポート
from step_modules.step0_asset_preservation import Step0AssetPreservation
from step_modules.step1_extract import Step1Extract
from step_modules.step2_skeleton_old_02 import Step2Skeleton
from step_modules.step3_skinning_unirig import Step3UniRigSkinning
from step_modules.step4_merge import Step4CrossPlatformMerge
from step_modules.step5_reliable_uv_material_transfer import Step5ReliableUVMaterialTransfer

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
class SimpleFileManager:
    """ファイルベース状態管理 - JSONファイル不要のシンプル設計"""
    
    def __init__(self, model_name: str):
        if not model_name:
            app_logger.warning("FileManager初期化: model_nameが空です。デフォルト名を使用します。")
            model_name = DEFAULT_MODEL_NAME
        self.model_name = self._sanitize_model_name(model_name)
        self.base_model_dir = PIPELINE_BASE_DIR / self.model_name
        
        # 各ステップのディレクトリパス
        self.step_dirs = {
            'step0': self.base_model_dir / "00_asset_preservation",
            'step1': self.base_model_dir / "01_extracted_mesh", 
            'step2': self.base_model_dir / "02_skeleton",
            'step3': self.base_model_dir / "03_skinning",
            'step4': self.base_model_dir / "04_merge",
            'step5': self.base_model_dir / "05_blender_integration"
        }
        
        # ディレクトリ作成
        self.base_model_dir.mkdir(parents=True, exist_ok=True)
        for step_dir in self.step_dirs.values():
            step_dir.mkdir(parents=True, exist_ok=True)
            
        self._setup_logging()

    def _sanitize_model_name(self, model_name: str) -> str:
        """モデル名をサニタイズ"""
        return model_name.replace(" ", "_").replace(":", "_").replace("/", "_")

    def _setup_logging(self):
        """モデル固有のロガー設定"""
        self.logger = logging.getLogger(f"UniRigApp.{self.model_name}")
        self.logger.setLevel(logging.DEBUG)
        
        if not any(isinstance(h, logging.StreamHandler) for h in self.logger.handlers):
            console_handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(formatter)
            console_handler.setLevel(logging.INFO)
            self.logger.addHandler(console_handler)
        self.logger.propagate = False

    def save_uploaded_file(self, original_path: str, original_filename: str) -> Path:
        """アップロードファイルを保存"""
        target_path = self.base_model_dir / original_filename
        if target_path.exists():
            self.logger.warning(f"ファイルを上書き: {target_path}")
        shutil.copy(original_path, target_path)
        self.logger.info(f"ファイル保存: {target_path}")
        return target_path

    def get_uploaded_file_path(self, original_filename: str) -> Path:
        """アップロードファイルパス取得"""
        return self.base_model_dir / original_filename

    # === ファイルベース状態確認 ===
    def get_step_status(self, step: str) -> dict:
        """各ステップの完了状態をファイル存在で判定"""
        status = {"completed": False, "files": [], "message": "未実行"}
        
        if step == "step0":
            # Step0: アセット保存
            asset_file = self.step_dirs['step0'] / f"{self.model_name}.glb"
            metadata_file = self.step_dirs['step0'] / f"{self.model_name}_asset_metadata.json"
            if asset_file.exists() or metadata_file.exists():  # どちらかがあれば完了とみなす
                files = [str(f) for f in [asset_file, metadata_file] if f.exists()]
                status = {"completed": True, "files": files, "message": "アセット保存完了"}
                
        elif step == "step1":
            # Step1: メッシュ抽出 
            npz_file = self.step_dirs['step1'] / "raw_data.npz"
            if npz_file.exists():
                status = {"completed": True, "files": [str(npz_file)], "message": "メッシュ抽出完了"}
                
        elif step == "step2":
            # Step2: スケルトン生成
            skeleton_fbx = self.step_dirs['step2'] / f"{self.model_name}.fbx"
            skeleton_npz = self.step_dirs['step2'] / "predict_skeleton.npz"
            if skeleton_fbx.exists() or skeleton_npz.exists():  # どちらかがあれば完了
                files = [str(f) for f in [skeleton_fbx, skeleton_npz] if f.exists()]
                status = {"completed": True, "files": files, "message": "スケルトン生成完了"}
                
        elif step == "step3":
            # Step3: スキニング
            skinned_fbx = self.step_dirs['step3'] / f"{self.model_name}_skinned.fbx"
            if skinned_fbx.exists():
                status = {"completed": True, "files": [str(skinned_fbx)], "message": "スキニング完了"}
                
        elif step == "step4":
            # Step4: マージ
            merged_fbx = self.step_dirs['step4'] / f"{self.model_name}_merged.fbx"
            if merged_fbx.exists():
                status = {"completed": True, "files": [str(merged_fbx)], "message": "マージ完了"}
                
        elif step == "step5":
            # Step5: 最終統合
            final_fbx = self.step_dirs['step5'] / f"{self.model_name}_final.fbx"
            if final_fbx.exists():
                status = {"completed": True, "files": [str(final_fbx)], "message": "最終統合完了"}
        
        return status

    def get_pipeline_status(self) -> dict:
        """全パイプライン状態を取得"""
        return {
            "step0": self.get_step_status("step0"),
            "step1": self.get_step_status("step1"), 
            "step2": self.get_step_status("step2"),
            "step3": self.get_step_status("step3"),
            "step4": self.get_step_status("step4"),
            "step5": self.get_step_status("step5")
        }

    def reset_pipeline_state(self):
        """パイプライン状態リセット"""
        self.logger.info(f"パイプライン状態リセット: {self.model_name}")
        if self.base_model_dir.exists():
            try:
                shutil.rmtree(self.base_model_dir)
                self.logger.info(f"ディレクトリ削除: {self.base_model_dir}")
            except OSError as e:
                self.logger.error(f"ディレクトリ削除失敗: {e}")
        
        # 再作成
        self.base_model_dir.mkdir(parents=True, exist_ok=True)
        for step_dir in self.step_dirs.values():
            step_dir.mkdir(parents=True, exist_ok=True)

    def get_step_output_dir(self, step_key: str) -> Path:
        """ステップ出力ディレクトリ取得"""
        if step_key in self.step_dirs:
            return self.step_dirs[step_key]
        else:
            raise ValueError(f"Unknown step key: {step_key}")

# --- ステップ実行関数群 ---
def execute_step0(model_name: str, input_file_path: str) -> tuple[bool, str]:
    """Step0: アセット保存実行"""
    try:
        fm = SimpleFileManager(model_name)
        step0 = Step0AssetPreservation(model_name, fm.get_step_output_dir('step0'))
        success, logs, files = step0.preserve_assets(input_file_path, model_name)
        return success, logs
    except Exception as e:
        return False, f"Step0 エラー: {str(e)}"

def execute_step1(model_name: str, input_file_path: str) -> tuple[bool, str]:
    """Step1: メッシュ抽出実行"""
    try:
        fm = SimpleFileManager(model_name)
        step1 = Step1Extract(model_name, fm.get_step_output_dir('step1'))
        success, logs, files = step1.extract_mesh(input_file_path, model_name)
        return success, logs
    except Exception as e:
        return False, f"Step1 エラー: {str(e)}"

def execute_step2(model_name: str, gender: str) -> tuple[bool, str]:
    """Step2: スケルトン生成実行"""
    try:
        fm = SimpleFileManager(model_name)
        # Step1の出力を探す
        raw_data_npz = fm.step_dirs['step1'] / "raw_data.npz"
        if not raw_data_npz.exists():
            return False, "Step1の出力ファイル raw_data.npz が見つかりません"
        
        step2 = Step2Skeleton(model_name, fm.get_step_output_dir('step2'))
        success, logs, files = step2.generate_skeleton(model_name, gender, str(raw_data_npz))
        return success, logs
    except Exception as e:
        return False, f"Step2 エラー: {str(e)}"

def execute_step3(model_name: str) -> tuple[bool, str]:
    """Step3: スキニング実行"""
    try:
        fm = SimpleFileManager(model_name)
        # 必要ファイルの確認
        raw_data_npz = fm.step_dirs['step1'] / "raw_data.npz"
        skeleton_fbx = fm.step_dirs['step2'] / f"{model_name}.fbx"
        if not raw_data_npz.exists():
            return False, "Step1の出力ファイル raw_data.npz が見つかりません"
        if not skeleton_fbx.exists():
            return False, f"Step2の出力ファイル {model_name}.fbx が見つかりません"
        
        step3 = Step3UniRigSkinning(model_name, fm.get_step_output_dir('step3'))
        success, logs, files = step3.apply_skinning(model_name, str(raw_data_npz), str(skeleton_fbx))
        return success, logs
    except Exception as e:
        return False, f"Step3 エラー: {str(e)}"

def execute_step4(model_name: str) -> tuple[bool, str]:
    """Step4: マージ実行"""
    try:
        fm = SimpleFileManager(model_name)
        # 必要ファイルの確認
        skeleton_fbx = fm.step_dirs['step2'] / f"{model_name}.fbx"
        skinned_fbx = fm.step_dirs['step3'] / f"{model_name}_skinned.fbx"
        if not skeleton_fbx.exists():
            return False, f"Step2の出力ファイル {model_name}.fbx が見つかりません"
        if not skinned_fbx.exists():
            return False, f"Step3の出力ファイル {model_name}_skinned.fbx が見つかりません"
        
        step4 = Step4CrossPlatformMerge(model_name, fm.get_step_output_dir('step4'))
        success, logs, files = step4.merge_skeleton_skinning(model_name, {}, {"skeleton_fbx": str(skeleton_fbx)}, {"skinned_fbx": str(skinned_fbx)})
        return success, logs
    except Exception as e:
        return False, f"Step4 エラー: {str(e)}"

def execute_step5(model_name: str, original_file_path: str) -> tuple[bool, str]:
    """Step5: 最終統合実行"""
    try:
        fm = SimpleFileManager(model_name)
        # 必要ファイルの確認
        merged_fbx = fm.step_dirs['step4'] / f"{model_name}_merged.fbx"
        if not merged_fbx.exists():
            return False, f"Step4の出力ファイル {model_name}_merged.fbx が見つかりません"
        
        step5 = Step5ReliableUVMaterialTransfer(model_name, fm.get_step_output_dir('step5'))
        success, logs, files = step5.integrate_with_blender(model_name, original_file_path, str(merged_fbx))
        return success, logs
    except Exception as e:
        return False, f"Step5 エラー: {str(e)}"

# --- Gradio UI ---
def create_simple_ui():
    """シンプル化されたGradio UI作成"""
    
    with gr.Blocks(title="UniRig - シンプル化パイプライン") as demo:
        gr.Markdown("# UniRig シンプル化パイプライン")
        gr.Markdown("ファイルベース状態管理によるシンプル化されたパイプライン")
        
        with gr.Row():
            with gr.Column():
                # アップロード
                uploaded_file = gr.File(label="3Dモデルファイル (.glb, .fbx, .obj)")
                model_name_input = gr.Textbox(label="モデル名", value="bird", placeholder="例: bird")
                gender_input = gr.Radio(["neutral", "male", "female"], label="性別", value="neutral")
                
                # ステップ実行ボタン
                step0_btn = gr.Button("Step 0: アセット保存")
                step1_btn = gr.Button("Step 1: メッシュ抽出")
                step2_btn = gr.Button("Step 2: スケルトン生成")
                step3_btn = gr.Button("Step 3: スキニング")
                step4_btn = gr.Button("Step 4: マージ")
                step5_btn = gr.Button("Step 5: 最終統合")
                
                reset_btn = gr.Button("リセット", variant="secondary")
                
            with gr.Column():
                # 状態表示
                status_display = gr.Textbox(label="パイプライン状態", lines=10, interactive=False)
                log_display = gr.Textbox(label="実行ログ", lines=10, interactive=False)
                refresh_btn = gr.Button("状態更新")
        
        # --- イベントハンドラー ---
        def handle_upload(uploaded_file_info, model_name):
            if not uploaded_file_info or not model_name:
                return "アップロードファイルまたはモデル名が指定されていません"
            
            try:
                fm = SimpleFileManager(model_name)
                saved_path = fm.save_uploaded_file(uploaded_file_info.name, Path(uploaded_file_info.name).name)
                return f"アップロード完了: {saved_path}"
            except Exception as e:
                return f"アップロードエラー: {str(e)}"
        
        def get_status(model_name):
            if not model_name:
                return "モデル名が指定されていません"
            
            try:
                fm = SimpleFileManager(model_name)
                status = fm.get_pipeline_status()
                status_text = f"=== {model_name} パイプライン状態 ===\\n"
                for step, info in status.items():
                    status_text += f"{step}: {info['message']} ({len(info['files'])} files)\\n"
                    for file_path in info['files']:
                        status_text += f"  - {file_path}\\n"
                return status_text
            except Exception as e:
                return f"状態取得エラー: {str(e)}"
        
        def handle_step0(uploaded_file_info, model_name):
            if not uploaded_file_info or not model_name:
                return "アップロードファイルまたはモデル名が指定されていません"
            success, logs = execute_step0(model_name, uploaded_file_info.name)
            return f"Step0 {'成功' if success else '失敗'}: {logs}"
        
        def handle_step1(uploaded_file_info, model_name):
            if not uploaded_file_info or not model_name:
                return "アップロードファイルまたはモデル名が指定されていません"
            success, logs = execute_step1(model_name, uploaded_file_info.name)
            return f"Step1 {'成功' if success else '失敗'}: {logs}"
        
        def handle_step2(model_name, gender):
            if not model_name:
                return "モデル名が指定されていません"
            success, logs = execute_step2(model_name, gender)
            return f"Step2 {'成功' if success else '失敗'}: {logs}"
        
        def handle_step3(model_name):
            if not model_name:
                return "モデル名が指定されていません"
            success, logs = execute_step3(model_name)
            return f"Step3 {'成功' if success else '失敗'}: {logs}"
        
        def handle_step4(model_name):
            if not model_name:
                return "モデル名が指定されていません"
            success, logs = execute_step4(model_name)
            return f"Step4 {'成功' if success else '失敗'}: {logs}"
        
        def handle_step5(uploaded_file_info, model_name):
            if not uploaded_file_info or not model_name:
                return "アップロードファイルまたはモデル名が指定されていません"
            success, logs = execute_step5(model_name, uploaded_file_info.name)
            return f"Step5 {'成功' if success else '失敗'}: {logs}"
        
        def handle_reset(model_name):
            if not model_name:
                return "モデル名が指定されていません"
            try:
                fm = SimpleFileManager(model_name)
                fm.reset_pipeline_state()
                return f"パイプライン状態をリセットしました: {model_name}"
            except Exception as e:
                return f"リセットエラー: {str(e)}"
        
        # イベント接続
        uploaded_file.change(handle_upload, [uploaded_file, model_name_input], log_display)
        step0_btn.click(handle_step0, [uploaded_file, model_name_input], log_display)
        step1_btn.click(handle_step1, [uploaded_file, model_name_input], log_display)
        step2_btn.click(handle_step2, [model_name_input, gender_input], log_display)
        step3_btn.click(handle_step3, [model_name_input], log_display)
        step4_btn.click(handle_step4, [model_name_input], log_display)
        step5_btn.click(handle_step5, [uploaded_file, model_name_input], log_display)
        reset_btn.click(handle_reset, [model_name_input], log_display)
        refresh_btn.click(get_status, [model_name_input], status_display)
    
    return demo

# --- メイン実行 ---
def find_available_port(start_port=7860, max_attempts=10):
    """利用可能ポート検索"""
    for i in range(max_attempts):
        port = start_port + i
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(('0.0.0.0', port))
                app_logger.info(f"利用可能ポート: {port}")
                return port
        except OSError:
            continue
    raise RuntimeError(f"利用可能ポートが見つかりません (範囲: {start_port}-{start_port + max_attempts - 1})")

if __name__ == "__main__":
    app_logger.info("UniRig シンプル化パイプラインアプリケーション開始")
    
    try:
        port = find_available_port()
        demo = create_simple_ui()
        app_logger.info("Gradioインターフェース構築完了")
        
        demo.launch(
            server_name="0.0.0.0",
            server_port=port,
            share=False,
            debug=False,
            show_error=True
        )
    except Exception as e:
        app_logger.error(f"アプリケーション起動エラー: {e}", exc_info=True)
        sys.exit(1)
