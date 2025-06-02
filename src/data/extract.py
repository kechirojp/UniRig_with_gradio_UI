#!/usr/bin/env python3
"""
Mesh extraction script for UniRig Gradio application.
Handles 3D model loading, processing, and NPZ data extraction.
"""

import sys
import os
import logging
import traceback
import bpy
from collections import defaultdict
from tqdm import tqdm
import numpy as np
from numpy import ndarray
from typing import Dict, Tuple, List, Optional, Union
import trimesh
import fast_simplification
from scipy.spatial import KDTree
import gc
import argparse
import yaml
from box import Box
import datetime
import signal
import atexit
import shutil  # Added for texture file management
from pathlib import Path  # Added for path handling

# Force disable Blender's default crash handler to prevent segfaults
try:
    # Clear any existing atexit handlers from Blender
    atexit._clear()
    
    # Set up signal handlers to handle crashes gracefully
    def signal_handler(signum, frame):
        print(f"DEBUG: Received signal {signum}, forcing clean exit")
        try:
            os._exit(1)
        except:
            pass
    
    signal.signal(signal.SIGSEGV, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
except Exception as e:
    print(f"DEBUG: Warning setting up signal handlers: {e}")

# Ensure proper Python path setup
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)  # src directory
root_dir = os.path.dirname(parent_dir)     # app directory

# Add necessary paths to sys.path
for path in ["/app", root_dir, parent_dir, current_dir]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Import logging and RawData with comprehensive fallback
log_functions_imported = False
raw_data_imported = False

# Try multiple import strategies
try:
    # Try absolute imports from /app
    from src.data.log import new_entry, add_error, add_warning, new_log, end_log
    from src.data.raw_data import RawData
    log_functions_imported = True
    raw_data_imported = True
    print("Successfully imported using absolute paths from /app")
except ImportError as e:
    print(f"Absolute import failed: {e}")
    try:
        # Try relative imports
        from .log import new_entry, add_error, add_warning, new_log, end_log
        from .raw_data import RawData
        log_functions_imported = True
        raw_data_imported = True
        print("Successfully imported using relative imports")
    except ImportError as e:
        print(f"Relative import failed: {e}")
        try:
            # Try direct module imports
            from data.log import new_entry, add_error, add_warning, new_log, end_log
            from data.raw_data import RawData
            log_functions_imported = True
            raw_data_imported = True
            print("Successfully imported using data module imports")
        except ImportError as e:
            print(f"Data module import failed: {e}")

# Create fallback implementations if imports failed
if not log_functions_imported:
    print("WARNING: Could not import log functions, using minimal implementations")
    def new_entry(*args, **kwargs): 
        print(f"LOG: {args}")
    def add_error(*args, **kwargs): 
        print(f"ERROR: {args}")
    def add_warning(*args, **kwargs): 
        print(f"WARNING: {args}")
    def new_log(*args, **kwargs): 
        print(f"NEW_LOG: {args}")
    def end_log(*args, **kwargs): 
        print(f"END_LOG: {args}")

if not raw_data_imported:
    print("WARNING: Could not import RawData class, using minimal implementation")
    # Minimal RawData implementation
    class RawData:
        def __init__(self, vertices, vertex_normals, faces, face_normals, joints, tails, skin, no_skin, parents, names, matrix_local, uv_coords=None, materials=None):
            self.vertices = vertices
            self.vertex_normals = vertex_normals
            self.faces = faces
            self.face_normals = face_normals
            self.joints = joints
            self.tails = tails
            self.skin = skin
            self.no_skin = no_skin
            self.parents = parents
            self.names = names
            self.matrix_local = matrix_local
            self.uv_coords = uv_coords or []
            self.materials = materials or []
        
        def check(self):
            # Minimal validation
            if self.parents is not None:
                for i, pid in enumerate(self.parents):
                    if i == 0:
                        assert pid is None
                    else:
                        assert pid is not None
                        assert pid < i
        
        def save(self, path):
            np.savez_compressed(
                path,
                vertices=self.vertices,
                vertex_normals=self.vertex_normals,
                faces=self.faces,
                face_normals=self.face_normals,
                joints=self.joints,
                tails=self.tails,
                skin=self.skin,
                no_skin=self.no_skin,
                parents=self.parents,
                names=self.names,
                matrix_local=self.matrix_local,
                uv_coords=self.uv_coords,
                materials=self.materials,
                path=path,
                cls='RawData'
            )


