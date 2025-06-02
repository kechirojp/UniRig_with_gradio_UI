from collections import defaultdict
import lightning as L
import os
import torch
import numpy as np
from torch import Tensor
from typing import Dict, Union, List
from lightning.pytorch.callbacks import BasePredictionWriter

from numpy import ndarray

from ..data.raw_data import RawData
from ..data.order import OrderConfig, get_order
from ..model.spec import ModelSpec
from ..tokenizer.spec import DetokenzeOutput

class ARSystem(L.LightningModule):
    
    def __init__(
        self,
        steps_per_epoch: int,
        model: ModelSpec,
        generate_kwargs: Dict={},
        output_path: Union[str, None]=None,
        record_res: Union[bool]=False,
        validate_cast: str='bfloat16',
        val_interval: Union[int, None]=None,
        val_start_from: Union[int, None]=None,
    ):
        super().__init__()
        self.save_hyperparameters(ignore="model")
        self.steps_per_epoch    = steps_per_epoch
        self.model              = model
        self.generate_kwargs    = generate_kwargs
        self.output_path        = output_path
        self.record_res         = record_res
        self.validate_cast      = validate_cast
        self.val_interval       = val_interval
        self.val_start_from     = val_start_from
        
        if self.record_res:
            assert self.output_path is not None, "record_res is True, but output_path in ar is None"
    
    def _predict_step(self, batch, batch_idx, dataloader_idx=None):
        batch['generate_kwargs'] = self.generate_kwargs
        res = self.model.predict_step(batch)
        assert isinstance(res, list), f"expect type of prediction from {self.model.__class__} to be a list, found: {type(res)}"
        return res
    
    def predict_step(self, batch, batch_idx, dataloader_idx=None):
        try:
            prediction: List[DetokenzeOutput] = self._predict_step(batch=batch, batch_idx=batch_idx, dataloader_idx=dataloader_idx)
            return prediction
        except Exception as e:
            print(str(e))
            return []
    
