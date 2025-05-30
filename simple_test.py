import os
import sys

# Test file existence
files_to_check = [
    '/app/pipeline_work/01_extracted_mesh/bird/raw_data.npz',
    '/app/pipeline_work/01_extracted_mesh/bird/skeleton.fbx',
    '/app/pipeline_work/01_extracted_mesh/bird/skeleton_pred.txt',
    '/app/pipeline_work/01_extracted_mesh/bird/predict_skeleton.npz'
]

print("File existence check:")
for file_path in files_to_check:
    exists = os.path.exists(file_path)
    size = os.path.getsize(file_path) if exists else 0
    print(f"  {file_path}: {'EXISTS' if exists else 'MISSING'} ({size} bytes)")

# Test skeleton generation config
print("\nChecking skeleton config...")
sys.path.append('/app')

try:
    import app
    app.load_app_config()
    
    if app.APP_CONFIG is None:
        print("ERROR: APP_CONFIG is None after loading!")
    else:
        print(f"APP_CONFIG type: {type(app.APP_CONFIG)}")
        if hasattr(app.APP_CONFIG, 'skeleton_generation'):
            skeleton_config = app.APP_CONFIG.skeleton_generation
            print(f"  output_fbx_filename: '{skeleton_config.output_fbx_filename}'")
            print(f"  output_txt_filename: '{skeleton_config.output_txt_filename}'")
            print(f"  output_npz_filename: '{skeleton_config.output_npz_filename}'")
        else:
            print("ERROR: skeleton_generation not found in APP_CONFIG")
            print(f"Available keys: {list(app.APP_CONFIG.keys()) if app.APP_CONFIG else 'None'}")
    
except Exception as e:
    print(f"Error loading config: {e}")
    import traceback
    traceback.print_exc()

print("\nTest completed!")
