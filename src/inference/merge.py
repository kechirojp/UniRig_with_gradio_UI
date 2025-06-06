'''
inject the result in res.npz into model.vrm and exports as res_textured.vrm
'''
import argparse
import yaml
import os
import numpy as np
from numpy import ndarray

from typing import Tuple, Union, List

import argparse
from tqdm import tqdm
from box import Box

from scipy.spatial import cKDTree

import open3d as o3d
import itertools

import bpy
from mathutils import Vector

from ..data.raw_data import RawData, RawSkin
from ..data.extract import process_mesh_for_merge, process_armature_for_merge, get_arranged_bones

try:
    from safe_texture_restoration import SafeTextureRestoration
    SAFE_TEXTURE_RESTORATION_AVAILABLE = True
except ImportError:
    SAFE_TEXTURE_RESTORATION_AVAILABLE = False
    print("⚠️ SafeTextureRestoration not available")

try:
    import sys
    sys.path.append("/app")
    from improved_safe_texture_restoration import ImprovedSafeTextureRestoration
    IMPROVED_SAFE_TEXTURE_RESTORATION_AVAILABLE = True
    print("✅ ImprovedSafeTextureRestoration loaded successfully")
except ImportError as e:
    IMPROVED_SAFE_TEXTURE_RESTORATION_AVAILABLE = False
    print(f"⚠️ ImprovedSafeTextureRestoration not available: {e}")

def parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str)
    parser.add_argument('--num_runs', type=int)
    parser.add_argument('--id', type=int)
    return parser.parse_args()

def clean_bpy(preserve_textures=False):
    """Clean Blender data with optional texture preservation."""
    for c in bpy.data.actions:
        bpy.data.actions.remove(c)
    for c in bpy.data.armatures:
        bpy.data.armatures.remove(c)
    for c in bpy.data.cameras:
        bpy.data.cameras.remove(c)
    for c in bpy.data.collections:
        bpy.data.collections.remove(c)
    
    # Conditionally preserve images and materials for textures
    if not preserve_textures:
        for c in bpy.data.images:
            bpy.data.images.remove(c)
        for c in bpy.data.materials:
            bpy.data.materials.remove(c)
        for c in bpy.data.textures:
            bpy.data.textures.remove(c)
    
    for c in bpy.data.meshes:
        bpy.data.meshes.remove(c)
    for c in bpy.data.objects:
        bpy.data.objects.remove(c)

def load(filepath: str, return_armature: bool=False):
    if return_armature:
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
            bpy.ops.wm.obj_import(filepath=filepath)
        elif filepath.endswith(".fbx") or filepath.endswith(".FBX"):
            bpy.ops.import_scene.fbx(filepath=filepath, ignore_leaf_bones=False, use_image_search=True)
        elif filepath.endswith(".glb") or filepath.endswith(".gltf"):
            bpy.ops.import_scene.gltf(filepath=filepath, import_pack_images=True)
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
    if return_armature:
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

def get_skin(arranged_bones):
    meshes = []
    for v in bpy.data.objects:
        if v.type == 'MESH':
            meshes.append(v)
    index = {}
    for (id, pbone) in enumerate(arranged_bones):
        index[pbone.name] = id
    _dict_skin = {}
    total_bones = len(arranged_bones)
    for obj in meshes:
        total_vertices = len(obj.data.vertices)
        skin_weight = np.zeros((total_vertices, total_bones))
        obj_group_names = [g.name for g in obj.vertex_groups]
        obj_verts = obj.data.vertices
        for bone in arranged_bones:
            if bone.name not in obj_group_names:
                continue

            gidx = obj.vertex_groups[bone.name].index
            bone_verts = [v for v in obj_verts if gidx in [g.group for g in v.groups]]
            for v in bone_verts:
                which = [id for id in range(len(v.groups)) if v.groups[id].group==gidx]
                w = v.groups[which[0]].weight
                skin_weight[v.index, index[bone.name]] = w
        _dict_skin[obj.name] = {
            'skin': skin_weight,
        }
    
    skin = np.concatenate([
        _dict_skin[d]['skin'] for d in _dict_skin
    ], axis=0)
    return skin

def axis(a: np.ndarray):
    b = np.concatenate([-a[:, 0:1], -a[:, 1:2], a[:, 2:3]], axis=1)
    return b

def get_correct_orientation_kdtree(a: np.ndarray, b: np.ndarray, bones: np.ndarray, num: int=16384) -> np.ndarray:
    '''
    a: sampled_vertiecs
    b: mesh_vertices
    '''
    min_loss = float('inf')
    best_transformed = a.copy()
    axis_permutations = list(itertools.permutations([0, 1, 2]))
    sign_combinations = [(x, y, z) for x in [1, -1] 
                        for y in [1, -1] 
                        for z in [1, -1]]
    _bones = bones.copy()
    for perm in axis_permutations:
        permuted_a = a[np.random.permutation(a.shape[0])[:num]][:, perm]
        for signs in sign_combinations:
            transformed = permuted_a * np.array(signs)
            tree = cKDTree(transformed)
            distances, indices = tree.query(b)
            current_loss = distances.mean()
            if current_loss < min_loss: # prevent from mirroring
                min_loss = current_loss
                best_transformed = a[:, perm] * np.array(signs)
                bones[:, :3] = _bones[:, :3][:, perm] * np.array(signs)
                bones[:, 3:] = _bones[:, 3:][:, perm] * np.array(signs)
    
    return best_transformed, bones

def denormalize_vertices(mesh_vertices: ndarray, vertices: ndarray, bones: ndarray) -> np.ndarray:
    min_vals = np.min(mesh_vertices, axis=0)
    max_vals = np.max(mesh_vertices, axis=0)
    center = (min_vals + max_vals) / 2
    scale = np.max(max_vals - min_vals) / 2
    denormalized_vertices = vertices * scale + center
    denormalized_bones = bones * scale
    denormalized_bones[:, :3] += center
    denormalized_bones[:, 3:] += center

    return denormalized_vertices, denormalized_bones

