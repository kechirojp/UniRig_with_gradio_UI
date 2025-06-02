#!/usr/bin/env python3
"""
改良されたSafeTextureRestoration - YAML based texture restoration
YAMLマニフェストファイルからテクスチャ情報を読み込み、完全なマテリアル再構築を実行
"""

import os
import sys
import subprocess
import yaml
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Blender availability check
try:
    import bpy
    BLENDER_AVAILABLE = True
except ImportError:
    BLENDER_AVAILABLE = False
    print("⚠️ Blender Python API not available - using subprocess mode")

class ImprovedSafeTextureRestoration:
    """
    改良版SafeTextureRestoration
    YAMLマニフェストファイルベースのテクスチャ復元
    """
    
    def __init__(self, working_dir: str, model_name: str, use_subprocess: bool = True):
        self.working_dir = Path(working_dir)
        self.model_name = model_name
        self.use_subprocess = use_subprocess
        
        # Initialize paths
        self.extracted_dir = self.working_dir / "01_extracted_mesh" / model_name
        self.skinning_dir = self.working_dir / "03_skinning_output" / model_name
        self.output_dir = self.working_dir / "08_final_output" / model_name
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Stage files
        self.stage1_blend = self.output_dir / f"{model_name}_stage1_imported.blend"
        self.stage3_blend = self.output_dir / f"{model_name}_stage3_materials.blend"
        self.stage4_blend = self.output_dir / f"{model_name}_stage4_assigned.blend"
        self.final_fbx = self.output_dir / f"{model_name}_final_textured_rigged.fbx"
        
        print(f"🔧 ImprovedSafeTextureRestoration initialized for: {model_name}")
        print(f"📁 Working directory: {self.working_dir}")
        print(f"📁 Output directory: {self.output_dir}")
    
    def execute_full_restoration(self, skinned_fbx_path: Optional[str] = None) -> Tuple[bool, str, Dict]:
        """
        完全なテクスチャ復元パイプラインを実行
        
        Args:
            skinned_fbx_path: スキン済みFBXファイルのパス (オプション)
        
        Returns:
            tuple: (success, final_fbx_path, quality_report)
        """
        print("🚀 Improved Safe Texture Restoration - Full Pipeline")
        print("=" * 60)
        
        # Store custom skinned FBX path if provided
        if skinned_fbx_path:
            self.custom_skinned_fbx_path = skinned_fbx_path
            print(f"🎯 Using custom skinned FBX: {skinned_fbx_path}")
        
        # Stage 1: FBX Import
        if not self.stage1_safe_fbx_import():
            return False, "", {"error": "Stage 1 failed"}
        
        # Stage 2: Texture Manifest Recovery
        texture_data = self.stage2_yaml_manifest_recovery()
        if not texture_data:
            return False, "", {"error": "Stage 2 failed"}
        
        # Stage 3: Complete Material Reconstruction
        if not self.stage3_complete_material_reconstruction(texture_data):
            return False, "", {"error": "Stage 3 failed"}
        
        # Stage 4: Material Assignment & Validation
        if not self.stage4_material_assignment_validation():
            return False, "", {"error": "Stage 4 failed"}
        
        # Stage 5: Optimized FBX Export
        if not self.stage5_optimized_fbx_export():
            return False, "", {"error": "Stage 5 failed"}
        
        # Stage 6: Quality Validation
        quality_report = self.stage6_comprehensive_quality_validation()
        
        print("✅ Improved Safe Texture Restoration completed successfully!")
        return True, str(self.final_fbx), quality_report
    
    def stage1_safe_fbx_import(self) -> bool:
        """
        Stage 1: スキンFBXファイルの安全インポート
        """
        print("📥 Stage 1: Safe FBX Import")
        
        # Find skinned FBX
        skinned_fbx = self.skinning_dir / "skinned_model.fbx"
        if not skinned_fbx.exists():
            print(f"❌ Skinned FBX not found: {skinned_fbx}")
            return False
        
        print(f"📂 Importing: {skinned_fbx}")
        
        script_content = f'''
import bpy
import os

def safe_import_fbx():
    try:
        # Clean workspace
        bpy.ops.wm.read_factory_settings(use_empty=True)
        
        # Import FBX with armature preservation
        bpy.ops.import_scene.fbx(
            filepath="{skinned_fbx}",
            use_image_search=False,
            use_anim=True,
            ignore_leaf_bones=False,
            use_custom_normals=True
        )
        
        # Analyze imported content
        print(f"📊 Imported objects: {{len(bpy.data.objects)}}")
        print(f"📊 Mesh objects: {{len([o for o in bpy.data.objects if o.type == 'MESH'])}}")
        print(f"📊 Armatures: {{len([o for o in bpy.data.objects if o.type == 'ARMATURE'])}}")
        print(f"📊 Materials: {{len(bpy.data.materials)}}")
        
        # Save workspace
        bpy.ops.wm.save_as_mainfile(filepath="{self.stage1_blend}")
        print(f"✅ Stage 1 complete: {{len(bpy.data.objects)}} objects imported")
        return True
        
    except Exception as e:
        print(f"❌ Stage 1 error: {{e}}")
        import traceback
        traceback.print_exc()
        return False

result = safe_import_fbx()
if result:
    print("Stage1Success")
else:
    print("Stage1Failed")
'''
        
        try:
            result = subprocess.run([
                "blender", "--background", "--python-expr", script_content
            ], capture_output=True, text=True, timeout=180)
            
            if "Stage1Success" in result.stdout:
                print("✅ Stage 1: FBX import successful")
                return True
            else:
                print("❌ Stage 1: FBX import failed")
                print("Stdout:", result.stdout)
                print("Stderr:", result.stderr)
                return False
                
        except Exception as e:
            print(f"❌ Stage 1: Subprocess error: {e}")
            return False
    
    def stage2_yaml_manifest_recovery(self) -> Optional[Dict]:
        """
        Stage 2: YAMLマニフェストからテクスチャ情報の回復
        """
        print("📋 Stage 2: YAML Manifest Recovery")
        
        yaml_manifest = self.extracted_dir / "texture_manifest.yaml"
        if not yaml_manifest.exists():
            print(f"❌ YAML manifest not found: {yaml_manifest}")
            return None
        
        try:
            with open(yaml_manifest, 'r') as f:
                manifest_data = yaml.safe_load(f)
            
            print(f"📋 Loaded manifest for: {manifest_data.get('model_name', 'unknown')}")
            print(f"📋 Texture count: {manifest_data.get('texture_count', 0)}")
            
            # Validate texture files exist
            texture_files = {}
            for texture_info in manifest_data.get('textures', []):
                texture_name = texture_info['original_name']
                texture_path = Path(texture_info['saved_path'])
                
                if texture_path.exists():
                    file_size = texture_path.stat().st_size / (1024 * 1024)
                    texture_files[texture_name] = {
                        'path': str(texture_path),
                        'size_mb': file_size,
                        'type': self._detect_texture_type(texture_name)
                    }
                    print(f"   ✅ {texture_name} ({file_size:.2f} MB) - {texture_files[texture_name]['type']}")
                else:
                    print(f"   ❌ {texture_name} - File not found")
            
            if not texture_files:
                print("❌ No valid texture files found")
                return None
            
            return {
                'manifest': manifest_data,
                'texture_files': texture_files,
                'texture_dir': str(self.extracted_dir / "textures")
            }
            
        except Exception as e:
            print(f"❌ Stage 2 error: {e}")
            return None
    
    def _detect_texture_type(self, texture_name: str) -> str:
        """テクスチャ名からタイプを推測"""
        name_lower = texture_name.lower()
        if '_col_' in name_lower or '_bc' in name_lower or '_base' in name_lower:
            return 'BASE_COLOR'
        elif '_nrml' in name_lower or '_n' in name_lower or '_normal' in name_lower:
            return 'NORMAL'
        elif '_gloss' in name_lower or '_r' in name_lower or '_rough' in name_lower:
            return 'ROUGHNESS'
        elif '_metal' in name_lower or '_m' in name_lower:
            return 'METALLIC'
        else:
            return 'UNKNOWN'
    
    def stage3_complete_material_reconstruction(self, texture_data: Dict) -> bool:
        """
        Stage 3: 完全なマテリアル再構築
        """
        print("🎨 Stage 3: Complete Material Reconstruction")
        
        texture_files = texture_data['texture_files']
        
        script_content = f'''
import bpy
import os

def reconstruct_complete_materials():
    try:
        # Load workspace
        bpy.ops.wm.open_mainfile(filepath="{self.stage1_blend}")
        
        # Clear existing materials (if any)
        for mat in list(bpy.data.materials):
            bpy.data.materials.remove(mat)
        
        # Create main material
        material = bpy.data.materials.new(name="M_Tucano_bird_material")
        material.use_nodes = True
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        
        # Clear default nodes
        nodes.clear()
        
        # Create Principled BSDF
        principled = nodes.new(type='ShaderNodeBsdfPrincipled')
        principled.location = (0, 0)
        
        # Create Material Output
        output = nodes.new(type='ShaderNodeOutputMaterial')
        output.location = (300, 0)
        
        # Connect Principled to Output
        links.new(principled.outputs['BSDF'], output.inputs['Surface'])
        
        # Texture file mapping
        texture_mapping = {texture_files}
        
        # Create texture nodes for each available texture
        texture_nodes = {{}}
        y_offset = 300
        
        for tex_name, tex_info in texture_mapping.items():
            tex_path = tex_info['path']
            tex_type = tex_info['type']
            
            if os.path.exists(tex_path):
                # Create Image Texture node
                tex_node = nodes.new(type='ShaderNodeTexImage')
                tex_node.location = (-400, y_offset)
                tex_node.name = f"TEX_{{tex_name}}"
                tex_node.label = f"{{tex_type}}_{{tex_name}}"
                
                # Load image
                try:
                    image = bpy.data.images.load(tex_path)
                    tex_node.image = image
                    print(f"📎 Loaded texture: {{tex_name}} ({{tex_type}})")
                    
                    # Connect to appropriate input
                    if tex_type == 'BASE_COLOR':
                        links.new(tex_node.outputs['Color'], principled.inputs['Base Color'])
                        print(f"   🔗 Connected to Base Color")
                    elif tex_type == 'NORMAL':
                        # Create Normal Map node
                        normal_map = nodes.new(type='ShaderNodeNormalMap')
                        normal_map.location = (-200, y_offset - 50)
                        links.new(tex_node.outputs['Color'], normal_map.inputs['Color'])
                        links.new(normal_map.outputs['Normal'], principled.inputs['Normal'])
                        print(f"   🔗 Connected to Normal (via Normal Map)")
                    elif tex_type == 'ROUGHNESS':
                        links.new(tex_node.outputs['Color'], principled.inputs['Roughness'])
                        print(f"   🔗 Connected to Roughness")
                    elif tex_type == 'METALLIC':
                        links.new(tex_node.outputs['Color'], principled.inputs['Metallic'])
                        print(f"   🔗 Connected to Metallic")
                    else:
                        print(f"   ⚠️ Unknown texture type: {{tex_type}}")
                    
                    texture_nodes[tex_name] = tex_node
                    
                except Exception as e:
                    print(f"❌ Failed to load texture {{tex_name}}: {{e}}")
                
                y_offset -= 200
        
        # Assign material to mesh objects
        assigned_count = 0
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                # Clear existing materials
                obj.data.materials.clear()
                # Assign new material
                obj.data.materials.append(material)
                assigned_count += 1
                print(f"🎨 Material assigned to: {{obj.name}}")
        
        # Save workspace
        bpy.ops.wm.save_as_mainfile(filepath="{self.stage3_blend}")
        
        print(f"✅ Stage 3 complete: {{len(texture_nodes)}} textures, {{assigned_count}} objects")
        return True
        
    except Exception as e:
        print(f"❌ Stage 3 error: {{e}}")
        import traceback
        traceback.print_exc()
        return False

result = reconstruct_complete_materials()
if result:
    print("Stage3Success")
else:
    print("Stage3Failed")
'''
        
        try:
            result = subprocess.run([
                "blender", "--background", "--python-expr", script_content
            ], capture_output=True, text=True, timeout=240)
            
            if "Stage3Success" in result.stdout:
                print("✅ Stage 3: Material reconstruction successful")
                return True
            else:
                print("❌ Stage 3: Material reconstruction failed")
                print("Stdout:", result.stdout[:2000] + "..." if len(result.stdout) > 2000 else result.stdout)
                return False
                
        except Exception as e:
            print(f"❌ Stage 3: Subprocess error: {e}")
            return False
    
    def stage4_material_assignment_validation(self) -> bool:
        """
        Stage 4: マテリアル割り当てと検証
        """
        print("🔗 Stage 4: Material Assignment & Validation")
        
        script_content = f'''
import bpy

def validate_material_assignment():
    try:
        # Load workspace
        bpy.ops.wm.open_mainfile(filepath="{self.stage3_blend}")
        
        # Validate material connections
        validation_passed = True
        
        for mat in bpy.data.materials:
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
            
            # Check critical connections
            base_color_connected = bool(principled.inputs['Base Color'].links)
            normal_connected = bool(principled.inputs['Normal'].links)
            roughness_connected = bool(principled.inputs['Roughness'].links)
            
            print(f"   🔗 Base Color: {{'✅' if base_color_connected else '❌'}}")
            print(f"   🔗 Normal: {{'✅' if normal_connected else '❌'}}")
            print(f"   🔗 Roughness: {{'✅' if roughness_connected else '❌'}}")
            
            if not (base_color_connected or normal_connected or roughness_connected):
                print(f"   ❌ No critical connections found")
                validation_passed = False
        
        # Check mesh assignments
        mesh_with_materials = 0
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                if obj.data.materials:
                    mesh_with_materials += 1
                    print(f"   ✅ {{obj.name}} has {{len(obj.data.materials)}} material(s)")
                else:
                    print(f"   ❌ {{obj.name}} has no materials")
                    validation_passed = False
        
        # Save validated workspace
        if validation_passed:
            bpy.ops.wm.save_as_mainfile(filepath="{self.stage4_blend}")
        
        print(f"🔗 Validation result: {{'PASSED' if validation_passed else 'FAILED'}}")
        print(f"🔗 Meshes with materials: {{mesh_with_materials}}")
        
        return validation_passed
        
    except Exception as e:
        print(f"❌ Stage 4 error: {{e}}")
        import traceback
        traceback.print_exc()
        return False

result = validate_material_assignment()
if result:
    print("Stage4Success")
else:
    print("Stage4Failed")
'''
        
        try:
            result = subprocess.run([
                "blender", "--background", "--python-expr", script_content
            ], capture_output=True, text=True, timeout=180)
            
            if "Stage4Success" in result.stdout:
                print("✅ Stage 4: Material validation successful")
                return True
            else:
                print("❌ Stage 4: Material validation failed")
                print("Stdout:", result.stdout)
                return False
                
        except Exception as e:
            print(f"❌ Stage 4: Subprocess error: {e}")
            return False
    
    def stage5_optimized_fbx_export(self) -> bool:
        """
        Stage 5: 最適化されたFBXエクスポート
        """
        print("📤 Stage 5: Optimized FBX Export")
        
        script_content = f'''
import bpy
import os

def optimized_fbx_export():
    try:
        # Load final workspace
        bpy.ops.wm.open_mainfile(filepath="{self.stage4_blend}")
        
        # Force pack all textures
        packed_count = 0
        for img in bpy.data.images:
            if img.name not in ['Render Result', 'Viewer Node']:
                try:
                    if not (hasattr(img, 'packed_file') and img.packed_file):
                        img.pack()
                        packed_count += 1
                        print(f"📦 Packed: {{img.name}} ({{img.size[0]}}x{{img.size[1]}})")
                    else:
                        print(f"✅ Already packed: {{img.name}}")
                except Exception as e:
                    print(f"❌ Failed to pack {{img.name}}: {{e}}")
        
        print(f"📦 Total packed images: {{packed_count}}")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname("{self.final_fbx}"), exist_ok=True)
        
        # Export FBX with enhanced texture embedding
        bpy.ops.export_scene.fbx(
            filepath="{self.final_fbx}",
            # Selection and objects
            use_selection=False,
            object_types={{'MESH', 'ARMATURE'}},
            # Texture embedding (CRITICAL)
            path_mode='COPY',           # Copy texture files
            embed_textures=True,        # Embed in FBX
            # Material and mesh settings
            use_mesh_modifiers=True,
            use_custom_props=True,
            # Animation and armature
            add_leaf_bones=True,
            use_armature_deform_only=True,
            bake_anim=False,
            # UV and tangent space
            use_tspace=True,
            # Smoothing and geometry
            mesh_smooth_type='FACE',
            use_mesh_edges=True,
            use_triangles=False,
            # Additional optimizations
            batch_mode='OFF',
            use_metadata=True
        )
        
        # Verify export
        if os.path.exists("{self.final_fbx}"):
            file_size = os.path.getsize("{self.final_fbx}")
            file_size_mb = file_size / (1024 * 1024)
            print(f"✅ FBX exported: {{file_size_mb:.2f}} MB")
            
            # Quality check
            if file_size_mb >= 7.0:
                print("✅ File size indicates successful texture embedding")
            elif file_size_mb >= 4.0:
                print("⚠️ File size indicates partial texture embedding")
            else:
                print("❌ File size indicates incomplete texture embedding")
            
            return True
        else:
            print("❌ FBX file not created")
            return False
        
    except Exception as e:
        print(f"❌ Stage 5 error: {{e}}")
        import traceback
        traceback.print_exc()
        return False

result = optimized_fbx_export()
if result:
    print("Stage5Success")
else:
    print("Stage5Failed")
'''
        
        try:
            result = subprocess.run([
                "blender", "--background", "--python-expr", script_content
            ], capture_output=True, text=True, timeout=300)
            
            if "Stage5Success" in result.stdout:
                print("✅ Stage 5: FBX export successful")
                return True
            else:
                print("❌ Stage 5: FBX export failed")
                print("Stdout:", result.stdout)
                return False
                
        except Exception as e:
            print(f"❌ Stage 5: Subprocess error: {e}")
            return False
    
    def stage6_comprehensive_quality_validation(self) -> Dict:
        """
        Stage 6: 包括的品質検証
        """
        print("🔍 Stage 6: Comprehensive Quality Validation")
        
        if not self.final_fbx.exists():
            return {"error": "Final FBX does not exist"}
        
        file_size = self.final_fbx.stat().st_size
        file_size_mb = file_size / (1024 * 1024)
        
        # Quality scoring
        score = "EXCELLENT"
        if file_size_mb < 4.0:
            score = "POOR"
        elif file_size_mb < 7.0:
            score = "NEEDS_IMPROVEMENT"
        
        report = {
            "final_fbx_path": str(self.final_fbx),
            "file_size_bytes": file_size,
            "file_size_mb": round(file_size_mb, 2),
            "quality_score": score,
            "expected_size_mb": "7.5-10.0",
            "texture_embedding_success": file_size_mb >= 7.0,
            "processing_stages_completed": 6
        }
        
        print(f"📊 Final Quality Report:")
        print(f"   📁 File: {self.final_fbx.name}")
        print(f"   📏 Size: {file_size_mb:.2f} MB")
        print(f"   🎯 Score: {score}")
        print(f"   ✅ Texture embedding: {'SUCCESS' if report['texture_embedding_success'] else 'FAILED'}")
        
        return report

def test_improved_safe_texture_restoration():
    """改良版SafeTextureRestorationのテスト"""
    print("🧪 Testing Improved Safe Texture Restoration")
    print("=" * 60)
    
    # Initialize system
    improved_system = ImprovedSafeTextureRestoration(
        working_dir="/app/pipeline_work",
        model_name="bird",
        use_subprocess=True
    )
    
    # Execute full restoration
    success, final_fbx, quality_report = improved_system.execute_full_restoration()
    
    if success:
        print("✅ Improved Safe Texture Restoration completed successfully!")
        print(f"📁 Final FBX: {final_fbx}")
        print(f"📊 Quality: {quality_report.get('quality_score', 'UNKNOWN')}")
        print(f"📏 Size: {quality_report.get('file_size_mb', 0):.2f} MB")
    else:
        print("❌ Improved Safe Texture Restoration failed")
        print(f"❌ Error: {quality_report.get('error', 'Unknown error')}")
    
    return success, final_fbx, quality_report

if __name__ == "__main__":
    test_improved_safe_texture_restoration()
