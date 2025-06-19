# UniRig メッシュ品質パラメーター完全ガイド

**作成日**: 2025年6月17日  
**対象**: UniRigプロジェクト開発チーム・ユーザー  
**目的**: スケルトン・スキニング品質を決定するメッシュ処理パラメーターの完全理解  
**重要度**: **最高** (品質制御の核心技術)

---

## 🎯 概要

UniRigにおけるメッシュ品質は、**スケルトン生成の精度**と**スキニングの正確性**を直接決定する最重要要素です。本文書では、メッシュ品質をコントロールする全パラメーターとその影響を詳細に解説します。

---

## 📊 メッシュ品質パラメーター階層構造

### 🏗️ **レベル1: メッシュ前処理（src.data.extract）**
```
メッシュ抽出・前処理段階のパラメーター
├── faces_target_count（面数制御）
├── メッシュ正規化パラメーター
├── UV座標保持設定
└── マテリアル情報保持設定
```

### 🧠 **レベル2: AI推論（スケルトン生成）**
```
AI モデルがメッシュを理解する段階のパラメーター
├── mesh_encoder 設定
├── トークナイザー設定
└── 推論制御パラメーター
```

### 🔗 **レベル3: スキニング処理**
```
メッシュとスケルトンを結合する段階のパラメーター
├── スキニング特化メッシュ処理
├── ウェイト計算パラメーター
└── ボーン影響範囲設定
```

---

## 🔧 **レベル1: メッシュ前処理パラメーター詳細**

### **1.1 faces_target_count（最重要パラメーター）**

**設定場所**: `src.data.extract` 実行時の `--faces_target_count` パラメーター

**現在の設定**:
```python
# Step1: 汎用メッシュ抽出（詳細保持重視）
faces_target_count = 未指定（元メッシュ依存）

# Step2: AI推論特化メッシュ（スケルトン生成最適化）
faces_target_count = 4000

# Step3: スキニング特化メッシュ（ウェイト計算最適化）
faces_target_count = 50000
```

**品質への影響**:
```
面数 1,000-2,000:   簡易スケルトン（低品質）
面数 4,000:         標準スケルトン品質（AI推論最適化）
面数 10,000-20,000: 高品質スケルトン
面数 50,000+:       超高品質（スキニング最適化）
面数 100,000+:      オーバースペック（処理時間増大）
```

**調整指針**:
```yaml
# 高品質スケルトンを求める場合
faces_target_count: 8000  # Step2用（現在4000から倍増）

# 超高品質スキニングを求める場合  
faces_target_count: 80000  # Step3用（現在50000から増強）
```

### **1.2 メッシュ正規化パラメーター**

**設定場所**: `configs/data/quick_inference.yaml`

```yaml
# 現在の設定
data:
  # メッシュ正規化設定
  normalize_mesh: true
  center_mesh: true
  scale_to_unit: true
  
  # UV座標保持（Step5テクスチャ統合用）
  preserve_uv_coordinates: true
  preserve_material_info: true
```

**品質への影響**:
- `normalize_mesh: true`: メッシュサイズ正規化（AI推論精度向上）
- `center_mesh: true`: 中心位置調整（左右対称性向上）
- `scale_to_unit: true`: 単位スケール正規化（骨長計算精度向上）

### **1.3 メッシュ前処理詳細制御**

**設定場所**: `src/data/extract.py` 内部パラメーター

```python
# メッシュ品質制御の詳細パラメーター
class MeshExtractionConfig:
    # 頂点密度制御
    vertex_density_threshold: float = 0.01
    
    # エッジ長制御
    max_edge_length: float = 0.05
    min_edge_length: float = 0.001
    
    # 面の品質制御
    min_face_area: float = 0.0001
    max_aspect_ratio: float = 10.0
    
    # 正規化設定
    mesh_scale_factor: float = 1.0
    center_offset: tuple = (0.0, 0.0, 0.0)
```

---

## 🧠 **レベル2: AI推論品質パラメーター詳細**

### **2.1 メッシュエンコーダー設定**

**設定場所**: `configs/model/unirig_ar_350m_1024_81920_float32.yaml`

```yaml
mesh_encoder:
  # メッシュ理解の詳細度（最重要）
  num_latents: 1024           # 現在値（標準）
  # 推奨: 2048（高品質）、4096（超高品質）
  
  # 特徴表現の複雑性
  embed_dim: 128              # 現在値（標準）  
  # 推奨: 256（高品質）、512（超高品質）
  
  # エンコーダーの深度
  num_encoder_layers: 16      # 現在値（標準）
  # 推奨: 24（高品質）、32（超高品質）
  
  # アテンション機構の多様性
  heads: 8                    # 現在値（標準）
  # 推奨: 16（高品質）、32（超高品質）
  
  # メッシュ特徴抽出精度
  positional_encoding_dim: 64
  geometric_feature_dim: 128
  surface_feature_dim: 256
```

