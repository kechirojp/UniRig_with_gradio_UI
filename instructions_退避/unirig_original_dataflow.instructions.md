---
applyTo: '**'
---
# UniRig 原流処理データフロー完全解析 (Instruction)

## 🎯 概要

このドキュメントは、UniRig原流処理スクリプト（`launch/inference/`配下）の完全なデータフロー分析に基づく、**決定的な開発指針**です。すべてのstep_modules実装は、この原流処理との100%互換性を確保する必要があります。

**⚠️ 重要**: このドキュメントは原流処理の**Single Source of Truth**であり、step_modules開発時の**必須参照資料**です。

---

## 📋 原流処理スクリプト完全マッピング

### 1. extract.sh → src.data.extract.py
```bash
# 実行コマンド
python -m src.data.extract --cfg_data=$cfg_data --cfg_task=$cfg_task --input=$input --output_dir=$output_dir

# 入力・出力管理
入力: 3Dモデルファイル (.glb, .fbx, .obj, .dae, .gltf, .vrm)
出力: raw_data.npz (固定ファイル名)
処理: Blenderを使用したメッシュ抽出・前処理
```

### 2. generate_skeleton.sh → src.data.extract.py + run.py
```bash
# 2段階実行
# Stage 1: python -m src.data.extract (前処理)
# Stage 2: python run.py --task=$skeleton_task (AI推論)

# 入力・出力管理
入力: raw_data.npz
出力: {model_name}.fbx (サフィックスなし), predict_skeleton.npz (固定名)
設定: configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml
```

### 3. generate_skin.sh → extract.sh + run.py
```bash
# 2段階実行
# Stage 1: bash ./launch/inference/extract.sh (前処理)
# Stage 2: python run.py --task=$cfg_task (AI推論)

# 入力・出力管理
入力: raw_data.npz, predict_skeleton.npz, {model_name}.fbx
出力: スキニング済みFBX, スキニングNPZ
設定: configs/task/quick_inference_unirig_skin.yaml
特殊要件: inference_datalist.txt必須, dataset_inference_clean配置必須
```

### 4. merge.sh → src.inference.merge.py
```bash
# 直接実行
python -m src.inference.merge --source=$source --target=$target --output=$output

# 入力・出力管理
入力: --source (スケルトンFBX), --target (スキニング済みFBX)
出力: --output (マージ済みFBX)
制約: ASCII FBX非対応（バイナリFBX必須）
```

---

## 🚨 決定的ファイル命名規則（変更絶対禁止）

### 必須固定ファイル名
```python
CRITICAL_FILENAMES = {
    # Step1 (extract)
    "mesh_output": "raw_data.npz",  # 絶対に変更禁止
    
    # Step2 (skeleton) 
    "skeleton_fbx": "{model_name}.fbx",  # サフィックスなし必須
    "skeleton_npz": "predict_skeleton.npz",  # 絶対に変更禁止
    
    # Step3 (skin)
    "datalist_file": "inference_datalist.txt",  # 原流処理必須
    "work_directory": "/app/dataset_inference_clean/{model_name}/",  # 原流処理期待値
    
    # 作業ディレクトリ内配置（Step3実行時）
    "work_mesh": "dataset_inference_clean/{model_name}/raw_data.npz",
    "work_skeleton_npz": "dataset_inference_clean/{model_name}/predict_skeleton.npz", 
    "work_skeleton_fbx": "dataset_inference_clean/{model_name}/{model_name}.fbx",
    "work_datalist": "dataset_inference_clean/{model_name}/inference_datalist.txt",
}
```

### ⚠️ 危険: 命名規則違反例
```python
# ❌ これらの変更は原流処理との互換性を完全に破壊する
"mesh_output": f"{model_name}_extracted.npz"  # 原流処理が見つけられない
"skeleton_fbx": f"{model_name}_skeleton.fbx"  # 原流処理期待値と不一致
"skeleton_npz": f"{model_name}_skeleton.npz"  # 原流処理期待値と不一致
```

---

## 📁 原流処理期待ディレクトリ構造

