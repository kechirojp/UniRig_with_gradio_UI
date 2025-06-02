# GitHub Copilot Instructions for UniRig 3D Model Rigging Application

## 🎯 Application Purpose

This is a **3D Model Automatic Rigging Application** that processes 3D models (GLB/FBX/OBJ) to add skeletal rigging for animation purposes. The application provides a Gradio web interface for user-friendly operation.

## 📋 Standard User Workflow (Expected Behavior)

### 🔄 Basic User Expectation
```
INPUT: 3D Model with Textures (e.g., bird.glb with materials and textures)
↓
PROCESSING: Automatic Rigging (Mesh → Skeleton → Skinning → Final Output)
↓
OUTPUT: Rigged FBX with Original Textures and Materials Preserved
```

### 📊 Required Processing Pipeline

1. **Step 1: Mesh Extraction** (0-25% progress)
   - Extract mesh geometry from input model
   - Generate NPZ file with vertex/face data
   - **Critical**: Preserve material and texture information for later restoration

2. **Step 2: Skeleton Generation** (25-50% progress)
   - AI-driven skeleton structure prediction using UniRig
   - Generate optimal bone hierarchy for the model
   - Output: FBX skeleton, TXT bone data, NPZ skeleton data

3. **Step 3: Skinning Weight Prediction** (50-75% progress)
   - Calculate per-vertex bone weights automatically
   - Apply skinning to mesh using AI prediction
   - Output: Skinned FBX with rigging applied

4. **Step 4: Texture Integration & Final Merge** (75-100% progress)
   - **CRITICAL REQUIREMENT**: Restore original textures and materials
   - Merge skinned model with preserved texture data
   - Output: Final rigged FBX with complete texture fidelity

## 🚨 Critical Requirements (Minimum Standard Features)

### ✅ Essential Features (Must Work)
- **Texture Preservation**: Original textures MUST be maintained in final output
- **Material Integrity**: Material assignments and properties MUST be preserved
- **UV Mapping**: UV coordinates MUST remain intact through the pipeline
- **File Format Support**: GLB/FBX input → Rigged FBX output
- **Quality Assurance**: Final model should have same visual quality as input

### 🎯 User Experience Expectations
- **One-Click Operation**: Full pipeline automation via web interface
- **Visual Feedback**: 3D preview at each processing stage
- **Progress Tracking**: Real-time progress indicators (0-100%)
- **File Downloads**: Access to all intermediate and final files
- **Error Handling**: Clear error messages and recovery options

## 🔧 Technical Implementation Requirements

### 🗂️ File Processing Standards
```
Input Formats: .glb, .fbx, .obj, .gltf, .ply
Output Format: .fbx (rigged with textures)
Intermediate: .npz (data), .txt (bone info), .glb (preview)

Texture Size Requirements:
├── Individual Texture Files: 1-4MB each (PNG/JPG format)
├── Total Texture Package: 5-10MB combined
├── Final FBX Output: Input size + 1-3MB (rigging data + embedded textures)
└── Quality Threshold: Final FBX ≥ 75% of total texture size
```

### 📁 Directory Structure
```
/app/
├── pipeline_work/           # Processing workspace
│   ├── 01_extracted_mesh/   # Mesh extraction output
│   ├── 02_skeleton/         # Skeleton generation output
│   ├── 03_skinning/         # Skinning weight output
│   ├── 04_merge/           # Model merging output
│   ├── 05_texture_preservation/ # Texture backup/restore
│   ├── 06_blender_native/  # Blender native workflow (.blend files)
│   ├── 07_material_metadata/ # Material structure JSON storage
│   └── 08_final_output/    # Final rigged models with textures
├── proposed_blender_texture_flow.py # BlenderNativeTextureFlow implementation
└── examples/               # Sample input models
```

### 🎨 Texture Preservation System (Dual Flow Architecture)

#### 🔄 Primary Implementation: Blender Native Texture Flow
```python
# Four-tier Blender native texture preservation workflow
1. ANALYZE: Complete material structure analysis (Blender → Metadata JSON)
2. EXTRACT & APPLY: Skinning applied to mesh via Blender operations
3. RESTORE: Material node tree reconstruction from preserved metadata
4. OPTIMIZE: FBX-compatible export with texture path optimization
```

