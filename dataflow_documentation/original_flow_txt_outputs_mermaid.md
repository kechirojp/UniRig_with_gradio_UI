# 📋 原流処理スクリプト .txtファイル出力・後続活用 マーメイド図

## 🔍 原流処理における.txtファイルの生成・活用フロー

```mermaid
graph TB
    %% ========== Step 1: メッシュ抽出 ==========
    INPUT["🎯 入力3Dモデル<br>giraffe.glb"]
    
    %% extract.sh実行
    EXTRACT["⚙️ launch/inference/extract.sh<br>python -m src.data.extract<br>--config configs/data/quick_inference.yaml<br>--target_count 50000"]
    
    %% Step1出力ファイル
    RAW_NPZ["📦 raw_data.npz<br>メッシュ+スケルトンデータ"]
    DATALIST_TXT["📄 inference_datalist.txt<br>NPZファイルパス一覧"]
    
    %% ========== Step 2: スケルトン生成 ==========
    %% generate_skeleton.sh実行  
    SKELETON_EXTRACT["⚙️ メッシュ抽出再実行<br>python -m src.data.extract<br>raw_data.npz準備"]
    
    SKELETON_GEN["⚙️ python run.py<br>--task configs/task/skeleton<br>--npz_dir tmp"]
    
    %% Step2出力ファイル
    SKELETON_NPZ["📦 predict_skeleton.npz<br>53ボーンスケルトンデータ"]
    SKELETON_FBX["📦 giraffe_skeleton.fbx<br>3Dスケルトンモデル"]
    SKELETON_PRED_TXT["📄 skeleton_pred.txt<br>スケルトン座標・階層情報<br>53ジョイント詳細データ"]
    BONES_TXT["📄 model_name_bones.txt<br>ボーン階層テキスト<br>親子関係・名前一覧"]
    
    %% ========== Step 3: スキニング適用 ==========
    %% generate_skin.sh実行
    SKIN_EXTRACT["⚙️ メッシュ抽出再実行<br>bash launch/inference/extract.sh<br>メッシュデータ準備"]
    
    SKIN_GEN["⚙️ python run.py<br>--task configs/task/unirig_skin<br>--npz_dir dataset_inference_clean"]
    
    %% Step3出力ファイル
    SKINNED_FBX["📦 giraffe_skin.fbx<br>スキニング適用済みモデル"]
    WEIGHTS_TXT["📄 model_name_weights.txt<br>頂点ウェイト情報<br>7702頂点×42ボーン"]
    SKINNING_NPZ["📦 predict_skin.npz<br>スキニングウェイトデータ"]
    
    %% ========== Step 4: マージ処理 ==========
    MERGE["⚙️ launch/inference/merge.sh<br>python -m src.inference.merge<br>--source skeleton.fbx<br>--target original.glb"]
    
    %% Step4出力ファイル
    FINAL_FBX["📦 giraffe_rigged.glb<br>最終リギング済みモデル"]
    
    %% ========== データフロー接続 ==========
    INPUT --> EXTRACT
    EXTRACT --> RAW_NPZ
    EXTRACT --> DATALIST_TXT
    
    %% Step2フロー
    RAW_NPZ --> SKELETON_EXTRACT
    SKELETON_EXTRACT --> SKELETON_GEN
    SKELETON_GEN --> SKELETON_NPZ
    SKELETON_GEN --> SKELETON_FBX
    SKELETON_GEN --> SKELETON_PRED_TXT
    SKELETON_GEN --> BONES_TXT
    
    %% Step3フロー（Step2出力を活用）
    RAW_NPZ --> SKIN_EXTRACT
    SKELETON_NPZ --> SKIN_GEN
    SKIN_EXTRACT --> SKIN_GEN
    SKIN_GEN --> SKINNED_FBX
    SKIN_GEN --> WEIGHTS_TXT
    SKIN_GEN --> SKINNING_NPZ
    
    %% Step4フロー
    SKELETON_FBX --> MERGE
    INPUT --> MERGE
    MERGE --> FINAL_FBX
    
    %% ========== .txtファイルの詳細分析 ==========
    classDef txtFile fill:#ffe6cc,stroke:#ff9933,color:#000
    classDef npzFile fill:#e6f3ff,stroke:#3399ff,color:#000
    classDef fbxFile fill:#e6ffe6,stroke:#66cc66,color:#000
    classDef process fill:#f0f0f0,stroke:#333,color:#000
    
    class DATALIST_TXT,SKELETON_PRED_TXT,BONES_TXT,WEIGHTS_TXT txtFile
    class RAW_NPZ,SKELETON_NPZ,SKINNING_NPZ npzFile
    class SKELETON_FBX,SKINNED_FBX,FINAL_FBX fbxFile
    class EXTRACT,SKELETON_EXTRACT,SKELETON_GEN,SKIN_EXTRACT,SKIN_GEN,MERGE process
```

