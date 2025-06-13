# UniRig Merge処理フロー詳細分析

## 📋 概要

`launch/inference/merge.sh`は、スケルトン・スキンウェイトのマージ処理に加えて、**高度なテクスチャ保持・復元システム**を含む、産業レベルの包括的3Dモデル統合システムです。

**予想の検証結果**: 
- ✅ **スケルトン・スキンウェイトのマージ**: 確認済み
- ✅ **テクスチャ保持・復元システム**: 発見された主要機能
- ✅ **Linear Blend Skinning (LBS)**: 実装確認
- ✅ **KDTree最適化**: 方向補正システム確認

## 🎯 merge.shの基本構造

```bash
python -m src.inference.merge \
    --require_suffix=$require_suffix \
    --num_runs=1 \
    --id=0 \
    --source=$source \      # オリジナルモデル（テクスチャ付き）
    --target=$target \      # スキニング済みモデル（テクスチャなし）
    --output=$output        # 最終出力FBX
```

**キー理解**: `source`がテクスチャ情報を提供し、`target`がスキンウェイトを提供します。

## 🔄 処理段階の詳細

### 段階1: データ抽出・構造化

#### 1.1 スケルトンデータ抽出
```python
# sourceからアーマチュア（スケルトン）を抽出
armature = load(filepath=source, return_armature=True)
arranged_bones = get_arranged_bones(armature)
joints, tails, parents, names, matrix_local = process_armature_for_merge(armature, arranged_bones)
```

**抽出される情報:**
- **joints**: ボーンの開始位置（3D座標）
- **tails**: ボーンの終点位置（3D座標）
- **parents**: ボーンの親子関係（階層構造）
- **names**: ボーン名リスト
- **matrix_local**: ローカル変換マトリックス

#### 1.2 メッシュデータ処理
```python
# targetのメッシュデータを処理
vertices, faces = process_mesh_for_merge()
```

**処理内容:**
- 頂点座標の抽出と正規化
- フェース（面）情報の構造化
- メッシュのワールド座標変換

### 段階2: スキンウェイト計算

#### 2.1 既存ウェイト解析
```python
skin = get_skin(arranged_bones)
```

**処理詳細:**
```python
def get_skin(arranged_bones):
    # 各メッシュオブジェクトから頂点グループを抽出
    for obj in meshes:
        skin_weight = np.zeros((total_vertices, total_bones))
        for bone in arranged_bones:
            # 既存の頂点グループウェイトを取得
            gidx = obj.vertex_groups[bone.name].index
            bone_verts = [v for v in obj_verts if gidx in [g.group for g in v.groups]]
            for v in bone_verts:
                w = v.groups[which[0]].weight
                skin_weight[v.index, index[bone.name]] = w
    return skin
```

#### 2.2 ウェイト正規化
- 各頂点の総ウェイト値を1.0に正規化
- 最大4つのボーンまでの影響を考慮
- 無効なウェイト値（NaN等）の処理

### 段階3: アーマチュア構築・統合

#### 3.1 基本マージ処理
```python
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
```

#### 3.2 アーマチュア生成
```python
def make_armature(vertices, bones, parents, names, skin, group_per_vertex=4):
```

**処理内容:**
1. **ボーン生成**: 各ジョイントにボーンオブジェクトを作成
2. **階層設定**: parent配列に基づいてボーン階層を構築
3. **頂点グループ作成**: 各ボーンに対応する頂点グループを生成
4. **ウェイト適用**: 計算されたスキンウェイトを頂点グループに適用
5. **親子関係設定**: メッシュオブジェクトをアーマチュアに親子付け

#### 3.3 座標系補正
```python
vertices, bones = get_correct_orientation_kdtree(vertices, mesh_vertices, bones)
```

- KDTreeを使用した頂点位置の最適化
- ボーン方向の補正
- ワールド座標系での整合性確保

### 段階4: テクスチャ統合システム

#### 4.1 テクスチャ保持機能
```python
# マテリアル情報の保存
stored_materials = {}
stored_images = {}
mesh_material_assignments = {}

# 全てのマテリアルとテクスチャを保持
for mat in bpy.data.materials:
    stored_materials[mat.name] = mat
for img in bpy.data.images:
    stored_images[img.name] = img
```

#### 4.2 段階的テクスチャ復元

##### 優先度1: ImprovedSafeTextureRestoration
```python
if IMPROVED_SAFE_TEXTURE_RESTORATION_AVAILABLE and output.endswith('.fbx'):
    # YAML manifest検索
    yaml_manifest_path = find_yaml_manifest(source)
    if yaml_manifest_path:
        improved_safe_flow = ImprovedSafeTextureRestoration(
            working_dir=base_working_dir,
            model_name=model_name,
            use_subprocess=True
        )
        success, final_fbx_path, quality_report = improved_safe_flow.execute_full_restoration(
            skinned_fbx_path=output
        )
```

##### フォールバック: LegacySafeTextureRestoration
```python
elif SAFE_TEXTURE_RESTORATION_AVAILABLE and output.endswith('.fbx'):
    # JSON metadata検索
    metadata_json_path = find_json_metadata(source)
    if metadata_json_path:
        safe_flow = SafeTextureRestoration(output_dir)
        safe_result = safe_flow.process_skinned_fbx(
            skinned_fbx_path=output,
            metadata_json_path=metadata_json_path,
            texture_dir=texture_dir,
            model_name=model_name
        )
```

