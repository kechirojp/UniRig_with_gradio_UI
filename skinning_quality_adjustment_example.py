#!/usr/bin/env python3
"""
UniRig スキニング品質調整の実例
Step3のfaces_target_countを調整してスキンウェイト精度を向上
"""

# 現在の設定: step_modules/step3_skinning_unirig.py Line 234
# "--faces_target_count", "50000",  # 🔥 スキニング特化: 詳細メッシュ

# 調整例:

# 🔥 超高品質スキニング用 (推奨)
SKINNING_ULTRA_QUALITY = "80000"  # 現在の1.6倍: より滑らかな変形

# 🔥 最高品質スキニング用 (プロダクション向け)
SKINNING_MAX_QUALITY = "100000"  # 現在の2倍: プロ品質

# 🔥 標準スキニング用 (現在)
SKINNING_STANDARD_QUALITY = "50000"  # 現在の設定

# 🔥 軽量スキニング用 (プロトタイプ用)
SKINNING_LIGHT_QUALITY = "25000"  # 現在の半分: 高速処理

def modify_step3_quality(target_faces: str = "80000"):
    """
    Step3のスキニング品質を調整する実例コード
    
    Args:
        target_faces: ターゲット面数（文字列）
    
    調整場所:
        /app/step_modules/step3_skinning_unirig.py
        Line 234: "--faces_target_count", "50000",
    """
    
    # 実際の調整方法
    adjustment_code = f'''
    # step_modules/step3_skinning_unirig.py 内の調整箇所
    extract_cmd = [
        sys.executable, "-m", "src.data.extract",
        "--config", str(data_config),
        "--force_override", "true",
        "--num_runs", "1",
        "--faces_target_count", "{target_faces}",  # 🔥 この値を調整
        "--require_suffix", "obj,fbx,FBX,dae,glb,gltf,vrm",
        "--time", time_str,
        "--id", "0",
        "--input", str(original_file),
        "--output_dir", str(unirig_model_processing_dir)
    ]
    '''
    
    print("スキニング品質調整コード例:")
    print(adjustment_code)
    
    # 品質レベルの説明
    quality_levels = {
        "25000": "軽量処理（プロトタイプ用）",
        "50000": "標準品質（現在の設定）",
        "80000": "超高品質（推奨アップグレード）",
        "100000": "最高品質（プロダクション用）",
        "150000": "極限品質（処理時間極大）"
    }
    
    print(f"\n選択した品質レベル: {target_faces} - {quality_levels.get(target_faces, '不明')}")
    
    return adjustment_code

def explain_skinning_quality_impact():
    """スキニング品質調整の影響を説明"""
    
    print("=== スキニング品質調整の影響 ===")
    print()
    print("📈 面数を増加させると:")
    print("  ✅ より滑らかな皮膚変形")
    print("  ✅ 関節部分の自然な曲がり")
    print("  ✅ 細かい部位（指・顔）の精密制御")
    print("  ✅ ボーンウェイトの詳細計算")
    print("  ❌ 処理時間の大幅増加")
    print("  ❌ GPUメモリ使用量増加")
    print()
    print("📉 面数を減少させると:")
    print("  ✅ 高速処理")
    print("  ✅ 軽量な処理負荷")
    print("  ❌ 粗い皮膚変形")
    print("  ❌ 関節部分の不自然な曲がり")
    print()
    print("🎯 推奨設定:")
    print("  - プロトタイプ・テスト: 25000")
    print("  - 標準品質: 50000 (現在)")
    print("  - 高品質アニメーション: 80000")
    print("  - プロダクション品質: 100000")

if __name__ == "__main__":
    print("=== UniRig スキニング品質調整実例 ===")
    
    # 超高品質設定の例
    modify_step3_quality("80000")
    
    print("\n=== 品質レベル比較 ===")
    print("faces_target_count = 25000:  軽量処理（約90秒）")
    print("faces_target_count = 50000:  標準品質（約180秒）- 現在")
    print("faces_target_count = 80000:  超高品質（約300秒）- 推奨")
    print("faces_target_count = 100000: 最高品質（約450秒）")
    print("faces_target_count = 150000: 極限品質（約900秒）")
    
    explain_skinning_quality_impact()
