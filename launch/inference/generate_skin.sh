# generate skin
cfg_data="configs/data/quick_inference.yaml"
cfg_task="configs/task/quick_inference_unirig_skin.yaml"
require_suffix="obj,fbx,FBX,dae,glb,gltf,vrm"
num_runs=1
force_override="false"
faces_target_count=50000
output_dir="results/"
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
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

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

# 2. inference skin
cmd="\
    python run.py \
    --task=$cfg_task \
    --seed=12345 \
"
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

eval $cmd

wait

echo "done"