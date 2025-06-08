# UniRig マイクロサービス化 実装ガイド

## 🏗️ アーキテクチャ概要

UniRigマイクロサービス化とは、**同一アプリ内で独立した実行機能を持つ構造**です：

```
app.py (UI + データ受け渡し)
├── Step1Module (独立実行機能) - メッシュ抽出
├── Step2Module (独立実行機能) - スケルトン生成  
├── Step3Module (独立実行機能) - スキニング適用
└── Step4Module (独立実行機能) - テクスチャ統合

データフロー: app.py → Step1 → app.py → Step2 → app.py → Step3 → app.py → Step4 → app.py
```

## 📋 マイクロサービス化の基本原則

### 🎯 app.py の責務
- **UI表示**: Gradioインターフェース
- **ファイル管理**: アップロード・ダウンロード・状態管理
- **データ受け渡し**: 各ステップ間のデータ橋渡し
- **進行管理**: パイプライン全体の進行制御

### 🔧 Step Modules の責務
各ステップは独立した実行機能として設計：

#### 📦 Step 1 Module - メッシュ抽出
- **責務**: 3Dモデルからメッシュデータを抽出
- **入力**: 3Dモデルファイルパス (.glb, .fbx, .obj等)
- **出力**: メッシュデータファイルパス (.npz)
- **独立性**: 他ステップの実行環境を汚さない
- **実装場所**: `src/data/extract.py`
- **内部処理**: このモジュールは、元々 `launch/inference/extract.sh` スクリプトによって実行されていた処理をPython関数としてカプセル化します。`extract.sh` は内部で `python -m src.data.extract` コマンドを呼び出し、入力ファイルパス、出力ディレクトリパス、設定ファイルパス (`configs/data/quick_inference.yaml` など)、目標ポリゴン数などのパラメータを渡してメッシュ抽出処理を実行します。

#### 🦴 Step 2 Module - スケルトン生成
- **責務**: AIによるスケルトン構造の生成
- **入力**: メッシュデータファイルパス (.npz), 性別設定
- **出力**: スケルトンFBXファイルパス, スケルトンデータファイルパス (.npz)
- **独立性**: メッシュ抽出とは独立して実行
- **実装場所**: UniRigアルゴリズム呼び出し
- **内部処理**: このモジュールは、`launch/inference/generate_skeleton.sh` の処理をカプセル化します。このシェルスクリプトは2段階の処理を実行します。
    1.  **メッシュデータ準備**: まず `python -m src.data.extract` を呼び出し、入力3Dモデルからスケルトン生成に必要な中間データ (`raw_data.npz`) を生成します。この際、`--config` で指定されたデータ設定と、`--output_dir` で指定された中間データ保存場所が重要になります。
    2.  **スケルトン推論**: 次に `python run.py` を呼び出し、準備された中間データと `--task` で指定されたスケルトン生成タスク設定ファイル（例: `configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml`）に基づいてスケルトンを生成します。生成されたスケルトンはFBX形式とNPZ形式で出力されます。

#### 🎭 Step 3 Module - スキニング適用
- **目的**: メッシュとスケルトンのバインディング（スキニング）
- **入力**: メッシュデータファイルパス、スケルトンFBXファイルパス（例）
- **出力**: リグ済みFBXファイルパス、スキニングデータファイルパス（.npz）（例）
- **独立性**: 前のステージの結果のみを使用し、環境汚染なし
- **内部処理**: このモジュールは `launch/inference/generate_skin.sh` の機能をカプセル化します。このスクリプトは、まず `launch/inference/extract.sh` を呼び出してメッシュデータを準備し（スケルトン生成と同様）、次に `python run.py` をタスク固有の設定（例: `--task=configs/task/quick_inference_unirig_skin.yaml`）で呼び出してスキニングを適用します。入力として、元のモデル、出力ディレクトリ、およびスケルトンファイルが格納されているディレクトリ（例: `dataset_inference_clean`）を取ります。

#### 🎨 Step 4 Module - テクスチャ統合
- **目的**: オリジナルのテクスチャ統合と最終出力
- **入力**: リグ済みFBXファイルパス、オリジナルモデルファイルパス（例）
- **出力**: 最終FBXファイルパス（テクスチャ付き）（例）
- **独立性**: テクスチャ処理のみに焦点を当て、他の機能との干渉なし
- **内部処理**: このモジュールは `launch/inference/merge.sh` の機能をカプセル化します。このスクリプトは `python -m src.inference.merge` を呼び出し、ソース（オリジナルモデル）、ターゲット（スキニング済みモデル）、出力ファイルパスなどのパラメータを渡します。

## 🔧 内部API 仕様

### データ受け渡しインターフェース
```python
# 共通レスポンス形式
def step_function(input_data: dict) -> tuple[bool, str, dict]:
    """
    Args:
        input_data: 入力データ辞書
    
    Returns:
        success: 成功フラグ
        logs: 実行ログ
        output_files: 出力ファイル辞書
    """
```

### Step 1 Interface
```python
def extract_mesh(input_file: str, model_name: str) -> tuple[bool, str, dict]:
    """
    Args:
        input_file: 3Dモデルファイルパス
        model_name: モデル名
    
    Returns:
        success: True/False
        logs: "メッシュ抽出完了: /path/to/extracted.npz"
        output_files: {"extracted_npz": "/path/to/extracted.npz"}
    """
```

### Step 2 Interface
```python
def generate_skeleton(model_name: str, gender: str, extracted_file: str) -> tuple[bool, str, dict]:
    """
    Args:
        model_name: モデル名
        gender: "neutral|male|female"
        extracted_file: 抽出済みメッシュファイルパス
    
    Returns:
        success: True/False
        logs: "スケルトン生成完了: /path/to/skeleton.fbx"
        output_files: {
            "skeleton_fbx": "/path/to/skeleton.fbx",
            "skeleton_npz": "/path/to/skeleton.npz"
        }
    """
```

