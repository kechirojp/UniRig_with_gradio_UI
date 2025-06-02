#!/usr/bin/env python3
"""
NPZファイルの中身を分析してテクスチャ情報を確認
"""

import numpy as np
import os

def analyze_npz_file(npz_path):
    """NPZファイルの内容を分析"""
    print(f"\n=== {npz_path}の分析 ===")
    
    if not os.path.exists(npz_path):
        print("❌ ファイルが存在しません")
        return
    
    file_size = os.path.getsize(npz_path)
    print(f"ファイルサイズ: {file_size:,} バイト ({file_size/1024:.1f} KB)")
    
    try:
        data = np.load(npz_path, allow_pickle=True)
        print(f"含まれるキー: {list(data.keys())}")
        
        for key in data.keys():
            value = data[key]
            if isinstance(value, np.ndarray):
                print(f"{key}: shape={value.shape}, dtype={value.dtype}")
                if value.size < 20:  # 小さい配列の場合は内容も表示
                    print(f"  値: {value}")
            else:
                print(f"{key}: type={type(value)}, value={value}")
        
        # 特に重要なキーの詳細確認
        if 'uv_coords' in data:
            uv_coords = data['uv_coords']
            print(f"\n📍 UV座標詳細:")
            print(f"  形状: {uv_coords.shape}")
            print(f"  データ型: {uv_coords.dtype}")
            print(f"  値の範囲: min={np.min(uv_coords):.3f}, max={np.max(uv_coords):.3f}")
            if uv_coords.size > 0:
                print(f"  最初の5つの座標: {uv_coords.flatten()[:10]}")
            else:
                print("  ❌ UV座標データが空です")
        
        if 'materials' in data:
            materials = data['materials']
            print(f"\n🎨 マテリアル詳細:")
            print(f"  型: {type(materials)}")
            if isinstance(materials, np.ndarray):
                print(f"  形状: {materials.shape}")
                if materials.size > 0:
                    print(f"  内容: {materials}")
                else:
                    print("  ❌ マテリアルデータが空です")
            else:
                print(f"  内容: {materials}")
        
        print(f"\n✅ 分析完了")
        
    except Exception as e:
        print(f"❌ エラー: {e}")

def main():
    """メイン関数"""
    npz_files = [
        "/app/pipeline_work/01_extracted_mesh/bird/raw_data.npz",
        "/app/pipeline_work/01_extracted_mesh/bird/predict_skeleton.npz",
        "/app/pipeline_work/03_skinning_output/bird/predict_skin.npz"
    ]
    
    print("NPZファイルのテクスチャ情報分析開始...")
    
    for npz_file in npz_files:
        analyze_npz_file(npz_file)
    
    print("\n=== 分析サマリー ===")
    print("1. raw_data.npz: 元のメッシュ抽出時のデータ（UV座標、マテリアル含む）")
    print("2. predict_skeleton.npz: スケルトン予測時のデータ")
    print("3. predict_skin.npz: スキニング処理時のデータ")

if __name__ == "__main__":
    main()
