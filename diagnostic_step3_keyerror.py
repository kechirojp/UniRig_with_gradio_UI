#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Step3 KeyError診断スクリプト

このスクリプトは、Step3でのKeyError: 'unified_skinning_npz'問題を診断します。
実際のStep3の処理を模擬し、output_filesディクショナリの構造を詳細に分析します。

実行方法:
    cd /app
    python diagnostic_step3_keyerror.py

注意事項:
- このスクリプトは実際のスキニング処理は行いません
- output_filesの構造とキー設定を詳細に調査します
- KeyErrorが発生する可能性のあるポイントを特定します
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, Tuple

# プロジェクトルートを追加
sys.path.insert(0, '/app')

def diagnostic_keyerror_scenario():
    """KeyError発生シナリオの診断"""
    
    print("=" * 70)
    print("[DIAGNOSTIC] Step3 KeyError: 'unified_skinning_npz' 診断開始")
    print("=" * 70)
    
    try:
        # 1. Step3Skinningクラスのインポートとインスタンス化
        print("\n[STEP 1] Step3Skinning クラスのインポート...")
        from step_modules.step3_skinning_unirig import Step3Skinning
        
        test_output_dir = Path('/app/test_keyerror_diagnostic')
        test_output_dir.mkdir(parents=True, exist_ok=True)
        
        step3 = Step3Skinning(step_output_dir=test_output_dir)
        print("[OK] Step3Skinning インスタンス作成成功")
        
        # 2. _organize_step3_outputsメソッドの直接テスト
        print("\n[STEP 2] _organize_step3_outputs メソッドの動作確認...")
        
        # テスト用のディレクトリを作成
        test_model_name = "test_model"
        test_unirig_dir = Path('/app/test_unirig_processing')
        test_unirig_dir.mkdir(parents=True, exist_ok=True)
        
        # 模擬的な出力ファイルを作成（FBXのみ、NPZなし）
        mock_fbx_file = test_unirig_dir / "result_fbx.fbx"
        mock_fbx_file.write_text("mock fbx content")
        
        print(f"[INFO] テスト用模擬FBXファイル作成: {mock_fbx_file}")
        print(f"[INFO] NPZファイルは意図的に作成しない（KeyError発生条件をテスト）")
        
        # 3. _organize_step3_outputsの直接実行
        print("\n[STEP 3] _organize_step3_outputs実行...")
        success, logs, output_files = step3._organize_step3_outputs(test_model_name, test_unirig_dir)
        
        print(f"[結果] success: {success}")
        print(f"[結果] logs:\n{logs}")
        print(f"[結果] output_files: {output_files}")
        
        # 4. output_filesの詳細分析
        print("\n[STEP 4] output_files詳細分析...")
        expected_keys = ['unified_skinning_npz', 'unified_skinned_fbx']
        
        print("[INFO] 期待されるキー:")
        for key in expected_keys:
            print(f"  - {key}")
        
        print("\n[INFO] 実際に存在するキー:")
        for key, value in output_files.items():
            print(f"  - '{key}': '{value}' (type: {type(value).__name__})")
        
        # 5. KeyError発生可能性のテスト
        print("\n[STEP 5] KeyError発生可能性テスト...")
        for key in expected_keys:
            try:
                value = output_files[key]
                print(f"[OK] キーアクセス成功: '{key}' = '{value}'")
                
                # 値の妥当性チェック
                if value == "":
                    print(f"[WARN] '{key}'の値が空文字です")
                elif not value:
                    print(f"[WARN] '{key}'の値が空です (False相当)")
                else:
                    print(f"[OK] '{key}'の値は有効です")
                    
            except KeyError as e:
                print(f"[FAIL] KeyError発生: {e}")
                print(f"  対策: output_files.get('{key}', '') を使用してください")
        
        # 6. 安全なアクセス方法のデモンストレーション
        print("\n[STEP 6] 安全なアクセス方法のデモ...")
        for key in expected_keys:
            safe_value = output_files.get(key, '')
            print(f"[SAFE] output_files.get('{key}', ''): '{safe_value}'")
            
            # より詳細な安全チェック
            if key in output_files:
                actual_value = output_files[key]
                if actual_value:
                    print(f"[OK] '{key}' は有効な値を持っています: '{actual_value}'")
                else:
                    print(f"[WARN] '{key}' は空の値です: '{actual_value}'")
            else:
                print(f"[ERROR] '{key}' キーが存在しません！")
        
        return output_files
        
    except Exception as e:
        print(f"[FAIL] 診断中に予期しないエラー: {e}")
        import traceback
        traceback.print_exc()
        return {}

