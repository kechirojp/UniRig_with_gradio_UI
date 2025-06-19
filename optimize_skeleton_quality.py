#!/usr/bin/env python3
"""
スケルトン品質向上パラメーター調整スクリプト
2025年6月17日 - メッシュに沿った正確なスケルトン生成のための設定最適化
"""

import shutil
import yaml
from pathlib import Path

def backup_config_files():
    """設定ファイルのバックアップ作成"""
    config_files = [
        "/app/configs/system/ar_inference_articulationxl.yaml",
        "/app/configs/model/unirig_ar_350m_1024_81920_float32.yaml",
    ]
    
    for config_file in config_files:
        backup_path = config_file + ".backup"
        shutil.copy2(config_file, backup_path)
        print(f"✅ バックアップ作成: {backup_path}")

def optimize_skeleton_quality():
    """スケルトン品質向上のための設定最適化"""
    
    print("🔧 スケルトン品質向上設定を適用中...")
    
    # 1. システム設定最適化 - より精密な推論
    system_config_path = "/app/configs/system/ar_inference_articulationxl.yaml"
    with open(system_config_path, 'r') as f:
        system_config = yaml.safe_load(f)
    
    # 高品質化パラメーター
    system_config['generate_kwargs'].update({
        'max_new_tokens': 6144,      # 🔥 より複雑なスケルトン対応
        'num_beams': 30,             # 🔥 探索精度向上
        'temperature': 1.2,          # 🔥 安定性重視（創造性を少し下げる）
        'top_k': 8,                  # 🔥 候補を絞ってより精密に
        'top_p': 0.9,               # 🔥 確率的カットオフを厳しく
        'repetition_penalty': 2.5,   # 🔥 重複を防止しつつ自然性保持
        'do_sample': True,
        'use_dir_cls': False,
        'no_cls': False,
        'assign_cls': 'articulationxl'
    })
    
    with open(system_config_path, 'w') as f:
        yaml.safe_dump(system_config, f, default_flow_style=False)
    
    print(f"✅ システム設定最適化完了: {system_config_path}")
    
    # 2. モデル設定最適化 - メッシュ理解向上
    model_config_path = "/app/configs/model/unirig_ar_350m_1024_81920_float32.yaml"
    with open(model_config_path, 'r') as f:
        model_config = yaml.safe_load(f)
    
    # メッシュエンコーダー高精度化
    model_config['mesh_encoder'].update({
        'num_latents': 1536,         # 🔥 メッシュ理解詳細度向上
        'embed_dim': 192,            # 🔥 特徴表現の複雑性向上
        'num_encoder_layers': 20,    # 🔥 エンコーダー深度向上
        'heads': 12,                 # 🔥 アテンション多様性向上
        'width': 768,                # 🔥 内部表現幅拡大
        'use_checkpoint': True,      # 🔥 メモリ効率化
        'flash': True,               # 🔥 高速化維持
    })
    
    with open(model_config_path, 'w') as f:
        yaml.safe_dump(model_config, f, default_flow_style=False)
    
    print(f"✅ モデル設定最適化完了: {model_config_path}")

def create_high_quality_config():
    """高品質専用設定ファイル作成"""
    
    # 高品質専用システム設定
    hq_system_config = {
        '__target__': 'ar',
        'val_interval': 1,
        'generate_kwargs': {
            'max_new_tokens': 8192,     # 最大複雑性
            'num_return_sequences': 1,
            'num_beams': 50,            # 最高探索精度
            'do_sample': True,
            'top_k': 5,                 # 最も厳選された候補
            'top_p': 0.85,             # 厳しい確率カットオフ
            'repetition_penalty': 2.0,
            'temperature': 1.0,         # 最も安定的
            'no_cls': False,
            'assign_cls': 'articulationxl',
            'use_dir_cls': False
        }
    }
    
    hq_system_path = "/app/configs/system/ar_inference_articulationxl_high_quality.yaml"
    with open(hq_system_path, 'w') as f:
        yaml.safe_dump(hq_system_config, f, default_flow_style=False)
    
    print(f"✅ 高品質専用設定作成: {hq_system_path}")
    
    # 高品質専用タスク設定
    hq_task_config_path = "/app/configs/task/quick_inference_skeleton_articulationxl_ar_256_high_quality.yaml"
    with open("/app/configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml", 'r') as f:
        base_task_config = yaml.safe_load(f)
    
    # 高品質用にシステム設定を変更
    base_task_config['components']['system'] = 'ar_inference_articulationxl_high_quality'
    base_task_config['experiment_name'] = 'quick_inference_skeleton_articulationxl_ar_256_high_quality'
    
    with open(hq_task_config_path, 'w') as f:
        yaml.safe_dump(base_task_config, f, default_flow_style=False)
    
    print(f"✅ 高品質専用タスク設定作成: {hq_task_config_path}")
    
    return hq_task_config_path

def main():
    print("🚀 スケルトン品質向上設定適用開始")
    
    # バックアップ作成
    backup_config_files()
    
    # 設定最適化
    optimize_skeleton_quality()
    
    # 高品質専用設定作成
    hq_config_path = create_high_quality_config()
    
    print("\n📋 適用された最適化:")
    print("🔥 推論精度向上:")
    print("  - num_beams: 20 → 30 (探索精度向上)")
    print("  - temperature: 1.5 → 1.2 (安定性重視)")
    print("  - top_k: 10 → 8 (候補精選)")
    print("  - max_new_tokens: 4096 → 6144 (複雑性対応)")
    
    print("\n🔥 メッシュ理解向上:")
    print("  - num_latents: 1024 → 1536 (詳細度+50%)")
    print("  - embed_dim: 128 → 192 (特徴表現+50%)")
    print("  - num_encoder_layers: 16 → 20 (深度向上)")
    print("  - heads: 8 → 12 (アテンション多様性+50%)")
    
    print(f"\n🎯 次のステップ:")
    print(f"1. 標準品質: 既存設定で再実行")
    print(f"2. 高品質モード: {hq_config_path} を使用")
    print(f"3. 元に戻す場合: .backup ファイルから復元")
    
    print("\n✅ スケルトン品質向上設定適用完了")

if __name__ == "__main__":
    main()
