import sys # Ensure sys is imported
import os # Ensure os is imported
import logging # Ensure logging is imported
import bpy, os # bpy, os should be at the top
print(f"Attempting to import bpy. Version: {bpy.app.version_string if bpy and hasattr(bpy, 'app') else 'bpy not fully available'}")
from collections import defaultdict
from tqdm import tqdm
import numpy as np # numpy should be imported before ndarray
from numpy import ndarray
from typing import Dict, Tuple, List, Optional, Union
import trimesh
import fast_simplification
from scipy.spatial import KDTree
import gc
import argparse
import yaml
from box import Box
import datetime # ADDED

# Fix relative imports for standalone execution
import sys
import os

# Ensure /app is in the Python path
app_dir = "/app"
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

# Also ensure src directory is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)  # src directory
root_dir = os.path.dirname(parent_dir)     # app directory

for path in [root_dir, parent_dir, current_dir]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Try to import required modules with comprehensive fallback
log_functions_imported = False
raw_data_imported = False

# First, try absolute imports from the app directory structure
try:
    import sys
    import os
    sys.path.insert(0, '/app')
    from src.data.log import new_entry, add_error, add_warning, new_log, end_log
    from src.data.raw_data import RawData
    log_functions_imported = True
    raw_data_imported = True
    print("Successfully imported using absolute paths from /app")
except ImportError as e:
    print(f"Absolute import failed: {e}")
    
    # Try relative imports
    try:
        from .log import new_entry, add_error, add_warning, new_log, end_log
        from .raw_data import RawData
        log_functions_imported = True
        raw_data_imported = True
        print("Successfully imported using relative imports")
    except ImportError as e:
        print(f"Relative import failed: {e}")
        
        # Try direct module imports
        try:
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
        def __init__(self, vertices, vertex_normals, faces, face_normals, joints, tails, skin, no_skin, parents, names, matrix_local):
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
                        path=path,
                        cls='RawData'
                    )

def load(filepath: str):
    old_objs = set(bpy.context.scene.objects)
    
    if not os.path.exists(filepath):
        raise ValueError(f'File {filepath} does not exist !')
    
    try:
        if filepath.endswith(".vrm"):
            # enable vrm addon and load vrm model
            bpy.ops.preferences.addon_enable(module='vrm')
            
            bpy.ops.import_scene.vrm(
                filepath=filepath,
                use_addon_preferences=True,
                extract_textures_into_folder=False,
                make_new_texture_folder=False,
                set_shading_type_to_material_on_import=False,
                set_view_transform_to_standard_on_import=True,
                set_armature_display_to_wire=True,
                set_armature_display_to_show_in_front=True,
                set_armature_bone_shape_to_default=True,
                disable_bake=True, # customized option for better performance
            )
        elif filepath.endswith(".obj"):
            bpy.ops.wm.obj_import(filepath=filepath)
        elif filepath.endswith(".fbx") or filepath.endswith(".FBX"):
            # end bone is removed using remove_dummy_bone
            bpy.ops.import_scene.fbx(filepath=filepath, ignore_leaf_bones=False, use_image_search=False)
        elif filepath.endswith(".glb") or filepath.endswith(".gltf"):
            bpy.ops.import_scene.gltf(filepath=filepath, import_pack_images=False)
        elif filepath.endswith(".dae"):
            bpy.ops.wm.collada_import(filepath=filepath)
        elif filepath.endswith(".blend"):
            with bpy.data.libraries.load(filepath) as (data_from, data_to):
                data_to.objects = data_from.objects
            for obj in data_to.objects:
                if obj is not None:
                    bpy.context.collection.objects.link(obj)
        else:
            raise ValueError(f"not suported type {filepath}")
    except:
        raise ValueError(f"failed to load {filepath}")

    armature = [x for x in set(bpy.context.scene.objects)-old_objs if x.type=="ARMATURE"]
    if len(armature)==0:
        return None
    if len(armature)>1:
        raise ValueError(f"multiple armatures found")
    armature = armature[0]
    
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='EDIT')
    for bone in bpy.data.armatures[0].edit_bones:
        bone.roll = 0. # change all roll to 0. to prevent weird behaviour

    bpy.ops.object.mode_set(mode='OBJECT')
    armature.select_set(False)
    
    bpy.ops.object.select_all(action='DESELECT')
    return armature

