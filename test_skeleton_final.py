#!/usr/bin/env python3

import sys
import os
sys.path.append('/app')

import app

def dummy_progress(fraction, desc=''):
    print(f'Progress: {fraction:.1%} - {desc}')

def main():
    # Load configuration
    print("Loading configuration...")
    app.load_app_config()
    
    # Test parameters
    extracted_npz_path = '/app/pipeline_work/01_extracted_mesh/bird/raw_data.npz'
    model_name = 'bird'
    gender = 'neutral'
    
    print(f"Testing skeleton generation for {model_name} (gender: {gender})")
    print(f"Input NPZ: {extracted_npz_path}")
    print(f"NPZ exists: {os.path.exists(extracted_npz_path)}")
    print()
    
    # Run skeleton generation
    print("Starting skeleton generation...")
    result = app.process_generate_skeleton(extracted_npz_path, model_name, gender, dummy_progress)
    
    if result is None:
        print("ERROR: Skeleton generation returned None")
        return
    
    display_glb_path, logs, fbx_path, txt_path, npz_path = result
    
    print('\n' + '='*50)
    print('SKELETON GENERATION RESULTS')
    print('='*50)
    print(f'Display GLB: {display_glb_path}')
    print(f'FBX Path: {fbx_path}')
    print(f'TXT Path: {txt_path}')
    print(f'NPZ Path: {npz_path}')
    
    # Check if files exist
    files_to_check = [
        ('Display GLB', display_glb_path),
        ('FBX', fbx_path),
        ('TXT', txt_path),
        ('NPZ', npz_path)
    ]
    
    print('\nFile verification:')
    for file_type, file_path in files_to_check:
        if file_path:
            exists = os.path.exists(file_path)
            size = os.path.getsize(file_path) if exists else 0
            print(f'  {file_type}: {"EXISTS" if exists else "MISSING"} ({size} bytes)')
        else:
            print(f'  {file_type}: None')
    
    print('\n' + '='*50)
    print('DETAILED LOGS')
    print('='*50)
    print(logs)

if __name__ == "__main__":
    main()
