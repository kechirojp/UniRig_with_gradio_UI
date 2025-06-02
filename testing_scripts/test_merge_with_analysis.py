#!/usr/bin/env python3
"""
マージ処理を実行してFBXファイルの構造を分析
クリーンアップ前にファイルを検証する
"""
import os
import sys
import shutil
from app import process_merge_model, load_app_config

def dummy_progress(progress, desc=""):
    print(f"Progress: {progress:.2f} - {desc}")

def test_merge_with_analysis():
    """マージテストとFBX分析を実行"""
    
    # Initialize config first
    try:
        load_app_config()
        print("✓ アプリケーション設定を初期化しました")
    except Exception as e:
        print(f"❌ 設定初期化エラー: {e}")
        return False
    
    print("=== Testing Merge Model Process with Analysis ===")
    
    # Test parameters
    original_model_path = "/app/examples/bird.glb"
    skinned_fbx_path = "/app/pipeline_work/03_skinning_output/bird/skinned_model.fbx"
    skinning_npz_path = "/app/pipeline_work/03_skinning_output/bird/predict_skin.npz"
    model_name = "bird"
    
    print(f"Testing with:")
    print(f"  Original model: {original_model_path}")
    print(f"  Skinned FBX: {skinned_fbx_path}")
    print(f"  Skinning NPZ: {skinning_npz_path}")
    
    print(f"\nFile existence check:")
    print(f"  Original model exists: {os.path.exists(original_model_path)}")
    print(f"  Skinned FBX exists: {os.path.exists(skinned_fbx_path)}")
    print(f"  Skinning NPZ exists: {os.path.exists(skinning_npz_path)}")
    
    if not os.path.exists(skinned_fbx_path):
        print("ERROR: Skinned FBX file not found. Please run skinning step first.")
        return False
        
    if not os.path.exists(skinning_npz_path):
        print("ERROR: Skinning NPZ file not found. Please run skinning step first.")
        return False
    
    try:
        print(f"\n=== Starting merge process ===")
        
        display_glb_path, logs, final_fbx_path = process_merge_model(
            original_model_path=original_model_path,
            skinned_fbx_path=skinned_fbx_path,
            skinning_npz_path=skinning_npz_path,
            model_name_for_output=model_name,
            progress_fn=dummy_progress
        )
        
        print(f"\n=== Merge Results ===")
        print(f"Display GLB path: {display_glb_path}")
        print(f"Final FBX path: {final_fbx_path}")
        
        # Copy FBX file to permanent location for analysis BEFORE cleanup
        if final_fbx_path and os.path.exists(final_fbx_path):
            analysis_dir = "/app/fbx_analysis"
            os.makedirs(analysis_dir, exist_ok=True)
            
            permanent_fbx_path = os.path.join(analysis_dir, "merged_for_analysis.fbx")
            shutil.copy2(final_fbx_path, permanent_fbx_path)
            print(f"\n📋 FBXファイルを分析用にコピー: {permanent_fbx_path}")
            
            # Also copy GLB if available
            if display_glb_path and os.path.exists(display_glb_path):
                permanent_glb_path = os.path.join(analysis_dir, "merged_for_analysis.glb")
                shutil.copy2(display_glb_path, permanent_glb_path)
                print(f"📋 GLBファイルを分析用にコピー: {permanent_glb_path}")
        
        print(f"\n=== Process Logs ===")
        print(logs)
        
        if final_fbx_path and os.path.exists(final_fbx_path):
            file_size = os.path.getsize(final_fbx_path)
            print(f"\n✓ SUCCESS: Final FBX created successfully!")
            print(f"  File: {final_fbx_path}")
            print(f"  Size: {file_size:,} bytes")
            return True
        else:
            print(f"\n✗ FAILED: Final FBX not created or empty")
            return False
            
    except Exception as e:
        print(f"\n✗ ERROR during merge process: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_merge_with_analysis()
    if success:
        print("\n🎉 Merge test with analysis completed successfully!")
    else:
        print("\n❌ Merge test failed!")
    sys.exit(0 if success else 1)
