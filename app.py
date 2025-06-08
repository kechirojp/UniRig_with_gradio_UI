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
import os
import logging
import gradio as gr
from pathlib import Path
import socket
import json
import shutil
from datetime import datetime

# 内部マイクロサービスモジュールのインポート
from step_modules.step0_asset_preservation import execute_step0
from step_modules.step1_extract import execute_step1
from step_modules.step2_skeleton import execute_step2
from step_modules.step3_skinning import execute_step3
from step_modules.step4_texture_integrated import Step4TextureIntegrated

# ===============================================
# 1. 基本設定 - 最小限の設定
# ===============================================

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 作業ディレクトリ設定（ファイル管理のみ）
APP_DIR = Path(__file__).parent
PIPELINE_DIR = APP_DIR / "pipeline_work"
PIPELINE_DIR.mkdir(exist_ok=True)

# パイプライン出力ディレクトリ（ファイル保存用）
ASSET_PRESERVATION_DIR = PIPELINE_DIR / "00_asset_preservation"
EXTRACT_DIR = PIPELINE_DIR / "01_extracted_mesh"
SKELETON_DIR = PIPELINE_DIR / "02_skeleton"
SKINNING_DIR = PIPELINE_DIR / "03_skinning"
MERGE_DIR = PIPELINE_DIR / "04_merge"

for directory in [ASSET_PRESERVATION_DIR, EXTRACT_DIR, SKELETON_DIR, SKINNING_DIR, MERGE_DIR]:
    directory.mkdir(exist_ok=True)

# ===============================================
# 2. データ管理 - ファイル状態のみ管理
# ===============================================

class FileManager:
    """ファイル状態管理（UIとファイルシステムの橋渡し）"""
    
    def __init__(self):
        self.uploaded_files = {}
        self.generated_files = {}
        self.pipeline_state = {
            "step0_complete": False,
            "step1_complete": False,
            "step2_complete": False,
            "step3_complete": False,
            "step4_complete": False,
            "current_model": None
        }
    
    def save_uploaded_file(self, file_path: str, model_name: str) -> str:
        """アップロードファイルの保存"""
        if not file_path:
            return None
        
        # ファイル情報を記録
        self.uploaded_files[model_name] = {
            "original_path": file_path,
            "upload_time": datetime.now().isoformat(),
            "status": "uploaded"
        }
        
        self.pipeline_state["current_model"] = model_name
        return file_path
    
    def get_file_status(self, model_name: str) -> dict:
        """ファイル状態の取得"""
        return {
            "uploaded": model_name in self.uploaded_files,
            "pipeline_state": self.pipeline_state.copy(),
            "files": self.generated_files.get(model_name, {})
        }
    
    def get_step_files(self, step: int) -> dict:
        """ステップの出力ファイル取得"""
        if self.pipeline_state["current_model"]:
            return self.generated_files.get(self.pipeline_state["current_model"], {})
        return {}
    
    def mark_step_complete(self, step: int, output_files: dict):
        """ステップ完了マーク"""
        self.pipeline_state[f"step{step}_complete"] = True
        
        if self.pipeline_state["current_model"]:
            if self.pipeline_state["current_model"] not in self.generated_files:
                self.generated_files[self.pipeline_state["current_model"]] = {}
            
            self.generated_files[self.pipeline_state["current_model"]].update(output_files)

# グローバルファイルマネージャー
file_manager = FileManager()

# ===============================================
# 3. 内部マイクロサービス呼び出し - モジュール連携層
# ===============================================

def call_step0_asset_preservation(input_file: str, model_name: str) -> tuple[bool, str, dict]:
    """ステップ0内部モジュール呼び出し（アセット保存）"""
    
    try:
        logger.info(f"Step 0 開始: {input_file} → {model_name}")
        
        # 内部モジュール実行
        success, logs, output_files = execute_step0(
            input_file=input_file,
            model_name=model_name,
            output_dir=str(ASSET_PRESERVATION_DIR)
        )
        
        if success:
            file_manager.mark_step_complete(0, output_files)
            logger.info(f"Step 0 完了: {output_files}")
        else:
            logger.error(f"Step 0 失敗: {logs}")
        
        return success, logs, output_files
        
    except Exception as e:
        error_msg = f"Step 0 内部モジュール呼び出しエラー: {e}"
        logger.error(error_msg)
        return False, error_msg, {}

