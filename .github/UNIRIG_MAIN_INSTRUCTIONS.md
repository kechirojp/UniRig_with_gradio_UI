# UniRig WebUI 開発・運用・保守 総合インストラクション

**作成日**: 2025年6月14日  
**更新日**: 2025年6月14日  
**文書バージョン**: v1.0  
**スコープ**: UniRig WebUI化プロジェクトの全体指針

## 📋 概要

このファイルは、UniRig WebUI化プロジェクトの**唯一の権威ある指針**です。本プロジェクトに関わる全ての開発・運用・保守活動は、このインストラクションに従って実行されなければなりません。

### 🎯 プロジェクトの使命

**複雑で技術的なオリジナルUniRigを、誰でも使えるワンクリックWebUIシステムに変革する**

- ✅ 4段階手動操作 → 1クリック自動実行
- ✅ Linux専用 → Windows/Mac/Linux全対応  
- ✅ 85%のコード削減と完全自動化
- ✅ 原流処理との94%互換性確保
- ✅ 70%以上のエラー事前予防システム

---

## 🏗️ アーキテクチャ基本原則

### 1. 決め打ちディレクトリ戦略（絶対遵守）

```
/app/pipeline_work/{model_name}/
├── 00_asset_preservation/     # Step0: 元データ保全
│   ├── original_metadata.json
│   └── preserved_textures/
├── 01_extracted_mesh/         # Step1: メッシュ抽出
│   └── raw_data.npz          # 固定ファイル名（原流互換）
├── 02_skeleton/               # Step2: スケルトン生成
│   ├── {model_name}.fbx      # 原流互換名（重要）
│   └── predict_skeleton.npz  # 固定ファイル名（原流互換）
├── 03_skinning/               # Step3: スキニング適用
│   ├── {model_name}_skinned_unirig.fbx
│   ├── skinning_data.npz
│   └── inference_datalist.txt # Step3実行必須
├── 04_merge/                  # Step4: 3つのデータソース統合マージ（KDTree技術）
│   ├── {model_name}_merged.fbx   # オリジナルメッシュ+AIスケルトン+AIスキニング統合済み
│   └── merge_process.log
└── 05_blender_integration/    # Step5: 最終統合
    └── {model_name}_final.fbx
```

**重要規則**:
- **動的ディレクトリ禁止**: テスト用・一時的ディレクトリの作成は一切禁止
- **JSON状態管理禁止**: ファイル存在のみで状態判定を行う
- **パス変更禁止**: 上記ディレクトリ構造の変更は絶対禁止

### 2. 統一命名規則（厳密遵守）

```python
UNIFIED_NAMING_CONVENTION = {
    # 原流処理完全互換ファイル名（変更絶対禁止）
    "step1_output": "raw_data.npz",                    
    "step2_fbx": "{model_name}.fbx",                   # サフィックスなし（重要）
    "step2_npz": "predict_skeleton.npz",               
    "step3_input_list": "inference_datalist.txt",     # Step3実行必須
    
    # 新規統一命名
    "step3_fbx": "{model_name}_skinned_unirig.fbx",    # 統一サフィックス
    "step4_fbx": "{model_name}_merged.fbx",            
    "step5_fbx": "{model_name}_final.fbx",             # 最終出力
    
    # 中間データファイル
    "step0_metadata": "original_metadata.json",        
    "step3_skinning": "skinning_data.npz",            
    "step4_merge_log": "merge_process.log"             
}
```

### 3. シンプル・ダイレクト実行原則

**禁止事項**:
- `src/pipeline/` ディレクトリの使用禁止
- `step_modules/` ディレクトリの使用禁止  
- 複雑なオーケストレーターの作成禁止

**必須事項**:
- `app.py` が直接各ステップを呼び出す
- 各ステップは独立したPython関数として実装
- 固定パス・固定ファイル名のみ使用

---

## 🚀 実装ガイドライン

### 1. app.py の実装方針

```python
def process_complete_pipeline(input_file, gender="neutral"):
    """
    メイン処理関数：全5ステップを順次実行
    """
    model_name = extract_model_name(input_file)
    
    # 固定ディレクトリの作成
    setup_fixed_directories(model_name)
    
    # 各ステップを直接呼び出し
    step0_result = preserve_assets(input_file, model_name)
    step1_result = extract_mesh(model_name)  
    step2_result = generate_skeleton(model_name, gender)
    step3_result = apply_skinning(model_name)
    step4_result = merge_three_data_sources(model_name, input_file)  # 3つのデータソース統合
    step5_result = integrate_blender_processing(model_name)
    
    return step5_result  # 最終FBXファイルパス
```

### 2. 各ステップ関数の実装方針

```python
def extract_mesh(model_name: str) -> tuple[bool, str, Path]:
    """
    Step1: メッシュ抽出処理
    
    Args:
        model_name: モデル名（ユーザーファイル名由来）
        
    Returns:
        tuple[成功フラグ, ログメッセージ, 出力ファイルパス]
    """
    # 入力検証
    input_file = get_input_file_path(model_name)
    if not input_file.exists():
        return False, f"Input file not found: {input_file}", None
    
    # 出力パス（固定）
    output_file = Path(f"/app/pipeline_work/{model_name}/01_extracted_mesh/raw_data.npz")
    
    # 実際の処理（原流コード呼び出し）
    success = call_original_extract_process(input_file, output_file)
    
    return success, "Extract completed", output_file
```

### 3. 原流処理互換性の確保

**必須事項**:
- `raw_data.npz` ファイル名の厳守
- `predict_skeleton.npz` ファイル名の厳守  
- `{model_name}.fbx` 形式の厳守（サフィックスなし）
- `inference_datalist.txt` の正確な生成

