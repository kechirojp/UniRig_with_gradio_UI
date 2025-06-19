'''
🎯 UniRig マージ処理 - スケルトンとスキニングの統合
====================================================

このモジュールの主な機能:
1. スケルトン（骨格）データの読み込み
2. スキニング（皮膚）データの読み込み  
3. オリジナル3Dモデルへの統合
4. 最終的なリギング済み3Dモデルの出力

処理フロー:
Step1: Blender環境の初期化とクリーンアップ
Step2: ソース（スケルトン）ファイルの読み込み
Step3: ターゲット（スキニング）ファイルの読み込み
Step4: データの統合とアーマチュア作成
Step5: 最終FBXファイルの出力

入力:  スケルトンFBX + スキニングFBX
出力:  統合済みFBX（アニメーション可能）
'''
import argparse
import yaml
import os
import numpy as np
from numpy import ndarray

from typing import Tuple, Union, List

import argparse
from tqdm import tqdm
from box import Box

from scipy.spatial import cKDTree

import open3d as o3d
import itertools

import bpy
from mathutils import Vector

from ..data.raw_data import RawData, RawSkin
from ..data.extract import process_mesh, process_armature, get_arranged_bones

def parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str)
    parser.add_argument('--num_runs', type=int)
    parser.add_argument('--id', type=int)
    return parser.parse_args()

def clean_bpy():
    """
    🧹 Blender環境の完全クリーンアップ
    =================================
    
    処理内容:
    - 既存のアクション、アーマチュア、メッシュ等を全削除
    - メモリリークを防ぎ、新しい処理のための環境を準備
    
    重要性:
    - マージ処理前の環境汚染を防ぐ
    - 複数モデル処理時の干渉を回避
    """
    for c in bpy.data.actions:
        bpy.data.actions.remove(c)
    for c in bpy.data.armatures:
        bpy.data.armatures.remove(c)
    for c in bpy.data.cameras:
        bpy.data.cameras.remove(c)
    for c in bpy.data.collections:
        bpy.data.collections.remove(c)
    for c in bpy.data.images:
        bpy.data.images.remove(c)
    for c in bpy.data.materials:
        bpy.data.materials.remove(c)
    for c in bpy.data.meshes:
        bpy.data.meshes.remove(c)
    for c in bpy.data.objects:
        bpy.data.objects.remove(c)
    for c in bpy.data.textures:
        bpy.data.textures.remove(c)

def load(filepath: str, return_armature: bool=False):
    """
    📂 3Dファイルの読み込み（多形式対応）
    ==================================
    
    サポート形式:
    - .vrm (VRoid models)
    - .fbx/.FBX (FBX models) 
    - .obj (Wavefront OBJ)
    - .glb/.gltf (glTF models)
    - .dae (Collada)
    - .blend (Blender files)
    
    引数:
    - filepath: 読み込むファイルのパス
    - return_armature: アーマチュア（骨格）を返すかどうか
    
    戻り値:
    - return_armature=True の場合: アーマチュアオブジェクト
    - return_armature=False の場合: None
    
    重要な処理:
    - ファイル形式に応じた適切なインポート
    - アーマチュアのロール値を0にリセット（異常動作防止）
    """
    if return_armature:
        old_objs = set(bpy.context.scene.objects)

    if not os.path.exists(filepath):
        raise ValueError(f'File {filepath} does not exist !')
    try:
        if filepath.endswith(".vrm"):
            # enable vrm addon and load vrm model
            bpy.ops.preferences.addon_enable(module='vrm')
            
            bpy.ops.import_scene.vrm(
                filepath=filepath,
                use_addon_preferences=True,
                extract_textures_into_folder=False,
                make_new_texture_folder=False,
                set_shading_type_to_material_on_import=False,
                set_view_transform_to_standard_on_import=True,
                set_armature_display_to_wire=True,
                set_armature_display_to_show_in_front=True,
                set_armature_bone_shape_to_default=True,
                disable_bake=True, # customized option for better performance
            )
        elif filepath.endswith(".obj"):
            bpy.ops.wm.obj_import(filepath=filepath)
        elif filepath.endswith(".fbx") or filepath.endswith(".FBX"):
            bpy.ops.import_scene.fbx(filepath=filepath, ignore_leaf_bones=False, use_image_search=False)
        elif filepath.endswith(".glb") or filepath.endswith(".gltf"):
            bpy.ops.import_scene.gltf(filepath=filepath, import_pack_images=False)
        elif filepath.endswith(".dae"):
            bpy.ops.wm.collada_import(filepath=filepath)
        elif filepath.endswith(".blend"):
            with bpy.data.libraries.load(filepath) as (data_from, data_to):
                data_to.objects = data_from.objects
            for obj in data_to.objects:
                if obj is not None:
                    bpy.context.collection.objects.link(obj)
        else:
            raise ValueError(f"not suported type {filepath}")
    except:
        raise ValueError(f"failed to load {filepath}")
    if return_armature:
        armature = [x for x in set(bpy.context.scene.objects)-old_objs if x.type=="ARMATURE"]
        if len(armature)==0:
            return None
        if len(armature)>1:
            raise ValueError(f"multiple armatures found")
        armature = armature[0]
        
        armature.select_set(True)
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='EDIT')
        for bone in bpy.data.armatures[0].edit_bones:
            bone.roll = 0. # change all roll to 0. to prevent weird behaviour

        bpy.ops.object.mode_set(mode='OBJECT')
        armature.select_set(False)
        
        bpy.ops.object.select_all(action='DESELECT')
        return armature

