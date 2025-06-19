#!/usr/bin/env python3
"""
UniRig スケルトン品質調整の実例
Step2のfaces_target_countを調整してスケルトン精度を向上
"""

# 現在の設定: step_modules/step2_skeleton.py Line 180
# "--faces_target_count", "4000",  # 🔥 スケルトン特化: 面数最適化

# 調整例:

# 🔥 高品質スケルトン生成用 (推奨)
SKELETON_HIGH_QUALITY = "8000"  # 現在の2倍: より詳細な骨格構造

# 🔥 超高品質スケルトン生成用 (重いモデル向け)
SKELETON_ULTRA_QUALITY = "12000"  # 現在の3倍: 複雑なキャラクター対応

# 🔥 軽量スケルトン生成用 (テスト・プロトタイプ用)
SKELETON_LIGHT_QUALITY = "2000"  # 現在の半分: 高速処理

def modify_step2_quality(target_faces: str = "8000"):
    """
    Step2のスケルトン品質を調整する実例コード
    
    Args:
        target_faces: ターゲット面数（文字列）
    
    調整場所:
        /app/step_modules/step2_skeleton.py
        Line 180: "--faces_target_count", "4000",
    """
    
    # 実際の調整方法
    adjustment_code = f'''
    # step_modules/step2_skeleton.py 内の調整箇所
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
    
    print("スケルトン品質調整コード例:")
    print(adjustment_code)
    
    # 品質レベルの説明
    quality_levels = {
        "2000": "軽量処理（テスト用）",
        "4000": "標準品質（現在の設定）",
        "8000": "高品質（推奨アップグレード）",
        "12000": "超高品質（複雑キャラクター用）",
        "16000": "最高品質（処理時間大幅増加）"
    }
    
    print(f"\n選択した品質レベル: {target_faces} - {quality_levels.get(target_faces, '不明')}")
    
    return adjustment_code

if __name__ == "__main__":
    print("=== UniRig スケルトン品質調整実例 ===")
    
    # 高品質設定の例
    modify_step2_quality("8000")
    
    print("\n=== 品質レベル比較 ===")
    print("faces_target_count = 2000:  軽量処理（約30秒）")
    print("faces_target_count = 4000:  標準品質（約60秒）- 現在")
    print("faces_target_count = 8000:  高品質（約120秒）- 推奨")
    print("faces_target_count = 12000: 超高品質（約300秒）")
    print("faces_target_count = 16000: 最高品質（約600秒）")
    
    print("\n=== 調整の影響 ===")
    print("✅ 面数増加 → スケルトンの骨格精度向上")
    print("✅ 面数増加 → より自然な関節配置")
    print("✅ 面数増加 → 複雑な形状への対応力向上")
    print("❌ 面数増加 → 処理時間の増加")
    print("❌ 面数増加 → GPU/メモリ使用量増加")