## 📄 .txtファイルの詳細内容・活用方法

### 🔸 Step 1 出力: `inference_datalist.txt`
```mermaid
graph LR
    A["📄 inference_datalist.txt"] --> B["📋 内容: NPZファイルパス一覧<br>/app/results/raw_data.npz"]
    B --> C["🎯 用途: 後続ステップでの<br>NPZファイル場所特定"]
    C --> D["⚙️ 活用: generate_skeleton.sh<br>generate_skin.sh が参照"]
```

**実際の内容例:**
```txt
/app/pipeline_work_fixed/01_extract/raw_data.npz
```

### 🔸 Step 2 出力: `skeleton_pred.txt`
```mermaid
graph LR
    A["📄 skeleton_pred.txt"] --> B["📋 内容: 53ジョイント座標<br>X Y Z 親インデックス 名前"]
    B --> C["🎯 用途: スケルトン構造の<br>詳細情報保存"]
    C --> D["⚙️ 活用: デバッグ・検証<br>外部ツール連携"]
```

**実際の内容例:**
```txt
# Skeleton Prediction Data
# Number of joints: 53
# Class: articulationxl
# Format: joint_index x y z parent_index name
0 0.003906 -0.027344 0.035156 -1 bone_0
1 0.003906 -0.066406 0.050781 0 bone_1
2 0.003906 -0.152344 0.074219 1 bone_2
...（53ボーン分）
```

### 🔸 Step 2 出力: `{model_name}_bones.txt`
```mermaid
graph LR
    A["📄 giraffe_bones.txt"] --> B["📋 内容: ボーン階層情報<br>親子関係・名前一覧"]
    B --> C["🎯 用途: ボーン構造の<br>可読形式での保存"]
    C --> D["⚙️ 活用: アニメーション制作<br>リギング検証"]
```

**実際の内容例:**
```txt
# Bone Hierarchy for giraffe
# Total bones: 53
Bone  0: bone_0 (root)
Bone  1: bone_1 (parent: bone_0)
Bone  2: bone_2 (parent: bone_1)
...（53ボーン分の階層情報）
```

### 🔸 Step 3 出力: `{model_name}_weights.txt`
```mermaid
graph LR
    A["📄 giraffe_weights.txt"] --> B["📋 内容: 頂点ウェイト情報<br>7702頂点×最大4ボーン影響"]
    B --> C["🎯 用途: スキニングウェイト<br>詳細データ保存"]
    C --> D["⚙️ 活用: ウェイトペイント調整<br>スキニング品質検証"]
```

**実際の内容例:**
```txt
# Skinning Weight Information
# Vertex count: 7702
# Bone count: 42
# Max influences per vertex: 4
vertex_0000: bone_19=0.261 bone_21=0.252 bone_40=0.250 bone_33=0.237
vertex_0001: bone_36=0.255 bone_00=0.254 bone_17=0.253 bone_18=0.237
...（7702頂点分のウェイト情報）
```

## 🔄 .txtファイルの後続ステップでの活用パターン

