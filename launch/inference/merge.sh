#!/bin/bash
set -x # Enable command tracing

# 🎯 統一マージスクリプト - ユーザー中心設計対応
# 統一命名規則: {model_name}_merged.fbx (スケルトン+スキニング統合済み)

# merge texture and rigging components
require_suffix="obj,fbx,FBX,dae,glb,gltf,vrm"
source=""
target=""
output=""
model_name="" # 統一命名規則対応: モデル名パラメータ追加

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --require_suffix) require_suffix="$2"; shift ;;
        --source) source="$2"; shift ;;
        --target) target="$2"; shift ;;
        --output) output="$2"; shift ;;
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

echo "INFO: Merging components for model: $model_name"
echo "INFO: Source (skeleton): $source"
echo "INFO: Target (skinned): $target"
echo "INFO: Output path: $output"

# 統一マージコマンド実行
cmd=" \
    python -m src.inference.merge \
    --require_suffix=$require_suffix \
    --num_runs=1 \
    --id=0 \
    --source=$source \
    --target=$target \
    --output=$output \
    --model_name=$model_name \
"

echo "INFO: Executing merge command: $cmd"
cmd="$cmd &"
eval $cmd

wait

# 統一命名規則確認
if [ -f "$output" ]; then
    echo "INFO: Merge completed successfully"
    echo "INFO: Generated unified merged file: $output"
    
    # ファイル名が統一規則に準拠しているか確認
    expected_name="${model_name}_merged.fbx"
    if [[ "$output" != *"$expected_name" ]]; then
        echo "WARNING: Output filename does not follow unified naming convention"
        echo "Expected: $expected_name"
        echo "Actual: $output"
        
        # 統一命名規則準拠への修正（オプション）
        output_dir=$(dirname "$output")
        unified_output="$output_dir/$expected_name"
        if [ "$output" != "$unified_output" ]; then
            echo "INFO: Renaming to unified convention: $unified_output"
            mv "$output" "$unified_output"
        fi
    fi
else
    echo "ERROR: Merge failed - output file not found: $output"
    exit 1
fi

echo "INFO: Merge process completed with unified naming convention"