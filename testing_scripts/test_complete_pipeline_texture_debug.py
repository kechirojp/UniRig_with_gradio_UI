#!/usr/bin/env python3

import sys
import os
sys.path.append('/app')

from app import load_app_config, process_full_auto_rigging

def dummy_progress(fraction, desc=''):
    print(f"Progress: {fraction*100:.1f}% - {desc}")

def main():
    """完全なパイプラインテスト"""
    print("=== Complete Pipeline Test ===")
    
    # 設定の読み込み
    print("Loading configuration...")
    try:
        load_app_config()
        print("✓ Configuration loaded successfully")
    except Exception as e:
        print(f"✗ Failed to load configuration: {e}")
        return False
    
    # テスト用ファイルのパス
    model_name = "bird"
    original_model_path = "/app/examples/bird.glb"
    
    print(f"\nTest parameters:")
    print(f"  Model name: {model_name}")
    print(f"  Original model: {original_model_path}")
    print(f"  Original model exists: {os.path.exists(original_model_path)}")
    
    if not os.path.exists(original_model_path):
        print("✗ Original model file not found")
        return False
    
    try:
        print(f"\n=== Testing Complete Auto-Rigging Pipeline ===")
        print("Calling process_full_auto_rigging...")
        
        result = process_full_auto_rigging(
            original_model_path=original_model_path,
            model_name_for_output=model_name,
            use_texture_preservation=True,  # テクスチャ保持を有効にする
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
                
            # Expected return: (display_glb_path, logs)
            if len(result) == 2:
                display_glb_path, logs = result
                print(f"\n=== Successfully unpacked 2 values ===")
                print(f"Display GLB path: {display_glb_path}")
                
                # ファイル存在チェック
                if display_glb_path and os.path.exists(display_glb_path):
                    file_size = os.path.getsize(display_glb_path)
                    print(f"Display GLB file size: {file_size} bytes ({file_size/1024/1024:.2f} MB)")
                    
                    if file_size > 100000:  # 100KB以上
                        print("✓ SUCCESS: Display GLB has reasonable size")
                    else:
                        print("✗ WARNING: Display GLB file is too small")
                else:
                    print(f"✗ ERROR: Display GLB file does not exist: {display_glb_path}")
                    return False
                
                print(f"\n=== Process Logs ===")
                print(logs)
                
                return True
            else:
                print(f"ERROR: Expected 2 values, got {len(result)}")
                return False
        else:
            print(f"ERROR: Expected tuple return, got {type(result)}")
            return False
            
    except Exception as e:
        print(f"ERROR: Exception during pipeline test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Complete pipeline test successful!")
    else:
        print("\n💥 Complete pipeline test failed!")
    
    print("\nCleaning up...")
