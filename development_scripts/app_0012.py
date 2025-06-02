# This application uses UniRig (https://github.com/VAST-AI-Research/UniRig),
# which is licensed under the MIT License.
# A copy of the license can be found at:
# https://github.com/VAST-AI-Research/UniRig/blob/main/LICENSE
#
# Gradio application for 3D model preview and bone information display.

import gradio as gr
import os
import subprocess
import tempfile
import datetime
import yaml
from box import Box
import shutil
import traceback
import numpy as np
import trimesh # For model inspection if needed, or by Blender script
import logging
import sys
import pathlib # Not strictly used in this version, but good for path manipulation
import json # For datalist
import atexit
from texture_preservation_system import TexturePreservationSystem
from proposed_blender_texture_flow import BlenderNativeTextureFlow

# Import ImprovedSafeTextureRestoration for priority texture processing
try:
    from improved_safe_texture_restoration import ImprovedSafeTextureRestoration
    IMPROVED_SAFE_TEXTURE_RESTORATION_AVAILABLE = True
    print("✅ ImprovedSafeTextureRestoration loaded in app.py")
except ImportError as e:
    IMPROVED_SAFE_TEXTURE_RESTORATION_AVAILABLE = False
    print(f"⚠️ ImprovedSafeTextureRestoration not available in app.py: {e}")

# --- Global Configuration and Setup ---
APP_CONFIG = None
TEMP_FILES_TO_CLEAN = []

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Helper: Load Application Configuration ---
def load_app_config(config_path='configs/app_config.yaml'):
    global APP_CONFIG
    try:
        with open(config_path, 'r') as f:
            APP_CONFIG = Box(yaml.safe_load(f))
        logging.info(f"アプリケーション設定をロードしました: {config_path}")
        
        # Setup working directory base and ensure it exists
        base_dir = APP_CONFIG.get('working_directory_base', 'pipeline_work')
        if not os.path.isabs(base_dir):
            base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), base_dir)
        APP_CONFIG.working_directory_base = os.path.abspath(base_dir)
        os.makedirs(APP_CONFIG.working_directory_base, exist_ok=True)
        logging.info(f"ワーキングディレクトリベース: {APP_CONFIG.working_directory_base}")

    except FileNotFoundError:
        logging.error(f"設定ファイルが見つかりません: {config_path}")
        APP_CONFIG = Box({'error': 'Config file not found'}) # Ensure APP_CONFIG is not None
    except yaml.YAMLError as e:
        logging.error(f"設定ファイルの解析エラー: {e}")
        APP_CONFIG = Box({'error': 'Config YAML error'})
    except Exception as e:
        logging.error(f"設定ファイルのロード中に予期せぬエラー: {e}")
        APP_CONFIG = Box({'error': f'Unexpected error loading config: {e}'})

# --- Helper: Create Unique Working Directory ---
def create_working_directory(model_name, step_name):
    if not APP_CONFIG or 'working_directory_base' not in APP_CONFIG:
        logging.error("APP_CONFIGが正しくロードされていないか、working_directory_baseが未定義です。")
        # Fallback to a temporary directory if config is not loaded
        fallback_dir = os.path.join(tempfile.gettempdir(), "unirig_fallback_work", model_name, step_name)
        os.makedirs(fallback_dir, exist_ok=True)
        logging.warning(f"フォールバックワーキングディレクトリを使用します: {fallback_dir}")
        return fallback_dir

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    # Sanitize model_name and step_name to be filesystem-friendly
    safe_model_name = "".join(c if c.isalnum() or c in ('_', '-') else '_' for c in model_name)
    safe_step_name = "".join(c if c.isalnum() or c in ('_', '-') else '_' for c in step_name)
    
    # Use a simpler, more predictable path structure based on model name and step
    # Example: pipeline_work/bird/01_extracted_mesh/
    # No timestamp for easier debugging and re-running, unless specifically needed for uniqueness
    # For now, let's keep it simple. If multiple runs for the same model/step need to be distinct,
    # then a timestamp or run ID might be necessary.
    # work_dir = os.path.join(APP_CONFIG.working_directory_base, safe_model_name, f"{safe_step_name}_{timestamp}")
    work_dir = os.path.join(APP_CONFIG.working_directory_base, safe_model_name, safe_step_name)
    
    os.makedirs(work_dir, exist_ok=True)
    logging.info(f"ワーキングディレクトリを作成しました: {work_dir}")
    return work_dir

# --- Helper: Progress Bar Segmentation ---
def progress_segment(progress_bar, start_fraction, end_fraction):
    def update_progress(current_step_progress, desc=""):
        # current_step_progress is from 0.0 to 1.0 for the current step
        overall_progress = start_fraction + (current_step_progress * (end_fraction - start_fraction))
        progress_bar(overall_progress, desc=desc)
    return update_progress

