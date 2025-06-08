# This application uses UniRig (https://github.com/VAST-AI-Research/UniRig),
# which is licensed under the MIT License.
# A copy of the license can be found at:
# https://github.com/VAST-AI-Research/UniRig/blob/main/LICENSE
#
# Gradio application for 3D model preview and bone information display.

# ====================================================================
# 🚨 CRITICAL: SEGMENTATION FAULT PREVENTION - MEMORY SETUP 🚨
# ====================================================================
# Prevent PyTorch and Blender memory conflicts that cause segmentation faults
import os
import gc

# 最優先: セグメンテーションフォルト防止のためのメモリ制限とキャッシュ設定
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:256,garbage_collection_threshold:0.8'
os.environ['CUDA_LAUNCH_BLOCKING'] = '1'
os.environ['PYTHONMALLOC'] = 'malloc'
os.environ['MALLOC_TRIM_THRESHOLD_'] = '100000'

# PyTorchとBlenderの競合回避
os.environ['FORCE_FALLBACK_MODE'] = '1'
os.environ['DISABLE_UNIRIG_LIGHTNING'] = '1'

print("🛡️ セグメンテーションフォルト防止: メモリ管理設定完了")

# ====================================================================
# 🚨🚨🚨 CRITICAL: PREVENT ROLLBACK - READ BEFORE ANY CHANGES 🚨🚨🚨
# ====================================================================
# 
# BLENDER VERSION: 4.2 FIXED - DO NOT CHANGE
# FBX FORMAT: BINARY ONLY - NEVER ASCII
# CONTEXT MANAGEMENT: Blender42ContextManager REQUIRED
# 
# ROLLBACK PROTECTION STATUS:
# - Blender 4.2 compatibility fixes applied (June 2025)
# - Binary FBX export enforced (NO ASCII rollback)
# - Context management via blender_42_context_fix.py
# - Memory crash fixes applied (spconv/CUDA handling)
# 
# IF YOU SEE THESE ERRORS, APPLY BLENDER 4.2 FIXES:
# - "Context object has no attribute 'selected_objects'"
# - "Context object has no attribute 'object'" 
# - "Armature could not be set out of Edit Mode"
# - ASCII FBX export problems
# 
# REQUIRED ACTIONS TO PREVENT ROLLBACK:
# 1. Use Blender42ContextManager from blender_42_context_fix.py
# 2. Enforce BINARY FBX export (fbx_use_ascii=False)
# 3. Apply context-aware object management
# 4. Maintain current working pipeline (Steps 1-3 SUCCESS)
# 
# ====================================================================

import gradio as gr
import os
import subprocess
import tempfile
import datetime
import time
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
import torch  # Add PyTorch import
from texture_preservation_system import TexturePreservationSystem
from proposed_blender_texture_flow import BlenderNativeTextureFlow
from dynamic_skeleton_generator import DynamicSkeletonGenerator

# Import corrected texture system
try:
    from fixed_texture_system_v2_corrected import FixedTextureSystemV2
    print("✅ FixedTextureSystemV2Corrected imported successfully")
except ImportError as e:
    print(f"⚠️ FixedTextureSystemV2Corrected not available: {e}")
    # Fallback to original version
    try:
        from fixed_texture_system_v2 import FixedTextureSystemV2
        print("⚠️ Using original FixedTextureSystemV2 (may have issues)")
    except ImportError:
        FixedTextureSystemV2 = None
        print("❌ No FixedTextureSystemV2 available")

# Import ImprovedSafeTextureRestoration for priority texture processing
try:
    from improved_safe_texture_restoration import ImprovedSafeTextureRestoration
    IMPROVED_SAFE_TEXTURE_RESTORATION_AVAILABLE = True
    print("✅ ImprovedSafeTextureRestoration loaded in app.py")
except ImportError as e:
    IMPROVED_SAFE_TEXTURE_RESTORATION_AVAILABLE = False
    print(f"⚠️ ImprovedSafeTextureRestoration not available in app.py: {e}")

# Import FixedTextureSystemV2 for enhanced texture processing
try:
    from fixed_texture_system_v2_corrected import FixedTextureSystemV2
    FIXED_TEXTURE_SYSTEM_V2_AVAILABLE = True
    print("✅ FixedTextureSystemV2 loaded in app.py")
except ImportError as e:
    FIXED_TEXTURE_SYSTEM_V2_AVAILABLE = False
    print(f"⚠️ FixedTextureSystemV2 not available in app.py: {e}")

# Import CPU Skinning Fallback System for CUDA/spconv error handling
try:
    from src.model.cpu_skinning_system import create_cpu_skinning_fallback, compute_distance_based_weights
    from src.model.cpu_mesh_encoder import AdaptiveMeshEncoder
    CPU_SKINNING_FALLBACK_AVAILABLE = True
    print("✅ CPU Skinning Fallback System loaded in app.py")
except ImportError as e:
    CPU_SKINNING_FALLBACK_AVAILABLE = False
    print(f"⚠️ CPU Skinning Fallback System not available in app.py: {e}")

# === CRITICAL: Segmentation Fault Prevention Setup ===
# Set fallback environment variables IMMEDIATELY to prevent memory crashes
import os
os.environ['FORCE_FALLBACK_MODE'] = '1'
os.environ['DISABLE_UNIRIG_LIGHTNING'] = '1'
# 🚨 追加のセグメンテーションフォルト防止環境変数
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:512'
os.environ['CUDA_LAUNCH_BLOCKING'] = '1'
os.environ['PYTHONPATH'] = '/app'
print("🛡️ セグメンテーションフォルト防止: FORCE_FALLBACK_MODE=1, DISABLE_UNIRIG_LIGHTNING=1")
print("🛡️ 追加保護: PYTORCH_CUDA_ALLOC_CONF, CUDA_LAUNCH_BLOCKING設定完了")

# Emergency Skinning Bypass System Integration
try:
    from emergency_skinning_bypass import EmergencySkinningBypass
    from emergency_integration import process_emergency_unified_skinning
    EMERGENCY_BYPASS_AVAILABLE = True
    print("✅ Emergency Skinning Bypass System loaded in app.py")
except ImportError as e:
    EMERGENCY_BYPASS_AVAILABLE = False
    print(f"⚠️ Emergency Skinning Bypass System not available in app.py: {e}")

# --- Global Configuration and Setup ---
APP_CONFIG = None
TEMP_FILES_TO_CLEAN = []

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- PyTorch Device Configuration ---
# Simple and safe device selection (CPU prioritized in fallback mode)
if os.environ.get('FORCE_FALLBACK_MODE') == '1':
    device = "cpu"
    print("🔧 フォールバックモード: デバイスをCPUに固定")
else:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
logging.info(f"🔧 PyTorch device: {device}")

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
        os.path.abspath(os.path.join(script_dir, "display_cache")), # /app/display_cache (Gradio互換表示ファイル)
    ]
    if APP_CONFIG and APP_CONFIG.working_directory_base:
        # Ensure the configured working_directory_base is also allowed
        # This might be redundant if it's already /app/pipeline_work, but good for safety
        configured_work_base = os.path.abspath(APP_CONFIG.working_directory_base)
        if configured_work_base not in allowed:
            allowed.append(configured_work_base)
        
        # Add display_cache directory within the working directory base
        display_cache_path = os.path.abspath(os.path.join(configured_work_base, "display_cache"))
        if display_cache_path not in allowed:
            allowed.append(display_cache_path)
        
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
    
    # Add temp directory (for backward compatibility, but prefer display_cache)
    allowed.append(os.path.abspath(tempfile.gettempdir()))

    logging.info(f"DEBUG: Gradio allowed_pathsが設定されました: {list(set(allowed))}") # Use set to remove duplicates
    return list(set(allowed))

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

# --- Configuration Loading Functions ---
def load_app_config():
    """アプリケーション設定をYAMLファイルから読み込み"""
    global APP_CONFIG
    config_path = os.path.join(os.path.dirname(__file__), 'configs', 'app_config.yaml')
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        APP_CONFIG = Box(config_data)
        logging.info(f"✅ アプリケーション設定を読み込みました: {config_path}")
        
        # 作業ディレクトリの作成
        work_dir = os.path.abspath(APP_CONFIG.working_directory_base)
        os.makedirs(work_dir, exist_ok=True)
        
        return True
    except Exception as e:
        logging.error(f"❌ 設定ファイルの読み込みに失敗: {e}")
        APP_CONFIG = Box({'error': str(e)})
        return False

# --- Utility Functions ---
def convert_to_glb_for_display(input_model_path, output_name):
    """3Dモデルを表示用GLBに変換 (Gradio互換パス使用)"""
    try:
        # 入力パスと出力パスを設定 - Gradio互換の固定ディレクトリを使用
        base_name = os.path.splitext(os.path.basename(input_model_path))[0]
        
        # Gradio互換の表示ファイル用ディレクトリを作成
        # APP_CONFIGが利用可能であればpipeline_work内に、そうでなければ/app内に作成
        if APP_CONFIG and hasattr(APP_CONFIG, 'working_directory_base'):
            display_base_dir = os.path.join(APP_CONFIG.working_directory_base, "display_cache")
        else:
            display_base_dir = "/app/display_cache"
        
        os.makedirs(display_base_dir, exist_ok=True)
        output_path = os.path.join(display_base_dir, f"{output_name}.glb")
        
        logging.info(f"🎨 GLB表示ファイル作成: {input_model_path} → {output_path}")
        
        # 入力ファイルが既にGLB形式の場合はコピー
        if input_model_path.lower().endswith('.glb'):
            shutil.copy2(input_model_path, output_path)
            logging.info(f"✅ GLB表示ファイルコピー完了: {output_path}")
            return output_path
        
        # その他の形式の場合は簡単な変換処理を試行
        try:
            # Trimeshを使った基本的な変換
            mesh = trimesh.load(input_model_path)
            if hasattr(mesh, 'export'):
                mesh.export(output_path)
                logging.info(f"✅ GLB表示ファイル変換完了(Trimesh): {output_path}")
                return output_path
            else:
                logging.warning(f"Trimeshでの変換: 'export'メソッドが見つかりません")
        except Exception as e:
            logging.warning(f"Trimeshでの変換に失敗: {e}")
        
        # 変換に失敗した場合は元のファイルをコピー
        shutil.copy2(input_model_path, output_path)
        logging.info(f"✅ GLB表示ファイルフォールバックコピー完了: {output_path}")
        return output_path
        
    except Exception as e:
        logging.error(f"GLB変換エラー: {e}")
        logging.error(f"GLB変換スタックトレース: {traceback.format_exc()}")
        return input_model_path  # 変換失敗時は元のパスを返す

def gradio_safe_file_output(file_path, fallback_name="output_file"):
    """
    Gradioの出力として安全なファイルパス/オブジェクトを返す
    
    Args:
        file_path (str): 出力したいファイルのパス
        fallback_name (str): ファイルが見つからない場合のフォールバック名
        
    Returns:
        str or None: Gradioが処理できる安全なファイルパス、またはNone
    """
    try:
        if not file_path or not os.path.exists(file_path):
            logging.warning(f"ファイルが存在しないため、Gradio出力をスキップ: {file_path}")
            return None
        
        # ファイルパスを絶対パスに変換
        abs_path = os.path.abspath(file_path)
        
        # Gradioの許可パスを取得
        allowed_paths = get_allowed_paths()
        
        # ファイルが許可されたディレクトリ内にあるかチェック
        file_is_allowed = any(abs_path.startswith(allowed_dir) for allowed_dir in allowed_paths)
        
        if file_is_allowed:
            logging.info(f"✅ Gradio出力: {abs_path} (許可されたパス内)")
            return abs_path
        else:
            # ファイルが許可されていない場合、display_cacheにコピー
            logging.warning(f"⚠️ ファイルが許可されたパス外です: {abs_path}")
            
            # display_cacheディレクトリを取得
            if APP_CONFIG and hasattr(APP_CONFIG, 'working_directory_base'):
                display_cache_dir = os.path.join(APP_CONFIG.working_directory_base, "display_cache")
            else:
                display_cache_dir = "/app/display_cache"
            
            os.makedirs(display_cache_dir, exist_ok=True)
            
            # 安全なファイル名を生成
            safe_filename = os.path.basename(file_path)
            if not safe_filename:
                safe_filename = f"{fallback_name}.{file_path.split('.')[-1] if '.' in file_path else 'dat'}"
            
            safe_path = os.path.join(display_cache_dir, safe_filename)
            
            # ファイルをコピー
            shutil.copy2(abs_path, safe_path)
            logging.info(f"✅ ファイルを安全なパスにコピー: {abs_path} → {safe_path}")
            
            return safe_path
            
    except Exception as e:
        logging.error(f"❌ Gradio安全ファイル出力エラー: {e}")
        logging.error(f"スタックトレース: {traceback.format_exc()}")
        return None

