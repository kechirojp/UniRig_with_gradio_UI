# This application uses UniRig (https://github.com/VAST-AI-Research/UniRig),
# which is licensed under the MIT License.
# A copy of the license can be found at:
# https://github.com/VAST-AI-Research/UniRig/blob/main/LICENSE
#
# Gradio application for 3D model preview and bone information display.

import gradio as gr
import os
import shutil
import subprocess
import tempfile
import time # クリーンアップ処理で使用
import signal # クリーンアップ処理で使用
import atexit # クリーンアップ処理で使用
from tqdm import tqdm #進捗表示用
import trimesh # 追加
import datetime # 追加
import traceback # エラーハンドリング用に追加

# 定数
GRADIO_TEMP_DIR = os.path.join(os.path.dirname(__file__), "gradio_tmp_files")

# --- グローバル変数とクリーンアップ関数 ---
TEMP_FILES_TO_CLEAN = [] 

def add_to_cleanup_list(path):
    if path and path not in TEMP_FILES_TO_CLEAN:
        print(f"クリーンアップリストに追加: {path}")
        TEMP_FILES_TO_CLEAN.append(path)

def cleanup_temp_files():
    print("一時ファイルのクリーンアップを開始...")
    paths_to_remove = list(TEMP_FILES_TO_CLEAN)
    TEMP_FILES_TO_CLEAN.clear() 

    for path in paths_to_remove:
        try:
            if os.path.isfile(path):
                os.remove(path)
                print(f"一時ファイル {path} を削除しました。")
            elif os.path.isdir(path):
                shutil.rmtree(path)
                print(f"一時ディレクトリ {path} を削除しました。")
        except Exception as e:
            print(f"一時ファイル/ディレクトリ {path} の削除中にエラー: {e}")
    print("一時ファイルのクリーンアップが完了しました。")

atexit.register(cleanup_temp_files)


# --- ヘルパー関数 ---
def run_script(command_parts: list[str], working_dir: str | None = None) -> tuple[bool, str]:
    full_command = " ".join(command_parts)
    log_message = f"Executing: {full_command}\\n"
    try:
        process = subprocess.Popen(command_parts, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=working_dir)
        output = []
        if process.stdout:
            for line in iter(process.stdout.readline, ''):
                print(line, end='') # Print to console in real-time
                output.append(line)
        process.wait()
        return_code = process.returncode
        
        log_message += "".join(output)
        if return_code == 0:
            log_message += "Script executed successfully.\\n"
            return True, log_message
        else:
            log_message += f"Script failed with return code {return_code}.\\n"
            return False, log_message
    except Exception as e:
        error_info = traceback.format_exc()
        log_message += f"Error running script: {e}\\n{error_info}\\n"
        print(log_message)
        return False, log_message

# Helper function for progress updates in sequential pipeline
def progress_segment(progress_obj: gr.Progress | None, start_fraction: float, end_fraction: float):
    if progress_obj is None:
        # Return a dummy callable if no progress object is provided
        return lambda value, desc="": None

    def new_progress_tracker(value, desc=""):
        mapped_value = start_fraction + (value * (end_fraction - start_fraction))
        progress_obj(mapped_value, desc=desc)
    
    class SegmentedProgress:
        def __init__(self, tracker_fn):
            self.tracker_fn = tracker_fn
        def __call__(self, value, desc=""):
            self.tracker_fn(value, desc)
    return SegmentedProgress(new_progress_tracker)

