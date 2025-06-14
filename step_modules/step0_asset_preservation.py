#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 0 Module - Asset Preservation（アセット保存機能）
UV、マテリアル、テクスチャ情報の詳細保存（Step5で使用）

設計方針（2025年6月12日修正版）:
- UV、マテリアル、テクスチャ情報の詳細保存機能を復活
- .glbファイルとして完全なアセット情報を保存
- Step5でテクスチャ統合に使用するメタデータ生成

責務: UV、マテリアル、テクスチャ情報の詳細保存（Step5で使用）
入力: 3Dモデルファイルパス (.glb, .fbx, .obj, .vrm等)
出力: アセットメタデータJSON、テクスチャファイル群 (00_asset_preservation/内)
"""
import os
import sys
import json
import shutil
import logging
import time
import trimesh
from pathlib import Path
from typing import Tuple, Dict, Optional


class Step0AssetPreservation:
    """Step 0: Asset Preservation（アセット保存機能）"""

    def __init__(self, model_name: str, input_file: str, output_dir: str, logger_instance: logging.Logger):
        """
        Step0初期化

        Args:
            model_name: モデル名
            input_file: アップロードされた3Dモデルファイルパス
            output_dir: 出力ディレクトリ（00_asset_preservation/）
            logger_instance: ロガーインスタンス
        """
        self.model_name = model_name
        self.input_file = Path(input_file)
        self.output_dir = Path(output_dir)
        self.logger = logger_instance
        
        # 出力ディレクトリ作成
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Step0 Asset Preservation初期化: {self.model_name}")
        self.logger.info(f"入力ファイル: {self.input_file}")
        self.logger.info(f"出力ディレクトリ: {self.output_dir}")

    def preserve_assets(self) -> Tuple[bool, str, Dict]:
        """
        アセット保存処理（完全なアセット情報を保存）
        
        Returns:
            success: 保存成功フラグ
            logs: 保存ログ
            output_files: 保存されたファイルパス情報
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"=== Step 0: {self.model_name} アセット保存開始 ===")
            
            # 入力ファイル存在確認
            if not self.input_file.exists():
                error_msg = f"入力ファイルが存在しません: {self.input_file}"
                self.logger.error(error_msg)
                return False, error_msg, {}
            
            # ファイルサイズ確認
            file_size_mb = self.input_file.stat().st_size / (1024 * 1024)
            self.logger.info(f"ファイルサイズ: {file_size_mb:.1f}MB")
            
            # ファイル拡張子取得
            file_extension = self.input_file.suffix.lower()
            
            # 元のファイルを保存（完全な情報保持）
            preserved_file = self.output_dir / f"{self.model_name}{file_extension}"
            shutil.copy2(self.input_file, preserved_file)
            self.logger.info(f"アセットファイル保存完了: {preserved_file}")
            
            # アセット情報解析
            asset_info = self._analyze_asset_info()
            
            # メタデータJSON生成
            metadata = {
                "model_name": self.model_name,
                "original_file": str(self.input_file),
                "preserved_file": str(preserved_file),
                "file_extension": file_extension,
                "file_size_mb": round(file_size_mb, 2),
                "preservation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "asset_info": asset_info
            }
            
            # メタデータJSON保存
            metadata_file = self.output_dir / f"{self.model_name}_asset_metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"メタデータ保存完了: {metadata_file}")
            
            # 処理時間計算
            processing_time = time.time() - start_time
            
            success_log = (
                f"Step 0 アセット保存完了: {self.input_file.name} → {preserved_file.name} "
                f"({file_size_mb:.1f}MB, {processing_time:.2f}秒)"
            )
            self.logger.info(success_log)
            
            # 出力ファイル情報
            output_files = {
                "preserved_original": str(preserved_file),
                "asset_metadata_json": str(metadata_file)
            }
            
            return True, success_log, output_files
            
        except Exception as e:
            error_msg = f"Step 0 アセット保存エラー: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg, {}
    
    def _analyze_asset_info(self) -> Dict:
        """
        3Dモデルのアセット情報解析
        
        Returns:
            アセット情報辞書
        """
        asset_info = {
            "has_textures": False,
            "texture_count": 0,
            "material_count": 0,
            "vertex_count": 0,
            "face_count": 0,
            "uv_coordinates": 0,
            "analysis_method": "trimesh"
        }
        
        try:
            # trimeshでシーン読み込み
            scene = trimesh.load(str(self.input_file))
            
            # シーン内のジオメトリ解析
            if hasattr(scene, 'geometry'):
                for name, geometry in scene.geometry.items():
                    if hasattr(geometry, 'vertices'):
                        asset_info["vertex_count"] += len(geometry.vertices)
                    if hasattr(geometry, 'faces'):
                        asset_info["face_count"] += len(geometry.faces)
                    if hasattr(geometry, 'visual') and hasattr(geometry.visual, 'uv'):
                        if geometry.visual.uv is not None:
                            asset_info["uv_coordinates"] += len(geometry.visual.uv)
                    
                    # PBRマテリアルからテクスチャ検出
                    if hasattr(geometry, 'visual') and hasattr(geometry.visual, 'material'):
                        material = geometry.visual.material
                        asset_info["material_count"] += 1
                        
                        # PBRマテリアルのテクスチャ属性をチェック
                        texture_attributes = [
                            'baseColorTexture',
                            'metallicRoughnessTexture', 
                            'normalTexture',
                            'occlusionTexture',
                            'emissiveTexture'
                        ]
                        
                        for texture_attr in texture_attributes:
                            if hasattr(material, texture_attr):
                                texture = getattr(material, texture_attr)
                                if texture is not None:
                                    asset_info["texture_count"] += 1
                                    self.logger.info(f"テクスチャ検出: {texture_attr} = {type(texture)}")
            
            # 従来のトップレベルマテリアル解析（互換性のため）
            if hasattr(scene, 'materials'):
                for material in scene.materials:
                    # 従来の image 属性チェック（互換性のため）
                    if hasattr(material, 'image') and material.image:
                        asset_info["texture_count"] += 1
            
            asset_info["has_textures"] = asset_info["texture_count"] > 0
            self.logger.info(f"アセット解析結果: {asset_info}")
            
        except Exception as e:
            self.logger.warning(f"アセット解析エラー（処理続行）: {str(e)}")
        
        return asset_info


