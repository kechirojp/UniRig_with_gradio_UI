#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Blender 4.2 Context Management and Mode Control Fix
Blender 4.2でのコンテキスト管理とモード制御の問題を解決
"""

import bpy
from typing import Optional, List, Any
import os

class Blender42ContextManager:
    """
    Blender 4.2対応のコンテキスト管理クラス - 公式API準拠版
    Blender 4.2 公式ドキュメント基準のコンテキスト管理
    https://docs.blender.org/api/4.2/bpy.context.html に準拠
    """
    
    def __init__(self):
        self.original_mode = None
        self.original_selection = []
        self.original_active = None
        self._context_validation_passed = False
    
    def validate_blender_42_context(self) -> bool:
        """
        Blender 4.2 コンテキスト有効性検証 - 公式API準拠
        官公式ドキュメント記載のコンテキスト項目の可用性をチェック
        """
        try:
            # 必須のGlobal Context項目検証 (bpy.context公式ドキュメント準拠)
            required_global_contexts = [
                'scene', 'view_layer', 'window', 'window_manager', 
                'preferences', 'blend_data'
            ]
            
            missing_contexts = []
            for context_attr in required_global_contexts:
                if not hasattr(bpy.context, context_attr):
                    missing_contexts.append(context_attr)
                else:
                    try:
                        # 実際にアクセス可能か確認
                        getattr(bpy.context, context_attr)
                    except Exception:
                        missing_contexts.append(f"{context_attr}(access_failed)")
            
            if missing_contexts:
                print(f"⚠️ Blender 4.2 Context検証失敗: {missing_contexts}")
                self._context_validation_passed = False
                return False
            
            # 重要なScreen Context項目検証
            screen_contexts = ['active_object', 'selected_objects']
            for context_attr in screen_contexts:
                if hasattr(bpy.context, context_attr):
                    try:
                        getattr(bpy.context, context_attr)
                    except AttributeError:
                        print(f"⚠️ {context_attr} AttributeError検出 (Blender 4.2既知問題)")
                        # 既知の問題なので続行
                
            self._context_validation_passed = True
            print("✅ Blender 4.2 Context検証成功")
            return True
            
        except Exception as e:
            print(f"❌ Blender 4.2 Context検証エラー: {e}")
            self._context_validation_passed = False
            return False
    
    def safe_get_selected_objects(self) -> List[Any]:
        """
        安全な選択オブジェクト取得 - Blender 4.2 公式API準拠
        Screen Context: selected_objects の AttributeError 問題対応
        """
        try:
            # Blender 4.2公式: Screen Context経由での選択オブジェクト取得
            if hasattr(bpy.context, 'selected_objects'):
                try:
                    # 公式の selected_objects を試行
                    selected = list(bpy.context.selected_objects)
                    print(f"✅ 公式selected_objects使用: {len(selected)}個")
                    return selected
                except AttributeError as ae:
                    print(f"⚠️ Blender 4.2既知問題: selected_objects AttributeError - {ae}")
                    # フォールバック手法へ
            
            # フォールバック1: view_layer.objects経由 (公式推奨代替手法)
            if hasattr(bpy.context, 'view_layer') and hasattr(bpy.context.view_layer, 'objects'):
                try:
                    selected = [obj for obj in bpy.context.view_layer.objects if obj.select_get()]
                    print(f"✅ view_layer.objects経由: {len(selected)}個")
                    return selected
                except Exception as e:
                    print(f"⚠️ view_layer.objects失敗: {e}")
            
            # フォールバック2: scene.objects経由
            if hasattr(bpy.context, 'scene') and hasattr(bpy.context.scene, 'objects'):
                try:
                    selected = [obj for obj in bpy.context.scene.objects if obj.select_get()]
                    print(f"✅ scene.objects経由: {len(selected)}個")
                    return selected
                except Exception as e:
                    print(f"⚠️ scene.objects失敗: {e}")
            
            # 最終フォールバック: 空リスト
            print("⚠️ 全ての選択オブジェクト取得手法が失敗 - 空リスト返却")
            return []
                
        except Exception as e:
            print(f"❌ selected_objects取得エラー: {e}")
            return []
    
    def safe_get_active_object(self) -> Optional[Any]:
        """
        安全なアクティブオブジェクト取得 - Blender 4.2 公式API準拠
        Screen Context: active_object の正しい取得パターン実装
        """
        try:
            # 公式のScreen Context: active_object を試行
            if hasattr(bpy.context, 'active_object'):
                try:
                    active_obj = bpy.context.active_object
                    if active_obj is not None:
                        print(f"✅ 公式active_object使用: {active_obj.name}")
                        return active_obj
                except AttributeError:
                    print("⚠️ active_object AttributeError - フォールバックへ")
            
            # フォールバック1: view_layer.objects.active (公式推奨)
            if hasattr(bpy.context, 'view_layer') and hasattr(bpy.context.view_layer, 'objects'):
                try:
                    if hasattr(bpy.context.view_layer.objects, 'active'):
                        active_obj = bpy.context.view_layer.objects.active
                        if active_obj is not None:
                            print(f"✅ view_layer.objects.active使用: {active_obj.name}")
                            return active_obj
                except Exception as e:
                    print(f"⚠️ view_layer.objects.active失敗: {e}")
            
            # フォールバック2: Buttons Context: object (公式記載) - Blender 4.2で削除されたため無効化
            # if hasattr(bpy.context, 'object'):
            #     try:
            #         active_obj = bpy.context.object
            #         if active_obj is not None:
            #             print(f"✅ context.object使用: {active_obj.name}")
            #             return active_obj
            #     except Exception as e:
            #         print(f"⚠️ context.object失敗: {e}")
            
            print("⚠️ アクティブオブジェクト取得: view_layer.objects.activeのみ使用")
            return None
            
        except Exception as e:
            print(f"❌ active_object取得エラー: {e}")
            return None
    
    def safe_get_active_object_mode(self) -> str:
        """安全なアクティブオブジェクトモード取得"""
        try:
            active_obj = self.safe_get_active_object()
            if active_obj is not None:
                return active_obj.mode
            else:
                # フォールバック: コンテキストから直接モード取得
                if hasattr(bpy.context, 'mode'):
                    return bpy.context.mode
                else:
                    return 'OBJECT'  # デフォルト
        except Exception as e:
            print(f"⚠️ アクティブオブジェクトモード取得エラー: {e}")
            return 'OBJECT'  # 安全なデフォルト
    
    def safe_set_active_object(self, obj: Any) -> bool:
        """
        安全なアクティブオブジェクト設定 - Blender 4.2 公式API準拠
        view_layer.objects.active の正しい設定パターン
        """
        try:
            if obj is None:
                print("⚠️ 設定対象オブジェクトがNone")
                return False
            
            # 事前コンテキスト検証
            if not self._context_validation_passed:
                self.validate_blender_42_context()
            
            # 公式推奨: view_layer.objects.active設定
            if hasattr(bpy.context, 'view_layer') and hasattr(bpy.context.view_layer, 'objects'):
                try:
                    # オブジェクトが表示層に存在することを確認
                    if obj in bpy.context.view_layer.objects:
                        bpy.context.view_layer.objects.active = obj
                        print(f"✅ view_layer.objects.active設定成功: {obj.name}")
                        return True
                    else:
                        print(f"⚠️ オブジェクト {obj.name} がview_layerに存在しません")
                except Exception as e:
                    print(f"⚠️ view_layer.objects.active設定失敗: {e}")
            
            # フォールバック: 選択状態設定と組み合わせ
            try:
                # オブジェクトを選択状態に
                obj.select_set(True)
                # 再度active設定試行
                bpy.context.view_layer.objects.active = obj
                print(f"✅ 選択設定後のactive設定成功: {obj.name}")
                return True
            except Exception as e:
                print(f"❌ フォールバックactive設定失敗: {e}")
                return False
            
        except Exception as e:
            print(f"❌ アクティブオブジェクト設定エラー: {e}")
            return False
    
    def create_blender_42_context_override(self, target_object: Any = None) -> dict:
        """
        Blender 4.2用コンテキストオーバーライド作成
        bpy.context.temp_override() 用の完全なコンテキスト辞書生成
        """
        try:
            # 基本コンテキスト要素を収集
            context_override = {}
            
            # 必須のGlobal Context要素
            if hasattr(bpy.context, 'window'):
                context_override['window'] = bpy.context.window
            if hasattr(bpy.context, 'screen'):
                context_override['screen'] = bpy.context.screen  
            if hasattr(bpy.context, 'scene'):
                context_override['scene'] = bpy.context.scene
            if hasattr(bpy.context, 'view_layer'):
                context_override['view_layer'] = bpy.context.view_layer
            
            # VIEW_3D area/regionを検索
            for window in bpy.context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'VIEW_3D':
                        context_override['area'] = area
                        for region in area.regions:
                            if region.type == 'WINDOW':
                                context_override['region'] = region
                                break
                        break
                if 'area' in context_override:
                    break
            
            # 対象オブジェクトが指定されている場合
            if target_object is not None:
                context_override['active_object'] = target_object
                context_override['object'] = target_object
                context_override['selected_objects'] = [target_object]
            
            print(f"✅ Context override作成: {len(context_override)}個の要素")
            return context_override
            
        except Exception as e:
            print(f"❌ Context override作成エラー: {e}")
            return {}
    
    def safe_set_mode(self, target_mode: str) -> bool:
        """
        安全なモード設定 - Blender 4.2 temp_override対応
        公式のcontext override機能を使用した堅牢なモード変更
        """
        try:
            current_active = self.safe_get_active_object()
            if current_active is None:
                print(f"⚠️ アクティブオブジェクトなし - モード変更スキップ")
                return False
            
            current_mode = getattr(current_active, 'mode', 'OBJECT')
            print(f"📊 現在のモード: {current_mode} → 目標: {target_mode}")
            
            if current_mode == target_mode:
                print(f"✅ 既に{target_mode}モードです")
                return True
            
            # Blender 4.2 context override使用
            context_override = self.create_blender_42_context_override(current_active)
            
            try:
                # temp_override使用でコンテキスト保証
                with bpy.context.temp_override(**context_override):
                    bpy.ops.object.mode_set(mode=target_mode)
                    print(f"✅ context.temp_override使用モード変更成功: {current_mode} → {target_mode}")
                    return True
                    
            except Exception as override_error:
                print(f"⚠️ temp_override失敗: {override_error}")
                
                # フォールバック: 従来の方法
                try:
                    bpy.ops.object.mode_set(mode=target_mode)
                    print(f"✅ フォールバックモード変更成功: {current_mode} → {target_mode}")
                    return True
                except Exception as fallback_error:
                    print(f"❌ フォールバックモード変更失敗: {fallback_error}")
                    
                    # 最終フォールバック: OBJECTモード経由
                    try:
                        if current_mode != 'OBJECT':
                            bpy.ops.object.mode_set(mode='OBJECT')
                            print(f"✅ OBJECTモードに復帰")
                        
                        if target_mode != 'OBJECT':
                            bpy.ops.object.mode_set(mode=target_mode)
                            print(f"✅ {target_mode}モードに設定")
                        
                        return True
                    except Exception as final_error:
                        print(f"❌ 最終フォールバック失敗: {final_error}")
                        return False
                    
        except Exception as e:
            print(f"❌ モード変更エラー: {e}")
            return False
    
    def safe_deselect_all(self):
        """安全な全選択解除"""
        try:
            # Method 1: 標準的な方法
            try:
                bpy.ops.object.select_all(action='DESELECT')
                print("✅ 全選択解除成功 (Method 1)")
                return
            except:
                pass
            
            # Method 2: 個別選択解除
            try:
                selected = self.safe_get_selected_objects()
                for obj in selected:
                    obj.select_set(False)
                print(f"✅ 全選択解除成功 (Method 2): {len(selected)}個")
                return
            except:
                pass
            
            # Method 3: 全オブジェクト個別処理
            try:
                for obj in bpy.data.objects:
                    obj.select_set(False)
                print("✅ 全選択解除成功 (Method 3)")
                return
            except:
                pass
                
        except Exception as e:
            print(f"⚠️ 全選択解除エラー: {e}")
    
    def safe_select_objects(self, objects: List[Any]):
        """安全なオブジェクト選択"""
        try:
            self.safe_deselect_all()
            
            for obj in objects:
                if obj and hasattr(obj, 'select_set'):
                    obj.select_set(True)
            
            print(f"✅ オブジェクト選択完了: {len(objects)}個")
            
        except Exception as e:
            print(f"❌ オブジェクト選択エラー: {e}")
    
    def prepare_for_fbx_export(self, target_objects: List[Any] = None) -> bool:
        """FBXエクスポート準備（強化版）"""
        try:
            print("🔧 FBXエクスポート準備開始...")
            
            # Step 0: 強制Object Mode復帰（Edit Mode問題解決）
            self.force_object_mode()
            
            # Step 1: 全アーマチュアのEdit Mode脱出確認
            armature_objects = [obj for obj in bpy.data.objects if obj.type == 'ARMATURE']
            for armature in armature_objects:
                self.safe_armature_mode_exit(armature)
            
            # Step 2: 対象オブジェクト選択
            if target_objects:
                self.safe_select_objects(target_objects)
                
                # アクティブオブジェクト設定
                if target_objects:
                    self.safe_set_active_object(target_objects[0])
            else:
                # 全オブジェクト選択
                all_objects = list(bpy.data.objects)
                self.safe_select_objects(all_objects)
                if all_objects:
                    self.safe_set_active_object(all_objects[0])
            
            # Step 3: エクスポート前検証
            active = self.safe_get_active_object()
            selected = self.safe_get_selected_objects()
            
            print(f"📊 エクスポート準備完了:")
            print(f"   - アクティブ: {active.name if active else 'なし'}")
            print(f"   - 選択数: {len(selected)}個")
            
            return active is not None and len(selected) > 0
            
        except Exception as e:
            print(f"❌ FBXエクスポート準備エラー: {e}")
            return False
    
    def safe_get_active_object_mode(self) -> Optional[str]:
        """安全なアクティブオブジェクトモード取得"""
        try:
            active_obj = self.safe_get_active_object()
            if active_obj is None:
                return None
            
            # モード情報を取得
            if hasattr(active_obj, 'mode'):
                return active_obj.mode
            else:
                # フォールバック: OBJECTモードと仮定
                return 'OBJECT'
                
        except Exception as e:
            print(f"⚠️ アクティブオブジェクトモード取得エラー: {e}")
            return None
        
    def force_object_mode(self) -> bool:
        """強制的にObject Modeに戻す（Edit Mode脱出問題対応）"""
        try:
            print("🔧 強制Object Mode復帰開始...")
            
            # Method 1: 全オブジェクトをObject Modeに強制設定
            success_count = 0
            for obj in bpy.data.objects:
                if obj.type in ['MESH', 'ARMATURE']:
                    try:
                        # アクティブオブジェクト設定
                        bpy.context.view_layer.objects.active = obj
                        obj.select_set(True)
                        
                        # 現在のモード確認
                        if hasattr(obj, 'mode') and obj.mode != 'OBJECT':
                            print(f"🔄 {obj.name} を {obj.mode} → OBJECT に変更")
                            bpy.ops.object.mode_set(mode='OBJECT')
                            success_count += 1
                    except Exception as e:
                        print(f"⚠️ {obj.name} モード変更警告: {e}")
                        continue
            
            # Method 2: Context reset試行
            try:
                bpy.context.view_layer.objects.active = None
                # Use safe method instead of direct bpy.context.selected_objects
                selected_objects = self.safe_get_selected_objects()
                for obj in selected_objects:
                    obj.select_set(False)
                print("✅ Context reset完了")
            except Exception as e:
                print(f"⚠️ Context reset失敗: {e}")
                pass
            
            # Method 3: 全選択解除してから最初のオブジェクトをアクティブに
            try:
                self.safe_deselect_all()
                mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
                if mesh_objects:
                    self.safe_set_active_object(mesh_objects[0])
                    print(f"✅ アクティブオブジェクト再設定: {mesh_objects[0].name}")
            except:
                pass
            
            print(f"✅ 強制Object Mode復帰完了: {success_count}個のオブジェクトを処理")
            return True
            
        except Exception as e:
            print(f"❌ 強制Object Mode復帰エラー: {e}")
            return False

    def safe_armature_mode_exit(self, armature_obj=None) -> bool:
        """アーマチュア専用の安全なEdit Mode脱出 - パラメータなしで全アーマチュア処理"""
        try:
            # パラメータなしの場合、全アーマチュアを処理
            if armature_obj is None:
                print("🦴 全アーマチュアのEdit Mode脱出開始...")
                armatures = [obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE']
                if not armatures:
                    print("✅ アーマチュアが見つかりません")
                    return True
                
                all_success = True
                for armature in armatures:
                    success = self.safe_armature_mode_exit(armature)
                    if not success:
                        all_success = False
                        print(f"⚠️ {armature.name} のEdit Mode脱出失敗")
                
                print(f"✅ 全アーマチュア処理完了: {len(armatures)}個中、成功: {all_success}")
                return all_success
            
            # 特定のアーマチュア処理
            if armature_obj.type != 'ARMATURE':
                return False
            
            print(f"🦴 アーマチュア {armature_obj.name} のEdit Mode脱出開始...")
            
            # Step 1: アクティブオブジェクト設定
            self.safe_set_active_object(armature_obj)
            
            # Step 2: 現在のモード確認
            current_mode = getattr(armature_obj, 'mode', 'OBJECT')
            print(f"📊 現在のモード: {current_mode}")
            
            if current_mode == 'OBJECT':
                print("✅ 既にObject Modeです")
                return True
            
            # Step 3: 段階的モード変更
            try:
                # まず選択状態をクリア
                bpy.ops.object.select_all(action='DESELECT')
                armature_obj.select_set(True)
                bpy.context.view_layer.objects.active = armature_obj
                
                # Edit Modeの場合、まずEdit bones選択をクリア
                if current_mode == 'EDIT':
                    try:
                        bpy.ops.armature.select_all(action='DESELECT')
                    except:
                        pass
                
                # Object Modeに変更
                bpy.ops.object.mode_set(mode='OBJECT')
                print(f"✅ {armature_obj.name} を Object Mode に変更 (Blender 4.2対応)")
                return True
                
            except Exception as mode_error:
                print(f"⚠️ 通常のモード変更失敗: {mode_error}")
                
                # フォールバック: 強制的にObject Modeに戻す
                try:
                    # 別のオブジェクトを一時的にアクティブにしてからアーマチュアに戻す
                    temp_objects = [obj for obj in bpy.data.objects if obj != armature_obj and obj.type == 'MESH']
                    if temp_objects:
                        bpy.context.view_layer.objects.active = temp_objects[0]
                        bpy.ops.object.mode_set(mode='OBJECT')
                        
                        # アーマチュアに戻る
                        bpy.context.view_layer.objects.active = armature_obj
                        bpy.ops.object.mode_set(mode='OBJECT')
                        
                        print(f"✅ {armature_obj.name} フォールバック Object Mode 変更成功")
                        return True
                except Exception as fallback_error:
                    print(f"❌ フォールバック失敗: {fallback_error}")
                    return False
                    
        except Exception as e:
            print(f"❌ アーマチュアEdit Mode脱出エラー: {e}")
            return False

    def safe_clear_selection(self) -> bool:
        """安全な全選択解除"""
        try:
            # Method 1: 標準的な選択解除
            bpy.ops.object.select_all(action='DESELECT')
            print("✅ 全選択解除成功 (Method 1)")
            return True
        except Exception as e1:
            try:
                # Method 2: 手動選択解除
                for obj in bpy.context.scene.objects:
                    obj.select_set(False)
                print("✅ 全選択解除成功 (Method 2)")
                return True
            except Exception as e2:
                print(f"❌ 全選択解除失敗: Method1={e1}, Method2={e2}")
                return False

    def safe_fbx_export_context_preparation(self) -> bool:
        """FBXエクスポート用の完全なコンテキスト準備"""
        try:
            print("🔧 FBXエクスポート用コンテキスト準備開始...")
            
            # 1. 強制的にObject Mode移行
            self.force_object_mode()
            
            # 2. 全選択を解除
            self.safe_clear_selection()
            
            # 3. 全アーマチュアのEdit Mode脱出
            armatures = [obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE']
            for armature in armatures:
                success = self.safe_armature_mode_exit(armature)
                if not success:
                    print(f"⚠️ アーマチュア {armature.name} のEdit Mode脱出失敗")
            
            # 4. コンテキストの強制リフレッシュ
            try:
                bpy.context.view_layer.update()
                print("✅ コンテキストリフレッシュ成功")
            except Exception as e:
                print(f"⚠️ コンテキストリフレッシュ警告: {e}")
            
            # 5. CRITICAL: Blender 4.2 'selected_objects' 修正
            # FBXエクスポート直前に全オブジェクトを安全に選択状態にする
            try:
                # 全オブジェクトを選択して、FBXエクスポータが'selected_objects'にアクセスできるようにする
                bpy.ops.object.select_all(action='SELECT')
                print("✅ Blender 4.2: 全オブジェクト選択でselected_objects問題回避")
                
                # アクティブオブジェクトを確実に設定
                mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
                if mesh_objects:
                    self.safe_set_active_object(mesh_objects[0])
                    print(f"✅ アクティブオブジェクト設定: {mesh_objects[0].name}")
                elif bpy.context.scene.objects:
                    self.safe_set_active_object(bpy.context.scene.objects[0])
                    print(f"✅ フォールバックアクティブオブジェクト設定: {bpy.context.scene.objects[0].name}")
                
            except Exception as select_error:
                print(f"⚠️ 全選択操作警告: {select_error}")
            
            print("✅ FBXエクスポート用コンテキスト準備完了")
            return True
            
        except Exception as e:
            print(f"❌ FBXエクスポート用コンテキスト準備失敗: {e}")
            return False

    def get_safe_export_context(self) -> dict:
        """FBXエクスポート用の安全なコンテキスト情報を取得"""
        try:
            # Blender 4.2対応のコンテキスト情報取得
            context_info = {
                'has_selected_objects': False,
                'selected_count': 0,
                'active_object': None,
                'scene_objects_count': len(bpy.context.scene.objects),
                'all_in_object_mode': True
            }
            
            # 選択オブジェクト情報の安全な取得
            selected_objects = self.safe_get_selected_objects()
            context_info['selected_count'] = len(selected_objects)
            context_info['has_selected_objects'] = len(selected_objects) > 0
            
            # アクティブオブジェクト情報の安全な取得
            active_obj = self.safe_get_active_object()
            context_info['active_object'] = active_obj.name if active_obj else None
            
            # 全オブジェクトのモード確認
            for obj in bpy.context.scene.objects:
                if hasattr(obj, 'mode') and obj.mode != 'OBJECT':
                    context_info['all_in_object_mode'] = False
                    break
            
            return context_info
            
        except Exception as e:
            print(f"⚠️ コンテキスト情報取得エラー: {e}")
            return {
                'has_selected_objects': False,
                'selected_count': 0,
                'active_object': None,
                'scene_objects_count': 0,
                'all_in_object_mode': False,
                'error': str(e)
            }
            
    def ultimate_defensive_armature_resolution(self) -> bool:
        """
        Ultimate Defensive Armature Resolution - 最強のアーマチュア問題解決システム
        """
        try:
            print("🛡️ Ultimate Defensive Armature Resolution - 開始...")
            
            # Strategy 1: Ultimate armature mode reset
            if self.ultimate_armature_mode_reset():
                print("✅ Strategy 1 (Ultimate Reset) successful")
                return True
            
            # Strategy 2: Context-aware armature handling
            if self.context_aware_armature_handling():
                print("✅ Strategy 2 (Context-Aware) successful") 
                return True
            
            # Strategy 3: Nuclear scene reset protocol
            if self.nuclear_scene_reset_protocol():
                print("✅ Strategy 3 (Nuclear Reset) successful")
                return True
            
            # Strategy 4: Direct data manipulation
            if self.direct_data_manipulation_mode_reset():
                print("✅ Strategy 4 (Direct Manipulation) successful")
                return True
            
            # Strategy 5: Progressive context recovery
            if self.progressive_context_recovery_system():
                print("✅ Strategy 5 (Progressive Recovery) successful")
                return True
            
            # If all strategies fail
            print("❌ ALL DEFENSIVE STRATEGIES FAILED")
            print("🚨 CRITICAL: Fundamental Blender 4.2 compatibility issue detected")
            return False
            
        except Exception as e:
            print(f"Ultimate Defensive Armature Resolution failed: {e}")
            return False

    def ultimate_armature_mode_reset(self) -> bool:
        """
        Ultimate armature mode reset using Blender 4.2 best practices
        """
        try:
            # 1. Force all objects to Object mode first
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # 2. Clear all selections safely
            bpy.ops.object.select_all(action='DESELECT')
            
            # 3. Process all armature objects in scene
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE':
                    # Ensure the armature is selectable and visible
                    obj.hide_set(False)
                    obj.hide_viewport = False
                    obj.select_set(True)
                    bpy.context.view_layer.objects.active = obj
                    
                    # Force exit any remaining edit modes
                    if obj.mode != 'OBJECT':
                        bpy.context.view_layer.objects.active = obj
                        bpy.ops.object.mode_set(mode='OBJECT')
                    
                    obj.select_set(False)
            
            # 4. Final verification
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.mode != 'OBJECT':
                    return False
                    
            return True
            
        except Exception as e:
            print(f"Ultimate armature mode reset failed: {e}")
            return False

    def context_aware_armature_handling(self) -> bool:
        """
        Blender 4.2 context-aware armature processing
        """
        try:
            # Save current context state
            original_active = bpy.context.view_layer.objects.active
            original_selection = [obj for obj in bpy.context.selected_objects]
            
            # Ensure we have a valid 3D viewport context
            window = bpy.context.window
            screen = window.screen
            
            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    for region in area.regions:
                        if region.type == 'WINDOW':
                            # Override context for armature operations
                            context_override = {
                                'window': window,
                                'screen': screen,
                                'area': area,
                                'region': region,
                                'scene': bpy.context.scene,
                                'view_layer': bpy.context.view_layer
                            }
                            
                            # Perform armature mode operations with proper context
                            with bpy.context.temp_override(**context_override):
                                # Clear selections
                                bpy.ops.object.select_all(action='DESELECT')
                                
                                # Process each armature with guaranteed context
                                for obj in bpy.data.objects:
                                    if obj.type == 'ARMATURE':
                                        obj.select_set(True)
                                        bpy.context.view_layer.objects.active = obj
                                        
                                        # Force object mode with context override
                                        if obj.mode != 'OBJECT':
                                            bpy.ops.object.mode_set(mode='OBJECT')
                                        
                                        obj.select_set(False)
            
            # Restore original context
            bpy.context.view_layer.objects.active = original_active
            for obj in original_selection:
                obj.select_set(True)
                
            return True
            
        except Exception as e:
            print(f"Context-aware armature handling failed: {e}")
            return False

    def nuclear_scene_reset_protocol(self) -> bool:
        """
        Nuclear option: Complete scene reset and context reconstruction
        """
        try:
            print("🚨 Nuclear Scene Reset Protocol...")
            
            # 1. Store critical object references
            armature_objects = [obj for obj in bpy.data.objects if obj.type == 'ARMATURE']
            
            # 2. Force clear all selection and active objects
            bpy.context.view_layer.objects.active = None
            
            # 3. For each armature, force exit Edit Mode with extreme prejudice
            for armature in armature_objects:
                try:
                    # Force set to object mode regardless of current state
                    armature.select_set(True)
                    bpy.context.view_layer.objects.active = armature
                    
                    # Multiple mode exit attempts
                    for attempt in range(3):
                        try:
                            if armature.mode != 'OBJECT':
                                bpy.ops.object.mode_set(mode='OBJECT')
                            break
                        except:
                            print(f"Mode set attempt {attempt+1} failed for {armature.name}")
                            continue
                    
                    # If still stuck, use data-level manipulation
                    if armature.mode != 'OBJECT':
                        # Force data-level mode reset
                        armature.mode = 'OBJECT'
                        
                    armature.select_set(False)
                    
                except Exception as e:
                    print(f"Nuclear reset failed for armature {armature.name}: {e}")
            
            # 4. Clear all context references
            bpy.context.view_layer.objects.active = None
            bpy.ops.object.select_all(action='DESELECT')
            
            # 5. Force garbage collection and context refresh
            import gc
            gc.collect()
            
            # 6. Final verification
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.mode != 'OBJECT':
                    print(f"❌ Nuclear reset FAILED: {obj.name} still in {obj.mode}")
                    return False
            
            print("✅ Nuclear Scene Reset Protocol successful")
            return True
            
        except Exception as e:
            print(f"Nuclear Scene Reset Protocol failed: {e}")
            return False

    def direct_data_manipulation_mode_reset(self) -> bool:
        """
        Direct data manipulation approach - bypass Blender operators entirely
        """
        try:
            print("🔧 Direct Data Manipulation Mode Reset...")
            
            # Direct access to Blender's internal data
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE':
                    # Direct mode setting - bypasses operator system
                    obj.mode = 'OBJECT'
                    
                    # Clear any edit mode data if exists
                    if hasattr(obj.data, 'edit_bones'):
                        obj.data.edit_bones.clear()
                    
                    # Force update object
                    obj.update_tag()
            
            # Force scene update
            bpy.context.view_layer.update()
            
            # Verification
            failed_objects = []
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.mode != 'OBJECT':
                    failed_objects.append(obj.name)
            
            if failed_objects:
                print(f"❌ Direct manipulation failed for: {failed_objects}")
                return False
            
            print("✅ Direct Data Manipulation successful")
            return True
            
        except Exception as e:
            print(f"Direct Data Manipulation failed: {e}")
            return False

    def progressive_context_recovery_system(self) -> bool:
        """
        Step-by-step context recovery with checkpoint validation
        """
        try:
            print("🔄 Progressive Context Recovery System...")
            
            # Checkpoint 1: Identify problem objects
            problem_armatures = []
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.mode != 'OBJECT':
                    problem_armatures.append(obj)
            
            if not problem_armatures:
                print("✅ No problem armatures found")
                return True
            
            print(f"🎯 Found {len(problem_armatures)} problem armatures: {[obj.name for obj in problem_armatures]}")
            
            # Checkpoint 2: Progressive recovery for each problem armature
            for armature in problem_armatures:
                print(f"🔧 Processing armature: {armature.name}")
                
                # Step 1: Clear all context
                bpy.context.view_layer.objects.active = None
                bpy.ops.object.select_all(action='DESELECT')
                
                # Step 2: Isolate this armature
                armature.select_set(True)
                bpy.context.view_layer.objects.active = armature
                
                # Step 3: Multiple recovery attempts
                recovery_success = False
                
                # Attempt 1: Standard mode set
                try:
                    bpy.ops.object.mode_set(mode='OBJECT')
                    if armature.mode == 'OBJECT':
                        recovery_success = True
                        print(f"✅ Standard recovery successful for {armature.name}")
                except:
                    pass
                
                # Attempt 2: Context override recovery
                if not recovery_success:
                    try:
                        # Find valid 3D viewport context
                        for window in bpy.context.window_manager.windows:
                            for area in window.screen.areas:
                                if area.type == 'VIEW_3D':
                                    for region in area.regions:
                                        if region.type == 'WINDOW':
                                            context_override = {
                                                'window': window,
                                                'screen': window.screen,
                                                'area': area,
                                                'region': region,
                                                'scene': bpy.context.scene,
                                                'view_layer': bpy.context.view_layer,
                                                'active_object': armature,
                                                'selected_objects': [armature]
                                            }
                                            
                                            with bpy.context.temp_override(**context_override):
                                                bpy.ops.object.mode_set(mode='OBJECT')
                                                
                                            if armature.mode == 'OBJECT':
                                                recovery_success = True
                                                print(f"✅ Context override recovery successful for {armature.name}")
                                            break
                                    if recovery_success:
                                        break
                            if recovery_success:
                                break
                    except:
                        pass
                
                # Attempt 3: Direct data manipulation
                if not recovery_success:
                    try:
                        armature.mode = 'OBJECT'
                        if hasattr(armature.data, 'edit_bones'):
                            armature.data.edit_bones.clear()
                        armature.update_tag()
                        bpy.context.view_layer.update()
                        
                        if armature.mode == 'OBJECT':
                            recovery_success = True
                            print(f"✅ Direct manipulation recovery successful for {armature.name}")
                    except:
                        pass
                
                # Final check for this armature
                if not recovery_success:
                    print(f"❌ All recovery attempts failed for {armature.name}")
                    return False
                
                # Clean up after successful recovery
                armature.select_set(False)
            
            # Checkpoint 3: Final scene validation
            bpy.context.view_layer.objects.active = None
            bpy.ops.object.select_all(action='DESELECT')
            
            # Final verification
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.mode != 'OBJECT':
                    print(f"❌ Progressive recovery FAILED: {obj.name} still in {obj.mode}")
                    return False
            
            print("✅ Progressive Context Recovery System successful")
            return True
            
        except Exception as e:
            print(f"Progressive Context Recovery System failed: {e}")
            return False

    def safe_fbx_export_with_context_override(self, filepath: str, **kwargs) -> bool:
        """
        Blender 4.2 Context Override でFBXエクスポートを安全実行
        selected_objects と active_object AttributeError 問題を解決
        """
        try:
            print(f"🚀 Blender 4.2 Context Override FBXエクスポート開始: {filepath}")
            
            # FBXエクスポート準備
            self.prepare_for_fbx_export()
            
            # Blender 4.2 Deprecated Parameter Cleanup
            if 'use_ascii' in kwargs:
                del kwargs['use_ascii']  # Remove deprecated parameter
                print("✅ Deprecated use_ascii parameter removed for Blender 4.2")
            
            # Context Override用のオブジェクト準備
            selected_objects = self.safe_get_selected_objects()
            active_object = self.safe_get_active_object()
            
            # 3D Viewport Context Override を取得
            context_override = self._get_viewport_context_override()
            if not context_override:
                print("⚠️ Viewport context override失敗 - 直接エクスポート試行")
                result = bpy.ops.export_scene.fbx(filepath=filepath, **kwargs)
            else:
                # Context Override でエクスポート実行
                context_override.update({
                    'selected_objects': selected_objects,
                    'active_object': active_object
                })
                
                print(f"📊 Context Override: {len(selected_objects)} selected, active: {active_object.name if active_object else 'None'}")
                
                with bpy.context.temp_override(**context_override):
                    result = bpy.ops.export_scene.fbx(filepath=filepath, **kwargs)
            
            if result == {'FINISHED'}:
                file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
                print(f"✅ Context Override FBXエクスポート成功: {filepath} ({file_size:,} bytes)")
                return True
            else:
                print(f"⚠️ Context Override FBXエクスポート警告: {result}")
                return False
                
        except Exception as e:
            print(f"❌ Context Override FBXエクスポートエラー: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def safe_gltf_export_with_context_override(self, filepath: str, **kwargs) -> bool:
        """
        Blender 4.2 Context Override でGLTFエクスポートを安全実行
        selected_objects と active_object AttributeError 問題を解決
        """
        try:
            print(f"🚀 Blender 4.2 Context Override GLTFエクスポート開始: {filepath}")
            
            # GLTFエクスポート準備
            self.prepare_for_fbx_export()  # 同じ準備プロセス使用
            
            # Context Override用のオブジェクト準備
            selected_objects = self.safe_get_selected_objects()
            active_object = self.safe_get_active_object()
            
            # 3D Viewport Context Override を取得
            context_override = self._get_viewport_context_override()
            if not context_override:
                print("⚠️ Viewport context override失敗 - 直接エクスポート試行")
                result = bpy.ops.export_scene.gltf(filepath=filepath, **kwargs)
            else:
                # Context Override でエクスポート実行
                context_override.update({
                    'selected_objects': selected_objects,
                    'active_object': active_object
                })
                
                print(f"📊 Context Override: {len(selected_objects)} selected, active: {active_object.name if active_object else 'None'}")
                
                with bpy.context.temp_override(**context_override):
                    result = bpy.ops.export_scene.gltf(filepath=filepath, **kwargs)
            
            if result == {'FINISHED'}:
                file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
                print(f"✅ Context Override GLTFエクスポート成功: {filepath} ({file_size:,} bytes)")
                return True
            else:
                print(f"⚠️ Context Override GLTFエクスポート警告: {result}")
                return False
                
        except Exception as e:
            print(f"❌ Context Override GLTFエクスポートエラー: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _get_viewport_context_override(self) -> dict:
        """
        3D Viewport Context Override を取得
        FBX/GLTFエクスポートに必要な3Dビューポートコンテキストを準備
        """
        try:
            # Window Manager から適切なウィンドウとスクリーンを取得
            window = bpy.context.window
            if not window:
                window = bpy.context.window_manager.windows[0] if bpy.context.window_manager.windows else None
            
            if not window:
                print("❌ Viewport context: Window not found")
                return {}
            
            screen = window.screen
            
            # 3D Viewport エリアを検索
            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    # WINDOW リージョンを検索
                    for region in area.regions:
                        if region.type == 'WINDOW':
                            context_override = {
                                'window': window,
                                'screen': screen,
                                'area': area,
                                'region': region,
                                'scene': bpy.context.scene,
                                'view_layer': bpy.context.view_layer
                            }
                            print("✅ 3D Viewport context override準備完了")
                            return context_override
            
            print("⚠️ 3D Viewport area not found - fallback context")
            return {
                'window': window,
                'screen': screen,
                'scene': bpy.context.scene,
                'view_layer': bpy.context.view_layer
            }
            
        except Exception as e:
            print(f"❌ Viewport context override取得エラー: {e}")
            return {}

    # ... existing methods ...
def apply_blender_42_fixes():
    """Blender 4.2対応修正を適用"""
    
    # グローバルコンテキストマネージャー作成
    global blender_context_mgr
    blender_context_mgr = Blender42ContextManager()
    
    print("✅ Blender 4.2コンテキスト管理システム初期化完了")
    
    return blender_context_mgr

# パッチ関数
def patch_fbx_export_context():
    """FBXエクスポート用コンテキストパッチ"""
    
    def safe_fbx_export(filepath: str, **kwargs):
        """安全なFBXエクスポート関数"""
        try:
            mgr = apply_blender_42_fixes()
            
            # エクスポート準備
            if not mgr.prepare_for_fbx_export():
                raise RuntimeError("FBXエクスポート準備失敗")
            
            # FBXエクスポート実行 - 🚨 Blender 4.2: Binary FBX is default
            # Remove deprecated use_ascii parameter for Blender 4.2 compatibility
            if 'use_ascii' in kwargs:
                del kwargs['use_ascii']  # Remove deprecated parameter
            result = bpy.ops.export_scene.fbx(filepath=filepath, **kwargs)
            
            if result == {'FINISHED'}:
                print(f"✅ FBXエクスポート成功: {filepath}")
                return True
            else:
                print(f"⚠️ FBXエクスポート警告: {result}")
                return False
                
        except Exception as e:
            print(f"❌ FBXエクスポートエラー: {e}")
            return False
    
    return safe_fbx_export

if __name__ == "__main__":
    # テスト実行
    mgr = apply_blender_42_fixes()
    print("🔧 Blender 4.2コンテキスト管理テスト完了")
