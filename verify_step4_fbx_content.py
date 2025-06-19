#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Step4出力FBXの実際の内容検証スクリプト

マージされたFBXファイルに実際にウェイトやボーンが正しく含まれているかを
Blenderを使って詳細に検証します。

実行方法:
    cd /app
    python verify_step4_fbx_content.py
"""

import sys
import os
import subprocess
import tempfile
from pathlib import Path

# プロジェクトルートを追加
sys.path.insert(0, '/app')

def verify_step4_fbx_content():
    """Step4出力FBXの実際の内容を検証"""
    print("\n=== Step4出力FBX内容検証 ===")
    
    # 検証対象ファイル
    merged_fbx = Path("/app/pipeline_work/bird/04_merge/bird_merged.fbx")
    skeleton_fbx = Path("/app/pipeline_work/bird/02_skeleton/bird_skeleton.fbx")
    skinned_fbx = Path("/app/pipeline_work/bird/03_skinning/bird_skinned.fbx")
    results_skinned = Path("/app/results/skinned_model.fbx")
    
    if not merged_fbx.exists():
        print("❌ マージFBXが存在しません")
        return
    
    # Blenderスクリプトでウェイト・ボーン検証
    blender_script = f'''
import bpy
import json
import os

def analyze_fbx(filepath, name):
    """FBXファイルを解析してボーン・ウェイト情報を取得"""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    
    try:
        bpy.ops.import_scene.fbx(filepath=filepath)
        
        analysis = {{
            "file": filepath,
            "name": name,
            "objects": [],
            "armatures": [],
            "mesh_objects": [],
            "total_bones": 0,
            "total_vertex_groups": 0,
            "meshes_with_weights": 0
        }}
        
        # 全オブジェクト分析
        for obj in bpy.data.objects:
            obj_info = {{
                "name": obj.name,
                "type": obj.type,
                "vertex_groups": 0,
                "has_armature_modifier": False
            }}
            
            if obj.type == "MESH":
                analysis["mesh_objects"].append(obj.name)
                obj_info["vertex_groups"] = len(obj.vertex_groups)
                analysis["total_vertex_groups"] += obj_info["vertex_groups"]
                
                # Armature Modifierの存在確認
                for modifier in obj.modifiers:
                    if modifier.type == "ARMATURE":
                        obj_info["has_armature_modifier"] = True
                        break
                
                # ウェイトが実際に設定されているか確認
                if len(obj.vertex_groups) > 0:
                    has_weights = False
                    # 最初の数個の頂点をチェック
                    for i in range(min(10, len(obj.data.vertices))):
                        vertex = obj.data.vertices[i]
                        for group_elem in vertex.groups:
                            if group_elem.weight > 0.0:
                                has_weights = True
                                break
                        if has_weights:
                            break
                    if has_weights:
                        analysis["meshes_with_weights"] += 1
            
            elif obj.type == "ARMATURE":
                analysis["armatures"].append(obj.name)
                bone_count = len(obj.data.bones)
                analysis["total_bones"] += bone_count
                obj_info["bone_count"] = bone_count
            
            analysis["objects"].append(obj_info)
        
        return analysis
        
    except Exception as e:
        return {{"error": str(e), "file": filepath, "name": name}}

# 各ファイルを分析
files_to_analyze = [
    ("{str(skeleton_fbx)}", "skeleton"),
    ("{str(skinned_fbx)}", "skinned"),
    ("{str(merged_fbx)}", "merged"),
    ("{str(results_skinned)}", "results_original")
]

results = []
for filepath, name in files_to_analyze:
    if os.path.exists(filepath):
        print(f"Analyzing {{name}}: {{filepath}}")
        analysis = analyze_fbx(filepath, name)
        results.append(analysis)
    else:
        results.append({{"error": "File not found", "file": filepath, "name": name}})

# 結果をJSONで出力
print("=== ANALYSIS RESULTS ===")
import json
print(json.dumps(results, indent=2))
'''
    
    print("=== Blenderによる詳細分析実行 ===")
    
    try:
        # Blenderスクリプトを一時ファイルに保存
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(blender_script)
            script_path = f.name
        
        # Blender実行
        cmd = ["blender", "--background", "--python", script_path]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,  # 3分
            cwd="/app"
        )
        
        print(f"Blender実行結果 (リターンコード: {result.returncode})")
        
        # 出力から分析結果を抽出
        output_lines = result.stdout.split('\n')
        analysis_started = False
        analysis_output = []
        
        for line in output_lines:
            if "=== ANALYSIS RESULTS ===" in line:
                analysis_started = True
                continue
            if analysis_started:
                analysis_output.append(line)
        
        if analysis_output:
            try:
                analysis_json = '\n'.join(analysis_output)
                # JSONの開始を見つける
                json_start = analysis_json.find('[')
                if json_start >= 0:
                    json_data = analysis_json[json_start:]
                    import json
                    results = json.loads(json_data)
                    
                    print("\n=== FBX内容詳細分析結果 ===")
                    
                    for analysis in results:
                        if "error" in analysis:
                            print(f"❌ {analysis['name']}: {analysis['error']}")
                            continue
                        
                        name = analysis['name']
                        print(f"\n📋 {name.upper()}ファイル分析:")
                        print(f"  ファイル: {analysis['file']}")
                        print(f"  オブジェクト数: {len(analysis['objects'])}")
                        print(f"  アーマチュア数: {len(analysis['armatures'])}")
                        print(f"  メッシュオブジェクト数: {len(analysis['mesh_objects'])}")
                        print(f"  総ボーン数: {analysis['total_bones']}")
                        print(f"  総バーテックスグループ数: {analysis['total_vertex_groups']}")
                        print(f"  ウェイト付きメッシュ数: {analysis['meshes_with_weights']}")
                        
                        # 詳細オブジェクト情報
                        for obj in analysis['objects']:
                            if obj['type'] == 'MESH' and obj['vertex_groups'] > 0:
                                modifier_status = "✅" if obj['has_armature_modifier'] else "❌"
                                print(f"    メッシュ '{obj['name']}': {obj['vertex_groups']} VG, Armature修飾子: {modifier_status}")
                            elif obj['type'] == 'ARMATURE':
                                print(f"    アーマチュア '{obj['name']}': {obj.get('bone_count', 0)} ボーン")
                    
                    # 比較分析
                    print(f"\n=== 比較分析 ===")
                    
                    skeleton_data = next((r for r in results if r.get('name') == 'skeleton'), None)
                    skinned_data = next((r for r in results if r.get('name') == 'skinned'), None)
                    merged_data = next((r for r in results if r.get('name') == 'merged'), None)
                    results_data = next((r for r in results if r.get('name') == 'results_original'), None)
                    
                    if merged_data and not merged_data.get('error'):
                        print(f"マージFBX検証:")
                        
                        # ボーン数比較
                        if skeleton_data and not skeleton_data.get('error'):
                            if merged_data['total_bones'] == skeleton_data['total_bones']:
                                print(f"  ✅ ボーン数: {merged_data['total_bones']} (スケルトンと一致)")
                            else:
                                print(f"  ❌ ボーン数不一致: マージ {merged_data['total_bones']} vs スケルトン {skeleton_data['total_bones']}")
                        
                        # ウェイト比較
                        if skinned_data and not skinned_data.get('error'):
                            if merged_data['meshes_with_weights'] == skinned_data['meshes_with_weights']:
                                print(f"  ✅ ウェイト付きメッシュ数: {merged_data['meshes_with_weights']} (スキニングと一致)")
                            else:
                                print(f"  ❌ ウェイト不一致: マージ {merged_data['meshes_with_weights']} vs スキニング {skinned_data['meshes_with_weights']}")
                        
                        # 実際のデータと比較
                        if results_data and not results_data.get('error'):
                            print(f"  🔍 results/ファイルとの比較:")
                            print(f"    ウェイト: マージ {merged_data['meshes_with_weights']} vs results {results_data['meshes_with_weights']}")
                            print(f"    ボーン: マージ {merged_data['total_bones']} vs results {results_data['total_bones']}")
                        
                        # 問題の診断
                        if merged_data['meshes_with_weights'] == 0:
                            print(f"  ❌ 重大な問題: マージFBXにウェイトが全く含まれていません")
                        elif merged_data['total_bones'] == 0:
                            print(f"  ❌ 重大な問題: マージFBXにボーンが全く含まれていません")
                        else:
                            print(f"  ✅ マージFBXにボーンとウェイトが含まれています")
                
            except json.JSONDecodeError as e:
                print(f"❌ JSON解析エラー: {e}")
                print("生の出力:")
                print('\n'.join(analysis_output[:20]))  # 最初の20行
        else:
            print("❌ 分析結果が取得できませんでした")
            print("Blender標準出力:")
            print(result.stdout[-1000:])  # 最後の1000文字
            print("Blender標準エラー:")
            print(result.stderr[-1000:])
        
        # 一時ファイル削除
        os.unlink(script_path)
        
    except subprocess.TimeoutExpired:
        print("❌ Blender分析がタイムアウトしました")
    except Exception as e:
        print(f"❌ Blender分析エラー: {e}")

if __name__ == "__main__":
    verify_step4_fbx_content()
