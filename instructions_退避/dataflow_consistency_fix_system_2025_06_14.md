---
applyTo: '**'
---

# UniRig決め打ちデータフロー整合性修正システム - 2025年6月14日

## 🎯 最重要課題: データフロー齟齬の完全解決

**目標**: `.github/unirig_original_dataflow.instructions.md`で特定された全データフロー齟齬を解決し、決め打ちデータフローを確立

## 🚨 発見された重大な齟齬と修正方針

### 1. 🔥 Step2出力ファイル名齟齬の修正 (最高優先)

#### 問題: `skeleton.fbx` vs `{model_name}.fbx`
```yaml
# 現在の問題設定
# /app/configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml
export_fbx: skeleton  # ❌ "skeleton.fbx"として出力される
```

#### 決定的解決策:
```yaml
# 修正後の設定
export_fbx: "{model_name}"  # ✅ "{model_name}.fbx"として出力される
```

### 2. 🔥 Step3設定重複定義の除去 (最高優先)

#### 問題: 設定ファイル内の重複writer定義
```yaml
# 現在の問題 - /app/configs/task/quick_inference_unirig_skin.yaml
writer:                    # 1回目の定義
  export_npz: "{model_name}_skinning"
  export_fbx: "{model_name}_skinned_unirig"

# ...中略...

writer:                    # 2回目の定義（重複）
  export_npz: predict_skin
  export_fbx: result_fbx
```

#### 決定的解決策:
```yaml
# 単一writer定義（統一命名規則準拠）
writer:
  export_npz: "{model_name}_skinning"
  export_fbx: "{model_name}_skinned_unirig"
```

### 3. 🔥 generate_skin.shのnpz_dirパラメータ修正 (高優先)

#### 問題: 固定値の強制
```bash
# 現在の問題
if [ -n "$npz_dir" ]; then
    cmd="$cmd --npz_dir=dataset_inference_clean"  # 固定値強制
fi
```

#### 決定的解決策:
```bash
# パラメータ値を正しく使用
if [ -n "$npz_dir" ]; then
    cmd="$cmd --npz_dir=$npz_dir"  # ユーザー指定値を使用
fi
```

## 🛠️ 実装する修正システム

### Phase 1: 設定ファイル修正

#### quick_inference_skeleton_articulationxl_ar_256.yaml修正
```yaml
# 決め打ちファイル名修正
task: inference
writer:
  export_fbx: "{model_name}"      # ✅ 修正: skeleton → {model_name}
  export_npz: predict_skeleton    # ✅ 維持: 原流処理期待値
```

#### quick_inference_unirig_skin.yaml修正
```yaml
# 重複定義の完全除去
task: inference
writer:
  export_npz: "{model_name}_skinning"      # ✅ 統一命名規則
  export_fbx: "{model_name}_skinned_unirig" # ✅ 統一命名規則
# 重複writer定義を完全削除
```

### Phase 2: シェルスクリプト修正

#### generate_skeleton.sh修正
```bash
# パラメータ処理の改善
output_dir=${output_dir:-"results"}
model_name=${model_name:-"unknown"}

# Stage 2での--model_nameパラメータ追加
cmd="$cmd --model_name=$model_name"
```

#### generate_skin.sh修正
```bash
# npz_dirパラメータの正しい処理
if [ -n "$npz_dir" ]; then
    cmd="$cmd --npz_dir=$npz_dir"     # ユーザー指定値使用
else
    cmd="$cmd --npz_dir=dataset_inference_clean"  # デフォルト値のみ
fi
```

#### merge.sh修正
```bash
# --model_nameパラメータ追加（統一命名規則対応）
model_name=""
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --model_name) model_name="$2"; shift ;;
        # ...existing cases...
    esac
    shift
done

# model_nameをsrc.inference.mergeに渡す
cmd="$cmd --model_name=$model_name"
```

## 📁 決め打ちデータフロー仕様

### 確定ファイル命名規則
```python
UNIFIED_DATAFLOW_SPECIFICATION = {
    # Step1出力（固定）
    "mesh_output": "raw_data.npz",
    
    # Step2出力（決め打ち修正済み）
    "skeleton_fbx": "{model_name}.fbx",      # ✅ 修正済み
    "skeleton_npz": "predict_skeleton.npz",   # ✅ 原流処理期待値
    
    # Step3出力（決め打ち修正済み）
    "skinned_fbx": "{model_name}_skinned_unirig.fbx", # ✅ 統一命名
    "skinned_npz": "{model_name}_skinning.npz",       # ✅ 統一命名
    
    # Step4出力（決め打ち）
    "merged_fbx": "{model_name}_merged.fbx",   # ✅ 統一命名
    
    # Step5出力（決め打ち）
    "final_fbx": "{model_name}_final.fbx"     # ✅ 統一命名
}
```