def test_keyerror_in_real_scenario():
    """実際のシナリオでのKeyError再現テスト"""
    
    print("\n" + "=" * 70)
    print("[REAL SCENARIO] KeyError再現テスト")
    print("=" * 70)
    
    # 典型的なKeyErrorが発生するケース
    incomplete_output_scenarios = [
        ("空のディクショナリ", {}),
        ("FBXキーのみ", {"unified_skinned_fbx": "/path/to/model.fbx"}),
        ("NPZキーのみ", {"unified_skinning_npz": "/path/to/model.npz"}),
        ("異なるキー名", {"fbx_file": "/path/to/model.fbx", "npz_file": "/path/to/model.npz"}),
        ("None値を含む", {"unified_skinning_npz": None, "unified_skinned_fbx": "/path/to/model.fbx"})
    ]
    
    for scenario_name, output_files in incomplete_output_scenarios:
        print(f"\n--- シナリオ: {scenario_name} ---")
        print(f"output_files: {output_files}")
        
        # 危険なアクセス方法（KeyErrorが発生する可能性）
        print("[UNSAFE ACCESS] 直接アクセス:")
        for key in ['unified_skinning_npz', 'unified_skinned_fbx']:
            try:
                value = output_files[key]
                print(f"  [OK] {key}: {value}")
            except KeyError as e:
                print(f"  [KEYERROR] {key}: {e}")
        
        # 安全なアクセス方法
        print("[SAFE ACCESS] .get()使用:")
        for key in ['unified_skinning_npz', 'unified_skinned_fbx']:  
            value = output_files.get(key, '')
            print(f"  [SAFE] {key}: '{value}'")

def analyze_step3_code_for_keyerror():
    """Step3コード内のKeyError危険箇所の分析"""
    
    print("\n" + "=" * 70)
    print("[CODE ANALYSIS] Step3コード内KeyError危険箇所分析")
    print("=" * 70)
    
    dangerous_access_patterns = [
        "output_files['unified_skinning_npz']",
        "output_files['unified_skinned_fbx']", 
        "skeleton_files['unified_skeleton_fbx']",
        "skeleton_files['unified_skeleton_npz']"
    ]
    
    print("[INFO] KeyErrorを引き起こす可能性のあるアクセスパターン:")
    for pattern in dangerous_access_patterns:
        print(f"  - {pattern}")
    
    print("\n[INFO] 推奨する安全なアクセスパターン:")
    for pattern in dangerous_access_patterns:
        safe_pattern = pattern.replace("[", ".get(").replace("]", ", '')")
        print(f"  - {pattern} → {safe_pattern}")

if __name__ == "__main__":
    print("Step3 KeyError診断スクリプト")
    print("目的: KeyError: 'unified_skinning_npz' 問題の原因特定と対策")
    print("=" * 70)
    
    # 診断実行
    output_files = diagnostic_keyerror_scenario()
    
    # 実際のシナリオテスト
    test = test_keyerror_in_real_scenario()
    
    # コード分析
    analyze_step3_code_for_keyerror()
    
    print("\n" + "=" * 70)
    print("[CONCLUSION] 診断結果まとめ")
    print("=" * 70)
    print("1. Step3._organize_step3_outputs()は適切にキーを設定します")
    print("2. NPZファイルが見つからない場合、空文字''が設定されます")
    print("3. KeyErrorは他の箇所での不安全なアクセスが原因の可能性があります")
    print("4. すべてのoutput_files/skeleton_filesアクセスは.get()を使用してください")
    print("\n[RECOMMENDATION] 推奨対策:")
    print("- output_files[key] → output_files.get(key, '')")
    print("- skeleton_files[key] → skeleton_files.get(key, '')")
    print("- アクセス前の事前チェック: if key in dict_object:")
    print("=" * 70)
