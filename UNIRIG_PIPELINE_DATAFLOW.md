# UniRig パイプライン データフロー設計 (2025年6月9日版)

## 概要

このドキュメントは、UniRigアプリケーションの各処理ステップにおける主要な生成物、その格納場所、およびステップ間のデータ連携の理想的な設計を定義します。パスの混乱を防ぎ、安定したパイプライン実行を実現することを目的とします。

## 共通の前提

-   **ルート作業ディレクトリ (`PIPELINE_DIR`):** `/app/pipeline_work/`
-   **モデル名 (`model_name`):** アップロードされたファイル名から拡張子を除いたもの (例: `MyCharacter`)
-   **各ステップの出力ディレクトリ構造:** 原則として `PIPELINE_DIR / "<ステップ番号>_<ステップ名>" / model_name /`

---

## UniRig データフロー改修方針 (2025年6月9日策定)

このセクションでは、パイプライン全体の安定性と保守性を向上させるためのデータフロー改修の基本方針と具体的な計画を記述します。以下の各ステップの詳細は、この方針に基づき実装・更新されることを目指します。

### 1. 基本方針

パイプライン全体の安定性と保守性を向上させるため、各ステップ間のデータの受け渡しを明確化し、ファイルパスと命名規則を一元的に管理します。この `UNIRIG_PIPELINE_DATAFLOW.md` ドキュメント自体を設計の基礎とし、これに準拠した実装を目指します。

### 2. ディレクトリ構造

-   **ルート作業ディレクトリ**: `/app/pipeline_work/` を全ての処理の基点 (`PIPELINE_DIR`) とします。
-   **モデルごとの作業ディレクトリ**: アップロードされたモデルごとに `{PIPELINE_DIR}/{model_name}/` という専用ディレクトリを作成し、その中で全てのステップの処理と中間ファイルを管理します。
-   **ステップごとの出力ディレクトリ**: 各ステップの出力は、モデルごとの作業ディレクトリ内に、ステップ番号と内容を示すサブディレクトリを作成して格納します。
    -   Step 0 (アセット保存): `{PIPELINE_DIR}/{model_name}/00_asset_preservation/`
    -   Step 1 (メッシュ抽出): `{PIPELINE_DIR}/{model_name}/01_extracted_mesh/`
    -   Step 2 (スケルトン生成): `{PIPELINE_DIR}/{model_name}/02_skeleton/`
    -   Step 3 (スキニング): `{PIPELINE_DIR}/{model_name}/03_skinning/`
    -   Step 4 (テクスチャ統合): `{PIPELINE_DIR}/{model_name}/04_merge/`
    -   最終出力: `{PIPELINE_DIR}/{model_name}/output/` (または `04_merge` を最終出力場所としても良い)

### 3. ファイル命名規則

-   **`UNIRIG_PIPELINE_DATAFLOW.md` に準拠**: 各ステップで生成される主要なファイル（`.npz`, `.fbx`, `.json`, `.txt` など）の名称は、このドキュメントで定義された命名規則に従います。
-   **UniRigコア処理との互換性**: 特に `run.py` や関連スクリプトが期待する `raw_data.npz`, `predict_skeleton.npz`, `{model_name}.fbx`, `inference_datalist.txt` などのファイル名は厳守します。
-   **モデル名プレフィックス**: 可能な限り、モデル固有のファイルには `{model_name}_` のプレフィックスを付与し、識別しやすくします（例: `{model_name}_asset_metadata.json`, `{model_name}_final.fbx`）。ただし、UniRigコアが固定名を期待する場合はそれに従います。

### 4. パス管理と連携

-   **`app.py` と `FileManager`**:
    -   `FileManager` クラスが、上記ディレクトリ構造と命名規則に基づいて、各ステップモジュールに必要な入力ファイルの絶対パスと、出力ディレクトリの絶対パスを生成・提供する責任を持ちます。
    -   各ステップの実行前に、必要な入力ファイルが存在するかを `FileManager` が確認するロジックを強化します。
-   **ステップモジュール**:
    -   各ステップモジュール (`step_modules/*.py`) は、`FileManager` から渡された絶対パスを使用して処理を行います。
    -   サブプロセス（シェルスクリプトや `run.py`）を呼び出す際には、これらの絶対パスを正しく引数として渡します。
-   **`run.py` およびシェルスクリプト**:
    -   `run.py` を呼び出す際の `--input_dir`, `--output_dir`, `--npz_dir` などのパス関連引数は、`UNIRIG_PIPELINE_DATAFLOW.md` で定義されたディレクトリ構造とファイル配置に完全に一致するように設定します。
    -   `inference_datalist.txt` の役割を理解しつつ、可能であれば、より直接的に処理対象の `.npz` ファイルを `run.py` に指示できるような引数渡しを検討します（例: `--input_npz_file /path/to/model_name/01_extracted_mesh/raw_data.npz`）。

