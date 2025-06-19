#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Step4入力データ詳細調査スクリプト

Step4のマージ処理に実際に渡されているファイルの内容を詳細調査し、
resultsディレクトリのファイルと比較検証します。

実行方法:
    cd /app
    python step4_input_data_investigation.py
"""

import sys
import os
from pathlib import Path
import hashlib

# プロジェクトルートを追加
sys.path.insert(0, '/app')

def calculate_file_hash(file_path):
    """ファイルのMD5ハッシュを計算"""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        return f"ERROR: {e}"

def analyze_file_details(file_path, description):
    """ファイルの詳細情報を分析"""
    print(f"\n=== {description} ===")
    print(f"パス: {file_path}")
    
    if not Path(file_path).exists():
        print("❌ ファイルが存在しません")
        return None
    
    # ファイルサイズ
    size = Path(file_path).stat().st_size
    print(f"サイズ: {size:,} bytes ({size / (1024*1024):.2f} MB)")
    
    # ファイルハッシュ
    file_hash = calculate_file_hash(file_path)
    print(f"MD5ハッシュ: {file_hash}")
    
    # 修正時刻
    mtime = Path(file_path).stat().st_mtime
    import datetime
    mod_time = datetime.datetime.fromtimestamp(mtime)
    print(f"最終更新: {mod_time}")
    
    return {
        "path": str(file_path),
        "size": size,
        "hash": file_hash,
        "mtime": mod_time
    }

def compare_files(file1_info, file2_info, name1, name2):
    """2つのファイル情報を比較"""
    print(f"\n🔍 {name1} vs {name2} 比較:")
    
    if file1_info is None or file2_info is None:
        print("❌ 比較不可能 (ファイル不存在)")
        return False
    
    # サイズ比較
    if file1_info["size"] == file2_info["size"]:
        print(f"✅ サイズ一致: {file1_info['size']:,} bytes")
    else:
        print(f"❌ サイズ不一致: {file1_info['size']:,} vs {file2_info['size']:,} bytes")
        return False
    
    # ハッシュ比較
    if file1_info["hash"] == file2_info["hash"]:
        print(f"✅ ハッシュ一致: {file1_info['hash']}")
        print("🎯 ファイル内容が完全に同一です")
        return True
    else:
        print(f"❌ ハッシュ不一致:")
        print(f"  {name1}: {file1_info['hash']}")
        print(f"  {name2}: {file2_info['hash']}")
        print("🚨 ファイル内容が異なります")
        return False

def investigate_step4_inputs():
    """Step4の入力データを詳細調査"""
    print("🔥 Step4入力データ詳細調査開始")
    print("=" * 60)
    
    # Step4の想定入力ファイル
    skeleton_fbx = "/app/pipeline_work/bird/02_skeleton/bird_skeleton.fbx"
    skinned_fbx = "/app/pipeline_work/bird/03_skinning/bird_skinned.fbx"
    
    # resultsディレクトリのファイル
    results_skinned = "/app/results/skinned_model.fbx"
    results_predict = "/app/results/predict_skin.npz"
    
    # Step4入力ファイルの詳細分析
    skeleton_info = analyze_file_details(skeleton_fbx, "Step4入力: スケルトンFBX")
    skinned_info = analyze_file_details(skinned_fbx, "Step4入力: スキニングFBX")
    
    # resultsファイルの詳細分析
    results_skinned_info = analyze_file_details(results_skinned, "results/skinned_model.fbx")
    results_predict_info = analyze_file_details(results_predict, "results/predict_skin.npz")
    
    # 比較検証
    print("\n" + "=" * 60)
    print("🔍 ファイル同一性検証")
    print("=" * 60)
    
    # Step3出力 vs results/skinned_model.fbx
    is_same_skinned = compare_files(
        skinned_info, results_skinned_info,
        "Step3出力 (bird_skinned.fbx)", "results/skinned_model.fbx"
    )
    
    # Step3のNPZファイルも確認
    skinning_npz = "/app/pipeline_work/bird/03_skinning/bird_skinning.npz"
    skinning_npz_info = analyze_file_details(skinning_npz, "Step3出力: スキニングNPZ")
    
    # Step3 NPZ vs results/predict_skin.npz
    is_same_npz = compare_files(
        skinning_npz_info, results_predict_info,
        "Step3出力 (bird_skinning.npz)", "results/predict_skin.npz"
    )
    
    # 結論
    print("\n" + "=" * 60)
    print("🎯 調査結果と結論")
    print("=" * 60)
    
    print(f"Step3 FBX → results 同一性: {'✅ 同一' if is_same_skinned else '❌ 異なる'}")
    print(f"Step3 NPZ → results 同一性: {'✅ 同一' if is_same_npz else '❌ 異なる'}")
    
    if is_same_skinned and is_same_npz:
        print("\n✅ Step3は正しくresultsディレクトリのファイルを使用している")
        print("✅ Step4への入力データは正常")
        print("🔍 問題はStep4のマージ処理ロジックにある可能性が高い")
    else:
        print("\n🚨 Step3の出力がresultsディレクトリと異なる")
        print("🚨 Step4は正しいデータを受け取っていない")
    
    return {
        "skeleton_info": skeleton_info,
        "skinned_info": skinned_info,
        "results_skinned_info": results_skinned_info,
        "results_predict_info": results_predict_info,
        "skinning_npz_info": skinning_npz_info,
        "is_same_skinned": is_same_skinned,
        "is_same_npz": is_same_npz
    }

def check_step4_actual_execution():
    """Step4の実際の実行コマンドとパラメータを確認"""
    print("\n" + "=" * 60)
    print("🔍 Step4実行コマンド詳細調査")
    print("=" * 60)
    
    # Step4のマージ処理実装を確認
    try:
        from unified_merge_orchestrator import UnifiedMergeOrchestrator
        
        print("✅ UnifiedMergeOrchestrator インポート成功")
        
        # 実際のStep4実行をシミュレート
        model_name = "bird"
        output_dir = Path("/app/pipeline_work/bird/04_merge")
        
        orchestrator = UnifiedMergeOrchestrator(model_name, output_dir)
        
        # 入力ファイル情報
        skeleton_files = {"skeleton_fbx": "/app/pipeline_work/bird/02_skeleton/bird_skeleton.fbx"}
        skinning_files = {"skinned_fbx": "/app/pipeline_work/bird/03_skinning/bird_skinned.fbx"}
        
        print(f"Step4入力設定:")
        print(f"  スケルトン: {skeleton_files['skeleton_fbx']}")
        print(f"  スキニング: {skinning_files['skinned_fbx']}")
        
        # ファイル存在確認
        skeleton_exists = Path(skeleton_files['skeleton_fbx']).exists()
        skinning_exists = Path(skinning_files['skinned_fbx']).exists()
        
        print(f"  スケルトン存在: {'✅' if skeleton_exists else '❌'}")
        print(f"  スキニング存在: {'✅' if skinning_exists else '❌'}")
        
        if skeleton_exists and skinning_exists:
            print("✅ Step4の入力ファイル準備完了")
        else:
            print("❌ Step4の入力ファイル不備")
            
    except ImportError as e:
        print(f"❌ UnifiedMergeOrchestrator インポートエラー: {e}")
    except Exception as e:
        print(f"❌ Step4調査エラー: {e}")

if __name__ == "__main__":
    try:
        # Step4入力データ調査
        investigation_result = investigate_step4_inputs()
        
        # Step4実行詳細調査
        check_step4_actual_execution()
        
        print("\n🎯 調査完了")
        
    except Exception as e:
        print(f"❌ 調査実行エラー: {e}")
        import traceback
        traceback.print_exc()
