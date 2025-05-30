# NVIDIA CUDAベースイメージ (CUDA 12.1 + cuDNN 8)
FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04

# エラー出力をバッファリングしないように設定
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# 作業ディレクトリの設定
WORKDIR /app

# 基本システムパッケージのインストール
RUN apt-get update && apt-get install -y \
    git \
    wget \
    sudo \
    curl \
    libgl1-mesa-glx \
    libgl1-mesa-dri \
    libglu1-mesa \
    libxi6 \
    libxrender1 \
    libxkbcommon-x11-0 \
    xvfb \
    ninja-build \
    build-essential \
    cmake \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Minicondaのインストール
RUN wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh && \
    bash /tmp/miniconda.sh -b -p /opt/conda && \
    rm /tmp/miniconda.sh && \
    /opt/conda/bin/conda clean -ya

# 環境変数の設定
ENV PATH=/opt/conda/bin:$PATH

# Conda環境の作成
RUN conda create -n UniRig python=3.11 -y && \
    echo "source activate UniRig" >> ~/.bashrc

# ユニバーサルBashシェルを使用
SHELL ["/bin/bash", "-c"]

# Blenderのインストール
RUN mkdir -p /opt/blender && \
    wget -q https://download.blender.org/release/Blender4.2/blender-4.2.0-linux-x64.tar.xz && \
    tar -xf blender-4.2.0-linux-x64.tar.xz -C /opt/blender --strip-components=1 && \
    rm blender-4.2.0-linux-x64.tar.xz && \
    ln -s /opt/blender/blender /usr/local/bin/blender

# プロジェクトコードのコピー (Gradioアプリのapp.pyもここにコピーされる想定)
COPY . /app/

# 依存関係のインストール
RUN source activate UniRig && \
    # PyTorchを明示的にインストール
    pip install torch==2.3.1 torchvision --index-url https://download.pytorch.org/whl/cu121 && \
    # まずNinjaとTritonをインストール (flash-attnの依存関係)
    pip install ninja && \
    pip install triton && \
    # requirements.txtで指定された依存関係をインストール
    pip install -r requirements.txt && \
    # Gradioをインストール
    pip install gradio && \
    # その他の必須依存関係
    pip install spconv-cu121 && \
    pip install torch_scatter torch_cluster -f https://data.pyg.org/whl/torch-2.3.1+cu121.html --no-cache-dir && \
    pip install numpy==1.26.4 && \
    # Condaのキャッシュをクリーン
    conda clean -ya

# Blender用VRMアドオンのインストール
# Copy the pre-created Python script into the image
COPY install_blender_addon.py /app/install_blender_addon.py

RUN source activate UniRig && \
    mkdir -p /root/.config/blender/4.2/scripts/addons && \
    echo "Listing contents of /app and /app/blender before running Blender:" && \
    ls -l /app && \
    ls -l /app/blender && \
    xvfb-run -a blender --background --python /app/install_blender_addon.py && \
    echo "Blender script finished. Cleaning up." && \
    rm /app/install_blender_addon.py

# ARG to allow providing an initial PYTHONPATH value during build
ARG _ARG_INITIAL_PYTHONPATH=""

# 環境変数の設定
ENV PATH=/opt/conda/envs/UniRig/bin:$PATH
# Use the ARG to safely construct PYTHONPATH, defaulting to "/app" if ARG is empty
ENV PYTHONPATH="/app${_ARG_INITIAL_PYTHONPATH:+:${_ARG_INITIAL_PYTHONPATH}}"
ENV BLENDER_PATH=/opt/blender/blender
ENV CUDA_HOME=/usr/local/cuda
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# Gradioが使用するポートを開放
EXPOSE 7860

# ヘルスチェックコマンド
HEALTHCHECK CMD python -c "import torch; print('GPU available:', torch.cuda.is_available()); print('CUDA version:', torch.version.cuda)"

# Gradioアプリケーションを起動するコマンド
# app.py はGradioアプリケーションのメインスクリプトとします
# CMD ["source activate UniRig && python app.py"]
# For development, keep the container running
CMD ["sleep", "infinity"]