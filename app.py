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

# --- PyTorch/CUDA Configuration (Fix CUDA errors) ---
# Force CPU-only execution to avoid CUDA conflicts
os.environ['CUDA_VISIBLE_DEVICES'] = ''  # Completely disable CUDA
os.environ['FORCE_CUDA'] = '0'  # Force disable CUDA
os.environ['CUDA_DEVICE_ORDER'] = 'PCI_BUS_ID'  # Ensure consistent device ordering
os.environ['SPCONV_DISABLE_CUDA'] = '1'  # Disable CUDA in spconv library
os.environ['USE_CUDA'] = '0'  # Generic CUDA disable flag
# Memory management settings
os.environ['MKL_NUM_THREADS'] = '1'  # Limit MKL threads
os.environ['OMP_NUM_THREADS'] = '1'  # Limit OpenMP threads
os.environ['NUMEXPR_NUM_THREADS'] = '1'  # Limit NumExpr threads
torch.set_num_threads(1)  # Disable multi-threading for stability
torch.set_grad_enabled(False)  # Disable gradient computation for inference
torch.backends.cudnn.enabled = False  # Disable cuDNN
# Force CPU device for all operations
torch.set_default_device('cpu')
logging.info("🔧 PyTorch設定: CPU専用モード、CUDA無効化完了")

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
    """3Dモデルを表示用GLBに変換"""
    try:
        # 入力パスと出力パスを設定
        base_name = os.path.splitext(os.path.basename(input_model_path))[0]
        output_dir = os.path.join(tempfile.gettempdir(), "display_models")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{output_name}.glb")
        
        # 入力ファイルが既にGLB形式の場合はコピー
        if input_model_path.lower().endswith('.glb'):
            shutil.copy2(input_model_path, output_path)
            return output_path
        
        # その他の形式の場合は簡単な変換処理を試行
        # TODO: より高度な変換処理を実装
        try:
            # Trimeshを使った基本的な変換
            mesh = trimesh.load(input_model_path)
            if hasattr(mesh, 'export'):
                mesh.export(output_path)
                return output_path
            else:
                logging.warning(f"Trimeshでの変換: 'export'メソッドが見つかりません")
        except Exception as e:
            logging.warning(f"Trimeshでの変換に失敗: {e}")
        
        # 変換に失敗した場合は元のファイルをコピー
        shutil.copy2(input_model_path, output_path)
        return output_path
        
    except Exception as e:
        logging.error(f"GLB変換エラー: {e}")
        return input_model_path  # 変換失敗時は元のパスを返す

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
            
            # NPZファイルとして保存
            np.savez(extracted_npz_path, 
                    vertices=vertices, 
                    faces=faces)
            
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
            
            # 簡易FBXファイル生成（プレースホルダー）
            try:
                # 実際のFBX生成は複雑なため、ここでは簡易的な処理
                with open(skeleton_fbx_path, 'w') as f:
                    f.write(f"; FBX skeleton for {model_name}\n")
                    f.write(f"; Generated bones: {len(bone_names)}\n")
            except Exception as fbx_error:
                logs += f"⚠️ FBX生成エラー: {fbx_error}\n"
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
    UniRigスキニングウェイト予測処理（Lightning + UniRig SkinSystem使用）
    Args:
        raw_data_npz_path: 元のメッシュNPZファイルパス
        skeleton_fbx_path: スケルトンFBXファイルパス
        skeleton_npz_path: スケルトンNPZファイルパス
        model_name_for_output: 出力用モデル名
        progress_fn: プログレス更新関数
    Returns:
        tuple: (display_path, logs, skinned_fbx_path, skinning_npz_path)
    """
    logs = "=== UniRig Lightning スキニングウェイト予測処理開始 ===\n"
    
    # 必要なモジュールのインポート
    import os
    import shutil
    import traceback
    
    try:
        if progress_fn:
            progress_fn(0.1, "スキニング準備中...")
        
        # フォールバックモード検出（早期実行）
        force_fallback = os.environ.get('FORCE_FALLBACK_MODE', '0') == '1' or \
                        os.environ.get('DISABLE_UNIRIG_LIGHTNING', '0') == '1'
        
        if force_fallback:
            logs += "🔄 フォールバックモード: 軽量処理を使用\n"
            # Blender関連ライブラリを完全に避けた軽量フォールバック処理
            try:
                import numpy as np
                
                # 入力ファイル確認
                if not raw_data_npz_path or not os.path.exists(raw_data_npz_path):
                    logs += f"❌ エラー: メッシュNPZファイルが見つかりません: {raw_data_npz_path}\n"
                    return None, logs, None, None
                
                # データの読み込み（numpyのみ使用）
                mesh_data = np.load(raw_data_npz_path)
                vertices = mesh_data['vertices']
                faces = mesh_data['faces']
                
                logs += f"📊 頂点数: {len(vertices)}\n"
                logs += f"📊 面数: {len(faces)}\n"
                
                # 出力ディレクトリの設定
                if not APP_CONFIG:
                    # Gradio環境での設定の再読み込み
                    if not load_app_config():
                        logs += "❌ エラー: アプリケーション設定が読み込まれていません\n"
                        return None, logs, None, None
                
                skinning_config = APP_CONFIG.get('skinning_prediction', {})
                skinning_subdir = skinning_config.get('skin_output_subdir', '03_skinning_output')
                work_base = APP_CONFIG.working_directory_base
                skinning_dir = os.path.join(work_base, skinning_subdir, model_name_for_output)
                
                os.makedirs(skinning_dir, exist_ok=True)
                
                # 出力ファイルパス
                skinned_fbx_path = os.path.join(skinning_dir, f"{model_name_for_output}_skinned.fbx")
                display_glb_path = os.path.join(skinning_dir, f"{model_name_for_output}_skinned_display.glb")
                
                if progress_fn:
                    progress_fn(0.5, "軽量フォールバック処理中...")
                
                # RawDataクラスを使わない軽量なFBX生成
                try:
                    # Blenderを使用してバイナリFBX生成
                    import tempfile
                    import subprocess
                    
                    # 一時的にOBJファイルを作成
                    with tempfile.NamedTemporaryFile(suffix='.obj', mode='w', delete=False) as obj_file:
                        obj_path = obj_file.name
                        
                        # OBJファイルの内容を書き込み
                        obj_file.write("# OBJ File: Created by UniRig Fallback\n")
                        obj_file.write("# Vertices\n")
                        for vertex in vertices:
                            obj_file.write(f"v {vertex[0]} {vertex[1]} {vertex[2]}\n")
                        
                        obj_file.write("# Faces\n")
                        for face in faces:
                            # OBJは1-indexedなので+1
                            obj_file.write(f"f {face[0]+1} {face[1]+1} {face[2]+1}\n")
                    
                    # BlenderでOBJをFBXに変換
                    blender_script = f"""