# 新設計に基づく統一APIインターフェース
def preserve_assets(input_file: str, model_name: str, output_dir: str) -> Tuple[bool, str, Dict]:
    """
    Step0統一APIインターフェース - アセット保存機能
    
    Args:
        input_file: アップロードされた3Dモデルファイルパス
        model_name: モデル識別名
        output_dir: 出力ディレクトリ（00_asset_preservation/）
    
    Returns:
        success: True/False
        logs: "アセット保存完了: /path/to/preserved_file" 
        output_files: {
            "preserved_original": "/path/to/model.glb",
            "asset_metadata_json": "/path/to/model_asset_metadata.json"
        }
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
        # Step0アセット保存実行
        step0_processor = Step0AssetPreservation(
            model_name=model_name,
            input_file=input_file,
            output_dir=output_dir,
            logger_instance=logger
        )
        
        return step0_processor.preserve_assets()
        
    except Exception as e:
        error_msg = f"Step0統一API実行エラー: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg, {}


# 互換性のための関数（ファイル転送のみ・機能簡略化）
def transfer_file(input_file: str, model_name: str) -> Tuple[bool, str, Dict]:
    """
    旧ファイル転送API（互換性のみ・機能簡略化済み）
    
    注意: この関数は新設計では使用されません。
    preserve_assets()関数を使用してください。
    """
    logger = logging.getLogger(f"Step0_Transfer_{model_name}")
    logger.warning("transfer_file()は非推奨です。preserve_assets()を使用してください。")
    
    try:
        # ダミー出力ディレクトリ
        dummy_output_dir = "/tmp/step0_dummy"
        
        # preserve_assets()に転送
        success, logs, output_files = preserve_assets(input_file, model_name, dummy_output_dir)
        
        # 旧形式のレスポンス（空の辞書）
        return success, logs, {}
        
    except Exception as e:
        error_msg = f"転送API実行エラー: {str(e)}"
        logger.error(error_msg)
        return False, error_msg, {}


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
    success, logs, output_files = preserve_assets(input_file, model_name, "/tmp/step0_test")
    
    print(f"\n=== Step0実行結果 ===")
    print(f"成功: {success}")
    print(f"ログ: {logs}")
    print(f"出力ファイル: {output_files}")
    
    if success:
        print("\n✅ Step0 ファイル転送成功")
    else:
        print("\n❌ Step0 ファイル転送失敗")
        sys.exit(1)
