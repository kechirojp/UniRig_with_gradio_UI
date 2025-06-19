---
applyTo: '**'
---

# UniRig Step4 マージ処理 技術的完全ガイド (2025年6月17日策定)

## 📋 Step4の本質的責務と技術的解明

### 🎯 Step4の正確な定義
**Step4 = 3つのデータソースの統合による完全なリギングシステム構築**

```
入力データソース (3つ):
├── 📦 オリジナルメッシュ: ユーザーアップロードファイル (例: bird.glb)
├── 🦴 AIスケルトン: Step2生成データ (joints, names, parents, tails)
└── 🎨 AIスキニング: Step3生成データ (vertices, skin weights)

出力:
└── 🎯 統合FBXファイル: 動かせる3Dモデル (例: bird_merged.fbx)
```

### 🔍 重要な技術的発見: 「transfer」の真の意味

**誤解されやすい命名**: `transfer(source, target, output)`
- **source**: スケルトンFBXファイル（Step2出力）
- **target**: **オリジナルメッシュファイル**（ユーザーアップロード）
- **output**: 統合済みFBXファイル（Step4出力）

**実際の処理**: 単純な転送ではなく **3つのデータソースの高度な統合**

## 🏗️ データフロー詳細解析

### 📊 入力ファイル構成の完全解明

#### 1. オリジナルメッシュファイル (target引数)
```python
# merge()関数内での処理
def merge(path: str, ...):  # path = target = "/app/uploads/bird.glb"
    load(path)  # Blenderシーンにオリジナルメッシュを読み込み
```

**技術的詳細**:
- **ファイル**: ユーザーがアップロードした元ファイル
- **役割**: メッシュ形状・UV座標・テクスチャ・マテリアルの提供元
- **頂点数**: 実際のモデル仕様（例: 5,742頂点）
- **座標系**: 実サイズ・実位置での座標

#### 2. AIスケルトンデータ (source引数)
```python
# transfer()関数内での処理
armature = load(filepath=source, return_armature=True)  # Step2のFBXから抽出
joints, tails, parents, names, matrix_local = process_armature(armature, arranged_bones)
```

**技術的詳細**:
- **ファイル**: Step2で生成されたスケルトンFBX（例: bird.fbx）
- **データ内容**: ボーン座標・親子関係・ボーン名・階層構造
- **特徴**: AI推論により生成された最適なボーン配置

#### 3. AIスキニングデータ (メモリ内)
```python
# transfer()関数内での処理
vertices, faces = process_mesh()  # Step3処理済みメッシュデータ
skin = get_skin(arranged_bones)   # Step3生成スキニングウェイト
```

**技術的詳細**:
- **データソース**: Step3で生成されたスキニング結果（NPZファイル由来）
- **データ内容**: 頂点ウェイト行列・ボーン影響度情報
- **頂点数**: AI処理用正規化メッシュ（例: 2,048頂点）
- **座標系**: 正規化された座標（-1〜1等）

### 🔧 頂点数差異吸収システムの技術的仕組み

#### 問題: 頂点数の不一致
```
AI処理頂点: 2,048個 (正規化座標、Step3スキニング処理済み)
実メッシュ頂点: 5,742個 (実サイズ座標、オリジナルモデル)
```

#### 解決: KDTree最近傍マッチングシステム

**Phase 1: 座標系統一**
```python
# denormalize_vertices()での処理
def denormalize_vertices(mesh_vertices, vertices, bones):
    # オリジナルメッシュのバウンディングボックス計算
    min_vals = np.min(mesh_vertices, axis=0)  # 実メッシュの最小座標
    max_vals = np.max(mesh_vertices, axis=0)  # 実メッシュの最大座標
    center = (min_vals + max_vals) / 2        # 中心点算出
    scale = np.max(max_vals - min_vals) / 2   # スケール算出
    
    # AI頂点を実メッシュサイズに変換
    denormalized_vertices = vertices * scale + center
    return denormalized_vertices, denormalized_bones
```

**Phase 2: KDTree構築と最近傍検索**
```python
# make_armature()での処理
tree = cKDTree(vertices)  # AI頂点（サイズ調整済み）でKDTree構築
_, index = tree.query(n_vertices)  # 各実頂点に最近傍AI頂点を検索
```

**Phase 3: ウェイト転写**
```python
# 各実メッシュ頂点にAIウェイトを適用
for v, co in enumerate(n_vertices):  # 実頂点ループ（5,742個）
    for ii in range(group_per_vertex):  # 最大4ボーン影響
        i = argsorted[index[v], ii]     # 最近傍AI頂点のウェイト順序
        # 実頂点vにAI頂点のウェイトを転写
        ob.vertex_groups[n].add([v], vertex_group_reweight[index[v], ii], 'REPLACE')
```

