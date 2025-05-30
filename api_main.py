# /app/api_main.py
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
import shutil
import os
import tempfile
import subprocess # For running UniRig scripts

app = FastAPI()

# Temporary directory to store uploaded and processed files
# This should be persistent for the duration the container is running if files are large
# or processing takes time. Consider volume mapping for production.
TEMP_DIR_BASE = tempfile.mkdtemp(prefix="unirig_api_")
UPLOAD_DIR = os.path.join(TEMP_DIR_BASE, "uploads")
PROCESSED_DIR = os.path.join(TEMP_DIR_BASE, "processed")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

print(f"Temporary directories created: UPLOAD_DIR={UPLOAD_DIR}, PROCESSED_DIR={PROCESSED_DIR}")

@app.post("/rig_model/")
async def rig_model_endpoint(model_file: UploadFile = File(...)):
    uploaded_file_path = None
    processed_file_path = None # This will be the final rigged file
    
    try:
        original_filename = model_file.filename
        sanitized_filename = os.path.basename(original_filename) # Basic sanitization
        
        uploaded_file_path = os.path.join(UPLOAD_DIR, sanitized_filename)
        with open(uploaded_file_path, "wb") as buffer:
            shutil.copyfileobj(model_file.file, buffer)
        print(f"File '{sanitized_filename}' uploaded to '{uploaded_file_path}'")

        # --- UniRig Processing Steps ---
        # These paths assume the UniRig scripts are in /app/launch/inference/
        # and the input/output are relative or absolute paths accessible by the container.
        
        # 1. Skeleton Prediction
        skeleton_output_filename = f"skel_{sanitized_filename.rsplit('.',1)[0]}.fbx" # UniRig often outputs FBX
        skeleton_output_path = os.path.join(PROCESSED_DIR, skeleton_output_filename)
        
        skeleton_cmd = [
            "bash", "/app/launch/inference/generate_skeleton.sh",
            "--input", uploaded_file_path,
            "--output", skeleton_output_path
        ]
        print(f"Running skeleton command: {' '.join(skeleton_cmd)}")
        process_skel = subprocess.run(skeleton_cmd, capture_output=True, text=True, check=False)
        
        if process_skel.returncode != 0:
            print(f"Skeleton Prediction Error Output: {process_skel.stderr}")
            print(f"Skeleton Prediction Stdout: {process_skel.stdout}")
            raise HTTPException(status_code=500, detail=f"Skeleton prediction failed: {process_skel.stderr or process_skel.stdout}")
        print(f"Skeleton prediction stdout: {process_skel.stdout}")
        if not os.path.exists(skeleton_output_path):
             raise HTTPException(status_code=500, detail=f"Skeleton output file not found: {skeleton_output_path}")


        # 2. Skinning Weight Prediction
        # Input for skinning is often the skeleton FBX, but UniRig's script might take the original mesh
        # and the predicted skeleton separately or a merged file.
        # This example assumes generate_skin.sh takes the skeletonized FBX as input.
        # Adjust according to UniRig's actual script requirements.
        # The output of skinning might be another FBX or the final rigged GLB/FBX.
        
        # For UniRig, merge.sh is typically used after skeleton and skin prediction.
        # Let's assume generate_skin.sh produces a skinned FBX using the skeleton.
        # The `merge.sh` script is more likely to be the final step.

        # Let's simplify: Assume skeleton.sh gives a rigged FBX or GLB directly for now,
        # or that the user will perform skinning/merging as a separate step if needed,
        # or that generate_skeleton.sh already produces a somewhat usable rigged model.
        # For a full pipeline, you'd chain generate_skeleton, generate_skin, and merge.

        # For this example, we'll assume the skeleton_output_path is the file to be returned.
        # In a more complete implementation, you would call generate_skin.sh and merge.sh here.
        # Example for skinning (conceptual):
        # skin_output_filename = f"skin_{sanitized_filename.rsplit('.',1)[0]}.fbx"
        # skin_output_path = os.path.join(PROCESSED_DIR, skin_output_filename)
        # skin_cmd = [
        #     "bash", "/app/launch/inference/generate_skin.sh",
        #     "--input", skeleton_output_path, # This might need the original mesh too
        #     "--output", skin_output_path
        # ]
        # print(f"Running skin command: {' '.join(skin_cmd)}")
        # process_skin = subprocess.run(skin_cmd, capture_output=True, text=True, check=False)
        # if process_skin.returncode != 0:
        #     print(f"Skinning Error Output: {process_skin.stderr}")
        #     raise HTTPException(status_code=500, detail=f"Skinning failed: {process_skin.stderr}")
        # print(f"Skinning stdout: {process_skin.stdout}")
        #
        # final_rigged_filename = f"rigged_{sanitized_filename}"
        # final_rigged_path = os.path.join(PROCESSED_DIR, final_rigged_filename)
        # merge_cmd = [
        #    "bash", "/app/launch/inference/merge.sh",
        #    "--source", skin_output_path, # or skeleton_output_path if skinning is part of it
        #    "--target", uploaded_file_path, # Original geometry
        #    "--output", final_rigged_path
        # ]
        # print(f"Running merge command: {' '.join(merge_cmd)}")
        # process_merge = subprocess.run(merge_cmd, capture_output=True, text=True, check=False)
        # if process_merge.returncode != 0:
        #    print(f"Merge Error Output: {process_merge.stderr}")
        #    raise HTTPException(status_code=500, detail=f"Merging failed: {process_merge.stderr}")
        # print(f"Merge stdout: {process_merge.stdout}")
        # processed_file_path = final_rigged_path
        
        # Simplified: returning the direct output of generate_skeleton.sh
        processed_file_path = skeleton_output_path
        final_return_filename = skeleton_output_filename
        # --- End UniRig Processing ---

        if not os.path.exists(processed_file_path):
            raise HTTPException(status_code=500, detail=f"Processed file not found after UniRig execution: {processed_file_path}")

        media_type = 'model/gltf-binary' if final_return_filename.lower().endswith('.glb') else 'application/octet-stream'

        return FileResponse(
            path=processed_file_path,
            filename=final_return_filename,
            media_type=media_type
        )
    except HTTPException:
        raise # Re-raise HTTPException so FastAPI handles it
    except Exception as e:
        print(f"Error in /rig_model/ endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
    finally:
        # Clean up uploaded file to save space, processed file is handled by FileResponse
        if uploaded_file_path and os.path.exists(uploaded_file_path):
            try:
                os.remove(uploaded_file_path)
                print(f"Cleaned up uploaded file: {uploaded_file_path}")
            except OSError as e:
                print(f"Error cleaning up uploaded file {uploaded_file_path}: {e}")
        # Note: TEMP_DIR_BASE and its subdirectories (PROCESSED_DIR) are not cleaned up here.
        # For a production server, a strategy for cleaning PROCESSED_DIR would be needed.
        pass

@app.get("/")
async def root():
    return {"message": "UniRig API is running. Use POST /rig_model/ to process models."}

# To run this app (from the /app directory inside the container, or locally for testing):
# Ensure UniRig environment is activated if running locally: conda activate UniRig
# uvicorn api_main:app --host 0.0.0.0 --port 8000 --reload (for development)
