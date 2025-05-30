#!/bin/bash
set -x # Enable command tracing
# set -e # Disable exit on error to handle expected segfault gracefully

# extract mesh
cfg_data="configs/data/quick_inference.yaml" # Default value
cfg_task="configs/task/quick_inference_unirig_skin.yaml" # Default value
require_suffix="obj,fbx,FBX,dae,glb,gltf,vrm"
num_runs=1
force_override="false"
faces_target_count=50000
output_dir="results/" # Default output directory changed to results/

PYTHON_EXEC="/opt/conda/envs/UniRig/bin/python3"
PIP_EXEC="/opt/conda/envs/UniRig/bin/pip"

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --cfg_data|-c) cfg_data="$2"; shift; shift ;;
        --cfg_task|-t) cfg_task="$2"; shift; shift ;;
        --require_suffix) require_suffix="$2"; shift; shift ;;
        --num_runs) num_runs="$2"; shift; shift ;;
        --force_override) force_override="$2"; shift; shift ;;
        --faces_target_count) faces_target_count="$2"; shift; shift ;;
        --time) time="$2"; shift; shift ;;
        --input|-i) input="$2"; shift; shift ;;
        --input_dir) input_dir="$2"; shift; shift ;;
        --output_dir|-o) output_dir="$2"; shift; shift ;;
        -*) echo "Unknown parameter: $1"; exit 1 ;;
        *) # If no flag prefix, assume it's the input file
           if [[ -z "$input" ]]; then
               input="$1"
           else
               echo "Unknown parameter: $1"; exit 1
           fi
           shift ;;
    esac
done

# Create output directory if it doesn't exist
if [ -n "$output_dir" ] && [ ! -d "$output_dir" ]; then
    echo "DEBUG: Output directory $output_dir does not exist. Creating it."
    mkdir -p "$output_dir"
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create output directory $output_dir"
        exit 1
    fi
fi

# ensure psutil is installed for memory management
echo "DEBUG: Attempting to install psutil using $PIP_EXEC"
"$PIP_EXEC" install psutil --quiet
if [ $? -ne 0 ]; then
    echo "Warning: Failed to install psutil using $PIP_EXEC. Memory management may not work properly."
fi

# Check for Python executable
echo "DEBUG: Checking for Python executable at $PYTHON_EXEC"
if [ ! -f "$PYTHON_EXEC" ]; then
    echo "ERROR: Python executable NOT FOUND at $PYTHON_EXEC"
    exit 1
elif [ ! -x "$PYTHON_EXEC" ]; then
    echo "ERROR: Python executable IS NOT EXECUTABLE at $PYTHON_EXEC"
    ls -l "$PYTHON_EXEC"
    exit 1
else
    echo "DEBUG: Python executable found and is executable: $PYTHON_EXEC"
fi

# set the time for all processes to use
time=$(date "+%Y_%m_%d_%H_%M_%S")

for (( i=0; i<num_runs; i++ ))
do
    # Build the command and arguments in an array
    command_args=()
    command_args+=("$PYTHON_EXEC")
    command_args+=("-m")
    command_args+=("src.data.extract")
    command_args+=("--cfg_data=$cfg_data")
    command_args+=("--cfg_task=$cfg_task")
    command_args+=("--require_suffix=$require_suffix")
    command_args+=("--force_override=$force_override")
    command_args+=("--num_runs=$num_runs")
    command_args+=("--id=$i")
    command_args+=("--time=$time")
    command_args+=("--faces_target_count=$faces_target_count")

    if [ -n "$input" ]; then
        command_args+=("--input=$input")
    fi
    if [ -n "$input_dir" ]; then
        command_args+=("--input_dir=$input_dir")
    fi
    if [ -n "$output_dir" ]; then
        command_args+=("--output_dir=$output_dir")
    fi

    # Execute the command in the background and get PID
    echo "DEBUG: Executing command: ${command_args[*]}" # Print the command for debugging
    "${command_args[@]}" &
    PYTHON_PID=$!
    echo "DEBUG: Python process started with PID: $PYTHON_PID"
done

echo "DEBUG: Waiting for all background Python processes to complete..."
# Use wait with explicit error handling
for job in $(jobs -p); do
    echo "DEBUG: Waiting for job $job"
    if wait $job; then
        echo "DEBUG: Job $job completed successfully"
    else
        exit_code=$?
        if [ $exit_code -eq 139 ]; then
            echo "DEBUG: Job $job terminated with segmentation fault (exit code 139), but this is expected with Blender cleanup"
        else
            echo "ERROR: Job $job failed with exit code $exit_code"
            exit $exit_code
        fi
    fi
done

echo "All Python jobs completed (ignoring expected Blender segfault)."

# Check if any Python processes are still running
echo "DEBUG: Checking for remaining Python processes..."
if ps -p $PYTHON_PID > /dev/null 2>&1; then
    echo "DEBUG: Python process $PYTHON_PID is still running"
else
    echo "DEBUG: Python process $PYTHON_PID has terminated"
fi

# Optional: Add a small delay to see if it helps with resource cleanup
# sleep 2 # Let's keep this commented for now to see if set -x gives more info

echo "done"