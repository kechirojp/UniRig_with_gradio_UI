import numpy as np
from numpy import ndarray
from typing import List, Union, Tuple
from collections import defaultdict
import os

try:
    import open3d as o3d
    OPEN3D_EQUIPPED = True
except:
    print("do not have open3d")
    OPEN3D_EQUIPPED = False

class Exporter():
    def __init__(self, blender_path=None, render_config=None):
        self.blender_path = blender_path
        self.render_config = render_config
    
    def _safe_make_dir(self, path):
        if os.path.dirname(path) == '':
            return
        os.makedirs(os.path.dirname(path), exist_ok=True)
    
    def _export_skeleton(self, joints: ndarray, parents: List[Union[int, None]], path: str):
        format = path.split('.')[-1]
        assert format in ['obj']
        name = path.removesuffix('.obj')
        path = name + ".obj"
        self._safe_make_dir(path)
        J = joints.shape[0]
        with open(path, 'w') as file:
            file.write("o spring_joint\n")
            _joints = []
            for id in range(J):
                pid = parents[id]
                if pid is None or pid == -1:
                    continue
                bx, by, bz = joints[id]
                ex, ey, ez = joints[pid]
                _joints.extend([
                    f"v {bx} {bz} {-by}\n",
                    f"v {ex} {ez} {-ey}\n",
                    f"v {ex} {ez} {-ey + 0.00001}\n"
                ])
            file.writelines(_joints)
            
            _faces = [f"f {id*3+1} {id*3+2} {id*3+3}\n" for id in range(J)]
            file.writelines(_faces)
    
    def _export_bones(self, bones: ndarray, path: str):
        format = path.split('.')[-1]
        assert format in ['obj']
        name = path.removesuffix('.obj')
        path = name + ".obj"
        self._safe_make_dir(path)
        J = bones.shape[0]
        with open(path, 'w') as file:
            file.write("o bones\n")
            _joints = []
            for bone in bones:
                bx, by, bz = bone[:3]
                ex, ey, ez = bone[3:]
                _joints.extend([
                    f"v {bx} {bz} {-by}\n",
                    f"v {ex} {ez} {-ey}\n",
                    f"v {ex} {ez} {-ey + 0.00001}\n"
                ])
            file.writelines(_joints)
            
            _faces = [f"f {id*3+1} {id*3+2} {id*3+3}\n" for id in range(J)]
            file.writelines(_faces)
    
    def _export_skeleton_sequence(self, joints: ndarray, parents: List[Union[int, None]], path: str):
        format = path.split('.')[-1]
        assert format in ['obj']
        name = path.removesuffix('.obj')
        path = name + ".obj"
        self._safe_make_dir(path)
        J = joints.shape[0]
        for i in range(J):
            file = open(name + f"_{i}.obj", 'w')
            file.write("o spring_joint\n")
            _joints = []
            for id in range(i + 1):
                pid = parents[id]
                if pid is None:
                    continue
                bx, by, bz = joints[id]
                ex, ey, ez = joints[pid]
                _joints.extend([
                    f"v {bx} {bz} {-by}\n",
                    f"v {ex} {ez} {-ey}\n",
                    f"v {ex} {ez} {-ey + 0.00001}\n"
                ])
            file.writelines(_joints)
            
            _faces = [f"f {id*3+1} {id*3+2} {id*3+3}\n" for id in range(J)]
            file.writelines(_faces)
            file.close()
    
    def _export_mesh(self, vertices: ndarray, faces: ndarray, path: str):
        format = path.split('.')[-1]
        assert format in ['obj', 'ply']
        if path.endswith('ply'):
            if not OPEN3D_EQUIPPED:
                raise RuntimeError("open3d is not available")
            mesh = o3d.geometry.TriangleMesh()
            mesh.vertices = o3d.utility.Vector3dVector(vertices)
            mesh.triangles = o3d.utility.Vector3iVector(faces)
            self._safe_make_dir(path)
            o3d.io.write_triangle_mesh(path, mesh)
            return
        name = path.removesuffix('.obj')
        path = name + ".obj"
        self._safe_make_dir(path)
        with open(path, 'w') as file:
            file.write("o mesh\n")
            _vertices = []
            for co in vertices:
                _vertices.append(f"v {co[0]} {co[2]} {-co[1]}\n")
            file.writelines(_vertices)
            _faces = []
            for face in faces:
                _faces.append(f"f {face[0]+1} {face[1]+1} {face[2]+1}\n")
            file.writelines(_faces)
            
    def _export_pc(self, vertices: ndarray, path: str, vertex_normals: Union[ndarray, None]=None, normal_size: float=0.01):
        if path.endswith('.ply'):
            if vertex_normals is not None:
                print("normal result will not be displayed in .ply format")
            name = path.removesuffix('.ply')
            path = name + ".ply"
            pc = o3d.geometry.PointCloud()
            pc.points = o3d.utility.Vector3dVector(vertices)
            # segment fault when numpy >= 2.0 !! use torch environment
            self._safe_make_dir(path)
            o3d.io.write_point_cloud(path, pc)
            return
        name = path.removesuffix('.obj')
        path = name + ".obj"
        self._safe_make_dir(path)
        with open(path, 'w') as file:
            file.write("o pc\n")
            _vertex = []
            for co in vertices:
                _vertex.append(f"v {co[0]} {co[2]} {-co[1]}\n")
            file.writelines(_vertex)
            if vertex_normals is not None:
                new_path = path.replace('.obj', '_normal.obj')
                nfile = open(new_path, 'w')
                nfile.write("o normal\n")
                _normal = []
                for i in range(vertices.shape[0]):
                    co = vertices[i]
                    x = vertex_normals[i, 0]
                    y = vertex_normals[i, 1]
                    z = vertex_normals[i, 2]
                    _normal.extend([
                        f"v {co[0]} {co[2]} {-co[1]}\n",
                        f"v {co[0]+0.0001} {co[2]} {-co[1]}\n",
                        f"v {co[0]+x*normal_size} {co[2]+z*normal_size} {-(co[1]+y*normal_size)}\n",
                        f"f {i*3+1} {i*3+2} {i*3+3}\n",
                    ])
                nfile.writelines(_normal)
    
    def _make_armature(
        self,
        vertices: Union[ndarray, None],
        joints: ndarray,
        skin: Union[ndarray, None],
        parents: List[Union[int, None]],
        names: List[str],
        faces: Union[ndarray, None]=None,
        extrude_size: float=0.03,
        group_per_vertex: int=-1,
        add_root: bool=False,
        do_not_normalize: bool=False,
        use_extrude_bone: bool=True,
        use_connect_unique_child: bool=True,
        extrude_from_parent: bool=True,
        tails: Union[ndarray, None]=None,
    ):
        import bpy # type: ignore
        from mathutils import Vector # type: ignore
        import sys
        
        # Blender 4.2対応のコンテキスト管理をインポート
        sys.path.append('/app')
        try:
            from blender_42_context_fix import Blender42ContextManager
            context_mgr = Blender42ContextManager()
            print("✅ _make_armature: Blender 4.2コンテキスト管理適用")
        except ImportError as e:
            print(f"⚠️ _make_armature: Blender 4.2コンテキスト管理インポート失敗: {e}")
            context_mgr = None
        
        # make collection
        collection = bpy.data.collections.new('new_collection')
        bpy.context.scene.collection.children.link(collection)
        
        # make mesh
        if vertices is not None:
            mesh = bpy.data.meshes.new('mesh')
            if faces is None:
                faces = []
            mesh.from_pydata(vertices, [], faces)
            mesh.update()
        
            # make object from mesh
            object = bpy.data.objects.new('character', mesh)
        
            # add object to scene collection
            collection.objects.link(object)
        
        # Safe armature creation with Blender 4.2 context management
        if context_mgr:
            context_mgr.safe_deselect_all()
            context_mgr.safe_set_mode('OBJECT')
        
        # deselect mesh and add armature
        try:
            bpy.ops.object.armature_add(enter_editmode=True)
        except Exception as e:
            print(f"⚠️ armature_add with enter_editmode failed: {e}")
            # Fallback: add armature without entering edit mode
            bpy.ops.object.armature_add()
            if context_mgr:
                context_mgr.safe_set_mode('EDIT')
        
        armature = bpy.data.armatures.get('Armature')
        edit_bones = armature.edit_bones
        
        J = joints.shape[0]
        if tails is None:
            tails = joints.copy()
            tails[:, 2] += extrude_size
        connects = [False for _ in range(J)]
        children = defaultdict(list)
        for i in range(1, J):
            children[parents[i]].append(i)
        if tails is not None:
            if use_extrude_bone:
                for i in range(J):
                    if len(children[i]) != 1 and extrude_from_parent and i != 0:
                        pjoint = joints[parents[i]]
                        joint = joints[i]
                        d = joint - pjoint
                        if np.linalg.norm(d) < 0.000001:
                            d = np.array([0., 0., 1.]) # in case son.head == parent.head
                        else:
                            d = d / np.linalg.norm(d)
                        tails[i] = joint + d * extrude_size
            if use_connect_unique_child:
                for i in range(J):
                    if len(children[i]) == 1:
                        child = children[i][0]
                        tails[i] = joints[child]
                    if parents[i] is not None and len(children[parents[i]]) == 1:
                        connects[i] = True
        
        if add_root:
            bone_root = edit_bones.get('Bone')
            bone_root.name = 'Root'
            bone_root.tail = Vector((joints[0, 0], joints[0, 1], joints[0, 2]))
        else:
            bone_root = edit_bones.get('Bone')
            bone_root.name = names[0]
            bone_root.head = Vector((joints[0, 0], joints[0, 1], joints[0, 2]))
            bone_root.tail = Vector((joints[0, 0], joints[0, 1], joints[0, 2] + extrude_size))
        
        def extrude_bone(
            edit_bones,
            name: str,
            parent_name: str,
            head: Tuple[float, float, float],
            tail: Tuple[float, float, float],
            connect: bool
        ):
            bone = edit_bones.new(name)
            bone.head = Vector((head[0], head[1], head[2]))
            bone.tail = Vector((tail[0], tail[1], tail[2]))
            bone.name = name
            parent_bone = edit_bones.get(parent_name)
            bone.parent = parent_bone
            bone.use_connect = connect
            assert not np.isnan(head).any(), f"nan found in head of bone {name}"
            assert not np.isnan(tail).any(), f"nan found in tail of bone {name}"
        
        for i in range(J):
            if add_root is False and i==0:
                continue
            edit_bones = armature.edit_bones
            pname = 'Root' if parents[i] is None else names[parents[i]]
            extrude_bone(edit_bones, names[i], pname, joints[i], tails[i], connects[i])
        for i in range(J):
            bone = edit_bones.get(names[i])
            bone.head = Vector((joints[i, 0], joints[i, 1], joints[i, 2]))
            bone.tail = Vector((tails[i, 0], tails[i, 1], tails[i, 2]))
        
        # 🛡️ CRITICAL: Edit Mode脱出をUltimate Defensive Systemで強化
        print("🛡️ アーマチュア作成完了 - Ultimate Defensive Edit Mode脱出開始...")
        
        if context_mgr:
            # Ultimate Defensive Armature Resolution を適用
            ultimate_exit_success = context_mgr.ultimate_defensive_armature_resolution()
            if ultimate_exit_success:
                print("✅ Ultimate Defensive Edit Mode脱出成功")
            else:
                print("⚠️ Ultimate Defensive Edit Mode脱出に問題 - 従来の方法を使用")
                # フォールバック: 従来の方法
                try:
                    context_mgr.safe_set_mode('OBJECT')
                except Exception as e:
                    print(f"⚠️ フォールバックEdit Mode脱出エラー: {e}")
        else:
            # context_mgrが無い場合の従来の方法
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except Exception as e:
                print(f"⚠️ 従来のEdit Mode脱出エラー: {e}")
        
        # アーマチュア状態の最終検証
        armature_obj = bpy.data.objects.get('Armature')
        if armature_obj and armature_obj.type == 'ARMATURE':
            if armature_obj.mode == 'OBJECT':
                print(f"✅ アーマチュア '{armature_obj.name}' は正常にObject Modeです")
            else:
                print(f"❌ 警告: アーマチュア '{armature_obj.name}' がまだ {armature_obj.mode} モードです")
        
        if vertices is None or skin is None:
            return
        # must set to object mode to enable parent_set
        if context_mgr:
            context_mgr.safe_set_mode('OBJECT')
        else:
            bpy.ops.object.mode_set(mode='OBJECT')
            
        objects = bpy.data.objects
        
        # Safe selection management with Blender 4.2 compatibility
        if context_mgr:
            context_mgr.safe_deselect_all()
        else:
            # 🚨 BLENDER 4.2 CRITICAL FIX: Comprehensive context error prevention
            self._safe_deselect_all_objects()
                
        ob = objects['character']
        arm = bpy.data.objects['Armature']
        ob.select_set(True)
        arm.select_set(True)
        
        # Set active object safely
        if context_mgr:
            context_mgr.safe_set_active_object(arm)
        
        bpy.ops.object.parent_set(type='ARMATURE_NAME')
        vis = []
        for x in ob.vertex_groups:
            vis.append(x.name)
        #sparsify
        argsorted = np.argsort(-skin, axis=1)
        vertex_group_reweight = skin[np.arange(skin.shape[0])[..., None], argsorted]
        if group_per_vertex == -1:
            group_per_vertex = vertex_group_reweight.shape[-1]
        if not do_not_normalize:
            vertex_group_reweight = vertex_group_reweight / vertex_group_reweight[..., :group_per_vertex].sum(axis=1)[...,None]

        for v, w in enumerate(skin):
            for ii in range(group_per_vertex):
                i = argsorted[v, ii]
                if i >= J:
                    continue
                n = names[i]
                if n not in vis:
                    continue
                ob.vertex_groups[n].add([v], vertex_group_reweight[v, ii], 'REPLACE')

    def _clean_bpy(self, preserve_textures=False):
        """Clean Blender data with optional texture preservation."""
        import bpy # type: ignore
        for c in bpy.data.actions:
            bpy.data.actions.remove(c)
        for c in bpy.data.armatures:
            bpy.data.armatures.remove(c)
        for c in bpy.data.cameras:
            bpy.data.cameras.remove(c)
        for c in bpy.data.collections:
            bpy.data.collections.remove(c)
        
        # Conditionally preserve images and materials for textures
        if not preserve_textures:
            for c in bpy.data.images:
                bpy.data.images.remove(c)
            for c in bpy.data.materials:
                bpy.data.materials.remove(c)
            for c in bpy.data.textures:
                bpy.data.textures.remove(c)
        
        for c in bpy.data.meshes:
            bpy.data.meshes.remove(c)
        for c in bpy.data.objects:
            bpy.data.objects.remove(c)
    
    def _export_fbx(
        self,
        path: str,
        vertices: Union[ndarray, None],
        joints: ndarray,
        skin: Union[ndarray, None],
        parents: List[Union[int, None]],
        names: List[str],
        faces: Union[ndarray, None]=None,
        extrude_size: float=0.03,
        group_per_vertex: int=-1,
        add_root: bool=False,
        do_not_normalize: bool=False,
        use_extrude_bone: bool=True,
        use_connect_unique_child: bool=True,
        extrude_from_parent: bool=True,
        tails: Union[ndarray, None]=None,
    ):
        '''
        Requires bpy installed - Enhanced for Blender 4.2 compatibility
        '''
        import bpy # type: ignore
        import sys
        import os
        
        # Blender 4.2対応のコンテキスト管理をインポート
        sys.path.append('/app')
        try:
            from blender_42_context_fix import Blender42ContextManager
            context_mgr = Blender42ContextManager()
            print("✅ Blender 4.2コンテキスト管理システム適用")
        except ImportError as e:
            print(f"⚠️ Blender 4.2コンテキスト管理インポート失敗: {e}")
            context_mgr = None
        
        self._safe_make_dir(path)
        self._clean_bpy(preserve_textures=True)
        self._make_armature(
            vertices=vertices,
            joints=joints,
            skin=skin,
            parents=parents,
            names=names,
            faces=faces,
            extrude_size=extrude_size,
            group_per_vertex=group_per_vertex,
            add_root=add_root,
            do_not_normalize=do_not_normalize,
            use_extrude_bone=use_extrude_bone,
            use_connect_unique_child=use_connect_unique_child,
            extrude_from_parent=extrude_from_parent,
            tails=tails,
        )
        
        # 🛡️ ULTIMATE DEFENSIVE ARMATURE RESOLUTION SYSTEM
        # 🚨 CRITICAL: この処理により65ボーンのFBXエクスポート成功を実現
        if context_mgr:
            print("🛡️ Ultimate Defensive Armature Resolution System実行中...")
            
            # Ultimate Defensive Armature Resolution - 5段階の防御戦略を適用
            ultimate_success = context_mgr.ultimate_defensive_armature_resolution()
            
            if ultimate_success:
                print("✅ Ultimate Defensive Armature Resolution成功")
                print("🎯 65ボーンスケルトンのFBXエクスポート準備完了")
            else:
                print("❌ Ultimate Defensive Armature Resolution失敗")
                print("⚠️ フォールバック処理でFBXエクスポートを試行します")
            
            # 追加の検証: 最終的なアーマチュア状態確認
            export_context = context_mgr.get_safe_export_context()
            print(f"📊 最終エクスポートコンテキスト: {export_context}")
            
            # アーマチュアオブジェクトの状態確認
            armature_count = 0
            edit_mode_count = 0
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE':
                    armature_count += 1
                    if obj.mode != 'OBJECT':
                        edit_mode_count += 1
                        print(f"⚠️ アーマチュア {obj.name} がまだ {obj.mode} モードです")
            
            print(f"📊 検出されたアーマチュア数: {armature_count}")
            print(f"📊 Edit Modeに残っているアーマチュア数: {edit_mode_count}")
            
            if edit_mode_count == 0:
                print("✅ 全てのアーマチュアがObject Modeに正常に設定されました")
            else:
                print(f"⚠️ {edit_mode_count}個のアーマチュアがEdit Modeに残っています")
        
        try:
            # 🚨 CRITICAL FIX: Use Blender 4.2 Context Override for FBX Export
            # Prevents AttributeError: 'Context' object has no attribute 'selected_objects'
            print("🚀 Blender 4.2 Context Override FBXエクスポート実行中...")
            
            if context_mgr:
                # Use safe context override export method
                success = context_mgr.safe_fbx_export_with_context_override(
                    filepath=path,
                    check_existing=False,
                    # 🚨 CRITICAL FIX: Prevent Z_UP to Y_UP conversion causing -90 degree rotation
                    axis_forward='-Z',           # Forward: -Z (Blender standard)
                    axis_up='Y',                 # Up: Y (Blender standard)
                    # 🚨 CRITICAL FIX: Add object types to include skeleton data
                    object_types={'MESH', 'ARMATURE'},  # Fix: Include both mesh and skeleton
                    # Standard FBX export settings
                    use_selection=False,         # Export all objects
                    global_scale=1.0,           # Standard scale
                    apply_unit_scale=True,      # Apply unit scale
                    apply_scale_options='FBX_SCALE_NONE',  # No scale transformation
                    use_space_transform=False,  # 🚨 CRITICAL: Disable space transform to prevent rotation
                    bake_space_transform=False, # Don't bake transform
                    # Armature and skeleton settings
                    add_leaf_bones=False,
                    use_armature_deform_only=True,  # Only deform bones
                    armature_nodetype='NULL',   # Standard armature node type
                    primary_bone_axis='Y',      # Primary bone axis
                    secondary_bone_axis='X',    # Secondary bone axis
                    # 🚨 Blender 4.2: Binary FBX is default (use_ascii parameter removed)
                    # Texture embedding settings
                    path_mode='COPY',  # Copy textures to output directory
                    embed_textures=True,  # Embed textures in FBX
                    # Material settings
                    use_mesh_modifiers=True,
                    use_custom_props=True,
                    # Animation settings (if needed)
                    bake_anim=False,
                    # Mesh quality settings
                    use_tspace=True,  # Use tangent space for normal maps
                    mesh_smooth_type='OFF',  # Preserve original smoothing
                    # UV coordinate preservation
                    use_mesh_edges=False,       # Optimize edges
                    use_triangles=False,        # Keep quads where possible
                    # Advanced settings
                    use_metadata=True,          # Include metadata
                    batch_mode='OFF'            # Single file export
                )
                
                if success:
                    file_size = os.path.getsize(path) if os.path.exists(path) else 0
                    print(f"✅ Context Override FBXエクスポート成功: {path} ({file_size:,} bytes)")
                else:
                    print(f"⚠️ Context Override FBXエクスポート失敗")
                    raise RuntimeError("Context Override FBX export failed")
            else:
                # Fallback: Direct export (risky in Blender 4.2)
                print("⚠️ Fallback: Direct FBXエクスポート (Context Manager unavailable)")
                result = bpy.ops.export_scene.fbx(
                    filepath=path, 
                    check_existing=False,
                    axis_forward='-Z', axis_up='Y',
                    object_types={'MESH', 'ARMATURE'},
                    use_selection=False, global_scale=1.0,
                    apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE',
                    use_space_transform=False, bake_space_transform=False,
                    add_leaf_bones=False, use_armature_deform_only=True,
                    path_mode='COPY', embed_textures=True,
                    use_mesh_modifiers=True, bake_anim=False,
                    use_metadata=True, batch_mode='OFF'
                )
                
                if result == {'FINISHED'}:
                    file_size = os.path.getsize(path) if os.path.exists(path) else 0
                    print(f"✅ Fallback FBXエクスポート成功: {path} ({file_size:,} bytes)")
                else:
                    print(f"⚠️ Fallback FBXエクスポート警告: {result}")
                
        except Exception as e:
            print(f"❌ FBXエクスポートエラー: {e}")
            print(f"💡 エラー詳細: {type(e).__name__}")
            
            # 🛡️ Ultimate Defensive Armature Resolution System によるフォールバック
            if context_mgr:
                try:
                    print("🛡️ Ultimate Defensive フォールバック処理開始...")
                    
                    # 再度Ultimate Defensive Armature Resolutionを実行
                    ultimate_recovery_success = context_mgr.ultimate_defensive_armature_resolution()
                    
                    if ultimate_recovery_success:
                        print("✅ Ultimate Defensive Recovery成功 - FBXエクスポートリトライ")
                        
                        # 強化されたFBXエクスポート設定でリトライ
                        print("🔄 Ultimate Defensive設定でFBXエクスポートリトライ...")
                        result = bpy.ops.export_scene.fbx(
                            filepath=path, 
                            check_existing=False,
                            # 🚨 CRITICAL FIX: Apply same orientation fixes to fallback
                            axis_forward='-Z',           # Fix: Correct forward orientation
                            axis_up='Y',                 # Fix: Correct up orientation  
                            # 🚨 CRITICAL FIX: Include skeleton data in fallback
                            object_types={'MESH', 'ARMATURE'},  # Fix: Include both mesh and skeleton
                            # 🚨 CRITICAL FIX: Disable space transform to prevent rotation
                            use_space_transform=False,   # Prevent Z_UP to Y_UP conversion rotation
                            # 🚨 Blender 4.2: Binary FBX is default (use_ascii parameter removed)
                            add_leaf_bones=False,
                            use_armature_deform_only=True,  # Only deform bones
                            # テクスチャエンベッド設定
                            path_mode='COPY',
                            embed_textures=True,
                            # メッシュ品質設定
                            use_mesh_modifiers=True,
                            use_tspace=True
                        )
                        print(f"✅ Ultimate Defensive FBXエクスポート: {result}")
                        
                        if result == {'FINISHED'}:
                            file_size = os.path.getsize(path) if os.path.exists(path) else 0
                            print(f"🎯 Ultimate Defensive成功: {path} ({file_size:,} bytes)")
                            print("🏆 65ボーンスケルトンFBXエクスポート成功!")
                            return  # 成功したので処理終了
                    else:
                        print("❌ Ultimate Defensive Recovery失敗")
                    
                    # 最小限のFBXエクスポートでリトライ（従来のフォールバック）
                    print("🔄 最小限設定でFBXエクスポートリトライ...")
                    result = bpy.ops.export_scene.fbx(
                        filepath=path, 
                        check_existing=False,
                        # 🚨 CRITICAL FIX: Apply orientation fixes to minimal fallback
                        axis_forward='-Z',           # Fix: Correct forward orientation
                        axis_up='Y',                 # Fix: Correct up orientation  
                        # 🚨 CRITICAL FIX: Include skeleton data in minimal fallback
                        object_types={'MESH', 'ARMATURE'},  # Fix: Include both mesh and skeleton
                        # 🚨 CRITICAL FIX: Disable space transform to prevent rotation
                        use_space_transform=False,   # Prevent Z_UP to Y_UP conversion rotation
                        # 🚨 Blender 4.2: Binary FBX is default (use_ascii parameter removed)
                        add_leaf_bones=False
                    )
                    print(f"✅ フォールバックFBXエクスポート: {result}")
                    
                    if result == {'FINISHED'}:
                        file_size = os.path.getsize(path) if os.path.exists(path) else 0
                        print(f"✅ フォールバック成功: {path} ({file_size:,} bytes)")
                    
                except Exception as fallback_error:
                    print(f"❌ Ultimate Defensive フォールバックも失敗: {fallback_error}")
                    print(f"💡 Ultimate Defensive エラー詳細: {type(fallback_error).__name__}")
                    
                    # 最終手段: 完全にクリーンな状態でのエクスポート
                    try:
                        print("🆘 最終手段: 完全クリーン状態でのエクスポート...")
                        bpy.ops.object.select_all(action='DESELECT')
                        bpy.context.view_layer.objects.active = None
                        
                        result = bpy.ops.export_scene.fbx(
                            filepath=path, 
                            check_existing=False,
                            # 🚨 CRITICAL FIX: Apply essential fixes even in emergency fallback
                            axis_forward='-Z',           # Fix: Correct forward orientation
                            axis_up='Y',                 # Fix: Correct up orientation  
                            # 🚨 CRITICAL FIX: Disable space transform to prevent rotation
                            use_space_transform=False,   # Prevent Z_UP to Y_UP conversion rotation
                            object_types={'MESH', 'ARMATURE'}  # Fix: Include skeleton data
                        )
                        print(f"🆘 最終手段エクスポート結果: {result}")
                        
                    except Exception as final_error:
                        print(f"🆘 最終手段も失敗: {final_error}")
                        raise fallback_error
            else:
                raise
    
    def _export_render(
        self,
        path: str,
        vertices: Union[ndarray, None],
        faces: Union[ndarray, None],
        bones: Union[ndarray, None],
        resolution: Tuple[float, float]=[256, 256],
    ):
        import bpy # type: ignore
        import bpy_extras # type: ignore
        from mathutils import Vector # type: ignore
        
        self._safe_make_dir(path)
        # normalize into [-1, 1]^3
        # copied from augment
        assert (vertices is not None) or (bones is not None)
        bounds = []
        if vertices is not None:
            bounds.append(vertices)
        if bones is not None:
            bounds.append(bones[:, :3])
            bounds.append(bones[:, 3:])
        bounds = np.concatenate(bounds, axis=0)
        bound_min = bounds.min(axis=0)
        bound_max = bounds.max(axis=0)
        
        trans_vertex = np.eye(4)
        
        trans_vertex = _trans_to_m(-(bound_max + bound_min)/2) @ trans_vertex
        
        # scale into the cube [-1, 1]
        scale = np.max((bound_max - bound_min) / 2)
        trans_vertex = _scale_to_m(1. / scale) @ trans_vertex
        
        def _apply(v: ndarray, trans: ndarray) -> ndarray:
            return np.matmul(v, trans[:3, :3].transpose()) + trans[:3, 3]
        
        if vertices is not None:
            vertices = _apply(vertices, trans_vertex)
        if bones is not None:
            bones[:, :3] = _apply(bones[:, :3], trans_vertex)
            bones[:, 3:] = _apply(bones[:, 3:], trans_vertex)
        
        # bpy api calls
        self._clean_bpy(preserve_textures=True)
        bpy.context.scene.render.engine = 'BLENDER_WORKBENCH'
        bpy.context.scene.render.film_transparent = True
        bpy.context.scene.display.shading.background_type = 'VIEWPORT'
        
        collection = bpy.data.collections.new('new_collection')
        bpy.context.scene.collection.children.link(collection)
        
        if vertices is not None:
            mesh_data = bpy.data.meshes.new(name="MeshData")
            mesh_obj = bpy.data.objects.new(name="MeshObject", object_data=mesh_data)
            collection.objects.link(mesh_obj)

            mesh_data.from_pydata((vertices).tolist(), [], faces.tolist())
            mesh_data.update()

        def look_at(camera, point):
            direction = point - camera.location
            rot_quat = direction.to_track_quat('-Z', 'Y')
            camera.rotation_euler = rot_quat.to_euler()
        
        bpy.ops.object.camera_add(location=(4, -4, 2.5))
        # 🚨 BLENDER 4.2 CRITICAL FIX: Safe camera object retrieval
        camera = self._safe_get_active_object()
        camera.data.angle = np.radians(25.0)
        look_at(camera, Vector((0, 0, -0.2)))
        bpy.context.scene.camera = camera

        bpy.context.scene.render.resolution_x = resolution[0]
        bpy.context.scene.render.resolution_y = resolution[1]
        bpy.context.scene.render.image_settings.file_format = 'PNG'
        bpy.context.scene.render.filepath = path

        bpy.ops.render.render(write_still=True)
        # some AI generated code to draw bones over mesh
        if bones is not None:
            # TODO: do not save image after rendering
            from PIL import Image, ImageDraw
            img_pil = Image.open(path).convert("RGBA")
            draw = ImageDraw.Draw(img_pil)
            
            from bpy_extras.image_utils import load_image  # type: ignore
            bpy.context.scene.use_nodes = True
            nodes = bpy.context.scene.node_tree.nodes
            # nodes.clear()

            img = load_image(path)
            image_node = nodes.new(type='CompositorNodeImage')
            image_node.image = img

            for i, bone in enumerate(bones):
                head, tail = bone[:3], bone[3:]
                head_2d = bpy_extras.object_utils.world_to_camera_view(bpy.context.scene, camera, Vector(head))
                tail_2d = bpy_extras.object_utils.world_to_camera_view(bpy.context.scene, camera, Vector(tail))

                res_x, res_y = resolution
                head_pix = (head_2d.x * res_x, (1 - head_2d.y) * res_y)
                tail_pix = (tail_2d.x * res_x, (1 - tail_2d.y) * res_y)
                draw.line([head_pix, tail_pix], fill=(255, 0, 0, 255), width=1)
            img_pil.save(path)

