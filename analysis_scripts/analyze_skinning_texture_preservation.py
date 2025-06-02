#!/usr/bin/env python3
"""
Analyze texture preservation in skinning NPZ files to verify that UV coordinates and materials
are properly preserved throughout the pipeline.
"""
import os
import sys
import numpy as np
sys.path.append('/app')

from src.data.raw_data import RawData

def analyze_skinning_texture_preservation():
    """Analyze the texture preservation in skinning NPZ files."""
    print("=== Analyzing Skinning Texture Preservation ===")
    
    # Test cases: Compare different stages of the pipeline
    test_cases = [
        {
            'name': 'Original Extracted Data',
            'path': '/app/pipeline_work/01_extracted_mesh/bird/raw_data.npz',
            'description': 'Original mesh extraction with texture data'
        },
        {
            'name': 'Skeleton Generation Output',
            'path': '/app/pipeline_work/01_extracted_mesh/bird/predict_skeleton.npz',
            'description': 'Output from skeleton generation stage (should preserve textures)'
        },
        {
            'name': 'Skinning Output (if exists)',
            'path': '/app/pipeline_work/02_skin_prediction/bird/predict_skin.npz',
            'description': 'Output from skinning stage (should preserve textures)'
        }
    ]
    
    print("\n📊 Texture Preservation Analysis:")
    print("=" * 60)
    
    preserved_cases = 0
    total_cases = 0
    
    for case in test_cases:
        print(f"\n🔍 {case['name']}:")
        print(f"   📁 Path: {case['path']}")
        print(f"   📝 Description: {case['description']}")
        
        if not os.path.exists(case['path']):
            print(f"   ❌ File not found")
            continue
            
        total_cases += 1
        
        try:
            # Check file size
            file_size = os.path.getsize(case['path'])
            print(f"   📦 File size: {file_size:,} bytes ({file_size / (1024*1024):.2f} MB)")
            
            # Load and analyze NPZ content
            raw_data = RawData.load(case['path'])
            
            # Check basic mesh data
            print(f"   🔢 Vertices: {len(raw_data.vertices) if raw_data.vertices is not None else 0:,}")
            print(f"   🔷 Faces: {len(raw_data.faces) if raw_data.faces is not None else 0:,}")
            print(f"   🦴 Joints: {len(raw_data.joints) if raw_data.joints is not None else 0:,}")
            
            # Check skinning data
            if hasattr(raw_data, 'skin') and raw_data.skin is not None:
                print(f"   🎨 Skin weights: {raw_data.skin.shape}")
            else:
                print(f"   🎨 Skin weights: None")
            
            # Check texture preservation
            has_uv = hasattr(raw_data, 'uv_coords') and raw_data.uv_coords is not None
            has_materials = hasattr(raw_data, 'materials') and raw_data.materials is not None
            
            if has_uv:
                uv_count = len(raw_data.uv_coords)
                print(f"   🗺️ UV coordinates: {uv_count:,}")
                if uv_count > 0:
                    print(f"      Sample UV: {raw_data.uv_coords[0] if isinstance(raw_data.uv_coords[0], (list, tuple)) else 'N/A'}")
            else:
                print(f"   🗺️ UV coordinates: None")
            
            if has_materials:
                material_count = len(raw_data.materials)
                print(f"   🎨 Materials: {material_count}")
                if material_count > 0:
                    print(f"      Sample material: {raw_data.materials[0]['name'] if isinstance(raw_data.materials[0], dict) and 'name' in raw_data.materials[0] else raw_data.materials[0]}")
            else:
                print(f"   🎨 Materials: None")
            
            # Check if texture data is preserved
            if has_uv and has_materials:
                print(f"   ✅ Texture preservation: COMPLETE")
                preserved_cases += 1
            elif has_uv or has_materials:
                print(f"   ⚠️ Texture preservation: PARTIAL ({('UV' if has_uv else '') + (' + ' if has_uv and has_materials else '') + ('Materials' if has_materials else '')})")
            else:
                print(f"   ❌ Texture preservation: LOST")
                
        except Exception as e:
            print(f"   ❌ Error loading file: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"📈 Texture Preservation Summary:")
    print(f"   Total files analyzed: {total_cases}")
    print(f"   Files with complete texture preservation: {preserved_cases}")
    print(f"   Preservation rate: {(preserved_cases/total_cases*100) if total_cases > 0 else 0:.1f}%")
    
    if preserved_cases == total_cases and total_cases > 0:
        print(f"   🎉 SUCCESS: All analyzed files have complete texture preservation!")
        return True
    elif preserved_cases > 0:
        print(f"   ⚠️ PARTIAL: Some files have texture preservation issues")
        return False
    else:
        print(f"   ❌ FAILED: No files have complete texture preservation")
        return False

def compare_file_sizes():
    """Compare file sizes to show improvement from texture preservation fixes."""
    print("\n🔍 File Size Comparison (Before vs After Fixes):")
    print("=" * 50)
    
    files_to_check = [
        {
            'name': 'Skeleton NPZ',
            'path': '/app/pipeline_work/01_extracted_mesh/bird/predict_skeleton.npz',
            'expected_improved_size': 1200000  # ~1.2MB with texture data
        },
        {
            'name': 'Skinning NPZ',
            'path': '/app/pipeline_work/02_skin_prediction/bird/predict_skin.npz',
            'expected_improved_size': 2000000  # ~2MB with texture data
        }
    ]
    
    for file_info in files_to_check:
        if os.path.exists(file_info['path']):
            actual_size = os.path.getsize(file_info['path'])
            expected_size = file_info['expected_improved_size']
            
            print(f"\n📁 {file_info['name']}:")
            print(f"   Current size: {actual_size:,} bytes ({actual_size/(1024*1024):.2f} MB)")
            print(f"   Expected size: {expected_size:,} bytes ({expected_size/(1024*1024):.2f} MB)")
            
            if actual_size >= expected_size * 0.8:  # Allow 20% variance
                print(f"   ✅ Size indicates texture preservation (within expected range)")
            else:
                print(f"   ❌ Size too small - may indicate missing texture data")
        else:
            print(f"\n📁 {file_info['name']}: File not found")

if __name__ == "__main__":
    print("🎨 UniRig Texture Preservation Analysis")
    print("=" * 50)
    
    success = analyze_skinning_texture_preservation()
    compare_file_sizes()
    
    print(f"\n{'🎉 ANALYSIS COMPLETE' if success else '⚠️ ANALYSIS COMPLETE WITH ISSUES'}")