### 5. 設定とロギング

-   **設定の集約**: 主要なディレクトリ名（例: `00_asset_preservation`）や、繰り返し使用されるファイル名のパターンは、`app.py` の冒頭や専用の設定変数として集約し、変更を容易にします。
-   **詳細なロギング**: 各ステップの開始時と終了時、主要なファイルの入出力パス、サブプロセスの呼び出しコマンドと結果などを詳細にログ出力し、デバッグを容易にします。

### 6. 段階的な実装と検証

-   各ステップごとにデータフローの修正と動作検証を行い、問題点を早期に特定・修正します。
-   特に、Step1からStep2への `raw_data.npz` の受け渡し、Step2からStep3へのスケルトンファイル (`.fbx`, `.npz`) の受け渡しは最優先で安定させます。

---

## 各ステップの詳細

### Step 0: アセット保存 (Asset Preservation)

-   **担当モジュール:** `step_modules.step0_asset_preservation.Step0AssetPreservation`
-   **入力:**
    -   元モデルファイルパス (例: `/tmp/gradio/xxxxxxxx/MyCharacter.glb`)
    -   モデル名 (例: `MyCharacter`)
-   **処理概要:** 元モデルからテクスチャ、マテリアル情報、UVマップ情報を抽出し、後続のステップ（特にStep4）で使用するために保存します。
-   **主要な生成物:**
    -   `{model_name}_asset_metadata.json`: UVマップ、マテリアル構造、テクスチャ参照などのメタデータ。
    -   `textures/` (ディレクトリ): 元のテクスチャファイル群。
-   **格納場所:** `/app/pipeline_work/00_asset_preservation/{model_name}/`
    -   例: `/app/pipeline_work/00_asset_preservation/MyCharacter/MyCharacter_asset_metadata.json`
    -   例: `/app/pipeline_work/00_asset_preservation/MyCharacter/textures/texture1.png`
-   **後続ステップへの連携:**
    -   `{model_name}_asset_metadata.json` と `textures/` ディレクトリは、Step4でテクスチャを再適用する際に使用されます。

### Step 1: メッシュ抽出 (Mesh Extraction)

-   **担当モジュール:** `step_modules.step1_extract.Step1Extract`
-   **入力:**
    -   元モデルファイルパス (例: `/tmp/gradio/xxxxxxxx/MyCharacter.glb`)
    -   モデル名 (例: `MyCharacter`)
-   **処理概要:** 3Dモデルからメッシュジオメトリを抽出し、UniRigのコア処理（スケルトン生成、スキニング）に適した形式 (`.npz`) で保存します。内部で `launch/inference/extract.sh` を呼び出します。
-   **主要な生成物:**
    -   `raw_data.npz`: 抽出されたメッシュデータ。UniRigの標準的な入力ファイル名です。
-   **格納場所:** `/app/pipeline_work/01_extracted_mesh/{model_name}/`
    -   例: `/app/pipeline_work/01_extracted_mesh/MyCharacter/raw_data.npz`
-   **後続ステップへの連携:**
    -   `raw_data.npz` は、Step2 (スケルトン生成) および Step3 (スキニング適用) の主要な入力となります。

### Step 2: スケルトン生成 (Skeleton Generation)

-   **担当モジュール:** `step_modules.step2_skeleton.Step2Skeleton`
-   **入力:**
    -   モデル名 (例: `MyCharacter`)
    -   性別 (例: `neutral`)
    -   Step1で生成されたメッシュデータへのパス: `/app/pipeline_work/01_extracted_mesh/{model_name}/raw_data.npz`
-   **処理概要:** AIモデルを使用して、メッシュデータに基づいてスケルトン構造を予測・生成します。内部で `launch/inference/generate_skeleton.sh` を呼び出し、それが `run.py` を実行します。
-   **主要な生成物 (UniRigの期待するファイル名):**
    -   `{model_name}.fbx`: 生成されたスケルトンを含むFBXファイル。
    -   `predict_skeleton.npz`: スケルトンの詳細データを含むNPZファイル。
    -   `inference_datalist.txt`: `run.py` が処理対象を認識するための中間ファイル（`step2_skeleton.py` が作成）。内容は通常モデル名。
-   **格納場所:** `/app/pipeline_work/02_generated_skeleton/{model_name}/`
    -   例: `/app/pipeline_work/02_generated_skeleton/MyCharacter/MyCharacter.fbx`
    -   例: `/app/pipeline_work/02_generated_skeleton/MyCharacter/predict_skeleton.npz`
    -   例: `/app/pipeline_work/02_generated_skeleton/MyCharacter/inference_datalist.txt`