def get_skin(arranged_bones):
    """
    🎭 スキニングデータの抽出
    ========================
    
    処理内容:
    1. シーン内の全メッシュオブジェクトを取得
    2. 各ボーンに対する頂点ウェイトを抽出
    3. ウェイト行列を構築 (頂点数 × ボーン数)
    
    入力:
    - arranged_bones: 整理されたボーンリスト
    
    出力:
    - skin: スキニングウェイト行列 (numpy配列)
    
    重要な仕組み:
    - バーテックスグループ名とボーン名の対応
    - 各頂点に対する複数ボーンの影響度を数値化
    """
    meshes = []
    for v in bpy.data.objects:
        if v.type == 'MESH':
            meshes.append(v)
    index = {}
    for (id, pbone) in enumerate(arranged_bones):
        index[pbone.name] = id
    _dict_skin = {}
    total_bones = len(arranged_bones)
    for obj in meshes:
        total_vertices = len(obj.data.vertices)
        skin_weight = np.zeros((total_vertices, total_bones))
        obj_group_names = [g.name for g in obj.vertex_groups]
        obj_verts = obj.data.vertices
        for bone in arranged_bones:
            if bone.name not in obj_group_names:
                continue

            gidx = obj.vertex_groups[bone.name].index
            bone_verts = [v for v in obj_verts if gidx in [g.group for g in v.groups]]
            for v in bone_verts:
                which = [id for id in range(len(v.groups)) if v.groups[id].group==gidx]
                w = v.groups[which[0]].weight
                skin_weight[v.index, index[bone.name]] = w
        _dict_skin[obj.name] = {
            'skin': skin_weight,
        }
    
    skin = np.concatenate([
        _dict_skin[d]['skin'] for d in _dict_skin
    ], axis=0)
    return skin

def axis(a: np.ndarray):
    b = np.concatenate([-a[:, 0:1], -a[:, 1:2], a[:, 2:3]], axis=1)
    return b

def get_correct_orientation_kdtree(a: np.ndarray, b: np.ndarray, bones: np.ndarray, num: int=16384) -> np.ndarray:
    """
    🔄 メッシュの正しい向きを決定（KDTree使用）
    ==========================================
    
    問題:
    - AIで生成されたメッシュとスケルトンの向きが一致しない場合がある
    - 軸の順序や符号が異なる可能性
    
    解決方法:
    1. 全ての軸の並び替えパターンを試行 (3! = 6通り)
    2. 各軸の符号パターンを試行 (2³ = 8通り)  
    3. KDTreeで最短距離を計算し、最適な変換を選択
    
    引数:
    - a: サンプリングされた頂点
    - b: メッシュ頂点
    - bones: ボーン座標
    - num: サンプリング数（性能調整用）
    
    戻り値:
    - 変換後の頂点とボーン座標
    
    重要性:
    - この処理により、スケルトンとメッシュの位置合わせが正確になる
    - 間違った向きだとアニメーションが破綻する
    """
    '''
    a: sampled_vertiecs
    b: mesh_vertices
    '''
    min_loss = float('inf')
    best_transformed = a.copy()
    axis_permutations = list(itertools.permutations([0, 1, 2]))
    sign_combinations = [(x, y, z) for x in [1, -1] 
                        for y in [1, -1] 
                        for z in [1, -1]]
    _bones = bones.copy()
    for perm in axis_permutations:
        permuted_a = a[np.random.permutation(a.shape[0])[:num]][:, perm]
        for signs in sign_combinations:
            transformed = permuted_a * np.array(signs)
            tree = cKDTree(transformed)
            distances, indices = tree.query(b)
            current_loss = distances.mean()
            if current_loss < min_loss: # prevent from mirroring
                min_loss = current_loss
                best_transformed = a[:, perm] * np.array(signs)
                bones[:, :3] = _bones[:, :3][:, perm] * np.array(signs)
                bones[:, 3:] = _bones[:, 3:][:, perm] * np.array(signs)
    
    return best_transformed, bones

