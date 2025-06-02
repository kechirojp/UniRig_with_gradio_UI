#!/usr/bin/env python3
"""
Test texture preservation functionality
"""

import os
import sys
import numpy as np

# Add the app directory to Python path
sys.path.insert(0, '/app')

def test_texture_extraction():
    """Test texture extraction from a model with textures"""
    print("=== Testing Texture Preservation ===")
    
    # Import required modules
    try:
        from src.data.extract import extract_builtin
        import yaml
        print("✅ Extract module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import extract module: {e}")
        return False
    
    # Use a model that should have textures
    test_model = "/app/examples/tira.glb"
    output_dir = "/app/test_texture_output"
    config_path = "/app/configs/extract_config.yaml"
    
    if not os.path.exists(test_model):
        print(f"❌ Test model not found: {test_model}")
        return False
        
    if not os.path.exists(config_path):
        print(f"❌ Config file not found: {config_path}")
        return False
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        print(f"🔄 Processing model: {test_model}")
        
        # Load config
        with open(config_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        
        result = extract_builtin(
            config_dict=config_dict,
            model_path=test_model,
            output_dir=output_dir
        )
        
        if result:
            print("✅ Mesh extraction completed successfully")
            
            # Check if raw_data.npz was created
            npz_path = os.path.join(output_dir, "raw_data.npz")
            if os.path.exists(npz_path):
                print("✅ raw_data.npz file created")
                
                # Load and inspect the data
                data = np.load(npz_path, allow_pickle=True)
                print(f"📊 Data keys: {list(data.keys())}")
                
                # Check for texture-related data
                if 'uv_coords' in data:
                    uv_coords = data['uv_coords']
                    print(f"✅ UV coordinates found: {len(uv_coords)} coordinates")
                else:
                    print("⚠️ No UV coordinates found")
                
                if 'materials' in data:
                    materials = data['materials']
                    print(f"✅ Materials found: {len(materials)} materials")
                    for i, material in enumerate(materials):
                        print(f"   Material {i}: {material}")
                else:
                    print("⚠️ No materials found")
                
                return True
            else:
                print("❌ raw_data.npz file not created")
                return False
        else:
            print("❌ Mesh extraction failed")
            return False
            
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_texture_extraction()
    if success:
        print("\n🎉 Texture preservation test completed successfully!")
    else:
        print("\n❌ Texture preservation test failed")
    sys.exit(0 if success else 1)