#### 4.3 マテリアルノード復元
```python
def restore_material_nodes(material):
    # Base Color, Normal, Roughnessテクスチャの自動識別
    base_color_textures = identify_base_color_textures(material)
    normal_textures = identify_normal_textures(material)
    roughness_textures = identify_roughness_textures(material)
    
    # Principled BSDFへの接続復元
    if base_color_textures:
        # Mix nodeを使用したブレンド接続
        links.new(base_color_node.outputs['Color'], mix_node.inputs['A'])
        links.new(color_attr_node.outputs['Color'], mix_node.inputs['B'])
        links.new(mix_node.outputs['Result'], principled_node.inputs['Base Color'])
    
    if normal_textures:
        # Normal Map nodeを介した接続
        links.new(normal_texture_node.outputs['Color'], normal_map_node.inputs['Color'])
        links.new(normal_map_node.outputs['Normal'], principled_node.inputs['Normal'])
    
    if roughness_textures:
        # Separate Color nodeを使用した多チャンネル接続
        links.new(roughness_node.outputs['Color'], separate_node.inputs['Color'])
        links.new(separate_node.outputs['Green'], principled_node.inputs['Roughness'])
        links.new(separate_node.outputs['Blue'], math_node.inputs['Value'])
        links.new(math_node.outputs['Value'], principled_node.inputs['Metallic'])
```

### 段階5: 最終出力

#### 5.1 FBXエクスポート設定
```python
bpy.ops.export_scene.fbx(
    filepath=output_path,
    use_selection=False,  # 全オブジェクトをエクスポート
    add_leaf_bones=True,  # リーフボーンを追加
    path_mode='COPY',     # テクスチャをコピー
    embed_textures=True,  # テクスチャを埋め込み
    use_mesh_modifiers=True,  # モディファイアを適用
    use_custom_props=True,    # カスタムプロパティを保持
    mesh_smooth_type='OFF',   # 元のスムージングを保持
    use_tspace=True,          # タンジェント空間を使用
    bake_anim=False          # アニメーションをベイクしない
)
```

#### 5.2 品質検証
- ファイルサイズの確認
- テクスチャ埋め込みの検証
- マテリアル接続の整合性チェック
- ボーン階層の正確性確認

## 🎨 テクスチャ処理の高度な機能

### テクスチャタイプ自動識別
```python
def identify_texture_type(node, image_name, color_space):
    image_name = image_name.lower()
    
    # Base Color識別（sRGB色空間 + 名前パターン）
    if (color_space == 'sRGB' and 
        ('col' in image_name or 'bc' in image_name or 
         'base' in image_name or 'diffuse' in image_name)):
        return 'BASE_COLOR'
    
    # Normal Map識別（Non-Color + 名前パターン）
    elif (color_space == 'Non-Color' and 
          ('nrml' in image_name or 'normal' in image_name)):
        return 'NORMAL'
    
    # Roughness識別（Non-Color + 名前パターン）
    elif (color_space == 'Non-Color' and 
          ('rough' in image_name or 'metallic' in image_name)):
        return 'ROUGHNESS'
```

### マテリアルノード構造の保持
- Shader Editor内のノード接続を完全に保持
- テクスチャの色空間設定を維持
- カスタムノードグループの対応
- UVマッピング情報の保持

## 📊 出力結果

### 最終生成物
1. **完全にリギング済みのFBXファイル**
   - アーマチュア（ボーン構造）
   - スキンウェイト（頂点とボーンの結合情報）
   - オリジナルテクスチャ（材質情報）
   - アニメーション対応構造

2. **テクスチャアセット**
   - 埋め込まれたテクスチャファイル
   - マテリアル定義
   - UV座標マッピング

3. **品質保証データ**
   - ファイルサイズ情報
   - テクスチャ数と総サイズ
   - 処理ログと検証結果

## 🔧 技術的特徴

### Linear Blend Skinning (LBS)
```python
def linear_blend_skinning(vertex, matrix_local, matrix, skin):
    # 各ボーンの変換マトリックスを重み付き平均
    weighted_per_bone_matrix = skin.transpose(1, 2).unsqueeze(2) * per_bone_matrix
    g = weighted_per_bone_matrix.sum(dim=1)
    final = g[:, 0:3, :] / (skin.transpose(1, 2).sum(dim=1) + 1e-8).unsqueeze(1)
    return final.permute(0, 2, 1)
```

### KDTree最適化
- 頂点とボーンの最適な対応関係を計算
- 空間的に近いボーンへの重み付けを優先
- 計算効率の向上

### メモリ管理
- Blenderデータブロックの適切なクリーンアップ
- テクスチャの重複排除
- プロセス分離による安定性確保

## 🚨 重要な注意点

### ファイル命名規則
- `{model_name}.fbx`: スケルトンファイル（Step2出力）
- `predict_skeleton.npz`: スケルトンデータ（固定名）
- `{model_name}_textured.fbx`: 最終出力ファイル

### 処理順序の重要性
1. スケルトン抽出 → メッシュ処理 → ウェイト計算 → マージ → テクスチャ統合
2. 各段階での検証とフォールバック処理
3. エラー時の安全な復旧機能

### 互換性要件
- Blender 4.2 API準拠
- UniRigコアスクリプトとの完全互換性
- FBXフォーマットの業界標準準拠

## 🎯 結論

`launch/inference/merge.sh`は単純なマージ処理ではなく、**産業レベルの3Dリギングパイプライン**の最終工程を担う包括的なシステムです。スケルトン統合、スキンウェイト計算、高度なテクスチャ保持・復元、アニメーション対応構造生成を一括して処理し、完全にリギング済みの3Dモデルを出力します。