def denormalize_vertices(mesh_vertices: ndarray, vertices: ndarray, bones: ndarray) -> np.ndarray:
    """
    📏 頂点とボーンの正規化解除
    =========================
    
    背景:
    - AI推論では正規化された座標系で処理される
    - 実際のメッシュサイズとスケールに戻す必要
    
    処理内容:
    1. オリジナルメッシュのバウンディングボックスを計算
    2. 中心点とスケールを算出
    3. AI生成データを実際のサイズに変換
    
    変換式:
    - denormalized = normalized * scale + center
    
    重要性:
    - この処理により、スケルトンがモデルの正しいサイズになる
    - スケールが間違うとアニメーションが機能しない
    """
    min_vals = np.min(mesh_vertices, axis=0)
    max_vals = np.max(mesh_vertices, axis=0)
    center = (min_vals + max_vals) / 2
    scale = np.max(max_vals - min_vals) / 2
    denormalized_vertices = vertices * scale + center
    denormalized_bones = bones * scale
    denormalized_bones[:, :3] += center
    denormalized_bones[:, 3:] += center

    return denormalized_vertices, denormalized_bones

def make_armature(
    vertices: ndarray,
    bones: ndarray, # (joint, tail)
    parents: list[Union[int, None]],
    names: list[str],
    skin: ndarray,
    group_per_vertex: int=4,
    add_root: bool=False,
    is_vrm: bool=False,
):
    """
    🦴 アーマチュア（骨格）の作成とスキニング適用
    ==========================================
    
    この関数はマージ処理の核心部分です。
    
    処理の流れ:
    1. 【メッシュ頂点の取得】現在シーンのメッシュ頂点を収集
    2. 【正規化解除】AI生成データを実際のサイズに変換
    3. 【アーマチュア作成】Blenderでアーマチュアオブジェクト作成
    4. 【ボーン構築】親子関係を持つボーン階層を構築
    5. 【向き修正】KDTreeで最適な向きを決定
    6. 【スキニング適用】各頂点に対するボーンウェイトを設定
    7. 【VRM対応】VRMモデルの場合はヒューマノイドボーン設定
    
    引数:
    - vertices: AI生成された頂点座標
    - bones: ボーン座標 (ジョイント + テール)
    - parents: ボーンの親子関係
    - names: ボーン名リスト
    - skin: スキニングウェイト行列
    - group_per_vertex: 頂点あたりの最大ボーン影響数
    - add_root: ルートボーンを追加するか
    - is_vrm: VRMモデルかどうか
    
    重要な技術的処理:
    - KDTreeによる頂点とボーンの最適マッチング
    - ウェイト正規化によるスキニング品質向上
    - バーテックスグループの事前作成による安定性確保
    """
    context = bpy.context
    
    # 🎯 Step 1: メッシュ頂点の収集
    # 【重要な処理】シーン内の全メッシュオブジェクトから頂点座標を取得
    # load(path)で読み込まれたオリジナルメッシュ（bird.glb等）の実際の頂点を収集
    # ワールド座標系に変換して統一座標系で処理
    mesh_vertices = []
    for ob in bpy.data.objects:
        print(ob.name)
        if ob.type != 'MESH':
            continue
        m = np.array(ob.matrix_world)
        matrix_world_rot = m[:3, :3]
        matrix_world_bias = m[:3, 3]
        for v in ob.data.vertices:
            mesh_vertices.append(matrix_world_rot @ np.array(v.co) + matrix_world_bias)

    mesh_vertices = np.stack(mesh_vertices)
    # 📊 例: mesh_vertices.shape = (5742, 3) ← 実際のメッシュ頂点数
    
    # 🎯 Step 2: 正規化解除
    # 【重要な変換処理】AI生成データを実際のメッシュサイズに合わせてスケール調整
    # AI推論では正規化された座標系（-1〜1等）で処理されるため、実サイズに復元
    # vertices: AI生成頂点（2048個、正規化済み）→ 実メッシュサイズの座標に変換
    # bones: AIスケルトン座標 → 実メッシュに合わせたサイズ・位置に調整
    vertices, bones = denormalize_vertices(mesh_vertices, vertices, bones)
    
    # 🎯 Step 3: アーマチュアオブジェクトの作成
    # Blenderでアーマチュア（骨格）オブジェクトを新規作成
    bpy.ops.object.add(type="ARMATURE", location=(0, 0, 0))
    armature = context.object
    
    # VRMモデルの場合は専用設定を適用
    if hasattr(armature.data, 'vrm_addon_extension'):
        armature.data.vrm_addon_extension.spec_version = "1.0"
        humanoid = armature.data.vrm_addon_extension.vrm1.humanoid
        is_vrm = True
        
    # 🎯 Step 4: ボーン階層の構築
    # エディットモードでボーン構造を作成
    bpy.ops.object.mode_set(mode="EDIT")
    edit_bones = armature.data.edit_bones
    
    # オプション: ルートボーンの追加
    if add_root:
        bone_root = edit_bones.new('Root')
        bone_root.name = 'Root'
        bone_root.head = (0., 0., 0.)
        bone_root.tail = (bones[0, 0], bones[0, 1], bones[0, 2])
    
    J = len(names)
    
    # ボーン作成用のヘルパー関数
    def extrude_bone(
        name: Union[None, str],
        parent_name: Union[None, str],
        head: Tuple[float, float, float],
        tail: Tuple[float, float, float],
    ):
        """個別ボーンを作成し、親子関係を設定"""
        bone = edit_bones.new(name)
        bone.head = (head[0], head[1], head[2])
        bone.tail = (tail[0], tail[1], tail[2])
        bone.name = name
        if parent_name is None:
            return
        parent_bone = edit_bones.get(parent_name)
        bone.parent = parent_bone
        bone.use_connect = False # always False currently

    # 🎯 Step 5: 向きの最適化
    # KDTreeを使用してメッシュとスケルトンの向きを最適化
    vertices, bones = get_correct_orientation_kdtree(vertices, mesh_vertices, bones)
    
    # 🎯 Step 6: 全ボーンの作成
    # AI生成されたボーンデータから実際のBlenderボーンを作成
    for i in range(J):
        if add_root:
            pname = 'Root' if parents[i] is None else names[parents[i]]
        else:
            pname = None if parents[i] is None else names[parents[i]]
        extrude_bone(names[i], pname, bones[i, :3], bones[i, 3:])

    # 🎯 Step 7: スキニング適用の準備
    # オブジェクトモードに戻してアーマチュア設定を有効化
    bpy.ops.object.mode_set(mode='OBJECT')
    objects = bpy.data.objects
    for o in bpy.context.selected_objects:
        o.select_set(False)
    
    # 🎯 Step 8: ウェイト正規化
    # 各頂点に対するボーン影響度を正規化（合計が1になるよう調整）
    argsorted = np.argsort(-skin, axis=1)
    vertex_group_reweight = skin[np.arange(skin.shape[0])[..., None], argsorted]
    
    # ゼロ除算防止: 分母が0の場合の安全な処理
    weight_sums = vertex_group_reweight[..., :group_per_vertex].sum(axis=1)
    # 分母が0の場合は1に置き換えて正規化をスキップ
    weight_sums_safe = np.where(weight_sums == 0, 1.0, weight_sums)
    vertex_group_reweight = vertex_group_reweight / weight_sums_safe[..., None]
    vertex_group_reweight = np.nan_to_num(vertex_group_reweight)
    
    # 🎯 Step 9: KDTreeによる頂点マッチング
    # 【核心技術】AI生成頂点と実際のメッシュ頂点の対応関係を構築
    # これが頂点数差異吸収の仕組みの中核部分
    # AI頂点（2048個）で構築したKDTreeに対して実メッシュ頂点（5742個）を検索
    tree = cKDTree(vertices)  # vertices = AI生成頂点（denormalized済み）
    # 🎯 Step 10: 各メッシュオブジェクトへのスキニング適用
    for ob in objects:
        if ob.type != 'MESH':
            continue
            
        # メッシュをアーマチュアの子に設定
        ob.select_set(True)
        armature.select_set(True)
        bpy.ops.object.parent_set(type='ARMATURE_NAME')
        
        # 既存のバーテックスグループ確認
        vis = []
        for x in ob.vertex_groups:
            vis.append(x.name)
        
        # メッシュ頂点をワールド座標系で取得
        n_vertices = []
        m = np.array(ob.matrix_world)
        matrix_world_rot = m[:3, :3]
        matrix_world_bias = m[:3, 3]
        for v in ob.data.vertices:
            n_vertices.append(matrix_world_rot @ np.array(v.co) + matrix_world_bias)
        n_vertices = np.stack(n_vertices)

        # KDTreeで最近傍頂点を検索
        # 【重要】各実メッシュ頂点に対して最も近いAI頂点のインデックスを取得
        # これにより頂点数が異なってもウェイト情報を確実に転写できる
        _, index = tree.query(n_vertices)  # index[i] = 実頂点iに最も近いAI頂点のインデックス

        # 🔧 バーテックスグループ事前作成: names内の全ボーンに対してバーテックスグループを作成
        for bone_name in names:
            if bone_name not in ob.vertex_groups:
                ob.vertex_groups.new(name=bone_name)

        # 🎯 Step 11: 頂点ウェイトの設定
        # 【核心処理】各実メッシュ頂点に対してAI生成ウェイトを転写
        # KDTreeマッチングで見つけた最近傍AI頂点のウェイト情報を実頂点に適用
        for v, co in enumerate(tqdm(n_vertices)):  # 実際のメッシュ頂点をループ（5742個例）
            for ii in range(group_per_vertex):     # 各頂点に最大4ボーンまで影響設定
                i = argsorted[index[v], ii]        # 最近傍AI頂点のウェイト順序取得
                if i >= len(names):
                    continue
                n = names[i]                       # ボーン名取得
                if n not in ob.vertex_groups:
                    continue
                        
                # 【ウェイト転写】実頂点vにAI頂点のウェイトを適用
                # vertex_group_reweight[index[v], ii] = 最近傍AI頂点の正規化済みウェイト
                ob.vertex_groups[n].add([v], vertex_group_reweight[index[v], ii], 'REPLACE')
        armature.select_set(False)
        ob.select_set(False)
    
    # 🎯 Step 12: VRMヒューマノイドボーン設定
    # VRMモデルの場合は標準的なヒューマノイドボーン構造を設定
    if is_vrm:
        armature.data.vrm_addon_extension.spec_version = "1.0"
        humanoid.human_bones.hips.node.bone_name = "J_Bip_C_Hips"
        humanoid.human_bones.spine.node.bone_name = "J_Bip_C_Spine"
        
        humanoid.human_bones.chest.node.bone_name = "J_Bip_C_Chest"
        humanoid.human_bones.neck.node.bone_name = "J_Bip_C_Neck"
        humanoid.human_bones.head.node.bone_name = "J_Bip_C_Head"
        humanoid.human_bones.left_upper_leg.node.bone_name = "J_Bip_L_UpperLeg"
        humanoid.human_bones.left_lower_leg.node.bone_name = "J_Bip_L_LowerLeg"
        humanoid.human_bones.left_foot.node.bone_name = "J_Bip_L_Foot"
        humanoid.human_bones.right_upper_leg.node.bone_name = "J_Bip_R_UpperLeg"
        humanoid.human_bones.right_lower_leg.node.bone_name = "J_Bip_R_LowerLeg"
        humanoid.human_bones.right_foot.node.bone_name = "J_Bip_R_Foot"
        humanoid.human_bones.left_upper_arm.node.bone_name = "J_Bip_L_UpperArm"
        humanoid.human_bones.left_lower_arm.node.bone_name = "J_Bip_L_LowerArm"
        humanoid.human_bones.left_hand.node.bone_name = "J_Bip_L_Hand"
        humanoid.human_bones.right_upper_arm.node.bone_name = "J_Bip_R_UpperArm"
        humanoid.human_bones.right_lower_arm.node.bone_name = "J_Bip_R_LowerArm"
        humanoid.human_bones.right_hand.node.bone_name = "J_Bip_R_Hand"
        
        bpy.ops.vrm.assign_vrm1_humanoid_human_bones_automatically(armature_name="Armature")

