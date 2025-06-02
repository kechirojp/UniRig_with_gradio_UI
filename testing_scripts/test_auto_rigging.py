#!/usr/bin/env python3
"""
自動リギング機能のテストスクリプト
"""

import sys
sys.path.append('/app')

from app import process_full_auto_rigging
import tempfile
import os

def test_auto_rigging():
    """自動リギング機能をテスト"""
    try:
        # テスト用のサンプルモデル
        test_model = "/app/examples/tira.glb"
        
        if not os.path.exists(test_model):
            print(f"テストモデルが見つかりません: {test_model}")
            return
        
        print(f"テスト開始: {test_model}")
        
        # 自動リギング実行（progress=None でテスト）
        result = process_full_auto_rigging(test_model, "Female", None)
        
        print("=== 結果 ===")
        print(f"リギング済みモデル: {result[0]}")
        print(f"ログ: {result[1][:500]}...")  # 最初の500文字のみ表示
        
        # ファイルが作成されているか確認
        if result[0] and os.path.exists(result[0]):
            print(f"✓ リギング済みモデルが正常に作成されました: {result[0]}")
        else:
            print("✗ リギング済みモデルの作成に失敗しました")
            
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_auto_rigging()