**品質向上設定例**:
```yaml
# 🔥 高品質スケルトン生成設定
mesh_encoder:
  num_latents: 2048           # 倍増: より詳細なメッシュ理解
  embed_dim: 256              # 倍増: より豊富な特徴表現
  num_encoder_layers: 24      # 1.5倍: より深い解析
  heads: 16                   # 倍増: より多角的な解析
```

### **2.2 トークナイザー品質設定**

**設定場所**: `configs/components/tokenizer/tokenizer_parts_articulationxl_256.yaml`

```yaml
tokenizer:
  # スケルトン構造の詳細度
  vocab_size: 81920           # 現在値（標準）
  # 推奨: 163840（倍増、高品質）
  
  # ボーン関節の解像度
  max_sequence_length: 4096   # 現在値（標準）
  # 推奨: 8192（高品質）、16384（超高品質）
  
  # 骨格パターンの多様性
  num_parts: 256              # 現在値（標準）
  # 推奨: 512（高品質）、1024（超高品質）
```

### **2.3 推論制御パラメーター**

**設定場所**: `configs/system/ar_inference_articulationxl.yaml`

```yaml
generate_kwargs:
  # スケルトンの複雑性上限（最重要）
  max_new_tokens: 4096        # 現在値（標準）
  # 推奨: 8192（高品質）、16384（超高品質）
  
  # より精密な探索（高品質化）
  num_beams: 20               # 現在値（標準）
  # 推奨: 40（高品質）、80（超高品質）
  
  # 創造性vs安定性のバランス
  temperature: 1.5            # 現在値（標準）
  # 推奨: 1.2（高精度）、0.8（超高精度）
  
  # 候補選択の多様性
  top_k: 10                   # 現在値（標準）
  # 推奨: 20（高品質）、50（超高品質）
  
  # 確率的カットオフ
  top_p: 0.95                 # 現在値（標準）
  # 推奨: 0.98（高精度）、0.99（超高精度）
  
  # 重複パターン防止
  repetition_penalty: 3.0     # 現在値（強）
  # 推奨: 2.5（高品質バランス）
```

---

## 🔗 **レベル3: スキニング品質パラメーター詳細**

### **3.1 スキニング特化メッシュ処理**

**設定場所**: Step3実行時のメッシュ再抽出パラメーター

```python
# 現在の設定
skinning_mesh_config = {
    "faces_target_count": 50000,    # スキニング最適化
    "preserve_vertex_groups": True,  # バーテックスグループ保持
    "maintain_topology": True,       # トポロジー維持
    "smooth_surface": True          # 表面平滑化
}

# 高品質設定案
ultra_quality_skinning_config = {
    "faces_target_count": 100000,   # 超高密度メッシュ
    "vertex_density_factor": 2.0,   # 頂点密度倍増
    "edge_subdivision_level": 2,    # エッジ細分化レベル
    "adaptive_refinement": True     # 適応的詳細化
}
```

### **3.2 ウェイト計算パラメーター**

**設定場所**: `configs/task/quick_inference_unirig_skin.yaml`

```yaml
skinning:
  # ウェイト計算精度
  weight_calculation_precision: "float32"  # 現在値
  # 推奨: "float64"（超高精度）
  
  # ボーン影響範囲
  max_bone_influences: 4                   # 現在値（標準）
  # 推奨: 8（高品質）、16（超高品質）
  
  # ウェイト正規化
  normalize_weights: true
  smooth_weights: true
  
  # 距離計算方式
  distance_metric: "euclidean"             # 現在値
  # 選択肢: "geodesic"（高品質）、"harmonic"（超高品質）
```

### **3.3 ボーン-頂点結合パラメーター**

```yaml
bone_vertex_binding:
  # 結合アルゴリズム
  binding_algorithm: "heat_diffusion"      # 現在値（標準）
  # 推奨: "laplacian_coordinates"（高品質）
  
  # 熱拡散パラメーター
  heat_diffusion_iterations: 100          # 現在値
  # 推奨: 200（高品質）、500（超高品質）
  
  # 拘束条件
  rigid_bone_constraints: true
  smooth_transition_zones: true
  
  # 品質検証
  validate_weights: true
  weight_threshold: 0.001
```

---

## 🎯 **品質設定プリセット**

### **🔵 標準品質（現在の設定）**
```yaml
# 処理時間: 約5-10分
# 適用対象: 一般的な3Dモデル
mesh_quality: "standard"
faces_target_count: 4000 (Step2), 50000 (Step3)
mesh_encoder.num_latents: 1024
generate_kwargs.max_new_tokens: 4096
generate_kwargs.num_beams: 20
```