def load(filepath: str):
    """Load 3D model file into Blender with safe cleanup."""
    print(f"DEBUG: Loading file: {filepath}")
    print(f"DEBUG: File exists: {os.path.exists(filepath)}")
    print(f"DEBUG: File size: {os.path.getsize(filepath) if os.path.exists(filepath) else 'N/A'}")
    
    old_objs = set(bpy.context.scene.objects)
    print(f"DEBUG: Objects in scene before import: {len(old_objs)}")
    
    if not os.path.exists(filepath):
        raise ValueError(f'File {filepath} does not exist !')
    
    try:
        # Clear any existing selection before import
        bpy.ops.object.select_all(action='DESELECT')
        print("DEBUG: Cleared selection")
        
        if filepath.endswith(".vrm"):
            print("DEBUG: Importing VRM file")
            # enable vrm addon and load vrm model
            bpy.ops.preferences.addon_enable(module='vrm')
            
            bpy.ops.import_scene.vrm(
                filepath=filepath,
                use_addon_preferences=True,
                extract_textures_into_folder=True,
                make_new_texture_folder=False,
                set_shading_type_to_material_on_import=True,
                set_view_transform_to_standard_on_import=True,
                set_armature_display_to_wire=True,
                set_armature_display_to_show_in_front=True,
                set_armature_bone_shape_to_default=True,
                disable_bake=False,
            )
        elif filepath.endswith(".obj"):
            print("DEBUG: Importing OBJ file")
            bpy.ops.wm.obj_import(filepath=filepath)
        elif filepath.endswith(".fbx") or filepath.endswith(".FBX"):
            print("DEBUG: Importing FBX file with texture preservation")
            bpy.ops.import_scene.fbx(filepath=filepath, ignore_leaf_bones=False, use_image_search=True)
        elif filepath.endswith(".glb") or filepath.endswith(".gltf"):
            print("DEBUG: Importing GLB/GLTF file with texture preservation")
            bpy.ops.import_scene.gltf(filepath=filepath, import_pack_images=True)
        elif filepath.endswith(".dae"):
            print("DEBUG: Importing DAE file")
            bpy.ops.wm.collada_import(filepath=filepath)
        elif filepath.endswith(".blend"):
            print("DEBUG: Loading BLEND file")
            with bpy.data.libraries.load(filepath) as (data_from, data_to):
                data_to.objects = data_from.objects
            for obj in data_to.objects:
                if obj is not None:
                    bpy.context.collection.objects.link(obj)
        else:
            raise ValueError(f"not suported type {filepath}")
            
        print("DEBUG: Import operation completed")
        # Force scene update after import
        bpy.context.view_layer.update()
        print("DEBUG: Scene updated")
        
    except Exception as e:
        print(f"DEBUG: Exception during import: {e}")
        raise ValueError(f"failed to load {filepath}: {str(e)}")

    new_objs = set(bpy.context.scene.objects) - old_objs
    print(f"DEBUG: New objects imported: {len(new_objs)}")
    
    armature = [x for x in new_objs if x.type=="ARMATURE"]
    print(f"DEBUG: Armatures found: {len(armature)}")
    
    if len(armature)==0:
        print("DEBUG: No armature found in imported model")
        return None
    if len(armature)>1:
        print(f"DEBUG: Multiple armatures found: {[a.name for a in armature]}")
        # Use the first armature found
        armature = [armature[0]]
    
    armature = armature[0]
    print(f"DEBUG: Using armature: {armature.name}")
    
    # Process armature safely
    try:
        armature.select_set(True)
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='EDIT')
        
        # Reset bone rolls safely
        for bone in bpy.data.armatures[0].edit_bones:
            bone.roll = 0.

        bpy.ops.object.mode_set(mode='OBJECT')
        armature.select_set(False)
        
    except Exception as e:
        print(f"DEBUG: Warning during armature processing: {e}")
    
    bpy.ops.object.select_all(action='DESELECT')
    print(f"DEBUG: Successfully loaded {filepath}")
    return armature


def clean_bpy():
    """Remove all data in bpy with comprehensive cleanup."""
    print("DEBUG: Entering clean_bpy")
    try:
        # Ensure we're in object mode
        if bpy.context.object and bpy.context.object.mode != 'OBJECT':
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except:
                pass
        
        # Clear selection and delete all objects
        try:
            bpy.ops.object.select_all(action='SELECT')
            bpy.ops.object.delete(use_global=False)
        except:
            pass
        
        # Safe cleanup function for data blocks
        def safe_remove_blocks(block_collection, block_type_name):
            try:
                blocks_to_remove = list(block_collection)
                for block in blocks_to_remove:
                    try:
                        block_collection.remove(block, do_unlink=True)
                    except:
                        pass
                print(f"DEBUG: Cleaned {len(blocks_to_remove)} {block_type_name} blocks")
            except Exception as e:
                print(f"DEBUG: Error cleaning {block_type_name}: {e}")
        
        # Clean all data blocks systematically
        safe_remove_blocks(bpy.data.meshes, "mesh")
        safe_remove_blocks(bpy.data.materials, "material")
        safe_remove_blocks(bpy.data.textures, "texture")
        safe_remove_blocks(bpy.data.images, "image")
        safe_remove_blocks(bpy.data.armatures, "armature")
        safe_remove_blocks(bpy.data.curves, "curve")
        safe_remove_blocks(bpy.data.cameras, "camera")
        safe_remove_blocks(bpy.data.lights, "light")
        safe_remove_blocks(bpy.data.collections, "collection")
        safe_remove_blocks(bpy.data.actions, "action")
        safe_remove_blocks(bpy.data.node_groups, "node_group")
        safe_remove_blocks(bpy.data.worlds, "world")
        
        # Clean orphaned data
        try:
            bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
        except:
            pass
        
        # Force context and view layer updates
        try:
            bpy.context.view_layer.update()
            if hasattr(bpy.context.scene, 'frame_set'):
                bpy.context.scene.frame_set(1)  # Reset timeline
        except:
            pass
        
        # Clear undo history to free memory
        try:
            bpy.ops.ed.undo_history_clear()
        except:
            pass
        
    except Exception as e:
        print(f"DEBUG: Error during cleanup: {e}")
    
    print("DEBUG: Exiting clean_bpy")


