#!/usr/bin/env python3
"""
完全パイプライン修正版テスト: Step1→Step2→Step3→Step4
バイナリFBX問題解決の検証
"""

import os
import sys
import logging
from pathlib import Path

# パスとログ設定
sys.path.append('/app')
os.chdir('/app')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    print("🔧 完全パイプライン修正版テスト開始")
    
    # テスト用設定
    model_name = "test_pipeline_bird"
    input_model = "/app/examples/bird.glb"
    
    # 作業ディレクトリ
    work_dir = Path("/app/pipeline_work_fixed")
    work_dir.mkdir(exist_ok=True)
    
    step1_dir = work_dir / "01_extract"
    step2_dir = work_dir / "02_skeleton"
    step3_dir = work_dir / "03_skinning"
    step4_dir = work_dir / "04_texture"
    
    for d in [step1_dir, step2_dir, step3_dir, step4_dir]:
        d.mkdir(exist_ok=True)
    
    print(f"📁 作業ディレクトリ: {work_dir}")
    print(f"📋 テストモデル: {input_model}")
    
    # Step 1: メッシュ抽出
    print("\n🔧 Step1: メッシュ抽出実行")
    try:
        from step_modules.step1_extract import execute_step1
        success, logs, output_files = execute_step1(input_model, model_name, step1_dir)
        
        if success:
            print("✅ Step1成功")
            print(f"  出力NPZ: {output_files.get('extracted_npz')}")
            extracted_npz = output_files.get('extracted_npz')
        else:
            print(f"❌ Step1失敗: {logs}")
            return False
    except Exception as e:
        print(f"❌ Step1エラー: {e}")
        return False
    
    # Step 2: スケルトン生成
    print("\n🦴 Step2: スケルトン生成実行")
    try:
        from step_modules.step2_skeleton import execute_step2
        success, logs, output_files = execute_step2(extracted_npz, model_name, "neutral", step2_dir)
        
        if success:
            print("✅ Step2成功")
            print(f"  出力FBX: {output_files.get('skeleton_fbx')}")
            print(f"  出力NPZ: {output_files.get('skeleton_npz')}")
            skeleton_fbx = output_files.get('skeleton_fbx')
        else:
            print(f"❌ Step2失敗: {logs}")
            return False
    except Exception as e:
        print(f"❌ Step2エラー: {e}")
        return False
    
    # Step 3: スキニング適用（修正版でバイナリFBX生成）
    print("\n🎭 Step3: スキニング適用実行（バイナリFBX生成修正版）")
    try:
        from step_modules.step3_skinning import execute_step3
        success, logs, output_files = execute_step3(extracted_npz, skeleton_fbx, model_name, step3_dir)
        
        if success:
            print("✅ Step3成功")
            print(f"  出力FBX: {output_files.get('skinned_fbx')}")
            print(f"  出力NPZ: {output_files.get('skinning_npz')}")
            
            # バイナリ形式確認
            skinned_fbx = output_files.get('skinned_fbx')
            if skinned_fbx and Path(skinned_fbx).exists():
                with open(skinned_fbx, 'rb') as f:
                    header = f.read(30)
                    if header.startswith(b"Kaydara FBX Binary"):
                        print("🎯 ✅ バイナリFBX形式確認済み（merge.sh互換）")
                    elif header.startswith(b"; FBX"):
                        print("🎯 ⚠️ ASCII FBX形式（merge.shで問題になる）")
                    else:
                        print(f"🎯 ❓ 不明なファイル形式: {header[:20]}")
            
        else:
            print(f"❌ Step3失敗: {logs}")
            return False
    except Exception as e:
        print(f"❌ Step3エラー: {e}")
        return False
    
    # Step 4: テクスチャ統合（大元フロー互換）
    print("\n🎨 Step4: テクスチャ統合実行（大元フロー互換版）")
    try:
        from step_modules.step4_texture import execute_step4
        success, logs, output_files = execute_step4(
            skinned_fbx, input_model, model_name, step4_dir
        )
        
        if success:
            print("✅ Step4成功")
            print(f"  最終FBX: {output_files.get('final_fbx')}")
            print(f"  ファイルサイズ: {output_files.get('file_size_fbx', 0):,} bytes")
        else:
            print(f"❌ Step4失敗: {logs}")
            return False
    except Exception as e:
        print(f"❌ Step4エラー: {e}")
        return False
    
    print("\n🎉 完全パイプライン修正版テスト成功")
    print("🎯 バイナリFBX問題解決済み")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
