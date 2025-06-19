from fixed_directory_manager import FixedDirectoryManager
from pathlib import Path
import logging

# ロガー設定
logger = logging.getLogger('test')
logger.setLevel(logging.INFO)

# app.pyと同じ設定
PIPELINE_BASE_DIR = Path('pipeline_work')
model_name = 'bird'

fdm = FixedDirectoryManager(PIPELINE_BASE_DIR, model_name, logger)

# Step4の入力検証
valid, message, available_files = fdm.validate_step_inputs('step4')
print(f'Step4入力検証: {valid}')
print(f'メッセージ: {message}')
print(f'利用可能ファイル:')
for key, value in available_files.items():
    print(f'  {key}: {value}')

# オリジナルファイル探索
original_files = list(fdm.model_dir.glob('*'))
print(f'\\nモデルディレクトリ内ファイル:')
for f in original_files:
    if f.suffix.lower() in ['.glb', '.fbx', '.obj', '.dae', '.gltf']:
        print(f'  {f}')