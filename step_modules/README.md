# step_modules - UniRig統合後の構成

## 🎯 統合状況 (2025年6月14日)

### ✅ 統合完了・アーカイブ済み
以下のファイルは`src/pipeline`に統合されたため、`step_modules_archive/legacy_implementations/`に移動されました：

- **step1_extract.py** → `src/pipeline/unified_extract.py`
- **step2_skeleton.py** → `src/pipeline/unified_skeleton.py` 
- **step3_skinning_unirig.py** → `src/pipeline/unified_skinning.py`
- **step4_merge.py** → `src/pipeline/unified_merge.py`
- **step5_*.py** → `src/pipeline/unified_blender.py`

### 🔄 継続使用中
- **step0_asset_preservation.py** - アセット保存機能（Step0専用）

## 📋 使用方法

### Step0 (アセット保存)
```python
from step_modules.step0_asset_preservation import Step0AssetPreservation

step0 = Step0AssetPreservation(model_name, input_file, output_dir, logger)
success, logs, files = step0.preserve_assets()
```

### Step1-5 (統合オーケストレーター)
```python
from src.pipeline.unified_extract import UnifiedExtractor
from src.pipeline.unified_skeleton import UnifiedSkeletonOrchestrator
from src.pipeline.unified_skinning import UnifiedSkinningOrchestrator
from src.pipeline.unified_merge import UnifiedMergeOrchestrator
from src.pipeline.unified_blender import UnifiedBlenderOrchestrator

# Step1: メッシュ抽出
extractor = UnifiedExtractor(logger)
success, logs = extractor.extract_mesh_unified(input_file, model_name, output_dir)

# Step2: スケルトン生成
skeleton_orch = UnifiedSkeletonOrchestrator(logger)
success, logs = skeleton_orch.generate_skeleton_unified(model_name, gender, extracted_file, output_dir)

# Step3: スキニング適用
skinning_orch = UnifiedSkinningOrchestrator(logger)
success, logs = skinning_orch.apply_skinning_unified(model_name, mesh_file, skeleton_file, output_dir)

# Step4: マージ処理
merge_orch = UnifiedMergeOrchestrator(logger)
success, logs = merge_orch.merge_skeleton_skinning_unified(model_name, skeleton_fbx, skinned_fbx, output_dir)

# Step5: Blender統合
blender_orch = UnifiedBlenderOrchestrator(logger)
success, logs = blender_orch.integrate_with_blender_unified(model_name, original_file, merged_file, output_dir)
```

## 🚨 重要な変更点

### 1. インポート変更
```python
# ❌ 旧方式 (非推奨)
from step_modules.step1_extract import Step1Extract

# ✅ 新方式 (推奨)
from src.pipeline.unified_extract import UnifiedExtractor
```

### 2. メソッド名変更
```python
# ❌ 旧方式
step1.extract_mesh()

# ✅ 新方式
extractor.extract_mesh_unified()
```

### 3. 決め打ちディレクトリ戦略
```python
# ✅ 推奨: FixedDirectoryManager使用
from fixed_directory_manager import FixedDirectoryManager
fdm = FixedDirectoryManager(base_dir, model_name, logger)
output_dir = fdm.get_step_dir('step1')
```

## 📊 統合メリット

1. **コード重複排除**: 単一実装による一貫性確保
2. **保守性向上**: 変更箇所の明確化
3. **実行安定性**: 原流処理100%互換性
4. **エラー処理統一**: PipelineErrorAnalyzerによる一元管理

## 🔗 関連ドキュメント

- [app_改修ポイント整理_2025_06_14.md](../app_改修ポイント整理_2025_06_14.md) - 改修詳細
- [step_modules統合レポート_2025_06_14.md](../step_modules統合レポート_2025_06_14.md) - 統合状況
- [src/pipeline/](../src/pipeline/) - 統合オーケストレーター実装

---

**📅 最終更新**: 2025年6月14日  
**🎯 統合状況**: Step1-5完了、Step0継続使用  
**📝 重要度**: 最高 (開発方針変更)
