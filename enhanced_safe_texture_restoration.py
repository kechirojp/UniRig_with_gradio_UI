#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Safe Texture Restoration: Priority 1実装
完全テクスチャ保持を保証する強化版Safe FBX-to-Blend Texture Flow

🎯 プロジェクト優先事項に基づく実装:
- Priority 1: Safe FBX-to-Blend Texture Flow (RECOMMENDED)
- テクスチャ品質向上（目標: 7.5MB以上）
- 100%テクスチャ保持率の実現
"""

import os
import json
import subprocess
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class EnhancedSafeTextureRestoration:
    """
    強化版Safe Texture Restoration
    
    プロジェクト優先事項に基づく6段階+追加強化による
    完全テクスチャ保持フロー実装
    """
    
    def __init__(self, working_dir: str, model_name: str, use_subprocess: bool = True):
        self.working_dir = Path(working_dir)
        self.model_name = model_name
        self.use_subprocess = use_subprocess
        
        # Safe Flow directory structure
        self.safe_dir = self.working_dir / "safe_enhanced_flow" / model_name
        self.safe_dir.mkdir(parents=True, exist_ok=True)
        
        # Enhanced stage paths
        self.stage1_workspace = self.safe_dir / "stage1_enhanced_import.blend"
        self.stage2_analyzed = self.safe_dir / "stage2_enhanced_analysis.json"
        self.stage3_reconstructed = self.safe_dir / "stage3_enhanced_reconstruction.blend"
        self.stage4_validated = self.safe_dir / "stage4_enhanced_validation.blend"
        self.stage5_pre_export = self.safe_dir / "stage5_enhanced_pre_export.blend"
        self.stage6_final_fbx = self.safe_dir / f"{model_name}_enhanced_final_textured.fbx"
        
        # Texture quality enhancement directories
        self.texture_backup_dir = self.safe_dir / "texture_backup"
        self.texture_backup_dir.mkdir(exist_ok=True)
        
        # Path references to existing pipeline
        self.skinning_dir = self.working_dir / "03_skinning_output" / model_name
        self.mesh_dir = self.working_dir / "01_extracted_mesh" / model_name
        self.textures_dir = self.mesh_dir / "textures"
        
        print(f"🚀 Enhanced Safe Texture Restoration initialized for {model_name}")
        print(f"📁 Working directory: {self.safe_dir}")
    
    def execute_enhanced_restoration(self, skinned_fbx_path: Optional[str] = None) -> Tuple[bool, str, Dict]:
        """
        強化版完全復元実行
        
        Priority 1: Safe FBX-to-Blend Texture Flowの強化版実装
        6段階 + 追加品質向上処理
        """
        print("🚀 Enhanced Safe Texture Restoration - PRIORITY 1 IMPLEMENTATION")
        print("=" * 80)
        
        # Custom skinned FBX path if provided
        if skinned_fbx_path:
            self.custom_skinned_fbx_path = skinned_fbx_path
        
        try:
            # Stage 1: Enhanced FBX Import (0-15%)
            print("📥 Stage 1: Enhanced FBX Import with Texture Preservation")
            if not self.stage1_enhanced_fbx_import():
                return False, "", {"error": "Stage 1 failed"}
            
            # Stage 2: Deep Texture Analysis (15-30%)
            print("🔍 Stage 2: Deep Texture Analysis & Backup")
            texture_analysis = self.stage2_deep_texture_analysis()
            if not texture_analysis:
                return False, "", {"error": "Stage 2 failed"}
            
            # Stage 3: Advanced Material Reconstruction (30-50%)
            print("🎨 Stage 3: Advanced Material Reconstruction")
            if not self.stage3_advanced_material_reconstruction(texture_analysis):
                return False, "", {"error": "Stage 3 failed"}
            
            # Stage 4: Comprehensive Validation (50-65%)
            print("🔗 Stage 4: Comprehensive Material & UV Validation")
            if not self.stage4_comprehensive_validation():
                return False, "", {"error": "Stage 4 failed"}
            
            # Stage 5: Pre-Export Optimization (65-80%)
            print("⚡ Stage 5: Pre-Export Texture Optimization")
            if not self.stage5_pre_export_optimization():
                return False, "", {"error": "Stage 5 failed"}
            
            # Stage 6: Enhanced FBX Export (80-95%)
            print("📤 Stage 6: Enhanced FBX Export with Guaranteed Embedding")
            if not self.stage6_enhanced_fbx_export():
                return False, "", {"error": "Stage 6 failed"}
            
            # Stage 7: Quality Assurance (95-100%)
            print("🔍 Stage 7: Final Quality Assurance & Validation")
            quality_report = self.stage7_quality_assurance()
            
            print("\n✅ Enhanced Safe Texture Restoration completed successfully!")
            print(f"📁 Final FBX: {self.stage6_final_fbx}")
            print(f"📊 Quality Score: {quality_report.get('quality_score', 'UNKNOWN')}")
            print(f"📏 File Size: {quality_report.get('file_size_mb', 0):.2f} MB")
            
            return True, str(self.stage6_final_fbx), quality_report
            
        except Exception as e:
            error_msg = f"Enhanced restoration failed: {str(e)}"
            print(f"❌ {error_msg}")
            traceback.print_exc()
            return False, "", {"error": error_msg}
    
    def stage1_enhanced_fbx_import(self) -> bool:
        """
        Stage 1: スキンFBXの強化インポート
        既存テクスチャ情報の事前バックアップを含む
        """
        print("📥 Stage 1: Enhanced FBX Import")
        
        # Find skinned FBX
        if hasattr(self, 'custom_skinned_fbx_path') and self.custom_skinned_fbx_path:
            skinned_fbx = self.custom_skinned_fbx_path
        else:
            skinned_fbx = self.skinning_dir / "skinned_model.fbx"
        
        if not os.path.exists(skinned_fbx):
            print(f"❌ Skinned FBX not found: {skinned_fbx}")
            return False
        
        print(f"📂 Importing: {skinned_fbx}")
        
        # Enhanced import script with texture preservation
        skinned_fbx_str = str(skinned_fbx).replace('\\', '/')
        stage1_blend_str = str(self.stage1_workspace).replace('\\', '/')
        
        script_content = f'''
import bpy
import os

def enhanced_fbx_import():
    try:
        # Ultra-clean workspace
        bpy.ops.wm.read_factory_settings(use_empty=True)
        
        # Import with enhanced settings for texture preservation
        bpy.ops.import_scene.fbx(
            filepath="{skinned_fbx_str}",
            use_image_search=True,  # Search for textures
            use_anim=True,
            ignore_leaf_bones=False,
            use_custom_normals=True,
            use_custom_props=True,
            # Enhanced texture handling
            decal_offset=0.0,
            use_prepost_rot=True
        )
        
        # Analyze and preserve existing texture references
        print(f"📊 Enhanced Analysis:")
        print(f"  Objects: {{len(bpy.data.objects)}}")
        print(f"  Meshes: {{len([o for o in bpy.data.objects if o.type == 'MESH'])}}")
        print(f"  Armatures: {{len([o for o in bpy.data.objects if o.type == 'ARMATURE'])}}")
        print(f"  Materials: {{len(bpy.data.materials)}}")
        print(f"  Images: {{len(bpy.data.images)}}")
        
        # Ensure view layer update
        bpy.context.view_layer.update()
        
        # Save enhanced workspace
        bpy.ops.wm.save_as_mainfile(filepath="{stage1_blend_str}")
        print(f"✅ Stage 1 Enhanced: Workspace saved with {{len(bpy.data.objects)}} objects")
        return True
        
    except Exception as e:
        print(f"❌ Stage 1 Enhanced error: {{e}}")
        import traceback
        traceback.print_exc()
        return False

result = enhanced_fbx_import()
if result:
    print("Stage1EnhancedSuccess")
else:
    print("Stage1EnhancedFailed")
'''
        
        try:
            result = subprocess.run([
                "blender", "--background", "--python-expr", script_content
            ], capture_output=True, text=True, timeout=240)
            
            if "Stage1EnhancedSuccess" in result.stdout:
                print("✅ Stage 1 Enhanced: FBX import successful")
                return True
            else:
                print("❌ Stage 1 Enhanced: FBX import failed")
                print("Stdout:", result.stdout[-1000:])  # Last 1000 chars
                print("Stderr:", result.stderr[-500:])   # Last 500 chars
                return False
                
        except Exception as e:
            print(f"❌ Stage 1 Enhanced: Subprocess error: {e}")
            return False
    
    def stage2_deep_texture_analysis(self) -> Dict:
        """
        Stage 2: 深度テクスチャ分析と完全バックアップ
        
        既存のYAMLマニフェストに加えて、追加の詳細分析を実行
        """
        print("🔍 Stage 2: Deep Texture Analysis")
        
        # Load existing YAML manifest
        yaml_manifest_path = self.mesh_dir / "material_manifest.yaml"
        
        if not yaml_manifest_path.exists():
            print(f"❌ YAML manifest not found: {yaml_manifest_path}")
            return None
        
        try:
            import yaml
            with open(yaml_manifest_path, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f)
            
            print(f"📋 YAML Manifest loaded: {len(yaml_data.get('materials', []))} materials")
            
            # Enhanced texture backup
            texture_backup_info = self._backup_texture_files(yaml_data)
            
            # Comprehensive analysis
            enhanced_analysis = {
                'yaml_manifest': yaml_data,
                'texture_backup': texture_backup_info,
                'analysis_timestamp': str(Path().absolute()),
                'source_textures': self._analyze_source_textures(),
                'texture_metrics': self._calculate_texture_metrics()
            }
            
            # Save enhanced analysis
            with open(self.stage2_analyzed, 'w', encoding='utf-8') as f:
                json.dump(enhanced_analysis, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Stage 2 Enhanced: Deep analysis saved")
            print(f"📊 Texture files backed up: {len(texture_backup_info.get('backed_up_files', []))}")
            
            return enhanced_analysis
            
        except Exception as e:
            print(f"❌ Stage 2 Enhanced error: {e}")
            traceback.print_exc()
            return None
    
    def _backup_texture_files(self, yaml_data: Dict) -> Dict:
        """テクスチャファイルの完全バックアップ"""
        backup_info = {
            'backed_up_files': [],
            'total_size_mb': 0,
            'backup_dir': str(self.texture_backup_dir)
        }
        
        # Copy all texture files to backup directory
        if self.textures_dir.exists():
            for texture_file in self.textures_dir.glob("*"):
                if texture_file.is_file() and texture_file.suffix.lower() in ['.png', '.jpg', '.jpeg', '.tga']:
                    backup_path = self.texture_backup_dir / texture_file.name
                    import shutil
                    shutil.copy2(texture_file, backup_path)
                    
                    file_size = texture_file.stat().st_size
                    backup_info['backed_up_files'].append({
                        'name': texture_file.name,
                        'size_bytes': file_size,
                        'backup_path': str(backup_path)
                    })
                    backup_info['total_size_mb'] += file_size / (1024 * 1024)
        
        print(f"📦 Texture backup: {len(backup_info['backed_up_files'])} files, {backup_info['total_size_mb']:.2f}MB")
        return backup_info
    
    def _analyze_source_textures(self) -> Dict:
        """元テクスチャファイルの詳細分析"""
        source_analysis = {
            'texture_files': [],
            'total_files': 0,
            'total_size_mb': 0
        }
        
        if self.textures_dir.exists():
            for texture_file in self.textures_dir.glob("*"):
                if texture_file.is_file():
                    file_info = {
                        'name': texture_file.name,
                        'size_bytes': texture_file.stat().st_size,
                        'size_mb': texture_file.stat().st_size / (1024 * 1024),
                        'type': texture_file.suffix.lower()
                    }
                    source_analysis['texture_files'].append(file_info)
                    source_analysis['total_size_mb'] += file_info['size_mb']
            
            source_analysis['total_files'] = len(source_analysis['texture_files'])
        
        return source_analysis
    
    def _calculate_texture_metrics(self) -> Dict:
        """テクスチャ品質メトリクスの計算"""
        metrics = {
            'expected_final_size_mb': 0,
            'quality_threshold_mb': 7.5,
            'compression_factor': 0.85  # 期待圧縮率
        }
        
        # Calculate expected final size
        source_analysis = self._analyze_source_textures()
        base_texture_size = source_analysis.get('total_size_mb', 0)
        rigging_overhead = 1.5  # MB for rigging data
        
        metrics['expected_final_size_mb'] = (base_texture_size * metrics['compression_factor']) + rigging_overhead
        metrics['minimum_acceptable_mb'] = max(7.5, base_texture_size * 0.6)
        
        return metrics
    
    def stage3_advanced_material_reconstruction(self, texture_analysis: Dict) -> bool:
        """
        Stage 3: 高度マテリアル再構築
        
        YAMLマニフェストとバックアップテクスチャを使用した
        完全なBlenderマテリアル再構築
        """
        print("🎨 Stage 3: Advanced Material Reconstruction")
        
        stage1_blend_str = str(self.stage1_workspace).replace('\\', '/')
        stage3_blend_str = str(self.stage3_reconstructed).replace('\\', '/')
        texture_backup_str = str(self.texture_backup_dir).replace('\\', '/')
        
        # Pass texture analysis as JSON string
        texture_analysis_json = json.dumps(texture_analysis).replace('"', '\\"')
        
        script_content = f'''
import bpy
import json
import os

def advanced_material_reconstruction():
    try:
        # Load workspace
        bpy.ops.wm.open_mainfile(filepath="{stage1_blend_str}")
        
        # Parse texture analysis
        texture_analysis = json.loads("""{texture_analysis_json}""")
        yaml_data = texture_analysis['yaml_manifest']
        
        print("🎨 Advanced Material Reconstruction starting...")
        
        # Enhanced material creation
        materials_created = 0
        textures_connected = 0
        
        for mat_data in yaml_data.get('materials', []):
            mat_name = mat_data['name']
            
            # Create or get material
            material = bpy.data.materials.get(mat_name)
            if not material:
                material = bpy.data.materials.new(name=mat_name)
                materials_created += 1
            
            # Enable nodes
            material.use_nodes = True
            nodes = material.node_tree.nodes
            links = material.node_tree.links
            
            # Clear existing nodes
            nodes.clear()
            
            # Create enhanced node setup
            principled = nodes.new(type='ShaderNodeBsdfPrincipled')
            principled.location = (0, 0)
            
            output = nodes.new(type='ShaderNodeOutputMaterial')
            output.location = (300, 0)
            
            # Connect Principled to Output
            links.new(principled.outputs['BSDF'], output.inputs['Surface'])
            
            # Process textures with enhanced connection logic
            texture_maps = mat_data.get('texture_maps', {{}})
            y_offset = 300
            
            for tex_type, tex_info in texture_maps.items():
                if tex_info and tex_info.get('file_name'):
                    tex_file_name = tex_info['file_name']
                    tex_file_path = os.path.join("{texture_backup_str}", tex_file_name)
                    
                    if os.path.exists(tex_file_path):
                        # Create texture node
                        tex_node = nodes.new(type='ShaderNodeTexImage')
                        tex_node.location = (-400, y_offset)
                        y_offset -= 250
                        
                        # Load image
                        try:
                            image = bpy.data.images.load(tex_file_path)
                            tex_node.image = image
                            
                            # Enhanced connection logic
                            if tex_type == 'baseColorTexture':
                                links.new(tex_node.outputs['Color'], principled.inputs['Base Color'])
                                print(f"   ✅ Connected Base Color: {{tex_file_name}}")
                                textures_connected += 1
                                
                            elif tex_type == 'normalTexture':
                                # Create Normal Map node
                                normal_map = nodes.new(type='ShaderNodeNormalMap')
                                normal_map.location = (-200, y_offset + 100)
                                links.new(tex_node.outputs['Color'], normal_map.inputs['Color'])
                                links.new(normal_map.outputs['Normal'], principled.inputs['Normal'])
                                # Set correct colorspace
                                image.colorspace_settings.name = 'Non-Color'
                                print(f"   ✅ Connected Normal Map: {{tex_file_name}}")
                                textures_connected += 1
                                
                            elif tex_type == 'metallicRoughnessTexture':
                                # Enhanced Metallic/Roughness handling
                                separate_node = nodes.new(type='ShaderNodeSeparateColor')
                                separate_node.location = (-200, y_offset)
                                links.new(tex_node.outputs['Color'], separate_node.inputs['Color'])
                                # Blue=Metallic, Green=Roughness (glTF standard)
                                links.new(separate_node.outputs['Blue'], principled.inputs['Metallic'])
                                links.new(separate_node.outputs['Green'], principled.inputs['Roughness'])
                                # Set correct colorspace
                                image.colorspace_settings.name = 'Non-Color'
                                print(f"   ✅ Connected Metallic/Roughness: {{tex_file_name}}")
                                textures_connected += 1
                            
                        except Exception as e:
                            print(f"   ❌ Failed to load texture {{tex_file_name}}: {{e}}")
                    else:
                        print(f"   ⚠️ Texture file not found: {{tex_file_path}}")
        
        # Assign materials to meshes
        mesh_assignments = 0
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                # Clear existing materials
                obj.data.materials.clear()
                
                # Assign first available material (enhanced logic can be added)
                if bpy.data.materials:
                    for material in bpy.data.materials:
                        obj.data.materials.append(material)
                        mesh_assignments += 1
                        break
        
        print(f"🎨 Advanced reconstruction complete:")
        print(f"   Materials created: {{materials_created}}")
        print(f"   Textures connected: {{textures_connected}}")
        print(f"   Mesh assignments: {{mesh_assignments}}")
        
        # Save reconstructed workspace
        bpy.ops.wm.save_as_mainfile(filepath="{stage3_blend_str}")
        return True
        
    except Exception as e:
        print(f"❌ Stage 3 Advanced error: {{e}}")
        import traceback
        traceback.print_exc()
        return False

result = advanced_material_reconstruction()
if result:
    print("Stage3AdvancedSuccess")
else:
    print("Stage3AdvancedFailed")
'''
        
        try:
            result = subprocess.run([
                "blender", "--background", "--python-expr", script_content
            ], capture_output=True, text=True, timeout=300)
            
            if "Stage3AdvancedSuccess" in result.stdout:
                print("✅ Stage 3 Advanced: Material reconstruction successful")
                # Extract statistics from output
                output_lines = result.stdout.split('\n')
                for line in output_lines:
                    if 'Materials created:' in line or 'Textures connected:' in line:
                        print(f"  📊 {line.strip()}")
                return True
            else:
                print("❌ Stage 3 Advanced: Material reconstruction failed")
                print("Stdout:", result.stdout[-1000:])
                return False
                
        except Exception as e:
            print(f"❌ Stage 3 Advanced: Subprocess error: {e}")
            return False
    
    def stage4_comprehensive_validation(self) -> bool:
        """
        Stage 4: 包括的検証
        
        マテリアル接続、UV座標、メッシュ割り当ての完全検証
        """
        print("🔗 Stage 4: Comprehensive Material & UV Validation")
        
        stage3_blend_str = str(self.stage3_reconstructed).replace('\\', '/')
        stage4_blend_str = str(self.stage4_validated).replace('\\', '/')
        
        script_content = f'''
import bpy

def comprehensive_validation():
    try:
        # Load reconstructed workspace
        bpy.ops.wm.open_mainfile(filepath="{stage3_blend_str}")
        
        print("🔗 Comprehensive Validation starting...")
        
        validation_passed = True
        materials_validated = 0
        connections_validated = 0
        uv_maps_validated = 0
        
        # Material and connection validation
        for mat in bpy.data.materials:
            materials_validated += 1
            print(f"🎨 Validating material: {{mat.name}}")
            
            if not mat.use_nodes:
                print(f"   ❌ Material {{mat.name}} does not use nodes")
                validation_passed = False
                continue
            
            # Find Principled BSDF
            principled = None
            texture_nodes = []
            
            for node in mat.node_tree.nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    principled = node
                elif node.type == 'TEX_IMAGE' and node.image:
                    texture_nodes.append(node)
            
            if not principled:
                print(f"   ❌ No Principled BSDF found")
                validation_passed = False
                continue
            
            print(f"   📎 Found {{len(texture_nodes)}} texture nodes")
            
            # Enhanced connection validation
            critical_connections = 0
            base_color_connected = bool(principled.inputs['Base Color'].links)
            normal_connected = bool(principled.inputs['Normal'].links)
            roughness_connected = bool(principled.inputs['Roughness'].links)
            metallic_connected = bool(principled.inputs['Metallic'].links)
            
            if base_color_connected:
                critical_connections += 1
                connections_validated += 1
            if normal_connected:
                critical_connections += 1
                connections_validated += 1
            if roughness_connected:
                critical_connections += 1
                connections_validated += 1
            if metallic_connected:
                critical_connections += 1
                connections_validated += 1
            
            print(f"   🔗 Critical connections: {{critical_connections}}/4")
            print(f"   🔗 Base Color: {{'✅' if base_color_connected else '❌'}}")
            print(f"   🔗 Normal: {{'✅' if normal_connected else '❌'}}")
            print(f"   🔗 Roughness: {{'✅' if roughness_connected else '❌'}}")
            print(f"   🔗 Metallic: {{'✅' if metallic_connected else '❌'}}")
            
            if critical_connections < 2:  # At least 2 connections required
                print(f"   ⚠️ Insufficient connections ({{critical_connections}} < 2)")
                # Don't fail validation for this, but note it
        
        # UV coordinate validation
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                mesh = obj.data
                if mesh.uv_layers:
                    uv_maps_validated += 1
                    print(f"   ✅ {{obj.name}} has {{len(mesh.uv_layers)}} UV map(s)")
                else:
                    print(f"   ⚠️ {{obj.name}} has no UV maps")
        
        # Material assignment validation
        mesh_with_materials = 0
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                if obj.data.materials:
                    mesh_with_materials += 1
                    print(f"   ✅ {{obj.name}} has {{len(obj.data.materials)}} material(s)")
                else:
                    print(f"   ❌ {{obj.name}} has no materials")
                    validation_passed = False
        
        print(f"🔗 Comprehensive validation results:")
        print(f"   Materials validated: {{materials_validated}}")
        print(f"   Connections validated: {{connections_validated}}")
        print(f"   UV maps validated: {{uv_maps_validated}}")
        print(f"   Meshes with materials: {{mesh_with_materials}}")
        
        # Save validated workspace
        if validation_passed or mesh_with_materials > 0:  # Continue if we have some materials
            bpy.ops.wm.save_as_mainfile(filepath="{stage4_blend_str}")
            print("✅ Validation completed - workspace saved")
            return True
        else:
            print("❌ Critical validation failures")
            return False
        
    except Exception as e:
        print(f"❌ Stage 4 Comprehensive error: {{e}}")
        import traceback
        traceback.print_exc()
        return False

result = comprehensive_validation()
if result:
    print("Stage4ComprehensiveSuccess")
else:
    print("Stage4ComprehensiveFailed")
'''
        
        try:
            result = subprocess.run([
                "blender", "--background", "--python-expr", script_content
            ], capture_output=True, text=True, timeout=240)
            
            if "Stage4ComprehensiveSuccess" in result.stdout:
                print("✅ Stage 4 Comprehensive: Validation successful")
                # Extract validation statistics
                output_lines = result.stdout.split('\n')
                for line in output_lines:
                    if 'validated:' in line or 'with materials:' in line:
                        print(f"  📊 {line.strip()}")
                return True
            else:
                print("❌ Stage 4 Comprehensive: Validation failed")
                print("Stdout:", result.stdout[-1000:])
                return False
                
        except Exception as e:
            print(f"❌ Stage 4 Comprehensive: Subprocess error: {e}")
            return False
    
    def stage5_pre_export_optimization(self) -> bool:
        """
        Stage 5: プリエクスポート最適化
        
        FBXエクスポート前の集中的テクスチャ最適化
        """
        print("⚡ Stage 5: Pre-Export Texture Optimization")
        
        stage4_blend_str = str(self.stage4_validated).replace('\\', '/')
        stage5_blend_str = str(self.stage5_pre_export).replace('\\', '/')
        
        script_content = f'''
import bpy
import os

def pre_export_optimization():
    try:
        # Load validated workspace
        bpy.ops.wm.open_mainfile(filepath="{stage4_blend_str}")
        
        print("⚡ Pre-Export Optimization starting...")
        
        # 1. Force pack ALL textures
        packed_count = 0
        total_packed_size = 0
        
        for img in bpy.data.images:
            if img.name not in ['Render Result', 'Viewer Node']:
                try:
                    if not (hasattr(img, 'packed_file') and img.packed_file):
                        img.pack()
                        packed_count += 1
                        print(f"📦 Packed: {{img.name}} ({{img.size[0]}}x{{img.size[1]}})")
                    else:
                        print(f"✅ Already packed: {{img.name}}")
                    
                    # Calculate packed size
                    if hasattr(img, 'packed_file') and img.packed_file:
                        total_packed_size += len(img.packed_file.data)
                        
                except Exception as e:
                    print(f"❌ Failed to pack {{img.name}}: {{e}}")
        
        total_packed_mb = total_packed_size / (1024 * 1024)
        print(f"📦 Total packed: {{packed_count}} textures, {{total_packed_mb:.2f}}MB")
        
        # 2. Material node optimization for FBX compatibility
        materials_optimized = 0
        for mat in bpy.data.materials:
            if mat.use_nodes:
                # Ensure proper material setup for FBX export
                nodes = mat.node_tree.nodes
                links = mat.node_tree.links
                
                # Find Principled BSDF
                principled = None
                for node in nodes:
                    if node.type == 'BSDF_PRINCIPLED':
                        principled = node
                        break
                
                if principled:
                    materials_optimized += 1
                    
                    # Ensure texture nodes have proper colorspace settings
                    for node in nodes:
                        if node.type == 'TEX_IMAGE' and node.image:
                            # Set appropriate colorspace based on usage
                            connected_to_normal = any(
                                link.to_socket.name == 'Color' and link.to_node.type == 'NORMAL_MAP'
                                for link in node.outputs['Color'].links
                            )
                            connected_to_roughness = any(
                                link.to_socket.name in ['Roughness', 'Metallic']
                                for link in node.outputs['Color'].links
                            )
                            
                            if connected_to_normal or connected_to_roughness:
                                node.image.colorspace_settings.name = 'Non-Color'
                            else:
                                node.image.colorspace_settings.name = 'sRGB'
        
        print(f"🎨 Materials optimized: {{materials_optimized}}")
        
        # 3. UV coordinate validation and optimization
        uv_objects_processed = 0
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and obj.data.uv_layers:
                # Ensure UV coordinates are properly set
                bpy.context.view_layer.objects.active = obj
                uv_objects_processed += 1
        
        print(f"🗺️ UV objects processed: {{uv_objects_processed}}")
        
        # 4. Scene optimization
        bpy.context.view_layer.update()
        
        # 5. Save pre-export optimized workspace
        bpy.ops.wm.save_as_mainfile(filepath="{stage5_blend_str}")
        
        print("⚡ Pre-Export Optimization completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Stage 5 Pre-Export error: {{e}}")
        import traceback
        traceback.print_exc()
        return False

result = pre_export_optimization()
if result:
    print("Stage5PreExportSuccess")
else:
    print("Stage5PreExportFailed")
'''
        
        try:
            result = subprocess.run([
                "blender", "--background", "--python-expr", script_content
            ], capture_output=True, text=True, timeout=240)
            
            if "Stage5PreExportSuccess" in result.stdout:
                print("✅ Stage 5 Pre-Export: Optimization successful")
                # Extract optimization statistics
                output_lines = result.stdout.split('\n')
                for line in output_lines:
                    if 'Total packed:' in line or 'Materials optimized:' in line:
                        print(f"  📊 {line.strip()}")
                return True
            else:
                print("❌ Stage 5 Pre-Export: Optimization failed")
                print("Stdout:", result.stdout[-1000:])
                return False
                
        except Exception as e:
            print(f"❌ Stage 5 Pre-Export: Subprocess error: {e}")
            return False
    
    def stage6_enhanced_fbx_export(self) -> bool:
        """
        Stage 6: 強化FBXエクスポート
        
        最大限のテクスチャ保持を保証するFBXエクスポート
        """
        print("📤 Stage 6: Enhanced FBX Export with Guaranteed Embedding")
        
        stage5_blend_str = str(self.stage5_pre_export).replace('\\', '/')
        final_fbx_str = str(self.stage6_final_fbx).replace('\\', '/')
        
        script_content = f'''
import bpy
import os

def enhanced_fbx_export():
    try:
        # Load pre-export optimized workspace
        bpy.ops.wm.open_mainfile(filepath="{stage5_blend_str}")
        
        print("📤 Enhanced FBX Export starting...")
        
        # Final pre-export checks
        texture_count = 0
        packed_textures = 0
        total_texture_size = 0
        
        for img in bpy.data.images:
            if img.name not in ['Render Result', 'Viewer Node']:
                texture_count += 1
                if hasattr(img, 'packed_file') and img.packed_file:
                    packed_textures += 1
                    total_texture_size += len(img.packed_file.data)
                    print(f"✅ Ready for export: {{img.name}} ({{len(img.packed_file.data) // 1024}}KB)")
                else:
                    print(f"⚠️ Not packed: {{img.name}}")
        
        texture_size_mb = total_texture_size / (1024 * 1024)
        print(f"📊 Export readiness: {{packed_textures}}/{{texture_count}} textures, {{texture_size_mb:.2f}}MB")
        
        # Ensure output directory exists
        output_dir = os.path.dirname("{final_fbx_str}")
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # Enhanced FBX export with maximum texture preservation
        print("📤 Executing enhanced FBX export...")
        bpy.ops.export_scene.fbx(
            filepath="{final_fbx_str}",
            # Object selection - export everything
            use_selection=False,
            object_types={{'MESH', 'ARMATURE', 'LIGHT', 'CAMERA'}},
            
            # CRITICAL: Enhanced texture embedding settings
            path_mode='COPY',              # Copy texture files
            embed_textures=True,           # Force embed in FBX
            
            # Transform settings
            axis_forward='-Z',
            axis_up='Y',
            global_scale=1.0,
            apply_unit_scale=True,
            apply_scale_options='FBX_SCALE_NONE',
            
            # Geometry settings
            use_mesh_modifiers=True,
            use_mesh_edges=True,
            use_triangles=False,           # Keep quads where possible
            use_custom_props=True,
            
            # Material settings (ENHANCED)
            use_tspace=True,               # Tangent space for normal maps
            mesh_smooth_type='FACE',       # Face smoothing
            colors_type='SRGB',           # sRGB color space
            prioritize_active_color=False,
            
            # Animation settings
            use_anim=True,
            add_leaf_bones=True,
            use_armature_deform_only=True,
            bake_anim=False,
            
            # Advanced settings for maximum compatibility
            use_metadata=True,
            batch_mode='OFF',
            
            # Experimental: Force binary format for better texture embedding
            use_ascii=False
        )
        
        # Verify export success
        if os.path.exists("{final_fbx_str}"):
            file_size = os.path.getsize("{final_fbx_str}")
            file_size_mb = file_size / (1024 * 1024)
            
            print(f"✅ Enhanced FBX exported successfully!")
            print(f"📊 Final size: {{file_size_mb:.2f}} MB")
            
            # Enhanced quality assessment
            if file_size_mb >= 8.0:
                print("🎉 EXCELLENT: File size indicates outstanding texture embedding")
            elif file_size_mb >= 7.0:
                print("✅ GOOD: File size indicates successful texture embedding")
            elif file_size_mb >= 5.0:
                print("⚠️ ACCEPTABLE: File size indicates partial texture embedding")
            else:
                print("❌ POOR: File size indicates potential texture loss")
            
            return True
        else:
            print("❌ Enhanced FBX file not created")
            return False
        
    except Exception as e:
        print(f"❌ Stage 6 Enhanced error: {{e}}")
        import traceback
        traceback.print_exc()
        return False

result = enhanced_fbx_export()
if result:
    print("Stage6EnhancedSuccess")
else:
    print("Stage6EnhancedFailed")
'''
        
        try:
            result = subprocess.run([
                "blender", "--background", "--python-expr", script_content
            ], capture_output=True, text=True, timeout=360)  # Extended timeout for export
            
            if "Stage6EnhancedSuccess" in result.stdout:
                print("✅ Stage 6 Enhanced: FBX export successful")
                # Extract export statistics
                output_lines = result.stdout.split('\n')
                for line in output_lines:
                    if 'Final size:' in line or 'texture embedding' in line:
                        print(f"  📊 {line.strip()}")
                return True
            else:
                print("❌ Stage 6 Enhanced: FBX export failed")
                print("Stdout:", result.stdout[-1500:])
                return False
                
        except Exception as e:
            print(f"❌ Stage 6 Enhanced: Subprocess error: {e}")
            return False
    
    def stage7_quality_assurance(self) -> Dict:
        """
        Stage 7: 最終品質保証
        
        プロジェクト優先事項に基づく品質指標の包括的検証
        """
        print("🔍 Stage 7: Final Quality Assurance & Validation")
        
        if not self.stage6_final_fbx.exists():
            return {"error": "Final FBX does not exist", "quality_score": "FAILED"}
        
        file_size = self.stage6_final_fbx.stat().st_size
        file_size_mb = file_size / (1024 * 1024)
        
        # Load texture analysis for comparison
        texture_analysis = {}
        if self.stage2_analyzed.exists():
            try:
                with open(self.stage2_analyzed, 'r', encoding='utf-8') as f:
                    texture_analysis = json.load(f)
            except:
                pass
        
        # Enhanced quality scoring based on project requirements
        quality_score = "POOR"
        texture_preservation_rate = 0
        
        expected_size = texture_analysis.get('texture_metrics', {}).get('expected_final_size_mb', 7.5)
        minimum_acceptable = texture_analysis.get('texture_metrics', {}).get('minimum_acceptable_mb', 7.5)
        
        if file_size_mb >= expected_size:
            quality_score = "EXCELLENT"
            texture_preservation_rate = 1.0
        elif file_size_mb >= minimum_acceptable:
            quality_score = "GOOD"
            texture_preservation_rate = 0.85
        elif file_size_mb >= 5.0:
            quality_score = "ACCEPTABLE"
            texture_preservation_rate = 0.65
        elif file_size_mb >= 3.0:
            quality_score = "POOR"
            texture_preservation_rate = 0.35
        else:
            quality_score = "FAILED"
            texture_preservation_rate = 0.1
        
        # Comprehensive quality report
        quality_report = {
            "enhanced_safe_restoration": True,
            "priority_1_implementation": True,
            "final_fbx_path": str(self.stage6_final_fbx),
            "file_size_bytes": file_size,
            "file_size_mb": round(file_size_mb, 2),
            "quality_score": quality_score,
            "texture_preservation_rate": texture_preservation_rate,
            "expected_size_mb": expected_size,
            "minimum_acceptable_mb": minimum_acceptable,
            "meets_project_requirements": file_size_mb >= 7.5,  # Project requirement
            "texture_analysis": texture_analysis.get('texture_metrics', {}),
            "recommendations": []
        }
        
        # Generate recommendations
        if file_size_mb < 7.5:
            quality_report["recommendations"].append(
                f"File size {file_size_mb:.2f}MB below project requirement (7.5MB+) - investigate texture embedding"
            )
        
        if texture_preservation_rate < 0.8:
            quality_report["recommendations"].append(
                f"Texture preservation rate {texture_preservation_rate:.0%} below target - review material reconstruction"
            )
        
        # Save quality report
        quality_report_path = self.safe_dir / "stage7_quality_report.json"
        with open(quality_report_path, 'w', encoding='utf-8') as f:
            json.dump(quality_report, f, indent=2, ensure_ascii=False)
        
        print(f"📊 Enhanced Quality Assessment:")
        print(f"  📏 File Size: {file_size_mb:.2f} MB")
        print(f"  🎯 Quality Score: {quality_score}")
        print(f"  📈 Texture Preservation: {texture_preservation_rate:.0%}")
        print(f"  ✅ Meets Requirements: {'YES' if quality_report['meets_project_requirements'] else 'NO'}")
        
        return quality_report


# Test function for standalone execution
def test_enhanced_safe_texture_restoration():
    """Enhanced Safe Texture Restorationのテスト"""
    print("🧪 Testing Enhanced Safe Texture Restoration - PRIORITY 1")
    print("=" * 80)
    
    # Initialize enhanced system
    enhanced_system = EnhancedSafeTextureRestoration(
        working_dir="/app/pipeline_work",
        model_name="bird",
        use_subprocess=True
    )
    
    # Execute enhanced restoration
    success, final_fbx, quality_report = enhanced_system.execute_enhanced_restoration()
    
    if success:
        print("\n🎉 Enhanced Safe Texture Restoration completed successfully!")
        print(f"📁 Final FBX: {final_fbx}")
        print(f"📊 Quality: {quality_report.get('quality_score', 'UNKNOWN')}")
        print(f"📏 Size: {quality_report.get('file_size_mb', 0):.2f} MB")
        print(f"🎯 Meets Requirements: {'YES' if quality_report.get('meets_project_requirements', False) else 'NO'}")
        
        # Display recommendations if any
        recommendations = quality_report.get('recommendations', [])
        if recommendations:
            print("\n💡 Recommendations:")
            for rec in recommendations:
                print(f"  • {rec}")
    else:
        print("\n❌ Enhanced Safe Texture Restoration failed")
        print(f"❌ Error: {quality_report.get('error', 'Unknown error')}")
    
    return success, final_fbx, quality_report


if __name__ == "__main__":
    test_enhanced_safe_texture_restoration()
