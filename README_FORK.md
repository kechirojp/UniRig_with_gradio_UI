# UniRig Gradio WebUI Fork

This is a private fork of the [UniRig](https://github.com/VAST-AI-Research/UniRig) repository with a complete Gradio web interface implementation for 3D model rigging automation.

## 🎯 Fork Purpose

**Private Repository for Version Control Only**  
- 🔒 **Private Repository**: Not for public distribution
- 📦 **Version Management**: Track development progress and changes
- 🚀 **Feature Extension**: Full pipeline Gradio web interface
- 🔧 **Development Environment**: Docker-based containerized deployment

## ✨ Added Features

### 🖥️ Complete Gradio Web Interface
- **Full Pipeline Automation**: One-click 3D model rigging from GLB/FBX to rigged FBX
- **Individual Stage Processing**: Mesh extraction, skeleton generation, skinning, model merging
- **Real-time Progress Tracking**: Multi-stage progress indicators
- **Interactive 3D Viewer**: Preview models at each processing stage
- **Download Management**: Access all intermediate and final files

### 🐳 Production-Ready Deployment
- **Docker Container**: CUDA 12.1 + Blender 4.2 environment
- **Automated Setup**: Complete dependency management
- **Optimized Performance**: GPU-accelerated AI processing
- **Blender Integration**: FBX/GLB conversion pipeline

### 🔧 Enhanced Processing Pipeline
- **Error Handling**: Robust failure recovery and logging
- **File Management**: Organized workspace and temporary file cleanup
- **Configuration System**: YAML-based settings management
- **Testing Suite**: Comprehensive validation and verification

## 📋 Original UniRig Information

**Base Repository**: [VAST-AI-Research/UniRig](https://github.com/VAST-AI-Research/UniRig)  
**Paper**: [One Model to Rig Them All: Diverse Skeleton Rigging with UniRig](https://arxiv.org/abs/2504.12451)  
**License**: MIT License  

### Original Features
- ✅ **Automated Skeleton Generation**: AI-driven skeleton structure prediction
- ✅ **Automated Skinning**: Per-vertex weight prediction
- 🎯 **Unified Framework**: Handles diverse model categories (humans, animals, objects)
- 🏆 **State-of-the-art**: High accuracy on challenging datasets

## 🚀 Quick Start

### Prerequisites
- Docker with GPU support
- NVIDIA Container Toolkit
- Git LFS

### Running the Application
```bash
# Build and run the container
docker build -t unirig-gradio .
docker run --gpus all -p 7860:7860 -v $(pwd):/app unirig-gradio

# Start the Gradio interface
python app.py
```

### Access the Web Interface
- Open browser: `http://localhost:7860`
- Upload a 3D model (GLB/FBX)
- Select gender parameter
- Click "フルパイプライン実行" for complete automation

## 📁 Repository Structure

```
/app/
├── app.py                 # Main Gradio application
├── Dockerfile            # Container configuration
├── requirements.txt      # Python dependencies
├── configs/              # Configuration files
├── src/                  # UniRig core implementation
├── blender/             # Blender integration scripts
├── examples/            # Sample 3D models
└── docs/                # Documentation
```

## 🔄 Development Status

**Current Version**: Fully functional web interface  
**Pipeline Status**: Complete automation working  
**Testing**: Comprehensive validation passed  
**Performance**: Optimized for production use  

## 📝 Version History

This fork maintains detailed version control for:
- Gradio interface development iterations
- Pipeline optimization improvements
- Bug fixes and stability enhancements
- Performance tuning and optimization

## ⚠️ Important Notes

- **Private Use Only**: This repository is not intended for public distribution
- **Educational Purpose**: For learning and development version control
- **Original Credit**: All core AI functionality belongs to the original UniRig authors
- **MIT License**: Respects original licensing terms

## 🤝 Original Authors Credit

**UniRig Framework**: Developed by Tsinghua University and [Tripo](https://www.tripo3d.ai)  
**Research Team**: VAST-AI-Research  
**Publication**: SIGGRAPH'25 (TOG)

---

*This is a development fork for version control and learning purposes. Please refer to the original repository for official releases and updates.*
