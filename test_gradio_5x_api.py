#!/usr/bin/env python3
"""
Gradio 5.x API用の自動リギング機能テストスクリプト
"""

import os
import sys
import time
import logging
from gradio_client import Client, file

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_gradio_api():
    """Gradio APIを使用して自動リギング機能をテストします"""
    
    # Gradioサーバーに接続
    server_url = "http://127.0.0.1:7860"
    logger.info(f"Gradioサーバーに接続中: {server_url}")
    
    try:
        client = Client(server_url)
        logger.info("Gradioクライアント接続成功")
        
        # 使用可能なAPIエンドポイントを確認
        logger.info("使用可能なAPIエンドポイント:")
        logger.info(client.view_api())
        
        # テスト用モデルファイルのパス
        test_model_path = "/app/examples/bird.glb"
        
        if not os.path.exists(test_model_path):
            logger.error(f"テストモデルファイルが見つかりません: {test_model_path}")
            return False
            
        logger.info(f"テストモデル: {test_model_path}")
        logger.info(f"ファイルサイズ: {os.path.getsize(test_model_path)} bytes")
        
        # 自動リギング機能をテスト
        logger.info("自動リギング機能をテスト中...")
        
        # gradio_clientのfile()関数を使用してファイルを準備
        test_file = file(test_model_path)
        gender = "neutral"
        
        # APIエンドポイントを呼び出し
        result = client.predict(
            original_model_file_obj=test_file,
            gender=gender,
            api_name="/gradio_full_auto_rigging"
        )
        
        logger.info("自動リギング処理完了")
        logger.info(f"結果: {type(result)}")
        
        # 結果を解析
        if isinstance(result, (list, tuple)) and len(result) >= 3:
            display_model_path, logs, download_file_path = result[:3]
            
            logger.info(f"表示用モデルパス: {display_model_path}")
            logger.info(f"処理ログ: {logs}")
            logger.info(f"ダウンロード用ファイルパス: {download_file_path}")
            
            # ログの内容を確認
            if logs:
                logger.info("=== 処理ログの内容 ===")
                for line in str(logs).split('\n'):
                    if line.strip():
                        logger.info(f"LOG: {line.strip()}")
            
            # 結果ファイルの存在確認
            if display_model_path and os.path.exists(display_model_path):
                logger.info(f"✅ 表示用モデルファイルが生成されました: {display_model_path}")
                logger.info(f"   ファイルサイズ: {os.path.getsize(display_model_path)} bytes")
            else:
                logger.warning("⚠️ 表示用モデルファイルが生成されませんでした")
                
            if download_file_path and os.path.exists(download_file_path):
                logger.info(f"✅ ダウンロード用ファイルが生成されました: {download_file_path}")
                logger.info(f"   ファイルサイズ: {os.path.getsize(download_file_path)} bytes")
            else:
                logger.warning("⚠️ ダウンロード用ファイルが生成されませんでした")
            
            return True
        else:
            logger.error(f"予期しない結果形式: {result}")
            return False
            
    except Exception as e:
        logger.error(f"API呼び出し中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_individual_endpoints():
    """個別のAPIエンドポイントをテストします"""
    
    server_url = "http://127.0.0.1:7860"
    logger.info(f"個別エンドポイントテストを開始: {server_url}")
    
    try:
        client = Client(server_url)
        test_model_path = "/app/examples/bird.glb"
        
        if not os.path.exists(test_model_path):
            logger.error(f"テストモデルファイルが見つかりません: {test_model_path}")
            return False
        
        # 1. スケルトン生成をテスト
        logger.info("=== スケルトン生成APIテスト ===")
        try:
            skeleton_result = client.predict(
                input_model_skel=file(test_model_path),
                motion_sequence_input_skel=None,
                person_measurements_input_skel=None,
                gender_dropdown_skel="neutral",
                api_name="/gradio_generate_skeleton"
            )
            logger.info(f"スケルトン生成結果: {type(skeleton_result)}")
            if skeleton_result:
                logger.info("✅ スケルトン生成API正常動作")
            else:
                logger.warning("⚠️ スケルトン生成APIから空の結果")
        except Exception as e:
            logger.error(f"スケルトン生成APIエラー: {e}")
        
        # 2. スキニング生成をテスト（スケルトンファイルが必要）
        logger.info("=== スキニング生成APIテスト ===")
        try:
            # テスト用のスケルトンファイルがあるかチェック
            skeleton_file_path = "/app/examples/skeleton"
            if os.path.exists(skeleton_file_path):
                skin_result = client.predict(
                    skin_input_model=file(test_model_path),
                    skin_input_skeleton_text=file(skeleton_file_path),
                    api_name="/gradio_generate_skin"
                )
                logger.info(f"スキニング生成結果: {type(skin_result)}")
                if skin_result:
                    logger.info("✅ スキニング生成API正常動作")
                else:
                    logger.warning("⚠️ スキニング生成APIから空の結果")
            else:
                logger.info("スケルトンファイルが存在しないため、スキニング生成APIをスキップ")
        except Exception as e:
            logger.error(f"スキニング生成APIエラー: {e}")
            
        return True
        
    except Exception as e:
        logger.error(f"個別エンドポイントテスト中にエラー: {e}")
        return False

def main():
    """メイン関数"""
    logger.info("=== Gradio 5.x API自動リギング機能テスト開始 ===")
    
    # Gradioサーバーが起動しているかチェック
    import requests
    try:
        response = requests.get("http://127.0.0.1:7860", timeout=5)
        if response.status_code == 200:
            logger.info("✅ Gradioサーバーが起動中")
        else:
            logger.error(f"❌ Gradioサーバーレスポンス異常: {response.status_code}")
            return False
    except requests.ConnectionError:
        logger.error("❌ Gradioサーバーに接続できません。アプリケーションが起動していることを確認してください。")
        return False
    except Exception as e:
        logger.error(f"❌ サーバー接続チェックエラー: {e}")
        return False
    
    # メインの自動リギング機能をテスト
    success = test_gradio_api()
    
    if success:
        logger.info("🎉 自動リギング機能テスト成功!")
        
        # 個別エンドポイントもテスト
        logger.info("\n=== 個別エンドポイントテスト ===")
        test_individual_endpoints()
        
    else:
        logger.error("❌ 自動リギング機能テスト失敗")
        return False
    
    logger.info("=== テスト完了 ===")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