def make_armature(
    vertices: ndarray,
    bones: ndarray, # (joint, tail)
    parents: list[Union[int, None]],
    names: list[str],
    skin: ndarray,
    group_per_vertex: int=4,
    add_root: bool=False,
    is_vrm: bool=False,
):
    context = bpy.context
    
    # Store material and texture information before processing
    stored_materials = {}
    stored_images = {}
    mesh_material_assignments = {}
    
    # Preserve all images
    for img in bpy.data.images:
        if img.name not in ['Render Result', 'Viewer Node']:
            stored_images[img.name] = img
            print(f"DEBUG: Storing image: {img.name}")
    
    # Preserve all materials and their node setups
    for mat in bpy.data.materials:
        stored_materials[mat.name] = mat
        print(f"DEBUG: Storing material: {mat.name}")
        if mat.use_nodes and mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    print(f"DEBUG: - Material {mat.name} has texture node with image: {node.image.name}")
    
    # Store mesh-material assignments
    for ob in bpy.data.objects:
        if ob.type == 'MESH':
            mesh_material_assignments[ob.name] = []
            for i, mat_slot in enumerate(ob.material_slots):
                if mat_slot.material:
                    mesh_material_assignments[ob.name].append((i, mat_slot.material.name))
                    print(f"DEBUG: Storing mesh {ob.name} material slot {i}: {mat_slot.material.name}")
    
    mesh_vertices = []
    for ob in bpy.data.objects:
        print(ob.name)
        if ob.type != 'MESH':
            continue
        m = np.array(ob.matrix_world)
        matrix_world_rot = m[:3, :3]
        matrix_world_bias = m[:3, 3]
        for v in ob.data.vertices:
            mesh_vertices.append(matrix_world_rot @ np.array(v.co) + matrix_world_bias)

    mesh_vertices = np.stack(mesh_vertices)
    vertices, bones = denormalize_vertices(mesh_vertices, vertices, bones)
    
    bpy.ops.object.add(type="ARMATURE", location=(0, 0, 0))
    armature = context.object
    if hasattr(armature.data, 'vrm_addon_extension'):
        armature.data.vrm_addon_extension.spec_version = "1.0"
        humanoid = armature.data.vrm_addon_extension.vrm1.humanoid
        is_vrm = True
    bpy.ops.object.mode_set(mode="EDIT")
    edit_bones = armature.data.edit_bones
    if add_root:
        bone_root = edit_bones.new('Root')
        bone_root.name = 'Root'
        bone_root.head = (0., 0., 0.)
        bone_root.tail = (bones[0, 0], bones[0, 1], bones[0, 2])
    
    J = len(names)
    def extrude_bone(
        name: Union[None, str],
        parent_name: Union[None, str],
        head: Tuple[float, float, float],
        tail: Tuple[float, float, float],
    ):
        bone = edit_bones.new(name)
        bone.head = (head[0], head[1], head[2])
        bone.tail = (tail[0], tail[1], tail[2])
        bone.name = name
        if parent_name is None:
            return
        parent_bone = edit_bones.get(parent_name)
        bone.parent = parent_bone
        bone.use_connect = False # always False currently

    vertices, bones = get_correct_orientation_kdtree(vertices, mesh_vertices, bones)
    for i in range(J):
        if add_root:
            pname = 'Root' if parents[i] is None else names[parents[i]]
        else:
            pname = None if parents[i] is None else names[parents[i]]
        extrude_bone(names[i], pname, bones[i, :3], bones[i, 3:])

    # must set to object mode to enable parent_set
    bpy.ops.object.mode_set(mode='OBJECT')
    objects = bpy.data.objects
    for o in bpy.context.selected_objects:
        o.select_set(False)
    
    argsorted = np.argsort(-skin, axis=1)
    vertex_group_reweight = skin[np.arange(skin.shape[0])[..., None], argsorted]
    vertex_group_reweight = vertex_group_reweight / vertex_group_reweight[..., :group_per_vertex].sum(axis=1)[...,None]
    vertex_group_reweight = np.nan_to_num(vertex_group_reweight)
    tree = cKDTree(vertices)
    for ob in objects:
        if ob.type != 'MESH':
            continue
        
        # Store original material assignment before parenting
        original_materials = []
        for mat_slot in ob.material_slots:
            original_materials.append(mat_slot.material)
        
        ob.select_set(True)
        armature.select_set(True)
        bpy.ops.object.parent_set(type='ARMATURE_NAME')
        
    # Restore material assignments after parenting
        for i, mat in enumerate(original_materials):
            if i < len(ob.material_slots):
                ob.material_slots[i].material = mat
                print(f"DEBUG: Restored material {mat.name if mat else 'None'} to slot {i} of mesh {ob.name}")
        
        # Restore texture node connections with proper identification
        for mat_slot in ob.material_slots:
            if mat_slot.material and mat_slot.material.use_nodes and mat_slot.material.node_tree:
                nodes = mat_slot.material.node_tree.nodes
                links = mat_slot.material.node_tree.links
                
                # Find the Principled BSDF node
                principled_node = None
                for node in nodes:
                    if node.type == 'BSDF_PRINCIPLED':
                        principled_node = node
                        break
                
                if principled_node:
                    # Identify and restore texture connections based on texture type
                    base_color_textures = []
                    normal_textures = []
                    roughness_textures = []
                    
                    # Categorize textures by name patterns
                    for node in nodes:
                        if node.type == 'TEX_IMAGE' and node.image:
                            image_name = node.image.name.lower()
                            color_space = node.image.colorspace_settings.name
                            
                            print(f"DEBUG: Analyzing texture {node.image.name} with color space {color_space}")
                            
                            # Base Color identification (sRGB color space + name patterns)
                            if (color_space == 'sRGB' or 
                                'col' in image_name or 'bc' in image_name or 
                                'base' in image_name or 'diffuse' in image_name or
                                'albedo' in image_name):
                                base_color_textures.append(node)
                                print(f"DEBUG: Identified {node.image.name} as BASE COLOR texture")
                            
                            # Normal map identification (Non-Color + name patterns)
                            elif (color_space == 'Non-Color' and 
                                  ('nrml' in image_name or 'normal' in image_name or 
                                   '_n' in image_name or 'norm' in image_name)):
                                normal_textures.append(node)
                                print(f"DEBUG: Identified {node.image.name} as NORMAL texture")
                            
                            # Roughness identification (Non-Color + name patterns)
                            elif (color_space == 'Non-Color' and 
                                  ('gloss' in image_name or 'rough' in image_name or 
                                   '_r' in image_name or 'metallic' in image_name)):
                                roughness_textures.append(node)
                                print(f"DEBUG: Identified {node.image.name} as ROUGHNESS texture")
                            
                            else:
                                print(f"DEBUG: Unknown texture type for {node.image.name}")
                    
                    # Connect Base Color textures through Mix node (matching original structure)
                    if base_color_textures:
                        base_color_node = base_color_textures[0]  # Use first base color texture
                        
                        # Find or create Mix node for base color
                        mix_node = None
                        for node in nodes:
                            if node.type == 'MIX' and any(link.to_node == principled_node and link.to_socket.name == 'Base Color' for link in node.outputs['Result'].links):
                                mix_node = node
                                break
                        
                        if not mix_node:
                            mix_node = nodes.new(type='ShaderNodeMix')
                            mix_node.data_type = 'RGBA'
                            mix_node.location = (principled_node.location.x - 300, principled_node.location.y + 300)
                        
                        # Find or create Color Attribute node
                        color_attr_node = None
                        for node in nodes:
                            if node.type == 'VERTEX_COLOR':
                                color_attr_node = node
                                break
                        
                        if not color_attr_node:
                            color_attr_node = nodes.new(type='ShaderNodeVertexColor')
                            color_attr_node.location = (mix_node.location.x - 300, mix_node.location.y)
                        
                        # Clear existing Base Color connections
                        for link in list(principled_node.inputs['Base Color'].links):
                            links.remove(link)
                        
                        # Connect: Base Color Texture -> Mix[A], Color Attribute -> Mix[B], Mix -> Principled BSDF Base Color
                        links.new(base_color_node.outputs['Color'], mix_node.inputs['A'])
                        links.new(color_attr_node.outputs['Color'], mix_node.inputs['B'])
                        links.new(mix_node.outputs['Result'], principled_node.inputs['Base Color'])
                        print(f"DEBUG: Connected {base_color_node.image.name} to Base Color via Mix node")
                    
                    # Connect Normal textures through Normal Map node
                    if normal_textures:
                        normal_texture_node = normal_textures[0]
                        
                        # Find or create Normal Map node
                        normal_map_node = None
                        for node in nodes:
                            if node.type == 'NORMAL_MAP':
                                normal_map_node = node
                                break
                        
                        if not normal_map_node:
                            normal_map_node = nodes.new(type='ShaderNodeNormalMap')
                            normal_map_node.location = (principled_node.location.x - 300, principled_node.location.y - 200)
                        
                        # Clear existing connections
                        for link in list(normal_texture_node.outputs['Color'].links):
                            links.remove(link)
                        for link in list(principled_node.inputs['Normal'].links):
                            links.remove(link)
                        
                        # Connect: Normal Texture -> Normal Map -> Principled BSDF
                        links.new(normal_texture_node.outputs['Color'], normal_map_node.inputs['Color'])
                        links.new(normal_map_node.outputs['Normal'], principled_node.inputs['Normal'])
                        print(f"DEBUG: Connected {normal_texture_node.image.name} to Normal via Normal Map node")
                    
                    # Connect Roughness textures (matching original structure with Separate Color)
                    if roughness_textures:
                        roughness_node = roughness_textures[0]
                        
                        # Find or create Separate Color node
                        separate_node = None
                        for node in nodes:
                            if node.type == 'SEPARATE_COLOR':
                                separate_node = node
                                break
                        
                        if not separate_node:
                            separate_node = nodes.new(type='ShaderNodeSeparateColor')
                            separate_node.location = (principled_node.location.x - 300, principled_node.location.y + 100)
                        
                        # Find or create Math node for metallic
                        math_node = None
                        for node in nodes:
                            if node.type == 'MATH' and any(link.to_node == principled_node and link.to_socket.name == 'Metallic' for link in node.outputs['Value'].links):
                                math_node = node
                                break
                        
                        if not math_node:
                            math_node = nodes.new(type='ShaderNodeMath')
                            math_node.operation = 'MULTIPLY'  # Or whatever operation was used originally
                            math_node.location = (principled_node.location.x - 150, principled_node.location.y + 50)
                        
                        # Clear existing connections
                        for link in list(principled_node.inputs['Roughness'].links):
                            links.remove(link)
                        for link in list(principled_node.inputs['Metallic'].links):
                            links.remove(link)
                        
                        # Connect according to original structure:
                        # Roughness Texture -> Separate Color -> Green -> Principled BSDF Roughness
                        # Roughness Texture -> Separate Color -> Blue -> Math -> Principled BSDF Metallic
                        links.new(roughness_node.outputs['Color'], separate_node.inputs['Color'])
                        links.new(separate_node.outputs['Green'], principled_node.inputs['Roughness'])
                        links.new(separate_node.outputs['Blue'], math_node.inputs['Value'])
                        links.new(math_node.outputs['Value'], principled_node.inputs['Metallic'])
                        print(f"DEBUG: Connected {roughness_node.image.name} to Roughness (Green) and Metallic (Blue) via Separate Color")
        
        vis = []
        for x in ob.vertex_groups:
            vis.append(x.name)
        
        n_vertices = []
        m = np.array(ob.matrix_world)
        matrix_world_rot = m[:3, :3]
        matrix_world_bias = m[:3, 3]
        for v in ob.data.vertices:
            n_vertices.append(matrix_world_rot @ np.array(v.co) + matrix_world_bias)
        n_vertices = np.stack(n_vertices)

        _, index = tree.query(n_vertices)

        for v, co in enumerate(tqdm(n_vertices)):
            for ii in range(group_per_vertex):
                i = argsorted[index[v], ii]
                if i >= len(names):
                    continue
                n = names[i]
                if n not in ob.vertex_groups:
                    continue
                        
                ob.vertex_groups[n].add([v], vertex_group_reweight[index[v], ii], 'REPLACE')
        armature.select_set(False)
        ob.select_set(False)
    
    # Final verification of material preservation
    print(f"DEBUG: Final verification - Materials after armature setup:")
    for ob in bpy.data.objects:
        if ob.type == 'MESH':
            print(f"DEBUG: Mesh '{ob.name}' has {len(ob.material_slots)} material slots")
            for i, mat_slot in enumerate(ob.material_slots):
                if mat_slot.material:
                    print(f"DEBUG: - Slot {i}: {mat_slot.material.name}")
                    if mat_slot.material.use_nodes and mat_slot.material.node_tree:
                        texture_nodes = [n for n in mat_slot.material.node_tree.nodes if n.type == 'TEX_IMAGE']
                        print(f"DEBUG:   - Has {len(texture_nodes)} texture nodes")
                        for tex_node in texture_nodes:
                            if tex_node.image:
                                print(f"DEBUG:     - Texture: {tex_node.image.name}")
    
    # set vrm bones link
    if is_vrm:
        armature.data.vrm_addon_extension.spec_version = "1.0"
        humanoid.human_bones.hips.node.bone_name = "J_Bip_C_Hips"
        humanoid.human_bones.spine.node.bone_name = "J_Bip_C_Spine"
        
        humanoid.human_bones.chest.node.bone_name = "J_Bip_C_Chest"
        humanoid.human_bones.neck.node.bone_name = "J_Bip_C_Neck"
        humanoid.human_bones.head.node.bone_name = "J_Bip_C_Head"
        humanoid.human_bones.left_upper_leg.node.bone_name = "J_Bip_L_UpperLeg"
        humanoid.human_bones.left_lower_leg.node.bone_name = "J_Bip_L_LowerLeg"
        humanoid.human_bones.left_foot.node.bone_name = "J_Bip_L_Foot"
        humanoid.human_bones.right_upper_leg.node.bone_name = "J_Bip_R_UpperLeg"
        humanoid.human_bones.right_lower_leg.node.bone_name = "J_Bip_R_LowerLeg"
        humanoid.human_bones.right_foot.node.bone_name = "J_Bip_R_Foot"
        humanoid.human_bones.left_upper_arm.node.bone_name = "J_Bip_L_UpperArm"
        humanoid.human_bones.left_lower_arm.node.bone_name = "J_Bip_L_LowerArm"
        humanoid.human_bones.left_hand.node.bone_name = "J_Bip_L_Hand"
        humanoid.human_bones.right_upper_arm.node.bone_name = "J_Bip_R_UpperArm"
        humanoid.human_bones.right_lower_arm.node.bone_name = "J_Bip_R_LowerArm"
        humanoid.human_bones.right_hand.node.bone_name = "J_Bip_R_Hand"
        
        bpy.ops.vrm.assign_vrm1_humanoid_human_bones_automatically(armature_name="Armature")

