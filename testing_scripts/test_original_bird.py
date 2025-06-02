#!/usr/bin/env python3
"""
Test texture preservation with the original bird.glb file
"""

import os
import logging
import bpy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_with_original_bird():
    """Test texture preservation with the original bird.glb file"""
    
    original_bird = "/app/examples/bird.glb"
    
    if not os.path.exists(original_bird):
        logger.error(f"Original bird GLB file not found: {original_bird}")
        return
    
    logger.info(f"Testing with original bird GLB: {original_bird}")
    logger.info(f"File size: {os.path.getsize(original_bird)/1024/1024:.1f} MB")
    
    # Load the original GLB file
    bpy.ops.wm.read_factory_settings(use_empty=True)
    try:
        bpy.ops.import_scene.gltf(filepath=original_bird)
    except Exception as e:
        logger.error(f"Failed to import bird GLB: {e}")
        return
    
    # Analyze what was imported
    materials = [mat for mat in bpy.data.materials]
    images = [img for img in bpy.data.images if img.name not in ['Render Result', 'Viewer Node']]
    meshes = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    
    logger.info(f"Original GLB content:")
    logger.info(f"  Materials: {len(materials)}")
    logger.info(f"  Images: {len(images)}")
    logger.info(f"  Meshes: {len(meshes)}")
    
    # Analyze materials and their textures
    for i, mat in enumerate(materials):
        logger.info(f"  Material {i}: {mat.name}")
        if mat.use_nodes and mat.node_tree:
            tex_nodes = [n for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image]
            logger.info(f"    Texture nodes: {len(tex_nodes)}")
            for tex in tex_nodes:
                logger.info(f"      {tex.image.name} (size: {tex.image.size[0]}x{tex.image.size[1]})")
    
    # Test FBX export with the current merge.py settings
    logger.info("Testing FBX export with original bird data...")
    
    # First, pack all images
    for img in images:
        if not img.packed_file:
            img.pack()
            logger.info(f"Packed image: {img.name}")
    
    # Prepare materials for FBX export
    from src.inference.merge import prepare_material_for_fbx_export
    for mat in materials:
        if mat.use_nodes:
            prepare_material_for_fbx_export(mat)
    
    # Export to FBX
    export_path = "/app/test_original_bird_export.fbx"
    bpy.ops.export_scene.fbx(
        filepath=export_path,
        use_selection=False,
        add_leaf_bones=True,
        path_mode='COPY',
        embed_textures=True,
        use_mesh_modifiers=True,
        use_custom_props=True,
        mesh_smooth_type='OFF',
        use_tspace=True,
        bake_anim=False
    )
    
    export_size = os.path.getsize(export_path) if os.path.exists(export_path) else 0
    logger.info(f"FBX export size: {export_size/1024:.1f} KB")
    
    # Re-import and test
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=export_path)
    
    final_materials = len(bpy.data.materials)
    final_images = len([img for img in bpy.data.images if img.name not in ['Render Result', 'Viewer Node']])
    
    logger.info(f"After FBX round-trip:")
    logger.info(f"  Materials: {final_materials}")
    logger.info(f"  Images: {final_images}")
    
    if final_materials > 0 and final_images > 0:
        logger.info("✅ Original bird textures preserved through FBX export!")
        
        # Check mesh material assignments
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                logger.info(f"  Mesh '{obj.name}': {len(obj.data.materials)} materials")
                for i, mat in enumerate(obj.data.materials):
                    if mat:
                        logger.info(f"    Material {i}: {mat.name}")
                        
        return True
    else:
        logger.error("❌ Original bird textures lost during FBX export!")
        return False

if __name__ == "__main__":
    test_with_original_bird()
