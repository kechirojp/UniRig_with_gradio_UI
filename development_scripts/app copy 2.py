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
        # This helps if APP_CONFIG.working_directory_base is different from /app/pipeline_work
        # or if subdirectories are outside the main pipeline_work structure.
        subdirs_to_check = [
            APP_CONFIG.get('mesh_extraction', {}).get('extract_output_subdir'),
            APP_CONFIG.get('skeleton_generation', {}).get('skeleton_output_subdir'),
            APP_CONFIG.get('skinning_prediction', {}).get('skin_output_subdir'),
            APP_CONFIG.get('model_merging', {}).get('merge_output_subdir'),
            APP_CONFIG.get('blender_processing', {}).get('conversion_output_subdir'),
            APP_CONFIG.get('blender_native_texture_flow', {}).get('blender_native_subdir', '06_blender_native'),
            APP_CONFIG.get('improved_safe_texture_restoration', {}).get('output_subdir', '08_final_output') # Example for improved flow
        ]
        for subdir_name in subdirs_to_check:
            if subdir_name:
                # Construct path relative to configured_work_base if it's not absolute
                # Or relative to script_dir if that makes more sense for your structure
                potential_path = os.path.join(configured_work_base, subdir_name)
                abs_path = os.path.abspath(potential_path)
                if abs_path not in allowed:
                    allowed.append(abs_path)
    
    # Add temp directory
    allowed.append(os.path.abspath(tempfile.gettempdir()))

    logging.info(f"DEBUG: Gradio allowed_pathsが設定されました: {list(set(allowed))}") # Use set to remove duplicates
    return list(set(allowed))
# --- End of modified section ---

# --- Add this helper function for debugging output paths ---
def log_output_paths_for_debug(output_dict, context_log_message=""):
    logging.info(f"--- DEBUG: Gradio出力パスの確認 ({context_log_message}) ---")
    if not isinstance(output_dict, dict):
        logging.warning(f"  出力は辞書ではありません: {type(output_dict)}, 値: {output_dict}")
        return

    for key, value in output_dict.items():
        if isinstance(value, str) and (value.endswith(('.glb', '.fbx', '.png', '.jpg', '.txt', '.npz', '.json', '.yaml')) or "/" in value or "\\\\" in value):
            # Heuristic: if it looks like a file path string
            abs_path = os.path.abspath(value)
            exists = os.path.exists(abs_path)
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
    skinning_npz_path = None
    
    if not uploaded_model_path:
        logs += "エラー: モデルファイルがアップロードされていません。\n"
        # Log paths before returning on error
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
            return None, logs, None, None, skeleton_display_path, None, None, None, None, None, None, None
        
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
            return None, logs, None, extracted_npz_path, skeleton_display_path, skeleton_fbx_path, skeleton_txt_path, skeleton_npz_path, skinned_display_path, None, None, None
        
        logs += f"✅ スキニング完了: {skinned_fbx_path}\n\n"

        # ステップ4: テクスチャ統合モデルマージ (0.75-1.0)
        logs += "🔗 ステップ4/4: テクスチャ統合モデルマージ開始 (二階建てフロー)\n"
        merge_progress = progress_segment(progress, 0.75, 1.0)
        merge_progress(0.0, "テクスチャ統合処理中...")
        
        # 新しい二階建てフローを使用
        final_display_path, merge_logs, final_merged_fbx_path = process_final_merge_with_textures(
            skinned_fbx_path=skinned_fbx_path,
            original_model_path=uploaded_model_path,
            model_name_for_output=model_name,
            progress_fn=merge_progress
        )
        logs += merge_logs
        
        if not final_merged_fbx_path:
            logs += "❌ テクスチャ統合モデルマージに失敗しました。\n"
            return None, logs, None, extracted_npz_path, skeleton_display_path, skeleton_fbx_path, skeleton_txt_path, skeleton_npz_path, skinned_display_path, skinned_fbx_path, skinning_npz_path, None
        
        logs += f"✅ テクスチャ統合モデルマージ完了: {final_merged_fbx_path}\n\n"

        # 成功メッセージ
        logs += "🎉 === フルパイプライン実行完了 (二階建てフロー) ===\n"
        logs += f"🎯 最終モデル: {final_merged_fbx_path}\n"
        logs += f"📊 テクスチャとマテリアルが保持された高品質なリギング済みモデルが生成されました。\n"
        logs += f"📋 すべての中間ファイルもダウンロード可能です。\n"

        progress(1.0, "フルパイプライン完了!")

        # --- Add this for debugging output paths ---
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
        # --- End of added section ---

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
        progress(1.0, "フルパイプラインエラー")

        # --- Add this for debugging output paths in error case ---
        error_output_details = {
            key: locals().get(key) for key in [
                'final_display_path', 'final_merged_fbx_path', 'extracted_npz_path',
                'skeleton_display_path', 'skeleton_fbx_path', 'skeleton_txt_path', 'skeleton_npz_path',
                'skinned_display_path', 'skinned_fbx_path', 'skinning_npz_path', 'uploaded_model_path'
            ]
        }
        log_output_paths_for_debug(error_output_details, "gradio_full_auto_rigging - error path")
        # --- End of added section ---
        
        return None, logs, None, None, None, None, None, None, None, None, None, None

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
    current_step_progress_fn(0.0, "メッシュ抽出準備中...")

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

def gradio_merge_model_with_textures(
    original_model_path_from_state: str, # Input from original_model_path_state
    skinned_fbx_path_from_state: str,    # Input from skinned_fbx_path_state
    model_name_from_state: str,          # Input from model_name_state
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
        # Return appropriate number of Nones for outputs
        # Outputs: final_model_display, logs_output, final_fbx_download, final_merged_fbx_path_state
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

    # Outputs: final_model_display, logs_output, final_fbx_download, final_merged_fbx_path_state
    return (
        display_model_path,
        logs,
        final_merged_fbx_path, # For download
        final_merged_fbx_path  # For state
    )

def gradio_merge_model(
    original_model_path_from_state: str, # Input from original_model_path_state
    skinned_fbx_path_from_state: str,    # Input from skinned_fbx_path_state
    skinning_npz_path_from_state: str,   # Input from skinning_npz_path_state
    model_name_from_state: str,          # Input from model_name_state
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
            ) # This is the last click handler in the 'Step-by-step' tab
        
        # Add demo.queue() here, after all UI elements and handlers for the demo are defined
        demo.queue()
            
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
    
    allowed_paths_list = get_allowed_paths()
    iface.launch(
        server_name=server_name, 
        server_port=server_port, 
        share=share_gradio, 
        inbrowser=inbrowser,
        debug=True, # Force debug=True for this debugging session
        allowed_paths=allowed_paths_list
    )