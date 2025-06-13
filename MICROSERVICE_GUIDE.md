# UniRig マイクロサービス化 実装ガイド (2025年6月10日改訂版)

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

## 🎯 新しい設計概要（2025年6月10日策定）

**変更前**: Step0(アセット保存) → Step1(メッシュ抽出) → Step2(スケルトン) → Step3(スキニング) → Step4(テクスチャ統合)

**変更後**: Step0(ファイル転送のみ) → Step1 → Step2 → Step3 → Step4(マージ特化) → Step5(Blender統合・最終出力)

## 📋 マイクロサービス化の基本原則（改訂版）

### 🎯 app.py の責務
- **Gradio UI表示**: Webインターフェース（アップロード・ダウンロード・進行表示）
- **ファイル管理**: アップロード・ダウンロード・状態管理
- **データ受け渡し**: 各ステップ間のデータ橋渡し
- **進行管理**: パイプライン全体の進行制御
- **最終出力管理**: FBXファイルのダウンロード提供

### 🔧 Step Modules の責務（改訂版）
各ステップは独立した実行機能として設計：

#### 📁 Step 0 Module - ファイル転送のみ（機能簡略化）
- **責務**: アップロードされたモデルをStep1に転送するのみ
- **入力**: 3Dモデルファイルパス (.glb, .fbx, .obj等)
- **出力**: ファイル転送完了フラグのみ
- **独立性**: 最小限の処理、アセット保存機能は廃止
- **実装場所**: `step_modules/step0_asset_preservation.py` (機能簡略化)
- **変更点**: UV・マテリアル・テクスチャ構造の保存機能を完全廃止

#### 📦 Step 1 Module - メッシュ抽出（既存維持）
- **責務**: 3Dモデルからメッシュデータを抽出
- **入力**: 3Dモデルファイルパス (.glb, .fbx, .obj等)
- **出力**: メッシュデータファイルパス (.npz)
- **独立性**: 他ステップの実行環境を汚さない
- **実装場所**: `step_modules/step1_extract.py`
- **内部処理**: `launch/inference/extract.sh` の機能をPython関数としてカプセル化

#### 🦴 Step 2 Module - スケルトン生成（既存維持）
- **責務**: AIによるスケルトン構造の生成
- **入力**: メッシュデータファイルパス (.npz), 性別設定
- **出力**: スケルトンFBXファイルパス, スケルトンデータファイルパス (.npz)
- **独立性**: メッシュ抽出とは独立して実行
- **実装場所**: `step_modules/step2_skeleton.py`
- **内部処理**: `launch/inference/generate_skeleton.sh` の機能をカプセル化

#### 🎭 Step 3 Module - スキニング適用（既存維持）
- **責務**: メッシュとスケルトンのバインディング（スキニング）
- **入力**: メッシュデータファイルパス、スケルトンFBXファイルパス
- **出力**: リグ済みFBXファイルパス、スキニングデータファイルパス (.npz)
- **独立性**: 前のステージの結果のみを使用し、環境汚染なし
- **実装場所**: `step_modules/step3_skinning_unirig.py`
- **内部処理**: `launch/inference/generate_skin.sh` の機能をカプセル化

#### ⚙️ Step 4 Module - スケルトン・スキンウェイトマージ（特化機能）
- **責務**: スケルトンとスキンウェイトのマージに専念
- **入力**: Step1・Step2・Step3の出力ファイル
- **出力**: マージ済みFBXファイルパス
- **独立性**: マージ処理のみに焦点を当て、テクスチャ処理は除外
- **実装場所**: `step_modules/step4_merge.py`
- **変更点**: テクスチャ統合機能を廃止し、マージ処理に特化
- **内部処理**: `launch/inference/merge.sh` の機能を活用したマージ処理

#### 🎨 Step 5 Module - Blender統合・最終出力（新設）
- **責務**: オリジナルモデルとマージモデルのBlender統合・最終FBX出力
- **入力**: 
  - アップロードされたオリジナルモデルファイルパス
  - Step4で作成されたマージ済みFBXファイルパス
- **出力**: テクスチャ・マテリアル・UV統合済み最終FBXファイルパス
- **独立性**: Blender背景実行による安全な統合処理
- **実装場所**: `step_modules/step5_blender_integration.py` (新設)
- **処理フロー**:
  1. オリジナルモデルをBlenderファイルに変換
  2. マージモデルをBlenderファイルに変換
  3. マージモデルにオリジナルモデルのマテリアル・テクスチャ・UVを移植
  4. 統合結果をFBXに変換
  5. app.pyに最終FBXファイルパスを返却

