#!/usr/bin/env python3
"""
最新の修正されたスケルトンNPZファイルのテクスチャ情報を確認
"""

import numpy as np
import os

def analyze_fixed_skeleton_npz():
    """修正されたスケルトンNPZファイルを分析"""
    
    npz_files = [
        "/app/pipeline_work/01_extracted_mesh/bird/raw_data.npz",
        "/app/pipeline_work/01_extracted_mesh/bird/pipeline_work/01_extracted_mesh/bird/predict_skeleton.npz"
    ]
    
    print("=== 修正版ARWriterで生成されたファイルの分析 ===")
    
    for npz_path in npz_files:
        print(f"\n--- {os.path.basename(npz_path)} ---")
        print(f"パス: {npz_path}")
        
        if not os.path.exists(npz_path):
            print("❌ ファイルが存在しません")
            continue
        
        file_size = os.path.getsize(npz_path)
        print(f"ファイルサイズ: {file_size:,} バイト ({file_size/1024:.1f} KB)")
        
        try:
            data = np.load(npz_path, allow_pickle=True)
            
            # UV座標確認
            if 'uv_coords' in data:
                uv_coords = data['uv_coords']
                if uv_coords is not None and hasattr(uv_coords, 'shape') and uv_coords.size > 0:
                    print(f"✅ UV座標: shape={uv_coords.shape}, dtype={uv_coords.dtype}")
                    print(f"  値の範囲: min={np.min(uv_coords):.3f}, max={np.max(uv_coords):.3f}")
                else:
                    print(f"❌ UV座標なし: {uv_coords}")
            
            # マテリアル確認
            if 'materials' in data:
                materials = data['materials']
                if materials is not None and hasattr(materials, '__len__') and len(materials) > 0:
                    print(f"✅ マテリアル保持: {len(materials)}個")
                    if isinstance(materials, np.ndarray) and materials.size > 0:
                        for i, mat in enumerate(materials):
                            if isinstance(mat, dict):
                                print(f"  マテリアル[{i}]: {mat.get('name', 'Unknown')}")
                                if 'textures' in mat:
                                    print(f"    テクスチャ数: {len(mat['textures'])}")
                                    for j, tex in enumerate(mat['textures']):
                                        print(f"      [{j}]: {tex.get('name', 'Unknown')}")
                else:
                    print(f"❌ マテリアルなし: {materials}")
            
            # スケルトン情報確認
            if 'joints' in data:
                joints = data['joints']
                joint_count = joints.shape[0] if hasattr(joints, 'shape') else 'N/A'
                print(f"ジョイント数: {joint_count}")
                
                if 'names' in data:
                    names = data['names']
                    if hasattr(names, '__len__'):
                        print(f"ジョイント名サンプル: {list(names[:5]) if len(names) > 5 else list(names)}")
        
        except Exception as e:
            print(f"❌ エラー: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    analyze_fixed_skeleton_npz()
