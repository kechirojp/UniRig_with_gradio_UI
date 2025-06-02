#!/usr/bin/env python3
"""
新しく生成されたスケルトンNPZファイルのテクスチャ情報を確認
"""

import numpy as np
import os

def analyze_new_npz_files():
    """新しく生成されたNPZファイルを分析"""
    
    npz_files = [
        "/app/test_texture_skeleton_output/raw_data.npz",
        "/app/test_texture_skeleton_output/skeleton_output/test_texture_skeleton_output/predict_skeleton.npz"
    ]
    
    print("=== 新しく生成されたNPZファイルの分析 ===")
    
    for npz_path in npz_files:
        print(f"\n--- {npz_path} ---")
        
        if not os.path.exists(npz_path):
            print("❌ ファイルが存在しません")
            continue
        
        file_size = os.path.getsize(npz_path)
        print(f"ファイルサイズ: {file_size:,} バイト ({file_size/1024:.1f} KB)")
        
        try:
            data = np.load(npz_path, allow_pickle=True)
            print(f"含まれるキー: {list(data.keys())}")
            
            # UV座標確認
            if 'uv_coords' in data:
                uv_coords = data['uv_coords']
                if uv_coords is not None and hasattr(uv_coords, 'shape'):
                    print(f"✅ UV座標: shape={uv_coords.shape}, dtype={uv_coords.dtype}")
                    print(f"  値の範囲: min={np.min(uv_coords):.3f}, max={np.max(uv_coords):.3f}")
                else:
                    print(f"❌ UV座標なし: {uv_coords}")
            
            # マテリアル確認
            if 'materials' in data:
                materials = data['materials']
                if materials is not None:
                    print(f"✅ マテリアル保持: {materials}")
                    if isinstance(materials, np.ndarray) and materials.size > 0:
                        for i, mat in enumerate(materials):
                            if isinstance(mat, dict):
                                print(f"  マテリアル[{i}]: {mat.get('name', 'Unknown')}")
                                if 'textures' in mat:
                                    print(f"    テクスチャ数: {len(mat['textures'])}")
                                    for j, tex in enumerate(mat['textures']):
                                        print(f"      テクスチャ[{j}]: {tex.get('name', 'Unknown')}")
                else:
                    print(f"❌ マテリアルなし: {materials}")
            
            # スケルトン情報確認
            if 'joints' in data:
                joints = data['joints']
                print(f"ジョイント数: {joints.shape[0] if hasattr(joints, 'shape') else 'N/A'}")
            
        except Exception as e:
            print(f"❌ エラー: {e}")

if __name__ == "__main__":
    analyze_new_npz_files()
