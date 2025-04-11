from collections import defaultdict

import torch.distributed
import lightning as L
import os
import torch
import numpy as np
from torch import Tensor, FloatTensor, LongTensor
from typing import Dict, Union, List
from lightning.pytorch.callbacks import BasePredictionWriter

from numpy import ndarray
from scipy.sparse import csr_matrix
from scipy.spatial import cKDTree

from ..data.order import OrderConfig, get_order
from ..data.raw_data import RawSkin, RawData
from ..data.exporter import Exporter
from ..model.spec import ModelSpec

class SkinSystem(L.LightningModule):
    
    def __init__(
        self,
        steps_per_epoch: int,
        model: ModelSpec,
        output_path: Union[str, None]=None,
        record_res: Union[bool]=False,
        val_interval: Union[int, None]=None,
        val_start_from: Union[int, None]=None,
    ):
        super().__init__()
        self.save_hyperparameters(ignore="model")
        self.steps_per_epoch    = steps_per_epoch
        self.model              = model
        self.output_path        = output_path
        self.record_res         = record_res
        self.val_interval       = val_interval
        self.val_start_from     = val_start_from
        
        if self.record_res:
            assert self.output_path is not None, "record_res is True, but output_path in skin is None"
    
    def predict_step(self, batch, batch_idx, dataloader_idx=None):
        res = self.model.predict_step(batch)
        
        if isinstance(res, list):
            return {
                'skin_pred': res,
            }
        elif isinstance(res, dict):
            assert 'skin_pred' in res, f"expect key 'skin_pred' in prediction from {self.model.__class__}, found: {res.keys()}"
            return res
        else:
            assert 0, f"expect type of prediction from {self.model.__class__} to be a list or dict, found: {type(res)}"

class SkinWriter(BasePredictionWriter):
    def __init__(
        self,
        output_dir: Union[str, None],
        save_name: str,
        order_config: Union[OrderConfig, None]=None,
        **kwargs
    ):
        super().__init__('batch')
        self.output_dir         = output_dir
        self.npz_dir            = kwargs.get('npz_dir', None)
        self.user_mode          = kwargs.get('user_mode', False)
        self.output_name        = kwargs.get('output_name', None) # for a single name
        self.save_name          = save_name
        self.add_num            = kwargs.get('add_num', False)
        self.export_npz         = kwargs.get('export_npz', True)
        self.export_fbx         = kwargs.get('export_fbx', False)
        if order_config is not None:
            self.order = get_order(config=order_config)
        else:
            self.order = None
        
        self._epoch = 0

    def write_on_batch_end(self, trainer, pl_module: SkinSystem, prediction: List[Dict], batch_indices, batch, batch_idx, dataloader_idx):
        assert 'path' in batch
        paths: List[str] = batch['path']
        data_names: List[str] = batch['data_name']
        joints: FloatTensor = batch['joints']
        num_bones: LongTensor = batch['num_bones']
        num_faces: LongTensor = batch['num_faces']
        num_points: LongTensor = batch['num_points']
        tails: FloatTensor = batch['tails']
        parents_list: LongTensor = batch['parents'] # -1 represents root
        vertices: FloatTensor = batch['origin_vertices']
        sampled_vertices: FloatTensor = batch['vertices']
        faces: LongTensor = batch['origin_faces']
        
        joints = joints.detach().cpu().numpy()
        tails = tails.detach().cpu().numpy()
        parents_list = parents_list.detach().cpu().numpy()
        num_bones = num_bones.detach().cpu().numpy()
        num_faces = num_faces.detach().cpu().numpy()
        vertices = vertices.detach().cpu().numpy()
        faces = faces.detach().cpu().numpy()

        skin_pred_list: List = prediction['skin_pred']
        ret_sampled_vertices = prediction.get('sampled_vertices', None)
        if ret_sampled_vertices is not None:
            assert isinstance(ret_sampled_vertices, Tensor)
            sampled_vertices = ret_sampled_vertices
        if isinstance(sampled_vertices, Tensor):
            sampled_vertices = sampled_vertices.type(torch.float32).detach().cpu().numpy()
        for (id, skin_pred) in enumerate(skin_pred_list):
            if isinstance(skin_pred, Tensor):
                skin_pred = skin_pred.type(torch.float32).detach().cpu().numpy()
                
            # TODO: add custom post-processing here
            
            # resample
            N = num_points[id]
            J = num_bones[id]
            F = num_faces[id]
            o_vertices = vertices[id, :N]
            skin_resampled = reskin(
                sampled_vertices=sampled_vertices[id],
                vertices=o_vertices,
                faces=faces[id, :F],
                sampled_skin=skin_pred,
                alpha=2.0,
                threshold=0.05
            )
            
            def make_path(save_name: str, suffix: str, trim: bool=False):
                if trim:
                    path = os.path.relpath(paths[id], self.npz_dir)
                else:
                    path = paths[id]

                if self.output_dir is not None:
                    path = os.path.join(self.output_dir, path)
                
                if self.add_num:
                    path = os.path.join(path, f"{save_name}_{self._epoch}.{suffix}")
                else:
                    path = os.path.join(path, f"{save_name}.{suffix}")
                return path
            
            raw_data = RawSkin(skin=skin_pred, vertices=sampled_vertices[id], joints=joints[id, :J])
            if self.export_npz is not None:
                raw_data.save(path=make_path(self.export_npz, 'npz'))
            if self.export_fbx is not None:
                try:
                    exporter = Exporter()
                    _parents = parents_list[id]
                    parents = []
                    for i in range(J):
                        if _parents[i] == -1:
                            parents.append(None)
                        else:
                            parents.append(_parents[i])
                    names = RawData.load(path=os.path.join(paths[id], data_names[id])).names
                    if names is None:
                        names = [f"bone_{i}" for i in range(J)]
                    if self.user_mode:
                        if self.output_name is not None:
                            path = self.output_name
                        else:
                            path = make_path(self.save_name, 'fbx', trim=True)
                    else:
                        path = make_path(self.export_fbx, 'fbx')
                    exporter._export_fbx(
                        path=path,
                        vertices=o_vertices,
                        joints=joints[id, :J],
                        skin=skin_resampled,
                        parents=parents,
                        names=names,
                        faces=faces[id, :F],
                        group_per_vertex=4,
                        tails=tails[id, :J],
                        use_extrude_bone=False,
                        use_connect_unique_child=False,
                        # do_not_normalize=True,
                    )
                except Exception as e:
                    print(str(e))
    
    def write_on_epoch_end(self, trainer, pl_module, predictions, batch_indices):
        self._epoch += 1

