#!/usr/bin/env python3
"""
自動リギング機能のテスト
修正されたパス設定での動作確認
"""

import os
import sys
import datetime

# appモジュールのインポート
sys.path.append('/app')
from app import process_full_auto_rigging

def test_auto_rigging():
    """自動リギング機能をテストする"""
    print("=== 自動リギング機能テスト開始 ===")
    print(f"開始時刻: {datetime.datetime.now()}")
    
    # テスト用のモデルファイル
    test_model_path = "/app/examples/bird.glb"
    
    print(f"テストモデル: {test_model_path}")
    
    # モデルファイルの存在確認
    if not os.path.exists(test_model_path):
        print(f"エラー: テストモデルが見つかりません: {test_model_path}")
        return False
    
    print("✓ テストモデルファイル確認完了")
    
    # スクリプトファイルの存在確認
    script_paths = [
        "/app/launch/inference/generate_skeleton.sh",
        "/app/launch/inference/generate_skin.sh", 
        "/app/launch/inference/merge.sh"
    ]
    
    for script_path in script_paths:
        if os.path.exists(script_path):
            print(f"✓ スクリプト確認: {script_path}")
        else:
            print(f"✗ スクリプト不見: {script_path}")
            return False
    
    print("\n--- 自動リギング実行 ---")
    
    try:
        # 自動リギング機能を実行
        results = process_full_auto_rigging(
            original_model_path=test_model_path,
            gender="neutral",
            progress=None
        )
        
        # 結果の確認
        if len(results) >= 11:
            (skeleton_glb_path, skeleton_logs, skeleton_fbx_path, skeleton_txt_path,
             skinned_model_glb_path, skinning_logs, downloadable_skinned_model_path,
             merged_model_glb_path, merge_logs, downloadable_merged_model_path,
             final_log_message) = results
            
            print("\n=== 結果 ===")
            print(f"スケルトン GLB: {skeleton_glb_path}")
            print(f"スケルトン FBX: {skeleton_fbx_path}")
            print(f"スケルトン TXT: {skeleton_txt_path}")
            print(f"スキンモデル GLB: {skinned_model_glb_path}")
            print(f"スキンモデル ダウンロード可能: {downloadable_skinned_model_path}")
            print(f"マージモデル GLB: {merged_model_glb_path}")
            print(f"マージモデル ダウンロード可能: {downloadable_merged_model_path}")
            
            print("\n=== ログ ===")
            print("スケルトン生成ログ:")
            print(skeleton_logs)
            print("\nスキニングログ:")
            print(skinning_logs)
            print("\nマージログ:")
            print(merge_logs)
            print("\n最終ログ:")
            print(final_log_message)
            
            # ファイルの存在確認
            success_count = 0
            total_files = 0
            
            expected_files = [
                ("スケルトン GLB", skeleton_glb_path),
                ("スケルトン FBX", skeleton_fbx_path),
                ("スケルトン TXT", skeleton_txt_path),
                ("スキンモデル GLB", skinned_model_glb_path),
                ("スキンモデル ダウンロード", downloadable_skinned_model_path),
                ("マージモデル GLB", merged_model_glb_path),
                ("マージモデル ダウンロード", downloadable_merged_model_path)
            ]
            
            print("\n=== ファイル存在確認 ===")
            for desc, file_path in expected_files:
                total_files += 1
                if file_path and os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    print(f"✓ {desc}: {file_path} ({file_size} bytes)")
                    success_count += 1
                else:
                    print(f"✗ {desc}: {file_path} (存在しない)")
            
            print(f"\n成功率: {success_count}/{total_files} ({success_count/total_files*100:.1f}%)")
            
            if success_count == total_files:
                print("\n🎉 自動リギング機能テスト成功！")
                return True
            else:
                print(f"\n⚠️  部分的成功（{success_count}/{total_files}ファイル作成）")
                return success_count > 0
        else:
            print(f"エラー: 予期しない戻り値の数: {len(results)}")
            print(f"戻り値: {results}")
            return False
            
    except Exception as e:
        print(f"エラー: 自動リギング実行中に例外が発生: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_auto_rigging()
    print(f"\n=== テスト完了: {'成功' if success else '失敗'} ===")
    print(f"終了時刻: {datetime.datetime.now()}")
    exit(0 if success else 1)