def process_mesh(objects):
    """Process mesh data from Blender objects with texture preservation."""
    print("DEBUG: Entering process_mesh with texture preservation")
    
    mesh_objects = [obj for obj in objects if obj.type == 'MESH']
    if not mesh_objects:
        print("No mesh objects found")
        return np.array([]), np.array([]), np.array([]), np.array([]), [], []
    
    all_vertices = []
    all_vertex_normals = []
    all_faces = []
    all_uv_coordinates = []
    all_materials = []
    vertex_offset = 0
    
    for obj in mesh_objects:
        print(f"Processing mesh object: {obj.name}")
        
        try:
            # Apply modifiers and get mesh data
            depsgraph = bpy.context.evaluated_depsgraph_get()
            eval_obj = obj.evaluated_get(depsgraph)
            mesh = eval_obj.to_mesh()
            
            # Ensure mesh is ready for processing
            mesh.calc_loop_triangles()
            
            # Calculate normals safely
            try:
                mesh.update()
            except:
                pass
            
            # Extract vertices
            vertices = np.array([[v.co.x, v.co.y, v.co.z] for v in mesh.vertices])
            
            # Extract vertex normals
            vertex_normals = np.array([[v.normal.x, v.normal.y, v.normal.z] for v in mesh.vertices])
            
            # Extract faces (triangulate)
            faces = [[mesh.loops[loop_idx].vertex_index + vertex_offset for loop_idx in tri.loops] 
                    for tri in mesh.loop_triangles]
            
            # Extract UV coordinates if available
            uv_coords = []
            if mesh.uv_layers:
                uv_layer = mesh.uv_layers.active
                if uv_layer:
                    print(f"DEBUG: Extracting UV coordinates from layer: {uv_layer.name}")
                    uv_coords = [[uv_layer.data[loop_idx].uv.x, uv_layer.data[loop_idx].uv.y] 
                               for tri in mesh.loop_triangles for loop_idx in tri.loops]
            
            # Extract material information
            materials = []
            if obj.data.materials:
                print(f"DEBUG: Found {len(obj.data.materials)} materials")
                for material in obj.data.materials:
                    if material:
                        material_info = {
                            'name': material.name,
                            'use_nodes': material.use_nodes if hasattr(material, 'use_nodes') else False
                        }
                        
                        # Extract texture information if available
                        if material.use_nodes and material.node_tree:
                            texture_nodes = [node for node in material.node_tree.nodes 
                                           if node.type == 'TEX_IMAGE']
                            if texture_nodes:
                                material_info['textures'] = []
                                for tex_node in texture_nodes:
                                    if tex_node.image:
                                        material_info['textures'].append({
                                            'name': tex_node.image.name,
                                            'filepath': tex_node.image.filepath if hasattr(tex_node.image, 'filepath') else ''
                                        })
                        materials.append(material_info)
            
            all_vertices.append(vertices)
            all_vertex_normals.append(vertex_normals)
            all_faces.extend(faces)
            all_uv_coordinates.append(uv_coords)
            all_materials.append(materials)
            vertex_offset += len(vertices)
            
            # Clean up mesh data immediately
            eval_obj.to_mesh_clear()
            
            # Force garbage collection after each mesh
            import gc
            gc.collect()
            
        except Exception as e:
            print(f"DEBUG: Error processing mesh {obj.name}: {e}")
            continue
    
    # Combine all mesh data
    if all_vertices:
        vertices = np.vstack(all_vertices)
        vertex_normals = np.vstack(all_vertex_normals)
        faces = np.array(all_faces)
        
        # Calculate face normals
        face_normals = np.zeros((len(faces), 3))
        for i, face in enumerate(faces):
            if len(face) >= 3:
                v0, v1, v2 = vertices[face[:3]]
                normal = np.cross(v1 - v0, v2 - v0)
                norm = np.linalg.norm(normal)
                if norm > 0:
                    normal = normal / norm
                face_normals[i] = normal
                
        # Combine UV coordinates
        combined_uv_coords = []
        for uv_list in all_uv_coordinates:
            combined_uv_coords.extend(uv_list)
        
        # Combine materials
        combined_materials = []
        for material_list in all_materials:
            combined_materials.extend(material_list)
            
        print(f"DEBUG: Extracted {len(combined_uv_coords)} UV coordinates")
        print(f"DEBUG: Extracted {len(combined_materials)} materials")
        
    else:
        vertices = np.array([])
        vertex_normals = np.array([])
        faces = np.array([])
        face_normals = np.array([])
        combined_uv_coords = []
        combined_materials = []
    
    print(f"DEBUG: Processed {len(vertices)} vertices, {len(faces)} faces")
    print("DEBUG: Exiting process_mesh with texture preservation")
    
    return vertices, vertex_normals, faces, face_normals, combined_uv_coords, combined_materials


