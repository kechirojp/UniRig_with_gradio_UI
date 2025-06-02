#!/usr/bin/env python3
"""
Blenderスクリプト生成テスト
"""
import sys
import os
sys.path.append('/app')

from proposed_blender_texture_flow import BlenderNativeTextureFlow
from pathlib import Path
import tempfile

def test_script_generation():
    """スクリプト生成の動作をテスト"""
    print("🔧 Blenderスクリプト生成テスト")
    print("=" * 50)
    
    # テスト用パラメータ
    model_path = "/app/examples/bird.glb"
    work_dir = Path("/app/pipeline_work/test_script_gen")
    work_dir.mkdir(parents=True, exist_ok=True)
    
    # BlenderNativeTextureFlowインスタンスを作成
    flow = BlenderNativeTextureFlow(
        work_dir=str(work_dir)
    )
    
    # スクリプトテンプレートを取得（_step1_subprocessから抽出）
    script_template = '''
import bpy
import bmesh
import json
import os
from pathlib import Path

def analyze_and_save_original(model_path: str, original_blend: str, material_metadata: str):
    try:
        print("DEBUG: Starting analysis for " + model_path)
        
        # メタデータファイルのディレクトリを作成
        os.makedirs(os.path.dirname(material_metadata), exist_ok=True)
        
        # Blenderクリーンアップ
        bpy.ops.wm.read_factory_settings(use_empty=True)
        print("DEBUG: Blender cleaned up")
        
        # 元モデルをロード
        ext = Path(model_path).suffix.lower()
        print("DEBUG: Loading model with extension " + ext)
        
        if ext in ['.glb', '.gltf']:
            bpy.ops.import_scene.gltf(filepath=model_path, import_pack_images=True)
        elif ext in ['.fbx']:
            bpy.ops.import_scene.fbx(filepath=model_path, use_image_search=True)
        elif ext in ['.obj']:
            bpy.ops.wm.obj_import(filepath=model_path)
        else:
            print("ERROR: Unsupported file format: " + ext)
            return None
            
        print("DEBUG: Model loaded. Objects: " + str(len(bpy.data.objects)) + ", Materials: " + str(len(bpy.data.materials)))
        
        # Blendファイルとして保存
        print("DEBUG: Saving blend file to " + original_blend)
        bpy.ops.wm.save_as_mainfile(filepath=original_blend)
        
        print("DEBUG: Analysis complete")
        return True
        
    except Exception as e:
        print("ERROR in analyze_and_save_original: " + str(e))
        import traceback
        traceback.print_exc()
        return None

# 実行
result = analyze_and_save_original(MODEL_PATH_PLACEHOLDER, ORIGINAL_BLEND_PLACEHOLDER, METADATA_PLACEHOLDER)
if result is not None:
    print("AnalysisComplete")
else:
    print("AnalysisFailed")
'''
    
    # プレースホルダーを置換
    script_content = script_template.replace('MODEL_PATH_PLACEHOLDER', '"' + str(model_path) + '"')
    script_content = script_content.replace('ORIGINAL_BLEND_PLACEHOLDER', '"' + str(flow.original_blend) + '"')
    script_content = script_content.replace('METADATA_PLACEHOLDER', '"' + str(flow.material_metadata) + '"')
    
    print("📝 生成されたスクリプト内容:")
    print("-" * 50)
    print(script_content)
    print("-" * 50)
    
    # 一時ファイルに保存
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(script_content)
        script_path = f.name
    
    print(f"📁 スクリプトファイル: {script_path}")
    
    # スクリプト実行テスト
    import subprocess
    try:
        cmd = ['blender', '--background', '--python', script_path]
        print(f"🔄 実行コマンド: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        print(f"📊 結果:")
        print(f"  戻り値: {result.returncode}")
        print(f"  stdout: {result.stdout}")
        if result.stderr:
            print(f"  stderr: {result.stderr}")
        
        success = result.returncode == 0 and "AnalysisComplete" in result.stdout
        print(f"✅ テスト結果: {'成功' if success else '失敗'}")
        
    except subprocess.TimeoutExpired:
        print("❌ タイムアウト")
    except Exception as e:
        print(f"❌ エラー: {e}")
    finally:
        try:
            os.unlink(script_path)
        except:
            pass

if __name__ == "__main__":
    test_script_generation()
