#!/usr/bin/env python3
"""
修正版自動リギング機能のテスト
短時間で結果を確認するための簡略版
"""

import os
import sys
import datetime
import tempfile
import subprocess

# appモジュールのインポート
sys.path.append('/app')

def test_scripts_directly():
    """スクリプトを直接実行してテストする"""
    print("=== スクリプト直接実行テスト ===")
    
    test_model = "/app/examples/bird.glb"
    temp_dir = tempfile.mkdtemp(prefix="unirig_test_")
    
    print(f"テストモデル: {test_model}")
    print(f"一時ディレクトリ: {temp_dir}")
    
    # Step 1: スケルトン生成
    skeleton_output = os.path.join(temp_dir, "skeleton.fbx")
    skeleton_txt = os.path.join(temp_dir, "skeleton.txt")
    
    print("\n--- Step 1: スケルトン生成 ---")
    cmd = [
        "bash", "/app/launch/inference/generate_skeleton.sh",
        "--input", test_model,
        "--output", skeleton_output,
        "--npz_dir", temp_dir
    ]
    
    print(f"実行コマンド: {' '.join(cmd)}")
    
    try:
        # タイムアウトを設定して実行
        result = subprocess.run(
            cmd, 
            cwd="/app", 
            capture_output=True, 
            text=True, 
            timeout=300  # 5分タイムアウト
        )
        
        print(f"リターンコード: {result.returncode}")
        if result.stdout:
            print("STDOUT:")
            print(result.stdout[-1000:])  # 最後の1000文字のみ表示
        if result.stderr:
            print("STDERR:")
            print(result.stderr[-1000:])  # 最後の1000文字のみ表示
        
        # 出力ファイルの確認
        if os.path.exists(skeleton_output):
            size = os.path.getsize(skeleton_output)
            print(f"✓ スケルトンファイル作成成功: {skeleton_output} ({size} bytes)")
            return True
        else:
            print(f"✗ スケルトンファイル作成失敗: {skeleton_output}")
            
            # npz_dirのファイルを確認
            print("NPZ ディレクトリの内容:")
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    full_path = os.path.join(root, file)
                    print(f"  {full_path}")
            
            return False
        
    except subprocess.TimeoutExpired:
        print("⚠️ タイムアウト: スケルトン生成が5分以内に完了しませんでした")
        return False
    except Exception as e:
        print(f"⚠️ 例外発生: {e}")
        return False

def test_auto_rigging_function():
    """自動リギング関数を直接テストする（短縮版）"""
    print("\n=== 自動リギング関数テスト ===")
    
    # 簡単なテストのため、事前に作成されたファイルを使用
    existing_skeleton = "/app/gradio_tmp_files/skeleton_output_fbx_20250528004115085428.fbx"
    existing_txt = None
    
    # スケルトンテキストファイルを探す
    for file in os.listdir("/app/tmp"):
        if file.endswith("bird") and os.path.isdir(f"/app/tmp/{file}"):
            txt_path = f"/app/tmp/{file}/skeleton_pred.txt"
            if os.path.exists(txt_path):
                existing_txt = txt_path
                break
    
    if os.path.exists(existing_skeleton) and existing_txt:
        print(f"✓ 既存のスケルトンファイル使用: {existing_skeleton}")
        print(f"✓ 既存のテキストファイル使用: {existing_txt}")
        
        # process_generate_skin関数をテスト
        try:
            from app import process_generate_skin
            
            result = process_generate_skin(
                original_model_path="/app/examples/bird.glb",
                skeleton_text_path=existing_txt,
                progress=None
            )
            
            if len(result) >= 3:
                skinned_glb, logs, downloadable = result
                print(f"スキニング結果 GLB: {skinned_glb}")
                print(f"スキニング結果 ダウンロード: {downloadable}")
                
                if skinned_glb and os.path.exists(skinned_glb):
                    size = os.path.getsize(skinned_glb)
                    print(f"✓ スキニング成功: {size} bytes")
                    return True
                else:
                    print("✗ スキニング失敗")
                    return False
            else:
                print(f"✗ 予期しない戻り値: {result}")
                return False
                
        except Exception as e:
            print(f"✗ スキニング処理エラー: {e}")
            import traceback
            traceback.print_exc()
            return False
    else:
        print(f"✗ 既存ファイルが見つかりません:")
        print(f"  スケルトン: {existing_skeleton} (存在: {os.path.exists(existing_skeleton)})")
        print(f"  テキスト: {existing_txt}")
        return False

def main():
    print("=== 自動リギング機能修正版テスト開始 ===")
    print(f"開始時刻: {datetime.datetime.now()}")
    
    # テスト1: スクリプト直接実行
    test1_success = test_scripts_directly()
    
    # テスト2: 関数テスト（条件付き）
    test2_success = test_auto_rigging_function()
    
    overall_success = test1_success or test2_success
    
    print(f"\n=== テスト結果 ===")
    print(f"スクリプトテスト: {'成功' if test1_success else '失敗'}")
    print(f"関数テスト: {'成功' if test2_success else '失敗'}")
    print(f"総合結果: {'成功' if overall_success else '失敗'}")
    print(f"終了時刻: {datetime.datetime.now()}")
    
    return overall_success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