def process_armature(armature, num_vertices=0):
    """Process armature/skeleton data."""
    print("DEBUG: Entering process_armature")
    
    if armature is None or (hasattr(armature, 'data') and len(armature.data.bones) == 0):
        print("No armature found or armature has no bones - creating default root joint")
        # Create a default root joint at origin to ensure non-empty joint arrays
        joints = np.array([[0.0, 0.0, 0.0]])  # Root at origin
        tails = np.array([[0.0, 0.0, 1.0]])   # Tail pointing up
        parents = np.array([None], dtype=object)  # Root has no parent
        names = np.array(['root'])
        matrix_local = np.array([np.eye(4)])  # Identity matrix
        
        # Create proper 2D skin array: (num_vertices, 1) for single root joint
        if num_vertices > 0:
            skin = np.ones((num_vertices, 1))  # All vertices weighted to root joint
            no_skin = np.zeros(num_vertices, dtype=bool)
        else:
            skin = np.zeros((0, 1))
            no_skin = np.zeros(0, dtype=bool)
        
        print(f"DEBUG: Created default root joint")
        print(f"DEBUG: Created skin matrix shape: {skin.shape}")
        print(f"DEBUG: Created no_skin array shape: {no_skin.shape}")
        print("DEBUG: Exiting process_armature")
        
        return joints, tails, skin, no_skin, parents, names, matrix_local
    
    bones = armature.data.bones
    joints = []
    tails = []
    parents = []
    names = []
    matrix_local = []
    
    bone_index_map = {bone.name: i for i, bone in enumerate(bones)}
    
    for i, bone in enumerate(bones):
        # Joint position (head of bone)
        joints.append([bone.head_local.x, bone.head_local.y, bone.head_local.z])
        
        # Tail position
        tails.append([bone.tail_local.x, bone.tail_local.y, bone.tail_local.z])
        
        # Parent index
        if bone.parent is None:
            parents.append(None)  # Root bone has no parent
        else:
            parents.append(bone_index_map[bone.parent.name])
        
        # Bone name
        names.append(bone.name)
        
        # Local matrix
        matrix = bone.matrix_local
        matrix_local.append([[matrix[i][j] for j in range(4)] for i in range(4)])
    
    # Convert to numpy arrays
    joints = np.array(joints) if joints else np.array([])
    tails = np.array(tails) if tails else np.array([])
    parents = np.array(parents, dtype=object) if parents else np.array([])
    names = np.array(names) if names else np.array([])
    matrix_local = np.array(matrix_local) if matrix_local else np.array([])
    
    # Create proper 2D skinning data with correct dimensions
    num_joints = len(joints)
    if num_vertices > 0 and num_joints > 0:
        # Create skin weights matrix: (num_vertices, num_joints)
        # For now, use dummy uniform weights (each vertex equally weighted to all bones)
        skin = np.ones((num_vertices, num_joints)) / num_joints if num_joints > 0 else np.zeros((num_vertices, 0))
        # Create no_skin array (vertices not affected by skinning)
        no_skin = np.zeros(num_vertices, dtype=bool)  # All vertices are skinned
    else:
        # Empty arrays with correct shapes
        skin = np.zeros((num_vertices, 0)) if num_vertices > 0 else np.zeros((0, 0))
        no_skin = np.zeros(num_vertices if num_vertices > 0 else 0, dtype=bool)
    
    print(f"DEBUG: Processed {len(joints)} bones")
    print(f"DEBUG: Created skin matrix shape: {skin.shape}")
    print(f"DEBUG: Created no_skin array shape: {no_skin.shape}")
    print("DEBUG: Exiting process_armature")
    
    return joints, tails, skin, no_skin, parents, names, matrix_local


def save_raw_data(output_dir, vertices, vertex_normals, faces, face_normals, 
                 joints, tails, skin, no_skin, parents, names, matrix_local, 
                 uv_coords=None, materials=None):
    """Save processed data to NPZ file with texture information."""
    print("DEBUG: Entering save_raw_data with texture preservation")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Create RawData object
    raw_data = RawData(
        vertices=vertices,
        vertex_normals=vertex_normals,
        faces=faces,
        face_normals=face_normals,
        joints=joints,
        tails=tails,
        skin=skin,
        no_skin=no_skin,
        parents=parents,
        names=names,
        matrix_local=matrix_local,
        uv_coords=uv_coords or [],
        materials=materials or []
    )
    
    # Save to NPZ file
    npz_path = os.path.join(output_dir, "raw_data.npz")
    raw_data.save(npz_path)
    
    # Create inference_datalist.txt
    datalist_path = os.path.join(output_dir, "inference_datalist.txt")
    with open(datalist_path, 'w') as f:
        f.write(f"{npz_path}\n")
    
    print(f"DEBUG: Saved raw data to {npz_path}")
    print(f"DEBUG: Created datalist at {datalist_path}")
    print("DEBUG: Exiting save_raw_data")