def call_step1_extract(input_file: str, model_name: str) -> tuple[bool, str, dict]:
    """ステップ1内部モジュール呼び出し（メッシュ抽出）"""
    
    try:
        logger.info(f"Step 1 開始: {input_file} → {model_name}")
        
        # current_modelを設定
        file_manager.pipeline_state["current_model"] = model_name
        
        # 内部モジュール実行
        success, logs, output_files = execute_step1(
            input_file=input_file,
            model_name=model_name,
            output_dir=EXTRACT_DIR,
            preserve_textures=True
        )
        
        if success:
            file_manager.mark_step_complete(1, output_files)
            logger.info(f"Step 1 完了: {output_files}")
        else:
            logger.error(f"Step 1 失敗: {logs}")
        
        return success, logs, output_files
        
    except Exception as e:
        error_msg = f"Step 1 内部モジュール呼び出しエラー: {e}"
        logger.error(error_msg)
        return False, error_msg, {}

def call_step2_skeleton(model_name: str, gender: str) -> tuple[bool, str, dict]:
    """ステップ2内部モジュール呼び出し（スケルトン生成）"""
    
    try:
        logger.info(f"Step 2 開始: {model_name} (gender: {gender})")
        
        # Step 1の出力ファイルを直接指定
        mesh_file = EXTRACT_DIR / "raw_data.npz"
        logger.info(f"Step 2: 探索ファイルパス = {mesh_file}")
        logger.info(f"Step 2: ファイル存在チェック = {mesh_file.exists()}")
        
        if not mesh_file.exists():
            logger.error(f"Step 2: EXTRACT_DIR = {EXTRACT_DIR}")
            logger.error(f"Step 2: ファイル一覧 = {list(EXTRACT_DIR.glob('*'))}")
            return False, f"Step 1の出力ファイルが見つかりません: {mesh_file}", {}
        
        # 内部モジュール実行
        logger.info(f"Step 2: execute_step2 呼び出し開始")
        success, logs, output_files = execute_step2(
            mesh_file=str(mesh_file),
            model_name=model_name,
            output_dir=SKELETON_DIR,
            gender=gender
        )
        
        if success:
            file_manager.mark_step_complete(2, output_files)
            logger.info(f"Step 2 完了: {output_files}")
        else:
            logger.error(f"Step 2 失敗: {logs}")
        
        return success, logs, output_files
        
    except Exception as e:
        error_msg = f"Step 2 内部モジュール呼び出しエラー: {e}"
        logger.error(error_msg)
        return False, error_msg, {}
        return False, error_msg, {}

def call_step3_skinning(model_name: str) -> tuple[bool, str, dict]:
    """ステップ3内部モジュール呼び出し（スキニング適用）"""
    
    try:
        logger.info(f"Step 3 開始: {model_name}")
        
        # Step 1, 2の実際の出力ファイルパス
        mesh_file = EXTRACT_DIR / "raw_data.npz"
        skeleton_file = SKELETON_DIR / f"{model_name}_skeleton.fbx"
        
        if not mesh_file.exists():
            return False, f"Step 1の出力ファイルが見つかりません: {mesh_file}", {}
        if not skeleton_file.exists():
            return False, f"Step 2の出力ファイルが見つかりません: {skeleton_file}", {}
        
        # 内部モジュール実行
        success, logs, output_files = execute_step3(
            mesh_file=str(mesh_file),
            skeleton_file=str(skeleton_file),
            model_name=model_name,
            output_dir=SKINNING_DIR
        )
        
        if success:
            file_manager.mark_step_complete(3, output_files)
            logger.info(f"Step 3 完了: {output_files}")
        else:
            logger.error(f"Step 3 失敗: {logs}")
        
        return success, logs, output_files
        
    except Exception as e:
        error_msg = f"Step 3 内部モジュール呼び出しエラー: {e}"
        logger.error(error_msg)
        return False, error_msg, {}

