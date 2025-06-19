#!/usr/bin/env python3
"""
run.py重大欠陥の修正版
2025年6月17日作成 - バーテックスグループ検証機能と合わせて、run.pyの安定性を向上

重大な修正点:
1. 複雑なファイルパス解決ロジックの簡素化
2. 条件分岐の混乱解消
3. 適切なエラーハンドリング実装
4. 無意味なコードの削除
5. data_name設定の明確化
"""

import argparse
import yaml
from box import Box
import os
import torch
import lightning as L
from lightning.pytorch.callbacks import ModelCheckpoint, Callback, BasePredictionWriter
from typing import List, Dict, Any, Optional
from math import ceil
import numpy as np
from lightning.pytorch.strategies import FSDPStrategy, DDPStrategy
from src.inference.download import download
import hydra
from pathlib import Path

from src.data.asset import Asset
from src.data.extract import get_files
from src.data.dataset import UniRigDatasetModule, DatasetConfig, ModelInput
from src.data.datapath import Datapath
from src.data.transform import TransformConfig
from src.tokenizer.spec import TokenizerConfig
from src.tokenizer.parse import get_tokenizer
from src.model.parse import get_model
from src.system.parse import get_system, get_writer

from tqdm import tqdm
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
run_logger = logging.getLogger(__name__)

os.environ['PYOPENGL_PLATFORM'] = 'osmesa'

