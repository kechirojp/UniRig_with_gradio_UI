# configs以下ファイルとデータフロー不整合分析報告書

## 🚨 重大な不整合発見

### 1. **ディレクトリ構造の不整合** ❌

#### configs/app_config.yaml vs 現在の実装

**❌ 問題**: `app_config.yaml`で定義されたディレクトリ構造が、データフロー仕様書および現在の`app.py`実装と完全に不一致

**configs/app_config.yaml 定義**:
```yaml
mesh_extraction:
  extract_output_subdir: "01_extracted_mesh"  # ✅ 一致
  
skeleton_generation:
  skeleton_output_subdir: "02_skeleton_output"  # ❌ 不整合
  
skinning_prediction:
  skin_output_subdir: "03_skinning_output"  # ❌ 不整合
  
model_merging:
  merge_output_subdir: "04_final_rigged_model"  # ❌ 不整合
```

**データフロー仕様書 (`app_dataflow.instructions.md`) 定義**:
```python
STEP_SUBDIR_NAMES = {
    "step0_asset_preservation": "00_asset_preservation",
    "step1_extract": "01_extracted_mesh", 
    "step2_skeleton": "02_skeleton",        # ❌ != "02_skeleton_output"
    "step3_skinning": "03_skinning",        # ❌ != "03_skinning_output"
    "step4_merge": "04_merge",              # ❌ != "04_final_rigged_model"
    "step5_blender_integration": "05_blender_integration",
}
```

**現在のapp.py実装**:
```python
STEP_SUBDIR_NAMES = {
    "step0_asset_preservation": "00_asset_preservation",
    "step1_extract": "01_extracted_mesh",
    "step2_skeleton": "02_skeleton",        # ✅ データフロー仕様書と一致
    "step3_skinning": "03_skinning",        # ✅ データフロー仕様書と一致
    "step4_merge": "04_merge",              # ✅ データフロー仕様書と一致
    "step5_blender_integration": "05_blender_integration",
}
```

### 2. **ファイル命名規則の不整合** ❌

#### configs/app_config.yaml vs データフロー仕様書

**configs/app_config.yaml 定義**:
```yaml
mesh_extraction:
  output_npz_filename: "{model_name}_raw_data.npz"  # ❌ 不整合

skeleton_generation:
  output_npz_filename: "predict_skeleton.npz"       # ✅ 一致
  output_fbx_filename: "skeleton.fbx"               # ❌ 不整合
  
skinning_prediction:
  output_skinned_fbx_filename: "skinned_model.fbx"  # ❌ 不整合
  output_skinning_npz_filename: "predict_skin.npz"  # ❌ 不整合
```

**データフロー仕様書 (`app_dataflow.instructions.md`) 定義**:
```python
# 原流処理互換性のための固定名
FIXED_FILENAMES = {
    "step1_output_npz": "raw_data.npz",              # ❌ != "{model_name}_raw_data.npz"
    "step2_skeleton_npz": "predict_skeleton.npz",    # ✅ 一致
    "step2_skeleton_fbx": "{model_name}.fbx",        # ❌ != "skeleton.fbx"
}

# ステップごとの命名パターン
- Step2出力: `{model_name}.fbx` (サフィックスなし) + `predict_skeleton.npz` (固定名)
- Step3出力: `{model_name}_skinned_unirig.fbx` + `{model_name}_skinning.npz`  # ❌ configsと不一致
```

### 3. **欠落している設定項目** ❌

**app_config.yaml で欠落している設定**:
- Step0 (Asset Preservation) の設定が完全に欠落
- Step5 (Blender Integration) の設定が完全に欠落
- 6ステップ構成への対応が不完全

### 4. **タスク設定ファイルの分析** ⚠️

#### configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml
```yaml
components:
  data_name: raw_data.npz  # ✅ データフロー仕様書と一致

writer:
  export_npz: predict_skeleton    # ✅ "predict_skeleton.npz"と一致
  export_fbx: skeleton           # ❌ "{model_name}.fbx"と不一致
```

#### configs/task/quick_inference_unirig_skin.yaml
```yaml
components:
  data_name: predict_skeleton.npz  # ✅ データフロー仕様書と一致

writer:
  export_npz: predict_skin        # ❌ "{model_name}_skinning.npz"と不一致
  export_fbx: result_fbx          # ❌ "{model_name}_skinned_unirig.fbx"と不一致
```

### 5. **データファイルパス設定の不整合** ❌

#### configs/data/quick_inference.yaml
```yaml
input_dataset_dir: ./dataset_inference
output_dataset_dir: ./dataset_inference_clean

datapath_config:
  input_dataset_dir: *output_dataset_dir  # ✅ 原流処理との一致確認済み
```

**問題点**:
- ハードコードされたパス使用
- 動的なモデル名対応ディレクトリ (`/app/pipeline_work/{model_name}/`) への対応なし

## 🛠️ 修正が必要な項目

### 優先度1: 重大な不整合（即座に修正必要）

1. **configs/app_config.yaml のディレクトリ構造統一**
   ```yaml
   # 修正前 → 修正後
   skeleton_output_subdir: "02_skeleton_output" → "02_skeleton"
   skin_output_subdir: "03_skinning_output" → "03_skinning" 
   merge_output_subdir: "04_final_rigged_model" → "04_merge"
   ```

2. **configs/app_config.yaml のファイル命名規則統一**
   ```yaml
   # 修正前 → 修正後
   output_npz_filename: "{model_name}_raw_data.npz" → "raw_data.npz"
   output_fbx_filename: "skeleton.fbx" → "{model_name}.fbx"
   output_skinned_fbx_filename: "skinned_model.fbx" → "{model_name}_skinned_uririg.fbx"
   ```

3. **欠落設定項目の追加**
   - Step0 (Asset Preservation) 設定追加
   - Step5 (Blender Integration) 設定追加

### 優先度2: 原流処理互換性確保

1. **タスク設定ファイルの出力名統一**
   - `configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml`
   - `configs/task/quick_inference_unirig_skin.yaml`

### 優先度3: 動的パス対応

1. **configs/data/quick_inference.yaml の動的パス対応検討**

## 📊 影響分析

### 現在のシステム動作への影響

**✅ 現在動作している理由**:
- `app.py`が `STEP_SUBDIR_NAMES` でハードコードされた正しいディレクトリ構造を使用
- データフロー仕様書との一致により、ステップモジュール間の連携は正常

**⚠️ 潜在的リスク**:
- 設定ファイル変更時の混乱
- 新規開発者の設定理解困難
- 設定の一元管理の破綻

## 🎯 推奨対応策

### 1. 緊急対応（即座実行）
1. `configs/app_config.yaml` をデータフロー仕様書に合わせて修正
2. 設定統一性確認テストスクリプト作成

### 2. 中期対応（次回開発時）
1. 設定ファイル読み込み機能の`app.py`への統合
2. 動的パス生成システムの実装

### 3. 長期対応（安定性確保）
1. 設定ファイル変更時の自動テスト仕組み構築
2. Single Source of Truth原則の徹底

## 📋 検証方法

### 修正後の確認項目
1. ディレクトリ構造の一致確認
2. ファイル命名規則の一致確認  
3. パイプライン全体の動作確認
4. 原流処理との互換性確認

---

**📅 分析日**: 2025年6月12日  
**🎯 結論**: configs設定ファイルとデータフロー仕様書との間に重大な不整合が複数存在。即座の修正が必要。
