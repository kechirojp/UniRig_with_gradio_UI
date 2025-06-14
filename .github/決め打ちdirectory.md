---
applyTo: '**'
---

/app/pipeline_work/{model_name}/
├── 00_asset_preservation/     # Step0: 元データ保存
├── 01_extracted_mesh/         # Step1: メッシュ抽出（汎用・アセット保持）
│   └── {model_name}_mesh.npz   # UV座標・マテリアル情報保持（Step5用）
├── 02_skeleton/               # Step2: スケルトン生成
│   ├── mesh_for_skeleton/     # Step2専用メッシュ（AI推論最適化）
│   │   └── raw_data.npz       # 面数4000・スケルトン生成特化
│   ├── {model_name}_skeleton.fbx
│   └── {model_name}_skeleton.npz
├── 03_skinning/               # Step3: スキニング適用
│   ├── mesh_for_skinning/     # Step3専用メッシュ（スキニング最適化）
│   │   └── raw_data.npz       # スキニング用再抽出メッシュ
│   ├── {model_name}_skinned.fbx
│   └── {model_name}_skinning.npz
├── 04_merge/                  # Step4: 骨・スキン統合
│   └── {model_name}_merged.fbx
└── 05_blender_integration/    # Step5: 最終成果物
    └── {model_name}_rigged.fbx ← これがユーザーが求める成果物

**重要な知見**: Step2とStep3は必ずオリジナルファイルからのメッシュ再抽出が必須
- Step2: AI推論最適化パラメータ（faces_target_count=4000）
- Step3: スキニング最適化パラメータ（faces_target_count=50000）
- Step1メッシュの流用は品質・互換性問題の原因となる

データを生成するスクリプトわかってんならそれをルールにしたがって改造しろ
それだけだけやれ