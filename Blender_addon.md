# WSL上のUniRig DockerコンテナとWindows版Blenderの連携ガイド

このドキュメントでは、WSL (Windows Subsystem for Linux) 上で動作するUniRigのDockerコンテナと、Windowsネイティブ環境で動作するBlenderを連携させる方法について説明します。
これにより、Windows版BlenderからUniRigの自動リギング機能を活用できます。

## 前提条件

*   Windows 10/11
*   WSL2がインストールされ、UbuntuなどのLinuxディストリビューションがセットアップ済みであること。
*   Docker Desktopがインストールされ、WSL2バックエンドを使用するように設定済みであること。
*   Windows版Blenderがインストール済みであること。
*   UniRigリポジトリがWSL内のLinuxディストリビューションにクローン済みであること。

## 連携の概要

連携は以下の流れで行います。

1.  **UniRig Dockerコンテナの準備:** WSL上でUniRigのDockerイメージをビルドし、コンテナを起動します。このコンテナは、HTTPリクエストを受け付けてUniRigの処理を実行するAPI（例: FastAPIやFlaskを使用）を内部で実行するように変更する必要があります。
2.  **Windows版Blenderアドオンの開発:** BlenderのPython APIを使用してアドオンを作成します。このアドオンは以下の機能を提供します。
    *   Blender内の3Dモデルデータをエクスポート（例: glb形式）。
    *   エクスポートしたモデルデータを、WSL上のUniRigコンテナが公開するAPIエンドポイントにHTTPリクエストで送信。
    *   UniRigコンテナからの処理結果（リギングされたモデルデータ）をHTTPレスポンスで受信。
    *   受信したモデルデータをBlenderにインポートして表示。
3.  **ネットワーク設定:** WindowsのファイアウォールやWSLのネットワーク設定が、Windows上のBlenderからWSL上のDockerコンテナ内のAPIにアクセスできるように適切に設定されていることを確認します。通常、`localhost` またはWSLのIPアドレス経由でアクセスできます。

## ステップ

### 1. UniRig DockerコンテナのAPI化 (開発者向け)

現在の `app.py` (Gradioベース) はインタラクティブなWeb UIを提供しますが、Blenderアドオンとの連携には、プログラムから呼び出し可能なAPIエンドポイントが必要です。

*   **APIフレームワークの導入:** FastAPIやFlaskなどのPythonフレームワークを使用して、UniRigの機能をラップするAPIを作成します。
    *   例: `/rig_model` エンドポイントを作成し、モデルファイルを受け取って処理結果を返す。
    *   以下にFastAPIを使用した `api_main.py` のサンプルを示します。これを `/app/api_main.py` としてプロジェクトのルートに配置します。

