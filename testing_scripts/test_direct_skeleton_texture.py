#!/usr/bin/env python3
"""
直接スケルトン生成を実行してARWriterのテクスチャ保持を確認
"""

import os
import sys
import torch
import numpy as np
from pathlib import Path

# パス設定
sys.path.append('/app/src')

# 必要なモジュールをインポート
from src.data.extract import extract_builtin
from src.data.raw_data import RawData

def test_skeleton_generation_with_texture():
    """テクスチャ保持を確認しながらスケルトン生成をテスト"""
    
    print("=== テクスチャ保持スケルトン生成テスト ===")
    
    # 設定
    input_model = "/app/examples/bird.glb"
    output_dir = "/app/test_texture_skeleton_output"
    
    # 出力ディレクトリを作成
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"入力ファイル: {input_model}")
    print(f"出力ディレクトリ: {output_dir}")
    
    # ステップ1: メッシュ抽出（テクスチャ情報を含む）
    print("\n--- ステップ1: メッシュ抽出 ---")
    try:
        config_dict = {
            'data': {
                'batch_size': 1,
                'num_joints': 53,
                'joint_loc': 'mesh'
            }
        }
        
        extract_output = extract_builtin(
            config_dict=config_dict,
            model_path=input_model,
            output_dir=output_dir,
            log_path=os.path.join(output_dir, "extract.log")
        )
        
        print(f"✅ メッシュ抽出完了: {extract_output}")
        
        # 抽出されたNPZファイルを確認
        npz_files = list(Path(output_dir).glob("**/*.npz"))
        print(f"生成されたNPZファイル: {npz_files}")
        
        if npz_files:
            raw_data_path = npz_files[0]
            print(f"\nraw_dataファイルを分析: {raw_data_path}")
            
            # NPZファイルを読み込んで内容確認
            data = np.load(raw_data_path, allow_pickle=True)
            print(f"含まれるキー: {list(data.keys())}")
            
            if 'uv_coords' in data:
                uv_coords = data['uv_coords']
                print(f"UV座標: shape={uv_coords.shape if hasattr(uv_coords, 'shape') else type(uv_coords)}")
            
            if 'materials' in data:
                materials = data['materials']
                print(f"マテリアル: {materials}")
        
    except Exception as e:
        print(f"❌ メッシュ抽出エラー: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # ステップ2: スケルトン生成（run.pyを使用）
    print(f"\n--- ステップ2: スケルトン生成 ---")
    
    try:
        # run.pyを使ってスケルトン生成を実行
        cmd = f"cd /app && python run.py configs/models/ArticulationGenerator.yaml --input_files {raw_data_path} --output_dir {output_dir}/skeleton_output"
        print(f"実行コマンド: {cmd}")
        
        result = os.system(cmd)
        print(f"コマンド実行結果: {result}")
        
        if result == 0:
            print("✅ スケルトン生成完了")
            
            # 生成されたファイルを確認
            skeleton_files = list(Path(f"{output_dir}/skeleton_output").glob("**/*"))
            print(f"生成されたファイル: {skeleton_files}")
            
            # predict_skeleton.npzがあれば内容確認
            predict_npz_files = list(Path(f"{output_dir}/skeleton_output").glob("**/predict_skeleton.npz"))
            if predict_npz_files:
                predict_npz = predict_npz_files[0]
                print(f"\npredict_skeleton.npz分析: {predict_npz}")
                
                data = np.load(predict_npz, allow_pickle=True)
                print(f"含まれるキー: {list(data.keys())}")
                
                if 'uv_coords' in data:
                    uv_coords = data['uv_coords']
                    if uv_coords is not None and hasattr(uv_coords, 'shape'):
                        print(f"✅ UV座標保持: shape={uv_coords.shape}")
                    else:
                        print(f"❌ UV座標なし: {uv_coords}")
                
                if 'materials' in data:
                    materials = data['materials']
                    if materials is not None:
                        print(f"✅ マテリアル保持: {materials}")
                    else:
                        print(f"❌ マテリアルなし: {materials}")
        else:
            print(f"❌ スケルトン生成失敗: {result}")
            
    except Exception as e:
        print(f"❌ スケルトン生成エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_skeleton_generation_with_texture()
