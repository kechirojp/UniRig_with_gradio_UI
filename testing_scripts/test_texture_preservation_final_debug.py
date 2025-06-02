#!/usr/bin/env python3
"""
完全なテクスチャ保持機能のテスト（デバッグ版）
修正されたパス設定での動作確認
"""

import os
import sys
import datetime
import traceback

# appモジュールのインポート
sys.path.append('/app')
from app import process_full_auto_rigging

def test_texture_preservation_debug():
    """完全なテクスチャ保持機能をテストする（デバッグ版）"""
    print("=== 完全テクスチャ保持機能テスト開始（デバッグ版） ===")
    print(f"開始時刻: {datetime.datetime.now()}")
    
    # テスト用のモデルファイル
    test_model_path = "/app/examples/bird.glb"
    
    print(f"テストモデル: {test_model_path}")
    
    # モデルファイルの存在確認
    if not os.path.exists(test_model_path):
        print(f"エラー: テストモデルが見つかりません: {test_model_path}")
        return False
    
    print("✓ テストモデルファイル確認完了")
    
    try:
        print("\n--- 完全自動リギング実行（テクスチャ保持付き） ---")
        
        # 完全自動リギング機能を実行（テクスチャ保持付き）
        results = process_full_auto_rigging(
            original_model_path=test_model_path,
            gender="neutral",
            progress=None
        )
        
        print(f"\n=== 戻り値解析 ===")
        print(f"戻り値の型: {type(results)}")
        print(f"戻り値の長さ: {len(results) if hasattr(results, '__len__') else 'N/A'}")
        
        # 戻り値の内容を詳しく確認
        if results and hasattr(results, '__len__'):
            for i, result_item in enumerate(results):
                print(f"results[{i}]: {type(result_item)} = {str(result_item)[:100]}{'...' if len(str(result_item)) > 100 else ''}")
        
        # 結果の確認（修正されたパス参照）
        if results and len(results) >= 11:
            (final_display_path, logs, final_merged_fbx_path,  # 0, 1, 2
             extracted_npz_path, skeleton_display_path, skeleton_fbx_path, skeleton_txt_path,  # 3, 4, 5, 6
             skeleton_npz_path, skinned_display_path, skinned_fbx_path, skinning_npz_path) = results  # 7, 8, 9, 10
            
            print("\n=== 結果ファイル ===")
            print(f"最終表示モデル: {final_display_path}")
            print(f"最終マージFBX: {final_merged_fbx_path}")
            print(f"スケルトンGLB: {skeleton_display_path}")
            print(f"スキニングGLB: {skinned_display_path}")
            
            print("\n=== ログ ===")
            print(logs)
            
            # ファイルの存在確認とサイズチェック
            success_count = 0
            total_files = 0
            
            expected_files = [
                ("最終表示モデル", final_display_path),
                ("最終マージFBX", final_merged_fbx_path),
                ("スケルトンGLB", skeleton_display_path),
                ("スケルトンFBX", skeleton_fbx_path),
                ("スキニングGLB", skinned_display_path),
                ("スキニングFBX", skinned_fbx_path)
            ]
            
            print("\n=== ファイル存在確認 ===")
            for desc, file_path in expected_files:
                total_files += 1
                if file_path and os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    print(f"✓ {desc}: {file_path} ({file_size / (1024*1024):.2f} MB)")
                    success_count += 1
                    
                    # テクスチャ付きモデルは大きなファイルサイズになっているはず
                    if "最終" in desc and file_size > 100000:  # 100KB以上
                        print(f"  ↳ テクスチャ保持による大容量ファイル確認 ✓")
                    elif "最終" in desc:
                        print(f"  ↳ 警告: ファイルサイズが小さい可能性")
                else:
                    print(f"✗ {desc}: {file_path} (存在しない)")
            
            print(f"\n成功率: {success_count}/{total_files} ({success_count/total_files*100:.1f}%)")
            
            if success_count == total_files:
                print("\n🎉 完全テクスチャ保持機能テスト成功！")
                return True
            else:
                print(f"\n⚠️ 一部ファイルが作成されませんでした（{total_files - success_count}個不足）")
                return False
        else:
            print(f"\n✗ 予期しない戻り値: 長さ={len(results) if hasattr(results, '__len__') else 'N/A'}")
            print(f"戻り値内容: {results}")
            return False
            
    except Exception as e:
        print(f"\n✗ テクスチャ保持機能テスト中にエラー: {e}")
        print(f"詳細トレースバック:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_texture_preservation_debug()
    print(f"\n=== テスト完了: {'成功' if success else '失敗'} ===")
    print(f"終了時刻: {datetime.datetime.now()}")
    exit(0 if success else 1)
