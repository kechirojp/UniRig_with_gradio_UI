---
applyTo: '**'
---
# UniRig マイクロサービス化 実装ガイド (2025年6月12日改訂版)

## 🏗️ アーキテクチャ概要

UniRigマイクロサービス化とは、**同一アプリ内で独立した実行機能を持つ構造**です：

```
app.py (Gradio UI + データ受け渡し・進行管理)
├── Step0Module (独立実行機能) - ファイル転送のみ
├── Step1Module (独立実行機能) - メッシュ抽出
├── Step2Module (独立実行機能) - スケルトン生成
├── Step3Module (独立実行機能) - スキニング適用
├── Step4Module (独立実行機能) - スケルトン・スキンウェイトマージ（特化）
└── Step5Module (独立実行機能) - Blender統合・最終FBX出力

データフロー: app.py → Step0 → app.py → Step1 → app.py → Step2 → app.py → Step3 → app.py → Step4 → app.py → Step5 → app.py
```
---

## 🎯 新しい設計概要（2025年6月10日策定）

**変更前**: Step0(アセット保存) → Step1(メッシュ抽出) → Step2(スケルトン) → Step3(スキニング) → Step4(スケルトン・スキンウェイトマージ)

**変更後**: Step0(**アセット保存**) → Step1 → Step2 → Step3 → Step4(**マージ特化**) → Step5(**Blender統合・最終出力**)
**<!-- 修正点: Step0の責務を「ファイル転送のみ」から「アセット保存」に明確化 -->**

## 📋 マイクロサービス化の基本原則（改訂版）

### ❌ フォールバック機能の禁止
- **理由**: フォールバック機能を導入すると、データフローが複雑化し、正しいデータの流れを追跡できなくなるため、システム全体の安定性が低下します。
- **方針**: 各ステップモジュールは、すべての入力データが前段のステップで正しく生成されていることを前提に動作します。エラーが発生した場合は、エラーの原因を修正し、再実行するアプローチを推奨します。

### 🎯 app.py の責務
- **Gradio UI表示**: Webインターフェース（アップロード・ダウンロード・進行表示）
- **ファイル管理**: アップロード・ダウンロード・状態管理
- **データ受け渡し**: 各ステップ間のデータ橋渡し
- **進行管理**: パイプライン全体の進行制御
- **最終出力管理**: FBXファイルのダウンロード提供

### 🔧 Step Modules の責務（改訂版）
**<!-- 修正点: 各ステップの責務と入出力を `app_dataflow.instructions.md` に基づいて正確化 -->**
**⭐ 重要: データフロー、ディレクトリ構造、ファイル命名規則に関する唯一の信頼できる情報源（Single Source of Truth）は `app_dataflow.instructions.md` です。実装時は必ずそちらを参照してください。**

#### 📁 Step 0 Module - Asset Preservation（アセット保存機能）
- **責務**: UV、マテリアル、テクスチャ情報の詳細保存（Step5で使用）
- **入力**: 3Dモデルファイルパス (.glb, .fbx, .obj等)
- **出力**: アセットメタデータJSON、テクスチャファイル群 (`00_asset_preservation/`内)

#### 📦 Step 1 Module - メッシュ抽出
- **責務**: 3Dモデルからメッシュデータを抽出
- **入力**: 3Dモデルファイルパス (.glb, .fbx, .obj等)
- **出力**: **`raw_data.npz` (固定名)**

#### 🦴 Step 2 Module - スケルトン生成
- **責務**: AIによるスケルトン構造の生成
- **入力**: `raw_data.npz`
- **出力**: **`{model_name}.fbx` (サフィックスなし)**, **`predict_skeleton.npz` (固定名)**

#### 🎭 Step 3 Module - スキニング適用
- **責務**: メッシュとスケルトンのバインディング（スキニング）
- **入力**: `raw_data.npz`, `predict_skeleton.npz`, `{model_name}.fbx`
- **出力**: **`{model_name}_skinned_unirig.fbx`**