### 確定ディレクトリ構造
```
決め打ちディレクトリ構造:
/app/pipeline_work/{model_name}/
├── 01_extracted_mesh/
│   └── raw_data.npz                           # Step1出力
├── 02_skeleton/
│   ├── {model_name}.fbx                       # ✅ 修正済み
│   └── predict_skeleton.npz                   # 原流処理期待値
├── 03_skinning/
│   ├── {model_name}_skinned_unirig.fbx        # ✅ 修正済み
│   └── {model_name}_skinning.npz              # ✅ 修正済み
├── 04_merge/
│   └── {model_name}_merged.fbx                # 統一命名
└── 05_blender_integration/
    └── {model_name}_final.fbx                 # 統一命名

# 原流処理互換作業ディレクトリ
/app/dataset_inference_clean/{model_name}/
├── raw_data.npz                               # Step1からコピー
├── predict_skeleton.npz                       # Step2からコピー
├── {model_name}.fbx                           # Step2からコピー
└── inference_datalist.txt                    # 新規作成
```

## 🔧 実装手順

### 1. 設定ファイル修正実行
```python
def fix_config_files():
    """設定ファイルの齟齬修正"""
    
    # Step2設定修正
    skeleton_config = "/app/configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml"
    fix_skeleton_config(skeleton_config)
    
    # Step3設定修正
    skin_config = "/app/configs/task/quick_inference_unirig_skin.yaml"
    fix_skin_config(skin_config)
```

### 2. シェルスクリプト修正実行
```python
def fix_shell_scripts():
    """シェルスクリプトの齟齬修正"""
    
    # generate_skeleton.sh修正
    fix_generate_skeleton_script()
    
    # generate_skin.sh修正
    fix_generate_skin_script()
    
    # merge.sh修正
    fix_merge_script()
```

### 3. step_modules統合確認
```python
def verify_dataflow_integrity():
    """データフロー整合性の完全確認"""
    
    checks = [
        verify_file_naming_consistency(),
        verify_directory_structure(),
        verify_original_flow_compatibility(),
        verify_unified_naming_convention()
    ]
    
    return all(checks)
```

## 📊 修正完了後の検証項目

### ✅ 確認チェックリスト
- [ ] Step2が`{model_name}.fbx`を出力する
- [ ] Step3設定の重複定義が除去されている
- [ ] `generate_skin.sh`のnpz_dirパラメータが正しく処理される
- [ ] 全ステップが統一命名規則に従う
- [ ] 原流処理との100%互換性が保たれる
- [ ] Step1→Step2→Step3→Step4のデータフローが決め打ちで動作する

### 🧪 エンドツーエンドテスト
```python
def test_unified_dataflow():
    """決め打ちデータフローの完全テスト"""
    
    # テストモデル名
    model_name = "test_bird"
    
    # Step1→Step2→Step3→Step4の順次実行
    step1_success = execute_step1(model_name)
    assert step1_success
    
    step2_success = execute_step2(model_name)
    assert step2_success
    assert Path(f"pipeline_work/{model_name}/02_skeleton/{model_name}.fbx").exists()
    
    step3_success = execute_step3(model_name)
    assert step3_success
    assert Path(f"pipeline_work/{model_name}/03_skinning/{model_name}_skinned_unirig.fbx").exists()
    
    step4_success = execute_step4(model_name)
    assert step4_success
    assert Path(f"pipeline_work/{model_name}/04_merge/{model_name}_merged.fbx").exists()
```

## 🚨 重要な注意事項

### 修正作業の注意点
1. **バックアップ必須**: 全修正対象ファイルのバックアップを作成
2. **段階的修正**: 一つずつ修正して動作確認
3. **互換性確認**: 各修正後に原流処理との互換性確認
4. **テスト実行**: 修正完了後のエンドツーエンドテスト実行

### 失敗時の復旧計画
```python
BACKUP_FILES = [
    "configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml",
    "configs/task/quick_inference_unirig_skin.yaml",
    "launch/inference/generate_skeleton.sh",
    "launch/inference/generate_skin.sh",
    "launch/inference/merge.sh"
]

def create_backups():
    """修正前のバックアップ作成"""
    for file_path in BACKUP_FILES:
        shutil.copy2(file_path, f"{file_path}.backup_{timestamp}")

def restore_backups():
    """問題発生時の復旧"""
    for file_path in BACKUP_FILES:
        backup_file = f"{file_path}.backup_{timestamp}"
        if Path(backup_file).exists():
            shutil.copy2(backup_file, file_path)
```

---

## 🎯 期待される成果

### 修正完了後の状態
- ✅ 全ファイル命名が決め打ちで予測可能
- ✅ 設定ファイルの重複・矛盾が完全除去
- ✅ シェルスクリプトパラメータが正しく処理される
- ✅ 原流処理との100%互換性維持
- ✅ Step1→Step2→Step3→Step4→Step5の完全自動化

### データフロー信頼性の向上
- 🚫 ファイル名の不整合によるエラー除去
- 🚫 設定の重複・矛盾によるエラー除去
- 🚫 パラメータ処理エラーの除去
- ✅ 決め打ちデータフローによる確実性保証

---

**📅 作成日**: 2025年6月14日  
**🎯 対象**: UniRig開発チーム（データフロー整合性確保）  
**📝 重要度**: 最高（決め打ちデータフロー実現に必須）  
**🔄 ステータス**: 修正計画策定完了、実装準備完了

**⚠️ 重要**: この修正システムは、UniRigの決め打ちデータフロー実現のための最重要作業です。すべての齟齬を解決し、確実なデータフローを確立します。