def load_config_safely(task_category: str, config_identifier: str) -> Box:
    """
    🔧 修正: 設定ファイル読み込みの簡素化と安全性向上
    
    Args:
        task_category: 設定カテゴリ ('task', 'data', など)
        config_identifier: 設定ファイル識別子
        
    Returns:
        Box: 読み込まれた設定
        
    Raises:
        FileNotFoundError: 設定ファイルが見つからない場合
    """
    # .yamlが付いていない場合は追加
    if not config_identifier.endswith('.yaml'):
        config_identifier += '.yaml'

    # パス解決を簡素化
    config_path = Path(config_identifier)
    
    # 絶対パスでない場合、configs/{task_category}/として処理
    if not config_path.is_absolute() and not str(config_path).startswith('configs/'):
        config_path = Path('configs') / task_category / config_path.name
    
    run_logger.info(f"設定ファイル読み込み: {config_path}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        return Box(config_data)
    except FileNotFoundError:
        run_logger.error(f"設定ファイルが見つかりません: {config_path}")
        raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")
    except yaml.YAMLError as e:
        run_logger.error(f"YAML解析エラー: {config_path} - {e}")
        raise

def resolve_input_files(args) -> tuple[List[str], Optional[Datapath]]:
    """
    🔧 修正: 入力ファイル解決ロジックの簡素化
    
    複雑だった入力ファイル解決ロジックを明確で理解しやすく修正
    
    Args:
        args: コマンドライン引数
        
    Returns:
        tuple: (処理対象ファイルリスト, Datapathオブジェクト)
    """
    files_to_process = []
    datapath = None
    
    # Case 1: npz_dirが指定されている場合（最優先）
    if args.npz_dir:
        npz_dir_path = Path(args.npz_dir).resolve()
        if npz_dir_path.exists():
            datapath = Datapath(files=[str(npz_dir_path)], cls=args.cls)
            run_logger.info(f"npz_dirを使用: {npz_dir_path}")
        else:
            run_logger.warning(f"指定されたnpz_dirが存在しません: {npz_dir_path}")
    
    # Case 2: 直接NPZファイルが指定されている場合
    elif args.input and args.input.endswith('.npz'):
        input_path = Path(args.input).resolve()
        if input_path.exists():
            files_to_process = [str(input_path)]
            datapath = Datapath(files=[str(input_path.parent)], cls=args.cls)
            run_logger.info(f"NPZファイルを直接使用: {input_path}")
        else:
            run_logger.warning(f"指定されたNPZファイルが存在しません: {input_path}")
    
    # Case 3: input_dirが指定されている場合
    elif args.input_dir:
        input_dir_path = Path(args.input_dir).resolve()
        if input_dir_path.exists():
            datapath = Datapath(files=[str(input_dir_path)], cls=args.cls)
            run_logger.info(f"input_dirを使用: {input_dir_path}")
        else:
            run_logger.warning(f"指定されたinput_dirが存在しません: {input_dir_path}")
    
    # Case 4: 個別ファイルが指定されている場合
    elif args.input:
        input_path = Path(args.input).resolve()
        if input_path.exists():
            files_to_process = [str(input_path)]
            run_logger.info(f"個別ファイルを使用: {input_path}")
        else:
            run_logger.warning(f"指定されたファイルが存在しません: {input_path}")
    
    else:
        run_logger.info("入力ファイル/ディレクトリが指定されていません")
    
    return files_to_process, datapath

def validate_prediction_requirements(task_config, resume_from_checkpoint) -> bool:
    """
    🔧 修正: 予測実行の要件検証
    
    Args:
        task_config: タスク設定
        resume_from_checkpoint: チェックポイントパス
        
    Returns:
        bool: 要件を満たしているかどうか
    """
    if task_config.mode != 'predict':
        run_logger.error(f"サポートされていないモード: {task_config.mode}")
        return False
    
    if not resume_from_checkpoint:
        run_logger.error("予測モードではcheckpointが必要ですが、指定されていません")
        return False
    
    checkpoint_path = Path(resume_from_checkpoint)
    if not checkpoint_path.exists():
        run_logger.error(f"指定されたcheckpointファイルが存在しません: {checkpoint_path}")
        return False
    
    return True

def nullable_string(val):
    """コマンドライン引数でNoneを許可"""
    if not val:
        return None
    return val

if __name__ == "__main__":
    torch.set_float32_matmul_precision('high')
    
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description="UniRig予測システム")
    parser.add_argument("--task", type=str, required=True, help="タスク設定ファイル")
    parser.add_argument("--seed", type=int, default=123, help="ランダムシード")
    parser.add_argument("--input", type=nullable_string, default=None, help="入力ファイル")
    parser.add_argument("--input_dir", type=nullable_string, default=None, help="入力ディレクトリ")
    parser.add_argument("--output", type=nullable_string, default=None, help="出力ファイル名")
    parser.add_argument("--output_dir", type=nullable_string, default=None, help="出力ディレクトリ")
    parser.add_argument("--npz_dir", type=nullable_string, default='tmp', help="中間NPZディレクトリ")
    parser.add_argument("--cls", type=nullable_string, default=None, help="クラス名")
    parser.add_argument("--data_name", type=nullable_string, default=None, help="NPZファイル名")
    
    args = parser.parse_args()
    
    # シード設定
    L.seed_everything(args.seed, workers=True)
    run_logger.info(f"ランダムシード設定: {args.seed}")
    
    try:
        # 設定ファイル読み込み
        task_config = load_config_safely('task', args.task)
        data_config = load_config_safely('data', task_config.components.data)
        transform_config = load_config_safely('transform', task_config.components.transform)
        
        # 入力ファイル解決
        files_to_process, datapath = resolve_input_files(args)
        
        # data_name設定の明確化
        data_name = args.data_name or task_config.components.get('data_name', 'raw_data.npz')
        run_logger.info(f"使用するdata_name: {data_name}")
        
        # トークナイザー設定
        tokenizer_config_obj = None
        tokenizer_cfg_path = task_config.components.get('tokenizer')
        if tokenizer_cfg_path:
            tokenizer_loaded_cfg = load_config_safely('tokenizer', tokenizer_cfg_path)
            tokenizer_config_obj = TokenizerConfig.parse(config=tokenizer_loaded_cfg)
        
        # データセット設定
        predict_dataset_config = None
        if data_config.get('predict_dataset_config'):
            predict_dataset_config = DatasetConfig.parse(config=data_config.predict_dataset_config).split_by_cls()
        
        # 変換設定
        predict_transform_config = None
        if transform_config.get('predict_transform_config'):
            predict_transform_config = TransformConfig.parse(config=transform_config.predict_transform_config)
        
        # モデル初期化
        model = None
        model_cfg_path = task_config.components.get('model')
        if model_cfg_path:
            model_loaded_cfg = load_config_safely('model', model_cfg_path)
            tokenizer_for_model = get_tokenizer(config=tokenizer_config_obj) if tokenizer_config_obj else None
            model = get_model(tokenizer=tokenizer_for_model, **model_loaded_cfg)
            run_logger.info(f"モデル読み込み完了: {type(model)}")
        
        # データモジュール初期化
        data_module = UniRigDatasetModule(
            process_fn=None if model is None else model._process_fn,
            predict_dataset_config=predict_dataset_config,
            predict_transform_config=predict_transform_config,
            tokenizer_config=tokenizer_config_obj,
            debug=False,
            data_name=data_name,
            datapath=datapath,
            cls=args.cls,
        )
        run_logger.info("データモジュール初期化完了")
        
        # コールバック設定
        callbacks_list: List[Callback] = []
        
        # チェックポイントコールバック
        checkpoint_config = task_config.get('checkpoint')
        if checkpoint_config:
            checkpoint_config['dirpath'] = os.path.join('experiments', task_config.experiment_name)
            callbacks_list.append(ModelCheckpoint(**checkpoint_config))
            run_logger.info(f"チェックポイントコールバック追加: {checkpoint_config['dirpath']}")
        
        # ライターコールバック
        active_writer = None
        writer_config_dict = task_config.get('writer')
        if writer_config_dict:
            output_dir = args.output_dir or writer_config_dict.get('output_dir', './outputs')
            save_name = args.output or writer_config_dict.get('save_name', 'output')
            
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            writer_params = {
                **writer_config_dict,
                'output_dir': output_dir,
                'save_name': save_name,
                'order_config': predict_transform_config.order_config if predict_transform_config else None
            }
            
            # 不要なパラメータを削除
            for key in ['npz_dir', 'user_mode', 'output_name', 'add_num', 'repeat']:
                writer_params.pop(key, None)
            
            active_writer = get_writer(**writer_params)
            callbacks_list.append(active_writer)
            run_logger.info(f"ライターコールバック追加: {type(active_writer)}")
        
        # システム初期化
        system = None
        system_cfg_path = task_config.components.get('system')
        if system_cfg_path:
            system_loaded_cfg = load_config_safely('system', system_cfg_path)
            system = get_system(
                **system_loaded_cfg,
                model=model,
                steps_per_epoch=1,
            )
            run_logger.info(f"システムモジュール初期化: {type(system)}")
        
        # チェックポイント設定
        resume_from_checkpoint = task_config.get('resume_from_checkpoint')
        if resume_from_checkpoint:
            resume_from_checkpoint = download(resume_from_checkpoint)
            run_logger.info(f"チェックポイント: {resume_from_checkpoint}")
        
        # 予測実行要件の検証
        if not validate_prediction_requirements(task_config, resume_from_checkpoint):
            exit(1)
        
        # トレーナー初期化
        trainer_config_dict = task_config.get('trainer', {})
        trainer = L.Trainer(
            callbacks=callbacks_list,
            **trainer_config_dict,
        )
        run_logger.info("トレーナー初期化完了")
        
        # 予測実行
        run_logger.info("予測実行開始...")
        predictions_output = trainer.predict(system, datamodule=data_module, ckpt_path=resume_from_checkpoint)
        run_logger.info("予測実行完了")
        
        if predictions_output:
            run_logger.info(f"予測結果: {len(predictions_output)}バッチ")
        else:
            run_logger.warning("予測結果が空です")
        
        if active_writer:
            run_logger.info(f"ライター出力完了: {active_writer.output_dir}")
        
        run_logger.info("スクリプト実行完了")
        
    except Exception as e:
        run_logger.error(f"予期せぬエラー: {type(e).__name__} - {e}")
        raise
