#!/usr/bin/env python3
"""
FBX to GLB converter using Blender
Based on https://qiita.com/y-okamon/items/179f74cf86da40b7cba1
and https://github.com/KhronosGroup/glTF-Tutorials/blob/main/BlenderGltfConverter/blender_gltf_converter.py
"""

import bpy
import sys
import os
import argparse

def clear_scene():
    """Clear all objects from the scene"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False, confirm=False)

def convert_fbx_to_glb(input_path, output_path=None):
    """
    Convert FBX file to GLB format
    
    Args:
        input_path (str): Path to input FBX file
        output_path (str): Path for output GLB file (optional)
    """
    if not os.path.exists(input_path):
        print(f"Error: Input file does not exist: {input_path}")
        return False
    
    if not input_path.lower().endswith('.fbx'):
        print(f"Error: Input file is not an FBX file: {input_path}")
        return False
    
    # Clear the scene
    clear_scene()
    
    try:
        # Import FBX file
        print(f"Importing FBX file: {input_path}")
        bpy.ops.import_scene.fbx(filepath=input_path)
        
        # Determine output path
        if output_path is None:
            output_path = input_path.replace(".fbx", ".glb")
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # Export as GLB with embedded textures
        print(f"Exporting GLB file: {output_path}")
        bpy.ops.export_scene.gltf(
            filepath=output_path,
            export_format='GLB',
            # Material settings
            export_materials='EXPORT',  # Export materials with textures
            # Image/texture settings (Blender 4.2 compatible)
            export_image_format='AUTO',  # Use original format when possible
            # Mesh settings
            export_normals=True,
            export_tangents=False,
            # Note: export_tex_coords removed - not available in Blender 4.2
            # UV coordinates are automatically exported with materials
            # Animation settings
            export_animations=True,  # Keep animations from FBX
            export_frame_range=False
        )
        
        print(f"Successfully converted {input_path} to {output_path}")
        return True
        
    except Exception as e:
        print(f"Error during conversion: {str(e)}")
        return False

def main():
    """Main function for command line usage"""
    # Parse arguments (skip Blender's arguments)
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    
    # Handle both named arguments (--input, --output) and positional arguments
    parser = argparse.ArgumentParser(description='Convert FBX to GLB using Blender')
    parser.add_argument('--input', help='Input FBX file path')
    parser.add_argument('--output', help='Output GLB file path (optional)')
    # Also support positional arguments for backward compatibility
    parser.add_argument('positional', nargs='*', help='Positional arguments: input_fbx [output_glb]')
    
    try:
        args = parser.parse_args(argv)
        
        # Determine input and output paths
        if args.input:
            input_path = args.input
            output_path = args.output
        elif args.positional and len(args.positional) >= 1:
            input_path = args.positional[0]
            output_path = args.positional[1] if len(args.positional) > 1 else None
        else:
            print("Error: No input file specified")
            print("Usage: blender --background --python fbx_to_glb_converter.py -- --input <input_fbx> --output <output_glb>")
            print("   or: blender --background --python fbx_to_glb_converter.py -- <input_fbx> [output_glb]")
            return
            
    except SystemExit:
        print("Error: Invalid arguments")
        print("Usage: blender --background --python fbx_to_glb_converter.py -- --input <input_fbx> --output <output_glb>")
        print("   or: blender --background --python fbx_to_glb_converter.py -- <input_fbx> [output_glb]")
        return
    
    success = convert_fbx_to_glb(input_path, output_path)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