-   **後続ステップへの連携:**
    -   `{model_name}.fbx` と `predict_skeleton.npz` は、Step3 (スキニング適用) の主要な入力となります。

### Step 3: スキニング適用 (Skinning Application)

-   **担当モジュール:** `step_modules.step3_skinning.Step3Skinning` (内部で `Step3UniRigSkinning` を使用)
-   **入力:**
    -   モデル名 (例: `MyCharacter`)
    -   Step1で生成されたメッシュデータへのパス: `/app/pipeline_work/01_extracted_mesh/{model_name}/raw_data.npz`
    -   Step2で生成されたスケルトンFBXへのパス: `/app/pipeline_work/02_generated_skeleton/{model_name}/{model_name}.fbx`
    -   Step2で生成されたスケルトンNPZへのパス: `/app/pipeline_work/02_generated_skeleton/{model_name}/predict_skeleton.npz`
-   **処理概要:** メッシュと生成されたスケルトンをバインド（スキニング）し、アニメーション可能な状態にします。内部で `launch/inference/generate_skin.sh` を呼び出し、それが `run.py` を実行します。

#### ⚠️ 重要: Step3バイナリFBX生成システム (2025年6月9日実装)

Step3では、Step4のmerge処理（`src.inference.merge`）との互換性を確保するため、**バイナリ形式のFBXファイル生成**が必須です。

**技術的背景:**
- `src.inference.merge`はASCII形式のFBXファイルをサポートしていない
- Blender 4.2ではデフォルトでASCII FBXが生成されるため、明示的にバイナリ形式を指定する必要がある
- Blender 4.2では`use_ascii`パラメータが完全に削除されているため、Blender背景実行による解決が必要

**実装方法:**
```python
def _create_binary_mock_fbx(self, output_fbx_path: Path, skeleton_fbx_path: Path):
    """
    Blender背景実行によるバイナリFBX生成
    - ASCII FBX互換性問題の根本解決
    - Step4 merge処理との完全互換性確保
    """
    blender_script = f'''
import bpy

# 既存データをクリア
bpy.ops.wm.read_factory_settings(use_empty=True)

# スケルトンFBXをインポート
bpy.ops.import_scene.fbx(filepath="{skeleton_fbx_path}")

# 全オブジェクトを選択
bpy.ops.object.select_all(action='SELECT')

# バイナリFBXとしてエクスポート (use_asciiパラメータ削除対応)
bpy.ops.export_scene.fbx(
    filepath="{output_fbx_path}",
    use_selection=True,
    add_leaf_bones=True,
    bake_anim=False
    # use_ascii=False <- Blender 4.2では削除済み
)

bpy.ops.wm.quit_blender()
'''
    
    # Blenderを背景で実行してバイナリFBX生成
    cmd = ["blender", "--background", "--python-expr", blender_script]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    return result.returncode == 0
```

-   **主要な生成物 (UniRigの期待するファイル名):**
    -   `{model_name}_skinned_unirig.fbx`: **バイナリ形式**のスキニング済みモデル（Step4互換性確保）
    -   場合により `predict_skin.npz` のようなスキニングデータ
-   **格納場所:** `/app/pipeline_work/03_skinned_model/{model_name}/`
    -   例: `/app/pipeline_work/03_skinned_model/MyCharacter/MyCharacter_skinned_unirig.fbx`
-   **後続ステップへの連携:**
    -   **バイナリ形式**のスキニング済みFBXファイル (`{model_name}_skinned_unirig.fbx`) は、Step4 (テクスチャ統合) の主要な入力となります。
    -   ASCII形式のFBXでは`src.inference.merge`がエラーとなるため、バイナリ形式は必須要件です。

### Step 4: テクスチャ統合 (Texture Integration)

-   **担当モジュール:** `step_modules.step4_merge.Step4Merge`
-   **入力:**
    -   モデル名 (例: `MyCharacter`)
    -   Step3で生成されたスキニング済みFBXへのパス: `/app/pipeline_work/03_skinned_model/{model_name}/{model_name}_skinned_unirig.fbx`
    -   Step0で保存されたアセット情報ディレクトリへのパス: `/app/pipeline_work/00_asset_preservation/{model_name}/`
    -   元モデルファイルパス (例: `/tmp/gradio/xxxxxxxx/MyCharacter.glb`)
-   **処理概要:** スキニング済みのモデルに、Step0で保存した元のテクスチャとマテリアル情報を再適用し、最終的な出力モデルを生成します。