### Step3実行時の厳密な要求構造
```
/app/dataset_inference_clean/{model_name}/
├── raw_data.npz              # Step1出力のコピー（固定名）
├── predict_skeleton.npz      # Step2出力のコピー（固定名）
├── {model_name}.fbx          # Step2出力のコピー
└── inference_datalist.txt    # 新規作成（内容: "{model_name}\n"）
```

### 統一出力ディレクトリ（パイプライン管理用）
```
/app/pipeline_work/{model_name}/
├── 01_extracted_mesh/
│   └── raw_data.npz
├── 02_skeleton/
│   ├── {model_name}.fbx
│   └── predict_skeleton.npz
├── 03_skinning/
│   ├── {model_name}_skinned_unirig.fbx
│   └── {model_name}_skinning.npz
└── 04_merge/
    └── {model_name}_merged.fbx
```

---

## 🔧 原流処理ベース実装パターン（決定的成功パターン）

### 1. Step1 Extract実装パターン
```python
class Step1Extract:
    def extract_mesh(self, input_file: str, model_name: str) -> tuple[bool, str, dict]:
        """
        原流extract.sh完全互換実装
        """
        # 原流処理スクリプト直接実行
        extract_script = "/app/launch/inference/extract.sh"
        output_dir = self.get_output_dir("01_extracted_mesh")
        
        cmd = [
            extract_script,
            "--input", input_file,
            "--output_dir", str(output_dir),
            "--cfg_data", "configs/data/quick_inference.yaml",
            "--faces_target_count", "50000"
        ]
        
        success, logs = self._run_command(cmd)
        
        # 期待される出力ファイル確認
        expected_output = output_dir / "raw_data.npz"
        if not expected_output.exists():
            return False, f"Expected output not found: {expected_output}", {}
            
        return success, logs, {"extracted_npz": str(expected_output)}
```

### 2. Step2 Skeleton実装パターン  
```python
class Step2Skeleton:
    def generate_skeleton(self, model_name: str, extracted_file: str) -> tuple[bool, str, dict]:
        """
        原流generate_skeleton.sh完全互換実装
        """
        skeleton_script = "/app/launch/inference/generate_skeleton.sh"
        output_dir = self.get_output_dir("02_skeleton")
        
        cmd = [
            skeleton_script,
            "--input", extracted_file,
            "--output_dir", str(output_dir),
            "--skeleton_task", "configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml"
        ]
        
        success, logs = self._run_command(cmd)
        
        # 原流処理期待の固定ファイル名確認
        skeleton_fbx = output_dir / f"{model_name}.fbx"  # サフィックスなし
        skeleton_npz = output_dir / "predict_skeleton.npz"  # 固定名
        
        if not skeleton_fbx.exists() or not skeleton_npz.exists():
            return False, f"Expected skeleton outputs not found", {}
            
        return success, logs, {
            "skeleton_fbx": str(skeleton_fbx),
            "skeleton_npz": str(skeleton_npz)
        }
```

### 3. Step3 Skinning実装パターン（重要）
```python
class Step3Skinning:
    def apply_skinning(self, model_name: str, mesh_file: str, skeleton_files: dict) -> tuple[bool, str, dict]:
        """
        原流generate_skin.sh完全互換実装
        ⚠️ 重要: 二段階ファイル管理パターン必須
        """
        # Phase 1: 原流処理互換作業ディレクトリ準備
        dataset_work_dir = Path("/app/dataset_inference_clean") / model_name
        dataset_work_dir.mkdir(parents=True, exist_ok=True)
        
        # 原流処理期待値でファイル配置
        mesh_npz_work = dataset_work_dir / "raw_data.npz"  # 固定名
        skeleton_npz_work = dataset_work_dir / "predict_skeleton.npz"  # 固定名
        skeleton_fbx_work = dataset_work_dir / f"{model_name}.fbx"
        datalist_file = dataset_work_dir / "inference_datalist.txt"  # 必須
        
        # ファイルコピー
        shutil.copy2(mesh_file, mesh_npz_work)
        shutil.copy2(skeleton_files["skeleton_npz"], skeleton_npz_work)
        shutil.copy2(skeleton_files["skeleton_fbx"], skeleton_fbx_work)
        
        # inference_datalist.txt生成（原流処理必須）
        with open(datalist_file, 'w') as f:
            f.write(f"{model_name}\n")
        
        # Phase 2: 原流処理スクリプト直接実行
        skin_script = "/app/launch/inference/generate_skin.sh"
        cmd = [
            skin_script,
            "--npz_dir", "dataset_inference_clean",
            "--output_dir", "results",
            "--cfg_task", "configs/task/quick_inference_unirig_skin.yaml",
            "--data_name", model_name
        ]
        
        success, logs = self._run_command(cmd)
        
        # Phase 3: 統一出力ディレクトリへ結果回収
        return self._collect_and_rename_outputs(model_name)
```