```python
# /app/api_main.py
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
import shutil
import os
import tempfile
import subprocess # For running UniRig scripts

app = FastAPI()

# Temporary directory to store uploaded and processed files
TEMP_DIR_BASE = tempfile.mkdtemp(prefix="unirig_api_")
UPLOAD_DIR = os.path.join(TEMP_DIR_BASE, "uploads")
PROCESSED_DIR = os.path.join(TEMP_DIR_BASE, "processed")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

print(f"Temporary directories created: UPLOAD_DIR={UPLOAD_DIR}, PROCESSED_DIR={PROCESSED_DIR}")

@app.post("/rig_model/")
async def rig_model_endpoint(model_file: UploadFile = File(...)):
    uploaded_file_path = None
    processed_file_path = None
    
    try:
        original_filename = model_file.filename
        sanitized_filename = os.path.basename(original_filename)
        
        uploaded_file_path = os.path.join(UPLOAD_DIR, sanitized_filename)
        with open(uploaded_file_path, "wb") as buffer:
            shutil.copyfileobj(model_file.file, buffer)
        print(f"File '{sanitized_filename}' uploaded to '{uploaded_file_path}'")

        # --- UniRig Processing Steps ---
        skeleton_output_filename = f"skel_{sanitized_filename.rsplit('.',1)[0]}.fbx"
        skeleton_output_path = os.path.join(PROCESSED_DIR, skeleton_output_filename)
        
        skeleton_cmd = [
            "bash", "/app/launch/inference/generate_skeleton.sh",
            "--input", uploaded_file_path,
            "--output", skeleton_output_path
        ]
        print(f"Running skeleton command: {' '.join(skeleton_cmd)}")
        process_skel = subprocess.run(skeleton_cmd, capture_output=True, text=True, check=False)
        
        if process_skel.returncode != 0:
            print(f"Skeleton Prediction Error Output: {process_skel.stderr}")
            print(f"Skeleton Prediction Stdout: {process_skel.stdout}")
            raise HTTPException(status_code=500, detail=f"Skeleton prediction failed: {process_skel.stderr or process_skel.stdout}")
        print(f"Skeleton prediction stdout: {process_skel.stdout}")
        if not os.path.exists(skeleton_output_path):
             raise HTTPException(status_code=500, detail=f"Skeleton output file not found: {skeleton_output_path}")

        # Simplified: returning the direct output of generate_skeleton.sh
        # For a full pipeline, you would also call generate_skin.sh and merge.sh here.
        processed_file_path = skeleton_output_path
        final_return_filename = skeleton_output_filename
        # --- End UniRig Processing ---

        if not os.path.exists(processed_file_path):
            raise HTTPException(status_code=500, detail=f"Processed file not found: {processed_file_path}")

        media_type = 'model/gltf-binary' if final_return_filename.lower().endswith('.glb') else 'application/octet-stream'

        return FileResponse(
            path=processed_file_path,
            filename=final_return_filename,
            media_type=media_type
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in /rig_model/ endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
    finally:
        if uploaded_file_path and os.path.exists(uploaded_file_path):
            try:
                os.remove(uploaded_file_path)
                print(f"Cleaned up uploaded file: {uploaded_file_path}")
            except OSError as e:
                print(f"Error cleaning up uploaded file {uploaded_file_path}: {e}")
        pass

@app.get("/")
async def root():
    return {"message": "UniRig API is running. Use POST /rig_model/ to process models."}

# To run (inside container or locally with UniRig env):
# uvicorn api_main:app --host 0.0.0.0 --port 8000 --reload

# --- ポート設定の柔軟化のための提案 ---
# api_main.py の変更案 (環境変数 UNIRIG_API_PORT を使用)
# import os
# ...
# if __name__ == "__main__":
#     import uvicorn
#     api_port = int(os.environ.get("UNIRIG_API_PORT", 8000))
#     uvicorn.run(app, host="0.0.0.0", port=api_port)
# --- ここまで ---
```

*   **Dockerfileの調整:** Dockerfileを更新し、Gradioアプリの代わりにこのFastAPIサーバーを起動するようにします。また、FastAPIとUvicornの依存関係を追加します。

    ```dockerfile
    # ... (既存のDockerfileの内容) ...

    # Conda環境が有効化されていることを確認
    # SHELL ["/bin/bash", "-c"]

    # APIサーバー用の依存関係をインストール
    RUN source activate UniRig && \
        pip install fastapi uvicorn python-multipart

    # 環境変数 UNIRIG_API_PORT を設定 (デフォルトは8000)
    ENV UNIRIG_API_PORT=8000
    # FastAPI用にポートを開放 (実際のポートは環境変数で上書き可能)
    EXPOSE $UNIRIG_API_PORT 

    # Gradioアプリの代わりにFastAPIサーバーを起動するCMD命令
    # CMD ["source activate UniRig && uvicorn api_main:app --host 0.0.0.0 --port $UNIRIG_API_PORT"]
    # 開発中は sleep infinity のままにしておき、コンテナ内で手動でUvicornを起動することもできます。
    # その場合、api_main.py を直接実行する際に環境変数を参照するようにしてください。
    # 例: python -c 'import os; import uvicorn; uvicorn.run("api_main:app", host="0.0.0.0", port=int(os.environ.get("UNIRIG_API_PORT", 8000)))'
    CMD ["sleep", "infinity"]
    ```
    **注:** `Dockerfile` の `EXPOSE` と `CMD` は、Gradio用からFastAPI用に適宜変更・調整してください。開発中は `sleep infinity` のままにしておき、コンテナ内で手動でUvicornを起動することもできます。