# --- Skeleton Generation ---
def process_generate_skeleton(
    original_model_path: str,
    motion_sequence_path: str | None,
    person_measurements_path: str | None,
    gender: str,
    progress: gr.Progress | None = None,
):
    if progress:
        progress(0, desc="準備中...")
    logs = f"スケルトン生成開始: {datetime.datetime.now()}\\n"
    logs += f"入力モデル: {original_model_path}\\n"
    
    skeleton_fbx_path = None # Rigged model (mesh + skeleton)
    skeleton_txt_path = None # Skeleton prediction text file
    display_model_glb_path = None # For Gradio display

    if not original_model_path or not os.path.exists(original_model_path):
        return None, logs + "エラー: オリジナルモデルのパスが無効です。", None, None

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    script_path = os.path.join(base_dir, "launch/inference/generate_skeleton.sh")

    if not os.path.exists(script_path):
        return None, logs + f"エラー: スケルトン生成スクリプトが見つかりません: {script_path}", None, None

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_model_name = os.path.splitext(os.path.basename(original_model_path))[0]
    
    # Create a unique temporary directory for this operation's inputs and outputs
    operation_temp_dir = tempfile.mkdtemp(prefix=f"unirig_skel_{base_model_name}_{timestamp}_")
    add_to_cleanup_list(operation_temp_dir)
    logs += f"スケルトン生成用一時ディレクトリ: {operation_temp_dir}\\\\n"

    # Prepare input and output subdirectories within the operation_temp_dir
    input_dir_for_script = os.path.join(operation_temp_dir, "input")
    output_dir_for_script = os.path.join(operation_temp_dir, "output")
    os.makedirs(input_dir_for_script, exist_ok=True)
    os.makedirs(output_dir_for_script, exist_ok=True)

    # Copy the input model to the script's input directory
    # The script expects the model to be in a subdirectory named after the model itself
    model_specific_input_dir = os.path.join(input_dir_for_script, base_model_name)
    os.makedirs(model_specific_input_dir, exist_ok=True)
    temp_model_path = os.path.join(model_specific_input_dir, os.path.basename(original_model_path))
    shutil.copy(original_model_path, temp_model_path)
    logs += f"一時入力モデル: {temp_model_path}\\\\n"

    cmd = [
        "bash", script_path,
        "--input_model_dir", input_dir_for_script, # Directory containing base_model_name/model.fbx
        "--output_dir", output_dir_for_script,    # Directory where base_model_name/skeleton.fbx etc. will be saved
        "--data_name", base_model_name,           # Name of the model (used for subdirectories)
        "--gender", gender if gender else "neutral" # Pass gender
    ]
    # Add optional motion and measurement files if provided
    # These need to be copied to the input_dir_for_script as well, and paths adjusted
    if motion_sequence_path and os.path.exists(motion_sequence_path):
        temp_motion_path = os.path.join(input_dir_for_script, base_model_name, os.path.basename(motion_sequence_path))
        shutil.copy(motion_sequence_path, temp_motion_path)
        cmd.extend(["--motion_sequence_path", temp_motion_path])
        logs += f"モーションシーケンス使用: {temp_motion_path}\\\\n"

    if person_measurements_path and os.path.exists(person_measurements_path):
        temp_measurements_path = os.path.join(input_dir_for_script, base_model_name, os.path.basename(person_measurements_path))
        shutil.copy(person_measurements_path, temp_measurements_path)
        cmd.extend(["--person_measurements_path", temp_measurements_path])
        logs += f"身体測定ファイル使用: {temp_measurements_path}\\\\n"

    if progress:
        progress(0.2, desc="スケルトン生成スクリプト実行中...")
    
    success, script_logs = run_script(cmd, base_dir) # Run from /app
    logs += script_logs

    if not success:
        return None, logs, None, None

    # Expected output paths (relative to output_dir_for_script/base_model_name)
    expected_output_subdir = os.path.join(output_dir_for_script, base_model_name)
    
    # 1. Rigged model (mesh + skeleton): skeleton.fbx
    # This is the primary output for rigging.
    potential_skeleton_fbx = os.path.join(expected_output_subdir, "skeleton.fbx")
    if os.path.exists(potential_skeleton_fbx):
        # Copy to a persistent temp location for Gradio download
        persistent_skel_fbx_name = f"{base_model_name}_skeleton_rigged.fbx"
        skeleton_fbx_path = os.path.join(GRADIO_TEMP_DIR, persistent_skel_fbx_name)
        shutil.copy(potential_skeleton_fbx, skeleton_fbx_path)
        add_to_cleanup_list(skeleton_fbx_path)
        logs += f"リグ付きモデル (FBX): {skeleton_fbx_path}\\\\n"
        
        # Convert this FBX to GLB for display
        if progress:
            progress(0.8, desc="表示用に変換中...")
        display_model_glb_path = convert_to_glb_for_display(skeleton_fbx_path, f"{base_model_name}_skeleton_display")
        if display_model_glb_path:
            logs += f"表示用モデル (GLB): {display_model_glb_path}\\\\n"
        else:
            logs += "警告: 表示用GLBへの変換に失敗しました。FBXを直接返します。\n"
            # display_model_glb_path = skeleton_fbx_path # Fallback, Model3D might handle FBX
    else:
        logs += f"エラー: 期待されたリグ付きモデル {potential_skeleton_fbx} が見つかりません。\n"

    # 2. Skeleton prediction text file: skeleton_pred.txt
    potential_skeleton_txt = os.path.join(expected_output_subdir, "skeleton_pred.txt")
    if os.path.exists(potential_skeleton_txt):
        persistent_skel_txt_name = f"{base_model_name}_skeleton_pred.txt"
        skeleton_txt_path = os.path.join(GRADIO_TEMP_DIR, persistent_skel_txt_name)
        shutil.copy(potential_skeleton_txt, skeleton_txt_path)
        add_to_cleanup_list(skeleton_txt_path)
        logs += f"スケルトン予測ファイル (txt): {skeleton_txt_path}\\\\n"
    else:
        logs += f"エラー: 期待されたスケルトン予測ファイル {potential_skeleton_txt} が見つかりません。\n"

    if not skeleton_fbx_path and not skeleton_txt_path: # If neither critical output is found
        logs += "エラー: スケルトン生成スクリプトは成功しましたが、主要な出力ファイルが見つかりませんでした。\n"
        # Log contents of output directory for debugging
        logs += f"スクリプト出力ディレクトリの内容 ({expected_output_subdir}):\\n"
        if os.path.exists(expected_output_subdir):
            for item in os.listdir(expected_output_subdir):
                logs += f"  - {item}\\n"
        else:
            logs += "  (出力サブディレクトリが存在しません)\\n"
        return None, logs, None, None # Critical failure

    if progress:
        progress(1, desc="スケルトン生成完了")
    logs += "スケルトン生成処理が正常に完了しました。\n"
    return display_model_glb_path, logs, skeleton_fbx_path, skeleton_txt_path


