#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
6ステップ完全パイプラインテスト
Step0 → Step1 → Step2 → Step3 → Step4 → Step5 端到端検証

改訂された6ステップ構成の完全動作確認
"""

import sys
import time
from pathlib import Path

# app.pyをインポート
sys.path.append('/app')
from app import UniRigApp

def test_complete_6_step_pipeline():
    """6ステップ完全パイプラインテスト"""
    
    print("🚀 6ステップ完全パイプラインテスト開始")
    print("=" * 60)
    
    # テスト用モデル
    test_model = "/app/pipeline_output/step1_extract/bird/bird_input.glb"
    
    if not Path(test_model).exists():
        print(f"❌ テストモデルが見つかりません: {test_model}")
        return False
    
    print(f"📥 テストモデル: {Path(test_model).name}")
    print(f"📊 ファイルサイズ: {Path(test_model).stat().st_size / (1024*1024):.1f}MB")
    
    # アプリケーション初期化
    app = UniRigApp()
    
    try:
        start_time = time.time()
        
        # 6ステップパイプライン実行
        print("\n🔄 6ステップパイプライン実行:")
        
        # Step 0: ファイル転送
        print("  🔸 Step 0: ファイル転送...")
        result_step0 = app.call_step0_file_transfer(test_model, "test_complete_pipeline")
        print(f"    結果: {result_step0[0]} - {result_step0[1]}")
        
        if not result_step0[0]:
            raise RuntimeError(f"Step0失敗: {result_step0[1]}")
        
        # Step 1: メッシュ抽出
        print("  🔸 Step 1: メッシュ抽出...")
        result_step1 = app.call_step1_extract("test_complete_pipeline", result_step0[2])
        print(f"    結果: {result_step1[0]} - {result_step1[1]}")
        
        if not result_step1[0]:
            raise RuntimeError(f"Step1失敗: {result_step1[1]}")
        
        # Step 2: スケルトン生成
        print("  🔸 Step 2: スケルトン生成...")
        result_step2 = app.call_step2_skeleton("test_complete_pipeline", "neutral", result_step1[2])
        print(f"    結果: {result_step2[0]} - {result_step2[1]}")
        
        if not result_step2[0]:
            raise RuntimeError(f"Step2失敗: {result_step2[1]}")
        
        # Step 3: スキニング適用
        print("  🔸 Step 3: スキニング適用...")
        result_step3 = app.call_step3_skinning("test_complete_pipeline", result_step1[2], result_step2[2])
        print(f"    結果: {result_step3[0]} - {result_step3[1]}")
        
        if not result_step3[0]:
            raise RuntimeError(f"Step3失敗: {result_step3[1]}")
        
        # Step 4: マージ処理
        print("  🔸 Step 4: マージ処理...")
        result_step4 = app.call_step4_merge_skeleton_skinning(
            "test_complete_pipeline", 
            result_step1[2], 
            result_step2[2], 
            result_step3[2]
        )
        print(f"    結果: {result_step4[0]} - {result_step4[1]}")
        
        if not result_step4[0]:
            raise RuntimeError(f"Step4失敗: {result_step4[1]}")
        
        # Step 5: Blender統合・最終出力
        print("  🔸 Step 5: Blender統合・最終出力...")
        result_step5 = app.call_step5_blender_integration(
            "test_complete_pipeline",
            test_model,  # オリジナルモデル
            result_step4[2]  # マージ済みFBX
        )
        print(f"    結果: {result_step5[0]} - {result_step5[1]}")
        
        if not result_step5[0]:
            raise RuntimeError(f"Step5失敗: {result_step5[1]}")
        
        # 完了時間計測
        total_time = time.time() - start_time
        
        print(f"\n✅ 6ステップパイプライン完了!")
        print(f"⏱️ 総処理時間: {total_time:.1f}秒")
        
        # 最終結果確認
        print(f"\n📁 最終出力ファイル:")
        for key, path in result_step5[2].items():
            if Path(path).exists():
                size_mb = Path(path).stat().st_size / (1024 * 1024)
                print(f"  ✅ {key}: {Path(path).name} ({size_mb:.1f}MB)")
            else:
                print(f"  ❌ {key}: {Path(path).name} (存在しません)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ パイプラインエラー: {e}")
        return False


def main():
    """メイン実行"""
    success = test_complete_6_step_pipeline()
    
    if success:
        print("\n🎉 6ステップ完全パイプラインテスト成功!")
    else:
        print("\n💥 6ステップ完全パイプラインテスト失敗!")
    
    return success


if __name__ == "__main__":
    main()
