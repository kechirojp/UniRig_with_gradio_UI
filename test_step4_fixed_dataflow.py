#!/usr/bin/env python3
"""
Step4大元フロー互換性検証スクリプト
現在のStep3出力データでStep4の大元フロー実行をテスト
"""

import os
import sys
import json
from pathlib import Path

# UniRigルートディレクトリをPythonパスに追加
sys.path.insert(0, '/app')

from step_modules.step4_texture import Step4Texture

def test_step4_with_current_data():
    """現在のStep3出力データでStep4テスト"""
    
    print("🧪 Step4大元フロー互換性検証開始")
    
    # 現在のStep3出力データ（ユーザー提供情報）
    step3_data = {
        "skinning_dir": "/app/pipeline_work/03_skinning",
        "skinned_fbx": "/app/pipeline_work/03_skinning/test_dataflow_bird_skinned.fbx",
        "skinning_npz": "/app/pipeline_work/03_skinning/test_dataflow_bird_skinning.npz",
        "weights_txt": "/app/pipeline_work/03_skinning/test_dataflow_bird_weights.txt"
    }
    
    # オリジナルモデル（Step1入力）
    original_model = "/app/examples/bird.glb"
    
    # Step4出力ディレクトリ
    step4_output_dir = Path("/app/test_step4_fixed_dataflow")
    step4_output_dir.mkdir(exist_ok=True)
    
    # 入力データの存在確認
    print("\n📋 入力データ検証:")
    for key, file_path in step3_data.items():
        exists = os.path.exists(file_path)
        size = os.path.getsize(file_path) if exists else 0
        print(f"  - {key}: {file_path}")
        print(f"    存在: {exists}, サイズ: {size} bytes")
    
    print(f"\n  - オリジナルモデル: {original_model}")
    print(f"    存在: {os.path.exists(original_model)}, サイズ: {os.path.getsize(original_model) if os.path.exists(original_model) else 0} bytes")
    
    # Step4実行
    print("\n🚀 Step4実行開始")
    step4 = Step4Texture(step4_output_dir)
    
    success, logs, output_files = step4.merge_textures(
        skinned_fbx=step3_data["skinned_fbx"],  # リギング済みFBX（target）
        original_model=original_model,           # オリジナルモデル（source）
        model_name="test_dataflow_bird",
        metadata_file=None
    )
    
    # 結果表示
    print(f"\n📊 Step4実行結果:")
    print(f"  成功: {success}")
    print(f"  ログ:\n{logs}")
    
    if success and output_files:
        print(f"\n📁 出力ファイル:")
        for key, value in output_files.items():
            print(f"  - {key}: {value}")
            
        # 最終FBXの詳細検証
        final_fbx = output_files.get("final_fbx")
        if final_fbx and os.path.exists(final_fbx):
            final_size = os.path.getsize(final_fbx)
            print(f"\n✅ 最終FBX生成成功:")
            print(f"  - ファイル: {final_fbx}")
            print(f"  - サイズ: {final_size} bytes")
            
            # 品質評価
            if final_size > 100000:  # 100KB以上
                print(f"  - 品質評価: 良好（{final_size/1024:.1f}KB）")
            elif final_size > 20000:  # 20KB以上
                print(f"  - 品質評価: 普通（{final_size/1024:.1f}KB）")
            else:
                print(f"  - 品質評価: 問題あり（{final_size/1024:.1f}KB - 小さすぎ）")
    else:
        print(f"\n❌ Step4失敗")
        
    return success, logs, output_files

if __name__ == "__main__":
    test_step4_with_current_data()