def extract_builtin(config_dict, model_path, output_dir, log_path=None, log_name=None):
    """Main extraction function with complete 3D model processing pipeline."""
    print("DEBUG: Starting extract_builtin")
    print(f"Model path: {model_path}")
    print(f"Output directory: {output_dir}")
    print(f"Model path exists: {os.path.exists(model_path)}")
    print(f"Output directory exists: {os.path.exists(output_dir)}")
    
    try:
        # Initialize logging if parameters provided
        if log_path and log_name:
            new_log(log_path, log_name)
            new_entry("Starting mesh extraction")
        
        # Clean Blender scene
        print("DEBUG: Cleaning Blender scene")
        clean_bpy()
        
        # Load 3D model
        print("DEBUG: Loading 3D model...")
        try:
            armature = load(model_path)
            print(f"DEBUG: Armature loaded: {armature}")
        except Exception as load_error:
            print(f"DEBUG: Error loading model: {load_error}")
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            raise
        
        # Get all objects in scene
        try:
            objects = list(bpy.context.scene.objects)
            print(f"DEBUG: Found {len(objects)} objects in scene")
        except Exception as objects_error:
            print(f"DEBUG: Error getting objects: {objects_error}")
            raise
        
        # Process mesh data
        print("DEBUG: Processing mesh data...")
        try:
            vertices, vertex_normals, faces, face_normals, uv_coords, materials = process_mesh(objects)
            print(f"DEBUG: Processed mesh data - vertices: {len(vertices)}, faces: {len(faces)}")
            print(f"DEBUG: UV coordinates: {len(uv_coords)}, materials: {len(materials)}")
        except Exception as mesh_error:
            print(f"DEBUG: Error processing mesh: {mesh_error}")
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            raise
        
        # Process armature data with vertex count for skin matrix
        print("DEBUG: Processing armature data...")
        try:
            num_vertices = len(vertices) if len(vertices) > 0 else 0
            joints, tails, skin, no_skin, parents, names, matrix_local = process_armature(armature, num_vertices)
            print(f"DEBUG: Processed armature data - joints: {len(joints)}")
        except Exception as armature_error:
            print(f"DEBUG: Error processing armature: {armature_error}")
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            raise
        
        # Save processed data
        print("DEBUG: Saving processed data...")
        try:
            save_raw_data(output_dir, vertices, vertex_normals, faces, face_normals,
                         joints, tails, skin, no_skin, parents, names, matrix_local,
                         uv_coords, materials)
            print("DEBUG: Data saved successfully")
        except Exception as save_error:
            print(f"DEBUG: Error saving data: {save_error}")
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            raise
        
        # Save texture files alongside NPZ data - CRITICAL for Step 1 texture preservation
        print("DEBUG: Saving texture files...")
        try:
            model_name = os.path.splitext(os.path.basename(model_path))[0]
            saved_textures = save_texture_files(output_dir, model_name)
            print(f"DEBUG: Successfully saved {len(saved_textures)} texture files: {saved_textures}")
            
            # Update material metadata with saved texture filepaths for Blender Native Flow
            for material in materials:
                for texture in material.get('textures', []):
                    texture_name = texture['name']
                    # Find saved texture file with matching name
                    for saved_texture in saved_textures:
                        if texture_name == saved_texture.get('original_name'):
                            texture['filepath'] = saved_texture.get('relative_path', '')
                            print(f"DEBUG: Updated texture filepath: {texture_name} -> {texture['filepath']}")
                            break
                    else:
                        print(f"WARNING: No saved texture file found for {texture_name}")
                        
        except Exception as texture_error:
            print(f"DEBUG: Error in texture handling: {texture_error}")
            # Don't raise - texture handling is optional
            
        # Re-save NPZ data with updated material metadata containing texture filepaths
        print("DEBUG: Re-saving NPZ data with updated texture filepaths...")
        try:
            save_raw_data(output_dir, vertices, vertex_normals, faces, face_normals,
                         joints, tails, skin, no_skin, parents, names, matrix_local,
                         uv_coords, materials)
            print("DEBUG: NPZ data re-saved with updated texture metadata")
        except Exception as resave_error:
            print(f"DEBUG: Error re-saving NPZ data: {resave_error}")
        
        # Log completion
        if log_path and log_name:
            new_entry("Mesh extraction completed successfully")
            end_log()
        
        print("DEBUG: extract_builtin completed successfully")
        
        # Check if running in Gradio environment (subprocess)
        import sys
        is_gradio_subprocess = any('gradio' in str(arg).lower() for arg in sys.argv) or 'GRADIO' in os.environ
        
        if is_gradio_subprocess:
            # In Gradio environment, do gentle cleanup without force exit
            print("DEBUG: Running in Gradio environment, performing gentle cleanup")
            try:
                clean_bpy()
                import gc
                gc.collect()
                print("DEBUG: Gentle cleanup completed, returning normally")
            except Exception as cleanup_error:
                print(f"DEBUG: Cleanup warning: {cleanup_error}")
            return True
        else:
            # Standalone execution - use force exit to prevent segmentation fault
            try:
                # Clear all Blender data immediately
                clean_bpy()
                
                # Force multiple garbage collection cycles
                import gc
                for _ in range(5):
                    gc.collect()
                
                # Clear all atexit handlers to prevent Blender's problematic cleanup
                import atexit
                atexit._clear()
                
                # Use the most direct exit method available - no delayed handlers
                print("DEBUG: Forcing immediate exit to prevent segmentation fault")
                force_safe_exit(0)
                
            except Exception as cleanup_error:
                print(f"DEBUG: Cleanup warning: {cleanup_error}")
                force_safe_exit(0)
        
        return True
        
    except Exception as e:
        error_msg = f"Error in extract_builtin: {str(e)}"
        print(f"DEBUG: {error_msg}")
        if log_path and log_name:
            add_error(error_msg)
            end_log()
        raise


def main():
    """Command line interface for mesh extraction."""
    print("DEBUG: Starting main() function")
    parser = argparse.ArgumentParser(description='Extract mesh data from 3D models')
    parser.add_argument('--config', required=True, help='Path to config file')
    parser.add_argument('--model_path', required=True, help='Path to 3D model file')
    parser.add_argument('--output_dir', required=True, help='Output directory')
    parser.add_argument('--log_path', help='Log file path')
    parser.add_argument('--log_name', help='Log name')
    
    args = parser.parse_args()
    print(f"DEBUG: Parsed arguments - config: {args.config}, model_path: {args.model_path}, output_dir: {args.output_dir}")
    
    # Load configuration
    try:
        print(f"DEBUG: Loading config from {args.config}")
        with open(args.config, 'r') as f:
            config_dict = yaml.safe_load(f)
        print(f"DEBUG: Config loaded successfully: {list(config_dict.keys()) if config_dict else 'None'}")
    except Exception as e:
        print(f"Error loading config: {e}")
        print(f"DEBUG: Config error traceback: {traceback.format_exc()}")
        force_safe_exit(1)
    
    # Run extraction
    try:
        result = extract_builtin(
            config_dict=config_dict,
            model_path=args.model_path,
            output_dir=args.output_dir,
            log_path=args.log_path,
            log_name=args.log_name
        )
        print("Extraction completed successfully")
        
        # Check if running in Gradio environment
        import sys
        is_gradio_subprocess = any('gradio' in str(arg).lower() for arg in sys.argv) or 'GRADIO' in os.environ
        
        if is_gradio_subprocess:
            # In Gradio, return normally
            return result
        else:
            # Standalone execution, use force exit
            force_safe_exit(0)
            
    except Exception as e:
        print(f"Extraction failed: {e}")
        import sys
        is_gradio_subprocess = any('gradio' in str(arg).lower() for arg in sys.argv) or 'GRADIO' in os.environ
        
        if is_gradio_subprocess:
            raise e
        else:
            force_safe_exit(1)