*   **コンテナのビルドと実行:**
    ```bash
    # WSLのUniRigプロジェクトディレクトリで
    docker build -t unirig-api .
    # ローカルでテスト実行する場合
    # docker run -p 8000:8000 unirig-api 
    # ポートマッピングを確認 (例: Windowsから http://localhost:8000 でアクセス)
    # ポートを変更して実行する場合 (ホストの8001番をコンテナの8080番にマッピング):
    # docker run -e UNIRIG_API_PORT=8080 -p 8001:8080 unirig-api
    ```

*   **(オプション) Docker Hubへの公開 (開発者向け):**
    ビルドした `unirig-api` イメージをDocker Hubに公開することで、他のユーザーが簡単に利用できるようになります。

    1.  **Docker Hubアカウントの準備:** Docker Hub ([https://hub.docker.com/](https://hub.docker.com/)) でアカウントを作成またはログインしておきます。
    2.  **イメージへのタグ付け:** Docker Hubのリポジトリ名に合わせてイメージにタグを付けます。通常、`<DockerHubユーザー名>/<リポジトリ名>:<タグ>` の形式です。
        ```bash
        # 例: Docker Hubユーザー名が "yourusername" の場合
        docker tag unirig-api yourusername/unirig-api:latest
        # または、バージョンを指定する場合
        # docker tag unirig-api yourusername/unirig-api:0.1.0 
        ```
    3.  **Docker Hubへのログイン (対話的処理):** ターミナルで以下のコマンドを実行し、指示に従ってDocker Hubの認証情報を入力します。このステップは手動で行う必要があります。
        ```bash
        docker login
        ```
    4.  **イメージのプッシュ:** タグ付けしたイメージをDocker Hubにアップロードします。
        ```bash
        docker push yourusername/unirig-api:latest
        # バージョンタグを指定した場合
        # docker push yourusername/unirig-api:0.1.0
        ```
    上記 `docker tag` と `docker push` コマンドは、`docker login` が完了していればスクリプトに組み込むことが可能です。

*   **(利用者向け) Docker Hubからのイメージ利用:**
    開発者がDocker Hubに `unirig-api` イメージを公開した場合、利用者は以下のコマンドで簡単にAPIサーバーを起動できます。
    APIサーバーが使用するポート番号は、Blenderアドオン側で設定可能にし、Dockerコンテナ起動時にもホストOS側のポートを柔軟に指定できるようにします。

    ```bash
    # 1. Docker Hubからイメージを取得 (yourusername/unirig-api:latest は公開されているイメージ名に置き換えてください)
    docker pull yourusername/unirig-api:latest

    # 2. イメージを実行してコンテナを起動
    docker run -d -p 8000:8000 --gpus all yourusername/unirig-api:latest 
    # -d: デタッチモード（バックグラウンド実行）
    # -p 8000:8000: ホストのポート8000をコンテナのポート8000にマッピング
    # --gpus all: NVIDIA GPUをコンテナから利用可能にする (UniRigの処理に必要)
    #
    # ポート競合を避けるために、ホスト側のポートやコンテナ内のポートを変更する場合:
    # 例1: ホストのポート8001を、コンテナがデフォルトでリッスンするポート(DockerfileのEXPOSEまたはCMDで指定されたもの、ここでは仮に8000とする)にマッピング
    # docker run -d -p 8001:8000 --gpus all yourusername/unirig-api:latest
    #
    # 例2: コンテナ内のAPIサーバーがリッスンするポートを環境変数で8080に変更し、ホストのポート8001にマッピング
    # docker run -d -e UNIRIG_API_PORT=8080 -p 8001:8080 --gpus all yourusername/unirig-api:latest
    #
    # この場合、Blenderアドオンからは http://localhost:8001 (ホスト側で指定したポート) にアクセスします。
    ```
    コンテナが起動したら、Windows上のBlenderアドオンから `http://localhost:<ホスト側で指定したポート>/rig_model` にアクセスできるようになります。

### 2. Windows版Blenderアドオンの開発

BlenderのPythonスクリプト機能を使用してアドオンを作成します。

*   **UIの作成:** BlenderのUIパネルに、APIサーバーのホスト名とポート番号を入力するフィールドと、リギング実行ボタン（例: "UniRigでリギング"）を追加します。
*   **モデルデータのエクスポート:** アクティブなオブジェクトや選択されたオブジェクトを一時ファイル（例: `.glb`）としてエクスポートします。
*   **HTTPリクエストの送信:** Pythonの `requests` ライブラリ（Blenderにバンドルされているか、別途アドオンに含める）を使用して、エクスポートしたモデルファイルをWSL上のUniRig APIに送信します。
    ```python
    # Blenderアドオン内のPythonコード (イメージ)
    import bpy
    import requests
    import tempfile
    import os

    # アドオンのプロパティとしてAPIのホストとポートを定義 (ユーザーがUIで設定可能にする)
    # class UniRigProperties(bpy.types.PropertyGroup):
    #     api_host: bpy.props.StringProperty(name="API Host", default="localhost")
    #     api_port: bpy.props.IntProperty(name="API Port", default=8000) # デフォルトは8000

    def rig_with_unirig(context): # contextを渡すように変更
        # アドオンの設定からホストとポートを取得
        # unirig_props = context.scene.unirig_properties # プロパティグループの登録方法による
        # api_host = unirig_props.api_host
        # api_port = unirig_props.api_port
        # unirig_api_url = f"http://{api_host}:{api_port}/rig_model"
        
        # 以下、デモ用に固定値を使用。実際は上記のようにプロパティから取得
        unirig_api_url = "http://localhost:8000/rig_model" # ユーザーが設定変更できるようにするべき箇所

        # 1. モデルをエクスポート
        temp_dir = tempfile.mkdtemp()
        filepath = os.path.join(temp_dir, "model_to_rig.glb")
        
        # 現在選択されているオブジェクトを取得 (要調整)
        obj_to_export = bpy.context.active_object 
        if not obj_to_export or obj_to_export.type != 'MESH':
            print("メッシュオブジェクトを選択してください。")
            # self.report({'WARNING'}, "メッシュオブジェクトを選択してください。") # アドオンの場合
            return

        # エクスポート処理 (例)
        # 選択されたオブジェクトのみをエクスポートするように調整
        bpy.ops.export_scene.gltf(filepath=filepath, use_selection=True, export_format='GLB')

        # 2. UniRig APIに送信
        # unirig_api_url = "http://localhost:8000/rig_model" # WSL上のAPIエンドポイント # この行は上記で動的に生成するため不要
        try:
            with open(filepath, 'rb') as f:
                files = {'model_file': (os.path.basename(filepath), f, 'model/gltf-binary')}
                # タイムアウトを長めに設定 (例: 5分)
                response = requests.post(unirig_api_url, files=files, timeout=300) 
            
            response.raise_for_status() # HTTPエラーチェック

            # 3. 結果を受信してインポート
            # レスポンスヘッダーからファイル名を取得することを検討 (Content-Disposition)
            # ここでは仮に "rigged_model.glb" とします
            processed_filename = response.headers.get('Content-Disposition', 'filename="rigged_model.glb"').split('filename=')[-1].strip('"')
            if not processed_filename.endswith(('.glb', '.fbx', '.gltf')): # UniRigの出力形式に合わせて調整
                 processed_filename = "rigged_model.glb" # デフォルトフォールバック

            rigged_filepath = os.path.join(temp_dir, processed_filename)
            with open(rigged_filepath, 'wb') as f:
                f.write(response.content)
            
            if rigged_filepath.lower().endswith('.glb') or rigged_filepath.lower().endswith('.gltf'):
                bpy.ops.import_scene.gltf(filepath=rigged_filepath)
            elif rigged_filepath.lower().endswith('.fbx'):
                bpy.ops.import_scene.fbx(filepath=rigged_filepath)
            else:
                print(f"未対応のファイル形式です: {rigged_filepath}")
                # self.report({'WARNING'}, f"未対応のファイル形式です: {rigged_filepath}")
                return

            print("UniRigによるリギングが完了しました。")
            # self.report({'INFO'}, "UniRigによるリギングが完了しました。")

        except requests.exceptions.ConnectionError:
            print(f"UniRig API ({unirig_api_url}) に接続できませんでした。Dockerコンテナが起動しており、ポート設定が正しいか確認してください。")
            # self.report({'ERROR'}, f"UniRig API ({unirig_api_url}) に接続できませんでした。")
        except requests.exceptions.Timeout:
            print(f"UniRig API ({unirig_api_url}) がタイムアウトしました。モデルが大きいか、処理に時間がかかっています。")
            # self.report({'ERROR'}, f"UniRig API ({unirig_api_url}) がタイムアウトしました。")
        except requests.exceptions.HTTPError as e:
            error_detail = e.response.text
            print(f"UniRig APIエラー ({unirig_api_url}): {e.response.status_code} - {error_detail}")
            # self.report({'ERROR'}, f"UniRig APIエラー: {e.response.status_code} - {error_detail}")
        except Exception as e:
            print(f"エラーが発生しました: {e}")
            # self.report({'ERROR'}, f"エラーが発生しました: {e}")
        finally:
            # 一時ファイルを削除
            if os.path.exists(filepath):
                os.remove(filepath)
            if 'rigged_filepath' in locals() and os.path.exists(rigged_filepath):
                os.remove(rigged_filepath)
            os.rmdir(temp_dir)

    # Blenderアドオンの登録処理に上記関数を組み込む
    # (例: bpy.utils.register_class(UniRigProperties) のようにプロパティグループも登録)
    ```
*   **結果のインポート:** UniRig APIから返されたリギング済みモデルデータをBlenderにインポートします。

### 3. ネットワーク設定とテスト

*   **WSL IPアドレスの確認:** 必要に応じて、WSLのIPアドレスを確認します (`ip addr show eth0` など)。多くの場合、Windowsからは `localhost` でWSL内のサービスにアクセスできます。
*   **ファイアウォール:** Windows Defenderファイアウォールなどが、BlenderからWSL上のポート（例: ユーザーが指定したポート）への通信をブロックしていないか確認します。必要であれば許可ルールを追加します。
*   **テスト:** BlenderアドオンのUIでAPIホスト/ポートを設定し、ボタンをクリックしてモデルがWSL上のUniRigコンテナに送られ、処理結果がBlenderにインポートされることを確認します。

## 注意点

*   **エラーハンドリング:** API通信やファイル処理には堅牢なエラーハンドリングを実装することが重要です。
*   **パフォーマンス:** 大きなモデルファイルの場合、ネットワーク転送や処理に時間がかかることがあります。ユーザーに進捗状況をフィードバックするUIを検討してください。
*   **セキュリティ:** もしUniRig APIを外部ネットワークに公開する場合は、認証などのセキュリティ対策を講じる必要があります。ローカルホスト間の連携であれば、リスクは比較的低いです。
*   **ポート設定の案内:** Blenderアドオンの初回起動時やヘルプメニューなどで、Dockerコンテナの起動方法（ポート指定を含む）や、アドオン側でのAPIホスト/ポート設定方法をユーザーに明確に伝えることが重要です。
*   **UniRigのAPI設計:** UniRig側でどのようなAPIエンドポイントを公開するか（入力形式、出力形式、パラメータなど）を詳細に設計する必要があります。

このガイドは基本的な概念を示すものです。実際の開発では、より詳細な設計と実装が必要になります。