def merge(
    path: str,
    output_path: str,
    vertices: ndarray,
    joints: ndarray,
    skin: ndarray,
    parents: List[Union[None, int]],
    names: List[str],
    tails: ndarray,
    add_root: bool=False,
    is_vrm: bool=False,
):
    '''
    Merge skin and bone into original file with texture preservation.
    '''
    clean_bpy(preserve_textures=True)
    try:
        load(path)
        # Try to load texture files if they exist
        model_name = os.path.splitext(os.path.basename(path))[0]
        data_dir = os.path.dirname(path)
        # loaded_textures = load_texture_files(data_dir, model_name)  # Disabled - use native format embedding
        print(f"DEBUG: Skipping separate texture file loading - relying on GLB/FBX native embedding")
        
        # Debug material information before armature removal
        print(f"DEBUG: Materials before armature removal: {len(bpy.data.materials)}")
        for mat in bpy.data.materials:
            print(f"DEBUG: Material: {mat.name}")
            if mat.use_nodes and mat.node_tree:
                for node in mat.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image:
                        print(f"DEBUG: - Texture node: {node.image.name}")
        
        # Debug mesh objects and their materials
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and obj.data.materials:
                print(f"DEBUG: Mesh '{obj.name}' has {len(obj.data.materials)} materials")
                for i, mat in enumerate(obj.data.materials):
                    if mat:
                        print(f"DEBUG: - Material slot {i}: {mat.name}")
        
    except Exception as e:
        print(f"Failed to load {path}: {e}")
        return
    for c in bpy.data.armatures:
        bpy.data.armatures.remove(c)
    
    bones = np.concatenate([joints, tails], axis=1)
    # if the result is weired, orientation may be wrong
    make_armature(
        vertices=vertices,
        bones=bones,
        parents=parents,
        names=names,
        skin=skin,
        group_per_vertex=4,
        add_root=add_root,
        is_vrm=is_vrm,
    )
    
    # Debug material information after make_armature
    print(f"DEBUG: Materials after make_armature: {len(bpy.data.materials)}")
    for mat in bpy.data.materials:
        print(f"DEBUG: Material: {mat.name}")
        if mat.use_nodes and mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    print(f"DEBUG: - Texture node: {node.image.name}")
    
    # Debug image data blocks availability
    print(f"DEBUG: Available images: {len(bpy.data.images)}")
    for img in bpy.data.images:
        if img.name not in ['Render Result', 'Viewer Node']:
            print(f"DEBUG: - Image: {img.name}, Size: {img.size[:]} pixels")
            if hasattr(img, 'packed_file') and img.packed_file:
                print(f"DEBUG:   - Image is packed: {len(img.packed_file.data)} bytes")
            elif img.filepath:
                print(f"DEBUG:   - Image filepath: {img.filepath}")
                print(f"DEBUG:   - File exists: {os.path.exists(img.filepath)}")
    
    # Debug mesh objects and their materials after armature setup
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.data.materials:
            print(f"DEBUG: Mesh '{obj.name}' has {len(obj.data.materials)} materials after armature setup")
            for i, mat in enumerate(obj.data.materials):
                if mat:
                    print(f"DEBUG: - Material slot {i}: {mat.name}")
    
    dirpath = os.path.dirname(output_path)
    if dirpath != '':
        os.makedirs(dirpath, exist_ok=True)
    
    # Ensure texture images are properly packed before export
    print("DEBUG: Packing texture images for export...")
    for img in bpy.data.images:
        if img.name not in ['Render Result', 'Viewer Node']:
            if not (hasattr(img, 'packed_file') and img.packed_file):
                try:
                    img.pack()
                    print(f"DEBUG: Packed image: {img.name}")
                except Exception as e:
                    print(f"DEBUG: Failed to pack image {img.name}: {e}")
            else:
                print(f"DEBUG: Image already packed: {img.name}")
    
    try:
        if is_vrm:
            bpy.ops.export_scene.vrm(filepath=output_path)
        elif output_path.endswith(".fbx") or output_path.endswith(".FBX"):
            # Ensure all mesh objects are selected for export
            bpy.ops.object.select_all(action='DESELECT')
            for obj in bpy.data.objects:
                if obj.type in ['MESH', 'ARMATURE']:
                    obj.select_set(True)
            
            # Final debug before export
            print("DEBUG: Final state before FBX export:")
            for obj in bpy.data.objects:
                if obj.type == 'MESH':
                    print(f"DEBUG: - Mesh: {obj.name}")
                    for i, mat_slot in enumerate(obj.material_slots):
                        if mat_slot.material and mat_slot.material.use_nodes:
                            print(f"DEBUG:   - Material {i}: {mat_slot.material.name}")
                            for node in mat_slot.material.node_tree.nodes:
                                if node.type == 'TEX_IMAGE' and node.image:
                                    print(f"DEBUG:     - Texture node: {node.image.name}")
                                    print(f"DEBUG:     - Connected to: {[link.to_socket.name for link in node.outputs[0].links]}")
            
            # Verify images are still available
            print(f"DEBUG: Images available for export: {len([img for img in bpy.data.images if img.name not in ['Render Result', 'Viewer Node']])}")
            
            # Prepare materials for FBX export - simplify node connections for better compatibility
            print("DEBUG: Preparing materials for FBX export...")
            for obj in bpy.data.objects:
                if obj.type == 'MESH' and obj.data.materials:
                    for i, material in enumerate(obj.data.materials):
                        if material and material.use_nodes:
                            prepare_material_for_fbx_export(material)
            
            bpy.ops.export_scene.fbx(
                filepath=output_path, 
                use_selection=False,  # Export all objects
                add_leaf_bones=True,
                # Texture embedding settings
                path_mode='COPY',  # Copy textures to output directory
                embed_textures=True,  # Embed textures in FBX
                # Material settings
                use_mesh_modifiers=True,
                use_custom_props=True,
                # Texture coordinate settings
                mesh_smooth_type='OFF',  # Keep original smoothing
                use_tspace=True,  # Use tangent space for normal maps
                # Animation settings (if needed)
                bake_anim=False
            )
        elif output_path.endswith(".glb") or output_path.endswith(".gltf"):
            # Ensure all mesh objects are selected for export
            bpy.ops.object.select_all(action='DESELECT')
            for obj in bpy.data.objects:
                if obj.type in ['MESH', 'ARMATURE']:
                    obj.select_set(True)
            
            # Use Blender 4.2 context override for safe GLTF export
            try:
                from blender_42_context_fix import Blender42ContextManager
                context_mgr = Blender42ContextManager()
                
                success = context_mgr.safe_gltf_export_with_context_override(
                    filepath=output_path,
                    use_selection=False,  # Export all objects
                    export_format='GLB' if output_path.endswith('.glb') else 'GLTF_EMBEDDED',
                    # Texture and material embedding
                    export_materials='EXPORT',  # Export materials with textures
                    export_colors=True,  # Export vertex colors
                    # Image format settings
                    export_image_format='AUTO',  # Use original format when possible
                    export_jpeg_quality=90,  # High quality for JPEG textures
                    # Mesh settings
                    export_normals=True,
                    export_tangents=False,
                    export_tex_coords=True,  # Essential for UV mapping
                    export_attributes=True,  # Export custom attributes
                    # Compression settings
                    export_draco_mesh_compression_enable=False,  # Disable compression to preserve quality
                    # Animation settings
                    export_animations=False,  # Disable for static models
                )
                
                if not success:
                    raise Exception("GLTF export failed with context error")
                    
            except ImportError as e:
                print(f"Warning: Context manager not available, using fallback: {e}")
                bpy.ops.export_scene.gltf(
                    filepath=output_path,
                    use_selection=False,  # Export all objects
                    export_format='GLB' if output_path.endswith('.glb') else 'GLTF_EMBEDDED',
                    # Texture and material embedding
                    export_materials='EXPORT',  # Export materials with textures
                    export_colors=True,  # Export vertex colors
                    # Image format settings
                    export_image_format='AUTO',  # Use original format when possible
                    export_jpeg_quality=90,  # High quality for JPEG textures
                    # Mesh settings
                    export_normals=True,
                    export_tangents=False,
                    export_tex_coords=True,  # Essential for UV mapping
                    export_attributes=True,  # Export custom attributes
                    # Compression settings
                    export_draco_mesh_compression_enable=False,  # Disable compression to preserve quality
                    # Animation settings
                    export_animations=False,  # Disable for static models
                export_frame_range=False,
                # Other settings
                export_apply=False,  # Don't apply modifiers
                export_yup=True  # Use Y-up coordinate system
            )
        elif output_path.endswith(".dae"):
            bpy.ops.wm.collada_export(filepath=output_path)
        elif output_path.endswith(".blend"):
            with bpy.data.libraries.load(output_path) as (data_from, data_to):
                data_to.objects = data_from.objects
        else:
            raise ValueError(f"not suported type {output_path}")
    except:
        raise ValueError(f"failed to export {output_path}")

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

def parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('--require_suffix', type=str, required=True)
    parser.add_argument('--num_runs', type=int, required=True)
    parser.add_argument('--id', type=int, required=True)
    parser.add_argument('--data_config', type=str, required=False)
    parser.add_argument('--skeleton_config', type=str, required=False)
    parser.add_argument('--skin_config', type=str, required=False)
    parser.add_argument('--merge_dir', type=str, required=False)
    parser.add_argument('--merge_name', type=str, required=False)
    parser.add_argument('--add_root', type=str2bool, required=False, default=False)
    parser.add_argument('--source', type=nullable_string, required=False, default=None)
    parser.add_argument('--target', type=nullable_string, required=False, default=None)
    parser.add_argument('--output', type=nullable_string, required=False, default=None)
    return parser.parse_args()

def transfer(source: str, target: str, output: str, add_root: bool=False):
    try:
        armature = load(filepath=source, return_armature=True)
        assert armature is not None
        # Try to load texture files for the source model
        model_name = os.path.splitext(os.path.basename(source))[0]
        data_dir = os.path.dirname(source)
        # loaded_textures = load_texture_files(data_dir, model_name)  # Disabled - use native format embedding
        print(f"DEBUG: Skipping separate texture file loading - relying on GLB/FBX native embedding")
    except Exception as e:
        print(f"failed to load {source}")
        return
    vertices, faces = process_mesh_for_merge()
    arranged_bones = get_arranged_bones(armature)
    skin = get_skin(arranged_bones)
    joints, tails, parents, names, matrix_local = process_armature_for_merge(armature, arranged_bones)
    
    # First, create the basic rigged model using standard merge
    merge(
        path=target,
        output_path=output,
        vertices=vertices,
        joints=joints,
        skin=skin,
        parents=parents,
        names=names,
        tails=tails,
        add_root=add_root,
    )
    
    # 🛡️ PRIORITY 1: Improved Safe FBX-to-Blend Texture Flow (Post-Processing)
    if IMPROVED_SAFE_TEXTURE_RESTORATION_AVAILABLE and output.endswith('.fbx'):
        print("🛡️ Starting ImprovedSafeTextureRestoration post-processing (YAML-based)...")
        
        # Determine model name and paths
        model_name = os.path.splitext(os.path.basename(source))[0]
        output_dir = os.path.dirname(output)
        
        # Look for YAML manifest in Step 1 extraction directory (multiple possible locations)
        possible_paths = [
            # CORRECTED: Absolute paths to known locations (high priority)
            "/app/pipeline_work/01_extracted_mesh_fixed/texture_manifest.yaml",
            "/app/pipeline_work/01_extracted_mesh_fixed2/texture_manifest.yaml",
            # Standard relative paths (fallback)
            os.path.join(output_dir, "..", "..", "01_extracted_mesh", model_name, "texture_manifest.yaml"),
            os.path.join(output_dir, "..", "..", "01_extracted_mesh_fixed", "texture_manifest.yaml"),
            os.path.join(output_dir, "..", "..", "01_extracted_mesh_fixed2", "texture_manifest.yaml"),
            os.path.join(output_dir, "..", "..", "01_extracted_mesh", "texture_manifest.yaml"),
            os.path.join(os.path.dirname(source), "texture_manifest.yaml")
        ]
        
        yaml_manifest_path = None
        texture_dir = None
        
        for path in possible_paths:
            if os.path.exists(path):
                yaml_manifest_path = path
                texture_dir = os.path.join(os.path.dirname(path), "textures")
                print(f"📂 Found YAML manifest at: {yaml_manifest_path}")
                break
        
        if yaml_manifest_path and os.path.exists(yaml_manifest_path):
            print(f"✅ Found YAML manifest for ImprovedSafeTextureRestoration: {yaml_manifest_path}")
            
            try:
                # Initialize ImprovedSafeTextureRestoration with correct parameters
                working_dir = os.path.dirname(output)  # Use directory containing the FBX
                base_working_dir = os.path.dirname(os.path.dirname(working_dir))  # Go up to pipeline_work level
                
                improved_safe_flow = ImprovedSafeTextureRestoration(
                    working_dir=base_working_dir,
                    model_name=model_name,
                    use_subprocess=True
                )
                
                # Execute 6-stage improved safe flow
                success, final_fbx_path, quality_report = improved_safe_flow.execute_full_restoration(
                    skinned_fbx_path=output  # Use the FBX just created by merge()
                )
                
                # Process results
                if success and final_fbx_path and os.path.exists(final_fbx_path):
                    safe_result = {
                        'success': True,
                        'final_fbx_path': final_fbx_path,
                        'quality_report': quality_report,
                        'logs': f"ImprovedSafeTextureRestoration completed successfully!\nFinal FBX: {final_fbx_path}"
                    }
                else:
                    safe_result = {
                        'success': False,
                        'error_message': "ImprovedSafeTextureRestoration failed to complete",
                        'quality_report': quality_report if 'quality_report' in locals() else {}
                    }
                
                if safe_result['success']:
                    print("✅ ImprovedSafeTextureRestoration completed successfully!")
                    print(f"📁 Improved Safe FBX with textures: {safe_result['final_fbx_path']}")
                    print(f"📊 Quality Score: {safe_result['validation_report']['quality_score']}")
                    print(f"📏 Final Size: {safe_result['validation_report']['file_size_mb']:.2f}MB")
                    
                    # Replace original output with improved safe result
                    import shutil
                    shutil.copy2(safe_result['final_fbx_path'], output)
                    print(f"📋 Replaced original FBX with ImprovedSafeTextureRestoration result")
                    
                    print(f"🔍 ImprovedSafeTextureRestoration Summary:\n{safe_result['logs']}")
                else:
                    print(f"❌ ImprovedSafeTextureRestoration failed: {safe_result['error_message']}")
                    print(f"📋 Error Logs:\n{safe_result['logs']}")
                    print("🔄 Continuing with original merge result...")
                    
            except Exception as e:
                print(f"❌ ImprovedSafeTextureRestoration exception: {e}")
                import traceback
                traceback.print_exc()
                print("🔄 Continuing with original merge result...")
        else:
            print(f"⚠️ YAML manifest not found for ImprovedSafeTextureRestoration: {yaml_manifest_path}")
            print("🔄 Continuing with original merge result...")
    
    # 🔄 Fallback: Legacy Safe Texture Flow (JSON-based)
    elif SAFE_TEXTURE_RESTORATION_AVAILABLE and output.endswith('.fbx'):
        print("🔄 Falling back to legacy SafeTextureRestoration (JSON-based)...")
        
        # Determine metadata and texture paths
        model_name = os.path.splitext(os.path.basename(source))[0]
        output_dir = os.path.dirname(output)
        
        # Look for metadata in Step 1 extraction directory (multiple possible locations)
        possible_metadata_paths = [
            # CORRECTED: Absolute paths to known locations (high priority)
            "/app/pipeline_work/01_extracted_mesh_fixed/material_metadata.json",
            "/app/pipeline_work/01_extracted_mesh_fixed2/material_metadata.json",
            # Standard relative paths (fallback)
            os.path.join(output_dir, "..", "..", "01_extracted_mesh", model_name, "material_metadata.json"),
            os.path.join(output_dir, "..", "..", "01_extracted_mesh_fixed", "material_metadata.json"),
            os.path.join(output_dir, "..", "..", "01_extracted_mesh_fixed2", "material_metadata.json"),
            os.path.join(output_dir, "..", "..", "01_extracted_mesh", "material_metadata.json"),
            os.path.join(os.path.dirname(source), "material_metadata.json")
        ]
        
        metadata_json_path = None
        texture_dir = None
        
        for path in possible_metadata_paths:
            if os.path.exists(path):
                metadata_json_path = path
                texture_dir = os.path.join(os.path.dirname(path), "textures")
                print(f"📂 Found metadata for legacy SafeTextureRestoration at: {metadata_json_path}")
                break
        
        if metadata_json_path and os.path.exists(metadata_json_path):
            print(f"✅ Found metadata for legacy SafeTextureRestoration: {metadata_json_path}")
            
            try:
                # Initialize SafeTextureRestoration
                safe_flow = SafeTextureRestoration(output_dir)
                
                # Execute 6-stage safe flow
                safe_result = safe_flow.process_skinned_fbx(
                    skinned_fbx_path=output,  # Use the FBX just created by merge()
                    metadata_json_path=metadata_json_path,
                    texture_dir=texture_dir,
                    model_name=model_name,
                    progress_callback=lambda progress, desc: print(f"LegacySafeFlow: {progress:.1%} - {desc}")
                )
                
                if safe_result['success']:
                    print("✅ Legacy SafeTextureRestoration completed successfully!")
                    print(f"📁 Safe FBX with textures: {safe_result['final_fbx_path']}")
                    print(f"📊 Quality Score: {safe_result['validation_report']['quality_score']}")
                    print(f"📏 Final Size: {safe_result['validation_report']['file_size_mb']:.2f}MB")
                    
                    # Replace original output with safe result
                    import shutil
                    shutil.copy2(safe_result['final_fbx_path'], output)
                    print(f"📋 Replaced original FBX with legacy SafeTextureRestoration result")
                    
                    print(f"🔍 Legacy SafeTextureRestoration Summary:\n{safe_result['logs']}")
                else:
                    print(f"❌ Legacy SafeTextureRestoration failed: {safe_result['error_message']}")
                    print(f"📋 Error Logs:\n{safe_result['logs']}")
                    print("🔄 Continuing with original merge result...")
                    
            except Exception as e:
                print(f"❌ Legacy SafeTextureRestoration exception: {e}")
                import traceback
                traceback.print_exc()
                print("🔄 Continuing with original merge result...")
        else:
            print(f"⚠️ Metadata not found for legacy SafeTextureRestoration: {metadata_json_path}")
            print("🔄 Continuing with original merge result...")
    else:
        if not IMPROVED_SAFE_TEXTURE_RESTORATION_AVAILABLE and not SAFE_TEXTURE_RESTORATION_AVAILABLE:
            print("⚠️ Neither ImprovedSafeTextureRestoration nor SafeTextureRestoration available")
        elif not output.endswith('.fbx'):
            print(f"ℹ️ SafeTextureRestoration skipped - output format not FBX: {output}")
        print("🔄 Using original merge result...")
    
    print(f"✅ transfer() completed: {output}")

