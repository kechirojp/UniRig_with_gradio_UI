#!/usr/bin/env python3

import sys
import os
sys.path.append('/app')

from app import load_app_config, process_final_merge_with_textures

def dummy_progress(fraction, desc=''):
    print(f"Progress: {fraction*100:.1f}% - {desc}")

def main():
    print("=== テクスチャ統合テスト ===")
    
    # Load configuration
    print("Loading configuration...")
    load_app_config()
    
    # Test parameters (最新のテスト結果から)
    model_name = 'bird'
    original_model_path = '/app/examples/bird.glb'
    skinned_fbx_path = '/app/pipeline_work/03_skinning_output/bird/skinned_model.fbx'
    
    print(f"Testing texture integration for {model_name}")
    print(f"Original model: {original_model_path}")
    print(f"Skinned FBX: {skinned_fbx_path}")
    print(f"Original model exists: {os.path.exists(original_model_path)}")
    print(f"Skinned FBX exists: {os.path.exists(skinned_fbx_path)}")
    
    if not os.path.exists(original_model_path):
        print("ERROR: Original model not found")
        return
        
    if not os.path.exists(skinned_fbx_path):
        print("ERROR: Skinned FBX not found")
        return
    
    # Check skinned FBX file size before texture integration
    skinned_size = os.path.getsize(skinned_fbx_path)
    print(f"Skinned FBX size before texture integration: {skinned_size / (1024*1024):.2f} MB")
    
    print("\n" + "="*60)
    print("STARTING TEXTURE INTEGRATION PROCESS")
    print("="*60)
    
    # Run texture integration process
    try:
        result = process_final_merge_with_textures(
            skinned_fbx_path=skinned_fbx_path,
            original_model_path=original_model_path,
            model_name_for_output=model_name,
            progress_fn=dummy_progress
        )
        
        if result is None:
            print("ERROR: Texture integration returned None")
            return
        
        if len(result) != 3:
            print(f"ERROR: Expected 3 return values, got {len(result)}: {result}")
            return
            
        display_glb_path, logs, final_fbx_path = result
        
        print('\n' + '='*60)
        print('TEXTURE INTEGRATION RESULTS')
        print('='*60)
        print(f'Display GLB: {display_glb_path}')
        print(f'Final FBX: {final_fbx_path}')
        
        # Check final file sizes
        if final_fbx_path and os.path.exists(final_fbx_path):
            final_size = os.path.getsize(final_fbx_path)
            print(f'Final FBX size: {final_size / (1024*1024):.2f} MB')
            
            size_increase = final_size - skinned_size
            print(f'Size increase: {size_increase / (1024*1024):.2f} MB')
            
            if final_size > skinned_size * 1.5:  # 期待される増加
                print("✓ SUCCESS: Final FBX size significantly increased - textures likely embedded")
            elif final_size > skinned_size:
                print("? PARTIAL: Final FBX size increased, but may not contain all textures")
            else:
                print("✗ FAILED: Final FBX size not increased - textures not embedded")
        
        if display_glb_path and os.path.exists(display_glb_path):
            display_size = os.path.getsize(display_glb_path)
            print(f'Display GLB size: {display_size / (1024*1024):.2f} MB')
        
        print('\n' + '='*60)
        print('DETAILED LOGS')
        print('='*60)
        print(logs)
        
        # Analyze final FBX content
        if final_fbx_path and os.path.exists(final_fbx_path):
            print('\n' + '='*60)
            print('FINAL FBX ANALYSIS')
            print('='*60)
            analyze_fbx_texture_content(final_fbx_path)
        
    except Exception as e:
        print(f"ERROR during texture integration: {e}")
        import traceback
        traceback.print_exc()

def analyze_fbx_texture_content(fbx_path):
    """FBXファイルのテクスチャ内容を分析"""
    try:
        with open(fbx_path, 'rb') as f:
            content = f.read(min(os.path.getsize(fbx_path), 200000))  # 最初の200KBを分析
            content_str = content.decode('latin-1', errors='ignore')
            
            # テクスチャ関連キーワードを検索
            texture_keywords = [
                'Texture', 'texture',
                'Material', 'material', 
                'Image', 'image',
                'DiffuseColor', 'BaseColor', 'Albedo',
                '.png', '.jpg', '.jpeg',
                'Video', 'video',
                'FileName', 'RelativeFilename'
            ]
            
            texture_found = False
            for keyword in texture_keywords:
                count = content_str.count(keyword)
                if count > 0:
                    print(f"'{keyword}': {count}回出現")
                    texture_found = True
            
            if texture_found:
                print("✓ Texture references found in FBX file")
            else:
                print("✗ No texture references found in FBX file")
                
    except Exception as e:
        print(f"Error analyzing FBX content: {e}")

if __name__ == "__main__":
    main()
