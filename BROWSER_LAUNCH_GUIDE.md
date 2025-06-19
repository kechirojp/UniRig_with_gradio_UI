# 🚀 UniRig WebUI ブラウザ自動起動ガイド

## 📋 起動方法

### 1. 基本起動（ブラウザ自動起動有効）
```bash
python app.py
```
または
```bash
python launch_with_browser.py
```

### 2. 高速起動モード
```bash
python launch_with_browser.py --quick
```

### 3. ブラウザ自動起動無効
```bash
python launch_with_browser.py --no-browser
```

### 4. カスタムポート指定
```bash
python launch_with_browser.py --port 8080
```

## 🔧 環境変数による制御

### ブラウザ自動起動制御
```bash
# ブラウザ自動起動を無効化
export UNIRIG_AUTO_BROWSER=false
python app.py

# ブラウザ自動起動を有効化（デフォルト）
export UNIRIG_AUTO_BROWSER=true
python app.py
```

### ポート指定
```bash
# カスタムポートで起動
export UNIRIG_PORT=8080
python app.py
```

## 📱 起動後の動作

1. **app.py**または**quick_start_app.py**が実行される
2. 利用可能なポートが自動検索される
3. ブラウザが自動的に開く（無効化されていない場合）
4. UniRig WebUIがすぐに使用可能になる

## 🛠️ トラブルシューティング

### ブラウザが開かない場合
```bash
# 手動でブラウザ起動を無効化して実行
python launch_with_browser.py --no-browser
# その後、手動でブラウザから http://localhost:7860 にアクセス
```

### ポートが使用中の場合
- app.pyは自動的に7860～7870の範囲で利用可能なポートを検索します
- カスタムポートを指定する場合は`--port`オプションを使用してください

### 起動エラーが発生する場合
```bash
# 高速起動モードを試す
python launch_with_browser.py --quick

# または、直接quick_start_app.pyを実行
python quick_start_app.py
```

## 🎯 推奨使用法

**通常使用**:
```bash
python launch_with_browser.py
```

**開発・デバッグ**:
```bash
python launch_with_browser.py --no-browser --port 8080
```

**高速起動**:
```bash
python launch_with_browser.py --quick
```