def load_texture_files(data_dir, model_name):
    """Load texture files back into Blender during merge process."""
    texture_dir = os.path.join(data_dir, "textures")
    manifest_path = os.path.join(data_dir, "texture_manifest.yaml")
    
    loaded_textures = []
    
    if not os.path.exists(manifest_path):
        print(f"DEBUG: No texture manifest found at {manifest_path}")
        return loaded_textures
    
    try:
        with open(manifest_path, 'r') as f:
            manifest = yaml.safe_load(f)
        
        print(f"DEBUG: Loading textures from manifest: {manifest.get('texture_count', 0)} textures")
        
        for texture_info in manifest.get('textures', []):
            texture_path = texture_info.get('saved_path')
            original_name = texture_info.get('original_name')
            
            if texture_path and os.path.exists(texture_path):
                try:
                    # Load image into Blender
                    image = bpy.data.images.load(texture_path)
                    image.name = original_name or os.path.basename(texture_path)
                    loaded_textures.append({
                        'name': image.name,
                        'path': texture_path,
                        'image': image
                    })
                    print(f"DEBUG: Loaded texture: {image.name} from {texture_path}")
                except Exception as e:
                    print(f"DEBUG: Failed to load texture {texture_path}: {e}")
            else:
                print(f"DEBUG: Texture file not found: {texture_path}")
    
    except Exception as e:
        print(f"DEBUG: Error loading texture manifest: {e}")
    
    return loaded_textures

