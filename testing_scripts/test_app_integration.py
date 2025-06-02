#!/usr/bin/env python3
"""
統合テクスチャ保持機能テスト
"""
import sys
import os
sys.path.append('/app')

def test_app_texture_merge():
    """app.pyのテクスチャマージ機能をテスト"""
    print("🔄 アプリケーション統合テクスチャ保持テスト")
    print("=" * 60)
    
    # 必要なパラメータを設定
    input_model_path = "/app/examples/bird.glb"
    skinned_fbx_path = "/app/final_test_results/tmp_test_skeleton_output.fbx"
    output_dir = "/app/pipeline_work/integration_test"
    model_name = "bird_integration"
    
    # 作業ディレクトリを作成
    os.makedirs(output_dir, exist_ok=True)
    
    # スキニング済みFBXファイルが存在するかチェック
    if not os.path.exists(skinned_fbx_path):
        print(f"❌ スキニング済みFBXファイルが見つかりません: {skinned_fbx_path}")
        print("🔄 スケルトン生成を実行します...")
        
        # 簡単なスケルトン生成実行
        import subprocess
        try:
            cmd = [
                "python", "/app/src/inference/run.py",
                "--input_model", input_model_path,
                "--output_fbx", skinned_fbx_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                print(f"❌ スケルトン生成失敗: {result.stderr}")
                return False
            print("✅ スケルトン生成完了")
        except Exception as e:
            print(f"❌ スケルトン生成エラー: {e}")
            return False
    
    # app.pyからテクスチャマージ機能をインポートしてテスト
    try:
        # まず設定を初期化
        from app import load_app_config
        load_app_config()
        
        from app import process_final_merge_with_textures
        
        print("🎨 テクスチャマージ機能を実行中...")
        result_tuple = process_final_merge_with_textures(
            skinned_fbx_path=skinned_fbx_path,
            original_model_path=input_model_path,
            model_name_for_output=model_name,
            progress_fn=lambda x, desc="": print(f"進行状況: {x:.0%} - {desc}")
        )
        
        # 結果のタプルを解析
        display_glb_path, logs, final_fbx_path = result_tuple
        
        if final_fbx_path and os.path.exists(final_fbx_path):
            print("✅ テクスチャマージ成功!")
            print(f"  GLB表示ファイル: {display_glb_path}")
            print(f"  最終FBXファイル: {final_fbx_path}")
            print(f"  ログ: {logs[-200:]}...")  # 最後の200文字のみ表示
            return True
        else:
            print("❌ テクスチャマージ失敗")
            print(f"  ログ: {logs}")
            return False
            
    except Exception as e:
        print(f"❌ テスト実行エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_app_texture_merge()
    print(f"\n🏁 統合テスト結果: {'成功' if success else '失敗'}")
    sys.exit(0 if success else 1)
