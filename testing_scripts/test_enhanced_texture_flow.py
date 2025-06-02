#!/usr/bin/env python3
"""
Test enhanced BlenderNativeTextureFlow with improved FBX export
"""

import os
import time
from pathlib import Path
from gradio_client import Client, handle_file

def test_enhanced_auto_rigging():
    """Test auto-rigging with enhanced texture flow"""
    print("🎯 Testing enhanced auto-rigging pipeline with improved FBX export...")
    
    # Setup client
    client = Client("http://127.0.0.1:7861")
    
    # Test file path
    test_file = "./examples/bird.glb"
    print(f"Testing auto-rigging with: {test_file}")
    
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return False
    
    try:
        start_time = time.time()
        
        # Use handle_file for proper file upload
        result = client.predict(
            handle_file(test_file),  # uploaded_model_path: properly handled file
            "neutral",  # gender: defaults to neutral
            api_name="/run_full_auto_rigging"
        )
        
        elapsed_time = time.time() - start_time
        print(f"✅ Auto-rigging completed in {elapsed_time:.1f} seconds!")
        print(f"📊 Result: {result}")
        
        # Check the outputs
        if result and isinstance(result, (list, tuple)) and len(result) >= 3:
            final_preview = result[0]     # 最終リギング済みモデルプレビュー
            full_logs = result[1]         # フルパイプラインログ  
            final_fbx_path = result[2]    # _最終モデル_fbx
            print(f"📁 Final FBX path: {final_fbx_path}")
            print(f"📄 Processing logs: {full_logs}")
            
            if final_fbx_path and os.path.exists(final_fbx_path):
                file_size_mb = os.path.getsize(final_fbx_path) / (1024 * 1024)
                print(f"📏 Final FBX file size: {file_size_mb:.2f} MB")
                
                # Get original texture sizes for comparison
                texture_dir = "/app/pipeline_work/01_extracted_mesh/bird/textures"
                if os.path.exists(texture_dir):
                    total_texture_size = 0
                    texture_files = []
                    for ext in ['*.png', '*.jpg', '*.jpeg']:
                        texture_files.extend(Path(texture_dir).glob(ext))
                    
                    for tex_file in texture_files:
                        size_mb = tex_file.stat().st_size / (1024 * 1024)
                        total_texture_size += size_mb
                        print(f"   📸 {tex_file.name}: {size_mb:.2f} MB")
                    
                    print(f"📊 Total original texture size: {total_texture_size:.2f} MB")
                    
                    # Quality analysis
                    if file_size_mb >= 7.5:
                        print("✅ EXCELLENT: File size indicates successful texture embedding!")
                        texture_retention = (file_size_mb / total_texture_size) * 100 if total_texture_size > 0 else 0
                        print(f"📈 Texture retention rate: {texture_retention:.1f}%")
                    elif file_size_mb >= 5.0:
                        print("⚠️ PARTIAL: File size is borderline - textures may be partially embedded")
                        texture_retention = (file_size_mb / total_texture_size) * 100 if total_texture_size > 0 else 0
                        print(f"📈 Texture retention rate: {texture_retention:.1f}%")
                    else:
                        print("❌ FAILED: File size too small - texture embedding likely failed")
                        print(f"   Expected: ≥7.5 MB, Got: {file_size_mb:.2f} MB")
                
                # Test if the file can be opened by Blender
                print("\n🔍 Testing FBX file integrity...")
                test_fbx_integrity(final_fbx_path)
                
            else:
                print(f"❌ Final FBX file not found: {final_fbx_path}")
                return False
        else:
            print(f"❌ Unexpected result format: {result}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Auto-rigging failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_fbx_integrity(fbx_path):
    """Test if FBX file can be imported in Blender"""
    import bpy
    
    try:
        # Clear the scene
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        
        # Import the FBX
        bpy.ops.import_scene.fbx(filepath=fbx_path)
        
        # Check what was imported
        imported_objects = [obj for obj in bpy.context.scene.objects]
        print(f"✅ FBX imported successfully: {len(imported_objects)} objects")
        
        # Check for materials
        materials = [mat for mat in bpy.data.materials if mat.name != 'Dots Stroke']
        print(f"📎 Materials found: {len(materials)}")
        
        for mat in materials:
            print(f"   🎨 Material: {mat.name}")
            if mat.node_tree:
                texture_nodes = [node for node in mat.node_tree.nodes if node.type == 'TEX_IMAGE']
                print(f"      📸 Texture nodes: {len(texture_nodes)}")
                for tex_node in texture_nodes:
                    if tex_node.image:
                        print(f"         🖼️ {tex_node.image.name} ({tex_node.image.size[0]}x{tex_node.image.size[1]})")
        
        # Check for armature
        armatures = [obj for obj in imported_objects if obj.type == 'ARMATURE']
        if armatures:
            print(f"🦴 Armature found: {len(armatures[0].data.bones)} bones")
        else:
            print("⚠️ No armature found")
            
        return True
        
    except Exception as e:
        print(f"❌ FBX integrity test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Enhanced BlenderNativeTextureFlow...")
    success = test_enhanced_auto_rigging()
    
    if success:
        print("\n🎉 Enhanced texture flow test completed successfully!")
    else:
        print("\n❌ Enhanced texture flow test failed!")