def force_safe_exit(exit_code=0):
    """Force a safe exit from Blender to prevent segmentation faults."""
    print(f"DEBUG: force_safe_exit called with code {exit_code}")
    
    try:
        # Final cleanup attempt
        print("DEBUG: Performing final cleanup")
        clean_bpy()
        
        # Multiple garbage collection cycles
        import gc
        for i in range(5):
            print(f"DEBUG: Garbage collection cycle {i+1}")
            gc.collect()
        
        # Clear all possible atexit handlers
        import atexit
        atexit._clear()
        print("DEBUG: Cleared atexit handlers")
        
        # Flush all output buffers
        import sys
        sys.stdout.flush()
        sys.stderr.flush()
        print("DEBUG: Flushed output buffers")
        
        # Force immediate termination using the most direct method
        print(f"DEBUG: Forcing exit with code {exit_code}")
        os._exit(exit_code)
        
    except Exception as e:
        print(f"DEBUG: Exception in force_safe_exit: {e}")
        # If cleanup fails, still try to exit
        try:
            os._exit(exit_code)
        except:
            # Absolute last resort
            import signal
            import time
            time.sleep(0.1)  # Small delay
            os.kill(os.getpid(), signal.SIGKILL)


def get_files(
    data_name: str,
    input_dataset_dir: str,
    output_dataset_dir: str,
    inputs: Union[str, None]=None,
    require_suffix: list[str]=['obj','fbx','FBX','dae','glb','gltf','vrm'],
    force_override: bool=False,
    warning: bool=True,
) -> list[Tuple[str, str]]:
    """
    Get list of files to process for mesh extraction.
    
    Args:
        data_name: Name of data file (e.g., 'raw_data.npz')
        input_dataset_dir: Input directory to scan
        output_dataset_dir: Output directory base
        inputs: Comma-separated list of input files
        require_suffix: List of required file suffixes
        force_override: Whether to override existing files
        warning: Whether to show warnings
    
    Returns:
        List of (input_file_path, output_directory) tuples
    """
    files = []  # (input_file, output_dir)
    print(f"DEBUG: get_files START: inputs='{inputs}', input_dataset_dir='{input_dataset_dir}', output_dataset_dir='{output_dataset_dir}', force_override={force_override}, require_suffix={require_suffix}, data_name='{data_name}'")

    if inputs is not None:
        vis = {}
        inputs_list = inputs.split(',')
        print(f"DEBUG: get_files: Processing inputs_list: {inputs_list}")
        for file_path_in_list in inputs_list:
            file_path_in_list = file_path_in_list.strip()
            if not file_path_in_list: 
                continue

            print(f"DEBUG: get_files: Current file_path_in_list: '{file_path_in_list}'")
            
            if not os.path.exists(file_path_in_list):
                print(f"DEBUG: get_files: Skipped (input file does not exist): {file_path_in_list}")
                if warning and log_functions_imported:
                    add_warning(f"input file {file_path_in_list} does not exist, skip")
                continue

            base_name_with_suffix = os.path.basename(file_path_in_list)
            name_no_suffix = '.'.join(base_name_with_suffix.split('.')[:-1])
            if not name_no_suffix and base_name_with_suffix.startswith('.'):
                name_no_suffix = base_name_with_suffix
            elif not name_no_suffix:
                name_no_suffix = base_name_with_suffix
            
            print(f"DEBUG: get_files: name_no_suffix: '{name_no_suffix}'")

            output_dir_for_file = os.path.join(output_dataset_dir, name_no_suffix)
            print(f"DEBUG: get_files: output_dir_for_file: '{output_dir_for_file}'")
            output_npz_path = os.path.join(output_dir_for_file, data_name)
            print(f"DEBUG: get_files: output_npz_path: '{output_npz_path}'")

            if not force_override and os.path.exists(output_npz_path):
                print(f"DEBUG: get_files: Skipped (NPZ exists and not force_override): {output_npz_path}")
                if warning and log_functions_imported:
                    add_warning(f"{output_npz_path} already exists, skip")
                continue

            valid_suffix = False
            actual_suffix = file_path_in_list.split('.')[-1] if '.' in base_name_with_suffix else ''
            print(f"DEBUG: get_files: Checking suffix for '{file_path_in_list}', actual_suffix='{actual_suffix.lower()}' against {require_suffix}")
            for suffix_item in require_suffix:
                if file_path_in_list.lower().endswith(f".{suffix_item.lower()}"):
                    valid_suffix = True
                    print(f"DEBUG: get_files: Valid suffix found (.{suffix_item}) for {file_path_in_list}")
                    break
            
            if not valid_suffix:
                print(f"DEBUG: get_files: Skipped (invalid suffix): {file_path_in_list}. Expected one of {require_suffix}, got '{actual_suffix}'")
                if warning and log_functions_imported:
                    add_warning(f"input file {file_path_in_list} does not have required suffix {require_suffix}, skip")
                continue

            if vis.get(file_path_in_list) is None:
                print(f"DEBUG: get_files: Adding to files list: ('{file_path_in_list}', '{output_dir_for_file}')")
                files.append((file_path_in_list, output_dir_for_file))
                vis[file_path_in_list] = True
            else:
                print(f"DEBUG: get_files: Skipped (already visited): {file_path_in_list}")
    else:
        # Directory scanning logic
        print(f"DEBUG: get_files: No explicit inputs provided, scanning input_dataset_dir: {input_dataset_dir}")
        if not os.path.isdir(input_dataset_dir):
            print(f"DEBUG: get_files: input_dataset_dir '{input_dataset_dir}' is not a valid directory. Skipping scan.")
            if warning and log_functions_imported:
                add_warning(f"input_dataset_dir {input_dataset_dir} is not a directory, skip scan.")
            return []

        vis = {}
        for root, _, files_in_dir_list in os.walk(input_dataset_dir):
            for file_in_dir_item in files_in_dir_list:
                file_path_in_list = os.path.join(root, file_in_dir_item)
                print(f"DEBUG: get_files (dir_scan): Checking file: '{file_path_in_list}'")

                valid_suffix = False
                actual_suffix = file_path_in_list.split('.')[-1].lower() if '.' in file_path_in_list else ''
                for suffix_item in require_suffix:
                    if file_path_in_list.lower().endswith(f".{suffix_item.lower()}"):
                        valid_suffix = True
                        break
                
                if not valid_suffix:
                    print(f"DEBUG: get_files (dir_scan): Skipped (invalid suffix): {file_path_in_list}. Expected one of {require_suffix}, got '{actual_suffix}'")
                    continue
                
                print(f"DEBUG: get_files (dir_scan): Valid suffix for {file_path_in_list}")
                relative_path_from_input_dir = os.path.relpath(file_path_in_list, input_dataset_dir)
                name_no_suffix_with_subdir = '.'.join(relative_path_from_input_dir.split('.')[:-1])
                if not name_no_suffix_with_subdir and relative_path_from_input_dir.startswith('.'):
                    name_no_suffix_with_subdir = relative_path_from_input_dir
                elif not name_no_suffix_with_subdir:
                    name_no_suffix_with_subdir = relative_path_from_input_dir

                output_dir_for_file = os.path.join(output_dataset_dir, name_no_suffix_with_subdir)
                output_npz_path = os.path.join(output_dir_for_file, data_name)
                print(f"DEBUG: get_files (dir_scan): output_dir_for_file: '{output_dir_for_file}', output_npz_path: '{output_npz_path}'")

                if not force_override and os.path.exists(output_npz_path):
                    print(f"DEBUG: get_files (dir_scan): Skipped (NPZ exists and not force_override): {output_npz_path}")
                    if warning and log_functions_imported:
                        add_warning(f"{output_npz_path} already exists, skip")
                    continue
                
                if vis.get(file_path_in_list) is None:
                    print(f"DEBUG: get_files (dir_scan): Adding to files list: ('{file_path_in_list}', '{output_dir_for_file}')")
                    files.append((file_path_in_list, output_dir_for_file))
                    vis[file_path_in_list] = True
                else:
                    print(f"DEBUG: get_files (dir_scan): Skipped (already visited): {file_path_in_list}")

    print(f"DEBUG: get_files END: returning files: {files}")
    return files


