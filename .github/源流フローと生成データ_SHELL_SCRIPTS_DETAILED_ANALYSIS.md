# UniRig シェルスクリプト詳細解析レポート

**作成日**: 2025年6月14日  
**目的**: ボーン生成問題とマージ時のウェイト/バーテックスグループ欠損問題の解決  
**対象**: オリジナルシェルスクリプト群の入力/出力仕様の完全把握

**🔥 重要な発見**: Step2/Step3は必ずオリジナルファイルからメッシュ再抽出を行う
- Step2: faces_target_count=4000（AI推論最適化）
- Step3: faces_target_count=50000（スキニング最適化）
- この違いが品質保証の要諦

---

## 🔍 解析方法

1. 各シェルスクリプトのソースコード精読
2. 関連する設定ファイル（YAML）の解析
3. 実際のPythonモジュール（`src/data/extract.py`, `src/system/ar.py`, `src/system/skin.py`, `src/inference/merge.py`）の確認
4. 入力ファイル、出力ファイル、依存関係の詳細マッピング

---

## 📋 1. extract.sh の詳細解析

### 🎯 役割・目的
- 3Dモデルファイルからメッシュデータを抽出
- Blender経由での前処理
- NPZ形式での標準化されたデータ出力

### 📥 入力要件
| パラメータ | 必須/オプション | 説明 | デフォルト値 |
|-----------|---------------|------|-------------|
| `--input` / `-i` | 必須 | 3Dモデルファイルパス | なし |
| `--output_dir` / `-o` | オプション | 出力ディレクトリ | `results/` |
| `--cfg_data` / `-c` | オプション | データ設定ファイル | `configs/data/quick_inference.yaml` |
| `--cfg_task` / `-t` | オプション | タスク設定ファイル | `configs/task/quick_inference_unirig_skin.yaml` |
| `--faces_target_count` | オプション | 面数の目標値 | `50000` |
| `--require_suffix` | オプション | 対応ファイル形式 | `obj,fbx,FBX,dae,glb,gltf,vrm` |

### 📤 出力ファイル
| ファイル名 | 場所 | 形式 | 内容 |
|-----------|------|------|------|
| `raw_data.npz` | `{output_dir}/` | NPZ | 抽出されたメッシュデータ（頂点、面、UV等） |

### 🔧 実行コマンド
```bash
bash ./launch/inference/extract.sh \
    --input /path/to/model.glb \
    --output_dir /path/to/output \
    --faces_target_count 50000
```

### ⚠️ 重要な注意点
- **セグメンテーションフォルト**: Blenderクリーンアップ時に予期されるエラー（コメント内で明記）
- **パフォーマンス**: psutilを自動インストールしてメモリ管理を最適化
- **Python実行環境**: `/opt/conda/envs/UniRig/bin/python3` を前提

---

## 📋 2. generate_skeleton.sh の詳細解析

### 🎯 役割・目的
- AIモデルによるスケルトン（骨格）構造の生成
- 統一命名規則への対応
- FBXとNPZ形式での出力

### 📥 入力要件
| パラメータ | 必須/オプション | 説明 | デフォルト値 |
|-----------|---------------|------|-------------|
| `--input` | 必須 | 3Dモデルファイルパス | なし |
| `--model_name` | 必須 | モデル識別名（統一命名規則用） | なし |
| `--output_dir` | オプション | 出力ディレクトリ | なし |
| `--skeleton_task` | オプション | スケルトン生成タスク設定 | `configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml` |
| `--seed` | オプション | 乱数シード | `12345` |

### 📤 出力ファイル
| ファイル名 | 場所 | 形式 | 内容 |
|-----------|------|------|------|
| `{model_name}.fbx` | `{output_dir}/` | FBX | スケルトン構造を含むFBXファイル |
| `predict_skeleton.npz` → `{model_name}_skeleton.npz` | `{output_dir}/` | NPZ | スケルトンデータ（ボーン情報） |

### 🔧 実行コマンド
```bash
bash ./launch/inference/generate_skeleton.sh \
    --input /path/to/model.glb \
    --model_name bird \
    --output_dir /path/to/output
```

### ⚠️ 重要な注意点
- **2段階処理**: 1. extract.sh の実行 → 2. run.py でのスケルトン生成
- **統一命名規則**: 出力ファイルを `{model_name}_skeleton.*` にリネーム
- **依存ファイル**: `raw_data.npz` が必須（extract.shで生成）

### 🔍 設定ファイル解析（quick_inference_skeleton_articulationxl_ar_256.yaml）
```yaml
writer:
  export_npz: predict_skeleton  # → predict_skeleton.npz
  export_fbx: skeleton          # → skeleton.fbx
```
**問題発見**: 
- `export_fbx: skeleton` → 実際は `skeleton.fbx` が生成される
- これが `{model_name}.fbx` として期待されているファイル名との不一致を生じている

