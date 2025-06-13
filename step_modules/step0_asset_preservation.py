#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 0 Module - シンプルファイル転送（2025年6月10日改訂版）
アップロードされたモデルをStep1に転送するだけのシンプル機能

新設計方針:
- アセット保存機能は完全廃止
- UV・マテリアル・テクスチャ構造の保存機能を完全廃止
- ファイル転送確認のみの最小限処理

責務: アップロードされたモデルファイル → Step1への転送確認
入力: 3Dモデルファイルパス (.glb, .fbx, .obj等)
出力: ファイル転送完了フラグのみ（空の辞書）

従来の504行から約150行に大幅簡略化
"""
import os
import sys
import logging
import time
from pathlib import Path
from typing import Tuple, Dict


class Step0FileTransfer:
    """Step 0: シンプルファイル転送モジュール（機能簡略化版）"""

    def __init__(self, model_name: str, input_file: str, output_dir: str, logger_instance: logging.Logger):
        """
        Step0初期化

        Args:
            model_name: モデル名
            input_file: アップロードされた3Dモデルファイルパス
            output_dir: 出力ディレクトリ（使用しないが互換性のため保持）
            logger_instance: ロガーインスタンス
        """
        self.model_name = model_name
        self.input_file = Path(input_file)
        self.output_dir = Path(output_dir)
        self.logger = logger_instance
        
        # 出力ディレクトリは作成しない（ファイル転送のみ）
        self.logger.info(f"Step0 ファイル転送初期化: {self.model_name}")
        self.logger.info(f"入力ファイル: {self.input_file}")

    def transfer_file(self) -> Tuple[bool, str, Dict]:
        """
        シンプルファイル転送処理（機能簡略化版）
        
        Returns:
            success: 転送成功フラグ
            logs: 転送ログ
            output_files: 空の辞書（ファイル出力なし）
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"=== Step 0: {self.model_name} ファイル転送開始 ===")
            
            # 入力ファイル存在確認
            if not self.input_file.exists():
                error_msg = f"入力ファイルが存在しません: {self.input_file}"
                self.logger.error(error_msg)
                return False, error_msg, {}
            
            # ファイルサイズ確認
            file_size_mb = self.input_file.stat().st_size / (1024 * 1024)
            self.logger.info(f"ファイルサイズ: {file_size_mb:.1f}MB")
            
            # ファイル形式確認
            file_extension = self.input_file.suffix.lower()
            supported_formats = ['.glb', '.fbx', '.obj', '.gltf', '.ply', '.dae']
            
            if file_extension not in supported_formats:
                warning_msg = f"未確認のファイル形式: {file_extension} (サポート形式: {', '.join(supported_formats)})"
                self.logger.warning(warning_msg)
            else:
                self.logger.info(f"ファイル形式確認済み: {file_extension}")
            
            # 処理時間計算
            processing_time = time.time() - start_time
            
            success_log = (
                f"Step 0 ファイル転送完了: {self.input_file.name} "
                f"({file_size_mb:.1f}MB, {processing_time:.2f}秒)"
            )
            self.logger.info(success_log)
            
            # ファイル出力なし、転送準備完了のみ
            return True, success_log, {}
            
        except Exception as e:
            error_msg = f"Step 0 ファイル転送エラー: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg, {}


# 新設計に基づく統一APIインターフェース
def transfer_file(input_file: str, model_name: str) -> Tuple[bool, str, Dict]:
    """
    Step0統一APIインターフェース - ファイル転送のみ（機能簡略化）
    
    Args:
        input_file: アップロードされた3Dモデルファイルパス
        model_name: モデル識別名
    
    Returns:
        success: True/False
        logs: "ファイル転送完了: /path/to/file" 
        output_files: {} (空の辞書・ファイル出力なし)
    """
    # 簡易ロガー作成
    logger = logging.getLogger(f"Step0_{model_name}")
    logger.setLevel(logging.INFO)
    
    # ハンドラーが既に存在しない場合のみ追加
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    try:
        # ダミー出力ディレクトリ（使用しない）
        dummy_output_dir = "/tmp/step0_dummy"
        
        # Step0ファイル転送実行
        step0_processor = Step0FileTransfer(
            model_name=model_name,
            input_file=input_file,
            output_dir=dummy_output_dir,
            logger_instance=logger
        )
        
        return step0_processor.transfer_file()
        
    except Exception as e:
        error_msg = f"Step0統一API実行エラー: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg, {}


# 互換性のための関数（使用非推奨・将来削除予定）
def preserve_assets(input_file: str, model_name: str, output_dir: str) -> Tuple[bool, str, Dict[str, str]]:
    """
    旧アセット保存API（互換性のみ・機能簡略化済み）
    
    注意: この関数は新設計では使用されません。
    transfer_file()関数を使用してください。
    """
    logger = logging.getLogger(f"Step0_Deprecated_{model_name}")
    logger.warning("preserve_assets()は非推奨です。transfer_file()を使用してください。")
    
    # 新しいtransfer_file()に転送
    success, logs, _ = transfer_file(input_file, model_name)
    
    # 旧形式のレスポンス（空の辞書）
    return success, logs, {}


if __name__ == "__main__":
    # テスト実行
    if len(sys.argv) != 3:
        print("使用方法: python step0_asset_preservation.py <input_file> <model_name>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    model_name = sys.argv[2]
    
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Step0実行
    success, logs, output_files = transfer_file(input_file, model_name)
    
    print(f"\n=== Step0実行結果 ===")
    print(f"成功: {success}")
    print(f"ログ: {logs}")
    print(f"出力ファイル: {output_files}")
    
    if success:
        print("\n✅ Step0 ファイル転送成功")
    else:
        print("\n❌ Step0 ファイル転送失敗")
        sys.exit(1)
