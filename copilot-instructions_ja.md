````````markdown
``````instructions
`````instructions
````instructions
# GitHub Copilot Instructions for UniRig 3D Model Rigging System (Reboot Guidance) - 日本語版

## 🎯 オリジナルプロジェクトの概要とミッション（歴史的背景）

### 🏆 オリジナルのコアミッション：「すべてのモデルをリギングする」
オリジナルのUniRigは、自動化されたパイプライン処理を通じて3Dアニメーションを民主化するために設計された**3Dモデル自動リギングアプリケーション**でした。このシステムは、静的な3Dモデルをアニメーション対応のリグ付きアセットに自動的に変換することを目的としていました。

**オリジナルの主な目的**：「3Dモデルを持っている」ことと「それをアニメートできる」ことの間の技術的な障壁を取り除くこと。

### 🎨 オリジナルのユーザーへの価値提案
- **創造的な自由**：技術的なリギングの複雑さではなく、ストーリーテリングに集中できる
- **アクセシビリティ**：専門知識がなくてもプロ品質のリギングが可能
- **時間革命**：数時間/数日かかる手作業を数分の自動処理に変換
- **ユニバーサルソリューション**：多様なモデルカテゴリ（人間、動物、オブジェクト）を単一の統合システムで処理

**リブートに関する注意**：このドキュメントは歴史的な参照資料であり、技術的な洞察を提供します。リブートされるプロジェクトの範囲、ミッション、およびアーキテクチャは、主に `MICROSERVICE_GUIDE.md` と新しい `app.py` の実装によって定義されます。

## 🏗️ アーキテクチャ原則（マイクロサービスに着想を得た内部モジュール）
### 🎯 コア設計思想
リブートされるUniRigは、単一アプリケーション内で**マイクロサービスに着想を得た内部モジュールアーキテクチャ**に従い、オリジナルの設計から教訓を得ます。

```
app.py (UI + データオーケストレーション)
├── Step1Module (独立実行) - 例：メッシュ抽出
├── Step2Module (独立実行) - 例：スケルトン生成
├── Step3Module (独立実行) - 例：スキニング適用
└── Step4Module (独立実行) - 例：テクスチャ統合

データフロー: app.py → Step1 → app.py → Step2 → app.py → Step3 → app.py → Step4 → app.py
```
（リブートのための具体的なモジュールとデータフローは `MICROSERVICE_GUIDE.md` で詳述されます）

### 📋 モジュールの責任分離

#### 🖥️ app.py の責任（リブートの焦点）
- **UI表示**：Gradioウェブインターフェース（または代替）
- **ファイル管理**：アップロード/ダウンロード/状態管理
- **データオーケストレーション**：マイクロサービス間のステップ間データブリッジ
- **進捗管理**：パイプライン全体の進捗管理

#### 🔧 ステップモジュールの責任（リブートの焦点）
各ステップモジュールは、独立した、コンテナ化された、またはその他の方法で分離された実行ユニットとして機能する必要があります。責任は、リブートされたアーキテクチャに基づいてモジュールごとに定義されます。オリジナルコンセプトからの例：

**ステップ1モジュールの例 - メッシュ抽出**
- **目的**：3Dモデルからメッシュジオメトリを抽出する
- **入力**：3Dモデルファイルパス（.glb、.fbx、.objなど）
- **出力**：メッシュデータファイルパス（.npz）+ 保存されたテクスチャメタデータ（例）
- **独立性**：他のステップからの環境汚染なし
- **基盤スクリプト**: このモジュールは、元々 `launch/inference/extract.sh` にあった機能をカプセル化します。このスクリプトは、入力ファイル、出力ディレクトリ、設定ファイル（例：`configs/data/quick_inference.yaml`）、ターゲット面カウントなどのパラメータを指定して `python -m src.data.extract` を呼び出します。

**ステップ2モジュールの例 - スケルトン生成**
- **目的**：AI駆動のスケルトン構造予測
- **入力**：メッシュデータファイルパス（.npz）、性別設定（例）
- **出力**：スケルトンFBXファイルパス、スケルトンデータファイルパス（.npz）（例）
- **独立性**：メッシュ抽出とは独立して実行
- **基盤スクリプト**: このモジュールは `launch/inference/generate_skeleton.sh` の機能をカプセル化します。このスクリプトは、最初に `python -m src.data.extract` を呼び出してメッシュデータ (例: `raw_data.npz`) を準備し、次に `python run.py` をタスク固有の設定 (例: `--task=configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml`) で呼び出してスケルトンを生成します。

**ステップ3モジュールの例 - スキニング適用**
- **目的**：メッシュとスケルトンのバインディング（スキニング）
- **入力**：メッシュデータファイルパス、スケルトンFBXファイルパス（例）
- **出力**：リグ付きFBXファイルパス、スキニングデータファイルパス（.npz）（例）
- **独立性**：前のステージの結果のみを使用し、環境汚染なし
- **基盤スクリプト**: このモジュールは `launch/inference/generate_skin.sh` の機能をカプセル化します。このスクリプトは、まず `launch/inference/extract.sh` を呼び出してメッシュデータを準備し（スケルトン生成と同様）、次に `python run.py` をタスク固有の設定（例: `--task=configs/task/quick_inference_unirig_skin.yaml`）で呼び出してスキニングを適用します。入力として、元のモデル、出力ディレクトリ、およびスケルトンファイルが格納されているディレクトリ（例: `dataset_inference_clean`）を取ります。

**ステップ4モジュールの例 - テクスチャ統合**
- **目的**：オリジナルテクスチャの統合と最終出力
- **入力**：リグ付きFBXファイルパス、オリジナルモデルファイルパス（例）
- **出力**：最終FBXファイルパス（テクスチャ付き）（例）
- **独立性**：テクスチャ処理のみに焦点を当て、他の機能との干渉なし
- **基盤スクリプト**: このモジュールは `launch/inference/merge.sh` の機能をカプセル化します。このスクリプトは `python -m src.inference.merge` を呼び出し、ソース（オリジナルモデル）、ターゲット（スキニング済みモデル）、出力ファイルパスなどのパラメータを渡します。

## 🔧 内部モジュールAPI仕様（リブートガイダンス）

### 📋共通レスポンス形式（推奨）
```python
def step_function(input_data: dict) -> tuple[bool, str, dict]:
    """
    Args:
        input_data: マイクロサービス用の入力データ辞書
    
    Returns:
        success: 成功フラグ (True/False)
        logs: 実行ログメッセージまたは構造化ログデータ
        output_files: 出力ファイルパスまたは識別子の辞書
    """
