# UniRig app.py Step0-Step5 データフローマーメイド図

## 📊 app.py 6ステップマイクロサービス構成データフロー

以下は、app.pyで実装されている6ステップパイプラインのデータフロー分析結果です：

```mermaid
graph TB
    %% Upload Flow
    User[👤 ユーザー] --> Upload[📁 ファイルアップロード<br/>bird.glb]
    Upload --> FileManager[📂 FileManager<br/>pipeline_work/{model_name}/]
    
    %% Step 0: Asset Preservation
    FileManager --> Step0[🛡️ Step0: Asset Preservation<br/>step0_asset_preservation.py]
    Step0 --> Step0Dir[📁 00_asset_preservation/<br/>- {model_name}_asset_metadata.json<br/>- {model_name}_asset_metadata_blender.json<br/>- textures/]
    
    %% Step 1: Mesh Extraction  
    Step0Dir --> Step1[🔧 Step1: Mesh Extraction<br/>step1_extract.py]
    Step1 --> Step1Dir[📁 01_extracted_mesh/<br/>- raw_data.npz<br/>- {model_name}.glb (copied)]
    
    %% Step 2: Skeleton Generation
    Step1Dir --> Step2[🦴 Step2: Skeleton Generation<br/>step2_skeleton.py]
    Step2 --> Step2Dir[📁 02_skeleton/<br/>- {model_name}.fbx (NO suffix)<br/>- predict_skeleton.npz (FIXED name)]
    
    %% Step 3: UniRig Skinning
    Step2Dir --> Step3[🎭 Step3: UniRig Skinning<br/>step3_skinning_unirig.py]
    Step3 --> Step3Dir[📁 03_skinning/<br/>- {model_name}_skinned_unirig.fbx<br/>- {model_name}_skinning.npz]
    
    %% Step 4: Skeleton & Skinning Merge
    Step3Dir --> Step4[🔀 Step4: Skeleton & Skinning Merge<br/>step4_merge.py]
    Step4 --> Step4Dir[📁 04_merge/<br/>- {model_name}_merged.fbx]
    
    %% Step 5: Blender Integration
    Step4Dir --> Step5[🎨 Step5: Blender Integration<br/>step5_blender_integration.py]
    Step5 --> Step5Dir[📁 05_blender_integration/<br/>- {model_name}_final.fbx]
    
    %% State Management
    FileManager -.-> State[🗃️ Pipeline State<br/>pipeline_state.json]
    State -.-> FileManager
    
    %% File Key Mapping
    classDef stepBox fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef dirBox fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef fileBox fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
    
    class Step0,Step1,Step2,Step3,Step4,Step5 stepBox
    class Step0Dir,Step1Dir,Step2Dir,Step3Dir,Step4Dir,Step5Dir dirBox
    class Upload,FileManager,State fileBox
```

## 🔄 ステップ間データフロー詳細

### Step0 → Step1
```python
# Step0出力キー
"asset_metadata_json": "00_asset_preservation/{model_name}_asset_metadata.json"

# Step1入力
uploaded_file_path = file_manager.get_uploaded_file_path(original_filename)
# Step1は元ファイルを直接処理、Step0出力は後段で使用
```

### Step1 → Step2  
```python
# Step1出力キー
"extracted_npz": "01_extracted_mesh/raw_data.npz"

# Step2入力
step1_outputs = pipeline_state.get("step1_extract", {}).get("outputs", {})
input_mesh_npz_path = step1_outputs.get("extracted_npz")
```

### Step2 → Step3
```python
# Step2出力キー
"skeleton_fbx": "02_skeleton/{model_name}.fbx"  # NO suffix!
"skeleton_npz": "02_skeleton/predict_skeleton.npz"  # FIXED name!

# Step3入力
step2_outputs = pipeline_state.get("step2_skeleton", {}).get("outputs", {})
skeleton_fbx_path = step2_outputs.get("skeleton_fbx")
skeleton_npz_path = step2_outputs.get("skeleton_npz")
```

### Step3 → Step4
```python
# Step3出力キー
"skinned_fbx": "03_skinning/{model_name}_skinned_unirig.fbx"
"skinning_npz": "03_skinning/{model_name}_skinning.npz"

# Step4入力
step3_outputs = pipeline_state.get("step3_skinning", {}).get("outputs", {})
skinned_fbx = step3_outputs.get("skinned_fbx")
```

### Step4 → Step5
```python
# Step4出力キー
"merged_fbx": "04_merge/{model_name}_merged.fbx"

# Step5入力
step4_outputs = pipeline_state.get("step4_merge", {}).get("outputs", {})
merged_fbx = step4_outputs.get("merged_fbx")
```

### Step5最終出力
```python
# Step5出力キー
"final_fbx": "05_blender_integration/{model_name}_final.fbx"
```

## 🎯 重要な技術的発見

### 1. ファイル命名規則の一貫性
- **Step2出力**: `{model_name}.fbx` (サフィックスなし) + `predict_skeleton.npz` (固定名)
- **Step3出力**: `{model_name}_skinned_unirig.fbx` + `{model_name}_skinning.npz`
- **Step4出力**: `{model_name}_merged.fbx`
- **Step5出力**: `{model_name}_final.fbx`

### 2. pipeline_state.json による状態管理
```python
# FileManager.load_pipeline_state()で各ステップの出力を取得
pipeline_state = {
    "original_filename": "bird.glb",
    "step0_asset_preservation": {"status": "success", "outputs": {...}},
    "step1_extract": {"status": "success", "outputs": {...}},
    "step2_skeleton": {"status": "success", "outputs": {...}},
    "step3_skinning": {"status": "success", "outputs": {...}},
    "step4_merge": {"status": "success", "outputs": {...}},
    "step5_blender_integration": {"status": "success", "outputs": {...}}
}
```

### 3. STEP_SUBDIR_NAMES による統一ディレクトリ管理
```python
STEP_SUBDIR_NAMES = {
    "step0_asset_preservation": "00_asset_preservation",
    "step1_extract": "01_extracted_mesh", 
    "step2_skeleton": "02_skeleton",
    "step3_skinning": "03_skinning",
    "step4_merge": "04_merge",
    "step5_blender_integration": "05_blender_integration",
}
```

### 4. Step間の依存関係
- **Step0**: オプショナル（アセット保存、後段のStep5で使用）
- **Step1**: 必須（全パイプラインの基盤となるメッシュデータ）
- **Step2**: Step1の`raw_data.npz`に依存
- **Step3**: Step1の`raw_data.npz` + Step2の`skeleton_fbx`, `skeleton_npz`に依存
- **Step4**: Step2の`skeleton_fbx` + Step3の`skinned_fbx`に依存（スケルトン・スキンウェイトマージ）
- **Step5**: Step0の`asset_metadata_json` + Step4の`merged_fbx`に依存（テクスチャ統合）

## 🚨 重要な修正確認事項

### Step4の責務修正確認済み
- **修正前**: テクスチャ統合
- **修正後**: スケルトン・スキンウェイトマージ（src.inference.merge使用）
- **Step5で実行**: テクスチャ統合（Blender使用）

### 修正済みインストラクションファイル
- ✅ `/app/.github/DATAFLOW_REFACTORING_GUIDE.instructions.md`
- ✅ `/app/.github/microservice_guide.instructions.md`
- ✅ `/app/MICROSERVICE_GUIDE.md`
- ✅ `/app/copilot-instructions_ja.md`

---

**2025年1月24日作成** - app.pyデータフロー分析完了