def gradio_generate_skeleton(
    original_model_file_obj: tempfile._TemporaryFileWrapper | None,
    motion_sequence_file_obj: tempfile._TemporaryFileWrapper | None,
    person_measurements_file_obj: tempfile._TemporaryFileWrapper | None,
    gender: str,
    progress=gr.Progress(track_tqdm=True)
):
    if original_model_file_obj is None:
        return None, "オリジナルモデルをアップロードしてください。", None, None

    original_model_path = original_model_file_obj.name
    motion_sequence_path = motion_sequence_file_obj.name if motion_sequence_file_obj else None
    person_measurements_path = person_measurements_file_obj.name if person_measurements_file_obj else None
    
    progress(0, desc="スケルトン生成準備中...")
    
    display_model_path, logs, skeleton_fbx_download_path, skeleton_txt_download_path = process_generate_skeleton(
        original_model_path,
        motion_sequence_path,
        person_measurements_path,
        gender,
        progress
    )
    progress(1, desc="スケルトン生成完了")

    return display_model_path, logs, skeleton_fbx_download_path, skeleton_txt_download_path

# --- Skinning Weight Prediction ---
def process_generate_skin(
    original_model_path: str, 
    skeleton_text_path: str, 
    progress: gr.Progress | None = None
):
    if progress:
        progress(0, desc="準備中...")
    logs = f"スキニング処理開始: {datetime.datetime.now()}\\n"
    logs += f"入力モデル: {original_model_path}\\n"
    logs += f"スケルトンファイル: {skeleton_text_path}\\n"

    skinned_model_downloadable_path = None # Final path for download (GLB or FBX)
    display_model_path_glb = None      # GLB path for display

    if not original_model_path or not os.path.exists(original_model_path):
        return None, logs + "エラー: オリジナルモデルのパスが無効です。", None
    if not skeleton_text_path or not os.path.exists(skeleton_text_path):
        return None, logs + "エラー: スケルトン予測テキストファイルのパスが無効です。", None
    
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    script_path = os.path.join(base_dir, "launch/inference/generate_skin.sh")
    if not os.path.exists(script_path):
        return None, logs + f"エラー: スキニング生成スクリプトが見つかりません: {script_path}", None

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_original_model_name = os.path.splitext(os.path.basename(original_model_path))[0]
    
    operation_temp_dir = tempfile.mkdtemp(prefix=f"unirig_skin_{base_original_model_name}_{timestamp}_")
    add_to_cleanup_list(operation_temp_dir)
    logs += f"スキニング用一時ディレクトリ: {operation_temp_dir}\\\\n"

    # Script's input structure:
    # input_model_dir/data_name/model.fbx (or other format)
    # input_model_dir/data_name/skeleton_pred.txt
    # output_dir/ (script will create data_name subdir here)
    # npz_dir/ (script will create data_name subdir here)

    script_input_dir = os.path.join(operation_temp_dir, "input_for_script")
    model_specific_input_subdir = os.path.join(script_input_dir, base_original_model_name)
    os.makedirs(model_specific_input_subdir, exist_ok=True)

    script_output_dir = os.path.join(operation_temp_dir, "output_from_script")
    os.makedirs(script_output_dir, exist_ok=True)
    
    script_npz_dir = os.path.join(operation_temp_dir, "npz_from_script")
    os.makedirs(script_npz_dir, exist_ok=True)

    # Copy original model and skeleton_pred.txt into model_specific_input_subdir
    temp_input_model_path = os.path.join(model_specific_input_subdir, os.path.basename(original_model_path))
    shutil.copy(original_model_path, temp_input_model_path)
    logs += f"一時入力モデル (スキニング用): {temp_input_model_path}\\\\n"

    temp_skeleton_txt_path = os.path.join(model_specific_input_subdir, os.path.basename(skeleton_text_path))
    shutil.copy(skeleton_text_path, temp_skeleton_txt_path)
    logs += f"一時スケルトンファイル (スキニング用): {temp_skeleton_txt_path}\\\\n"

    cmd = [
        "bash", script_path,
        "--input_model_dir", script_input_dir, # Contains base_original_model_name/
        "--output_dir", script_output_dir,
        "--npz_dir", script_npz_dir,
        "--data_name", base_original_model_name,
        "--force_override_npz", "True" # Or make this configurable
    ]

    if progress:
        progress(0.2, desc="スキニングスクリプト実行中...")
    
    success, script_logs = run_script(cmd, base_dir) # Run from /app
    logs += script_logs

    if not success:
        return None, logs, None

    # Expected output: script_output_dir/base_original_model_name/skinned_mesh.glb (or .fbx)
    expected_skinned_output_subdir = os.path.join(script_output_dir, base_original_model_name)
    
    found_skinned_model_path = None
    possible_skinned_outputs = ["skinned_mesh.glb", "skinned_mesh.fbx"] # Check GLB first
    
    for fname in possible_skinned_outputs:
        path_to_check = os.path.join(expected_skinned_output_subdir, fname)
        if os.path.exists(path_to_check):
            found_skinned_model_path = path_to_check
            logs += f"スキニング済みモデル発見: {found_skinned_model_path}\\\\n"
            break
            
    if not found_skinned_model_path:
        logs += f"エラー: スキニング済みモデルが期待される場所に見つかりませんでした ({expected_skinned_output_subdir})。\n"
        logs += f"スクリプト出力ディレクトリの内容 ({expected_skinned_output_subdir}):\\n"
        if os.path.exists(expected_skinned_output_subdir):
            for item in os.listdir(expected_skinned_output_subdir):
                logs += f"  - {item}\n"
        else:
            logs += "  (出力サブディレクトリが存在しません)\\n"
        return None, logs, None

    # Copy to persistent temp location for Gradio download and display
    persistent_skinned_model_basename = f"{base_original_model_name}_skinned{os.path.splitext(found_skinned_model_path)[1]}"
    skinned_model_downloadable_path = os.path.join(GRADIO_TEMP_DIR, persistent_skinned_model_basename)
    shutil.copy(found_skinned_model_path, skinned_model_downloadable_path)
    add_to_cleanup_list(skinned_model_downloadable_path)
    logs += f"ダウンロード用スキニング済みモデル: {skinned_model_downloadable_path}\\\\n"

    if progress:
        progress(0.8, desc="表示用に変換中...")
    display_model_path_glb = convert_to_glb_for_display(skinned_model_downloadable_path, f"{base_original_model_name}_skinned_display")
    if display_model_path_glb:
        logs += f"表示用スキニング済みモデル (GLB): {display_model_path_glb}\\\\n"
    else:
        logs += "警告: 表示用GLBへの変換に失敗しました。\n"

    if progress:
        progress(1, desc="スキニング完了")
    logs += "スキニング処理正常終了\\n"
    return display_model_path_glb, logs, skinned_model_downloadable_path