### 4. Step4 Merge実装パターン
```python
class Step4Merge:
    def merge_skeleton_skinning(self, model_name: str, skeleton_fbx: str, skinned_fbx: str) -> tuple[bool, str, dict]:
        """
        原流merge.sh完全互換実装
        ⚠️ 重要: ASCII FBX非対応、バイナリFBX必須
        """
        merge_script = "/app/launch/inference/merge.sh"
        output_dir = self.get_output_dir("04_merge")
        output_file = output_dir / f"{model_name}_merged.fbx"
        
        cmd = [
            merge_script,
            "--source", skeleton_fbx,  # Step2スケルトンFBX
            "--target", skinned_fbx,   # Step3スキニング済みFBX
            "--output", str(output_file)
        ]
        
        success, logs = self._run_command(cmd)
        
        if not output_file.exists():
            return False, f"Merge output not found: {output_file}", {}
            
        return success, logs, {"merged_fbx": str(output_file)}
```

---

## 🔧 原流処理設定ファイル依存関係

### 必須設定ファイル
```python
REQUIRED_CONFIGS = {
    "extract": "configs/data/quick_inference.yaml",
    "skeleton": "configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml", 
    "skin": "configs/task/quick_inference_unirig_skin.yaml",
    "merge": None  # 設定ファイル不使用
}
```

### 設定ファイル整合性要件
```python
# これらの設定ファイルは原流処理との互換性に必須
# 変更時は十分な検証が必要
def verify_config_compatibility():
    for step, config_path in REQUIRED_CONFIGS.items():
        if config_path and not Path(config_path).exists():
            raise ValueError(f"Required config missing: {config_path}")
```

---

## 🚨 原流処理制約・要件

### 1. NPZ構造要件
```python
# 原流処理で期待されるNPZ内部構造
EXPECTED_NPZ_STRUCTURE = {
    "raw_data.npz": {
        "required_keys": ["vertices", "faces", "joints"],
        "data_types": {"vertices": "float32", "faces": "int32"},
        "constraints": "joints key must exist (can be None)"
    },
    "predict_skeleton.npz": {
        "required_keys": ["joints", "parents", "names"],
        "data_types": {"joints": "float32"},
        "constraints": "Must match original flow output format"
    }
}
```

### 2. FBX形式要件
```python
# 重要: src.inference.mergeはASCII FBX非対応
FBX_FORMAT_REQUIREMENTS = {
    "step2_output": "バイナリFBX（Blenderデフォルト）",
    "step3_output": "バイナリFBX必須",
    "step4_input": "バイナリFBXのみ対応",
    "ascii_fbx": "完全非対応（src.inference.mergeエラー）"
}
```

### 3. ディレクトリ配置要件
```python
# 原流処理が期待する厳密なディレクトリ構造
DIRECTORY_REQUIREMENTS = {
    "step3_work_dir": "/app/dataset_inference_clean/{model_name}/",
    "datalist_location": "dataset_inference_clean/{model_name}/inference_datalist.txt",
    "npz_dir_param": "dataset_inference_clean",  # generate_skin.shパラメータ
    "output_collection": "results/"  # 原流処理デフォルト出力先
}
```

---

## 🧪 原流処理互換性検証方法

