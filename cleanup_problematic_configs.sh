#!/bin/bash
# プロジェクト中止を引き起こした問題設定ファイルの削除スクリプト
# 実行前にバックアップを作成することを推奨

echo "🚨 プロジェクト中止原因ファイルの削除開始..."

# 1. 未使用のpyrender回避設定ファイル削除
if [ -f "/app/configs/transform/inference_skin_transform_no_pyrender.yaml" ]; then
    echo "📁 削除: inference_skin_transform_no_pyrender.yaml (未使用・5月29日作成)"
    rm -f "/app/configs/transform/inference_skin_transform_no_pyrender.yaml"
fi

# 2. 不要な抽出設定ファイル削除
if [ -f "/app/configs/extract_config.yaml" ]; then
    echo "📁 削除: extract_config.yaml (app_config.yamlで代替可能)"
    rm -f "/app/configs/extract_config.yaml"
fi

# 3. app_config.yamlの肥大化した設定をシンプル化（バックアップ作成）
if [ -f "/app/configs/app_config.yaml" ]; then
    echo "💾 バックアップ作成: app_config.yaml → app_config.yaml.backup"
    cp "/app/configs/app_config.yaml" "/app/configs/app_config.yaml.backup"
    
    echo "⚠️  app_config.yamlの手動簡素化が必要："
    echo "   - blender_native_texture_flow セクション削除"
    echo "   - 基本設定のみ保持"
    echo "   - 動作しない機能の設定削除"
fi

echo ""
echo "✅ 問題ファイル削除完了"
echo "📋 次のステップ:"
echo "   1. app_config.yamlの手動簡素化"
echo "   2. MVP機能のみ保持"
echo "   3. 段階的機能追加"
echo ""
echo "🎯 目標: ファイル数 ≤ 50, 設定は最小限"
