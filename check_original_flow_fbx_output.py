#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大元フローFBX出力確認スクリプト
Step3でFBXファイルが出力されるべきかどうかを調査
"""

import os
import sys
import subprocess
from pathlib import Path

def check_unirig_config_files():
    """UniRig設定ファイルでFBX出力設定を確認"""
    print("🔍 UniRig設定ファイル確認")
    print("=" * 60)
    
    # タスク設定ファイル確認
    task_config = "/app/configs/task/quick_inference_unirig_skin.yaml"
    if os.path.exists(task_config):
        print(f"✅ タスク設定ファイル: {task_config}")
        with open(task_config, 'r') as f:
            content = f.read()
            if 'export_fbx' in content:
                print(f"🎯 FBX出力設定発見:")
                for line in content.split('\n'):
                    if 'export_fbx' in line:
                        print(f"   {line.strip()}")
            else:
                print("❌ FBX出力設定が見つかりません")
    else:
        print(f"❌ タスク設定ファイルが見つかりません: {task_config}")
    
    # システム設定ファイル確認
    system_config = "/app/configs/system/skin.yaml"
    if os.path.exists(system_config):
        print(f"\n✅ システム設定ファイル: {system_config}")
        with open(system_config, 'r') as f:
            content = f.read()
            if 'export_fbx' in content or 'fbx' in content.lower():
                print(f"🎯 FBX関連設定:")
                for line in content.split('\n'):
                    if 'fbx' in line.lower():
                        print(f"   {line.strip()}")
    else:
        print(f"❌ システム設定ファイルが見つかりません: {system_config}")

def check_skin_writer_source():
    """SkinWriter実装でFBX出力処理を確認"""
    print("\n🔍 SkinWriter実装確認")
    print("=" * 60)
    
    skin_writer = "/app/src/system/skin.py"
    if os.path.exists(skin_writer):
        print(f"✅ SkinWriter実装: {skin_writer}")
        with open(skin_writer, 'r') as f:
            content = f.read()
            
        # FBX関連コード確認
        fbx_lines = []
        for i, line in enumerate(content.split('\n'), 1):
            if 'fbx' in line.lower() or 'export_fbx' in line:
                fbx_lines.append(f"Line {i}: {line.strip()}")
        
        if fbx_lines:
            print("🎯 FBX関連コード:")
            for line in fbx_lines[:10]:  # 最初の10行のみ表示
                print(f"   {line}")
            if len(fbx_lines) > 10:
                print(f"   ... (その他 {len(fbx_lines) - 10} 行)")
        else:
            print("❌ FBX関連コードが見つかりません")
    else:
        print(f"❌ SkinWriter実装が見つかりません: {skin_writer}")

def test_original_launch_script():
    """大元のlaunch/inference/generate_skin.shを確認"""
    print("\n🔍 大元のlaunch スクリプト確認")
    print("=" * 60)
    
    launch_script = "/app/launch/inference/generate_skin.sh"
    if os.path.exists(launch_script):
        print(f"✅ 大元スクリプト: {launch_script}")
        with open(launch_script, 'r') as f:
            content = f.read()
            print("📝 スクリプト内容:")
            print(content)
    else:
        print(f"❌ 大元スクリプトが見つかりません: {launch_script}")

def check_test_step3_output():
    """Test Step3の実際の出力ファイルを確認"""
    print("\n🔍 Test Step3実際の出力確認")
    print("=" * 60)
    
    test_output_dir = "/app/test_step3_fix"
    if os.path.exists(test_output_dir):
        print(f"✅ Test Step3出力ディレクトリ: {test_output_dir}")
        
        # 全ファイル一覧
        all_files = list(Path(test_output_dir).rglob("*"))
        print(f"📁 出力ファイル一覧 ({len(all_files)} ファイル):")
        for file_path in sorted(all_files):
            if file_path.is_file():
                size = file_path.stat().st_size
                print(f"   {file_path.name}: {size:,} bytes")
        
        # NPZファイル詳細確認
        npz_files = list(Path(test_output_dir).glob("*.npz"))
        for npz_file in npz_files:
            print(f"\n🔍 NPZファイル詳細: {npz_file.name}")
            try:
                import numpy as np
                data = np.load(npz_file, allow_pickle=True)
                print(f"   キー: {list(data.keys())}")
                for key in data.keys():
                    item = data[key]
                    if hasattr(item, 'shape'):
                        print(f"   {key}: shape={item.shape}, dtype={item.dtype}")
                    else:
                        print(f"   {key}: {type(item)} = {item}")
            except Exception as e:
                print(f"   ❌ NPZ読み込みエラー: {e}")
    else:
        print(f"❌ Test Step3出力ディレクトリが見つかりません: {test_output_dir}")

def check_results_directory():
    """UniRigのresultsディレクトリを確認"""
    print("\n🔍 UniRig results ディレクトリ確認")
    print("=" * 60)
    
    results_dir = "/app/results"
    if os.path.exists(results_dir):
        print(f"✅ Results ディレクトリ: {results_dir}")
        
        # 全ファイル一覧
        all_files = list(Path(results_dir).rglob("*"))
        print(f"📁 結果ファイル一覧 ({len(all_files)} ファイル):")
        for file_path in sorted(all_files):
            if file_path.is_file():
                size = file_path.stat().st_size
                rel_path = file_path.relative_to(results_dir)
                print(f"   {rel_path}: {size:,} bytes")
                
                # FBXファイルの場合は詳細確認
                if file_path.suffix.lower() == '.fbx':
                    print(f"   🎯 FBXファイル発見: {rel_path}")
    else:
        print(f"❌ Results ディレクトリが見つかりません: {results_dir}")

def check_blender_availability():
    """Blender実行可能性確認"""
    print("\n🔍 Blender実行可能性確認")
    print("=" * 60)
    
    try:
        result = subprocess.run(
            ["blender", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print(f"✅ Blender利用可能:")
            print(f"   {result.stdout.strip()}")
        else:
            print(f"❌ Blenderバージョン確認失敗:")
            print(f"   {result.stderr}")
    except Exception as e:
        print(f"❌ Blender実行エラー: {e}")

def main():
    """メイン実行"""
    print("🔧 大元フローFBX出力確認スクリプト")
    print("=" * 80)
    print("Step3でFBXファイルが出力されるべきかどうかを調査します")
    print("=" * 80)
    
    # 各種確認実行
    check_unirig_config_files()
    check_skin_writer_source()
    test_original_launch_script()
    check_test_step3_output()
    check_results_directory()
    check_blender_availability()
    
    print("\n🏁 調査完了")
    print("=" * 80)

if __name__ == "__main__":
    main()
