#!/usr/bin/env python3
"""
SafeTextureRestoration段階別デバッグ分析
各ステージでのテクスチャ接続状況を詳細に確認
"""

import os
import sys
import subprocess
import tempfile
import json
from pathlib import Path

def debug_stage_by_stage():
    """段階別テクスチャ接続分析"""
    print("🔍 SafeTextureRestoration 段階別デバッグ分析")
    print("=" * 60)
    
    # Test data
    test_dir = Path("/app/pipeline_work/safe_test")
    skinned_fbx = "/app/pipeline_work/03_skinning_output/bird/skinned_model.fbx"
    metadata_path = "/app/pipeline_work/01_extracted_mesh/bird/materials_metadata.json"
    texture_dir = "/app/pipeline_work/01_extracted_mesh/bird/textures"
    
    print(f"📁 Skinned FBX: {skinned_fbx}")
    print(f"📋 Metadata: {metadata_path}")
    print(f"🖼️ Texture dir: {texture_dir}")
    print()
    
    # Check input files
    if not os.path.exists(skinned_fbx):
        print("❌ Skinned FBX not found!")
        return
    
    if not os.path.exists(metadata_path):
        print("❌ Metadata not found!")
        return
        
    if not os.path.exists(texture_dir):
        print("❌ Texture directory not found!")
        return
    
    # Load metadata
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    print("📋 メタデータ分析:")
    for mat_name, mat_data in metadata.items():
        print(f"   🎨 Material: {mat_name}")
        if 'textures' in mat_data:
            for tex_type, tex_info in mat_data['textures'].items():
                print(f"      {tex_type}: {tex_info.get('image_name', 'N/A')}")
    print()
    
    # List available texture files
    texture_files = list(Path(texture_dir).glob("*.png"))
    print(f"🖼️ 利用可能テクスチャファイル ({len(texture_files)}):")
    for tex_file in texture_files:
        file_size = tex_file.stat().st_size / (1024 * 1024)
        print(f"   📎 {tex_file.name} ({file_size:.2f} MB)")
    print()
    
    # Stage 1: FBX Import Analysis
    print("🔍 Stage 1 分析: FBXインポート")
    analyze_stage1_import(skinned_fbx)
    print()
    
    # Stage 3: Material Reconstruction Analysis
    print("🔍 Stage 3 分析: マテリアル再構築")
    analyze_stage3_materials(metadata, texture_files)
    print()
    
    # Stage 5: FBX Export Analysis
    print("🔍 Stage 5 分析: FBXエクスポート設定")
    analyze_stage5_export_settings()
    print()

def analyze_stage1_import(skinned_fbx_path: str):
    """Stage 1: FBXインポート分析"""
    script_content = f'''
import bpy
import os

def analyze_import():
    try:
        # Clean workspace
        bpy.ops.wm.read_factory_settings(use_empty=True)
        
        # Import FBX
        bpy.ops.import_scene.fbx(
            filepath="{skinned_fbx_path}",
            use_image_search=False,
            use_anim=True,
            ignore_leaf_bones=False
        )
        
        print("📊 インポート後の状況:")
        print(f"   Objects: {{len(bpy.data.objects)}}")
        print(f"   Materials: {{len(bpy.data.materials)}}")
        print(f"   Images: {{len(bpy.data.images)}}")
        print(f"   Armatures: {{len(bpy.data.armatures)}}")
        
        # Analyze materials
        for mat in bpy.data.materials:
            print(f"   🎨 Material: {{mat.name}}")
            if mat.use_nodes:
                for node in mat.node_tree.nodes:
                    if node.type == 'TEX_IMAGE':
                        print(f"      🖼️ Image Node: {{node.name}}")
                        if node.image:
                            print(f"         Image: {{node.image.name}}")
                        else:
                            print("         ❌ No image assigned")
        
        return True
    except Exception as e:
        print(f"❌ Error: {{e}}")
        return False

result = analyze_import()
if result:
    print("Stage1AnalysisComplete")
else:
    print("Stage1AnalysisFailed")
'''
    
    try:
        result = subprocess.run([
            "blender", "--background", "--python-expr", script_content
        ], capture_output=True, text=True, timeout=120)
        
        print(result.stdout)
        if result.stderr:
            print("⚠️ Warnings:", result.stderr)
    except Exception as e:
        print(f"❌ Stage 1 analysis error: {e}")

def analyze_stage3_materials(metadata: dict, texture_files: list):
    """Stage 3: マテリアル再構築分析"""
    print("📋 マテリアル再構築シミュレーション:")
    
    for mat_name, mat_data in metadata.items():
        print(f"   🎨 Material: {mat_name}")
        
        if 'textures' in mat_data:
            for tex_type, tex_info in mat_data['textures'].items():
                image_name = tex_info.get('image_name', '')
                
                # Check if texture file exists
                matching_files = [f for f in texture_files if f.name == image_name]
                
                if matching_files:
                    tex_file = matching_files[0]
                    file_size = tex_file.stat().st_size / (1024 * 1024)
                    print(f"      ✅ {tex_type}: {image_name} ({file_size:.2f} MB)")
                else:
                    print(f"      ❌ {tex_type}: {image_name} (NOT FOUND)")

def analyze_stage5_export_settings():
    """Stage 5: FBXエクスポート設定分析"""
    print("📤 現在のFBXエクスポート設定:")
    print("   ✅ path_mode='COPY' - テクスチャファイルをコピー")
    print("   ✅ embed_textures=True - FBXに埋め込み")
    print("   ✅ use_mesh_modifiers=True - メッシュ修正子適用")
    print("   ✅ use_custom_props=True - カスタムプロパティ保持")
    print("   ✅ add_leaf_bones=True - リーフボーン追加")
    print("   ✅ use_armature_deform_only=True - デフォームボーンのみ")
    print("   ✅ use_tspace=True - タンジェント空間")
    
    print("\n🔧 推奨される追加設定:")
    print("   🔧 bake_anim=False - アニメーションをベイクしない")
    print("   🔧 mesh_smooth_type='FACE' - 面スムージング")
    print("   🔧 use_mesh_edges=True - メッシュエッジ使用")
    print("   🔧 use_triangles=False - クアッドを可能な限り保持")

if __name__ == "__main__":
    debug_stage_by_stage()
