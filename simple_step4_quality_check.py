#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
修正されたStep4出力の簡潔な品質検証

実行方法:
    cd /app
    python simple_step4_quality_check.py
"""

import sys
import os
from pathlib import Path
import tempfile
import subprocess

# プロジェクトルートを追加
sys.path.insert(0, '/app')

def quick_blender_analysis(fbx_path, description):
    """Blenderでの簡潔なFBX分析"""
    
    blender_script = f'''
import bpy

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

try:
    bpy.ops.import_scene.fbx(filepath="{fbx_path}")
    
    print("=== {description} ===")
    
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            vg_count = len(obj.vertex_groups)
            vertex_count = len(obj.data.vertices)
            
            weighted_count = 0
            for vertex in obj.data.vertices:
                for group in vertex.groups:
                    if group.weight > 0:
                        weighted_count += 1
                        break
            
            print(f"Mesh: {{obj.name}}")
            print(f"  Vertices: {{vertex_count}}")
            print(f"  Vertex Groups: {{vg_count}}")
            print(f"  Weighted Vertices: {{weighted_count}}")
            
            if vg_count > 0 and weighted_count > 0:
                ratio = weighted_count / vertex_count * 100
                print(f"  Weight Coverage: {{ratio:.1f}}%")
                print("  Status: SUCCESS")
            else:
                print("  Status: FAILED - No weights")
        
        elif obj.type == 'ARMATURE':
            bone_count = len(obj.data.bones)
            print(f"Armature: {{obj.name}} ({{bone_count}} bones)")

except Exception as e:
    print(f"ERROR: {{e}}")
'''
    
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
            tmp.write(blender_script)
            tmp.flush()
            
            cmd = ["blender", "--background", "--python", tmp.name]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.stdout:
                lines = result.stdout.split('\n')
                for line in lines:
                    if any(keyword in line for keyword in ["===", "Mesh:", "Vertices:", "Vertex Groups:", "Weighted Vertices:", "Weight Coverage:", "Status:", "Armature:", "ERROR:"]):
                        print(line.strip())
            
            os.unlink(tmp.name)
            
    except Exception as e:
        print(f"分析エラー: {e}")

def main():
    print("🚀 Step4修正後品質検証 (簡潔版)")
    print("=" * 60)
    
    # ファイルサイズ比較
    fixed_output = "/tmp/test_merge_fixed.fbx"
    original_output = "/app/pipeline_work/bird/04_merge/bird_merged.fbx"
    
    print("📊 ファイルサイズ比較:")
    if Path(fixed_output).exists():
        fixed_size = Path(fixed_output).stat().st_size
        print(f"修正後: {fixed_size:,} bytes")
    else:
        print("修正後: ファイルなし")
        return
    
    if Path(original_output).exists():
        original_size = Path(original_output).stat().st_size
        print(f"修正前: {original_size:,} bytes")
        print(f"差分: {abs(fixed_size - original_size):,} bytes")
    
    print("\n" + "=" * 60)
    
    # 修正後の品質分析
    print("🔍 修正後Step4出力分析:")
    quick_blender_analysis(fixed_output, "修正後 Step4 出力")
    
    print("\n" + "=" * 60)
    
    # Step3入力との比較
    step3_input = "/app/pipeline_work/bird/03_skinning/bird_skinned.fbx"
    print("🔍 Step3入力 (参考):")
    quick_blender_analysis(step3_input, "Step3 入力")
    
    print("\n🎯 検証完了")

if __name__ == "__main__":
    main()
