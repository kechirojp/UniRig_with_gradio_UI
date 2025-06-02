#!/usr/bin/env python3
"""
Test script to properly test FBX texture embedding with correct image data
"""

import os
import logging
import bpy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_proper_fbx_texture_embedding():
    """Test FBX texture embedding with properly created images"""
    logger.info("Testing proper FBX texture embedding...")
    
    # Clear scene
    bpy.ops.wm.read_factory_settings(use_empty=True)
    
    # Create test scene with textured mesh
    bpy.ops.mesh.primitive_cube_add()
    cube = bpy.context.active_object
    cube.name = "TestCube"
    
    # Create material
    material = bpy.data.materials.new(name="TestMaterial")
    material.use_nodes = True
    
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    
    # Create nodes
    principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    principled.location = (0, 0)
    
    output = nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (300, 0)
    
    # Create base color texture with actual pixel data
    base_image = bpy.data.images.new("BaseColor", 256, 256)
    # Create red checkerboard pattern
    pixels = []
    for y in range(256):
        for x in range(256):
            if (x // 32 + y // 32) % 2:
                pixels.extend([1.0, 0.0, 0.0, 1.0])  # Red
            else:
                pixels.extend([1.0, 1.0, 1.0, 1.0])  # White
    base_image.pixels = pixels
    base_image.pack()  # Pack the image data
    
    # Verify packing worked
    logger.info(f"Base image packed: {base_image.packed_file is not None}")
    logger.info(f"Base image size: {len(base_image.packed_file.data) if base_image.packed_file else 0} bytes")
    
    tex_node = nodes.new(type='ShaderNodeTexImage')
    tex_node.image = base_image
    tex_node.location = (-300, 0)
    
    # Connect nodes
    links.new(tex_node.outputs['Color'], principled.inputs['Base Color'])
    links.new(principled.outputs['BSDF'], output.inputs['Surface'])
    
    # Assign material to mesh
    cube.data.materials.append(material)
    
    logger.info(f"Before export:")
    logger.info(f"  Materials: {len(bpy.data.materials)}")
    logger.info(f"  Images: {len([img for img in bpy.data.images if img.name not in ['Render Result', 'Viewer Node']])}")
    logger.info(f"  Cube materials: {len(cube.data.materials)}")
    
    # Export to FBX with texture embedding
    export_path = "/app/test_proper_fbx_embedding.fbx"
    bpy.ops.export_scene.fbx(
        filepath=export_path,
        embed_textures=True,
        path_mode='COPY'
    )
    
    # Check file size
    size = os.path.getsize(export_path) if os.path.exists(export_path) else 0
    logger.info(f"Export size: {size/1024:.1f} KB")
    
    # Re-import to test
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=export_path)
    
    materials_after = len(bpy.data.materials)
    images_after = len([img for img in bpy.data.images if img.name not in ['Render Result', 'Viewer Node']])
    
    logger.info(f"After import:")
    logger.info(f"  Materials: {materials_after}")
    logger.info(f"  Images: {images_after}")
    
    # Check mesh materials
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            logger.info(f"  Mesh '{obj.name}': {len(obj.data.materials)} materials")
            for i, mat in enumerate(obj.data.materials):
                if mat:
                    logger.info(f"    Material {i}: {mat.name}")
                    if mat.use_nodes and mat.node_tree:
                        tex_nodes = [n for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE']
                        logger.info(f"      Texture nodes: {len(tex_nodes)}")
                        for tex in tex_nodes:
                            if tex.image:
                                logger.info(f"        Image: {tex.image.name}")
    
    if materials_after > 0 and images_after > 0:
        logger.info("✅ FBX texture embedding successful!")
        return True
    else:
        logger.error("❌ FBX texture embedding failed!")
        return False

if __name__ == "__main__":
    test_proper_fbx_texture_embedding()