---

## 📋 3. generate_skin.sh の詳細解析

### 🎯 役割・目的
- メッシュとスケルトンのバインディング（スキニング）処理
- バーテックスグループ（ウェイト）の生成
- リギング済みFBXファイルの出力

### 📥 入力要件
| パラメータ | 必須/オプション | 説明 | デフォルト値 |
|-----------|---------------|------|-------------|
| `--input` | 必須 | 3Dモデルファイルパス | なし |
| `--model_name` | 必須 | モデル識別名 | なし |
| `--output_dir` | オプション | 出力ディレクトリ | `results/` |
| `--cfg_task` | オプション | スキニングタスク設定 | `configs/task/quick_inference_unirig_skin.yaml` |

### 📤 出力ファイル
| ファイル名 | 場所 | 形式 | 内容 |
|-----------|------|------|------|
| `{model_name}_skinned.fbx` | `{output_dir}/` | FBX | スキニング済みFBXファイル（バーテックスグループ含む） |
| `{model_name}_skinning.npz` | `{output_dir}/` | NPZ | スキニングデータ |

### 🔧 実行コマンド
```bash
bash ./launch/inference/generate_skin.sh \
    --input /path/to/model.glb \
    --model_name bird \
    --output_dir /path/to/output
```

### ⚠️ 重要な注意点
- **🔥 2段階処理**: 1. extract.sh の実行（スキニング用メッシュ再抽出） → 2. run.py でのスキニング処理
- **🔥 必須メッシュ再抽出**: Step1のメッシュは使用せず、オリジナルファイルから独自のメッシュ再抽出を実行
- **依存ファイル**: `predict_skeleton.npz` が必須（generate_skeleton.shで生成）
- **特殊ディレクトリ**: スキニング処理は `dataset_inference_clean` ディレクトリを使用
- **🔥 メッシュパラメータ**: `--faces_target_count 50000` (スケルトンの4000より多い詳細メッシュ)

### 🔍 設定ファイル解析（quick_inference_unirig_skin.yaml）
```yaml
components:
  data_name: predict_skeleton.npz  # スケルトンデータを参照

writer:
  export_npz: predict_skin  # → predict_skin.npz
  export_fbx: result_fbx    # → result_fbx.fbx
```
**問題発見**:
- `export_fbx: result_fbx` → 実際は `result_fbx.fbx` が生成される
- これが統一命名規則の `{model_name}_skinned.fbx` との不一致を生じている

---

## 📋 4. merge.sh の詳細解析

### 🎯 役割・目的
- 3つのデータソース（オリジナルメッシュ、AIスケルトン、AIスキニング）の統合
- KDTreeマッチングによる頂点数差異吸収システム
- 完全なリギングシステムの構築

### 📥 入力要件
| パラメータ | 必須/オプション | 説明 | デフォルト値 |
|-----------|---------------|------|-------------|
| `--source` | 必須 | AIスケルトンFBXファイルパス（Step2出力） | なし |
| `--target` | 必須 | オリジナルメッシュファイルパス（ユーザーアップロード） | なし |
| `--output` | 必須 | 統合済みFBXファイルパス | なし |
| `--model_name` | 必須 | モデル識別名 | なし |

### 📤 出力ファイル
| ファイル名 | 場所 | 形式 | 内容 |
|-----------|------|------|------|
| `{model_name}_merged.fbx` | 指定パス | FBX | 3つのデータソース統合済みFBXファイル（オリジナルメッシュ+AIスケルトン+AIスキニング） |

### 🔧 実行コマンド
```bash
bash ./launch/inference/merge.sh \
    --source /path/to/step2_skeleton.fbx \
    --target /path/to/original_model.glb \
    --output /path/to/merged.fbx \
    --model_name bird
```

### ⚠️ 重要な注意点
- **3つのデータソース統合**: オリジナルメッシュ、AIスケルトン、AIスキニングの高度な統合処理
- **KDTreeマッチング**: 頂点数差異を空間的最近傍検索で吸収
- **座標系統一**: AI処理座標からオリジナルメッシュサイズへの変換
- **ASCII FBX問題**: ASCII形式のFBXファイルは非対応（Binary FBXのみ）

---

## 🚨 5. 発見された問題と解決策

### 🔴 問題1: ファイル命名の不整合

#### 問題の詳細
```
Step 2 (skeleton) 出力:
- 設定: export_fbx: skeleton
- 実際: skeleton.fbx が生成される
- 期待: {model_name}.fbx が必要

Step 3 (skinning) 出力:  
- 設定: export_fbx: result_fbx
- 実際: result_fbx.fbx が生成される
- 期待: {model_name}_skinned.fbx が必要
```