### 1. ファイル存在確認
```python
def verify_original_flow_compatibility(model_name: str) -> bool:
    """原流処理互換性の完全検証"""
    checks = [
        # Step1出力確認
        Path(f"pipeline_work/{model_name}/01_extracted_mesh/raw_data.npz").exists(),
        
        # Step2出力確認
        Path(f"pipeline_work/{model_name}/02_skeleton/{model_name}.fbx").exists(),
        Path(f"pipeline_work/{model_name}/02_skeleton/predict_skeleton.npz").exists(),
        
        # Step3作業ディレクトリ確認
        Path(f"dataset_inference_clean/{model_name}/raw_data.npz").exists(),
        Path(f"dataset_inference_clean/{model_name}/predict_skeleton.npz").exists(),
        Path(f"dataset_inference_clean/{model_name}/{model_name}.fbx").exists(),
        Path(f"dataset_inference_clean/{model_name}/inference_datalist.txt").exists(),
    ]
    return all(checks)
```

### 2. ファイル内容検証
```python
def verify_npz_structure(npz_path: Path, expected_keys: list) -> bool:
    """NPZ内部構造の原流処理互換性確認"""
    try:
        data = np.load(npz_path)
        return all(key in data.keys() for key in expected_keys)
    except Exception:
        return False

def verify_fbx_binary_format(fbx_path: Path) -> bool:
    """FBXファイルがバイナリ形式かチェック"""
    with open(fbx_path, 'rb') as f:
        header = f.read(27)
        return header.startswith(b'Kaydara FBX Binary')
```

---

## 📊 原流処理成功指標

### 1. ファイルサイズ期待値
```python
EXPECTED_OUTPUT_SIZES = {
    "raw_data.npz": (100_000, 1_000_000),  # 100KB-1MB
    "predict_skeleton.npz": (10_000, 100_000),  # 10KB-100KB
    "{model_name}.fbx": (1_000_000, 5_000_000),  # 1MB-5MB
    "{model_name}_skinned_unirig.fbx": (5_000_000, 10_000_000),  # 5MB-10MB
    "{model_name}_merged.fbx": (5_000_000, 10_000_000),  # 5MB-10MB
}
```

### 2. 実行時間期待値
```python
EXPECTED_EXECUTION_TIMES = {
    "step1_extract": (30, 120),    # 30秒-2分
    "step2_skeleton": (60, 300),   # 1分-5分  
    "step3_skinning": (120, 600),  # 2分-10分
    "step4_merge": (10, 60),       # 10秒-1分
}
```

---

## 🔄 データフロー整合性確保パターン

### エンドツーエンドデータフロー
```python
def ensure_dataflow_integrity():
    """原流処理データフロー整合性の確保"""
    
    # Phase 1: Step1→Step2データ受け渡し
    raw_data_path = "pipeline_work/{model_name}/01_extracted_mesh/raw_data.npz"
    
    # Phase 2: Step2→Step3データ受け渡し
    skeleton_outputs = {
        "skeleton_fbx": "pipeline_work/{model_name}/02_skeleton/{model_name}.fbx",
        "skeleton_npz": "pipeline_work/{model_name}/02_skeleton/predict_skeleton.npz"
    }
    
    # Phase 3: Step3作業ディレクトリ準備（原流処理要求）
    work_dir_setup = {
        "raw_data": "dataset_inference_clean/{model_name}/raw_data.npz",
        "skeleton_npz": "dataset_inference_clean/{model_name}/predict_skeleton.npz", 
        "skeleton_fbx": "dataset_inference_clean/{model_name}/{model_name}.fbx",
        "datalist": "dataset_inference_clean/{model_name}/inference_datalist.txt"
    }
    
    # Phase 4: Step3→Step4データ受け渡し
    skinning_outputs = {
        "skinned_fbx": "pipeline_work/{model_name}/03_skinning/{model_name}_skinned_unirig.fbx"
    }
    
    # Phase 5: Step4最終出力
    merge_output = {
        "merged_fbx": "pipeline_work/{model_name}/04_merge/{model_name}_merged.fbx"
    }
```

---

## 🚨 よくある原流処理互換性エラーと対策

