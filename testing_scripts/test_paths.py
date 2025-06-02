#!/usr/bin/env python3
"""
パス修正の確認テスト
"""

import os
import sys

sys.path.append('/app')

def test_script_paths():
    """スクリプトパスの確認"""
    print("=== スクリプトパス確認テスト ===")
    
    # app.pyからの相対パス計算をテスト
    app_file = "/app/app.py"
    base_dir = os.path.dirname(app_file)
    
    script_paths = [
        "launch/inference/generate_skeleton.sh",
        "launch/inference/generate_skin.sh", 
        "launch/inference/merge.sh"
    ]
    
    print(f"ベースディレクトリ: {base_dir}")
    
    for script_name in script_paths:
        script_path = os.path.join(base_dir, script_name)
        exists = os.path.exists(script_path)
        executable = os.access(script_path, os.X_OK) if exists else False
        
        print(f"{script_name}:")
        print(f"  パス: {script_path}")
        print(f"  存在: {exists}")
        print(f"  実行可能: {executable}")
        print()
    
    return True

if __name__ == "__main__":
    test_script_paths()
