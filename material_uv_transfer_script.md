# Blender マテリアル・UVマップ移植スクリプト

## 概要

このスクリプトは、Blenderで一つのオブジェクトのマテリアルとUVマップを別のオブジェクトに移植するためのPythonスクリプトです。テクスチャとUVマッピングの設定を簡単にコピーできます。

## 機能

- ✅ **マテリアルの完全移植**：シェーダーノード、テクスチャ、設定値をすべて移植
- ✅ **UVマップの完全移植**：UV座標データとアクティブ設定を移植
- ✅ **上書き動作**：ターゲットオブジェクトの既存データを完全に置き換え
- ✅ **独立処理**：マテリアルまたはUVマップのどちらか一方だけでも移植可能
- ✅ **エラーハンドリング**：オブジェクトが見つからない場合の適切な処理

## 使用方法

### 基本的な使用

```python
# スクリプトをBlenderで実行
exec(open(r'd:\Blender_script\blender_script.py').read())
```

### カスタム使用

```python
import bpy

# 関数を直接呼び出し
success = transfer_materials_and_uvmaps("ソースオブジェクト名", "ターゲットオブジェクト名")

if success:
    print("移植完了")
else:
    print("移植失敗")
```

## 関数リファレンス

### `transfer_materials_and_uvmaps(source_name, target_name)`

ソースオブジェクトのマテリアルとUVマップをターゲットオブジェクトに移植します。

**パラメータ:**
- `source_name` (str): 移植元オブジェクトの名前
- `target_name` (str): 移植先オブジェクトの名前

**戻り値:**
- `bool`: 移植が成功した場合は `True`、失敗した場合は `False`

**処理フロー:**
1. オブジェクトの存在確認
2. マテリアルの移植（存在する場合）
3. UVマップの移植（存在する場合）
4. 成功/失敗の判定

## 使用されているBlender Python API

### オブジェクト取得
```python
bpy.data.objects.get(object_name)
```
- **説明**: 指定した名前のオブジェクトを取得
- **戻り値**: オブジェクトまたは `None`

### マテリアル操作

#### `obj.data.materials.clear()`
- **説明**: オブジェクトのすべてのマテリアルスロットをクリア
- **用途**: 既存マテリアルの完全削除

#### `obj.data.materials.append(material)`
- **説明**: オブジェクトにマテリアルを追加
- **パラメータ**: マテリアルオブジェクトまたは `None`

#### `len(obj.data.materials)`
- **説明**: オブジェクトのマテリアル数を取得
- **戻り値**: 整数

### UVマップ操作

#### `obj.data.uv_layers`
- **説明**: オブジェクトのUVマップコレクション
- **操作**: 反復処理、追加、削除が可能

#### `obj.data.uv_layers.remove(uv_layer)`
- **説明**: 指定したUVマップを削除
- **パラメータ**: UVマップオブジェクト

#### `obj.data.uv_layers.new(name)`
- **説明**: 新しいUVマップを作成
- **パラメータ**: UVマップの名前
- **戻り値**: 新しいUVマップオブジェクト

#### `obj.data.uv_layers.active`
- **説明**: アクティブなUVマップを取得/設定
- **取得**: 現在アクティブなUVマップ
- **設定**: 指定したUVマップをアクティブに設定

#### `uv_layer.data[index].uv`
- **説明**: 特定のループのUV座標を取得/設定
- **形式**: (U, V) の2Dベクトル

### メッシュデータ操作

#### `obj.data.loops`
- **説明**: メッシュのループ（面を構成する頂点）のコレクション
- **用途**: UV座標のインデックス範囲確認

#### `len(obj.data.loops)`
- **説明**: メッシュのループ数を取得
- **戻り値**: 整数

## 実行例

```python
# bear_boyのマテリアルとUVマップをbear_boy.001に移植
success = transfer_materials_and_uvmaps("bear_boy", "bear_boy.001")

# 出力例:
# ソースオブジェクト 'bear_boy' を確認
# ターゲットオブジェクト 'bear_boy.001' を確認
# ソースオブジェクトのマテリアル数: 1
# ターゲットオブジェクトの既存マテリアル数: 1
# ターゲットオブジェクトの既存マテリアルをクリアしました
# マテリアル 'Material.001' を bear_boy.001 に追加しました
# マテリアル移植完了: bear_boy → bear_boy.001
# ソースオブジェクトのUVマップ数: 1
# ターゲットオブジェクトの既存UVマップ数: 1
# ターゲットオブジェクトの既存UVマップをクリアしました
# UVマップ 'UVMap' を bear_boy.001 に追加しました
# アクティブUVマップを 'UVMap' に設定しました
# UVマップ移植完了: bear_boy → bear_boy.001
# ✅ マテリアルとUVマップの移植が正常に完了しました
```

## 注意事項

### 前提条件
- ソースとターゲットのオブジェクトが同じトポロジー（同じ頂点・面構造）である必要があります
- 異なるトポロジーの場合、UVマップのコピーが正常に動作しない可能性があります

