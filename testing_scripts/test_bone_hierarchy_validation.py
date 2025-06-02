#!/usr/bin/env python3
"""
Test script to validate that bone hierarchy is preserved during texture preservation modifications.
This ensures the core functionality (skeleton and skinning weight prediction) remains intact.
"""

import os
import sys
import numpy as np
import bpy

# Add the src directory to Python path
sys.path.append('/app/src')

from inference.merge import process_merge_model, clean_bpy, load
from data.extract import process_mesh_for_merge, process_armature_for_merge, get_arranged_bones

def validate_bone_hierarchy(armature, expected_parents, expected_names):
    """Validate that bone hierarchy matches expected structure."""
    print(f"=== BONE HIERARCHY VALIDATION ===")
    
    # Switch to edit mode to access bone hierarchy
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='EDIT')
    
    edit_bones = armature.data.edit_bones
    bone_dict = {bone.name: bone for bone in edit_bones}
    
    hierarchy_intact = True
    
    for i, name in enumerate(expected_names):
        if name not in bone_dict:
            print(f"ERROR: Expected bone '{name}' not found in armature")
            hierarchy_intact = False
            continue
            
        bone = bone_dict[name]
        expected_parent_idx = expected_parents[i]
        expected_parent_name = expected_names[expected_parent_idx] if expected_parent_idx is not None else None
        
        actual_parent_name = bone.parent.name if bone.parent else None
        
        if actual_parent_name != expected_parent_name:
            print(f"ERROR: Bone '{name}' parent mismatch!")
            print(f"  Expected parent: {expected_parent_name}")
            print(f"  Actual parent: {actual_parent_name}")
            hierarchy_intact = False
        else:
            print(f"OK: Bone '{name}' -> parent: {expected_parent_name}")
    
    bpy.ops.object.mode_set(mode='OBJECT')
    
    return hierarchy_intact

def validate_skinning_weights(expected_skin_shape):
    """Validate that skinning weights are properly applied."""
    print(f"=== SKINNING WEIGHTS VALIDATION ===")
    
    total_vertices = 0
    total_weight_groups = 0
    
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            print(f"Mesh '{obj.name}':")
            print(f"  Vertices: {len(obj.data.vertices)}")
            print(f"  Vertex groups: {len(obj.vertex_groups)}")
            
            total_vertices += len(obj.data.vertices)
            total_weight_groups = len(obj.vertex_groups)
            
            # Check if vertices have weight assignments
            weighted_vertices = 0
            for vertex in obj.data.vertices:
                if len(vertex.groups) > 0:
                    weighted_vertices += 1
            
            print(f"  Weighted vertices: {weighted_vertices}/{len(obj.data.vertices)}")
            
            if weighted_vertices == 0:
                print(f"  WARNING: No vertices have skinning weights!")
                return False
    
    print(f"Total vertices across all meshes: {total_vertices}")
    print(f"Expected skin shape: {expected_skin_shape}")
    
    return True

def test_complete_pipeline_with_bone_validation():
    """Test the complete pipeline while validating bone hierarchy preservation."""
    
    # Test file paths
    test_input = "/app/examples/meshes/A_pose.glb"
    test_output = "/app/test_bone_validation_output"
    os.makedirs(test_output, exist_ok=True)
    
    if not os.path.exists(test_input):
        print(f"ERROR: Test input file not found: {test_input}")
        return False
    
    print(f"Testing bone hierarchy preservation with: {test_input}")
    
    try:
        # Step 1: Load and extract original data
        clean_bpy(preserve_textures=True)
        armature = load(filepath=test_input, return_armature=True)
        
        if armature is None:
            print("ERROR: Could not load armature from input file")
            return False
        
        print(f"Successfully loaded armature: {armature.name}")
        
        # Extract mesh and armature data
        vertices, faces = process_mesh_for_merge()
        arranged_bones = get_arranged_bones(armature)
        
        # Extract bone hierarchy information BEFORE processing
        joints, tails, parents, names, matrix_local = process_armature_for_merge(armature, arranged_bones)
        
        print(f"Original bone structure:")
        print(f"  Number of bones: {len(names)}")
        print(f"  Bone names: {names[:10]}...")  # Show first 10
        print(f"  Parent relationships: {parents[:10]}...")  # Show first 10
        
        # Extract skin weights
        from inference.merge import get_skin
        skin = get_skin(arranged_bones)
        print(f"Skin weights shape: {skin.shape}")
        
        # Step 2: Process through merge pipeline (this includes make_armature)
        output_file = os.path.join(test_output, "bone_validation_output.glb")
        
        result = process_merge_model(
            model_path=test_input,
            output_path=output_file,
            vertices=vertices,
            joints=joints,
            skin=skin,
            parents=parents,
            names=names,
            tails=tails,
            add_root=False,
            is_vrm=False
        )
        
        if not result:
            print("ERROR: Merge process failed")
            return False
        
        # Step 3: Validate output
        # Load the output file and check bone hierarchy
        clean_bpy(preserve_textures=True)
        output_armature = load(filepath=output_file, return_armature=True)
        
        if output_armature is None:
            print("ERROR: Could not load armature from output file")
            return False
        
        # Validate bone hierarchy preservation
        hierarchy_ok = validate_bone_hierarchy(output_armature, parents, names)
        
        # Validate skinning weights
        skinning_ok = validate_skinning_weights(skin.shape)
        
        # Step 4: Check material/texture preservation
        print(f"=== TEXTURE PRESERVATION VALIDATION ===")
        material_count = len(bpy.data.materials)
        image_count = len([img for img in bpy.data.images if img.name not in ['Render Result', 'Viewer Node']])
        
        print(f"Materials in output: {material_count}")
        print(f"Images in output: {image_count}")
        
        # Check if meshes have materials
        textured_meshes = 0
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and len(obj.material_slots) > 0:
                has_material = any(slot.material for slot in obj.material_slots)
                if has_material:
                    textured_meshes += 1
                    print(f"Mesh '{obj.name}' has materials")
        
        texture_ok = textured_meshes > 0
        
        # Final result
        all_tests_passed = hierarchy_ok and skinning_ok and texture_ok
        
        print(f"\n=== FINAL VALIDATION RESULTS ===")
        print(f"Bone hierarchy preserved: {'✓' if hierarchy_ok else '✗'}")
        print(f"Skinning weights applied: {'✓' if skinning_ok else '✗'}")
        print(f"Textures preserved: {'✓' if texture_ok else '✗'}")
        print(f"Overall result: {'✓ ALL TESTS PASSED' if all_tests_passed else '✗ SOME TESTS FAILED'}")
        
        return all_tests_passed
        
    except Exception as e:
        print(f"ERROR during pipeline test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Starting bone hierarchy validation test...")
    success = test_complete_pipeline_with_bone_validation()
    
    if success:
        print("\n🎉 SUCCESS: All core functionality preserved with texture enhancement!")
    else:
        print("\n❌ FAILURE: Core functionality compromised - need to fix implementation!")
    
    sys.exit(0 if success else 1)
