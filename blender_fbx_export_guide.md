# Blender FBXエクスポート・テクスチャ埋め込み完全ガイド

## 概要

このドキュメントは、Blenderからの高品質なFBXエクスポートとテクスチャ埋め込みに関する包括的なガイドです。マテリアル・UVマップ移植スクリプトと組み合わせて使用することで、他の3Dソフトウェアとの互換性を最大化できます。

## 目次

1. [FBXエクスポートの基本](#fbxエクスポートの基本)
2. [テクスチャ埋め込み技術](#テクスチャ埋め込み技術)
3. [マテリアル・UVマップの互換性](#マテリアルuvマップの互換性)
4. [実装コード集](#実装コード集)
5. [他ソフトウェアとの互換性](#他ソフトウェアとの互換性)
6. [トラブルシューティング](#トラブルシューティング)
7. [ベストプラクティス](#ベストプラクティス)

## FBXエクスポートの基本

### 推奨エクスポート設定

```python
def export_fbx_standard(filepath, embed_textures=True):
    """標準的なFBXエクスポート設定"""
    bpy.ops.export_scene.fbx(
        filepath=filepath,
        
        # 基本設定
        use_selection=False,          # 全オブジェクトをエクスポート
        use_active_collection=False,
        global_scale=1.0,
        apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_NONE',
        
        # メッシュ関連
        use_mesh_modifiers=True,      # モディファイアを適用
        use_mesh_edges=False,
        use_tspace=True,              # タンジェントスペースを計算
        
        # テクスチャ関連（重要）
        path_mode='COPY',             # テクスチャファイルをコピー
        embed_textures=embed_textures, # テクスチャを埋め込み
        
        # アニメーション関連
        use_anim=True,
        use_anim_action_all=True,
        use_default_take=True,
        use_anim_optimize=True,
        anim_optimize_precision=6.0,
        
        # 座標系（Unity/Unreal対応）
        axis_forward='-Z',
        axis_up='Y',
    )
    print(f"✅ FBXエクスポート完了: {filepath}")
```

### エクスポートパラメータ詳細解説

| パラメータ | 説明 | 推奨値 | 理由 |
|-----------|------|--------|------|
| `embed_textures` | テクスチャをFBXファイル内に埋め込み | `True` | 単一ファイルで完結 |
| `path_mode` | テクスチャファイルの処理方法 | `'COPY'` | 確実にテクスチャを保持 |
| `use_tspace` | タンジェントスペースの計算 | `True` | 法線マップの正確な表示 |
| `use_mesh_modifiers` | モディファイアの適用 | `True` | 最終形状をエクスポート |
| `apply_unit_scale` | 単位スケールの適用 | `True` | 他ソフトでの正確なサイズ |

## テクスチャ埋め込み技術

### Blenderファイルへのテクスチャ埋め込み

```python
def pack_all_textures():
    """すべての外部テクスチャをBlenderファイルに埋め込み"""
    packed_count = 0
    failed_count = 0
    
    print("=== テクスチャ埋め込み開始 ===")
    
    for img in bpy.data.images:
        if img.type != 'IMAGE':
            continue
            
        if img.filepath and not img.packed_file:
            try:
                img.pack()
                print(f"✅ 埋め込み成功: {img.name}")
                packed_count += 1
            except Exception as e:
                print(f"❌ 埋め込み失敗: {img.name} - {str(e)}")
                failed_count += 1
        elif img.packed_file:
            print(f"📦 既に埋め込み済み: {img.name}")
    
    print(f"\n=== 結果 ===")
    print(f"埋め込み成功: {packed_count}")
    print(f"埋め込み失敗: {failed_count}")
    print(f"=============")
    
    return packed_count
```

### テクスチャ状況の詳細確認

```python
def check_texture_status():
    """テクスチャの詳細状況を確認・レポート"""
    print("=== テクスチャ状況レポート ===")
    
    total_images = 0
    packed_images = 0
    external_images = 0
    missing_images = 0
    
    for img in bpy.data.images:
        if img.type != 'IMAGE':
            continue
            
        total_images += 1
        print(f"\n📄 {img.name}")
        
        if img.packed_file:
            packed_images += 1
            print(f"   状態: 🟢 埋め込み済み")
            print(f"   サイズ: {len(img.packed_file.data)} bytes")
        elif img.filepath:
            external_images += 1
            import os
            if os.path.exists(bpy.path.abspath(img.filepath)):
                print(f"   状態: 🟡 外部ファイル（存在）")
                print(f"   パス: {img.filepath}")
            else:
                missing_images += 1
                print(f"   状態: 🔴 外部ファイル（見つからない）")
                print(f"   パス: {img.filepath}")
        else:
            print(f"   状態: ⚪ 生成テクスチャ")
        
        print(f"   解像度: {img.size[0]} x {img.size[1]}")
        print(f"   カラースペース: {img.colorspace_settings.name}")
    
    print(f"\n=== サマリー ===")
    print(f"総テクスチャ数: {total_images}")
    print(f"埋め込み済み: {packed_images}")
    print(f"外部ファイル: {external_images}")
    print(f"見つからない: {missing_images}")
    
    if missing_images > 0:
        print(f"\n⚠️  {missing_images} 個のテクスチャファイルが見つかりません")
        print("FBXエクスポート前に問題を解決してください")
    
    return {
        'total': total_images,
        'packed': packed_images,
        'external': external_images,
        'missing': missing_images
    }
```

### 埋め込み可能なテクスチャの種類

#### ✅ 埋め込み可能

- **Image Texture ノード**: PNG, JPEG, TIFF, TGA, BMP等
- **HDR/EXR**: 環境マップやHDRI画像
- **手動でインポートした画像**: ファイル > インポート > 画像
- **生成済みテクスチャ**: レンダリング結果等

#### ❌ 埋め込み不可

- **プロシージャルテクスチャ**: Noise, Gradient, Magic等のノード
- **Blender固有ノード**: ColorRamp, MixRGB等の複雑な設定
- **アニメーション画像**: 動画ファイルやシーケンス

```python
def analyze_material_nodes():
    """マテリアルノードの互換性を分析"""
    print("=== マテリアルノード互換性レポート ===")
    
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue
            
        print(f"\n🎨 マテリアル: {mat.name}")
        
        compatible_nodes = []
        incompatible_nodes = []
        
        for node in mat.node_tree.nodes:
            if node.type == 'TEX_IMAGE':
                if node.image:
                    compatible_nodes.append(f"Image Texture: {node.image.name}")
                else:
                    incompatible_nodes.append("Image Texture: 画像未設定")
            elif node.type in ['TEX_NOISE', 'TEX_GRADIENT', 'TEX_MAGIC', 'TEX_MUSGRAVE']:
                incompatible_nodes.append(f"Procedural: {node.type}")
            elif node.type == 'BSDF_PRINCIPLED':
                compatible_nodes.append("Principled BSDF")
            elif node.type in ['MIX_RGB', 'VALTORGB', 'MAPPING']:
                incompatible_nodes.append(f"Complex: {node.type}")
        
        print(f"   ✅ 互換ノード: {len(compatible_nodes)}")
        for node in compatible_nodes:
            print(f"      - {node}")
            
        print(f"   ❌ 非互換ノード: {len(incompatible_nodes)}")
        for node in incompatible_nodes:
            print(f"      - {node}")
```

## マテリアル・UVマップの互換性

### Principled BSDF → FBX マッピング

```text
Blender Principled BSDF     →  FBX Material Property
├─ Base Color              →  Diffuse Color ✅
├─ Metallic                →  Metallic Factor ✅
├─ Roughness               →  Roughness Factor ✅
├─ Normal                  →  Normal Map ⚠️ (設定要確認)
├─ Emission                →  Emissive ✅
├─ Alpha                   →  Transparency ⚠️ (アプリ依存)
├─ Subsurface              →  未対応 ❌
├─ Transmission            →  未対応 ❌
└─ Clearcoat               →  未対応 ❌
```

### UVマップの互換性

```python
def prepare_uvmaps_for_export(obj_name):
    """エクスポート用にUVマップを最適化"""
    obj = bpy.data.objects.get(obj_name)
    if not obj or obj.type != 'MESH':
        return False
    
    uv_layers = obj.data.uv_layers
    if not uv_layers:
        print(f"⚠️  {obj_name} にUVマップがありません")
        return False
    
    # 第1UVマップを最重要として設定
    main_uv = uv_layers.get("UVMap") or uv_layers[0]
    uv_layers.active = main_uv
    
    print(f"✅ {obj_name} のメインUVマップ: {main_uv.name}")
    
    # UVマップ名を英語に変更（互換性向上）
    for i, uv_layer in enumerate(uv_layers):
        old_name = uv_layer.name
        if not old_name.isascii():
            uv_layer.name = f"UV_Channel_{i}"
            print(f"🔄 UVマップ名変更: {old_name} → {uv_layer.name}")
    
    return True
```

### マテリアル互換性の向上

```python
def optimize_materials_for_fbx():
    """FBX互換性を高めるためのマテリアル最適化"""
    print("=== マテリアル最適化開始 ===")
    
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue
            
        print(f"\n🎨 最適化中: {mat.name}")
        
        # Principled BSDFを探す
        principled = None
        for node in mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                principled = node
                break
        
        if not principled:
            print("   ⚠️  Principled BSDFが見つかりません")
            continue
        
        # アルファブレンドモードの設定
        if principled.inputs['Alpha'].default_value < 1.0:
            mat.blend_method = 'BLEND'
            print("   🔧 アルファブレンドを有効化")
        
        # メタリック値の最適化（0 or 1 推奨）
        metallic = principled.inputs['Metallic'].default_value
        if 0.1 < metallic < 0.9:
            principled.inputs['Metallic'].default_value = 1.0 if metallic > 0.5 else 0.0
            print(f"   🔧 メタリック値を最適化: {metallic:.2f} → {principled.inputs['Metallic'].default_value}")
        
        print("   ✅ 最適化完了")
```

## 実装コード集

### 完全版FBXエクスポート関数

```python
def export_fbx_complete(filepath, objects_to_export=None, quality_mode='HIGH'):
    """
    包括的なFBXエクスポート関数
    
    Args:
        filepath (str): 出力ファイルパス
        objects_to_export (list): エクスポートするオブジェクト名のリスト（Noneで全て）
        quality_mode (str): 品質モード ('HIGH', 'MEDIUM', 'FAST')
    """
    
    print(f"=== FBXエクスポート開始 ({quality_mode}モード) ===")
    
    # 1. 事前チェック
    status = check_texture_status()
    if status['missing'] > 0:
        print("⚠️  見つからないテクスチャがあります。続行しますか？")
    
    # 2. テクスチャの準備
    if quality_mode in ['HIGH', 'MEDIUM']:
        print("\n📦 テクスチャを埋め込み中...")
        pack_all_textures()
    
    # 3. マテリアルの最適化
    if quality_mode == 'HIGH':
        print("\n🎨 マテリアルを最適化中...")
        optimize_materials_for_fbx()
    
    # 4. UVマップの準備
    if objects_to_export:
        for obj_name in objects_to_export:
            prepare_uvmaps_for_export(obj_name)
    else:
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                prepare_uvmaps_for_export(obj.name)
    
    # 5. 選択状態の管理
    if objects_to_export:
        bpy.ops.object.select_all(action='DESELECT')
        exported_objects = []
        for obj_name in objects_to_export:
            obj = bpy.data.objects.get(obj_name)
            if obj:
                obj.select_set(True)
                exported_objects.append(obj_name)
        print(f"📋 エクスポート対象: {exported_objects}")
        use_selection = True
    else:
        use_selection = False
        print("📋 エクスポート対象: 全オブジェクト")
    
    # 6. 品質設定
    quality_settings = {
        'HIGH': {
            'embed_textures': True,
            'use_mesh_modifiers': True,
            'anim_optimize_precision': 6.0,
            'use_tspace': True
        },
        'MEDIUM': {
            'embed_textures': True,
            'use_mesh_modifiers': True,
            'anim_optimize_precision': 4.0,
            'use_tspace': False
        },
        'FAST': {
            'embed_textures': False,
            'use_mesh_modifiers': False,
            'anim_optimize_precision': 2.0,
            'use_tspace': False
        }
    }
    
    settings = quality_settings[quality_mode]
    
    # 7. FBXエクスポート実行
    print(f"\n📤 FBXエクスポート実行中...")
    
    try:
        bpy.ops.export_scene.fbx(
            filepath=filepath,
            
            # 基本設定
            use_selection=use_selection,
            use_active_collection=False,
            global_scale=1.0,
            apply_unit_scale=True,
            apply_scale_options='FBX_SCALE_NONE',
            
            # メッシュ関連
            use_mesh_modifiers=settings['use_mesh_modifiers'],
            use_mesh_edges=False,
            use_tspace=settings['use_tspace'],
            
            # テクスチャ関連
            embed_textures=settings['embed_textures'],
            path_mode='COPY',
            
            # アニメーション関連
            use_anim=True,
            use_anim_action_all=True,
            use_default_take=True,
            use_anim_optimize=True,
            anim_optimize_precision=settings['anim_optimize_precision'],
            
            # 座標系
            axis_forward='-Z',
            axis_up='Y',
        )
        
        import os
        file_size = os.path.getsize(filepath) / (1024 * 1024)  # MB
        print(f"✅ エクスポート完了!")
        print(f"📁 ファイル: {filepath}")
        print(f"📏 サイズ: {file_size:.2f} MB")
        
        return True
        
    except Exception as e:
        print(f"❌ エクスポートエラー: {str(e)}")
        return False
```

### バッチエクスポート関数

```python
def batch_export_objects(output_directory, object_groups=None):
    """
    複数オブジェクトを個別のFBXファイルとしてバッチエクスポート
    
    Args:
        output_directory (str): 出力ディレクトリ
        object_groups (dict): {'ファイル名': ['オブジェクト名']} の辞書
    """
    
    import os
    
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
        print(f"📁 ディレクトリを作成: {output_directory}")
    
    if object_groups is None:
        # 全オブジェクトを個別にエクスポート
        object_groups = {}
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                object_groups[obj.name] = [obj.name]
    
    print(f"=== バッチエクスポート開始 ({len(object_groups)} ファイル) ===")
    
    success_count = 0
    for filename, objects in object_groups.items():
        filepath = os.path.join(output_directory, f"{filename}.fbx")
        print(f"\n📤 {filename}.fbx をエクスポート中...")
        
        if export_fbx_complete(filepath, objects, 'HIGH'):
            success_count += 1
            print(f"✅ {filename}.fbx 完了")
        else:
            print(f"❌ {filename}.fbx 失敗")
    
    print(f"\n=== バッチエクスポート完了 ===")
    print(f"成功: {success_count}/{len(object_groups)}")

# 使用例
batch_export_objects("d:/exported_models", {
    "bear_character": ["bear_boy", "bear_boy.001"],
    "environment": ["Ground", "Tree", "Rock"],
    "props": ["Chair", "Table"]
})
```

## 他ソフトウェアとの互換性

### Unity での使用

```csharp
// Unity C# でのFBXインポート後の確認事項
using UnityEngine;
using UnityEditor;

public class FBXImportChecker : EditorWindow
{
    [MenuItem("Tools/FBX Import Checker")]
    public static void ShowWindow()
    {
        // マテリアルの確認
        var renderer = Selection.activeGameObject.GetComponent<Renderer>();
        if (renderer != null)
        {
            foreach (var material in renderer.materials)
            {
                Debug.Log($"Material: {material.name}");
                Debug.Log($"Shader: {material.shader.name}");
                
                // テクスチャの確認
                if (material.mainTexture != null)
                    Debug.Log($"Main Texture: {material.mainTexture.name}");
            }
        }
        
        // UV Channelの確認
        var meshFilter = Selection.activeGameObject.GetComponent<MeshFilter>();
        if (meshFilter != null)
        {
            var mesh = meshFilter.mesh;
            Debug.Log($"UV Channels: {mesh.uv.Length > 0 ? "UV0" : ""}" +
                     $"{mesh.uv2.Length > 0 ? " UV1" : ""}" +
                     $"{mesh.uv3.Length > 0 ? " UV2" : ""}" +
                     $"{mesh.uv4.Length > 0 ? " UV3" : ""}");
        }
    }
}
```

### Unreal Engine での使用

```cpp
// Unreal Engine C++ でのマテリアル設定例
#include "Materials/MaterialInstanceDynamic.h"

// マテリアルパラメータの設定
void SetupImportedMaterial(UMaterialInstanceDynamic* MaterialInstance)
{
    if (MaterialInstance)
    {
        // Blenderからの基本パラメータを設定
        MaterialInstance->SetScalarParameterValue(TEXT("Metallic"), 0.0f);
        MaterialInstance->SetScalarParameterValue(TEXT("Roughness"), 0.5f);
        MaterialInstance->SetVectorParameterValue(TEXT("BaseColor"), 
            FLinearColor(0.8f, 0.8f, 0.8f, 1.0f));
        
        // テクスチャの確認
        UTexture* BaseColorTexture = nullptr;
        if (MaterialInstance->GetTextureParameterValue(TEXT("BaseColorTexture"), BaseColorTexture))
        {
            UE_LOG(LogTemp, Log, TEXT("Base Color Texture found: %s"), 
                   *BaseColorTexture->GetName());
        }
    }
}
```

### Maya での使用

```python
# Maya Python でのFBXインポート後処理
import maya.cmds as cmds

def check_imported_fbx():
    """インポートされたFBXの状態をチェック"""
    
    # マテリアルの確認
    materials = cmds.ls(materials=True)
    for mat in materials:
        if mat.startswith('lambert') or mat.startswith('blinn'):
            continue
            
        print(f"Material: {mat}")
        
        # カラー属性の確認
        if cmds.attributeExists('color', mat):
            color = cmds.getAttr(f'{mat}.color')[0]
            print(f"  Color: {color}")
        
        # テクスチャファイルの確認
        file_nodes = cmds.listConnections(mat, type='file')
        if file_nodes:
            for file_node in file_nodes:
                texture_path = cmds.getAttr(f'{file_node}.fileTextureName')
                print(f"  Texture: {texture_path}")
    
    # UVセットの確認
    meshes = cmds.ls(type='mesh')
    for mesh in meshes:
        uv_sets = cmds.polyUVSet(mesh, query=True, allUVSets=True)
        print(f"Mesh {mesh} UV Sets: {uv_sets}")

# 実行
check_imported_fbx()
```

## トラブルシューティング

### よくある問題と解決法

#### 1. テクスチャが表示されない

**問題**: FBXをインポートしてもテクスチャが真っ白

**原因と対処法**:

```python
def fix_texture_issues():
    """テクスチャ問題の診断と修正"""
    print("=== テクスチャ問題診断 ===")
    
    issues = []
    
    # 1. テクスチャファイルの存在確認
    for img in bpy.data.images:
        if img.filepath and not img.packed_file:
            import os
            if not os.path.exists(bpy.path.abspath(img.filepath)):
                issues.append(f"❌ テクスチャファイルが見つからない: {img.name}")
        
        # 2. カラースペースの確認
        if img.colorspace_settings.name not in ['sRGB', 'Non-Color']:
            issues.append(f"⚠️  カラースペース要確認: {img.name} ({img.colorspace_settings.name})")
    
    # 3. マテリアルノードの接続確認
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue
            
        principled = None
        for node in mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                principled = node
                break
        
        if principled and not principled.inputs['Base Color'].is_linked:
            issues.append(f"⚠️  Base Colorが未接続: {mat.name}")
    
    # 問題レポート
    if issues:
        print("\n🔍 検出された問題:")
        for issue in issues:
            print(f"  {issue}")
        
        print("\n💡 修正提案:")
        print("  1. テクスチャファイルを pack_all_textures() で埋め込み")
        print("  2. カラースペースを sRGB に設定")
        print("  3. Image Texture ノードを Base Color に接続")
    else:
        print("✅ テクスチャ設定に問題なし")
```

#### 2. マテリアルプロパティが転送されない

**解決コード**:

```python
def validate_material_export():
    """マテリアルエクスポートの妥当性を検証"""
    print("=== マテリアル転送妥当性チェック ===")
    
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            print(f"⚠️  {mat.name}: ノードが無効（Lambert等の基本マテリアル）")
            continue
        
        principled = None
        for node in mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                principled = node
                break
        
        if not principled:
            print(f"❌ {mat.name}: Principled BSDFが見つからない")
            continue
        
        print(f"✅ {mat.name}:")
        print(f"    Base Color: {principled.inputs['Base Color'].default_value[:3]}")
        print(f"    Metallic: {principled.inputs['Metallic'].default_value:.2f}")
        print(f"    Roughness: {principled.inputs['Roughness'].default_value:.2f}")
        
        # テクスチャ接続の確認
        if principled.inputs['Base Color'].is_linked:
            linked_node = principled.inputs['Base Color'].links[0].from_node
            if linked_node.type == 'TEX_IMAGE':
                print(f"    Texture: {linked_node.image.name if linked_node.image else 'None'}")
```

#### 3. UVマップが正しく転送されない

**解決コード**:

```python
def validate_uv_transfer(obj_name):
    """UVマップ転送の妥当性を検証"""
    obj = bpy.data.objects.get(obj_name)
    if not obj or obj.type != 'MESH':
        print(f"❌ オブジェクトが見つからない: {obj_name}")
        return False
    
    print(f"=== {obj_name} UV検証 ===")
    
    uv_layers = obj.data.uv_layers
    if not uv_layers:
        print("❌ UVマップが存在しない")
        return False
    
    for i, uv_layer in enumerate(uv_layers):
        print(f"UV Layer {i}: {uv_layer.name}")
        
        # UV座標の範囲チェック
        min_u, max_u = float('inf'), float('-inf')
        min_v, max_v = float('inf'), float('-inf')
        
        for loop_idx in range(len(obj.data.loops)):
            u, v = uv_layer.data[loop_idx].uv
            min_u, max_u = min(min_u, u), max(max_u, u)
            min_v, max_v = min(min_v, v), max(max_v, v)
        
        print(f"  UV範囲: U({min_u:.3f} ~ {max_u:.3f}), V({min_v:.3f} ~ {max_v:.3f})")
        
        # 範囲外UV座標の警告
        if min_u < -0.01 or max_u > 1.01 or min_v < -0.01 or max_v > 1.01:
            print(f"  ⚠️  0-1範囲外のUV座標が検出されました")
    
    print(f"アクティブUV: {uv_layers.active.name if uv_layers.active else 'None'}")
    return True
```

#### 4. ファイルサイズが大きすぎる

**最適化コード**:

```python
def optimize_fbx_size():
    """FBXファイルサイズを最適化"""
    print("=== ファイルサイズ最適化 ===")
    
    # 1. 高解像度テクスチャの確認
    large_textures = []
    for img in bpy.data.images:
        if img.size[0] * img.size[1] > 2048 * 2048:
            large_textures.append(img)
    
    if large_textures:
        print(f"⚠️  高解像度テクスチャ検出: {len(large_textures)} 個")
        for img in large_textures:
            print(f"  {img.name}: {img.size[0]} x {img.size[1]}")
        print("💡 提案: テクスチャサイズを2K以下に変更")
    
    # 2. 未使用マテリアルの確認
    used_materials = set()
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.data.materials:
            for mat in obj.data.materials:
                if mat:
                    used_materials.add(mat)
    
    unused_materials = set(bpy.data.materials) - used_materials
    if unused_materials:
        print(f"📦 未使用マテリアル: {len(unused_materials)} 個")
        print("💡 提案: 未使用マテリアルを削除")
    
    # 3. 高ポリゴンメッシュの確認
    high_poly_objects = []
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            poly_count = len(obj.data.polygons)
            if poly_count > 10000:
                high_poly_objects.append((obj.name, poly_count))
    
    if high_poly_objects:
        print(f"🔺 高ポリゴンオブジェクト:")
        for name, count in high_poly_objects:
            print(f"  {name}: {count:,} ポリゴン")
        print("💡 提案: Decimate モディファイアで最適化")
```

## ベストプラクティス

### 1. プロジェクト開始時の設定

```python
def setup_project_for_fbx_export():
    """FBXエクスポートに最適なプロジェクト設定"""
    
    # 単位設定
    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.context.scene.unit_settings.scale_length = 1.0
    
    # カラーマネジメント
    bpy.context.scene.view_settings.view_transform = 'Standard'
    bpy.context.scene.view_settings.look = 'None'
    
    print("✅ プロジェクト設定を最適化しました")
```

### 2. 命名規則

```python
def enforce_naming_conventions():
    """FBX互換性のための命名規則を適用"""
    
    # オブジェクト名
    for obj in bpy.data.objects:
        old_name = obj.name
        # 日本語や特殊文字を除去
        new_name = ''.join(c for c in old_name if c.isalnum() or c in ['_', '-'])
        if new_name != old_name:
            obj.name = new_name
            print(f"オブジェクト名変更: {old_name} → {new_name}")
    
    # マテリアル名
    for mat in bpy.data.materials:
        old_name = mat.name
        new_name = ''.join(c for c in old_name if c.isalnum() or c in ['_', '-'])
        if new_name != old_name:
            mat.name = new_name
            print(f"マテリアル名変更: {old_name} → {new_name}")
```

### 3. 品質チェックリスト

```python
def fbx_export_checklist():
    """エクスポート前の品質チェックリスト"""
    
    checklist = {
        "テクスチャ埋め込み": False,
        "UV範囲確認": False,
        "マテリアル最適化": False,
        "命名規則": False,
        "ポリゴン数確認": False
    }
    
    print("=== FBXエクスポート チェックリスト ===")
    
    # 1. テクスチャ埋め込み確認
    packed_count = 0
    for img in bpy.data.images:
        if img.packed_file:
            packed_count += 1
    checklist["テクスチャ埋め込み"] = packed_count > 0
    
    # 2. UV範囲確認
    uv_issues = 0
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.data.uv_layers:
            for uv_layer in obj.data.uv_layers:
                for loop_idx in range(len(obj.data.loops)):
                    u, v = uv_layer.data[loop_idx].uv
                    if u < -0.01 or u > 1.01 or v < -0.01 or v > 1.01:
                        uv_issues += 1
                        break
    checklist["UV範囲確認"] = uv_issues == 0
    
    # 3. Principled BSDF確認
    principled_materials = 0
    for mat in bpy.data.materials:
        if mat.use_nodes:
            for node in mat.node_tree.nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    principled_materials += 1
                    break
    checklist["マテリアル最適化"] = principled_materials > 0
    
    # 4. 命名規則確認
    naming_issues = 0
    for obj in bpy.data.objects:
        if not obj.name.isascii():
            naming_issues += 1
    checklist["命名規則"] = naming_issues == 0
    
    # 5. ポリゴン数確認
    total_polygons = 0
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            total_polygons += len(obj.data.polygons)
    checklist["ポリゴン数確認"] = total_polygons < 100000  # 10万ポリゴン以下
    
    # 結果表示
    for item, status in checklist.items():
        icon = "✅" if status else "❌"
        print(f"{icon} {item}")
    
    all_passed = all(checklist.values())
    print(f"\n{'🎉 すべてOK！' if all_passed else '⚠️  問題があります'}")
    
    return checklist
```

### 4. 自動化スクリプト

```python
def auto_fbx_export_workflow(source_obj, target_obj, output_path):
    """完全自動化されたFBXエクスポートワークフロー"""
    
    print("=== 自動FBXエクスポートワークフロー開始 ===")
    
    # 1. マテリアル・UVマップ移植
    print("1. マテリアル・UVマップ移植中...")
    if not transfer_materials_and_uvmaps(source_obj, target_obj):
        print("❌ 移植失敗")
        return False
    
    # 2. 品質チェック
    print("2. 品質チェック中...")
    checklist = fbx_export_checklist()
    
    # 3. 自動修正
    print("3. 自動修正中...")
    if not checklist["テクスチャ埋め込み"]:
        pack_all_textures()
    
    if not checklist["命名規則"]:
        enforce_naming_conventions()
    
    if not checklist["マテリアル最適化"]:
        optimize_materials_for_fbx()
    
    # 4. FBXエクスポート
    print("4. FBXエクスポート中...")
    success = export_fbx_complete(output_path, [target_obj], 'HIGH')
    
    if success:
        print("🎉 ワークフロー完了！")
    else:
        print("❌ エクスポート失敗")
    
    return success

# 使用例
auto_fbx_export_workflow(
    "bear_boy",           # ソースオブジェクト
    "bear_boy.001",       # ターゲットオブジェクト
    "d:/final_model.fbx"  # 出力パス
)
```

## まとめ

このガイドを使用することで以下が実現できます：

### ✅ 確実な成果

1. **高品質なFBXエクスポート**: テクスチャ埋め込み、マテリアル保持
2. **他ソフトウェアとの互換性**: Unity、Unreal、Maya等での確実な動作
3. **自動化ワークフロー**: 手動作業の最小化
4. **品質管理**: エクスポート前の問題検出と自動修正

### 🔧 実用的なツール

- 包括的なエクスポート関数
- 品質チェック機能
- トラブルシューティング機能
- バッチ処理対応

### 📚 応用可能な知識

- FBX形式の特性理解
- Blender APIの活用
- 3Dパイプラインの最適化
- マテリアル・テクスチャ管理

このガイドと `transfer_materials_and_uvmaps()` 関数を組み合わせることで、プロフェッショナルな3Dアセット制作ワークフローを構築できます。

---

**関連ファイル:**
- `blender_script.py` - メインスクリプト
- `README.md` - 基本的な使用方法
- `mcp_server_integration.md` - AI統合ガイド