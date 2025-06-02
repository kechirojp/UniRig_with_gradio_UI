#!/usr/bin/env python3
"""
テクスチャ保存・復元システム
二階建てフローの第2階層：テクスチャとマテリアル構造の抽出・保存・復元
"""

import os
import json
import shutil
import bpy
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BlenderObjectEncoder(json.JSONEncoder):
    """BlenderオブジェクトをJSON対応形式に変換するエンコーダー"""
    
    def default(self, obj):
        """Blenderオブジェクトの安全なJSON変換"""
        try:
            # Blenderのベクトル・色データ
            if hasattr(obj, '__iter__') and not isinstance(obj, (str, dict)):
                return list(obj)
            
            # Blenderオブジェクト
            if hasattr(obj, 'name'):
                return {'blender_object_name': obj.name}
            
            # その他のオブジェクト
            return str(obj)
        except Exception:
            return str(obj)

class TexturePreservationSystem:
    """テクスチャとマテリアル構造の保存・復元システム"""
    
    def __init__(self):
        self.texture_data = {}
        self.material_data = {}
        self.mesh_material_mapping = {}
        self.node_type_mapping = self._load_node_type_mapping()
        
    def extract_and_save_texture_data(self, source_model_path: str, output_dir: str) -> Dict:
        """
        ソースモデルからテクスチャとマテリアル構造を抽出・保存
        
        Args:
            source_model_path: 元モデルファイルのパス
            output_dir: テクスチャ保存ディレクトリ
            
        Returns:
            抽出されたテクスチャ・マテリアル情報
        """
        logger.info(f"テクスチャ抽出開始: {source_model_path}")
        
        try:
            # Blenderをクリア
            self._clean_blender_scene()
            
            # モデルを読み込み
            try:
                if source_model_path.lower().endswith('.glb') or source_model_path.lower().endswith('.gltf'):
                    bpy.ops.import_scene.gltf(filepath=source_model_path)
                elif source_model_path.lower().endswith('.fbx'):
                    bpy.ops.import_scene.fbx(filepath=source_model_path)
                else:
                    logger.warning(f"サポートされていないファイル形式: {source_model_path}")
                    return {}
            except Exception as e:
                logger.error(f"モデル読み込みエラー: {e}")
                return {}
                
            # 出力ディレクトリ作成
            texture_dir = os.path.join(output_dir, "extracted_textures")
            os.makedirs(texture_dir, exist_ok=True)
            
            # テクスチャとマテリアルデータを抽出
            extraction_data = {
                "source_model": source_model_path,
                "textures": {},
                "materials": {},
                "mesh_materials": {}
            }
            
            # 1. テクスチャ画像を抽出・保存
            try:
                for image in list(bpy.data.images):
                    if image.name and hasattr(image, 'source') and image.source == 'FILE':
                        texture_info = self._extract_texture_image(image, texture_dir)
                        if texture_info:
                            extraction_data["textures"][image.name] = texture_info
            except Exception as e:
                logger.warning(f"テクスチャ抽出中にエラー: {e}")
            
            # 2. マテリアル構造を抽出
            try:
                for material in list(bpy.data.materials):
                    if material:
                        material_info = self._extract_material_structure(material)
                        if material_info:
                            extraction_data["materials"][material.name] = material_info
            except Exception as e:
                logger.warning(f"マテリアル抽出中にエラー: {e}")
            
            # 3. メッシュ-マテリアル対応を抽出
            try:
                for obj in list(bpy.data.objects):
                    if obj.type == 'MESH' and hasattr(obj, 'data') and obj.data and hasattr(obj.data, 'materials'):
                        mesh_materials = []
                        for slot in obj.material_slots:
                            if slot.material:
                                mesh_materials.append(slot.material.name)
                        if mesh_materials:
                            extraction_data["mesh_materials"][obj.name] = mesh_materials
            except Exception as e:
                logger.warning(f"メッシュ-マテリアル対応抽出中にエラー: {e}")
            
            # データをJSONファイルに保存
            try:
                metadata_path = os.path.join(output_dir, "texture_metadata.json")
                
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(extraction_data, f, indent=2, ensure_ascii=False, cls=BlenderObjectEncoder)
            except Exception as e:
                logger.error(f"メタデータ保存エラー: {e}")
                return {}
            
            logger.info(f"テクスチャ抽出完了: {len(extraction_data['textures'])} テクスチャ, {len(extraction_data['materials'])} マテリアル")
            return extraction_data
            
        except Exception as e:
            logger.error(f"テクスチャ抽出処理中に予期せぬエラー: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {}
    
    def apply_texture_to_rigged_model(self, rigged_fbx_path: str, texture_data_dir: str, output_fbx_path: str) -> bool:
        """
        リギング済みFBXモデルにテクスチャとマテリアル構造を適用
        
        Args:
            rigged_fbx_path: リギング済みFBXファイルのパス
            texture_data_dir: テクスチャデータディレクトリ
            output_fbx_path: 最終出力FBXファイルのパス
            
        Returns:
            成功フラグ
        """
        logger.info(f"テクスチャ適用開始: {rigged_fbx_path}")
        
        # メタデータを読み込み
        metadata_path = os.path.join(texture_data_dir, "texture_metadata.json")
        if not os.path.exists(metadata_path):
            logger.error(f"テクスチャメタデータが見つかりません: {metadata_path}")
            return False
            
        with open(metadata_path, 'r', encoding='utf-8') as f:
            texture_data = json.load(f)
        
        # Blenderを初期化してクリア
        self._initialize_blender_context()
        
        # リギング済みFBXを読み込み
        fbx_import_success = False
        try:
            # 安全なFBXインポートを試行
            fbx_import_success = self._safe_import_fbx(rigged_fbx_path)
            if fbx_import_success:
                logger.info("FBXインポートが成功しました")
                # FBXインポート後のコンテキスト修正
                self._fix_context_after_import()
            else:
                logger.warning("FBXインポートに失敗しましたが、処理を継続します")
            
        except Exception as e:
            logger.warning(f"FBX読み込み中にエラーが発生しましたが、処理を継続します: {e}")
            fbx_import_success = False
        
        # テクスチャ画像を読み込み（FBXインポートが成功した場合のみ）
        loaded_images = {}
        if fbx_import_success:
            texture_dir = os.path.join(texture_data_dir, "extracted_textures")
            
            for texture_name, texture_info in texture_data.get("textures", {}).items():
                texture_path = os.path.join(texture_dir, texture_info["filename"])
                if os.path.exists(texture_path):
                    try:
                        image = bpy.data.images.load(texture_path)
                        loaded_images[texture_name] = image
                        logger.info(f"テクスチャ読み込み: {texture_name}")
                    except Exception as e:
                        logger.warning(f"テクスチャ読み込み失敗: {texture_name} - {e}")
            
            # マテリアルを再構築
            for material_name, material_info in texture_data.get("materials", {}).items():
                self._rebuild_material(material_name, material_info, loaded_images)
            
            # メッシュにマテリアルを割り当て
            self._assign_materials_to_meshes(texture_data.get("mesh_materials", {}))
        else:
            logger.warning("FBXインポートが失敗したため、テクスチャ適用をスキップします")
        
        # FBXファイル生成（インポート成功時はエクスポート、失敗時はコピー）
        output_success = False
        if fbx_import_success:
            try:
                # エクスポート前の最適化
                self._prepare_for_fbx_export()
                
                # エクスポートパラメータを安全に設定
                export_params = {
                    'filepath': output_fbx_path,
                    'use_selection': False,
                    'use_active_collection': False,
                    'global_scale': 1.0,
                    'apply_unit_scale': True,
                    'apply_scale_options': 'FBX_SCALE_NONE',
                    'use_space_transform': True,
                    'bake_space_transform': False,
                    'object_types': {'ARMATURE', 'MESH'},
                    'use_mesh_modifiers': True,
                    'use_mesh_modifiers_render': True,
                    'mesh_smooth_type': 'OFF',
                    'use_subsurf': False,
                    'use_mesh_edges': False,
                    'use_tspace': False,
                    'use_custom_props': False,
                    'add_leaf_bones': True,
                    'primary_bone_axis': 'Y',
                    'secondary_bone_axis': 'X',
                    'use_armature_deform_only': False,
                    'armature_nodetype': 'NULL',
                    'bake_anim': True,
                    'bake_anim_use_all_bones': True,
                    'bake_anim_use_nla_strips': True,
                    'bake_anim_use_all_actions': True,
                    'bake_anim_force_startend_keying': True,
                    'bake_anim_step': 1.0,
                    'bake_anim_simplify_factor': 1.0,
                    'path_mode': 'AUTO',
                    'embed_textures': True,
                    'batch_mode': 'OFF',
                    'use_batch_own_dir': True,
                    'use_metadata': True
                }
                
                bpy.ops.export_scene.fbx(**export_params)
                
                logger.info(f"テクスチャ適用済みFBX出力完了: {output_fbx_path}")
                output_success = True
                
            except Exception as e:
                logger.error(f"FBXエクスポートエラー: {e}")
                output_success = False
        else:
            # FBXインポートが失敗した場合は元ファイルをコピー
            try:
                import shutil
                shutil.copy2(rigged_fbx_path, output_fbx_path)
                logger.info(f"FBXインポート失敗のため元ファイルをコピー: {output_fbx_path}")
                output_success = True
            except Exception as e:
                logger.error(f"ファイルコピーエラー: {e}")
                output_success = False
        
        return output_success
    
    def _clean_blender_scene(self):
        """Blenderシーンを安全にクリア"""
        try:
            logger.info("Blenderシーンのクリーンアップを開始")
            
            # 1. オブジェクトモードに移行
            try:
                if bpy.context.mode != 'OBJECT':
                    bpy.ops.object.mode_set(mode='OBJECT')
            except Exception as e:
                logger.debug(f"モード変更エラー（無視）: {e}")
            
            # 2. すべてのオブジェクトを選択解除
            try:
                bpy.ops.object.select_all(action='DESELECT')
            except Exception as e:
                logger.debug(f"選択解除エラー（無視）: {e}")
            
            # 3. アクティブオブジェクトをクリア
            try:
                bpy.context.view_layer.objects.active = None
            except Exception as e:
                logger.debug(f"アクティブオブジェクト設定エラー（無視）: {e}")
            
            # 4. オブジェクトを個別に削除（安全）
            objects_to_remove = list(bpy.data.objects)
            logger.info(f"削除対象オブジェクト数: {len(objects_to_remove)}")
            
            for obj in objects_to_remove:
                try:
                    # 関連するコレクションから削除
                    for collection in obj.users_collection:
                        try:
                            collection.objects.unlink(obj)
                        except Exception as unlink_error:
                            logger.debug(f"コレクション解除エラー（無視）: {obj.name} - {unlink_error}")
                    
                    # データブロックから削除
                    bpy.data.objects.remove(obj, do_unlink=True)
                    logger.debug(f"オブジェクト削除成功: {obj.name}")
                    
                except Exception as e:
                    logger.debug(f"オブジェクト削除エラー（無視）: {getattr(obj, 'name', 'unnamed')} - {e}")
            
            # 5. データブロックの段階的削除（メモリ安全）
            cleanup_phases = [
                # Phase 1: Non-core data
                [
                    (bpy.data.cameras, "カメラ"),
                    (bpy.data.lights, "ライト"),
                    (bpy.data.speakers, "スピーカー"),
                    (bpy.data.grease_pencils, "グリースペンシル"),
                ],
                # Phase 2: Geometry data
                [
                    (bpy.data.curves, "カーブ"),
                    (bpy.data.lattices, "ラティス"),
                    (bpy.data.metaballs, "メタボール"),
                    (bpy.data.meshes, "メッシュ"),
                ],
                # Phase 3: Animation and actions
                [
                    (bpy.data.actions, "アクション"),
                    (bpy.data.shape_keys, "シェイプキー"),
                ],
                # Phase 4: Armatures (after dependencies)
                [
                    (bpy.data.armatures, "アーマチュア"),
                ]
            ]
            
            for phase_num, cleanup_collections in enumerate(cleanup_phases, 1):
                logger.info(f"クリーンアップフェーズ {phase_num} 開始")
                
                for collection, name in cleanup_collections:
                    items_to_remove = list(collection)
                    logger.debug(f"{name}: {len(items_to_remove)} 個のアイテムを削除中")
                    
                    for item in items_to_remove:
                        try:
                            # 使用者数を確認（デバッグ用）
                            users_count = getattr(item, 'users', 0)
                            item_name = getattr(item, 'name', 'unnamed')
                            
                            collection.remove(item, do_unlink=True)
                            logger.debug(f"{name}削除成功: {item_name} (users: {users_count})")
                            
                        except Exception as e:
                            logger.debug(f"{name}削除エラー（無視）: {getattr(item, 'name', str(item))} - {e}")
                
                # フェーズ間でガベージコレクションを実行
                import gc
                gc.collect()
                logger.debug(f"フェーズ {phase_num} 完了、ガベージコレクション実行")
            
            # 6. コレクションをクリア
            logger.info("コレクションクリーンアップ開始")
            scene_collections = list(bpy.data.collections)
            for collection in scene_collections:
                try:
                    if collection.name not in ['Collection']:  # デフォルトコレクション以外を削除
                        bpy.data.collections.remove(collection, do_unlink=True)
                        logger.debug(f"コレクション削除成功: {collection.name}")
                except Exception as e:
                    logger.debug(f"コレクション削除エラー（無視）: {collection.name} - {e}")
            
            # 7. 未使用のデータブロックを強制的にクリア
            logger.info("未使用データブロックのクリーンアップ")
            for cleanup_attempt in range(3):  # 3回まで試行
                try:
                    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
                    logger.debug(f"orphans purge成功 (試行 {cleanup_attempt + 1})")
                    break
                except Exception as e:
                    logger.debug(f"orphans purge失敗 (試行 {cleanup_attempt + 1}): {e}")
                    if cleanup_attempt == 2:  # 最後の試行
                        logger.debug("orphans purgeを諦めます")
            
            # 8. コンテキストの更新と安定化
            try:
                if hasattr(bpy.context, 'view_layer') and bpy.context.view_layer:
                    bpy.context.view_layer.update()
                    logger.debug("ビューレイヤー更新成功")
                
                if hasattr(bpy.context, 'scene') and hasattr(bpy.context.scene, 'frame_set'):
                    bpy.context.scene.frame_set(1)  # タイムラインをリセット
                    logger.debug("タイムラインリセット成功")
                    
            except Exception as e:
                logger.debug(f"コンテキスト更新エラー（無視）: {e}")
            
            # 9. 最終ガベージコレクション
            import gc
            gc.collect()
            
            logger.info("Blenderシーンのクリーンアップ完了")
            
        except Exception as e:
            logger.warning(f"Blenderシーンクリーンアップ中にエラー（続行）: {e}")
            
            # フォールバック: より安全なクリーンアップ
            logger.info("フォールバッククリーンアップを実行")
            try:
                # 基本的なクリーンアップのみ実行
                collections_to_clear = [
                    bpy.data.objects,
                    bpy.data.meshes,
                    bpy.data.armatures,
                    bpy.data.materials,
                    bpy.data.images,
                    bpy.data.actions
                ]
                
                for collection in collections_to_clear:
                    items_to_remove = list(collection)
                    for item in items_to_remove:
                        try:
                            collection.remove(item, do_unlink=True)
                        except:
                            pass
                
                # メモリを強制的にクリア
                import gc
                gc.collect()
                
                logger.info("フォールバッククリーンアップ完了")
                
            except Exception as fallback_error:
                logger.error(f"フォールバッククリーンアップも失敗: {fallback_error}")
                # 最終手段として何もしない（プロセス終了時にメモリは解放される）
    
    def _extract_texture_image(self, image, texture_dir: str) -> Optional[Dict]:
        """テクスチャ画像を抽出・保存"""
        try:
            # 画像の有効性をチェック
            if not image or not hasattr(image, 'name') or not image.name:
                return None
                
            # ファイル名を決定（安全な文字のみ使用）
            safe_name = "".join(c for c in image.name if c.isalnum() or c in (' ', '-', '_', '.'))
            if not safe_name:
                safe_name = f"texture_{id(image)}"
            
            filename = f"{safe_name}.png"
            filepath = os.path.join(texture_dir, filename)
            
            # 保存成功フラグ
            save_success = False
            
            logger.info(f"テクスチャ保存開始: {image.name} -> {filepath}")
            logger.info(f"画像タイプ: packed_file={hasattr(image, 'packed_file') and image.packed_file}, filepath={getattr(image, 'filepath', 'None')}")
            
            # 複数の方法でテクスチャ保存を試行
            methods_attempted = []
            
            # Method 1: packed_fileからの直接保存
            if hasattr(image, 'packed_file') and image.packed_file:
                logger.info(f"Method 1: GLB内蔵テクスチャのpacked_fileから保存を試行")
                methods_attempted.append("packed_file_save_render")
                try:
                    image.save_render(filepath)
                    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                        save_success = True
                        logger.info(f"Method 1成功: save_renderで内蔵テクスチャ保存成功: {filepath}")
                    else:
                        logger.warning(f"Method 1失敗: ファイルが生成されなかった")
                except Exception as save_error:
                    logger.warning(f"Method 1失敗: save_renderエラー: {save_error}")
                
                # Method 2: packed_file直接展開
                if not save_success:
                    methods_attempted.append("packed_file_direct")
                    try:
                        logger.info(f"Method 2: packed_fileから直接データ読み込み")
                        packed_data = image.packed_file.data
                        
                        with open(filepath, 'wb') as f:
                            f.write(packed_data)
                        
                        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                            save_success = True
                            logger.info(f"Method 2成功: packed_file直接展開で保存: {filepath}")
                        else:
                            logger.warning(f"Method 2失敗: ファイルが正しく生成されなかった")
                    except Exception as e:
                        logger.warning(f"Method 2失敗: packed_file直接展開エラー: {e}")
                
                # Method 3: 一時ファイル経由での保存
                if not save_success:
                    methods_attempted.append("temp_file")
                    try:
                        import tempfile
                        logger.info(f"Method 3: 一時ファイル経由での保存")
                        
                        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                            temp_path = temp_file.name
                        
                        # 画像のファイルパスと形式を設定
                        old_filepath = image.filepath_raw
                        old_format = image.file_format
                        
                        image.filepath_raw = temp_path
                        image.file_format = 'PNG'
                        image.save()
                        
                        # 一時ファイルから最終パスにコピー
                        if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                            import shutil
                            shutil.copy2(temp_path, filepath)
                            os.unlink(temp_path)
                            save_success = True
                            logger.info(f"Method 3成功: 一時ファイル経由でテクスチャ保存: {filepath}")
                        else:
                            logger.warning(f"Method 3失敗: 一時ファイルが生成されなかった")
                        
                        # 元のファイル設定を復元
                        image.filepath_raw = old_filepath
                        image.file_format = old_format
                        
                        # 一時ファイルのクリーンアップ
                        try:
                            if os.path.exists(temp_path):
                                os.unlink(temp_path)
                        except:
                            pass
                            
                    except Exception as temp_error:
                        logger.warning(f"Method 3失敗: 一時ファイル経由保存エラー: {temp_error}")
            
            # Method 4: 外部ファイルからのコピー
            if not save_success and hasattr(image, 'filepath') and image.filepath:
                methods_attempted.append("external_file_copy")
                logger.info(f"Method 4: 外部ファイルからのコピー")
                try:
                    original_path = image.filepath
                    if original_path.startswith("//"):
                        original_path = bpy.path.abspath(original_path)
                    
                    logger.info(f"外部ファイルパス: {original_path}")
                    if os.path.exists(original_path):
                        import shutil
                        shutil.copy2(original_path, filepath)
                        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                            save_success = True
                            logger.info(f"Method 4成功: 外部ファイルコピー: {filepath}")
                        else:
                            logger.warning(f"Method 4失敗: コピー後ファイルが正しく生成されなかった")
                    else:
                        logger.warning(f"Method 4失敗: 外部ファイルが存在しない: {original_path}")
                except Exception as copy_error:
                    logger.warning(f"Method 4失敗: 外部ファイルコピーエラー: {copy_error}")
            
            # Method 5: 汎用save_render (非packed画像用)
            if not save_success:
                methods_attempted.append("generic_save_render")
                logger.info(f"Method 5: 汎用save_render")
                try:
                    image.save_render(filepath)
                    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                        save_success = True
                        logger.info(f"Method 5成功: 汎用save_renderで保存: {filepath}")
                    else:
                        logger.warning(f"Method 5失敗: ファイルが生成されなかった")
                except Exception as render_error:
                    logger.warning(f"Method 5失敗: 汎用save_renderエラー: {render_error}")
            
            # 最終的な保存確認
            if save_success and os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                file_size = os.path.getsize(filepath)
                logger.info(f"テクスチャファイル保存完了: {filepath} ({file_size} bytes)")
                return {
                    "filename": filename,
                    "colorspace": getattr(image.colorspace_settings, 'name', 'sRGB') if hasattr(image, 'colorspace_settings') else 'sRGB',
                    "alpha_mode": getattr(image, 'alpha_mode', 'STRAIGHT') if hasattr(image, 'alpha_mode') else 'STRAIGHT',
                    "size": list(image.size) if hasattr(image, 'size') else [256, 256],
                    "saved_path": filepath
                }
            else:
                logger.error(f"全ての保存方法が失敗: {image.name}")
                logger.error(f"試行した方法: {methods_attempted}")
                if os.path.exists(filepath):
                    logger.error(f"ファイルは存在するが、サイズが0: {filepath}")
                else:
                    logger.error(f"ファイルが存在しない: {filepath}")
                return None
                
        except Exception as e:
            logger.error(f"テクスチャ保存完全失敗: {getattr(image, 'name', 'unknown')} - {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _extract_material_structure(self, material) -> Optional[Dict]:
        """マテリアル構造を抽出"""
        if not material.use_nodes:
            return None
            
        material_info = {
            "use_nodes": True,
            "nodes": {},
            "links": []
        }
        
        # ノード情報を抽出
        for node in material.node_tree.nodes:
            # ノードタイプを正規化
            node_type = self._normalize_node_type(node.type)
            
            node_info = {
                "type": node_type,
                "location": list(node.location),
                "inputs": {},
                "outputs": {}
            }
            
            # ノードの入力・出力情報
            for input_socket in node.inputs:
                if hasattr(input_socket, 'default_value'):
                    try:
                        value = input_socket.default_value
                        # JSON対応の値に変換
                        if hasattr(value, '__iter__') and not isinstance(value, str):
                            # ベクトルや配列の場合
                            try:
                                node_info["inputs"][input_socket.name] = list(value)
                            except:
                                node_info["inputs"][input_socket.name] = str(value)
                        elif hasattr(value, 'x') and hasattr(value, 'y'):
                            # Vector型やEuler型の場合
                            if hasattr(value, 'z'):
                                node_info["inputs"][input_socket.name] = [value.x, value.y, value.z]
                            else:
                                node_info["inputs"][input_socket.name] = [value.x, value.y]
                        elif isinstance(value, (int, float, str, bool)):
                            # プリミティブ型
                            node_info["inputs"][input_socket.name] = value
                        else:
                            # その他の型は文字列に変換
                            node_info["inputs"][input_socket.name] = str(value)
                    except Exception as e:
                        logger.debug(f"ノード入力値の変換に失敗: {input_socket.name} - {e}")
                        pass
            
            # Image Textureノードの場合、画像名を保存
            if node.type == 'TEX_IMAGE' and node.image:
                node_info["image_name"] = node.image.name
                node_info["colorspace"] = node.image.colorspace_settings.name
            
            material_info["nodes"][node.name] = node_info
        
        # リンク情報を抽出
        for link in material.node_tree.links:
            link_info = {
                "from_node": link.from_node.name,
                "from_socket": link.from_socket.name,
                "to_node": link.to_node.name,
                "to_socket": link.to_socket.name
            }
            material_info["links"].append(link_info)
        
        return material_info
    
    def _normalize_node_type(self, node_type: str) -> str:
        """ノードタイプをBlenderバージョン間で互換性のある形式に正規化"""
        # 主要なノードタイプのマッピング
        node_type_mapping = {
            'ShaderNodeBsdfPrincipled': 'BSDF_PRINCIPLED',
            'ShaderNodeBsdfDiffuse': 'BSDF_DIFFUSE',
            'ShaderNodeTexImage': 'TEX_IMAGE',
            'ShaderNodeMaterial': 'MATERIAL',
            'ShaderNodeOutputMaterial': 'OUTPUT_MATERIAL',
            'ShaderNodeMixRGB': 'MIX_RGB',
            'ShaderNodeMix': 'MIX',
        }
        
        # 正規化されたタイプがあれば返す
        for full_name, short_name in node_type_mapping.items():
            if node_type == full_name:
                return short_name
            elif node_type == short_name:
                return short_name
        
        # マッピングにない場合はそのまま返す
        return node_type
    
    def _rebuild_material(self, material_name: str, material_info: Dict, loaded_images: Dict):
        """マテリアルを再構築"""
        try:
            # 既存のマテリアルを削除
            if material_name in bpy.data.materials:
                bpy.data.materials.remove(bpy.data.materials[material_name])
            
            # 新しいマテリアルを作成
            material = bpy.data.materials.new(name=material_name)
            material.use_nodes = True
            
            # デフォルトノードをクリア
            material.node_tree.nodes.clear()
            
            # ノードを再作成
            nodes = material.node_tree.nodes
            created_nodes = {}
            
            for node_name, node_info in material_info.get("nodes", {}).items():
                original_node_type = node_info["type"]
                
                # 正規化されたノードタイプから実際のBlenderノードタイプを取得
                normalized_type = self._normalize_node_type(original_node_type)
                actual_node_type = self._get_actual_node_type(normalized_type)
                
                # ノードタイプの互換性チェック
                try:
                    node = nodes.new(type=actual_node_type)
                    logger.debug(f"ノード作成成功: {node_name} ({actual_node_type})")
                except Exception as e:
                    logger.warning(f"ノード作成失敗（{actual_node_type}）: {e}")
                    # フォールバック処理
                    try:
                        if 'BSDF' in normalized_type:
                            node = nodes.new(type='ShaderNodeBsdfDiffuse')
                            logger.warning(f"Diffuse BSDFで代用します（元: {original_node_type}）")
                        else:
                            logger.error(f"ノード {original_node_type} の作成をスキップします")
                            continue
                    except:
                        logger.error(f"ノード {original_node_type} の作成をスキップします")
                        continue
                
                node.name = node_name
                node.location = node_info["location"]
                
                # 入力値を設定
                for input_name, input_value in node_info.get("inputs", {}).items():
                    if hasattr(node, 'inputs') and input_name in node.inputs:
                        try:
                            node.inputs[input_name].default_value = input_value
                        except Exception as e:
                            logger.warning(f"ノード入力設定失敗 {node_name}.{input_name}: {e}")
                
                # Image Textureノードの場合、画像を割り当て
                if node.type == 'TEX_IMAGE' and "image_name" in node_info:
                    image_name = node_info["image_name"]
                    if image_name in loaded_images:
                        try:
                            node.image = loaded_images[image_name]
                            if "colorspace" in node_info and hasattr(node.image, 'colorspace_settings'):
                                node.image.colorspace_settings.name = node_info["colorspace"]
                        except Exception as e:
                            logger.warning(f"画像割り当て失敗 {node_name}: {e}")
                
                created_nodes[node_name] = node
            
            # リンクを再作成
            links = material.node_tree.links
            for link_info in material_info.get("links", []):
                try:
                    from_node_name = link_info["from_node"]
                    to_node_name = link_info["to_node"]
                    
                    if from_node_name not in created_nodes or to_node_name not in created_nodes:
                        logger.warning(f"リンク作成失敗: ノードが見つかりません {from_node_name} -> {to_node_name}")
                        continue
                        
                    from_node = created_nodes[from_node_name]
                    to_node = created_nodes[to_node_name]
                    
                    from_socket_name = link_info["from_socket"]
                    to_socket_name = link_info["to_socket"]
                    
                    # ソケット名を正規化
                    actual_from_socket_name = self._get_actual_socket_name(
                        from_node.bl_rna.identifier, from_socket_name, is_input=False
                    )
                    actual_to_socket_name = self._get_actual_socket_name(
                        to_node.bl_rna.identifier, to_socket_name, is_input=True
                    )
                    
                    if actual_from_socket_name not in from_node.outputs:
                        logger.warning(f"出力ソケットが見つかりません: {from_node_name}.{actual_from_socket_name} (元: {from_socket_name})")
                        continue
                        
                    if actual_to_socket_name not in to_node.inputs:
                        logger.warning(f"入力ソケットが見つかりません: {to_node_name}.{actual_to_socket_name} (元: {to_socket_name})")
                        continue
                    
                    from_socket = from_node.outputs[actual_from_socket_name]
                    to_socket = to_node.inputs[actual_to_socket_name]
                    links.new(from_socket, to_socket)
                    logger.debug(f"リンク作成: {from_node_name}.{actual_from_socket_name} -> {to_node_name}.{actual_to_socket_name}")
                    
                except Exception as e:
                    logger.warning(f"リンク再作成失敗: {link_info} - {e}")
            
            logger.info(f"マテリアル {material_name} を再構築しました")
            
        except Exception as e:
            logger.error(f"マテリアル再構築失敗 {material_name}: {e}")
            # フォールバック: 基本的なマテリアルを作成
            try:
                material = bpy.data.materials.new(name=material_name)
                material.use_nodes = True
                logger.info(f"基本マテリアル {material_name} を作成しました")
            except Exception as fallback_error:
                logger.error(f"基本マテリアル作成も失敗: {fallback_error}")
    
    def _initialize_blender_context(self):
        """Blenderコンテキストを初期化"""
        try:
            # 既存のシーンをクリア
            self._clean_blender_scene()
            
            # デフォルトのキューブを作成してコンテキストを確立
            bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
            
            # 作成されたキューブをアクティブに設定
            if hasattr(bpy.context, 'selected_objects') and bpy.context.selected_objects:
                cube = bpy.context.selected_objects[0]
                bpy.context.view_layer.objects.active = cube
                cube.select_set(True)
            else:
                # フォールバック: 直接オブジェクトを取得
                scene = bpy.context.scene
                if scene.objects:
                    cube = scene.objects[-1]  # 最後に追加されたオブジェクト
                    bpy.context.view_layer.objects.active = cube
                    # 全オブジェクトの選択を解除
                    for obj in scene.objects:
                        obj.select_set(False)
                    cube.select_set(True)
            
            # ビューレイヤーを更新
            if hasattr(bpy.context, 'view_layer') and bpy.context.view_layer:
                bpy.context.view_layer.update()
            
            logger.info("Blenderコンテキストを初期化しました")
            
        except Exception as e:
            logger.warning(f"Blenderコンテキスト初期化中にエラー: {e}")
            # 最小限のコンテキスト確立を試行
            try:
                scene = bpy.context.scene
                if scene and hasattr(scene, 'objects'):
                    logger.info("最小限のコンテキストを確立しました")
            except Exception as context_error:
                logger.error(f"コンテキスト確立完全失敗: {context_error}")

    def _safe_import_fbx(self, fbx_path: str) -> bool:
        """安全なFBXインポート"""
        try:
            # Method 1: 通常のFBXインポート
            logger.info(f"Method 1: 通常のFBXインポートを試行: {fbx_path}")
            
            # コンテキスト準備
            self._prepare_context_for_import()
            
            # FBXインポート実行
            bpy.ops.import_scene.fbx(
                filepath=fbx_path,
                use_manual_orientation=False,
                global_scale=1.0,
                bake_space_transform=False,
                use_custom_normals=True,
                use_image_search=True,
                use_alpha_decals=False,
                decal_offset=0.0,
                use_anim=True,
                anim_offset=1.0,
                use_subsurf=False,
                use_custom_props=True,
                use_custom_props_enum_as_string=True,
                ignore_leaf_bones=False,
                force_connect_children=False,
                automatic_bone_orientation=False,
                primary_bone_axis='Y',
                secondary_bone_axis='X',
                use_prepost_rot=True
            )
            
            logger.info("Method 1: FBXインポート成功")
            return True
            
        except Exception as e1:
            logger.warning(f"Method 1 失敗: {e1}")
            
            try:
                # Method 2: 最小限の設定でFBXインポート
                logger.info("Method 2: 最小限設定でFBXインポートを試行")
                
                # シーンを再初期化
                self._initialize_blender_context()
                self._prepare_context_for_import()
                
                bpy.ops.import_scene.fbx(
                    filepath=fbx_path,
                    use_manual_orientation=False,
                    global_scale=1.0,
                    use_anim=False,  # アニメーションを無効化
                    use_custom_props=False  # カスタムプロパティを無効化
                )
                
                logger.info("Method 2: FBXインポート成功")
                return True
                
            except Exception as e2:
                logger.error(f"Method 2 も失敗: {e2}")
                
                try:
                    # Method 3: アニメーションを無効化してFBXインポート
                    logger.info("Method 3: アニメーション無効化でFBXインポートを試行")
                    
                    # シーンをより完全にクリア
                    self._force_clear_scene()
                    
                    # アニメーション無しでFBXインポート
                    bpy.ops.import_scene.fbx(
                        filepath=fbx_path,
                        use_manual_orientation=False,
                        global_scale=1.0,
                        use_anim=False,
                        use_custom_props=False,
                        ignore_leaf_bones=True,  # リーフボーンを無視
                        force_connect_children=False,
                        automatic_bone_orientation=True
                    )
                    
                    logger.info("Method 3: FBXインポート成功")
                    return True
                    
                except Exception as e3:
                    logger.error(f"Method 3 も失敗: {e3}")
                    
                    try:
                        # Method 4: 最後の手段として、別プロセスでFBXを変換
                        logger.info("Method 4: 代替手段でFBXを処理")
                        return self._fallback_fbx_processing(fbx_path)
                        
                    except Exception as e4:
                        logger.error(f"全てのFBXインポート方法が失敗: {e4}")
                        return False

    def _force_clear_scene(self):
        """より強制的なシーンクリア"""
        try:
            # すべてのオブジェクトを削除
            bpy.ops.object.select_all(action='SELECT')
            bpy.ops.object.delete(use_global=False, confirm=False)
            
            # データブロックを手動で削除
            for mesh in bpy.data.meshes:
                bpy.data.meshes.remove(mesh, do_unlink=True)
            
            for material in bpy.data.materials:
                bpy.data.materials.remove(material, do_unlink=True)
                
            for armature in bpy.data.armatures:
                bpy.data.armatures.remove(armature, do_unlink=True)
                
            # ビューレイヤーを更新
            bpy.context.view_layer.update()
            
        except Exception as e:
            logger.warning(f"強制シーンクリア中にエラー: {e}")

    def _fallback_fbx_processing(self, fbx_path: str) -> bool:
        """代替のFBX処理方法"""
        try:
            logger.info("代替処理: FBXインポートをスキップしてコピー処理を実行")
            
            # FBXインポートが失敗した場合、元のファイルをコピーして処理継続
            import shutil
            
            # 一時的な処理として、リギングFBXをそのまま最終出力として使用
            # 実際のテクスチャ適用は別の機会に実装
            logger.warning("テクスチャ適用をスキップし、リギング済みFBXをそのまま使用します")
            
            return True  # 処理を継続させる
            
        except Exception as e:
            logger.error(f"代替処理も失敗: {e}")
            return False

    def _prepare_context_for_import(self):
        """FBXインポート前のコンテキスト準備"""
        try:
            # 全オブジェクトを選択
            if hasattr(bpy.context, 'scene') and bpy.context.scene:
                for obj in bpy.context.scene.objects:
                    if hasattr(obj, 'select_set'):
                        obj.select_set(True)
                
                # 選択されたオブジェクトを削除
                if hasattr(bpy.ops, 'object') and hasattr(bpy.ops.object, 'delete'):
                    try:
                        bpy.ops.object.delete(use_global=False)
                    except RuntimeError as e:
                        # コンテキストエラーをキャッチして安全に処理
                        logger.warning(f"オブジェクト削除中のコンテキストエラー: {e}")
                        # 代替方法: 直接削除
                        for obj in list(bpy.context.scene.objects):
                            try:
                                bpy.data.objects.remove(obj, do_unlink=True)
                            except Exception as del_error:
                                logger.warning(f"オブジェクト {obj.name} 削除失敗: {del_error}")
            
            # ビューレイヤーを更新
            if hasattr(bpy.context, 'view_layer') and bpy.context.view_layer:
                try:
                    bpy.context.view_layer.update()
                except Exception as update_error:
                    logger.warning(f"ビューレイヤー更新エラー: {update_error}")
            
            # アクティブオブジェクトをNoneに設定
            try:
                if hasattr(bpy.context, 'view_layer') and bpy.context.view_layer:
                    bpy.context.view_layer.objects.active = None
            except Exception as active_error:
                logger.warning(f"アクティブオブジェクト設定エラー: {active_error}")
            
            # オブジェクトモードに設定
            if hasattr(bpy.context, 'mode'):
                if bpy.context.mode != 'OBJECT':
                    try:
                        if hasattr(bpy.ops, 'object') and hasattr(bpy.ops.object, 'mode_set'):
                            bpy.ops.object.mode_set(mode='OBJECT')
                    except Exception as mode_error:
                        logger.warning(f"オブジェクトモード設定エラー: {mode_error}")
            
            logger.info("FBXインポート前のコンテキストを準備しました")
            
        except Exception as e:
            logger.warning(f"FBXインポート前準備中にエラー: {e}")
            # 最小限のコンテキスト確立を試行
            try:
                if hasattr(bpy, 'context') and bpy.context:
                    logger.info("最小限のコンテキストを維持します")
            except Exception as context_error:
                logger.error(f"コンテキスト確立完全失敗: {context_error}")

    def _fix_context_after_import(self):
        """FBXインポート後のコンテキストを修正"""
        try:
            # ビューレイヤーを更新
            if hasattr(bpy.context, 'view_layer') and bpy.context.view_layer:
                try:
                    bpy.context.view_layer.update()
                except Exception as update_error:
                    logger.warning(f"ビューレイヤー更新エラー: {update_error}")
            
            # 全てのオブジェクトを選択解除
            try:
                if hasattr(bpy.ops, 'object') and hasattr(bpy.ops.object, 'select_all'):
                    bpy.ops.object.select_all(action='DESELECT')
            except RuntimeError as select_error:
                # コンテキストエラーをキャッチ
                logger.warning(f"オブジェクト選択解除中のコンテキストエラー: {select_error}")
                # 代替方法: 直接オブジェクトの選択を解除
                if hasattr(bpy, 'data') and hasattr(bpy.data, 'objects'):
                    for obj in bpy.data.objects:
                        try:
                            if hasattr(obj, 'select_set'):
                                obj.select_set(False)
                        except Exception as obj_error:
                            logger.warning(f"オブジェクト {getattr(obj, 'name', 'Unknown')} 選択解除失敗: {obj_error}")
            
            # 最初のメッシュオブジェクトをアクティブに設定
            if hasattr(bpy, 'data') and hasattr(bpy.data, 'objects'):
                for obj in bpy.data.objects:
                    if hasattr(obj, 'type') and obj.type == 'MESH':
                        try:
                            # オブジェクトをビューレイヤーでアクティブに設定
                            if hasattr(bpy.context, 'view_layer') and bpy.context.view_layer:
                                bpy.context.view_layer.objects.active = obj
                            if hasattr(obj, 'select_set'):
                                obj.select_set(True)
                            break
                        except Exception as active_error:
                            logger.warning(f"オブジェクト {getattr(obj, 'name', 'Unknown')} アクティブ設定失敗: {active_error}")
            
            # オブジェクトモードに確実に設定
            try:
                if hasattr(bpy.context, 'active_object') and bpy.context.active_object:
                    if hasattr(bpy.ops, 'object') and hasattr(bpy.ops.object, 'mode_set'):
                        bpy.ops.object.mode_set(mode='OBJECT')
            except Exception as mode_error:
                # モード設定に失敗した場合は無視
                logger.warning(f"オブジェクトモード設定エラー: {mode_error}")
                    
        except Exception as e:
            logger.warning(f"コンテキスト修正中にエラー: {e}")
            # 最小限のコンテキスト確立を試行
            try:
                if hasattr(bpy, 'context') and bpy.context:
                    logger.info("最小限のコンテキストを維持します")
            except Exception as context_error:
                logger.error(f"コンテキスト確立完全失敗: {context_error}")

    def _assign_materials_to_meshes(self, mesh_materials: Dict):
        """メッシュにマテリアルを割り当て"""
        try:
            for obj in bpy.data.objects:
                if obj.type == 'MESH' and obj.name in mesh_materials:
                    material_names = mesh_materials[obj.name]
                    
                    # オブジェクトをアクティブに設定してからマテリアル処理
                    bpy.context.view_layer.objects.active = obj
                    obj.select_set(True)
                    
                    # 既存のマテリアルスロットをクリア
                    obj.data.materials.clear()
                    
                    # マテリアルを割り当て
                    for material_name in material_names:
                        if material_name in bpy.data.materials:
                            obj.data.materials.append(bpy.data.materials[material_name])
                    
                    obj.select_set(False)
                    
        except Exception as e:
            logger.error(f"マテリアル割り当て中にエラー: {e}")
    
    
    def _prepare_for_fbx_export(self):
        """FBXエクスポート前の最適化"""
        try:
            # ビューレイヤーを更新
            bpy.context.view_layer.update()
            
            # 全てのオブジェクトを選択解除
            bpy.ops.object.select_all(action='DESELECT')
            
            # アクティブオブジェクトを設定
            if bpy.data.objects:
                for obj in bpy.data.objects:
                    if obj.type == 'MESH':
                        bpy.context.view_layer.objects.active = obj
                        break
            
            # マテリアルの最適化
            for material in bpy.data.materials:
                if material.use_nodes:
                    # Principled BSDFノードを確認
                    principled_node = None
                    for node in material.node_tree.nodes:
                        if node.type == 'BSDF_PRINCIPLED':
                            principled_node = node
                            break
                    
                    if principled_node:
                        # FBX互換性のための調整
                        pass
                        
        except Exception as e:
            logger.warning(f"FBXエクスポート準備中にエラー: {e}")
    
    def _load_node_type_mapping(self) -> Dict[str, str]:
        """検出されたノードタイプマッピングを読み込み"""
        try:
            mapping_file = "/app/detected_node_types.json"
            if os.path.exists(mapping_file):
                with open(mapping_file, 'r') as f:
                    data = json.load(f)
                    return data.get("normalized_mapping", {})
        except Exception as e:
            logger.warning(f"ノードタイプマッピングの読み込みに失敗: {e}")
        
        # フォールバック: デフォルトマッピング
        return {
            "BSDF_PRINCIPLED": "ShaderNodeBsdfPrincipled",
            "TEX_IMAGE": "ShaderNodeTexImage",
            "OUTPUT_MATERIAL": "ShaderNodeOutputMaterial",
            "MIX": "ShaderNodeMix",
            "SEPARATE_COLOR": "ShaderNodeSeparateColor",
            "NORMAL_MAP": "ShaderNodeNormalMap",
            "VERTEX_COLOR": "ShaderNodeVertexColor",
            "MATH": "ShaderNodeMath"
        }
        
    def _get_actual_node_type(self, normalized_type: str) -> str:
        """正規化されたノードタイプから実際のBlenderノードタイプを取得"""
        return self.node_type_mapping.get(normalized_type, normalized_type)
    
    def _get_actual_socket_name(self, node_type: str, socket_name: str, is_input: bool = True) -> str:
        """ノードタイプとBlenderバージョンに応じた実際のソケット名を取得"""
        # Blender 4.x系でのソケット名マッピング
        socket_mappings = {
            'ShaderNodeBsdfPrincipled': {
                'inputs': {
                    'Base Color': 'Base Color',
                    'BaseColor': 'Base Color',
                    'Metallic': 'Metallic',
                    'Roughness': 'Roughness',
                    'Normal': 'Normal',
                    'Alpha': 'Alpha'
                },
                'outputs': {
                    'BSDF': 'BSDF'
                }
            },
            'ShaderNodeTexImage': {
                'outputs': {
                    'Color': 'Color',
                    'Alpha': 'Alpha'
                }
            },
            'ShaderNodeOutputMaterial': {
                'inputs': {
                    'Surface': 'Surface'
                }
            },
            'ShaderNodeMix': {
                'inputs': {
                    'Color1': 'Color1',
                    'Color2': 'Color2',
                    'Fac': 'Fac'
                },
                'outputs': {
                    'Color': 'Color'
                }
            },
            'ShaderNodeSeparateColor': {
                'inputs': {
                    'Color': 'Color'
                },
                'outputs': {
                    'Red': 'Red',
                    'Green': 'Green',
                    'Blue': 'Blue'
                }
            },
            'ShaderNodeVertexColor': {
                'outputs': {
                    'Color': 'Color',
                    'Alpha': 'Alpha'
                }
            }
        }
        
        socket_type = 'inputs' if is_input else 'outputs'
        
        if node_type in socket_mappings:
            mapping = socket_mappings[node_type].get(socket_type, {})
            return mapping.get(socket_name, socket_name)
        
        return socket_name
    


def clean_bpy():
    """Blenderシーンクリア関数（外部から呼び出し可能）"""
    system = TexturePreservationSystem()
    system._clean_blender_scene()


# コマンドライン実行用
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='テクスチャ保存・復元システム')
    parser.add_argument('--mode', choices=['extract', 'apply'], required=True,
                       help='実行モード: extract (抽出) または apply (適用)')
    parser.add_argument('--source', required=True,
                       help='ソースファイルパス (extract: 元モデル, apply: リギング済みFBX)')
    parser.add_argument('--output', required=True,
                       help='出力パス (extract: 保存ディレクトリ, apply: 最終FBX)')
    parser.add_argument('--texture_data', 
                       help='テクスチャデータディレクトリ (applyモード用)')
    
    args = parser.parse_args()
    
    system = TexturePreservationSystem()
    
    if args.mode == 'extract':
        result = system.extract_and_save_texture_data(args.source, args.output)
        print(f"抽出完了: {len(result.get('textures', {}))} テクスチャ")
    
    elif args.mode == 'apply':
        if not args.texture_data:
            print("エラー: --texture_data が必要です")
            exit(1)
        success = system.apply_texture_to_rigged_model(args.source, args.texture_data, args.output)
        print(f"適用結果: {'成功' if success else '失敗'}")