# Additional functions needed by merge.py
def get_arranged_bones(armature):
    """Get bones arranged in depth-first search order."""
    matrix_world = armature.matrix_world
    arranged_bones = []
    root = armature.pose.bones[0]
    while root.parent is not None:
        root = root.parent
    Q = [root]
    rot = np.array(matrix_world)[:3, :3]
    
    # dfs and sort
    while len(Q) != 0:
        b = Q.pop(0)
        arranged_bones.append(b)
        children = []
        for cb in b.children:
            head = rot @ np.array(b.head)
            children.append((cb, head[0], head[1], head[2]))
        children = sorted(children, key=lambda x: (x[3], x[1], x[2]))
        _c = [x[0] for x in children]
        Q = _c + Q
    return arranged_bones

def process_mesh_for_merge():
    """Process mesh data from Blender scene."""
    meshes = []
    for v in bpy.data.objects:
        if v.type == 'MESH':
            meshes.append(v)
    
    _dict_mesh = {}
    vertices_list = []
    faces_list = []
    
    for obj in meshes:
        m = np.array(obj.matrix_world)
        matrix_world_rot = m[:3, :3]
        matrix_world_bias = m[:3, 3]
        rot = matrix_world_rot
        total_vertices = len(obj.data.vertices)
        vertex = np.zeros((4, total_vertices))
        vertex_normal = np.zeros((total_vertices, 3))
        obj_verts = obj.data.vertices
        faces = []
        normals = []
        
        for v in obj_verts:
            vertex_normal[v.index] = rot @ np.array(v.normal)
            vv = rot @ v.co
            vv = np.array(vv) + matrix_world_bias
            vertex[0:3, v.index] = vv
            vertex[3][v.index] = 1
        
        for polygon in obj.data.polygons:
            edges = polygon.edge_keys
            nodes = []
            adj = {}
            for edge in edges:
                if adj.get(edge[0]) is None:
                    adj[edge[0]] = []
                adj[edge[0]].append(edge[1])
                if adj.get(edge[1]) is None:
                    adj[edge[1]] = []
                adj[edge[1]].append(edge[0])
                nodes.append(edge[0])
                nodes.append(edge[1])
            normal = polygon.normal
            nodes = list(set(sorted(nodes)))
            first = nodes[0]
            loop = []
            now = first
            vis = {}
            while True:
                loop.append(now)
                vis[now] = True
                if vis.get(adj[now][0]) is None:
                    now = adj[now][0]
                elif vis.get(adj[now][1]) is None:
                    now = adj[now][1]
                else:
                    break
            for (second, third) in zip(loop[1:], loop[2:]):
                faces.append((first + 1, second + 1, third + 1))
                normals.append(rot @ normal)
        
        vertices_list.append(vertex[:3].T)
        faces_list.append(np.array(faces))
    
    if vertices_list:
        return vertices_list[0], faces_list[0]
    return np.array([]), np.array([])

