#!/usr/bin/env python3
"""
UniRig WebUI Quick Start
app.pyが起動しない問題を回避するためのシンプルな起動スクリプト
"""

import sys
import os
from pathlib import Path

# パスを追加
sys.path.insert(0, '/app')

def quick_start():
    """迅速にapp.pyを起動する"""
    print("🚀 UniRig WebUI Quick Start")
    print("=" * 50)
    
    # 1. 基本チェック
    print("1. 環境チェック...")
    print(f"   Python: {sys.version.split()[0]}")
    print(f"   作業ディレクトリ: {os.getcwd()}")
    
    # 2. 必要ディレクトリの確認
    print("2. ディレクトリチェック...")
    pipeline_work = Path("/app/pipeline_work")
    if not pipeline_work.exists():
        pipeline_work.mkdir(parents=True, exist_ok=True)
        print("   pipeline_work ディレクトリを作成しました")
    
    # 3. app.pyのインポートを試行
    print("3. app.pyのインポート...")
    try:
        from app import create_simple_ui
        print("   [OK] app.py インポート成功")
    except Exception as e:
        print(f"   [FAIL] app.py インポートエラー: {e}")
        return False
    
    # 4. アプリケーション起動
    print("4. WebUI起動...")
    try:
        app = create_simple_ui()
        print("   [OK] Gradioアプリ作成成功")
        
        # ポート・ブラウザ設定（環境変数対応）
        port = int(os.getenv("UNIRIG_PORT", "7860"))
        auto_browser = os.getenv("UNIRIG_AUTO_BROWSER", "true").lower() == "true"
        
        print(f"\n🌐 WebUIを起動しています...")
        print(f"   アクセスURL: http://localhost:{port}")
        
        if auto_browser:
            print("   🚀 ブラウザが自動的に開きます...")
        else:
            print("   📌 ブラウザ自動起動は無効")
        
        print("   停止: Ctrl+C")
        print("=" * 50)
        
        app.launch(
            server_name="0.0.0.0",
            server_port=port,
            share=False,
            inbrowser=auto_browser,  # 環境変数で制御
            show_error=True,
            debug=False
        )
        
    except Exception as e:
        print(f"   [FAIL] WebUI起動エラー: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = quick_start()
    if not success:
        print("\n❌ 起動に失敗しました")
        sys.exit(1)
