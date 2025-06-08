"""
Step 1 Module - メッシュ抽出
独立した実行機能として、3Dモデルからメッシュデータを抽出

責務: 3Dモデルファイル → メッシュNPZファイル
入力: 3Dモデルファイルパス (.glb, .fbx, .obj等)
出力: メッシュデータファイルパス (.npz)
"""

import os
import sys
import logging
import subprocess
import yaml
from pathlib import Path
from typing import Tuple, Dict, Optional
import json
import numpy as np
import time

# UniRig実行パス設定
sys.path.append('/app')

logger = logging.getLogger(__name__)

class Step1Extract:
    """Step 1: メッシュ抽出モジュール"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    def extract_mesh(self, input_file: str, model_name: str, preserve_textures: bool = True) -> Tuple[bool, str, Dict]:
        """
        実際のメッシュ抽出の実行 (UniRig extract.py使用)
        
        Args:
            input_file: 入力3Dモデルファイルパス
            model_name: モデル名（出力ファイル名に使用）
            preserve_textures: テクスチャ情報を保持するか
            
        Returns:
            (success, logs, output_files)
        """
        logs = ""
        try:
            logger.info(f"Step 1 開始: {input_file} → {model_name}")
            
            # 入力ファイル存在確認
            if not os.path.exists(input_file):
                error_msg = f"❌ 入力ファイルが見つかりません: {input_file}"
                logger.error(error_msg)
                return False, error_msg, {}
            
            # Gradio一時ファイルを永続的な場所にコピー
            import shutil
            persistent_input = self.output_dir / f"{model_name}_input{Path(input_file).suffix}"
            if not persistent_input.exists():
                shutil.copy2(input_file, persistent_input)
                logs += f"📋 入力ファイル永続化: {persistent_input}\n"
            
            # 出力ファイルパス
            output_npz = self.output_dir / "raw_data.npz"  # UniRigデフォルト名
            output_datalist = self.output_dir / "inference_datalist.txt"  # UniRigデフォルト名
            config_path = "/app/configs/extract_config.yaml"
            
            logs += f"🔍 メッシュ抽出開始: {input_file}\n"
            logs += f"📁 出力ディレクトリ: {self.output_dir}\n"
            
            # UniRig extract.py実行
            cmd = [
                sys.executable, "-m", "src.data.extract",
                "--config", config_path,
                "--model_path", str(persistent_input),  # 永続化されたファイルを使用
                "--output_dir", str(self.output_dir)
            ]
            
            logs += f"🚀 実行コマンド: {' '.join(cmd)}\n"
            
            # 実行環境設定
            env = os.environ.copy()
            env['PYTHONPATH'] = f"/app:{env.get('PYTHONPATH', '')}"
            env['GRADIO'] = '1'  # Gradio環境として認識
            
            # UniRig抽出処理実行
            start_time = time.time()
            result = subprocess.run(
                cmd,
                cwd="/app",
                env=env,
                capture_output=True,
                text=True,
                timeout=120  # 2分タイムアウト
            )
            
            execution_time = time.time() - start_time
            logs += f"⏱️ 実行時間: {execution_time:.2f}秒\n"
            
            # 結果確認
            if result.returncode == 0:
                logs += "✅ UniRig抽出プロセス正常終了\n"
                
                # 出力ファイル確認
                if output_npz.exists():
                    file_size = output_npz.stat().st_size
                    file_size_mb = file_size / (1024 * 1024)
                    logs += f"📊 NPZファイル生成: {output_npz.name} ({file_size:,} bytes, {file_size_mb:.2f} MB)\n"
                    
                    # データリスト確認
                    if output_datalist.exists():
                        logs += f"📋 データリスト生成: {output_datalist.name}\n"
                    
                    # 出力ファイル情報
                    output_files = {
                        "extracted_npz": str(output_npz),  # Step2が期待するキー名に修正
                        "extracted_mesh": str(output_npz),  # 後方互換性のため
                        "datalist": str(output_datalist) if output_datalist.exists() else None,
                        "model_name": model_name,
                        "file_size": file_size,
                        "preserve_textures": preserve_textures
                    }
                    
                    # テクスチャ保存処理
                    if preserve_textures:
                        texture_info = self._preserve_texture_metadata(input_file, model_name)
                        output_files.update(texture_info)
                        logs += f"🎨 テクスチャメタデータ保存完了\n"
                    
                    logs += "✅ Step 1: メッシュ抽出完了\n"
                    return True, logs, output_files
                else:
                    error_msg = f"❌ NPZファイルが生成されませんでした: {output_npz}"
                    logs += error_msg + "\n"
                    return False, logs, {}
            else:
                # エラー処理
                logs += f"❌ UniRig抽出プロセスエラー (コード: {result.returncode})\n"
                if result.stdout:
                    logs += f"STDOUT:\n{result.stdout}\n"
                if result.stderr:
                    logs += f"STDERR:\n{result.stderr}\n"
                return False, logs, {}
                
        except subprocess.TimeoutExpired:
            error_msg = "❌ タイムアウト: メッシュ抽出処理が2分を超過しました"
            logs += error_msg + "\n"
            logger.error(error_msg)
            return False, logs, {}
        except Exception as e:
            error_msg = f"❌ Step 1 実行エラー: {str(e)}"
            logs += error_msg + "\n"
            logger.error(error_msg, exc_info=True)
            return False, logs, {}
    
    def _preserve_texture_metadata(self, input_file: str, model_name: str) -> Dict:
        """テクスチャメタデータの保存"""
        try:
            # テクスチャディレクトリ作成
            texture_dir = self.output_dir / "textures"
            texture_dir.mkdir(exist_ok=True)
            
            # メタデータファイルパス
            metadata_file = self.output_dir / f"{model_name}_texture_metadata.json"
            
            # 基本的なメタデータ情報
            metadata = {
                "model_name": model_name,
                "original_file": input_file,
                "preserved_at": time.time(),
                "texture_directory": str(texture_dir),
                "materials": [],
                "textures": []
            }
            
            # メタデータファイル保存
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            return {
                "texture_metadata": str(metadata_file),
                "texture_directory": str(texture_dir),
                "texture_count": len(metadata.get("textures", []))
            }
        except Exception as e:
            logger.warning(f"テクスチャメタデータ保存エラー: {e}")
            return {"texture_metadata": None, "texture_directory": None, "texture_count": 0}


# def extract_mesh(input_file: str, model_name: str) -> tuple[bool, str, dict]: # 元の関数名
def execute_step1(input_file: str, model_name: str, output_dir: Path, preserve_textures: bool = True) -> tuple[bool, str, dict]: # 新しい関数名と引数の追加
    """
    3Dモデルからメッシュデータを抽出します。

    Args:
        input_file: 3Dモデルファイルパス
        model_name: モデル名
        output_dir: 出力ディレクトリのパス (Pathオブジェクト)
        preserve_textures: テクスチャ情報を保持するか

    Returns:
        success: 成功フラグ (True/False)
        logs: 実行ログメッセージ
        output_files: 出力ファイル辞書
    """
    try:
        # Step1Extractクラスのインスタンスを作成して、そのメソッドを呼び出す
        extractor = Step1Extract(output_dir=output_dir) # output_dirは既にPathオブジェクトであることを期待
        return extractor.extract_mesh(input_file, model_name, preserve_textures)
    except Exception as e:
        error_message = f"Step 1 実行中に予期せぬエラーが発生: {e}"
        logger.error(error_message, exc_info=True)
        return False, error_message, {}

if __name__ == '__main__':
    # モジュールのテスト用コード
    # 実際のファイルパスやモデル名に置き換えてください
    test_input_file = "/app/examples/bird.glb"
    test_model_name = "bird_test" # テスト実行時と通常実行時でファイル名が衝突しないように
    test_output_dir = Path("/app/pipeline_work/01_extracted_mesh_test") # テスト用の出力ディレクトリ

    if not os.path.exists(test_input_file):
        print(f"テスト用入力ファイルが見つかりません: {test_input_file}")
        print("代わりにダミーファイルを作成してテストを続行します。")
        os.makedirs(os.path.dirname(test_input_file), exist_ok=True)
        with open(test_input_file, 'w') as f:
            f.write("dummy glb data")
        created_dummy_input = True
    else:
        created_dummy_input = False

    print(f"テスト実行: execute_step1('{test_input_file}', '{test_model_name}', Path('{test_output_dir}'))")
    success, logs, files = execute_step1(test_input_file, test_model_name, test_output_dir)
    
    print("\\n--- テスト実行結果 ---")
    print(f"  成功: {success}")
    print(f"  ログ: {logs}")
    print(f"  出力ファイル: {files}")

    # クリーンアップ
    if success and "extracted_mesh" in files and os.path.exists(files["extracted_mesh"]): # "extracted_npz" から "extracted_mesh" に変更
        os.remove(files["extracted_mesh"])
        print(f"  クリーンアップ: {files['extracted_mesh']} を削除しました。")
    
    # テストで作成された可能性のある他のファイルも削除
    if success and files.get("datalist") and os.path.exists(files["datalist"]):
        os.remove(files["datalist"])
        print(f"  クリーンアップ: {files['datalist']} を削除しました。")
    if success and files.get("texture_metadata") and os.path.exists(files["texture_metadata"]):
        os.remove(files["texture_metadata"])
        print(f"  クリーンアップ: {files['texture_metadata']} を削除しました。")
    
    # テスト用出力ディレクトリ自体も削除 (中身が空なら)
    try:
        if test_output_dir.exists() and not any(test_output_dir.iterdir()):
            test_output_dir.rmdir()
            print(f"  クリーンアップ: テスト用出力ディレクトリ {test_output_dir} を削除しました。")
        elif test_output_dir.exists():
            print(f"  注意: テスト用出力ディレクトリ {test_output_dir} は空ではないため削除されませんでした。")
    except Exception as e:
        print(f"  クリーンアップ中エラー: {e}")

    if created_dummy_input:
        os.remove(test_input_file)
        print(f"  クリーンアップ: ダミー入力ファイル {test_input_file} を削除しました。")

    print("--- テスト完了 ---")
