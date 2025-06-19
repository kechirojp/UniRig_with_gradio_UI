#!/usr/bin/env python3
"""
🚀 UniRig WebUI ブラウザ自動起動ランチャー

このスクリプトを実行すると：
1. app.pyが起動
2. ブラウザが自動的に開く
3. WebUIがすぐに使用可能
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path

def main():
    """メイン起動処理"""
    parser = argparse.ArgumentParser(description="UniRig WebUI ブラウザ自動起動ランチャー")
    parser.add_argument(
        "--no-browser", 
        action="store_true", 
        help="ブラウザ自動起動を無効化"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=7860, 
        help="起動ポート (デフォルト: 7860)"
    )
    parser.add_argument(
        "--quick", 
        action="store_true", 
        help="quick_start_app.pyを使用（高速起動）"
    )
    
    args = parser.parse_args()
    
    print("🚀 UniRig WebUI ブラウザ自動起動ランチャー")
    print("=" * 60)
    
    # 環境変数設定
    if args.no_browser:
        os.environ["UNIRIG_AUTO_BROWSER"] = "false"
        print("📌 ブラウザ自動起動: 無効")
    else:
        os.environ["UNIRIG_AUTO_BROWSER"] = "true"
        print("🌐 ブラウザ自動起動: 有効")
    
    if args.port != 7860:
        os.environ["UNIRIG_PORT"] = str(args.port)
        print(f"📡 指定ポート: {args.port}")
    
    # 起動スクリプト選択
    if args.quick:
        script_path = "/app/quick_start_app.py"
        print("⚡ 高速起動モード (quick_start_app.py)")
    else:
        script_path = "/app/app.py"
        print("🎯 通常起動モード (app.py)")
    
    print("=" * 60)
    print("🎯 WebUI起動中...")
    
    try:
        # app.pyまたはquick_start_app.pyを実行
        subprocess.run([sys.executable, script_path], cwd="/app")
    except KeyboardInterrupt:
        print("\n⏹️ ユーザーによって停止されました")
    except Exception as e:
        print(f"\n❌ 起動エラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
