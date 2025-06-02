#!/usr/bin/env python3
"""
Test script to reproduce the material loss issue in make_armature function
"""

import os
import logging
import bpy
import numpy as np
from src.inference.merge import make_armature

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_make_armature_material_preservation():
    """Test if make_armature preserves materials correctly"""
    logger.info("Testing make_armature material preservation...")
    
    # Clear scene
    bpy.ops.wm.read_factory_settings(use_empty=True)
    
    # Create test scene with textured mesh
    bpy.ops.mesh.primitive_cube_add()
    cube = bpy.context.active_object
    cube.name = "TestCube"
    
    # Create material with texture
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
    
    # Create and pack a test image
    image = bpy.data.images.new("TestTexture", 512, 512)
    image.pack()
    
    tex_node = nodes.new(type='ShaderNodeTexImage')
    tex_node.image = image
    tex_node.location = (-300, 0)
    
    # Connect nodes
    links.new(tex_node.outputs['Color'], principled.inputs['Base Color'])
    links.new(principled.outputs['BSDF'], output.inputs['Surface'])
    
    # Assign material to mesh
    cube.data.materials.append(material)
    
    logger.info(f"Before make_armature - Materials: {len(bpy.data.materials)}")
    logger.info(f"Before make_armature - Images: {len([img for img in bpy.data.images if img.name not in ['Render Result', 'Viewer Node']])}")
    logger.info(f"Before make_armature - Cube materials: {len(cube.data.materials)}")
    for i, mat in enumerate(cube.data.materials):
        if mat:
            logger.info(f"  Material {i}: {mat.name}")
    
    # Test make_armature with simple single-bone setup
    vertices = np.array([[0.0, 0.0, 0.0]])  # Single vertex
    bones = np.array([[0.0, 0.0, 0.0, 0.0, 0.0, 1.0]])  # Single bone from origin to (0,0,1)
    parents = [None]
    names = ["TestBone"]
    skin = np.array([[1.0]])  # Single vertex fully weighted to single bone
    
    try:
        make_armature(
            vertices=vertices,
            bones=bones,
            parents=parents,
            names=names,
            skin=skin,
            group_per_vertex=1,
            add_root=False,
            is_vrm=False
        )
        
        logger.info(f"After make_armature - Materials: {len(bpy.data.materials)}")
        logger.info(f"After make_armature - Images: {len([img for img in bpy.data.images if img.name not in ['Render Result', 'Viewer Node']])}")
        
        # Check if cube still has materials
        test_mesh = None
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and obj.name == "TestCube":
                test_mesh = obj
                break
        
        if test_mesh:
            logger.info(f"After make_armature - Cube materials: {len(test_mesh.data.materials)}")
            for i, mat in enumerate(test_mesh.data.materials):
                if mat:
                    logger.info(f"  Material {i}: {mat.name}")
                    if mat.use_nodes and mat.node_tree:
                        tex_nodes = [n for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE']
                        logger.info(f"    Texture nodes: {len(tex_nodes)}")
                        for tex in tex_nodes:
                            if tex.image:
                                logger.info(f"      Image: {tex.image.name}")
        else:
            logger.error("TestCube mesh not found after make_armature!")
        
        # Export to FBX to test final preservation
        export_path = "/app/test_make_armature_export.fbx"
        bpy.ops.export_scene.fbx(
            filepath=export_path,
            embed_textures=True,
            path_mode='COPY'
        )
        
        # Re-import to verify
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=export_path)
        
        final_materials = len(bpy.data.materials)
        final_images = len([img for img in bpy.data.images if img.name not in ['Render Result', 'Viewer Node']])
        
        logger.info(f"After FBX round-trip - Materials: {final_materials}")
        logger.info(f"After FBX round-trip - Images: {final_images}")
        
        if final_materials == 0:
            logger.error("❌ Materials were lost during make_armature + FBX export process")
            return False
        else:
            logger.info("✅ Materials preserved through make_armature + FBX export process")
            return True
            
    except Exception as e:
        logger.error(f"Error during make_armature: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_make_armature_material_preservation()