def reskin(
    sampled_vertices: ndarray,
    vertices: ndarray,
    faces: ndarray,
    sampled_skin: ndarray,
    **kwargs,
) -> ndarray:
    nearest_samples = kwargs.get('nearest_samples', 5)
    iter_steps = kwargs.get('iter_steps', 2)
    link_same = kwargs.get('link_same', True)
    threshold = kwargs.get('threshold', 0.01)
    alpha = kwargs.get('alpha', 2)
    
    N = vertices.shape[0]
    tree = cKDTree(sampled_vertices)
    dis, nearest = tree.query(vertices, k=nearest_samples, p=2)
    # weighted sum
    weights = np.exp(-alpha * dis)  # (N, nearest_samples)
    weight_sum = weights.sum(axis=1, keepdims=True)
    sampled_skin_nearest = sampled_skin[nearest]
    skin = (sampled_skin_nearest * weights[..., np.newaxis]).sum(axis=1) / weight_sum
    
    edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]], axis=0)

    # link gaps between parts
    source_indices = None
    if link_same:
        # Create sparse adjacency matrix
        row = np.concatenate([edges[:, 0], edges[:, 1]])
        col = np.concatenate([edges[:, 1], edges[:, 0]])
        data = np.zeros_like(row, dtype=bool)
        mask = csr_matrix((data, (row, col)), shape=(N, N))
        mask[faces[:, 0], faces[:, 1]] ^= True
        mask[faces[:, 1], faces[:, 0]] ^= True
        mask[faces[:, 1], faces[:, 2]] ^= True
        mask[faces[:, 2], faces[:, 1]] ^= True
        mask[faces[:, 2], faces[:, 0]] ^= True
        mask[faces[:, 0], faces[:, 2]] ^= True
        mask_on_boundry = mask.sum(axis=1) > 0
        
        # Get vertices with edges (boundary vertices)
        mask_boundry_vertices = np.where(mask_on_boundry)[0]
        m = len(mask_boundry_vertices)
        
        if m > 0:
            # Map between full vertex indices and masked subset
            map_back = mask_boundry_vertices
            map_to = np.zeros(N, dtype=int)
            map_to[mask_boundry_vertices] = np.arange(m)
            
            # Calculate distances only for masked vertices
            masked_vertices = vertices[mask_boundry_vertices]
            tree_edge = cKDTree(masked_vertices)
            
            # Find nearest neighbors
            dis, nearest = tree_edge.query(masked_vertices, k=1, p=2)
            source_indices = np.arange(m)
            target_indices = nearest
            
            source_indices = ((masked_vertices[source_indices] - masked_vertices[target_indices])**2).sum(axis=1) < 1e-10
            new_edges = np.stack([map_back[source_indices], map_back[target_indices[source_indices]]], axis=1)
            edges = np.concatenate([edges, new_edges], axis=0)

    edges = np.concatenate([edges, edges[:, [1, 0]]], axis=0) # (2*F*3, 2)

    # diffusion in neighbours
    for _ in range(iter_steps):
        neighbor_skin = np.zeros_like(skin)  # (N, J)
        neighbor_co = np.zeros((N, 1), dtype=np.float32)

        dis = np.sqrt(((vertices[edges[:, 1]] - vertices[edges[:, 0]])**2).sum(axis=1, keepdims=True))
        co = np.exp(-dis * alpha)

        neighbor_skin[edges[:, 1]] += skin[edges[:, 0]] * co
        neighbor_co[edges[:, 1]] += co

        skin = (skin + neighbor_skin) / (1. + neighbor_co)
    if link_same and source_indices is not None:
        # guarantee continuity at the boundry
        g = (skin[mask_boundry_vertices][source_indices] + skin[mask_boundry_vertices][target_indices]) / 2
        skin[mask_boundry_vertices] = g
    
    skin = skin / skin.sum(axis=-1, keepdims=True)
    # avoid 0-skin
    mask = (skin>=threshold).any(axis=-1, keepdims=True)
    skin[(skin<threshold)&mask] = 0.
    skin = skin / skin.sum(axis=-1, keepdims=True)
    
    return skin