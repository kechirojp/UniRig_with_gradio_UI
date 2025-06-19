#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
修正されたStep4出力の品質検証

修正後のsrc.inference.mergeによって生成されたFBXファイルの
バーテックスグループとウェイトデータを詳細検証します。

実行方法:
    cd /app
    python verify_step4_fix_quality.py
"""

import sys
import os
from pathlib import Path
import tempfile
import subprocess

# プロジェクトルートを追加
sys.path.insert(0, '/app')

def analyze_fixed_merge_output():
    """修正されたマージ出力を詳細分析"""
    print("🔍 修正されたStep4出力の品質検証")
    print("=" * 60)
    
    # 修正後の出力ファイル
    fixed_output = "/tmp/test_merge_fixed.fbx"
    
    if not Path(fixed_output).exists():
        print("❌ 修正後の出力ファイルが見つかりません")
        return False
    
    # ファイルサイズ確認
    size = Path(fixed_output).stat().st_size
    print(f"修正後ファイルサイズ: {size:,} bytes ({size / (1024*1024):.2f} MB)")
    
    # 元のStep4出力と比較
    original_output = "/app/pipeline_work/bird/04_merge/bird_merged.fbx"
    if Path(original_output).exists():
        original_size = Path(original_output).stat().st_size
        print(f"元のStep4出力サイズ: {original_size:,} bytes")
        size_diff = abs(size - original_size)
        print(f"サイズ差: {size_diff:,} bytes")
        
        if size == original_size:
            print("✅ 同一サイズ - 一貫性確認")
        else:
            print("❌ サイズ異なる - 処理内容が変更された")
    
    # Blenderでの詳細品質分析
    blender_script = f'''
import bpy
import sys

# 既存オブジェクトクリア
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

try:
    # 修正後FBXインポート
    bpy.ops.import_scene.fbx(filepath="{fixed_output}")
    
    print("=== 修正後Step4出力品質分析 ===")
    
    # オブジェクト分析
    total_vertex_groups = 0
    total_weighted_vertices = 0
    total_vertices = 0
    
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            print(f"メッシュオブジェクト: {{obj.name}}")
            print(f"  頂点数: {{len(obj.data.vertices)}}")
            print(f"  面数: {{len(obj.data.polygons)}}")
            
            # バーテックスグループ分析
            vg_count = len(obj.vertex_groups)
            total_vertex_groups += vg_count
            print(f"  バーテックスグループ数: {{vg_count}}")
            
            if vg_count > 0:
                # 詳細ウェイト分析
                weighted_vertices = 0
                zero_weighted = 0
                total_weight_sum = 0
                non_zero_weights = []
                
                for vertex in obj.data.vertices:
                    vertex_weight_sum = 0
                    vertex_has_weight = False
                    
                    for group in vertex.groups:
                        if group.weight > 0:
                            vertex_weight_sum += group.weight
                            vertex_has_weight = True
                            non_zero_weights.append(group.weight)
                    
                    if vertex_has_weight:
                        weighted_vertices += 1
                        total_weight_sum += vertex_weight_sum
                    else:
                        zero_weighted += 1
                
                total_weighted_vertices += weighted_vertices
                total_vertices += len(obj.data.vertices)
                
                print(f"  ウェイト付き頂点: {{weighted_vertices}}")
                print(f"  ウェイトなし頂点: {{zero_weighted}}")
                
                if weighted_vertices > 0:
                    weight_ratio = weighted_vertices / len(obj.data.vertices) * 100
                    avg_weight_sum = total_weight_sum / weighted_vertices
                    print(f"  ウェイト付与率: {{weight_ratio:.1f}}%")
                    print(f"  平均ウェイト合計: {{avg_weight_sum:.3f}}")
                    
                    if non_zero_weights:
                        min_weight = min(non_zero_weights)
                        max_weight = max(non_zero_weights)
                        avg_weight = sum(non_zero_weights) / len(non_zero_weights)
                        print(f"  ウェイト範囲: {{min_weight:.6f}} - {{max_weight:.6f}}")
                        print(f"  平均個別ウェイト: {{avg_weight:.6f}}")
                
                # バーテックスグループ名の表示
                print(f"  バーテックスグループ名:")
                for i, vg in enumerate(obj.vertex_groups):
                    if i < 10:  # 最初の10個のみ表示
                        print(f"    {{i+1}}. {{vg.name}}")
                    elif i == 10:
                        print(f"    ... ({{vg_count}}個のグループ)")
                        break
            else:
                print("  ⚠️ バーテックスグループなし")
        
        elif obj.type == 'ARMATURE':
            print(f"アーマチュア: {{obj.name}}")
            print(f"  ボーン数: {{len(obj.data.bones)}}")
            
            # ボーン階層
            root_bones = [b for b in obj.data.bones if b.parent is None]
            print(f"  ルートボーン数: {{len(root_bones)}}")
    
    # 全体統計
    print("\n=== 全体統計 ===")
    print(f"総バーテックスグループ数: {{total_vertex_groups}}")
    print(f"総頂点数: {{total_vertices}}")
    print(f"ウェイト付き頂点数: {{total_weighted_vertices}}")
    
    if total_vertices > 0:
        overall_weight_ratio = total_weighted_vertices / total_vertices * 100
        print(f"全体ウェイト付与率: {{overall_weight_ratio:.1f}}%")
    
    # 修正成功判定
    if total_vertex_groups > 0 and total_weighted_vertices > 0:
        print("\n✅ 修正成功: バーテックスグループとウェイトが正常に生成されています")
    else:
        print("\n❌ 修正失敗: バーテックスグループまたはウェイトが不足")

except Exception as e:
    print(f"❌ Blender分析エラー: {{e}}")
    import traceback
    traceback.print_exc()
'''
    
    # Blenderでスクリプト実行
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
            tmp.write(blender_script)
            tmp.flush()
            
            print("\nBlender品質分析実行中...")
            cmd = ["blender", "--background", "--python", tmp.name]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.stdout:
                # Blender出力から重要部分を抽出
                lines = result.stdout.split('\n')
                in_analysis = False
                for line in lines:
                    if "=== 修正後Step4出力品質分析 ===" in line:
                        in_analysis = True
                    elif in_analysis and line.strip():
                        print(line)
            
            if result.stderr and "Error" in result.stderr:
                print(f"Blenderエラー: {result.stderr}")
            
            # 一時ファイル削除
            os.unlink(tmp.name)
            
            return True
            
    except Exception as e:
        print(f"❌ Blender分析実行エラー: {e}")
        return False

def compare_with_step3_input():
    """Step3の入力との比較検証"""
    print("\n🔍 Step3入力との比較検証")
    print("=" * 60)
    
    step3_input = "/app/pipeline_work/bird/03_skinning/bird_skinned.fbx"
    
    if not Path(step3_input).exists():
        print("❌ Step3入力ファイルが見つかりません")
        return
    
    # Step3入力の詳細分析
    blender_script = f'''
import bpy

# 既存オブジェクトクリア
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

try:
    # Step3入力FBXインポート
    bpy.ops.import_scene.fbx(filepath="{step3_input}")
    
    print("=== Step3入力 (bird_skinned.fbx) 分析 ===")
    
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            print(f"メッシュオブジェクト: {{obj.name}}")
            print(f"  頂点数: {{len(obj.data.vertices)}}")
            print(f"  バーテックスグループ数: {{len(obj.vertex_groups)}}")
            
            if len(obj.vertex_groups) > 0:
                # ウェイト付き頂点をカウント
                weighted_vertices = 0
                for vertex in obj.data.vertices:
                    for group in vertex.groups:
                        if group.weight > 0:
                            weighted_vertices += 1
                            break
                
                weight_ratio = weighted_vertices / len(obj.data.vertices) * 100
                print(f"  ウェイト付き頂点: {{weighted_vertices}} ({{weight_ratio:.1f}}%)")

except Exception as e:
    print(f"❌ Step3分析エラー: {{e}}")
'''
    
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
            tmp.write(blender_script)
            tmp.flush()
            
            cmd = ["blender", "--background", "--python", tmp.name]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.stdout:
                lines = result.stdout.split('\n')
                in_analysis = False
                for line in lines:
                    if "=== Step3入力" in line:
                        in_analysis = True
                    elif in_analysis and line.strip():
                        print(line)
            
            os.unlink(tmp.name)
            
    except Exception as e:
        print(f"❌ Step3比較分析エラー: {e}")

if __name__ == "__main__":
    try:
        print("🚀 修正されたStep4出力の品質検証開始")
        print("=" * 80)
        
        # 1. 修正後出力の詳細分析
        analysis_success = analyze_fixed_merge_output()
        
        # 2. Step3入力との比較
        compare_with_step3_input()
        
        print("\n🎯 検証完了")
        
        if analysis_success:
            print("✅ 修正後のStep4出力が正常に検証されました")
        else:
            print("❌ 検証中にエラーが発生しました")
        
    except Exception as e:
        print(f"❌ 検証実行エラー: {e}")
        import traceback
        traceback.print_exc()