# remove all data in bpy
def clean_bpy():
    print("DEBUG: Entering clean_bpy")
    # Blender 4.2 compatible active object check
    try:
        active_obj = bpy.context.view_layer.objects.active
        if active_obj and active_obj.mode != 'OBJECT':
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except Exception as e:
                print(f"DEBUG: clean_bpy - Error setting mode to OBJECT: {e}")
    except AttributeError:
        # bpy.context.object not available in Blender 4.2
        pass
    try:
        bpy.ops.object.select_all(action='DESELECT')
    except Exception as e:
        print(f"DEBUG: clean_bpy - Error deselecting all objects: {e}")

    print("DEBUG: clean_bpy - Unlinking objects from scene collection.")
    if bpy.context.scene:
        scene_collection = bpy.context.scene.collection
        objects_to_unlink = [obj for obj in scene_collection.objects]
        for obj in objects_to_unlink:
            print(f"DEBUG: clean_bpy - Unlinking {obj.name if hasattr(obj, 'name') else 'Unnamed Object'} from scene collection.")
            try:
                scene_collection.objects.unlink(obj)
                print(f"DEBUG: clean_bpy - Successfully unlinked {obj.name if hasattr(obj, 'name') else 'Unnamed Object'}.")
            except Exception as e:
                print(f"DEBUG: clean_bpy - Error unlinking {obj.name if hasattr(obj, 'name') else 'Unnamed Object'}: {e}")
    else:
        print("DEBUG: clean_bpy - bpy.context.scene is None, skipping unlinking.")

    print("DEBUG: clean_bpy - Removing objects with no users from bpy.data.objects.")
    objects_to_remove_data = [obj for obj in bpy.data.objects if obj.users == 0 and not obj.use_fake_user]
    for obj in objects_to_remove_data:
        obj_name = obj.name if hasattr(obj, 'name') else 'Unnamed Object'
        print(f"DEBUG: clean_bpy - Attempting to remove {obj_name} from bpy.data.objects.")
        try:
            bpy.data.objects.remove(obj, do_unlink=True)
            print(f"DEBUG: clean_bpy - Successfully removed {obj_name} from bpy.data.objects.")
        except Exception as e:
            print(f"DEBUG: clean_bpy - Error removing {obj_name} from bpy.data.objects: {e}")

    data_collections_to_clean = {
        'meshes': bpy.data.meshes,
        'armatures': bpy.data.armatures,
        'materials': bpy.data.materials,
        'images': bpy.data.images,
        'actions': bpy.data.actions,
    }
    print("DEBUG: clean_bpy - Cleaning other data types (meshes, armatures, etc.).")
    for block_name, data_collection in data_collections_to_clean.items():
        items_to_remove = [item for item in data_collection if item.users == 0 and not item.use_fake_user]
        print(f"DEBUG: clean_bpy - Found {len(items_to_remove)} items to remove in {block_name}.")
        for item in items_to_remove:
            item_name = item.name if hasattr(item, 'name') else f'Unnamed {block_name[:-1]}'
            print(f"DEBUG: clean_bpy - Attempting to remove {item_name} from {block_name}.")
            try:
                data_collection.remove(item)
                print(f"DEBUG: clean_bpy - Successfully removed {item_name} from {block_name}.")
            except Exception as e:
                print(f"DEBUG: clean_bpy - Error removing {item_name} from {block_name}: {e}")
    print("DEBUG: clean_bpy - Finished cleaning other data types.")

    if hasattr(bpy.ops.outliner, 'orphans_purge'):
        try:
            print("DEBUG: clean_bpy - Attempting bpy.ops.outliner.orphans_purge() (second attempt, after targeted cleanup)")
            bpy.ops.outliner.orphans_purge(do_recursive=True)
            print("DEBUG: clean_bpy - bpy.ops.outliner.orphans_purge() executed.")
        except RuntimeError as e: # Catch RuntimeError specifically for orphans_purge
            print(f"DEBUG: clean_bpy - RuntimeError during orphans_purge (possibly no orphans or context issue): {e}")
        except Exception as e:
            print(f"DEBUG: clean_bpy - Error during orphans_purge: {e}")
    else:
        print("DEBUG: clean_bpy - bpy.ops.outliner.orphans_purge not found.")

    print("DEBUG: clean_bpy - Attempting gc.collect()")
    gc.collect()
    print("DEBUG: clean_bpy - gc.collect() finished, exiting clean_bpy")

def get_arranged_bones(armature):
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

def process_mesh():
    meshes = []
    for v in bpy.data.objects:
        if v.type == 'MESH':
            meshes.append(v)
    
    _dict_mesh = {}
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
            vertex_normal[v.index] = rot @ np.array(v.normal) # be careful !
            vv = rot @ v.co
            vv = np.array(vv) + matrix_world_bias
            vertex[0:3, v.index] = vv
            vertex[3][v.index] = 1 # affine coordinate
        
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
                faces.append((first + 1, second + 1, third + 1)) # the cursed +1
                normals.append(rot @ normal) # and the cursed normal of BLENDER

        correct_faces = []
        for (i, face) in enumerate(faces):
            normal = normals[i]
            v0 = face[0] - 1
            v1 = face[1] - 1
            v2 = face[2] - 1
            v = np.cross(
                vertex[:3, v1] - vertex[:3, v0],
                vertex[:3, v2] - vertex[:3, v0],
            )
            if (v*normal).sum() > 0:
                correct_faces.append(face)
            else:
                correct_faces.append((face[0], face[2], face[1]))
        if len(correct_faces) > 0:
            _dict_mesh[obj.name] = {
                'vertex': vertex,
                'face': correct_faces,
            }
    
    vertex = np.concatenate([_dict_mesh[name]['vertex'] for name in _dict_mesh], axis=1)[:3, :].transpose()
    print(f"DEBUG: process_mesh - Total vertices after concatenation: {vertex.shape[0]}")
    
    total_faces = 0
    now_bias = 0
    for name in _dict_mesh:
        total_faces += len(_dict_mesh[name]['face'])
    faces = np.zeros((total_faces, 3), dtype=np.int64)
    tot = 0
    for name in _dict_mesh:
        f = np.array(_dict_mesh[name]['face'], dtype=np.int64)
        print(f"DEBUG: process_mesh - Processing mesh '{name}': faces shape {f.shape}, now_bias {now_bias}")
        print(f"DEBUG: process_mesh - Face indices range: min={f.min()}, max={f.max()}")
        # Convert from 1-based to 0-based indexing before adding bias
        f_adjusted = f - 1 + now_bias
        print(f"DEBUG: process_mesh - After adjustment: min={f_adjusted.min()}, max={f_adjusted.max()}")
        print(f"DEBUG: process_mesh - Current vertex count: {vertex.shape[0]}")
        if f_adjusted.max() >= vertex.shape[0]:
            print(f"ERROR: Face index {f_adjusted.max()} exceeds vertex count {vertex.shape[0]}")
        faces[tot:tot+f.shape[0]] = f_adjusted
        now_bias += _dict_mesh[name]['vertex'].shape[1]
        tot += f.shape[0]
    
    print(f"DEBUG: process_mesh - Final faces shape: {faces.shape}")
    print(f"DEBUG: process_mesh - Final face indices range: min={faces.min()}, max={faces.max()}")
    return vertex, faces

