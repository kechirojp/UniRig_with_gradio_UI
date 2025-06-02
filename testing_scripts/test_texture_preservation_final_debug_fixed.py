#!/usr/bin/env python3

import sys
import os
sys.path.append('/app')

from app import load_app_config, process_final_merge_with_textures

def dummy_progress(fraction, desc=''):
    print(f"Progress: {fraction:.1%} - {desc}")

def main():
    print("=== Testing Texture Preservation Pipeline (Debug Fixed) ===")
    
    # Load configuration
    print("Loading configuration...")
    load_app_config()
    
    # Define test parameters using actual available files
    model_name = "bird"
    original_model_path = "/app/examples/bird.glb"
    
    # Check for existing skinned FBX from previous pipeline runs
    possible_skinned_paths = [
        "/app/pipeline_work/03_skinning_output/bird/skinned_model.fbx",
        "/app/output_skeleton/bird/skinned_model.fbx",
        "/app/results/bird/skinned_model.fbx"
    ]
    
    skinned_fbx_path = None
    for path in possible_skinned_paths:
        if os.path.exists(path):
            skinned_fbx_path = path
            break
    
    print(f"\nTest parameters:")
    print(f"  Model name: {model_name}")
    print(f"  Original model: {original_model_path}")
    print(f"  Original model exists: {os.path.exists(original_model_path)}")
    print(f"  Skinned FBX: {skinned_fbx_path}")
    print(f"  Skinned FBX exists: {skinned_fbx_path and os.path.exists(skinned_fbx_path)}")
    
    if not os.path.exists(original_model_path):
        print("ERROR: Original model file not found!")
        return False
    
    if not skinned_fbx_path or not os.path.exists(skinned_fbx_path):
        print("ERROR: No skinned FBX file found. Please run the skinning pipeline first.")
        print("Available files in potential directories:")
        for path in possible_skinned_paths:
            parent_dir = os.path.dirname(path)
            if os.path.exists(parent_dir):
                print(f"  {parent_dir}: {os.listdir(parent_dir)}")
        return False
    
    print("\n=== Testing process_final_merge_with_textures ===")
    
    try:
        # Test the function with detailed debugging
        print("Calling process_final_merge_with_textures...")
        
        result = process_final_merge_with_textures(
            skinned_fbx_path=skinned_fbx_path,
            original_model_path=original_model_path,
            model_name_for_output=model_name,
            progress_fn=dummy_progress
        )
        
        print(f"\n=== Function Return Analysis ===")
        print(f"Return type: {type(result)}")
        print(f"Return value: {result}")
        
        if result is None:
            print("ERROR: Function returned None")
            return False
        
        if isinstance(result, tuple):
            print(f"Tuple length: {len(result)}")
            for i, item in enumerate(result):
                print(f"  result[{i}]: {type(item)} = {item}")
                
            # Expected return: (display_glb_path, logs, final_fbx_path)
            if len(result) == 3:
                display_glb_path, logs, final_fbx_path = result
                print(f"\n=== Successfully unpacked 3 values ===")
                print(f"Display GLB path: {display_glb_path}")
                print(f"Final FBX path: {final_fbx_path}")
                
                # Check file sizes
                if final_fbx_path and os.path.exists(final_fbx_path):
                    file_size = os.path.getsize(final_fbx_path)
                    print(f"Final FBX file size: {file_size} bytes ({file_size / (1024*1024):.2f} MB)")
                    
                    if file_size > 100000:  # More than 100KB
                        print("✓ SUCCESS: Final FBX has reasonable size")
                        success = True
                    else:
                        print("⚠ WARNING: Final FBX is unexpectedly small")
                        success = False
                else:
                    print("✗ ERROR: Final FBX file not found or not created")
                    success = False
                
                print(f"\n=== Process Logs ===")
                print(logs)
                
                return success
            else:
                print(f"ERROR: Expected 3 return values, got {len(result)}")
                return False
        else:
            print(f"ERROR: Expected tuple return, got {type(result)}")
            return False
        
    except ValueError as e:
        if "too many values to unpack" in str(e):
            print(f"\n❌ REPRODUCED THE ERROR: {e}")
            print("This is the exact error we were looking for!")
            
            # Let's analyze what the function actually returned
            try:
                raw_result = process_final_merge_with_textures(
                    skinned_fbx_path=skinned_fbx_path,
                    original_model_path=original_model_path,
                    model_name_for_output=model_name,
                    progress_fn=dummy_progress
                )
                print(f"Raw result type: {type(raw_result)}")
                print(f"Raw result: {raw_result}")
                if isinstance(raw_result, (tuple, list)):
                    print(f"Raw result length: {len(raw_result)}")
                    for i, item in enumerate(raw_result):
                        print(f"  item[{i}]: {type(item)} = {item}")
            except Exception as e2:
                print(f"Error in second attempt: {e2}")
            
            return False
        else:
            print(f"❌ Unexpected ValueError: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Test completed successfully!")
    else:
        print("\n💥 Test failed!")
    
    print("\nCleaning up...")