#### ⚙️ Step 4 Module - 3つのデータソース統合マージ（高度技術）
- **責務**: オリジナルメッシュ・AIスケルトン・AIスキニングの高度な統合処理
- **入力**: 
  - ユーザーアップロードのオリジナルメッシュファイル
  - Step2出力のスケルトンFBXファイル
  - Step3出力のスキニングNPZデータ（メモリ内）
- **核心技術**: KDTree最近傍マッチングによる頂点数差異吸収システム
- **出力**: **`{model_name}_merged.fbx`** (3つのデータソース完全統合済み)

#### 🎨 Step 5 Module - Blender統合・最終出力（新設）
- **責務**: オリジナルモデルのアセット情報とマージ済みモデルを統合し、最終FBXを出力
- **入力**: 
  - アップロードされたオリジナルモデルファイルパス
  - Step4で作成されたマージ済みFBXファイルパス
- **出力**: **`{model_name}_final.fbx`** 及びテクスチャフォルダ **`{model_name}_final.fbm/`**

## 🔧 内部API 仕様（改訂版）

**<!-- 修正点: 詳細なAPI仕様を削除し、共通形式と `app_dataflow` への参照に一本化 -->**
**⭐ 重要: 各ステップ間の具体的なデータ受け渡し（インターフェース）は、`pipeline_state.json` の構造に基づきます。唯一の信頼できる情報源として、必ず `app_dataflow.instructions.md` を参照してください。**

### データ受け渡しインターフェース
```python
# 共通レスポンス形式
def step_function(input_data: dict) -> tuple[bool, str, dict]:
    """
    Args:
        input_data: 入力データ辞書
    
    Returns:
        success: 成功フラグ (True/False)
        logs: 実行ログメッセージ
        output_files: 出力ファイルパス辞書 (pipeline_state.jsonに保存されるキーと値)
    """

### Step 0 Interface（アセット保存機能）

def preserve_assets(input_file: str, model_name: str) -> tuple[bool, str, dict]:
    """
    Args:
        input_file: アップロードされた3Dモデルファイルパス
        model_name: モデル識別名
    
    Returns:
        success: True/False
        logs: "アセット保存完了: /path/to/metadata.json"
        output_files: {
            "asset_metadata_json": "/path/to/{model_name}_asset_metadata.json",
            "asset_metadata_blender_json": "/path/to/{model_name}_asset_metadata_blender.json",
            "textures_dir": "/path/to/textures/"
        }
    """
```

### Step 1 Interface（既存維持）
```python
def extract_mesh(input_file: str, model_name: str) -> tuple[bool, str, dict]:
    """
    Args:
        input_file: 3Dモデルファイルパス
        model_name: モデル識別名
    
    Returns:
        success: True/False
        logs: "メッシュ抽出完了: /path/to/extracted.npz"
        output_files: {
            "extracted_npz": "/path/to/extracted.npz"
        }
    """
```

