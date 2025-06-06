#!/usr/bin/env python3
"""
CPU環境対応メッシュエンコーダー

PTv3Object（spconv依存）の代替として、CPU環境で動作する
シンプルなメッシュエンコーダーを提供
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Optional, Tuple


class SimpleCPUMeshEncoder(nn.Module):
    """
    CPU環境で動作するシンプルなメッシュエンコーダー
    Point Transformer V3の代替として軽量な処理を実行
    """
    
    def __init__(self, 
                 in_channels: int = 6,  # xyz + normals
                 enc_channels: List[int] = [32, 64, 128, 256],
                 num_layers: int = 4,
                 num_heads: int = 8,
                 dropout: float = 0.1):
        super().__init__()
        
        self.in_channels = in_channels
        self.enc_channels = enc_channels
        self.num_layers = num_layers
        self.num_heads = num_heads
        
        # 入力プロジェクション
        self.input_proj = nn.Linear(in_channels, enc_channels[0])
        
        # 階層的特徴抽出
        self.encoders = nn.ModuleList()
        for i in range(len(enc_channels) - 1):
            self.encoders.append(
                nn.Sequential(
                    nn.Linear(enc_channels[i], enc_channels[i + 1]),
                    nn.LayerNorm(enc_channels[i + 1]),
                    nn.ReLU(),
                    nn.Dropout(dropout)
                )
            )
        
        # マルチヘッドアテンション層
        self.attention_layers = nn.ModuleList()
        for _ in range(num_layers):
            self.attention_layers.append(
                nn.MultiheadAttention(
                    embed_dim=enc_channels[-1],
                    num_heads=num_heads,
                    dropout=dropout,
                    batch_first=True
                )
            )
            
        # LayerNorm layers
        self.layer_norms = nn.ModuleList([
            nn.LayerNorm(enc_channels[-1]) for _ in range(num_layers)
        ])
        
        # 出力プロジェクション
        self.output_proj = nn.Linear(enc_channels[-1], enc_channels[-1])
        
    def forward(self, coords: torch.Tensor, 
                features: Optional[torch.Tensor] = None,
                batch: Optional[torch.Tensor] = None) -> Dict[str, torch.Tensor]:
        """
        前向き処理
        
        Args:
            coords: 座標 (N, 3)
            features: 特徴量 (N, C) または None
            batch: バッチインデックス (N,) または None
            
        Returns:
            特徴量辞書
        """
        device = coords.device
        N = coords.shape[0]
        
        # 入力特徴量の準備
        if features is None:
            # 座標のみを使用
            input_features = coords  # (N, 3)
        else:
            # 座標と特徴量を結合
            input_features = torch.cat([coords, features], dim=-1)  # (N, 3+C)
            
        # バッチ処理の準備
        if batch is None:
            batch = torch.zeros(N, dtype=torch.long, device=device)
            
        # バッチごとの処理
        batch_size = batch.max().item() + 1
        outputs = []
        
        for b in range(batch_size):
            mask = (batch == b)
            if not mask.any():
                continue
                
            batch_features = input_features[mask]  # (N_b, C)
            
            # 入力プロジェクション
            x = self.input_proj(batch_features)
            
            # 階層的特徴抽出
            for encoder in self.encoders:
                x = encoder(x)
                
            # Self-attention処理
            for attn, norm in zip(self.attention_layers, self.layer_norms):
                residual = x
                x, _ = attn(x, x, x)
                x = norm(x + residual)
                
            # 出力プロジェクション
            x = self.output_proj(x)
            
            outputs.append(x)
            
        # バッチを再結合
        if len(outputs) == 1:
            final_features = outputs[0]
        else:
            final_features = torch.cat(outputs, dim=0)
            
        return {
            'features': final_features,
            'coordinates': coords
        }


class CPUMeshEncoderWrapper:
    """
    PTv3Objectインターフェース互換のラッパー
    """
    
    def __init__(self, enc_channels: List[int] = [32, 64, 128, 256], **kwargs):
        self.enc_channels = enc_channels
        self.encoder = SimpleCPUMeshEncoder(enc_channels=enc_channels, **kwargs)
        
    def __call__(self, *args, **kwargs):
        return self.encoder(*args, **kwargs)
        
    def cuda(self):
        """CUDA移行（CPU版では何もしない）"""
        return self
        
    def cpu(self):
        """CPU移行"""
        self.encoder = self.encoder.cpu()
        return self
        
    def to(self, device):
        """デバイス移行"""
        self.encoder = self.encoder.to(device)
        return self
        
    def train(self, mode=True):
        """訓練モード設定"""
        self.encoder.train(mode)
        return self
        
    def eval(self):
        """評価モード設定"""
        self.encoder.eval()
        return self
        
    def parameters(self):
        """パラメータ取得"""
        return self.encoder.parameters()
        
    def state_dict(self):
        """状態辞書取得"""
        return self.encoder.state_dict()
        
    def load_state_dict(self, state_dict):
        """状態辞書読み込み"""
        return self.encoder.load_state_dict(state_dict)


def get_cpu_encoder(**kwargs) -> CPUMeshEncoderWrapper:
    """
    CPU対応エンコーダーのファクトリ関数
    PTv3Objectのget_encoder関数と互換
    """
    return CPUMeshEncoderWrapper(**kwargs)


class AdaptiveMeshEncoder(nn.Module):
    """
    GPU/CPU環境を自動判定して適切なエンコーダーを選択
    """
    
    def __init__(self, fallback_to_cpu: bool = True, **kwargs):
        super().__init__()
        self.fallback_to_cpu = fallback_to_cpu
        
        # CUDA利用可能性チェック
        self.use_cuda = torch.cuda.is_available() and not fallback_to_cpu
        
        if self.use_cuda:
            try:
                # PTv3Objectを試行
                from .pointcept.models.PTv3Object import get_encoder as get_ptv3_encoder
                self.encoder = get_ptv3_encoder(**kwargs)
                self.encoder_type = "ptv3"
                print("🚀 PTv3Object エンコーダーを使用（CUDA）")
            except Exception as e:
                print(f"⚠️ PTv3Object初期化失敗: {e}")
                print("🔄 CPUエンコーダーにフォールバック")
                self.encoder = get_cpu_encoder(**kwargs)
                self.encoder_type = "cpu"
        else:
            self.encoder = get_cpu_encoder(**kwargs)
            self.encoder_type = "cpu"
            print("🔧 CPUエンコーダーを使用")
            
    def forward(self, *args, **kwargs):
        return self.encoder(*args, **kwargs)
        
    def get_encoder_info(self) -> Dict[str, str]:
        """エンコーダー情報を取得"""
        return {
            "type": self.encoder_type,
            "device": "cuda" if self.use_cuda else "cpu",
            "fallback_enabled": self.fallback_to_cpu
        }


def get_adaptive_encoder(**kwargs) -> AdaptiveMeshEncoder:
    """
    環境に応じた適応的エンコーダーを取得
    """
    return AdaptiveMeshEncoder(**kwargs)
