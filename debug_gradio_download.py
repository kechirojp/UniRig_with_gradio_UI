#!/usr/bin/env python3
"""
Gradioダウンロード機能デバッグスクリプト
問題: ダウンロードボタンを押してもファイルがダウンロードされない

調査ポイント:
1. ファイルが実際に存在するか
2. Gradioがファイルにアクセスできるか
3. ファイルパス形式が正しいか
4. Gradio File コンポーネントの使用方法が正しいか
"""

import gradio as gr
from pathlib import Path
import os
import shutil
import tempfile
import logging

# 基本設定
app_logger = logging.getLogger("GradioDownloadDebug")
logging.basicConfig(level=logging.DEBUG)

# テスト用のファイル作成
TEST_DIR = Path("/tmp/gradio_test")
TEST_DIR.mkdir(exist_ok=True)

def create_test_file():
    """テスト用ファイルを作成"""
    test_file = TEST_DIR / "test_model.fbx"
    with open(test_file, "w") as f:
        f.write("# Test FBX file for Gradio download debugging\n")
        f.write("# This is not a real FBX file, just for testing\n")
    return test_file

def test_download_method1(file_path):
    """方法1: 直接パスを返す（現在の方法）"""
    if Path(file_path).exists():
        return str(file_path), f"[OK] ファイル準備完了: {file_path}"
    else:
        return None, f"[FAIL] ファイルが見つかりません: {file_path}"

def test_download_method2(file_path):
    """方法2: 一時ディレクトリにコピーして返す"""
    if not Path(file_path).exists():
        return None, f"[FAIL] ファイルが見つかりません: {file_path}"
    
    try:
        # 一時ディレクトリにコピー
        temp_dir = Path(tempfile.mkdtemp())
        temp_file = temp_dir / Path(file_path).name
        shutil.copy2(file_path, temp_file)
        
        return str(temp_file), f"[OK] 一時ファイル準備完了: {temp_file}"
    except Exception as e:
        return None, f"[FAIL] ファイルコピーエラー: {e}"

def test_download_method3(file_path):
    """方法3: Gradioの一時ディレクトリを使用"""
    if not Path(file_path).exists():
        return None, f"[FAIL] ファイルが見つかりません: {file_path}"
    
    try:
        # Gradioが自動的に処理できる形式で返す
        return file_path, f"[OK] ファイルパス返却: {file_path}"
    except Exception as e:
        return None, f"[FAIL] エラー: {e}"

def create_gradio_interface():
    """Gradioインターフェース作成"""
    
    # テストファイル作成
    test_file = create_test_file()
    print(f"テストファイル作成: {test_file}")
    
    with gr.Blocks(title="Gradio Download Debug") as demo:
        gr.Markdown("# Gradio ダウンロード機能デバッグ")
        
        with gr.Row():
            gr.Markdown(f"**テストファイル**: {test_file}")
        
        with gr.Column():
            gr.Markdown("## 方法1: 直接パス返却（現在の方法）")
            download_btn1 = gr.Button("方法1でダウンロード")
            download_file1 = gr.File(label="ダウンロードファイル1", visible=True)
            log1 = gr.Textbox(label="ログ1", lines=2)
            
        with gr.Column():
            gr.Markdown("## 方法2: 一時ディレクトリコピー")
            download_btn2 = gr.Button("方法2でダウンロード")
            download_file2 = gr.File(label="ダウンロードファイル2", visible=True)
            log2 = gr.Textbox(label="ログ2", lines=2)
            
        with gr.Column():
            gr.Markdown("## 方法3: ファイルパス直接指定")
            download_btn3 = gr.Button("方法3でダウンロード")
            download_file3 = gr.File(label="ダウンロードファイル3", visible=True)
            log3 = gr.Textbox(label="ログ3", lines=2)
        
        # イベント接続
        download_btn1.click(
            lambda: test_download_method1(str(test_file)),
            [],
            [download_file1, log1]
        )
        
        download_btn2.click(
            lambda: test_download_method2(str(test_file)),
            [],
            [download_file2, log2]
        )
        
        download_btn3.click(
            lambda: test_download_method3(str(test_file)),
            [],
            [download_file3, log3]
        )
    
    return demo

if __name__ == "__main__":
    print("Gradio ダウンロード機能デバッグを開始...")
    demo = create_gradio_interface()
    demo.launch(server_name="0.0.0.0", server_port=7777, debug=True)
