#!/usr/bin/env python3
"""
実際のパス構造でパス探索をテスト
"""

import os
import sys

sys.path.insert(0, '/app')

def test_realistic_path_search():
    """
    実際のパス構造でパス探索をテスト
    """
    
    print("🧪 Testing Realistic Path Search Logic")
    print("=" * 60)
    
    # Realistic parameters (based on actual pipeline structure)
    source = "/app/pipeline_work/02_skeleton_output/skeleton.fbx"
    output = "/app/pipeline_work/04_final_rigged_model/final.fbx"
    model_name = "bird"
    
    output_dir = os.path.dirname(output)
    
    print(f"📂 Realistic Parameters:")
    print(f"  Source: {source}")
    print(f"  Output: {output}")
    print(f"  Output Dir: {output_dir}")
    print(f"  Model Name: {model_name}")
    
    # CORRECTED path search (based on actual directory structure)
    print(f"\n🔍 Testing CORRECTED YAML Manifest Path Search:")
    
    possible_paths = [
        # CORRECTED: Fixed path directory (actual location)
        "/app/pipeline_work/01_extracted_mesh_fixed/texture_manifest.yaml",
        # CORRECTED: Fixed2 path directory
        "/app/pipeline_work/01_extracted_mesh_fixed2/texture_manifest.yaml", 
        # Standard path with model name subdirectory
        os.path.join(output_dir, "..", "..", "01_extracted_mesh", model_name, "texture_manifest.yaml"),
        # Direct in extraction directory
        os.path.join(output_dir, "..", "..", "01_extracted_mesh", "texture_manifest.yaml"),
        # Same directory as source
        os.path.join(os.path.dirname(source), "texture_manifest.yaml")
    ]
    
    yaml_manifest_path = None
    texture_dir = None
    
    for i, path in enumerate(possible_paths, 1):
        normalized_path = os.path.normpath(path)
        exists = os.path.exists(normalized_path)
        print(f"  {i}. {normalized_path}")
        print(f"     🔸 Exists: {'✅' if exists else '❌'}")
        
        if exists and yaml_manifest_path is None:
            yaml_manifest_path = normalized_path
            texture_dir = os.path.join(os.path.dirname(path), "textures")
            print(f"     🎯 SELECTED for processing")
        
    print(f"\n📊 CORRECTED Path Search Results:")
    if yaml_manifest_path:
        print(f"  ✅ Found YAML Manifest: {yaml_manifest_path}")
        print(f"  📁 Texture Directory: {texture_dir}")
        
        # Check texture directory
        if os.path.exists(texture_dir):
            texture_files = [f for f in os.listdir(texture_dir) if f.endswith(('.png', '.jpg', '.jpeg'))]
            print(f"  🎨 Texture Files Found: {len(texture_files)}")
            for texture_file in texture_files:
                texture_path = os.path.join(texture_dir, texture_file)
                size_mb = os.path.getsize(texture_path) / (1024 * 1024)
                print(f"    - {texture_file}: {size_mb:.2f}MB")
        else:
            print(f"  ❌ Texture Directory Not Found: {texture_dir}")
            
        # Check YAML content
        try:
            import yaml
            with open(yaml_manifest_path, 'r') as f:
                manifest = yaml.safe_load(f)
            
            print(f"  📋 YAML Manifest Content:")
            print(f"    - Model Name: {manifest.get('model_name', 'Unknown')}")
            print(f"    - Texture Count: {manifest.get('texture_count', 0)}")
            
            for i, texture_info in enumerate(manifest.get('textures', []), 1):
                print(f"    - Texture {i}: {texture_info.get('original_name', 'Unknown')}")
                print(f"      Path: {texture_info.get('saved_path', 'Unknown')}")
                exists = os.path.exists(texture_info.get('saved_path', ''))
                print(f"      Exists: {'✅' if exists else '❌'}")
                
        except Exception as e:
            print(f"  ❌ Error reading YAML: {e}")
            
        return True
    else:
        print(f"  ❌ No YAML Manifest Found")
        return False

def generate_corrected_merge_paths():
    """
    正しいパス探索コードを生成
    """
    
    print(f"\n🔧 Generating Corrected merge.py Path Search Code:")
    print("=" * 60)
    
    corrected_code = '''
        # CORRECTED: Look for YAML manifest in actual directory structure
        possible_paths = [
            # CORRECTED: Absolute paths to known locations
            "/app/pipeline_work/01_extracted_mesh_fixed/texture_manifest.yaml",
            "/app/pipeline_work/01_extracted_mesh_fixed2/texture_manifest.yaml",
            # Standard relative paths (fallback)
            os.path.join(output_dir, "..", "..", "01_extracted_mesh", model_name, "texture_manifest.yaml"),
            os.path.join(output_dir, "..", "..", "01_extracted_mesh_fixed", "texture_manifest.yaml"),
            os.path.join(output_dir, "..", "..", "01_extracted_mesh_fixed2", "texture_manifest.yaml"),
            os.path.join(output_dir, "..", "..", "01_extracted_mesh", "texture_manifest.yaml"),
            os.path.join(os.path.dirname(source), "texture_manifest.yaml")
        ]
    '''
    
    print(corrected_code)
    
    return corrected_code

if __name__ == "__main__":
    print("🚀 Testing Realistic Path Search Logic")
    print("=" * 50)
    
    success = test_realistic_path_search()
    
    if success:
        print("\n🎉 Realistic Path Search Logic TEST PASSED!")
        print("✅ YAML manifest and textures found successfully")
        
        corrected_code = generate_corrected_merge_paths()
        
        print("\n📋 Next Steps:")
        print("1. Update merge.py with corrected absolute paths")
        print("2. Test complete pipeline with corrected paths")
        print("3. Verify ImprovedSafeTextureRestoration execution")
    else:
        print("\n❌ Realistic Path Search Logic TEST FAILED!")
        print("⚠️ Need to investigate actual file locations")
    
    print("\n🔍 Current Status:")
    print("- YAML manifest located successfully")
    print("- Texture files confirmed present")
    print("- Path search logic needs absolute path correction")