def process_armature_for_merge(armature, arranged_bones):
    """Process armature data from Blender."""
    from typing import Tuple
    
    matrix_world = armature.matrix_world
    index = {}

    for (id, pbone) in enumerate(arranged_bones):
        index[pbone.name] = id
    
    root = armature.pose.bones[0]
    while root.parent is not None:
        root = root.parent
    m = np.array(matrix_world.to_4x4())
    scale_inv = np.linalg.inv(np.diag(matrix_world.to_scale()))
    rot = m[:3, :3]
    bias = m[:3, 3]
    
    s = []
    bpy.ops.object.editmode_toggle()
    edit_bones = armature.data.edit_bones
    
    J = len(arranged_bones)
    joints = np.zeros((J, 3), dtype=np.float32)
    tails = np.zeros((J, 3), dtype=np.float32)
    parents = []
    name_to_id = {}
    names = []
    matrix_local_stack = np.zeros((J, 4, 4), dtype=np.float32)
    for (id, pbone) in enumerate(arranged_bones):
        name = pbone.name
        names.append(name)
        matrix_local = np.array(pbone.bone.matrix_local)
        use_inherit_rotation = pbone.bone.use_inherit_rotation
        if use_inherit_rotation == False:
            print(f"WARNING: use_inherit_rotation of bone {name} is False !")
        head = rot @ matrix_local[0:3, 3] + bias
        s.append(head)
        edit_bone = edit_bones.get(name)
        tail = rot @ np.array(edit_bone.tail) + bias
        
        name_to_id[name] = id
        joints[id] = head
        tails[id] = tail
        parents.append(None if pbone.parent not in arranged_bones else name_to_id[pbone.parent.name])
        # remove scale part
        matrix_local[:, 3:4] = m @ matrix_local[:, 3:4]
        matrix_local[:3, :3] = scale_inv @ matrix_local[:3, :3]
        matrix_local_stack[id] = matrix_local
    bpy.ops.object.editmode_toggle()
    
    return joints, tails, parents, names, matrix_local_stack


def save_texture_files(output_dir, model_name):
    """Save texture files alongside NPZ data."""
    texture_dir = os.path.join(output_dir, "textures")
    os.makedirs(texture_dir, exist_ok=True)
    
    saved_textures = []
    
    try:
        # Save all images from Blender
        for image in bpy.data.images:
            if image.name and image.filepath:
                # Get original file extension
                original_path = image.filepath
                if original_path.startswith("//"):
                    original_path = bpy.path.abspath(original_path)
                
                if os.path.exists(original_path):
                    # Create safe filename
                    safe_name = "".join(c for c in image.name if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
                    if not safe_name:
                        safe_name = f"texture_{len(saved_textures)}"
                    
                    # Preserve original extension
                    original_ext = os.path.splitext(original_path)[1]
                    if not safe_name.endswith(original_ext):
                        safe_name += original_ext
                    
                    target_path = os.path.join(texture_dir, safe_name)
                    
                    # Copy texture file
                    try:
                        shutil.copy2(original_path, target_path)
                        saved_textures.append({
                            'original_name': image.name,
                            'original_path': original_path,
                            'saved_path': target_path,
                            'relative_path': os.path.relpath(target_path, output_dir)
                        })
                        print(f"DEBUG: Saved texture: {image.name} -> {target_path}")
                    except Exception as e:
                        print(f"DEBUG: Failed to copy texture {image.name}: {e}")
            elif image.name and image.packed_file:
                # Handle packed images
                safe_name = "".join(c for c in image.name if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
                if not safe_name:
                    safe_name = f"packed_texture_{len(saved_textures)}"
                
                # Determine format from image data or use PNG as default
                if not safe_name.lower().endswith(('.png', '.jpg', '.jpeg', '.tga', '.bmp')):
                    safe_name += '.png'
                
                target_path = os.path.join(texture_dir, safe_name)
                
                try:
                    # Save packed image
                    image.save_render(filepath=target_path)
                    saved_textures.append({
                        'original_name': image.name,
                        'original_path': 'packed',
                        'saved_path': target_path,
                        'relative_path': os.path.relpath(target_path, output_dir)
                    })
                    print(f"DEBUG: Saved packed texture: {image.name} -> {target_path}")
                except Exception as e:
                    print(f"DEBUG: Failed to save packed texture {image.name}: {e}")
    
    except Exception as e:
        print(f"DEBUG: Error in save_texture_files: {e}")
    
    # Save texture manifest
    if saved_textures:
        manifest_path = os.path.join(output_dir, "texture_manifest.yaml")
        try:
            with open(manifest_path, 'w') as f:
                yaml.dump({
                    'model_name': model_name,
                    'texture_count': len(saved_textures),
                    'textures': saved_textures
                }, f, default_flow_style=False)
            print(f"DEBUG: Saved texture manifest: {manifest_path}")
        except Exception as e:
            print(f"DEBUG: Failed to save texture manifest: {e}")
    
    return saved_textures

# Call main function when script is executed directly
if __name__ == "__main__":
    main()