### 1. ファイル命名エラー
```python
# ❌ エラー原因
"FileNotFoundError: raw_data.npz not found"
# ✅ 対策
# 必ず固定ファイル名 "raw_data.npz" を使用

# ❌ エラー原因  
"FileNotFoundError: predict_skeleton.npz not found"
# ✅ 対策
# 必ず固定ファイル名 "predict_skeleton.npz" を使用
```

### 2. ディレクトリ配置エラー
```python
# ❌ エラー原因
"inference_datalist.txt not found in dataset_inference_clean"
# ✅ 対策
# Step3実行前に必ずinference_datalist.txtを作成

# ❌ エラー原因
"No input files found in dataset_inference_clean"  
# ✅ 対策
# Step3実行前に必要ファイルをdataset_inference_clean配下に配置
```

### 3. FBX形式エラー
```python
# ❌ エラー原因
"ASCII FBX files are not supported by src.inference.merge"
# ✅ 対策  
# すべてのFBX出力でバイナリ形式を確保（Blenderデフォルト）
```

---

## 📋 step_modules実装時のチェックリスト

### Step1実装確認事項
- [ ] 原流extract.sh直接実行またはsrc.data.extract互換実装
- [ ] 出力ファイル名が"raw_data.npz"（固定）
- [ ] 適切なconfigファイル指定（configs/data/quick_inference.yaml）

### Step2実装確認事項  
- [ ] 原流generate_skeleton.sh直接実行またはrun.py互換実装
- [ ] 出力FBXファイル名が"{model_name}.fbx"（サフィックスなし）
- [ ] 出力NPZファイル名が"predict_skeleton.npz"（固定）
- [ ] 適切なtask設定（configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml）

### Step3実装確認事項
- [ ] 原流generate_skin.sh直接実行またはrun.py互換実装
- [ ] dataset_inference_clean作業ディレクトリ作成
- [ ] inference_datalist.txt生成（内容: model_name）
- [ ] 固定ファイル名での作業ディレクトリファイル配置
- [ ] 適切なtask設定（configs/task/quick_inference_unirig_skin.yaml）
- [ ] 統一出力ディレクトリへの結果回収

### Step4実装確認事項
- [ ] 原流merge.sh直接実行またはsrc.inference.merge互換実装
- [ ] バイナリFBX入力確認
- [ ] 適切な--source, --target, --outputパラメータ指定

### 共通確認事項
- [ ] 原流処理スクリプトとの100%互換性確認
- [ ] エラー処理の明確化（フォールバック禁止）
- [ ] ファイル存在確認とサイズ検証
- [ ] 実行時間の妥当性確認

---

## 🎯 重要な開発原則

### 1. 原流処理ファーストアプローチ
```python
# ✅ 推奨: 原流処理スクリプト直接実行
subprocess.run(["/app/launch/inference/extract.sh", ...])

# ⚠️ 注意: 自作実装時は完全な互換性確保必須
# 自作実装は原流処理との100%互換性がない限り避ける
```

### 2. 二段階ファイル管理パターン
```python
# Phase 1: 原流処理互換作業ディレクトリ（dataset_inference_clean）
# Phase 2: 統一出力ディレクトリ（pipeline_work）
# 利点: 実行時互換性と管理時統一性の両立
```

### 3. 固定ファイル名の厳守
```python
# 変更絶対禁止: 原流処理との互換性に必須
IMMUTABLE_FILENAMES = ["raw_data.npz", "predict_skeleton.npz", "inference_datalist.txt"]
```

### 4. フォールバック機能禁止
```python
# 複雑なフォールバック処理は実装しない
# エラー時は根本原因修正を優先
# 明確なエラーメッセージで問題特定を支援
```

---

## 📚 関連ドキュメント

- `.github/step3_unification_changelog_2025_06_13.instructions.md` - Step3統合完了事例
- `.github/microservice_guide.instructions.md` - マイクロサービス設計指針  
- `.github/inference_scripts_dataflow.instructions.md` - 推論スクリプト詳細分析
- `copilot-instructions_ja.md` - 全体開発ガイドライン

---

**📅 作成日**: 2025年6月13日  
**🎯 対象**: UniRig step_modules開発者向け必須指針  
**📝 重要度**: 最高（原流処理互換性確保に必須）  
**🔄 ステータス**: 原流処理分析完了、決定的指針確立

