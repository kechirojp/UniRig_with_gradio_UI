#!/usr/bin/env python3
"""
Gradio関数直接実行テスト（フォールバックモード）
Gradio APIを経由せず、関数を直接呼び出してフォールバックモードをテスト
"""

import os
import sys
import time

def test_direct_fallback_execution():
    """
    Gradio関数を直接実行してフォールバックモードをテスト
    """
    print("=" * 80)
    print("🚀 Gradio関数直接実行テスト（フォールバックモード）開始")
    print("=" * 80)
    
    try:
        # フォールバックモード環境変数設定
        os.environ['FORCE_FALLBACK_MODE'] = '1'
        os.environ['DISABLE_UNIRIG_LIGHTNING'] = '1'
        
        print("🔧 フォールバックモード環境設定完了")
        print(f"FORCE_FALLBACK_MODE: {os.environ.get('FORCE_FALLBACK_MODE')}")
        print(f"DISABLE_UNIRIG_LIGHTNING: {os.environ.get('DISABLE_UNIRIG_LIGHTNING')}")
        
        # app.pyから関数をインポート
        print("📦 アプリケーションモジュールをインポート中...")
        sys.path.insert(0, '/app')
        from app import gradio_full_auto_rigging, load_app_config
        
        # 設定読み込み
        print("⚙️ アプリケーション設定を読み込み中...")
        if not load_app_config():
            raise Exception("設定読み込みに失敗")
        
        # テストモデルパス
        test_model_path = "/app/examples/bird.glb"
        
        if not os.path.exists(test_model_path):
            raise FileNotFoundError(f"テストモデルが見つかりません: {test_model_path}")
        
        print(f"📂 テストモデル: {test_model_path}")
        print(f"📊 モデルサイズ: {os.path.getsize(test_model_path):,} bytes")
        
        # プログレス関数のモック
        def mock_progress(value, desc=None):
            print(f"🔄 進行状況: {value:.1%} - {desc or ''}")
        
        print("\n🔄 フルパイプライン処理開始（フォールバックモード）...")
        start_time = time.time()
        
        # フルパイプライン実行
        result = gradio_full_auto_rigging(
            uploaded_model_path=test_model_path,
            gender="neutral",
            progress=mock_progress
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n⏱️ 実行時間: {duration:.2f} 秒")
        
        # 結果の分析
        print("\n📋 フルパイプライン結果:")
        if isinstance(result, (list, tuple)):
            print(f"   - 結果要素数: {len(result)}")
            
            # 結果の各要素をチェック
            final_display = result[0] if len(result) > 0 else None
            logs = result[1] if len(result) > 1 else ""
            final_fbx = result[2] if len(result) > 2 else None
            
            print(f"   - 最終表示モデル: {final_display}")
            print(f"   - 最終FBXモデル: {final_fbx}")
            
            # 成功判定
            success = final_fbx is not None and final_fbx != ""
            print(f"   - 成功: {'✅' if success else '❌'}")
            
            # ログの最後の部分を表示
            if logs:
                print(f"\n📄 ログ（最後の800文字）:")
                log_preview = logs[-800:] if len(logs) > 800 else logs
                print(log_preview)
            
            # ファイル存在確認
            if final_fbx and os.path.exists(final_fbx):
                file_size = os.path.getsize(final_fbx)
                print(f"\n📁 最終FBXファイル確認:")
                print(f"   - パス: {final_fbx}")
                print(f"   - サイズ: {file_size:,} bytes")
                print(f"   - 存在: ✅")
            elif final_fbx:
                print(f"\n📁 最終FBXファイル確認:")
                print(f"   - パス: {final_fbx}")
                print(f"   - 存在: ❌")
            
            return success
        else:
            print(f"   - 予期しない結果形式: {type(result)} = {result}")
            return False
            
    except Exception as e:
        print(f"\n❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """
    メイン実行関数
    """
    success = test_direct_fallback_execution()
    
    print("\n" + "=" * 80)
    print("🎉 Gradio関数直接実行テスト（フォールバックモード） 完了")
    print("=" * 80)
    
    if success:
        print("\n🎯 総合判定: ✅ 成功")
        print("\n✅ フォールバックモードでパイプラインが正常動作しています")
    else:
        print("\n🎯 総合判定: ❌ 失敗")
        print("\n⚠️ フォールバックモードでも問題が発生しています")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
