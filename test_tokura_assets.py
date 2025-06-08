#!/usr/bin/env python3
"""
テクスチャ付きモデルでのStep0アセット保存テスト
"""

import sys
sys.path.append('/app')

from step_modules.step0_asset_preservation import Step0AssetPreservation
from pathlib import Path

def test_tokura_asset_preservation():
    """Tokura_chara_sampleでのアセット保存テスト"""
    print("🔧 Tokura_chara_sampleアセット保存テスト開始")
    
    # Step0モジュール初期化
    output_dir = Path("/app/pipeline_work/00_asset_preservation")
    step0 = Step0AssetPreservation(output_dir)
    
    # テクスチャ付きモデルでテスト
    model_file = "/app/examples/Tokura_chara_sample.glb"
    model_name = "tokura_test"
    
    print(f"入力モデル: {model_file}")
    print(f"モデル名: {model_name}")
    
    # アセット保存実行
    success, logs, output_files = step0.preserve_assets(model_file, model_name)
    
    print(f"\n結果: {'成功' if success else '失敗'}")
    print(f"ログ:\n{logs}")
    print(f"出力ファイル: {output_files}")
    
    if success and output_files:
        # 保存されたアセット情報を表示
        metadata_path = output_files.get("asset_metadata_json")
        textures_dir = output_files.get("preserved_textures_dir")
        
        if metadata_path:
            print(f"\n📋 メタデータファイル: {metadata_path}")
            
        if textures_dir:
            print(f"📁 テクスチャディレクトリ: {textures_dir}")
            import os
            if os.path.exists(textures_dir):
                texture_files = [f for f in os.listdir(textures_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tga'))]
                print(f"   テクスチャファイル数: {len(texture_files)}")
                for tex_file in texture_files[:5]:  # 最初の5つを表示
                    print(f"   - {tex_file}")
                if len(texture_files) > 5:
                    print(f"   ... その他 {len(texture_files) - 5} ファイル")
    
    return success

if __name__ == "__main__":
    test_tokura_asset_preservation()
