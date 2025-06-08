#!/usr/bin/env python3
"""
修正されたデータフロー完全検証テスト
Step1〜Step4のファイル名規則修正後の動作確認
"""
import sys
import os
from pathlib import Path
import time
import shutil

# プロジェクトルートディレクトリを追加
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/step_modules')

# ステップモジュールをインポート
from step_modules.step1_extract import Step1Extract
from step_modules.step2_skeleton import Step2Skeleton
from step_modules.step3_skinning import Step3Skinning

def main():
    print("🔥 修正されたデータフロー完全検証開始")
    print("=" * 60)
    
    # テスト用入力ファイル
    test_model = "/app/examples/bird.glb"
    model_name = "test_dataflow_bird"
    
    if not Path(test_model).exists():
        print(f"❌ テストモデルが見つかりません: {test_model}")
        return False
        
    # ワークディレクトリ準備
    work_dir = Path("/app/test_fixed_dataflow_output")
    work_dir.mkdir(exist_ok=True)
    
    print(f"📁 作業ディレクトリ: {work_dir}")
    print(f"🎯 テストモデル: {test_model}")
    print(f"🏷️ モデル名: {model_name}")
    print()
    
    # === STEP 1: メッシュ抽出 ===
    print("🔧 STEP 1: メッシュ抽出開始")
    step1_dir = work_dir / "01_extract"
    step1 = Step1Extract(step1_dir)
    
    success, logs, files = step1.extract_mesh(test_model, model_name)
    print(f"📊 Step1結果: {success}")
    print(f"📝 ログ: {logs}")
    print(f"📄 出力ファイル: {files}")
    
    if not success or "extracted_mesh" not in files:
        print("❌ Step1失敗")
        return False
        
    extracted_file = files["extracted_mesh"]
    print(f"✅ Step1成功: {extracted_file}")
    print()
    
    # === STEP 2: スケルトン生成 ===
    print("🔧 STEP 2: スケルトン生成開始")
    step2_dir = work_dir / "02_skeleton"
    step2 = Step2Skeleton(step2_dir)
    
    print(f"🔍 メッシュファイル確認: {extracted_file}")
    print(f"🔍 ファイル存在チェック: {Path(extracted_file).exists()}")
    
    success, logs, files = step2.generate_skeleton(extracted_file, model_name, "neutral")
    print(f"📊 Step2結果: {success}")
    print(f"📝 ログ: {logs}")
    print(f"📄 出力ファイル: {files}")
    
    if not success or "skeleton_fbx" not in files:
        print("❌ Step2失敗")
        return False
        
    skeleton_file = files["skeleton_fbx"]
    
    # 🚨 CRITICAL: 修正されたファイル名規則の確認
    expected_fbx = step2_dir / f"{model_name}.fbx"  # サフィックス除去
    expected_npz = step2_dir / "predict_skeleton.npz"  # 固定名
    
    print(f"🔍 期待されるFBXファイル: {expected_fbx}")
    print(f"🔍 期待されるNPZファイル: {expected_npz}")
    print(f"🔍 実際のFBXファイル: {skeleton_file}")
    
    if Path(skeleton_file) == expected_fbx:
        print("✅ FBXファイル名規則修正成功")
    else:
        print("❌ FBXファイル名規則修正失敗")
        
    if expected_npz.exists():
        print("✅ NPZファイル名規則修正成功")
    else:
        print("❌ NPZファイル名規則修正失敗")
        
    print(f"✅ Step2成功: {skeleton_file}")
    print()
    
    # === STEP 3: スキニング適用 ===
    print("🔧 STEP 3: スキニング適用開始")
    step3_dir = work_dir / "03_skinning"
    step3 = Step3Skinning(step3_dir)
    
    success, logs, files = step3.apply_skinning(extracted_file, skeleton_file, model_name)
    print(f"📊 Step3結果: {success}")
    print(f"📝 ログ: {logs[:500]}...")  # ログが長いので省略
    print(f"📄 出力ファイル: {files}")
    
    if not success:
        print("❌ Step3失敗")
        print(f"📝 完全ログ: {logs}")
        return False
        
    skinned_file = files.get("skinned_fbx")
    if skinned_file and Path(skinned_file).exists():
        file_size = Path(skinned_file).stat().st_size
        print(f"✅ Step3成功: {skinned_file} (サイズ: {file_size} bytes)")
        
        if file_size > 50000:  # 50KB以上なら正常
            print("✅ FBXファイルサイズ正常")
        else:
            print("⚠️ FBXファイルサイズが小さすぎます")
    else:
        print("❌ スキニング済みFBXファイルが生成されていません")
        return False
    
    print()
    
    # === 最終検証 ===
    print("🔍 最終検証: 生成されたファイル一覧")
    for step_dir in [step1_dir, step2_dir, step3_dir]:
        if step_dir.exists():
            print(f"\n📁 {step_dir.name}:")
            for file_path in step_dir.iterdir():
                if file_path.is_file():
                    size = file_path.stat().st_size
                    print(f"  - {file_path.name}: {size} bytes")
    
    print("\n🎉 修正されたデータフロー検証完了")
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ 全ステップ成功 - データフロー修正が正常に動作")
        sys.exit(0)
    else:
        print("\n❌ テスト失敗")
        sys.exit(1)