### データの上書き
- ターゲットオブジェクトの既存マテリアルとUVマップは**完全に削除**されます
- 元のデータを保持したい場合は、事前にバックアップを作成してください

### エラーケース
- オブジェクトが見つからない場合は処理を停止し、エラーメッセージを表示
- ソースオブジェクトにマテリアル/UVマップがない場合は、該当する処理をスキップ

## ファイル情報

- **ファイル名**: `blender_script.py`
- **場所**: `d:\Blender_script\`
- **実行環境**: Blender内のPython環境
- **依存関係**: `bpy`モジュール（Blender標準）

## バージョン履歴

- **v1.0**: マテリアル移植機能
- **v2.0**: UVマップ移植機能を追加
- **v2.1**: 独立処理とエラーハンドリングを改善

---

## FBX保存時の注意点

### マテリアル・テクスチャの互換性

#### **推奨設定**
```python
# FBXエクスポート時の重要設定
bpy.ops.export_scene.fbx(
    filepath="output.fbx",
    use_selection=False,          # 全オブジェクトをエクスポート
    use_active_collection=False,
    global_scale=1.0,
    apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_NONE',
    
    # マテリアル関連
    use_mesh_modifiers=True,      # モディファイアを適用
    use_mesh_edges=False,
    use_tspace=True,              # タンジェントスペースを計算
    
    # テクスチャ関連
    path_mode='COPY',             # テクスチャファイルをコピー
    embed_textures=True,          # テクスチャを埋め込み（推奨）
    
    # アニメーション関連
    use_anim=True,
    use_anim_action_all=True,
    use_default_take=True,
    use_anim_optimize=True,
    anim_optimize_precision=6.0,
    
    # その他
    axis_forward='-Z',
    axis_up='Y',
)
```

#### **テクスチャの互換性問題**
- **Image Texture**: ✅ 基本的なテクスチャは保持
- **Procedural Texture**: ❌ ノイズ、グラデーション等は失われる
- **Normal Map**: ⚠️ 設定によっては正しく転送されない
- **Custom Nodes**: ❌ 完全に失われる

#### **マテリアルプロパティの対応**
```
Principled BSDF → FBX材質
├─ Base Color → Diffuse Color ✅
├─ Metallic → Metallic Factor ✅
├─ Roughness → Roughness Factor ✅
├─ Normal → Normal Map ⚠️
├─ Emission → Emissive ✅
└─ Alpha → Transparency ⚠️
```

### UVマップの互換性

#### **保持されるUVデータ**
- 第1UVマップ（通常「UVMap」）: ✅ 確実に保持
- 第2UVマップ以降: ⚠️ アプリケーション依存
- アクティブUVマップ設定: ❌ 失われる可能性

#### **推奨UVマップ構成**
```python
# エクスポート前にUVマップを整理
def prepare_uvmaps_for_fbx(obj_name):
    obj = bpy.data.objects.get(obj_name)
    if obj and obj.data.uv_layers:
        # 最重要なUVマップを最初に配置
        main_uv = obj.data.uv_layers.get("UVMap") or obj.data.uv_layers[0]
        obj.data.uv_layers.active = main_uv
        print(f"アクティブUVマップ: {main_uv.name}")
```

### 互換性を高めるベストプラクティス

#### **エクスポート前の準備**
1. **テクスチャの埋め込み**
   ```python
   # 外部テクスチャをBlenderファイルに埋め込み
   for img in bpy.data.images:
       if img.filepath and not img.packed_file:
           img.pack()
   ```

2. **UVマップ名の英語化**
   ```python
   # 日本語UVマップ名を英語に変更
   for obj in bpy.data.objects:
       if obj.type == 'MESH' and obj.data.uv_layers:
           for uv in obj.data.uv_layers:
               if not uv.name.isascii():
                   uv.name = "UV_Map"
   ```

3. **シンプルなマテリアル構成**
   - Principled BSDFのみ使用
   - 複雑なノードグループは避ける
   - 必要に応じて事前にベイク処理

### 他のアプリケーションでの確認事項

#### **Unity**
- マテリアルは手動で再設定が必要
- UVマップは通常保持される
- テクスチャパスの確認が必要

#### **Unreal Engine**
- FBX + テクスチャファイルの組み合わせ推奨
- マテリアルは自動インポートされる
- UV Channelの確認が必要

#### **Maya/3ds Max**
- マテリアルの基本プロパティは保持
- 複雑なシェーダーは再作成が必要
- UVマップは通常問題なし

### トラブルシューティング

#### **よくある問題と対処法**
1. **テクスチャが表示されない**
   - テクスチャファイルの存在確認
   - パスの相対/絶対設定確認
   - `embed_textures=True`でエクスポート

2. **マテリアルが真っ白**
   - Principled BSDFの使用確認
   - Base Colorの接続確認
   - アルファ値の確認

3. **UVマップが崩れる**
   - エクスポート前のUVマップ確認
   - アクティブUVマップの設定
   - UV座標の範囲確認（0-1）