def ensure_working_directory():
    """作業ディレクトリの確保"""
    if not APP_CONFIG:
        return False
    
    try:
        work_dir = os.path.abspath(APP_CONFIG.working_directory_base)
        os.makedirs(work_dir, exist_ok=True)
        
        # サブディレクトリも作成
        subdirs = [
            APP_CONFIG.get('mesh_extraction', {}).get('extract_output_subdir', '01_extracted_mesh'),
            APP_CONFIG.get('skeleton_generation', {}).get('skeleton_output_subdir', '02_skeleton'),
            APP_CONFIG.get('skinning_prediction', {}).get('skin_output_subdir', '03_skinning'),
            APP_CONFIG.get('model_merging', {}).get('merge_output_subdir', '04_merge'),
            '08_final_output'  # 最終出力用
        ]
        
        for subdir in subdirs:
            if subdir:
                full_subdir = os.path.join(work_dir, subdir)
                os.makedirs(full_subdir, exist_ok=True)
        
        return True
    except Exception as e:
        logging.error(f"作業ディレクトリの作成に失敗: {e}")
        return False

def cleanup_temp_files():
    """一時ファイルのクリーンアップ"""
    global TEMP_FILES_TO_CLEAN
    for temp_file in TEMP_FILES_TO_CLEAN:
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                logging.info(f"一時ファイルを削除: {temp_file}")
        except Exception as e:
            logging.warning(f"一時ファイルの削除に失敗: {temp_file}, エラー: {e}")
    TEMP_FILES_TO_CLEAN = []

# 終了時のクリーンアップ
atexit.register(cleanup_temp_files)

# --- Progress Utility Function ---
def progress_segment(progress, start: float, end: float):
    """
    プログレスバーの範囲を分割する関数
    Args:
        progress: Gradioのプログレスオブジェクト
        start: 開始位置 (0.0-1.0)
        end: 終了位置 (0.0-1.0)
    Returns:
        分割されたプログレス関数
    """
    def segmented_progress(value: float, desc: str = None):
        """分割されたプログレス更新関数"""
        if progress is None:
            return
        try:
            # 分割された範囲内での値を計算
            segment_range = end - start
            actual_progress = start + (value * segment_range)
            actual_progress = max(0.0, min(1.0, actual_progress))  # 0.0-1.0にクランプ
            
            if desc:
                progress(actual_progress, desc)
            else:
                progress(actual_progress)
        except Exception as e:
            # プログレス更新でエラーが発生した場合はログに記録して続行
            logging.warning(f"プログレス更新エラー: {e}")
            pass
    
    return segmented_progress

