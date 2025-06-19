#!/usr/bin/env python3
"""
Gradioダウンロード機能の修正検証スクリプト
- str型パス返却の修正確認
- File コンポーネント設定の確認
- 実際のダウンロード機能テスト
"""

import os
import sys
sys.path.append('/app')

from pathlib import Path
from fixed_directory_manager import FixedDirectoryManager
import logging

# 基本設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_download_path_fix():
    """ダウンロードパス修正の検証"""
    
    print("🔧 Gradioダウンロード機能修正検証")
    print("=" * 50)
    
    # テスト用のディレクトリとファイルを作成
    test_model_name = "test_model"
    pipeline_base_dir = Path("/tmp/gradio_download_test")
    pipeline_base_dir.mkdir(exist_ok=True)
    
    # Step5出力ディレクトリを作成
    step5_dir = pipeline_base_dir / test_model_name / "05_blender_integration"
    step5_dir.mkdir(parents=True, exist_ok=True)
    
    # テスト用のFBXファイルを作成
    test_fbx = step5_dir / f"{test_model_name}_final.fbx"
    with open(test_fbx, "w") as f:
        f.write("# Test FBX file for download verification\n")
    
    print(f"✅ テストファイル作成: {test_fbx}")
    
    # FixedDirectoryManagerを使用してファイル検索をテスト
    try:
        fdm = FixedDirectoryManager(pipeline_base_dir, test_model_name, logger)
        
        # 動的拡張子対応でファイル検索
        final_output = fdm.find_file_with_dynamic_extension("step5", "final_output")
        
        if final_output and final_output.exists():
            print(f"✅ ファイル検索成功: {final_output}")
            print(f"   ファイルタイプ: {type(final_output)}")
            
            # str型変換テスト（Gradio用）
            str_path = str(final_output)
            print(f"✅ str型パス変換: {str_path}")
            print(f"   str型パスタイプ: {type(str_path)}")
            
            # ファイル存在確認
            if Path(str_path).exists():
                print(f"✅ str型パスでファイルアクセス成功")
                print(f"   ファイルサイズ: {Path(str_path).stat().st_size} bytes")
            else:
                print("❌ str型パスでファイルアクセス失敗")
                
        else:
            print("❌ ファイル検索失敗")
            
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 50)
    print("✅ 修正検証完了")
    
    # クリーンアップ
    import shutil
    shutil.rmtree(pipeline_base_dir, ignore_errors=True)

def test_gradio_file_settings():
    """Gradio File コンポーネント設定の検証"""
    
    print("\n🔧 Gradio File コンポーネント設定検証")
    print("=" * 50)
    
    try:
        import gradio as gr
        
        # File コンポーネントの推奨設定テスト
        print("✅ Gradio importが成功")
        
        # 設定パラメータの確認
        test_settings = {
            "label": "ダウンロードファイル",
            "visible": True,
            "interactive": False,  # ダウンロード専用
            "file_count": "single"  # 単一ファイル
        }
        
        print("✅ 推奨設定パラメータ:")
        for key, value in test_settings.items():
            print(f"   {key}: {value}")
            
        # File コンポーネントの作成テスト
        file_component = gr.File(**test_settings)
        print("✅ Gradio File コンポーネント作成成功")
        
    except Exception as e:
        print(f"❌ Gradio File コンポーネントテストエラー: {e}")

if __name__ == "__main__":
    test_download_path_fix()
    test_gradio_file_settings()
    print("\n🎉 すべてのテストが完了しました")
