## Step3 データ要件分析結果

### 🔍 原流処理 vs Step3実装の比較

#### 原流処理（generate_skin.sh）の要件:
```bash
# 1. extract.sh でメッシュ抽出 (Step1で対応済み)
bash ./launch/inference/extract.sh --input $input --output_dir $npz_dir

# 2. UniRig run.py実行
python run.py \
    --task=configs/task/quick_inference_unirig_skin.yaml \
    --npz_dir=dataset_inference_clean \
    --output_dir=results \
    --data_name=raw_data \
    --seed=12345
```

#### Step3実装の対応状況:
```python
# ✅ メッシュデータ: Step1のraw_data.npzを使用
target_mesh_npz = unirig_model_processing_dir / "raw_data.npz"
shutil.copy2(source_mesh_npz, target_mesh_npz)

# ✅ スケルトンデータ: Step2のpredict_skeleton.npzを使用  
target_skeleton_npz = unirig_model_processing_dir / "predict_skeleton.npz"
shutil.copy2(source_skeleton_npz, target_skeleton_npz)

# ✅ UniRig実行コマンド: 原流処理と同等
cmd = [
    "/opt/conda/envs/UniRig/bin/python", 
    "/app/run.py",
    "--task=configs/task/quick_inference_unirig_skin.yaml",
    "--data_name=raw_data",
    "--npz_dir=/app/dataset_inference_clean",
    "--output_dir=/app/results",
    "--seed=12345"
]
```

### ✅ 結論: Step3は原流処理の要件を完全に満たしている

**受け取るデータ:**
1. **メッシュNPZ**: `raw_data.npz` (Step1出力)
2. **スケルトンFBX**: `{model_name}.fbx` (Step2出力)  
3. **スケルトンNPZ**: `predict_skeleton.npz` (Step2出力)

**データ配置:**
- `/app/dataset_inference_clean/{model_name}/` にファイル配置
- 原流処理が期待する構造と一致

**実行環境:**
- 同じPythonパス、同じconfigファイル使用
- 環境変数の適切な管理
- timeout設定による安全な実行

**出力:**
- 原流処理と同じ出力先（`/app/results/`）
- configで定義されたファイル命名規則に従って出力
