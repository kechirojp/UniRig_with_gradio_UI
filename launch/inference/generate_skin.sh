#!/bin/bash
set -x # Enable command tracing

# 🎯 統一スキニング生成スクリプト - ユーザー中心設計対応
# 統一命名規則: {model_name}_skinned.fbx, {model_name}_skinning.npz

# generate skin
cfg_data="configs/data/quick_inference.yaml"
cfg_task="configs/task/quick_inference_unirig_skin.yaml"
require_suffix="obj,fbx,FBX,dae,glb,gltf,vrm"
num_runs=1
force_override="false"
faces_target_count=50000
output_dir="results/"
model_name="" # 統一命名規則対応: モデル名パラメータ追加
PYTHON_EXEC="/opt/conda/envs/UniRig/bin/python3"
PIP_EXEC="/opt/conda/envs/UniRig/bin/pip"

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --cfg_data) cfg_data="$2"; shift ;;
        --cfg_task) cfg_task="$2"; shift ;;
        --require_suffix) require_suffix="$2"; shift ;;
        --num_runs) num_runs="$2"; shift ;;
        --force_override) force_override="$2"; shift ;;
        --faces_target_count) faces_target_count="$2"; shift ;;
        --input) input="$2"; shift ;;
        --input_dir) input_dir="$2"; shift ;;
        --output_dir) output_dir="$2"; shift ;;
        --output) output="$2"; shift ;;
        --data_name) data_name="$2"; shift ;;
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

echo "INFO: Generating skinning for model: $model_name"
echo "INFO: Output directory: $output_dir"

# 1. extract mesh
cmd=" \
    bash ./launch/inference/extract.sh \
    --cfg_data $cfg_data \
    --require_suffix $require_suffix \
    --force_override $force_override \
    --num_runs $num_runs \
    --faces_target_count $faces_target_count \
"
if [ -n "$input" ]; then
    cmd="$cmd --input $input"
fi
if [ -n "$input_dir" ]; then
    cmd="$cmd --input_dir $input_dir"
fi
if [ -n "$npz_dir" ]; then
    cmd="$cmd --output_dir $npz_dir"
elif [ -n "$output_dir" ]; then
    cmd="$cmd --output_dir $output_dir"
fi

cmd="$cmd &"
eval $cmd

wait

# 2. 統一スキニング生成処理
echo "INFO: Starting skinning generation with unified naming..."

cmd="\
    python run.py \
    --task=$cfg_task \
    --seed=12345 \
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
if [ -n "$output_dir" ]; then
    cmd="$cmd --output_dir=$output_dir"
fi
if [ -n "$npz_dir" ]; then
    cmd="$cmd --npz_dir=dataset_inference_clean"
elif [ -n "$output_dir" ]; then
    # Use dataset_inference_clean as npz_dir where skeleton files are located
    cmd="$cmd --npz_dir=dataset_inference_clean"
fi
if [ -n "$data_name" ]; then
    cmd="$cmd --data_name=$data_name"
fi

echo "INFO: Executing skinning generation command: $cmd"
eval $cmd

wait

# 統一命名規則確認
echo "INFO: Checking unified naming convention compliance..."
if [ -n "$output_dir" ]; then
    echo "INFO: Expected files in $output_dir:"
    echo "  - ${model_name}_skinned.fbx (skinned model FBX)"
    echo "  - ${model_name}_skinning.npz (skinning data)"
    
    # ファイル存在確認と命名規則統一
    if [ -f "$output_dir/predict_skin.npz" ]; then
        echo "INFO: Found predict_skin.npz - renaming to ${model_name}_skinning.npz"
        mv "$output_dir/predict_skin.npz" "$output_dir/${model_name}_skinning.npz"
    fi
    
    if [ -f "$output_dir/skinned_model.fbx" ]; then
        echo "INFO: Found skinned_model.fbx - renaming to ${model_name}_skinned.fbx"
        mv "$output_dir/skinned_model.fbx" "$output_dir/${model_name}_skinned.fbx"
    fi
    
    if [ -f "$output_dir/result_fbx.fbx" ]; then
        echo "INFO: Found result_fbx.fbx - renaming to ${model_name}_skinned.fbx"
        mv "$output_dir/result_fbx.fbx" "$output_dir/${model_name}_skinned.fbx"
    fi
fi

echo "INFO: Skinning generation completed with unified naming convention"