## 🔧 内部API 仕様（改訂版）

### データ受け渡しインターフェース
```python
# 共通レスポンス形式（維持）
def step_function(input_data: dict) -> tuple[bool, str, dict]:
    """
    Args:
        input_data: 入力データ辞書
    
    Returns:
        success: 成功フラグ (True/False)
        logs: 実行ログメッセージ
        output_files: 出力ファイルパス辞書
    """
```

### Step 0 Interface（機能簡略化）
```python
def transfer_file(input_file: str, model_name: str) -> tuple[bool, str, dict]:
    """
    Args:
        input_file: アップロードされた3Dモデルファイルパス
        model_name: モデル識別名
    
    Returns:
        success: True/False
        logs: "ファイル転送完了"
        output_files: {} (空の辞書・ファイル出力なし)
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

### Step 4 Interface（マージ特化）
```python
def merge_skeleton_skinning(model_name: str, step1_files: dict, step2_files: dict, step3_files: dict) -> tuple[bool, str, dict]:
    """
    Args:
        model_name: モデル識別名
        step1_files: Step1出力ファイル辞書
        step2_files: Step2出力ファイル辞書  
        step3_files: Step3出力ファイル辞書
    
    Returns:
        success: True/False
        logs: "スケルトン・スキンウェイトマージ完了: /path/to/merged.fbx"
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
    
    # Step 4: スケルトン・スキンウェイトマージ（特化）
    success, logs, files = merge_skeleton_skinning(model_name, step1_files, step2_files, step3_files)
    
    # Step 5: Blender統合・最終出力（新設）
    success, logs, files = integrate_with_blender(model_name, input_file, files["merged_fbx"])
    
    return files["final_fbx"]  # ダウンロード可能なFBXファイル
```

### 2. Step Module 実装例（改訂版）
```python
# step_modules/step0_asset_preservation.py （機能簡略化）
def transfer_file(input_file: str, model_name: str) -> tuple[bool, str, dict]:
    """シンプルファイル転送のみ"""
    try:
        # アセット保存機能は廃止
        # ファイル転送完了のみ確認
        input_path = Path(input_file)
        if input_path.exists():
            self.logger.info(f"ファイル転送確認: {input_file}")
            return True, f"ファイル転送完了: {input_file}", {}
        else:
            return False, f"ファイルが見つかりません: {input_file}", {}
            
    except Exception as e:
        return False, f"ファイル転送エラー: {e}", {}
```

```python
# step_modules/step4_merge.py （マージ特化）
def merge_skeleton_skinning(model_name: str, step1_files: dict, step2_files: dict, step3_files: dict) -> tuple[bool, str, dict]:
    """スケルトン・スキンウェイトマージに特化"""
    try:
        # テクスチャ統合機能を廃止、マージ処理のみ
        # launch/inference/merge.sh の機能を活用
        
        extracted_npz = step1_files["extracted_npz"]
        skeleton_fbx = step2_files["skeleton_fbx"] 
        skinned_fbx = step3_files["skinned_fbx"]
        
        # マージ処理実行
        output_path = f"/app/pipeline_work/04_merge/{model_name}_merged.fbx"
        
        # スケルトンとスキンウェイトのマージ
        success = self._execute_merge_process(skeleton_fbx, skinned_fbx, output_path)
        
        if success:
            return True, f"マージ完了: {output_path}", {"merged_fbx": output_path}
        else:
            return False, "マージ処理失敗", {}
            
    except Exception as e:
        return False, f"マージエラー: {e}", {}
```

```python
# step_modules/step5_blender_integration.py （新設）
def integrate_with_blender(model_name: str, original_file: str, merged_file: str) -> tuple[bool, str, dict]:
    """Blender統合・最終FBX出力"""
    try:
        # 処理フロー:
        # 1. オリジナルモデルをBlenderファイルに変換
        original_blend = self._convert_to_blender(original_file)
        
        # 2. マージモデルをBlenderファイルに変換  
        merged_blend = self._convert_to_blender(merged_file)
        
        # 3. マージモデルにオリジナルモデルのマテリアル・テクスチャ・UVを移植
        integrated_blend = self._transplant_materials(merged_blend, original_blend)
        
        # 4. 統合結果をFBXに変換
        final_fbx = f"/app/pipeline_work/05_final/{model_name}_final.fbx"
        success = self._convert_to_fbx(integrated_blend, final_fbx)
        
        if success:
            return True, f"Blender統合完了: {final_fbx}", {"final_fbx": final_fbx}
        else:
            return False, "Blender統合失敗", {}
            
    except Exception as e:
        return False, f"Blender統合エラー: {e}", {}
```

### 3. app.py での Module 呼び出し実装（改訂版）
```python
# app.py
from step_modules.step0_asset_preservation import transfer_file
from step_modules.step1_extract import extract_mesh
from step_modules.step2_skeleton import generate_skeleton
from step_modules.step3_skinning_unirig import apply_skinning
from step_modules.step4_merge import merge_skeleton_skinning  # 特化機能
from step_modules.step5_blender_integration import integrate_with_blender  # 新設

def call_microservice_step0(input_file: str, model_name: str):
    """Step0 Module を直接呼び出し（機能簡略化）"""
    return transfer_file(input_file, model_name)

def call_microservice_step4(model_name: str, step1_files: dict, step2_files: dict, step3_files: dict):
    """Step4 Module を直接呼び出し（マージ特化）"""
    return merge_skeleton_skinning(model_name, step1_files, step2_files, step3_files)

def call_microservice_step5(model_name: str, original_file: str, merged_file: str):
    """Step5 Module を直接呼び出し（新設）"""
    return integrate_with_blender(model_name, original_file, merged_file)
```

## 🔧 ディレクトリ構成

```
/app/
├── app.py                    # UI + データ受け渡し
├── step_modules/             # 独立実行機能群
│   ├── __init__.py
│   ├── step1_extract.py     # メッシュ抽出モジュール
│   ├── step2_skeleton.py    # スケルトン生成モジュール
│   ├── step3_skinning_unirig.py    # スキニング適用モジュール
│   ├── step4_merge.py       # スケルトンとスキンウェイトのマージモジュール
│   └── step5_blender_integration.py # UV マテリアル　テクスチャの復元モジュール
├── pipeline_work/           # データ保存ディレクトリ
│   ├── 01_extracted_mesh/
│   ├── 02_skeleton/
│   ├── 03_skinning/
│   ├── 04_merge/
│   └── 05_blender_integration/
└── src/                     # 既存のUniRigコア機能
    ├── data/extract.py      # Step1で使用
    ├── inference/           # Step2, Step3で使用
    └── ...
```

## 🔗 データフロー設計方針とマイクロサービス連携 (2025年6月9日策定)

UniRigのマイクロサービス風内部モジュールアーキテクチャを効果的に機能させるためには、各モジュール（ステップ）間のデータフローが明確かつ一貫していることが不可欠です。このため、以下のデータフロー設計方針が策定され、全てのステップモジュール開発の基礎となります。詳細は `UNIRIG_PIPELINE_DATAFLOW.md` を参照してください。

### 1. 基本方針

パイプライン全体の安定性と保守性を向上させるため、各ステップ間のデータの受け渡しを明確化し、ファイルパスと命名規則を一元的に管理します。`UNIRIG_PIPELINE_DATAFLOW.md` を設計の基礎とし、これに準拠した実装を目指します。

### 2. ディレクトリ構造とパス管理

-   **ルート作業ディレクトリ**: `/app/pipeline_work/` (`PIPELINE_DIR`) を使用します。
-   **モデルごとの作業ディレクトリ**: `{PIPELINE_DIR}/{model_name}/` 内に、各ステップの出力は専用サブディレクトリ（例: `01_extracted_mesh/`, `02_skeleton/`）に格納されます。
-   **パスの提供**: `app.py` の `FileManager` が、これらの構造に基づき、各ステップモジュール（マイクロサービス）に必要な入力ファイルの絶対パスと出力ディレクトリの絶対パスを提供します。
-   **モジュール内のパス利用**: 各ステップモジュールは、渡された絶対パスをそのまま使用します。これにより、モジュール自体のロジック内で複雑なパス計算を行う必要がなくなり、独立性が高まります。

### 3. ファイル命名規則

-   `UNIRIG_PIPELINE_DATAFLOW.md` で定義されたファイル名（例: `raw_data.npz`, `{model_name}.fbx`, `predict_skeleton.npz`）を厳守します。これにより、各ステップモジュールは期待される入力ファイルを確実に見つけ、後続モジュールが利用可能な形式で出力ファイルを提供できます。

### 4. マイクロサービス間の連携

-   `app.py` がオーケストレーターとして機能し、あるステップモジュールの出力を次のステップモジュールの入力として正確にマッピングします。このマッピングは、上記のディレクトリ構造とファイル命名規則に依存します。
-   例えば、Step1 (`extract_mesh`) が `/app/pipeline_work/{model_name}/01_extracted_mesh/raw_data.npz` を出力すると、`app.py` はこのパスを Step2 (`generate_skeleton`) の入力として渡します。

この統一されたデータフロー方針に従うことで、各ステップモジュールはより独立して開発・テスト可能になり、システム全体の信頼性が向上します。

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

## 🎯 2025年6月10日 重大更新: 6ステップマイクロサービス構成実装

### 🚀 新設計概要の実装完了
新しいマイクロサービス風内部モジュール構成:

**変更前**: Step0(アセット保存) → Step1(メッシュ抽出) → Step2(スケルトン) → Step3(スキニング) → Step4(テクスチャ統合)

**変更後**: Step0(ファイル転送のみ) → Step1 → Step2 → Step3 → Step4(マージ特化) → Step5(Blender統合・最終出力)

### 🔧 Step4マージ特化実装
Step4はスケルトン・スキンウェイトのマージに特化し、テクスチャ統合機能は新設のStep5に移動:

```python
# Step4マージ特化実装
class Step4Merge:
    def merge_skeleton_skinning(self, step1_files: dict, step2_files: dict, step3_files: dict) -> Tuple[bool, str, Dict]:
        """スケルトンとスキンウェイトのマージに専念"""
        
        # Step1のメッシュデータ読み込み
        mesh_data = self._load_step1_data(step1_files["extracted_npz"])
        
        # Step2のスケルトンデータ読み込み
        skeleton_data = self._load_step2_data(step2_files["skeleton_npz"])
        
        # Step3のスキニングデータ読み込み
        skinning_data = self._load_step3_data(step3_files["skinned_fbx"])
        
        # マージ処理実行（テクスチャ統合機能は除外）
        merged_fbx = self._execute_merge_process(mesh_data, skeleton_data, skinning_data)
        
        return True, f"マージ完了: {merged_fbx}", {"merged_fbx": merged_fbx}
```

### 🎨 Step5Blender統合新設実装
Step5では、オリジナルモデルの完全なマテリアル・テクスチャ・UV復元処理を実行:

```python
# Step5Blender統合新設実装
class Step5BlenderIntegration:
    def integrate_with_blender(self, original_file: str, merged_file: str) -> Tuple[bool, str, Dict]:
        """Blender統合・最終FBX出力"""
        
        # 段階1: オリジナルモデルのBlender変換
        original_blend = self._convert_original_to_blender(original_file)
        
        # 段階2: マージモデルのBlender変換
        merged_blend = self._convert_merged_to_blender(merged_file)
        
        # 段階3: マテリアル・テクスチャ・UV移植
        integrated_blend = self._transplant_materials(merged_blend, original_blend)
        
        # 段階4: 最終FBX出力
        final_fbx = self._export_final_fbx(integrated_blend)
        
        return True, f"Blender統合完了: {final_fbx}", {"final_fbx": final_fbx}
```

### 🔧 旧Step4Merge実装の技術的参考資料
以下は、データフロー改修で実装されたStep4Merge 5段階処理フローの技術的参考資料です。
新設計では、この機能をStep4（マージ特化）とStep5（Blender統合）に分割しています。

#### 参考: 段階的データ抽出システム
```python
# 参考実装: Step1・Step2のNPZファイルからデータ読み込み
def _reference_data_extraction(self, model_name: str) -> Dict:
    """技術的参考: NPZファイルからのデータ抽出パターン"""
    
    pipeline_work_dir = Path("/app/pipeline_work") / model_name
    step1_dir = pipeline_work_dir / "01_extracted_mesh"
    step2_dir = pipeline_work_dir / "02_skeleton"
    
    # 核心技術: allow_pickle=True での UniRig NPZファイル読み込み
    raw_data = np.load(step1_dir / "raw_data.npz", allow_pickle=True)
    skeleton_data = np.load(step2_dir / "predict_skeleton.npz", allow_pickle=True)
    
    # 構造化データ変換
    mesh_data = {
        "vertices": raw_data.get("vertices", np.array([])),
        "faces": raw_data.get("faces", np.array([])),
        "vertex_normals": raw_data.get("vertex_normals", np.array([])),
        "uv_coords": raw_data.get("uv_coords", np.array([])),
        "materials": raw_data.get("materials", []),
        "vertex_count": len(raw_data.get("vertices", []))
    }
    
    skeleton_info = {
        "joints": skeleton_data.get("joints", np.array([])),
        "tails": skeleton_data.get("tails", np.array([])),
        "names": skeleton_data.get("names", []),
        "parents": skeleton_data.get("parents", np.array([])),
        "bone_count": len(skeleton_data.get("names", []))
    }
    
    return {
        "success": True,
        "mesh_data": mesh_data,
        "skeleton_data": skeleton_info,
        "extraction_method": "reference_implementation"
    }
```

#### 参考: バイナリFBX生成システム
```python
# 参考実装: ASCII FBX互換性問題の根本解決
def _reference_binary_fbx_generation(self, output_fbx_path: Path, skeleton_fbx_path: Path) -> bool:
    """技術的参考: src.inference.merge互換のバイナリFBX生成パターン"""
    
    # Blender背景実行でバイナリFBX生成
    blender_script = f'''
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath="{skeleton_fbx_path}")
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.fbx(
    filepath="{output_fbx_path}",
    use_selection=True,
    add_leaf_bones=True,
    bake_anim=False
    # 注意: use_ascii=False はBlender 4.2で削除済み
    # デフォルトでバイナリ形式になる
)
bpy.ops.wm.quit_blender()
'''
    
    # プロセス分離でのBlender実行
    cmd = ["blender", "--background", "--python-expr", blender_script]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    return result.returncode == 0
```

#### 参考: クロスプラットフォーム対応技術
```python
# 参考実装: src.inference.merge直接呼び出しパターン
def _reference_cross_platform_merge(self, skinned_fbx: str, original_model: str, output_path: str) -> bool:
    """技術的参考: Windows環境でのmerge.sh実行問題回避パターン"""
    
    try:
        # クロスプラットフォーム対応: シェルスクリプト依存排除
        from src.inference.merge import transfer
        
        # 核心技術: transfer()関数の直接呼び出し
        transfer(
            source=original_model,
            target=skinned_fbx, 
            output=output_path
        )
        
        return True
        
    except Exception as e:
        self.logger.error(f"Reference merge implementation failed: {e}")
        return False
```

### 📊 新設計の技術的意義と利点

#### 解決した設計課題
1. **責務分離の明確化**: Step4（マージ特化）とStep5（Blender統合）の明確な機能分離
2. **Step0の簡略化**: アセット保存機能廃止によるパイプライン簡素化
3. **処理フローの最適化**: オリジナルモデルの特性保持とリグ処理の分離
4. **開発・保守性向上**: 各ステップの独立性強化

#### 新6ステップ構成の技術的優位性
- **Step0**: ファイル転送のみ → シンプルな入力検証
- **Step1-3**: 従来通り → 既存の実装資産活用
- **Step4**: マージ特化 → スケルトン・スキンウェイト処理に集中
- **Step5**: Blender統合 → オリジナルモデルの完全復元処理

#### 実装における重要な技術的継承
新設計においても、データフロー改修で確立された以下の技術的パターンを継承します：

1. **ファイル命名規則の厳守**: `raw_data.npz`, `predict_skeleton.npz` などの固定名
2. **バイナリFBX生成**: ASCII FBX互換性問題の回避技術
3. **プロセス分離**: 外部プロセス実行時の安全性確保
4. **絶対パス管理**: `FileManager`による統一パス生成

この新設計により、UniRigは6ステップのマイクロサービス風内部モジュール構成で、より安定した3Dモデル自動リギングシステムを実現します。

---

**注意**: 上記の「旧Step4Merge実装の技術的参考資料」は、データフロー改修で実装された貴重な技術資産です。新設計のStep4とStep5の実装において、これらの技術的パターンを適切に活用することを推奨します。
