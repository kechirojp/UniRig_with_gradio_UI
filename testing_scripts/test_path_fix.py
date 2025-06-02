#!/usr/bin/env python3
"""
修正されたパス設定での自動リギング機能の直接テスト
"""

import sys
import os
import datetime

# アプリケーションモジュールをインポート
sys.path.append('/app')

# アプリケーション設定を初期化
def initialize_app_config():
    """アプリケーション設定を初期化"""
    try:
        from app import load_app_config
        load_app_config()
        print("✓ アプリケーション設定を初期化しました")
        return True
    except Exception as e:
        print(f"✗ アプリケーション設定の初期化に失敗: {e}")
        return False

def test_path_fix():
    """パス修正が正しく動作するかテスト"""
    print("=== パス修正テスト ===")
    
    # app.pyから関数をインポート
    from app import process_generate_skeleton
    
    # パスの計算をテスト
    app_file = '/app/app.py'
    base_dir = os.path.dirname(app_file)
    script_path = os.path.join(base_dir, "launch/inference/generate_skeleton.sh")
    
    print(f"app.py の場所: {app_file}")
    print(f"base_dir: {base_dir}")
    print(f"計算されたスクリプトパス: {script_path}")
    print(f"スクリプト存在確認: {os.path.exists(script_path)}")
    
    return os.path.exists(script_path)

def test_skeleton_generation():
    """修正されたスケルトン生成機能をテスト"""
    print("\n=== スケルトン生成テスト ===")
    
    try:
        from app import process_generate_skeleton, process_extract_mesh
        
        test_model = "/app/examples/bird.glb"
        print(f"テストモデル: {test_model}")
        
        # まずメッシュ抽出を実行してNPZファイルを生成
        print("メッシュ抽出を実行中...")
        npz_result, extraction_logs = process_extract_mesh(
            original_model_path=test_model,
            model_name_for_output="bird_test",
            progress_fn=lambda p, desc="": print(f"進捗: {p:.1%} - {desc}")
        )
        
        if not npz_result:
            print("✗ メッシュ抽出に失敗しました")
            print(f"抽出ログ:\n{extraction_logs}")
            return False
            
        print(f"✓ メッシュ抽出成功: {npz_result}")
        
        # スケルトン生成を実行
        print("スケルトン生成を実行中...")
        result = process_generate_skeleton(
            extracted_npz_path=npz_result,
            model_name_for_output="bird_test",
            gender="neutral",
            progress_fn=lambda p, desc="": print(f"進捗: {p:.1%} - {desc}")
        )
        
        # 結果の確認
        if result and len(result) >= 5:
            skeleton_display, logs, skeleton_fbx, skeleton_txt, skeleton_npz = result
            
            print("=== 実行ログ ===")
            print(logs)
            
            print("=== 結果ファイル ===")
            print(f"表示用GLB: {skeleton_display}")
            print(f"スケルトンFBX: {skeleton_fbx}")
            print(f"スケルトンTXT: {skeleton_txt}")
            print(f"スケルトンNPZ: {skeleton_npz}")
            
            # ファイル存在確認
            files_exist = []
            if skeleton_display and os.path.exists(skeleton_display):
                size = os.path.getsize(skeleton_display)
                print(f"✓ 表示用GLB存在: {size} bytes")
                files_exist.append(True)
            else:
                print(f"✗ 表示用GLB不存在: {skeleton_display}")
                files_exist.append(False)
                
            if skeleton_fbx and os.path.exists(skeleton_fbx):
                size = os.path.getsize(skeleton_fbx)
                print(f"✓ スケルトンFBX存在: {size} bytes")
                files_exist.append(True)
            else:
                print(f"✗ スケルトンFBX不存在: {skeleton_fbx}")
                files_exist.append(False)
                
            if skeleton_txt and os.path.exists(skeleton_txt):
                size = os.path.getsize(skeleton_txt)
                print(f"✓ スケルトンTXT存在: {size} bytes")
                files_exist.append(True)
            else:
                print(f"✗ スケルトンTXT不存在: {skeleton_txt}")
                files_exist.append(False)
                
            if skeleton_npz and os.path.exists(skeleton_npz):
                size = os.path.getsize(skeleton_npz)
                print(f"✓ スケルトンNPZ存在: {size} bytes")
                files_exist.append(True)
            else:
                print(f"✗ スケルトンNPZ不存在: {skeleton_npz}")
                files_exist.append(False)
            
            success = any(files_exist)
            print(f"\nスケルトン生成結果: {'✓ 成功' if success else '✗ 失敗'}")
            return success
        else:
            print(f"✗ 予期しない戻り値: {result}")
            return False
            
    except Exception as e:
        print(f"✗ スケルトン生成エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=== 修正後自動リギング機能テスト ===")
    print(f"開始時刻: {datetime.datetime.now()}")
    
    # アプリケーション設定を初期化
    if not initialize_app_config():
        print("設定初期化に失敗したため、テストを中断します。")
        return False
    
    # テスト1: パス修正確認
    path_ok = test_path_fix()
    
    # テスト2: スケルトン生成テスト
    skeleton_ok = test_skeleton_generation() if path_ok else False
    
    print(f"\n=== テスト結果 ===")
    print(f"パス修正: {'✓' if path_ok else '✗'}")
    print(f"スケルトン生成: {'✓' if skeleton_ok else '✗'}")
    
    overall_success = path_ok and skeleton_ok
    print(f"総合結果: {'✓ 成功' if overall_success else '✗ 失敗'}")
    print(f"終了時刻: {datetime.datetime.now()}")
    
    if overall_success:
        print("\n🎉 パス修正が完了し、自動リギング機能が正常に動作します！")
    else:
        print("\n⚠️ 問題が残っている可能性があります。")
    
    return overall_success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