def gradio_generate_skin(
    original_model_file_obj: tempfile._TemporaryFileWrapper | None, 
    skeleton_text_file_obj: tempfile._TemporaryFileWrapper | None, 
    progress=gr.Progress(track_tqdm=True)
):
    if original_model_file_obj is None or skeleton_text_file_obj is None:
        return None, "オリジナルモデルとスケルトン予測テキストファイルの両方をアップロードしてください。", None

    original_model_path = original_model_file_obj.name
    skeleton_text_path = skeleton_text_file_obj.name
    
    progress(0, desc="スキニング処理準備中...")
    display_model_path, logs, skinned_model_download_path = process_generate_skin(
        original_model_path, skeleton_text_path, progress
    )
    progress(1, desc="スキニング完了")
    
    return display_model_path, logs, skinned_model_download_path

# --- Merge Model ---
def process_merge_model(
    target_model_path: str,
    source_rig_model_path: str,
    progress: gr.Progress | None = None,
):
    if progress:
        progress(0, desc="準備中...")
    logs = f"マージ処理開始: {datetime.datetime.now()}\\n"
    print(f"Merge: Target model: {target_model_path}")
    print(f"Merge: Source rig model: {source_rig_model_path}")

    if not target_model_path or not os.path.exists(target_model_path):
        return None, logs + "ターゲットモデルのパスが無効です。", None
    if not source_rig_model_path or not os.path.exists(source_rig_model_path):
        return None, logs + "ソースリグモデルのパスが無効です。", None

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    merge_script_path = os.path.join(base_dir, "launch/inference/merge.sh")
    if not os.path.exists(merge_script_path):
        return None, logs + f"エラー: マージスクリプトが見つかりません: {merge_script_path}", None

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_target_name = os.path.splitext(os.path.basename(target_model_path))[0]
    base_source_name = os.path.splitext(os.path.basename(source_rig_model_path))[0]

    operation_temp_dir = tempfile.mkdtemp(prefix=f"unirig_merge_{base_target_name}_{base_source_name}_{timestamp}_")
    add_to_cleanup_list(operation_temp_dir)
    logs += f"マージ用一時ディレクトリ: {operation_temp_dir}\\\\n"
    
    input_dir = os.path.join(operation_temp_dir, "inputs") # Script doesn't use subdirs for inputs
    output_dir_for_script = os.path.join(operation_temp_dir, "outputs") # Script will create output here
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir_for_script, exist_ok=True)

    temp_target_model_path = os.path.join(input_dir, f"target_{os.path.basename(target_model_path)}")
    shutil.copy(target_model_path, temp_target_model_path)
    logs += f"一時ターゲットモデル: {temp_target_model_path}\\\\n"
    
    temp_source_rig_model_path = os.path.join(input_dir, f"source_{os.path.basename(source_rig_model_path)}")
    shutil.copy(source_rig_model_path, temp_source_rig_model_path)
    logs += f"一時ソースリグモデル: {temp_source_rig_model_path}\\\\n"

    if progress:
        progress(0.2, desc="マージスクリプトを実行中...")
    
    cmd = [
        "bash", merge_script_path,
        "--source", temp_source_rig_model_path, # This is the rigged low-poly or skinned model
        "--target", temp_target_model_path,     # This is the original high-poly model
        "--output", output_dir_for_script       # Directory where merged output will be saved
    ]
    
    logs += f"コマンドを実行中: {' '.join(cmd)}\\n"
    success, script_output = run_script(cmd, base_dir) # Run from /app
    logs += script_output

    if not success:
        error_msg = f"マージスクリプトの実行に失敗しました。\\n" # 修正箇所
        error_msg += f"一時ディレクトリの内容 ({operation_temp_dir}):\\n"
        for root_dir, _, files_in_dir in os.walk(operation_temp_dir):
            for name in files_in_dir:
                error_msg += f"  {os.path.join(root_dir, name)}\\n"
        print(error_msg)
        return None, logs + "\\n" + error_msg, None

    if progress:
        progress(0.8, desc="出力ファイルを検索中...")
    
    # The script `src.inference.merge.py` saves output as `f"{output_dir}/{data_name}_merged.fbx"`
    # where data_name is derived from the source file's name (without extension).
    # The shell script passes `output_dir_for_script` as the base output.
    # The python script then creates `output_dir_for_script/source_basename_merged.fbx`
    
    source_basename_for_output = os.path.splitext(os.path.basename(temp_source_rig_model_path))[0]
    # The merge.py script seems to use the original name of the source passed to it.
    # Our temp_source_rig_model_path is like "source_originalbasename.fbx".
    # So, the output would be "output_dir_for_script/source_character_merged.fbx"

    expected_merged_fbx_name = f"{source_basename_for_output}_merged.fbx" # e.g. source_mymodel_merged.fbx
    expected_merged_glb_name = f"{source_basename_for_output}_merged.glb"
    
    merged_model_path_from_script = None
    
    # Check for GLB first, then FBX
    path_check_glb = os.path.join(output_dir_for_script, expected_merged_glb_name)
    path_check_fbx = os.path.join(output_dir_for_script, expected_merged_fbx_name)

    if os.path.exists(path_check_glb):
        merged_model_path_from_script = path_check_glb
    elif os.path.exists(path_check_fbx):
        merged_model_path_from_script = path_check_fbx
    else:
        # Fallback: list directory if specific name not found
        logs += f"エラー: 期待されたマージ済みモデル ({expected_merged_glb_name} または {expected_merged_fbx_name}) が出力ディレクトリに見つかりませんでした。\n"
        logs += f"出力ディレクトリ ({output_dir_for_script}) の内容:\n"
        if os.path.exists(output_dir_for_script):
            for item in os.listdir(output_dir_for_script):
                logs += f"  - {item}\n"
                # If we find *any* _merged.fbx or _merged.glb, let's try to use it.
                if "_merged.fbx" in item.lower() or "_merged.glb" in item.lower():
                    if not merged_model_path_from_script: # Take the first one found
                         merged_model_path_from_script = os.path.join(output_dir_for_script, item)
                         logs += f"代替のマージ済みモデル候補を発見: {merged_model_path_from_script}\n"
        else:
            logs += "  (出力ディレクトリが存在しません)\n"
        
        if not merged_model_path_from_script: # Still not found
            print(logs)
            return None, logs, None

    logs += f"マージされたモデルを発見: {merged_model_path_from_script}\\\\n"
    
    # Copy to a persistent location for Gradio
    final_merged_model_basename = f"{base_target_name}_final_merged{os.path.splitext(merged_model_path_from_script)[1]}"
    persistent_merged_model_path = os.path.join(GRADIO_TEMP_DIR, final_merged_model_basename)
    shutil.copy(merged_model_path_from_script, persistent_merged_model_path)
    add_to_cleanup_list(persistent_merged_model_path)
    logs += f"ダウンロード用マージ済みモデル: {persistent_merged_model_path}\\\\n"

    if progress:
        progress(0.9, desc="表示用に変換中...")
    
    merged_model_glb_path_for_display = convert_to_glb_for_display(persistent_merged_model_path, f"{base_target_name}_merged_display")
    
    if not merged_model_glb_path_for_display:
        logs += "エラー: マージされたモデルをGLBに変換できませんでした。\n"
        # Return original persistent path if conversion fails, Model3D might handle it or user can download
        # return None, logs, persistent_merged_model_path 
    else:
         logs += f"表示用マージ済みモデル (GLB): {merged_model_glb_path_for_display}\\\\n"


    if progress:
        progress(1, desc="完了")
    
    logs += "マージ処理が正常に完了しました。"
    return merged_model_glb_path_for_display, logs, persistent_merged_model_path

