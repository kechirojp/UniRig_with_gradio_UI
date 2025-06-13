import argparse
import yaml
from box import Box
import os
import torch
import lightning as L
from lightning.pytorch.callbacks import ModelCheckpoint, Callback, BasePredictionWriter # Added BasePredictionWriter
from typing import List, Dict, Any, Optional # Added Dict, Any, Optional
from math import ceil
import numpy as np
from lightning.pytorch.strategies import FSDPStrategy, DDPStrategy
from src.inference.download import download
import hydra # Added hydra
from pathlib import Path # Added Path

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
run_logger = logging.getLogger(__name__) # Specific logger for this module

os.environ['PYOPENGL_PLATFORM'] = 'osmesa'
# print(f"PYOPENGL_PLATFORM in run.py (set): {os.environ.get('PYOPENGL_PLATFORM')}") # Commented out for cleaner logs

def load(task_category: str, config_identifier: str) -> Box:
    # Ensure it ends with .yaml
    if not config_identifier.endswith('.yaml'):
        config_identifier += '.yaml'

    # Determine the final config path
    # Assumes config_identifier could be:
    # 1. A full path like "configs/task/file.yaml"
    # 2. A path relative to "configs/" like "task/file.yaml"
    # 3. Just a filename like "file.yaml", to be found under "configs/<task_category>/"
    
    path_obj = Path(config_identifier)

    if path_obj.parts[0] == 'configs':
        # Case 1: Already a full path from project root starting with "configs/"
        config_path = path_obj
    elif len(path_obj.parts) > 1 and path_obj.parts[0] == task_category:
        # Case 2: Path like "task/file.yaml", relative to "configs/"
        # This means config_identifier was like "task/specific_task.yaml"
        # and task_category was "task".
        config_path = Path('configs') / path_obj
    else:
        # Case 3: Just a filename like "specific_task.yaml"
        # Or potentially "task_category/specific_task.yaml" where task_category in path_obj.parts[0]
        # was not the same as the passed task_category argument.
        # For safety, we assume it's a filename and prepend "configs/<task_category>/"
        config_path = Path('configs') / task_category / path_obj.name
    
    run_logger.info(f"Attempting to load {task_category} config from: {config_path}")
    try:
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        return Box(config_data)
    except FileNotFoundError:
        run_logger.error(f"Config file not found at {config_path}. Original identifier: {config_identifier}, category: {task_category}")
        # Try an alternative if original path was "configs/task/file.yaml"
        if config_identifier.startswith("configs/task/"):
            alt_path_name = Path(config_identifier).name
            alt_config_path = Path('configs') / task_category / alt_path_name
            run_logger.info(f"Attempting alternative path: {alt_config_path}")
            try:
                with open(alt_config_path, 'r') as f:
                    config_data = yaml.safe_load(f)
                return Box(config_data)
            except FileNotFoundError:
                run_logger.error(f"Alternative config file not found at {alt_config_path}.")
                raise
        raise

def nullable_string(val):
    if not val:
        return None
    return val

