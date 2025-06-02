#!/usr/bin/env python3
"""
Blenderノードタイプ認識問題の修正システム
現在のBlenderバージョンで利用可能なノードタイプを検出し、
テクスチャ保存システムを修正します。
"""

import bpy
import json
import logging
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def detect_available_node_types() -> Dict[str, str]:
    """
    現在のBlenderバージョンで利用可能なノードタイプを検出
    
    Returns:
        利用可能なノードタイプのマッピング辞書
    """
    logger.info("Blenderノードタイプの検出を開始")
    
    # テスト用の一時マテリアルを作成
    temp_material = bpy.data.materials.new(name="node_type_test")
    temp_material.use_nodes = True
    nodes = temp_material.node_tree.nodes
    
    # 検出対象のノードタイプリスト（複数のバリエーション）
    node_types_to_test = [
        # Principled BSDF
        'BSDF_PRINCIPLED',
        'ShaderNodeBsdfPrincipled',
        'Principled BSDF',
        
        # Image Texture
        'TEX_IMAGE',
        'ShaderNodeTexImage',
        'Image Texture',
        
        # Material Output
        'OUTPUT_MATERIAL',
        'ShaderNodeOutputMaterial',
        'Material Output',
        
        # Mix
        'MIX',
        'ShaderNodeMix',
        'MIX_RGB',
        'ShaderNodeMixRGB',
        'Mix',
        
        # Separate Color/RGB
        'SEPARATE_COLOR',
        'ShaderNodeSeparateColor',
        'SEPARATE_RGB',
        'ShaderNodeSeparateRGB',
        'Separate Color',
        'Separate RGB',
        
        # Normal Map
        'NORMAL_MAP',
        'ShaderNodeNormalMap',
        'Normal Map',
        
        # Vertex Color/Attribute
        'VERTEX_COLOR',
        'ShaderNodeVertexColor',
        'ATTRIBUTE',
        'ShaderNodeAttribute',
        'Color Attribute',
        
        # Math
        'MATH',
        'ShaderNodeMath',
        'Math',
        
        # Mapping
        'MAPPING',
        'ShaderNodeMapping',
        'Mapping',
        
        # Texture Coordinate
        'TEX_COORD',
        'ShaderNodeTexCoord',
        'Texture Coordinate'
    ]
    
    available_types = {}
    
    for node_type in node_types_to_test:
        try:
            # ノードの作成を試行
            test_node = nodes.new(type=node_type)
            
            # 成功した場合、実際のタイプ名を記録
            actual_type = test_node.bl_rna.identifier if hasattr(test_node, 'bl_rna') else node_type
            available_types[node_type] = actual_type
            
            logger.info(f"✅ ノードタイプ '{node_type}' 利用可能 -> 実際のタイプ: '{actual_type}'")
            
            # テストノードを削除
            nodes.remove(test_node)
            
        except Exception as e:
            logger.debug(f"❌ ノードタイプ '{node_type}' 利用不可: {e}")
    
    # テスト用マテリアルを削除
    bpy.data.materials.remove(temp_material)
    
    logger.info(f"検出完了: {len(available_types)} 個のノードタイプが利用可能")
    return available_types

def generate_node_type_mapping(available_types: Dict[str, str]) -> Dict[str, str]:
    """
    検出されたノードタイプから最適なマッピングを生成
    
    Args:
        available_types: 検出された利用可能ノードタイプ
        
    Returns:
        正規化されたマッピング辞書
    """
    mapping = {}
    
    # Principled BSDF
    principled_candidates = [
        'BSDF_PRINCIPLED', 'ShaderNodeBsdfPrincipled', 'Principled BSDF'
    ]
    for candidate in principled_candidates:
        if candidate in available_types:
            mapping['BSDF_PRINCIPLED'] = candidate
            break
    
    # Image Texture
    image_candidates = [
        'TEX_IMAGE', 'ShaderNodeTexImage', 'Image Texture'
    ]
    for candidate in image_candidates:
        if candidate in available_types:
            mapping['TEX_IMAGE'] = candidate
            break
    
    # Material Output
    output_candidates = [
        'OUTPUT_MATERIAL', 'ShaderNodeOutputMaterial', 'Material Output'
    ]
    for candidate in output_candidates:
        if candidate in available_types:
            mapping['OUTPUT_MATERIAL'] = candidate
            break
    
    # Mix
    mix_candidates = [
        'MIX', 'ShaderNodeMix', 'MIX_RGB', 'ShaderNodeMixRGB', 'Mix'
    ]
    for candidate in mix_candidates:
        if candidate in available_types:
            mapping['MIX'] = candidate
            break
    
    # Separate Color
    separate_candidates = [
        'SEPARATE_COLOR', 'ShaderNodeSeparateColor',
        'SEPARATE_RGB', 'ShaderNodeSeparateRGB',
        'Separate Color', 'Separate RGB'
    ]
    for candidate in separate_candidates:
        if candidate in available_types:
            mapping['SEPARATE_COLOR'] = candidate
            break
    
    # Normal Map
    normal_candidates = [
        'NORMAL_MAP', 'ShaderNodeNormalMap', 'Normal Map'
    ]
    for candidate in normal_candidates:
        if candidate in available_types:
            mapping['NORMAL_MAP'] = candidate
            break
    
    # Vertex Color/Attribute
    vertex_candidates = [
        'VERTEX_COLOR', 'ShaderNodeVertexColor',
        'ATTRIBUTE', 'ShaderNodeAttribute',
        'Color Attribute'
    ]
    for candidate in vertex_candidates:
        if candidate in available_types:
            mapping['VERTEX_COLOR'] = candidate
            break
    
    # Math
    math_candidates = [
        'MATH', 'ShaderNodeMath', 'Math'
    ]
    for candidate in math_candidates:
        if candidate in available_types:
            mapping['MATH'] = candidate
            break
    
    return mapping

