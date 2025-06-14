# UniRig 推論スクリプト 詳細データフロー

このドキュメントは、UniRigの主要な推論処理スクリプト (`launch/inference/` ディレクトリ配下) が各段階で使用する入力データと生成する出力データについて、そのディレクトリ構造とファイル名を詳細に記述したものです。

パス中の `{model_name}` は、処理対象のモデル名に置き換えてください (例: `bird`)。

---

## 1. `launch/inference/extract.sh` (メッシュ抽出 - Step1相当)

このスクリプトは、入力された3Dモデルファイルからメッシュ情報を抽出し、NPZ形式で保存します。

### 入力データ

-   **データの説明:** ユーザーによってアップロードされた元の3Dモデルファイル。
-   **ディレクトリ:** `/app/pipeline_work/{model_name}/` (アップロード時に `FileManager` によってここに配置される想定)
-   **ファイル名:** (ユーザーがアップロードしたファイル名, 例: `bird.glb`)

### 出力データ

-   **データの説明:** 抽出されたメッシュデータ。
-   **ディレクトリ:** `/app/pipeline_work/{model_name}/01_extracted_mesh/`
-   **ファイル名:** `raw_data.npz`
    -   *備考: この `raw_data.npz` という固定ファイル名は、後続の原流処理スクリプトとの互換性のために非常に重要です。*

---

## 2. `launch/inference/generate_skeleton.sh` (スケルトン生成 - Step2相当)

このスクリプトは、抽出されたメッシュデータ (`raw_data.npz`) を基に、AIモデルを使用してスケルトンを予測・生成します。

### 入力データ

-   **データの説明:** Step1で抽出されたメッシュデータ。
-   **ディレクトリ:** `/app/pipeline_work/{model_name}/01_extracted_mesh/`
-   **ファイル名:** `raw_data.npz`

### 出力データ

-   **データの説明:** 生成されたスケルトンモデル。
-   **ディレクトリ:** `/app/pipeline_work/{model_name}/02_skeleton/`
-   **ファイル名:** `{model_name}.fbx`
    -   *備考: この `{model_name}.fbx` というサフィックスなしのファイル名は、後続の原流処理スクリプトとの互換性のために重要です。*

-   **データの説明:** 生成されたスケルトンデータ。
-   **ディレクトリ:** `/app/pipeline_work/{model_name}/02_skeleton/`
-   **ファイル名:** `predict_skeleton.npz`
    -   *備考: この `predict_skeleton.npz` という固定ファイル名は、後続の原流処理スクリプトとの互換性のために非常に重要です。*

---

## 3. `launch/inference/generate_skin.sh` (スキニング適用 - Step3相当)

このスクリプトは、抽出されたメッシュデータ (`raw_data.npz`) と生成されたスケルトン (`{model_name}.fbx`, `predict_skeleton.npz`) を使用して、メッシュにスキンウェイトを適用（スキニング）します。

### 入力データ (原流処理スクリプトが参照する一時作業ディレクトリ内のファイル)

スクリプト実行前に、`step_modules/step3_skinning_unirig.py` などの呼び出し元モジュールが、以下のデータを原流処理が期待する一時的な作業ディレクトリ `/app/dataset_inference_clean/{model_name}/` 配下に準備します。

-   **データの説明:** Step1で抽出されたメッシュデータ (コピー)。
-   **ディレクトリ (作業用):** `/app/dataset_inference_clean/{model_name}/`
-   **ファイル名 (作業用):** `raw_data.npz`

-   **データの説明:** Step2で生成されたスケルトンモデル (コピー)。
-   **ディレクトリ (作業用):** `/app/dataset_inference_clean/{model_name}/`
-   **ファイル名 (作業用):** `{model_name}.fbx`

-   **データの説明:** Step2で生成されたスケルトンデータ (コピー)。
-   **ディレクトリ (作業用):** `/app/dataset_inference_clean/{model_name}/`
-   **ファイル名 (作業用):** `predict_skeleton.npz`

-   **データの説明:** 処理対象のモデル名をリストしたファイル (動的に生成)。
-   **ディレクトリ (作業用):** `/app/dataset_inference_clean/{model_name}/`
-   **ファイル名 (作業用):** `inference_datalist.txt` (内容は `{model_name}\n`)

### 出力データ (統一出力ディレクトリに格納される最終成果物)

-   **データの説明:** スキニング済みの3Dモデル。
-   **ディレクトリ:** `/app/pipeline_work/{model_name}/03_skinning/`
-   **ファイル名:** `{model_name}_skinned_unirig.fbx`

-   **データの説明:** スキニング処理に関する補助データ。
-   **ディレクトリ:** `/app/pipeline_work/{model_name}/03_skinning/`
-   **ファイル名:** `{model_name}_skinning.npz`

---