```mermaid
flowchart TD
    %% .txtファイル活用フロー
    subgraph TXT_USAGE[".txtファイル活用パターン"]
        direction TB
        
        %% 内部活用
        subgraph INTERNAL["🔧 内部処理活用"]
            DATALIST_READ["📄 datalist.txt読み込み<br>→ NPZファイルパス取得"]
            SKELETON_DEBUG["📄 skeleton_pred.txt<br>→ デバッグ・検証"]
            WEIGHTS_VERIFY["📄 weights.txt<br>→ スキニング品質検証"]
        end
        
        %% 外部ツール連携
        subgraph EXTERNAL["🌐 外部ツール連携"]
            BLENDER_IMPORT["📄 bones.txt<br>→ Blender手動インポート"]
            MAYA_EXPORT["📄 skeleton_pred.txt<br>→ Maya/3ds Max連携"]
            CUSTOM_TOOLS["📄 weights.txt<br>→ カスタムツール開発"]
        end
        
        %% 品質保証
        subgraph QA["✅ 品質保証"]
            BONE_COUNT["📄 bones.txt<br>→ ボーン数検証"]
            WEIGHT_ANALYSIS["📄 weights.txt<br>→ ウェイト分布分析"]
            HIERARCHY_CHECK["📄 skeleton_pred.txt<br>→ 階層構造チェック"]
        end
    end
    
    %% 接続関係
    DATALIST_READ --> SKELETON_DEBUG
    SKELETON_DEBUG --> WEIGHTS_VERIFY
    
    BLENDER_IMPORT --> BONE_COUNT
    MAYA_EXPORT --> HIERARCHY_CHECK
    CUSTOM_TOOLS --> WEIGHT_ANALYSIS
```

## 📊 .txtファイル生成タイミング・容量・用途一覧

| ステップ | ファイル名 | 生成タイミング | 典型的サイズ | 主要用途 |
|---------|------------|---------------|-------------|----------|
| **Step 1** | `inference_datalist.txt` | extract.sh完了時 | ~100B | NPZファイルパス管理 |
| **Step 2** | `skeleton_pred.txt` | ARWriter.write_on_batch_end() | ~5KB | スケルトン座標詳細 |
| **Step 2** | `{model_name}_bones.txt` | スケルトン生成完了時 | ~2KB | ボーン階層情報 |
| **Step 3** | `{model_name}_weights.txt` | SkinWriter.write_on_batch_end() | ~500KB | 頂点ウェイト詳細 |

## 🎯 重要な技術的洞察

### 1. **ファイル間依存関係**
- `datalist.txt` → 全後続ステップでのNPZファイル発見
- `skeleton_pred.txt` → 外部ツールとのデータ交換
- `weights.txt` → スキニング品質の詳細検証

### 2. **命名規則の一貫性**
```bash
# 固定命名パターン
inference_datalist.txt          # 常に固定名
skeleton_pred.txt              # 常に固定名  
{model_name}_bones.txt         # モデル名プレフィックス
{model_name}_weights.txt       # モデル名プレフィックス
```

### 3. **後続ステップでの実際の参照方法**
```python
# datalist.txt の活用例
with open("inference_datalist.txt", "r") as f:
    npz_path = f.read().strip()
    
# skeleton_pred.txt の活用例
skeleton_data = []
with open("skeleton_pred.txt", "r") as f:
    for line in f:
        if line.startswith("#"): continue
        joint_data = line.strip().split()
        skeleton_data.append({
            "index": int(joint_data[0]),
            "position": [float(joint_data[1]), float(joint_data[2]), float(joint_data[3])],
            "parent": int(joint_data[4]) if joint_data[4] != "-1" else None,
            "name": joint_data[5]
        })

# weights.txt の活用例  
vertex_weights = {}
with open(f"{model_name}_weights.txt", "r") as f:
    for line in f:
        if line.startswith("vertex_"):
            vertex_id = line.split(":")[0]
            weights = line.split(":")[1].strip().split()
            vertex_weights[vertex_id] = {
                bone.split("=")[0]: float(bone.split("=")[1]) 
                for bone in weights
            }
```

---

**📝 注記**: このドキュメントは`README_ORIGINAL.md`および原流処理スクリプト（`launch/inference/*.sh`）の詳細分析に基づいています。実際の.txtファイルサンプルは`pipeline_work_fixed/`配下で確認済みです。