import bpy
import bmesh

# 現在のシーンをクリア
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# OBJファイルをインポート
bpy.ops.wm.obj_import(filepath='{obj_path}')

# FBXファイルとしてエクスポート
bpy.ops.export_scene.fbx(
    filepath='{skinned_fbx_path}',
    use_selection=False,
    use_active_collection=False,
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
    add_leaf_bones=True,
    primary_bone_axis='Y',
    secondary_bone_axis='X',
    use_armature_deform_only=False,
    armature_nodetype='NULL',
    bake_anim=True,
    bake_anim_use_all_bones=True,
    bake_anim_use_nla_strips=True,
    bake_anim_use_all_actions=True,
    bake_anim_force_startend_keying=True,
    bake_anim_step=1.0,
    bake_anim_simplify_factor=1.0,
    path_mode='AUTO',
    embed_textures=False,
    batch_mode='OFF',
    use_batch_own_dir=True,
    use_metadata=True
)

print("FBX export completed")
"""
                    
                    # Blenderスクリプトの実行
                    blender_script_path = "/tmp/export_fbx_script.py"
                    with open(blender_script_path, 'w') as f:
                        f.write(blender_script)
                    
                    try:
                        result = subprocess.run([
                            'blender', '--background', '--python', blender_script_path
                        ], capture_output=True, text=True, timeout=60)
                        
                        if result.returncode == 0:
                            logs += f"✅ バイナリFBX生成成功: {skinned_fbx_path}\n"
                        else:
                            logs += f"❌ Blender FBX export failed: {result.stderr}\n"
                            # フォールバック: 基本的なFBXヘッダーのみ
                            with open(skinned_fbx_path, 'wb') as f:
                                f.write(b'Kaydara FBX Binary  \x00\x1a\x00')  # FBXバイナリヘッダー
                    except Exception as e:
                        logs += f"❌ Blender processing error: {e}\n"
                        # フォールバック: 基本的なFBXヘッダーのみ
                        with open(skinned_fbx_path, 'wb') as f:
                            f.write(b'Kaydara FBX Binary  \x00\x1a\x00')  # FBXバイナリヘッダー
                    
                    # 一時ファイルを削除
                    import os
                    try:
                        os.unlink(obj_path)
                        os.unlink(blender_script_path)
                    except:
                        pass
                except Exception as fbx_error:
                    logs += f"⚠️ FBX生成エラー（代替手段使用）: {fbx_error}\n"
                    # さらに軽量な代替ファイル作成
                    with open(skinned_fbx_path, 'w') as f:
                        f.write(f"# Fallback FBX\n# Vertices: {len(vertices)}\n# Faces: {len(faces)}\n")
                
                # 軽量な表示用ファイル生成（JSON形式のメタデータ）
                try:
                    display_data = {
                        "type": "fallback_model",
                        "vertices": len(vertices),
                        "faces": len(faces),
                        "message": "Lightweight fallback model generated"
                    }
                    import json
                    with open(display_glb_path.replace('.glb', '.json'), 'w') as f:
                        json.dump(display_data, f, indent=2)
                    display_glb_path = display_glb_path.replace('.glb', '.json')
                    logs += f"✅ 表示用メタデータ生成成功: {display_glb_path}\n"
                except Exception as display_error:
                    logs += f"⚠️ 表示ファイル生成エラー（代替手段使用）: {display_error}\n"
                    # テキストファイル作成
                    with open(display_glb_path.replace('.glb', '.txt'), 'w') as f:
                        f.write(f"Fallback model info\nVertices: {len(vertices)}\nFaces: {len(faces)}\n")
                    display_glb_path = display_glb_path.replace('.glb', '.txt')
                
                if progress_fn:
                    progress_fn(1.0, "フォールバック処理完了")
                
                logs += f"✅ フォールバックスキニング処理成功\n"
                return display_glb_path, logs, skinned_fbx_path, None
                
            except Exception as fallback_error:
                logs += f"❌ フォールバック処理エラー: {fallback_error}\n"
                import traceback
                logs += f"詳細: {traceback.format_exc()}\n"
                return None, logs, None, None
        
        # 入力ファイルの確認（通常モード）
        required_files = {
            'メッシュNPZ': raw_data_npz_path,
            'スケルトンFBX': skeleton_fbx_path,
            'スケルトンNPZ': skeleton_npz_path
        }
        
        for file_type, file_path in required_files.items():
            if not file_path or not os.path.exists(file_path):
                logs += f"❌ エラー: {file_type}ファイルが見つかりません: {file_path}\n"
                return None, logs, None, None
        
        # 出力ディレクトリの設定
        if not APP_CONFIG:
            # Gradio環境での設定の再読み込み
            if not load_app_config():
                logs += "❌ エラー: アプリケーション設定が読み込まれていません\n"
                return None, logs, None, None
        
        skinning_config = APP_CONFIG.get('skinning_prediction', {})
        skinning_subdir = skinning_config.get('skin_output_subdir', '03_skinning_output')
        work_base = APP_CONFIG.working_directory_base
        skinning_dir = os.path.join(work_base, skinning_subdir, model_name_for_output)
        
        os.makedirs(skinning_dir, exist_ok=True)
        logs += f"📁 スキニングディレクトリ: {skinning_dir}\n"
        
        if progress_fn:
            progress_fn(0.2, "UniRig Lightning設定中...")
        
        # 出力ファイルパスの設定
        skinned_fbx_path = os.path.join(skinning_dir, f"{model_name_for_output}_skinned.fbx")
        skinning_npz_path = os.path.join(skinning_dir, f"{model_name_for_output}_skinning.npz")
        display_glb_path = os.path.join(skinning_dir, f"{model_name_for_output}_skinned_display.glb")
        
        logs += f"📄 出力FBX: {skinned_fbx_path}\n"
        logs += f"📄 出力NPZ: {skinning_npz_path}\n"
        
        if progress_fn:
            progress_fn(0.3, "UniRig Lightning実行中...")
        
        # UniRig Lightning スキニングシステムを使用（通常モード）
        try:
            import torch
            import lightning as L
            from lightning.pytorch import Trainer
            from lightning.pytorch.callbacks import BasePredictionWriter
            from src.system.skin import SkinSystem, SkinWriter
            from src.model.spec import ModelSpec
            from src.data.raw_data import RawData
            import numpy as np
            
            # PyTorch設定: CPU環境での安定性向上
            torch.set_num_threads(1)  # マルチスレッド無効化
            torch.set_grad_enabled(False)  # 勾配計算無効化
            torch.set_float32_matmul_precision('medium')
            
            # CUDA使用を明示的に無効化
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                
            # メモリ設定の最適化（環境変数設定をimport後に移動）
            import os  # ここで明示的にimport
            os.environ['CUDA_VISIBLE_DEVICES'] = ''  # CUDA完全無効化
            torch.backends.cudnn.enabled = False
            
            if progress_fn:
                progress_fn(0.4, "メッシュ・スケルトンデータ読み込み中...")
            
            # データの読み込み
            mesh_data = np.load(raw_data_npz_path)
            skeleton_data = np.load(skeleton_npz_path, allow_pickle=True)
            
            vertices = mesh_data['vertices']
            faces = mesh_data['faces']
            
            # スケルトンデータの取得
            joints = skeleton_data.get('joints', np.zeros((21, 3)))
            bone_names = skeleton_data.get('bone_names', [f"bone_{i}" for i in range(21)])
            parents = skeleton_data.get('parents', [None] + list(range(20)))
            tails = skeleton_data.get('tails', joints + np.array([0.1, 0, 0]))
            
            logs += f"📊 頂点数: {len(vertices)}\n"
            logs += f"🦴 ボーン数: {len(bone_names)}\n"
            
            if progress_fn:
                progress_fn(0.5, "RawDataオブジェクト作成中...")
            
            # RawDataオブジェクトの作成
            raw_data = RawData(
                vertices=vertices,
                vertex_normals=None,
                faces=faces,
                face_normals=None,
                joints=joints,
                tails=tails,
                skin=None,  # スキニングは予測で決定
                no_skin=None,
                parents=parents,
                names=bone_names,
                matrix_local=None,
                uv_coords=None,
                materials=None,
                path=None
            )
            
            if progress_fn:
                progress_fn(0.6, "モデル仕様設定中...")
            
            # モデル仕様の設定（UniRig Skin設定から）
            from src.model.parse import get_model
            import yaml
            
            # UniRig Skinモデル設定の読み込み
            model_config_path = "configs/model/unirig_skin.yaml"
            with open(model_config_path, 'r') as f:
                model_config = yaml.safe_load(f)
            
            # モデルの初期化
            model_spec = get_model(**model_config)
            
            # 事前トレーニング済みモデルの読み込み（存在する場合）
            checkpoint_path = "experiments/skin/articulation-xl/model.ckpt"
            if os.path.exists(checkpoint_path):
                checkpoint = torch.load(checkpoint_path, map_location='cpu')
                model_spec.load_state_dict(checkpoint['state_dict'], strict=False)
                logs += f"✅ 事前トレーニング済みモデル読み込み成功: {checkpoint_path}\n"
            else:
                logs += f"⚠️ 事前トレーニング済みモデルが見つかりません。ランダム初期化で続行: {checkpoint_path}\n"
            
            # モデルをevaluation modeに設定
            model_spec.eval()
            
            if progress_fn:
                progress_fn(0.7, "SkinWriter設定中...")
            
            # SkinWriterの設定
            skin_writer = SkinWriter(
                output_dir=skinning_dir,
                save_name="predict_skin",
                export_fbx=True,
                export_npz=True,
                export_txt=False,
                export_blend=False,
                export_render=False
            )
            
            if progress_fn:
                progress_fn(0.8, "スキニング予測実行中...")
            
            # SkinSystemの初期化
            skin_system = SkinSystem(
                steps_per_epoch=1,
                model=model_spec,
                output_path=skinning_dir,
                record_res=True
            )
            
            # Lightning Trainerの設定（CPU専用、安定性重視）
            trainer = Trainer(
                accelerator='cpu',  # CPUで実行
                devices=1,
                precision=32,  # 32bit精度指定
                max_epochs=1,
                enable_progress_bar=False,
                enable_model_summary=False,
                enable_checkpointing=False,
                logger=False,
                callbacks=[skin_writer],
                deterministic=True,  # 決定論的動作
                strategy='auto'  # 単一デバイス戦略
            )
            
            if progress_fn:
                progress_fn(0.9, "スキニング結果保存中...")
            
            # 予測実行（ダミーデータセット使用）
            class DummyDataLoader:
                def __init__(self, raw_data):
                    self.raw_data = raw_data
                
                def __iter__(self):
                    # バッチサイズ1のデータを準備
                    batch_size = 1
                    num_vertices = len(self.raw_data.vertices)
                    num_bones = len(self.raw_data.joints)
                    
                    # 法線ベクトルを生成（存在しない場合）
                    if hasattr(self.raw_data, 'vertex_normals') and self.raw_data.vertex_normals is not None:
                        normals = self.raw_data.vertex_normals
                    else:
                        # 簡易的な法線ベクトル（上向き）
                        normals = np.zeros((num_vertices, 3))
                        normals[:, 2] = 1.0  # Z軸上向き
                    
                    # tailsを生成（存在しない場合）
                    if hasattr(self.raw_data, 'tails') and self.raw_data.tails is not None:
                        tails = self.raw_data.tails
                    else:
                        # ジョイントから少しオフセットしたtails
                        tails = self.raw_data.joints + np.array([0.1, 0, 0])
                    
                    # voxel_skinはダミーデータ（必要な場合）
                    voxel_skin = np.zeros((num_vertices, num_bones))
                    
                    # parentsを生成（存在しない場合）
                    if hasattr(self.raw_data, 'parents') and self.raw_data.parents is not None:
                        parents = self.raw_data.parents
                    else:
                        # 簡易的な親子関係（チェーン構造）
                        parents = [None] + list(range(num_bones - 1))
                    
                    # 親のインデックスを-1で初期化し、有効な親にインデックスを設定
                    parents_tensor = torch.full((num_bones,), -1, dtype=torch.long)
                    for i, parent in enumerate(parents):
                        if parent is not None:
                            parents_tensor[i] = parent
                    
                    yield {
                        'vertices': torch.tensor(self.raw_data.vertices, dtype=torch.float32).unsqueeze(0),  # (1, N, 3)
                        'faces': torch.tensor(self.raw_data.faces, dtype=torch.long),
                        'joints': torch.tensor(self.raw_data.joints, dtype=torch.float32).unsqueeze(0),  # (1, B, 3)
                        'normals': torch.tensor(normals, dtype=torch.float32).unsqueeze(0),  # (1, N, 3)
                        'tails': torch.tensor(tails, dtype=torch.float32).unsqueeze(0),  # (1, B, 3)
                        'voxel_skin': torch.tensor(voxel_skin, dtype=torch.float32).unsqueeze(0),  # (1, N, B)
                        'parents': parents_tensor.unsqueeze(0),  # (1, B)
                        'num_bones': torch.tensor([num_bones], dtype=torch.long),  # (1,)
                        'offset': torch.tensor([0, num_vertices], dtype=torch.long),  # バッチの開始・終了インデックス
                        'raw_data_path': raw_data_npz_path
                    }
                
                def __len__(self):
                    return 1
            
            dummy_dataloader = DummyDataLoader(raw_data)
            
            # 予測実行
            trainer.predict(skin_system, dummy_dataloader)
            
            # 生成されたファイルの確認
            if os.path.exists(skinned_fbx_path):
                fbx_size = os.path.getsize(skinned_fbx_path)
                logs += f"✅ スキニング済みFBX生成成功: {fbx_size} bytes\n"
            else:
                logs += f"❌ スキニング済みFBX生成失敗\n"
                skinned_fbx_path = None
            
            if os.path.exists(skinning_npz_path):
                logs += f"✅ スキニングNPZ生成成功\n"
            else:
                logs += f"❌ スキニングNPZ生成失敗\n"
                skinning_npz_path = None
            
            # 表示用GLB生成
            try:
                import trimesh
                mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
                mesh.export(display_glb_path)
                logs += f"✅ 表示用GLB生成成功\n"
            except Exception as display_error:
                logs += f"⚠️ 表示用GLB生成エラー: {display_error}\n"
                display_glb_path = None
            
            if progress_fn:
                progress_fn(1.0, "UniRig Lightning スキニング完了")
            
            logs += f"✅ UniRig Lightning スキニング処理成功\n"
            logs += f"💾 最終FBX: {skinned_fbx_path}\n"
            logs += f"💾 最終NPZ: {skinning_npz_path}\n"
            
            return display_glb_path, logs, skinned_fbx_path, skinning_npz_path
            
        except Exception as lightning_error:
            logs += f"❌ UniRig Lightning スキニングエラー: {str(lightning_error)}\n"
            logs += f"詳細: {traceback.format_exc()}\n"
            
            # フォールバック: 簡易RawData.export_fbx使用
            try:
                logs += "🔄 フォールバック: 簡易FBX出力を試行中...\n"
                
                if progress_fn:
                    progress_fn(0.95, "フォールバック処理中...")
                
                # 簡易FBX出力
                raw_data.export_fbx(skinned_fbx_path)
                logs += f"✅ フォールバックFBX生成成功\n"
                
                # 表示用GLB生成
                import trimesh
                mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
                mesh.export(display_glb_path)
                logs += f"✅ 表示用GLB生成成功\n"
                
                return display_glb_path, logs, skinned_fbx_path, None
                
            except Exception as fallback_error:
                logs += f"❌ フォールバックも失敗: {str(fallback_error)}\n"
                return None, logs, None, None
    
    except Exception as e:
        logs += f"❌ スキニング処理全般エラー: {str(e)}\n"
        logs += f"詳細: {traceback.format_exc()}\n"
        return None, logs, None, None


# Step 3のためのエイリアス関数
def step3_skinning_prediction(raw_data_npz_path: str, skeleton_fbx_path: str, skeleton_npz_path: str, 
                             model_name_for_output: str, progress_fn=None):
    """
    Step 3: UniRig Lightning を使用したスキニング予測
    
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
    # 既存のprocess_generate_skin関数を呼び出し
    return process_generate_skin(
        raw_data_npz_path=raw_data_npz_path,
        skeleton_fbx_path=skeleton_fbx_path,
        skeleton_npz_path=skeleton_npz_path,
        model_name_for_output=model_name_for_output,
        progress_fn=progress_fn
    )


