#!/usr/bin/env python3
"""
実際のrun.pyでの設定読み込み検証
"""
import sys
import os
sys.path.append('/app')

from omegaconf import OmegaConf

def debug_config_loading():
    """run.pyが実際に使用する設定の検証"""
    
    print("=== run.py設定読み込み検証 ===")
    
    # run.pyと同じ順序で設定を読み込み
    task_config_path = "configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml"
    print(f"1. タスク設定読み込み: {task_config_path}")
    task_config = OmegaConf.load(task_config_path)
    print(f"   モデル設定指定: {task_config.components.model}")
    
    # モデル設定読み込み
    model_config_name = task_config.components.model
    model_config_path = f"configs/model/{model_config_name}.yaml"
    print(f"2. モデル設定読み込み: {model_config_path}")
    model_config = OmegaConf.load(model_config_path)
    
    print(f"   n_positions: {model_config.llm.n_positions}")
    print(f"   max_position_embeddings: {model_config.llm.max_position_embeddings}")
    
    # 実際にOPTConfigが作成される値をシミュレート
    from transformers import AutoConfig
    
    print(f"3. OPT設定作成テスト...")
    opt_config = AutoConfig.from_pretrained(
        model_config.llm.pretrained_model_name_or_path,
        max_position_embeddings=model_config.llm.max_position_embeddings,
        hidden_size=model_config.llm.hidden_size,
        word_embed_proj_dim=model_config.llm.word_embed_proj_dim
    )
    
    print(f"   OPT設定のmax_position_embeddings: {opt_config.max_position_embeddings}")
    
    # 実際のposition embedding作成をシミュレート
    try:
        from transformers import OPTModel
        print(f"4. OPTモデル作成テスト...")
        model = OPTModel(opt_config)
        pos_embed_size = model.decoder.embed_positions.weight.shape
        print(f"   実際の位置埋め込みサイズ: {pos_embed_size}")
        print(f"   位置数: {pos_embed_size[0]}")
        
        expected = 3078
        actual = pos_embed_size[0]
        
        if actual == expected:
            print("   ✅ 位置埋め込みサイズが正しく修正されています！")
        else:
            print(f"   ❌ まだ不一致: 期待値={expected}, 実際={actual}, 差異={actual-expected}")
            
    except Exception as e:
        print(f"   ❌ OPTモデル作成エラー: {e}")

if __name__ == "__main__":
    debug_config_loading()