def prepare_material_for_fbx_export(material):
    """
    FBXエクスポート用にマテリアルを準備する
    複雑なノード構造をシンプル化してFBX互換性を向上
    """
    if not material.use_nodes or not material.node_tree:
        return
    
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    
    print(f"DEBUG: Preparing material '{material.name}' for FBX export")
    
    # Principled BSDFノードを見つける
    principled_node = None
    for node in nodes:
        if node.type == 'BSDF_PRINCIPLED':
            principled_node = node
            break
    
    if not principled_node:
        print(f"DEBUG: No Principled BSDF found in material '{material.name}'")
        return
    
    # テクスチャノードを特定
    base_color_texture = None
    normal_texture = None
    roughness_texture = None
    
    for node in nodes:
        if node.type == 'TEX_IMAGE' and node.image:
            image_name = node.image.name.lower()
            color_space = node.image.colorspace_settings.name
            
            # Base color texture
            if (color_space == 'sRGB' or 
                any(pattern in image_name for pattern in ['col', 'bc', 'base', 'diffuse', 'albedo'])):
                base_color_texture = node
            # Normal texture
            elif (color_space == 'Non-Color' and 
                  any(pattern in image_name for pattern in ['nrml', 'normal', '_n', 'norm'])):
                normal_texture = node
            # Roughness texture
            elif (color_space == 'Non-Color' and 
                  any(pattern in image_name for pattern in ['gloss', 'rough', '_r', 'metallic'])):
                roughness_texture = node
    
    # シンプル化: 直接接続を優先
    # Base Colorの直接接続（Mix nodeをバイパス）
    if base_color_texture:
        # 既存の接続をクリア
        for link in list(principled_node.inputs['Base Color'].links):
            links.remove(link)
        
        # 直接接続
        links.new(base_color_texture.outputs['Color'], principled_node.inputs['Base Color'])
        print(f"DEBUG: Direct connection: {base_color_texture.image.name} → Base Color")
    
    # Normal mapは保持（Normal Map nodeを経由）
    if normal_texture:
        # Normal Map nodeを探す
        normal_map_node = None
        for node in nodes:
            if node.type == 'NORMAL_MAP':
                normal_map_node = node
                break
        
        if normal_map_node:
            # 接続を確認・復元
            if not normal_map_node.inputs['Color'].links:
                links.new(normal_texture.outputs['Color'], normal_map_node.inputs['Color'])
            if not principled_node.inputs['Normal'].links:
                links.new(normal_map_node.outputs['Normal'], principled_node.inputs['Normal'])
            print(f"DEBUG: Normal map connection maintained: {normal_texture.image.name} → Normal")
    
    # Roughnessの直接接続（Separate Colorをバイパス）
    if roughness_texture:
        # 既存の接続をクリア
        for link in list(principled_node.inputs['Roughness'].links):
            links.remove(link)
        
        # 直接接続（Greenチャンネルを使用）
        # Separate Color nodeを作成または見つける
        separate_node = None
        for node in nodes:
            if node.type == 'SEPARATE_COLOR':
                separate_node = node
                break
        
        if not separate_node:
            separate_node = nodes.new(type='ShaderNodeSeparateColor')
            separate_node.location = (principled_node.location.x - 200, principled_node.location.y - 200)
        
        # 接続を設定
        if not separate_node.inputs['Color'].links:
            links.new(roughness_texture.outputs['Color'], separate_node.inputs['Color'])
        if not principled_node.inputs['Roughness'].links:
            links.new(separate_node.outputs['Green'], principled_node.inputs['Roughness'])
        
        print(f"DEBUG: Roughness connection: {roughness_texture.image.name} → Roughness (Green)")
    
    print(f"DEBUG: Material '{material.name}' prepared for FBX export")

if __name__ == "__main__":
    print("DEBUG: merge.py main execution started")
    
    # Parse command line arguments
    args = parse()
    print(f"DEBUG: Parsed arguments: {args}")
    
    # Check if we have the required arguments for transfer function
    if args.source and args.target and args.output:
        print(f"DEBUG: Calling transfer function with source={args.source}, target={args.target}, output={args.output}, add_root={args.add_root}")
        try:
            transfer(args.source, args.target, args.output, args.add_root)
            print("DEBUG: Transfer function completed successfully")
        except Exception as e:
            print(f"ERROR: Transfer function failed: {e}")
            import traceback
            traceback.print_exc()
            exit(1)
    else:
        print(f"ERROR: Missing required arguments - source: {args.source}, target: {args.target}, output: {args.output}")
        exit(1)
    
    print("DEBUG: merge.py main execution completed")