class ARWriter(BasePredictionWriter):
    def __init__(
        self,
        output_dir: Union[str, None],
        order_config: Union[OrderConfig, None]=None,
        **kwargs
    ):
        super().__init__('batch')
        self.output_dir         = output_dir
        self.npz_dir            = kwargs.get('npz_dir', None)
        self.user_mode          = kwargs.get('user_mode', False)
        self.output_name        = kwargs.get('output_name', None) # for a single name
        self.repeat             = kwargs.get('repeat', 1)
        self.add_num            = kwargs.get('add_num', False)
        self.export_npz         = kwargs.get('export_npz', None)
        self.export_obj         = kwargs.get('export_obj', None)
        self.export_fbx         = kwargs.get('export_fbx', None)
        self.export_pc          = kwargs.get('export_pc', None)
        if order_config is not None:
            self.order = get_order(config=order_config)
        else:
            self.order = None
        
        self._epoch = 0
        
    def on_predict_end(self, trainer, pl_module):
        if self._epoch < self.repeat - 1:
            print(f"Finished prediction run {self._epoch + 1}/{self.repeat}, starting next run...")
            self._epoch += 1
            trainer.predict_dataloader = trainer.datamodule.predict_dataloader()
            trainer.predict_loop.run()

    def write_on_batch_end(self, trainer, pl_module: ARSystem, prediction: List[Dict], batch_indices, batch, batch_idx, dataloader_idx):
        assert 'path' in batch
        paths = batch['path']
        detokenize_output_list: List[DetokenzeOutput] = prediction
        vertices = batch['vertices']
        
        origin_vertices = batch['origin_vertices']
        origin_vertex_normals = batch['origin_vertex_normals']
        origin_faces = batch['origin_faces']
        origin_face_normals = batch['origin_face_normals']
        num_points = batch['num_points']
        num_faces = batch['num_faces']
        
        if isinstance(origin_vertices, torch.Tensor):
            origin_vertices = origin_vertices.detach().cpu().numpy()
        if isinstance(origin_vertex_normals, torch.Tensor):
            origin_vertex_normals = origin_vertex_normals.detach().cpu().numpy()
        if isinstance(origin_faces, torch.Tensor):
            origin_faces = origin_faces.detach().cpu().numpy()
        if isinstance(origin_face_normals, torch.Tensor):
            origin_face_normals = origin_face_normals.detach().cpu().numpy()
        if isinstance(num_points, torch.Tensor):
            num_points = num_points.detach().cpu().numpy()
        if isinstance(num_faces, torch.Tensor):
            num_faces = num_faces.detach().cpu().numpy()

        for (id, detokenize_output) in enumerate(detokenize_output_list):
            assert isinstance(detokenize_output, DetokenzeOutput), f"expect item of the list to be DetokenzeOutput, found: {type(detokenize_output)}"
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
            
            num_p = num_points[id]
            num_f = num_faces[id]
            
            # Load original material data from the extraction NPZ file
            original_uv_coords = []
            original_materials = []
            try:
                # Get the path from batch - this might be a directory or NPZ file
                batch_path = paths[id]
                original_npz_path = batch_path
                
                # If it's a directory, look for raw_data.npz inside it
                if os.path.isdir(batch_path):
                    original_npz_path = os.path.join(batch_path, 'raw_data.npz')
                
                print(f"DEBUG: ARWriter batch path: {batch_path}")
                print(f"DEBUG: ARWriter original NPZ path: {original_npz_path}")
                
                if os.path.exists(original_npz_path):
                    print(f"DEBUG: ARWriter loading original material data from: {original_npz_path}")
                    original_data = RawData.load(original_npz_path)
                    if hasattr(original_data, 'uv_coords') and original_data.uv_coords is not None:
                        original_uv_coords = original_data.uv_coords
                        print(f"DEBUG: ARWriter loaded {len(original_uv_coords)} UV coordinates")
                    if hasattr(original_data, 'materials') and original_data.materials is not None:
                        original_materials = original_data.materials
                        print(f"DEBUG: ARWriter loaded {len(original_materials)} materials")
                else:
                    print(f"DEBUG: ARWriter - original NPZ path not found: {original_npz_path}")
            except Exception as e:
                print(f"DEBUG: ARWriter - failed to load original material data: {e}")
                import traceback
                print(f"DEBUG: ARWriter - traceback: {traceback.format_exc()}")
            
            raw_data = RawData(
                vertices=origin_vertices[id, :num_p],
                vertex_normals=origin_vertex_normals[id, :num_p],
                faces=origin_faces[id, :num_f],
                face_normals=origin_face_normals[id, :num_f],
                joints=detokenize_output.joints,
                tails=detokenize_output.tails,
                parents=detokenize_output.parents,
                skin=None,
                no_skin=detokenize_output.no_skin,
                names=detokenize_output.names,
                matrix_local=None,
                uv_coords=original_uv_coords,
                materials=original_materials,
                path=None,
                cls=detokenize_output.cls,
            )
            if self.export_npz is not None:
                npz_path = make_path(self.export_npz, 'npz')
                print(npz_path)
                raw_data.save(path=npz_path)
            if self.export_obj is not None:
                raw_data.export_skeleton(path=make_path(self.export_obj, 'obj'))
            if self.export_pc is not None:
                raw_data.export_pc(path=make_path(self.export_pc, 'obj'))
            if self.export_fbx is not None:
                if not self.user_mode:
                    raw_data.export_fbx(path=make_path(self.export_fbx, 'fbx'))
                else:
                    if self.output_name is not None:
                        raw_data.export_fbx(path=self.output_name)
                    else:
                        raw_data.export_fbx(path=make_path(self.export_fbx, 'fbx', trim=True))
            
            # Export skeleton prediction text file
            if self.export_fbx is not None:
                skeleton_txt_path = make_path('skeleton_pred', 'txt')
                os.makedirs(os.path.dirname(skeleton_txt_path), exist_ok=True)
                
                # Create skeleton prediction text content
                with open(skeleton_txt_path, 'w') as f:
                    f.write("# Skeleton Prediction Data\n")
                    f.write(f"# Number of joints: {len(detokenize_output.joints)}\n")
                    f.write(f"# Class: {detokenize_output.cls}\n")
                    f.write("# Format: joint_index x y z parent_index name\n")
                    
                    for i, (joint, name) in enumerate(zip(detokenize_output.joints, detokenize_output.names)):
                        parent_idx = detokenize_output.parents[i] if detokenize_output.parents[i] is not None else -1
                        f.write(f"{i} {joint[0]:.6f} {joint[1]:.6f} {joint[2]:.6f} {parent_idx} {name}\n")
                    
                    if detokenize_output.tails is not None:
                        f.write("\n# Tail positions\n")
                        f.write("# Format: joint_index tail_x tail_y tail_z\n")
                        for i, tail in enumerate(detokenize_output.tails):
                            f.write(f"{i} {tail[0]:.6f} {tail[1]:.6f} {tail[2]:.6f}\n")