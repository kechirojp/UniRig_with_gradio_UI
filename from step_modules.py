from step_modules.step0_asset_preservation import Step0AssetPreservation
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('test')
try:
    step0 = Step0AssetPreservation(
        model_name='bird',
        input_file='/app/pipeline_work/bird/bird.glb',
        output_dir='/app/pipeline_work/bird/00_asset_preservation',
        logger_instance=logger
    )
    print('Step0AssetPreservation初期化成功')
except Exception as e:
    print(f'エラー: {e}')
    import traceback
    traceback.print_exc()