def gradio_merge_model(
    target_model_file_obj: tempfile._TemporaryFileWrapper | None,
    source_rig_model_file_obj: tempfile._TemporaryFileWrapper | None,
    progress=gr.Progress(track_tqdm=True)
):
    if not target_model_file_obj or not source_rig_model_file_obj:
        return None, "ターゲットモデルとソースリグモデルの両方をアップロードしてください。", None

    target_model_path = target_model_file_obj.name
    source_rig_model_path = source_rig_model_file_obj.name
    
    progress(0, desc="マージ処理準備中...")
    display_path, logs, download_path = process_merge_model(
        target_model_path,
        source_rig_model_path,
        progress
    )
    progress(1, desc="マージ完了")
    return display_path, logs, download_path

# --- Full Rigging Pipeline ---
def run_full_pipeline_sequential(
    original_model_file: tempfile._TemporaryFileWrapper | None,
    motion_sequence_file: tempfile._TemporaryFileWrapper | None,
    person_measurements_file: tempfile._TemporaryFileWrapper | None,
    gender: str,
    progress=gr.Progress(track_tqdm=True),
):
    # Initialize all output paths to None
    skeleton_glb_path, skeleton_logs, skeleton_fbx_path, skeleton_txt_path = None, "", None, None
    skinned_model_glb_path, skinning_logs, downloadable_skinned_model_path = None, "", None
    merged_model_glb_path, merge_logs, downloadable_merged_model_path = None, "", None
    final_log_message = ""

    if not original_model_file:
        final_log_message = "オリジナルモデルをアップロードしてください。"
        return (
            skeleton_glb_path, skeleton_logs, skeleton_fbx_path, skeleton_txt_path,
            skinned_model_glb_path, skinning_logs, downloadable_skinned_model_path,
            merged_model_glb_path, merge_logs, downloadable_merged_model_path,
            final_log_message
        )
    
    original_model_path = original_model_file.name
    motion_sequence_path = motion_sequence_file.name if motion_sequence_file else None
    person_measurements_path = person_measurements_file.name if person_measurements_file else None

    # Step 1: Generate Skeleton
    progress(0, desc="ステップ1/3: スケルトン生成中...")
    skeleton_glb_path, skeleton_logs_update, skeleton_fbx_path, skeleton_txt_path = process_generate_skeleton(
        original_model_path, motion_sequence_path, person_measurements_path, gender, progress=progress_segment(progress, 0, 0.33)
    )
    skeleton_logs += skeleton_logs_update
    if not skeleton_fbx_path or not skeleton_txt_path: # skeleton_glb_path might be None if conversion fails
        final_log_message = skeleton_logs + "\\nスケルトン生成に失敗しました。パイプラインを中止します。"
        return (
            skeleton_glb_path, skeleton_logs, skeleton_fbx_path, skeleton_txt_path,
            skinned_model_glb_path, skinning_logs, downloadable_skinned_model_path,
            merged_model_glb_path, merge_logs, downloadable_merged_model_path,
            final_log_message
        )

    # Step 2: Generate Skinning
    progress(0.33, desc="ステップ2/3: スキニング生成中...")
    skinned_model_glb_path, skinning_logs_update, downloadable_skinned_model_path = process_generate_skin(
        original_model_path, 
        skeleton_txt_path,
        progress=progress_segment(progress, 0.33, 0.66)
    )
    skinning_logs += skinning_logs_update
    if not downloadable_skinned_model_path: # skinned_model_glb_path might be None
        final_log_message = skeleton_logs + "\\n" + skinning_logs + "\\nスキニング生成に失敗しました。パイプラインを中止します。"
        return (
            skeleton_glb_path, skeleton_logs, skeleton_fbx_path, skeleton_txt_path,
            skinned_model_glb_path, skinning_logs, downloadable_skinned_model_path,
            merged_model_glb_path, merge_logs, downloadable_merged_model_path,
            final_log_message
        )

    # Step 3: Merge Model
    progress(0.66, desc="ステップ3/3: モデルマージ中...")
    merged_model_glb_path, merge_logs_update, downloadable_merged_model_path = process_merge_model(
        target_model_path=original_model_path, 
        source_rig_model_path=downloadable_skinned_model_path, 
        progress=progress_segment(progress, 0.66, 1.0)
    )
    merge_logs += merge_logs_update
    if not downloadable_merged_model_path: # merged_model_glb_path might be None
        final_log_message = skeleton_logs + "\\n" + skinning_logs + "\\n" + merge_logs + "\\nモデルのマージに失敗しました。パイプラインを中止します。"
        return (
            skeleton_glb_path, skeleton_logs, skeleton_fbx_path, skeleton_txt_path,
            skinned_model_glb_path, skinning_logs, downloadable_skinned_model_path,
            merged_model_glb_path, merge_logs, downloadable_merged_model_path,
            final_log_message
        )

    progress(1.0, desc="パイプライン完了")
    final_log_message = skeleton_logs + "\\n" + skinning_logs + "\\n" + merge_logs + "\\nパイプラインが正常に完了しました。"
    return (
        skeleton_glb_path, skeleton_logs, skeleton_fbx_path, skeleton_txt_path,
        skinned_model_glb_path, skinning_logs, downloadable_skinned_model_path,
        merged_model_glb_path, merge_logs, downloadable_merged_model_path,
        final_log_message
    )