def merge(
    path: str,
    output_path: str,
    vertices: ndarray,
    joints: ndarray,
    skin: ndarray,
    parents: List[Union[None, int]],
    names: List[str],
    tails: ndarray,
    add_root: bool=False,
    is_vrm: bool=False,
):
    """
    🎯 UniRig Step4メインマージ関数 - 3つのデータソース統合
    ====================================================
    
    【重要な技術的発見】3つのデータソースの統合処理:
    1. 📦 オリジナルメッシュ: ユーザーがアップロードしたモデル（path引数）
    2. 🦴 AIスケルトン: Step2で生成されたボーン構造（joints, names, parents, tails）
    3. 🎨 AIスキニング: Step3で生成されたウェイト情報（vertices, skin）
    
    【データフロー解析】入力ファイル構成:
    - path = "/app/uploads/bird.glb" (ユーザーアップロード元ファイル)
    - joints/names/parents/tails = Step2のpredict_skeleton.npzから読み込み
    - vertices/skin = Step3のスキニングNPZファイルから読み込み
    
    【頂点数差異吸収の仕組み】:
    - AIスケルトン頂点: 2,048個（例）← 正規化済み座標
    - 実際メッシュ頂点: 5,742個（例）← 実サイズ座標
    - KDTree最近傍マッチングで各実頂点に最適なAIウェイトを転写
    
    処理の流れ:
    1. Blender環境のクリーンアップ
    2. オリジナルモデルファイル（bird.glb）の読み込み → シーンに配置
    3. 既存アーマチュアの削除（クリーンスレート）
    4. AI生成データからアーマチュア作成（KDTreeマッチング＋ウェイト転写）
    5. 最終ファイルのエクスポート（統合FBX出力）
    
    引数:
    - path: オリジナルモデルファイルのパス（例: bird.glb）
    - output_path: 出力ファイルのパス（例: bird_merged.fbx）
    - vertices: AI生成された頂点データ（Step3スキニング処理済み）
    - joints: ジョイント（ボーンの開始点）座標
    - skin: スキニングウェイト行列
    - parents: ボーンの親子関係
    - names: ボーン名リスト
    - tails: ボーンの終点座標
    - add_root: ルートボーンを追加するか
    - is_vrm: VRMモデルかどうか
    """
    # 🎯 Step 1: Blender環境の初期化
    clean_bpy()
    
    # 🎯 Step 2: オリジナルモデルの読み込み
    # 【重要】ここでユーザーがアップロードした元ファイル（bird.glb等）をBlenderシーンに読み込み
    # このメッシュ形状・UV・テクスチャが最終成果物のベースとなる
    try:
        load(path)
    except Exception as e:
        print(f"Failed to load {path}: {e}")
        return
        
    # 🎯 Step 3: 既存アーマチュアの削除
    # オリジナルモデルにアーマチュアがある場合は削除
    for c in bpy.data.armatures:
        bpy.data.armatures.remove(c)
    
    # 🎯 Step 4: ボーンデータの統合
    # ジョイントとテールを結合してボーン座標を作成
    bones = np.concatenate([joints, tails], axis=1)
    
    # 🎯 Step 5: 新しいアーマチュアの作成
    # AI生成データから完全な骨格を構築
    make_armature(
        vertices=vertices,
        bones=bones,
        parents=parents,
        names=names,
        skin=skin,
        group_per_vertex=4,
        add_root=add_root,
        is_vrm=is_vrm,
    )
    
    # 🎯 Step 6: 最終ファイルのエクスポート
    # 出力ディレクトリの作成
    dirpath = os.path.dirname(output_path)
    if dirpath != '':
        os.makedirs(dirpath, exist_ok=True)
    
    # ファイル形式に応じたエクスポート
    try:
        if is_vrm:
            bpy.ops.export_scene.vrm(filepath=output_path)
        elif output_path.endswith(".fbx") or output_path.endswith(".FBX"):
            bpy.ops.export_scene.fbx(filepath=output_path, add_leaf_bones=True)
        elif output_path.endswith(".glb") or output_path.endswith(".gltf"):
            bpy.ops.export_scene.gltf(filepath=output_path)
        elif output_path.endswith(".dae"):
            bpy.ops.wm.collada_export(filepath=output_path)
        elif output_path.endswith(".blend"):
            with bpy.data.libraries.load(output_path) as (data_from, data_to):
                data_to.objects = data_from.objects
        else:
            raise ValueError(f"not suported type {output_path}")
            
        print(f"✅ エクスポート完了: {output_path}")
        
        # 🛡️ エクスポート後の安全な状態リセット
        try:
            # シーン内の選択状態をクリア
            bpy.ops.object.select_all(action='DESELECT')
            # アクティブオブジェクトをクリア
            bpy.context.view_layer.objects.active = None
        except Exception as reset_e:
            print(f"⚠️ 状態リセット中の軽微なエラー: {reset_e}")
            
    except Exception as export_e:
        raise ValueError(f"failed to export {output_path}: {export_e}")

