#!/usr/bin/env python3
"""
Unicode (emoji) print statements fixing tool.
SyntaxError: Non-UTF-8 code starting with '\xe2' を修正するためのツール
"""

import os
import re
import sys
from pathlib import Path

# 修正対象のファイル（実行されるPythonファイルのみ）
TARGET_FILES = [
    'app.py',
    'test.py',
    'テスト.py',  # このファイルも含める
    'cleanup_intermediate_data.py',
    'test_cleanup_functionality.py',
    'test_integration.py',
    'test_unified_pipeline_real.py',
    'test_step5_rigging_transfer.py',
    'test_step5_simple.py',
    'test_step5_real.py',
    'test_step5_flexible_formats.py',
    'create_dummy_rigged_fbx.py',
    'rigging_transfer_script.py',
    'test_step2_mesh_reextraction.py',
    'app_complex_backup.py',
    'step_modules/step5_blender_integration.py',
    'test_fixed_directory_only.py',
    'app_dataflow_整流化_diagnostic.py',
    'step_modules_archive/legacy_implementations/step5_blender_integration copy.py',
    'step_modules_archive/legacy_implementations/step5_simplified_blender_integration.py',
    'step_modules_archive/legacy_implementations/step4_merge.py',
    'step_modules_archive/legacy_implementations/step5_reliable_uv_material_transfer.py',
    'step_modules_archive/legacy_implementations/step1_extract.py',
    'step_modules_archive/legacy_implementations/step2_skeleton.py',
    'fixed_directory_manager.py',
    'test_step1_direct.py',
    'material_uv_transfer_script.py',
    'app_dataflow_verification.py',
    'pipeline_file_validation_test.py',
    'test_step2_fixed.py',
    'test_step1_app_integration.py'
]

# Unicode文字のマッピング（安全なASCII文字に変換）
UNICODE_REPLACEMENTS = {
    '✅': '[OK]',
    '❌': '[FAIL]',
    '⏳': '[WAIT]',
    '📁': '[FILE]',
    '📏': '[SIZE]',
    '🏷️': '[TAG]',
    '📂': '[DIR]',
}

def fix_unicode_in_file(file_path):
    """単一ファイル内のUnicode文字を修正"""
    if not file_path.exists():
        print(f"[SKIP] File not found: {file_path}")
        return False
    
    try:
        # ファイル読み込み
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes_made = False
        
        # Unicode文字を置換
        for unicode_char, replacement in UNICODE_REPLACEMENTS.items():
            count = content.count(unicode_char)
            if count > 0:
                content = content.replace(unicode_char, replacement)
                changes_made = True
                print(f"  - {unicode_char} -> {replacement} ({count} occurrences)")
        
        # 変更があった場合のみファイルを更新
        if changes_made:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[FIXED] {file_path}")
            return True
        else:
            print(f"[CLEAN] {file_path}")
            return False
            
    except Exception as e:
        print(f"[ERROR] {file_path}: {e}")
        return False

def main():
    """メイン処理"""
    print("Unicode (emoji) print statements fixing tool")
    print("=" * 50)
    
    workspace_root = Path('/app')
    fixed_files = []
    
    for target_file in TARGET_FILES:
        file_path = workspace_root / target_file
        print(f"\nProcessing: {target_file}")
        
        if fix_unicode_in_file(file_path):
            fixed_files.append(target_file)
    
    print("\n" + "=" * 50)
    print(f"Summary: {len(fixed_files)} files were modified")
    
    if fixed_files:
        print("\nFixed files:")
        for file in fixed_files:
            print(f"  - {file}")
    
    print("\nUnicode fixing completed!")

if __name__ == "__main__":
    main()
