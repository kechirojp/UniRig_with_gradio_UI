#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
スキニングFBXのウェイト合計分析

ゼロ除算エラーの根本原因を特定するため、
各頂点のウェイト合計を詳細に分析します。

実行方法:
    cd /app
    python analyze_weight_sums.py
"""

import sys
import os
import tempfile
import subprocess
from pathlib import Path

# プロジェクトルートを追加
sys.path.insert(0, '/app')

def analyze_weight_sums(fbx_path: Path):
    """各頂点のウェイト合計を分析してゼロ除算原因を特定"""
    
    blender_script = f'''
import bpy
import bmesh
import json

# 既存オブジェクトをすべて削除
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

try:
    # FBXファイルをインポート
    bpy.ops.import_scene.fbx(filepath="{fbx_path}")
    
    weight_analysis = {{
        "total_vertices": 0,
        "zero_weight_sum_vertices": [],
        "very_low_weight_vertices": [],
        "weight_sum_statistics": {{}}
    }}
    
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            mesh = obj.data
            weight_analysis["total_vertices"] = len(mesh.vertices)
            
            weight_sums = []
            zero_sum_vertices = []
            very_low_vertices = []
            
            # 各頂点のウェイト合計を計算
            for v_idx, vertex in enumerate(mesh.vertices):
                total_weight = 0.0
                vertex_weights = []
                
                # この頂点の全バーテックスグループのウェイトを合計
                for group in vertex.groups:
                    try:
                        weight = obj.vertex_groups[group.group].weight(v_idx)
                        vertex_weights.append(weight)
                        total_weight += weight
                    except:
                        pass
                
                weight_sums.append(total_weight)
                
                # ゼロ合計頂点を記録
                if total_weight == 0.0:
                    zero_sum_vertices.append({{
                        "vertex_index": v_idx,
                        "group_count": len(vertex.groups)
                    }})
                
                # 非常に小さいウェイト合計を記録
                elif total_weight < 0.001:
                    very_low_vertices.append({{
                        "vertex_index": v_idx,
                        "weight_sum": total_weight,
                        "group_count": len(vertex.groups)
                    }})
            
            # 統計計算
            if weight_sums:
                weight_analysis["weight_sum_statistics"] = {{
                    "min": min(weight_sums),
                    "max": max(weight_sums),
                    "average": sum(weight_sums) / len(weight_sums),
                    "zero_count": weight_sums.count(0.0),
                    "below_0001": len([w for w in weight_sums if w < 0.001 and w > 0]),
                    "below_001": len([w for w in weight_sums if w < 0.01 and w >= 0.001]),
                    "normal_range": len([w for w in weight_sums if w >= 0.01])
                }}
            
            weight_analysis["zero_weight_sum_vertices"] = zero_sum_vertices[:10]  # 最初の10個
            weight_analysis["very_low_weight_vertices"] = very_low_vertices[:10]  # 最初の10個
            
            break  # 最初のメッシュのみ分析
    
    print("=== WEIGHT_ANALYSIS_START ===")
    print(json.dumps(weight_analysis, indent=2))
    print("=== WEIGHT_ANALYSIS_END ===")
    
except Exception as e:
    print(f"エラー: {{e}}")
    import traceback
    traceback.print_exc()
'''
    
    # 一時ファイルでBlenderスクリプトを作成
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(blender_script)
        script_path = f.name
    
    try:
        cmd = ["blender", "--background", "--python", script_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            # 結果を解析
            output_lines = result.stdout.split('\n')
            capturing = False
            json_lines = []
            
            for line in output_lines:
                if line.strip() == "=== WEIGHT_ANALYSIS_START ===":
                    capturing = True
                    continue
                elif line.strip() == "=== WEIGHT_ANALYSIS_END ===":
                    capturing = False
                    break
                elif capturing:
                    json_lines.append(line)
            
            if json_lines:
                try:
                    import json
                    analysis = json.loads('\n'.join(json_lines))
                    return analysis
                except json.JSONDecodeError as e:
                    print(f"❌ JSON解析エラー: {e}")
        else:
            print(f"❌ Blender実行エラー: {result.stderr}")
            
    except Exception as e:
        print(f"❌ 実行エラー: {e}")
    finally:
        try:
            os.unlink(script_path)
        except:
            pass
    
    return None

def main():
    print("🔍 スキニングFBXのウェイト合計分析開始")
    
    fbx_path = Path("/app/pipeline_work/bird/03_skinning/bird_skinned.fbx")
    
    if not fbx_path.exists():
        print(f"❌ ファイルが存在しません: {fbx_path}")
        return
    
    print(f"📊 分析対象: {fbx_path}")
    print(f"ファイルサイズ: {fbx_path.stat().st_size:,} bytes")
    
    analysis = analyze_weight_sums(fbx_path)
    
    if analysis:
        stats = analysis["weight_sum_statistics"]
        
        print(f"\n🎯 ウェイト合計統計:")
        print(f"  総頂点数: {analysis['total_vertices']:,}")
        print(f"  最小ウェイト合計: {stats['min']:.6f}")
        print(f"  最大ウェイト合計: {stats['max']:.6f}")
        print(f"  平均ウェイト合計: {stats['average']:.6f}")
        
        print(f"\n🚨 問題の可能性:")
        print(f"  ゼロ合計頂点: {stats['zero_count']:,}個")
        print(f"  超低値（<0.001）: {stats['below_0001']:,}個")
        print(f"  低値（0.001-0.01）: {stats['below_001']:,}個")
        print(f"  正常範囲（≥0.01）: {stats['normal_range']:,}個")
        
        if stats['zero_count'] > 0:
            print(f"\n❌ ゼロ除算エラーの原因発見！")
            print(f"   {stats['zero_count']}個の頂点でウェイト合計が0.0")
            print(f"   これらの頂点でvertex_group_reweight[..., :group_per_vertex].sum(axis=1)が0になる")
            
            print(f"\n📋 ゼロ合計頂点の例:")
            for vertex in analysis["zero_weight_sum_vertices"]:
                print(f"     頂点{vertex['vertex_index']}: グループ数{vertex['group_count']}")
        
        if stats['below_0001'] > 0:
            print(f"\n⚠️ 超低値ウェイト頂点:")
            for vertex in analysis["very_low_weight_vertices"]:
                print(f"     頂点{vertex['vertex_index']}: 合計{vertex['weight_sum']:.6f}")
        
        if stats['zero_count'] == 0 and stats['below_0001'] == 0:
            print(f"\n✅ ウェイト合計は正常範囲内")
            print(f"   ゼロ除算エラーの原因は別の箇所にある可能性")
    
    else:
        print("❌ 分析に失敗しました")

if __name__ == "__main__":
    main()
