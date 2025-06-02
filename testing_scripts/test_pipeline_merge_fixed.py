#!/usr/bin/env python3
"""
Test the complete pipeline step by step to verify the merge.py fix
"""

import os
import sys
import shutil
import time
from pathlib import Path

# Add app directory to path
sys.path.append('/app')

import app

def dummy_progress(fraction, desc=''):
    """Progress callback for testing"""
    print(f"Progress: {fraction*100:.1f}% - {desc}")

def test_complete_pipeline_step_by_step():
    """Test each step of the pipeline individually."""
    
    print("🚀 ステップバイステップパイプラインテスト開始")
    print("=" * 60)
    
    # Load configuration
    print("📋 設定を読み込み中...")
    app.load_app_config()
    
    # Test file path
    input_file = "/app/examples/bird.glb"
    model_name = "bird_test"
    gender = "neutral"
    
    if not os.path.exists(input_file):
        print(f"❌ エラー: テストファイルが見つかりません: {input_file}")
        return False
    
    print(f"📁 入力ファイル: {input_file}")
    print(f"🏷️  モデル名: {model_name}")
    print(f"👤 性別: {gender}")
    
    # Clean up previous test outputs
    output_dirs = [
        f"/app/pipeline_work/01_extracted_mesh/{model_name}",
        f"/app/pipeline_work/02_skeleton_output/{model_name}", 
        f"/app/pipeline_work/03_skinning_output/{model_name}",
        f"/app/pipeline_work/04_final_rigged_model/{model_name}"
    ]
    
    for output_dir in output_dirs:
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
            print(f"🧹 クリーンアップ: {output_dir}")
    
    # Step 1: Mesh Extraction
    print("\n" + "="*60)
    print("🔧 ステップ1: メッシュ抽出")
    print("="*60)
    
    start_time = time.time()
    extracted_npz_path, extract_logs = app.process_extract_mesh(
        input_file, 
        model_name, 
        dummy_progress
    )
    extract_time = time.time() - start_time
    
    if not extracted_npz_path:
        print("❌ メッシュ抽出失敗")
        print("ログ:")
        print(extract_logs)
        return False
    
    print(f"✅ メッシュ抽出成功 ({extract_time:.1f}秒)")
    print(f"📄 出力NPZ: {extracted_npz_path}")
    print(f"📊 ファイルサイズ: {os.path.getsize(extracted_npz_path):,} bytes")
    
    # Step 2: Skeleton Generation  
    print("\n" + "="*60)
    print("🦴 ステップ2: スケルトン生成")
    print("="*60)
    
    start_time = time.time()
    result = app.process_generate_skeleton(
        extracted_npz_path, 
        model_name, 
        gender, 
        dummy_progress
    )
    skeleton_time = time.time() - start_time
    
    if result is None:
        print("❌ スケルトン生成失敗")
        return False
    
    skeleton_display_path, skeleton_logs, skeleton_fbx_path, skeleton_txt_path, skeleton_npz_path = result
    
    print(f"✅ スケルトン生成成功 ({skeleton_time:.1f}秒)")
    print(f"📄 FBXファイル: {skeleton_fbx_path}")
    print(f"📄 TXTファイル: {skeleton_txt_path}")
    print(f"📄 NPZファイル: {skeleton_npz_path}")
    
    if skeleton_fbx_path and os.path.exists(skeleton_fbx_path):
        print(f"📊 FBXファイルサイズ: {os.path.getsize(skeleton_fbx_path):,} bytes")
    
    # Step 3: Skinning Weight Prediction
    print("\n" + "="*60)
    print("🎨 ステップ3: スキニングウェイト予測")
    print("="*60)
    
    start_time = time.time()
    skinning_result = app.process_generate_skin(
        extracted_npz_path,
        skeleton_fbx_path,
        skeleton_npz_path,
        model_name,
        dummy_progress
    )
    skinning_time = time.time() - start_time
    
    if skinning_result is None:
        print("❌ スキニング処理失敗")
        return False
    
    skinned_display_path, skinning_logs, skinned_fbx_path, skinning_npz_path = skinning_result
    
    print(f"✅ スキニング処理成功 ({skinning_time:.1f}秒)")
    print(f"📄 スキン済みFBX: {skinned_fbx_path}")
    print(f"📄 スキニングNPZ: {skinning_npz_path}")
    
    if skinned_fbx_path and os.path.exists(skinned_fbx_path):
        print(f"📊 スキン済みFBXサイズ: {os.path.getsize(skinned_fbx_path):,} bytes")
    
    # Step 4: Model Merge (The fixed step!)
    print("\n" + "="*60)
    print("🔗 ステップ4: モデルマージ（修正済み）")
    print("="*60)
    
    start_time = time.time()
    merge_result = app.process_merge_model(
        original_model_path=input_file,  # Use the original input file
        skinned_fbx_path=skinned_fbx_path,
        skinning_npz_path=skinning_npz_path,
        model_name_for_output=model_name,
        progress_fn=dummy_progress
    )
    merge_time = time.time() - start_time
    
    if merge_result is None or len(merge_result) != 3:
        print("❌ モデルマージ失敗")
        return False
    
    final_display_path, merge_logs, final_merged_fbx_path = merge_result
    
    print(f"✅ モデルマージ成功 ({merge_time:.1f}秒)")
    print(f"📄 最終FBXファイル: {final_merged_fbx_path}")
    
    if final_merged_fbx_path and os.path.exists(final_merged_fbx_path):
        file_size = os.path.getsize(final_merged_fbx_path)
        print(f"📊 最終FBXサイズ: {file_size:,} bytes")
        
        if file_size > 0:
            print("🎉 最終マージ済みFBXファイルが正常に生成されました!")
            
            # Summary
            total_time = extract_time + skeleton_time + skinning_time + merge_time
            print("\n" + "="*60)
            print("📈 処理時間サマリー")
            print("="*60)
            print(f"メッシュ抽出:     {extract_time:6.1f}秒")
            print(f"スケルトン生成:   {skeleton_time:6.1f}秒") 
            print(f"スキニング処理:   {skinning_time:6.1f}秒")
            print(f"モデルマージ:     {merge_time:6.1f}秒")
            print(f"合計処理時間:     {total_time:6.1f}秒")
            print("="*60)
            print("🎊 完全パイプライン成功!")
            
            return True
        else:
            print("❌ 最終FBXファイルのサイズが0です")
            return False
    else:
        print("❌ 最終FBXファイルが作成されませんでした")
        return False

def main():
    """Run the step-by-step pipeline test."""
    
    print("UniRig パイプライン修正検証テスト")
    print("merge.pyの修正による問題解決を確認します")
    print()
    
    success = test_complete_pipeline_step_by_step()
    
    if success:
        print("\n🎉 テスト成功!")
        print("merge.py修正により、パイプラインが正常に動作しています。")
    else:
        print("\n💥 テスト失敗")
        print("さらなる調査が必要です。")
        
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