def call_step4_texture(model_name: str) -> tuple[bool, str, dict]:
    """ステップ4内部モジュール呼び出し（テクスチャ統合）- モック版"""
    
    try:
        logger.info(f"Step 4 開始: {model_name}")
        
        # Step 3の出力ファイル
        skinned_fbx = SKINNING_DIR / f"{model_name}_skinned.fbx"
        
        if not skinned_fbx.exists():
            return False, f"Step 3の出力ファイルが見つかりません: {skinned_fbx}", {}
        
        # モック版の最終ファイル（とりあえずStep3の出力をコピー）
        final_fbx = MERGE_DIR / f"{model_name}_final.fbx"
        MERGE_DIR.mkdir(exist_ok=True)
        
        import shutil
        shutil.copy2(skinned_fbx, final_fbx)
        
        output_files = {"final_fbx": str(final_fbx)}
        file_manager.mark_step_complete(4, output_files)
        
        return True, f"Step 4 モック完了: {final_fbx}", output_files
        
    except Exception as e:
        error_msg = f"Step 4 内部モジュール呼び出しエラー: {e}"
        logger.error(error_msg)
        return False, error_msg, {}
        
        if success:
            file_manager.mark_step_complete(4, output_files)
            logger.info(f"Step 4 完了: {output_files}")
        else:
            logger.error(f"Step 4 失敗: {logs}")
        
        return success, logs, output_files
        
    except Exception as e:
        error_msg = f"Step 4 内部モジュール呼び出しエラー: {e}"
        logger.error(error_msg)
        return False, error_msg, {}

def call_step4_texture_v2(model_name: str) -> tuple[bool, str, dict]:
    """ステップ4内部モジュール呼び出し（テクスチャ統合 - v2版）"""
    
    try:
        logger.info(f"Step 4 v2開始: {model_name}")
        
        # Step 3の出力ファイルを状態管理から取得
        step3_files = file_manager.get_step_files(3)
        skinned_fbx = step3_files.get("skinned_fbx")
        
        if not skinned_fbx or not Path(skinned_fbx).exists():
            return False, f"Step 3の出力ファイルが見つかりません: {skinned_fbx}", {}
        
        # オリジナルファイルパスの取得
        original_model = None
        if file_manager.pipeline_state["current_model"]:
            uploaded_info = file_manager.uploaded_files.get(file_manager.pipeline_state["current_model"])
            if uploaded_info:
                original_model = uploaded_info["original_path"]
        
        if not original_model:
            return False, "オリジナルモデルファイルの情報が見つかりません", {}
        
        # メタデータファイルの確認
        metadata_file = ASSET_PRESERVATION_DIR / model_name / f"{model_name}_asset_metadata.json"
        
        # Step4統合モジュールのインスタンス作成
        step4_module = Step4TextureIntegrated(MERGE_DIR)
        
        # 内部モジュール実行 (統合版)
        success, logs, output_files = step4_module.merge_textures(
            skinned_fbx=skinned_fbx,
            original_model=original_model,
            model_name=model_name,
            metadata_file=str(metadata_file) if metadata_file.exists() else None
        )
        
        if success:
            file_manager.mark_step_complete(4, output_files)
            logger.info(f"Step 4 統合版完了: {output_files}")
        else:
            logger.error(f"Step 4 統合版失敗: {logs}")
        
        return success, logs, output_files
        
    except Exception as e:
        error_msg = f"Step 4 v2内部モジュール呼び出しエラー: {e}"
        logger.error(error_msg)
        return False, error_msg, {}

# ===============================================
# 4. UI処理関数 - データ受け渡しのみ
# ===============================================