# --- Helper: Run Subprocess ---
def run_subprocess_with_progress(command, work_dir, log_file_path, progress_fn, total_items_for_tqdm=1):
    logs = ""
    try:
        process = subprocess.Popen(command, cwd=work_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
        
        # For simple progress if not using tqdm directly in the script
        # This assumes the script itself doesn't output tqdm-parsable lines for this specific progress bar.
        # If the script has its own tqdm, this might conflict or be redundant.
        # For now, let's simulate progress based on time or completion.
        # A more robust way would be if the script outputted progress updates.
        
        # Simulate progress for the subprocess duration if it's a single task
        # This is a placeholder. Real progress depends on the script's output.
        progress_fn(0.1, desc=f"実行中: {command[1]}...") 

        with open(log_file_path, 'w') as log_f:
            for line in process.stdout:
                logs += line
                log_f.write(line)
                # If the script outputs progress, parse it here.
                # For now, we don't have a specific format to parse.
        
        process.wait()
        progress_fn(0.9, desc=f"完了待ち: {command[1]}...")

        if process.returncode == 0:
            logs += f"コマンド成功: {' '.join(command)}\n"
            progress_fn(1.0, desc=f"完了: {command[1]}")
            return True, logs
        else:
            logs += f"コマンド失敗 (コード {process.returncode}): {' '.join(command)}\n"
            logs += f"ログファイル参照: {log_file_path}\n"
            progress_fn(1.0, desc=f"エラー: {command[1]}") # Mark as complete even on error for progress bar
            return False, logs
    except FileNotFoundError:
        logs += f"エラー: コマンドが見つかりません - {command[0]}。パスを確認してください。\n"
        progress_fn(1.0, desc=f"エラー: {command[0]} not found")
        return False, logs
    except Exception as e:
        logs += f"サブプロセス実行中に予期せぬエラー: {e}\n"
        logs += f"コマンド: {' '.join(command)}\n"
        logs += f"詳細: {traceback.format_exc()}\n"
        progress_fn(1.0, desc=f"例外: {command[1]}")
        return False, logs

# --- Helper: Convert to GLB for Display ---
def convert_to_glb_for_display(model_path, output_name_stem, work_dir_override=None):
    if not model_path or not os.path.exists(model_path):
        logging.warning(f"GLB変換のためのモデルパスが無効または存在しません: {model_path}")
        return None

    original_model_name = os.path.splitext(os.path.basename(model_path))[0]
    
    if work_dir_override:
        # Use a specific directory if provided (e.g., a common display_cache)
        display_work_dir = work_dir_override
        os.makedirs(display_work_dir, exist_ok=True)
    else:
        # Default to a subdirectory within the model's pipeline_work for organization
        # This assumes APP_CONFIG and working_directory_base are set.
        if APP_CONFIG and APP_CONFIG.working_directory_base:
            display_work_dir = tempfile.mkdtemp(prefix=f"{original_model_name}_display_")
            TEMP_FILES_TO_CLEAN.append(display_work_dir) # Schedule for cleanup
        else: # Fallback if APP_CONFIG is not properly set
            display_work_dir = tempfile.mkdtemp(prefix="unirig_display_")
            TEMP_FILES_TO_CLEAN.append(display_work_dir)
            logging.warning(f"APP_CONFIG未設定のため、GLB表示に一時ディレクトリを使用: {display_work_dir}")

    # Sanitize output_name_stem for the filename
    safe_output_name_stem = "".join(c if c.isalnum() or c in ('_', '-') else '_' for c in output_name_stem)
    output_glb_path = os.path.join(display_work_dir, f"{safe_output_name_stem}_display.glb")
    
    # Ensure Blender path is correctly configured
    blender_executable = APP_CONFIG.blender_settings.blender_executable
    conversion_script = os.path.abspath(APP_CONFIG.blender_processing.conversion_script) # Ensure absolute path

    if not os.path.exists(blender_executable):
        logging.error(f"Blender実行ファイルが見つかりません: {blender_executable}")
        return None
    if not os.path.exists(conversion_script):
        logging.error(f"Blender変換スクリプトが見つかりません: {conversion_script}")
        return None

    command = [
        blender_executable,
        "--background",
        "--python", conversion_script,
        "--",
        "--input", os.path.abspath(model_path), # Ensure absolute path for Blender
        "--output", os.path.abspath(output_glb_path) # Ensure absolute path for Blender
    ]
    
    logging.info(f"GLB変換コマンド: {' '.join(command)}")
    log_file = os.path.join(display_work_dir, f"{safe_output_name_stem}_conversion.log")

    try:
        result = subprocess.run(command, cwd=os.path.dirname(conversion_script), capture_output=True, text=True, check=False)
        
        with open(log_file, 'w') as f_log:
            f_log.write("--- STDOUT ---\n")
            f_log.write(result.stdout if result.stdout else "")
            f_log.write("\n--- STDERR ---\n")
            f_log.write(result.stderr if result.stderr else "")

        if result.returncode == 0 and os.path.exists(output_glb_path):
            logging.info(f"GLBへの変換成功: {output_glb_path}")
            return output_glb_path
        else:
            logging.error(f"GLBへの変換失敗。リターンコード: {result.returncode}")
            logging.error(f"STDOUT: {result.stdout}")
            logging.error(f"STDERR: {result.stderr}")
            logging.error(f"変換ログファイル: {log_file}")
            return None
    except Exception as e:
        logging.error(f"GLB変換のサブプロセス実行中にエラー: {e}")
        logging.error(f"詳細: {traceback.format_exc()}")
        return None

# --- Cleanup Temporary Files ---
def cleanup_temp_files():
    for item_path in TEMP_FILES_TO_CLEAN:
        try:
            if os.path.isfile(item_path):
                os.remove(item_path)
                logging.info(f"一時ファイルを削除しました: {item_path}")
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
                logging.info(f"一時ディレクトリを削除しました: {item_path}")
        except Exception as e:
            logging.warning(f"一時ファイル/ディレクトリの削除エラー ({item_path}): {e}")
atexit.register(cleanup_temp_files)


# --- Modify this section for allowed paths (DEBUGGING) ---
def get_allowed_paths():
    script_dir = os.path.dirname(os.path.abspath(__file__)) # /app
    allowed = [
        os.path.abspath(script_dir), # /app
        os.path.abspath(os.path.join(script_dir, "pipeline_work")), # /app/pipeline_work
        os.path.abspath(os.path.join(script_dir, "examples")), # /app/examples
        os.path.abspath(os.path.join(script_dir, "src")), # /app/src
        os.path.abspath(os.path.join(script_dir, "configs")), # /app/configs
        os.path.abspath(os.path.join(script_dir, "blender")), # /app/blender
    ]
    if APP_CONFIG and APP_CONFIG.working_directory_base:
        # Ensure the configured working_directory_base is also allowed
        # This might be redundant if it's already /app/pipeline_work, but good for safety
        configured_work_base = os.path.abspath(APP_CONFIG.working_directory_base)
        if configured_work_base not in allowed:
            allowed.append(configured_work_base)
        
        # Add specific subdirectories from config if they exist, ensuring they are absolute
        subdirs_to_check = [
            APP_CONFIG.get('mesh_extraction', {}).get('extract_output_subdir'),
            APP_CONFIG.get('skeleton_generation', {}).get('skeleton_output_subdir'),
            APP_CONFIG.get('skinning_prediction', {}).get('skin_output_subdir'),
            APP_CONFIG.get('model_merging', {}).get('merge_output_subdir'),
            APP_CONFIG.get('blender_processing', {}).get('conversion_output_subdir'),
            APP_CONFIG.get('blender_native_texture_flow', {}).get('blender_native_subdir', '06_blender_native'),
            APP_CONFIG.get('improved_safe_texture_restoration', {}).get('output_subdir', '08_final_output')
        ]
        for subdir_name in subdirs_to_check:
            if subdir_name:
                potential_path = os.path.join(configured_work_base, subdir_name)
                abs_path = os.path.abspath(potential_path)
                if abs_path not in allowed:
                    allowed.append(abs_path)
    
    allowed.append(os.path.abspath(tempfile.gettempdir()))
    unique_allowed_paths = list(set(allowed)) # Remove duplicates
    logging.info(f"DEBUG: Gradio allowed_pathsが設定されました: {unique_allowed_paths}")
    return unique_allowed_paths
# --- End of modified section --


# --- Add this helper function for debugging output paths ---
def log_output_paths_for_debug(output_dict, context_log_message=""):
    logging.info(f"--- DEBUG: Gradio出力パスの確認 ({context_log_message}) ---")
    if not isinstance(output_dict, dict):
        logging.warning(f"  出力は辞書ではありません: {type(output_dict)}, 値: {output_dict}")
        return

    for key, value in output_dict.items():
        if isinstance(value, str) and (value.endswith(('.glb', '.fbx', '.png', '.jpg', '.txt', '.npz', '.json', '.yaml')) or "/" in value or "\\" in value):
            # Heuristic: if it looks like a file path string
            abs_path = os.path.abspath(value) if value else "N/A (None or empty string)"
            exists = os.path.exists(abs_path) if value else False
            is_file = os.path.isfile(abs_path) if exists else "N/A"
            logging.info(f"  出力キー: '{key}', パス: '{value}' (絶対パス: '{abs_path}'), 存在: {exists}, ファイル?: {is_file}")
            if exists and is_file:
                try:
                    logging.info(f"    ファイルサイズ: {os.path.getsize(abs_path)} bytes")
                except Exception as e:
                    logging.warning(f"    ファイルサイズの取得エラー: {e}")
        elif isinstance(value, list) and all(isinstance(item, str) for item in value):
             logging.info(f"  出力キー: '{key}', 値 (リスト): {value} - (リスト内のパスは個別に確認されません)")
        else:
            logging.info(f"  出力キー: '{key}', 値: {value} (型: {type(value)}) - パスとして扱われません")
    logging.info("--- DEBUG: Gradio出力パスの確認完了 ---")
# --- End of added helper function ---

# --- Pipeline Step 1: Mesh Extraction ---
def process_extract_mesh(original_model_path, model_name, progress_fn):
    logs = ""
    if not original_model_path or not os.path.exists(original_model_path):
        logs += f"エラー: 入力モデルファイルが見つかりません: {original_model_path}\n"
        progress_fn(1.0, "エラー: 入力ファイルなし")
        return None, logs

    # Create working directory for this step
    extract_config = APP_CONFIG.mesh_extraction
    work_dir = create_working_directory(model_name, extract_config.extract_output_subdir)
    log_file_path = os.path.join(work_dir, f"{model_name}_extract_log.txt")
    
    # Expected output NPZ path
    expected_npz_filename = f"{model_name}_{extract_config.output_npz_suffix}.npz"
    expected_npz_path = os.path.join(work_dir, expected_npz_filename)

    # Texture Preservation System: Analyze and Backup
    # This should happen BEFORE any UniRig processing that might lose texture info
    texture_system = TexturePreservationSystem(
        original_model_path=original_model_path,
        model_name=model_name,
        base_processing_dir=APP_CONFIG.working_directory_base, # e.g., pipeline_work/
        config=APP_CONFIG.texture_preservation_system
    )
    progress_fn(0.1, "テクスチャ情報解析中...")
    try:
        texture_backup_success, texture_info_log = texture_system.analyze_and_backup_textures()
        logs += texture_info_log
        if not texture_backup_success:
            logs += "警告: テクスチャのバックアップまたは解析に失敗しました。処理は続行されますが、テクスチャが失われる可能性があります。\n"
            # Decide if this is a critical failure or a warning. For now, warning.
        else:
            logs += "テクスチャ情報の解析とバックアップが完了しました。\n"
    except Exception as tex_e:
        logs += f"テクスチャ処理中にエラーが発生しました: {tex_e}\n{traceback.format_exc()}\n"
        # Continue with extraction, but log the error.

    progress_fn(0.3, "UniRigメッシュ抽出スクリプト実行中...")
    # Command for UniRig's extract_mesh.py
    # Example: python src/UniRig/extract_mesh.py --mesh_path <input_model> --save_path <output_dir> --output_name <model_name_raw.npz>
    unirig_extract_script = os.path.join(APP_CONFIG.unirig_paths.base_path, extract_config.script_name)
    
    command = [
        APP_CONFIG.python_executable,
        unirig_extract_script,
        "--mesh_path", original_model_path,
        "--save_path", work_dir, # UniRig script expects directory for save_path
        "--output_name", expected_npz_filename # UniRig script will append .npz if not present, but good to be explicit
    ]
    
    success, process_logs = run_subprocess_with_progress(command, work_dir, log_file_path, progress_fn)
    logs += process_logs

    if success and os.path.exists(expected_npz_path):
        logs += f"メッシュ抽出成功: {expected_npz_path}\n"
        progress_fn(1.0, "メッシュ抽出完了")
        return expected_npz_path, logs
    else:
        logs += "メッシュ抽出失敗。ログを確認してください。\n"
        if not os.path.exists(expected_npz_path):
            logs += f"期待された出力ファイルが見つかりません: {expected_npz_path}\n"
        progress_fn(1.0, "メッシュ抽出エラー")
        return None, logs

# --- Pipeline Step 2: Skeleton Generation ---
def process_generate_skeleton(raw_data_npz_path, model_name, gender, progress_fn):
    logs = ""
    if not raw_data_npz_path or not os.path.exists(raw_data_npz_path):
        logs += f"エラー: 抽出されたNPZファイルが見つかりません: {raw_data_npz_path}\n"
        progress_fn(1.0, "エラー: NPZファイルなし")
        return None, logs, None, None, None

    skeleton_config = APP_CONFIG.skeleton_generation
    work_dir = create_working_directory(model_name, skeleton_config.skeleton_output_subdir)
    log_file_path = os.path.join(work_dir, f"{model_name}_skeleton_log.txt")

    # Expected output paths
    # UniRig's generate_skeleton.py saves multiple files:
    # - <output_name>_skeleton_bones.txt
    # - <output_name>_skeleton.fbx
    # - <output_name>_skeleton.npz
    # - <output_name>_skeleton_mesh.glb (for visualization)
    output_name_stem = f"{model_name}_{skeleton_config.output_name_suffix}" # e.g., bird_skeleton
    
    expected_fbx_path = os.path.join(work_dir, f"{output_name_stem}.fbx")
    expected_txt_path = os.path.join(work_dir, f"{output_name_stem}_bones.txt")
    expected_npz_path = os.path.join(work_dir, f"{output_name_stem}.npz")
    expected_glb_path = os.path.join(work_dir, f"{output_name_stem}_mesh.glb") # For display

    unirig_skeleton_script = os.path.join(APP_CONFIG.unirig_paths.base_path, skeleton_config.script_name)
    command = [
        APP_CONFIG.python_executable,
        unirig_skeleton_script,
        "--raw_data_path", raw_data_npz_path,
        "--gender", gender,
        "--save_path", work_dir,
        "--output_name", output_name_stem, # UniRig script uses this as a stem
        "--rest_pose_path", APP_CONFIG.unirig_paths.rest_pose_path # Add rest pose path from config
    ]

    success, process_logs = run_subprocess_with_progress(command, work_dir, log_file_path, progress_fn)
    logs += process_logs

    if success and os.path.exists(expected_fbx_path) and os.path.exists(expected_npz_path):
        logs += f"スケルトン生成成功。FBX: {expected_fbx_path}, NPZ: {expected_npz_path}\n"
        display_glb_path = expected_glb_path if os.path.exists(expected_glb_path) else None
        if not display_glb_path:
            logs += f"警告: 表示用GLBファイルが見つかりません: {expected_glb_path}\n"
        progress_fn(1.0, "スケルトン生成完了")
        return display_glb_path, logs, expected_fbx_path, expected_txt_path, expected_npz_path
    else:
        logs += "スケルトン生成失敗。ログを確認してください。\n"
        if not os.path.exists(expected_fbx_path): logs += f"期待されたFBXファイルが見つかりません: {expected_fbx_path}\n"
        if not os.path.exists(expected_npz_path): logs += f"期待されたNPZファイルが見つかりません: {expected_npz_path}\n"
        progress_fn(1.0, "スケルトン生成エラー")
        return None, logs, None, None, None

# --- Pipeline Step 3: Skinning Prediction ---
def process_generate_skin(raw_data_npz_path, skeleton_fbx_path, skeleton_npz_path, model_name_for_output, progress_fn):
    logs = ""
    required_files = {
        "Raw NPZ": raw_data_npz_path,
        "Skeleton FBX": skeleton_fbx_path,
        "Skeleton NPZ": skeleton_npz_path
    }
    for name, path in required_files.items():
        if not path or not os.path.exists(path):
            logs += f"エラー: スキニングに必要なファイルが見つかりません - {name}: {path}\n"
            progress_fn(1.0, f"エラー: {name}なし")
            return None, logs, None, None
            
    skin_config = APP_CONFIG.skinning_prediction
    work_dir = create_working_directory(model_name_for_output, skin_config.skin_output_subdir)
    log_file_path = os.path.join(work_dir, f"{model_name_for_output}_skin_log.txt")

    # Expected output paths for UniRig's generate_skin.py
    # - <output_name>_skinned_mesh.glb (visualization)
    # - <output_name>_skinning_weights.npz
    # - <output_name>_skinned.fbx (skinned model without original textures)
    output_name_stem = f"{model_name_for_output}_{skin_config.output_name_suffix}" # e.g., bird_skinned

    expected_glb_path = os.path.join(work_dir, f"{output_name_stem}_mesh.glb") # For display
    expected_skin_npz_path = os.path.join(work_dir, f"{output_name_stem}_weights.npz")
    expected_skinned_fbx_path = os.path.join(work_dir, f"{output_name_stem}.fbx")


    unirig_skin_script = os.path.join(APP_CONFIG.unirig_paths.base_path, skin_config.script_name)
    command = [
        APP_CONFIG.python_executable,
        unirig_skin_script,
        "--raw_data_path", raw_data_npz_path,
        "--skeleton_path", skeleton_npz_path, # UniRig uses the skeleton NPZ
        "--skeleton_fbx_path", skeleton_fbx_path, # And the skeleton FBX
        "--save_path", work_dir,
        "--output_name", output_name_stem, # UniRig uses this as a stem
        "--model_name", model_name_for_output # Pass model name for internal use if script supports
    ]

    success, process_logs = run_subprocess_with_progress(command, work_dir, log_file_path, progress_fn)
    logs += process_logs

    if success and os.path.exists(expected_skinned_fbx_path) and os.path.exists(expected_skin_npz_path):
        logs += f"スキニングウェイト予測成功。FBX: {expected_skinned_fbx_path}, NPZ: {expected_skin_npz_path}\n"
        display_glb_path = expected_glb_path if os.path.exists(expected_glb_path) else None
        if not display_glb_path:
            # Fallback: try to convert the output FBX to GLB for display if the script didn't make one
            logs += f"警告: スキニング表示用GLBファイル ({expected_glb_path}) がUniRigスクリプトによって生成されませんでした。FBXから変換を試みます...\n"
            display_glb_path = convert_to_glb_for_display(expected_skinned_fbx_path, f"{output_name_stem}_fbx_conv")
            if display_glb_path:
                logs += f"FBXからのGLB変換成功 (表示用): {display_glb_path}\n"
            else:
                logs += f"警告: スキン済みFBXからのGLB変換に失敗しました。プレビューは利用できません。\n"

        progress_fn(1.0, "スキニング完了")
        return display_glb_path, logs, expected_skinned_fbx_path, expected_skin_npz_path
    else:
        logs += "スキニングウェイト予測失敗。ログを確認してください。\n"
        if not os.path.exists(expected_skinned_fbx_path): logs += f"期待されたスキン済みFBXが見つかりません: {expected_skinned_fbx_path}\n"
        if not os.path.exists(expected_skin_npz_path): logs += f"期待されたスキニングNPZが見つかりません: {expected_skin_npz_path}\n"
        progress_fn(1.0, "スキニングエラー")
        return None, logs, None, None

# --- Pipeline Step 4: Model Merging (Old UniRig method, if needed as fallback) ---
def process_merge_model(original_model_path, skinned_fbx_path, skinning_npz_path, model_name_for_output, progress_fn):
    logs = "--- 旧UniRigマージ処理 (フォールバックまたは比較用) ---\n"
    required_files = {
        "Original Model": original_model_path,
        "Skinned FBX": skinned_fbx_path,
        "Skinning NPZ": skinning_npz_path
    }
    for name, path in required_files.items():
        if not path or not os.path.exists(path):
            logs += f"エラー: マージに必要なファイルが見つかりません - {name}: {path}\n"
            progress_fn(1.0, f"エラー: {name}なし")
            return None, logs, None

    merge_config = APP_CONFIG.model_merging # Assuming a general merge config section
    work_dir = create_working_directory(model_name_for_output, merge_config.get('merge_output_subdir_old', '04_merge_old'))
    log_file_path = os.path.join(work_dir, f"{model_name_for_output}_merge_old_log.txt")
    
    output_name_stem = f"{model_name_for_output}_{merge_config.get('output_name_suffix_old', 'final_rigged_old')}"
    expected_merged_fbx_path = os.path.join(work_dir, f"{output_name_stem}.fbx")
    
    # This refers to UniRig's original merge script, which might not handle textures well.
    unirig_merge_script = os.path.join(APP_CONFIG.unirig_paths.base_path, merge_config.script_name) # e.g., merge.py from UniRig
    
    command = [
        APP_CONFIG.python_executable,
        unirig_merge_script,
        "--fbx_path", original_model_path, # Original model with textures
        "--skeleton_path", skinned_fbx_path, # This is likely the FBX with UniRig skeleton
        "--skin_path", skinning_npz_path,   # Skinning weights
        "--save_path", work_dir,
        "--output_name", output_name_stem,
        "--uv_path", APP_CONFIG.unirig_paths.uv_template_path # UV template from config
    ]

    success, process_logs = run_subprocess_with_progress(command, work_dir, log_file_path, progress_fn)
    logs += process_logs

    if success and os.path.exists(expected_merged_fbx_path):
        logs += f"旧UniRigモデルマージ成功: {expected_merged_fbx_path}\n"
        display_glb_path = convert_to_glb_for_display(expected_merged_fbx_path, f"{output_name_stem}_display")
        progress_fn(1.0, "旧マージ完了")
        return display_glb_path, logs, expected_merged_fbx_path
    else:
        logs += "旧UniRigモデルマージ失敗。ログを確認してください。\n"
        if not os.path.exists(expected_merged_fbx_path):
            logs += f"期待されたマージ済みFBXが見つかりません: {expected_merged_fbx_path}\n"
        progress_fn(1.0, "旧マージエラー")
        return None, logs, None

# --- Pipeline Step 4 (New): Final Merge with Texture Preservation ---
def process_final_merge_with_textures(skinned_fbx_path, original_model_path, model_name_for_output, progress_fn):
    logs = "--- テクスチャ保持型最終マージ処理開始 ---\n"
    
    required_paths = {
        "Skinned FBX (from UniRig skinning step)": skinned_fbx_path,
        "Original Model Path (with original textures)": original_model_path,
    }
    for name, path in required_paths.items():
        if not path or not os.path.exists(path):
            logs += f"エラー: 最終マージに必要なファイルが見つかりません - {name}: {path}\n"
            progress_fn(1.0, f"エラー: {name}なし")
            return None, logs, None

    # Determine which texture flow to use based on availability and configuration
    use_improved_safe_flow = IMPROVED_SAFE_TEXTURE_RESTORATION_AVAILABLE and APP_CONFIG.texture_processing_priority == "improved_safe_texture_restoration"
    use_blender_native_flow = APP_CONFIG.texture_processing_priority == "blender_native_texture_flow"

    final_fbx_path = None
    display_path = None
    
    progress_fn(0.05, "テクスチャ処理フロー準備中...")

    if use_improved_safe_flow:
        logs += "🚀 ImprovedSafeTextureRestoration フローを使用します。\n"
        safe_texture_config = APP_CONFIG.improved_safe_texture_restoration
        output_subdir = safe_texture_config.get('output_subdir', '08_final_output')
        final_work_dir = create_working_directory(model_name_for_output, output_subdir)
        
        # Path to the material metadata JSON saved by TexturePreservationSystem during mesh extraction
        # This path needs to be correctly constructed based on where TexturePreservationSystem saves it.
        # TexturePreservationSystem saves it in: <base_processing_dir>/<model_name>/<metadata_subdir>/<filename>
        # Example: pipeline_work/bird/07_material_metadata/bird_material_structure.json
        tps_config = APP_CONFIG.texture_preservation_system
        metadata_dir = os.path.join(APP_CONFIG.working_directory_base, model_name_for_output, tps_config.metadata_subdir)
        material_metadata_path = os.path.join(metadata_dir, f"{model_name_for_output}_{tps_config.metadata_filename}")
        
        # Path to the backed-up textures, also from TexturePreservationSystem
        # Example: pipeline_work/bird/05_texture_preservation/
        texture_backup_dir = os.path.join(APP_CONFIG.working_directory_base, model_name_for_output, tps_config.backup_subdir)

        if not os.path.exists(material_metadata_path):
            logs += f"❌ クリティカルエラー: マテリアルメタデータファイルが見つかりません: {material_metadata_path}。ImprovedSafeTextureRestorationは実行できません。\n"
            progress_fn(1.0, "エラー: メタデータなし")
            return None, logs, None
        if not os.path.exists(texture_backup_dir) or not os.listdir(texture_backup_dir): # Check if dir exists and is not empty
            logs += f"⚠️ 警告: テクスチャバックアップディレクトリが見つからないか空です: {texture_backup_dir}。テクスチャが復元されない可能性があります。\n"
            # Allow to proceed but with a warning.

        try:
            progress_fn(0.1, "ImprovedSafeTextureRestoration 初期化中...")
            safe_restorer = ImprovedSafeTextureRestoration(
                skinned_fbx_path=skinned_fbx_path,
                material_metadata_json_path=material_metadata_path,
                texture_directory_path=texture_backup_dir,
                output_directory=final_work_dir,
                model_name=model_name_for_output,
                blender_executable=APP_CONFIG.blender_settings.blender_executable,
                processing_config=safe_texture_config # Pass the specific config section
            )
            
            logs += "⚙️ ImprovedSafeTextureRestoration パイプライン実行中...\n"
            # This method should internally handle progress reporting via a passed callback if designed for it.
            # For now, we'll wrap its main call with broader progress updates.
            
            # If safe_restorer.run_full_pipeline takes a progress_callback:
            # sub_progress_fn = progress_segment(progress_fn, 0.1, 0.9) # Allocate 80% of this step's bar
            # final_fbx_path, stage_logs = safe_restorer.run_full_pipeline(progress_callback=sub_progress_fn)
            
            # If not, simulate progress around the call
            progress_fn(0.2, "SafeFlow: FBXインポート...")
            final_fbx_path, stage_logs = safe_restorer.run_full_pipeline() # Assuming it returns (output_fbx_path, logs_string)
            logs += stage_logs
            
            if final_fbx_path and os.path.exists(final_fbx_path):
                logs += f"✅ ImprovedSafeTextureRestoration 成功。最終FBX: {final_fbx_path}\n"
                progress_fn(0.95, "SafeFlow: GLBプレビュー生成中...")
                display_path = convert_to_glb_for_display(final_fbx_path, f"{model_name_for_output}_final_safe_textured")
            else:
                logs += f"❌ ImprovedSafeTextureRestoration 失敗。詳細はログを確認してください。\n"
                final_fbx_path = None # Ensure it's None on failure
        except Exception as e:
            logs += f"❌ ImprovedSafeTextureRestoration 実行中に予期せぬエラー: {e}\n{traceback.format_exc()}\n"
            final_fbx_path = None
            
    elif use_blender_native_flow:
        logs += "🔶 BlenderNativeTextureFlow を使用します。\n"
        bntf_config = APP_CONFIG.blender_native_texture_flow
        output_subdir = bntf_config.get('blender_native_subdir', '06_blender_native') # Default from instructions
        final_work_dir = create_working_directory(model_name_for_output, output_subdir)

        # Similar to above, get metadata and texture paths
        tps_config = APP_CONFIG.texture_preservation_system
        metadata_dir = os.path.join(APP_CONFIG.working_directory_base, model_name_for_output, tps_config.metadata_subdir)
        material_metadata_path = os.path.join(metadata_dir, f"{model_name_for_output}_{tps_config.metadata_filename}")
        texture_backup_dir = os.path.join(APP_CONFIG.working_directory_base, model_name_for_output, tps_config.backup_subdir)

        if not os.path.exists(material_metadata_path):
            logs += f"❌ クリティカルエラー: マテリアルメタデータファイルが見つかりません: {material_metadata_path}。BlenderNativeTextureFlowは実行できません。\n"
            progress_fn(1.0, "エラー: メタデータなし")
            return None, logs, None
        
        try:
            progress_fn(0.1, "BlenderNativeTextureFlow 初期化中...")
            native_flow = BlenderNativeTextureFlow(
                original_model_path=original_model_path, # BNTF might need the original model directly
                skinned_fbx_path=skinned_fbx_path,       # And the skinned FBX from UniRig
                model_name=model_name_for_output,
                output_dir_base=final_work_dir, # Base for its own subdirectories if it creates them
                blender_executable=APP_CONFIG.blender_settings.blender_executable,
                material_metadata_path=material_metadata_path, # Pass metadata
                texture_backup_path=texture_backup_dir,       # Pass texture backup dir
                config=bntf_config # Pass its specific config
            )
            
            logs += "⚙️ BlenderNativeTextureFlow パイプライン実行中...\n"
            # progress_fn for BNTF:
            # sub_bntf_progress = progress_segment(progress_fn, 0.1, 0.9)
            # final_fbx_path, bntf_logs = native_flow.process_model_with_native_textures(progress_callback=sub_bntf_progress)
            
            progress_fn(0.2, "BNTF: Blender処理中...")
            final_fbx_path, bntf_logs = native_flow.process_model_with_native_textures()
            logs += bntf_logs

            if final_fbx_path and os.path.exists(final_fbx_path):
                logs += f"✅ BlenderNativeTextureFlow 成功。最終FBX: {final_fbx_path}\n"
                progress_fn(0.95, "BNTF: GLBプレビュー生成中...")
                display_path = convert_to_glb_for_display(final_fbx_path, f"{model_name_for_output}_final_native_textured")
            else:
                logs += f"❌ BlenderNativeTextureFlow 失敗。詳細はログを確認してください。\n"
                final_fbx_path = None
        except Exception as e:
            logs += f"❌ BlenderNativeTextureFlow 実行中に予期せぬエラー: {e}\n{traceback.format_exc()}\n"
            final_fbx_path = None
    else:
        # Fallback to old UniRig merge if no advanced texture flow is configured or available
        logs += "⚠️ 高度なテクスチャ処理フローが設定されていません。旧UniRigマージ処理を試みます（テクスチャ品質が低下する可能性があります）。\n"
        # This requires skinning_npz_path, which is not directly available here.
        # This indicates a potential design issue if this fallback is truly desired.
        # For now, let's assume this fallback is not the primary path and might be removed or rethought.
        # If we must call it, we need to fetch skinning_npz_path from a previous step's output.
        # This makes the function signature more complex or reliant on a shared state.
        
        # For now, let's just log that we can't do the old merge without skin_npz
        logs += "❌ 旧UniRigマージ処理は、この関数シグネチャでは直接呼び出せません (skinning_npz_path が必要)。\n"
        logs += "処理を中止します。テクスチャ処理フローを設定してください。\n"
        final_fbx_path = None # Explicitly set to None
        # To actually call old merge:
        # skin_npz_path_for_fallback = ... # This needs to be found or passed
        # display_path, merge_logs_old, final_fbx_path = process_merge_model(
        #     original_model_path, skinned_fbx_path, skin_npz_path_for_fallback, model_name_for_output, progress_fn
        # )
        # logs += merge_logs_old
        
    if final_fbx_path:
        logs += f"✅ 最終マージ処理完了。最終モデル: {final_fbx_path}\n"
        if not display_path: # If display_path wasn't set by the specific flow (e.g. GLB conversion failed)
            logs += "警告: 最終モデルのプレビューGLBの生成に失敗しました。\n"
        progress_fn(1.0, "最終マージ完了")
    else:
        logs += "❌ 最終マージ処理失敗。適切なテクスチャ処理フローが見つからないか、エラーが発生しました。\n"
        progress_fn(1.0, "最終マージエラー")

    return display_path, logs, final_fbx_path

# --- Full Pipeline Handler Function ---
def gradio_full_auto_rigging(
    uploaded_model_path: str,
    gender: str,
    progress=gr.Progress(track_tqdm=True)
):
    """
    フルパイプライン実行: アップロードから最終マージまでの全ステップを自動実行
    """
    logs = "=== UniRig フルパイプライン自動実行開始 ===\n"
    
    # Initialize paths to None for robust logging in error cases
    final_display_path = None
    final_merged_fbx_path = None
    extracted_npz_path = None
    skeleton_display_path = None
    skeleton_fbx_path = None
    skeleton_txt_path = None
    skeleton_npz_path = None
    skinned_display_path = None
    skinned_fbx_path = None
    skinning_npz_path = None # Corrected: was skinnning_npz_path
    
    if not uploaded_model_path:
        logs += "エラー: モデルファイルがアップロードされていません。\n"
        error_output_details = {
            key: locals().get(key) for key in [
                'final_display_path', 'final_merged_fbx_path', 'extracted_npz_path',
                'skeleton_display_path', 'skeleton_fbx_path', 'skeleton_txt_path', 'skeleton_npz_path',
                'skinned_display_path', 'skinned_fbx_path', 'skinning_npz_path', 'uploaded_model_path'
            ]
        }
        log_output_paths_for_debug(error_output_details, "gradio_full_auto_rigging - error: no_upload")
        return None, logs, None, None, None, None, None, None, None, None, None, None

    try:
        # モデル名を抽出
        model_name = os.path.splitext(os.path.basename(uploaded_model_path))[0]
        logs += f"📁 処理モデル: {model_name}\n"
        logs += f"📂 入力ファイル: {uploaded_model_path}\n\n"

        # ステップ1: メッシュ抽出 (0.0-0.25)
        logs += "🔧 ステップ1/4: メッシュ抽出開始\n"
        extract_progress = progress_segment(progress, 0.0, 0.25)
        extract_progress(0.0, "メッシュ抽出中...")
        
        extracted_npz_path, extract_logs = process_extract_mesh(
            uploaded_model_path, 
            model_name,
            extract_progress
        )
        logs += extract_logs
        
        if not extracted_npz_path:
            logs += "❌ メッシュ抽出に失敗しました。処理を中止します。\n"
            error_output_details = { key: locals().get(key) for key in [ 'final_display_path', 'final_merged_fbx_path', 'extracted_npz_path', 'skeleton_display_path', 'skeleton_fbx_path', 'skeleton_txt_path', 'skeleton_npz_path', 'skinned_display_path', 'skinned_fbx_path', 'skinning_npz_path', 'uploaded_model_path'] }
            log_output_paths_for_debug(error_output_details, "gradio_full_auto_rigging - error: mesh_extraction_failed")
            return None, logs, None, None, None, None, None, None, None, None, None, None
        
        logs += f"✅ メッシュ抽出完了: {extracted_npz_path}\n\n"

        # ステップ2: スケルトン生成 (0.25-0.5)
        logs += "🦴 ステップ2/4: スケルトン生成開始\n"
        skeleton_progress = progress_segment(progress, 0.25, 0.5)
        skeleton_progress(0.0, "スケルトン生成中...")
        
        skeleton_display_path, skeleton_logs, skeleton_fbx_path, skeleton_txt_path, skeleton_npz_path = process_generate_skeleton(
            extracted_npz_path,
            model_name,
            gender,
            skeleton_progress
        )
        logs += skeleton_logs
        
        if not skeleton_fbx_path or not skeleton_npz_path:
            logs += "❌ スケルトン生成に失敗しました。処理を中止します。\n"
            error_output_details = { key: locals().get(key) for key in [ 'final_display_path', 'final_merged_fbx_path', 'extracted_npz_path', 'skeleton_display_path', 'skeleton_fbx_path', 'skeleton_txt_path', 'skeleton_npz_path', 'skinned_display_path', 'skinned_fbx_path', 'skinning_npz_path', 'uploaded_model_path'] }
            log_output_paths_for_debug(error_output_details, "gradio_full_auto_rigging - error: skeleton_generation_failed")
            return None, logs, None, extracted_npz_path, skeleton_display_path, None, None, None, None, None, None, None # Pass on what we have
        
        logs += f"✅ スケルトン生成完了: {skeleton_fbx_path}\n\n"

        # ステップ3: スキニング (0.5-0.75)
        logs += "🎨 ステップ3/4: スキニングウェイト予測開始\n"
        skinning_progress = progress_segment(progress, 0.5, 0.75)
        skinning_progress(0.0, "スキニング処理中...")
        
        skinned_display_path, skinning_logs, skinned_fbx_path, skinning_npz_path = process_generate_skin(
            raw_data_npz_path=extracted_npz_path,
            skeleton_fbx_path=skeleton_fbx_path,
            skeleton_npz_path=skeleton_npz_path,
            model_name_for_output=model_name,
            progress_fn=skinning_progress
        )
        logs += skinning_logs
        
        if not skinned_fbx_path or not skinning_npz_path:
            logs += "❌ スキニング処理に失敗しました。処理を中止します。\n"
            error_output_details = { key: locals().get(key) for key in [ 'final_display_path', 'final_merged_fbx_path', 'extracted_npz_path', 'skeleton_display_path', 'skeleton_fbx_path', 'skeleton_txt_path', 'skeleton_npz_path', 'skinned_display_path', 'skinned_fbx_path', 'skinning_npz_path', 'uploaded_model_path'] }
            log_output_paths_for_debug(error_output_details, "gradio_full_auto_rigging - error: skinning_failed")
            return None, logs, None, extracted_npz_path, skeleton_display_path, skeleton_fbx_path, skeleton_txt_path, skeleton_npz_path, skinned_display_path, None, None, None # Pass on what we have
        
        logs += f"✅ スキニング完了: {skinned_fbx_path}\n\n"

        # ステップ4: テクスチャ統合モデルマージ (0.75-1.0)
        logs += "🔗 ステップ4/4: テクスチャ統合モデルマージ開始 (二階建てフロー)\n"
        merge_progress = progress_segment(progress, 0.75, 1.0)
        merge_progress(0.0, "テクスチャ統合処理中...")
        
        final_display_path, merge_logs, final_merged_fbx_path = process_final_merge_with_textures(
            skinned_fbx_path=skinned_fbx_path,
            original_model_path=uploaded_model_path,
            model_name_for_output=model_name,
            progress_fn=merge_progress
        )
        logs += merge_logs
        
        if not final_merged_fbx_path:
            logs += "❌ テクスチャ統合モデルマージに失敗しました。\n"
            error_output_details = { key: locals().get(key) for key in [ 'final_display_path', 'final_merged_fbx_path', 'extracted_npz_path', 'skeleton_display_path', 'skeleton_fbx_path', 'skeleton_txt_path', 'skeleton_npz_path', 'skinned_display_path', 'skinned_fbx_path', 'skinning_npz_path', 'uploaded_model_path'] }
            log_output_paths_for_debug(error_output_details, "gradio_full_auto_rigging - error: merge_failed")
            return None, logs, None, extracted_npz_path, skeleton_display_path, skeleton_fbx_path, skeleton_txt_path, skeleton_npz_path, skinned_display_path, skinned_fbx_path, skinning_npz_path, None # Pass on what we have
        
        logs += f"✅ テクスチャ統合モデルマージ完了: {final_merged_fbx_path}\n\n"

        # 成功メッセージ
        logs += "🎉 === フルパイプライン実行完了 (二階建てフロー) ===\n"
        logs += f"🎯 最終モデル: {final_merged_fbx_path}\n"
        logs += f"📊 テクスチャとマテリアルが保持された高品質なリギング済みモデルが生成されました。\n"
        logs += f"📋 すべての中間ファイルもダウンロード可能です。\n"

        progress(1.0, "フルパイプライン完了!")

        output_details_for_log = {
            "final_display_path": final_display_path,
            "final_merged_fbx_path": final_merged_fbx_path,
            "extracted_npz_path": extracted_npz_path,
            "skeleton_display_path": skeleton_display_path,
            "skeleton_fbx_path": skeleton_fbx_path,
            "skeleton_txt_path": skeleton_txt_path,
            "skeleton_npz_path": skeleton_npz_path,
            "skinned_display_path": skinned_display_path,
            "skinned_fbx_path": skinned_fbx_path,
            "skinning_npz_path": skinning_npz_path,
            "uploaded_model_path": uploaded_model_path
        }
        log_output_paths_for_debug(output_details_for_log, "gradio_full_auto_rigging - success path")

        return (
            final_display_path,
            logs,
            final_merged_fbx_path,
            extracted_npz_path,
            skeleton_display_path,
            skeleton_fbx_path,
            skeleton_txt_path,
            skeleton_npz_path,
            skinned_display_path,
            skinned_fbx_path,
            skinning_npz_path
        )

    except Exception as e:
        error_msg = f"❌ フルパイプライン実行中に予期せぬエラーが発生しました: {str(e)}\n"
        error_msg += f"詳細: {traceback.format_exc()}\n"
        logs += error_msg
        progress(1.0, "フルパイプラインエラー")
        error_output_details = {
            key: locals().get(key) for key in [
                'final_display_path', 'final_merged_fbx_path', 'extracted_npz_path',
                'skeleton_display_path', 'skeleton_fbx_path', 'skeleton_txt_path', 'skeleton_npz_path',
                'skinned_display_path', 'skinned_fbx_path', 'skinning_npz_path', 'uploaded_model_path'
            ]
        }
        log_output_paths_for_debug(error_output_details, "gradio_full_auto_rigging - exception path")
        return None, logs, None, None, None, None, None, None, None, None, None, None

# --- Gradio Handler Functions ---
def gradio_extract_mesh(original_model_path_state: str, model_name_state: str, progress=gr.Progress(track_tqdm=True)):
    logs = "--- Gradio Extract Mesh Wrapper ---\n"
    if not original_model_path_state or not model_name_state:
        logs += "エラー: モデルパスまたはモデル名が提供されていません。ステップ0でモデルをアップロードしてください。\n"
        return logs, gr.DownloadButton(visible=False), None
    
    current_step_progress_fn = progress_segment(progress, 0.0, 1.0)
    current_step_progress_fn(0.0, "メッシュ抽出準備中...")

    extracted_npz_path, process_logs = process_extract_mesh(
        original_model_path_state, 
        model_name_state,
        current_step_progress_fn
    )
    logs += process_logs
    
    if extracted_npz_path:
        logs += "メッシュ抽出成功 (Gradioラッパー)。\n"
        return logs, gr.DownloadButton(label="抽出NPZをダウンロード", value=extracted_npz_path, visible=True), extracted_npz_path
    else:
        logs += "メッシュ抽出失敗 (Gradioラッパー)。\n"
        return logs, gr.DownloadButton(label="抽出NPZをダウンロード", value=None, visible=False), None

def gradio_generate_skeleton(
    raw_data_npz_path_from_state: str, 
    model_name_from_state: str,      
    gender: str,
    progress=gr.Progress(track_tqdm=True)
):
    logs = "--- Gradio Generate Skeleton Wrapper ---\n"
    if not raw_data_npz_path_from_state or not model_name_from_state:
        logs += "エラー: NPZパスまたはモデル名が提供されていません。ステップ0を完了し、モデル名が設定されていることを確認してください。\n"
        return None, logs, None, None, None, None, None 
    
    current_step_progress_fn = progress_segment(progress, 0.0, 1.0)
    current_step_progress_fn(0.0, desc="スケルトン生成準備中...")

    display_model_path, process_logs, fbx_path, txt_path, npz_path = process_generate_skeleton(
        raw_data_npz_path_from_state, 
        model_name_from_state,
        gender,
        current_step_progress_fn
    )
    logs += process_logs

    if display_model_path and fbx_path and npz_path:
        logs += f"✓ スケルトン生成成功。表示モデル: {display_model_path}\n"
    else:
        logs += "スケルトン生成に失敗しました。ログを確認してください。\n"
    
    return (
        display_model_path, 
        logs, 
        fbx_path, 
        txt_path, 
        npz_path, 
        fbx_path, 
        npz_path  
    )

def gradio_generate_skin(
    raw_data_npz_path_from_state: str,   
    skeleton_fbx_path_from_state: str, 
    skeleton_npz_path_from_state: str,  
    model_name_from_state: str,         
    progress=gr.Progress(track_tqdm=True)
):
    logs = "--- Gradio Generate Skin Wrapper ---\n"
    if not (
        raw_data_npz_path_from_state and
        skeleton_fbx_path_from_state and
        skeleton_npz_path_from_state and
        model_name_from_state
    ):
        logs += "エラー: スキニングに必要なパス (raw NPZ, skeleton FBX, skeleton NPZ) またはモデル名が提供されていません。\n"
        return None, logs, None, None, None, None 
    
    current_step_progress_fn = progress_segment(progress, 0.0, 1.0)
    current_step_progress_fn(0.0, desc="スキニングウェイト予測準備中...")

    display_model_path, process_logs, skinned_fbx_path, skinning_npz_path = process_generate_skin(
        raw_data_npz_path=raw_data_npz_path_from_state,
        skeleton_fbx_path=skeleton_fbx_path_from_state,
        skeleton_npz_path=skeleton_npz_path_from_state,
        model_name_for_output=model_name_from_state,
        progress_fn=current_step_progress_fn
    )
    logs += process_logs
    
    if display_model_path and skinned_fbx_path and skinning_npz_path:
        logs += f"✓ スキニングウェイト予測成功。表示モデル: {display_model_path}\n"
        logs += f"  スキン済みFBX: {skinned_fbx_path}\n"
        logs += f"  スキニングNPZ: {skinning_npz_path}\n"
    else:
        logs += "スキニングウェイト予測に失敗しました。\n"

    return (
        display_model_path, 
        logs, 
        skinned_fbx_path, 
        skinning_npz_path, 
        skinned_fbx_path, 
        skinning_npz_path  
    )

def gradio_merge_model_with_textures(
    original_model_path_from_state: str, 
    skinned_fbx_path_from_state: str,   
    model_name_from_state: str,         
    progress=gr.Progress(track_tqdm=True)
):
    """二階建てフローによるテクスチャ統合モデルマージ（ステップバイステップ用）"""
    logs = "--- Gradio Texture-Integrated Merge Model Wrapper (二階建てフロー) ---\n"
    if not (
        original_model_path_from_state and
        skinned_fbx_path_from_state and
        model_name_from_state
    ):
        logs += "エラー: テクスチャ統合モデルマージに必要なパス (オリジナルモデル, スキン済みFBX) またはモデル名が提供されていません。\n"
        return None, logs, None, None
    
    current_step_progress_fn = progress_segment(progress, 0.0, 1.0)
    current_step_progress_fn(0.0, desc="テクスチャ統合モデルマージ準備中...")

    display_model_path, process_logs, final_merged_fbx_path = process_final_merge_with_textures(
        skinned_fbx_path=skinned_fbx_path_from_state,
        original_model_path=original_model_path_from_state,
        model_name_for_output=model_name_from_state,
        progress_fn=current_step_progress_fn
    )
    logs += process_logs

    if display_model_path and final_merged_fbx_path:
        logs += f"✓ テクスチャ統合モデルマージ成功。表示モデル: {display_model_path}\n"
        logs += f"  最終マージ済みFBX (テクスチャ付き): {final_merged_fbx_path}\n"
    else:
        logs += "テクスチャ統合モデルマージに失敗しました。\n"

    return (
        display_model_path,
        logs,
        final_merged_fbx_path, 
        final_merged_fbx_path  
    )

def gradio_merge_model(
    original_model_path_from_state: str, 
    skinned_fbx_path_from_state: str,   
    skinning_npz_path_from_state: str,  
    model_name_from_state: str,         
    progress=gr.Progress(track_tqdm=True)
):
    logs = "--- Gradio Merge Model Wrapper (従来フロー) ---\n"
    if not (
        original_model_path_from_state and
        skinned_fbx_path_from_state and
        skinning_npz_path_from_state and
        model_name_from_state
    ):
        logs += "エラー: モデルマージに必要なパス (オリジナルモデル, スキン済みFBX, スキニングNPZ) またはモデル名が提供されていません。\n"
        return None, logs, None, None
    
    current_step_progress_fn = progress_segment(progress, 0.0, 1.0)
    current_step_progress_fn(0.0, desc="モデルマージ準備中...")

    display_model_path, process_logs, final_merged_fbx_path = process_merge_model(
        original_model_path=original_model_path_from_state,
        skinned_fbx_path=skinned_fbx_path_from_state,
        skinning_npz_path=skinning_npz_path_from_state,
        model_name_for_output=model_name_from_state,
        progress_fn=current_step_progress_fn
    )
    logs += process_logs

    if display_model_path and final_merged_fbx_path:
        logs += f"✓ モデルマージ成功。表示モデル: {display_model_path}\n"
        logs += f"  最終マージ済みFBX: {final_merged_fbx_path}\n"
    else:
        logs += "モデルマージに失敗しました。\n"

    return (
        display_model_path,
        logs,
        final_merged_fbx_path, 
        final_merged_fbx_path 
    )

# --- Gradio UI Builder ---
def build_gradio_interface():
    with gr.Blocks(theme=gr.themes.Base()) as demo:
        s_original_model_path = gr.State()
        s_model_name = gr.State()
        s_extracted_npz_path = gr.State()
        s_skeleton_fbx_path = gr.State()
        s_skeleton_txt_path = gr.State() # Added state for this
        s_skeleton_npz_path = gr.State()
        s_skinned_fbx_path = gr.State()
        s_skinning_npz_path = gr.State()
        s_merged_fbx_path = gr.State()
        
        gr.Markdown("<h1>UniRig 3Dモデル自動リギングアプリケーション</h1>")
        gr.Markdown("3Dモデル（FBX、OBJ、GLB/GLTF、PLYなどTrimeshが扱える形式）をアップロードし、自動でリギング処理を行います。")
        gr.Markdown("""
        **🆕 二階建てフローによる高品質テクスチャ保持:**
        - **第1階層**: 元モデルからテクスチャ・マテリアル情報を抽出・保存
        - **第2階層**: スキニング済みモデルに保存されたテクスチャを適用
        - **結果**: テクスチャとマテリアル品質を完全に保持したリギング済みモデル
        
        フルパイプラインでは自動的に二階建てフローが適用されます。
        """)

        with gr.Tab("フルパイプライン実行"):
            gr.Markdown("""
            ## 🚀 ワンクリックで完全自動リギング
            
            **二階建てフロー技術による高品質処理:**
            1. **メッシュ抽出** → 3Dモデルの構造解析
            2. **スケルトン生成** → AI による最適な骨格構造予測
            3. **スキニング処理** → 頂点ウェイト自動計算
            4. **テクスチャ統合マージ** → 元の品質を保持した最終結合
            
            ✨ **従来方式との違い**: テクスチャ・マテリアル情報を完全保持し、高品質な仕上がりを実現
            """)
            
            with gr.Row():
                with gr.Column(scale=1):
                    full_input_model_upload = gr.File(label="3Dモデルをアップロード", file_types=[".fbx", ".obj", ".glb", ".gltf", ".ply"], type="filepath")
                    full_gender_dropdown = gr.Dropdown(label="性別（スケルトン生成用）", choices=["female", "male", "neutral"], value="female")
                    full_pipeline_button = gr.Button("🎯 フルパイプライン実行", variant="primary", size="lg")
                with gr.Column(scale=2):
                    full_final_model_display = gr.Model3D(label="最終リギング済みモデルプレビュー", interactive=False, camera_position=(0, 2.5, 3.5))
            
            full_pipeline_logs = gr.Textbox(label="フルパイプラインログ", lines=15, interactive=False, show_copy_button=True)
            
            with gr.Accordion("📁 中間成果物のダウンロードとプレビュー", open=False):
                gr.Markdown("### 処理段階別の成果物")
                gr.Markdown("各処理段階で生成されるファイルをダウンロード・プレビューできます。")
                
                gr.Markdown("#### 🔧 ステップ1: メッシュ抽出結果")
                full_extracted_npz_download = gr.DownloadButton(label="📦 抽出NPZ", interactive=True, visible=False)
                
                gr.Markdown("#### 🦴 ステップ2: スケルトン生成結果")
                full_skeleton_model_display = gr.Model3D(label="スケルトンモデルプレビュー", interactive=False, camera_position=(0, 2.5, 3.5), visible=False)
                with gr.Row():
                    full_skeleton_fbx_download = gr.DownloadButton(label="🦴 スケルトン (FBX)", interactive=True, visible=False)
                    full_skeleton_txt_download = gr.DownloadButton(label="📄 スケルトン (TXT)", interactive=True, visible=False)
                    full_skeleton_npz_download = gr.DownloadButton(label="📦 スケルトン (NPZ)", interactive=True, visible=False)

                gr.Markdown("#### 🎨 ステップ3: スキニングウェイト予測結果")
                full_skinned_model_display = gr.Model3D(label="スキン済みモデルプレビュー", interactive=False, camera_position=(0, 2.5, 3.5), visible=False)
                with gr.Row():
                    full_skinned_model_fbx_download = gr.DownloadButton(label="🎨 スキン済み (FBX)", interactive=True, visible=False)
                    full_skinning_npz_download = gr.DownloadButton(label="📦 スキニング (NPZ)", interactive=True, visible=False)
                
                gr.Markdown("#### 🎯 ステップ4: 最終マージモデル")
                full_final_model_download_accordion = gr.DownloadButton(label="🎯 最終モデル (FBX)", interactive=True, visible=False)

            full_pipeline_button.click(
                fn=gradio_full_auto_rigging,
                inputs=[
                    full_input_model_upload, 
                    full_gender_dropdown
                ],
                outputs=[
                    full_final_model_display, full_pipeline_logs, full_final_model_download_accordion,
                    full_extracted_npz_download,
                    full_skeleton_model_display, 
                    full_skeleton_fbx_download, full_skeleton_txt_download, full_skeleton_npz_download,
                    full_skinned_model_display,
                    full_skinned_model_fbx_download, full_skinning_npz_download
                ],
                api_name="run_full_auto_rigging"
            ).then(
                fn=lambda d1, d2, d3, d4, d5, d6, d7, d8, d9, d10, d11: (
                    gr.update(visible=d1 is not None and d1 != ''), 
                    gr.update(visible=d3 is not None and d3 != ''), 
                    gr.update(visible=d4 is not None and d4 != ''), 
                    gr.update(visible=d5 is not None and d5 != ''), 
                    gr.update(visible=d6 is not None and d6 != ''), 
                    gr.update(visible=d7 is not None and d7 != ''), 
                    gr.update(visible=d8 is not None and d8 != ''), 
                    gr.update(visible=d9 is not None and d9 != ''), 
                    gr.update(visible=d10 is not None and d10 != ''),
                    gr.update(visible=d11 is not None and d11 != '') 
                ),
                inputs=[
                    full_final_model_display, full_pipeline_logs, full_final_model_download_accordion,
                    full_extracted_npz_download, full_skeleton_model_display, 
                    full_skeleton_fbx_download, full_skeleton_txt_download, full_skeleton_npz_download,
                    full_skinned_model_display, full_skinned_model_fbx_download, full_skinning_npz_download
                ],
                outputs=[
                    full_final_model_display, full_final_model_download_accordion,
                    full_extracted_npz_download, full_skeleton_model_display,
                    full_skeleton_fbx_download, full_skeleton_txt_download, full_skeleton_npz_download,
                    full_skinned_model_display, full_skinned_model_fbx_download, full_skinning_npz_download
                ],
                api_name=False # No need for a separate API endpoint for this UI update
            )

        with gr.Tab("ステップバイステップ実行"):
            gr.Markdown("""
            ## 🛠️ 段階的な処理実行
            
            各処理ステップを個別に実行し、中間結果を確認しながら進めることができます。
            処理の仕組みを理解したい場合や、特定のステップで問題が発生した場合の診断に有用です。
            """)
            
            gr.Markdown("### 🔧 ステップ0: 初期設定とメッシュ抽出")
            with gr.Row():
                step_upload_button = gr.File(label="1. 3Dモデルをアップロード", file_types=[".fbx", ".obj", ".glb", ".gltf", ".ply"], type="filepath")
                step_input_model_display_step0 = gr.Model3D(label="アップロードモデルプレビュー", interactive=False, camera_position=(0, 2.5, 3.5))
            
            btn_run_extract = gr.Button("🔧 0. メッシュ抽出実行", variant="primary")
            step_extract_logs = gr.Textbox(label="抽出ログ", lines=5, interactive=False, show_copy_button=True)
            step_extracted_model_download = gr.DownloadButton(label="📦 抽出NPZ", interactive=True, visible=False)

            gr.Markdown("### 🦴 ステップ1: スケルトン生成")
            step_gender_dropdown = gr.Dropdown(label="性別（スケルトン生成用）", choices=["female", "male", "neutral"], value="female")
            btn_run_skeleton = gr.Button("🦴 1. スケルトン生成実行", variant="primary")
            step_skeleton_model_display = gr.Model3D(label="スケルトンモデルプレビュー", interactive=False, camera_position=(0, 2.5, 3.5))
            step_skeleton_logs = gr.Textbox(label="スケルトン生成ログ", lines=5, interactive=False, show_copy_button=True)
            with gr.Row():
                step_skeleton_fbx_download = gr.DownloadButton(label="🦴 スケルトン (FBX)", interactive=True, visible=False)
                step_skeleton_txt_download = gr.DownloadButton(label="📄 スケルトン (TXT)", interactive=True, visible=False)
                step_skeleton_npz_download = gr.DownloadButton(label="📦 スケルトン (NPZ)", interactive=True, visible=False)

            gr.Markdown("### 🎨 ステップ2: スキニングウェイト予測")
            btn_run_skin = gr.Button("🎨 2. スキニングウェイト予測実行", variant="primary")
            step_skinned_model_display = gr.Model3D(label="スキン済みモデルプレビュー", interactive=False, camera_position=(0, 2.5, 3.5))
            step_skin_logs = gr.Textbox(label="スキニングログ", lines=5, interactive=False, show_copy_button=True)
            with gr.Row():
                step_skinned_model_fbx_download = gr.DownloadButton(label="🎨 スキン済み (FBX)", interactive=True, visible=False)
                step_skinning_npz_download = gr.DownloadButton(label="📦 スキニング (NPZ)", interactive=True, visible=False)

            gr.Markdown("### 🔗 ステップ3: モデルマージ")
            with gr.Row():
                btn_run_merge = gr.Button("🔗 3a. 従来モデルマージ実行", variant="secondary")
                btn_run_merge_with_textures = gr.Button("✨ 3b. テクスチャ統合マージ実行 (推奨)", variant="primary")
            step_merged_model_display = gr.Model3D(label="最終マージモデルプレビュー", interactive=False, camera_position=(0, 2.5, 3.5))
            step_merge_logs = gr.Textbox(label="マージログ", lines=5, interactive=False, show_copy_button=True)
            step_merged_model_download = gr.DownloadButton(label="🎯 最終モデル (FBX)", interactive=True, visible=False)
            
            with gr.Accordion("💡 二階建てフローについて", open=False):
                gr.Markdown("""
                ### 🏗️ 二階建てフロー技術の詳細
                
                **従来の問題点:**
                - リギング処理中にテクスチャ・マテリアル情報が失われる
                - 最終モデルの見た目が元モデルと異なってしまう
                - 手動でのテクスチャ復元作業が必要
                
                **二階建てフローの解決策:**
                
                **🏗️ 第1階層 - テクスチャ保存:**
                1. 元モデルからテクスチャ画像を抽出・保存
                2. マテリアル構造（ノード接続）情報を記録
                3. メッシュ-マテリアル対応関係を保存
                
                **🏗️ 第2階層 - テクスチャ復元:**
                1. スキニング済みFBXを読み込み
                2. 保存されたテクスチャを再適用
                3. マテリアル構造を完全再構築
                4. FBX互換性を考慮した最適化
                
                **✨ 結果:**
                - 元モデルと同品質のテクスチャ・マテリアル
                - 完全なリギング機能
                - 安定したエラー処理とフォールバック機能
                
                **推奨使用場面:**
                - 高品質な3Dモデルのリギング
                - ゲーム・アニメーション用アセット作成
                - 商用プロジェクトでの利用
                """)
            
            gr.Markdown("""
            **💡 二階建てフローの選択について:**
            - **3a. 従来モデルマージ**: スキニング済みFBXをオリジナルモデルにマージします（旧方式）
            - **3b. テクスチャ統合マージ (推奨)**: 元モデルのテクスチャ・マテリアルを保持しながらマージします（新方式、高品質）
            
            **推奨**: より高品質な結果を得るため「✨ テクスチャ統合マージ」をご利用ください。
            """)

            # Event handlers for step-by-step execution
            def handle_upload_step(file_path_obj): # Gradio File component with type="filepath" returns a string path
                if file_path_obj:
                    original_path = file_path_obj # This is now a string path
                    model_name_val = os.path.splitext(os.path.basename(original_path))[0]
                    glb_for_display = convert_to_glb_for_display(original_path, f"{model_name_val}_original_display_step")
                    
                   
                    
                    # Reset logs and subsequent step outputs/states
                    extract_log_msg = f"アップロード完了: {model_name_val}。抽出を実行してください。"
                    return (
                        original_path, model_name_val, glb_for_display, 
                        extract_log_msg, gr.DownloadButton(visible=False), None, # Extract
                        None, "", gr.DownloadButton(visible=False), gr.DownloadButton(visible=False), gr.DownloadButton(visible=False), None, None, None, # Skeleton
                        None, "", gr.DownloadButton(visible=False), gr.DownloadButton(visible=False), None, None, # Skin
                        None, "", gr.DownloadButton(visible=False), None # Merge
                    )
                # No file uploaded or cleared
                return None, None, None, "ファイルをアップロードしてください。", gr.DownloadButton(visible=False), None, None, "", gr.DownloadButton(visible=False), gr.DownloadButton(visible=False), gr.DownloadButton(visible=False), None, None, None, None, "", gr.DownloadButton(visible=False), gr.DownloadButton(visible=False), None, None, None, "", gr.DownloadButton(visible=False), None

            step_upload_button.change( # Use .change for File component when type="filepath"
                fn=handle_upload_step,
                inputs=[step_upload_button],
                outputs=[
                    s_original_model_path, s_model_name, step_input_model_display_step0, 
                    step_extract_logs, step_extracted_model_download, s_extracted_npz_path,
                    step_skeleton_model_display, step_skeleton_logs, step_skeleton_fbx_download, step_skeleton_txt_download, step_skeleton_npz_download,
                    s_skeleton_fbx_path, s_skeleton_txt_path, s_skeleton_npz_path,
                    step_skinned_model_display, step_skin_logs, step_skinned_model_fbx_download, step_skinning_npz_download,
                    s_skinned_fbx_path, s_skinning_npz_path,
                    step_merged_model_display, step_merge_logs, step_merged_model_download,
                    s_merged_fbx_path
                ],
                api_name=False
            )
            
            btn_run_extract.click(
                fn=gradio_extract_mesh,
                inputs=[s_original_model_path, s_model_name],
                outputs=[step_extract_logs, step_extracted_model_download, s_extracted_npz_path],
                api_name="run_extract_mesh_step"
            )
            
            btn_run_skeleton.click(
                fn=gradio_generate_skeleton,
                inputs=[
                    s_extracted_npz_path, # from step 0
                    s_model_name,         # from step 0
                    step_gender_dropdown  # Add gender dropdown
                ],
                outputs=[
                    step_skeleton_model_display, 
                    step_skeleton_logs,
                    step_skeleton_fbx_download,
                    step_skeleton_txt_download,
                    step_skeleton_npz_download,
                    s_skeleton_fbx_path, # State update
                    s_skeleton_npz_path  # State update
                ]
            ).then(
                fn=lambda d1, d2, d3, d4, d5: (gr.update(visible=d1 is not None and d1!=''), gr.update(visible=d2 is not None and d2!=''), gr.update(visible=d3 is not None and d3!=''), gr.update(visible=d4 is not None and d4!=''), gr.update(visible=d5 is not None and d5!='')),
                inputs=[step_skeleton_model_display, step_skeleton_fbx_download, step_skeleton_txt_download, step_skeleton_npz_download, step_skeleton_logs],
                outputs=[step_skeleton_model_display, step_skeleton_fbx_download, step_skeleton_txt_download, step_skeleton_npz_download, step_skeleton_logs],
                api_name=False
            )

            btn_run_skin.click(
                fn=gradio_generate_skin,
                inputs=[
                    s_extracted_npz_path, # raw_data_npz_path - from step 0
                    s_skeleton_fbx_path,  # skeleton_fbx_path - from step 1
                    s_skeleton_npz_path,  # skeleton_npz_path - from step 1
                    s_model_name          # model_name - from step 0
                ],
                outputs=[
                    step_skinned_model_display, step_skin_logs, 
                    step_skinned_model_fbx_download, step_skinning_npz_download,
                    s_skinned_fbx_path, s_skinning_npz_path
                ],
                api_name="run_generate_skin_step"
            )

            btn_run_merge.click(
                fn=gradio_merge_model,
                inputs=[s_original_model_path, s_skinned_fbx_path, s_skinning_npz_path, s_model_name],
                outputs=[
                    step_merged_model_display, step_merge_logs, 
                    step_merged_model_download, 
                    s_merged_fbx_path
                ],
                api_name="run_merge_model_step"
            )

            btn_run_merge_with_textures.click(
                fn=gradio_merge_model_with_textures,
                inputs=[s_original_model_path, s_skinned_fbx_path, s_model_name],
                outputs=[
                    step_merged_model_display, step_merge_logs, 
                    step_merged_model_download, 
                    s_merged_fbx_path
                ],
                api_name="run_merge_model_with_textures_step"
            )
        
        demo.queue() # Ensure queue is enabled for the demo
            
    return demo

if __name__ == "__main__":
    load_app_config() 

    if not APP_CONFIG or APP_CONFIG.get('error'): # Check for error during load
        logging.error(f"アプリケーション設定のロードに失敗しました。エラー: {APP_CONFIG.get('error', 'Unknown error')}。起動を中止します。")
        sys.exit(1)

    gradio_config = APP_CONFIG.get('gradio_interface', {})
    server_name = gradio_config.get('server_name', '0.0.0.0')
    base_port = int(gradio_config.get('server_port', 7860))
    share_gradio = gradio_config.get('share', False)
    inbrowser = gradio_config.get('inbrowser', True)
    
    import socket
    def find_free_port(start_port, max_attempts=10):
        for port in range(start_port, start_port + max_attempts):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(('', port))
                    return port
                except OSError:
                    logging.warning(f"ポート {port} は使用中です。次のポートを試します...")
                    continue
        return None
    
    server_port = find_free_port(base_port)
    if server_port is None:
        logging.error(f"利用可能なポートが見つかりません（{base_port}から{base_port+9}まで試行）")
        sys.exit(1)

    logging.info(f"Gradioサーバーを起動します: http://{server_name}:{server_port}")
    if share_gradio:
        logging.info("Gradio共有が有効になっています。")

    iface = build_gradio_interface()
    
    allowed_paths_list = get_allowed_paths()
    
    # Ensure debug mode is True for this session, overriding config if necessary for debugging
    # server_debug_mode = APP_CONFIG.server.get('debug_mode', False) # Get from config
    # logging.info(f"設定ファイルからのデバッグモード: {server_debug_mode}")
    
    iface.launch(
        server_name=server_name, 
        server_port=server_port, 
        share=share_gradio, 
        inbrowser=inbrowser,
        debug=True, # Force debug=True for this debugging session
        allowed_paths=allowed_paths_list
    )