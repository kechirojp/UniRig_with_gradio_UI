#!/usr/bin/env python3
"""
モデルマージの引数順序修正をテストするスクリプト
"""

import os
import sys
import logging

# Add src to path for imports
sys.path.append('/app/src')

from app import load_app_config, process_merge_model

def test_merge_with_fixed_arguments():
    """修正された引数順序でモデルマージをテスト"""
    
    print("=== モデルマージ引数順序修正テスト ===")
    
    # Load app configuration
    load_app_config()
    
    # Define test inputs (using existing pipeline_work data)
    original_model_path = "/app/examples/bird.glb"
    skinned_fbx_path = "/app/pipeline_work/03_skinning_output/bird/skinned_model.fbx"
    skinning_npz_path = "/app/pipeline_work/03_skinning_output/bird/predict_skin.npz"
    model_name = "bird"  # This should be the correct model name, not a file path
    
    print(f"オリジナルモデルパス: {original_model_path}")
    print(f"スキン済みFBXパス: {skinned_fbx_path}")
    print(f"スキニングNPZパス: {skinning_npz_path}")
    print(f"モデル名: {model_name}")
    print()
    
    # Validate input files exist
    if not os.path.exists(original_model_path):
        print(f"エラー: オリジナルモデルが見つかりません: {original_model_path}")
        return False
        
    if not os.path.exists(skinned_fbx_path):
        print(f"エラー: スキン済みFBXが見つかりません: {skinned_fbx_path}")
        return False
        
    if not os.path.exists(skinning_npz_path):
        print(f"エラー: スキニングNPZが見つかりません: {skinning_npz_path}")
        return False
    
    print("✓ すべての入力ファイルが存在します")
    print()
    
    # Define a simple progress function for testing
    def test_progress_fn(progress, desc=None):
        if desc:
            print(f"進行状況 {progress:.1%}: {desc}")
        else:
            print(f"進行状況: {progress:.1%}")
    
    try:
        print("モデルマージを実行中...")
        display_glb_path, logs, final_fbx_path = process_merge_model(
            original_model_path=original_model_path,
            skinned_fbx_path=skinned_fbx_path,
            skinning_npz_path=skinning_npz_path,
            model_name_for_output=model_name,  # Should be "bird", not a file path
            progress_fn=test_progress_fn
        )
        
        print("\n=== マージ処理ログ ===")
        print(logs)
        print("=== ログ終了 ===\n")
        
        if display_glb_path and final_fbx_path:
            print("✓ モデルマージ成功！")
            print(f"表示用GLBパス: {display_glb_path}")
            print(f"最終FBXパス: {final_fbx_path}")
            
            # Check if output files exist
            if os.path.exists(final_fbx_path):
                file_size = os.path.getsize(final_fbx_path)
                print(f"✓ 最終FBXファイル生成完了: {file_size:,} bytes")
            else:
                print("⚠ 最終FBXファイルが見つかりません")
                
            if display_glb_path and os.path.exists(display_glb_path):
                file_size = os.path.getsize(display_glb_path)
                print(f"✓ 表示用GLBファイル生成完了: {file_size:,} bytes")
            else:
                print("⚠ 表示用GLBファイルが見つかりません")
                
            return True
        else:
            print("✗ モデルマージに失敗しました")
            return False
            
    except Exception as e:
        print(f"✗ マージ処理中にエラーが発生: {str(e)}")
        import traceback
        print("詳細なエラー情報:")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    success = test_merge_with_fixed_arguments()
    
    if success:
        print("\n🎉 修正テスト成功: 引数順序の問題が解決されました！")
        sys.exit(0)
    else:
        print("\n❌ 修正テスト失敗: まだ問題が残っています")
        sys.exit(1)