#### 🛡️ Secondary Implementation: Safe FBX-to-Blend Texture Flow (RECOMMENDED)
```python
# Six-stage safe texture preservation workflow (Post-Rigging Processing)
1. INPUT: Receive skinned FBX from UniRig pipeline (without textures)
2. CONVERT: Import skinned FBX → Create new .blend file with armature
3. ANALYZE: Load preserved JSON metadata from Step 1 (Mesh Extraction)
4. RESTORE: Reconstruct complete material node trees from metadata
5. ASSIGN: Apply materials to mesh with texture file connections
6. EXPORT: Final FBX with embedded textures and optimized settings
```

#### 🎯 Technical Implementation Goals
- **100% Material Fidelity**: Preserve all Blender material node connections
- **Native Format Advantage**: Use .blend files to maintain complete material data
- **Metadata-Based Recovery**: JSON storage of material structure for reconstruction
- **Safe Processing**: Process rigged models without interference to skinning data
- **FBX Export Optimization**: Smart texture path management for external compatibility

#### 🔧 Core Processing Architecture (Safe Flow)
```
SKINNED FBX INPUT (from UniRig Step 3)
↓
STAGE 1: Safe FBX Import to Blender
├── Import skinned FBX maintaining armature and vertex groups
├── Preserve mesh topology, UV coordinates, and skinning weights
├── Create clean .blend workspace for material processing
└── Verify skinning integrity after import
↓
STAGE 2: Material Metadata Recovery
├── Load preserved material metadata JSON from Step 1
├── Validate texture file availability in organized directory
├── Parse material node tree structure from metadata
└── Prepare texture file paths for reconnection
↓
STAGE 3: Material Node Tree Reconstruction
├── Create Blender materials from metadata specifications
├── Rebuild complete node tree structure (Principled BSDF + texture nodes)
├── Connect texture image nodes to preserved texture files
└── Validate material properties and UV mapping assignments
↓
STAGE 4: Material Assignment & Validation
├── Apply reconstructed materials to mesh objects
├── Verify texture assignments match original model visually
├── Check UV coordinate integrity through skinning transformation
└── Validate material slot assignments and mesh face connections
↓
STAGE 5: FBX Export Optimization
├── Configure FBX export settings for texture embedding
├── Apply texture packing and compression optimization
├── Ensure armature and skinning data preservation
└── Export final rigged FBX with complete texture integration
↓
STAGE 6: Quality Validation
├── File size verification (Expected: 7.5-10MB for bird.glb example)
├── Texture embedding confirmation (all texture files in FBX binary)
├── Visual quality comparison (input vs output model)
└── Skinning functionality validation in external software
```

#### 🔍 Safe Flow Advantages
- **Non-Destructive Processing**: Works with already-rigged models without interfering with skinning
- **Separation of Concerns**: Rigging and texturing handled independently for stability
- **Metadata-Driven Recovery**: Complete material reconstruction from JSON blueprints
- **Quality Assurance**: Multiple validation checkpoints throughout the process
- **Error Recovery**: Failed texture processing doesn't affect rigging quality
- **External Software Compatibility**: Optimized FBX export for animation software

#### 🛠️ Implementation Requirements
- **BlenderNativeTextureFlow Class**: Core processing class in `/app/proposed_blender_texture_flow.py`
- **Material Metadata Schema**: JSON structure for complete material preservation
- **Blender API Integration**: Native .blend file manipulation for maximum fidelity
- **Progressive Validation**: Stage-by-stage visual verification system

## 🚀 Code Development Guidelines

### 🎯 When Writing Code
- **Primary Goal**: Implement Blender Native Texture Flow as the standard texture preservation method
- **Core Implementation**: Utilize `/app/proposed_blender_texture_flow.py` as foundation for texture processing
- **Material Fidelity**: Preserve complete Blender material node structures, not just texture files
- **Progressive Processing**: Implement stage-by-stage verification with .blend file checkpoints
- **Error Handling**: Robust fallback mechanisms with metadata validation at each stage
- **Performance**: Optimize Blender Python API calls and memory management for large models
- **Logging**: Comprehensive progress reporting for each stage of the Blender native workflow

