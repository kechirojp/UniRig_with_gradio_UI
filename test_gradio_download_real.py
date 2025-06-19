#!/usr/bin/env python3
"""
実際のGradioダウンロード機能テスト
- 修正されたapp.pyの動作確認
- ダウンロードボタンの挙動テスト
"""

import gradio as gr
from pathlib import Path
import os
import tempfile
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_download_interface():
    """テスト用ダウンロードインターフェース"""
    
    # テスト用ファイルの作成
    test_dir = Path("/tmp/gradio_download_real_test")
    test_dir.mkdir(exist_ok=True)
    
    test_files = {
        "fbx": test_dir / "test_model.fbx",
        "glb": test_dir / "test_model.glb", 
        "obj": test_dir / "test_model.obj"
    }
    
    # テストファイル作成
    for ext, file_path in test_files.items():
        with open(file_path, "w") as f:
            f.write(f"# Test {ext.upper()} file for download testing\n")
            f.write(f"# File created for Gradio download verification\n")
            f.write(f"# Extension: .{ext}\n")
    
    def handle_download_test(file_type):
        """テスト用ダウンロード処理"""
        try:
            file_path = test_files.get(file_type)
            if file_path and file_path.exists():
                # 修正されたロジック: str型パスを返す
                return str(file_path), f"[OK] {file_type.upper()}ファイル準備完了: {file_path.name}"
            else:
                return None, f"[FAIL] {file_type.upper()}ファイルが見つかりません"
        except Exception as e:
            return None, f"[FAIL] エラー: {str(e)}"
    
    # Gradioインターフェース
    with gr.Blocks(title="Gradio Download Test", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🔧 Gradioダウンロード機能テスト")
        gr.Markdown("修正されたダウンロード機能の動作確認")
        
        with gr.Row():
            with gr.Column():
                gr.Markdown("## FBXファイルダウンロード")
                fbx_btn = gr.Button("📥 FBXダウンロード", variant="primary")
                fbx_file = gr.File(
                    label="FBXファイル", 
                    visible=True,
                    interactive=False,
                    file_count="single"
                )
                fbx_log = gr.Textbox(label="FBXログ", lines=2)
            
            with gr.Column():
                gr.Markdown("## GLBファイルダウンロード")
                glb_btn = gr.Button("📥 GLBダウンロード", variant="primary")
                glb_file = gr.File(
                    label="GLBファイル",
                    visible=True, 
                    interactive=False,
                    file_count="single"
                )
                glb_log = gr.Textbox(label="GLBログ", lines=2)
                
            with gr.Column():
                gr.Markdown("## OBJファイルダウンロード")
                obj_btn = gr.Button("📥 OBJダウンロード", variant="primary")
                obj_file = gr.File(
                    label="OBJファイル",
                    visible=True,
                    interactive=False, 
                    file_count="single"
                )
                obj_log = gr.Textbox(label="OBJログ", lines=2)
        
        # イベント接続
        fbx_btn.click(
            lambda: handle_download_test("fbx"),
            [],
            [fbx_file, fbx_log]
        )
        
        glb_btn.click(
            lambda: handle_download_test("glb"),
            [],
            [glb_file, glb_log]
        )
        
        obj_btn.click(
            lambda: handle_download_test("obj"),
            [],
            [obj_file, obj_log]
        )
        
        gr.Markdown("---")
        gr.Markdown("### 📋 テスト手順")
        gr.Markdown("""
        1. 各形式のダウンロードボタンをクリック
        2. ファイルコンポーネントにファイルが表示されることを確認
        3. ファイル名をクリックしてダウンロードが開始することを確認
        4. ブラウザのダウンロードフォルダにファイルが保存されることを確認
        """)
    
    return demo

if __name__ == "__main__":
    print("🚀 Gradio ダウンロード機能テストを開始...")
    demo = create_test_download_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7778,
        debug=True,
        show_error=True
    )
