#!/usr/bin/env python3
"""
Analyze the actual bird FBX file to understand why materials are lost
"""

import os
import logging
import bpy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_bird_fbx():
    """Analyze the bird FBX file to understand material loss"""
    
    bird_fbx = "/app/pipeline_work/06_final_output/bird/bird_final_textures_fixed.fbx"
    
    if not os.path.exists(bird_fbx):
        logger.error(f"Bird FBX file not found: {bird_fbx}")
        return
    
    logger.info(f"Analyzing bird FBX file: {bird_fbx}")
    logger.info(f"File size: {os.path.getsize(bird_fbx)/1024:.1f} KB")
    
    # Load the FBX file
    bpy.ops.wm.read_factory_settings(use_empty=True)
    try:
        bpy.ops.import_scene.fbx(filepath=bird_fbx)
    except Exception as e:
        logger.error(f"Failed to import bird FBX: {e}")
        return
    
    # Analyze what was imported
    materials = [mat for mat in bpy.data.materials]
    images = [img for img in bpy.data.images if img.name not in ['Render Result', 'Viewer Node']]
    meshes = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    armatures = [obj for obj in bpy.data.objects if obj.type == 'ARMATURE']
    
    logger.info(f"Imported content:")
    logger.info(f"  Materials: {len(materials)}")
    logger.info(f"  Images: {len(images)}")
    logger.info(f"  Meshes: {len(meshes)}")
    logger.info(f"  Armatures: {len(armatures)}")
    
    # Analyze materials
    for i, mat in enumerate(materials):
        logger.info(f"  Material {i}: {mat.name}")
        if mat.use_nodes and mat.node_tree:
            nodes = mat.node_tree.nodes
            logger.info(f"    Nodes: {len(nodes)}")
            for node in nodes:
                logger.info(f"      {node.type}: {node.name}")
                if node.type == 'TEX_IMAGE' and node.image:
                    logger.info(f"        Image: {node.image.name}")
    
    # Analyze images
    for i, img in enumerate(images):
        logger.info(f"  Image {i}: {img.name}")
        logger.info(f"    Size: {img.size[0]}x{img.size[1]}")
        logger.info(f"    Packed: {img.packed_file is not None}")
        logger.info(f"    Filepath: {img.filepath}")
        logger.info(f"    Color space: {img.colorspace_settings.name}")
        if img.packed_file:
            logger.info(f"    Packed size: {len(img.packed_file.data)} bytes")
    
    # Analyze meshes and their materials
    for i, obj in enumerate(meshes):
        logger.info(f"  Mesh {i}: {obj.name}")
        logger.info(f"    Material slots: {len(obj.material_slots)}")
        for j, slot in enumerate(obj.material_slots):
            logger.info(f"      Slot {j}: {slot.material.name if slot.material else 'None'}")
    
    # Try to find the original texture files
    bird_dir = os.path.dirname(bird_fbx)
    logger.info(f"Checking for texture files in: {bird_dir}")
    
    for file in os.listdir(bird_dir):
        if file.lower().endswith(('.png', '.jpg', '.jpeg', '.tga', '.bmp')):
            filepath = os.path.join(bird_dir, file)
            size = os.path.getsize(filepath)
            logger.info(f"  Found texture: {file} ({size/1024:.1f} KB)")
    
    # Check the parent directory for any original FBX
    parent_dir = os.path.dirname(bird_dir)
    logger.info(f"Checking parent directory: {parent_dir}")
    for file in os.listdir(parent_dir):
        if file.lower().endswith('.fbx'):
            filepath = os.path.join(parent_dir, file)
            size = os.path.getsize(filepath)
            logger.info(f"  Found FBX: {file} ({size/1024:.1f} KB)")

if __name__ == "__main__":
    analyze_bird_fbx()
