#!/usr/bin/env python3
"""
Test skinning process and analyze texture preservation without cleanup
"""
import os
import sys
sys.path.append('/app')

# Import and initialize config
from app import load_app_config, process_generate_skin

# Load configuration
load_app_config()

def test_skinning_with_analysis():
    print("=== Testing Skinning Process with Texture Analysis ===")
    
    # Input files from previous steps
    raw_data_npz_path = "/app/pipeline_work/01_extracted_mesh/bird/raw_data.npz"
    skeleton_fbx_path = "/app/pipeline_work/01_extracted_mesh/bird/skeleton.fbx"
    skeleton_npz_path = "/app/pipeline_work/01_extracted_mesh/bird/predict_skeleton.npz"
    model_name = "bird_texture_test"
    
    # Check input files exist
    for path in [raw_data_npz_path, skeleton_fbx_path, skeleton_npz_path]:
        if os.path.exists(path):
            size = os.path.getsize(path)
            print(f"✓ {path} ({size} bytes)")
        else:
            print(f"✗ Missing: {path}")
            return False
    
    # Dummy progress function
    def progress_fn(value, desc=None):
        print(f"Progress: {value*100:.2f}% - {desc if desc else ''}")
    
    print("\n--- Starting skinning process ---")
    
    try:
        display_glb_path, logs, skinned_fbx_path, skinning_npz_path = process_generate_skin(
            raw_data_npz_path=raw_data_npz_path,
            skeleton_fbx_path=skeleton_fbx_path,
            skeleton_npz_path=skeleton_npz_path,
            model_name_for_output=model_name,
            progress_fn=progress_fn
        )
        
        print("\n--- Results ---")
        print(f"Display GLB: {display_glb_path}")
        print(f"Skinned FBX: {skinned_fbx_path}")
        print(f"Skinning NPZ: {skinning_npz_path}")
        
        print("\n--- Process Logs ---")
        print(logs)
        
        # Check if output files were created
        success = True
        if skinned_fbx_path and os.path.exists(skinned_fbx_path):
            size = os.path.getsize(skinned_fbx_path)
            print(f"✓ Skinned FBX created: {skinned_fbx_path} ({size} bytes)")
        else:
            print(f"✗ Skinned FBX not created: {skinned_fbx_path}")
            success = False
            
        if skinning_npz_path and os.path.exists(skinning_npz_path):
            size = os.path.getsize(skinning_npz_path)
            print(f"✓ Skinning NPZ created: {skinning_npz_path} ({size} bytes)")
            
            # Analyze texture preservation in the final NPZ file
            print("\n--- Analyzing Texture Preservation ---")
            try:
                from src.data.raw_data import RawData
                raw_data = RawData.load(skinning_npz_path)
                
                print(f"📦 Final skinning NPZ file size: {size:,} bytes ({size/(1024*1024):.2f} MB)")
                print(f"🔢 Vertices: {len(raw_data.vertices) if raw_data.vertices is not None else 0:,}")
                print(f"🔷 Faces: {len(raw_data.faces) if raw_data.faces is not None else 0:,}")
                print(f"🦴 Joints: {len(raw_data.joints) if raw_data.joints is not None else 0:,}")
                
                if hasattr(raw_data, 'skin') and raw_data.skin is not None:
                    print(f"🎨 Skin weights: {raw_data.skin.shape}")
                else:
                    print(f"🎨 Skin weights: None")
                    
                has_uv = hasattr(raw_data, 'uv_coords') and raw_data.uv_coords is not None
                has_materials = hasattr(raw_data, 'materials') and raw_data.materials is not None
                
                if has_uv:
                    uv_count = len(raw_data.uv_coords)
                    print(f"🗺️ UV coordinates: {uv_count:,}")
                else:
                    print(f"🗺️ UV coordinates: None")
                
                if has_materials:
                    material_count = len(raw_data.materials)
                    print(f"🎨 Materials: {material_count}")
                    if material_count > 0:
                        sample_material = raw_data.materials[0]
                        if isinstance(sample_material, dict) and 'name' in sample_material:
                            print(f"   Sample material: {sample_material['name']}")
                        else:
                            print(f"   Sample material: {sample_material}")
                else:
                    print(f"🎨 Materials: None")
                
                # Final verification
                if has_uv and has_materials:
                    print(f"🎉 TEXTURE PRESERVATION: COMPLETE ✅")
                    return True
                elif has_uv or has_materials:
                    print(f"⚠️ TEXTURE PRESERVATION: PARTIAL")
                    return False
                else:
                    print(f"❌ TEXTURE PRESERVATION: LOST")
                    return False
                    
            except Exception as e:
                print(f"❌ Error analyzing NPZ file: {e}")
                import traceback
                traceback.print_exc()
                return False
        else:
            print(f"✗ Skinning NPZ not created: {skinning_npz_path}")
            success = False
        
        return success
        
    except Exception as e:
        print(f"✗ Exception during skinning: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_skinning_with_analysis()
    print(f"\n=== Test Result: {'SUCCESS' if success else 'FAILED'} ===")