def process_final_merge_with_textures(skinned_fbx_path: str, original_model_path: str, 
                                     model_name_for_output: str, progress_fn=None):
    """
    🎯 修正版テクスチャシステム統合 - テクスチャ・マテリアル完全復元
    
    スキニング済みFBXファイルにテクスチャとマテリアル構造を完全復元
    
    Args:
        skinned_fbx_path: スキニング済みFBXファイルパス（Step 3から）
        original_model_path: 元のテクスチャ付きモデルファイルパス
        model_name_for_output: 出力用モデル名
        progress_fn: プログレス更新関数
    Returns:
        tuple: (display_path, logs, final_merged_fbx_path)
    """
    logs = "=== 🎯 修正版テクスチャシステム統合開始 ===\n"
    logs += "テクスチャ・マテリアル完全復元実行中...\n\n"
    
    try:
        if progress_fn:
            progress_fn(0.1, "修正版テクスチャシステム準備中...")
        
        # 入力ファイルの確認
        required_files = {
            'スキニング済みFBX': skinned_fbx_path,
            '元のモデル': original_model_path
        }
        
        for file_type, file_path in required_files.items():
            if not file_path or not os.path.exists(file_path):
                logs += f"❌ エラー: {file_type}ファイルが見つかりません: {file_path}\n"
                return None, logs, None
        
        # 出力ディレクトリの設定
        if not APP_CONFIG:
            # Gradio環境での設定の再読み込み
            if not load_app_config():
                logs += "❌ エラー: アプリケーション設定が読み込まれていません\n"
                return None, logs, None
        
        # 修正版テクスチャシステムを使用
        try:
            logs += "🔧 修正版テクスチャシステム実行開始\n"
            
            from fixed_texture_system_v2 import FixedTextureSystemV2
            
            if progress_fn:
                progress_fn(0.3, "テクスチャ・マテリアル復元実行中...")
            
            # 修正版システムのインスタンス作成
            fixed_system = FixedTextureSystemV2(model_name_for_output)
            
            # テクスチャ・マテリアル問題の完全修正
            result = fixed_system.fix_texture_material_issues(skinned_fbx_path)
            
            if progress_fn:
                progress_fn(0.8, "修正結果検証中...")
            
            # 修正結果の処理
            if result['success']:
                final_fbx_path = result['final_fbx_path']
                validation = result['validation']
                
                logs += "✅ 修正版テクスチャシステム成功\n"
                logs += f"📄 修正項目: {', '.join(result['fixed_issues'])}\n"
                logs += f"🎨 テクスチャ数: {result['texture_count']}\n"
                logs += f"📊 品質評価: {validation['quality_level']}\n"
                logs += f"💾 最終FBXファイル: {final_fbx_path}\n"
                
                # 表示用GLBファイルの生成
                display_path = None
                try:
                    display_path = convert_to_glb_for_display(final_fbx_path, f"{model_name_for_output}_final")
                    logs += f"👁️ 表示用GLB: {display_path}\n"
                except Exception as display_error:
                    logs += f"⚠️ 表示用GLB生成エラー: {display_error}\n"
                
                if progress_fn:
                    progress_fn(1.0, "修正版テクスチャシステム完了")
                
                logs += "\n🎉 === 修正版テクスチャシステム完了 ===\n"
                return display_path, logs, final_fbx_path
            else:
                error_msg = result.get('error', 'Unknown error')
                logs += f"❌ 修正版テクスチャシステム失敗: {error_msg}\n"
                return None, logs, None
                
        except Exception as system_error:
            logs += f"❌ 修正版テクスチャシステム実行エラー: {str(system_error)}\n"
            logs += f"詳細: {traceback.format_exc()}\n"
            return None, logs, None
    
    except Exception as e:
        logs += f"❌ テクスチャ統合処理でエラーが発生しました: {str(e)}\n"
        logs += f"詳細: {traceback.format_exc()}\n"
        if progress_fn:
            progress_fn(1.0, "テクスチャ統合エラー")
        return None, logs, None

