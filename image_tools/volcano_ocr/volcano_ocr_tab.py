"""
火山引擎OCR标签页模块
提供图像文字识别和视觉理解功能
"""

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import logging
import os
from PIL import Image, ImageTk
from typing import Optional, Tuple, Dict, Any, List
import threading
import time

from image_tools.core.tab_base import TabBase
from image_tools.utils.image_utils import load_image, resize_image
from image_tools.volcano_ocr.volcano_ocr_service import VolcanoOCRService

class VolcanoOCRTab(TabBase):
    """
    火山引擎OCR标签页
    提供图像文字识别和视觉理解功能的用户界面
    """
    
    def __init__(self, parent: tk.Widget, config_manager: Any, **kwargs):
        """
        初始化火山引擎OCR标签页
        
        Args:
            parent: 父级窗口部件
            config_manager: 配置管理器
            **kwargs: 其他参数
        """
        super().__init__(parent, **kwargs)
        
        self.config_manager = config_manager
        self.service = VolcanoOCRService(config_manager)
        
        # 图像相关属性
        self.image_path = None
        self.original_image = None
        self.display_image = None
        self.photo_image = None
        
        # 创建标签页UI
        self._create_widgets()
        
        # 检查API设置状态
        self._check_api_settings()
    
    def _create_widgets(self):
        """创建标签页的UI元素"""
        # 创建主框架
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建左右分栏
        left_frame = ttk.Frame(main_frame, width=400)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        left_frame.pack_propagate(False)
        
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # === 左侧框架 ===
        # 图像显示区域
        image_frame = ttk.LabelFrame(left_frame, text="图像预览")
        image_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        self.canvas = tk.Canvas(image_frame, bg="white", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 图像操作按钮
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.select_image_btn = ttk.Button(
            button_frame, 
            text="选择图像", 
            command=self.select_image
        )
        self.select_image_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.extract_text_btn = ttk.Button(
            button_frame, 
            text="提取文字", 
            command=self.extract_text,
            state=tk.DISABLED
        )
        self.extract_text_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.describe_image_btn = ttk.Button(
            button_frame, 
            text="描述图像", 
            command=self.describe_image,
            state=tk.DISABLED
        )
        self.describe_image_btn.pack(side=tk.LEFT)
        
        # === 右侧框架 ===
        # 结果显示区域
        result_frame = ttk.LabelFrame(right_frame, text="识别结果")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        self.result_text = scrolledtext.ScrolledText(
            result_frame,
            wrap=tk.WORD,
            height=10
        )
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # AI助手区域
        assistant_frame = ttk.LabelFrame(right_frame, text="AI视觉助手")
        assistant_frame.pack(fill=tk.BOTH, expand=True)
        
        self.chat_text = scrolledtext.ScrolledText(
            assistant_frame,
            wrap=tk.WORD,
            height=10
        )
        self.chat_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 输入框和发送按钮
        input_frame = ttk.Frame(assistant_frame)
        input_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        self.question_entry = ttk.Entry(input_frame)
        self.question_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        self.send_btn = ttk.Button(
            input_frame, 
            text="发送", 
            command=self.send_message,
            state=tk.DISABLED
        )
        self.send_btn.pack(side=tk.RIGHT)
        
        # 绑定回车键
        self.question_entry.bind("<Return>", lambda event: self.send_message())
    
    def _check_api_settings(self):
        """检查API设置状态并更新UI"""
        if self.service._load_api_keys():
            self.update_status("API配置已加载")
        else:
            self.show_warning("API未配置", "请在设置中配置火山引擎API密钥")
    
    def select_image(self):
        """选择图像文件并显示"""
        file_types = [
            ("图像文件", "*.jpg *.jpeg *.png *.bmp *.gif"),
            ("所有文件", "*.*")
        ]
        
        image_path = filedialog.askopenfilename(
            title="选择图像",
            filetypes=file_types
        )
        
        if image_path:
            self.image_path = image_path
            if self.load_and_display_image(image_path):
                self.extract_text_btn.configure(state=tk.NORMAL)
                self.describe_image_btn.configure(state=tk.NORMAL)
                self.send_btn.configure(state=tk.NORMAL)
                
                # 清空结果区域
                self.result_text.delete(1.0, tk.END)
                self.chat_text.delete(1.0, tk.END)
                
                # 显示图像信息
                file_name = os.path.basename(image_path)
                self.update_status(f"已加载图像: {file_name}")
    
    def load_and_display_image(self, image_path: str) -> bool:
        """
        加载并显示图像
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            bool: 是否成功加载图像
        """
        try:
            # 加载图像
            result = load_image(image_path)
            
            if result is None:
                self.show_error("加载失败", "无法加载图像，请检查文件格式")
                return False
            
            self.original_image = result
            
            # 更新图像显示
            self.update_image_display()
            return True
            
        except Exception as e:
            self.show_error("加载错误", f"加载图像时出错: {str(e)}")
            self.logger.error(f"Image loading error: {str(e)}", exc_info=True)
            return False
    
    def update_image_display(self):
        """更新画布上的图像显示"""
        if self.original_image:
            # 获取画布尺寸
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            # 如果画布尚未实际渲染，使用预设尺寸
            if canvas_width <= 1:
                canvas_width = 380
            if canvas_height <= 1:
                canvas_height = 300
            
            # 调整图像大小以适应画布
            resized_image = resize_image(self.original_image, canvas_width, canvas_height)
            
            # 创建PhotoImage对象用于显示
            self.display_image = resized_image
            self.photo_image = ImageTk.PhotoImage(self.display_image)
            
            # 清除画布并显示新图像
            self.canvas.delete("all")
            self.canvas.create_image(
                canvas_width // 2,
                canvas_height // 2,
                image=self.photo_image,
                anchor=tk.CENTER
            )
    
    def extract_text(self):
        """提取图像中的文字"""
        if not self.image_path or not self.original_image:
            self.show_error("操作失败", "请先选择一个图像")
            return
        
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "正在提取文字，请稍候...\n")
        self.update()
        
        # 禁用按钮
        self.extract_text_btn.configure(state=tk.DISABLED)
        self.describe_image_btn.configure(state=tk.DISABLED)
        self.send_btn.configure(state=tk.DISABLED)
        
        try:
            # 创建线程执行文字提取
            def extract_thread():
                try:
                    # 调用服务提取文字
                    result = self.service.extract_text(self.image_path)
                    
                    # 在主线程中更新UI
                    self.after(0, lambda: self._update_text_result(result))
                except Exception as e:
                    error_msg = f"提取文字时出错: {str(e)}"
                    self.logger.error(error_msg, exc_info=True)
                    self.after(0, lambda: self.show_error("提取失败", error_msg))
                finally:
                    # 重新启用按钮
                    self.after(0, lambda: self._enable_buttons())
            
            # 启动线程
            threading.Thread(target=extract_thread, daemon=True).start()
            
        except Exception as e:
            self.show_error("操作失败", f"提取文字时出错: {str(e)}")
            self._enable_buttons()
    
    def describe_image(self):
        """描述图像内容"""
        if not self.image_path or not self.original_image:
            self.show_error("操作失败", "请先选择一个图像")
            return
        
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "正在分析图像，请稍候...\n")
        self.update()
        
        # 禁用按钮
        self.extract_text_btn.configure(state=tk.DISABLED)
        self.describe_image_btn.configure(state=tk.DISABLED)
        self.send_btn.configure(state=tk.DISABLED)
        
        try:
            # 创建线程执行图像描述
            def describe_thread():
                try:
                    # 调用服务描述图像
                    result = self.service.describe_image(self.image_path)
                    
                    # 在主线程中更新UI
                    self.after(0, lambda: self._update_text_result(result))
                except Exception as e:
                    error_msg = f"描述图像时出错: {str(e)}"
                    self.logger.error(error_msg, exc_info=True)
                    self.after(0, lambda: self.show_error("描述失败", error_msg))
                finally:
                    # 重新启用按钮
                    self.after(0, lambda: self._enable_buttons())
            
            # 启动线程
            threading.Thread(target=describe_thread, daemon=True).start()
            
        except Exception as e:
            self.show_error("操作失败", f"描述图像时出错: {str(e)}")
            self._enable_buttons()
    
    def send_message(self):
        """发送问题给AI助手"""
        question = self.question_entry.get().strip()
        
        if not question:
            return
        
        if not self.image_path or not self.original_image:
            self.show_error("操作失败", "请先选择一个图像")
            return
        
        # 清空输入框
        self.question_entry.delete(0, tk.END)
        
        # 在聊天窗口显示用户问题
        self.chat_text.insert(tk.END, f"你: {question}\n\n")
        self.chat_text.insert(tk.END, "AI助手: ")
        self.chat_text.see(tk.END)
        self.update()
        
        # 禁用按钮
        self.extract_text_btn.configure(state=tk.DISABLED)
        self.describe_image_btn.configure(state=tk.DISABLED)
        self.send_btn.configure(state=tk.DISABLED)
        
        try:
            # 创建线程执行问答
            def answer_thread():
                try:
                    # 调用服务回答问题
                    answer = ""
                    
                    # 使用流式响应
                    for chunk in self.service.chat_stream(self.image_path, question):
                        answer += chunk
                        # 在主线程中更新UI
                        self.after(0, lambda c=chunk: self._update_chat_text(c))
                    
                    # 添加换行
                    self.after(0, lambda: self.chat_text.insert(tk.END, "\n\n"))
                    self.after(0, lambda: self.chat_text.see(tk.END))
                    
                except Exception as e:
                    error_msg = f"回答问题时出错: {str(e)}"
                    self.logger.error(error_msg, exc_info=True)
                    self.after(0, lambda: self.show_error("回答失败", error_msg))
                    # 添加错误提示到聊天窗口
                    self.after(0, lambda: self.chat_text.insert(tk.END, f"[错误: {str(e)}]\n\n"))
                    self.after(0, lambda: self.chat_text.see(tk.END))
                    
                finally:
                    # 重新启用按钮
                    self.after(0, lambda: self._enable_buttons())
            
            # 启动线程
            threading.Thread(target=answer_thread, daemon=True).start()
            
        except Exception as e:
            self.show_error("操作失败", f"回答问题时出错: {str(e)}")
            self.chat_text.insert(tk.END, f"[错误: {str(e)}]\n\n")
            self.chat_text.see(tk.END)
            self._enable_buttons()
    
    def _update_text_result(self, result: str):
        """更新结果文本区域"""
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, result)
    
    def _update_chat_text(self, text_chunk: str):
        """更新聊天文本区域"""
        self.chat_text.insert(tk.END, text_chunk)
        self.chat_text.see(tk.END)
    
    def _enable_buttons(self):
        """重新启用按钮"""
        if self.original_image:
            self.extract_text_btn.configure(state=tk.NORMAL)
            self.describe_image_btn.configure(state=tk.NORMAL)
            self.send_btn.configure(state=tk.NORMAL)
    
    def on_show(self):
        """标签页显示时的回调"""
        # 检查API设置
        self._check_api_settings()
        
        # 更新图像显示（如果有）
        if self.original_image:
            self.update_image_display()
    
    def refresh(self):
        """刷新标签页"""
        # 检查API设置
        self._check_api_settings() 