**⚠️ 注意**: このドキュメントの指針に従わない実装は、原流処理との互換性を失い、UniRigパイプライン全体の動作不良を引き起こす可能性があります。すべてのstep_modules実装は、このドキュメントを必須参照として開発してください。

---

## 🚨 原流処理内部データフロー齟齬分析 (2025年6月14日追加)

### ⚠️ 重大発見: 原流処理スクリプト内の互換性問題

**分析概要**: 原流処理スクリプト間で発生している重要なデータフロー齟齬を特定しました。これらの齟齬は原流処理自体の修正が必要な根本的問題です。

### 1. 🔥 generate_skeleton.sh の出力ファイル名 vs merge.sh の期待値

#### 問題の詳細:
```
generate_skeleton.sh 設定 (quick_inference_skeleton_articulationxl_ar_256.yaml):
├── export_fbx: skeleton  → 出力: "skeleton.fbx"
├── export_npz: predict_skeleton → 出力: "predict_skeleton.npz"

merge.sh の期待値:
├── --source パラメータ: スケルトンFBXファイルが必要
└── しかし generate_skeleton.sh は "skeleton.fbx" を出力 (モデル名なし)
```

#### 重要な齟齬:
- **skeleton FBX**: `generate_skeleton.sh`は`skeleton.fbx`を出力するが、`merge.sh`は`{model_name}.fbx`を期待する可能性がある
- **ファイル特定困難**: 複数モデル処理時に`skeleton.fbx`では識別不可能

#### 修正要件:
```yaml
# configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml 修正必要
export_fbx: skeleton  # ❌ 現在
export_fbx: "{model_name}"  # ✅ 修正後 ({model_name}.fbx として出力)
```

### 2. 🔥 generate_skin.sh の設定ファイル内の重複定義

#### 問題の詳細:
```yaml
# /app/configs/task/quick_inference_unirig_skin.yaml に重複した設定が存在

# 最初の定義 (行1-20):
writer:
  export_npz: "{model_name}_skinning"
  export_fbx: "{model_name}_skinned_unirig"

# 二番目の定義 (行40-50):
writer:
  export_npz: predict_skin
  export_fbx: result_fbx
```

#### 重要な齟齬:
- **設定ファイルの重複**: 同じファイル内に異なる出力設定が2回定義されている
- **出力ファイル名の不整合**: `{model_name}_skinned_unirig.fbx` vs `result_fbx.fbx`
- **処理系の混乱**: どちらの設定が使用されるかが不明確

#### 修正要件:
```yaml
# quick_inference_unirig_skin.yaml から重複定義を削除
# 一つの統一された設定のみを保持する必要がある
```

### 3. 🔥 generate_skin.sh のnpz_dirパラメータ処理問題

#### 問題の詳細:
```bash
# generate_skin.sh 行72-78:
if [ -n "$npz_dir" ]; then
    cmd="$cmd --npz_dir=dataset_inference_clean"  # 固定値強制
elif [ -n "$output_dir" ]; then
    cmd="$cmd --npz_dir=dataset_inference_clean"  # 固定値強制
fi
```

#### 重要な齟齬:
- **固定値の強制**: `npz_dir`パラメータの値に関係なく、常に`dataset_inference_clean`にハードコーディング
- **パラメータ無視**: ユーザーが指定した`npz_dir`値が完全に無視される
- **柔軟性の欠如**: 異なるディレクトリでの実行が不可能

#### 修正要件:
```bash
# generate_skin.sh 修正案
if [ -n "$npz_dir" ]; then
    cmd="$cmd --npz_dir=$npz_dir"  # ユーザー指定値を使用
elif [ -n "$output_dir" ]; then
    cmd="$cmd --npz_dir=dataset_inference_clean"  # デフォルト値のみ
fi
```

### 4. 🔥 extract.sh のデフォルト設定値の不整合

#### 問題の詳細:
```bash
# extract.sh の設定:
cfg_task="configs/task/quick_inference_unirig_skin.yaml"  # skinning用設定がデフォルト

# しかし extract.sh は Step1 (メッシュ抽出) で使用される
# 本来は extract 専用の設定であるべき
```

