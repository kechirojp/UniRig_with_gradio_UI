#!/bin/bash
# UniRig Gradio WebUI Fork - GitHub Repository Setup Script
# プライベートフォーク用GitHubリポジトリセットアップスクリプト

echo "🚀 UniRig Gradio WebUI Fork - GitHub セットアップ開始"
echo "================================================"

# Git設定確認
echo "📋 Git設定を確認中..."
git config --global user.name || echo "⚠️  Git user.name が設定されていません"
git config --global user.email || echo "⚠️  Git user.email が設定されていません"

# Git LFS確認
echo "📦 Git LFS状態確認..."
git lfs version || echo "❌ Git LFS がインストールされていません"

# リポジトリ状態確認
echo "📊 リポジトリ状態確認..."
echo "追加されるファイル数: $(git status --porcelain | wc -l)"
echo "LFS管理ファイル数: $(git lfs ls-files | wc -l)"

# 重要ファイルをステージング
echo "📝 重要ファイルをステージング..."
git add README_FORK.md README_FORK_ja.md
git add .gitignore .gitattributes
git add requirements.txt Dockerfile
git add app.py configs/ src/ blender/
git add examples/*.glb examples/*.fbx
git add assets/doc/

# コミット作成
echo "💾 コミット作成..."
git commit -m "feat: UniRig Gradio WebUI フォーク - 完全なWebインターフェース実装

✨ 新機能:
- フルパイプライン Gradio WebUI実装
- 個別ステージ処理とプレビュー機能  
- リアルタイム進捗表示
- エラーハンドリングと堅牢な処理
- Docker + CUDA 12.1 環境対応
- Git LFS による大容量ファイル管理

🔧 技術的改善:
- PyTorch 2.3.1 + CUDA 12.1最適化
- Blender 4.2統合FBX/GLB変換
- 設定管理とログシステム
- 包括的テストスイート

📚 ドキュメント:
- 日本語・英語対応README
- プライベートフォーク説明
- 詳細なセットアップガイド

🎯 目的: 学習・開発用バージョン管理
👥 元の功績: VAST-AI-Research/UniRig
📄 ライセンス: MIT (元ライセンス準拠)"

echo "✅ コミット完了!"
echo ""
echo "🔗 次のステップ:"
echo "1. GitHubでプライベートリポジトリを作成"
echo "2. git remote add origin <YOUR_REPO_URL>"
echo "3. git push -u origin main"
echo ""
echo "📊 リポジトリ統計:"
echo "ファイル数: $(find . -type f | grep -v .git | wc -l)"
echo "コード行数: $(find . -name "*.py" | xargs wc -l | tail -1)"
echo "サイズ: $(du -sh . | cut -f1)"
echo ""
echo "🎉 セットアップ完了! GitHubにプッシュする準備ができました。"