def process_armature(
    armature,
    arranged_bones,
) -> Tuple[np.ndarray, np.ndarray]:
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
            add_warning(f"use_inherit_rotation of bone {name} is False !")
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

def save_raw_data(
    path: str,
    vertices: ndarray,
    faces: ndarray,
    joints: Union[ndarray, None],
    tails: Union[ndarray, None],
    parents: Union[List[Union[int, None]], None],
    names: Union[List[str], None],
    matrix_local: Union[ndarray, None],
    target_count: int,
):
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
    vertices = np.array(mesh.vertices, dtype=np.float32)
    faces = np.array(mesh.faces, dtype=np.int64)
    if faces.shape[0] > target_count:
        vertices, faces = fast_simplification.simplify(vertices, faces, target_count=target_count)
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
    
    new_vertices = np.array(mesh.vertices, dtype=np.float32)
    new_vertex_normals = np.array(mesh.vertex_normals, dtype=np.float32)
    new_faces = np.array(mesh.faces, dtype=np.int64)
    new_face_normals = np.array(mesh.face_normals, dtype=np.float32)
    if joints is not None:
        new_joints = np.array(joints, dtype=np.float32)
    else:
        new_joints = None
    raw_data = RawData(
        vertices=new_vertices,
        vertex_normals=new_vertex_normals,
        faces=new_faces,
        face_normals=new_face_normals,
        joints=new_joints,
        tails=tails,
        skin=None,
        no_skin=None,
        parents=parents,
        names=names,
        matrix_local=matrix_local,
    )
    raw_data.check()
    raw_data.save(path=path)
    print(f"DEBUG: save_raw_data - np.savez_compressed called for {path}") # ADDED
    sys.stdout.flush() # ADDED

