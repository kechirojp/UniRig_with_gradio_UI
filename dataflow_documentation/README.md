# 📊 UniRig データフロー ドキュメンテーション

このフォルダには、UniRigシステムのデータフロー分析・可視化ドキュメントが整理されています。

## 📋 ファイル一覧

### 🔸 [`original_flow_dataflow_mermaid.md`](./original_flow_dataflow_mermaid.md)
**原流処理スクリプトのデータフローマーメイド図**
- 対象: `launch/inference/*.sh` スクリプト群
- 内容: extract.sh → generate_skeleton.sh → generate_skin.sh → merge.sh の完全フロー
- 用途: 原流処理の理解・app.pyマイクロサービス設計の参考

### 🔸 [`app_dataflow_mermaid.md`](./app_dataflow_mermaid.md)
**app.pyマイクロサービス構成のデータフローマーメイド図**
- 対象: app.py内のStep0-Step5マイクロサービス風モジュール
- 内容: 6ステップマイクロサービス構成の詳細フロー
- 用途: 現行システムの理解・改良・デバッグ

### 🔸 [`original_flow_txt_outputs_mermaid.md`](./original_flow_txt_outputs_mermaid.md)
**原流処理における.txtファイル出力・後続活用マーメイド図**
- 対象: launch/inference/スクリプトが生成する.txtファイル群
- 内容: inference_datalist.txt, skeleton_pred.txt, bones.txt, weights.txt の詳細分析
- 用途: .txtファイルの役割理解・外部ツール連携設計

## 🎯 活用方法

### 📚 学習・理解用途
- **原流処理の理解**: `original_flow_dataflow_mermaid.md` で原流の完全フローを把握
- **現行システム把握**: `app_dataflow_mermaid.md` で6ステップ構成の詳細を理解
- **データ活用理解**: `original_flow_txt_outputs_mermaid.md` で.txtファイルの役割を把握

### 🔧 開発・改良用途
- **バグ修正**: 該当ステップのデータフロー図でボトルネック特定
- **機能追加**: 既存フローを理解した上での安全な機能拡張
- **パフォーマンス最適化**: データフローの無駄な処理の特定・改善

### 🌐 外部連携用途
- **API設計**: データフロー理解に基づく適切なAPI設計
- **ツール連携**: .txtファイル出力仕様の理解に基づく外部ツール開発
- **ドキュメント作成**: 正確なデータフロー情報に基づく技術文書作成

## 📈 技術的価値

### ✅ **システム理解の加速**
- 複雑なUniRigシステムの全体像を視覚的に把握
- 原流処理とapp.pyマイクロサービスの対応関係の理解

### ✅ **開発効率向上**
- データフロー図による効率的なデバッグ・改良作業
- 新機能開発時の影響範囲の事前把握

### ✅ **品質保証**
- データフロー理解に基づく適切なテスト設計
- システム変更時の影響範囲チェックリスト

---

**📝 作成日**: 2025年6月12日  
**📝 更新履歴**: 
- 2025年6月12日: 初版作成、3つのマーメイド図を統合整理
