# オリジナル鳥モデル (bird.glb) マテリアル構造分析結果

## 基本情報
- ファイルパス: `/app/examples/bird.glb`
- マテリアル数: 1
- メッシュオブジェクト: `SK_tucano_bird.001`

## マテリアル詳細: M_Tucano_bird_material

### ノード構造 (10ノード)
1. **Principled BSDF** (BSDF_PRINCIPLED)
   - Base Color ← Mix.Result
   - Metallic ← Math.Value
   - Roughness ← Separate Color.Green
   - Normal ← Normal Map.Normal

2. **Material Output** (OUTPUT_MATERIAL)
   - Surface ← Principled BSDF.BSDF

3. **Mix** (MIX)
   - A ← Image Texture.Color (Base Color テクスチャ)
   - B ← Color Attribute.Color (頂点カラー)

4. **Color Attribute** (VERTEX_COLOR)
   - 頂点カラーデータ

5. **Image Texture** (TEX_IMAGE) - Base Color
   - 画像: T_tucano_bird_col_v2_BC
   - サイズ: 2048x2048
   - パックサイズ: 3,506,846 bytes (3.5MB)

6. **Math** (MATH)
   - Value ← Separate Color.Blue

7. **Separate Color** (SEPARATE_COLOR)
   - Color ← Image Texture.001.Color

8. **Image Texture.001** (TEX_IMAGE) - Roughness/Gloss
   - 画像: T_tucano_bird_gloss6_R
   - サイズ: 2048x2048
   - パックサイズ: 2,071,796 bytes (2.1MB)

9. **Normal Map** (NORMAL_MAP)
   - Color ← Image Texture.002.Color

10. **Image Texture.002** (TEX_IMAGE) - Normal
    - 画像: T_tucano_bird_nrml5_N
    - サイズ: 2048x2048
    - パックサイズ: 2,055,744 bytes (2.1MB)

### 接続構造 (10リンク)
1. Principled BSDF.BSDF → Material Output.Surface
2. Mix.Result → Principled BSDF.Base Color
3. Color Attribute.Color → Mix.B
4. Image Texture.Color → Mix.A
5. Math.Value → Principled BSDF.Metallic
6. Separate Color.Blue → Math.Value
7. Separate Color.Green → Principled BSDF.Roughness
8. Image Texture.001.Color → Separate Color.Color
9. Normal Map.Normal → Principled BSDF.Normal
10. Image Texture.002.Color → Normal Map.Color

### テクスチャ情報
- **総テクスチャサイズ**: 7,634,386 bytes (約7.6MB)
- **Base Color**: T_tucano_bird_col_v2_BC (3.5MB, PNG)
- **Roughness/Gloss**: T_tucano_bird_gloss6_R (2.1MB, PNG)
- **Normal Map**: T_tucano_bird_nrml5_N (2.1MB, PNG)

### 重要な特徴
1. **複雑なマテリアル構造**: 単純なテクスチャマッピングではなく、Mix、Separate Color、Mathノードを使用
2. **頂点カラー統合**: Base ColorはテクスチャとVertex Colorの混合
3. **チャンネル分離**: Roughness/Glossマップから個別チャンネルを抽出
4. **ノーマルマッピング**: 専用のNormal Mapノード使用

## 問題の根本原因

UniRigのテクスチャ統合プロセスで以下のノードタイプが認識されていない:
- `BSDF_PRINCIPLED`
- `TEX_IMAGE` 
- `VERTEX_COLOR`
- `SEPARATE_COLOR`
- `MIX`
- `NORMAL_MAP`
- `MATH`

これらのノードタイプが正しく処理されないため、マテリアルの再構築に失敗している。