def process_complete_pipeline(input_file, gender: str = "neutral"):
    """
    完全パイプライン実行 - マイクロサービス版
    各ステップをマイクロサービスとして呼び出し
    """
    if not input_file:
        return "❌ ファイルがアップロードされていません", None
    
    # モデル名の生成
    model_name = Path(input_file.name).stem
    
    # アップロードファイルを保存
    file_manager.save_uploaded_file(input_file.name, model_name)
    
    logs = []
    
    try:
        # Step 0: アセット保存（内部モジュール）
        logs.append("=== ステップ 0: アセット保存 開始 ===")
        success, step_logs, output_files = call_step0_asset_preservation(input_file.name, model_name)
        logs.append(step_logs)
        
        if not success:
            logs.append("❌ ステップ 0 でエラーが発生しました")
            return "\n".join(logs), None
        logs.append("✅ ステップ 0 完了")
        
        # Step 1: メッシュ抽出（内部モジュール）
        logs.append("\n=== ステップ 1: メッシュ抽出 開始 ===")
        success, step_logs, output_files = call_step1_extract(input_file.name, model_name)
        logs.append(step_logs)
        
        if not success:
            logs.append("❌ ステップ 1 でエラーが発生しました")
            return "\n".join(logs), None
        logs.append("✅ ステップ 1 完了")
        
        # Step 2: スケルトン生成（内部モジュール）
        logs.append("\n=== ステップ 2: スケルトン生成 開始 ===")
        success, step_logs, output_files = call_step2_skeleton(model_name, gender)
        logs.append(step_logs)
        
        if not success:
            logs.append("❌ ステップ 2 でエラーが発生しました")
            return "\n".join(logs), None
        logs.append("✅ ステップ 2 完了")
        
        # Step 3: スキニング生成（内部モジュール）
        logs.append("\n=== ステップ 3: スキニング生成 開始 ===")
        success, step_logs, output_files = call_step3_skinning(model_name)
        logs.append(step_logs)
        
        if not success:
            logs.append("❌ ステップ 3 でエラーが発生しました")
            return "\n".join(logs), None
        logs.append("✅ ステップ 3 完了")
        
        # Step 4: 最終統合（内部モジュール - モック版）
        logs.append("\n=== ステップ 4: 最終統合 開始 ===")
        success, step_logs, output_files = call_step4_texture(model_name)
        logs.append(step_logs)
        
        if not success:
            logs.append("❌ ステップ 4 でエラーが発生しました")
            return "\n".join(logs), None
        logs.append("✅ ステップ 4 完了")
        
        # 最終ファイルパスを取得
        final_fbx = output_files.get("final_fbx")
        
        logs.append("\n🎉 自動リギング完了！アニメーション可能なモデルが生成されました。")
        return "\n".join(logs), final_fbx
        
    except Exception as e:
        error_msg = f"❌ パイプライン実行中にエラーが発生しました: {e}"
        logs.append(error_msg)
        logger.error(error_msg)
        return "\n".join(logs), None

# ===============================================
# 5. 段階別処理関数 - マイクロサービス版
# ===============================================

# ステップバイステップ実行用の状態管理（簡略化）
stepwise_state = {
    "current_model": None
}

def process_step0_only(input_file):
    """ステップ0のみ実行: アセット保存（内部モジュール）"""
    if not input_file:
        return "❌ ファイルがアップロードされていません", None
    
    model_name = Path(input_file.name).stem
    stepwise_state["current_model"] = model_name
    
    success, logs, output_files = call_step0_asset_preservation(input_file.name, model_name)
    
    if success:
        return f"✅ アセット保存完了:\n{logs}", output_files.get("asset_metadata_json")
    else:
        return f"❌ アセット保存失敗:\n{logs}", None

def process_step1_only(input_file):
    """ステップ1のみ実行: メッシュ抽出（内部モジュール）"""
    if not input_file:
        return "❌ ファイルがアップロードされていません", None
    
    model_name = Path(input_file.name).stem
    stepwise_state["current_model"] = model_name
    # file_managerにも設定
    file_manager.pipeline_state["current_model"] = model_name
    
    success, logs, output_files = call_step1_extract(input_file.name, model_name)
    
    if success:
        extracted_file = output_files.get("extracted_mesh")
        return f"Step 1完了: {extracted_file}", extracted_file
    else:
        return f"❌ ステップ 1 失敗\n{logs}", None

def process_step2_only(gender):
    """ステップ2のみ実行: スケルトン生成（内部モジュール）"""
    model_name = stepwise_state.get("current_model")
    if not model_name:
        return "❌ 先にステップ 1を実行してください", None, None
    
    success, logs, output_files = call_step2_skeleton(model_name, gender)
    
    if success:
        skeleton_fbx = output_files.get("skeleton_fbx")
        skeleton_npz = output_files.get("skeleton_npz")
        return f"✅ ステップ 2 完了\n{logs}", skeleton_fbx, skeleton_npz
    else:
        return f"❌ ステップ 2 失敗\n{logs}", None, None