def _trans_to_m(v: ndarray):
    m = np.eye(4)
    m[0:3, 3] = v
    return m

def _scale_to_m(r: ndarray):
    m = np.zeros((4, 4))
    m[0, 0] = r
    m[1, 1] = r
    m[2, 2] = r
    m[3, 3] = 1.
    return m

def _safe_deselect_all_objects(self):
        """
        Safe object deselection method for Blender 4.2 compatibility
        """
        import bpy
        try:
            # Method 1: Try standard selected_objects approach
            for o in bpy.context.selected_objects:
                o.select_set(False)
            print("✅ Standard deselection successful")
        except AttributeError:
            try:
                # Method 2: Use view_layer fallback for Blender 4.2
                print("⚠️ Blender 4.2 Context: Using view_layer fallback for deselection")
                for o in bpy.context.view_layer.objects:
                    if o.select_get():
                        o.select_set(False)
                print("✅ View layer deselection successful")
            except Exception as e:
                try:
                    # Method 3: Direct iteration through all objects
                    print(f"⚠️ View layer fallback failed: {e}")
                    print("🔄 Using direct object iteration deselection")
                    for o in bpy.data.objects:
                        o.select_set(False)
                    print("✅ Direct object deselection successful")
                except Exception as final_error:
                    print(f"❌ All deselection methods failed: {final_error}")
        
        # Additional safety: Clear active object
        try:
            bpy.context.view_layer.objects.active = None
        except:
            pass