def extract_builtin(
    output_folder: str, # This is where datalist.txt and potentially model-specific subdirs are created
    target_count: int,
    num_runs: int,
    id: int,
    time: str,
    files: list, # List of (input_file_path, output_dir_for_this_file)
    cfg: Box,
) -> list[str]: # Returns list of relative NPZ paths created
    print(f"DEBUG: extract_builtin START - output_folder for datalist: {output_folder}")
    sys.stdout.flush()
    
    # Initialize logging with appropriate parameters
    try:
        log_dir = os.path.join(output_folder, "logs")
        os.makedirs(log_dir, exist_ok=True)
        new_log(log_dir, f"extract_builtin_{time}")
    except Exception as e:
        print(f"WARNING: Could not initialize logging: {e}")
    
    # Safely get log path configurations
    # Use output_folder as a base if specific log paths are not in cfg
    base_log_dir = cfg.get('output_path', output_folder) # Default to overall output if not specified
    log_name_template = cfg.get('log_name', 'extract_log_{name}.txt')

    successfully_created_relative_npz_paths = []
    tot = len(files) // num_runs
    if len(files) % num_runs != 0:
        tot += 1
    
    processed_count = 0
    for idx in range(tot):
        if idx % num_runs != id:
            continue
        
        input_file, output_dir_for_file = files[idx] # output_dir_for_file is specific to this model, e.g., .../output/model_name
        name_no_suffix = os.path.splitext(os.path.basename(input_file))[0]

        # Configure logging for this specific file, placing logs within its own output directory
        current_log_dir = os.path.join(output_dir_for_file, "logs") # Store logs inside the model's specific output dir
        os.makedirs(current_log_dir, exist_ok=True)
        log_file_name = log_name_template.format(name=name_no_suffix)
        log_path_full = os.path.join(current_log_dir, log_file_name)
        
        print(f"DEBUG: extract_builtin - Processing file {idx+1}/{len(files)}: {input_file}")
        print(f"DEBUG: extract_builtin - Output directory for this file: {output_dir_for_file}")
        print(f"DEBUG: extract_builtin - Log file for this item: {log_path_full}")
        sys.stdout.flush()

        # Setup logging to file for this specific item
        file_handler = logging.FileHandler(log_path_full, mode='a')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # Get a logger instance (can be the root logger or a specific one)
        logger = logging.getLogger(__name__ + f".{name_no_suffix}") # Unique logger per file
        if logger.hasHandlers(): # Clear existing handlers for this logger if any (e.g. from previous loop iteration)
            logger.handlers.clear()
        logger.addHandler(file_handler)
        logger.setLevel(logging.INFO) # Or DEBUG for more verbosity

        try:
            logger.info(f"Start processing: {input_file}")
            processed_count += 1
            print(f"DEBUG: extract_builtin - [{id}/{num_runs}] {processed_count}/{tot} {input_file}")
            sys.stdout.flush()

            # output_dir_for_file is like 'dataset_output/model_name'
            # npz_path should be 'dataset_output/model_name/raw_data.npz'
            data_name_from_cfg = cfg.get('components.data_name', 'raw_data.npz') # Default if not in cfg
            npz_path = os.path.join(output_dir_for_file, data_name_from_cfg)
            print(f"DEBUG: extract_builtin - Target NPZ path: {npz_path}")
            sys.stdout.flush()

            os.makedirs(output_dir_for_file, exist_ok=True)

            # Safely get debug_save_blend configuration
            debug_save_blend = cfg.get('debug_save_blend', False) # Default to False
            blend_path = ""
            if debug_save_blend:
                blend_dir = os.path.join(output_dir_for_file, "blender_debug")
                os.makedirs(blend_dir, exist_ok=True)
                blend_path = os.path.join(blend_dir, f"{name_no_suffix}_{time}.blend")
                print(f"DEBUG: extract_builtin - Debug blend file will be saved to: {blend_path}")
                sys.stdout.flush()
            
            # Load and process the 3D model file
            print(f"DEBUG: extract_builtin - Loading 3D model: {input_file}")
            sys.stdout.flush()
            
            try:
                # Clear existing scene first
                clean_bpy()
                
                # Load the model file
                load(input_file)
                
                # Process the mesh to extract vertices and faces
                print(f"DEBUG: extract_builtin - Processing mesh data")
                sys.stdout.flush()
                vertices, faces = process_mesh()
                print(f"DEBUG: extract_builtin - Extracted {len(vertices)} vertices and {len(faces)} faces")
                sys.stdout.flush()
                
                # Find armature and process bones
                armature = None
                arranged_bones = []
                for obj in bpy.context.scene.objects:
                    if obj.type == 'ARMATURE':
                        armature = obj
                        break
                
                if armature:
                    print(f"DEBUG: extract_builtin - Found armature: {armature.name}")
                    sys.stdout.flush()
                    # Get bones in a reasonable order
                    for bone in armature.data.bones:
                        arranged_bones.append(bone)
                    
                    # Process armature to extract bone data
                    joints, tails = process_armature(armature, arranged_bones)
                    
                    # Extract bone hierarchy information
                    parents = []
                    names = []
                    matrix_local = []
                    
                    for bone in arranged_bones:
                        names.append(bone.name)
                        if bone.parent:
                            parents.append(arranged_bones.index(bone.parent))
                        else:
                            parents.append(None)  # Use None instead of -1 for root bone
                        # Use the bone's matrix_local or create identity matrix
                        if hasattr(bone, 'matrix_local'):
                            matrix_local.append(np.array(bone.matrix_local))
                        else:
                            matrix_local.append(np.eye(4))
                    
                    parents = np.array(parents, dtype=object)  # Use object dtype to handle None values
                    matrix_local = np.array(matrix_local)
                    
                    print(f"DEBUG: extract_builtin - Processed {len(names)} bones")
                    sys.stdout.flush()
                else:
                    print(f"WARNING: extract_builtin - No armature found in {input_file}, creating dummy bone data")
                    sys.stdout.flush()
                    # Create minimal dummy bone data
                    joints = np.array([[0, 0, 0]])
                    tails = np.array([[0, 0, 1]])
                    parents = np.array([None], dtype=object)  # Use None for root bone
                    names = ['root']
                    matrix_local = np.array([np.eye(4)])
                
            except Exception as e:
                print(f"ERROR: extract_builtin - Failed to load/process model {input_file}: {e}")
                import traceback
                traceback.print_exc()
                sys.stdout.flush()
                logger.error(f"Failed to load/process model: {e}")
                continue  # Skip to next file
            
            save_raw_data(
                path=npz_path,
                vertices=vertices,
                faces=faces,
                joints=joints,
                tails=tails,
                parents=parents,
                names=names,
                matrix_local=matrix_local,
                target_count=target_count
            )
            print(f"DEBUG: extract_builtin - save_raw_data call completed for {npz_path}")

            # === ADDED: File existence check and detailed logging ===
            npz_file_valid_and_created = False # ADDED Flag
            if os.path.exists(npz_path):
                print(f"SUCCESS: extract_builtin - Verified NPZ file exists after save: {npz_path}")
                sys.stdout.flush()
                file_size = os.path.getsize(npz_path)
                print(f"DEBUG: extract_builtin - NPZ file size: {file_size} bytes")
                sys.stdout.flush()
                if file_size == 0:
                    print(f"WARNING: extract_builtin - NPZ file was created but is EMPTY: {npz_path}")
                    sys.stdout.flush()
                else:
                    # === ADDED: Self-load verification ===
                    try:
                        print(f"DEBUG: extract_builtin - Attempting to self-load NPZ for verification: {npz_path}")
                        sys.stdout.flush()
                        loaded_test_data = np.load(npz_path, allow_pickle=True)
                        print(f"SUCCESS: extract_builtin - Successfully self-loaded NPZ. Keys: {list(loaded_test_data.keys())}")
                        sys.stdout.flush()
                        loaded_test_data.close()
                        npz_file_valid_and_created = True # Set flag if load successful
                    except Exception as e_load:
                        print(f"CRITICAL_ERROR: extract_builtin - Failed to self-load NPZ from {npz_path}: {e_load}")
                        sys.stdout.flush()
                    # === END ADDED: Self-load verification ===
            else:
                print(f"CRITICAL_ERROR: extract_builtin - NPZ file NOT FOUND after save_raw_data call: {npz_path}")
                sys.stdout.flush() # ADDED
            # === END ADDED ===

            base_name_with_suffix = os.path.basename(input_file)
            name_no_suffix = '.'.join(base_name_with_suffix.split('.')[:-1])
            if not name_no_suffix and base_name_with_suffix.startswith('.'): name_no_suffix = base_name_with_suffix
            elif not name_no_suffix: name_no_suffix = base_name_with_suffix
            
            # Use safe config access for data_name
            data_name = cfg.get('components', {}).get('data_name', 'raw_data.npz')
            relative_npz_path = os.path.join(name_no_suffix, data_name)
            
            if npz_file_valid_and_created: # MODIFIED to use the flag
                successfully_created_relative_npz_paths.append(relative_npz_path)
                print(f"DEBUG: extract_builtin - Successfully processed, verified, and will list: {relative_npz_path}")
                sys.stdout.flush() # ADDED
            else:
                print(f"Warning: extract_builtin - NPZ file {npz_path} was NOT valid or not found; NOT adding to list for {input_file}.")
                sys.stdout.flush() # ADDED

        except Exception as e: 
            print(f"ERROR: extract_builtin - Failed to process {input_file} (path: {npz_path}): {e}")
            import traceback
            traceback.print_exc()
        finally: 
            print(f"DEBUG: extract_builtin loop - In finally block for {input_file}. Calling clean_bpy().") 
            # clean_bpy() # TEMPORARILY COMMENTED OUT FOR DEBUGGING
            print("DEBUG: extract_builtin loop - clean_bpy() was TEMPORARILY COMMENTED OUT.")
        tot += 1

    end_log()
    print(f"{tot} models processed")
    print(f"DEBUG: extract_builtin END - Total models attempted in this run: {tot}") # MODIFIED for clarity
    print(f"DEBUG: extract_builtin END - Returning successfully_created_relative_npz_paths: {successfully_created_relative_npz_paths}") # MODIFIED
    sys.stdout.flush() # ADDED
    return successfully_created_relative_npz_paths

