#!/usr/bin/env python3
"""
UniRig Gradioダウンロード機能修正テスト

Gradio 5.31.0対応の正しいファイルダウンロード実装をテスト
"""

import gradio as gr
from pathlib import Path
import tempfile
import shutil

def create_test_file():
    """テスト用のFBXファイルを作成"""
    test_dir = Path("/tmp/unirig_download_test")
    test_dir.mkdir(exist_ok=True)
    test_file = test_dir / "test_rigged_model.fbx"
    
    # 簡単なテキストベースのFBXファイルを作成
    with open(test_file, "w") as f:
        f.write("; FBX test file for UniRig download testing\n")
        f.write("; This simulates a rigged model output\n")
        f.write("FBXHeaderExtension: {\n")
        f.write("    FBXHeaderVersion: 1003\n")
        f.write("    FBXVersion: 7400\n")
        f.write("}\n")
    
    return test_file

# 現在のUniRigアプローチ（問題があるかもしれない方法）
def download_current_approach():
    """現在のapp.pyと同じ方法"""
    test_file = create_test_file()
    if test_file.exists():
        return str(test_file)  # 直接パスを文字列で返す
    return None

# 推奨されるアプローチ1: Gradio.File()の使用
def download_recommended_approach1():
    """推奨アプローチ1: ファイルオブジェクトを返す"""
    test_file = create_test_file()
    if test_file.exists():
        return test_file  # Pathオブジェクトを直接返す
    return None

# 推奨されるアプローチ2: update()を使用
def download_recommended_approach2():
    """推奨アプローチ2: gr.File.update()を使用"""
    test_file = create_test_file()
    if test_file.exists():
        return gr.File.update(value=str(test_file), visible=True)
    return gr.File.update(value=None, visible=False)

# 推奨されるアプローチ3: 一時ファイルコピー
def download_recommended_approach3():
    """推奨アプローチ3: 一時ディレクトリにコピー"""
    test_file = create_test_file()
    if test_file.exists():
        # Gradioの一時ディレクトリにコピー
        temp_file = Path(tempfile.gettempdir()) / f"unirig_download_{test_file.name}"
        shutil.copy2(test_file, temp_file)
        return str(temp_file)
    return None

def create_download_test_ui():
    """ダウンロードテスト用UI"""
    
    with gr.Blocks(title="UniRig Download Test", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# UniRig ダウンロード機能テスト")
        gr.Markdown("異なるアプローチでファイルダウンロードをテストします。")
        
        with gr.Row():
            with gr.Column():
                gr.Markdown("### 現在の方法")
                gr.Markdown("app.pyで使用されている方法")
                current_btn = gr.Button("現在の方法でダウンロード", variant="secondary")
                current_file = gr.File(label="ダウンロード (現在の方法)", visible=True)
                
            with gr.Column():
                gr.Markdown("### 推奨方法1")
                gr.Markdown("Pathオブジェクト直接返却")
                rec1_btn = gr.Button("推奨方法1でダウンロード", variant="primary")
                rec1_file = gr.File(label="ダウンロード (推奨方法1)", visible=True)
        
        with gr.Row():
            with gr.Column():
                gr.Markdown("### 推奨方法2")
                gr.Markdown("gr.File.update()使用")
                rec2_btn = gr.Button("推奨方法2でダウンロード", variant="primary")
                rec2_file = gr.File(label="ダウンロード (推奨方法2)", visible=True)
                
            with gr.Column():
                gr.Markdown("### 推奨方法3")
                gr.Markdown("一時ファイルコピー")
                rec3_btn = gr.Button("推奨方法3でダウンロード", variant="primary")
                rec3_file = gr.File(label="ダウンロード (推奨方法3)", visible=True)
        
        # イベント接続
        current_btn.click(download_current_approach, [], current_file)
        rec1_btn.click(download_recommended_approach1, [], rec1_file)
        rec2_btn.click(download_recommended_approach2, [], rec2_file)
        rec3_btn.click(download_recommended_approach3, [], rec3_file)
    
    return demo

if __name__ == "__main__":
    print("UniRig Gradio ダウンロード機能テストを開始...")
    demo = create_download_test_ui()
    demo.launch(server_name="0.0.0.0", server_port=7778, debug=True)
