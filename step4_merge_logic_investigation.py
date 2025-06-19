#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Step4マージ処理ロジック詳細調査

Step4のsrc.inference.mergeの実際の処理内容と
出力結果を詳細に調査します。

実行方法:
    cd /app
    python step4_merge_logic_investigation.py
"""

import sys
import os
from pathlib import Path
import subprocess
import tempfile

# プロジェクトルートを追加
sys.path.insert(0, '/app')

def run_merge_with_debug():
    """src.inference.mergeを直接実行してデバッグ情報を取得"""
    print("🔍 src.inference.merge 直接実行テスト")
    print("=" * 60)
    
    # 入力ファイル
    source_fbx = "/app/pipeline_work/bird/02_skeleton/bird_skeleton.fbx"
    target_fbx = "/app/pipeline_work/bird/03_skinning/bird_skinned.fbx"
    
    # テスト用出力ファイル
    test_output = "/tmp/test_merge_output.fbx"
    
    # マージコマンド実行
    cmd = [
        sys.executable, "-m", "src.inference.merge",
        "--require_suffix", "obj,fbx,FBX,dae,glb,gltf,vrm",
        "--num_runs", "1",
        "--id", "0",
        "--source", source_fbx,
        "--target", target_fbx,
        "--output", test_output
    ]
    
    print(f"実行コマンド: {' '.join(cmd)}")
    print("\n実行開始...")
    
    try:
        # 詳細な出力を取得
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd="/app"
        )
        
        print(f"終了コード: {result.returncode}")
        
        if result.stdout:
            print("\n--- STDOUT ---")
            print(result.stdout)
        
        if result.stderr:
            print("\n--- STDERR ---")
            print(result.stderr)
        
        # 出力ファイル確認
        if Path(test_output).exists():
            size = Path(test_output).stat().st_size
            print(f"\n✅ 出力ファイル生成成功: {test_output}")
            print(f"サイズ: {size:,} bytes ({size / (1024*1024):.2f} MB)")
            
            # 元のStep4出力と比較
            original_output = "/app/pipeline_work/bird/04_merge/bird_merged.fbx"
            if Path(original_output).exists():
                original_size = Path(original_output).stat().st_size
                print(f"元のStep4出力サイズ: {original_size:,} bytes")
                print(f"サイズ差: {abs(size - original_size):,} bytes")
                
                if size == original_size:
                    print("✅ 同一サイズ - 処理は一貫している")
                else:
                    print("❌ サイズ異なる - 処理に差がある")
        else:
            print("❌ 出力ファイル生成失敗")
        
        return result.returncode == 0, result.stdout, result.stderr
        
    except subprocess.TimeoutExpired:
        print("❌ タイムアウト (300秒)")
        return False, "", "Timeout"
    except Exception as e:
        print(f"❌ 実行エラー: {e}")
        return False, "", str(e)

def analyze_merge_source_code():
    """src.inference.mergeのソースコードを分析"""
    print("\n🔍 src.inference.merge ソースコード分析")
    print("=" * 60)
    
    merge_file = "/app/src/inference/merge.py"
    
    if not Path(merge_file).exists():
        print("❌ src/inference/merge.py が見つかりません")
        return
    
    print(f"✅ ファイル発見: {merge_file}")
    
    # 重要な部分を抽出
    try:
        with open(merge_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # ファイルサイズ
        print(f"ファイルサイズ: {len(content):,} 文字")
        
        # キーワード検索
        keywords = [
            "vertex_group_reweight",
            "np.nan_to_num",
            "divide",
            "weight",
            "skinning",
            "RuntimeWarning"
        ]
        
        print("\n重要キーワード検索:")
        for keyword in keywords:
            count = content.count(keyword)
            if count > 0:
                print(f"  '{keyword}': {count}箇所")
                
                # 該当行を表示
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if keyword in line:
                        print(f"    Line {i}: {line.strip()}")
                        break
        
        # エラー処理箇所を検索
        error_patterns = [
            "except",
            "try:",
            "warning",
            "error",
            "fail"
        ]
        
        print("\nエラー処理パターン:")
        for pattern in error_patterns:
            if pattern in content.lower():
                print(f"  '{pattern}': 含まれています")
        
    except Exception as e:
        print(f"❌ ファイル読み込みエラー: {e}")

def check_merge_output_quality():
    """マージ出力の品質を詳細チェック"""
    print("\n🔍 マージ出力品質チェック")
    print("=" * 60)
    
    output_file = "/app/pipeline_work/bird/04_merge/bird_merged.fbx"
    
    if not Path(output_file).exists():
        print("❌ マージ出力ファイルが存在しません")
        return
    
    # Blenderでの詳細分析
    blender_script = f'''
import bpy
import sys

# 既存オブジェクトクリア
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

try:
    # FBXインポート
    bpy.ops.import_scene.fbx(filepath="{output_file}")
    
    print("=== マージ出力FBX分析 ===")
    
    # オブジェクト分析
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            print(f"メッシュオブジェクト: {{obj.name}}")
            print(f"  頂点数: {{len(obj.data.vertices)}}")
            print(f"  面数: {{len(obj.data.polygons)}}")
            
            # バーテックスグループ分析
            vg_count = len(obj.vertex_groups)
            print(f"  バーテックスグループ数: {{vg_count}}")
            
            if vg_count > 0:
                # ウェイト分析
                total_weighted = 0
                zero_weighted = 0
                
                for vertex in obj.data.vertices:
                    vertex_weights = []
                    for group in vertex.groups:
                        if group.weight > 0:
                            vertex_weights.append(group.weight)
                    
                    if vertex_weights:
                        total_weighted += 1
                    else:
                        zero_weighted += 1
                
                print(f"  ウェイト付き頂点: {{total_weighted}}")
                print(f"  ウェイトなし頂点: {{zero_weighted}}")
                
                # ウェイト統計
                if total_weighted > 0:
                    weight_ratio = total_weighted / len(obj.data.vertices) * 100
                    print(f"  ウェイト付与率: {{weight_ratio:.1f}}%")
            else:
                print("  ⚠️ バーテックスグループなし")
        
        elif obj.type == 'ARMATURE':
            print(f"アーマチュア: {{obj.name}}")
            print(f"  ボーン数: {{len(obj.data.bones)}}")
            
            # ボーン階層
            root_bones = [b for b in obj.data.bones if b.parent is None]
            print(f"  ルートボーン数: {{len(root_bones)}}")

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
            
            cmd = ["blender", "--background", "--python", tmp.name]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            print("Blender分析結果:")
            if result.stdout:
                # Blender出力から重要部分を抽出
                lines = result.stdout.split('\n')
                in_analysis = False
                for line in lines:
                    if "=== マージ出力FBX分析 ===" in line:
                        in_analysis = True
                    elif in_analysis and line.strip():
                        print(line)
            
            if result.stderr and "Error" in result.stderr:
                print(f"Blenderエラー: {result.stderr}")
            
            # 一時ファイル削除
            os.unlink(tmp.name)
            
    except Exception as e:
        print(f"❌ Blender分析実行エラー: {e}")

if __name__ == "__main__":
    try:
        print("🚀 Step4マージ処理ロジック詳細調査開始")
        print("=" * 80)
        
        # 1. src.inference.merge 直接実行
        success, stdout, stderr = run_merge_with_debug()
        
        # 2. ソースコード分析
        analyze_merge_source_code()
        
        # 3. 出力品質チェック
        check_merge_output_quality()
        
        print("\n🎯 調査完了")
        
    except Exception as e:
        print(f"❌ 調査実行エラー: {e}")
        import traceback
        traceback.print_exc()
