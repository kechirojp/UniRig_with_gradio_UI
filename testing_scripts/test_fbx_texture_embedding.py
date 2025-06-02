#!/usr/bin/env python3
"""
Test script to debug FBX texture embedding issues
"""

import os
import logging
import bpy
from src.inference.merge import prepare_material_for_fbx_export

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_fbx_texture_embedding():
    """Test FBX texture embedding specifically"""
    logger.info("Testing FBX texture embedding...")
    
    # Clear scene
    bpy.ops.wm.read_factory_settings(use_empty=True)
    
    # Create test scene with textured mesh
    bpy.ops.mesh.primitive_cube_add()
    cube = bpy.context.active_object
    cube.name = "TestCube"
    
    # Create material with multiple texture types
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
    
    # Create base color texture
    base_image = bpy.data.images.new("BaseColor_bc", 512, 512)
    base_image.colorspace_settings.name = 'sRGB'
    base_image.pack()  # Pack into Blender file
    
    base_tex = nodes.new(type='ShaderNodeTexImage')
    base_tex.image = base_image
    base_tex.location = (-300, 200)
    
    # Create normal texture  
    normal_image = bpy.data.images.new("Normal_nrml", 512, 512)
    normal_image.colorspace_settings.name = 'Non-Color'
    normal_image.pack()  # Pack into Blender file
    
    normal_tex = nodes.new(type='ShaderNodeTexImage')
    normal_tex.image = normal_image
    normal_tex.location = (-300, 0)
    
    normal_map = nodes.new(type='ShaderNodeNormalMap')
    normal_map.location = (-150, 0)
    
    # Create roughness texture
    rough_image = bpy.data.images.new("Roughness_r", 512, 512)
    rough_image.colorspace_settings.name = 'Non-Color'
    rough_image.pack()  # Pack into Blender file
    
    rough_tex = nodes.new(type='ShaderNodeTexImage')
    rough_tex.image = rough_image
    rough_tex.location = (-300, -200)
    
    # Connect nodes (simplified connections for testing)
    links.new(base_tex.outputs['Color'], principled.inputs['Base Color'])
    links.new(normal_tex.outputs['Color'], normal_map.inputs['Color'])
    links.new(normal_map.outputs['Normal'], principled.inputs['Normal'])
    links.new(rough_tex.outputs['Color'], principled.inputs['Roughness'])
    links.new(principled.outputs['BSDF'], output.inputs['Surface'])
    
    # Assign material to mesh
    cube.data.materials.append(material)
    
    logger.info(f"Before export setup:")
    logger.info(f"  Materials: {len(bpy.data.materials)}")
    logger.info(f"  Images: {len([img for img in bpy.data.images if img.name not in ['Render Result', 'Viewer Node']])}")
    logger.info(f"  Cube materials: {len(cube.data.materials)}")
    
    # Check image packing status
    for img in bpy.data.images:
        if img.name not in ['Render Result', 'Viewer Node']:
            logger.info(f"  Image {img.name}: packed={img.packed_file is not None}, filepath={img.filepath}")
    
    # Test 1: Export without prepare_material_for_fbx_export
    export_path_1 = "/app/test_fbx_embedding_raw.fbx"
    bpy.ops.export_scene.fbx(
        filepath=export_path_1,
        embed_textures=True,
        path_mode='COPY'
    )
    
    # Test 2: Export with prepare_material_for_fbx_export
    logger.info("Preparing material for FBX export...")
    prepare_material_for_fbx_export(material)
    
    export_path_2 = "/app/test_fbx_embedding_prepared.fbx"
    bpy.ops.export_scene.fbx(
        filepath=export_path_2,
        embed_textures=True,
        path_mode='COPY'
    )
    
    # Check file sizes
    size_1 = os.path.getsize(export_path_1) if os.path.exists(export_path_1) else 0
    size_2 = os.path.getsize(export_path_2) if os.path.exists(export_path_2) else 0
    
    logger.info(f"Export sizes:")
    logger.info(f"  Raw export: {size_1/1024:.1f} KB")
    logger.info(f"  Prepared export: {size_2/1024:.1f} KB")
    
    # Test imports
    def test_import(path, name):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        try:
            bpy.ops.import_scene.fbx(filepath=path)
            materials = len(bpy.data.materials)
            images = len([img for img in bpy.data.images if img.name not in ['Render Result', 'Viewer Node']])
            logger.info(f"  {name} import: {materials} materials, {images} images")
            return materials, images
        except Exception as e:
            logger.error(f"  {name} import failed: {e}")
            return 0, 0
    
    logger.info("Testing imports:")
    test_import(export_path_1, "Raw")
    test_import(export_path_2, "Prepared")
    
    # Test 3: Export with different settings
    bpy.ops.wm.read_factory_settings(use_empty=True)
    
    # Recreate the material and textures again
    bpy.ops.mesh.primitive_cube_add()
    cube = bpy.context.active_object
    material = bpy.data.materials.new(name="TestMaterial")
    material.use_nodes = True
    
    # Just create a simple base color texture
    base_image = bpy.data.images.new("SimpleTexture", 512, 512)
    # Fill with a test pattern
    pixels = [1.0, 0.0, 0.0, 1.0] * (512 * 512)  # Red texture
    base_image.pixels = pixels
    base_image.pack()
    
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    
    principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    output = nodes.new(type='ShaderNodeOutputMaterial')
    tex_node = nodes.new(type='ShaderNodeTexImage')
    tex_node.image = base_image
    
    links.new(tex_node.outputs['Color'], principled.inputs['Base Color'])
    links.new(principled.outputs['BSDF'], output.inputs['Surface'])
    
    cube.data.materials.append(material)
    
    # Test different FBX export settings
    export_path_3 = "/app/test_fbx_embedding_simple.fbx"
    
    logger.info("Testing simple texture with different FBX settings...")
    bpy.ops.export_scene.fbx(
        filepath=export_path_3,
        embed_textures=True,
        path_mode='COPY',
        use_mesh_modifiers=False,
        use_custom_props=False
    )
    
    size_3 = os.path.getsize(export_path_3) if os.path.exists(export_path_3) else 0
    logger.info(f"  Simple export: {size_3/1024:.1f} KB")
    
    test_import(export_path_3, "Simple")

if __name__ == "__main__":
    test_fbx_texture_embedding()
