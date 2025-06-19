from fixed_directory_manager import FixedDirectoryManager
from pathlib import Path
import tempfile

# テスト用の一時ディレクトリ
with tempfile.TemporaryDirectory() as temp_dir:
    base_dir = Path(temp_dir)
    model_name = 'test'
    
    fdm = FixedDirectoryManager(base_dir, model_name)
    fdm.create_all_directories()
    
    # Step5ディレクトリにテストファイル作成
    step5_dir = fdm.get_step_dir('step5')
    test_file = step5_dir / f'{model_name}_final.glb'
    test_file.write_text('test')
    
    # 動的検索テスト
    found = fdm.find_file_with_dynamic_extension('step5', 'final_output')
    print(f'Found: {found}')
    print(f'Exists: {found.exists() if found else False}')
    print('Test successful!' if found and found.exists() else 'Test failed!')