def update_texture_preservation_system():
    """
    テクスチャ保存システムを検出されたノードタイプで更新
    """
    logger.info("テクスチャ保存システムの更新を開始")
    
    # 利用可能なノードタイプを検出
    available_types = detect_available_node_types()
    
    # 最適なマッピングを生成
    node_mapping = generate_node_type_mapping(available_types)
    
    logger.info("検出されたノードタイプマッピング:")
    for normalized, actual in node_mapping.items():
        logger.info(f"  {normalized} -> {actual}")
    
    # マッピング結果をファイルに保存
    mapping_file = "/app/detected_node_types.json"
    with open(mapping_file, 'w') as f:
        json.dump({
            'available_types': available_types,
            'normalized_mapping': node_mapping,
            'blender_version': bpy.app.version_string
        }, f, indent=2)
    
    logger.info(f"ノードタイプマッピングを保存: {mapping_file}")
    
    return node_mapping

def test_material_reconstruction():
    """
    修正されたノードタイプマッピングでマテリアル再構築をテスト
    """
    logger.info("マテリアル再構築テストを開始")
    
    # ノードタイプマッピングを更新
    node_mapping = update_texture_preservation_system()
    
    if not node_mapping.get('BSDF_PRINCIPLED'):
        logger.error("Principled BSDFノードが利用できません")
        return False
    
    if not node_mapping.get('TEX_IMAGE'):
        logger.error("Image Textureノードが利用できません")
        return False
    
    # テスト用マテリアルを作成
    test_material = bpy.data.materials.new(name="test_material_reconstruction")
    test_material.use_nodes = True
    nodes = test_material.node_tree.nodes
    
    try:
        # 既存ノードをクリア
        nodes.clear()
        
        # Principled BSDFノードを作成
        principled = nodes.new(type=node_mapping['BSDF_PRINCIPLED'])
        principled.location = (0, 0)
        
        # Image Textureノードを作成
        if node_mapping.get('TEX_IMAGE'):
            tex_image = nodes.new(type=node_mapping['TEX_IMAGE'])
            tex_image.location = (-300, 0)
        
        # Material Outputノードを作成
        if node_mapping.get('OUTPUT_MATERIAL'):
            output = nodes.new(type=node_mapping['OUTPUT_MATERIAL'])
            output.location = (300, 0)
            
            # Principled BSDFからOutputに接続
            test_material.node_tree.links.new(
                principled.outputs['BSDF'], 
                output.inputs['Surface']
            )
        
        logger.info("✅ マテリアル再構築テスト成功")
        return True
        
    except Exception as e:
        logger.error(f"❌ マテリアル再構築テスト失敗: {e}")
        return False
    finally:
        # テスト用マテリアルを削除
        bpy.data.materials.remove(test_material)

if __name__ == "__main__":
    logger.info("=== Blenderノードタイプ修正システム ===")
    
    # システム情報を表示
    logger.info(f"Blenderバージョン: {bpy.app.version_string}")
    
    # ノードタイプ検出とマッピング更新
    node_mapping = update_texture_preservation_system()
    
    # マテリアル再構築テスト
    test_success = test_material_reconstruction()
    
    if test_success:
        logger.info("✅ ノードタイプ修正完了 - テクスチャ保存システムが使用可能です")
    else:
        logger.error("❌ ノードタイプ修正に失敗 - 手動での対応が必要です")
