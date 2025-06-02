#!/usr/bin/env python3
"""
Direct analysis of the enhanced FBX file
"""

import os
import sys
import bpy
from pathlib import Path

def analyze_enhanced_fbx(fbx_path=None):
    """Analyze the enhanced FBX file in Blender"""
    
    # Clear existing scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # Clear existing materials
    for material in bpy.data.materials:
        bpy.data.materials.remove(material)
    
    # Import the enhanced FBX
    if fbx_path is None:
        enhanced_fbx_path = "/app/pipeline_work/06_blender_native/bird/bird_final_rigged_textured.fbx"
    else:
        enhanced_fbx_path = fbx_path
    
    if not os.path.exists(enhanced_fbx_path):
        print(f"❌ Enhanced FBX not found: {enhanced_fbx_path}")
        return False
    
    print(f"🔍 Analyzing enhanced FBX: {enhanced_fbx_path}")
    file_size_mb = os.path.getsize(enhanced_fbx_path) / (1024 * 1024)
    print(f"📏 File size: {file_size_mb:.2f} MB")
    
    try:
        # Import FBX
        bpy.ops.import_scene.fbx(filepath=enhanced_fbx_path)
        
        # Analyze imported content
        objects = [obj for obj in bpy.context.scene.objects]
        print(f"📦 Imported objects: {len(objects)}")
        
        meshes = [obj for obj in objects if obj.type == 'MESH']
        armatures = [obj for obj in objects if obj.type == 'ARMATURE']
        
        print(f"🔺 Mesh objects: {len(meshes)}")
        print(f"🦴 Armatures: {len(armatures)}")
        
        if armatures:
            bones = armatures[0].data.bones
            print(f"   Bones: {len(bones)}")
        
        # Analyze materials
        materials = [mat for mat in bpy.data.materials]
        print(f"🎨 Materials: {len(materials)}")
        
        total_texture_size = 0
        embedded_textures = 0
        
        for i, material in enumerate(materials):
            print(f"\n📎 Material {i+1}: {material.name}")
            
            if material.node_tree:
                nodes = material.node_tree.nodes
                tex_nodes = [node for node in nodes if node.type == 'TEX_IMAGE']
                print(f"   🖼️ Texture nodes: {len(tex_nodes)}")
                
                for j, tex_node in enumerate(tex_nodes):
                    if tex_node.image:
                        image = tex_node.image
                        print(f"      Texture {j+1}: {image.name}")
                        print(f"         Size: {image.size[0]}x{image.size[1]}")
                        print(f"         Source: {image.source}")
                        print(f"         Filepath: {image.filepath}")
                        
                        # Check if texture is packed (embedded)
                        if image.packed_file:
                            packed_size = len(image.packed_file.data)
                            packed_size_mb = packed_size / (1024 * 1024)
                            total_texture_size += packed_size_mb
                            embedded_textures += 1
                            print(f"         ✅ PACKED: {packed_size_mb:.2f} MB")
                        else:
                            print(f"         ❌ NOT PACKED - External reference")
                            
                        # Check connections
                        output_socket = tex_node.outputs.get('Color')
                        if output_socket and output_socket.links:
                            connected_to = [link.to_node.name for link in output_socket.links]
                            print(f"         🔗 Connected to: {connected_to}")
            else:
                print("   ❌ No node tree")
        
        print(f"\n📊 Summary:")
        print(f"   Total embedded textures: {embedded_textures}")
        print(f"   Total packed texture size: {total_texture_size:.2f} MB")
        print(f"   FBX file size: {file_size_mb:.2f} MB")
        print(f"   Estimated geometry + rigging: {file_size_mb - total_texture_size:.2f} MB")
        
        if embedded_textures == 0:
            print("❌ CRITICAL: No textures are embedded in the FBX file!")
        elif total_texture_size < 5.0:
            print("⚠️ WARNING: Embedded texture size is significantly less than expected (7.8MB)")
        else:
            print("✅ Texture embedding appears successful")
            
        return True
        
    except Exception as e:
        print(f"❌ Failed to analyze FBX: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔍 Enhanced FBX Analysis")
    
    # Check for command line argument
    if len(sys.argv) > 1:
        fbx_path = sys.argv[1]
        analyze_enhanced_fbx(fbx_path)
    else:
        analyze_enhanced_fbx()
