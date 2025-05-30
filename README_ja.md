# UniRig: 1つのモデルですべてをリギングする

<div align="center">

[![プロジェクトページ](https://img.shields.io/badge/🏠-プロジェクトページ-blue.svg)](https://zjp-shadow.github.io/works/UniRig/)
[![論文](https://img.shields.io/badge/📑-論文-green.svg)](https://arxiv.org/abs/2504.12451)
[![モデル](https://img.shields.io/badge/🤗-モデル-yellow.svg)](https://huggingface.co/VAST-AI/UniRig)

</div>

![ティーザー](assets/doc/unirig_teaser.png)

このリポジトリは、清華大学と[Tripo](https://www.tripo3d.ai)によって開発された、3Dモデルの自動リギングのための統合ソリューション、**SIGGRAPH'25 (TOG) UniRig**フレームワークの公式実装を含んでいます。

**論文:** [One Model to Rig Them All: Diverse Skeleton Rigging with UniRig（すべてをリギングする1つのモデル：UniRigによる多様なスケルトンリギング）](https://arxiv.org/abs/2504.12451)

## 概要

3Dモデルのリギング（スケルトンの作成とスキニングウェイトの割り当て）は、3Dアニメーションにおいて重要ながらも複雑で時間のかかるステップです。UniRigは、大規模な自己回帰モデルを活用した革新的な統合フレームワークを導入し、多様な3Dアセットに対するこのプロセスの自動化に取り組みます。

UniRigとキーフレームアニメーションを組み合わせると、以下のような結果が得られます：

| ![デビル](assets/doc/devil.gif) | ![ドラゴン](assets/doc/dragon.gif) | ![ウサギ](assets/doc/rabbit.gif) |
|:-----------------------------:|:-------------------------------:|:-------------------------------:|

完全なUniRigシステムは主に2つの段階で構成されています：
1. **スケルトン予測:** GPT風のトランスフォーマーが、新規の**スケルトンツリートークン化**スキームを使用して、位相的に有効なスケルトン階層を自己回帰的に予測します。
2. **スキニングウェイトと属性予測:** **ボーン-ポイントクロスアテンション**メカニズムが、予測されたスケルトンと入力メッシュジオメトリに基づいて、頂点ごとのスキニングウェイトと関連するボーン属性（物理シミュレーション用など）を予測します。

このリポジトリは、段階的にリリースされるコンポーネントを含む、フレームワークビジョン全体のコード実装を提供します。

## 主な機能（完全なUniRigフレームワーク）

* **統合モデル:** 単一のフレームワークで多様なモデルカテゴリ（人間、動物、物体）を扱うことを目指します。
* **自動スケルトン生成:** 位相的に有効なスケルトン構造を予測します。**（✅ 現在のリリースで利用可能）**
* **自動スキニング予測:** 頂点ごとのスキニングウェイトを予測します。**（✅ 現在のリリースで利用可能）**
* **ボーン属性予測:** 物理ベースの二次運動のための剛性などの属性を予測します。**（⏳ 近日公開）**
* **高精度と堅牢性:** 難しいデータセットで最先端の結果を達成します（論文ではRig-XL/VRoidトレーニングで示されています）。
* **効率的なトークン化:** コンパクトな表現と効率的な処理のために、スケルトンツリートークン化を使用します。
* **ヒューマンインザループ対応:** 反復的な改良ワークフローをサポートするよう設計されています。

## 🚨 現在のリリース状況とロードマップ 🚨

私たちはUniRigを段階的にオープンソース化しています。現在の状況に注意してください：

**現在利用可能（初期リリース）:**
* ✅ **コード:** スケルトンとスキニング予測の実装。
* ✅ **モデル:** [**Articulation-XL2.0**](https://huggingface.co/datasets/Seed3D/Articulation-XL2.0)でトレーニングされたスケルトン＆スキニング予測チェックポイント。[Hugging Face](https://huggingface.co/VAST-AI/UniRig)で入手可能。

**今後予定されているリリース:**
* ⏳ 論文で使用された**Rig-XL**および**VRoid**データセットのリリース。
* ⏳ Rig-XL/VRoidでトレーニングされた完全なUniRigモデルチェックポイント（スケルトン＋スキニング）で、論文の主な結果を再現します。

これらのコンポーネントのリリース準備を進めている間、お待ちいただきありがとうございます。更新情報については[VAST-AI-Research](https://github.com/orgs/VAST-AI-Research)のアナウンスをフォローしてください！

## インストール

1. **前提条件:**
   * Python 3.11
   * PyTorch（バージョン>=2.3.1でテスト済み）

2. **リポジトリをクローン:**
   ```bash
   git clone https://github.com/VAST-AI-Research/UniRig
   cd UniRig
   ```

3. **仮想環境をセットアップ（推奨）:**
   ```bash
   conda create -n UniRig python=3.11
   conda activate UniRig
   ```

4. **依存関係をインストール:**
   ```bash
   python -m pip install torch torchvision
   python -m pip install -r requirements.txt
   python -m pip install spconv-{あなたのcudaバージョン}
   python -m pip install torch_scatter torch_cluster -f https://data.pyg.org/whl/torch-{あなたのtorchバージョン}+{あなたのcudaバージョン}.html --no-cache-dir
   python -m pip install numpy==1.26.4
   ```

5. **モデルチェックポイントをダウンロード:**
   現在利用可能なスケルトン予測モデルチェックポイントはHugging Faceでホストされており、通常は提供されたスクリプト/関数によって自動的にダウンロードされます。

6. **（オプション、.vrmのインポート/エクスポート用）Blenderアドオンをインストール:**
   このBlenderアドオンは[VRM-Addon-for-Blender](https://github.com/saturday06/VRM-Addon-for-Blender)を修正したものです。Blender 4.2での使用を推奨します。
   
   プロジェクトのルートディレクトリにいることを確認し、次を実行します：
   ```bash
   python -c "import bpy, os; bpy.ops.preferences.addon_install(filepath=os.path.abspath('blender/add-on-vrm-v2.20.77_modified.zip'))"
   ```
   
   または、Blender 4.2を起動し、編集 > プリファレンス > アドオンから「インストール」ボタンをクリックして手動でZIPファイル（`blender/add-on-vrm-v2.20.77_modified.zip`）をインストールすることもできます。

## 使用方法

### スケルトン予測（現在利用可能）

事前学習済みモデルを使用して3Dモデル用のスケルトンを生成します。このプロセスはジオメトリを自動的に分析し、適切なスケルトン構造を予測します。

```bash
# 単一ファイルを処理
bash launch/inference/generate_skeleton.sh --input examples/giraffe.glb --output results/giraffe_skeleton.fbx

# ディレクトリ内の複数ファイルを処理
bash launch/inference/generate_skeleton.sh --input_dir <入力ディレクトリ> --output_dir <出力ディレクトリ>

# ランダムシードを変更して異なるスケルトンバリエーションを試す
bash launch/inference/generate_skeleton.sh --input examples/giraffe.glb --output results/giraffe_skeleton.fbx --seed 42
```

サポートされている入力形式：`.obj`、`.fbx`、`.glb`、および`.vrm`

### スキニングウェイト予測（現在利用可能）
```bash
# 単一ファイルのスキニング
bash launch/inference/generate_skin.sh --input examples/skeleton/giraffe.fbx --output results/giraffe_skin.fbx

# ディレクトリ内の複数ファイルを処理
bash launch/inference/generate_skin.sh --input_dir <入力ディレクトリ> --output_dir <出力ディレクトリ>
```

上記のコマンドはスケルトン段階からの**編集版**を使用することに注意してください。スケルトンが不正確な場合—例えば、尾のボーンや翼のボーンが欠けている場合—結果は大幅に低下する可能性があります。したがって、より良い結果を得るためにスキニングを実行する前にスケルトンを改良することをお勧めします。

### 予測結果の結合

予測されたスケルトンと元の3Dモデルを組み合わせて、完全にリギングされたアセットを作成します：

```bash
# スケルトン予測からスケルトンを結合
bash launch/inference/merge.sh --source results/giraffe_skeleton.fbx --target examples/giraffe.glb --output results/giraffe_rigged.glb

# またはスキン予測からスキンを結合
bash launch/inference/merge.sh --source results/giraffe_skin.fbx --target examples/giraffe.glb --output results/giraffe_rigged.glb
```

## モデル

利用可能なモデルは以下でホストされています：https://huggingface.co/VAST-AI/UniRig

## システム要件

- 少なくとも8GB VRAMを備えたCUDA対応GPU

## 引用

```
@article{zhang2025unirig,
  title={One Model to Rig Them All: Diverse Skeleton Rigging with UniRig},
  author={Zhang, Jia-Peng and Pu, Cheng-Feng and Guo, Meng-Hao and Cao, Yan-Pei and Hu, Shi-Min},
  journal={arXiv preprint arXiv:2504.12451},
  year={2025}
}
```

## 謝辞

以下のオープンソースプロジェクトと研究成果に感謝します：

- モデルアーキテクチャについては[OPT](https://huggingface.co/facebook/opt-350m)
- 3D形状表現については[3DShape2VecSet](https://github.com/1zb/3DShape2VecSet)
- 形状エンコーダ実装については[SAMPart3D](https://github.com/Pointcept/SAMPart3D)と[Michelangelo](https://github.com/NeuralCarver/Michelangelo/)
- 整理されたデータセットについては[Articulation-XL2.0](https://huggingface.co/datasets/Seed3D/Articulation-XL2.0)

3D生成分野へのオープンな探求と貢献をしている研究コミュニティ全体に感謝します。

---

**Windowsユーザー向けの注意:**

このドキュメントで言及されている `.sh` スクリプトは、Unixライクな環境（LinuxやmacOSのターミナルなど）で実行することを前提としています。Windows環境でこれらのスクリプトを実行するための標準的な手順と、一般的なトラブルシューティングについて説明します。

**A. Git Bashでの標準的な作業フロー**

1.  **Git Bashを起動:**
    *   [Git for Windows](https://git-scm.com/download/win) がインストールされていることを確認してください。
    *   Windowsのスタートメニューから「Git Bash」を検索し、起動します。
    *   **ディレクトリ移動 (`cd`) の注意:**
        *   Git Bashでディレクトリを移動する際は、WindowsのパスをUnix形式に変換して指定します。例えば、`J:\マイドライブ\blender_AI\UniRig` は `/j/マイドライブ/blender_AI/UniRig` となります。

2.  **Conda初期設定（初回のみ、または `conda` コマンドが見つからない場合）:**
    *   Git Bash内で `conda` コマンド（例: `conda activate`）が認識されない場合は、Condaの初期設定が必要です。
    *   **推奨手順:**
        1.  Windowsのスタートメニューから「Anaconda Prompt」を起動します。
        2.  Anaconda Promptで `conda init bash` と入力し、実行します。
        3.  Git Bashを再起動します。これで `conda` コマンドが利用可能になるはずです。
    *   詳細は後述の「B. トラブルシューティング」セクションを参照してください。

3.  **Anaconda仮想環境をアクティベート:**
    *   起動したGit Bashのターミナル内で、目的のAnaconda仮想環境（例: `UniRig`）をアクティベートします。
      ```bash
      conda activate UniRig
      ```

4.  **.shスクリプトを実行:**
    *   仮想環境がアクティベートされたGit Bashターミナルで、ドキュメントに記載されている `.sh` スクリプトを実行します。
      ```bash
      # 例:
      # bash launch/inference/generate_skeleton.sh --input examples/giraffe.glb --output results/giraffe_skeleton.fbx
      ```

**B. トラブルシューティング / よくあるエラーと対処法**

1.  **`conda` コマンドがGit Bashで見つからない (`command not found: conda`)**
    *   **原因:** Git BashがCondaの実行ファイルを見つけられるように設定されていません。
    *   **対処法 (推奨): `conda init bash` を使用する**
        1.  **Anaconda Prompt を起動:** Windowsのスタートメニューから「Anaconda Prompt」を検索して起動します。
        2.  **`conda init bash` を実行:** Anaconda Promptで `conda init bash` と入力し、実行します。これにより、Git Bashが必要とするCondaの初期化設定が自動的にユーザーの `.bashrc` ファイル（通常 `C:\Users\<あなたのWindowsユーザー名>\.bashrc`）に書き込まれます。
            *   もし `no change` と表示されたり、既に `conda initialize` ブロックが `.bashrc` にあるにも関わらず問題が解決しない場合は、一度 `.bashrc` 内の `>>> conda initialize >>>` から `<<< conda initialize <<<` までのブロックを手動で削除し、再度 `conda init bash` を実行してみてください。
        3.  **Git Bash を再起動:** 設定を反映させるため、すべてのGit Bashウィンドウを閉じてから再度起動します。
    *   **対処法 (代替案): 手動でGit Bashの設定ファイルを編集する**
        （`conda init bash` が何らかの理由でうまくいかない場合や、設定内容を細かく制御したい上級者向け）
        1.  **Conda初期化スクリプトの場所を確認:** Anaconda（またはMiniconda）のインストールディレクトリ内にある `etc/profile.d/conda.sh` を探します。 (例: `/c/Users/YourUser/anaconda3/etc/profile.d/conda.sh`)
        2.  **Git Bashの設定ファイルを編集:** Git Bashターミナルで、ホームディレクトリ（通常 `C:\Users\<あなたのWindowsユーザー名>`、Git Bash内では `~`）にある `.bashrc` ファイルを編集します。存在しない場合は新規作成します。
            ```bash
            nano ~/.bashrc
            ```
        3.  **初期化スクリプトの読み込みコマンドを追加:** ファイルの末尾に以下の行を追加します。パスはご自身の環境に合わせてください。
            ```bash
            . "/c/Users/YourUser/anaconda3/etc/profile.d/conda.sh"
            ```
            先頭の `.`（ドットとスペース）は `source` コマンドのエイリアスで、スクリプトを現在のシェルで実行するために必要です。
        4.  **設定を保存して適用:** ファイルを保存し、Git Bashを再起動するか `source ~/.bashrc` を実行します。

2.  **`conda activate` 実行時にパス関連のエラー (例: `bash: C:\Users\ownernaconda3\Scripts: No such file or directory`)**
    *   **原因:** Condaの初期化スクリプトがWindowsのパスを正しく解釈または構築できていない可能性があります。これは、`.bashrc` の手動編集が不完全だったり、古い設定が残っていたりする場合に発生しやすいです。
    *   **対処法:**
        1.  まず、上記の「`conda` コマンドがGit Bashで見つからない」の**推奨対処法である `conda init bash` を実行**してみてください。これにより、Condaが最適な設定を `.bashrc` に書き込みます。
        2.  `.bashrc` ファイルを確認し、手動で追加した古いConda関連の行や、不正確な可能性のある設定があれば削除またはコメントアウトし、`conda init bash` によって生成された `conda initialize` ブロックのみが有効になるようにします。
        3.  Git Bashを再起動して確認します。

3.  **Anaconda Prompt等で `bash` と入力するとWSLが起動してしまう**
    *   **原因:** Windowsの環境変数 `PATH` で、Git Bashの `bash.exe` よりもWSLの `bash.exe` が優先されている可能性があります。
    *   **対処法:**
        *   スクリプト実行時は、Windowsのスタートメニューから「Git Bash」を明示的に検索して起動してください。Anaconda Prompt内で `bash` と入力してGit Bashを起動しようとしないでください。

**C. WSL (Windows Subsystem for Linux) を使用する場合**

*   WSLを有効にし、Linuxディストリビューションをインストールします。
*   **WSLターミナル内で別途Anaconda（またはMiniconda）をインストールし、WSL専用の仮想環境を作成・アクティベートします。** その後、`.sh` スクリプトを実行します。
*   この方法では、Windowsのファイルシステムパス（例: `J:\...`）ではなく、WSL内のLinuxパス（例: `/mnt/j/...`）を使用することになります。
*   **注意:** Windows側のAnaconda/MinicondaとWSL側のAnaconda/Minicondaで仮想環境を直接共有することは、パスの違いやバイナリ互換性の問題から非常に複雑であり、推奨されません。それぞれの環境で独立してCondaをセットアップし、仮想環境を管理してください。

上記のように、まず適切なシェル環境（Git BashまたはWSL内のbash）を準備し、その中でAnaconda仮想環境をアクティベートしてからスクリプトを実行してください。これにより、Pythonの依存関係が正しく解決された状態でスクリプトが動作します。

## Docker環境での実行

環境構築の複雑さや依存関係の問題を回避するために、Dockerを使用してUniRigを実行することを推奨します。提供されている`Dockerfile`は、GradioベースのWeb UIアプリケーションを実行することも、従来のコマンドラインスクリプトを実行することも想定しています。

### 1. Dockerイメージのビルド

まず、プロジェクトのルートディレクトリ（`Dockerfile`が存在する場所）で以下のコマンドを実行し、Dockerイメージをビルドします。このビルド作業は一度だけ行えば、その後は同じイメージを繰り返し使用できます。

```bash
# Gradio UIを含むアプリケーション用のイメージをビルドする場合
docker build -t unirig-gradio:latest .

# コマンドライン実行のみを想定する場合 (イメージ名は任意)
# docker build -t unirig:latest .
```

### 2. Gradio Web UIの実行 (オプション)

GradioベースのWeb UIを使用してUniRigを対話的に実行したい場合は、以下のコマンドでDockerコンテナを起動します。

```bash
# Dockerコンテナを起動 (Gradio UI用)
# ホストOSの ./inputs ディレクトリをコンテナ内の /workspace/inputs に、
# ホストOSの ./outputs ディレクトリをコンテナ内の /workspace/outputs にマウントします。
# ポート7860をホストOSに公開します。
docker run -it --rm --gpus all \\
    -p 7860:7860 \\
    -v "$(pwd)/inputs:/workspace/inputs" \\
    -v "$(pwd)/outputs:/workspace/outputs" \\
    unirig-gradio:latest
```

**実行手順:**

1.  **入力ファイルの準備:**
    *   プロジェクトのルートディレクトリ（`Dockerfile`がある場所）に `inputs` という名前のディレクトリを作成します。
    *   処理したい3Dモデルファイル（例: `my_model.glb`）をこの `inputs` ディレクトリにコピーします。
2.  **出力ディレクトリの準備:**
    *   プロジェクトのルートディレクトリに `outputs` という名前のディレクトリを作成します。処理結果はここに保存されます。
3.  **Dockerコンテナの起動:**
    *   上記の `docker run` コマンドを実行します。
4.  **Web UIへのアクセス:**
    *   コンテナが正常に起動し、Gradioアプリケーションが開始されると、ターミナルにURL（通常は `http://127.0.0.1:7860` または `http://localhost:7860`）が表示されます。
    *   WebブラウザでこのURLを開くと、UniRigのWeb UIが表示されます。
5.  **操作:**
    *   UIの指示に従って、入力ファイルを選択し（例: `/workspace/inputs/my_model.glb`）、必要な設定を行い、処理を実行します。
    *   処理結果はコンテナ内の `/workspace/outputs` ディレクトリに保存され、ホストOSの `outputs` ディレクトリからもアクセスできます。

**注意:**
*   `$(pwd)` は現在の作業ディレクトリ（プロジェクトのルート）を指します。WindowsのコマンドプロンプトやPowerShellでは `%cd%` を使用してください。Git Bashでは `$(pwd)` が使えます。
*   `--gpus all` オプションはNVIDIA GPUを使用するために必要です。GPUが利用できない環境では、このオプションを削除するか、CPUベースの推論に対応しているか確認してください（UniRigはGPUを推奨しています）。

### 3. コマンドラインスクリプトの実行

従来の `.sh` スクリプトを使用してUniRigの各機能を実行することも可能です。この場合、Dockerコンテナ内でこれらのスクリプトを実行します。

**基本的なコマンド構造:**

```bash
docker run --rm --gpus all \\
    -v "$(pwd)/examples:/workspace/examples" \\
    -v "$(pwd)/results:/workspace/results" \\
    -v "$(pwd)/your_input_data:/workspace/your_input_data" \\ # 任意: 追加の入力データ用
    unirig-gradio:latest \\
    bash launch/inference/<script_name.sh> [スクリプトの引数...]
```

**各スクリプトの実行例:**

#### a. スケルトン予測 (`generate_skeleton.sh`)

```bash
# ホストOSの examples/giraffe.glb を入力とし、
# ホストOSの results/giraffe_skeleton.fbx に結果を出力
docker run --rm --gpus all \\
    -v "$(pwd)/examples:/workspace/examples" \\
    -v "$(pwd)/results:/workspace/results" \\
    unirig-gradio:latest \\
    bash launch/inference/generate_skeleton.sh \\
        --input /workspace/examples/giraffe.glb \\
        --output /workspace/results/giraffe_skeleton.fbx
```

**ディレクトリ全体を処理する場合:**

```bash
# ホストOSの my_models ディレクトリ内のモデルを処理し、
# ホストOSの my_skeletons ディレクトリに結果を出力
# (事前に my_models, my_skeletons ディレクトリを作成しておくこと)
docker run --rm --gpus all \\
    -v "$(pwd)/my_models:/workspace/my_models" \\
    -v "$(pwd)/my_skeletons:/workspace/my_skeletons" \\
    unirig-gradio:latest \\
    bash launch/inference/generate_skeleton.sh \\
        --input_dir /workspace/my_models \\
        --output_dir /workspace/my_skeletons
```

#### b. スキニングウェイト予測 (`generate_skin.sh`)

スケルトン予測で生成されたスケルトンファイル（または手動で編集したスケルトンファイル）を入力として使用します。

```bash
# ホストOSの results/giraffe_skeleton.fbx (スケルトン) を入力とし、
# ホストOSの results/giraffe_skin.fbx に結果を出力
docker run --rm --gpus all \\
    -v "$(pwd)/results:/workspace/results" \\
    unirig-gradio:latest \\
    bash launch/inference/generate_skin.sh \\
        --input /workspace/results/giraffe_skeleton.fbx \\
        --output /workspace/results/giraffe_skin.fbx
```

#### c. 予測結果の結合 (`merge.sh`)

元の3Dモデルと、予測されたスケルトン（またはスキン）を結合します。

```bash
# スケルトン予測の結果を結合する場合
docker run --rm --gpus all \\
    -v "$(pwd)/examples:/workspace/examples" \\
    -v "$(pwd)/results:/workspace/results" \\
    unirig-gradio:latest \\
    bash launch/inference/merge.sh \\
        --source /workspace/results/giraffe_skeleton.fbx \\
        --target /workspace/examples/giraffe.glb \\
        --output /workspace/results/giraffe_rigged_skeleton.glb

# スキン予測の結果を結合する場合
docker run --rm --gpus all \\
    -v "$(pwd)/examples:/workspace/examples" \\
    -v "$(pwd)/results:/workspace/results" \\
    unirig-gradio:latest \\
    bash launch/inference/merge.sh \\
        --source /workspace/results/giraffe_skin.fbx \\
        --target /workspace/examples/giraffe.glb \\
        --output /workspace/results/giraffe_rigged_skin.glb
```

**コマンドライン実行のポイント:**

*   **ボリュームマウント (`-v`):**
    *   ホストOSのディレクトリをコンテナ内のディレクトリにマッピングします。これにより、コンテナ内のスクリプトがホストのファイルにアクセスできるようになります。
    *   上記の例では、プロジェクトルートにある `examples` と `results` ディレクトリをコンテナ内の `/workspace/examples` と `/workspace/results` にそれぞれマウントしています。
    *   独自の入力ファイルや出力ディレクトリを使用する場合は、適宜 `-v` オプションを追加・変更してください。例えば、`-v "$(pwd)/my_data:/workspace/my_data"` のように指定します。
*   **ファイルパス:**
    *   スクリプトに渡す `--input`、`--output`、`--input_dir`、`--output_dir` などのファイルパスは、**コンテナ内のパス**で指定する必要があります。例えば、ホストの `$(pwd)/examples/giraffe.glb` は、コンテナ内では `/workspace/examples/giraffe.glb` となります。
*   **イメージ名:**
    *   `unirig-gradio:latest` はイメージビルド時に指定したタグ名です。異なるタグ名でビルドした場合は、そちらを使用してください。コマンドライン実行のみが目的で `unirig:latest` のようなイメージをビルドした場合は、そのイメージ名を指定します。
*   **スクリプトの引数:**
    *   各 `.sh` スクリプトが受け付ける引数は、従来の実行方法と同じです。Docker経由で実行する場合も、これらの引数を同様に指定できます。

これらの手順により、Dockerコンテナ内でUniRigの各機能を安定して実行できるようになります。環境構築の手間を大幅に削減し、再現性の高い実行環境を提供します。