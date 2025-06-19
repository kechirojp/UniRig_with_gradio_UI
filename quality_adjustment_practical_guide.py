#!/usr/bin/env python3
"""
UniRig 品質調整実践ガイド - 実際の変更方法

このファイルは、実際にUniRigの品質を調整する手順を示します。
"""

def show_skeleton_quality_adjustment():
    """スケルトン品質調整の実際の変更方法"""
    
    print("=== Step2: スケルトン品質調整 ===")
    print("ファイル: /app/step_modules/step2_skeleton.py")
    print("行数: 180")
    print()
    
    print("【現在の設定】")
    current_code = '''
            extract_cmd = [
                sys.executable, "-m", "src.data.extract",
                "--config", str(data_config),
                "--force_override", "true",
                "--num_runs", "1",
                "--faces_target_count", "4000",  # 🔥 現在: 標準品質
                "--require_suffix", "obj,fbx,FBX,dae,glb,gltf,vrm",
                "--time", time_str,
                "--id", "0",
                "--input", str(original_file),
                "--output_dir", str(unirig_model_processing_dir)
            ]
    '''
    print(current_code)
    
    print("【高品質設定への変更例】")
    high_quality_code = '''
            extract_cmd = [
                sys.executable, "-m", "src.data.extract",
                "--config", str(data_config),
                "--force_override", "true",
                "--num_runs", "1",
                "--faces_target_count", "8000",  # 🔥 変更: 高品質 (4000→8000)
                "--require_suffix", "obj,fbx,FBX,dae,glb,gltf,vrm",
                "--time", time_str,
                "--id", "0",
                "--input", str(original_file),
                "--output_dir", str(unirig_model_processing_dir)
            ]
    '''
    print(high_quality_code)

def show_skinning_quality_adjustment():
    """スキニング品質調整の実際の変更方法"""
    
    print("=== Step3: スキニング品質調整 ===")
    print("ファイル: /app/step_modules/step3_skinning_unirig.py")
    print("行数: 234")
    print()
    
    print("【現在の設定】")
    current_code = '''
            extract_cmd = [
                sys.executable, "-m", "src.data.extract",
                "--config", str(data_config),
                "--force_override", "true",
                "--num_runs", "1",
                "--faces_target_count", "50000",  # 🔥 現在: 標準品質
                "--require_suffix", "obj,fbx,FBX,dae,glb,gltf,vrm",
                "--time", time_str,
                "--id", "0",
                "--input", str(original_file),
                "--output_dir", str(unirig_model_processing_dir)
            ]
    '''
    print(current_code)
    
    print("【超高品質設定への変更例】")
    ultra_quality_code = '''
            extract_cmd = [
                sys.executable, "-m", "src.data.extract",
                "--config", str(data_config),
                "--force_override", "true",
                "--num_runs", "1",
                "--faces_target_count", "80000",  # 🔥 変更: 超高品質 (50000→80000)
                "--require_suffix", "obj,fbx,FBX,dae,glb,gltf,vrm",
                "--time", time_str,
                "--id", "0",
                "--input", str(original_file),
                "--output_dir", str(unirig_model_processing_dir)
            ]
    '''
    print(ultra_quality_code)

def show_terminal_commands():
    """ターミナルでの調整確認コマンド"""
    
    print("=== 変更後の確認方法 ===")
    print()
    print("1. ファイル編集確認:")
    print("   grep -n 'faces_target_count' /app/step_modules/step2_skeleton.py")
    print("   grep -n 'faces_target_count' /app/step_modules/step3_skinning_unirig.py")
    print()
    print("2. テスト実行:")
    print("   cd /app")
    print("   python app.py  # WebUIで新しい設定をテスト")
    print()
    print("3. 品質確認ポイント:")
    print("   - Step2完了後: スケルトンFBXファイルサイズ確認")
    print("   - Step3完了後: スキニングFBXファイルサイズ確認")
    print("   - 処理時間の変化確認")

def show_quality_comparison_table():
    """品質比較表"""
    
    print("=== 品質設定比較表 ===")
    print()
    print("| 設定 | Step2面数 | Step3面数 | 処理時間 | 品質レベル | 用途 |")
    print("|------|-----------|-----------|----------|------------|------|")
    print("| 軽量 | 2000      | 25000     | 短い     | 基本       | プロトタイプ |")
    print("| 標準 | 4000      | 50000     | 中程度   | 良好       | 現在の設定 |")
    print("| 高品質 | 8000    | 80000     | 長い     | 優秀       | 推奨設定 |")
    print("| 最高 | 12000     | 100000    | 非常に長い | 最高     | プロダクション |")
    print()
    print("⚠️ 注意: 面数を増やすと処理時間とGPUメモリ使用量が大幅に増加します")

if __name__ == "__main__":
    print("🎯 UniRig 品質調整実践ガイド")
    print("=" * 50)
    
    show_skeleton_quality_adjustment()
    print("\n" + "=" * 50)
    
    show_skinning_quality_adjustment()
    print("\n" + "=" * 50)
    
    show_terminal_commands()
    print("\n" + "=" * 50)
    
    show_quality_comparison_table()
    
    print("\n🚀 次のステップ:")
    print("1. 上記の設定を参考に、ファイルを編集")
    print("2. python app.py でWebUIを起動")
    print("3. 新しい設定でモデルを処理")
    print("4. 結果の品質と処理時間を確認")
    print("5. 必要に応じてさらに調整")