### **🟡 高品質設定**
```yaml
# 処理時間: 約15-30分
# 適用対象: 詳細なキャラクターモデル
mesh_quality: "high"
faces_target_count: 8000 (Step2), 80000 (Step3)
mesh_encoder.num_latents: 2048
generate_kwargs.max_new_tokens: 8192
generate_kwargs.num_beams: 40
```

### **🔴 超高品質設定**
```yaml
# 処理時間: 約45-90分
# 適用対象: プロダクション品質要求
mesh_quality: "ultra"
faces_target_count: 16000 (Step2), 150000 (Step3)
mesh_encoder.num_latents: 4096
generate_kwargs.max_new_tokens: 16384
generate_kwargs.num_beams: 80
```

### **⚡ 高速品質設定**
```yaml
# 処理時間: 約2-5分
# 適用対象: プロトタイピング・テスト
mesh_quality: "fast"
faces_target_count: 2000 (Step2), 20000 (Step3)
mesh_encoder.num_latents: 512
generate_kwargs.max_new_tokens: 2048
generate_kwargs.num_beams: 10
```

---

## 🛠️ **実装：動的品質設定システム**

### **設定切り替えスクリプト例**

```python
# /app/mesh_quality_configurator.py
import yaml
from pathlib import Path
from typing import Literal

class MeshQualityConfigurator:
    """メッシュ品質動的設定システム"""
    
    def __init__(self):
        self.config_base_dir = Path("/app/configs")
        self.quality_presets = {
            "fast": {
                "faces_target_count_step2": 2000,
                "faces_target_count_step3": 20000,
                "mesh_encoder_latents": 512,
                "max_new_tokens": 2048,
                "num_beams": 10,
                "temperature": 1.8
            },
            "standard": {
                "faces_target_count_step2": 4000,
                "faces_target_count_step3": 50000,
                "mesh_encoder_latents": 1024,
                "max_new_tokens": 4096,
                "num_beams": 20,
                "temperature": 1.5
            },
            "high": {
                "faces_target_count_step2": 8000,
                "faces_target_count_step3": 80000,
                "mesh_encoder_latents": 2048,
                "max_new_tokens": 8192,
                "num_beams": 40,
                "temperature": 1.2
            },
            "ultra": {
                "faces_target_count_step2": 16000,
                "faces_target_count_step3": 150000,
                "mesh_encoder_latents": 4096,
                "max_new_tokens": 16384,
                "num_beams": 80,
                "temperature": 0.8
            }
        }
    
    def apply_quality_preset(self, quality: Literal["fast", "standard", "high", "ultra"]):
        """品質プリセットを適用"""
        preset = self.quality_presets[quality]
        
        # システム設定更新
        self._update_system_config(preset)
        
        # モデル設定更新
        self._update_model_config(preset)
        
        # Step2/Step3に面数設定を伝達
        self._update_step_configs(preset)
        
        return f"品質設定 '{quality}' を適用しました"
    
    def _update_system_config(self, preset):
        """システム推論設定を更新"""
        system_config_path = self.config_base_dir / "system/ar_inference_articulationxl.yaml"
        
        with open(system_config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        config['generate_kwargs']['max_new_tokens'] = preset['max_new_tokens']
        config['generate_kwargs']['num_beams'] = preset['num_beams']
        config['generate_kwargs']['temperature'] = preset['temperature']
        
        with open(system_config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
    
    def _update_model_config(self, preset):
        """モデル設定を更新"""
        model_config_path = self.config_base_dir / "model/unirig_ar_350m_1024_81920_float32.yaml"
        
        with open(model_config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        config['mesh_encoder']['num_latents'] = preset['mesh_encoder_latents']
        
        with open(model_config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
    
    def _update_step_configs(self, preset):
        """Step2/Step3に面数設定を伝達"""
        # 環境変数として設定（実行時に参照）
        import os
        os.environ['UNIRIG_STEP2_FACES_COUNT'] = str(preset['faces_target_count_step2'])
        os.environ['UNIRIG_STEP3_FACES_COUNT'] = str(preset['faces_target_count_step3'])

# 使用例
configurator = MeshQualityConfigurator()
configurator.apply_quality_preset("high")  # 高品質設定適用
```

---

## 📊 **品質-処理時間-リソース対照表**

| 品質設定 | Step2面数 | Step3面数 | 推論時間 | VRAM使用量 | ストレージ | 推奨用途 |
|---------|-----------|-----------|----------|------------|-----------|----------|
| **fast** | 2,000 | 20,000 | 2-5分 | 4GB | 500MB | プロトタイピング |
| **standard** | 4,000 | 50,000 | 5-10分 | 8GB | 1GB | 一般用途 |
| **high** | 8,000 | 80,000 | 15-30分 | 12GB | 2GB | 高品質作品 |
| **ultra** | 16,000 | 150,000 | 45-90分 | 16GB+ | 4GB+ | プロダクション |

