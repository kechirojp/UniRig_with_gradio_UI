#!/usr/bin/env python3

import sys
import os
sys.path.append('/app')

# クリーンアップを無効にするため、これらの変数を一時的に設定
os.environ['DISABLE_CLEANUP'] = '1'

from app import load_app_config, process_final_merge_with_textures

def dummy_progress(fraction, desc=''):
    print(f"Progress: {fraction*100:.1f}% - {desc}")

def analyze_fbx_texture_content(fbx_path):
    """FBXファイルのテクスチャ内容を分析"""
    print(f"=== FBXファイル詳細分析: {fbx_path} ===")
    
    file_size = os.path.getsize(fbx_path)
    print(f"ファイルサイズ: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
    
    try:
        with open(fbx_path, 'rb') as f:
            content = f.read(min(file_size, 200000))  # 最初の200KBを分析
            content_str = content.decode('latin-1', errors='ignore')
            
            # テクスチャ関連キーワードを検索
            texture_keywords = [
                'Texture', 'texture',
                'Material', 'material', 
                'Image', 'image',
                'DiffuseColor', 'BaseColor', 'Albedo',
                '.png', '.jpg', '.jpeg',
                'Video', 'video',
                'FileName', 'RelativeFilename',
                'Properties70'
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

def test_with_file_preservation():
    """テクスチャ統合テストをファイル保持で実行"""
    print("=== テクスチャ統合テスト（ファイル保持版） ===")
    
    # Load configuration
    print("Loading configuration...")
    load_app_config()
    
    # Test parameters
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
        return False
        
    if not os.path.exists(skinned_fbx_path):
        print("ERROR: Skinned FBX not found")
        return False
    
    # Check skinned FBX file size before texture integration
    skinned_size = os.path.getsize(skinned_fbx_path)
    print(f"Skinned FBX size before texture integration: {skinned_size / (1024*1024):.2f} MB")
    
    print("\n" + "="*60)
    print("STARTING TEXTURE INTEGRATION PROCESS")
    print("="*60)
    
    # クリーンアップリストを一時的にクリア
    from app import TEMP_FILES_TO_CLEAN
    original_cleanup_list = TEMP_FILES_TO_CLEAN.copy()
    TEMP_FILES_TO_CLEAN.clear()
    
    try:
        result = process_final_merge_with_textures(
            skinned_fbx_path=skinned_fbx_path,
            original_model_path=original_model_path,
            model_name_for_output=model_name,
            progress_fn=dummy_progress
        )
        
        if result is None:
            print("ERROR: Texture integration returned None")
            return False
        
        if len(result) != 3:
            print(f"ERROR: Expected 3 return values, got {len(result)}: {result}")
            return False
            
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
        
        # 詳細な分析を実行（ファイルが保持されている間）
        if final_fbx_path and os.path.exists(final_fbx_path):
            print('\n' + '='*60)
            print('FINAL FBX ANALYSIS')
            print('='*60)
            analyze_fbx_texture_content(final_fbx_path)
            
            # Blenderで最終FBXを分析
            print('\n' + '='*60)
            print('BLENDER ANALYSIS OF FINAL FBX')
            print('='*60)
            blender_analysis_final_fbx(final_fbx_path)
        
        # 関連ディレクトリのファイルを保持したい場合はここに書く
        print('\n' + '='*60)
        print('PRESERVED WORKING DIRECTORIES')
        print('='*60)
        
        # テクスチャ関連ディレクトリを確認
        work_dirs = [
            '/app/pipeline_work/05_texture_preservation',
            '/app/pipeline_work/06_final_output',
            '/app/pipeline_work/05_blender_conversions'
        ]
        
        for work_dir in work_dirs:
            if os.path.exists(work_dir):
                print(f"Preserved directory: {work_dir}")
                for root, dirs, files in os.walk(work_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        file_size = os.path.getsize(file_path)
                        print(f"  {file_path}: {file_size:,} bytes")
        
        return True
        
    except Exception as e:
        print(f"ERROR during texture integration: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # クリーンアップリストを復元（ただし実行はしない）
        TEMP_FILES_TO_CLEAN.clear()
        TEMP_FILES_TO_CLEAN.extend(original_cleanup_list)

def blender_analysis_final_fbx(fbx_path):
    """Blenderを使用してFBXファイルを詳細分析"""
    try:
        import bpy
        
        # シーンをクリア
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        
        for material in bpy.data.materials:
            bpy.data.materials.remove(material)
        for image in bpy.data.images:
            bpy.data.images.remove(image)
        
        # FBXファイルをインポート
        bpy.ops.import_scene.fbx(filepath=fbx_path)
        
        print(f"Imported objects: {len(bpy.data.objects)}")
        print(f"Materials: {len(bpy.data.materials)}")
        print(f"Images: {len(bpy.data.images)}")
        
        # マテリアル分析
        for material in bpy.data.materials:
            print(f"\nMaterial: {material.name}")
            if material.use_nodes:
                print(f"  Node-based material with {len(material.node_tree.nodes)} nodes")
                for node in material.node_tree.nodes:
                    print(f"    Node: {node.name} (Type: {node.type})")
                    if node.type == 'TEX_IMAGE' and node.image:
                        print(f"      Image: {node.image.name}")
                        print(f"      Source: {node.image.source}")
                        if hasattr(node.image, 'packed_file') and node.image.packed_file:
                            print(f"      Packed: {node.image.packed_file.size:,} bytes")
        
        # 画像分析
        for image in bpy.data.images:
            print(f"\nImage: {image.name}")
            print(f"  Source: {image.source}")
            print(f"  Size: {image.size[0]}x{image.size[1]} pixels" if image.size[0] > 0 else "  Size: Unknown")
            if hasattr(image, 'packed_file') and image.packed_file:
                print(f"  Packed file: {image.packed_file.size:,} bytes")
        
    except Exception as e:
        print(f"Error in Blender analysis: {e}")

if __name__ == "__main__":
    success = test_with_file_preservation()
    print(f"\nTest result: {'SUCCESS' if success else 'FAILED'}")