### 🔬 Blender Native Flow Validation
- **Material Structure Integrity**: Verify node tree preservation through metadata comparison
- **Texture Path Management**: Ensure texture file organization supports both Blender and FBX workflows  
- **UV Coordinate Consistency**: Validate UV mapping preservation through rigging transformations
- **Node Connection Accuracy**: Test material node reconnection from metadata reconstruction
- **FBX Export Quality**: Verify final export maintains visual fidelity with original model

### 🔍 Testing Requirements
- **Integration Tests**: Full pipeline validation with textured models
- **Quality Assurance**: Visual comparison between input and output models
- **Edge Cases**: Handle various file formats and texture configurations
- **Performance Tests**: Processing time optimization for different model sizes

### 📝 Documentation Standards
- **User-Facing**: Clear instructions for web interface operation
- **Developer-Facing**: Technical details about pipeline architecture
- **API Documentation**: Gradio endpoint specifications
- **Troubleshooting**: Common issues and resolution steps

## 🎨 UI/UX Design Principles

### 🖥️ Web Interface Requirements
- **Intuitive Upload**: Drag-and-drop file upload with format validation
- **Real-time Preview**: 3D model viewer at each processing stage
- **Progress Feedback**: Clear progress bars and status messages
- **Download Management**: Easy access to all generated files
- **Mobile Responsive**: Works on various screen sizes

### 🔄 Workflow Presentation
- **Full Pipeline Tab**: One-click automatic processing
- **Step-by-Step Tab**: Individual stage execution for debugging
- **Advanced Options**: Fine-tuning parameters for expert users

## 🛠️ Development Priorities

### 🥇 Priority 1: Safe FBX-to-Blend Texture Flow Implementation (RECOMMENDED)
1. **SafeTextureRestoration Class**: Implementation of the 6-stage post-rigging texture restoration
2. **Material Metadata Recovery System**: Complete JSON-based material reconstruction
3. **Progressive .blend Validation**: Stage-by-stage FBX → Blend → FBX processing
4. **Non-Destructive Skinning Preservation**: Maintain rigging integrity through texture processing

### 🥈 Priority 2: Blender Native Texture Flow Enhancement
1. **BlenderNativeTextureFlow Class**: Complete implementation of the 4-stage processing pipeline
2. **Material Metadata System**: JSON schema for complete material structure preservation
3. **Progressive .blend Checkpoints**: Stage-by-stage file validation and recovery points
4. **UniRig Pipeline Integration**: Seamless integration with existing rigging workflow

### 🥉 Priority 3: Core Functionality Enhancement  
1. Reliable texture preservation through dual-flow architecture
2. Stable rigging quality across different model types
3. Robust error handling with metadata-based recovery
4. Performance optimization for large model processing

### 🥉 Priority 3: User Experience & Advanced Features
1. Intuitive web interface operation
2. Clear progress feedback and logging
3. Comprehensive file download options

### 🥉 Priority 3: Advanced Features
1. Batch processing capabilities
2. Custom rigging parameters
3. Integration with external 3D software

## 🎯 Success Criteria

### ✅ Definition of Success
- User uploads textured 3D model → Gets rigged model with identical visual quality
- Zero texture loss through processing pipeline
- Processing completes without manual intervention
- Final FBX file is compatible with standard 3D animation software

### 📊 Quality Metrics
- **Texture Fidelity**: 100% preservation of original textures
- **Processing Speed**: Reasonable processing time for target model sizes
- **Success Rate**: >95% successful completion rate for supported formats
- **User Satisfaction**: Intuitive operation without technical expertise required

### 🔍 Texture Size Analysis & Quality Validation

#### 📏 Expected Texture Integration Metrics (Reference: bird.glb)
```
Original Texture Assets:
├── T_tucano_bird_col_v2_BC.png    → 3.6MB (Color/Diffuse)
├── T_tucano_bird_gloss6_R.png     → 2.2MB (Roughness/Gloss)
└── T_tucano_bird_nrml5_N.png      → 2.1MB (Normal Map)
    
Total Texture Size: 7.8MB
Expected Final FBX Size: ~8.5-10MB (with embedded textures)
Minimum Acceptable Size: 7.5MB (compressed embedded textures)
```

#### ⚠️ Current Issue Analysis
```
PROBLEM DETECTED:
├── Expected: 8.5-10MB final FBX (with embedded textures)
├── Current:  3.0MB final FBX → TEXTURE LOSS CONFIRMED
└── Missing:  ~5.8MB texture data (74% texture data loss)

ROOT CAUSE: Blender Native Texture Flow not fully embedding textures in FBX export
```