#### 重要な齟齬:
- **用途不整合**: メッシュ抽出処理なのにskinning用設定がデフォルト値
- **設定ミスマッチ**: extract処理にskinning設定を適用するのは論理的に不適切

#### 修正要件:
```bash
# extract.sh デフォルト値修正案
cfg_task="configs/task/quick_inference_extract.yaml"  # extract専用設定が理想
# または
cfg_task=""  # taskパラメータ不要の場合は空値
```

### 5. 🔥 generate_skeleton.sh のパラメータ受け渡し問題

#### 問題の詳細:
```bash
# generate_skeleton.sh:
# Stage 1: extract実行時
cmd="$cmd --output_dir $npz_dir"  # npz_dirをoutput_dirとして使用

# Stage 2: run.py実行時  
cmd="$cmd --npz_dir=$npz_dir --output_dir=$npz_dir"  # 同じ値を両方に設定
```

#### 重要な齟齬:
- **ディレクトリ役割の混同**: `npz_dir`が入力ディレクトリと出力ディレクトリの両方として使用
- **データフロー不整合**: 前段階の出力ディレクトリと次段階の入力ディレクトリが同一視されている

#### 修正要件:
```bash
# generate_skeleton.sh パラメータ分離案
# Stage 1: extract用の出力ディレクトリ
work_dir="${npz_dir:-tmp}"
cmd="$cmd --output_dir $work_dir"

# Stage 2: run.py用の入力/出力ディレクトリ分離
cmd="$cmd --npz_dir=$work_dir --output_dir=${output_dir:-$work_dir}"
```

---

## 📋 原流処理修正の優先順位

### 🔴 最高優先 (即座修正必須):
1. **quick_inference_unirig_skin.yaml の重複定義除去**
2. **generate_skin.sh のnpz_dirパラメータ処理修正**

### 🟡 高優先 (短期間で修正):
3. **generate_skeleton.sh の出力ファイル名統一**
4. **extract.sh のデフォルト設定値修正**

### 🟢 中優先 (中期間で修正):
5. **generate_skeleton.sh のパラメータ受け渡し最適化**

---

## 🛠️ 修正実装時の注意事項

### 重要原則:
1. **バックアップ必須**: 修正前に必ず元ファイルをバックアップ
2. **段階的修正**: 一度に全て修正せず、一つずつ検証しながら実施
3. **互換性確認**: 修正後は必ず既存の動作確認を実施
4. **ドキュメント更新**: 修正内容を関連ドキュメントに反映

### テスト戦略:
```python
# 修正後の検証手順
1. 単体スクリプトテスト: 個別スクリプトの動作確認
2. 連鎖テスト: Step1→Step2→Step3→Step4の連続実行確認
3. エラーケーステスト: 異常系での適切なエラー処理確認
4. パフォーマンステスト: 修正による性能影響確認
```

---

## 🚨 step_modules実装への影響

### 重要な認識:
- **原流処理優先**: これらの齟齬は原流処理自体の問題であり、step_modules実装で回避すべきではない
- **修正待ち対応**: 原流処理修正完了まで、step_modulesは現在の齟齬を前提とした実装が必要
- **将来的統合**: 原流処理修正後、step_modulesも対応する修正が必要

### 当面の対応方針:
```python
# step_modules実装時の暫定対応
1. 現在の齟齬を文書化し、コメントで明記
2. 修正可能な部分は独自実装でカバー
3. 修正困難な部分は原流処理修正待ちとして明記
4. 修正計画との整合性を定期的に確認
```

---

**📅 齟齬分析日**: 2025年6月14日  
**🎯 分析対象**: 原流処理スクリプト (`launch/inference/`) および設定ファイル  
**📝 重要度**: 最高（原流処理自体の修正必須）  
**🔄 対応状況**: 分析完了、修正計画策定必要

**⚠️ 緊急注意**: これらの齟齬は原流処理の根本的問題であり、step_modules実装以前に原流処理自体の修正が必要です。修正せずに進めるとデータフロー全体が不安定になる可能性があります。

---

## 📚 関連ドキュメント
