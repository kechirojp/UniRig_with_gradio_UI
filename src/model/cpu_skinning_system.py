#!/usr/bin/env python3
"""
CPU環境対応スキニングシステム

UniRig スキニングウェイト予測のCPU環境フォールバック実装
CUDA/spconv依存を回避し、CPU環境で動作する軽量スキニング処理
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import os
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from .cpu_mesh_encoder import get_adaptive_encoder


@dataclass
class SkinningResult:
    """スキニング結果データクラス"""
    skin_weights: np.ndarray  # (N, J) 
    vertex_groups: Dict[str, Any]
    processing_info: Dict[str, Any]


class CPUSkinningPredictor(nn.Module):
    """
    CPU環境でのスキニングウェイト予測
    """
    
    def __init__(self, 
                 feat_dim: int = 256,
                 num_heads: int = 8,
                 max_bones: int = 256,
                 dropout: float = 0.1):
        super().__init__()
        
        self.feat_dim = feat_dim
        self.num_heads = num_heads
        self.max_bones = max_bones
        
        # メッシュ特徴抽出
        self.mesh_encoder = get_adaptive_encoder(
            enc_channels=[32, 64, 128, feat_dim],
            num_heads=num_heads,
            dropout=dropout
        )
        
        # ボーン特徴エンコーダー
        self.bone_encoder = nn.Sequential(
            nn.Linear(3, 64),  # joint coordinates
            nn.ReLU(),
            nn.Linear(64, 128),
            nn.ReLU(),
            nn.Linear(128, feat_dim)
        )
        
        # アテンション機構
        self.mesh_bone_attention = nn.MultiheadAttention(
            embed_dim=feat_dim,
            num_heads=num_heads,
            dropout=dropout,
            batch_first=True
        )
        
        # スキンウェイト予測ヘッド
        self.skin_predictor = nn.Sequential(
            nn.Linear(feat_dim, feat_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(feat_dim // 2, max_bones),
            nn.Softmax(dim=-1)
        )
        
        # レイヤー正規化
        self.mesh_norm = nn.LayerNorm(feat_dim)
        self.bone_norm = nn.LayerNorm(feat_dim)
        
    def forward(self, 
                vertices: torch.Tensor,  # (N, 3)
                normals: torch.Tensor,   # (N, 3)
                joints: torch.Tensor,    # (J, 3)
                num_bones: int) -> torch.Tensor:
        """
        スキニングウェイト予測
        
        Args:
            vertices: 頂点座標
            normals: 頂点法線
            joints: ボーン座標
            num_bones: 実際のボーン数
            
        Returns:
            skin_weights: スキニングウェイト (N, num_bones)
        """
        device = vertices.device
        N = vertices.shape[0]
        
        # メッシュ特徴抽出
        mesh_input = torch.cat([vertices, normals], dim=-1)  # (N, 6)
        mesh_features = self.mesh_encoder(
            coords=vertices,
            features=normals
        )['features']  # (N, feat_dim)
        
        mesh_features = self.mesh_norm(mesh_features)
        
        # ボーン特徴抽出
        bone_features = self.bone_encoder(joints[:num_bones])  # (num_bones, feat_dim)
        bone_features = self.bone_norm(bone_features)
        
        # メッシュ-ボーンアテンション
        # mesh_features: (N, feat_dim) -> (N, 1, feat_dim)
        # bone_features: (num_bones, feat_dim) -> (1, num_bones, feat_dim)
        mesh_query = mesh_features.unsqueeze(1)  # (N, 1, feat_dim)
        bone_key_value = bone_features.unsqueeze(0).expand(N, -1, -1)  # (N, num_bones, feat_dim)
        
        # アテンション計算
        attended_features, attention_weights = self.mesh_bone_attention(
            query=mesh_query,
            key=bone_key_value,
            value=bone_key_value
        )  # attended_features: (N, 1, feat_dim)
        
        attended_features = attended_features.squeeze(1)  # (N, feat_dim)
        
        # スキンウェイト予測
        skin_weights_full = self.skin_predictor(attended_features)  # (N, max_bones)
        
        # 実際のボーン数に切り詰め
        skin_weights = skin_weights_full[:, :num_bones]  # (N, num_bones)
        
        # 正規化
        skin_weights = skin_weights / (skin_weights.sum(dim=-1, keepdim=True) + 1e-8)
        
        return skin_weights


class CPUSkinningSystem:
    """
    CPU環境でのスキニングシステム統合クラス
    """
    
    def __init__(self, model_name: str, work_dir: str):
        self.model_name = model_name
        self.work_dir = work_dir
        self.device = torch.device("cpu")
        
        # モデル初期化
        self.predictor = CPUSkinningPredictor(
            feat_dim=256,
            num_heads=8,
            max_bones=256
        ).to(self.device)
        
        self.predictor.eval()
        
        # ロギング
        self.logger = logging.getLogger(__name__)
        
    def predict_skin_weights(self, 
                           mesh_data: Dict[str, np.ndarray],
                           skeleton_data: Dict[str, np.ndarray]) -> SkinningResult:
        """
        スキニングウェイト予測（メイン処理）
        
        Args:
            mesh_data: メッシュデータ（vertices, faces, normals等）
            skeleton_data: スケルトンデータ（joints, parents等）
            
        Returns:
            SkinningResult: 予測結果
        """
        try:
            self.logger.info("🔄 CPU環境スキニングウェイト予測開始")
            
            # データの準備
            vertices = torch.from_numpy(mesh_data['vertices']).float().to(self.device)
            normals = self._compute_normals(vertices, mesh_data['faces']) if 'normals' not in mesh_data else torch.from_numpy(mesh_data['normals']).float().to(self.device)
            
            # スケルトンデータの処理
            joints = torch.from_numpy(skeleton_data['joints']).float().to(self.device)
            num_bones = len(joints)
            
            self.logger.info(f"📊 頂点数: {len(vertices)}, ボーン数: {num_bones}")
            
            # 推論実行
            with torch.no_grad():
                skin_weights = self.predictor(
                    vertices=vertices,
                    normals=normals,
                    joints=joints,
                    num_bones=num_bones
                )
            
            # CPU側に移動
            skin_weights_np = skin_weights.cpu().numpy()
            
            # 頂点グループの生成
            vertex_groups = self._create_vertex_groups(
                skin_weights_np, 
                skeleton_data.get('bone_names', [f"Bone_{i:02d}" for i in range(num_bones)])
            )
            
            # 処理情報
            processing_info = {
                'method': 'cpu_fallback',
                'num_vertices': len(vertices),
                'num_bones': num_bones,
                'device': str(self.device),
                'model_type': self.predictor.mesh_encoder.get_encoder_info()['type']
            }
            
            result = SkinningResult(
                skin_weights=skin_weights_np,
                vertex_groups=vertex_groups,
                processing_info=processing_info
            )
            
            self.logger.info("✅ CPU環境スキニングウェイト予測完了")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ スキニング予測エラー: {e}")
            raise
            
    def _compute_normals(self, vertices: torch.Tensor, faces: np.ndarray) -> torch.Tensor:
        """頂点法線の計算"""
        faces_tensor = torch.from_numpy(faces).long().to(vertices.device)
        
        # 面法線の計算
        v0 = vertices[faces_tensor[:, 0]]
        v1 = vertices[faces_tensor[:, 1]]
        v2 = vertices[faces_tensor[:, 2]]
        
        face_normals = torch.cross(v1 - v0, v2 - v0, dim=1)
        face_normals = F.normalize(face_normals, dim=1)
        
        # 頂点法線の初期化
        vertex_normals = torch.zeros_like(vertices)
        
        # 面法線を頂点に累積
        for i in range(3):
            vertex_normals.index_add_(0, faces_tensor[:, i], face_normals)
            
        # 正規化
        vertex_normals = F.normalize(vertex_normals, dim=1)
        
        return vertex_normals
        
    def _create_vertex_groups(self, skin_weights: np.ndarray, bone_names: List[str]) -> Dict[str, Any]:
        """頂点グループの作成"""
        vertex_groups = {}
        
        for bone_idx, bone_name in enumerate(bone_names):
            weights = skin_weights[:, bone_idx]
            # 閾値以上のウェイトのみ保持
            significant_weights = weights[weights > 0.01]
            significant_indices = np.where(weights > 0.01)[0]
            
            if len(significant_weights) > 0:
                vertex_groups[bone_name] = {
                    'indices': significant_indices.astype(np.int32),
                    'weights': significant_weights.astype(np.float32)
                }
                
        # voxel_skin形式での保存（UniRig互換）
        vertex_groups['voxel_skin'] = skin_weights.astype(np.float32)
        
        return vertex_groups
        
    def save_skinning_data(self, result: SkinningResult, output_path: str):
        """スキニングデータの保存"""
        np.savez_compressed(output_path,
            skin_weights=result.skin_weights,
            vertex_groups=result.vertex_groups,
            processing_info=result.processing_info
        )
        self.logger.info(f"💾 スキニングデータ保存: {output_path}")


def create_cpu_skinning_fallback(model_name: str, work_dir: str) -> CPUSkinningSystem:
    """
    CPU環境スキニングシステムのファクトリ関数
    """
    return CPUSkinningSystem(model_name, work_dir)


# 距離ベースの簡易スキニングウェイト計算（さらなるフォールバック）
def compute_distance_based_weights(vertices: np.ndarray, 
                                 joints: np.ndarray,
                                 max_influences: int = 4) -> np.ndarray:
    """
    距離ベースの簡易スキニングウェイト計算
    AIモデルが利用できない場合のフォールバック
    """
    num_vertices = len(vertices)
    num_joints = len(joints)
    
    # 各頂点から各ジョイントへの距離を計算
    distances = np.zeros((num_vertices, num_joints))
    
    for i, vertex in enumerate(vertices):
        for j, joint in enumerate(joints):
            distances[i, j] = np.linalg.norm(vertex - joint)
    
    # 距離の逆数をウェイトとして使用
    weights = 1.0 / (distances + 1e-6)  # 0除算回避
    
    # 上位max_influences個のウェイトのみ保持
    for i in range(num_vertices):
        vertex_weights = weights[i]
        top_indices = np.argpartition(vertex_weights, -max_influences)[-max_influences:]
        
        # 上位以外を0に設定
        mask = np.zeros(num_joints, dtype=bool)
        mask[top_indices] = True
        weights[i, ~mask] = 0.0
        
        # 正規化
        weights[i] = weights[i] / (weights[i].sum() + 1e-8)
    
    return weights.astype(np.float32)