def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

def nullable_string(val):
    if not val:
        return None
    return val

def get_files(
    data_name: str,
    input_dataset_dir: str,
    output_dataset_dir: str,
    inputs: Union[str, None]=None,
    require_suffix: list[str]=['obj','fbx','FBX','dae','glb','gltf','vrm'],
    force_override: bool=False,
    warning: bool=True,
) -> list[Tuple[str, str]]:
    files = [] # (input_file, output_dir)
    print(f"DEBUG: get_files START: inputs='{inputs}', input_dataset_dir='{input_dataset_dir}', output_dataset_dir='{output_dataset_dir}', force_override={force_override}, require_suffix={require_suffix}, data_name='{data_name}'") # MODIFIED

    if inputs is not None:
        vis = {}
        inputs_list = inputs.split(',')
        print(f"DEBUG: get_files: Processing inputs_list: {inputs_list}")
        for file_path_in_list in inputs_list:
            file_path_in_list = file_path_in_list.strip() # Add strip
            if not file_path_in_list: continue # Skip empty paths

            print(f"DEBUG: get_files: Current file_path_in_list: '{file_path_in_list}'")
            
            if not os.path.exists(file_path_in_list):
                print(f"DEBUG: get_files: Skipped (input file does not exist): {file_path_in_list}")
                if warning: add_warning(f"input file {file_path_in_list} does not exist, skip")
                continue

            base_name_with_suffix = os.path.basename(file_path_in_list)
            name_no_suffix = '.'.join(base_name_with_suffix.split('.')[:-1])
            if not name_no_suffix and base_name_with_suffix.startswith('.'): # Handle hidden files like ".bashrc"
                name_no_suffix = base_name_with_suffix
            elif not name_no_suffix: # Handle files with no extension "file"
                 name_no_suffix = base_name_with_suffix
            print(f"DEBUG: get_files: name_no_suffix: '{name_no_suffix}'")

            output_dir_for_file = os.path.join(output_dataset_dir, name_no_suffix)
            print(f"DEBUG: get_files: output_dir_for_file: '{output_dir_for_file}'")
            output_npz_path = os.path.join(output_dir_for_file, data_name)
            print(f"DEBUG: get_files: output_npz_path: '{output_npz_path}'")

            if not force_override and os.path.exists(output_npz_path):
                print(f"DEBUG: get_files: Skipped (NPZ exists and not force_override): {output_npz_path}")
                if warning:
                    add_warning(f"{output_npz_path} already exists, skip")
                continue
            else:
                if force_override:
                    print(f"DEBUG: get_files: force_override is True. Will process {file_path_in_list} even if NPZ exists.")
                elif not os.path.exists(output_npz_path):
                    print(f"DEBUG: get_files: NPZ does not exist. Will process {file_path_in_list}.")


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
                if warning:
                    add_warning(f"input file {file_path_in_list} does not have required suffix {require_suffix}, skip")
                continue

            if vis.get(file_path_in_list) is None:
                print(f"DEBUG: get_files: Adding to files list: ('{file_path_in_list}', '{output_dir_for_file}')")
                files.append((file_path_in_list, output_dir_for_file))
                vis[file_path_in_list] = True
            else:
                print(f"DEBUG: get_files: Skipped (already visited): {file_path_in_list}")
    else: # input_dataset_dir scan logic
        print(f"DEBUG: get_files: No explicit inputs ('--input') provided, scanning input_dataset_dir: {input_dataset_dir}")
        if not os.path.isdir(input_dataset_dir):
            print(f"DEBUG: get_files: input_dataset_dir '{input_dataset_dir}' is not a valid directory. Skipping scan.")
            if warning: add_warning(f"input_dataset_dir {input_dataset_dir} is not a directory, skip scan.")
            return [] # Return empty if dir doesn't exist

        vis = {} # Initialize vis here for directory scan
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
                # Construct output_dir_for_file based on relative structure from input_dataset_dir
                relative_path_from_input_dir = os.path.relpath(file_path_in_list, input_dataset_dir) # e.g. "subdir/model.glb"
                name_no_suffix_with_subdir = '.'.join(relative_path_from_input_dir.split('.')[:-1]) # e.g. "subdir/model"
                if not name_no_suffix_with_subdir and relative_path_from_input_dir.startswith('.'):
                     name_no_suffix_with_subdir = relative_path_from_input_dir
                elif not name_no_suffix_with_subdir: # No extension
                     name_no_suffix_with_subdir = relative_path_from_input_dir


                output_dir_for_file = os.path.join(output_dataset_dir, name_no_suffix_with_subdir)
                output_npz_path = os.path.join(output_dir_for_file, data_name)
                print(f"DEBUG: get_files (dir_scan): output_dir_for_file: '{output_dir_for_file}', output_npz_path: '{output_npz_path}'")

                if not force_override and os.path.exists(output_npz_path):
                    print(f"DEBUG: get_files (dir_scan): Skipped (NPZ exists and not force_override): {output_npz_path}")
                    if warning: add_warning(f"{output_npz_path} already exists, skip")
                    continue
                
                if vis.get(file_path_in_list) is None:
                    print(f"DEBUG: get_files (dir_scan): Adding to files list: ('{file_path_in_list}', '{output_dir_for_file}')")
                    files.append((file_path_in_list, output_dir_for_file))
                    vis[file_path_in_list] = True
                else:
                    print(f"DEBUG: get_files (dir_scan): Skipped (already visited): {file_path_in_list}")

    print(f"DEBUG: get_files END: returning files: {files}")
    return files

def parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cfg_data', type=str, default='quick_inference.yaml')
    parser.add_argument('--cfg_task', type=str, default='quick_inference_skeleton_articulationxl_ar_256.yaml')
    parser.add_argument('--require_suffix', type=str, default='obj,fbx,FBX,dae,glb,gltf,vrm')
    parser.add_argument('--force_override', type=str2bool, default=False) # Use str2bool
    parser.add_argument('--num_runs', type=int, default=1)
    parser.add_argument('--faces_target_count', type=int, default=50000)
    parser.add_argument('--id', type=int, default=0)
    parser.add_argument('--time', type=str, default='NO_TIME_PROVIDED')
    parser.add_argument('--input', type=nullable_string, default=None) # For single or comma-separated files
    parser.add_argument('--input_dir', type=nullable_string, default=None) # For directory scanning (legacy or alternative)
    parser.add_argument('--output_dir', type=nullable_string, default=None) # Overrides cfg.output_dataset_dir
    args = parser.parse_args()

    print(f"DEBUG: Main - Parsed args: {args}")

    cfg_data_path = args.cfg_data
    if not os.path.isabs(cfg_data_path) and not cfg_data_path.startswith(('configs/', './configs/')):
        cfg_data_path = os.path.join('configs/data', cfg_data_path)
    print(f"DEBUG: Main - Loading cfg_data from: {os.path.abspath(cfg_data_path)}")
    cfg = Box(yaml.load(open(cfg_data_path, 'r', encoding='utf-8'), Loader=yaml.FullLoader))

    cfg_task_path = args.cfg_task
    if not os.path.isabs(cfg_task_path) and not cfg_task_path.startswith(('configs/', './configs/')):
        cfg_task_path = os.path.join('configs/task', cfg_task_path)
    print(f"DEBUG: Main - Loading cfg_task from: {os.path.abspath(cfg_task_path)}")
    cfg_task_content = Box(yaml.load(open(cfg_task_path, 'r', encoding='utf-8'), Loader=yaml.FullLoader))
    cfg.merge_update(cfg_task_content)
    print("DEBUG: Main - After merging task config into main cfg.")

    if args.output_dir:
        print(f"DEBUG: Main - Overriding cfg.output_dataset_dir with args.output_dir: {args.output_dir}")
        cfg.output_dataset_dir = args.output_dir
    elif not hasattr(cfg, 'output_dataset_dir') or not cfg.output_dataset_dir:
        cfg.output_dataset_dir = "./dataset_inference_clean" 
        print(f"Warning: Main - cfg.output_dataset_dir not set by args or config, using default: {cfg.output_dataset_dir}")
    
    print(f"DEBUG: Main - Final cfg.output_dataset_dir: {cfg.output_dataset_dir}")
    print(f"DEBUG: Main - Final cfg.input_dataset_dir: {cfg.get('input_dataset_dir', 'Not Set')}") # Use .get for safety
    print(f"DEBUG: Main - Final cfg.components.data_name: {cfg.get('components', {}).get('data_name', 'Not Set')}") # Use .get for safety

    if 'input_dataset_dir' not in cfg and args.input is None: # Only default if no --input is given
        cfg.input_dataset_dir = './dataset_inference' 
        print(f"Warning: Main - cfg.input_dataset_dir not set and no --input, using default: {cfg.input_dataset_dir}")
    elif 'input_dataset_dir' not in cfg: # If --input is given, this might not be strictly needed by get_files
        cfg.input_dataset_dir = None # Or some other indicator that it's not to be used for scanning

    if 'components' not in cfg or 'data_name' not in cfg.components:
        if 'components' not in cfg: cfg.components = Box()
        cfg.components.data_name = 'raw_data.npz'
        print(f"Warning: Main - cfg.components.data_name not set, using default: {cfg.components.data_name}")
    
    print(f"DEBUG: Main - Calling get_files with force_override={args.force_override} (type: {type(args.force_override)})")
    files_list = get_files(
        data_name=cfg.components.data_name,
        input_dataset_dir=cfg.input_dataset_dir, 
        output_dataset_dir=cfg.output_dataset_dir,
        inputs=args.input,
        require_suffix=args.require_suffix.split(','),
        force_override=args.force_override, 
        warning=True
    )
    print(f"DEBUG: Main - After get_files(), files_list is: {files_list}")

    processed_relative_npz_list = []
    main_loop_completed_or_skipped = False 

    if not files_list:
        print("Warning: Main - No files found/specified by get_files. extract_builtin will not run.")
        main_loop_completed_or_skipped = True 
    else:
        try:
            print("DEBUG: Main - Calling extract_builtin...")
            processed_relative_npz_list = extract_builtin(
                output_folder=cfg.output_dataset_dir, 
                target_count=args.faces_target_count,
                num_runs=args.num_runs,
                id=args.id,
                time=args.time,
                files=files_list,
                cfg=cfg 
            )
            print(f"DEBUG: Main - extract_builtin returned: {processed_relative_npz_list}")
            main_loop_completed_or_skipped = True 
        except Exception as e:
            print(f"ERROR: Main - Exception during extract_builtin call: {e}")
            import traceback
            traceback.print_exc()
            # main_loop_completed_or_skipped remains False

    if main_loop_completed_or_skipped:
        if processed_relative_npz_list: 
            datalist_path = os.path.join(cfg.output_dataset_dir, "inference_datalist.txt")
            print(f"DEBUG: Main (post-extract) - Creating {datalist_path} with entries: {processed_relative_npz_list}")
            try:
                os.makedirs(os.path.dirname(datalist_path), exist_ok=True)
                with open(datalist_path, 'w') as f:
                    for rel_path in processed_relative_npz_list:
                        f.write(f"{rel_path}\\n") 
                print(f"DEBUG: Main (post-extract) - Successfully created {datalist_path}")
            except IOError as e:
                print(f"ERROR: Main (post-extract) - Failed to write {datalist_path}: {e}")
        else: 
            datalist_path = os.path.join(cfg.output_dataset_dir, "inference_datalist.txt")
            print(f"Warning: Main (post-extract) - No NPZ files were successfully processed or returned. {datalist_path} will not be created or will be empty if it previously existed and is overwritten.")
    else: 
        print("DEBUG: Main (post-extract) - extract_builtin did not complete successfully, datalist creation skipped.")

    print("DEBUG: Main - Reached Blender exit logic.")
    try:
        if bpy and hasattr(bpy, 'ops') and hasattr(bpy.ops.wm, 'quit_blender'):
            print("DEBUG: Main - Attempting bpy.ops.wm.quit_blender()")
            bpy.ops.wm.quit_blender()
            print("DEBUG: Main - bpy.ops.wm.quit_blender() called (script will now exit if successful).") 
        else:
            print("DEBUG: Main - bpy.ops.wm.quit_blender() not available. Using sys.exit(0).")
            sys.exit(0)
    except Exception as e_quit: 
        print(f"DEBUG: Main - Exception during quit_blender/sys.exit: {e_quit}. Attempting final sys.exit(1).")
        sys.exit(1) 

    print("DEBUG: Main - Script end (should only be reached if exit methods failed).")

