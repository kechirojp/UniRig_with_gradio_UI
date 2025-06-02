
import sys
sys.path.append('/app')

import bpy
from texture_preservation_system import TexturePreservationSystem

# テクスチャ保存システムを初期化
system = TexturePreservationSystem()

# テクスチャ統合を実行
success = system.apply_texture_to_rigged_model(
    rigged_fbx_path="/app/pipeline_work/06_final_output/bird/bird_final.fbx",
    texture_data_dir="/app/pipeline_work/05_texture_preservation/bird",
    output_fbx_path="/app/pipeline_work/06_final_output/bird/bird_final_textures_fixed.fbx"
)

print(f"テクスチャ統合結果: {success}")

# 結果をファイルに記録
import json
result = {
    "success": success,
    "output_exists": os.path.exists("/app/pipeline_work/06_final_output/bird/bird_final_textures_fixed.fbx"),
    "output_size": os.path.getsize("/app/pipeline_work/06_final_output/bird/bird_final_textures_fixed.fbx") if os.path.exists("/app/pipeline_work/06_final_output/bird/bird_final_textures_fixed.fbx") else 0
}

with open("/app/texture_integration_result.json", "w") as f:
    json.dump(result, f, indent=2)