```

### 🔌 ステップモジュールインターフェース（リブート用に定義予定）
以下は*オリジナル*プロジェクトの例です。リブートでは、特定のモジュールインターフェースは `MICROSERVICE_GUIDE.md` と洗練されたモジュールの責任に基づいて設計されます。

#### 例 Step 1 Module - メッシュ抽出
```python
def extract_mesh(input_file: str, model_name: str) -> tuple[bool, str, dict]:
    """
    Args:
        input_file: 3Dモデルファイルパス
        model_name: モデル識別子名
    
    Returns:
        success: True/False
        logs: "メッシュ抽出完了: /path/to/extracted.npz"
        output_files: {
            "extracted_npz": "/path/to/extracted.npz",
            "texture_metadata": "/path/to/metadata.json"
        }
    """
```

#### 例 Step 2 Module - スケルトン生成
```python
def generate_skeleton(model_name: str, gender: str, extracted_file: str) -> tuple[bool, str, dict]:
    """
    Args:
        model_name: Model identifier name
        gender: "neutral|male|female"
        extracted_file: Extracted mesh file path
    
    Returns:
        success: True/False
        logs: "Skeleton generation complete: /path/to/skeleton.fbx"
        output_files: {
            "skeleton_fbx": "/path/to/skeleton.fbx",
            "skeleton_npz": "/path/to/skeleton.npz"
        }
    """