**禁止事項**:
- 原流処理で使用されるファイル名の変更
- 中間ファイル形式の変更
- 設定ファイル内の重複定義

---

## 🔧 技術仕様・制約事項

### 1. ファイル形式制約

```python
# 必須対応形式
SUPPORTED_INPUT_FORMATS = [".glb", ".gltf", ".fbx", ".obj"]
SUPPORTED_OUTPUT_FORMAT = ".fbx"  # Binary FBX のみ

# 禁止事項
FORBIDDEN_FORMATS = ["ASCII FBX"]  # merge処理で非対応
```

### 2. システム要件

```yaml
minimum_requirements:
  python: ">=3.8"
  gpu_memory: ">=8GB"  # AI推論処理用
  disk_space: ">=10GB" # 中間ファイル用
  
dependencies:
  - torch
  - pytorch3d  
  - trimesh
  - gradio
  - pathlib
```

### 3. エラーハンドリング方針

```python
def validate_input_requirements(step: str, model_name: str) -> tuple[bool, str]:
    """
    各ステップ実行前の事前検証（必須）
    
    70%以上のエラー事前予防を目標とする
    """
    # 入力ファイル存在確認
    # 依存ファイル確認  
    # システムリソース確認
    # 形式互換性確認
    
    return is_valid, error_message
```

---

## 📋 運用・保守ガイドライン

### 1. デバッグ・トラブルシューティング

**問題発生時の確認手順**:
1. 固定ディレクトリ内のファイル存在確認
2. ファイル命名規則の遵守確認  
3. 原流互換性の確認
4. ログファイルの詳細分析

**よくある問題と解決策**:
```
問題: "ファイルが見つかりません"
→ 解決: /app/pipeline_work/{model_name}/ 内の固定パス確認

問題: "ASCII FBX files are not supported"  
→ 解決: Binary FBX出力の確認・設定

問題: "inference_datalist.txt not found"
→ 解決: Step3実行前の必須ファイル生成確認
```

### 2. 性能最適化

**推奨設定**:
```python
PERFORMANCE_SETTINGS = {
    "batch_size": 1,           # メモリ使用量制御
    "max_faces": 50000,        # 処理上限
    "texture_resolution": 1024, # テクスチャ品質
    "parallel_processing": False # 安定性優先
}
```

### 3. 品質保証

**必須テスト項目**:
- [ ] 各ステップの独立実行確認
- [ ] ファイル命名規則の遵守確認
- [ ] 原流処理との出力互換性確認  
- [ ] エラーハンドリングの動作確認
- [ ] 複数モデルでのテスト実行

---

## 📚 関連文書・リソース

### 必読文書
1. `/app/.github/UniRig_改善完了報告書_最終版_2025_06_14.md` - プロジェクト成果詳細
2. `/app/dataflow_documentation/README.md` - データフロー仕様
3. `/app/fixed_directory_manager.py` - 実装参考コード

### 参考文書  
4. `/app/.github/unified_naming_convention.instructions.md` - 命名規則詳細
5. `/app/.github/fixed_directory_strategy.instructions.md` - ディレクトリ戦略
6. `/app/.github/microservice_guide.instructions.md` - アーキテクチャ設計
7. `/app/.github/unirig_original_dataflow.instructions.md` - 原流処理仕様

---

## ⚠️ 重要な禁止事項

### 絶対に実行してはいけない変更

1. **ディレクトリ構造の変更**
   - `/app/pipeline_work/{model_name}/XX_**/` 構造の変更禁止
   - 動的ディレクトリの作成禁止

2. **ファイル命名の変更**  
   - `raw_data.npz`, `predict_skeleton.npz` の名前変更禁止
   - `{model_name}.fbx` 形式の変更禁止

3. **アーキテクチャの複雑化**
   - `src/pipeline/` の復活禁止
   - `step_modules/` の復活禁止
   - 複雑なオーケストレーター作成禁止

4. **JSON状態管理の導入**
   - 状態管理はファイル存在のみで行う
   - JSON設定ファイルによる動的制御禁止

### 変更時の必須確認事項

**全ての変更は以下を確認後に実行**:
- [ ] 原流処理との互換性に影響がないか
- [ ] 固定ディレクトリ戦略に準拠しているか  
- [ ] 統一命名規則を遵守しているか
- [ ] シンプル・ダイレクト実行原則に従っているか

---

## 🎯 成功指標・品質基準

### 定量的目標
- **操作削減**: 4段階手動操作 → 1クリック自動実行
- **プラットフォーム対応**: Linux専用 → Win/Mac/Linux全対応
- **コード削減**: 85%以上の削減
- **エラー予防**: 70%以上の事前検出
- **原流互換性**: 94%以上の互換性確保

### 定性的目標  
- **ユーザビリティ**: 技術知識不要での利用実現
- **安定性**: 予測可能で信頼できる動作
- **保守性**: 明確で理解しやすいコード構造
- **拡張性**: 新機能追加の容易性

---

## 📞 サポート・連絡先

**技術的質問・問題報告**:
- このインストラクションファイルを最初に参照
- 関連文書での詳細確認
- コードレビューでの事前確認

**緊急時対応**:
- 原流処理の動作確認
- 固定ディレクトリの状態確認
- ログファイルの詳細分析

---

**文書ステータス**: ✅ **最終確定版**  
**更新方針**: 重大な仕様変更時のみ更新  
**権威性**: このファイルが唯一の権威ある指針

**最終更新者**: GitHub Copilot  
**承認日**: 2025年6月14日