# Ensure all existing functions like load, clean_bpy, etc. are included before this __main__ block.
# Make sure to replace the placeholder comments with the actual existing code for those functions.
# The provided snippet only shows the __main__ and related functions.
# The full file structure should be:
# imports (including import sys)
# ... other helper functions (load, clean_bpy, process_mesh, etc.) ...
# extract_builtin function (as modified)
# ... other helper functions (str2bool, nullable_string, get_files as modified) ...
# __main__ block (as modified)
if __name__ == "__main__":
    print("DEBUG: extract.py __main__ START")
    sys.stdout.flush()
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, default='configs/data/quick_inference.yaml', help='Path to the data configuration file.')
    parser.add_argument('--input', type=nullable_string, default=None, help='Comma-separated list of input file paths. Overrides input_dataset_dir.')
    parser.add_argument('--input_dir', type=nullable_string, default=None, help='Path to the input dataset directory.')
    parser.add_argument('--input_path', type=nullable_string, default=None, help='Single input file path (for Gradio compatibility).')
    parser.add_argument('--output_dir', type=str, default='dataset_output', help='Path to the output dataset directory.')
    parser.add_argument('--output_path', type=str, default=None, help='Single output file path (for Gradio compatibility).')
    parser.add_argument('--target_count', type=int, default=10000, help='Target face count for mesh simplification.')
    parser.add_argument('--num_runs', type=int, default=1, help='Number of parallel runs.')
    parser.add_argument('--id', type=int, default=0, help='ID of the current run.')
    parser.add_argument('--time', type=str, default='tmp', help='Time string for logging.')
    parser.add_argument('--force_override', type=str2bool, default=False, help='Force override existing files.')

    try:
        args = parser.parse_args()
        print(f"DEBUG: extract.py __main__ - Successfully parsed args: {args}")
        sys.stdout.flush()
    except SystemExit as e: # Catch SystemExit from parse_args
        print(f"CRITICAL: extract.py __main__ - Argument parsing caused SystemExit: {e}")
        sys.stdout.flush()
        # Log to temp file as well, as stderr might not be fully captured in all environments
        with open("/tmp/extract_argparse_error.txt", "a") as f_err:
            f_err.write(f"Argparse SystemExit: {e}\\n")
            import traceback
            traceback.print_exc(file=f_err)
        raise # Re-raise to ensure script exits
    except Exception as e:
        print(f"CRITICAL: extract.py __main__ - Argument parsing failed: {e}")
        sys.stdout.flush()
        with open("/tmp/extract_argparse_error.txt", "a") as f_err:
            f_err.write(f"Argparse Exception: {e}\\n")
            import traceback
            traceback.print_exc(file=f_err)
        sys.exit(1)

    try:
        print(f"DEBUG: extract.py __main__ - Loading config file: {args.config}")
        sys.stdout.flush()
        cfg = Box.from_yaml(filename=args.config)
        
        # Update cfg with command line arguments if they are provided
        # Check if 'data' key exists, otherwise update top-level cfg attributes
        
        # Handle --input_path (single file for Gradio compatibility)
        if args.input_path is not None:
            if 'data' in cfg:
                cfg.data.input = args.input_path
            else:
                cfg.input = args.input_path
                cfg.input_dataset_dir = None  # Explicitly nullify if single input is given

        if args.input is not None:
            if 'data' in cfg:
                cfg.data.input = args.input
            else: 
                cfg.input = args.input
                cfg.input_dataset_dir = None

        if args.input_dir is not None:
            if 'data' in cfg:
                cfg.data.input_dataset_dir = args.input_dir
            else:
                cfg.input_dataset_dir = args.input_dir
        
        # Handle --output_path (single file output for Gradio compatibility)
        output_dir_to_use = args.output_dir
        if args.output_path is not None:
            # Extract directory from output_path
            output_dir_to_use = os.path.dirname(args.output_path)
            if not output_dir_to_use:
                output_dir_to_use = os.getcwd()
        
        if output_dir_to_use != 'dataset_output': # argparse default
            if 'data' in cfg:
                cfg.data.output_dataset_dir = output_dir_to_use
            else:
                cfg.output_dataset_dir = output_dir_to_use
        
        if args.target_count != 10000: # argparse default
            if 'data' in cfg:
                cfg.data.target_count = args.target_count
            else:
                cfg.target_count = args.target_count
        
        if args.force_override: # This is a boolean, directly assign
            if 'data' in cfg:
                cfg.data.force_override = args.force_override
            else:
                cfg.force_override = args.force_override

        # Ensure essential cfg paths are resolved relative to a base directory if needed, or are absolute.
        # For now, assume paths in YAML/args are as intended.

        print(f"DEBUG: extract.py __main__ - Parsed args being used: {args}")
        print(f"DEBUG: extract.py __main__ - Loaded and potentially merged cfg: {cfg}")
        sys.stdout.flush()

        # Determine effective input and output directories from potentially merged config
        # Prefer command-line 'input_path' first, then 'input', then 'input_dir', then cfg's input_dataset_dir
        effective_input_source = None
        if args.input_path is not None:
            effective_input_source = args.input_path
        elif args.input is not None:
            effective_input_source = args.input
        elif args.input_dir is not None:
            effective_input_source = args.input_dir
        else:
            effective_input_source = cfg.get('input_dataset_dir')

        effective_output_dir = output_dir_to_use  # Use the processed output directory

        print(f"DEBUG: extract.py __main__ - Effective input source for get_files: {effective_input_source}")
        print(f"DEBUG: extract.py __main__ - Effective output_dir for get_files & datalist: {effective_output_dir}")
        sys.stdout.flush()
        
        # Determine how to pass input to get_files based on what was provided
        input_for_get_files_arg = None
        input_dir_for_get_files_arg = None
        if args.input_path: # Single file (Gradio mode)
            input_for_get_files_arg = args.input_path
        elif args.input: # Single file or comma-separated list
            input_for_get_files_arg = args.input
        elif args.input_dir: # Directory input
            input_dir_for_get_files_arg = args.input_dir
        else: # Fallback to config's input_dataset_dir
            input_dir_for_get_files_arg = cfg.get('input_dataset_dir')


        files_to_process = get_files(
            data_name=cfg.get('components.data_name', 'raw_data.npz'), # Use get with default
            input_dataset_dir=input_dir_for_get_files_arg,
            output_dataset_dir=effective_output_dir, 
            inputs=input_for_get_files_arg,
            require_suffix=cfg.get('require_suffix', ['obj', 'fbx', 'FBX', 'dae', 'glb', 'gltf', 'vrm']), # Use get with default
            force_override=cfg.get('force_override', False), # Use get with default
            warning=True
        )
        print(f"DEBUG: extract.py __main__ - Files to process after get_files: {files_to_process}")
        sys.stdout.flush()

        datalist_final_path = os.path.join(effective_output_dir, cfg.get('components.datalist_name', 'inference_datalist.txt')) # Use get with default
        print(f"DEBUG: extract.py __main__ - Final path for datalist: {datalist_final_path}")
        sys.stdout.flush()

        if files_to_process:
            print(f"DEBUG: extract.py __main__ - Calling extract_builtin. Output dir for items is within files_to_process tuples.")
            print(f"DEBUG: extract.py __main__ - Datalist will be written to: {datalist_final_path}")
            sys.stdout.flush()
            
            # Ensure the main output directory for the datalist exists
            os.makedirs(effective_output_dir, exist_ok=True)

            created_relative_paths = extract_builtin(
                output_folder=effective_output_dir, # This is where datalist.txt goes
                target_count=cfg.get('target_count', args.target_count), # Get from cfg or fallback to args
                num_runs=args.num_runs, # from args
                id=args.id, # from args
                time=args.time, # from args
                files=files_to_process,
                cfg=cfg # Pass the whole cfg object
            )
            print(f"DEBUG: extract.py __main__ - extract_builtin returned: {created_relative_paths}")
            sys.stdout.flush()

            print(f"DEBUG: extract.py __main__ - Writing inference_datalist.txt to {datalist_final_path}")
            sys.stdout.flush()
            with open(datalist_final_path, "w") as f:
                if created_relative_paths:
                    for rel_path in created_relative_paths:
                        f.write(f"{rel_path}\\n")
                    print(f"DEBUG: extract.py __main__ - Successfully wrote {len(created_relative_paths)} entries to {datalist_final_path}")
                else:
                    f.write("") # Create empty file
                    print(f"DEBUG: extract.py __main__ - No files successfully processed by extract_builtin. Wrote empty {datalist_final_path}")
            sys.stdout.flush()
        else:
            print(f"DEBUG: extract.py __main__ - No files to process after get_files. Creating empty {datalist_final_path}")
            sys.stdout.flush()
            os.makedirs(effective_output_dir, exist_ok=True) # Ensure dir exists
            with open(datalist_final_path, "w") as f:
                f.write("") # Create empty file
        
        print(f"DEBUG: extract.py __main__ - Datalist processing complete.")
        sys.stdout.flush()

    except Exception as e:
        print(f"CRITICAL: extract.py __main__ - Main execution error: {e}")
        import traceback
        traceback.print_exc()
        sys.stdout.flush() # Ensure this gets out
        # Log to temp file
        with open("/tmp/extract_main_error.txt", "a") as f_err:
            f_err.write(f"Timestamp: {datetime.datetime.now()}\\n")
            f_err.write(f"Main Exception: {e}\\n")
            traceback.print_exc(file=f_err)
            f_err.write("\\n")
        sys.exit(1)

    print("DEBUG: extract.py __main__ END")
    sys.stdout.flush()