if __name__ == "__main__":
    torch.set_float32_matmul_precision('high')
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", type=str, required=True)
    parser.add_argument("--seed", type=int, required=False, default=123,
                        help="random seed")
    parser.add_argument("--input", type=nullable_string, required=False, default=None,
                        help="a single input file or files splited by comma")
    parser.add_argument("--input_dir", type=nullable_string, required=False, default=None,
                        help="input directory")
    parser.add_argument("--output", type=nullable_string, required=False, default=None,
                        help="filename for a single output")
    parser.add_argument("--output_dir", type=nullable_string, required=False, default=None,
                        help="output directory")
    parser.add_argument("--npz_dir", type=nullable_string, required=False, default='tmp',
                        help="intermediate npz directory")
    parser.add_argument("--cls", type=nullable_string, required=False, default=None,
                        help="class name")
    parser.add_argument("--data_name", type=nullable_string, required=False, default=None,
                        help="npz filename from skeleton phase")
    args = parser.parse_args()
    
    L.seed_everything(args.seed, workers=True)
    run_logger.info(f"Seed set to {args.seed}")
    
    task_config = load('task', args.task) # Renamed to task_config for clarity
    mode = task_config.mode
    assert mode in ['predict'], f"Mode must be 'predict', got {mode}"
    
    files_to_process_directly = [] # 変更: files リストの名前を変更し、初期化

    if args.input is not None or args.input_dir is not None:
        assert args.output_dir is not None or args.output is not None, 'output or output_dir must be specified'
        # assert args.npz_dir is not None, 'npz_dir must be specified' # npz_dirは常に指定されるとは限らない

        if args.input and args.input.endswith('.npz'):
            run_logger.info(f"Using pre-processed NPZ file: {args.input}")
            # files_to_process_directly = [os.path.dirname(args.input)] # 以前のロジック
            files_to_process_directly = [args.input] # NPZファイルそのものをリストに
        elif args.input_dir: # input_dir が指定されている場合
            # task_config.components.data_name (e.g., raw_data.npz) が input_dir にあるか確認
            potential_npz_path = Path(args.input_dir) / task_config.components.data_name
            if potential_npz_path.exists():
                run_logger.info(f"Found {task_config.components.data_name} in input_dir: {potential_npz_path}")
                files_to_process_directly = [str(potential_npz_path)]
            else:
                run_logger.info(f"{task_config.components.data_name} not found in input_dir {args.input_dir}. Extracting files...")
                # input_dir からファイルを抽出する元のロジック
                files_info = get_files(
                    data_name=task_config.components.data_name,
                    inputs=args.input, # input も考慮に入れる
                    input_dataset_dir=args.input_dir,
                    output_dataset_dir=args.npz_dir if args.npz_dir else args.input_dir, # npz_dir がなければ input_dir に出力
                    force_override=True,
                    warning=False,
                )
                files_to_process_directly = [f_info[1] for f_info in files_info] # 抽出されたNPZファイルのパス
        elif args.input: # input が指定され、NPZではない場合 (例: .glb)
            run_logger.info(f"Input file specified for extraction: {args.input}")
            files_info = get_files(
                data_name=task_config.components.data_name,
                inputs=args.input,
                input_dataset_dir=None, # input_dir は使わない
                output_dataset_dir=args.npz_dir if args.npz_dir else '.', # npz_dir がなければカレントディレクトリ
                force_override=True,
                warning=False,
            )
            files_to_process_directly = [f_info[1] for f_info in files_info]
        
        run_logger.info(f"Files to process directly: {files_to_process_directly}")
            
        if len(files_to_process_directly) > 1 and args.output is not None:
            run_logger.warning("Output is specified, but multiple files are detected. Output will be written for each.")
        
        # Datapath の初期化方法を変更
        # files_to_process_directly はNPZファイルのフルパスのリストを期待
        # Datapath はディレクトリのリストを期待するので、
        # ここでは files_to_process_directly の親ディレクトリを使うか、Datapath のロジック修正が必要
        
        # 一時的な対応として、files_to_process_directly が空でなければ、その親ディレクトリを datapath に渡す
        if files_to_process_directly:
            # files_to_process_directly の各要素はNPZファイルのフルパスのはず
            # Datapath はディレクトリのリストを期待するので、各NPZファイルの親ディレクトリのリストを作成
            # ただし、重複を避けるために set を使用
            directories_for_datapath = list(set([str(Path(f).parent) for f in files_to_process_directly]))
            datapath = Datapath(files=directories_for_datapath, cls=args.cls)
            run_logger.info(f"Datapath initialized with directories: {directories_for_datapath}")
        else:
            datapath = None
            run_logger.info("No files to process directly, datapath is None.")

    elif args.npz_dir and not files_to_process_directly: # --input, --input_dir がなく、--npz_dir がある場合
        # このケースはStep2の呼び出し方に合致する
        # npz_dir 内の task_config.components.data_name (raw_data.npz) を処理対象とする
        potential_npz_in_npz_dir = Path(args.npz_dir) / task_config.components.data_name
        if potential_npz_in_npz_dir.exists():
            run_logger.info(f"Found {task_config.components.data_name} in npz_dir: {potential_npz_in_npz_dir}")
            # Datapath はディレクトリを期待するので、npz_dir を渡す
            datapath = Datapath(files=[args.npz_dir], cls=args.cls)
            run_logger.info(f"Datapath initialized with npz_dir: {args.npz_dir}")
            # files_to_process_directly にも追加しておく（後段の処理で使われる場合のため）
            files_to_process_directly.append(str(potential_npz_in_npz_dir))
        else:
            datapath = None
            run_logger.warning(f"{task_config.components.data_name} not found in npz_dir {args.npz_dir}. Datapath is None.")
    else:
        datapath = None
        run_logger.info("No input files or npz_dir specified for direct processing, datapath is None.")
    
    data_config = load('data', task_config.components.data)
    transform_config = load('transform', task_config.components.transform)
    
    tokenizer_cfg_path = task_config.components.get('tokenizer', None)
    tokenizer_config_obj = None
    if tokenizer_cfg_path is not None:
        tokenizer_loaded_cfg = load('tokenizer', tokenizer_cfg_path)
        tokenizer_config_obj = TokenizerConfig.parse(config=tokenizer_loaded_cfg)
    
    data_name = task_config.components.get('data_name', 'raw_data.npz')
    if args.data_name is not None:
        data_name = args.data_name
        run_logger.info(f"Overriding data_name with: {data_name}")
        
    predict_dataset_config = None
    if data_config.get('predict_dataset_config') is not None:
        predict_dataset_config = DatasetConfig.parse(config=data_config.predict_dataset_config).split_by_cls()
    
    predict_transform_config = None
    if transform_config.get('predict_transform_config') is not None:
        predict_transform_config = TransformConfig.parse(config=transform_config.predict_transform_config)
    
    model = None
    model_cfg_path = task_config.components.get('model', None)
    if model_cfg_path is not None:
        model_loaded_cfg = load('model', model_cfg_path)
        tokenizer_for_model = get_tokenizer(config=tokenizer_config_obj) if tokenizer_config_obj else None
        model = get_model(tokenizer=tokenizer_for_model, **model_loaded_cfg)
        run_logger.info(f"Model loaded: {type(model)}")
    
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
    run_logger.info("Data module initialized.")
    
    callbacks_list: List[Callback] = []
    checkpoint_config = task_config.get('checkpoint', None)
    if checkpoint_config is not None:
        checkpoint_config['dirpath'] = os.path.join('experiments', task_config.experiment_name)
        callbacks_list.append(ModelCheckpoint(**checkpoint_config))
        run_logger.info(f"ModelCheckpoint callback added. Dirpath: {checkpoint_config['dirpath']}")
    
    writer_config_dict = task_config.get('writer', None)
    active_writer: Optional[BasePredictionWriter] = None
    if writer_config_dict is not None:
        run_logger.info(f"Writer config found: {writer_config_dict}")
        assert predict_transform_config is not None, 'missing predict_transform_config in transform for writer'
        
        # Override writer config with command line arguments if provided
        final_writer_output_dir = args.output_dir if args.output_dir is not None else writer_config_dict.get('output_dir')
        if final_writer_output_dir is None:
            final_writer_output_dir = './outputs'  # Default fallback
        final_writer_save_name = args.output if args.output is not None else writer_config_dict.get('save_name', 'output')
        
        # Ensure output_dir exists for the writer
        Path(final_writer_output_dir).mkdir(parents=True, exist_ok=True)

        writer_params_for_instantiation = {
            **writer_config_dict,
            'output_dir': final_writer_output_dir,
            'save_name': final_writer_save_name, # Changed from output_name to save_name
            'order_config': predict_transform_config.order_config
        }
        # Remove params not expected by get_writer or the writer's __init__
        writer_params_for_instantiation.pop('npz_dir', None) # npz_dir is an arg, not for writer directly
        writer_params_for_instantiation.pop('user_mode', None) # user_mode is an arg, not for writer directly
        writer_params_for_instantiation.pop('output_name', None) # remove old output_name if present
        writer_params_for_instantiation.pop('add_num', None) # remove add_num if present
        writer_params_for_instantiation.pop('repeat', None) # remove repeat if present

        run_logger.info(f"Instantiating writer with params: {writer_params_for_instantiation}")
        active_writer = get_writer(**writer_params_for_instantiation)
        callbacks_list.append(active_writer)
        run_logger.info(f"Writer callback added: {type(active_writer)}")
    else:
        run_logger.info("No writer config found.")

    trainer_config_dict = task_config.get('trainer', {})
    
    system = None
    system_cfg_path = task_config.components.get('system', None)
    if system_cfg_path is not None:
        system_loaded_cfg = load('system', system_cfg_path)
        system = get_system(
            **system_loaded_cfg,
            model=model,
            steps_per_epoch=1, # Placeholder, may need adjustment based on actual usage
        )
        run_logger.info(f"System module initialized: {type(system)}")
    
    # Trainer logger (e.g., TensorBoardLogger) can be configured here if needed
    # For now, using default (None or as per trainer_config_dict)
    trainer_logger = trainer_config_dict.pop('logger', None) # Remove logger from dict if it was to be handled separately
    if isinstance(trainer_logger, str):
        # Basic handling if logger is specified as a string name in config
        # More complex instantiation (e.g. TensorBoardLogger) would go here
        run_logger.warning(f"Trainer logger specified as string '{trainer_logger}', but advanced instantiation not implemented here. Using None.")
        trainer_logger = None 

    resume_from_checkpoint = task_config.get('resume_from_checkpoint', None)
    if resume_from_checkpoint:
        resume_from_checkpoint = download(resume_from_checkpoint)
        run_logger.info(f"Checkpoint to resume from: {resume_from_checkpoint}")
    else:
        run_logger.warning("No checkpoint specified to resume from for prediction mode.")

    trainer = L.Trainer(
        callbacks=callbacks_list,
        logger=trainer_logger, # Use the potentially configured logger
        **trainer_config_dict,
    )
    run_logger.info("Trainer initialized.")
    
    if mode == 'predict':
        if system is None:
            run_logger.error("System module is None, cannot run prediction.")
            exit(1)
        if not resume_from_checkpoint:
            run_logger.error("'resume_from_checkpoint' is required for prediction mode but not provided or found.")
            exit(1)
        
        run_logger.info("Starting prediction phase...")
        # The predict call itself will trigger the writer's write_on_batch_end via callbacks
        predictions_output = trainer.predict(system, datamodule=data_module, ckpt_path=resume_from_checkpoint)
        run_logger.info("Prediction phase completed.")

        if predictions_output:
            run_logger.info(f"Predictions output received. Number of batches: {len(predictions_output)}")
            # Further logging of prediction content if necessary
            # for i, batch_pred in enumerate(predictions_output):
            #     if isinstance(batch_pred, dict):
            #         run_logger.info(f"  Batch {i} keys: {list(batch_pred.keys())}")
            #         for k, v in batch_pred.items():
            #             if hasattr(v, 'shape'):
            #                 run_logger.info(f"    Item '{k}' shape: {v.shape}")
            #             elif isinstance(v, list) and len(v) > 0:
            #                 run_logger.info(f"    Item '{k}' is a list of len {len(v)}")
            # else:
            #     run_logger.info(f"  Batch {i} type: {type(batch_pred)}")
        else:
            run_logger.warning("Predictions output from trainer.predict is empty or None.")

        # The writer (if configured) should have already processed and saved the files
        # during the trainer.predict call due to the callback mechanism.
        if active_writer:
            run_logger.info(f"Writer ({type(active_writer)}) was active. Check output directory: {active_writer.output_dir}")
        else:
            run_logger.info("Writer was not configured. No files were written by a writer callback.")
    else:
        run_logger.error(f"Mode '{mode}' not implemented or invalid.")
        assert False, f"Mode '{mode}' not implemented or invalid."

    run_logger.info("Script execution finished.")