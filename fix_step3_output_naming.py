#!/usr/bin/env python3
"""
Step3出力ファイル命名修正スクリプト - 決め打ちディレクトリ戦略対応
"""

import re
from pathlib import Path

def fix_step3_output_naming():
    """Step3の出力ファイル命名を決め打ちディレクトリ戦略に準拠させる"""
    
    step3_file = Path("/app/step_modules/step3_skinning_unirig.py")
    
    if not step3_file.exists():
        print(f"❌ ファイルが存在しません: {step3_file}")
        return False
    
    content = step3_file.read_text(encoding='utf-8')
    
    # 修正パターン1: unified_skinned_fbx → skinned_fbx
    content = content.replace('"unified_skinned_fbx"', '"skinned_fbx"')
    content = content.replace("'unified_skinned_fbx'", "'skinned_fbx'")
    
    # 修正パターン2: unified_skinning_npz → skinning_npz  
    content = content.replace('"unified_skinning_npz"', '"skinning_npz"')
    content = content.replace("'unified_skinning_npz'", "'skinning_npz'")
    
    # 修正パターン3: output_files辞書に必要なキーを全て含める
    # エラー戻り値の修正
    error_return_pattern = r'return False, [^,]+, \{[^}]*\}'
    
    def replace_error_return(match):
        return '''return False, logs, {
                    "skinned_fbx": "",
                    "skinning_npz": "",
                    "unified_skinned_fbx": "",
                    "unified_skinning_npz": ""
                }'''
    
    content = re.sub(error_return_pattern, replace_error_return, content)
    
    # 修正パターン4: 成功時のoutput_files確実設定
    # 最終出力の決め打ちディレクトリ戦略準拠
    final_output_pattern = r'output_files\["unified_skinned_fbx"\] = str\(unified_fbx_path\)'
    final_output_replacement = '''output_files["skinned_fbx"] = str(unified_fbx_path)
                output_files["unified_skinned_fbx"] = str(unified_fbx_path)'''
    
    content = re.sub(final_output_pattern, final_output_replacement, content)
    
    # バックアップ作成
    backup_file = step3_file.with_suffix('.py.backup')
    backup_file.write_text(step3_file.read_text(encoding='utf-8'), encoding='utf-8')
    print(f"✅ バックアップ作成: {backup_file}")
    
    # 修正されたコンテンツを書き込み
    step3_file.write_text(content, encoding='utf-8')
    print(f"✅ Step3出力命名修正完了: {step3_file}")
    
    return True

if __name__ == "__main__":
    success = fix_step3_output_naming()
    if success:
        print("🔥 Step3出力ファイル命名修正が正常完了しました。")
        print("📝 次のステップ: フルパイプラインテストを実行してください。")
    else:
        print("❌ Step3出力ファイル命名修正に失敗しました。")
