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

# --- Global Configuration and Setup ---
APP_CONFIG = None
TEMP_FILES_TO_CLEAN = []

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_app_config(config_path='configs/app_config.yaml'):
    global APP_CONFIG
    try:
        # Ensure the config path is absolute, assuming it's relative to this script's directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        abs_config_path = os.path.join(script_dir, config_path)
        
        logging.info(f"設定ファイルパスを解決中: {abs_config_path}")

        with open(abs_config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        APP_CONFIG = Box(config_data)
        
        base_work_dir = os.path.abspath(os.path.join(script_dir, APP_CONFIG.working_directory_base))
        APP_CONFIG.working_directory_base = base_work_dir # Update to absolute path
        os.makedirs(base_work_dir, exist_ok=True)

        for stage_key in ['mesh_extraction', 'skeleton_generation', 'skinning_prediction', 'model_merging', 'blender_processing']:
            if stage_key in APP_CONFIG:
                config_section = APP_CONFIG[stage_key]
                subdir_key_map = {
                    'mesh_extraction': 'extract_output_subdir',
                    'skeleton_generation': 'skeleton_output_subdir',
                    'skinning_prediction': 'skin_output_subdir',
                    'model_merging': 'merge_output_subdir',
                    'blender_processing': 'conversion_output_subdir'
                }
                if subdir_key_map.get(stage_key) and config_section.get(subdir_key_map.get(stage_key)):
                    # Ensure subdirectories are also created relative to the (now absolute) base_work_dir
                    subdir_path = os.path.join(base_work_dir, config_section[subdir_key_map.get(stage_key)])
                    os.makedirs(subdir_path, exist_ok=True)
        
        logging.info(f"アプリケーション設定を '{abs_config_path}' から正常にロードしました。")
        logging.info(f"作業ディレクトリベース: {base_work_dir}")

    except FileNotFoundError:
        logging.error(f"設定ファイルが見つかりません: {abs_config_path if 'abs_config_path' in locals() else config_path}")
        sys.exit("設定ファイルが見つかりません。アプリケーションを起動できません。")
    except yaml.YAMLError as e:
        logging.error(f"設定ファイルの解析中にエラーが発生しました: {e}")
        sys.exit("設定ファイルの形式が正しくありません。")
    except Exception as e:
        logging.error(f"設定のロード中に予期せぬエラーが発生しました: {e}")
        logging.error(traceback.format_exc())
        sys.exit(f"設定のロードエラー: {e}")

def add_to_cleanup_list(item_path):
    if item_path not in TEMP_FILES_TO_CLEAN:
        TEMP_FILES_TO_CLEAN.append(item_path)
        logging.debug(f"クリーンアップリストに追加: {item_path}")

def cleanup_temp_files():
    logging.info("一時ファイルとディレクトリのクリーンアップを開始します...")
    cleaned_count = 0
    error_count = 0
    for item_path in TEMP_FILES_TO_CLEAN:
        try:
            if os.path.isfile(item_path):
                os.remove(item_path)
                logging.info(f"削除されたファイル: {item_path}")
                cleaned_count += 1
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
                logging.info(f"削除されたディレクトリ: {item_path}")
                cleaned_count += 1
            else:
                logging.warning(f"クリーンアップ対象が見つかりません (既に削除されたか、パスが間違っています): {item_path}")
        except Exception as e:
            logging.error(f"アイテムの削除中にエラーが発生しました {item_path}: {e}")
            error_count += 1
    logging.info(f"一時ファイルのクリーンアップが完了しました。{cleaned_count} 個のアイテムを処理し、{error_count} 個のエラーが発生しました。")

atexit.register(cleanup_temp_files)

# --- Utility Functions ---
def run_script(command_parts, working_directory=None, script_name="スクリプト", env=None):
    logs = f"--- {script_name}実行開始 ---\n"
    logs += f"コマンド: {' '.join(command_parts)}\n"
    if working_directory:
        logs += f"作業ディレクトリ: {working_directory}\n"
    else:
        logs += f"作業ディレクトリ: {os.getcwd()} (デフォルト)\n"
    
    # Use provided environment or copy current environment
    if env is None:
        env = os.environ.copy()
    
    try:
        process = subprocess.Popen(
            command_parts,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=working_directory,
            env=env  # Use the provided environment
        )
        stdout, stderr = process.communicate()
        
        if stdout:
            logs += f"標準出力:\n{stdout}"
        if stderr:
            logs += f"標準エラー:\n{stderr}"
        
        if process.returncode == 0:
            logs += f"\n✓ {script_name} は正常に完了しました。\n"
            return True, logs
        else:
            # Special handling for Blender's common SIGSEGV (-11) after successful processing
            if process.returncode == -11 and script_name == "メッシュ抽出":
                logs += f"\n⚠️ {script_name} はBlenderの異常終了（コード {process.returncode}）で終了しましたが、処理は完了している可能性があります。\n"
                logs += "注意: これはBlenderの既知の問題で、ファイル生成が成功していれば正常です。\n"
            elif process.returncode == 139 and script_name == "メッシュ抽出":  # Another common Blender exit code
                logs += f"\n⚠️ {script_name} はBlenderのセグメンテーションフォルト（コード {process.returncode}）で終了しましたが、処理は完了している可能性があります。\n"
                logs += "注意: これはBlenderの既知の問題で、ファイル生成が成功していれば正常です。\n"
            else:
                logs += f"\nX {script_name} はエラーコード {process.returncode} で失敗しました。\n"
            return False, logs
            
    except FileNotFoundError:
        logs += f"X エラー: {script_name} の実行可能ファイルが見つかりません ({command_parts[0]})。パスを確認してください。\n"
        return False, logs
    except Exception as e:
        logs += f"X {script_name} の実行中に予期せぬエラーが発生しました: {str(e)}\n"
        logs += f"詳細: {traceback.format_exc()}\n"
        return False, logs

def convert_to_glb_for_display(fbx_path, output_name_stem, working_dir_override=None):
    """
    FBXファイルをBlenderを使用してGLBに変換し、表示に適したパスを返します。
    
    Args:
        fbx_path: 変換するFBXファイルのパス
        output_name_stem: 出力ファイル名のベース
        working_dir_override: 作業ディレクトリのオーバーライド（未使用）
    
    Returns:
        str or None: 変換されたGLBファイルのパス、または変換に失敗した場合は元のFBXパス、エラーの場合はNone
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))

    if not fbx_path or not os.path.exists(fbx_path):
        logging.error(f"変換するFBXファイルが見つかりません: {fbx_path}")
        return None

    blender_config = APP_CONFIG.blender
    blender_executable = blender_config.executable_path
    
    # conversion_script path should be relative to app.py or an absolute path in config
    conversion_script_path_from_config = blender_config.get('conversion_script_path', 'blender/fbx_to_glb_converter.py')
    if not os.path.isabs(conversion_script_path_from_config):
        conversion_script = os.path.join(script_dir, conversion_script_path_from_config)
    else:
        conversion_script = conversion_script_path_from_config
    
    base_work_dir = APP_CONFIG.working_directory_base
    conversion_output_subdir = blender_config.get('conversion_output_subdir', '05_blender_conversions')
    conversion_output_dir = os.path.join(base_work_dir, conversion_output_subdir, output_name_stem)
    os.makedirs(conversion_output_dir, exist_ok=True)
    add_to_cleanup_list(conversion_output_dir)

    output_glb_filename = f"{output_name_stem}.glb"
    output_glb_path = os.path.join(conversion_output_dir, output_glb_filename)

    # Check for Blender executable
    if not os.path.exists(blender_executable):
        # Try to find Blender in PATH if an absolute path isn't working or provided
        blender_in_path = shutil.which("blender")
        if blender_in_path:
            blender_executable = blender_in_path
            logging.info(f"BlenderをPATHで見つけました: {blender_executable}")
        else:
            logging.warning(f"Blender実行可能ファイルが見つかりません。FBXファイルをそのまま返します: {blender_executable}")
            return fbx_path
            
    # Check for conversion script
    if not os.path.exists(conversion_script):
        logging.warning(f"Blender変換スクリプトが見つかりません。FBXファイルをそのまま返します: {conversion_script}")
        return fbx_path

    cmd = [
        blender_executable,
        "--background",
        "--python", conversion_script,
        "--",
        os.path.abspath(fbx_path),
        os.path.abspath(output_glb_path)
    ]
    
    logging.info(f"Blender GLB変換コマンド: {' '.join(cmd)}")
    success, logs_run_script = run_script(cmd, script_name="Blender GLB変換")
    logging.info(logs_run_script)

    if success and os.path.exists(output_glb_path) and os.path.getsize(output_glb_path) > 0:
        logging.info(f"GLB変換成功: {output_glb_path}")
        return output_glb_path
    else:
        logging.error(f"GLB変換失敗、または空のファイルが生成されました。ログを確認してください。FBXパス: {fbx_path}, GLBパス: {output_glb_path}")
        if os.path.exists(output_glb_path) and os.path.getsize(output_glb_path) == 0:
            logging.warning(f"生成されたGLBファイルは空です: {output_glb_path}")
        # Return original FBX file as fallback
        return fbx_path

def progress_segment(progress_gradio: gr.Progress | None, start_fraction: float, end_fraction: float):
    if progress_gradio is None:
        # Return a dummy progress function if no Gradio progress object is provided
        def dummy_progress(current_progress_within_segment, desc=""):
            pass # Do nothing
        return dummy_progress
        
    def progress_wrapper(current_progress_within_segment, desc=""):
        actual_progress = start_fraction + (current_progress_within_segment * (end_fraction - start_fraction))
        progress_gradio(min(max(actual_progress, 0.0), 1.0), desc=desc) # Clamp progress
    return progress_wrapper

# --- Core Processing Functions ---
def process_extract_mesh(original_model_path, model_name_for_output, progress_fn):
    logs = f"--- ステップ0: メッシュ抽出開始 ({model_name_for_output}) ---\n"
    if not APP_CONFIG:
        logs += "エラー: アプリケーション設定がロードされていません。\n"
        return None, logs

    script_dir = os.path.dirname(os.path.abspath(__file__))
    extract_config = APP_CONFIG.mesh_extraction
    base_work_dir = APP_CONFIG.working_directory_base # Absolute path
    
    extract_subdir_name = extract_config.extract_output_subdir
    python_script_rel_path = extract_config.python_script_path
    output_npz_filename_template = extract_config.output_npz_filename

    stage_output_dir = os.path.join(base_work_dir, extract_subdir_name, model_name_for_output)
    os.makedirs(stage_output_dir, exist_ok=True)
    add_to_cleanup_list(stage_output_dir)
    logs += f"メッシュ抽出ステージ出力ディレクトリ: {stage_output_dir}\n"

    output_npz_filename = output_npz_filename_template.format(model_name=model_name_for_output)
    final_npz_output_path = os.path.join(stage_output_dir, output_npz_filename)
    
    extract_script_abs_path = os.path.join(script_dir, python_script_rel_path)

    if not original_model_path or not os.path.exists(original_model_path):
        logs += f"エラー: 入力モデルパスが見つかりません: {original_model_path}\n"
        return None, logs
    if not os.path.exists(extract_script_abs_path):
        logs += f"エラー: 抽出スクリプトが見つかりません: {extract_script_abs_path}\n"
        return None, logs

    # Set PYTHONPATH to include the src directory for proper imports
    env = os.environ.copy()
    env['PYTHONPATH'] = f"{script_dir}:{env.get('PYTHONPATH', '')}"
    env['GRADIO'] = '1'  # Signal that we're running in Gradio environment
    
    # Use a basic extract config - create one if needed
    extract_config_path = os.path.join(script_dir, "configs", "extract_config.yaml")
    if not os.path.exists(extract_config_path):
        # Create a minimal config file for extraction
        os.makedirs(os.path.dirname(extract_config_path), exist_ok=True)
        minimal_config = {
            'verbose': True,
            'remove_duplicated_vertices': True,
            'merge_vertices': True
        }
        with open(extract_config_path, 'w') as f:
            yaml.dump(minimal_config, f)
        logs += f"作成した抽出設定ファイル: {extract_config_path}\n"
    
    cmd = [
        sys.executable, "-m", "src.data.extract",  # Run as Python module
        "--config", extract_config_path,
        "--model_path", os.path.abspath(original_model_path),
        "--output_dir", os.path.abspath(stage_output_dir)
    ]
    
    logs += f"実行コマンド: {' '.join(cmd)}\n"
    logs += f"PYTHONPATH: {env['PYTHONPATH']}\n"
    progress_fn(0.1, desc="メッシュ抽出処理中...")

    # Update run_script call to pass the modified environment
    success, script_output = run_script(cmd, working_directory=script_dir, script_name="メッシュ抽出", env=env)
    logs += script_output

    # The extract script saves as "raw_data.npz" in the output directory
    actual_npz_output_path = os.path.join(stage_output_dir, "raw_data.npz")
    
    # Check if output file exists and is valid first (prioritize file existence over exit code)
    # Blender often exits with SIGSEGV (-11) even after successful processing
    if not os.path.exists(actual_npz_output_path) or os.path.getsize(actual_npz_output_path) == 0:
        logs += "期待されるNPZファイルが生成されませんでした（または空です）。\n"
        logs += f"期待されたファイル: {actual_npz_output_path}\n"
        # List files in output directory for debugging
        if os.path.exists(stage_output_dir):
            files_in_dir = os.listdir(stage_output_dir)
            logs += f"出力ディレクトリの内容: {files_in_dir}\n"
        # Only mention script failure if file is also missing
        if not success:
            logs += f"注意: スクリプトは異常終了しました（終了コード）が、出力ファイルも生成されていません。\n"
        return None, logs
    
    # File exists and is valid - extraction succeeded even if Blender crashed
    if not success:
        logs += f"X メッシュ抽出 はエラーコード -11 で失敗しました。\n"
        logs += f"注意: Blenderは異常終了しましたが、NPZファイルは正常に生成されました。\n"

    logs += f"✓ メッシュ抽出成功。NPZファイル: {actual_npz_output_path}\n\n"
    progress_fn(1.0, desc="メッシュ抽出完了") # 1.0 for this segment
    return actual_npz_output_path, logs

def process_generate_skeleton(extracted_npz_path, model_name_for_output, gender, progress_fn):
    logs = f"--- ステップ1: スケルトン生成開始 ({model_name_for_output}, 性別: {gender}) ---\n"
    if not APP_CONFIG:
        logs += "エラー: アプリケーション設定がロードされていません。\n"
        return None, logs, None, None, None

    script_dir = os.path.dirname(os.path.abspath(__file__))
    skeleton_config = APP_CONFIG.skeleton_generation
    base_work_dir = APP_CONFIG.working_directory_base

    skeleton_subdir_name = skeleton_config.skeleton_output_subdir
    if gender == "female":
        task_template_rel_path = skeleton_config.task_config_template_female
    elif gender == "male":
        task_template_rel_path = skeleton_config.task_config_template_male
    elif gender == "neutral":
        task_template_rel_path = skeleton_config.task_config_template_neutral
    else:
        logs += f"エラー: 無効な性別指定 '{gender}'。'female'、'male'、または 'neutral' を使用してください。\n"
        return None, logs, None, None, None
        
    output_fbx_filename = skeleton_config.output_fbx_filename
    output_txt_filename = skeleton_config.output_txt_filename
    output_npz_filename = skeleton_config.output_npz_filename
    datalist_filename = skeleton_config.datalist_filename
    seed = skeleton_config.seed

    stage_output_dir = os.path.join(base_work_dir, skeleton_subdir_name, model_name_for_output)
    os.makedirs(stage_output_dir, exist_ok=True)
    add_to_cleanup_list(stage_output_dir)
    logs += f"スケルトン生成ステージ出力ディレクトリ: {stage_output_dir}\n"

    operation_temp_dir = tempfile.mkdtemp(prefix=f"unirig_skel_{model_name_for_output}_")
    add_to_cleanup_list(operation_temp_dir)
    logs += f"一時設定ディレクトリ: {operation_temp_dir}\n"
    
    if not extracted_npz_path or not os.path.exists(extracted_npz_path):
        logs += f"エラー: スケルトン生成のための抽出NPZパスが無効です: {extracted_npz_path}\n"
        return None, logs, None, None, None

    # For run.py, we need to pass the NPZ file directly as input
    # Create a simple text file listing the NPZ file path for the data loader
    dynamic_datalist_content = os.path.abspath(extracted_npz_path)
    dynamic_datalist_path = os.path.join(operation_temp_dir, datalist_filename)
    with open(dynamic_datalist_path, 'w') as f:
        f.write(dynamic_datalist_content)
    logs += f"動的データリストファイル作成: {dynamic_datalist_path} (内容: {dynamic_datalist_content})\n"

    # run.py uses argparse, not Hydra, so construct proper arguments
    task_config_path = os.path.join(script_dir, task_template_rel_path)
    
    logs += f"タスク設定ファイル: {task_config_path}\n"

    # For skeleton generation, run.py expects directory paths, not file paths
    # The npz_dir should contain the raw_data.npz file, and input should be the same directory
    npz_directory = os.path.dirname(os.path.abspath(extracted_npz_path))
    
    cmd = [
        sys.executable, os.path.join(script_dir, "run.py"),
        "--task", task_config_path,
        "--input_dir", npz_directory,  # Use input_dir instead of input for directory scanning
        "--output_dir", os.path.abspath(stage_output_dir),
        "--npz_dir", npz_directory,  # Directory containing raw_data.npz
        "--seed", str(seed)
    ]

    logs += f"実行コマンド: {' '.join(cmd)}\n"
    progress_fn(0.1, desc="スケルトン推論中...")

    success, script_output = run_script(cmd, working_directory=script_dir, script_name="スケルトン生成 (run.py)")
    logs += script_output

    if not success:
        logs += "スケルトン生成スクリプト(run.py)の実行に失敗しました。\n"
        return None, logs, None, None, None

    expected_fbx_path = os.path.join(stage_output_dir, output_fbx_filename)
    expected_txt_path = os.path.join(stage_output_dir, output_txt_filename)
    expected_npz_path = os.path.join(stage_output_dir, output_npz_filename)

    # Check for files in multiple possible locations since they might be generated in extracted_mesh directory
    output_directories_to_check = [
        stage_output_dir,  # Expected output directory: 02_skeleton_output
        npz_directory,     # Source directory: 01_extracted_mesh (where files are actually generated)
        os.path.join(base_work_dir, "01_extracted_mesh", model_name_for_output),  # Alternative path
    ]
    
    # Find NPZ file
    actual_npz_path = None
    for output_dir in output_directories_to_check:
        potential_npz_path = os.path.join(output_dir, output_npz_filename)
        if os.path.exists(potential_npz_path) and os.path.getsize(potential_npz_path) > 0:
            actual_npz_path = potential_npz_path
            logs += f"NPZファイルを発見: {potential_npz_path}\n"
            break
    
    # Find FBX file
    actual_fbx_path = None
    logs += f"FBXファイル検索開始 (期待ファイル名: {output_fbx_filename}):\n"
    for output_dir in output_directories_to_check:
        potential_fbx_path = os.path.join(output_dir, output_fbx_filename)
        logs += f"  検索中: {potential_fbx_path}\n"
        if os.path.exists(potential_fbx_path):
            file_size = os.path.getsize(potential_fbx_path)
            logs += f"    -> ファイル発見! サイズ: {file_size} bytes\n"
            if file_size > 0:
                actual_fbx_path = potential_fbx_path
                logs += f"FBXファイルを発見: {potential_fbx_path}\n"
                break
            else:
                logs += f"    -> ファイルサイズが0のため無効\n"
        else:
            logs += f"    -> ファイルなし\n"
    
    # Find TXT file
    actual_txt_path = None
    logs += f"TXTファイル検索開始 (期待ファイル名: {output_txt_filename}):\n"
    for output_dir in output_directories_to_check:
        potential_txt_path = os.path.join(output_dir, output_txt_filename)
        logs += f"  検索中: {potential_txt_path}\n"
        if os.path.exists(potential_txt_path):
            actual_txt_path = potential_txt_path
            logs += f"TXTファイルを発見: {potential_txt_path}\n"
            break
        else:
            logs += f"    -> ファイルなし\n"
    
    fbx_ok = actual_fbx_path is not None
    npz_ok = actual_npz_path is not None
    txt_ok = actual_txt_path is not None

    if not fbx_ok: 
        logs += f"警告: FBXファイルが以下の場所で見つかりません:\n"
        for output_dir in output_directories_to_check:
            potential_path = os.path.join(output_dir, output_fbx_filename)
            logs += f"  - {potential_path}\n"
    if not npz_ok: 
        logs += f"警告: スケルトンNPZファイルが以下の場所で見つかりません:\n"
        for output_dir in output_directories_to_check:
            potential_path = os.path.join(output_dir, output_npz_filename)
            logs += f"  - {potential_path}\n"
    if not (fbx_ok and npz_ok):
        logs += "スケルトン生成の主要な出力（FBXまたはNPZ）が失敗しました。\n"
        # Return Nones for paths if critical files are missing
        return None, logs, None if not fbx_ok else actual_fbx_path, None if not txt_ok else actual_txt_path, None if not npz_ok else actual_npz_path

    logs += f"✓ スケルトン生成成功。\n"
    if fbx_ok: logs += f"  - FBXモデル: {actual_fbx_path}\n"
    if txt_ok: logs += f"  - TXT情報: {actual_txt_path}\n"
    if npz_ok: logs += f"  - NPZデータ: {actual_npz_path}\n"

    display_glb_path = None
    if fbx_ok:
        progress_fn(0.8, desc="スケルトンモデル表示用に変換中...")
        display_glb_path = convert_to_glb_for_display(actual_fbx_path, f"{model_name_for_output}_skeleton_display")
        if display_glb_path:
            logs += f"表示用GLBモデル: {display_glb_path}\n"
        else:
            logs += f"警告: スケルトンモデルのGLBへの変換に失敗しました。\n"

    logs += "\n"
    progress_fn(1.0, desc="スケルトン生成完了")
    
    return (
        display_glb_path, 
        logs, 
        actual_fbx_path if fbx_ok else None, 
        actual_txt_path if txt_ok else None,
        actual_npz_path if npz_ok else None
    )

def process_generate_skin(raw_data_npz_path, skeleton_fbx_path, skeleton_npz_path, model_name_for_output, progress_fn):
    logs = f"--- ステップ2: スキニングウェイト予測開始 ({model_name_for_output}) ---\n"
    if not APP_CONFIG:
        logs += "エラー: アプリケーション設定がロードされていません。\n"
        return None, logs, None, None 

    script_dir = os.path.dirname(os.path.abspath(__file__))

    try:
        skin_config = APP_CONFIG.skinning_prediction
        base_work_dir = APP_CONFIG.working_directory_base
        
        skin_subdir_name = skin_config.skin_output_subdir
        task_template_rel_path = skin_config.task_config_template
        
        output_skinned_fbx_filename = skin_config.output_skinned_fbx_filename
        output_skinning_npz_filename = skin_config.output_skinning_npz_filename
        datalist_filename = skin_config.datalist_filename
        seed = skin_config.seed

        stage_output_dir = os.path.join(base_work_dir, skin_subdir_name, model_name_for_output)
        os.makedirs(stage_output_dir, exist_ok=True)
        add_to_cleanup_list(stage_output_dir)
        logs += f"スキニングステージ出力ディレクトリ: {stage_output_dir}\n"

        operation_temp_dir = tempfile.mkdtemp(prefix=f"unirig_skin_{model_name_for_output}_")
        add_to_cleanup_list(operation_temp_dir)
        logs += f"一時設定ディレクトリ: {operation_temp_dir}\n"
        
        # Ensure input paths for datalist are valid
        if not raw_data_npz_path or not os.path.exists(raw_data_npz_path):
            logs += f"エラー: スキニングのための抽出NPZパスが無効です: {raw_data_npz_path}\n"
            return None, logs, None, None
        if not skeleton_npz_path or not os.path.exists(skeleton_npz_path):
            logs += f"エラー: スキニングのためのスケルトンNPZパスが無効です: {skeleton_npz_path}\n"
            return None, logs, None, None
        if not skeleton_fbx_path or not os.path.exists(skeleton_fbx_path): # Needed for input_skeleton_path override
             logs += f"エラー: スキニングのためのスケルトンFBXパスが無効です: {skeleton_fbx_path}\n"
             return None, logs, None, None

        # Create simple datalist for run.py - use simple line format instead of JSON
        # For skinning, each line should be: raw_data_path skeleton_data_path weight
        dynamic_datalist_content = f"{os.path.abspath(raw_data_npz_path)} {os.path.abspath(skeleton_npz_path)} 1.0"
        dynamic_datalist_path = os.path.join(operation_temp_dir, datalist_filename)
        with open(dynamic_datalist_path, 'w') as f:
            f.write(dynamic_datalist_content)
        logs += f"動的データリストファイル作成: {dynamic_datalist_path} (内容: {dynamic_datalist_content})\n"

        # Use standard task config path (not Hydra config)
        task_config_path = os.path.join(script_dir, task_template_rel_path)
        logs += f"タスク設定ファイル: {task_config_path}\n"

        # For skinning, we need to specify the directory containing the NPZ files, not the datalist file
        npz_directory = os.path.dirname(os.path.abspath(raw_data_npz_path))

        cmd = [
            sys.executable, os.path.join(script_dir, "run.py"),
            "--task", task_config_path,
            "--input_dir", npz_directory,  # Use the directory containing NPZ files
            "--output_dir", stage_output_dir,
            "--seed", str(seed)
        ]

        logs += f"実行コマンド: {' '.join(cmd)}\n"
        progress_fn(0.1, desc="スキニングウェイト推論中...")

        # Setup environment for headless OpenGL rendering
        env = os.environ.copy()
        env['DISPLAY'] = ':99'  # Virtual display
        # Use OSMesa instead of EGL for better headless compatibility
        env['PYOPENGL_PLATFORM'] = 'osmesa'
        env['OSMESA_LIBRARY'] = '/usr/lib/x86_64-linux-gnu/libOSMesa.so'
        # Mesa driver settings for software rendering
        env['MESA_GL_VERSION_OVERRIDE'] = '3.3'
        env['MESA_GLSL_VERSION_OVERRIDE'] = '330'
        env['GALLIUM_DRIVER'] = 'llvmpipe'
        env['LIBGL_ALWAYS_SOFTWARE'] = '1'
        env['LIBGL_ALWAYS_INDIRECT'] = '1'
        # DRI and driver path settings
        env['LIBGL_DRIVERS_PATH'] = '/usr/lib/x86_64-linux-gnu/dri'
        env['MESA_LOADER_DRIVER_OVERRIDE'] = 'swrast'
        # Fix library path conflicts between Conda and system
        system_lib_path = '/usr/lib/x86_64-linux-gnu:/lib/x86_64-linux-gnu'
        # conda_lib_path = '/opt/conda/envs/UniRig/lib' # Removed for this attempt
        env['LD_LIBRARY_PATH'] = system_lib_path # Prioritize system libraries
        # Disable hardware acceleration completely
        env['MPLBACKEND'] = 'Agg'  # For matplotlib if used
        
        # Start virtual display if not already running
        import subprocess
        try:
            subprocess.check_output(['pgrep', 'Xvfb'], stderr=subprocess.DEVNULL)
            logs += "仮想ディスプレイが既に実行中です\n"
        except subprocess.CalledProcessError:
            # Start Xvfb in the background
            xvfb_process = subprocess.Popen([
                'Xvfb', ':99', '-screen', '0', '1024x768x24', '-ac', '+extension', 'GLX', '+render', '-noreset'
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            import time
            time.sleep(3)  # Give Xvfb more time to start
            logs += "仮想ディスプレイ (Xvfb) を開始しました\n"
            
            # Verify GLX extension is available
            try:
                glx_check = subprocess.run(['glxinfo'], env=env, capture_output=True, text=True, timeout=10)
                if glx_check.returncode == 0:
                    logs += "GLX拡張が正常に利用可能です\n"
                else:
                    logs += f"GLX拡張チェック警告: {glx_check.stderr}\n"
            except (subprocess.TimeoutExpired, FileNotFoundError):
                logs += "GLX拡張チェックをスキップしました\n"

        success, script_output = run_script(cmd, working_directory=script_dir, script_name="スキニングウェイト予測 (run.py)", env=env)
        logs += script_output

        if not success:
            logs += "スキニングウェイト予測スクリプト(run.py)の実行に失敗しました。\n"
            return None, logs, None, None

        expected_skinned_fbx_path = os.path.join(stage_output_dir, output_skinned_fbx_filename)
        expected_skinning_npz_path = os.path.join(stage_output_dir, output_skinning_npz_filename)

        skinned_fbx_ok = os.path.exists(expected_skinned_fbx_path) and os.path.getsize(expected_skinned_fbx_path) > 0
        skinning_npz_ok = os.path.exists(expected_skinning_npz_path) and os.path.getsize(expected_skinning_npz_path) > 0

        if not skinned_fbx_ok: logs += f"警告: 期待されるスキン済みFBXファイルが見つからないか空です: {expected_skinned_fbx_path}\n"
        if not skinning_npz_ok: logs += f"警告: 期待されるスキニングNPZファイルが見つからないか空です: {expected_skinning_npz_path}\n"
        if not (skinned_fbx_ok and skinning_npz_ok):
            logs += "スキニングの主要な出力（FBXまたはNPZ）が失敗しました。\n"
            return None, logs, None if not skinned_fbx_ok else expected_skinned_fbx_path, None if not skinning_npz_ok else expected_skinning_npz_path

        logs += f"✓ スキニングウェイト予測成功。\n"
        if skinned_fbx_ok: logs += f"  - スキン済みFBXモデル: {expected_skinned_fbx_path}\n"
        if skinning_npz_ok: logs += f"  - スキニングNPZデータ: {expected_skinning_npz_path}\n"

        display_glb_path = None
        if skinned_fbx_ok:
            progress_fn(0.8, desc="スキン済みモデル表示用に変換中...")
            display_glb_path = convert_to_glb_for_display(expected_skinned_fbx_path, f"{model_name_for_output}_skinned_display")
            if display_glb_path:
                logs += f"表示用GLBモデル: {display_glb_path}\n"
            else:
                logs += f"警告: 表示用GLBへの変換に失敗しました。FBXパスを代わりに返します。\n"
                # display_glb_path = expected_fbx_path

        logs += "\n"
        progress_fn(1.0, desc="スキニングウェイト予測完了")
        
        return (
            display_glb_path, 
            logs, 
            expected_skinned_fbx_path if skinned_fbx_ok else None, 
            expected_skinning_npz_path if skinning_npz_ok else None
        )

    except Exception as e:
        error_msg = f"スキニングウェイト予測中に予期せぬエラーが発生しました: {str(e)}\n"
        error_msg += f"詳細: {traceback.format_exc()}\n"
        logs += error_msg
        progress_fn(1.0, desc="スキニングエラー")
        return None, logs, None, None

def process_merge_model(original_model_path, skinned_fbx_path, skinning_npz_path, model_name_for_output, progress_fn):
    logs = f"--- ステップ3: モデルマージ開始 ({model_name_for_output}) ---\n"
    if not APP_CONFIG:
        logs += "エラー: アプリケーション設定がロードされていません。\n"
        return None, logs, None 

    script_dir = os.path.dirname(os.path.abspath(__file__))

    try:
        merge_config = APP_CONFIG.model_merging
        base_work_dir = APP_CONFIG.working_directory_base
        
        merge_subdir_name = merge_config.merge_output_subdir
        merge_script_rel_path = merge_config.python_script_path 
        output_filename = merge_config.output_merged_fbx_filename

        stage_output_dir = os.path.join(base_work_dir, merge_subdir_name, model_name_for_output)
        os.makedirs(stage_output_dir, exist_ok=True)
        add_to_cleanup_list(stage_output_dir)
        logs += f"モデルマージステージ出力ディレクトリ: {stage_output_dir}\n"

        final_merged_fbx_path = os.path.join(stage_output_dir, output_filename)
        logs += f"最終マージ済みFBX出力パス: {final_merged_fbx_path}\n"

        merge_script_abs_path = os.path.join(script_dir, merge_script_rel_path)

        # Input validation
        valid_inputs = True
        if not original_model_path or not os.path.exists(original_model_path):
            logs += f"エラー: オリジナルモデルパスが無効: {original_model_path}\n"; valid_inputs = False
        if not skinned_fbx_path or not os.path.exists(skinned_fbx_path):
            logs += f"エラー: スキン済みFBXパスが無効: {skinned_fbx_path}\n"; valid_inputs = False
        if not skinning_npz_path or not os.path.exists(skinning_npz_path):
            logs += f"エラー: スキニングNPZパスが無効: {skinning_npz_path}\n"; valid_inputs = False
        if not os.path.exists(merge_script_abs_path):
            logs += f"エラー: マージスクリプトが見つかりません: {merge_script_abs_path}\n"; valid_inputs = False
        
        if not valid_inputs:
            return None, logs, None

        cmd = [
            sys.executable, "-m", "src.inference.merge",
            "--source", os.path.abspath(skinned_fbx_path),
            "--target", os.path.abspath(original_model_path),
            "--output", os.path.abspath(final_merged_fbx_path),
            "--add_root", "False",
            "--require_suffix", "none",
            "--num_runs", "1",
            "--id", "0"
        ]
        
        logs += f"実行コマンド: {' '.join(cmd)}\n"
        progress_fn(0.1, desc="モデルマージ処理中...")

        # Set PYTHONPATH to include the src directory for proper imports
        env = os.environ.copy()
        env['PYTHONPATH'] = f"{script_dir}:{env.get('PYTHONPATH', '')}"

        success, script_output = run_script(cmd, working_directory=script_dir, script_name="モデルマージ", env=env)
        logs += script_output

        merged_fbx_ok = os.path.exists(final_merged_fbx_path) and os.path.getsize(final_merged_fbx_path) > 0

        if not success or not merged_fbx_ok:
            logs += "モデルマージスクリプトの実行に失敗したか、期待されるFBXファイルが生成されませんでした（または空です）。\n"
            return None, logs, None
        
        logs += f"✓ モデルマージ成功。最終FBXモデル: {final_merged_fbx_path}\n"

        display_glb_path = None
        progress_fn(0.8, desc="マージ済みモデル表示用に変換中...")
        display_glb_path = convert_to_glb_for_display(final_merged_fbx_path, f"{model_name_for_output}_merged_display")
        if display_glb_path:
            logs += f"表示用GLBモデル: {display_glb_path}\
"
        else:
            logs += f"警告: 表示用GLBへの変換に失敗しました。FBXパスを代わりに返します。\n"
            # display_glb_path = final_merged_fbx_path

        logs += "\n"
        progress_fn(1.0, desc="モデルマージ完了")

        return display_glb_path, logs, final_merged_fbx_path

    except Exception as e:
        error_msg = f"モデルマージ中に予期せぬエラーが発生しました: {str(e)}\
"
        error_msg += f"詳細: {traceback.format_exc()}\
"
        logs += error_msg
        progress_fn(1.0, desc="モデルマージエラー")
        return None, logs, None

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
    
    if not uploaded_model_path:
        logs += "エラー: モデルファイルがアップロードされていません。\n"
        return None, logs, None, None, None, None, None, None, None, None, None, None

    try:
        # モデル名を抽出
        model_name = os.path.splitext(os.path.basename(uploaded_model_path))[0]
        logs += f"📁 処理モデル: {model_name}\n"
        logs += f"📂 入力ファイル: {uploaded_model_path}\n\n"

        # ステップ1: メッシュ抽出 (0.0-0.25)
        logs += "🔧 ステップ1/4: メッシュ抽出開始\n"
        extract_progress = progress_segment(progress, 0.0, 0.25)
        extract_progress(0.0, desc="メッシュ抽出中...")
        
        extracted_npz_path, extract_logs = process_extract_mesh(
            uploaded_model_path, 
            model_name,
            extract_progress
        )
        logs += extract_logs
        
        if not extracted_npz_path:
            logs += "❌ メッシュ抽出に失敗しました。処理を中止します。\n"
            return None, logs, None, None, None, None, None, None, None, None, None, None
        
        logs += f"✅ メッシュ抽出完了: {extracted_npz_path}\n\n"

        # ステップ2: スケルトン生成 (0.25-0.5)
        logs += "🦴 ステップ2/4: スケルトン生成開始\n"
        skeleton_progress = progress_segment(progress, 0.25, 0.5)
        skeleton_progress(0.0, desc="スケルトン生成中...")
        
        skeleton_display_path, skeleton_logs, skeleton_fbx_path, skeleton_txt_path, skeleton_npz_path = process_generate_skeleton(
            extracted_npz_path,
            model_name,
            gender,
            skeleton_progress
        )
        logs += skeleton_logs
        
        if not skeleton_fbx_path or not skeleton_npz_path:
            logs += "❌ スケルトン生成に失敗しました。処理を中止します。\n"
            return None, logs, None, None, skeleton_display_path, None, None, None, None, None, None, None
        
        logs += f"✅ スケルトン生成完了: {skeleton_fbx_path}\n\n"

        # ステップ3: スキニング (0.5-0.75)
        logs += "🎨 ステップ3/4: スキニングウェイト予測開始\n"
        skinning_progress = progress_segment(progress, 0.5, 0.75)
        skinning_progress(0.0, desc="スキニング処理中...")
        
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
            return None, logs, None, extracted_npz_path, skeleton_display_path, skeleton_fbx_path, skeleton_txt_path, skeleton_npz_path, skinned_display_path, None, None, None
        
        logs += f"✅ スキニング完了: {skinned_fbx_path}\n\n"

        # ステップ4: モデルマージ (0.75-1.0)
        logs += "🔗 ステップ4/4: モデルマージ開始\n"
        merge_progress = progress_segment(progress, 0.75, 1.0)
        merge_progress(0.0, desc="モデルマージ中...")
        
        final_display_path, merge_logs, final_merged_fbx_path = process_merge_model(
            original_model_path=uploaded_model_path,
            skinned_fbx_path=skinned_fbx_path,
            skinning_npz_path=skinning_npz_path,
            model_name_for_output=model_name,
            progress_fn=merge_progress
        )
        logs += merge_logs
        
        if not final_merged_fbx_path:
            logs += "❌ モデルマージに失敗しました。\n"
            return None, logs, None, extracted_npz_path, skeleton_display_path, skeleton_fbx_path, skeleton_txt_path, skeleton_npz_path, skinned_display_path, skinned_fbx_path, skinning_npz_path, None
        
        logs += f"✅ モデルマージ完了: {final_merged_fbx_path}\n\n"

        # 成功メッセージ
        logs += "🎉 === フルパイプライン実行完了 ===\n"
        logs += f"🎯 最終モデル: {final_merged_fbx_path}\n"
        logs += f"📊 すべての中間ファイルもダウンロード可能です。\n"

        progress(1.0, desc="フルパイプライン完了!")

        # 戻り値: 
        # final_model_display, logs, final_model_download,
        # extracted_npz_download, skeleton_model_display, 
        # skeleton_fbx_download, skeleton_txt_download, skeleton_npz_download,
        # skinned_model_display, skinned_fbx_download, skinning_npz_download
        return (
            final_display_path,         # full_final_model_display
            logs,                       # full_pipeline_logs
            final_merged_fbx_path,      # full_final_model_download_accordion
            extracted_npz_path,         # full_extracted_npz_download
            skeleton_display_path,      # full_skeleton_model_display
            skeleton_fbx_path,          # full_skeleton_fbx_download
            skeleton_txt_path,          # full_skeleton_txt_download
            skeleton_npz_path,          # full_skeleton_npz_download
            skinned_display_path,       # full_skinned_model_display
            skinned_fbx_path,           # full_skinned_model_fbx_download
            skinning_npz_path           # full_skinning_npz_download
        )

    except Exception as e:
        error_msg = f"❌ フルパイプライン実行中に予期せぬエラーが発生しました: {str(e)}\n"
        error_msg += f"詳細: {traceback.format_exc()}\n"
        logs += error_msg
        progress(1.0, desc="フルパイプラインエラー")
        return None, logs, None, None, None, None, None, None, None, None, None

# --- Gradio Handler Functions ---
def gradio_extract_mesh(original_model_path_state: str, model_name_state: str, progress=gr.Progress(track_tqdm=True)):
    logs = "--- Gradio Extract Mesh Wrapper ---\
"
    if not original_model_path_state or not model_name_state:
        logs += "エラー: モデルパスまたはモデル名が提供されていません。ステップ0でモデルをアップロードしてください。\n"
        return logs, gr.DownloadButton(visible=False), None
    
    # Use progress_segment to map this step's progress (0.0-1.0) to the Gradio progress bar
    # For a single step button, the segment is the full bar (0.0 to 1.0)
    current_step_progress_fn = progress_segment(progress, 0.0, 1.0)
    current_step_progress_fn(0.0, desc="メッシュ抽出準備中...")

    extracted_npz_path, process_logs = process_extract_mesh(
        original_model_path_state, 
        model_name_state,
        current_step_progress_fn # Pass the wrapped progress function
    )
    logs += process_logs
    
    if extracted_npz_path:
        logs += "メッシュ抽出成功 (Gradioラッパー)。\n"
        # current_step_progress_fn(1.0, desc="メッシュ抽出完了") # Already done by process_extract_mesh
        return logs, gr.DownloadButton(label="抽出NPZをダウンロード", value=extracted_npz_path, visible=True), extracted_npz_path
    else:
        logs += "メッシュ抽出失敗 (Gradioラッパー)。\n"
        current_step_progress_fn(1.0, desc="メッシュ抽出エラー")
        return logs, gr.DownloadButton(label="抽出NPZをダウンロード", value=None, visible=False), None

def gradio_generate_skeleton(
    raw_data_npz_path_from_state: str, # Input from raw_data_npz_path_state
    model_name_from_state: str,       # Input from model_name_state
    gender: str,
    progress=gr.Progress(track_tqdm=True)
):
    logs = "--- Gradio Generate Skeleton Wrapper ---\n"
    if not raw_data_npz_path_from_state or not model_name_from_state:
        logs += "エラー: NPZパスまたはモデル名が提供されていません。ステップ0を完了し、モデル名が設定されていることを確認してください。\n"
        # Outputs: skeleton_model_display, logs_output, skeleton_fbx_download, skeleton_txt_download, skeleton_npz_download, skeleton_fbx_path_state, skeleton_npz_path_state
        return None, logs, None, None, None, None, None 

    current_step_progress_fn = progress_segment(progress, 0.0, 1.0)
    current_step_progress_fn(0.0, desc="スケルトン生成準備中...")

    # Call process_generate_skeleton with the NPZ path from the previous step
    # process_generate_skeleton returns: display_glb_path, logs, expected_fbx_path, expected_txt_path, expected_npz_path
    display_model_path, process_logs, fbx_path, txt_path, npz_path = process_generate_skeleton(
        raw_data_npz_path_from_state, # Corrected parameter name
        model_name_from_state,
        gender,
        current_step_progress_fn # Pass the wrapped progress function
    )
    logs += process_logs

    if display_model_path and fbx_path and npz_path:
        logs += f"✓ スケルトン生成成功。表示モデル: {display_model_path}\n"
    else:
        logs += "スケルトン生成に失敗しました。ログを確認してください。\n"
    
    # Outputs: 
    # skeleton_model_display, logs_output, 
    # skeleton_fbx_download, skeleton_txt_download, skeleton_npz_download,
    # skeleton_fbx_path_state, skeleton_npz_path_state
    return (
        display_model_path, 
        logs, 
        fbx_path, # For skeleton_fbx_download
        txt_path, # For skeleton_txt_download
        npz_path, # For skeleton_npz_download
        fbx_path, # For skeleton_fbx_path_state
        npz_path  # For skeleton_npz_path_state
    )

def gradio_generate_skin(
    raw_data_npz_path_from_state: str,    # Input from raw_data_npz_path_state
    skeleton_fbx_path_from_state: str,  # Input from skeleton_fbx_path_state
    skeleton_npz_path_from_state: str,  # Input from skeleton_npz_path_state
    model_name_from_state: str,         # Input from model_name_state
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
        # Return appropriate number of Nones for outputs
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

    # Outputs: skin_model_display, logs_output, skin_fbx_download, skin_npz_download, skinned_fbx_path_state, skinning_npz_path_state
    return (
        display_model_path, 
        logs, 
        skinned_fbx_path, # For download
        skinning_npz_path, # For download
        skinned_fbx_path, # For state
        skinning_npz_path  # For state
    )

def gradio_merge_model(
    original_model_path_from_state: str, # Input from original_model_path_state
    skinned_fbx_path_from_state: str,    # Input from skinned_fbx_path_state
    skinning_npz_path_from_state: str,   # Input from skinning_npz_path_state
    model_name_from_state: str,          # Input from model_name_state
    progress=gr.Progress(track_tqdm=True)
):
    logs = "--- Gradio Merge Model Wrapper ---\n"
    if not (
        original_model_path_from_state and
        skinned_fbx_path_from_state and
        skinning_npz_path_from_state and
        model_name_from_state
    ):
        logs += "エラー: モデルマージに必要なパス (オリジナルモデル, スキン済みFBX, スキニングNPZ) またはモデル名が提供されていません。\n"
        # Return appropriate number of Nones for outputs
        # Outputs: final_model_display, logs_output, final_fbx_download, final_merged_fbx_path_state
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

    # Outputs: final_model_display, logs_output, final_fbx_download, final_merged_fbx_path_state
    return (
        display_model_path,
        logs,
        final_merged_fbx_path, # For download
        final_merged_fbx_path  # For state
    )

# --- Gradio UI Builder ---
def build_gradio_interface():
    with gr.Blocks(theme=gr.themes.Base()) as demo:
        # Define State variables at the beginning of the Blocks context
        s_original_model_path = gr.State()
        s_model_name = gr.State()
        s_extracted_npz_path = gr.State()
        s_skeleton_fbx_path = gr.State()
        s_skeleton_txt_path = gr.State()
        s_skeleton_npz_path = gr.State()
        s_skinned_fbx_path = gr.State()
        s_skinning_npz_path = gr.State()
        s_merged_fbx_path = gr.State()
        
        gr.Markdown("<h1>UniRig 3Dモデル自動リギングアプリケーション</h1>")
        gr.Markdown("3Dモデル（FBX、OBJ、GLB/GLTF、PLYなどTrimeshが扱える形式）をアップロードし、自動でリギング処理を行います。")

        with gr.Tab("フルパイプライン実行"):
            with gr.Row():
                with gr.Column(scale=1):
                    full_input_model_upload = gr.File(label="3Dモデルをアップロード", file_types=[".fbx", ".obj", ".glb", ".gltf", ".ply"], type="filepath")
                    full_gender_dropdown = gr.Dropdown(label="性別（スケルトン生成用）", choices=["female", "male", "neutral"], value="female")
                    full_pipeline_button = gr.Button("フルパイプライン実行", variant="primary")
                with gr.Column(scale=2):
                    full_final_model_display = gr.Model3D(label="最終リギング済みモデルプレビュー", interactive=False, camera_position=(0, 2.5, 3.5))
            
            full_pipeline_logs = gr.Textbox(label="フルパイプラインログ", lines=15, interactive=False, show_copy_button=True)
            
            with gr.Accordion("中間成果物のダウンロードとプレビュー", open=False):
                gr.Markdown("<h4>メッシュ抽出結果</h4>")
                full_extracted_npz_download = gr.DownloadButton(label="抽出NPZ", interactive=True, visible=False)
                
                gr.Markdown("<h4>スケルトン生成結果</h4>")
                full_skeleton_model_display = gr.Model3D(label="スケルトンモデルプレビュー", interactive=False, camera_position=(0, 2.5, 3.5), visible=False)
                with gr.Row():
                    full_skeleton_fbx_download = gr.DownloadButton(label="スケルトン (FBX)", interactive=True, visible=False)
                    full_skeleton_txt_download = gr.DownloadButton(label="スケルトン (TXT)", interactive=True, visible=False)
                    full_skeleton_npz_download = gr.DownloadButton(label="スケルトン (NPZ)", interactive=True, visible=False)

                gr.Markdown("<h4>スキニングウェイト予測結果</h4>")
                full_skinned_model_display = gr.Model3D(label="スキン済みモデルプレビュー", interactive=False, camera_position=(0, 2.5, 3.5), visible=False)
                with gr.Row():
                    full_skinned_model_fbx_download = gr.DownloadButton(label="スキン済み (FBX)", interactive=True, visible=False)
                    full_skinning_npz_download = gr.DownloadButton(label="スキニング (NPZ)", interactive=True, visible=False)
                
                gr.Markdown("<h4>最終マージモデル</h4>")
                full_final_model_download_accordion = gr.DownloadButton(label="最終モデル (FBX)", interactive=True, visible=False)

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
                    gr.update(visible=d1 is not None and d1 != ''),  # full_final_model_display
                    gr.update(visible=d3 is not None and d3 != ''),  # full_final_model_download_accordion
                    gr.update(visible=d4 is not None and d4 != ''),  # full_extracted_npz_download
                    gr.update(visible=d5 is not None and d5 != ''),  # full_skeleton_model_display
                    gr.update(visible=d6 is not None and d6 != ''),  # full_skeleton_fbx_download
                    gr.update(visible=d7 is not None and d7 != ''),  # full_skeleton_txt_download
                    gr.update(visible=d8 is not None and d8 != ''),  # full_skeleton_npz_download
                    gr.update(visible=d9 is not None and d9 != ''),  # full_skinned_model_display
                    gr.update(visible=d10 is not None and d10 != ''), # full_skinned_model_fbx_download
                    gr.update(visible=d11 is not None and d11 != '')  # full_skinning_npz_download
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
                api_name=False
            )

        with gr.Tab("ステップバイステップ実行"):            
            gr.Markdown("<h3>ステップ0: 初期設定とメッシュ抽出</h3>")
            with gr.Row():
                step_upload_button = gr.File(label="1. 3Dモデルをアップロード", file_types=[".fbx", ".obj", ".glb", ".gltf", ".ply"], type="filepath")
                step_input_model_display_step0 = gr.Model3D(label="アップロードモデルプレビュー", interactive=False, camera_position=(0, 2.5, 3.5))
            
            btn_run_extract = gr.Button("0. メッシュ抽出実行", variant="primary")
            step_extract_logs = gr.Textbox(label="抽出ログ", lines=5, interactive=False, show_copy_button=True)
            step_extracted_model_download = gr.DownloadButton(label="抽出NPZ", interactive=True, visible=False)

            gr.Markdown("<h3>ステップ1: スケルトン生成</h3>")
            step_gender_dropdown = gr.Dropdown(label="性別（スケルトン生成用）", choices=["female", "male", "neutral"], value="female")
            btn_run_skeleton = gr.Button("1. スケルトン生成実行", variant="primary")
            step_skeleton_model_display = gr.Model3D(label="スケルトンモデルプレビュー", interactive=False, camera_position=(0, 2.5, 3.5))
            step_skeleton_logs = gr.Textbox(label="スケルトン生成ログ", lines=5, interactive=False, show_copy_button=True)
            with gr.Row():
                step_skeleton_fbx_download = gr.DownloadButton(label="スケルトン (FBX)", interactive=True, visible=False)
                step_skeleton_txt_download = gr.DownloadButton(label="スケルトン (TXT)", interactive=True, visible=False)
                step_skeleton_npz_download = gr.DownloadButton(label="スケルトン (NPZ)", interactive=True, visible=False)

            gr.Markdown("<h3>ステップ2: スキニングウェイト予測</h3>")
            btn_run_skin = gr.Button("2. スキニングウェイト予測実行", variant="primary")
            step_skinned_model_display = gr.Model3D(label="スキン済みモデルプレビュー", interactive=False, camera_position=(0, 2.5, 3.5))
            step_skin_logs = gr.Textbox(label="スキニングログ", lines=5, interactive=False, show_copy_button=True)
            with gr.Row():
                step_skinned_model_fbx_download = gr.DownloadButton(label="スキン済み (FBX)", interactive=True, visible=False)
                step_skinning_npz_download = gr.DownloadButton(label="スキニング (NPZ)", interactive=True, visible=False)

            gr.Markdown("<h3>ステップ3: モデルマージ</h3>")
            with gr.Row():
                btn_run_merge = gr.Button("3. モデルマージ実行", variant="primary")
            step_merged_model_display = gr.Model3D(label="最終マージモデルプレビュー", interactive=False, camera_position=(0, 2.5, 3.5))
            step_merge_logs = gr.Textbox(label="マージログ", lines=5, interactive=False, show_copy_button=True)
            step_merged_model_download = gr.DownloadButton(label="最終モデル (FBX)", interactive=True, visible=False)

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
            
    return demo

if __name__ == "__main__":
    load_app_config() # Load configuration first

    if not APP_CONFIG:
        logging.error("アプリケーション設定のロードに失敗しました。起動を中止します。")
        sys.exit(1)

    # Safely access Gradio interface configurations with defaults
    gradio_config = APP_CONFIG.get('gradio_interface', {})
    server_name = gradio_config.get('server_name', '0.0.0.0')  # Changed to 0.0.0.0 for accessibility
    base_port = int(gradio_config.get('server_port', 7860))  # Base port
    share_gradio = gradio_config.get('share', False)
    inbrowser = gradio_config.get('inbrowser', True)
    
    # Try to find an available port starting from base_port
    import socket
    def find_free_port(start_port, max_attempts=10):
        for port in range(start_port, start_port + max_attempts):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(('', port))
                    return port
                except OSError:
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
    
    # Attempt to launch with or without auth based on presence of credentials
    # if auth_credentials:
    #     logging.info(f"Gradio認証が有効です。ユーザー: {auth_user}")
    #     iface.launch(
    #         server_name=server_name, 
    #         server_port=server_port, 
    #         share=share_gradio, 
    #         inbrowser=inbrowser,
    #         auth=auth_credentials
    #     )
    # else:
    #     logging.info("Gradio認証は無効です。")
    iface.launch(
        server_name=server_name, 
        server_port=server_port, 
        share=share_gradio, 
        inbrowser=inbrowser
    )