#### 🎯 Quality Validation Checklist
- **File Size Validation**: Final FBX ≥ 7.5MB (minimum acceptable)
- **Texture Embed Verification**: All 3 textures embedded in FBX binary
- **Material Node Preservation**: Complete Blender material node trees
- **UV Mapping Integrity**: Original UV coordinates maintained
- **Visual Quality Check**: Side-by-side comparison (input vs output)

#### 🔧 Debugging Priorities
1. **FBX Export Settings**: Verify texture embedding options in Blender export
2. **Material Node Connections**: Validate texture node links in final .blend
3. **Texture Path Resolution**: Ensure correct texture file references
4. **Memory Management**: Check for texture data loss during processing
5. **Binary Analysis**: Inspect FBX file structure for embedded texture data

#### 🛡️ Safe Flow Implementation Guidelines

##### 📁 Safe Flow Class Structure
```python
class SafeTextureRestoration:
    """
    Six-stage post-rigging texture restoration workflow
    Processes already-rigged FBX files without interfering with skinning data
    """
    
    def __init__(self, skinned_fbx_path: str, metadata_json_path: str, texture_dir: str):
        self.skinned_fbx = skinned_fbx_path
        self.material_metadata = metadata_json_path
        self.texture_directory = texture_dir
        
    def stage1_safe_fbx_import(self) -> str:
        """Import skinned FBX to clean .blend workspace"""
        # Import FBX with armature preservation
        # Validate skinning weights integrity
        # Return path to intermediate .blend file
        
    def stage2_metadata_recovery(self) -> dict:
        """Load and validate material metadata from Step 1"""
        # Parse JSON material structure
        # Validate texture file availability
        # Prepare texture path mappings
        
    def stage3_material_reconstruction(self) -> list:
        """Rebuild complete Blender material node trees"""
        # Create materials from metadata specifications
        # Connect texture nodes to preserved files
        # Validate node tree structure
        
    def stage4_material_assignment(self) -> bool:
        """Apply materials to mesh with validation"""
        # Assign materials to mesh objects
        # Verify UV coordinate integrity
        # Visual consistency checking
        
    def stage5_fbx_export_optimization(self) -> str:
        """Export final FBX with embedded textures"""
        # Configure FBX export settings for texture embedding
        # Apply texture packing optimization
        # Preserve armature and skinning data
        
    def stage6_quality_validation(self) -> dict:
        """Comprehensive output validation"""
        # File size verification (7.5-10MB threshold)
        # Texture embedding confirmation
        # Visual quality comparison
```

##### 🔧 Core Implementation Strategy
```python
# Integration with existing pipeline
def safe_texture_integration_workflow(skinned_fbx_path: str, model_name: str):
    """
    Safe post-rigging texture restoration
    Called after Step 3 (Skinning) completion
    """
    # Paths from established pipeline structure
    metadata_path = f"pipeline_work/01_extracted_mesh/{model_name}/materials_metadata.json"
    texture_dir = f"pipeline_work/01_extracted_mesh/{model_name}/textures/"
    output_dir = f"pipeline_work/08_final_output/{model_name}/"
    
    # Initialize safe restoration workflow
    safe_flow = SafeTextureRestoration(
        skinned_fbx_path=skinned_fbx_path,
        metadata_json_path=metadata_path,
        texture_dir=texture_dir
    )
    
    # Execute six-stage processing
    blend_workspace = safe_flow.stage1_safe_fbx_import()
    material_data = safe_flow.stage2_metadata_recovery()
    materials = safe_flow.stage3_material_reconstruction()
    assignment_success = safe_flow.stage4_material_assignment()
    final_fbx = safe_flow.stage5_fbx_export_optimization()
    validation_report = safe_flow.stage6_quality_validation()
    
    return final_fbx, validation_report
```

##### 🎯 Key Advantages of Safe Flow
- **Risk Mitigation**: No interference with existing rigging data
- **Modular Design**: Independent texture processing after rigging completion
- **Quality Assurance**: Multiple validation checkpoints prevent data loss
- **Debugging Friendly**: Clear separation allows isolated troubleshooting
- **Metadata-Driven**: Complete material reconstruction from preserved blueprints
- **External Compatibility**: Optimized FBX export for animation software integration

---
