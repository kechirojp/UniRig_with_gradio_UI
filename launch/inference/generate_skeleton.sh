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
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

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

# 2. inference skeleton
cmd="\
    python run.py \
    --task=$skeleton_task \
    --seed=$seed \
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
if [ -n "$npz_dir" ]; then
    cmd="$cmd --npz_dir=$npz_dir --output_dir=$npz_dir"
fi
if [ -n "$output_dir" ] && [ -z "$npz_dir" ]; then
    cmd="$cmd --output_dir=$output_dir"
fi

eval $cmd

wait

echo "done"