#### 解決策
1. **設定ファイル修正**: YAMLファイルでの `export_fbx` 値を統一命名規則に合わせる
2. **ポストプロセス**: シェルスクリプト内でのファイルリネーム処理（現在も部分的に実装済み）
3. **WebUI実装**: 決め打ちディレクトリ戦略での確実なファイル配置

### 🔴 問題2: 依存ファイルの配置場所

#### 問題の詳細
```
スキニング処理の依存:
- predict_skeleton.npz が dataset_inference_clean/ に必要
- しかし Step 2 は異なるディレクトリに出力する可能性
```

#### 解決策
1. **ファイルコピー**: 必要なファイルを適切なディレクトリにコピー
2. **統一ディレクトリ**: 全ステップで統一されたディレクトリ構造を使用
3. **パス指定**: 設定ファイルで明示的なパス指定

### 🔴 問題3: ASCII FBX互換性

#### 問題の詳細
```
src.inference.merge の制約:
- ASCII FBX ファイルは非対応
- Blenderデフォルト出力はASCII形式の場合がある
```

#### 解決策
1. **Binary FBX強制**: 全ステップでBinary FBX出力を強制
2. **事前検証**: マージ前にFBX形式を検証
3. **変換処理**: 必要に応じてASCII→Binary変換を実装

---

## 🎯 6. WebUI実装への推奨事項

### 📋 Step 1 (extract.sh) の実装
```python
def extract_mesh_step1(input_file: str, model_name: str, output_dir: str):
    """
    入力: 3Dモデルファイル
    出力: raw_data.npz (固定名)
    配置: {output_dir}/01_extracted_mesh/raw_data.npz
    """
```

### 📋 Step 2 (generate_skeleton.sh) の実装
```python
def generate_skeleton_step2(model_name: str, input_dir: str, output_dir: str):
    """
    入力※step2自身が抽出したスケルトン推定用のメッシュが必要
│   ├── mesh_for_skeleton/     # Step2専用メッシュ（AI推論最適化）
│   │   └── raw_data.npz       # 面数4000・スケルトン生成特化）
    出力: 
    - {model_name}.fbx (skeleton.fbx をリネーム)
    - predict_skeleton.npz (固定名)
    配置: {output_dir}/02_skeleton/
    """
```

### 📋 Step 3 (generate_skin.sh) の実装
```python
def apply_skinning_step3(model_name: str, input_dir: str, output_dir: str):
    """
    入力: 
    - raw_data.npz
    - predict_skeleton.npz
    出力: {model_name}_skinned_unirig.fbx (result_fbx.fbx をリネーム)
    配置: {output_dir}/03_skinning/
    
    重要: dataset_inference_clean/ に必要ファイルをコピー
    """
```

### 📋 Step 4 (merge.sh) の実装
```python
def merge_skeleton_skinning_step4(model_name: str, skinned_fbx: str, original_file: str, output_dir: str):
    """
    入力:
    - {model_name}_skinned.fbx (AIスキニング済み - Step3出力) - source引数
    - original_model.glb (オリジナルメッシュ - ユーザーアップロード) - target引数
    - AIスケルトンデータ (メモリ内、Step3処理で既に統合済み)
    出力: {model_name}_merged.fbx
    配置: {output_dir}/04_merge/
    
    重要: 3つのデータソースをKDTreeマッチングで統合
    最新知見: skinned_fbx（Step3出力）をsourceとして使用
    """
```

---

## 🔧 7. 実装時の注意点

### ⚠️ 必須チェック項目
1. **ファイル存在確認**: 各ステップの依存ファイルが存在すること
2. **FBX形式検証**: Binary FBX形式であることの確認
3. **統一命名規則**: 出力ファイル名が期待される形式であること
4. **ディレクトリ構造**: 決め打ちディレクトリ戦略に準拠すること

### 🎯 品質保証
1. **中間ファイル検証**: 各ステップの出力品質確認
2. **エラーハンドリング**: セグメンテーションフォルト等の予期されるエラー処理
3. **ログ記録**: 詳細な実行ログと問題診断情報

---

## 📊 8. 結論

### 🎉 解析成果
- **4つのシェルスクリプト** の完全な入力/出力仕様を把握
- **ファイル命名の不整合** を特定し、解決策を提示
- **依存関係** の詳細マッピングを完了
- **問題の根本原因** を特定（設定ファイルの命名規則不整合）

### 🚀 次のステップ
1. **設定ファイル修正**: YAML設定での命名規則統一
2. **WebUI実装修正**: 発見された問題への対応
3. **統合テスト**: 修正されたパイプラインでの動作確認
4. **品質検証**: ボーン生成とウェイト情報の正確性確認

この詳細解析により、ボーン生成問題とマージ時のウェイト欠損問題の根本原因が明確になりました。次は、これらの知見を基にWebUI実装を修正し、正確なリギングシステムを構築します。

---

**作成者**: GitHub Copilot  
**レビュー日**: 2025年6月14日  
**文書バージョン**: v1.0