def process_step3_only():
    """ステップ3のみ実行: スキニング生成（内部モジュール）"""
    model_name = stepwise_state.get("current_model")
    if not model_name:
        return "❌ 先にステップ 1, 2を実行してください", None, None
    
    success, logs, output_files = call_step3_skinning(model_name)
    
    if success:
        skinned_fbx = output_files.get("skinned_fbx")
        skinning_npz = output_files.get("skinning_npz")
        return f"✅ ステップ 3 完了\n{logs}", skinned_fbx, skinning_npz
    else:
        return f"❌ ステップ 3 失敗\n{logs}", None, None

def process_step4_only():
    """ステップ4のみ実行: 最終統合（内部モジュール）"""
    model_name = stepwise_state.get("current_model")
    if not model_name:
        return "❌ 先にステップ 1, 2, 3を実行してください", None
    
    success, logs, output_files = call_step4_texture(model_name)
    
    if success:
        final_fbx = output_files.get("final_fbx")
        return f"✅ ステップ 4 完了\n{logs}", final_fbx
    else:
        return f"❌ ステップ 4 失敗\n{logs}", None

# ===============================================
# 6. Gradio UI - 簡素化版
# ===============================================

def create_ui():
    """マイクロサービス対応UI - データ受け渡し特化版"""
    
    with gr.Blocks(
        title="UniRig MVP - マイクロサービス フロントエンド",
        theme=gr.themes.Default()
    ) as app:
        
        gr.Markdown("""
        # 🎯 UniRig MVP - 内部マイクロサービス フロントエンド
        
        **基本機能のみ: UI + データ受け渡し特化設計**
        
        - 🧩 各処理ステップは独立した内部モジュールとして動作
        - 📊 フロントエンドはファイル管理とUI表示のみ担当
        - 🔄 内部関数呼び出しでモジュールと通信
        - ⚡ 軽量・高速・拡張性に優れた設計
        
        ### 🧱 内部モジュール構成
        ```
        Step 0 (アセット保存): step_modules.step0_asset_preservation
        Step 1 (メッシュ抽出): step_modules.step1_extract
        Step 2 (スケルトン生成): step_modules.step2_skeleton  
        Step 3 (スキニング適用): step_modules.step3_skinning
        Step 4 (テクスチャ統合): step_modules.step4_texture
        ```
        """)
        
        with gr.Tabs():
            # =================================
            # タブ1: 自動実行
            # =================================
            with gr.TabItem("🚀 自動リギング実行"):
                gr.Markdown("""
                ### ワンクリック自動リギング
                内部マイクロサービス経由で全4ステップを自動実行します。
                """)
                
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("#### 📁 入力設定")
                        complete_input_file = gr.File(
                            label="3Dモデルファイル",
                            file_types=[".glb", ".fbx", ".obj", ".gltf", ".ply"],
                            type="filepath"
                        )
                        
                        complete_gender = gr.Radio(
                            choices=["neutral", "male", "female"],
                            value="neutral",
                            label="性別設定"
                        )
                        
                        complete_run_button = gr.Button(
                            "🚀 自動リギング開始",
                            variant="primary",
                            size="lg"
                        )
                        
                    with gr.Column(scale=2):
                        output_log = gr.Textbox(
                            label="実行ログ（マイクロサービス通信含む）",
                            lines=15,
                            max_lines=20,
                            placeholder="ここにマイクロサービスからのレスポンスが表示されます..."
                        )
                
                gr.Markdown("#### 📥 最終出力ファイル")
                complete_final = gr.File(label="🎯 リギング完了モデル (.fbx)", file_count="single")
            
            # =================================
            # タブ2: ステップバイステップ実行
            # =================================
            with gr.TabItem("🔧 段階別実行"):
                gr.Markdown("""
                ### 段階別内部モジュール実行
                各ステップを個別の内部モジュールとして実行・確認できます。
                """)
                
                # Step 0: アセット保存
                gr.Markdown("#### ステップ 0: アセット保存モジュール")
                with gr.Row():
                    with gr.Column(scale=1):
                        step0_input = gr.File(
                            label="3Dモデルファイル",
                            file_types=[".glb", ".fbx", ".obj", ".gltf", ".ply"],
                            type="filepath"
                        )
                        step0_button = gr.Button("内部モジュール実行", variant="secondary")
                    
                    with gr.Column(scale=2):
                        step0_logs = gr.Textbox(label="モジュール出力", lines=3)
                        step0_output = gr.File(label="アセットメタデータ (.json)")
                
                # Step 1: メッシュ抽出
                gr.Markdown("#### ステップ 1: メッシュ抽出モジュール")
                with gr.Row():
                    with gr.Column(scale=1):
                        step1_input = gr.File(
                            label="3Dモデルファイル",
                            file_types=[".glb", ".fbx", ".obj", ".gltf", ".ply"],
                            type="filepath"
                        )
                        step1_button = gr.Button("内部モジュール実行", variant="secondary")
                    
                    with gr.Column(scale=2):
                        step1_logs = gr.Textbox(label="モジュール出力", lines=3)
                        step1_output = gr.File(label="抽出メッシュ (.npz)")
                
                # Step 2: スケルトン生成
                gr.Markdown("#### ステップ 2: スケルトン生成モジュール")
                with gr.Row():
                    with gr.Column(scale=1):
                        step2_gender = gr.Radio(
                            choices=["neutral", "male", "female"],
                            value="neutral",
                            label="性別設定"
                        )
                        step2_button = gr.Button("内部モジュール実行", variant="secondary")
                    
                    with gr.Column(scale=2):
                        step2_logs = gr.Textbox(label="モジュール出力", lines=3)
                        with gr.Row():
                            step2_skeleton_fbx = gr.File(label="スケルトン (.fbx)")
                            step2_skeleton_npz = gr.File(label="スケルトンデータ (.npz)")
                
                # Step 3: スキニング生成
                gr.Markdown("#### ステップ 3: スキニング生成モジュール")
                with gr.Row():
                    with gr.Column(scale=1):
                        step3_button = gr.Button("内部モジュール実行", variant="secondary")
                    
                    with gr.Column(scale=2):
                        step3_logs = gr.Textbox(label="モジュール出力", lines=3)
                        with gr.Row():
                            step3_skinned_fbx = gr.File(label="リギング済み (.fbx)")
                            step3_skinning_npz = gr.File(label="スキニングデータ (.npz)")
                
                # Step 4: 最終統合
                gr.Markdown("#### ステップ 4: 最終統合モジュール")
                with gr.Row():
                    with gr.Column(scale=1):
                        step4_button = gr.Button("内部モジュール実行", variant="secondary")
                    
                    with gr.Column(scale=2):
                        step4_logs = gr.Textbox(label="モジュール出力", lines=3)
                        step4_final_fbx = gr.File(label="最終モデル (.fbx)")
        
        # =================================
        # イベント処理: 自動実行
        # =================================
        complete_run_button.click(
            fn=process_complete_pipeline,
            inputs=[complete_input_file, complete_gender],
            outputs=[
                output_log,
                complete_final
            ]
        )
        
        # =================================
        # イベント処理: 段階別実行
        # =================================
        step0_button.click(
            fn=process_step0_only,
            inputs=[step0_input],
            outputs=[step0_logs, step0_output]
        )
        
        step1_button.click(
            fn=process_step1_only,
            inputs=[step1_input],
            outputs=[step1_logs, step1_output]
        )
        
        step2_button.click(
            fn=process_step2_only,
            inputs=[step2_gender],
            outputs=[step2_logs, step2_skeleton_fbx, step2_skeleton_npz]
        )
        
        step3_button.click(
            fn=process_step3_only,
            inputs=[],
            outputs=[step3_logs, step3_skinned_fbx, step3_skinning_npz]
        )
        
        step4_button.click(
            fn=process_step4_only,
            inputs=[],
            outputs=[step4_logs, step4_final_fbx]
        )
    
    return app

# ===============================================
# 7. アプリケーション起動
# ===============================================

def find_available_port(start_port=7860, max_attempts=100):
    """利用可能なポートを見つける"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"利用可能なポートが見つかりません (範囲: {start_port}-{start_port + max_attempts})")

def main():
    """アプリケーションメイン"""
    logger.info("UniRig MVP 起動中...")
    
    # 利用可能なポートを自動検出
    try:
        port = find_available_port()
        logger.info(f"利用可能なポート発見: {port}")
    except RuntimeError as e:
        logger.error(f"ポート検出エラー: {e}")
        return
    
    # UI作成
    app = create_ui()
    
    # サーバー起動
    app.launch(
        server_name="0.0.0.0",
        server_port=port,
        share=False,
        debug=True,
        show_error=True
    )

if __name__ == "__main__":
    main()
