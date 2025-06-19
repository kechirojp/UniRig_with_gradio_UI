#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Step3 KeyError修正スクリプト

このスクリプトは、Step3のKeyError問題を修正します。
主な修正点:
1. _organize_step3_outputsで失敗時も最低限のキーを設定
2. 不安全なディクショナリアクセスを安全な.get()に変更
3. apply_skinningメソッドで必須キーの存在を保証

実行方法:
    cd /app
    python fix_step3_keyerror.py

このスクリプトを実行すると、Step3のコードが自動的に修正されます。
"""

import sys
import os
from pathlib import Path

# プロジェクトルートを追加
sys.path.insert(0, '/app')

def fix_step3_keyerror():
    """Step3のKeyError問題を修正"""
    
    print("=" * 70)
    print("[FIX] Step3 KeyError修正開始")
    print("=" * 70)
    
    step3_file_path = '/app/step_modules/step3_skinning_unirig.py'
    
    try:
        # ファイルを読み込み
        with open(step3_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"[INFO] ファイル読み込み完了: {step3_file_path}")
        
        # 修正1: _organize_step3_outputsの失敗時に最低限のキーを設定
        old_return_pattern = 'return False, logs + "❌ 必須出力ファイルの生成に失敗\\n", {}'
        new_return_pattern = '''return False, logs + "❌ 必須出力ファイルの生成に失敗\\n", {
                "unified_skinning_npz": "",
                "unified_skinned_fbx": "",
                "skinned_fbx": "",
                "skinning_npz": "",
                "step3_mesh": ""
            }'''
        
        if old_return_pattern in content:
            content = content.replace(old_return_pattern, new_return_pattern)
            print("[FIX 1] _organize_step3_outputs失敗時の最低限キー設定を追加")
        else:
            print("[INFO] _organize_step3_outputs修正パターンが見つかりません（既に修正済みの可能性）")
        
        # 修正2: apply_skinningメソッドの出力ファイル参照を安全にする
        unsafe_access_patterns = [
            "output_files['unified_skinned_fbx']",
            "output_files['unified_skinning_npz']"
        ]
        
        safe_access_patterns = [
            "output_files.get('unified_skinned_fbx', '')",
            "output_files.get('unified_skinning_npz', '')"
        ]
        
        fixes_applied = 0
        for old_pattern, new_pattern in zip(unsafe_access_patterns, safe_access_patterns):
            if old_pattern in content:
                content = content.replace(old_pattern, new_pattern)
                fixes_applied += 1
                print(f"[FIX 2.{fixes_applied}] 不安全なアクセス修正: {old_pattern} → {new_pattern}")
        
        if fixes_applied == 0:
            print("[INFO] 不安全なアクセスパターンが見つかりません（既に修正済みの可能性）")
        
        # 修正3: apply_skinningメソッドの最後に必須キーの存在を保証
        final_return_pattern = 'return True, logs, output_files'
        safe_final_return = '''# 必須キーの存在を保証
            if "unified_skinning_npz" not in output_files:
                output_files["unified_skinning_npz"] = ""
            if "unified_skinned_fbx" not in output_files:
                output_files["unified_skinned_fbx"] = ""
            
            return True, logs, output_files'''
        
        # apply_skinningメソッド内の最後のreturn文を探す
        if final_return_pattern in content:
            # 最後のreturn文のみを置換（他のreturn文は変更しない）
            lines = content.split('\n')
            for i in range(len(lines) - 1, -1, -1):  # 逆順で検索
                if 'return True, logs, output_files' in lines[i] and 'apply_skinning' in content[:content.find('\n'.join(lines[i:]))]:
                    # この行がapply_skinningメソッド内の最後のreturn文であることを確認
                    indent = len(lines[i]) - len(lines[i].lstrip())
                    indent_str = ' ' * indent
                    
                    safe_return_lines = [
                        f"{indent_str}# 必須キーの存在を保証",
                        f"{indent_str}if \"unified_skinning_npz\" not in output_files:",
                        f"{indent_str}    output_files[\"unified_skinning_npz\"] = \"\"",
                        f"{indent_str}if \"unified_skinned_fbx\" not in output_files:",
                        f"{indent_str}    output_files[\"unified_skinned_fbx\"] = \"\"",
                        f"{indent_str}",
                        lines[i]  # 元のreturn文
                    ]
                    
                    lines[i:i+1] = safe_return_lines
                    content = '\n'.join(lines)
                    print("[FIX 3] apply_skinningメソッドに必須キー保証ロジックを追加")
                    break
        
        # 修正4: エラー時のreturn文も安全にする
        error_return_pattern = 'return False, logs + error_msg + "\\n", {}'
        safe_error_return = '''return False, logs + error_msg + "\\n", {
                "unified_skinning_npz": "",
                "unified_skinned_fbx": ""
            }'''
        
        if error_return_pattern in content:
            content = content.replace(error_return_pattern, safe_error_return)
            print("[FIX 4] apply_skinning エラー時のreturn文を安全に修正")
        
        # ファイルに書き戻し
        with open(step3_file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"[SUCCESS] Step3 KeyError修正完了: {step3_file_path}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 修正中にエラーが発生: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_fixes():
    """修正の確認"""
    
    print("\n" + "=" * 70)
    print("[VERIFY] 修正内容の確認")
    print("=" * 70)
    
    try:
        # 修正されたStep3を再インポート
        import importlib
        if 'step_modules.step3_skinning_unirig' in sys.modules:
            importlib.reload(sys.modules['step_modules.step3_skinning_unirig'])
        
        from step_modules.step3_skinning_unirig import Step3Skinning
        
        # テスト用のインスタンス作成
        test_output_dir = Path('/app/test_fix_verification')
        test_output_dir.mkdir(parents=True, exist_ok=True)
        
        step3 = Step3Skinning(step_output_dir=test_output_dir)
        print("[OK] 修正されたStep3Skinning インスタンス作成成功")
        
        # 失敗シナリオのテスト
        print("\n[TEST] 失敗シナリオでのKeyError発生確認...")
        test_model_name = "test_model"
        test_unirig_dir = Path('/app/test_unirig_fail')
        test_unirig_dir.mkdir(parents=True, exist_ok=True)
        
        # 意図的に必要なファイルを作成しない（失敗シナリオ）
        success, logs, output_files = step3._organize_step3_outputs(test_model_name, test_unirig_dir)
        
        print(f"[結果] success: {success}")
        print(f"[結果] output_files keys: {list(output_files.keys())}")
        
        # KeyErrorが発生しないかテスト
        expected_keys = ['unified_skinning_npz', 'unified_skinned_fbx']
        for key in expected_keys:
            try:
                value = output_files[key]
                print(f"[OK] キーアクセス成功: '{key}' = '{value}'")
            except KeyError as e:
                print(f"[FAIL] KeyError依然として発生: {e}")
                return False
        
        print("[SUCCESS] KeyError修正が正常に機能しています")
        return True
        
    except Exception as e:
        print(f"[ERROR] 確認中にエラーが発生: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Step3 KeyError修正スクリプト")
    print("目的: KeyError: 'unified_skinning_npz' 問題の根本的修正")
    print("=" * 70)
    
    # 修正実行
    fix_success = fix_step3_keyerror()
    
    if fix_success:
        # 修正の確認
        verify_success = verify_fixes()
        
        print("\n" + "=" * 70)
        print("[RESULT] 修正結果")
        print("=" * 70)
        
        if verify_success:
            print("✅ Step3 KeyError修正が成功しました")
            print("✅ 修正内容:")
            print("   1. _organize_step3_outputs失敗時も最低限のキーを設定")
            print("   2. 不安全なディクショナリアクセスを.get()に変更")
            print("   3. apply_skinningメソッドで必須キーの存在を保証")
            print("   4. エラー時のreturn文も安全に修正")
            print("\n📋 次のステップ:")
            print("   - test_step3_basic_functionality.py を再実行")
            print("   - 実際のスキニング処理テストを実行")
        else:
            print("❌ 修正は完了しましたが、確認でエラーが発生しました")
            print("手動で確認してください")
    else:
        print("❌ 修正中にエラーが発生しました")
        print("手動で修正を行ってください")
    
    print("=" * 70)