def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

def nullable_string(val):
    if not val:
        return None
    return val

def parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('--require_suffix', type=str, required=True)
    parser.add_argument('--num_runs', type=int, required=True)
    parser.add_argument('--id', type=int, required=True)
    parser.add_argument('--data_config', type=str, required=False)
    parser.add_argument('--skeleton_config', type=str, required=False)
    parser.add_argument('--skin_config', type=str, required=False)
    parser.add_argument('--merge_dir', type=str, required=False)
    parser.add_argument('--merge_name', type=str, required=False)
    parser.add_argument('--add_root', type=str2bool, required=False, default=False)
    parser.add_argument('--source', type=nullable_string, required=False, default=None)
    parser.add_argument('--target', type=nullable_string, required=False, default=None)
    parser.add_argument('--output', type=nullable_string, required=False, default=None)
    return parser.parse_args()

def transfer(source: str, target: str, output: str, add_root: bool=False):
    """
    🔄 Step4ファイル間転送機能 - 簡易マージモード
    ============================================
    
    【Step4での実際の使用パターン】
    この関数はlaunch/inference/merge.shから呼び出される際の主要エントリーポイントです。
    
    【引数の実際の意味】Step4コンテキストでの解釈:
    - source: Step2で生成されたスケルトンFBXファイル（例: bird.fbx）
    - target: ユーザーがアップロードしたオリジナルモデル（例: bird.glb）
    - output: Step4の最終出力FBXファイル（例: bird_merged.fbx）
    
    【処理の実体】3つのデータソース統合:
    1. sourceからAIスケルトンデータを抽出（arranged_bones, joints, tails等）
    2. targetからオリジナルメッシュを読み込み（形状・UV・テクスチャ保持）
    3. メモリ内のStep3スキニングデータを取得（skin weights）
    4. KDTreeマッチングで頂点数差異を吸収して統合
    
    【重要な技術的洞察】：
    - 「transfer」という名前だが実際は3つのデータソースの完全統合処理
    - オリジナルメッシュの見た目を保ったままAI生成の動作システムを移植
    - 頂点数が異なっても最近傍マッチングで確実に処理
    
    用途:
    - launch/inference/merge.sh からの直接呼び出し（Step4メイン処理）
    - 2つのFBXファイル＋メモリ内データの統合処理
    """
    # 🎯 転送処理の実行
    try:
        # ソースファイルからアーマチュアを抽出
        armature = load(filepath=source, return_armature=True)
        assert armature is not None
    except Exception as e:
        print(f"failed to load {source}")
        return
        
    # メッシュとアーマチュアデータの処理
    vertices, faces = process_mesh()
    arranged_bones = get_arranged_bones(armature)
    skin = get_skin(arranged_bones)
    joints, tails, parents, names, matrix_local = process_armature(armature, arranged_bones)
    
    # 最終マージ実行
    try:
        merge(
            path=target,
            output_path=output,
            vertices=vertices,
            joints=joints,
            skin=skin,
            parents=parents,
            names=names,
            tails=tails,
            add_root=add_root,
        )
        print(f"✅ Transfer完了: {output}")
        
        # 🛡️ SIGSEGVクラッシュ防止のための軽量終了処理
        try:
            print("✅ Transfer完了、プロセス終了準備中...")
            
            # 最小限のクリーンアップ（SIGSEGVを避けるため）
            if hasattr(bpy.context, 'scene'):
                try:
                    bpy.context.view_layer.objects.active = None
                except:
                    pass
            
            print("🔚 Transfer完了 - プロセス自然終了を待機...")
            # sys.exit(0)をコメントアウト - プロセスが自然終了するのを許可
            # import sys
            # sys.exit(0)
                
        except Exception as cleanup_e:
            print(f"⚠️ クリーンアップ中にエラーが発生しましたが、処理は完了しています: {cleanup_e}")
            
    except Exception as merge_e:
        print(f"❌ マージ処理中にエラーが発生: {merge_e}")
        raise

