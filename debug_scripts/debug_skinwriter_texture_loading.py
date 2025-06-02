#!/usr/bin/env python3

import sys
import os
sys.path.append('/app')

import logging
from src.data.raw_data import RawData

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_texture_loading():
    """Debug texture loading in SkinWriter"""
    
    # Path to the skeleton NPZ that should contain texture data
    skeleton_npz_path = "/app/tmp/tmp/bird/predict_skeleton.npz"
    
    print(f"=== Debug Texture Loading from Skeleton NPZ ===")
    print(f"Skeleton NPZ path: {skeleton_npz_path}")
    print(f"Path exists: {os.path.exists(skeleton_npz_path)}")
    
    if not os.path.exists(skeleton_npz_path):
        print("ERROR: Skeleton NPZ file does not exist!")
        return
    
    try:
        # Load the skeleton data
        print("\n1. Loading skeleton NPZ file...")
        skeleton_data = RawData.load(skeleton_npz_path)
        
        print("\n2. Checking available attributes...")
        for attr in dir(skeleton_data):
            if not attr.startswith('_'):
                value = getattr(skeleton_data, attr)
                if value is not None:
                    if hasattr(value, 'shape'):
                        print(f"  {attr}: shape {value.shape}")
                    elif hasattr(value, '__len__'):
                        print(f"  {attr}: length {len(value)}")
                    else:
                        print(f"  {attr}: {type(value)}")
                else:
                    print(f"  {attr}: None")
        
        print("\n3. Texture data analysis...")
        
        # Check UV coordinates
        uv_coords = getattr(skeleton_data, 'uv_coords', None)
        if uv_coords is not None:
            print(f"  UV Coordinates: Found {len(uv_coords)} coordinates")
            print(f"  UV shape: {uv_coords.shape}")
            print(f"  UV sample: {uv_coords[:3] if len(uv_coords) > 3 else uv_coords}")
        else:
            print("  UV Coordinates: None")
        
        # Check materials
        materials = getattr(skeleton_data, 'materials', None)
        if materials is not None:
            print(f"  Materials: Found {len(materials)} materials")
            for i, material in enumerate(materials):
                print(f"    Material {i}: {material}")
        else:
            print("  Materials: None")
        
        print("\n4. Testing getattr approach (same as SkinWriter)...")
        test_uv = getattr(skeleton_data, 'uv_coords', None)
        test_materials = getattr(skeleton_data, 'materials', None)
        
        print(f"  getattr uv_coords: {'Found' if test_uv is not None else 'None'}")
        print(f"  getattr materials: {'Found' if test_materials is not None else 'None'}")
        
        return test_uv, test_materials
        
    except Exception as e:
        print(f"ERROR loading skeleton data: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def simulate_skinwriter_logic():
    """Simulate the exact logic used in SkinWriter"""
    
    print(f"\n=== Simulating SkinWriter Logic ===")
    
    # Simulate batch data that SkinWriter receives
    batch_path = "/app/tmp/tmp/bird/predict_skeleton.npz"
    
    original_uv_coords = None
    original_materials = None
    
    try:
        # This is the exact logic from SkinWriter
        if batch_path and batch_path.endswith('predict_skeleton.npz'):
            original_skeleton_npz_path = batch_path
            print(f"Loading texture data from skeleton NPZ: {original_skeleton_npz_path}")
            
            if os.path.exists(original_skeleton_npz_path):
                original_skeleton_data = RawData.load(original_skeleton_npz_path)
                if hasattr(original_skeleton_data, 'uv_coords') and original_skeleton_data.uv_coords is not None:
                    original_uv_coords = original_skeleton_data.uv_coords
                    print(f"Loaded {len(original_uv_coords)} UV coordinates from skeleton NPZ")
                if hasattr(original_skeleton_data, 'materials') and original_skeleton_data.materials is not None:
                    original_materials = original_skeleton_data.materials
                    print(f"Loaded {len(original_materials)} materials from skeleton NPZ")
            else:
                print(f"Skeleton NPZ path does not exist: {original_skeleton_npz_path}")
    except Exception as e:
        print(f"Could not load texture data from skeleton NPZ: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\nResult:")
    print(f"  UV Coordinates: {'Found' if original_uv_coords is not None else 'None'}")
    print(f"  Materials: {'Found' if original_materials is not None else 'None'}")
    
    return original_uv_coords, original_materials

if __name__ == "__main__":
    print("Starting SkinWriter texture loading debug...")
    
    # First, debug direct loading
    result1 = debug_texture_loading()
    if result1 is not None:
        uv1, mat1 = result1
    else:
        uv1, mat1 = None, None
    
    # Then, simulate exact SkinWriter logic
    uv2, mat2 = simulate_skinwriter_logic()
    
    print(f"\n=== Summary ===")
    print(f"Direct loading - UV: {'Found' if uv1 is not None else 'None'}, Materials: {'Found' if mat1 is not None else 'None'}")
    print(f"SkinWriter logic - UV: {'Found' if uv2 is not None else 'None'}, Materials: {'Found' if mat2 is not None else 'None'}")
    
    if uv1 is not None and uv2 is None:
        print("ERROR: Direct loading works but SkinWriter logic fails!")
    elif uv1 is None:
        print("ERROR: No UV coordinates found in skeleton NPZ file!")
    else:
        print("SUCCESS: Texture data loading works correctly!")