```
- **目的**: AIによるスケルトン構造の予測
- **入力**: メッシュデータファイルパス (.npz)、性別設定 (例)
- **出力**: スケルトンFBXファイルパス、スケルトンデータファイルパス (.npz) (例)
- **独立性**: メッシュ抽出とは独立して実行
- **基盤スクリプト**: このモジュールは `launch/inference/generate_skeleton.sh` の機能をカプセル化します。このスクリプトは、最初に `python -m src.data.extract` を呼び出してメッシュデータ (例: `raw_data.npz`) を準備し、次に `python run.py` をタスク固有の設定 (例: `--task=configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml`) で呼び出してスケルトンを生成します。

#### 例 Step 3 Module - スキニング適用
```python
def apply_skinning(model_name: str, mesh_file: str, skeleton_file: str) -> tuple[bool, str, dict]:
    """
    Args:
        model_name: モデル識別子名
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
- **目的**: メッシュとスケルトンのバインディング（スキニング）
- **入力**: メッシュデータファイルパス、スケルトンFBXファイルパス（例）
- **出力**: リグ付きFBXファイルパス、スキニングデータファイルパス（.npz）（例）
- **独立性**: 前のステージの結果のみを使用し、環境汚染なし
- **基盤スクリプト**: このモジュールは `launch/inference/generate_skin.sh` の機能をカプセル化します。このスクリプトは、まず `launch/inference/extract.sh` を呼び出してメッシュデータを準備し（スケルトン生成と同様）、次に `python run.py` をタスク固有の設定（例: `--task=configs/task/quick_inference_unirig_skin.yaml`）で呼び出してスキニングを適用します。入力として、元のモデル、出力ディレクトリ、およびスケルトンファイルが格納されているディレクトリ（例: `dataset_inference_clean`）を取ります。

#### 例 Step 4 Module - テクスチャ統合
```python
def merge_textures(model_name: str, skinned_file: str, original_file: str) -> tuple[bool, str, dict]:
    """
    Args:
        model_name: モデル識別子名
        skinned_file: リグ付きFBXファイルパス
        original_file: オリジナルモデルファイルパス
    
    Returns:
        success: True/False
        logs: "テクスチャ統合完了: /path/to/final.fbx"
        output_files: {"final_fbx": "/path/to/final.fbx"}
    """
```
- **目的**: オリジナルのテクスチャ統合と最終出力
- **入力**: リグ済みFBXファイルパス、オリジナルモデルファイルパス（例）
- **出力**: 最終FBXファイルパス（テクスチャ付き）（例）
- **独立性**: テクスチャ処理のみに焦点を当て、他の機能との干渉なし
- **基盤スクリプト**: このモジュールは `launch/inference/merge.sh` の機能をカプセル化します。このスクリプトは `python -m src.inference.merge` を呼び出し、ソース（オリジナルモデル）、ターゲット（スキニング済みモデル）、出力ファイルパスなどのパラメータを渡します。

## ⚠️ Step1-Step4データフロー統合の重要な知見（2025年1月3日追加）

### 🎯 データフロー不整合の根本原因と解決策

#### 🚨 発見された重要な問題
1. **ファイル名規則の不整合**
   ```
   問題: Step2出力 vs 大元フロー期待値
   ├── FBX: {model_name}_skeleton.fbx vs {model_name}.fbx
   ├── NPZ: {model_name}_skeleton.npz vs predict_skeleton.npz
   └── 結果: Step3がStep2の出力を読み込み不可
   ```

2. **ASCII vs バイナリFBX問題**
   ```
   問題: src.inference.merge がASCII FBXをサポートしない
   ├── エラー: "ASCII FBX files are not supported"
   ├── 原因: Blender標準エクスポートがASCII形式
   └── 解決: バイナリFBX生成が必須要件
   ```

3. **Step2実装の真実**
   ```
   発見: Step2は実際にはFBXを生成しない
   ├── 実態: 大元フローを実行してNPZファイルのみ生成
   ├── 方法: 既存FBXファイルをコピーしているだけ
   └── 影響: ファイル名規則の重要性が判明
   ```

#### ✅ 実装された解決策

##### 🔧 Step2ファイル名規則修正（必須パターン）
```python
# ❌ 修正前（非互換）
output_fbx = self.output_dir / f"{model_name}_skeleton.fbx"
output_npz = self.output_dir / f"{model_name}_skeleton.npz"

# ✅ 修正後（大元フロー互換）
output_fbx = self.output_dir / f"{model_name}.fbx"  # サフィックス除去
output_npz = self.output_dir / f"predict_skeleton.npz"  # 固定名（重要）
```

##### 🔧 Step3バイナリFBX生成（必須実装）
```python
def _generate_binary_fbx_background(self, output_path: Path, ...):
    """
    ASCII FBX問題の根本解決
    - バックグラウンドBlender実行による安全性
    - Blender 4.2互換のFBXエクスポート設定
    - use_asciiパラメータ完全除去（Blender 4.2で削除済み）
    """
    blender_script = f"""
import bpy