### 📈 効果と利点

#### ✅ 確実性
- **100%のカバレッジ**: 全ての実頂点がウェイト情報を取得
- **距離ベース**: 空間的に最も近いAI頂点のウェイトを使用
- **品質保証**: KDTreeにより最適なマッチングを保証

#### ✅ 柔軟性
- **頂点数無関係**: 実メッシュがAI想定より多くても少なくても対応
- **形状適応**: 複雑な形状でも空間的近さで適切にマッチング
- **スケール対応**: 任意のサイズのモデルに対応

## 🎯 実装における重要なポイント

### 🔧 処理順序の重要性
```python
# 必須順序
1. clean_bpy()                    # Blender環境クリーンアップ
2. load(path)                     # オリジナルメッシュ読み込み
3. denormalize_vertices()         # 座標系統一
4. make_armature()                # アーマチュア構築＋ウェイト転写
5. export                         # 最終FBX出力
```

### 🚨 避けるべき間違いパターン
```python
# ❌ 危険: 座標系変換の省略
vertices_raw = ai_vertices  # 正規化解除せずに使用 → 位置ずれ

# ❌ 危険: KDTree構築の順序間違い
tree = cKDTree(mesh_vertices)  # 実頂点でツリー構築 → マッチング失敗

# ❌ 危険: ウェイト正規化の省略
skin_weights_raw = raw_weights  # 正規化なし → ウェイト合計が1にならない
```

### ✅ 正しい実装パターン
```python
# ✅ 正しい: 完全な統合フロー
def step4_integration():
    # 1. 3つのデータソース準備
    original_mesh = load_original_file(user_upload)
    ai_skeleton = load_skeleton_data(step2_output)
    ai_skinning = load_skinning_data(step3_output)
    
    # 2. 座標系統一
    unified_vertices, unified_bones = denormalize_coordinates(
        original_mesh.vertices, ai_skinning.vertices, ai_skeleton.bones
    )
    
    # 3. KDTreeマッチング＋ウェイト転写
    merged_model = merge_with_kdtree_matching(
        original_mesh, unified_vertices, unified_bones, ai_skinning.weights
    )
    
    # 4. 最終出力
    export_fbx(merged_model, output_path)
```

## 📋 Step4品質保証ガイドライン

### 🔍 検証ポイント
1. **入力データ整合性**: 3つのデータソースが全て存在し有効
2. **座標系変換**: AI頂点が実メッシュサイズに正しく調整済み
3. **KDTreeマッチング**: 全実頂点に対して適切なAI頂点がマッチング
4. **ウェイト正規化**: 各頂点のウェイト合計が1.0
5. **ボーン階層**: 親子関係が正しく構築
6. **FBX出力**: バイナリ形式での正常出力

### ⚠️ 品質問題の兆候
- **頂点ウェイト0**: KDTreeマッチング失敗
- **異常な変形**: 座標系変換エラー
- **ボーン位置ずれ**: denormalization失敗
- **FBXロードエラー**: ASCII/バイナリ形式問題

## 🚀 Step4最適化戦略

### 🎯 性能向上
- **KDTree構築**: 一度だけ構築、複数メッシュで再利用
- **ウェイト正規化**: vectorize演算で高速化
- **メモリ管理**: 大容量メッシュでのチャンク処理

### 🛡️ 安定性向上
- **エラーハンドリング**: 各段階での検証とフォールバック
- **プロセス分離**: Blender実行の独立プロセス化
- **状態管理**: 中間結果の保存とリカバリ機能

---

## 📝 実装チェックリスト

### ✅ 必須実装項目
- [ ] 3つのデータソース読み込み機能
- [ ] 座標系統一処理（denormalize_vertices）
- [ ] KDTree最近傍マッチングシステム
- [ ] ウェイト正規化・転写機能
- [ ] バイナリFBXエクスポート
- [ ] エラーハンドリング・検証機能

### ✅ 品質保証項目
- [ ] 頂点数差異への対応確認
- [ ] 複数モデルでの動作検証
- [ ] メモリ使用量の最適化
- [ ] 処理時間の合理性確認
- [ ] 出力FBXの互換性検証

---

**重要**: Step4は単純なファイル転送ではなく、3つの異なるデータソースを空間的・論理的に統合する高度な3D処理技術です。KDTreeマッチングによる頂点数差異吸収が、この技術の核心的価値を提供しています。
