# 🎯 UniRig シンプルデータ受け渡し指針

## 📋 基本原則

### 🔒 決め打ち設計（固定値）
```
目的: app.pyウェブアプリ完成
方針: 決め打ちディレクトリ + 統一命名規則
複雑さ排除: フォールバック禁止、動的処理禁止
```

## 📁 固定ディレクトリ構造（変更禁止）

```
/app/pipeline_work/{model_name}/
├── 00_asset_preservation/     # Step0出力
├── 01_extracted_mesh/         # Step1出力
├── 02_skeleton/               # Step2出力  
├── 03_skinning/               # Step3出力
├── 04_merge/                  # Step4出力
└── 05_final/                  # Step5出力（最終成果物）
```

## 🏷️ 統一命名規則（変更禁止）

### Step0 - アセット保存
```
入力: アップロードファイル (任意の場所)
出力: /app/pipeline_work/{model_name}/00_asset_preservation/
    └── {model_name}_original.{ext}  # 元ファイル保存
```

### Step1 - メッシュ抽出  
```
入力: /app/pipeline_work/{model_name}/00_asset_preservation/{model_name}_original.{ext}
出力: /app/pipeline_work/{model_name}/01_extracted_mesh/
    └── raw_data.npz  # src.data.extract期待出力名（固定）
```

### Step2 - スケルトン生成
```
入力: /app/pipeline_work/{model_name}/01_extracted_mesh/raw_data.npz
出力: /app/pipeline_work/{model_name}/02_skeleton/
    ├── {model_name}.fbx             # run.py期待出力名
    └── predict_skeleton.npz         # run.py期待出力名（固定）
```

### Step3 - スキニング適用
```
入力: 
  - /app/pipeline_work/{model_name}/01_extracted_mesh/raw_data.npz
  - /app/pipeline_work/{model_name}/02_skeleton/predict_skeleton.npz
  - /app/pipeline_work/{model_name}/02_skeleton/{model_name}.fbx
出力: /app/pipeline_work/{model_name}/03_skinning/
    └── {model_name}_skinned_unirig.fbx  # run.py期待出力名
```

### Step4 - マージ
```
入力:
  - /app/pipeline_work/{model_name}/02_skeleton/{model_name}.fbx
  - /app/pipeline_work/{model_name}/03_skinning/{model_name}_skinned_unirig.fbx  
出力: /app/pipeline_work/{model_name}/04_merge/
    └── {model_name}_merged.fbx
```

### Step5 - 最終出力
```
入力:
  - /app/pipeline_work/{model_name}/00_asset_preservation/{model_name}_original.{ext}
  - /app/pipeline_work/{model_name}/04_merge/{model_name}_merged.fbx
出力: /app/pipeline_work/{model_name}/05_final/
    └── {model_name}_rigged.fbx  # ユーザーダウンロード用最終成果物
```

## 🔧 各ステップの責務（シンプル化）

### Step0: ファイル保存のみ
```python
def step0_preserve_asset(uploaded_file_path: str, model_name: str) -> bool:
    """アップロードファイルを決め打ちディレクトリに保存"""
    output_dir = f"/app/pipeline_work/{model_name}/00_asset_preservation/"
    os.makedirs(output_dir, exist_ok=True)
    
    # ファイル拡張子取得
    ext = Path(uploaded_file_path).suffix
    output_file = f"{output_dir}/{model_name}_original{ext}"
    
    # ファイルコピー
    shutil.copy2(uploaded_file_path, output_file)
    return True
```

### Step1: メッシュ抽出
```python
def step1_extract_mesh(model_name: str) -> bool:
    """原流src.data.extract実行"""
    input_file = f"/app/pipeline_work/{model_name}/00_asset_preservation/{model_name}_original.*"
    output_dir = f"/app/pipeline_work/{model_name}/01_extracted_mesh/"
    
    # src.data.extract実行（固定パラメータ）
    cmd = [
        "python3", "-m", "src.data.extract",
        "--config", "/app/configs/data/quick_inference.yaml",
        "--require_suffix", "True",
        "--faces_target_count", "5000", 
        "--num_runs", "1",
        "--force_override", "True",
        "--id", model_name,
        "--time", str(int(time.time())),
        "--input", input_file,
        "--output_dir", output_dir
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0
```

### Step2: スケルトン生成
```python
def step2_generate_skeleton(model_name: str) -> bool:
    """原流run.py実行（スケルトンタスク）"""
    input_file = f"/app/pipeline_work/{model_name}/01_extracted_mesh/raw_data.npz"
    output_dir = f"/app/pipeline_work/{model_name}/02_skeleton/"
    
    # run.py実行（固定パラメータ）
    cmd = [
        "python3", "run.py",
        "--task", "/app/configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml",
        "--data", input_file,
        "--output", output_dir,
        "--name", model_name
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0
```

## 📋 実装チェックリスト

### Step0実装
- [ ] アップロードファイル→決め打ちディレクトリ保存
- [ ] ファイル名統一規則適用（{model_name}_original.{ext}）
- [ ] ディレクトリ自動作成

### Step1実装  
- [ ] src.data.extract固定パラメータ実行
- [ ] 入力：決め打ちディレクトリから読み込み
- [ ] 出力：raw_data.npz（固定名）で出力

### Step2実装
- [ ] run.py固定パラメータ実行（スケルトンタスク）
- [ ] 入力：raw_data.npz読み込み
- [ ] 出力：{model_name}.fbx + predict_skeleton.npz

### Step3実装
- [ ] run.py固定パラメータ実行（スキニングタスク）
- [ ] 入力：複数ファイル読み込み（raw_data.npz + predict_skeleton.npz + {model_name}.fbx）
- [ ] 出力：{model_name}_skinned_unirig.fbx

### Step4実装
- [ ] src.inference.merge固定パラメータ実行
- [ ] 入力：スケルトンFBX + スキニングFBX
- [ ] 出力：{model_name}_merged.fbx

### Step5実装
- [ ] Blender統合処理
- [ ] 入力：元ファイル + マージ済みFBX
- [ ] 出力：{model_name}_rigged.fbx（最終成果物）

## 🚨 重要な制約

### 固定値の厳守
```
❌ 禁止: 動的ファイル名生成
❌ 禁止: フォールバック処理
❌ 禁止: 複雑な設定ファイル
✅ 必須: 決め打ち値での確実な処理
```

### エラー処理
```
エラー時: 明確なエラーメッセージ表示
復旧方法: 該当ステップの再実行
デバッグ: ファイル存在確認 + パス確認
```

## 🎯 最終目標

**app.pyで1クリックパイプライン実行 → {model_name}_rigged.fbx ダウンロード**

---

**この指針により、複雑さを排除し、確実なデータ受け渡しでapp.py完成を目指します。**
