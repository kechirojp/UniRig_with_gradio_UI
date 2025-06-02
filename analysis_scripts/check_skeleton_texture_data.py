#!/usr/bin/env python3
"""
Verify that the skeleton NPZ file contains texture data
"""

import sys
sys.path.insert(0, '/app')

from src.data.raw_data import RawData

def check_skeleton_texture_data():
    skeleton_npz_path = "/app/pipeline_work/01_extracted_mesh/bird/predict_skeleton.npz"
    
    print(f"=== Checking Skeleton NPZ Texture Data ===")
    print(f"File: {skeleton_npz_path}")
    
    try:
        skeleton_data = RawData.load(skeleton_npz_path)
        
        print(f"✅ Successfully loaded skeleton NPZ")
        print(f"UV coords: {hasattr(skeleton_data, 'uv_coords') and skeleton_data.uv_coords is not None}")
        if hasattr(skeleton_data, 'uv_coords') and skeleton_data.uv_coords is not None:
            print(f"UV coords length: {len(skeleton_data.uv_coords)}")
            
        print(f"Materials: {hasattr(skeleton_data, 'materials') and skeleton_data.materials is not None}")
        if hasattr(skeleton_data, 'materials') and skeleton_data.materials is not None:
            print(f"Materials length: {len(skeleton_data.materials)}")
            print(f"First material: {skeleton_data.materials[0] if skeleton_data.materials else 'None'}")
            
        # Check other attributes
        print(f"Vertices: {skeleton_data.vertices.shape if skeleton_data.vertices is not None else 'None'}")
        print(f"Faces: {skeleton_data.faces.shape if skeleton_data.faces is not None else 'None'}")
        print(f"Joints: {skeleton_data.joints.shape if skeleton_data.joints is not None else 'None'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error loading skeleton NPZ: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    check_skeleton_texture_data()