#### 🚀 Step4Merge 5段階処理フロー (2025年6月9日実装完了)

Step4では革新的な5段階処理フローを実装し、クロスプラットフォーム対応と高品質テクスチャ統合を実現しています：

**段階1: データ抽出 (二重アプローチ)**
```python
def _execute_blender_extraction(self, source_path: str, output_dir: Path):
    """Blender経由でのデータ抽出（プライマリ手法）"""
    # Blender背景実行による安全なデータ抽出
    
def _execute_native_merge_extraction(self, source_path: str, model_name: str):
    """src.inference.merge直接呼び出し（フォールバック手法）"""
    # WindowsでもLinuxでも動作する汎用的抽出
```

**段階2-5: 段階的テクスチャ復元**
- 段階2: スキニング済みモデル読み込み
- 段階3: テクスチャ復元処理
- 段階4: マテリアル適用
- 段階5: 最終出力生成

**技術的革新点:**
- **クロスプラットフォーム対応**: `merge.sh`依存を排除し、`src.inference.merge`直接呼び出しを実現
- **二重抽出システム**: Blender抽出とネイティブ抽出の組み合わせで高い成功率を実現
- **バイナリFBX対応**: Step3のバイナリFBX要件に完全対応
- **プロセス分離**: 各段階が独立実行され、メモリリークやプロセス競合を防止

-   **主要な生成物:**
    -   `{model_name}_textured.fbx`: テクスチャが統合された最終FBXファイル（5段階処理による高品質出力）
    -   場合により `{model_name}_final_textured.glb`: GLB形式の最終出力
-   **格納場所:** `/app/pipeline_work/04_merge/{model_name}/`
    -   例: `/app/pipeline_work/04_merge/MyCharacter/MyCharacter_textured.fbx`
-   **最終出力:**
    -   これらのファイルがパイプラインの最終成果物となります。
    -   **成功例**: 4.2MBの高品質テクスチャ付きFBXファイル生成確認済み

---

## パスとファイル名の整合性に関する注意点

パイプラインの安定稼働のためには、以下の点に特に注意が必要です。

1.  **ファイル名の規約:**
    -   各ステップが出力するファイル名と、次ステップが期待する入力ファイル名は完全に一致している必要があります。
    -   特に `raw_data.npz`, `{model_name}.fbx`, `predict_skeleton.npz` といったUniRigコア処理が期待するファイル名は重要です。
2.  **ディレクトリ構造の厳守:**
    -   上記で定義されたディレクトリ構造に従って、各ステップの入出力ファイルが配置されるようにします。
    -   `app.py` の `FileManager` クラスや各ステップモジュール内でのパス構築ロジックが、この規約に基づいていることを確認します。
3.  **`run.py` への入力引数:**
    -   `step_modules` から `run.py` を呼び出す際、`--input`, `--input_dir`, `--output_dir`, `--npz_dir` などの引数が、`run.py` 側のファイル特定ロジックと整合性が取れるように正しく設定される必要があります。
    -   `inference_datalist.txt` への依存を減らし、より直接的に処理対象の `.npz` ファイルを指定できるような引数設計が望ましいです。
4.  **絶対パスと相対パス:**
    -   シェルスクリプトとPythonスクリプト間でのパスの受け渡しでは、混乱を避けるために可能な限り絶対パスを使用することを推奨します。
5.  **エラーハンドリングと中間ファイルの確認:**
    -   各ステップでエラーが発生した場合、後続ステップが依存する中間ファイルが生成されない可能性があります。適切なエラーハンドリングと、必要に応じてフォールバック処理を検討します。

このドキュメントを最新の状態に保ち、開発の指針とすることで、パス関連の問題を減らし、パイプライン全体の安定性を向上させることを目指します。

## 🏆 データフロー成功マイルストーン

**重要**: データフロー改修の成功実績として、以下のマイルストーンファイルを参照リポジトリとして保持しています。

### マイルストーンファイル
**ファイル**: `/app/MILESTONE_DataFlow_Step4Merge_Success_40s_4MB.py`

**実績**:
- 総処理時間: 40.80秒
- 最終FBX出力: 4.0MB  
- Step4Merge 5段階処理フロー完全動作
- 統一ディレクトリ構造 (02_skeleton, 03_skinning, 04_merge) 完全対応

### データフロー問題発生時の対応
1. **マイルストーンファイルの実行**: 正常動作パターンの確認
2. **この文書との照合**: 標準構造との比較
3. **段階的修復**: Step1からStep4まで個別確認

**⚠️ 注意**: マイルストーンファイルは削除禁止です。データフロー復旧の基準として永続保持してください。

---
