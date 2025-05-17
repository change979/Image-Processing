"""
图像OCR和翻译界面模块
提供识别图像中文字并翻译的用户界面
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk
import threading
import cv2
import numpy as np
from typing import Optional, Dict, List, Any, Tuple

from ..utils.image_utils import load_image, resize_image_for_display, get_image_for_tk
from ..utils.config_manager import ConfigManager
from .ocr_translator import OCRTranslator

class OCRTranslatorTab(ttk.Frame):
    """OCR和翻译标签页"""
    
    def __init__(self, parent):
        """初始化OCR和翻译标签页
        
        Args:
            parent: 父级窗口组件
        """
        super().__init__(parent)
        
        # 初始化成员变量
        self.image = None  # 当前加载的PIL图像
        self.image_path = None  # 当前图像路径
        self.tk_image = None  # Tkinter图像对象
        self.config_manager = ConfigManager()  # 配置管理器
        self.ocr_translator = OCRTranslator()  # OCR和翻译处理器
        
        # 识别状态
        self.is_processing = False  # 是否正在处理
        self.recognized_text = ""  # 识别出的文本
        self.translated_text = ""  # 翻译结果
        
        # 设置UI
        self._setup_ui()
        
        # 加载保存的参数设置
        self._load_saved_params()
        
    def _setup_ui(self):
        """设置用户界面"""
        # 创建主分隔窗口
        self.paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        
        # 创建左侧控制面板
        self.control_frame = ttk.Frame(self.paned_window, width=300)
        self.control_frame.pack_propagate(False)  # 固定宽度
        self.paned_window.add(self.control_frame, weight=0)
        
        # 创建右侧显示区域
        self.display_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.display_frame, weight=1)
        
        # 设置左侧控制面板
        self._setup_control_panel()
        
        # 设置右侧显示区域
        self._setup_display_panel()
        
        # 状态栏
        self.status_frame = ttk.Frame(self)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_label = ttk.Label(self.status_frame, text="就绪")
        self.status_label.pack(side=tk.LEFT, padx=5, pady=2)
        
        self.progress_bar = ttk.Progressbar(self.status_frame, mode='indeterminate')
        self.progress_bar.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5, pady=2)
        self.progress_bar.pack_forget()  # 隐藏进度条
        
    def _setup_control_panel(self):
        """设置左侧控制面板"""
        # 图像加载区域
        load_frame = ttk.LabelFrame(self.control_frame, text="图像加载")
        load_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(load_frame, text="打开图像", command=self._load_image).pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(load_frame, text="截取屏幕", command=self._capture_screen).pack(fill=tk.X, padx=5, pady=5)
        
        # OCR设置区域
        ocr_frame = ttk.LabelFrame(self.control_frame, text="OCR设置")
        ocr_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # OCR服务选择
        ttk.Label(ocr_frame, text="OCR服务:").pack(anchor=tk.W, padx=5, pady=2)
        self.ocr_service_var = tk.StringVar(value="默认")
        ocr_service_values = ["默认", "百度OCR", "腾讯OCR", "讯飞OCR"]
        ocr_service_combo = ttk.Combobox(
            ocr_frame, 
            textvariable=self.ocr_service_var,
            values=ocr_service_values,
            state="readonly"
        )
        ocr_service_combo.pack(fill=tk.X, padx=5, pady=5)
        
        # 语言选择
        ttk.Label(ocr_frame, text="识别语言:").pack(anchor=tk.W, padx=5, pady=2)
        self.ocr_language_var = tk.StringVar(value="中文")
        ocr_language_values = ["中文", "英文", "日文", "韩文", "自动检测"]
        ocr_language_combo = ttk.Combobox(
            ocr_frame, 
            textvariable=self.ocr_language_var,
            values=ocr_language_values,
            state="readonly"
        )
        ocr_language_combo.pack(fill=tk.X, padx=5, pady=5)
        
        # 开始OCR按钮
        self.ocr_button = ttk.Button(
            ocr_frame, 
            text="识别文字", 
            command=self._start_ocr
        )
        self.ocr_button.pack(fill=tk.X, padx=5, pady=5)
        
        # 翻译设置区域
        translate_frame = ttk.LabelFrame(self.control_frame, text="翻译设置")
        translate_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 翻译服务选择
        ttk.Label(translate_frame, text="翻译服务:").pack(anchor=tk.W, padx=5, pady=2)
        self.translate_service_var = tk.StringVar(value="默认")
        translate_service_values = ["默认", "百度翻译", "腾讯翻译", "有道翻译"]
        translate_service_combo = ttk.Combobox(
            translate_frame, 
            textvariable=self.translate_service_var,
            values=translate_service_values,
            state="readonly"
        )
        translate_service_combo.pack(fill=tk.X, padx=5, pady=5)
        
        # 目标语言选择
        ttk.Label(translate_frame, text="目标语言:").pack(anchor=tk.W, padx=5, pady=2)
        self.target_language_var = tk.StringVar(value="英文")
        target_language_values = ["中文", "英文", "日文", "韩文", "法文", "德文", "俄文"]
        target_language_combo = ttk.Combobox(
            translate_frame, 
            textvariable=self.target_language_var,
            values=target_language_values,
            state="readonly"
        )
        target_language_combo.pack(fill=tk.X, padx=5, pady=5)
        
        # 开始翻译按钮
        self.translate_button = ttk.Button(
            translate_frame, 
            text="翻译文本", 
            command=self._start_translate,
            state=tk.DISABLED
        )
        self.translate_button.pack(fill=tk.X, padx=5, pady=5)
        
        # 结果操作区域
        result_frame = ttk.Frame(self.control_frame)
        result_frame.pack(fill=tk.X, padx=5, pady=10)
        
        ttk.Button(result_frame, text="复制原文", command=lambda: self._copy_text(self.recognized_text)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Button(result_frame, text="复制译文", command=lambda: self._copy_text(self.translated_text)).pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=2)
        
    def _setup_display_panel(self):
        """设置右侧显示区域"""
        # 创建垂直分隔区域
        self.vertical_paned = ttk.PanedWindow(self.display_frame, orient=tk.VERTICAL)
        self.vertical_paned.pack(fill=tk.BOTH, expand=True)
        
        # 创建上部图像显示区域
        self.image_frame = ttk.Frame(self.vertical_paned)
        self.vertical_paned.add(self.image_frame, weight=1)
        
        # 创建画布用于显示图像
        self.canvas = tk.Canvas(self.image_frame, bg="#EEEEEE", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # 创建下部文本显示区域
        self.text_frame = ttk.Frame(self.vertical_paned)
        self.vertical_paned.add(self.text_frame, weight=1)
        
        # 创建标签页来显示识别文本和翻译结果
        self.text_notebook = ttk.Notebook(self.text_frame)
        self.text_notebook.pack(fill=tk.BOTH, expand=True)
        
        # 创建识别文本标签页
        self.ocr_text_frame = ttk.Frame(self.text_notebook)
        self.text_notebook.add(self.ocr_text_frame, text="识别文本")
        
        self.ocr_text = scrolledtext.ScrolledText(self.ocr_text_frame, wrap=tk.WORD)
        self.ocr_text.pack(fill=tk.BOTH, expand=True)
        
        # 创建翻译结果标签页
        self.translated_text_frame = ttk.Frame(self.text_notebook)
        self.text_notebook.add(self.translated_text_frame, text="翻译结果")
        
        self.translated_text_widget = scrolledtext.ScrolledText(self.translated_text_frame, wrap=tk.WORD)
        self.translated_text_widget.pack(fill=tk.BOTH, expand=True)
        
    def _load_saved_params(self):
        """加载保存的参数设置"""
        # 读取OCR服务
        saved_ocr_service = self.config_manager.get_config("ocr_service", "默认")
        self.ocr_service_var.set(saved_ocr_service)
        
        # 读取OCR语言
        saved_ocr_language = self.config_manager.get_config("ocr_language", "中文")
        self.ocr_language_var.set(saved_ocr_language)
        
        # 读取翻译服务
        saved_translate_service = self.config_manager.get_config("translate_service", "默认")
        self.translate_service_var.set(saved_translate_service)
        
        # 读取目标语言
        saved_target_language = self.config_manager.get_config("target_language", "英文")
        self.target_language_var.set(saved_target_language)
        
    def _save_params(self):
        """保存当前参数设置"""
        # 保存OCR服务
        self.config_manager.save_config("ocr_service", self.ocr_service_var.get())
        
        # 保存OCR语言
        self.config_manager.save_config("ocr_language", self.ocr_language_var.get())
        
        # 保存翻译服务
        self.config_manager.save_config("translate_service", self.translate_service_var.get())
        
        # 保存目标语言
        self.config_manager.save_config("target_language", self.target_language_var.get())
        
    def _load_image(self):
        """加载图像"""
        file_path = filedialog.askopenfilename(
            title="选择图像",
            filetypes=[
                ("图像文件", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff"),
                ("所有文件", "*.*")
            ]
        )
        
        if not file_path:
            return
            
        # 加载图像
        image = load_image(file_path)
        if image:
            self.image = image
            self.image_path = file_path
            
            # 显示图像
            self._show_image(image)
            
            # 清空之前的识别结果
            self.ocr_text.delete(1.0, tk.END)
            self.translated_text_widget.delete(1.0, tk.END)
            self.recognized_text = ""
            self.translated_text = ""
            
            # 更新状态
            self._update_status(f"已加载图像: {os.path.basename(file_path)}")
            
            # 禁用翻译按钮，因为还没有识别文本
            self.translate_button.config(state=tk.DISABLED)
        else:
            messagebox.showerror("错误", f"无法加载图像: {file_path}")
            
    def _capture_screen(self):
        """截取屏幕"""
        # 此功能需要实现截屏功能，可以调用系统的截屏工具
        # 由于平台差异，这里只提供基本实现
        try:
            messagebox.showinfo("截屏", "请使用系统截图工具截取屏幕，然后复制到剪贴板。\n截图完成后，点击确定。")
            
            # 从剪贴板获取图像
            from PIL import ImageGrab
            image = ImageGrab.grabclipboard()
            
            if image and isinstance(image, Image.Image):
                self.image = image
                self.image_path = None  # 没有文件路径
                
                # 显示图像
                self._show_image(image)
                
                # 清空之前的识别结果
                self.ocr_text.delete(1.0, tk.END)
                self.translated_text_widget.delete(1.0, tk.END)
                self.recognized_text = ""
                self.translated_text = ""
                
                # 更新状态
                self._update_status("已加载屏幕截图")
                
                # 禁用翻译按钮，因为还没有识别文本
                self.translate_button.config(state=tk.DISABLED)
            else:
                messagebox.showerror("错误", "剪贴板中没有图像，请先截取屏幕并复制到剪贴板")
        except Exception as e:
            messagebox.showerror("错误", f"截取屏幕失败: {str(e)}")
            
    def _start_ocr(self):
        """开始OCR文字识别"""
        if self.image is None:
            messagebox.showinfo("提示", "请先加载图像")
            return
            
        if self.is_processing:
            return
            
        # 获取设置
        ocr_service = self.ocr_service_var.get()
        ocr_language = self.ocr_language_var.get()
        
        # 更新状态
        self.is_processing = True
        self._update_status("正在识别文字...")
        
        # 显示进度条
        self.progress_bar.config(mode='indeterminate')
        self.progress_bar.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5, pady=2)
        self.progress_bar.start()
        
        # 禁用按钮
        self.ocr_button.config(state=tk.DISABLED)
        
        # 在独立线程中处理，避免UI冻结
        threading.Thread(target=self._ocr_thread, args=(ocr_service, ocr_language), daemon=True).start()
            
    def _ocr_thread(self, ocr_service, ocr_language):
        """OCR处理线程
        
        Args:
            ocr_service: OCR服务名称
            ocr_language: 识别语言
        """
        try:
            # 转换为OpenCV格式进行处理
            if isinstance(self.image, Image.Image):
                cv_image = np.array(self.image)
                if len(cv_image.shape) == 3 and cv_image.shape[2] == 3:
                    cv_image = cv2.cvtColor(cv_image, cv2.COLOR_RGB2BGR)
            else:
                cv_image = self.image
                
            # 调用OCR识别
            result = self.ocr_translator.recognize_text(cv_image, ocr_service, ocr_language)
            
            # 保存识别结果
            self.recognized_text = result
            
            # 在主线程中更新UI
            self.after(0, lambda: self._update_ocr_result(result))
        except Exception as e:
            # 在主线程中显示错误
            self.after(0, lambda: self._show_error(f"OCR识别失败: {str(e)}"))
        finally:
            # 无论成功或失败，都需要重置状态
            self.after(0, self._reset_ocr_status)
            
    def _update_ocr_result(self, text):
        """更新OCR识别结果
        
        Args:
            text: 识别出的文本
        """
        # 清空之前的结果
        self.ocr_text.delete(1.0, tk.END)
        
        # 显示新结果
        self.ocr_text.insert(tk.END, text)
        
        # 切换到识别文本标签页
        self.text_notebook.select(0)
        
        # 如果有识别结果，启用翻译按钮
        if text.strip():
            self.translate_button.config(state=tk.NORMAL)
        
        # 更新状态
        self._update_status("文字识别完成")
        
    def _reset_ocr_status(self):
        """重置OCR状态"""
        # 停止进度条
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        
        # 启用按钮
        self.ocr_button.config(state=tk.NORMAL)
        
        # 重置处理状态
        self.is_processing = False
        
    def _start_translate(self):
        """开始翻译文本"""
        if not self.recognized_text.strip():
            messagebox.showinfo("提示", "没有可翻译的文本")
            return
            
        if self.is_processing:
            return
            
        # 获取设置
        translate_service = self.translate_service_var.get()
        target_language = self.target_language_var.get()
        
        # 更新状态
        self.is_processing = True
        self._update_status("正在翻译文本...")
        
        # 显示进度条
        self.progress_bar.config(mode='indeterminate')
        self.progress_bar.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5, pady=2)
        self.progress_bar.start()
        
        # 禁用按钮
        self.translate_button.config(state=tk.DISABLED)
        
        # 在独立线程中处理，避免UI冻结
        threading.Thread(target=self._translate_thread, args=(self.recognized_text, translate_service, target_language), daemon=True).start()
            
    def _translate_thread(self, text, translate_service, target_language):
        """翻译处理线程
        
        Args:
            text: 要翻译的文本
            translate_service: 翻译服务名称
            target_language: 目标语言
        """
        try:
            # 调用翻译
            result = self.ocr_translator.translate_text(text, translate_service, target_language)
            
            # 保存翻译结果
            self.translated_text = result
            
            # 在主线程中更新UI
            self.after(0, lambda: self._update_translate_result(result))
        except Exception as e:
            # 在主线程中显示错误
            self.after(0, lambda: self._show_error(f"翻译失败: {str(e)}"))
        finally:
            # 无论成功或失败，都需要重置状态
            self.after(0, self._reset_translate_status)
            
    def _update_translate_result(self, text):
        """更新翻译结果
        
        Args:
            text: 翻译后的文本
        """
        # 清空之前的结果
        self.translated_text_widget.delete(1.0, tk.END)
        
        # 显示新结果
        self.translated_text_widget.insert(tk.END, text)
        
        # 切换到翻译结果标签页
        self.text_notebook.select(1)
        
        # 更新状态
        self._update_status("翻译完成")
        
    def _reset_translate_status(self):
        """重置翻译状态"""
        # 停止进度条
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        
        # 启用按钮
        self.translate_button.config(state=tk.NORMAL)
        
        # 重置处理状态
        self.is_processing = False
        
    def _copy_text(self, text):
        """复制文本到剪贴板
        
        Args:
            text: 要复制的文本
        """
        if not text.strip():
            return
            
        # 复制到剪贴板
        self.clipboard_clear()
        self.clipboard_append(text)
        
        # 更新状态
        self._update_status("文本已复制到剪贴板")
        
    def _show_image(self, image):
        """在画布上显示图像
        
        Args:
            image: PIL图像或OpenCV图像
        """
        if image is None:
            return
            
        # 转换为PIL图像
        if not isinstance(image, Image.Image):
            # 假设是OpenCV格式的图像
            if len(image.shape) == 3 and image.shape[2] == 3:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(image)
        else:
            pil_image = image
            
        # 获取画布大小
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # 如果画布尚未实际显示，使用默认大小
        if canvas_width <= 1:
            canvas_width = 800
        if canvas_height <= 1:
            canvas_height = 600
        
        # 调整图像大小以适应画布
        image_width, image_height = pil_image.size
        scale = min(canvas_width / image_width, canvas_height / image_height) * 0.9
        
        new_width = int(image_width * scale)
        new_height = int(image_height * scale)
        
        resized_image = pil_image.resize((new_width, new_height), Image.LANCZOS)
        
        # 创建Tkinter图像
        self.tk_image = ImageTk.PhotoImage(resized_image)
        
        # 计算居中位置
        x_pos = (canvas_width - new_width) // 2
        y_pos = (canvas_height - new_height) // 2
        
        # 在画布上显示图像
        self.canvas.delete("all")
        self.canvas.create_image(x_pos, y_pos, anchor=tk.NW, image=self.tk_image)
        
    def _update_status(self, message):
        """更新状态栏信息
        
        Args:
            message: 状态消息
        """
        self.status_label.config(text=message)
        
    def _show_error(self, message):
        """显示错误消息
        
        Args:
            message: 错误消息
        """
        messagebox.showerror("错误", message)
        self._update_status("出错: " + message.split("\n")[0]) 