#!/bin/bash
set -x # Enable command tracing

# 🎯 統一スケルトン生成スクリプト - ユーザー中心設計対応
# 統一命名規則: {model_name}_skeleton.fbx, {model_name}_skeleton.npz

# generate skeleton
config="configs/data/quick_inference.yaml"
require_suffix="obj,fbx,FBX,dae,glb,gltf,vrm"
num_runs=1
force_override="false"
faces_target_count=50000
skeleton_task="configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml"
add_root="false"
seed=12345
npz_dir="tmp"
model_name="" # 統一命名規則対応: モデル名パラメータ追加

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --config) config="$2"; shift ;;
        --require_suffix) require_suffix="$2"; shift ;;
        --num_runs) num_runs="$2"; shift ;;
        --force_override) force_override="$2"; shift ;;
        --faces_target_count) faces_target_count="$2"; shift ;;
        --skeleton_task) skeleton_task="$2"; shift ;;
        --add_root) add_root="$2"; shift ;;
        --seed) seed="$2"; shift ;;
        --input) input="$2"; shift ;;
        --input_dir) input_dir="$2"; shift ;;
        --output_dir) output_dir="$2"; shift ;;
        --output) output="$2"; shift ;;
        --npz_dir) npz_dir="$2"; shift ;;
        --model_name) model_name="$2"; shift ;; # 統一命名規則対応
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# 統一命名規則チェック
if [ -z "$model_name" ]; then
    echo "ERROR: --model_name parameter is required for unified naming convention"
    exit 1
fi

echo "INFO: Generating skeleton for model: $model_name"
echo "INFO: Output directory: $output_dir"

# 1. extract mesh (for skeleton generation - needs raw_data.npz)
time=$(date +%Y_%m_%d_%H_%M_%S)
cmd=" \
    python -m src.data.extract \
    --config $config \
    --force_override $force_override \
    --num_runs $num_runs \
    --target_count $faces_target_count \
    --id 0 \
    --time $time \
"
# The --require_suffix logic is now handled inside extract.py based on the config or defaults.
# The --cfg_task is not directly used by extract.py anymore.
# It's assumed that the $config (e.g., configs/data/quick_inference.yaml) will point to
# the correct settings for data extraction, including any necessary component paths or values.

if [ -n "$input" ]; then
    cmd="$cmd --input $input"
fi
if [ -n "$input_dir" ]; then
    cmd="$cmd --input_dir $input_dir"
fi
if [ -n "$npz_dir" ]; then
    cmd="$cmd --output_dir $npz_dir"
fi

eval $cmd

wait

# 2. 統一スケルトン生成処理
echo "INFO: Starting skeleton generation with unified naming..."

cmd="\
    python run.py \
    --task=$skeleton_task \
    --seed=$seed \
    --model_name=$model_name \
"

# 統一パラメータ設定
if [ -n "$input" ]; then
    cmd="$cmd --input=$input"
fi
if [ -n "$input_dir" ]; then
    cmd="$cmd --input_dir=$input_dir"
fi
if [ -n "$output" ]; then
    cmd="$cmd --output=$output"
fi
if [ -n "$npz_dir" ]; then
    cmd="$cmd --npz_dir=$npz_dir --output_dir=$npz_dir"
fi
if [ -n "$output_dir" ] && [ -z "$npz_dir" ]; then
    cmd="$cmd --output_dir=$output_dir"
fi

echo "INFO: Executing skeleton generation command: $cmd"
eval $cmd

wait

# 統一命名規則確認
echo "INFO: Checking unified naming convention compliance..."
if [ -n "$output_dir" ]; then
    echo "INFO: Expected files in $output_dir:"
    echo "  - ${model_name}_skeleton.fbx (skeleton FBX)"
    echo "  - ${model_name}_skeleton.npz (skeleton data)"
    
    # ファイル存在確認
    if [ -f "$output_dir/predict_skeleton.npz" ]; then
        echo "INFO: Found predict_skeleton.npz - renaming to ${model_name}_skeleton.npz"
        mv "$output_dir/predict_skeleton.npz" "$output_dir/${model_name}_skeleton.npz"
    fi
    
    if [ -f "$output_dir/skeleton_model.fbx" ]; then
        echo "INFO: Found skeleton_model.fbx - renaming to ${model_name}_skeleton.fbx"
        mv "$output_dir/skeleton_model.fbx" "$output_dir/${model_name}_skeleton.fbx"
    fi
fi

echo "INFO: Skeleton generation completed with unified naming convention"