if __name__ == "__main__":
    """
    🚀 メインエントリーポイント
    ========================
    
    実行モード:
    1. 【ダイレクトモード】--source と --target が指定された場合
       → transfer()関数で直接ファイル間転送
       
    2. 【バッチモード】設定ファイルが指定された場合
       → 複数ファイルの一括処理
    
    使用例:
    # ダイレクトモード
    python -m src.inference.merge \
        --source skeleton.fbx \
        --target mesh.fbx \
        --output merged.fbx
    
    # バッチモード  
    python -m src.inference.merge \
        --data_config configs/data.yaml \
        --skeleton_config configs/skeleton.yaml \
        --skin_config configs/skin.yaml
    """
    args = parse()
    
    # 🎯 ダイレクトモード: 2ファイル間の直接転送
    if args.source is not None or args.target is not None:
        assert args.source is not None and args.target is not None
        transfer(args.source, args.target, args.output, args.add_root)
        exit()

    # 🎯 バッチモード: 設定ファイルベースの一括処理
    data_config     = Box(yaml.safe_load(open(args.data_config, "r")))
    skeleton_config = Box(yaml.safe_load(open(args.skeleton_config, "r")))
    skin_config     = Box(yaml.safe_load(open(args.skin_config, "r")))

    num_runs        = args.num_runs
    id              = args.id
    require_suffix  = args.require_suffix.split(',')
    merge_dir       = args.merge_dir
    merge_name      = args.merge_name
    add_root        = args.add_root

    input_dataset_dir   = data_config.input_dataset_dir
    dataset_name        = data_config.output_dataset_dir
    
    skin_output_dataset_dir = skin_config.writer.output_dir
    skin_name               = skin_config.writer.export_npz
    
    skeleton_output_dataset_dir = skeleton_config.writer.output_dir
    skeleton_name               = skeleton_config.writer.export_npz

    def make_path(output_dataset_dir, dataset_name, root, file_name):
        if output_dataset_dir is None:
            return os.path.join(
                dataset_name,
                os.path.relpath(root, input_dataset_dir),
                file_name,
            )
        return os.path.join(
            output_dataset_dir,
            dataset_name,
            os.path.relpath(root, input_dataset_dir),
            file_name,
        )

    # 処理対象ファイルの収集
    files = []
    for root, dirs, f in os.walk(input_dataset_dir):
        for file in f:
            if file.split('.')[-1] in require_suffix:
                file_name = file.removeprefix("./")
                suffix = file.split('.')[-1]
                # remove suffix
                file_name = '.'.join(file_name.split('.')[:-1])
                
                skin_path = make_path(skin_output_dataset_dir, dataset_name, root, os.path.join(file_name, skin_name+'.npz'))
                skeleton_path = make_path(skeleton_output_dataset_dir, dataset_name, root, os.path.join(file_name, skeleton_name+'.npz'))
                merge_path = make_path(merge_dir, dataset_name, root, os.path.join(file_name, merge_name+"."+suffix))
                
                # check if inference result exists
                if os.path.exists(skin_path) and os.path.exists(skeleton_path):
                    files.append((os.path.join(root, file), skin_path, skeleton_path, merge_path))

    # 🎯 並列処理のためのファイル分割
    num_files = len(files)
    print("num_files", num_files)
    gap = num_files // num_runs
    start = gap * id
    end = gap * (id + 1)
    if id+1==num_runs:
        end = num_files
    
    files = sorted(files)
    if end!=-1:
        files = files[:end]
        
    # 🎯 バッチマージ処理の実行
    tot = 0
    for file in tqdm(files[start:]):
        origin_file = file[0]
        skin_path = file[1]
        skeleton_path = file[2]
        merge_file = file[3]
        
        # NPZファイルからデータ読み込み
        raw_skin = RawSkin.load(path=skin_path)
        raw_data = RawData.load(path=skeleton_path)
        
        # マージ処理実行
        try:
            merge(
                path=origin_file,
                output_path=merge_file,
                vertices=raw_skin.vertices,
                joints=raw_skin.joints,
                skin=raw_skin.skin,
                parents=raw_data.parents,
                names=raw_data.names,
                tails=raw_data.tails,
                add_root=add_root,
                is_vrm=(raw_data.cls=='vroid'),
            )
        except Exception as e:
            print(f"failed to merge {origin_file}: {e}")
        
        tot += 1
    
    print(f"✅ マージ処理完了: {tot}ファイル処理済み")
    
    # 🛡️ SIGSEGVクラッシュ防止のための軽量終了処理
    try:
        print("✅ バッチマージ処理完了、プロセス終了準備中...")
        
        # 最小限のクリーンアップ（SIGSEGVを避けるため）
        if hasattr(bpy.context, 'scene'):
            try:
                bpy.context.view_layer.objects.active = None
            except:
                pass
        
        print("🔚 バッチマージ完了 - プロセス自然終了を待機...")
        # sys.exit(0)をコメントアウト - プロセスが自然終了するのを許可
        # import sys
        # sys.exit(0)
            
    except Exception as cleanup_e:
        print(f"⚠️ クリーンアップ中にエラーが発生しましたが、処理は完了しています: {cleanup_e}")
        # import sys
        # sys.exit(0)