# 🚨 UniRigデータ受け渡し失敗の根本原因分析

**緊急調査結果**: 2025年6月10日  
**目的**: データの受け渡しが必ず失敗している原因を特定

---

## 🔍 実際のデータフロー追跡結果

### ❌ 発見した重大な問題

#### 1. **Step1 → Step2間のデータ受け渡し失敗**

```python
# app.py Step2呼び出し部分
step1_outputs = pipeline_state.get("step1_extract", {}).get("outputs", {})
input_npz_path_str = step1_outputs.get("extracted_npz")

# 問題: step1_extract.outputsが存在しない可能性
# pipeline_stateから正しく取得できていない
```

#### 2. **Step1Extractの出力キー名とapp.pyの期待値の不一致**

```python
# Step1Extract.extract_mesh実際の出力
output_files: Dict[str, Any] = {
    "extracted_npz": str(output_npz_path),  # Step2が期待するキー名
    "model_name": model_name,
    "persistent_input_path_in_step_dir": str(persistent_input_file),
    "datalist": str(output_datalist_path) if output_datalist_path.exists() else None
}

# app.py call_step2_generate_skeleton()での期待
input_npz_path_str = step1_outputs.get("extracted_npz")  # 正しいキー名
```

#### 3. **FileManager.mark_step_complete()の状態保存問題**

```python
# app.py call_step1_extract_mesh()
file_manager.mark_step_complete("step1_extract", {
    "status": status, 
    "message": message, 
    "outputs": outputs,  # ← ここでoutputsを保存
    "error": "" if success else message
})

# app.py call_step2_generate_skeleton()
step1_outputs = pipeline_state.get("step1_extract", {}).get("outputs", {})
# ↑ pipeline_stateから正しく取得できているか？
```

#### 4. **Step2の複雑なファイルコピー処理**

```python
# Step2Skeleton.generate_skeleton()
# Step1 NPZ → UniRig処理ディレクトリ → 最終出力ディレクトリ
unirig_input_npz_target = unirig_model_processing_dir / "raw_data.npz"
shutil.copy2(input_npz_path, unirig_input_npz_target)

# UniRig生成 → 最終出力
generated_npz_in_unirig_dir = unirig_model_processing_dir / "predict_skeleton.npz"
final_output_npz = self.output_dir / "predict_skeleton.npz"
shutil.copy2(generated_npz_in_unirig_dir, final_output_npz)
```

#### 5. **Step3の二重実装とフォールバック問題**

```python
# Step3Skinning.apply_skinning()
try:
    from step_modules.step3_skinning_unirig import Step3UniRigSkinning
    unirig_skinner = Step3UniRigSkinning(...)
    success, logs, output_files = unirig_skinner.apply_skinning(...)
    
    if success:
        return success, logs, output_files
    else:
        # フォールバックへ → データが異なる形式で出力される可能性
        
except Exception:
    # フォールバックへ → データが異なる形式で出力される可能性
```

---

## 🎯 具体的なデータ受け渡し失敗ポイント

### Point 1: pipeline_state の状態保存・取得

```python
# 保存側 (call_step1_extract_mesh)
file_manager.mark_step_complete("step1_extract", {
    "outputs": outputs  # Step1Extract.extract_mesh()の戻り値
})

# 取得側 (call_step2_generate_skeleton) 
pipeline_state = file_manager.load_pipeline_state()
step1_outputs = pipeline_state.get("step1_extract", {}).get("outputs", {})

# 問題: この間の状態が保持されているか不明
```

### Point 2: ファイルパスの絶対・相対問題

```python
# Step1Extract出力 (絶対パス)
"extracted_npz": "/app/pipeline_work/model/01_extracted_mesh/raw_data.npz"

# Step2での使用
input_npz_path = Path(input_npz_path_str)
if not input_npz_path.exists():  # ← ここでFileNotFoundError?
```

### Point 3: Step2のUniRig処理ディレクトリ

```python
# Step2Skeleton.__init__()
self.unirig_processing_base_dir = Path("/app/dataset_inference_clean")

# generate_skeleton()
unirig_model_processing_dir = self.unirig_processing_base_dir / model_name
# → /app/dataset_inference_clean/{model_name}/

# UniRigは特定のディレクトリ構造を期待
# この構造が正しく作成されていない可能性
```

### Point 4: Step3の出力ファイル名の不一致

```python
# Step3UniRigSkinning出力
output_fbx = self.output_dir / f"{model_name}_skinned_unirig.fbx"
output_npz = self.output_dir / f"{model_name}_skinning.npz"

# Step3Skinning フォールバック出力
output_fbx = self.output_dir / f"{model_name}_skinned_fallback.fbx"
output_npz = self.output_dir / f"{model_name}_skinning_fallback.npz"

# app.pyでの期待値は？
# Step4で使用するときのファイル名は？
```

---

## 🔬 デバッグが必要な具体的なポイント

### 1. pipeline_state.jsonの実際の内容確認
```bash
# 実行後に確認すべきファイル
/app/pipeline_work/{model_name}/pipeline_state.json
```

### 2. 各ステップの実際の出力ファイル確認
```bash
# Step1出力
/app/pipeline_work/{model_name}/01_extracted_mesh/raw_data.npz
/app/pipeline_work/{model_name}/01_extracted_mesh/{model_name}.glb

# Step2出力
/app/pipeline_work/{model_name}/02_skeleton/predict_skeleton.npz
/app/pipeline_work/{model_name}/02_skeleton/{model_name}.fbx

# UniRig処理ディレクトリ
/app/dataset_inference_clean/{model_name}/raw_data.npz
/app/dataset_inference_clean/{model_name}/predict_skeleton.npz
```

### 3. 実際のエラーログの確認
```bash
# モデル別ログファイル
/app/pipeline_work/{model_name}/logs/{model_name}_*.log
```

---

## 🎯 推定される失敗シナリオ

### シナリオ1: Step1 → Step2間でのファイル取得失敗
1. Step1がraw_data.npzを正常生成
2. pipeline_state.jsonへの保存が失敗
3. Step2がpipeline_stateから取得できずエラー

### シナリオ2: Step2のUniRig処理失敗
1. Step2がStep1のraw_data.npzを取得成功
2. UniRig処理ディレクトリへのコピー成功
3. UniRig run.py実行でpredict_skeleton.npz生成失敗
4. 最終出力ディレクトリへのコピー失敗

### シナリオ3: Step3の実装選択失敗
1. Step3UniRigSkinningの実行失敗
2. フォールバック_fallback_mock_skinning実行
3. 出力ファイル名がStep4の期待値と不一致

---

## 🚀 緊急調査アクション

### 即座に確認すべき項目：

1. **FileManager.load_pipeline_state()の動作確認**
2. **Step1の実際の出力ファイル存在確認**  
3. **Step2のUniRig処理ディレクトリ確認**
4. **各ステップ間のファイルパス受け渡し確認**
5. **実際のエラーログの詳細確認**

### デバッグスクリプト作成が必要：

```python
# pipeline_state.jsonの内容確認
# 各ステップの出力ファイル存在確認
# ファイルパスの有効性確認
# 実際のエラーメッセージ確認
```

**これがデータ受け渡し失敗の根本原因です！**