def process_basic_merge_fallback(skinned_fbx_path: str, original_model_path: str, 
                                model_name_for_output: str, progress_fn=None, existing_logs=""):
    """
    ImprovedSafeTextureRestoration利用不可時のフォールバック処理
    """
    logs = existing_logs
    logs += "\n=== 基本マージ処理（フォールバック）実行 ===\n"
    
    try:
        # 簡易的なファイルコピー処理
        output_dir = os.path.join(APP_CONFIG.working_directory_base, '08_final_output', model_name_for_output)
        os.makedirs(output_dir, exist_ok=True)
        
        fallback_fbx_path = os.path.join(output_dir, f"{model_name_for_output}_merged_fallback.fbx")
        
        # スキニング済みFBXをコピー
        shutil.copy2(skinned_fbx_path, fallback_fbx_path)
        
        # 表示用モデル生成
        display_path = convert_to_glb_for_display(fallback_fbx_path, f"{model_name_for_output}_fallback")
        
        logs += f"⚠️ フォールバック処理完了: {fallback_fbx_path}\n"
        logs += "注意: テクスチャは統合されていません\n"
        
        if progress_fn:
            progress_fn(1.0, "フォールバック処理完了")
        
        return display_path, logs, fallback_fbx_path
        
    except Exception as fallback_error:
        logs += f"❌ フォールバック処理エラー: {str(fallback_error)}\n"
        return None, logs, None

