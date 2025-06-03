# dynamic_skeleton_generator.py
# UniRigベースの動的スケルトン生成システム
# UniRig (https://github.com/VAST-AI-Research/UniRig) に基づく実装

import numpy as np
from typing import Dict, List, Tuple, Union, Optional
from collections import defaultdict
import trimesh
import logging

class DynamicSkeletonGenerator:
    """
    UniRigのmake_skeleton()ロジックを参考にした動的ボーン生成システム
    メッシュ形状を解析して適応的なスケルトン構造を生成
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def analyze_mesh_for_skeleton_prediction(self, vertices: np.ndarray, faces: np.ndarray) -> Dict:
        """
        メッシュを解析してスケルトン生成のためのメタデータを抽出
        
        Args:
            vertices: (N, 3) メッシュの頂点座標
            faces: (F, 3) メッシュの面インデックス
        
        Returns:
            dict: スケルトン生成に必要なメタデータ
        """
        try:
            # メッシュの基本情報
            mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
            bounds = mesh.bounds
            center = mesh.centroid
            extents = mesh.extents
            
            # メッシュの主軸方向を計算
            principal_axes = self._compute_principal_axes(vertices)
            
            # 形状の特徴を分析
            shape_analysis = self._analyze_mesh_shape(mesh, vertices, faces)
            
            return {
                'bounds': bounds,
                'center': center,
                'extents': extents,
                'principal_axes': principal_axes,
                'shape_analysis': shape_analysis,
                'mesh': mesh
            }
        except Exception as e:
            self.logger.error(f"メッシュ解析エラー: {e}")
            return {}
    
    def _compute_principal_axes(self, vertices: np.ndarray) -> np.ndarray:
        """主軸方向を計算（PCA）"""
        centered_vertices = vertices - np.mean(vertices, axis=0)
        cov_matrix = np.cov(centered_vertices.T)
        eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)
        
        # 固有値の大きい順にソート
        sorted_indices = np.argsort(eigenvalues)[::-1]
        return eigenvectors[:, sorted_indices]
    
    def _analyze_mesh_shape(self, mesh: trimesh.Trimesh, vertices: np.ndarray, faces: np.ndarray) -> Dict:
        """メッシュ形状の特徴を分析"""
        analysis = {}
        
        # 基本的な形状特徴
        analysis['is_watertight'] = mesh.is_watertight
        analysis['volume'] = mesh.volume if mesh.is_watertight else 0
        analysis['surface_area'] = mesh.area
        
        # アスペクト比（縦横比）
        extents = mesh.extents
        analysis['aspect_ratios'] = {
            'xy': extents[0] / max(extents[1], 1e-6),
            'xz': extents[0] / max(extents[2], 1e-6), 
            'yz': extents[1] / max(extents[2], 1e-6)
        }
        
        # 形状タイプの推定
        analysis['estimated_type'] = self._estimate_creature_type(extents, analysis['aspect_ratios'])
        
        # 潜在的なジョイント領域の検出
        joint_regions = self._detect_potential_joint_regions(vertices, faces)
        analysis['joint_regions'] = joint_regions
        
        return analysis
    
    def _estimate_creature_type(self, extents: np.ndarray, aspect_ratios: Dict) -> str:
        """メッシュの形状から生物タイプを推定 - 修正版（鳥類認識改善）"""
        height = extents[2]  # Z軸を高さと仮定
        width = max(extents[0], extents[1])
        
        # より詳細な鳥類検出ロジック
        # 鳥の特徴: 横長だが幅がかなり大きい（翼のため）
        if aspect_ratios['xy'] > 4.0 and aspect_ratios['yz'] < 1.0:
            # 横幅が非常に大きく、高さが低い = 鳥類（翼を広げた状態）
            return 'bird'
        elif aspect_ratios['yz'] > 2.0:  # 縦長
            if width > height * 0.8:
                return 'bird'  # 幅もある縦長 = 鳥類
            else:
                return 'humanoid'  # 純粋に縦長 = ヒューマノイド
        elif aspect_ratios['yz'] < 0.5 and aspect_ratios['xy'] < 3.0:  # 横長だが極端に幅広くない
            return 'quadruped'  # 四足動物
        elif max(aspect_ratios['xy'], aspect_ratios['xz']) > 3.0:  # 極端に幅広い
            return 'multi_limbed'  # 多足動物（蜘蛛、タコなど）
        else:
            return 'generic'  # 汎用的な形状
    
    def _detect_potential_joint_regions(self, vertices: np.ndarray, faces: np.ndarray) -> List[Dict]:
        """
        メッシュから潜在的なジョイント位置を検出
        狭窄部（くびれ）や形状の変化点を検出
        """
        joint_regions = []
        
        try:
            # 簡易的な狭窄部検出
            # Z軸方向にスライスして断面積の変化を調べる
            z_min, z_max = vertices[:, 2].min(), vertices[:, 2].max()
            z_slices = np.linspace(z_min, z_max, 20)
            
            cross_section_areas = []
            for z in z_slices:
                # Z=z近傍の頂点を抽出
                mask = np.abs(vertices[:, 2] - z) < (z_max - z_min) / 40
                if np.sum(mask) > 3:
                    slice_vertices = vertices[mask]
                    # 断面の凸包面積を計算
                    try:
                        from scipy.spatial import ConvexHull
                        hull = ConvexHull(slice_vertices[:, :2])  # XY平面での凸包
                        area = hull.volume  # 2Dでは面積
                    except:
                        area = 0
                else:
                    area = 0
                cross_section_areas.append(area)
            
            # 面積の急激な変化点を検出
            areas = np.array(cross_section_areas)
            if len(areas) > 3:
                area_changes = np.abs(np.diff(areas))
                threshold = np.mean(area_changes) + 2 * np.std(area_changes)
                
                for i, change in enumerate(area_changes):
                    if change > threshold and i > 0 and i < len(z_slices) - 2:
                        joint_regions.append({
                            'position': [0, 0, z_slices[i]],
                            'strength': change / np.max(area_changes),
                            'type': 'constriction'
                        })
            
        except Exception as e:
            self.logger.warning(f"ジョイント検出エラー: {e}")
        
        return joint_regions
    
    def generate_adaptive_skeleton(self, 
                                 vertices: np.ndarray, 
                                 faces: np.ndarray,
                                 target_bone_count: Optional[int] = None) -> Dict:
        """
        メッシュ解析に基づいて適応的なスケルトン構造を生成
        
        Args:
            vertices: メッシュの頂点座標
            faces: メッシュの面インデックス
            target_bone_count: 目標ボーン数（Noneの場合は自動決定）
        
        Returns:
            dict: 生成されたスケルトンデータ
        """
        # メッシュ解析
        mesh_analysis = self.analyze_mesh_for_skeleton_prediction(vertices, faces)
        if not mesh_analysis:
            return self._generate_fallback_skeleton()
        
        # 生物タイプに基づくスケルトンテンプレート
        creature_type = mesh_analysis['shape_analysis']['estimated_type']
        skeleton_template = self._get_skeleton_template(creature_type)
        
        # ジョイント位置の予測
        predicted_joints = self._predict_joint_positions(mesh_analysis, skeleton_template)
        
        # UniRigスタイルの親子関係構築
        bones, tails, parents, names = self._build_skeleton_hierarchy(
            predicted_joints, 
            skeleton_template
        )
        
        return {
            'joints': predicted_joints,
            'bones': bones,
            'tails': tails,
            'parents': parents,
            'names': names,
            'creature_type': creature_type,
            'bone_count': len(names),
            'mesh_analysis': mesh_analysis
        }
    
    def _get_skeleton_template(self, creature_type: str) -> Dict:
        """生物タイプに応じたスケルトンテンプレートを取得 - 拡張版"""
        templates = {
            'humanoid': {
                'base_bones': ['Root', 'Hips', 'Spine1', 'Spine2', 'Neck', 'Head',
                              'LeftShoulder', 'LeftArm', 'LeftForeArm', 'LeftHand',
                              'RightShoulder', 'RightArm', 'RightForeArm', 'RightHand',
                              'LeftUpLeg', 'LeftLeg', 'LeftFoot',
                              'RightUpLeg', 'RightLeg', 'RightFoot'],
                'symmetry': True,
                'main_axis': 'vertical'
            },
            'quadruped': {
                'base_bones': ['Root', 'Spine1', 'Spine2', 'Spine3', 'Neck', 'Head',
                              'FrontLeftShoulder', 'FrontLeftLeg', 'FrontLeftFoot',
                              'FrontRightShoulder', 'FrontRightLeg', 'FrontRightFoot',
                              'BackLeftHip', 'BackLeftLeg', 'BackLeftFoot',
                              'BackRightHip', 'BackRightLeg', 'BackRightFoot',
                              'Tail1', 'Tail2', 'Tail3'],
                'symmetry': True,
                'main_axis': 'horizontal'
            },
            'bird': {
                'base_bones': [
                    # 体幹部の詳細構造
                    'Root', 'Hips', 'Spine1', 'Spine2', 'Spine3', 'Spine4', 'Neck1', 'Neck2', 'Head', 'Beak',
                    
                    # 左翼の詳細構造
                    'LeftWingShoulder', 'LeftWingArm', 'LeftWingElbow', 'LeftWingForeArm', 
                    'LeftWingWrist', 'LeftWingHand', 'LeftWingFinger1', 'LeftWingFinger2', 'LeftWingFinger3',
                    'LeftWingFeather1', 'LeftWingFeather2', 'LeftWingFeather3', 'LeftWingFeather4', 'LeftWingFeather5',
                    'LeftWingTip1', 'LeftWingTip2', 'LeftWingTip3',
                    
                    # 右翼の詳細構造
                    'RightWingShoulder', 'RightWingArm', 'RightWingElbow', 'RightWingForeArm',
                    'RightWingWrist', 'RightWingHand', 'RightWingFinger1', 'RightWingFinger2', 'RightWingFinger3',
                    'RightWingFeather1', 'RightWingFeather2', 'RightWingFeather3', 'RightWingFeather4', 'RightWingFeather5',
                    'RightWingTip1', 'RightWingTip2', 'RightWingTip3',
                    
                    # 脚部の詳細構造
                    'LeftLegUpper', 'LeftLegLower', 'LeftFoot', 'LeftToe1', 'LeftToe2', 'LeftToe3', 'LeftToe4', 'LeftClaw1',
                    'RightLegUpper', 'RightLegLower', 'RightFoot', 'RightToe1', 'RightToe2', 'RightToe3', 'RightToe4', 'RightClaw1',
                    
                    # 尻尾の詳細構造
                    'Tail1', 'Tail2', 'Tail3', 'Tail4', 'Tail5'
                ],
                'symmetry': True,
                'main_axis': 'vertical'
            },
            'multi_limbed': {
                'base_bones': ['Root', 'Abdomen', 'Thorax', 'Head',
                              'Leg1_Upper', 'Leg1_Lower', 'Leg1_Foot',
                              'Leg2_Upper', 'Leg2_Lower', 'Leg2_Foot',
                              'Leg3_Upper', 'Leg3_Lower', 'Leg3_Foot',
                              'Leg4_Upper', 'Leg4_Lower', 'Leg4_Foot',
                              'Leg5_Upper', 'Leg5_Lower', 'Leg5_Foot',
                              'Leg6_Upper', 'Leg6_Lower', 'Leg6_Foot',
                              'Leg7_Upper', 'Leg7_Lower', 'Leg7_Foot',
                              'Leg8_Upper', 'Leg8_Lower', 'Leg8_Foot'],
                'symmetry': True,
                'main_axis': 'horizontal'
            },
            'generic': {
                'base_bones': ['Root', 'Body1', 'Body2', 'Body3', 'Head',
                              'Limb1_Upper', 'Limb1_Lower', 'Limb1_End',
                              'Limb2_Upper', 'Limb2_Lower', 'Limb2_End',
                              'Limb3_Upper', 'Limb3_Lower', 'Limb3_End',
                              'Limb4_Upper', 'Limb4_Lower', 'Limb4_End'],
                'symmetry': False,
                'main_axis': 'vertical'
            }
        }
        
        return templates.get(creature_type, templates['generic'])
    
    def _predict_joint_positions(self, mesh_analysis: Dict, skeleton_template: Dict) -> np.ndarray:
        """メッシュ解析結果とテンプレートに基づいてジョイント位置を予測"""
        bounds = mesh_analysis['bounds']
        center = mesh_analysis['center']
        extents = mesh_analysis['extents']
        
        base_bones = skeleton_template['base_bones']
        joint_count = len(base_bones)
        
        # 基本的なジョイント配置を生成
        joints = np.zeros((joint_count, 3))
        
        if skeleton_template['main_axis'] == 'vertical':
            # 縦方向メインの配置（ヒューマノイド、鳥）
            joints = self._generate_vertical_skeleton(bounds, center, extents, base_bones)
        elif skeleton_template['main_axis'] == 'horizontal':
            # 横方向メインの配置（四足動物、多足動物）
            joints = self._generate_horizontal_skeleton(bounds, center, extents, base_bones)
        else:
            # 汎用配置
            joints = self._generate_generic_skeleton(bounds, center, extents, base_bones)
        
        return joints
    
    def _generate_vertical_skeleton(self, bounds: np.ndarray, center: np.ndarray, 
                                  extents: np.ndarray, bone_names: List[str]) -> np.ndarray:
        """縦方向メインのスケルトン生成"""
        joint_count = len(bone_names)
        joints = np.zeros((joint_count, 3))
        
        # 基本的な縦方向の配置
        z_min, z_max = bounds[0, 2], bounds[1, 2]
        height = z_max - z_min
        
        for i, bone_name in enumerate(bone_names):
            if 'Root' in bone_name or 'Hips' in bone_name:
                joints[i] = [center[0], center[1], z_min + height * 0.6]
            elif 'Head' in bone_name:
                joints[i] = [center[0], center[1], z_max - height * 0.1]
            elif 'Beak' in bone_name:
                joints[i] = [center[0], center[1] + extents[1] * 0.2, z_max - height * 0.05]
            elif 'Neck' in bone_name:
                neck_num = 1
                if '2' in bone_name:
                    neck_num = 2
                joints[i] = [center[0], center[1], z_max - height * (0.15 + neck_num * 0.05)]
            elif 'Spine' in bone_name:
                spine_num = 1
                if '2' in bone_name:
                    spine_num = 2
                elif '3' in bone_name:
                    spine_num = 3
                elif '4' in bone_name:
                    spine_num = 4
                joints[i] = [center[0], center[1], z_min + height * (0.6 + spine_num * 0.08)]
            elif 'Left' in bone_name:
                joints[i] = self._position_limb_joint(bone_name, center, extents, bounds, 'left')
            elif 'Right' in bone_name:
                joints[i] = self._position_limb_joint(bone_name, center, extents, bounds, 'right')
            elif 'Tail' in bone_name:
                tail_num = 1
                if '2' in bone_name:
                    tail_num = 2
                elif '3' in bone_name:
                    tail_num = 3
                elif '4' in bone_name:
                    tail_num = 4
                elif '5' in bone_name:
                    tail_num = 5
                joints[i] = [center[0] - extents[0] * 0.1 * tail_num, center[1], z_min + height * 0.5]
            else:
                # その他のボーンは中央付近に配置
                joints[i] = center + np.random.normal(0, extents.max() * 0.05, 3)
        
        return joints
    
    def _generate_horizontal_skeleton(self, bounds: np.ndarray, center: np.ndarray,
                                    extents: np.ndarray, bone_names: List[str]) -> np.ndarray:
        """横方向メインのスケルトン生成（四足動物など）"""
        joint_count = len(bone_names)
        joints = np.zeros((joint_count, 3))
        
        # 横方向の配置
        x_min, x_max = bounds[0, 0], bounds[1, 0]
        length = x_max - x_min
        
        for i, bone_name in enumerate(bone_names):
            if 'Root' in bone_name:
                joints[i] = center
            elif 'Head' in bone_name:
                joints[i] = [x_max - length * 0.1, center[1], center[2]]
            elif 'Tail' in bone_name:
                tail_num = 1
                if '2' in bone_name:
                    tail_num = 2
                elif '3' in bone_name:
                    tail_num = 3
                joints[i] = [x_min + length * 0.1 * tail_num, center[1], center[2]]
            elif 'Spine' in bone_name:
                spine_num = 1
                if '2' in bone_name:
                    spine_num = 2
                elif '3' in bone_name:
                    spine_num = 3
                joints[i] = [center[0] + length * (0.2 - spine_num * 0.1), center[1], center[2]]
            elif 'Front' in bone_name or 'Back' in bone_name:
                joints[i] = self._position_limb_joint(bone_name, center, extents, bounds, 'quadruped')
            elif 'Leg' in bone_name and any(c.isdigit() for c in bone_name):
                # 多足動物の脚
                joints[i] = self._position_multi_limb_joint(bone_name, center, extents, bounds)
            else:
                joints[i] = center + np.random.normal(0, extents.max() * 0.1, 3)
        
        return joints
    
    def _generate_generic_skeleton(self, bounds: np.ndarray, center: np.ndarray,
                                 extents: np.ndarray, bone_names: List[str]) -> np.ndarray:
        """汎用スケルトン生成"""
        joint_count = len(bone_names)
        joints = np.zeros((joint_count, 3))
        
        for i, bone_name in enumerate(bone_names):
            if 'Root' in bone_name:
                joints[i] = center
            else:
                # メッシュの境界内にランダム配置（但し中央寄り）
                scale = 0.8  # 境界から少し内側
                offset = (bounds[1] - bounds[0]) * scale * (np.random.rand(3) - 0.5)
                joints[i] = center + offset
        
        return joints
    
    def _position_limb_joint(self, bone_name: str, center: np.ndarray, 
                           extents: np.ndarray, bounds: np.ndarray, side: str) -> np.ndarray:
        """四肢ジョイントの位置決定（拡張版）"""
        if side == 'left':
            x_offset = -extents[0] * 0.4  # 翼のために幅を拡大
        elif side == 'right':
            x_offset = extents[0] * 0.4
        elif side == 'quadruped':
            if 'Front' in bone_name:
                x_offset = extents[0] * 0.2
            else:  # Back
                x_offset = -extents[0] * 0.2
            
            if 'Left' in bone_name:
                y_offset = -extents[1] * 0.3
            else:  # Right
                y_offset = extents[1] * 0.3
        else:
            x_offset = 0
            y_offset = 0
        
        # 高さの調整（鳥類の詳細構造に対応）
        if 'Shoulder' in bone_name or 'Wing' in bone_name:
            if 'Feather' in bone_name:
                z_offset = extents[2] * 0.05  # 羽根は翼より少し下
            elif 'Tip' in bone_name:
                z_offset = extents[2] * 0.02  # 翼端は最も下
            else:
                z_offset = extents[2] * 0.1
        elif 'Arm' in bone_name or 'ForeArm' in bone_name:
            z_offset = 0
        elif 'Hand' in bone_name or 'Wrist' in bone_name:
            z_offset = -extents[2] * 0.1
        elif 'Finger' in bone_name:
            z_offset = -extents[2] * 0.15
        elif 'Foot' in bone_name:
            z_offset = -extents[2] * 0.4
        elif 'Toe' in bone_name:
            z_offset = -extents[2] * 0.45
        elif 'Claw' in bone_name:
            z_offset = -extents[2] * 0.5
        elif 'Leg' in bone_name or 'UpLeg' in bone_name:
            z_offset = -extents[2] * 0.2
        else:
            z_offset = 0
        
        if side == 'quadruped':
            return np.array([center[0] + x_offset, center[1] + y_offset, center[2] + z_offset])
        else:
            return np.array([center[0] + x_offset, center[1], center[2] + z_offset])
    
    def _position_multi_limb_joint(self, bone_name: str, center: np.ndarray,
                                 extents: np.ndarray, bounds: np.ndarray) -> np.ndarray:
        """多足動物の脚位置決定"""
        # 脚番号を抽出
        leg_num = int([c for c in bone_name if c.isdigit()][0])
        
        # 円形配置
        angle = (leg_num - 1) * (2 * np.pi / 8)  # 8本脚想定
        radius = max(extents[0], extents[1]) * 0.4
        
        x_offset = radius * np.cos(angle)
        y_offset = radius * np.sin(angle)
        
        if 'Upper' in bone_name:
            z_offset = 0
        elif 'Lower' in bone_name:
            z_offset = -extents[2] * 0.2
        elif 'Foot' in bone_name:
            z_offset = -extents[2] * 0.4
        else:
            z_offset = 0
        
        return np.array([center[0] + x_offset, center[1] + y_offset, center[2] + z_offset])
    
    def _build_skeleton_hierarchy(self, joints: np.ndarray, skeleton_template: Dict) -> Tuple:
        """
        UniRigのmake_skeleton()ロジックに基づいて骨格階層を構築
        """
        bone_names = skeleton_template['base_bones']
        joint_count = len(joints)
        
        # 親子関係を構築（UniRigスタイル）
        parents = []
        bones = []
        
        for i, name in enumerate(bone_names):
            if i == 0:  # Root bone
                parents.append(None)
                bones.append(np.concatenate([joints[i], joints[i]]))  # UniRigスタイル
            else:
                # 最も近い前のジョイントを親とする（UniRigのロジック）
                parent_id = self._find_best_parent(i, joints, bone_names)
                parents.append(parent_id)
                
                if parent_id is not None:
                    parent_pos = joints[parent_id]
                    current_pos = joints[i]
                    bones.append(np.concatenate([parent_pos, current_pos]))
                else:
                    bones.append(np.concatenate([joints[i], joints[i]]))
        
        bones = np.stack(bones)
        
        # Tailsの生成（UniRigのmake_skeleton()ロジック）
        tails_dict = {}
        children = defaultdict(list)
        
        for i, pid in enumerate(parents):
            if pid is not None:
                children[pid].append(i)
        
        # UniRigのtail生成ロジックを適用
        tails = self._generate_tails_unirig_style(
            bones, parents, children, 
            convert_leaf_bones_to_tails=False,
            extrude_tail_for_leaf=True,
            extrude_tail_for_branch=True,
            extrude_scale=0.1
        )
        
        return bones, tails, parents, bone_names
    
    def _find_best_parent(self, current_idx: int, joints: np.ndarray, bone_names: List[str]) -> Optional[int]:
        """最適な親ボーンを見つける（拡張版階層ルール）"""
        current_name = bone_names[current_idx]
        current_pos = joints[current_idx]
        
        # 階層的な関係性を考慮（鳥類対応拡張）
        hierarchy_rules = {
            'Head': ['Neck2', 'Neck1', 'Neck'],
            'Beak': ['Head'],
            'Neck2': ['Neck1'],
            'Neck1': ['Spine4', 'Spine3', 'Spine2'],
            'Spine2': ['Spine1'],
            'Spine3': ['Spine2'],
            'Spine4': ['Spine3'],
            'LeftWingArm': ['LeftWingShoulder'],
            'RightWingArm': ['RightWingShoulder'],
            'LeftWingElbow': ['LeftWingArm'],
            'RightWingElbow': ['RightWingArm'],
            'LeftWingForeArm': ['LeftWingElbow'],
            'RightWingForeArm': ['RightWingElbow'],
            'LeftWingWrist': ['LeftWingForeArm'],
            'RightWingWrist': ['RightWingForeArm'],
            'LeftWingHand': ['LeftWingWrist'],
            'RightWingHand': ['RightWingWrist'],
            'LeftWingFinger1': ['LeftWingHand'],
            'LeftWingFinger2': ['LeftWingHand'],
            'LeftWingFinger3': ['LeftWingHand'],
            'RightWingFinger1': ['RightWingHand'],
            'RightWingFinger2': ['RightWingHand'],
            'RightWingFinger3': ['RightWingHand'],
            'LeftLegLower': ['LeftLegUpper'],
            'RightLegLower': ['RightLegUpper'],
            'LeftFoot': ['LeftLegLower'],
            'RightFoot': ['RightLegLower'],
            'Tail2': ['Tail1'],
            'Tail3': ['Tail2'],
            'Tail4': ['Tail3'],
            'Tail5': ['Tail4']
        }
        
        # 階層ルールに基づく検索
        if current_name in hierarchy_rules:
            for parent_name in hierarchy_rules[current_name]:
                for i, name in enumerate(bone_names[:current_idx]):
                    if parent_name == name:
                        return i
        
        # パターンマッチングによる親子関係の推定
        # 翼のFeatherは対応するWingの子
        if 'Feather' in current_name:
            wing_side = 'Left' if 'Left' in current_name else 'Right'
            for i, name in enumerate(bone_names[:current_idx]):
                if f'{wing_side}Wing' in name and 'Hand' in name:
                    return i
        
        # TipはFeatherの子
        if 'Tip' in current_name:
            wing_side = 'Left' if 'Left' in current_name else 'Right'
            for i, name in enumerate(bone_names[:current_idx]):
                if f'{wing_side}WingFeather' in name:
                    return i
        
        # Toeは対応するFootの子
        if 'Toe' in current_name:
            foot_side = 'Left' if 'Left' in current_name else 'Right'
            for i, name in enumerate(bone_names[:current_idx]):
                if f'{foot_side}Foot' == name:
                    return i
        
        # Clawは対応するToeの子
        if 'Claw' in current_name:
            toe_side = 'Left' if 'Left' in current_name else 'Right'
            for i, name in enumerate(bone_names[:current_idx]):
                if f'{toe_side}Toe' in name:
                    return i
        
        # ルールベースで見つからない場合、距離ベースで決定（UniRigロジック）
        best_parent = None
        min_distance = float('inf')
        
        for i in range(current_idx):
            distance = np.linalg.norm(current_pos - joints[i])
            if distance < min_distance:
                min_distance = distance
                best_parent = i
        
        return best_parent
    
    def _generate_tails_unirig_style(self, bones: np.ndarray, parents: List, children: Dict,
                                   convert_leaf_bones_to_tails: bool = False,
                                   extrude_tail_for_leaf: bool = True,
                                   extrude_tail_for_branch: bool = True,
                                   extrude_scale: float = 0.1) -> np.ndarray:
        """UniRigのmake_skeleton()から移植したtail生成ロジック"""
        tails_dict = {}
        
        # Available bones処理
        available_bones_id = []
        if convert_leaf_bones_to_tails:
            for i, pid in enumerate(parents):
                if len(children[i]) != 0:
                    available_bones_id.append(i)
                    continue
                if pid is not None:
                    tails_dict[pid] = bones[i, 3:]
        else:
            available_bones_id = list(range(bones.shape[0]))
        
        # Tail for leaf
        for i, pid in enumerate(parents):
            if len(children[i]) != 0:
                continue
            if extrude_tail_for_leaf:
                if pid is not None:
                    d = bones[i, 3:] - bones[pid, 3:]
                    length = np.linalg.norm(d)
                    if length <= 1e-9:
                        d = np.array([0., 0., 1.])
                    tails_dict[i] = bones[i, 3:] + d * extrude_scale
                else:
                    tails_dict[i] = bones[i, 3:]
        
        # Tail for branch
        for i, pid in enumerate(parents):
            if len(children[i]) <= 1:
                continue
            if extrude_tail_for_branch:
                if pid is None:  # root
                    av_len = 0
                    for child in children[i]:
                        av_len += np.linalg.norm(bones[i, 3:] - bones[child, 3:])
                    av_len /= len(children[i])
                    tails_dict[i] = bones[i, 3:] + np.array([0., 0., extrude_scale * av_len])
                else:
                    d = bones[i, 3:] - bones[pid, 3:]
                    length = np.linalg.norm(d)
                    if length <= 1e-9:
                        d = np.array([0., 0., 1.])
                    tails_dict[i] = bones[i, 3:] + d * extrude_scale
            else:
                tails_dict[i] = bones[i, 3:]
        
        # Assign new tail (子が1つの場合、子の位置をtailにする)
        for i, pid in enumerate(parents):
            if len(children[i]) != 1:
                continue
            child = children[i][0]
            tails_dict[i] = bones[child, 3:]
        
        # 最終的なtails配列を構築
        tails = []
        for i in range(bones.shape[0]):
            if i in tails_dict:
                tails.append(tails_dict[i])
            else:
                # デフォルトtail位置
                tails.append(bones[i, 3:] + np.array([0., 0., 0.1]))
        
        return np.stack(tails)
    
    def _generate_fallback_skeleton(self) -> Dict:
        """メッシュ解析に失敗した場合のフォールバックスケルトン"""
        # 最小限のスケルトン
        joints = np.array([[0, 0, 0], [0, 0, 1], [0, 0, 2]])
        bones = np.array([
            [[0, 0, 0], [0, 0, 0]],  # Root
            [[0, 0, 0], [0, 0, 1]],  # Body
            [[0, 0, 1], [0, 0, 2]]   # Head
        ])
        tails = np.array([[0, 0, 0.1], [0, 0, 1.1], [0, 0, 2.1]])
        parents = [None, 0, 1]
        names = ['Root', 'Body', 'Head']
        
        return {
            'joints': joints,
            'bones': bones, 
            'tails': tails,
            'parents': parents,
            'names': names,
            'creature_type': 'generic',
            'bone_count': 3,
            'mesh_analysis': {}
        }


# 使用例とテスト用関数
def test_dynamic_skeleton_generator():
    """動的スケルトン生成器のテスト"""
    generator = DynamicSkeletonGenerator()
    
    # テスト用のシンプルなメッシュ（立方体）
    vertices = np.array([
        [-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],  # 底面
        [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]       # 上面
    ])
    
    faces = np.array([
        [0, 1, 2], [0, 2, 3],  # 底面
        [4, 7, 6], [4, 6, 5],  # 上面
        [0, 4, 5], [0, 5, 1],  # 側面
        [2, 6, 7], [2, 7, 3],
        [0, 3, 7], [0, 7, 4],
        [1, 5, 6], [1, 6, 2]
    ])
    
    # スケルトン生成
    result = generator.generate_adaptive_skeleton(vertices, faces)
    
    print("=== 動的スケルトン生成テスト結果 ===")
    print(f"生物タイプ: {result['creature_type']}")
    print(f"ボーン数: {result['bone_count']}")
    print(f"ボーン名: {result['names']}")
    print(f"親子関係: {result['parents']}")
    print(f"ジョイント座標:\n{result['joints']}")
    
    return result

if __name__ == "__main__":
    test_dynamic_skeleton_generator()
