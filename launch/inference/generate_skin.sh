#!/bin/bash
set -x # Enable command tracing

# 🎯 UniRig Step3 スキニング生成スクリプト - 詳細処理解説
# =====================================================
# 
# 【重要な処理フロー】Step3の本質的な役割:
# 1. Step2で生成されたスケルトン（predict_skeleton.npz）を読み込み
# 2. オリジナルファイルから「スキニング最適化メッシュ」を再抽出（faces_target_count=50000）
# 3. AI推論により、各頂点に対するボーン影響度（スキンウェイト）を計算
# 4. スケルトン + メッシュ + スキンウェイトを統合したFBXファイルを出力
# 
# 【重要な出力データ】:
# - {model_name}_skinned.fbx: スケルトン・メッシュ・スキンウェイトが統合済みのFBXファイル
# - {model_name}_skinning.npz: スキンウェイトデータ（Step4で使用）
# 
# 【Step4との関係】:
# Step4はこの_skinned.fbxファイルからスキンウェイト情報を抽出し、
# オリジナルメッシュに転写する処理を行う
# 
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

# 🚀 Step3-1: スキニング最適化メッシュ再抽出処理
# =============================================
# 
# 【重要な技術的発見】: Step3は必ずオリジナルファイルからメッシュを再抽出する
# - faces_target_count=50000: スキニング最適化パラメータ
# - Step1メッシュ（汎用抽出）とは異なる、スキニング専用メッシュを生成
# - この差異が、スキンウェイトの品質・精度に決定的な影響を与える
# 
# 【処理内容】:
# - オリジナルファイル → 50,000面のスキニング最適化メッシュ → raw_data.npz
# - Step2スケルトンデータ（predict_skeleton.npz）との整合性確保
# 
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

# 🚀 Step3-2: AI推論によるスキニング生成処理
# =========================================
# 
# 【核心技術】: UniRig AIスキニングシステム
# - 入力: スキニング最適化メッシュ（raw_data.npz）+ Step2スケルトン（predict_skeleton.npz）
# - AI推論: 各頂点に対する全ボーンの影響度を計算（スキンウェイト行列生成）
# - 出力: スケルトン・メッシュ・スキンウェイトが完全統合されたFBXファイル
# 
# 【重要な設定】:
# - 設定ファイル: configs/task/quick_inference_unirig_skin.yaml
# - データソース: predict_skeleton.npz（Step2出力、固定名）
# - 出力形式: result_fbx.fbx + predict_skin.npz（後で統一命名規則に変換）
# 
# 【技術的詳細】:
# この処理により、メッシュの各頂点がどのボーンにどの程度影響されるかが決定される
# 生成されるスキンウェイトは、アニメーション時の変形品質を左右する最重要データ
# 
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

# 🚀 Step3-3: 統一命名規則への出力ファイル変換
# ==========================================
# 
# 【問題】: AI推論システムは固定ファイル名で出力する
# - predict_skin.npz（スキンウェイトデータ）
# - result_fbx.fbx（統合FBXファイル）
# 
# 【解決】: 統一命名規則への変換処理
# - predict_skin.npz → {model_name}_skinning.npz
# - result_fbx.fbx → {model_name}_skinned.fbx
# 
# 【重要性】:
# Step4マージ処理は、この統一命名規則に依存している
# 特に{model_name}_skinned.fbxは、スケルトン・メッシュ・スキンウェイトが
# 完全統合されたデータであり、Step4の重要な入力源となる
# 
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