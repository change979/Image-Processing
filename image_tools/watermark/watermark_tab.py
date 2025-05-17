"""
水印去除界面模块
提供交互式水印标记和去除功能的图形界面
"""
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import cv2
import numpy as np
from typing import Optional, Tuple, List, Dict, Any

from .watermark_remover import WatermarkRemover
from .batch_processor import BatchWatermarkProcessor
from ..utils.config_manager import ConfigManager

class WatermarkRemoverTab(ttk.Frame):
    """水印去除标签页，包含单张和批量处理功能"""
    
    def __init__(self, parent):
        """初始化水印去除标签页
        
        Args:
            parent: 父级窗口组件
        """
        super().__init__(parent)
        
        # 初始化成员变量
        self.watermark_remover = WatermarkRemover()  # 单张水印去除器
        self.batch_processor = BatchWatermarkProcessor()  # 批量处理器
        self.config_manager = ConfigManager()  # 配置管理器
        
        # 图像显示相关
        self.tk_image = None  # Tkinter图像对象
        self.canvas_image = None  # 画布上的图像ID
        self.brush_preview = None  # 笔刷预览ID
        self.drawing = False  # 是否正在绘制
        self.last_x = 0  # 上一个绘制点x坐标
        self.last_y = 0  # 上一个绘制点y坐标
        
        # 设置UI
        self._setup_ui()
        
        # 加载保存的参数
        self._load_saved_params()
        
        # 设置快捷键
        self._setup_shortcuts()
    
    def _setup_ui(self):
        """设置用户界面"""
        # 创建主分隔窗口
        self.paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        
        # 创建左侧控制面板
        self.control_frame = ttk.Frame(self.paned_window, width=250)
        self.control_frame.pack_propagate(False)  # 固定宽度
        self.paned_window.add(self.control_frame, weight=0)
        
        # 创建模式选择标签页控件
        self.mode_notebook = ttk.Notebook(self.control_frame)
        self.mode_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建单张去水印标签页
        self.single_mode_frame = ttk.Frame(self.mode_notebook)
        self.mode_notebook.add(self.single_mode_frame, text="单张去除")
        self._setup_single_mode_ui()
        
        # 创建批量去水印标签页
        self.batch_mode_frame = ttk.Frame(self.mode_notebook)
        self.mode_notebook.add(self.batch_mode_frame, text="批量去除")
        self._setup_batch_mode_ui()
        
        # 绑定标签页切换事件
        self.mode_notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        
        # 创建右侧显示区域
        self.display_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.display_frame, weight=1)
        
        # 创建画布
        self.canvas = tk.Canvas(self.display_frame, bg="#EEEEEE", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # 绑定鼠标事件
        self.canvas.bind("<ButtonPress-1>", self._start_draw)
        self.canvas.bind("<B1-Motion>", self._draw)
        self.canvas.bind("<ButtonRelease-1>", self._stop_draw)
        self.canvas.bind("<Motion>", self._show_brush_preview)
        self.canvas.bind("<Leave>", self._hide_brush_preview)
        
        # 状态栏
        self.status_frame = ttk.Frame(self)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_label = ttk.Label(self.status_frame, text="就绪")
        self.status_label.pack(side=tk.LEFT, padx=5, pady=2)
        
        self.progress_bar = ttk.Progressbar(self.status_frame, mode='determinate')
        self.progress_bar.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5, pady=2)
        self.progress_bar.pack_forget()  # 隐藏进度条
    
    def _setup_single_mode_ui(self):
        """设置单张去水印模式的UI"""
        # 图像加载区域
        load_frame = ttk.LabelFrame(self.single_mode_frame, text="图像加载")
        load_frame.pack(fill=tk.X, padx=5, pady=5)
        
        load_buttons_frame = ttk.Frame(load_frame)
        load_buttons_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(load_buttons_frame, text="打开图像", command=self._load_single_image).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Button(load_buttons_frame, text="清空图像", command=self._clear_single_image).pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=2)
        
        # 工具设置区域
        tools_frame = ttk.LabelFrame(self.single_mode_frame, text="工具设置")
        tools_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 画笔大小
        ttk.Label(tools_frame, text="画笔大小:").pack(anchor=tk.W, padx=5, pady=2)
        self.brush_size_var = tk.IntVar(value=10)
        brush_scale = ttk.Scale(
            tools_frame, from_=1, to=50, 
            variable=self.brush_size_var,
            orient=tk.HORIZONTAL, 
            command=self._update_brush_size
        )
        brush_scale.pack(fill=tk.X, padx=5, pady=5)
        
        # 添加画笔大小显示标签
        self.brush_size_label = ttk.Label(tools_frame, text="10")
        self.brush_size_label.pack(anchor=tk.E, padx=5)
        
        # 创建水印去除设置区域
        param_frame = ttk.LabelFrame(self.single_mode_frame, text="去除设置")
        param_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 算法选择
        ttk.Label(param_frame, text="算法选择:").pack(anchor=tk.W, padx=5, pady=2)
        self.algorithm_var = tk.StringVar(value="TELEA")
        ttk.Radiobutton(
            param_frame, text="TELEA算法(快速修复)", 
            variable=self.algorithm_var, value="TELEA",
            command=self._update_algorithm
        ).pack(anchor=tk.W, padx=5, pady=2)
        
        ttk.Radiobutton(
            param_frame, text="NS算法(自然场修复)", 
            variable=self.algorithm_var, value="NS",
            command=self._update_algorithm
        ).pack(anchor=tk.W, padx=5, pady=2)
        
        # 修复半径
        ttk.Label(param_frame, text="修复半径:").pack(anchor=tk.W, padx=5, pady=2)
        self.radius_var = tk.IntVar(value=3)
        radius_scale = ttk.Scale(
            param_frame, from_=1, to=20, 
            variable=self.radius_var,
            orient=tk.HORIZONTAL, 
            command=self._update_inpaint_radius
        )
        radius_scale.pack(fill=tk.X, padx=5, pady=5)
        
        # 操作按钮
        action_frame = ttk.Frame(self.single_mode_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=10)
        
        ttk.Button(action_frame, text="清除标记", command=self._clear_mask).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        edit_frame = ttk.Frame(action_frame)
        edit_frame.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        
        ttk.Button(edit_frame, text="撤销", command=self._undo_mark).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Button(edit_frame, text="重做", command=self._redo_mark).pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=2)
        
        # 去水印按钮
        ttk.Button(
            self.single_mode_frame, text="去除水印", 
            command=self._remove_watermark
        ).pack(fill=tk.X, padx=5, pady=5)
        
        # 结果操作区域
        result_frame = ttk.Frame(self.single_mode_frame)
        result_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 保存结果按钮
        self.save_button = ttk.Button(
            result_frame, text="保存结果", 
            command=self._save_result,
            state=tk.DISABLED
        )
        self.save_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2, pady=5)
        
        # 继续编辑按钮
        self.continue_edit_button = ttk.Button(
            result_frame, text="继续编辑", 
            command=self._continue_edit_result,
            state=tk.DISABLED
        )
        self.continue_edit_button.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=2, pady=5)
    
    def _setup_batch_mode_ui(self):
        """设置批量去水印模式的UI"""
        # 模板设置区域
        template_frame = ttk.LabelFrame(self.batch_mode_frame, text="模板设置")
        template_frame.pack(fill=tk.X, padx=5, pady=5)
        
        template_buttons_frame = ttk.Frame(template_frame)
        template_buttons_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(
            template_buttons_frame, text="加载模板图像", 
            command=self._load_template_image
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        ttk.Button(
            template_buttons_frame, text="清空模板", 
            command=self._clear_template_image
        ).pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=2)
        
        ttk.Label(template_frame, text="请在模板图像上标记水印区域").pack(padx=5, pady=5)
        
        # 批量图像区域
        batch_frame = ttk.LabelFrame(self.batch_mode_frame, text="批量图像")
        batch_frame.pack(fill=tk.X, padx=5, pady=5)
        
        batch_buttons_frame = ttk.Frame(batch_frame)
        batch_buttons_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(
            batch_buttons_frame, text="选择图像文件", 
            command=lambda: self._select_batch_images(False)
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        ttk.Button(
            batch_buttons_frame, text="选择图像文件夹", 
            command=lambda: self._select_batch_images(True)
        ).pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=2)
        
        # 添加清空批量图像按钮
        ttk.Button(
            batch_frame, text="清空批量图像", 
            command=self._clear_batch_images
        ).pack(fill=tk.X, padx=5, pady=5)
        
        # 显示已选文件数量
        self.file_count_label = ttk.Label(batch_frame, text="已选择: 0 个文件")
        self.file_count_label.pack(padx=5, pady=5)
        
        # 输出目录选择
        output_frame = ttk.LabelFrame(self.batch_mode_frame, text="输出设置")
        output_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(
            output_frame, text="选择输出目录", 
            command=self._select_output_dir
        ).pack(fill=tk.X, padx=5, pady=5)
        
        self.output_dir_label = ttk.Label(output_frame, text="未选择输出目录")
        self.output_dir_label.pack(padx=5, pady=5)
        
        # 处理参数
        param_frame = ttk.LabelFrame(self.batch_mode_frame, text="处理设置")
        param_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 算法选择 (使用与单张处理相同的变量)
        ttk.Label(param_frame, text="算法选择:").pack(anchor=tk.W, padx=5, pady=2)
        ttk.Radiobutton(
            param_frame, text="TELEA算法(快速修复)", 
            variable=self.algorithm_var, value="TELEA",
            command=self._update_algorithm
        ).pack(anchor=tk.W, padx=5, pady=2)
        
        ttk.Radiobutton(
            param_frame, text="NS算法(自然场修复)", 
            variable=self.algorithm_var, value="NS",
            command=self._update_algorithm
        ).pack(anchor=tk.W, padx=5, pady=2)
        
        # 修复半径 (使用与单张处理相同的变量)
        ttk.Label(param_frame, text="修复半径:").pack(anchor=tk.W, padx=5, pady=2)
        radius_scale = ttk.Scale(
            param_frame, from_=1, to=20, 
            variable=self.radius_var,
            orient=tk.HORIZONTAL, 
            command=self._update_inpaint_radius
        )
        radius_scale.pack(fill=tk.X, padx=5, pady=5)
        
        # 批量处理按钮
        self.batch_process_button = ttk.Button(
            self.batch_mode_frame, text="开始批量处理", 
            command=self._start_batch_processing
        )
        self.batch_process_button.pack(fill=tk.X, padx=5, pady=10)
        
        # 停止处理按钮
        self.stop_button = ttk.Button(
            self.batch_mode_frame, text="停止处理", 
            command=self._stop_batch_processing,
            state=tk.DISABLED
        )
        self.stop_button.pack(fill=tk.X, padx=5, pady=5)
    
    def _load_saved_params(self):
        """加载保存的参数设置"""
        # 读取笔刷大小
        saved_brush_size = self.config_manager.get_config("brush_size", 10)
        self.brush_size_var.set(saved_brush_size)
        
        # 读取修复半径
        saved_radius = self.config_manager.get_config("inpaint_radius", 3)
        self.radius_var.set(saved_radius)
        
        # 读取算法设置
        saved_algorithm = self.config_manager.get_config("algorithm", "TELEA")
        self.algorithm_var.set(saved_algorithm)
        
        # 读取输出目录
        saved_output_dir = self.config_manager.get_config("output_dir", "")
        if saved_output_dir and os.path.exists(saved_output_dir):
            self.batch_processor.set_output_directory(saved_output_dir)
            self.output_dir_label.config(text=f"输出目录: {saved_output_dir}")
        
        # 更新参数
        self._update_brush_size()
        self._update_inpaint_radius()
        self._update_algorithm()
    
    def _load_single_image(self):
        """加载单张图像"""
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
        if self.watermark_remover.load_image(file_path):
            # 设置显示尺寸
            self.watermark_remover.set_display_size(
                self.canvas.winfo_width(), 
                self.canvas.winfo_height()
            )
            
            # 显示图像
            preview = self.watermark_remover.get_masked_preview()
            self._show_image(preview)
            
            # 更新状态
            self._update_status(f"已加载: {os.path.basename(file_path)}")
            
            # 禁用保存按钮
            self.save_button.config(state=tk.DISABLED)
        else:
            # 显示错误
            messagebox.showerror("错误", "无法加载图像")
    
    def _load_template_image(self):
        """加载模板图像"""
        file_path = filedialog.askopenfilename(
            title="选择模板图像",
            filetypes=[
                ("图像文件", "*.jpg *.jpeg *.png *.bmp *.tiff *.webp"),
                ("所有文件", "*.*")
            ]
        )
        
        if not file_path:
            return
            
        # 加载模板图像
        if self.batch_processor.set_template(file_path):
            # 获取预览图像并显示
            template_remover = self.batch_processor.get_template_remover()
            preview = template_remover.get_masked_preview()
            self._show_image(preview)
            
            # 更新状态
            self._update_status(f"已加载模板图像: {os.path.basename(file_path)}")
        else:
            messagebox.showerror("错误", f"无法加载模板图像: {file_path}")
    
    def _select_batch_images(self, use_folder=False):
        """选择批量处理的图像文件
        
        Args:
            use_folder: 是否选择整个文件夹
        """
        if use_folder:
            # 选择文件夹
            folder_path = filedialog.askdirectory(title="选择图像文件夹")
            if not folder_path:
                return
                
            # 获取文件夹中的所有图像文件
            image_files = []
            for ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"]:
                image_files.extend(
                    [os.path.join(folder_path, f) for f in os.listdir(folder_path) 
                     if f.lower().endswith(ext)]
                )
        else:
            # 选择多个文件
            image_files = filedialog.askopenfilenames(
                title="选择图像文件",
                filetypes=[
                    ("图像文件", "*.jpg *.jpeg *.png *.bmp *.tiff *.webp"),
                    ("所有文件", "*.*")
                ]
            )
        
        if not image_files:
            return
            
        # 设置批处理图像
        self.batch_processor.set_batch_images(list(image_files))
        
        # 更新文件数量显示
        self.file_count_label.config(text=f"已选择: {len(image_files)} 个文件")
        
        # 更新状态
        self._update_status(f"已选择 {len(image_files)} 个图像文件")
    
    def _select_output_dir(self):
        """选择输出目录"""
        output_dir = filedialog.askdirectory(title="选择输出目录")
        if not output_dir:
            return
            
        # 设置输出目录
        if self.batch_processor.set_output_directory(output_dir):
            # 更新显示
            self.output_dir_label.config(text=f"输出目录: {output_dir}")
            
            # 保存到配置
            self.config_manager.save_config("output_dir", output_dir)
        else:
            messagebox.showerror("错误", f"无法设置输出目录: {output_dir}")
    
    def _on_tab_changed(self, event):
        """处理标签页切换事件"""
        # 获取当前选中的标签页
        current_tab = self.mode_notebook.index(self.mode_notebook.select())
        
        # 清空画布
        self.canvas.delete("all")
        self.tk_image = None
        
        # 获取画布尺寸
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # 根据当前标签页加载对应的图像
        if current_tab == 0:  # 单张模式
            # 更新单张模式水印去除器的显示尺寸
            self.watermark_remover.set_display_size(canvas_width, canvas_height)
            
            if hasattr(self.watermark_remover, 'image') and self.watermark_remover.image is not None:
                preview = self.watermark_remover.get_masked_preview()
                self._show_image(preview)
        else:  # 批量模式
            # 更新模板水印去除器的显示尺寸
            template_remover = self.batch_processor.get_template_remover()
            if template_remover:
                template_remover.set_display_size(canvas_width, canvas_height)
                
                if hasattr(template_remover, 'image') and template_remover.image is not None:
                    preview = template_remover.get_masked_preview()
                    self._show_image(preview)
                
        # 更新状态
        tab_name = "单张去除" if current_tab == 0 else "批量去除"
        self._update_status(f"切换到{tab_name}模式")
    
    def _start_draw(self, event):
        """
        开始绘制掩码的回调函数
        
        参数:
            event: 鼠标事件
        """
        # 获取当前模式
        current_tab = self.mode_notebook.index(self.mode_notebook.select())
        
        # 根据当前模式获取正确的水印去除器
        if current_tab == 0:  # 单张模式
            remover = self.watermark_remover
        else:  # 批量模式
            remover = self.batch_processor.get_template_remover()
        
        # 检查是否有图像
        if remover is None or remover.image is None:
            return
        
        # 获取画布尺寸
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # 设置水印去除器的显示尺寸
        remover.set_display_size(canvas_width, canvas_height)
        
        self.drawing = True
        self.last_x = event.x
        self.last_y = event.y
        
        # 使用新的start_draw方法处理第一个点
        remover.start_draw((event.x, event.y), self.brush_size_var.get())
        
        # 更新预览
        preview = remover.get_masked_preview()
        self._show_image(preview)
    
    def _draw(self, event):
        """
        绘制掩码的回调函数
        
        参数:
            event: 鼠标事件
        """
        if not self.drawing:
            return
            
        # 获取当前模式
        current_tab = self.mode_notebook.index(self.mode_notebook.select())
        
        # 根据当前模式获取正确的水印去除器
        if current_tab == 0:  # 单张模式
            remover = self.watermark_remover
        else:  # 批量模式
            remover = self.batch_processor.get_template_remover()
        
        # 检查是否有图像
        if remover is None or remover.image is None:
            return
        
        # 获取画布尺寸并确保设置正确
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        remover.set_display_size(canvas_width, canvas_height)
        
        # 使用改进的draw_line_on_mask方法绘制线条
        remover.draw_line_on_mask((self.last_x, self.last_y), (event.x, event.y), self.brush_size_var.get())
        
        # 更新上一个点的位置
        self.last_x = event.x
        self.last_y = event.y
        
        # 更新预览
        preview = remover.get_masked_preview()
        self._show_image(preview)
    
    def _stop_draw(self, event):
        """停止绘制掩码"""
        self.drawing = False
        
        # 获取当前模式
        current_tab = self.mode_notebook.index(self.mode_notebook.select())
        
        # 保存掩码历史（如果需要）
        if current_tab == 0:  # 单张模式
            if hasattr(self.watermark_remover, '_save_mask_to_history'):
                self.watermark_remover._save_mask_to_history()
        else:  # 批量模式
            remover = self.batch_processor.get_template_remover()
            if remover and hasattr(remover, '_save_mask_to_history'):
                remover._save_mask_to_history()
    
    def _clear_mask(self):
        """清除掩码"""
        # 获取当前模式
        current_tab = self.mode_notebook.index(self.mode_notebook.select())
        
        if current_tab == 0:  # 单张模式
            remover = self.watermark_remover
        else:  # 批量模式
            remover = self.batch_processor.get_template_remover()
        
        # 清除掩码
        remover.clear_mask()
        
        # 更新预览
        preview = remover.get_masked_preview()
        self._show_image(preview)
        
        # 更新状态
        self._update_status("已清除标记")
    
    def _undo_mark(self, event=None):
        """撤销最后一次标记"""
        # 获取当前模式
        current_tab = self.mode_notebook.index(self.mode_notebook.select())
        
        if current_tab == 0:  # 单张模式
            if self.watermark_remover.undo_mask():
                # 更新预览
                preview = self.watermark_remover.get_masked_preview()
                self._show_image(preview)
                
                # 更新状态
                self._update_status("已撤销标记")
            else:
                self._update_status("无法撤销，已到最早状态")
        else:  # 批量模式
            # 批量模式类似操作
            pass
    
    def _redo_mark(self, event=None):
        """重做标记"""
        # 获取当前模式
        current_tab = self.mode_notebook.index(self.mode_notebook.select())
        
        if current_tab == 0:  # 单张模式
            if self.watermark_remover.redo_mask():
                # 更新预览
                preview = self.watermark_remover.get_masked_preview()
                self._show_image(preview)
                
                # 更新状态
                self._update_status("已重做标记")
            else:
                self._update_status("无法重做，已到最新状态")
        else:  # 批量模式
            # 批量模式类似操作
            pass
    
    def _remove_watermark(self):
        """去除水印"""
        # 检查是否有图像
        if not hasattr(self.watermark_remover, 'image') or self.watermark_remover.image is None:
            messagebox.showinfo("提示", "请先加载图像")
            return
            
        # 检查是否有水印标记
        if np.max(self.watermark_remover.mask) == 0:
            messagebox.showinfo("提示", "请先标记水印区域")
            return
        
        # 显示进度条
        self.progress_bar.config(mode='indeterminate')
        self.progress_bar.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5, pady=2)
        self.progress_bar.start()
        
        # 更新状态
        self._update_status("正在处理中...")
        
        # 在独立线程中处理，避免UI冻结
        threading.Thread(target=self._process_watermark_thread, daemon=True).start()
    
    def _process_watermark_thread(self):
        """在独立线程中处理水印去除"""
        try:
            # 执行水印去除
            success = self.watermark_remover.remove_watermark()
            
            # 在主线程中更新UI
            self.after(0, lambda: self._update_after_processing(success))
        except Exception as e:
            # 在主线程中显示错误
            self.after(0, lambda: self._show_error(f"处理时出错: {e}"))
    
    def _update_after_processing(self, success):
        """处理完成后更新UI
        
        Args:
            success: 处理是否成功
        """
        # 停止进度条
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        
        if success:
            # 获取结果图像并显示
            result_image = self.watermark_remover.get_result_image()
            self._show_image(result_image)
            
            # 启用保存和继续编辑按钮
            self.save_button.config(state=tk.NORMAL)
            self.continue_edit_button.config(state=tk.NORMAL)
            
            # 更新状态
            self._update_status("水印去除完成")
        else:
            # 显示错误
            messagebox.showerror("错误", "水印去除失败")
            self._update_status("处理失败")
    
    def _save_result(self):
        """保存处理结果"""
        # 检查是否有处理结果
        if not hasattr(self.watermark_remover, 'result_image') or self.watermark_remover.result_image is None:
            messagebox.showinfo("提示", "没有可保存的结果")
            return
            
        # 打开保存对话框
        file_path = filedialog.asksaveasfilename(
            title="保存结果",
            defaultextension=".png",
            filetypes=[
                ("PNG图像", "*.png"),
                ("JPEG图像", "*.jpg *.jpeg"),
                ("BMP图像", "*.bmp"),
                ("TIFF图像", "*.tiff *.tif"),
                ("所有文件", "*.*")
            ]
        )
        
        if not file_path:
            return
            
        # 保存结果
        if self.watermark_remover.save_result(file_path):
            # 更新状态
            self._update_status(f"结果已保存至: {os.path.basename(file_path)}")
        else:
            # 显示错误
            messagebox.showerror("错误", "保存失败")
    
    def _start_batch_processing(self):
        """开始批量处理"""
        # 开始批量处理
        success = self.batch_processor.start_batch_processing(
            progress_callback=self._update_batch_progress,
            complete_callback=self._on_batch_complete,
            error_callback=self._show_error
        )
        
        if success:
            # 显示进度条
            self.progress_bar.config(mode='determinate', value=0)
            self.progress_bar.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5, pady=2)
            
            # 更新按钮状态
            self.batch_process_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            
            # 更新状态
            self._update_status("批量处理开始")
    
    def _stop_batch_processing(self):
        """停止批量处理"""
        self.batch_processor.stop_processing()
        
        # 更新按钮状态
        self.stop_button.config(state=tk.DISABLED)
        
        # 更新状态
        self._update_status("正在停止处理...")
    
    def _update_batch_progress(self, current, total):
        """更新批量处理进度
        
        Args:
            current: 当前处理数量
            total: 总数量
        """
        # 计算进度百分比
        percent = int((current / total) * 100)
        
        # 更新进度条
        self.progress_bar.config(value=percent)
        
        # 更新状态
        self._update_status(f"正在处理: {current}/{total} - {percent}%")
    
    def _on_batch_complete(self, success_count, total_count, failed_paths):
        """批量处理完成回调
        
        Args:
            success_count: 成功处理数量
            total_count: 总数量
            failed_paths: 失败的文件路径列表
        """
        # 隐藏进度条
        self.progress_bar.pack_forget()
        
        # 更新按钮状态
        self.batch_process_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
        # 更新状态
        self._update_status(f"批量处理完成: 成功 {success_count}/{total_count}")
        
        # 显示处理结果
        if failed_paths:
            # 有失败的文件
            failed_message = "\n".join(
                [os.path.basename(path) for path in failed_paths[:5]]
            )
            if len(failed_paths) > 5:
                failed_message += f"\n...及其他 {len(failed_paths)-5} 个文件"
                
            messagebox.showwarning(
                "处理完成", 
                f"成功处理 {success_count}/{total_count} 个图像\n\n"
                f"失败的文件:\n{failed_message}"
            )
        else:
            # 全部成功
            messagebox.showinfo(
                "处理完成", 
                f"成功处理所有 {total_count} 个图像\n\n"
                f"输出目录: {self.batch_processor.output_dir}"
            )
            
            # 尝试打开输出目录
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(self.batch_processor.output_dir)
                elif os.name == 'posix':  # macOS and Linux
                    if os.system('which xdg-open') == 0:  # Linux
                        os.system(f'xdg-open "{self.batch_processor.output_dir}"')
                    else:  # macOS
                        os.system(f'open "{self.batch_processor.output_dir}"')
            except:
                pass  # 忽略打开目录错误
    
    def _show_brush_preview(self, event):
        """显示画笔预览"""
        if self.drawing:
            return
            
        # 获取当前模式
        current_tab = self.mode_notebook.index(self.mode_notebook.select())
        
        # 根据当前模式获取正确的水印去除器
        if current_tab == 0:  # 单张模式
            remover = self.watermark_remover
        else:  # 批量模式
            remover = self.batch_processor.get_template_remover()
            
        # 检查是否有图像
        if remover is None or remover.image is None:
            self.canvas.delete("brush_preview")
            return
        
        # 获取画布尺寸并确保设置正确
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        remover.set_display_size(canvas_width, canvas_height)
            
        # 显示画笔预览
        brush_size = self.brush_size_var.get()
        
        # 删除旧的预览
        self.canvas.delete("brush_preview")
        
        # 获取带有预览的图像
        preview_image = remover.show_brush_preview((event.x, event.y), brush_size)
        
        if preview_image is not None:
            self._show_image(preview_image)
        else:
            # 在鼠标位置绘制圆形预览
            self.canvas.create_oval(
                event.x - brush_size // 2,
                event.y - brush_size // 2,
                event.x + brush_size // 2,
                event.y + brush_size // 2,
                outline="red",
                width=2,
                tags="brush_preview"
            )
    
    def _hide_brush_preview(self, event):
        """隐藏画笔预览"""
        # 删除预览
        self.canvas.delete("brush_preview")
        
        # 恢复原始图像显示
        current_tab = self.mode_notebook.index(self.mode_notebook.select())
        
        # 根据当前标签页显示对应的图像
        if current_tab == 0:  # 单张模式
            if hasattr(self.watermark_remover, 'image') and self.watermark_remover.image is not None:
                preview = self.watermark_remover.get_masked_preview()
                if preview is not None:
                    self._show_image(preview)
        else:  # 批量模式
            template_remover = self.batch_processor.get_template_remover()
            if template_remover and hasattr(template_remover, 'image') and template_remover.image is not None:
                preview = template_remover.get_masked_preview()
                if preview is not None:
                    self._show_image(preview)
    
    def _update_brush_size(self, *args):
        """更新画笔大小"""
        # 获取当前值
        value = self.brush_size_var.get()
        
        # 使用water_remover中的方法更新画笔大小
        self.watermark_remover.update_brush_size(value)
        
        # 更新画笔大小显示标签
        if hasattr(self, 'brush_size_label'):
            self.brush_size_label.config(text=str(value))
        
        # 保存到配置
        self.config_manager.save_config("brush_size", value)
        
        # 更新状态
        self._update_status(f"画笔大小: {value}")
    
    def _update_inpaint_radius(self, *args):
        """更新修复半径"""
        # 获取当前值
        value = self.radius_var.get()
        
        # 更新水印去除器设置
        self.watermark_remover.set_inpaint_radius(value)
        
        # 更新批处理器设置
        self.batch_processor.set_parameters(
            value, 
            self.algorithm_var.get(), 
            "none"
        )
        
        # 保存到配置
        self.config_manager.save_config("inpaint_radius", value)
        
        # 更新状态
        self._update_status(f"修复半径: {value}")
    
    def _update_algorithm(self, *args):
        """更新算法设置"""
        # 获取当前值
        value = self.algorithm_var.get()
        
        # 更新水印去除器设置
        self.watermark_remover.set_algorithm(value)
        
        # 更新批处理器设置
        self.batch_processor.set_parameters(
            self.radius_var.get(),
            value,
            "none"
        )
        
        # 保存到配置
        self.config_manager.save_config("algorithm", value)
        
        # 更新状态
        self._update_status(f"算法: {value}")
    
    def _show_image(self, image):
        """在画布上显示图像
        
        Args:
            image: OpenCV格式的图像 (numpy.ndarray)
        """
        if image is None:
            return
            
        # 转换为PIL格式
        if len(image.shape) == 3:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            
        pil_image = Image.fromarray(image_rgb)
        
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
        
        # 保存图像位置，用于坐标转换
        self.image_x_offset = x_pos
        self.image_y_offset = y_pos
        
        # 在画布上显示图像
        self.canvas.delete("all")
        self.canvas_image = self.canvas.create_image(x_pos, y_pos, anchor=tk.NW, image=self.tk_image)
    
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

    def _setup_shortcuts(self):
        """设置键盘快捷键"""
        # 撤销 - Ctrl+Z
        self.bind_all("<Control-z>", self._undo_mark)
        
        # 重做 - Ctrl+Y
        self.bind_all("<Control-y>", self._redo_mark)
        
        # 清除 - Ctrl+Delete
        self.bind_all("<Control-Delete>", self._clear_mask)
    
    def _continue_edit_result(self):
        """继续编辑处理结果"""
        # 检查是否有处理结果
        if not hasattr(self.watermark_remover, 'result_image') or self.watermark_remover.result_image is None:
            messagebox.showinfo("提示", "没有可编辑的结果")
            return
            
        # 将结果设置为当前图像并继续编辑
        if self.watermark_remover.continue_edit_result():
            # 获取预览图像并显示
            preview = self.watermark_remover.get_masked_preview()
            self._show_image(preview)
            
            # 禁用保存和继续编辑按钮
            self.save_button.config(state=tk.DISABLED)
            self.continue_edit_button.config(state=tk.DISABLED)
            
            # 更新状态
            self._update_status("已切换到编辑模式，可以继续标记水印区域")
        else:
            # 显示错误
            messagebox.showerror("错误", "无法继续编辑")

    def _clear_single_image(self):
        """清空单张模式的图像"""
        # 重置水印去除器
        self.watermark_remover = WatermarkRemover()
        
        # 清空画布
        self.canvas.delete("all")
        self.tk_image = None
        
        # 禁用保存按钮
        self.save_button.config(state=tk.DISABLED)
        self.continue_edit_button.config(state=tk.DISABLED)
        
        # 更新状态
        self._update_status("已清空图像")
    
    def _clear_template_image(self):
        """清空模板图像"""
        # 重置模板
        self.batch_processor.reset_template()
        
        # 清空画布
        self.canvas.delete("all")
        self.tk_image = None
        
        # 更新状态
        self._update_status("已清空模板图像")
    
    def _clear_batch_images(self):
        """清空批量处理的图像列表"""
        # 清空批量图像列表
        self.batch_processor.clear_batch_images()
        
        # 更新文件数量显示
        self.file_count_label.config(text="已选择: 0 个文件")
        
        # 更新状态
        self._update_status("已清空批量图像列表")
    
    def _show_brush_preview(self, event):
        """显示画笔预览"""
        if self.drawing:
            return
            
        # 获取当前模式
        current_tab = self.mode_notebook.index(self.mode_notebook.select())
        
        # 根据当前模式获取正确的水印去除器
        if current_tab == 0:  # 单张模式
            remover = self.watermark_remover
        else:  # 批量模式
            remover = self.batch_processor.get_template_remover()
            
        # 检查是否有图像
        if remover is None or remover.image is None:
            self.canvas.delete("brush_preview")
            return
        
        # 获取画布尺寸并确保设置正确
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        remover.set_display_size(canvas_width, canvas_height)
            
        # 显示画笔预览
        brush_size = self.brush_size_var.get()
        
        # 删除旧的预览
        self.canvas.delete("brush_preview")
        
        # 获取带有预览的图像
        preview_image = remover.show_brush_preview((event.x, event.y), brush_size)
        
        if preview_image is not None:
            self._show_image(preview_image)
        else:
            # 在鼠标位置绘制圆形预览
            self.canvas.create_oval(
                event.x - brush_size // 2,
                event.y - brush_size // 2,
                event.x + brush_size // 2,
                event.y + brush_size // 2,
                outline="red",
                width=2,
                tags="brush_preview"
            )
    
    def _hide_brush_preview(self, event):
        """隐藏画笔预览"""
        # 删除预览
        self.canvas.delete("brush_preview")
        
        # 恢复原始图像显示
        current_tab = self.mode_notebook.index(self.mode_notebook.select())
        
        # 根据当前标签页显示对应的图像
        if current_tab == 0:  # 单张模式
            if hasattr(self.watermark_remover, 'image') and self.watermark_remover.image is not None:
                preview = self.watermark_remover.get_masked_preview()
                if preview is not None:
                    self._show_image(preview)
        else:  # 批量模式
            template_remover = self.batch_processor.get_template_remover()
            if template_remover and hasattr(template_remover, 'image') and template_remover.image is not None:
                preview = template_remover.get_masked_preview()
                if preview is not None:
                    self._show_image(preview)
    
    def _update_brush_size(self, *args):
        """更新画笔大小"""
        # 获取当前值
        value = self.brush_size_var.get()
        
        # 使用water_remover中的方法更新画笔大小
        self.watermark_remover.update_brush_size(value)
        
        # 更新画笔大小显示标签
        if hasattr(self, 'brush_size_label'):
            self.brush_size_label.config(text=str(value))
        
        # 保存到配置
        self.config_manager.save_config("brush_size", value)
        
        # 更新状态
        self._update_status(f"画笔大小: {value}")
    
    def _update_inpaint_radius(self, *args):
        """更新修复半径"""
        # 获取当前值
        value = self.radius_var.get()
        
        # 更新水印去除器设置
        self.watermark_remover.set_inpaint_radius(value)
        
        # 更新批处理器设置
        self.batch_processor.set_parameters(
            value, 
            self.algorithm_var.get(), 
            "none"
        )
        
        # 保存到配置
        self.config_manager.save_config("inpaint_radius", value)
        
        # 更新状态
        self._update_status(f"修复半径: {value}")
    
    def _update_algorithm(self, *args):
        """更新算法设置"""
        # 获取当前值
        value = self.algorithm_var.get()
        
        # 更新水印去除器设置
        self.watermark_remover.set_algorithm(value)
        
        # 更新批处理器设置
        self.batch_processor.set_parameters(
            self.radius_var.get(),
            value,
            "none"
        )
        
        # 保存到配置
        self.config_manager.save_config("algorithm", value)
        
        # 更新状态
        self._update_status(f"算法: {value}")
    
    def _show_image(self, image):
        """在画布上显示图像
        
        Args:
            image: OpenCV格式的图像 (numpy.ndarray)
        """
        if image is None:
            return
            
        # 转换为PIL格式
        if len(image.shape) == 3:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            
        pil_image = Image.fromarray(image_rgb)
        
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
        
        # 保存图像位置，用于坐标转换
        self.image_x_offset = x_pos
        self.image_y_offset = y_pos
        
        # 在画布上显示图像
        self.canvas.delete("all")
        self.canvas_image = self.canvas.create_image(x_pos, y_pos, anchor=tk.NW, image=self.tk_image)
    
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

    def _setup_shortcuts(self):
        """设置键盘快捷键"""
        # 撤销 - Ctrl+Z
        self.bind_all("<Control-z>", self._undo_mark)
        
        # 重做 - Ctrl+Y
        self.bind_all("<Control-y>", self._redo_mark)
        
        # 清除 - Ctrl+Delete
        self.bind_all("<Control-Delete>", self._clear_mask)
    
    def _continue_edit_result(self):
        """继续编辑处理结果"""
        # 检查是否有处理结果
        if not hasattr(self.watermark_remover, 'result_image') or self.watermark_remover.result_image is None:
            messagebox.showinfo("提示", "没有可编辑的结果")
            return
            
        # 将结果设置为当前图像并继续编辑
        if self.watermark_remover.continue_edit_result():
            # 获取预览图像并显示
            preview = self.watermark_remover.get_masked_preview()
            self._show_image(preview)
            
            # 禁用保存和继续编辑按钮
            self.save_button.config(state=tk.DISABLED)
            self.continue_edit_button.config(state=tk.DISABLED)
            
            # 更新状态
            self._update_status("已切换到编辑模式，可以继续标记水印区域")
        else:
            # 显示错误
            messagebox.showerror("错误", "无法继续编辑")

    def _clear_single_image(self):
        """清空单张模式的图像"""
        # 重置水印去除器
        self.watermark_remover = WatermarkRemover()
        
        # 清空画布
        self.canvas.delete("all")
        self.tk_image = None
        
        # 禁用保存按钮
        self.save_button.config(state=tk.DISABLED)
        self.continue_edit_button.config(state=tk.DISABLED)
        
        # 更新状态
        self._update_status("已清空图像")
    
    def _clear_template_image(self):
        """清空模板图像"""
        # 重置模板
        self.batch_processor.reset_template()
        
        # 清空画布
        self.canvas.delete("all")
        self.tk_image = None
        
        # 更新状态
        self._update_status("已清空模板图像")
    
    def _clear_batch_images(self):
        """清空批量处理的图像列表"""
        # 清空批量图像列表
        self.batch_processor.clear_batch_images()
        
        # 更新文件数量显示
        self.file_count_label.config(text="已选择: 0 个文件")
        
        # 更新状态
        self._update_status("已清空批量图像列表")
    
    def _on_tab_changed(self, event):
        """处理标签页切换事件"""
        # 获取当前选中的标签页
        current_tab = self.mode_notebook.index(self.mode_notebook.select())
        
        # 清空画布
        self.canvas.delete("all")
        self.tk_image = None
        
        # 获取画布尺寸
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # 根据当前标签页加载对应的图像
        if current_tab == 0:  # 单张模式
            # 更新单张模式水印去除器的显示尺寸
            self.watermark_remover.set_display_size(canvas_width, canvas_height)
            
            if hasattr(self.watermark_remover, 'image') and self.watermark_remover.image is not None:
                preview = self.watermark_remover.get_masked_preview()
                self._show_image(preview)
        else:  # 批量模式
            # 更新模板水印去除器的显示尺寸
            template_remover = self.batch_processor.get_template_remover()
            if template_remover:
                template_remover.set_display_size(canvas_width, canvas_height)
                
                if hasattr(template_remover, 'image') and template_remover.image is not None:
                    preview = template_remover.get_masked_preview()
                    self._show_image(preview)
                
        # 更新状态
        tab_name = "单张去除" if current_tab == 0 else "批量去除"
        self._update_status(f"切换到{tab_name}模式") 