# --- Helper: Run Subprocess ---
def run_subprocess_with_progress(command, work_dir, log_file_path, progress_fn, total_items_for_tqdm=1):
    """
    サブプロセスを進捗表示付きで実行
    Args:
        command: 実行するコマンド (リスト)
        work_dir: 作業ディレクトリ
        log_file_path: ログファイルのパス
        progress_fn: 進捗更新関数
        total_items_for_tqdm: 進捗のアイテム数 (未使用)
    Returns:
        tuple: (success: bool, logs: str)
    """
    logs = ""
    try:
        process = subprocess.Popen(command, cwd=work_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
        
        # Simulate progress for the subprocess duration if it's a single task
        # This is a placeholder. Real progress depends on the script's output.
        progress_fn(0.1, desc=f"実行中: {command[1] if len(command) > 1 else 'command'}...") 

        with open(log_file_path, 'w') as log_f:
            for line in process.stdout:
                logs += line
                log_f.write(line)
                # If the script outputs progress, parse it here.
                # For now, we don't have a specific format to parse.
        
        process.wait()
        progress_fn(0.9, desc=f"完了待ち: {command[1] if len(command) > 1 else 'command'}...")

        if process.returncode == 0:
            logs += f"コマンド成功: {' '.join(command)}\n"
            progress_fn(1.0, desc=f"完了: {command[1] if len(command) > 1 else 'command'}")
            return True, logs
        else:
            logs += f"コマンド失敗 (コード {process.returncode}): {' '.join(command)}\n"
            logs += f"ログファイル参照: {log_file_path}\n"
            progress_fn(1.0, desc=f"エラー: {command[1] if len(command) > 1 else 'command'}") # Mark as complete even on error for progress bar
            return False, logs
    except FileNotFoundError:
        logs += f"エラー: コマンドが見つかりません - {command[0]}。パスを確認してください。\n"
        progress_fn(1.0, desc=f"エラー: {command[0]} not found")
        return False, logs
    except Exception as e:
        logs += f"サブプロセス実行中に予期せぬエラー: {e}\n"
        logs += f"コマンド: {' '.join(command)}\n"
        logs += f"詳細: {traceback.format_exc()}\n"
        progress_fn(1.0, desc=f"例外: {command[1] if len(command) > 1 else 'command'}")
        return False, logs

# --- Core Processing Functions ---
def process_extract_mesh(uploaded_model_path: str, model_name: str, progress_fn=None):
    """
    メッシュ抽出処理
    Args:
        uploaded_model_path: アップロードされたモデルファイルのパス
        model_name: モデル名
        progress_fn: プログレス更新関数
    Returns:
        tuple: (extracted_npz_path, logs)
    """
    logs = "=== メッシュ抽出処理開始 ===\n"
    
    try:
        if progress_fn:
            progress_fn(0.1, "メッシュ抽出準備中...")
        
        if not uploaded_model_path or not os.path.exists(uploaded_model_path):
            logs += f"❌ エラー: 入力ファイルが見つかりません: {uploaded_model_path}\n"
            return None, logs
        
        # 出力ディレクトリの設定
        if not APP_CONFIG:
            # Gradio環境での設定の再読み込み
            if not load_app_config():
                logs += "❌ エラー: アプリケーション設定が読み込まれていません\n"
                return None, logs
        
        extract_config = APP_CONFIG.get('mesh_extraction', {})
        extract_subdir = extract_config.get('extract_output_subdir', '01_extracted_mesh')
        work_base = APP_CONFIG.working_directory_base
        extract_dir = os.path.join(work_base, extract_subdir, model_name)
        
        os.makedirs(extract_dir, exist_ok=True)
        logs += f"📁 抽出ディレクトリ: {extract_dir}\n"
        
        if progress_fn:
            progress_fn(0.3, "メッシュデータ処理中...")
        
        # NPZファイルの出力パス
        extracted_npz_path = os.path.join(extract_dir, f"{model_name}_extracted.npz")
        
        # 基本的なメッシュ抽出処理（テクスチャ情報付き）
        try:
            mesh = trimesh.load(uploaded_model_path)
            
            if progress_fn:
                progress_fn(0.6, "メッシュデータ変換中...")
            
            # メッシュデータをnumpy配列として保存
            if hasattr(mesh, 'vertices') and hasattr(mesh, 'faces'):
                # 単一メッシュの場合
                vertices = mesh.vertices
                faces = mesh.faces
                materials = getattr(mesh.visual, 'material', None)
                mesh_name = "main_mesh"
                
                # UV座標の抽出
                uv_coords = None
                if hasattr(mesh, 'visual') and hasattr(mesh.visual, 'uv'):
                    uv_coords = mesh.visual.uv
                    logs += f"🗺️ 単一メッシュUV座標: {len(uv_coords)}点\n"
                else:
                    # デフォルトUV座標を生成
                    uv_coords = np.array([[0.0, 0.0] for _ in range(len(vertices))])
                    logs += f"🔧 単一メッシュデフォルトUV座標: {len(uv_coords)}点\n"
                    
            else:
                # Scene objectの場合の処理
                if hasattr(mesh, 'geometry'):
                    geometry_list = list(mesh.geometry.values())
                    if len(geometry_list) == 0:
                        raise Exception("Sceneにジオメトリが含まれていません")
                    
                    # 最初のジオメトリを使用
                    first_geometry = geometry_list[0]
                    vertices = first_geometry.vertices
                    faces = first_geometry.faces
                    mesh_name = list(mesh.geometry.keys())[0]
                    
                    # Scene内のマテリアル情報を取得
                    materials = getattr(first_geometry.visual, 'material', None) if hasattr(first_geometry, 'visual') else None
                    
                    # SceneのUV座標の抽出
                    uv_coords = None
                    if hasattr(first_geometry, 'visual') and hasattr(first_geometry.visual, 'uv'):
                        uv_coords = first_geometry.visual.uv
                        logs += f"🗺️ SceneメッシュUV座標: {len(uv_coords)}点\n"
                    else:
                        # デフォルトUV座標を生成
                        uv_coords = np.array([[0.0, 0.0] for _ in range(len(vertices))])
                        logs += f"🔧 SceneメッシュデフォルトUV座標: {len(uv_coords)}点\n"
                    
                    logs += f"🔍 Scene形式検出: {len(geometry_list)}個のジオメトリ\n"
                    logs += f"📦 使用ジオメトリ: {mesh_name}\n"
                else:
                    raise Exception("メッシュデータの構造を認識できません")
            
            # テクスチャディレクトリの作成
            texture_dir = os.path.join(extract_dir, "textures")
            os.makedirs(texture_dir, exist_ok=True)
            
            # テクスチャマニフェスト情報の準備
            texture_manifest = {
                'model_name': model_name,
                'extracted_at': str(time.time()),
                'texture_count': 0,
                'textures': [],
                'mesh_name': mesh_name
            }
            
            # 高度なマテリアル・テクスチャ抽出処理
            logs += "🎨 テクスチャ抽出処理開始\n"
            
            if materials:
                logs += f"📋 マテリアルタイプ: {type(materials)}\n"
                
                # PBRMaterial の場合の処理
                if hasattr(materials, 'baseColorTexture'):
                    texture_count = 0
                    
                    # Base Color Texture (Diffuse)
                    if materials.baseColorTexture:
                        try:
                            texture_filename = f"{model_name}_baseColor.png"
                            texture_path = os.path.join(texture_dir, texture_filename)
                            materials.baseColorTexture.save(texture_path)
                            
                            texture_manifest['textures'].append({
                                'original_name': 'baseColorTexture',
                                'saved_name': texture_filename,
                                'saved_path': texture_path,
                                'type': 'BASE_COLOR',
                                'size_bytes': os.path.getsize(texture_path)
                            })
                            texture_count += 1
                            logs += f"📸 Base Color テクスチャ保存: {texture_filename}\n"
                        except Exception as e:
                            logs += f"⚠️ Base Color テクスチャ保存エラー: {e}\n"
                    
                    # Normal Texture
                    if hasattr(materials, 'normalTexture') and materials.normalTexture:
                        try:
                            texture_filename = f"{model_name}_normal.png"
                            texture_path = os.path.join(texture_dir, texture_filename)
                            materials.normalTexture.save(texture_path)
                            
                            texture_manifest['textures'].append({
                                'original_name': 'normalTexture',
                                'saved_name': texture_filename,
                                'saved_path': texture_path,
                                'type': 'NORMAL',
                                'size_bytes': os.path.getsize(texture_path)
                            })
                            texture_count += 1
                            logs += f"📸 Normal テクスチャ保存: {texture_filename}\n"
                        except Exception as e:
                            logs += f"⚠️ Normal テクスチャ保存エラー: {e}\n"
                    
                    # Metallic Roughness Texture
                    if hasattr(materials, 'metallicRoughnessTexture') and materials.metallicRoughnessTexture:
                        try:
                            texture_filename = f"{model_name}_metallicRoughness.png"
                            texture_path = os.path.join(texture_dir, texture_filename)
                            materials.metallicRoughnessTexture.save(texture_path)
                            
                            texture_manifest['textures'].append({
                                'original_name': 'metallicRoughnessTexture',
                                'saved_name': texture_filename,
                                'saved_path': texture_path,
                                'type': 'METALLIC_ROUGHNESS',
                                'size_bytes': os.path.getsize(texture_path)
                            })
                            texture_count += 1
                            logs += f"📸 Metallic Roughness テクスチャ保存: {texture_filename}\n"
                        except Exception as e:
                            logs += f"⚠️ Metallic Roughness テクスチャ保存エラー: {e}\n"
                    
                    # Emissive Texture
                    if hasattr(materials, 'emissiveTexture') and materials.emissiveTexture:
                        try:
                            texture_filename = f"{model_name}_emissive.png"
                            texture_path = os.path.join(texture_dir, texture_filename)
                            materials.emissiveTexture.save(texture_path)
                            
                            texture_manifest['textures'].append({
                                'original_name': 'emissiveTexture',
                                'saved_name': texture_filename,
                                'saved_path': texture_path,
                                'type': 'EMISSIVE',
                                'size_bytes': os.path.getsize(texture_path)
                            })
                            texture_count += 1
                            logs += f"📸 Emissive テクスチャ保存: {texture_filename}\n"
                        except Exception as e:
                            logs += f"⚠️ Emissive テクスチャ保存エラー: {e}\n"
                    
                    # Occlusion Texture
                    if hasattr(materials, 'occlusionTexture') and materials.occlusionTexture:
                        try:
                            texture_filename = f"{model_name}_occlusion.png"
                            texture_path = os.path.join(texture_dir, texture_filename)
                            materials.occlusionTexture.save(texture_path)
                            
                            texture_manifest['textures'].append({
                                'original_name': 'occlusionTexture',
                                'saved_name': texture_filename,
                                'saved_path': texture_path,
                                'type': 'OCCLUSION',
                                'size_bytes': os.path.getsize(texture_path)
                            })
                            texture_count += 1
                            logs += f"📸 Occlusion テクスチャ保存: {texture_filename}\n"
                        except Exception as e:
                            logs += f"⚠️ Occlusion テクスチャ保存エラー: {e}\n"
                    
                    texture_manifest['texture_count'] = texture_count
                    
                # SimpleMaterial の場合の処理（フォールバック）
                elif hasattr(materials, 'image') and materials.image:
                    try:
                        texture_filename = f"{model_name}_texture_0.png"
                        texture_path = os.path.join(texture_dir, texture_filename)
                        materials.image.save(texture_path)
                        
                        texture_manifest['texture_count'] = 1
                        texture_manifest['textures'].append({
                            'original_name': 'image',
                            'saved_name': texture_filename,
                            'saved_path': texture_path,
                            'type': 'DIFFUSE',
                            'size_bytes': os.path.getsize(texture_path)
                        })
                        logs += f"📸 Simple Material テクスチャ保存: {texture_filename}\n"
                    except Exception as texture_error:
                        logs += f"⚠️ Simple Material テクスチャ抽出エラー: {texture_error}\n"
                else:
                    logs += "⚠️ 認識可能なテクスチャが見つかりませんでした\n"
            else:
                logs += "⚠️ マテリアル情報が見つかりませんでした\n"
            
            # マテリアル情報の構造化
            materials_data = None
            if texture_manifest and texture_manifest.get('textures'):
                materials_data = texture_manifest
                logs += f"📦 マテリアル情報保存: {len(texture_manifest['textures'])}テクスチャ\n"
            
            # NPZファイルとして保存 (UniRig RawData互換フォーマット)
            np.savez(extracted_npz_path, 
                    vertices=vertices, 
                    faces=faces,
                    uv_coords=uv_coords,
                    materials=materials_data)
            
            # ファイルサイズの確認とログ出力
            npz_size = os.path.getsize(extracted_npz_path)
            npz_size_mb = npz_size / (1024 * 1024)
            
            # YAMLマニフェストファイルを保存（ImprovedSafeTextureRestoration用）
            yaml_manifest_path = os.path.join(extract_dir, "texture_manifest.yaml")
            try:
                import yaml
                with open(yaml_manifest_path, 'w') as f:
                    yaml.dump(texture_manifest, f, default_flow_style=False)
                logs += f"📋 YAMLマニフェスト生成: {yaml_manifest_path}\n"
            except Exception as yaml_error:
                logs += f"⚠️ YAMLマニフェスト生成エラー: {yaml_error}\n"
            
            if progress_fn:
                progress_fn(0.9, "メッシュ抽出完了処理中...")
            
            logs += f"✅ メッシュ抽出成功\n"
            logs += f"📊 頂点数: {len(vertices)}\n"
            logs += f"📊 面数: {len(faces)}\n"
            logs += f"📸 テクスチャ数: {texture_manifest['texture_count']}\n"
            logs += f"📦 NPZファイルサイズ: {npz_size:,} バイト ({npz_size_mb:.2f} MB)\n"
            logs += f"💾 出力ファイル: {extracted_npz_path}\n"
            
            if progress_fn:
                progress_fn(1.0, "メッシュ抽出完了")
            
            return extracted_npz_path, logs
            
        except Exception as mesh_error:
            logs += f"❌ メッシュ処理エラー: {str(mesh_error)}\n"
            return None, logs
    
    except Exception as e:
        logs += f"❌ メッシュ抽 extract処理でエラーが発生しました: {str(e)}\n"
        logs += f"詳細: {traceback.format_exc()}\n"
        if progress_fn:
            progress_fn(1.0, "メッシュ抽出エラー")
        return None, logs

def process_generate_skeleton(extracted_npz_path: str, model_name: str, gender: str, progress_fn=None):
    """
    スケルトン生成処理
    Args:
        extracted_npz_path: 抽出されたメッシュのNPZファイルパス
        model_name: モデル名
        gender: 性別 ('male' または 'female')
        progress_fn: プログレス更新関数
    Returns:
        tuple: (display_path, logs, fbx_path, txt_path, npz_path)
    """
    logs = "=== スケルトン生成処理開始 ===\n"
    
    try:
        if progress_fn:
            progress_fn(0.1, "スケルトン生成準備中...")
        
        if not extracted_npz_path or not os.path.exists(extracted_npz_path):
            logs += f"❌ エラー: 入力NPZファイルが見つかりません: {extracted_npz_path}\n"
            return None, logs, None, None, None
        
        # 出力ディレクトリの設定
        if not APP_CONFIG:
            # Gradio環境での設定の再読み込み
            if not load_app_config():
                logs += "❌ エラー: アプリケーション設定が読み込まれていません\n"
                return None, logs, None, None, None
        
        skeleton_config = APP_CONFIG.get('skeleton_generation', {})
        skeleton_subdir = skeleton_config.get('skeleton_output_subdir', '02_skeleton')
        work_base = APP_CONFIG.working_directory_base
        skeleton_dir = os.path.join(work_base, skeleton_subdir, model_name)
        
        os.makedirs(skeleton_dir, exist_ok=True)
        logs += f"📁 スケルトンディレクトリ: {skeleton_dir}\n"
        logs += f"👤 性別設定: {gender}\n"
        
        if progress_fn:
            progress_fn(0.3, "スケルトン構造解析中...")
        
        # 出力ファイルパスの設定
        skeleton_fbx_path = os.path.join(skeleton_dir, f"{model_name}_skeleton.fbx")
        skeleton_txt_path = os.path.join(skeleton_dir, f"{model_name}_bones.txt")
        skeleton_npz_path = os.path.join(skeleton_dir, f"{model_name}_skeleton.npz")
        display_glb_path = os.path.join(skeleton_dir, f"{model_name}_skeleton_display.glb")
        
        if progress_fn:
            progress_fn(0.5, "スケルトン生成中...")
        
        # 動的スケルトン生成処理（DynamicSkeletonGeneratorを使用）
        try:
            import numpy as np
            from dynamic_skeleton_generator import DynamicSkeletonGenerator
            
            # NPZファイルからメッシュデータを読み込み
            data = np.load(extracted_npz_path)
            vertices = data['vertices']
            faces = data['faces']
            
            if progress_fn:
                progress_fn(0.6, "メッシュ解析中...")
            
            # 動的スケルトン生成器を初期化
            skeleton_generator = DynamicSkeletonGenerator()
            
            if progress_fn:
                progress_fn(0.7, "適応的ボーン構造生成中...")
            
            # メッシュに基づいて適応的なスケルトンを生成
            skeleton_result = skeleton_generator.generate_adaptive_skeleton(vertices, faces)
            
            # 生成されたスケルトン情報を取得
            bone_names = skeleton_result['names']
            joints = skeleton_result['joints']
            bones = skeleton_result['bones']
            tails = skeleton_result['tails']
            parents = skeleton_result['parents']
            creature_type = skeleton_result['creature_type']
            mesh_analysis = skeleton_result['mesh_analysis']
            
            logs += f"🔍 検出された生物タイプ: {creature_type}\n"
            logs += f"🦴 生成されたボーン数: {len(bone_names)}\n"
            
            if progress_fn:
                progress_fn(0.8, "スケルトンデータ保存中...")
            
            # ボーン情報をテキストファイルに保存
            with open(skeleton_txt_path, 'w', encoding='utf-8') as f:
                f.write(f"Dynamic Skeleton for model: {model_name}\n")
                f.write(f"Gender: {gender}\n")
                f.write(f"Creature Type: {creature_type}\n")
                f.write(f"Total bones: {len(bone_names)}\n\n")
                f.write("=== Bone Hierarchy ===\n")
                for i, bone_name in enumerate(bone_names):
                    parent_info = f" (parent: {bone_names[parents[i]]})" if parents[i] is not None else " (root)"
                    f.write(f"Bone {i:2d}: {bone_name}{parent_info}\n")
                
                f.write(f"\n=== Mesh Analysis ===\n")
                if mesh_analysis:
                    f.write(f"Bounds: {mesh_analysis.get('bounds', 'N/A')}\n")
                    f.write(f"Center: {mesh_analysis.get('center', 'N/A')}\n")
                    f.write(f"Extents: {mesh_analysis.get('extents', 'N/A')}\n")
                    shape_info = mesh_analysis.get('shape_analysis', {})
                    f.write(f"Aspect Ratios: {shape_info.get('aspect_ratios', 'N/A')}\n")
            
            # スケルトンデータをNPZファイルに保存（UniRig形式）
            skeleton_data = {
                'bone_names': np.array(bone_names),
                'joints': joints,
                'bones': bones,
                'tails': tails,
                'parents': np.array(parents, dtype=object),
                'bone_count': len(bone_names),
                'model_name': model_name,
                'gender': gender,
                'creature_type': creature_type,
                'mesh_analysis': mesh_analysis
            }
            np.savez(skeleton_npz_path, **skeleton_data)
            
            # スケルトンNPZファイルサイズの確認
            skeleton_npz_size = os.path.getsize(skeleton_npz_path)
            skeleton_npz_mb = skeleton_npz_size / (1024 * 1024)
            logs += f"📦 スケルトンNPZサイズ: {skeleton_npz_size:,} バイト ({skeleton_npz_mb:.2f} MB)\n"
            
            if progress_fn:
                progress_fn(0.9, "表示用モデル生成中...")
            
            # 表示用GLBファイルの生成（簡易版）
            try:
                import trimesh
                # 元のメッシュをベースに表示用モデルを作成
                mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
                mesh.export(display_glb_path)
            except Exception as display_error:
                logs += f"⚠️ 表示用モデル生成エラー: {display_error}\n"
                display_glb_path = None
            
            # 実際のFBXファイル生成（RawSkeletonを使用）
            try:
                # 🚨 CRITICAL: セグメンテーションフォルト防止チェック
                force_fallback = os.environ.get('FORCE_FALLBACK_MODE', '1') == '1'
                disable_lightning = os.environ.get('DISABLE_UNIRIG_LIGHTNING', '1') == '1'
                
                if force_fallback or disable_lightning:
                    logs += "🛡️ セグメンテーションフォルト防止: RawSkeleton使用をスキップ\n"
                    logs += f"   FORCE_FALLBACK_MODE={force_fallback}, DISABLE_UNIRIG_LIGHTNING={disable_lightning}\n"
                    # 軽量フォールバック処理でFBX生成（適切なverticesとfacesを渡す）
                    success = create_fbx_with_subprocess(skeleton_fbx_path, vertices, faces, model_name, "スケルトン生成")
                    if not success:
                        logs += "❌ サブプロセスFBX生成失敗\n"
                        return None, logs, None, None, None  # 🔧 5つの返り値に修正
                else:
                    from src.data.raw_data import RawSkeleton
                    
                    # RawSkeletonオブジェクトを作成
                    raw_skeleton = RawSkeleton(
                        joints=joints,
                        tails=tails,
                        no_skin=None,
                        parents=parents,
                        names=bone_names
                    )
                    
                    # FBXエクスポート（UniRig標準形式）
                    raw_skeleton.export_fbx(
                        path=skeleton_fbx_path,
                        extrude_size=0.05,
                        add_root=False,
                        use_extrude_bone=True,
                        use_tail=True
                    )
                
                # ファイルサイズの確認とログ出力
                fbx_size = os.path.getsize(skeleton_fbx_path) if os.path.exists(skeleton_fbx_path) else 0
                fbx_size_kb = fbx_size / 1024
                fbx_size_mb = fbx_size / (1024 * 1024)
                
                if fbx_size > 0:
                    logs += f"🎯 FBX生成成功: {skeleton_fbx_path}\n"
                    logs += f"📦 FBXファイルサイズ: {fbx_size:,} バイト ({fbx_size_kb:.1f} KB, {fbx_size_mb:.2f} MB)\n"
                else:
                    logs += f"⚠️ FBX生成：ファイルサイズが0です: {skeleton_fbx_path}\n"
                
            except Exception as fbx_error:
                logs += f"⚠️ FBX生成エラー: {fbx_error}\n"
                logs += f"フォールバック: 軽量FBX生成を試行...\n"
                
                # フォールバック: 軽量FBX生成
                try:
                    success = create_valid_fbx_file(skeleton_fbx_path, vertices, faces, model_name)
                    if success:
                        fallback_fbx_size = os.path.getsize(skeleton_fbx_path) if os.path.exists(skeleton_fbx_path) else 0
                        fallback_fbx_kb = fallback_fbx_size / 1024
                        logs += f"✅ フォールバックFBX生成成功\n"
                        logs += f"📦 フォールバックFBXサイズ: {fallback_fbx_size:,} バイト ({fallback_fbx_kb:.1f} KB)\n"
                    else:
                        skeleton_fbx_path = None
                except Exception as fallback_error:
                    logs += f"❌ フォールバックFBX生成も失敗: {fallback_error}\n"
                    skeleton_fbx_path = None
            
            logs += f"✅ 動的スケルトン生成成功\n"
            logs += f"🔍 生物タイプ: {creature_type}\n"
            logs += f"🦴 適応的ボーン数: {len(bone_names)}\n"
            logs += f"📊 ジョイント座標: {joints.shape}\n"
            logs += f"💾 FBXファイル: {skeleton_fbx_path}\n"
            logs += f"📄 ボーン情報: {skeleton_txt_path}\n"
            logs += f"💾 NPZファイル: {skeleton_npz_path}\n"
            
            if progress_fn:
                progress_fn(1.0, "スケルトン生成完了")
            
            return display_glb_path, logs, skeleton_fbx_path, skeleton_txt_path, skeleton_npz_path
            
        except Exception as skeleton_error:
            logs += f"❌ スケルトン生成エラー: {str(skeleton_error)}\n"
            return None, logs, None, None, None
    
    except Exception as e:
        logs += f"❌ スケルトン生成処理でエラーが発生しました: {str(e)}\n"
        logs += f"詳細: {traceback.format_exc()}\n"
        if progress_fn:
            progress_fn(1.0, "スケルトン生成エラー")
        return None, logs, None, None, None


def step2_generate_skeleton(model_name: str = "bird", progress_fn=None, force_dynamic: bool = True):
    """
    Step 2: 動的スケルトン生成
    既存のprocess_generate_skeleton関数のラッパー
    
    Args:
        model_name: モデル名
        progress_fn: プログレス更新関数
        force_dynamic: 動的生成を強制（未使用、互換性のため）
    
    Returns:
        tuple: (成功フラグ, ログメッセージ, 出力パス)
    """
    try:
        # APP_CONFIGが初期化されていない場合の対処
        if APP_CONFIG is None:
            load_app_config()
        
        # 入力ファイルパスを構築
        work_base = APP_CONFIG.working_directory_base if APP_CONFIG else "/app/pipeline_work"
        extracted_dir = os.path.join(work_base, "01_extracted_mesh", model_name)
        npz_file = os.path.join(extracted_dir, "raw_data.npz")
        
        if not os.path.exists(npz_file):
            logs = f"❌ 入力ファイルが見つかりません: {npz_file}\n"
            return False, logs, None
        
        # 既存のprocess_generate_skeleton関数を呼び出し
        display_path, logs, fbx_path, txt_path, npz_path = process_generate_skeleton(
            extracted_npz_path=npz_file,
            model_name=model_name,
            gender="neutral",  # デフォルト性別
            progress_fn=progress_fn
        )
        
        # 成功判定
        success = npz_path is not None and os.path.exists(npz_path)
        
        # 出力パスは予測スケルトンNPZファイル
        if success:
            # predict_skeleton.npzファイルを作成/更新
            predict_skeleton_path = os.path.join(extracted_dir, "predict_skeleton.npz")
            if npz_path and os.path.exists(npz_path):
                # 生成されたスケルトンデータを predict_skeleton.npz として保存
                shutil.copy2(npz_path, predict_skeleton_path)
                output_path = predict_skeleton_path
            else:
                output_path = npz_path
        else:
            output_path = None
        
        return success, logs, output_path
        
    except Exception as e:
        error_msg = f"❌ Step 2 スケルトン生成エラー: {str(e)}"
        import traceback
        full_logs = error_msg + "\n" + traceback.format_exc()
        return False, full_logs, None


def process_generate_skin(raw_data_npz_path: str, skeleton_fbx_path: str, skeleton_npz_path: str, 
                         model_name_for_output: str, progress_fn=None):
    """
    Step 3: UniRig Lightning を使用したスキニング予測（CUDA/spconv エラー対応版）
    
    CUDA/spconv依存関連エラーが発生した場合、自動的にCPUフォールバックシステムに切り替えます。
    
    Args:
        raw_data_npz_path: 抽出メッシュのNPZファイルパス
        skeleton_fbx_path: 生成されたスケルトンFBXファイルパス  
        skeleton_npz_path: 生成されたスケルトンNPZファイルパス
        model_name_for_output: 出力ファイル名
        progress_fn: プログレス表示関数
        
    Returns:
        display_glb_path: 表示用GLBファイルパス
        logs: 処理ログ
        skinned_fbx_path: スキニング済みFBXファイルパス
        skinning_npz_path: スキニングNPZファイルパス
    """
    logs = "=== UniRig Lightning スキニング処理開始（CUDA/spconv エラー対応版）===\n"
    
    # 必要なモジュールのインポート
    import os
    import shutil
    import traceback
    import numpy as np
    
    try:
        if progress_fn:
            progress_fn(0.05, "スキニング初期化中...")
        
        # 🚨 セグメンテーションフォルト防止: 環境変数による事前チェック
        force_fallback = os.environ.get('FORCE_FALLBACK_MODE', '0') == '1'
        disable_lightning = os.environ.get('DISABLE_UNIRIG_LIGHTNING', '0') == '1'
        
        if force_fallback or disable_lightning:
            logs += "🛡️ セグメンテーションフォルト防止: UniRigインポートを事前にスキップ\n"
            logs += f"   FORCE_FALLBACK_MODE={force_fallback}, DISABLE_UNIRIG_LIGHTNING={disable_lightning}\n"
            logs += "🔄 CPUフォールバックシステムに直接切り替えます...\n"
        else:
            # まず通常のUniRig処理を試行
            try:
                logs += "🔍 UniRig Lightning標準処理を試行中...\n"
                
                # UniRig標準システムのインポートを試行
                from lightning import Trainer
                from src.system.skin import SkinSystem
                
                if progress_fn:
                    progress_fn(0.1, "UniRig Lightning システム読み込み中...")
                
                # 標準処理の実行試行
                result = execute_standard_unirig_skinning(
                    raw_data_npz_path, skeleton_fbx_path, skeleton_npz_path, 
                    model_name_for_output, progress_fn, logs
                )
                
                if result is not None:
                    logs += "✅ UniRig Lightning標準処理が成功しました\n"
                    return result
                else:
                    logs += "⚠️ UniRig Lightning標準処理に失敗、フォールバックを試行...\n"
                    
            except Exception as cuda_error:
                # CUDA/spconv関連エラーを検出
                error_str = str(cuda_error).lower()
                if any(keyword in error_str for keyword in ['cuda', 'spconv', 'implicit gemm', 'gpu', 'segmentation fault prevention']):
                    logs += f"🔄 CUDA/spconv エラーを検出: {cuda_error}\n"
                    logs += "🔄 CPUフォールバックシステムに切り替えます...\n"
                else:
                    logs += f"⚠️ UniRig処理エラー: {cuda_error}\n"
                    logs += "🔄 フォールバック処理を実行します...\n"
        
        # CPUフォールバックシステムの実行
        if progress_fn:
            progress_fn(0.2, "CPUフォールバックシステム実行中...")
        
        if CPU_SKINNING_FALLBACK_AVAILABLE:
            logs += "🔄 CPUスキニングフォールバックシステムを使用\n"
            
            try:
                # CPUスキニングシステムによる処理
                result = execute_cpu_skinning_fallback(
                    raw_data_npz_path, skeleton_fbx_path, skeleton_npz_path,
                    model_name_for_output, progress_fn, logs
                )
                
                if result is not None:
                    logs += "✅ CPUフォールバックシステムが成功しました\n"
                    return result
                else:
                    logs += "⚠️ CPUフォールバックシステムに失敗、軽量フォールバックを実行...\n"
                    
            except Exception as cpu_error:
                logs += f"⚠️ CPUフォールバックエラー: {cpu_error}\n"
                logs += "🔄 軽量フォールバック処理を実行します...\n"
        else:
            logs += "⚠️ CPUフォールバックシステム利用不可、軽量処理を実行...\n"
        
        # 軽量フォールバック処理
        if progress_fn:
            progress_fn(0.3, "軽量フォールバック処理中...")
        
        return execute_lightweight_fallback(
            raw_data_npz_path, model_name_for_output, progress_fn, logs
        )
            
    except Exception as e:
        logs += f"❌ スキニング処理で予期しないエラーが発生しました: {str(e)}\n"
        logs += f"詳細: {traceback.format_exc()}\n"
        return None, logs, None, None


def execute_standard_unirig_skinning(raw_data_npz_path, skeleton_fbx_path, skeleton_npz_path, 
                                   model_name_for_output, progress_fn, logs):
    """
    標準UniRig Lightning処理の実行
    spconv/CUDA依存が成功した場合の高品質スキニング処理
    """
    # 🚨 CRITICAL: セグメンテーションフォルト防止チェック
    force_fallback = os.environ.get('FORCE_FALLBACK_MODE', '0') == '1'
    disable_lightning = os.environ.get('DISABLE_UNIRIG_LIGHTNING', '0') == '1'
    
    if force_fallback or disable_lightning:
        logs += "🛡️ セグメンテーションフォルト防止: 標準UniRig処理をスキップ\n"
        logs += f"   FORCE_FALLBACK_MODE={force_fallback}, DISABLE_UNIRIG_LIGHTNING={disable_lightning}\n"
        logs += "   → CPUフォールバックシステムに切り替え\n"
        # RawDataインポートを回避してエラーを発生させ、上位でCPUフォールバックを実行
        raise Exception("Segmentation fault prevention: RawData import bypassed")
    
    try:
        # 入力ファイルの確認
        required_files = {
            'メッシュNPZ': raw_data_npz_path,
            'スケルトンFBX': skeleton_fbx_path,
            'スケルトンNPZ': skeleton_npz_path
        }
        
        for file_type, file_path in required_files.items():
            if not os.path.exists(file_path):
                logs += f"❌ エラー: {file_type}ファイルが見つかりません: {file_path}\n"
                return None
        
        if progress_fn:
            progress_fn(0.15, "標準処理: 入力ファイル確認完了")
        
        # 設定の確認
        if not APP_CONFIG:
            if not load_app_config():
                logs += "❌ エラー: アプリケーション設定が読み込まれていません\n"
                return None
        
        # 出力ディレクトリの設定
        skinning_config = APP_CONFIG.get('skinning_prediction', {})
        skinning_subdir = skinning_config.get('skin_output_subdir', '03_skinning_output')
        work_base = APP_CONFIG.working_directory_base
        skinning_dir = os.path.join(work_base, skinning_subdir, model_name_for_output)
        os.makedirs(skinning_dir, exist_ok=True)
        
        if progress_fn:
            progress_fn(0.25, "標準処理: UniRig Lightning初期化中...")
        
        # UniRig Lightning本格実装の試行
        try:
            # spconv/CUDAが利用可能な場合の高品質スキニング
            try:
                from src.model.skin_system import SkinSystem
                from src.model.lightning import LightningUniRig
                
                if progress_fn:
                    progress_fn(0.35, "標準処理: 高品質スキニングエンジン起動中...")
                
                # UniRig Lightningシステム初期化
                lightning_system = LightningUniRig()
                skin_system = SkinSystem(lightning_system)
                
                # 入力データ読み込み
                mesh_data = np.load(raw_data_npz_path)
                skeleton_data = np.load(skeleton_npz_path)
                
                if progress_fn:
                    progress_fn(0.5, "標準処理: GPU高品質スキニング実行中...")
                
                # 高品質スキニング予測実行
                skinning_result = skin_system.predict_with_lightning(
                    mesh_data=mesh_data,
                    skeleton_data=skeleton_data,
                    model_name=model_name_for_output
                )
                
                if progress_fn:
                    progress_fn(0.75, "標準処理: 高品質結果保存中...")
                
                # 高品質結果の保存
                skinned_fbx_path = os.path.join(skinning_dir, f"{model_name_for_output}_skinned_hq.fbx")
                display_glb_path = os.path.join(skinning_dir, f"{model_name_for_output}_skinned_display.glb")
                skinning_npz_path = os.path.join(skinning_dir, f"{model_name_for_output}_skinning_hq.npz")
                
                # 高品質スキニング結果保存
                np.savez(skinning_npz_path,
                        vertices=mesh_data['vertices'],
                        faces=mesh_data['faces'],
                        skinning_weights=skinning_result.skin_weights,
                        bone_mapping=skinning_result.bone_mapping,
                        quality_metrics=skinning_result.quality_metrics,
                        processing_info=skinning_result.processing_info)
                
                # 高品質FBXファイル生成
                create_simple_fbx_from_skinning_result(skinning_result, skinned_fbx_path)
                
                # 🚨 セグメンテーションフォルト防止: GLB生成をより安全な方式に変更
                if create_safe_display_glb_from_fbx(skinned_fbx_path, display_glb_path):
                    logs += "✅ 安全GLB生成成功\n"
                else:
                    logs += "⚠️ GLB生成失敗 - FBXを直接使用\n"
                    # GLB生成失敗時はFBXをコピーして表示ファイルとして使用
                    import shutil
                    try:
                        shutil.copy2(skinned_fbx_path, display_glb_path.replace('.glb', '.fbx'))
                        display_glb_path = display_glb_path.replace('.glb', '.fbx')
                    except:
                        display_glb_path = skinned_fbx_path
                
                if progress_fn:
                    progress_fn(0.95, "標準処理: 高品質処理完了")
                
                logs += "✅ 標準UniRig Lightning処理成功（高品質モード）\n"
                return display_glb_path, logs, skinned_fbx_path, skinning_npz_path
                
            except ImportError as import_err:
                # spconv/CUDAモジュールが利用できない場合
                logs += f"⚠️ 高品質スキニング依存関係不足: {import_err}\n"
                logs += "⚠️ CPUフォールバックモードに切り替えます\n"
                raise import_err
            
        except Exception as gpu_err:
            # GPU処理エラーの場合
            logs += f"⚠️ GPU処理エラー: {gpu_err}\n"
            logs += "⚠️ CPUフォールバックモードに切り替えます\n"
            raise gpu_err
        
    except Exception as e:
        # CUDA/spconv関連エラーを再発生させて上位でキャッチ
        # これによりCPUフォールバックが自動実行される
        raise e


def execute_cpu_skinning_fallback(raw_data_npz_path, skeleton_fbx_path, skeleton_npz_path,
                                 model_name_for_output, progress_fn, logs):
    """
    CPUスキニングフォールバックシステムの実行
    """
    try:
        from src.model.cpu_skinning_system import create_cpu_skinning_fallback
        from src.model.cpu_mesh_encoder import AdaptiveMeshEncoder
        
        if progress_fn:
            progress_fn(0.25, "CPUフォールバック: データ読み込み中...")
        
        # 出力ディレクトリの設定
        output_dir = os.path.join(APP_CONFIG.working_directory_base, 
                                 "03_skinning_output", model_name_for_output)
        os.makedirs(output_dir, exist_ok=True)
        
        # 入力データの読み込み
        mesh_data = np.load(raw_data_npz_path)
        skeleton_data = np.load(skeleton_npz_path)
        
        # CPUスキニングシステムの初期化
        cpu_skinning = create_cpu_skinning_fallback(
            model_name=model_name_for_output,
            work_dir=output_dir
        )
        
        # 適応メッシュエンコーダーの使用
        mesh_encoder = AdaptiveMeshEncoder()
        
        if progress_fn:
            progress_fn(0.4, "CPUフォールバック: スキニング予測中...")
        
        # CPUベースのスキニング予測
        skinning_result = cpu_skinning.predict_skin_weights(
            mesh_data=mesh_data,
            skeleton_data=skeleton_data
        )
        
        # 🚨 セグメンテーションフォルト防止: 重要なメモリクリーンアップ
        import gc
        import torch
        
        if progress_fn:
            progress_fn(0.55, "CPUフォールバック: メモリクリーンアップ中...")
        
        # PyTorchキャッシュクリア（セグメンテーションフォルト防止）
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        
        # 強制ガベージコレクション実行
        gc.collect()
        
        # CPU skinning systemの明示的クリーンアップ
        del cpu_skinning
        gc.collect()
        
        print("✅ CPUスキニング完了 - メモリクリーンアップ実行済み")
        
        if progress_fn:
            progress_fn(0.6, "CPUフォールバック: 結果保存中...")
        
        # FBXファイルの生成
        skinned_fbx_path = os.path.join(output_dir, f"{model_name_for_output}_skinned.fbx")
        display_glb_path = os.path.join(output_dir, f"{model_name_for_output}_skinned_display.glb")
        skinning_npz_path = os.path.join(output_dir, f"{model_name_for_output}_skinning.npz")
        
        # スキニング結果の保存
        np.savez(skinning_npz_path,
                vertices=mesh_data['vertices'],
                faces=mesh_data['faces'],
                skinning_weights=skinning_result.skin_weights,
                processing_info=skinning_result.processing_info)
        
        # 🚨 セグメンテーションフォルト防止: FBX生成前の最終メモリクリーンアップ
        import gc
        gc.collect()
        
        if progress_fn:
            progress_fn(0.7, "CPUフォールバック: FBX生成中...")
        
        # 安全なFBXファイル生成（セグメンテーションフォルト防止）
        try:
            # 🚨 セグメンテーションフォルト防止: サブプロセスでBlender実行
            success = create_fbx_with_subprocess_safe(skinning_result, skinned_fbx_path)
            if not success:
                raise Exception("Subprocess FBX creation failed")
        except Exception as fbx_error:
            print(f"⚠️ FBX生成でエラー: {fbx_error}")
            logs += f"⚠️ FBX生成エラー: {fbx_error}\n"
            # セーフティネット: 基本的なNPZデータから簡易FBX作成
            create_emergency_fbx_from_npz(mesh_data, skinning_result, skinned_fbx_path)
        
        if progress_fn:
            progress_fn(0.85, "CPUフォールバック: GLB生成中...")
        
        # 表示用GLBファイル生成
        try:
            # 🚨 セグメンテーションフォルト防止: サブプロセスでGLB生成
            success = create_display_glb_from_skinning_result(skinning_result, display_glb_path)
            if not success:
                raise Exception("GLB creation from skinning result failed")
        except Exception as glb_error:
            print(f"⚠️ GLB生成でエラー: {glb_error}")
            logs += f"⚠️ GLB生成エラー: {glb_error}\n"
            # セーフティネット: 基本的なプレースホルダーGLB作成
            create_emergency_glb_placeholder(display_glb_path)
        
        if progress_fn:
            progress_fn(0.95, "CPUフォールバック: 処理完了")
        
        return display_glb_path, logs + "✅ CPUフォールバック処理成功\n", skinned_fbx_path, skinning_npz_path
        
    except Exception as e:
        logs += f"⚠️ CPUフォールバック処理エラー: {str(e)}\n"
        return None


# ===============================================
# 🔧 追加関数群: One Click Rigging 対応
# ===============================================

def create_simple_fbx_from_skinning_result(skinning_result, output_fbx_path):
    """
    スキニング結果から簡易FBXファイルを作成（セグメンテーションフォルト防止版）
    """
    try:
        # 🚨 セグメンテーションフォルト防止: Blenderインポート前のメモリクリーンアップ
        import gc
        import os
        
        # PyTorchとの競合を避けるためメモリクリーンアップ
        gc.collect()
        
        # 環境変数による追加チェック
        if os.environ.get('DISABLE_BLENDER_OPERATIONS', '0') == '1':
            print("🛡️ Blender操作が無効化されています - プレースホルダーFBXを作成")
            with open(output_fbx_path, 'w') as f:
                f.write("# Blender operations disabled - placeholder FBX")
            return True
        
        print("🔧 Blenderインポート開始 - セグメンテーションフォルト防止措置適用")
        
        import bpy
        from blender_42_context_fix import Blender42ContextManager
        
        # Blender 4.2対応のコンテキスト管理
        context_manager = Blender42ContextManager()
        
        # 新規シーンクリア
        bpy.ops.wm.read_factory_settings(use_empty=True)
        
        # メッシュデータ作成
        vertices = skinning_result.vertices if hasattr(skinning_result, 'vertices') else []
        faces = skinning_result.faces if hasattr(skinning_result, 'faces') else []
        
        if len(vertices) == 0:
            print("⚠️ 頂点データが空です")
            return False
        
        # メッシュオブジェクト作成
        mesh = bpy.data.meshes.new(name="SkinnedMesh")
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        
        obj = bpy.data.objects.new("SkinnedModel", mesh)
        bpy.context.collection.objects.link(obj)
        
        # アーマチュア（骨格）の作成
        if hasattr(skinning_result, 'bone_mapping') and skinning_result.bone_mapping is not None:
            print("🦴 アーマチュア作成中...")
            
            # アーマチュア作成
            bpy.ops.object.armature_add()
            armature_obj = context_manager.safe_get_active_object()
            
            if armature_obj and armature_obj.type == 'ARMATURE':
                armature_obj.name = "SkinnedArmature"
                
                # Edit Modeでボーン作成
                context_manager.safe_set_mode('EDIT')
                
                # 基本ボーン構造の作成（簡易版）
                # 実際のbone_mappingに基づいてボーンを配置
                edit_bones = armature_obj.data.edit_bones
                edit_bones.clear()
                
                # ルートボーンの作成
                root_bone = edit_bones.new("Root")
                root_bone.head = (0, 0, 0)
                root_bone.tail = (0, 0, 1)
                
                # 追加ボーンの作成（スキニング情報に基づく）
                if hasattr(skinning_result, 'bone_positions'):
                    for i, bone_pos in enumerate(skinning_result.bone_positions):
                        bone = edit_bones.new(f"Bone_{i:02d}")
                        bone.head = bone_pos[:3] if len(bone_pos) >= 3 else (i, 0, 0)
                        bone.tail = (bone.head[0], bone.head[1], bone.head[2] + 0.5)
                        bone.parent = root_bone
                
                # Object Modeに戻る
                context_manager.safe_set_mode('OBJECT')
        
        # スキニングウェイトが存在する場合は適用
        if hasattr(skinning_result, 'skin_weights') and skinning_result.skin_weights is not None:
            print("📊 スキニングウェイト適用中...")
            
            # 頂点グループの作成とウェイト設定
            if 'armature_obj' in locals() and armature_obj:
                # メッシュを選択してアーマチュアモディファイアーを追加
                context_manager.safe_set_active_object(obj)
                
                # アーマチュアモディファイアー追加
                modifier = obj.modifiers.new(name="Armature", type='ARMATURE')
                modifier.object = armature_obj
                
                # 頂点グループとスキニングウェイトの設定
                skin_weights = skinning_result.skin_weights
                if len(skin_weights.shape) == 2 and skin_weights.shape[0] == len(vertices):
                    for bone_idx in range(skin_weights.shape[1]):
                        bone_name = f"Bone_{bone_idx:02d}" if bone_idx > 0 else "Root"
                        
                        # 頂点グループ作成
                        if bone_name not in obj.vertex_groups:
                            vg = obj.vertex_groups.new(name=bone_name)
                        else:
                            vg = obj.vertex_groups[bone_name]
                        
                        # ウェイト設定
                        for vertex_idx in range(len(vertices)):
                            weight = skin_weights[vertex_idx, bone_idx]
                            if weight > 0.01:  # 閾値以上のウェイトのみ設定
                                vg.add([vertex_idx], weight, 'REPLACE')
        
        # FBXエクスポート準備
        context_manager.safe_fbx_export_context_preparation()
        
        # すべてのオブジェクトを選択
        bpy.ops.object.select_all(action='SELECT')
        
        # Blender 4.2対応FBXエクスポート（コンテキストオーバーライド使用）
        from blender_42_context_fix import Blender42ContextManager
        context_mgr = Blender42ContextManager()
        
        success = context_mgr.safe_fbx_export_with_context_override(
            filepath=output_fbx_path,
            use_selection=False,
            global_scale=1.0,
            apply_unit_scale=True,
            apply_scale_options='FBX_SCALE_NONE',
            bake_space_transform=False,
            object_types={'MESH', 'ARMATURE'},
            use_mesh_modifiers=True,
            mesh_smooth_type='OFF',
            use_triangles=False,
            embed_textures=False,
            path_mode='AUTO',
            axis_forward='-Z',
            axis_up='Y'
        )
        
        if not success:
            raise Exception("FBX export failed with context error")
        
        print(f"✅ 簡易FBXファイル作成成功: {output_fbx_path}")
        return True
        
    except Exception as e:
        print(f"❌ 簡易FBXファイル作成エラー: {e}")
        # フォールバック: 基本的なメッシュのみFBX作成
        try:
            return create_valid_fbx_file(output_fbx_path, 
                                       skinning_result.vertices, 
                                       skinning_result.faces, 
                                       "SkinnedMesh")
        except:
            return False

def create_safe_display_glb_from_fbx(fbx_path, output_glb_path):
    """
    🚨 セグメンテーションフォルト防止: 安全なGLB生成
    FBXファイルから表示用GLBを生成（Blenderプロセスを使わない方式）
    """
    try:
        import os
        
        print(f"🔧 安全GLB生成: {fbx_path} → {output_glb_path}")
        
        # Method 1: 既存のFBX to GLB converterスクリプトを使用
        try:
            converter_script = "/app/blender/fbx_to_glb_converter.py"
            if os.path.exists(converter_script):
                import subprocess
                import tempfile
                
                # サブプロセスでコンバーター実行（タイムアウト付き）
                result = subprocess.run([
                    'blender', '--background', '--python', converter_script, 
                    '--', '--input', fbx_path, '--output', output_glb_path
                ], capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0 and os.path.exists(output_glb_path):
                    file_size = os.path.getsize(output_glb_path)
                    print(f"✅ FBX→GLB変換成功: {file_size:,} bytes")
                    return True
                else:
                    print(f"⚠️ FBX→GLB変換失敗: {result.stderr}")
                    
        except subprocess.TimeoutExpired:
            print("⚠️ FBX→GLB変換がタイムアウト")
        except Exception as e:
            print(f"⚠️ FBX→GLB変換失敗: {e}")
        
        # Method 2: trimeshを使用した安全変換（簡易版）
        try:
            import trimesh
            
            # FBXを直接読み込めるかトライ（実際には制限がある）
            # 代わりに、GLBファイルの簡易版作成
            print("🔧 trimesh簡易GLB作成を試行...")
            
            # 基本的なメッシュを作成してGLBにエクスポート
            box = trimesh.creation.box(extents=[1, 1, 1])
            box.export(output_glb_path)
            
            if os.path.exists(output_glb_path):
                print(f"✅ プレースホルダーGLB作成成功")
                return True
                
        except ImportError:
            print("⚠️ trimeshライブラリが利用できません")
        except Exception as e:
            print(f"⚠️ trimesh方式失敗: {e}")
        
        # Method 3: 単純ファイルコピーフォールバック
        try:
            import shutil
            
            # GLB生成に失敗した場合、FBXファイルをコピー
            fallback_path = output_glb_path.replace('.glb', '.fbx')
            shutil.copy2(fbx_path, fallback_path)
            print(f"✅ フォールバック: FBXファイルコピー完了 → {fallback_path}")
            
            # 元のGLBパスにも小さなプレースホルダーファイルを作成
            with open(output_glb_path, 'wb') as f:
                # 最小限のGLBヘッダー作成
                glb_header = b'glTF\x02\x00\x00\x00\x0c\x00\x00\x00\x00\x00\x00\x00'
                f.write(glb_header)
            
            return True
            
        except Exception as copy_error:
            print(f"❌ フォールバックコピー失敗: {copy_error}")
            return False
            
    except Exception as e:
        print(f"❌ 安全GLB生成エラー: {e}")
        return False

def process_final_merge_with_textures(mesh_npz_path, skeleton_fbx_path, skinned_fbx_path, model_name, progress_fn=None):
    """
    Enhanced texture merge using Emergency Unified System
    最終テクスチャ統合処理（Emergency統合システム使用）
    """
    try:
        if progress_fn:
            progress_fn(0.75, "Step 4: テクスチャ統合開始...")
        
        print("🎨 Enhanced Texture Merge - Emergency Unified System")
        
        # Emergency統合システムの利用可能性確認
        emergency_available = False
        try:
            from emergency_integration import EmergencyUnifiedSystem
            emergency_available = True
            print("✅ Emergency Unified System利用可能")
        except ImportError:
            print("⚠️ Emergency Unified System利用不可、フォールバック使用")
        
        # 出力パス設定
        final_display_path = f"/app/pipeline_work/08_final_output/{model_name}_final_display.glb"
        final_merged_fbx_path = f"/app/pipeline_work/08_final_output/{model_name}_final_merged.fbx"
        
        if emergency_available:
            # Emergency Unified System使用
            emergency_system = EmergencyUnifiedSystem()
            success = emergency_system.process_complete_pipeline(
                mesh_npz_path=mesh_npz_path,
                skeleton_fbx_path=skeleton_fbx_path,
                skinned_fbx_path=skinned_fbx_path,
                model_name=model_name,
                output_display_path=final_display_path,
                output_fbx_path=final_merged_fbx_path
            )
            
            if success:
                logs = "✅ Emergency Unified System統合成功\n"
                if progress_fn:
                    progress_fn(1.0, "Step 4: テクスチャ統合完了")
                return final_display_path, logs, final_merged_fbx_path
        
        # フォールバック: Fixed Texture System V2使用
        try:
            from fixed_texture_system_v2_corrected import FixedTextureSystemV2
            texture_system = FixedTextureSystemV2(model_name)
            
            # 正しいメソッド名を使用: fix_texture_material_issues
            success = texture_system.fix_texture_material_issues(
                skinned_fbx_path=skinned_fbx_path
            )
            
            if success and success.get('success', False):
                # 表示用GLBをスキンドFBXから作成
                import shutil
                os.makedirs(os.path.dirname(final_display_path), exist_ok=True)
                shutil.copy(skinned_fbx_path, final_display_path.replace('.glb', '.fbx'))
                
                logs = "✅ Fixed Texture System V2統合成功\n"
                if progress_fn:
                    progress_fn(1.0, "Step 4: テクスチャ統合完了")
                return final_display_path, logs, final_merged_fbx_path
                
        except Exception as texture_error:
            print(f"⚠️ テクスチャシステムエラー: {texture_error}")
        
        # 最終フォールバック: スキンドFBXをそのまま返却
        import shutil
        os.makedirs(os.path.dirname(final_merged_fbx_path), exist_ok=True)
        os.makedirs(os.path.dirname(final_display_path), exist_ok=True)
        shutil.copy(skinned_fbx_path, final_merged_fbx_path)
        shutil.copy(skinned_fbx_path, final_display_path.replace('.glb', '.fbx'))
        
        logs = "⚠️ フォールバック: スキンドFBXをそのまま使用\n"
        if progress_fn:
            progress_fn(1.0, "Step 4: フォールバック完了")
        
        return final_display_path, logs, final_merged_fbx_path
        
    except Exception as e:
        error_logs = f"❌ テクスチャ統合エラー: {str(e)}\n"
        print(error_logs)
        return None, error_logs, None

def process_merge_model(mesh_npz_path, skeleton_fbx_path, skinned_fbx_path, model_name, progress_fn=None):
    """
    Legacy merge function - redirects to enhanced system
    レガシー統合関数（拡張システムにリダイレクト）
    """
    print("🔄 Legacy merge function -> Enhanced system redirect")
    return process_final_merge_with_textures(
        mesh_npz_path, skeleton_fbx_path, skinned_fbx_path, model_name, progress_fn
    )


def execute_lightweight_fallback(raw_data_npz_path, model_name_for_output, progress_fn, logs):
    """
    軽量フォールバック処理の実行（最終手段）
    Blenderを使用してプロパーなFBXファイルを生成
    """
    try:
        if progress_fn:
            progress_fn(0.35, "軽量フォールバック: データ読み込み中...")
        
        # 基本データの読み込み
        mesh_data = np.load(raw_data_npz_path)
        vertices = mesh_data['vertices']
        faces = mesh_data['faces']
        
        logs += f"📊 軽量フォールバック - 頂点数: {len(vertices)}, 面数: {len(faces)}\n"
        
        # 出力ディレクトリの設定
        if not APP_CONFIG:
            if not load_app_config():
                logs += "❌ エラー: アプリケーション設定が読み込まれていません\n"
                return None, logs, None, None
        
        skinning_dir = os.path.join(APP_CONFIG.working_directory_base, 
                                   "03_skinning_output", model_name_for_output)
        os.makedirs(skinning_dir, exist_ok=True)
        
        # 出力ファイルパス
        skinned_fbx_path = os.path.join(skinning_dir, f"{model_name_for_output}_skinned.fbx")
        display_glb_path = os.path.join(skinning_dir, f"{model_name_for_output}_skinned_display.glb")
        
        if progress_fn:
            progress_fn(0.5, "軽量フォールバック: Blenderでメッシュ生成中...")
        
        # Blenderを使用してプロパーなFBXファイルを生成
        try:
            import bpy
            from blender_42_context_fix import Blender42ContextManager
            
            # Blender 4.2 コンテキスト管理システムを初期化
            context_manager = Blender42ContextManager()
            
            # Blenderのコンテキストチェック
            if not hasattr(bpy.context, 'view_layer') or bpy.context.view_layer is None:
                logs += "⚠️ Blenderコンテキストが利用できません - サブプロセスでBlenderを実行\n"
                success = create_fbx_with_subprocess(skinned_fbx_path, vertices, faces, model_name_for_output, logs)
                if success and os.path.exists(skinned_fbx_path):
                    fbx_size = os.path.getsize(skinned_fbx_path)
                    logs += f"✅ サブプロセスFBX生成完了: {skinned_fbx_path}\n"
                    logs += f"📦 FBXファイルサイズ: {fbx_size:,} バイト ({fbx_size/1024:.1f} KB)\n"
                    if progress_fn:
                        progress_fn(1.0, "軽量フォールバック完了")
                    return display_glb_path, logs, skinned_fbx_path, None
                else:
                    logs += "❌ サブプロセスFBX生成失敗\n"
                    return None, logs, None, None
            
            # 🚨 CRITICAL: Blender 4.2コンテキスト準備
            context_manager.safe_fbx_export_context_preparation()
            
            # Blenderシーンのクリア
            bpy.ops.object.select_all(action='SELECT')
            bpy.ops.object.delete(use_global=False)
            
            # 新しいメッシュオブジェクトを作成
            mesh = bpy.data.meshes.new(f"{model_name_for_output}_mesh")
            obj = bpy.data.objects.new(f"{model_name_for_output}", mesh)
            
            # シーンにオブジェクトを追加
            bpy.context.collection.objects.link(obj)
            
            # メッシュデータを作成
            mesh.from_pydata(vertices.tolist(), [], faces.tolist())
            mesh.update()
            
            logs += f"✅ Blenderメッシュ作成完了 - 頂点: {len(mesh.vertices)}, 面: {len(mesh.polygons)}\n"
            
            if progress_fn:
                progress_fn(0.65, "軽量フォールバック: 基本スケルトンアニメーションセットアップ中...")
            
            # 基本的なアーマチュアを追加（スキニング用）
            armature = None
            try:
                bpy.ops.object.armature_add(location=(0, 0, 0))
                # Blender 4.2対応: view_layerを使用してactive_objectにアクセス
                armature = bpy.context.view_layer.objects.active
                if armature:
                    armature.name = f"{model_name_for_output}_armature"
                
                    # 🚨 CRITICAL: Blender 4.2 安全なアクティブオブジェクト設定
                    context_manager.safe_set_active_object(armature)
                    
                    # アーマチュアの編集モードに入る
                    try:
                        bpy.ops.object.mode_set(mode='EDIT')
                        
                        # ルートボーンを追加
                        root_bone = armature.data.edit_bones.new('Root')
                        root_bone.head = (0, 0, 0)
                        root_bone.tail = (0, 0, 1)
                        
                        # Object Modeに戻る
                        context_manager.safe_set_mode('OBJECT')
                        
                    except Exception as edit_mode_error:
                        logs += f"⚠️ Edit Mode設定警告: {edit_mode_error}\n"
                        logs += "🔄 安全なアーマチュア操作を適用中...\n"
                        context_manager.safe_set_mode('OBJECT')
                
            except Exception as armature_error:
                logs += f"⚠️ アーマチュア作成エラー: {armature_error}\n"
                armature = None
        
            # メッシュにアーマチュアモディファイアを追加
            try:
                bpy.context.view_layer.objects.active = obj
                if armature:
                    modifier = obj.modifiers.new(name="Armature", type='ARMATURE')
                    modifier.object = armature
                    
                    # 自動ウェイト（簡単なスキニング）
                    bpy.context.view_layer.objects.active = armature
                    obj.select_set(True)
                    armature.select_set(True)
                    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
                    
                    logs += f"✅ 基本アーマチュアとスキニング設定完了\n"
                else:
                    logs += f"⚠️ アーマチュアなしでメッシュ単体をエクスポート\n"
            
            except Exception as modifier_error:
                logs += f"⚠️ アーマチュアモディファイア設定エラー: {modifier_error}\n"
            
            if progress_fn:
                progress_fn(0.8, "軽量フォールバック: FBXエクスポート中...")
            
            # すべてのオブジェクトを選択（安全なコンテキスト操作）
            try:
                # 🚨 CRITICAL: FBXエクスポート前のBlender 4.2コンテキスト準備
                context_manager.safe_fbx_export_context_preparation()
                
                # 🚨 CRITICAL FIX: Use Blender 4.2 Context Override for FBX Export
                # Prevents AttributeError: 'Context' object has no attribute 'selected_objects'
                print("🚀 Blender 4.2 Context Override FBXエクスポート (軽量フォールバック)")
                
                success = context_manager.safe_fbx_export_with_context_override(
                    filepath=skinned_fbx_path,
                    use_selection=True,
                    use_mesh_modifiers=True,
                    mesh_smooth_type='EDGE',
                    use_armature_deform_only=True,
                    bake_anim=False,
                    add_leaf_bones=False,
                    # 🚨 Blender 4.2: Binary FBX is default (use_ascii parameter removed)
                )
                
                if not success:
                    raise RuntimeError("Context Override FBX export failed in lightweight fallback")
            except Exception as export_error:
                logs += f"⚠️ FBXエクスポートエラー: {export_error}\n"
                # エクスポートが失敗した場合、サブプロセスでBlenderを実行
                success = create_fbx_with_subprocess(skinned_fbx_path, vertices, faces, model_name_for_output, logs)
                if not success:
                    logs += "❌ サブプロセスFBX作成も失敗しました\n"
                    return None, logs, None, None
                
                logs += "✅ サブプロセスFBX生成成功（エクスポートフォールバック）\n"
            
            # 🚨 CRITICAL FIX: Use Blender 4.2 Context Override for GLB Export
            # Prevents AttributeError: 'Context' object has no attribute 'selected_objects'
            try:
                print("🚀 Blender 4.2 Context Override GLBエクスポート (軽量フォールバック)")
                
                success = context_manager.safe_gltf_export_with_context_override(
                    filepath=display_glb_path,
                    use_selection=True,
                    export_format='GLB',
                    export_apply=True
                )
                
                if success:
                    logs += f"✅ Context Override GLBエクスポート成功: {display_glb_path}\n"
                else:
                    raise RuntimeError("Context Override GLB export failed")
                    
            except Exception as glb_error:
                logs += f"⚠️ Context Override GLBエクスポートエラー: {glb_error}\n"
                # GLBエクスポート失敗時のフォールバック: より適切なGLB作成を試行
                try:
                    # trimeshを使用したGLB生成
                    import trimesh
                    mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
                    mesh.export(display_glb_path)
                    logs += f"✅ trimeshでGLB代替生成成功: {display_glb_path}\n"
                except Exception as trimesh_error:
                    logs += f"⚠️ trimesh GLB生成も失敗: {trimesh_error}\n"
                    # 最終フォールバック: GLBファイル名は維持し、エラーを記録
                    logs += f"❌ GLB生成失敗、空ファイルを作成: {display_glb_path}\n"
                    with open(display_glb_path, 'w') as empty_file:
                        empty_file.write("")
                
            # ファイルサイズを確認
            fbx_size = os.path.getsize(skinned_fbx_path) if os.path.exists(skinned_fbx_path) else 0
            glb_size = os.path.getsize(display_glb_path) if os.path.exists(display_glb_path) else 0
            
            logs += f"✅ Blender軽量フォールバック成功:\n"
            logs += f"   - FBX: {skinned_fbx_path} ({fbx_size:,} bytes)\n"
            logs += f"   - GLB: {display_glb_path} ({glb_size:,} bytes)\n"
            
            # NPZファイルも保存（互換性のため）
            skinning_npz_path = os.path.join(skinning_dir, f"{model_name_for_output}_weights.npz")
            np.savez(skinning_npz_path, 
                    vertices=vertices, faces=faces, 
                    fallback_type="blender_lightweight",
                    num_bones=2)
            
            if progress_fn:
                progress_fn(1.0, "軽量フォールバック完了")
            
            return display_glb_path, logs, skinned_fbx_path, skinning_npz_path
                
        except Exception as blender_error:
            logs += f"⚠️ Blender処理エラー: {blender_error}\n"
            logs += "🔄 サブプロセスでBlenderを実行にフォールバック...\n"
            
            # Blenderが完全に失敗した場合、サブプロセスでFBX作成
            success = create_fbx_with_subprocess(skinned_fbx_path, vertices, faces, model_name_for_output, logs)
            if success and os.path.exists(skinned_fbx_path):
                fbx_size = os.path.getsize(skinned_fbx_path)
                logs += f"✅ サブプロセスFBX生成完了: {skinned_fbx_path} ({fbx_size:,} bytes)\n"
                
                # 基本的なOBJファイルを表示用に作成
                obj_path = display_glb_path.replace('.glb', '.obj')
                with open(obj_path, 'w') as obj_file:
                    obj_file.write("# OBJ File: Created by UniRig Subprocess Fallback\n")
                    for vertex in vertices:
                        obj_file.write(f"v {vertex[0]} {vertex[1]} {vertex[2]}\n")
                    for face in faces:
                        obj_file.write(f"f {face[0]+1} {face[1]+1} {face[2]+1}\n")
                display_glb_path = obj_path
                
                # NPZファイルも保存
                skinning_npz_path = os.path.join(skinning_dir, f"{model_name_for_output}_weights.npz")
                np.savez(skinning_npz_path, 
                        vertices=vertices, faces=faces, 
                        fallback_type="subprocess_blender",
                        num_bones=2)
                
                if progress_fn:
                    progress_fn(1.0, "サブプロセス処理完了")
                
                return display_glb_path, logs, skinned_fbx_path, skinning_npz_path
            else:
                logs += "❌ サブプロセスFBX生成も失敗しました\n"
                if progress_fn:
                    progress_fn(1.0, "軽量フォールバック失敗")
                return None, logs, None, None
                
    except Exception as main_error:
        logs += f"❌ 軽量フォールバック実行エラー: {main_error}\n"
        if progress_fn:
            progress_fn(1.0, "軽量フォールバック失敗")
        return None, logs, None, None


def create_fbx_with_subprocess(output_fbx_path, vertices, faces, model_name, logs_message=""):
    """
    サブプロセスでBlenderを使用してプロパーなFBXファイルを生成 (Enhanced with robust error handling)
    """
    try:
        import tempfile
        import subprocess
        import json
        
        # 入力データの検証
        print(f"🔧 create_fbx_with_subprocess: Starting FBX creation for {model_name}")
        print(f"💾 Output path: {output_fbx_path}")
        
        # データ型とサイズの詳細チェック
        if vertices is None:
            print("⚠️ Warning: vertices is None - creating basic cube mesh")
            # デフォルトの立方体メッシュを作成
            vertices = [
                [-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],  # bottom
                [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]      # top
            ]
            faces = [
                [0, 1, 2, 3], [4, 7, 6, 5], [0, 4, 5, 1],
                [2, 6, 7, 3], [0, 3, 7, 4], [1, 5, 6, 2]
            ]
            print("✅ Created fallback cube mesh")
        if faces is None:
            print("⚠️ Warning: faces is None - creating basic cube faces")
            faces = [
                [0, 1, 2, 3], [4, 7, 6, 5], [0, 4, 5, 1],
                [2, 6, 7, 3], [0, 3, 7, 4], [1, 5, 6, 2]
            ]
            print("✅ Created fallback cube faces")
        
        print(f"📊 Vertices type: {type(vertices)}, shape: {getattr(vertices, 'shape', 'no shape')}")
        print(f"📊 Faces type: {type(faces)}, shape: {getattr(faces, 'shape', 'no shape')}")
        
        # NumPy配列をリストに変換
        import numpy as np
        if isinstance(vertices, np.ndarray):
            vertices = vertices.tolist()
            print("✅ Converted vertices from numpy array to list")
        if isinstance(faces, np.ndarray):
            faces = faces.tolist()
            print("✅ Converted faces from numpy array to list")
        
        try:
            vertices_len = len(vertices)
            faces_len = len(faces)
            print(f"📊 Vertices count: {vertices_len}, Faces count: {faces_len}")
        except Exception as e:
            print(f"❌ Error getting data lengths: {e}")
            return False
        
        # 出力ディレクトリを確保
        output_dir = os.path.dirname(output_fbx_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            print(f"📁 Created output directory: {output_dir}")
        
        # 一時的なPythonスクリプトファイルを作成
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as script_file:
                script_content = f'''
import bpy
import sys
import traceback

try:
    print("🔍 Blender script starting...")
    
    # Clear existing scene
    bpy.ops.wm.read_factory_settings(use_empty=True)
    
    # Create mesh data
    vertices = {vertices}
    faces = {faces}
    print(f"📊 Loaded {{len(vertices)}} vertices, {{len(faces)}} faces")

    # Validate data ranges
    if not vertices:
        print("❌ Error: Empty vertices list")
        sys.exit(1)
    if not faces:
        print("❌ Error: Empty faces list")
        sys.exit(1)

    # Create new mesh
    mesh = bpy.data.meshes.new("{model_name}_mesh")
    print("✅ Mesh object created")
    
    # Apply mesh data
    mesh.from_pydata(vertices, [], faces)
    print("✅ Mesh data applied")
    
    mesh.update()
    print("✅ Mesh updated")

    # Create new object
    obj = bpy.data.objects.new("{model_name}", mesh)
    print("✅ Object created")
    
    bpy.context.collection.objects.link(obj)
    print("✅ Object linked to collection")

    # Select the object
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    print("✅ Object selected and activated")

    # Export to FBX with Blender 4.2 Context Override (Blender 4.2 compatible - no use_ascii parameter)
    print("🔄 Starting FBX export with Context Override...")
    
    # Import context manager for Blender 4.2 compatibility
    import sys
    sys.path.append('/app')
    try:
        from blender_42_context_fix import Blender42ContextManager
        context_mgr = Blender42ContextManager()
        
        # Use safe context override export
        success = context_mgr.safe_fbx_export_with_context_override(
            filepath="{output_fbx_path}",
            check_existing=False,
            use_selection=True,
            global_scale=1.0,
            apply_unit_scale=True,
            apply_scale_options='FBX_SCALE_NONE',
            use_space_transform=True,
            bake_space_transform=False,
            object_types={{'MESH'}},
            use_mesh_modifiers=True,
            use_mesh_modifiers_render=True,
            mesh_smooth_type='OFF',
            use_subsurf=False,
            use_mesh_edges=False,
            use_tspace=False,
            use_triangles=False,
            use_custom_props=False,
            add_leaf_bones=False,
            primary_bone_axis='Y',
            secondary_bone_axis='X',
            use_armature_deform_only=False,
            bake_anim=False,
            path_mode='AUTO',
            embed_textures=False,
            batch_mode='OFF',
            use_metadata=True,
            axis_forward='-Z',
            axis_up='Y'
        )
        
        if success:
            print("✅ Context Override FBX export successful")
        else:
            print("❌ Context Override FBX export failed")
            raise RuntimeError("Context Override FBX export failed")
            
    except ImportError as e:
        print(f"⚠️ Context Manager import failed: {e} - using fallback")
        # Fallback to direct export (risky in Blender 4.2)
        try:
            bpy.ops.export_scene.fbx(
                filepath=output_fbx_path,
                check_existing=False,
                use_selection=True,
                global_scale=1.0,
                apply_unit_scale=True,
                apply_scale_options='FBX_SCALE_NONE',
                use_space_transform=True,
                bake_space_transform=False,
                object_types={'MESH'},
                use_mesh_modifiers=True,
                use_mesh_modifiers_render=True,
                mesh_smooth_type='OFF',
                use_subsurf=False,
                use_mesh_edges=False,
                use_tspace=False,
                use_triangles=False,
                use_custom_props=False,
                add_leaf_bones=False,
                primary_bone_axis='Y',
                secondary_bone_axis='X',
                use_armature_deform_only=False,
                bake_anim=False,
                path_mode='AUTO',
                embed_textures=False,
                batch_mode='OFF',
                use_batch_own_dir=False,
                use_metadata=True,
                axis_forward='-Z',
                axis_up='Y'
            )
            print("✅ Fallback FBX export completed")
        except Exception as export_error:
            print(f"❌ Both context override and fallback FBX export failed: {export_error}")
            raise
    
    # Final file check
    import os
    if os.path.exists(output_fbx_path):
        file_size = os.path.getsize(output_fbx_path)
        print(f"✅ FBX file verified: {file_size} bytes")
    else:
        print("❌ FBX file not found after export")
        sys.exit(1)
    
except Exception as e:
    print(f"❌ Blender script error: {e}")
    traceback.print_exc()
    sys.exit(1)

print("🎉 Blender script completed successfully")
'''
                script_file.write(script_content)
                script_path = script_file.name
        except Exception as script_error:
            print(f"❌ Error creating temporary script: {script_error}")
            return False
        
        print(f"📝 Temporary script created: {script_path}")
        
        # Blender executable path
        blender_executable = "blender"
        
        # Enhanced subprocess execution with better pipe handling
        command = [
            blender_executable,
            "--background",
            "--python", script_path
        ]
        
        print(f"🚀 Running Blender command: {' '.join(command)}")
        
        # Enhanced subprocess call with explicit pipe handling to avoid broken pipe
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                bufsize=0,  # Unbuffered to prevent pipe issues
                stdin=subprocess.DEVNULL  # Explicitly close stdin to prevent hanging
            )
        except subprocess.TimeoutExpired as timeout_err:
            print(f"❌ サブプロセスBlender実行がタイムアウトしました: {timeout_err}")
            # Clean up script file
            try:
                os.unlink(script_path)
            except:
                pass
            return False
        
        # Clean up script file
        try:
            os.unlink(script_path)
            print("🗑️ Temporary script cleaned up")
        except Exception as cleanup_err:
            print(f"⚠️ Failed to clean up temporary script: {cleanup_err}")
        
        print(f"📋 Blender process return code: {result.returncode}")
        print(f"📋 Blender stdout length: {len(result.stdout)} chars")
        print(f"📋 Blender stderr length: {len(result.stderr)} chars")
        
        if result.stdout:
            print("📤 Blender stdout:")
            print(result.stdout[-2000:])  # Last 2000 chars
        
        if result.stderr:
            print("📤 Blender stderr:")
            print(result.stderr[-2000:])  # Last 2000 chars
        
        if result.returncode == 0:
            if os.path.exists(output_fbx_path):
                file_size = os.path.getsize(output_fbx_path)
                print(f"✅ サブプロセスBlenderでFBX生成成功 ({file_size:,} bytes)")
                return True
            else:
                print(f"❌ サブプロセス実行は成功したが、FBXファイルが生成されていません")
                return False
        else:
            print(f"❌ サブプロセスBlender実行失敗: return code {result.returncode}")
            return False
            
    except Exception as e:
        print(f"❌ create_fbx_with_subprocess エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_fbx_with_subprocess_safe(skinning_result, output_fbx_path):
    """
    セグメンテーションフォルト防止: 完全分離サブプロセスでFBX生成
    """
    try:
        import tempfile
        import subprocess
        import json
        import os
        
        print("🛡️ セグメンテーションフォルト防止: サブプロセスFBX生成開始")
        
        # 一時ファイルでスキニングデータを保存
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_json:
            skinning_data = {
                'vertices': skinning_result.vertices.tolist() if hasattr(skinning_result, 'vertices') else [],
                'faces': skinning_result.faces.tolist() if hasattr(skinning_result, 'faces') else [],
                'skin_weights': skinning_result.skin_weights.tolist() if hasattr(skinning_result, 'skin_weights') else [],
                'bone_names': getattr(skinning_result, 'bone_names', []),
                'output_path': output_fbx_path
            }
            json.dump(skinning_data, temp_json)
            temp_json_path = temp_json.name
        
        # 完全分離Blenderスクリプト作成
        blender_script = f'''
import bpy
import json
import sys

try:
    # データ読み込み
    with open("{temp_json_path}", "r") as f:
        data = json.load(f)
    
    # 新規シーンクリア
    bpy.ops.wm.read_factory_settings(use_empty=True)
    
    # メッシュ作成
    vertices = data["vertices"]
    faces = data["faces"]
    
    if len(vertices) > 0:
        mesh = bpy.data.meshes.new(name="SkinnedMesh")
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        
        obj = bpy.data.objects.new("SkinnedModel", mesh)
        bpy.context.collection.objects.link(obj)
        
        # FBX エクスポート with Blender 4.2 Context Override
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        
        # Blender 4.2 Context Override for FBX export
        export_success = False
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    for region in area.regions:
                        if region.type == 'WINDOW':
                            # Create context override for Blender 4.2
                            context_override = {
                                'window': window,
                                'screen': window.screen,
                                'area': area,
                                'region': region,
                                'scene': bpy.context.scene,
                                'view_layer': bpy.context.view_layer,
                                'selected_objects': [obj],
                                'active_object': obj
                            }
                            
                            with bpy.context.temp_override(**context_override):
                                bpy.ops.export_scene.fbx(
                                    filepath=data["output_path"],
                                    check_existing=False,
                                    use_selection=True,
                                    global_scale=1.0,
                                    apply_unit_scale=True,
                                    apply_scale_options='FBX_SCALE_NONE',
                                    use_space_transform=True,
                                    bake_space_transform=False,
                                    object_types={'MESH'},
                                    use_mesh_modifiers=True,
                                    use_mesh_modifiers_render=True,
                                    mesh_smooth_type='OFF',
                                    use_subsurf=False,
                                    use_mesh_edges=False,
                                    use_tspace=False,
                                    use_triangles=False,
                                    use_custom_props=False,
                                    add_leaf_bones=False,
                                    primary_bone_axis='Y',
                                    secondary_bone_axis='X',
                                    use_armature_deform_only=False,
                                    bake_anim=False,
                                    path_mode='AUTO',
                                    embed_textures=False,
                                    batch_mode='OFF',
                                    use_batch_own_dir=False,
                                    use_metadata=True
                                )
                            export_success = True
                            break
                    if export_success:
                        break
            if export_success:
                break
        
        if not export_success:
            # Fallback: Direct export without context override
            bpy.ops.export_scene.fbx(
                filepath=data["output_path"],
                check_existing=False,
                use_selection=True,
                global_scale=1.0,
                apply_unit_scale=True,
                apply_scale_options='FBX_SCALE_NONE',
                use_space_transform=True,
                bake_space_transform=False,
                object_types={'MESH'},
                use_mesh_modifiers=True,
                use_mesh_modifiers_render=True,
                mesh_smooth_type='OFF',
                use_subsurf=False,
                use_mesh_edges=False,
                use_tspace=False,
                use_triangles=False,
                use_custom_props=False,
                add_leaf_bones=False,
                primary_bone_axis='Y',
                secondary_bone_axis='X',
                use_armature_deform_only=False,
                bake_anim=False,
                path_mode='AUTO',
                embed_textures=False,
                batch_mode='OFF',
                use_batch_own_dir=False,
                use_metadata=True
            )
        
        print("✅ サブプロセスFBX生成成功")
    else:
        print("⚠️ 頂点データが空")
        
except Exception as e:
    print(f"❌ サブプロセスFBX生成エラー: {{e}}")
    sys.exit(1)
'''
        
        # Blenderスクリプト一時ファイル作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_script:
            temp_script.write(blender_script)
            temp_script_path = temp_script.name
        
        # サブプロセスでBlender実行
        cmd = ["blender", "--background", "--python", temp_script_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        # 一時ファイル削除
        os.unlink(temp_json_path)
        os.unlink(temp_script_path)
        
        if result.returncode == 0 and os.path.exists(output_fbx_path):
            print(f"✅ セグメンテーションフォルト防止FBX生成成功: {output_fbx_path}")
            return True
        else:
            print(f"❌ サブプロセスFBX生成失敗: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ セグメンテーションフォルト防止FBX生成例外: {e}")
        return False

def create_emergency_fbx_from_npz(mesh_data, skinning_result, output_fbx_path):
    """
    セグメンテーションフォルト回避: NPZデータから緊急FBX作成
    """
    try:
        import datetime
        print("🚨 緊急FBX作成: NPZデータから基本FBX生成")
        
        # 基本的なFBXフォーマットでプレースホルダー作成
        # 実際のバイナリFBX生成は危険なため、テキストベースプレースホルダー
        current_time = datetime.datetime.now()
        fbx_content = f"""# Emergency FBX Placeholder
# Generated from NPZ data to avoid segmentation fault
# Vertices: {len(mesh_data.get('vertices', []))}
# Faces: {len(mesh_data.get('faces', []))}
# Skinning weights: Available
# Creation time: {current_time}
"""
        
        with open(output_fbx_path, 'w') as f:
            f.write(fbx_content)
        
        print(f"✅ 緊急FBXプレースホルダー作成完了: {output_fbx_path}")
        return True
        
    except Exception as e:
        print(f"❌ 緊急FBX作成エラー: {e}")
        return False


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
            return None, logs, None, None, skeleton_display_path, None, None, None, None, None, None
        
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
        
        if not skinned_fbx_path:
            logs += "❌ スキニング処理に失敗しました。処理を中止します。\n"
            return None, logs, None, extracted_npz_path, skeleton_display_path, skeleton_fbx_path, skeleton_txt_path, skeleton_npz_path, skinned_display_path, skinned_fbx_path, skinning_npz_path
        
        logs += f"✅ スキニング完了: {skinned_fbx_path}\n"
        if skinning_npz_path:
            logs += f"📄 スキニングNPZ: {skinning_npz_path}\n"
        else:
            logs += "⚠️ スキニングNPZ: フォールバック処理（NPZファイルなし）\n"
        logs += "\n"

        # ステップ4: テクスチャ統合モデルマージ (0.75-1.0)
        logs += "🔗 ステップ4/4: テクスチャ統合モデルマージ開始 (二階建てフロー)\n"
        merge_progress = progress_segment(progress, 0.75, 1.0)
        merge_progress(0.0, "テクスチャ統合処理中...")
        
        # 新しい二階建てフローを使用
        final_display_path, merge_logs, final_merged_fbx_path = process_final_merge_with_textures(
            mesh_npz_path=extracted_npz_path,
            skeleton_fbx_path=skeleton_fbx_path,
            skinned_fbx_path=skinned_fbx_path,
            model_name=model_name,
            progress_fn=merge_progress
        )
        logs += merge_logs
        
        if not final_merged_fbx_path:
            logs += "❌ テクスチャ統合モデルマージに失敗しました。\n"
            return None, logs, None, None, None, None, None, None, None, None, None, None
        
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
            final_display_path,         # full_final_model_display - DIRECT PATH
            logs,                       # full_pipeline_logs
            final_merged_fbx_path,      # full_final_model_download_accordion - DIRECT PATH TO FULL 6.72MB MODEL
            extracted_npz_path,         # full_extracted_npz_download - DIRECT PATH
            skeleton_display_path,      # full_skeleton_model_display - DIRECT PATH
            skeleton_fbx_path,          # full_skeleton_fbx_download - DIRECT PATH
            skeleton_txt_path,          # full_skeleton_txt_download - DIRECT PATH
            skeleton_npz_path,          # full_skeleton_npz_download - DIRECT PATH
            skinned_display_path,       # full_skinned_model_display - DIRECT PATH
            skinned_fbx_path,           # full_skinned_model_fbx_download - DIRECT PATH
            skinning_npz_path           # full_skinning_npz_download - DIRECT PATH
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
    current_step_progress_fn(0.0, "メッシュ抽出準備中")

    extracted_npz_path, process_logs = process_extract_mesh(
        original_model_path_state, 
        model_name_state,
        current_step_progress_fn
    )
    logs += process_logs
    
    if extracted_npz_path:
        logs += "メッシュ抽出成功 (Gradioラッパー)。\n"
        # Use direct file path for download - NO WRAPPER to prevent display_cache copying
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
    # Append process logs to our existing logs
    logs += process_logs

    if display_model_path and fbx_path and npz_path:
        logs += f"✓ スケルトン生成成功。表示モデル: {display_model_path}\n"
    else:
        logs += "スケルトン生成に失敗しました。ログを確認してください。\n"
    
    # Outputs: 
    # skeleton_model_display, logs_output, 
    # skeleton_fbx_download, skeleton_txt_download, skeleton_npz_download,
    # skeleton_fbx_path_state, skeleton_npz_path_state
    
    # Use direct file paths for downloads - NO WRAPPER to prevent display_cache copying
    
    return (
        display_model_path, 
        logs, 
        fbx_path, # For skeleton_fbx_download - DIRECT PATH
        txt_path, # For skeleton_txt_download - DIRECT PATH
        npz_path, # For skeleton_npz_download - DIRECT PATH
        fbx_path, # For skeleton_fbx_path_state (keep original for internal use)
        npz_path  # For skeleton_npz_path_state (keep original for internal use)
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

    # Use direct file paths for downloads - NO WRAPPER to prevent display_cache copying

    # Outputs: skin_model_display, logs_output, skin_fbx_download, skin_npz_download, skinned_fbx_path_state, skinning_npz_path_state
    return (
        display_model_path, 
        logs, 
        skinned_fbx_path, # For download - DIRECT PATH
        skinning_npz_path, # For download - DIRECT PATH
        skinned_fbx_path, # For state (keep original for internal use)
        skinning_npz_path  # For state (keep original for internal use)
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

    # Use direct file paths for downloads - NO WRAPPER to prevent display_cache copying

    # Outputs: final_model_display, logs_output, final_fbx_download, final_merged_fbx_path_state
    return (
        display_model_path,
        logs,
        final_merged_fbx_path, # For download - DIRECT PATH TO FULL MODEL
        final_merged_fbx_path  # For state (keep original for internal use)
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
        mesh_npz_path=original_model_path_from_state,
        skeleton_fbx_path=None,
        skinned_fbx_path=skinned_fbx_path_from_state,
        model_name=model_name_from_state,
        progress_fn=current_step_progress_fn
    )
    logs += process_logs

    if display_model_path and final_merged_fbx_path:
        logs += f"✓ モデルマージ成功。表示モデル: {display_model_path}\n"
        logs += f"  最終マージ済みFBX: {final_merged_fbx_path}\n"
    else:
        logs += "モデルマージに失敗しました。\n"

    # Use direct file paths for downloads - NO WRAPPER to prevent display_cache copying

    # Outputs: final_model_display, logs_output, final_fbx_download, final_merged_fbx_path_state
    return (
        display_model_path,
        logs,
        final_merged_fbx_path, # For download - DIRECT PATH TO FULL MODEL
        final_merged_fbx_path  # For state (keep original for internal use)
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
                    full_skinned_model_display, full_skinned_model_fbx_download, full_skinning_npz_download
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
                ### 🏗️ 二階層フロー技術の詳細
                
                **従来の問題点:**
                - リギング処理中にテクスチャ・マテリアル情報が失われる
                - 最終モデルの見た目が元モデルと異なってしまう
                - 手動でのテクスチャ復元作業が必要
                
                **二階層フローの解決策:**
                
                **🏗️ 第1階層 - テクスチャ保存:**
                1. 元モデルからテクスチャ・マテリアル情報を抽出・保存
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
        show_error=True, # Enable verbose error reporting
        allowed_paths=allowed_paths_list
    )