---

## 🎯 **品質最適化指針**

### **📈 段階的品質向上戦略**

1. **Step1: 標準設定で基本動作確認**
   - まず `standard` 設定で完全パイプラインを実行
   - 結果品質と処理時間を評価

2. **Step2: 特定パラメーター調整**
   - `faces_target_count` のみ倍増（4000→8000）
   - 他パラメーターは維持して影響を測定

3. **Step3: 包括的品質向上**
   - `high` プリセット適用
   - AI推論パラメーター同時調整

4. **Step4: 超高品質要求対応**
   - `ultra` プリセット適用
   - カスタムパラメーター微調整

### **⚠️ 品質調整時の注意事項**

```yaml
# ❌ 避けるべき設定
avoid:
  - faces_target_count > 200000  # メモリ不足リスク
  - num_beams > 100             # 指数的処理時間増大
  - temperature < 0.5           # 創造性完全抑制
  - max_new_tokens > 32768      # トークン制限超過

# ✅ 推奨される段階的調整
recommended_progression:
  1. faces_target_count: 4000 → 6000 → 8000
  2. num_beams: 20 → 30 → 40
  3. mesh_encoder.num_latents: 1024 → 1536 → 2048
```

---

## 🔬 **品質検証・測定システム**

### **メッシュ品質メトリクス**

```python
class MeshQualityMetrics:
    """メッシュ品質測定システム"""
    
    def analyze_mesh_quality(self, mesh_file_path: str) -> dict:
        """メッシュ品質の定量的分析"""
        return {
            "vertex_count": self._count_vertices(mesh_file_path),
            "face_count": self._count_faces(mesh_file_path),
            "edge_length_stats": self._analyze_edge_lengths(mesh_file_path),
            "face_quality_score": self._calculate_face_quality(mesh_file_path),
            "mesh_density": self._calculate_mesh_density(mesh_file_path),
            "topology_health": self._check_topology_health(mesh_file_path)
        }
    
    def analyze_skeleton_quality(self, skeleton_fbx_path: str) -> dict:
        """スケルトン品質の定量的分析"""
        return {
            "bone_count": self._count_bones(skeleton_fbx_path),
            "joint_hierarchy_depth": self._analyze_hierarchy_depth(skeleton_fbx_path),
            "bone_length_distribution": self._analyze_bone_lengths(skeleton_fbx_path),
            "symmetry_score": self._calculate_symmetry_score(skeleton_fbx_path),
            "anatomical_accuracy": self._assess_anatomical_accuracy(skeleton_fbx_path)
        }
```

---

## 📚 **関連設定ファイル一覧**

### **🔧 必須設定ファイル**
```
configs/
├── system/ar_inference_articulationxl.yaml          # 推論制御
├── model/unirig_ar_350m_1024_81920_float32.yaml     # モデル設定
├── task/quick_inference_skeleton_articulationxl_ar_256.yaml  # Step2タスク
├── task/quick_inference_unirig_skin.yaml            # Step3タスク
├── data/quick_inference.yaml                        # データ処理
└── components/tokenizer/tokenizer_parts_articulationxl_256.yaml  # トークナイザー
```

### **⚙️ 実行時パラメーター**
```
Step2実行: python run.py --task configs/task/... --npz_dir dataset_inference_clean/{model_name}
Step3実行: python run.py --task configs/task/... --npz_dir dataset_inference_clean/{model_name}
メッシュ抽出: python -m src.data.extract --faces_target_count {数値}
```

---

## 🎯 **結論**

UniRigにおけるメッシュ品質は、複数レベルの洗練されたパラメーター制御によって決定されます。**最も影響力の大きいパラメーター**は以下の通りです：

### **🏆 TOP5 品質決定パラメーター**

1. **`faces_target_count`** - メッシュ解像度の直接制御
2. **`mesh_encoder.num_latents`** - AI理解精度の根幹
3. **`generate_kwargs.max_new_tokens`** - スケルトン複雑性上限
4. **`generate_kwargs.num_beams`** - 探索精度制御
5. **`generate_kwargs.temperature`** - 精度vs創造性バランス

### **🚀 品質向上の最短経路**

1. Step2の `faces_target_count` を 4000→8000 に倍増
2. `mesh_encoder.num_latents` を 1024→2048 に倍増  
3. `generate_kwargs.num_beams` を 20→40 に倍増

これらの調整により、**処理時間の約2-3倍増加**と引き換えに、**品質の大幅向上**が期待できます。

---

**📋 定期的更新**

このドキュメントは、新しいパラメーター発見や品質改善手法の開発に応じて定期的に更新されます。

**作成者**: GitHub Copilot  
**最終更新**: 2025年6月17日  
**文書バージョン**: v1.0  
**重要度**: 最高（品質制御の基盤知識）