## 4. `launch/inference/merge.sh` (スケルトン・スキンウェイトマージ - Step4相当)

このスクリプトは、Step2で生成されたスケルトン情報 (`{model_name}.fbx`) とStep3で生成されたスキニング済みモデル (`{model_name}_skinned_unirig.fbx`) をマージし、スケルトンとスキンウェイト情報が統合された単一のFBXファイルを生成します。

### 入力データ

-   **データの説明:** Step2で生成されたスケルトンモデル (FBX形式)。これがマージの際のスケルトン情報のソースとなります。
-   **ディレクトリ:** `/app/pipeline_work/{model_name}/02_skeleton/`
-   **ファイル名:** `{model_name}.fbx` (スクリプト内では `$1` または `--source` 引数として渡される)

-   **データの説明:** Step3で生成されたスキニング済みモデル (FBX形式)。これがマージの際のスキンウェイト情報のターゲットとなります。
-   **ディレクトリ:** `/app/pipeline_work/{model_name}/03_skinning/`
-   **ファイル名:** `{model_name}_skinned_unirig.fbx` (スクリプト内では `$2` または `--target` 引数として渡される)

### 出力データ

-   **データの説明:** スケルトン情報とスキンウェイト情報がマージされた3Dモデル。
-   **ディレクトリ:** `/app/pipeline_work/{model_name}/04_merge/`
-   **ファイル名:** `{model_name}_merged.fbx` (スクリプト内では `$3` または `--output` 引数で指定されたパスに出力される)
    -   *備考: このステップではテクスチャ処理は行いません。テクスチャやマテリアルの統合はStep5の責務です。*

---

## 5. Blender統合処理 (UV・マテリアル・テクスチャ統合 - Step5相当)

このステップは、特定の推論スクリプト (`launch/inference/` 配下) に直接対応するものではなく、`step_modules/step5_reliable_uv_material_transfer.py` モジュール内のBlender Pythonスクリプトによって実行されます。このモジュールは、Step4でマージされたモデルに、Step0で保存された（または元のファイルから直接読み込まれた）UV、マテリアル、テクスチャ情報を統合し、最終的なFBXファイルを生成します。

### 入力データ

-   **データの説明:** Step4でスケルトンとスキンウェイトがマージされたモデル。
-   **ディレクトリ:** `/app/pipeline_work/{model_name}/04_merge/`
-   **ファイル名:** `{model_name}_merged.fbx`

-   **データの説明:** ユーザーによってアップロードされた元の3Dモデルファイル。UV、マテリアル、テクスチャ情報の参照元となります。
    -   Step0で `00_asset_preservation/` に保存されたものが利用されるか、あるいは `pipeline_work/{model_name}/` 直下の元ファイルが直接参照される場合があります。
-   **ディレクトリ:** `/app/pipeline_work/{model_name}/00_asset_preservation/` または `/app/pipeline_work/{model_name}/`
-   **ファイル名:** (ユーザーがアップロードしたファイル名, 例: `bird.glb`)
    -   *備考: `step0_asset_preservation.py` が `preserved_original` として元のファイルのパスを `pipeline_state.json` に記録している場合、そのパスが優先的に使用されます。*

-   **データの説明 (オプション):** Step0で抽出・保存されたアセットメタデータ。
-   **ディレクトリ:** `/app/pipeline_work/{model_name}/00_asset_preservation/`
-   **ファイル名:** `{model_name}_asset_metadata.json` や `{model_name}_asset_metadata_blender.json`

-   **データの説明 (オプション):** Step0で保存されたテクスチャファイル群。
-   **ディレクトリ:** `/app/pipeline_work/{model_name}/00_asset_preservation/textures/`
-   **ファイル名:** (元のテクスチャファイル名群)

### 出力データ

-   **データの説明:** UV、マテリアル、テクスチャ情報が完全に統合された最終的なリギング済み3Dモデル。
-   **ディレクトリ:** `/app/pipeline_work/{model_name}/05_blender_integration/`
-   **ファイル名:** `{model_name}_final.fbx`

-   **データの説明:** FBXエクスポート時にテクスチャが外部ファイルとして保存される場合、そのテクスチャが格納されるディレクトリ (例: `path_mode='COPY'` の場合)。
-   **ディレクトリ:** `/app/pipeline_work/{model_name}/05_blender_integration/{model_name}_final.fbm/`
-   **ファイル名:** (テクスチャファイル名群)

---
**参照ドキュメント:**
-   `copilot-instructions_ja.md`
-   `.github/app_dataflow.instructions.md`
-   `.github/step3_unification_changelog_2025_06_13.instructions.md`
-   `step_modules/step5_reliable_uv_material_transfer.py`

これらのドキュメントに記載されている統一出力ディレクトリ構造、ファイル命名規則、および各ステップの責務に基づいてこの情報をまとめています。