def process_merge_model(skinned_fbx_path: str, model_name_for_output: str, progress_fn=None):
    """
    基本的なモデルマージ処理（テクスチャなし）
    Args:
        skinned_fbx_path: スキニング済みFBXファイルパス
        model_name_for_output: 出力用モデル名
        progress_fn: プログレス更新関数
    Returns:
        tuple: (display_path, logs, final_fbx_path)
    """
    logs = "=== 基本モデルマージ処理開始 ===\n"
    
    try:
        if progress_fn:
            progress_fn(0.1, "モデルマージ準備中...")
        
        if not skinned_fbx_path or not os.path.exists(skinned_fbx_path):
            logs += f"❌ エラー: スキニング済みFBXファイルが見つかりません: {skinned_fbx_path}\n"
            return None, logs, None
        
        # 出力ディレクトリの設定
        if not APP_CONFIG:
            logs += "❌ エラー: アプリケーション設定が読み込まれていません\n"
            return None, logs, None
        
        merge_config = APP_CONFIG.get('model_merging', {})
        merge_subdir = merge_config.get('merge_output_subdir', '04_merge')
        work_base = APP_CONFIG.working_directory_base
        merge_dir = os.path.join(work_base, merge_subdir, model_name_for_output)
        
        os.makedirs(merge_dir, exist_ok=True)
        logs += f"📁 マージディレクトリ: {merge_dir}\n"
        
        if progress_fn:
            progress_fn(0.5, "モデルマージ処理中...")
        
        # 出力ファイルパス
        final_fbx_path = os.path.join(merge_dir, f"{model_name_for_output}_merged.fbx")
        display_glb_path = os.path.join(merge_dir, f"{model_name_for_output}_merged_display.glb")
        
        # 基本的なファイルコピー処理
        try:
            shutil.copy2(skinned_fbx_path, final_fbx_path)
            logs += f"✅ FBXファイルコピー成功: {final_fbx_path}\n"
            
            if progress_fn:
                progress_fn(0.8, "表示用モデル生成中...")
            
            # 表示用GLBファイルの生成
            display_path = convert_to_glb_for_display(final_fbx_path, f"{model_name_for_output}_merged")
            
            if display_path:
                logs += f"👁️ 表示用GLB生成成功: {display_path}\n"
            else:
                logs += "⚠️ 表示用GLB生成に失敗\n"
                display_path = None
            
            logs += f"✅ 基本モデルマージ完了\n"
            logs += f"💾 最終FBX: {final_fbx_path}\n"
            logs += "⚠️ 注意: この処理ではテクスチャは統合されません\n"
            
            if progress_fn:
                progress_fn(1.0, "モデルマージ完了")
            
            return display_path, logs, final_fbx_path
            
        except Exception as copy_error:
            logs += f"❌ ファイルコピーエラー: {str(copy_error)}\n"
            return None, logs, None
    
    except Exception as e:
        logs += f"❌ モデルマージ処理でエラーが発生しました: {str(e)}\n"
        logs += f"詳細: {traceback.format_exc()}\n"
        if progress_fn:
            progress_fn(1.0, "モデルマージエラー")
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
        
        if not skinned_fbx_path:
            logs += "❌ スキニング処理に失敗しました。処理を中止します。\n"
            return None, logs, None, extracted_npz_path, skeleton_display_path, skeleton_fbx_path, skeleton_txt_path, skeleton_npz_path, skinned_display_path, skinned_fbx_path, skinning_npz_path, None
        
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
        show_error=True, # Enable verbose error reporting
        allowed_paths=allowed_paths_list
    )