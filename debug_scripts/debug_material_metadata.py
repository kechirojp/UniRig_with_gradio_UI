#!/usr/bin/env python3
"""
Debug material metadata format to understand structure.
"""

import os
import numpy as np

def debug_material_metadata():
    """Debug the material metadata structure in NPZ."""
    
    npz_path = "/app/pipeline_work/01_extracted_mesh_fixed/raw_data.npz"
    
    if not os.path.exists(npz_path):
        print(f"NPZ file not found: {npz_path}")
        return
    
    print("=== DEBUGGING MATERIAL METADATA ===\n")
    
    try:
        data = np.load(npz_path, allow_pickle=True)
        
        if 'materials' in data:
            materials = data['materials']
            print(f"Materials type: {type(materials)}")
            print(f"Materials shape: {materials.shape if hasattr(materials, 'shape') else 'N/A'}")
            print(f"Materials dtype: {materials.dtype if hasattr(materials, 'dtype') else 'N/A'}")
            
            # Try different access methods
            if hasattr(materials, 'item'):
                materials_item = materials.item()
                print(f"Materials.item() type: {type(materials_item)}")
                print(f"Materials.item() content: {materials_item}")
            
            if isinstance(materials, np.ndarray) and materials.ndim == 0:
                # Scalar numpy array containing object
                actual_materials = materials[()]
                print(f"Materials[()] type: {type(actual_materials)}")
                print(f"Materials[()] content: {actual_materials}")
                
                if isinstance(actual_materials, list):
                    print(f"Material list length: {len(actual_materials)}")
                    for i, material in enumerate(actual_materials):
                        print(f"\nMaterial {i}:")
                        print(f"  Type: {type(material)}")
                        print(f"  Content: {material}")
                        if isinstance(material, dict):
                            for key, value in material.items():
                                print(f"    {key}: {value}")
            
            print(f"\nDirect materials content: {materials}")
        else:
            print("No 'materials' key found in NPZ")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_material_metadata()