### Step 3 Interface
```python
def apply_skinning(model_name: str, mesh_file: str, skeleton_file: str) -> tuple[bool, str, dict]:
    """
    Args:
        model_name: モデル名
        mesh_file: メッシュデータファイルパス
        skeleton_file: スケルトンFBXファイルパス
    
    Returns:
        success: True/False
        logs: "スキニング適用完了: /path/to/skinned.fbx"
        output_files: {
            "skinned_fbx": "/path/to/skinned.fbx",
            "skinning_npz": "/path/to/skinning.npz"
        }
    """
```

### Step 4 Interface
```python
def merge_textures(model_name: str, skinned_file: str, original_file: str) -> tuple[bool, str, dict]:
    """
    Args:
        model_name: モデル名
        skinned_file: リギング済みFBXファイルパス
        original_file: オリジナルモデルファイルパス
    
    Returns:
        success: True/False
        logs: "テクスチャ統合完了: /path/to/final.fbx"
        output_files: {"final_fbx": "/path/to/final.fbx"}
    """
```

## 🚀 実装手順

### 1. app.py の実装 (既に完成)
```python
# app.py - UI とデータ受け渡しのみ
def process_complete_pipeline(input_file, gender):
    # Step 1: メッシュ抽出
    success, logs, files = extract_mesh(input_file, model_name)
    
    # Step 2: スケルトン生成  
    success, logs, files = generate_skeleton(model_name, gender, files["extracted_npz"])
    
    # Step 3: スキニング適用
    success, logs, files = apply_skinning(model_name, extracted_file, skeleton_file)
    
    # Step 4: テクスチャ統合
    success, logs, files = merge_textures(model_name, skinned_file, original_file)
```

### 2. Step Module 実装例
```python
# step_modules/step1_extract.py
def extract_mesh(input_file: str, model_name: str) -> tuple[bool, str, dict]:
    """独立したメッシュ抽出機能"""
    try:
        # 実際のメッシュ抽出処理
        # ここに既存の extract.py のロジックを移植
        
        output_path = f"/app/pipeline_work/01_extracted_mesh/{model_name}_extracted.npz"
        
        # 処理実行（他の環境を汚さない）
        # ...
        
        return True, f"メッシュ抽出完了: {output_path}", {"extracted_npz": output_path}
        
    except Exception as e:
        return False, f"メッシュ抽出エラー: {e}", {}
```

### 3. app.py での Module 呼び出し実装
```python
# app.py
from step_modules.step1_extract import extract_mesh
from step_modules.step2_skeleton import generate_skeleton
from step_modules.step3_skinning import apply_skinning
from step_modules.step4_texture import merge_textures

def call_microservice_step1(input_file: str, model_name: str):
    """Step1 Module を直接呼び出し"""
    return extract_mesh(input_file, model_name)

def call_microservice_step2(model_name: str, gender: str):
    """Step2 Module を直接呼び出し"""
    extracted_file = f"/app/pipeline_work/01_extracted_mesh/{model_name}_extracted.npz"
    return generate_skeleton(model_name, gender, extracted_file)
```

## 🔧 ディレクトリ構成

```
/app/
├── app.py                    # UI + データ受け渡し
├── step_modules/             # 独立実行機能群
│   ├── __init__.py
│   ├── step1_extract.py     # メッシュ抽出モジュール
│   ├── step2_skeleton.py    # スケルトン生成モジュール
│   ├── step3_skinning.py    # スキニング適用モジュール
│   └── step4_texture.py     # テクスチャ統合モジュール
├── pipeline_work/           # データ保存ディレクトリ
│   ├── 01_extracted_mesh/
│   ├── 02_skeleton/
│   ├── 03_skinning/
│   └── 04_merge/
└── src/                     # 既存のUniRigコア機能
    ├── data/extract.py      # Step1で使用
    ├── inference/           # Step2, Step3で使用
    └── ...
```

## 📋 マイクロサービス化の利点

### ✅ 独立性
- 各ステップが独立して実行可能
- 他ステップの実行環境を汚さない
- エラーが他ステップに波及しない

### ✅ 保守性
- 各ステップの修正が他に影響しない
- テストが容易（単体テスト可能）
- デバッグが簡単

### ✅ 拡張性  
- 新しいステップの追加が容易
- 既存ステップの改良が安全
- パラメータ調整が独立

### ✅ 再利用性
- 各ステップを個別に呼び出し可能
- 段階的実行が可能
- バッチ処理への応用が容易

## 📊 監視・ログ

### ログ構造
```json
{
  "timestamp": "2025-01-03T10:00:00Z",
  "service": "frontend",
  "level": "INFO", 
  "message": "API call to step1 service",
  "request_id": "uuid",
  "user_id": "optional",
  "model_name": "bird",
  "processing_time": 1.5,
  "status": "success"
}
```

### メトリクス
- リクエスト数/秒
- レスポンス時間
- エラー率
- ファイルサイズ分布
- 処理成功率

## 🚧 次の開発ステップ

1. **Step 1 サービス実装**: メッシュ抽出マイクロサービス
2. **Step 2 サービス実装**: スケルトン生成マイクロサービス  
3. **Step 3 サービス実装**: スキニングマイクロサービス
4. **Step 4 サービス実装**: テクスチャ統合マイクロサービス
5. **認証・セキュリティ**: API認証とファイルアクセス制御
6. **監視・ログ**: 各サービスの監視とログ集約
7. **負荷分散**: サービス間の負荷分散設定
8. **CI/CD**: 自動テスト・デプロイパイプライン
