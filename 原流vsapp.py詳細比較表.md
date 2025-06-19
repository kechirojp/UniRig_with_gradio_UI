# 原流シェルスクリプト vs app.py 詳細比較分析

## 1. ディレクトリ・ファイル構造比較

### 原流シェルスクリプト方式
```
データフロー:
input_file → tmp/ (extract) → dataset_inference_clean/ (skeleton/skin) → results/ (merge)

Step1 (extract.sh):
├── 入力: --input bird.glb
├── 出力ディレクトリ: results/ または --output_dir指定
├── NPZファイル: raw_data.npz
└── 実行: python -m src.data.extract

Step2 (generate_skeleton.sh):
├── 入力: raw_data.npz (tmp/から)
├── 出力ディレクトリ: --output_dir指定
├── NPZファイル: predict_skeleton.npz → {model_name}_skeleton.npz (リネーム)
├── FBXファイル: skeleton_model.fbx → {model_name}_skeleton.fbx (リネーム)
└── 実行: python run.py --task=configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml

Step3 (generate_skin.sh):
├── 前処理: bash ./launch/inference/extract.sh (再実行)
├── 入力: raw_data.npz + skeleton files from dataset_inference_clean
├── 出力ディレクトリ: --output_dir指定
├── NPZファイル: predict_skin.npz → {model_name}_skinning.npz (リネーム)
├── FBXファイル: result_fbx.fbx → {model_name}_skinned.fbx (リネーム)
└── 実行: python run.py --task=configs/task/quick_inference_unirig_skin.yaml

Step4 (merge.sh):
├── 入力: --source (skeleton) --target (skinned)
├── 出力: --output指定パス
├── ファイル: {model_name}_merged.fbx
└── 実行: python -m src.inference.merge
```

### app.py方式 (マイクロサービス風)  
```
決め打ちディレクトリ戦略:
/app/pipeline_work/{model_name}/01_extracted_mesh/raw_data.npz
/app/pipeline_work/{model_name}/02_skeleton/{model_name}_skeleton.fbx
/app/pipeline_work/{model_name}/03_skinning/{model_name}_skinned.fbx
/app/pipeline_work/{model_name}/04_merge/{model_name}_merged.fbx
/app/pipeline_work/{model_name}/05_blender_integration/{model_name}_final.fbx

Step1:
├── ステート管理: FixedDirectoryManager
├── 出力: /app/pipeline_work/{model_name}/01_extracted_mesh/
├── NPZファイル: raw_data.npz
└── 実行: python -m src.data.extract

Step2:
├── ステート管理: FixedDirectoryManager
├── 入力: Step1の raw_data.npz
├── 出力: /app/pipeline_work/{model_name}/02_skeleton/
├── NPZファイル: predict_skeleton.npz → そのまま使用
├── FBXファイル: {model_name}_skeleton.fbx (コピー)
└── 実行: python run.py --task=configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml
```

## 2. データフロー比較

### 重要な違い: NPZディレクトリ戦略

#### 原流方式
```bash
# Step2: スケルトン生成
--npz_dir tmp → dataset_inference_clean にNPZデータ蓄積
# Step3: スキニング生成  
--npz_dir dataset_inference_clean から skeleton データ読み込み
```

#### app.py方式
```python
# Step2: 
input_data_path = step1_output_dir / "raw_data.npz"
# Step3:
skeleton_npz = step2_output_dir / "predict_skeleton.npz"  # 決め打ち固定パス
```

### Critical Issue: NPZ参照方式の違い

**原流**: dataset_inference_clean を共有ストレージとして使用
**app.py**: 各ステップのディレクトリから直接参照

## 3. 設定ファイル利用比較

### 原流方式のconfig利用
```bash
# Step1
python -m src.data.extract --cfg_data=configs/data/quick_inference.yaml --cfg_task=configs/task/quick_inference_unirig_skin.yaml

# Step2  
python run.py --task=configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml

# Step3
python run.py --task=configs/task/quick_inference_unirig_skin.yaml
```

### app.py方式のconfig利用
```python
# Step1: 直接パラメータ指定、--cfg_task は使用しない
cmd = [python_path, "-m", "src.data.extract", "--cfg_data=configs/data/quick_inference.yaml"]

# Step2/Step3: taskファイル直接指定
task_config = "configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml"
```

## 4. プロセス実行パターン比較

### 原流方式
```bash
# バックグラウンド実行 + wait
"${command_args[@]}" &
PYTHON_PID=$!
wait $job
```

### app.py方式
```python  
# subprocess.run同期実行
result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
```

## 5. ★★★ 決定的違い: スケルトンファイル参照方式 ★★★

### 原流方式 (正常動作)
```bash
# Step3でdataset_inference_cleanからskeletonファイル読み込み
--npz_dir=dataset_inference_clean  # skelton files location
```

### app.py方式 (問題発生源)
```python
# Step3でStep2の出力ディレクトリから直接読み込み
skeleton_npz = step2_output_dir / "predict_skeleton.npz"
```

**Critical Problem**: `dataset_inference_clean`を使わないため、スケルトンデータの共有ができていない可能性

## 6. バーテックスグループ問題の根本原因予測

### 原流方式での正常な処理フロー
1. **extract.sh**: raw_data.npz生成
2. **generate_skeleton.sh**: extract再実行 + skeleton生成 → dataset_inference_clean保存
3. **generate_skin.sh**: extract再実行 + dataset_inference_cleanからskeleton読み込み + skinning適用
4. **merge.sh**: skeleton + skinned → merged

### app.py方式での問題フロー
1. **Step1**: raw_data.npz生成 (pipeline_work保存)
2. **Step2**: skeleton生成 (pipeline_work保存、dataset_inference_clean使用せず)
3. **Step3**: Step2出力から直接読み込み (dataset_inference_clean使用せず)
4. **問題**: スケルトンとメッシュの関連付けが不完全

## 7. 修正方針

### 1. dataset_inference_clean統合戦略
```python
# Step2/Step3でdataset_inference_cleanを使用するよう修正
dataset_inference_dir = Path("/app/dataset_inference_clean")
```

### 2. NPZ参照パス統一
```python
# 原流方式と同様のNPZ参照パターンに修正
skeleton_npz = dataset_inference_dir / "predict_skeleton.npz"
```

### 3. extract再実行対応
```python
# Step3でextract再実行ロジック追加（原流方式準拠）
```