# --- Gradio UI --- 
def gradio_preview_model_and_bones(file_obj):
    if file_obj is None:
        return gr.update(value=None, visible=True), gr.update(value="ファイルがアップロードされていません。", visible=True)
    
    # Call the existing preview_model_and_bones function
    display_path, bone_info = preview_model_and_bones(file_obj)
    
    model_update = gr.update(value=display_path, visible=display_path is not None)
    text_update = gr.update(value=bone_info, visible=True)
    return model_update, text_update


with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    # UniRig Gradioインタフェース
    UniRigの機能を試すためのGradioアプリケーション。
    [UniRig GitHubリポジトリ](https://github.com/VAST-AI-Research/UniRig)
    """)

    with gr.Tabs():
        # スケルトン生成タブ (既存)
        with gr.Tab("1. スケルトン生成"):
            gr.Markdown("キャラクターメッシュからスケルトンを予測します。")
            with gr.Row():
                with gr.Column(scale=1):
                    input_model_skel = gr.File(label="入力3Dモデル (FBX, GLB, OBJなど)", type="filepath")
                    motion_sequence_input_skel = gr.File(label="モーションシーケンス (オプション .fbx, .bvh)", type="filepath")
                    person_measurements_input_skel = gr.File(label="身体測定ファイル (オプション .json)", type="filepath")
                    gender_dropdown_skel = gr.Dropdown(label="性別", choices=["neutral", "male", "female"], value="neutral")
                    
                    # Instant preview for skeleton prediction tab
                    preview_model_skel_display = gr.Model3D(label="入力モデルプレビュー", interactive=False)
                    preview_bone_info_skel = gr.Textbox(label="入力モデルのボーン情報", lines=5, max_lines=10, interactive=False)
                    input_model_skel.change(gradio_preview_model_and_bones, inputs=[input_model_skel], outputs=[preview_model_skel_display, preview_bone_info_skel])
                    
                    generate_skeleton_button = gr.Button("スケルトンを生成")
                with gr.Column(scale=1):
                    output_model_skel = gr.Model3D(label="リグ付きモデル (スケルトン付き)", interactive=False)
                    output_skeleton_file = gr.File(label="予測されたスケルトン (.txt) をダウンロード")
                    output_rigged_model_file = gr.File(label="リグ付きモデル (.glb) をダウンロード")
                    logs_skel = gr.Textbox(label="ログ", lines=10, max_lines=20, interactive=False)
            
            generate_skeleton_button.click(
                gradio_generate_skeleton, 
                inputs=[input_model_skel, motion_sequence_input_skel, person_measurements_input_skel, gender_dropdown_skel],
                outputs=[output_model_skel, logs_skel, output_rigged_model_file, output_skeleton_file]
            )

        # スキニング生成タブ (新規追加)
        with gr.Tab("2. スキニング生成"):
            gr.Markdown("""### ステップ2: スキニング生成

スケルトン生成ステップで得られたオリジナルモデルと `skeleton_pred.txt` を使用して、スキンウェイトを生成します。""")
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("#### 入力")
                    skin_input_model = gr.File(label="オリジナルモデル (GLB, FBX, OBJ等)", type="filepath")
                    gr.Markdown("スケルトン生成やスキニング生成で使用したオリジナルの入力モデルを指定してください。")
                    
                    skin_input_skeleton_text = gr.File(label="skeleton_pred.txt ファイル", type="filepath")
                    gr.Markdown("スケルトン生成ステップの「skeleton_pred.txt」を指定してください。")
                    
                    generate_skin_button = gr.Button("スキニング生成実行", variant="primary")
                with gr.Column(scale=2):
                    gr.Markdown("#### 出力")
                    skin_model_display = gr.Model3D(label="スキニング済みモデル (表示用)", clear_color=[0.8, 0.8, 0.8, 1.0])
                    skin_model_download = gr.File(label="スキニング済みモデル (ダウンロード用)", type="filepath", interactive=False)
                    logs_skin = gr.Textbox(label="ログ (スキニング)", lines=15, max_lines=30, autoscroll=True, show_copy_button=True)
            
            # スキニング生成処理の接続
            generate_skin_button.click(
                fn=gradio_generate_skin,
                inputs=[skin_input_model, skin_input_skeleton_text],
                outputs=[skin_model_display, skin_model_download, logs_skin]
            )
            
            gr.Markdown("""#### 次のステップへ
スキニング済みモデル（FBXまたはGLB）が得られたら、「3. マージ」ステップに進み、元の高解像度メッシュと結合できます（オプション）。""")


        # マージタブ (既存のものを更新、または新規で考える)
        with gr.Tab("3. マージ (モデル統合)"):
            gr.Markdown("""### ステップ3: モデルマージ (オプション)

オリジナルの高解像度モデルと、生成されたリグ（スケルトンまたはスキニング済みモデル）をマージして、最終的なリグ付きモデルを生成します。""")
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("#### 入力")
                    merge_target_model = gr.File(label="ターゲットモデル (オリジナル高解像度メッシュ: GLB, FBX, OBJ等)", type="filepath")
                    gr.Markdown("例: スケルトン生成やスキニング生成で使用したオリジナルの入力モデル。")
                    
                    merge_source_rig_model = gr.File(label="ソースリグモデル (リグ情報を持つモデル: FBX, GLB)", type="filepath")
                    gr.Markdown("例: スケルトン生成ステップの `skeleton.fbx`、またはスキニング生成ステップの「スキニング済みモデル」。")

                    merge_model_button = gr.Button("マージ実行", variant="primary")
                with gr.Column(scale=2):
                    gr.Markdown("#### 出力")
                    merged_model_display = gr.Model3D(label="マージ済みモデル (表示用)", clear_color=[0.8, 0.8, 0.8, 1.0])
                    merged_model_download = gr.File(label="マージ済みモデル (ダウンロード用 GLB)", type="filepath", interactive=False)
                    logs_merge = gr.Textbox(label="ログ (マージ)", lines=15, max_lines=30, autoscroll=True, show_copy_button=True)

            # マージ処理の接続 (process_merge_model と gradio_merge_model はこれから実装/調整)
            merge_model_button.click(
                gradio_merge_model,
                inputs=[merge_target_model, merge_source_rig_model],
                outputs=[merged_model_display, merged_model_download, logs_merge],
            )
            gr.Markdown("---")
            gr.Markdown("開発者向け: [デバッグ用] フルパイプラインのシーケンシャル実行 (現在は無効)")
            # ... (run_pipeline_button と関連コンポーネントはコメントアウトまたは削除) ...

    # ... (atexit.register(cleanup_temp_files) の前) ...

if __name__ == "__main__":
    # アプリケーションの一時ディレクトリをセットアップ
    if not os.path.exists(GRADIO_TEMP_DIR):
        os.makedirs(GRADIO_TEMP_DIR)
    
    # アプリケーション終了時に一時ファイルをクリーンアップする
    atexit.register(cleanup_temp_files)

    # Gradioアプリケーションを起動
    demo.launch()