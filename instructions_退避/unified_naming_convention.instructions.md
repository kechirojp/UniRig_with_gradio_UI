# 🎯 UniRig統一ファイル命名規則 - ユーザー中心設計

## 📋 基本原則

### 🎨 ユーザー体験最優先
```
ユーザーの期待: 
3Dモデル → [1クリック] → リギング済みFBX

不要な複雑さ:
- 分離された骨ファイルとスキンファイル  
- 予測困難な中間ファイル名
- 技術的制約による不整合
```

### 📄 統一命名規則（2025年6月改訂版）

#### 🔤 基本ファイル命名パターン
```
入力: {model_name}.glb (例: bird.glb)
└── 各ステップ出力:
    ├── Step1: {model_name}_mesh.npz        (bird_mesh.npz)
    ├── Step2: {model_name}_skeleton.fbx    (bird_skeleton.fbx)
    │          {model_name}_skeleton.npz    (bird_skeleton.npz)
    ├── Step3: {model_name}_skinned.fbx     (bird_skinned.fbx)
    │          {model_name}_skinning.npz    (bird_skinning.npz)
    ├── Step4: {model_name}_merged.fbx      (bird_merged.fbx)
    └── Step5: {model_name}_rigged.fbx      (bird_rigged.fbx) ← 最終成果物
```

#### 🎯 ユーザー向け最終成果物
```
最重要ファイル: {model_name}_rigged.fbx
- UV座標完全転送済み
- マテリアル・テクスチャ統合済み  
- スケルトン・スキンウェイト適用済み
- アニメーション可能状態
```

## 🔧 技術実装仕様

### 📁 固定ディレクトリ構造
```
/app/pipeline_work/{model_name}/
├── 00_asset_preservation/     # Step0: 元データ保存
├── 01_extracted_mesh/         # Step1: メッシュ抽出
│   └── {model_name}_mesh.npz
├── 02_skeleton/               # Step2: スケルトン生成
│   ├── {model_name}_skeleton.fbx
│   └── {model_name}_skeleton.npz
├── 03_skinning/               # Step3: スキニング適用
│   ├── {model_name}_skinned.fbx
│   └── {model_name}_skinning.npz
├── 04_merge/                  # Step4: 骨・スキン統合
│   └── {model_name}_merged.fbx
└── 05_blender_integration/    # Step5: 最終成果物
    └── {model_name}_rigged.fbx ← これがユーザーが求める成果物
```

### 🔍 源流処理統合要件

#### Config YAML統一仕様
```yaml
# スケルトン生成設定
writer:
  export_npz: predict_skeleton    # 固定名: スケルトンデータ
  export_fbx: skeleton_model      # 固定名: スケルトンFBX

# スキニング設定  
writer:
  export_npz: predict_skin        # 固定名: スキンデータ
  export_fbx: skinned_model       # 固定名: スキン適用FBX
```

#### Shell Script統一呼び出し
```bash
# 統一パラメータ渡し
generate_skeleton.sh "$input_file" "$output_dir" "$model_name"
generate_skin.sh "$mesh_file" "$skeleton_dir" "$output_dir" "$model_name"
merge.sh "$skeleton_fbx" "$skinned_fbx" "$output_dir" "$model_name"
```

## 🎨 ユーザー体験設計

### ✅ 理想的なユーザーフロー
```
1. ユーザー: 3Dモデルをアップロード
2. システム: [Processing...] 進捗表示
3. システム: "{model_name}_rigged.fbx ready for download!"
4. ユーザー: ダウンロード → 即座にアニメーションソフトで利用可能
```

### 🚫 避けるべき複雑さ
```
❌ 分離ファイルの個別提供:
   - "skeleton.fbx", "skinned.fbx"を別々にダウンロード
   - ユーザーが手動でマージ作業

❌ 技術的ファイル名の露出:
   - "predict_skeleton.npz", "raw_data.npz"
   - ユーザーには無関係な中間ファイル

❌ 不一致なファイル名:
   - 同じ処理で異なる命名規則
   - デバッグ困難、自動化阻害
```

## 🔧 実装チェックリスト

### 📋 Config YAML修正事項
- [ ] `quick_inference_skeleton_articulationxl_ar_256.yaml`: 統一命名適用
- [ ] `quick_inference_unirig_skin.yaml`: 重複定義除去、統一命名適用
- [ ] `quick_inference.yaml`: 基本設定確認

### 📋 Shell Script修正事項  
- [ ] `extract.sh`: 統一パラメータ対応
- [ ] `generate_skeleton.sh`: 統一出力名対応
- [ ] `generate_skin.sh`: 統一入出力名対応
- [ ] `merge.sh`: 統一パラメータ・出力名対応

### 📋 Python Module修正事項
- [ ] `src/data/extract.py`: 統一出力名対応
- [ ] `run.py`: config読み込み統一対応
- [ ] `src/inference/merge.py`: 統一入出力対応

### 📋 Step Module統合事項
- [ ] 全Step Module: 統一命名規則準拠
- [ ] 全Step Module: 固定ディレクトリ構造準拠
- [ ] 全Step Module: 源流処理との整合性確認

## 🚨 重要な設計原則

### 🎯 ユーザー中心主義
```
技術的制約 < ユーザー体験
複雑な内部処理 = シンプルな外部インターフェース
分離された中間成果物 = 統合された最終成果物
```

### 🔒 一貫性保証
```
同じ入力 = 同じ命名規則の出力
デバッグ可能 = 予測可能なファイル配置
拡張可能 = 統一されたインターフェース
```

### 🛡️ 堅牢性確保
```
ファイル存在チェック = シンプルな状態管理
エラー処理 = 明確なエラーメッセージ
回復処理 = 中間状態からの再実行可能
```

---

**この命名規則により、ユーザーは技術的な複雑さを意識することなく、高品質な3Dリギング成果物を確実に得ることができます。**