### Step 2 Interface（既存維持）
```python
def generate_skeleton(model_name: str, gender: str, extracted_file: str) -> tuple[bool, str, dict]:
    """
    Args:
        model_name: モデル識別名
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

### Step 3 Interface（既存維持）
```python
def apply_skinning(model_name: str, mesh_file: str, skeleton_file: str) -> tuple[bool, str, dict]:
    """
    Args:
        model_name: モデル識別名
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

### Step 4 Interface（3つのデータソース統合マージ）
```python
def merge_skeleton_skinning(model_name: str, original_file: str, step2_files: dict, step3_files: dict) -> tuple[bool, str, dict]:
    """
    【重要な技術的発見】Step4は3つのデータソースの高度な統合処理
    
    Args:
        model_name: モデル識別名
        original_file: ユーザーアップロードのオリジナルメッシュファイル（target引数相当）
        step2_files: Step2出力ファイル辞書（source引数相当のスケルトンFBX含む）
        step3_files: Step3出力ファイル辞書（スキニングNPZデータ含む）
    
    データソース統合:
        1. オリジナルメッシュ: 実際の形状・UV・テクスチャ（5,742頂点例）
        2. AIスケルトン: Step2生成ボーン構造（joints, names, parents, tails）
        3. AIスキニング: Step3生成ウェイト情報（2,048頂点例、正規化座標）
    
    核心技術: KDTree最近傍マッチングによる頂点数差異吸収システム
    
    Returns:
        success: True/False
        logs: "3つのデータソース統合マージ完了: /path/to/merged.fbx"
        output_files: {
            "merged_fbx": "/path/to/merged.fbx"
        }
    """
```

### Step 5 Interface（新設）
```python
def integrate_with_blender(model_name: str, original_file: str, merged_file: str) -> tuple[bool, str, dict]:
    """
    Args:
        model_name: モデル識別名
        original_file: アップロードされたオリジナルモデルファイルパス
        merged_file: Step4で作成されたマージ済みFBXファイルパス
    
    Returns:
        success: True/False
        logs: "Blender統合・最終出力完了: /path/to/final.fbx"
        output_files: {
            "final_fbx": "/path/to/final.fbx"
        }
    """
```

## 🚀 実装手順（改訂版）

### 1. app.py の実装 (Gradio UI + データ管理)
```python
# app.py - Gradio UI とデータ受け渡しのみ
def process_complete_pipeline(input_file, gender):
    model_name = generate_model_name(input_file)
    
    # Step 0: ファイル転送のみ
    success, logs, files = transfer_file(input_file, model_name)
    
    # Step 1: メッシュ抽出
    success, logs, files = extract_mesh(input_file, model_name)
    
    # Step 2: スケルトン生成  
    success, logs, files = generate_skeleton(model_name, gender, files["extracted_npz"])
    
    # Step 3: スキニング適用
    success, logs, files = apply_skinning(model_name, files["extracted_npz"], files["skeleton_fbx"])
    
    # Step 4: 3つのデータソース統合マージ（高度技術）
    success, logs, files = merge_skeleton_skinning(model_name, input_file, files["skinned_fbx"], step2_files)
    
    # Step 5: Blender統合・最終出力（新設）
    success, logs, files = integrate_with_blender(model_name, input_file, files["merged_fbx"])
    
    return files["final_fbx"]  # ダウンロード可能なFBXファイル
```



## 🔧 ディレクトリ構成
⭐ 重要: ディレクトリ構造は app_dataflow.instructions.md に定義されたものが正となります。
```
/app/
├── app.py                    # UI + データ受け渡し
├── step_modules/             # 独立実行機能群
│   ├── step0_asset_preservation.py
│   ├── step1_extract.py
│   ├── step2_skeleton.py
│   ├── step3_skinning_unirig.py
│   ├── step4_merge.py
│   └── step5_blender_integration.py
├── pipeline_work/           # データ保存ディレクトリ (構造はapp_dataflow参照)
└── src/                     # 既存のUniRigコア機能
```

🔗 データフロー設計方針とマイクロサービス連携
<!-- 修正点: このセクション全体を `app_dataflow` への参照に置き換え -->
⭐ 重要: データフロー、ファイルパス管理、ファイル命名規則、マイクロサービス間の連携に関する全ての詳細仕様は、
app_dataflow.instructions.md にて一元管理されています。実装の際は必ずこのドキュメントを正としてください。
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

1. **Step 0 サービス実装**: ファイル転送のみ（機能簡略化）
2. **Step 1 サービス実装**: メッシュ抽出マイクロサービス
3. **Step 2 サービス実装**: スケルトン生成マイクロサービス  
4. **Step 3 サービス実装**: スキニングマイクロサービス
5. **Step 4 サービス実装**: スケルトン・スキンウェイトマージマイクロサービス（特化）
6. **Step 5 サービス実装**: Blender統合・最終出力マイクロサービス（新設）
7. **認証・セキュリティ**: API認証とファイルアクセス制御
8. **監視・ログ**: 各サービスの監視とログ集約
9. **負荷分散**: サービス間の負荷分散設定
10. **CI/CD**: 自動テスト・デプロイパイプライン