# バイナリFBXエクスポート（ASCII回避）
bpy.ops.export_scene.fbx(
    filepath="{output_path}",
    use_selection=True,
    add_leaf_bones=True,
    bake_anim=False,
    # ❌ use_ascii=False  <- Blender 4.2で完全削除
)
"""
    # プロセス分離による安全な実行
    cmd = ["blender", "--background", "--python-text", blender_script]
    return subprocess.run(cmd, timeout=300, capture_output=True)
```

##### 🔧 Step3スケルトン読み込み修正（フォールバック設計）
```python
# 大元フロー互換優先検索パターン
skeleton_npz = skeleton_path.parent / "predict_skeleton.npz"
if not skeleton_npz.exists():
    # フォールバック: 従来の形式を検索
    skeleton_npz = skeleton_path.parent / f"{model_name}_skeleton.npz"
    if not skeleton_npz.exists():
        # グレースフルデグラデーション
        self.logger.warning(f"Skeleton NPZ not found: {skeleton_npz}")
        return self._generate_fallback_skeleton()
```

##### 🔧 Step4大元フロー互換メソッド（直接統合）
```python
def _execute_native_merge_flow(self, source: str, target: str, model_name: str):
    """
    merge.sh直接実行による大元フロー完全互換
    - オリジナルスクリプトの直接呼び出し
    - カスタム実装による問題回避
    """
    merge_script = "/app/launch/inference/merge.sh"
    output_file = self.output_dir / f"{model_name}_textured.fbx"
    
    cmd = [merge_script, source, target, str(output_file)]
    success, logs = self._run_command(cmd)
    
    return success, logs, {"textured_fbx": str(output_file)}
```

### 🛡️ 安定性確保の必須パターン

#### 🎯 ファイル名規則の厳格遵守
```python
# 大元フローとの完全互換性が成功の鍵
REQUIRED_FILE_NAMING = {
    "step2_output_fbx": "{model_name}.fbx",  # サフィックスなし
    "step2_output_npz": "predict_skeleton.npz",  # 固定名
    "step3_search_priority": ["predict_skeleton.npz", "{model_name}_skeleton.npz"],
    "step4_final_output": "{model_name}_textured.fbx"
}
```

#### 🔄 エラー許容度設計（グレースフルデグラデーション）
```python
# NPZファイル不足時の適切な処理
def handle_missing_npz(self, expected_path: Path, model_name: str):
    if not expected_path.exists():
        self.logger.warning(f"Expected NPZ not found: {expected_path}")
        # フォールバック処理
        return self._generate_fallback_data(model_name)
    return expected_path
```

#### 🚫 プロセス分離（メモリ汚染防止）
```python
# バックグラウンドBlender実行による安全性
def safe_blender_execution(script: str, timeout: int = 300):
    """
    Blender実行時のメモリ汚染防止
    - プロセス分離による安全性
    - タイムアウト保護
    - エラー出力キャプチャ
    """
    cmd = ["blender", "--background", "--python-text", script]
    result = subprocess.run(cmd, timeout=timeout, capture_output=True, text=True)
    return result.returncode == 0, result.stdout, result.stderr
```

### 📊 検証済み成功パターン

#### ✅ 完全パイプライン動作確認
```python
# 検証済み成功フロー
SUCCESSFUL_PIPELINE = {
    "Step1": "メッシュ抽出 → raw_data.npz",
    "Step2": "スケルトン生成 → {model_name}.fbx + predict_skeleton.npz", 
    "Step3": "スキニング適用 → バイナリFBX出力",
    "Step4": "テクスチャ統合 → 最終FBX（5.2MB）",
    "結果": "エンドツーエンド成功確認済み"
}
```

#### 🎯 重要な成功要因
1. **大元フロー理解**: オリジナルスクリプトとの互換性確保
2. **ファイル名厳格遵守**: わずかな不整合でもパイプライン破綻
3. **段階的検証**: 各ステップの独立テストによる問題特定
4. **プロセス分離**: 外部ツール実行時の安全性確保

### 🔬 今後の実装に向けた重要な教訓

#### 📋 統合前チェックリスト
- [ ] 大元フローとの完全ファイル名互換性確認
- [ ] ASCII/バイナリ形式の明確な仕様確認
- [ ] 各ステップの独立実行テスト
- [ ] エラー時のフォールバック機能実装
- [ ] プロセス分離による安全性確保

#### 🚨 回避すべき危険パターン
```python
# ❌ 危険: ファイル名規則の独自実装
output_file = f"{model_name}_custom_suffix.fbx"  # 大元フロー非互換

# ❌ 危険: ASCII FBX生成
bpy.ops.export_scene.fbx(use_ascii=True)  # src.inference.merge非対応

# ❌ 危険: NPZファイル固定パス仮定
skeleton_data = load_npz("skeleton.npz")  # ファイル名不整合リスク

# ✅ 安全: 大元フロー完全互換
output_file = f"{model_name}.fbx"  # 大元フロー期待値
bpy.ops.export_scene.fbx()  # デフォルトバイナリ
skeleton_npz = find_skeleton_npz_with_fallback()  # 複数パターン検索
```

### 📈 最新のデータフロー改修方針（2025年6月9日採択）
安定性と保守性を確保するため、統一されたデータフロー改修方針が採択されました。この方針は `UNIRIG_PIPELINE_DATAFLOW.md` に詳述されており、ファイルパス、命名規則、ステップ間のデータ管理に関する唯一の信頼できる情報源となります。

**改訂されたデータフローの主要原則:**
1.  **一元管理**: `app.py` とその `FileManager` が、必要な全ての絶対パスを生成し、ステップモジュールに提供する責任を負います。
2.  **標準化されたディレクトリ構造**: 全ての操作は `/app/pipeline_work/{model_name}/` 内で行われ、ステップ固有のサブディレクトリ（例: `00_asset_preservation/`, `01_extracted_mesh/` など）を使用します。
3.  **一貫したファイル命名**: `UNIRIG_PIPELINE_DATAFLOW.md` で指定された名前に準拠し、UniRigコアスクリプト（例: `raw_data.npz`, `predict_skeleton.npz`）との互換性を確保します。
4.  **絶対パスの使用**: ステップモジュールは `FileManager` から提供された絶対パスを使用し、特にサブプロセス呼び出し時の曖昧さを排除します。
5.  **明確な入出力**: 各ステップモジュールには、`UNIRIG_PIPELINE_DATAFLOW.md` に文書化されている通り、明確に定義された入力ファイル要件と出力場所があります。

**データフローにおけるCopilotの役割:**
- ステップモジュールを修正または作成する際、全てのファイル操作（入力の読み取り、出力の書き込み）が、通常はステップ関数への引数として渡されるこの計画から派生したパスと名前に厳密に従うようにしてください。
- 各ステップの具体的なパスとファイル名の詳細については、`UNIRIG_PIPELINE_DATAFLOW.md` を参照してください。
- `run.py` やシェルスクリプトと連携する際、パスに関するコマンドライン引数（`--input_dir`, `--output_dir`, `--npz_dir` など）が、この一元化されたデータフロー計画に従って構築されるようにしてください。

---

### 📈 現在のデータフローリファクタリング計画（2025年6月9日採用）
安定性と保守性を確保するため、統一されたデータフローリファクタリング計画が採用されました。この計画は `UNIRIG_PIPELINE_DATAFLOW.md` に詳述されており、ファイルパス、命名規則、およびステップ間データ管理の唯一の信頼できる情報源として機能します。

**改良されたデータフローの主要原則：**
1.  **集中管理**：`app.py` とその `FileManager` は、必要なすべての絶対パスをステップモジュールに生成して提供する責任があります。
2.  **標準化されたディレクトリ構造**：すべての操作は `/app/pipeline_work/{model_name}/` 内で行われ、`00_asset_preservation/`、`01_extracted_mesh/` などのステップ固有のサブディレクトリがあります。
3.  **一貫したファイル命名**：`UNIRIG_PIPELINE_DATAFLOW.md` で指定された名前に準拠し、コアUniRigスクリプト（`raw_data.npz`、`predict_skeleton.npz`など）との互換性を確保します。
4.  **絶対パス**：ステップモジュールは、特にサブプロセスを呼び出す際のあいまいさを避けるために、`FileManager` によって提供される絶対パスを使用します。
5.  **明確な入力/出力**：各ステップモジュールには、`UNIRIG_PIPELINE_DATAFLOW.md` に記載されているように、明確に定義された入力ファイル要件と出力場所があります。

**データフローにおけるCopilotの役割：**
- ステップモジュールを変更または作成する場合、すべてのファイル操作（入力の読み取り、出力の書き込み）が、通常ステップ関数への引数として渡されるこの計画から派生したパスと名前に厳密に従うようにします。
- 各ステップの特定のパスとファイル名の詳細については、`UNIRIG_PIPELINE_DATAFLOW.md` を参照してください。
- `run.py` またはシェルスクリプトと対話する場合は、パスのコマンドライン引数（`--input_dir`、`--output_dir`、`--npz_dir`など）がこの集中データフロー計画に従って構築されていることを確認してください。
```````
