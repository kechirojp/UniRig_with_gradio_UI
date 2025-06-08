#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step3スキニング処理テストスクリプト（修正版）
修正されたStep3の動作確認用
"""

import os
import sys
import time
from pathlib import Path

# プロジェクトルートを追加
sys.path.append('/app')
sys.path.append('/app/step_modules')

from step_modules.step3_skinning_unirig import Step3UniRigSkinning

def test_step3_fixed():
    """修正されたStep3スキニング処理のテスト"""
    print("🔧 Step3スキニング処理テスト開始（修正版）")
    print("=" * 60)
    
    # 入力ファイルパス
    mesh_file = "/app/pipeline_work/01_extracted_mesh/raw_data.npz"
    skeleton_file = "/app/pipeline_work/02_skeleton/bird_skeleton.fbx"
    model_name = "bird_test_fixed"
    
    # 出力ディレクトリ
    output_dir = Path("/app/test_step3_fix")
    output_dir.mkdir(exist_ok=True)
    
    # 入力ファイルの存在確認
    if not os.path.exists(mesh_file):
        print(f"❌ メッシュファイルが見つかりません: {mesh_file}")
        return False
        
    if not os.path.exists(skeleton_file):
        print(f"❌ スケルトンファイルが見つかりません: {skeleton_file}")
        return False
    
    print(f"✅ 入力ファイル確認完了")
    print(f"   メッシュ: {mesh_file}")
    print(f"   スケルトン: {skeleton_file}")
    print(f"   出力先: {output_dir}")
    
    # Step3インスタンス作成
    step3 = Step3UniRigSkinning(output_dir)
    
    # スキニング処理実行
    print("\n🚀 Step3スキニング処理実行中...")
    start_time = time.time()
    
    success, logs, output_files = step3.apply_skinning(
        mesh_file=mesh_file,
        skeleton_file=skeleton_file,
        model_name=model_name
    )
    
    processing_time = time.time() - start_time
    
    # 結果表示
    print(f"\n📊 処理結果 ({processing_time:.2f}秒)")
    print("=" * 60)
    
    if success:
        print("✅ Step3スキニング処理成功！")
        print(f"\n📝 実行ログ:")
        print(logs)
        
        print(f"\n📁 出力ファイル:")
        for key, value in output_files.items():
            if isinstance(value, str) and os.path.exists(value):
                file_size = os.path.getsize(value)
                print(f"   {key}: {value} ({file_size:,} bytes)")
            else:
                print(f"   {key}: {value}")
        
        # 出力ファイルの詳細チェック
        skinned_fbx = output_files.get("skinned_fbx")
        if skinned_fbx and os.path.exists(skinned_fbx):
            file_size = os.path.getsize(skinned_fbx)
            print(f"\n🎯 メインファイルサイズチェック:")
            print(f"   bird_test_fixed_skinned.fbx: {file_size:,} bytes")
            
            # 期待されるサイズ（7.5MB以上）との比較
            expected_min_size = 7.5 * 1024 * 1024  # 7.5MB
            if file_size >= expected_min_size:
                print(f"   ✅ ファイルサイズ良好 (期待値7.5MB以上)")
            elif file_size > 100 * 1024:  # 100KB以上
                print(f"   ⚠️  ファイルサイズが期待値より小さい（ただし100KB以上）")
            else:
                print(f"   ❌ ファイルサイズ異常に小さい（100KB未満）")
        
    else:
        print("❌ Step3スキニング処理失敗")
        print(f"\n❌ エラーログ:")
        print(logs)
        return False
    
    print("\n" + "=" * 60)
    print("🏁 Step3スキニング処理テスト完了")
    return success

def check_environment():
    """環境確認"""
    print("🔍 環境確認")
    print("-" * 40)
    
    # Python環境
    print(f"Python: {sys.executable}")
    
    # UniRig環境
    unirig_python = "/opt/conda/envs/UniRig/bin/python"
    if os.path.exists(unirig_python):
        print(f"✅ UniRig Python: {unirig_python}")
    else:
        print(f"❌ UniRig Python見つからず: {unirig_python}")
    
    # 設定ファイル
    config_file = "/app/configs/task/quick_inference_unirig_skin.yaml"
    if os.path.exists(config_file):
        print(f"✅ 設定ファイル: {config_file}")
    else:
        print(f"❌ 設定ファイル見つからず: {config_file}")
    
    # run.py
    run_py = "/app/run.py"
    if os.path.exists(run_py):
        print(f"✅ run.py: {run_py}")
    else:
        print(f"❌ run.py見つからず: {run_py}")
    
    print()

if __name__ == "__main__":
    print("🔧 Step3スキニング処理修正版テストスクリプト")
    print("修正されたStep3の動作確認")
    print("=" * 60)
    
    # 環境確認
    check_environment()
    
    # テスト実行
    success = test_step3_fixed()
    
    if success:
        print("\n🎉 テスト成功！修正されたStep3が正常動作しています。")
        sys.exit(0)
    else:
        print("\n💥 テスト失敗。Step3に問題があります。")
        sys.exit(1)
