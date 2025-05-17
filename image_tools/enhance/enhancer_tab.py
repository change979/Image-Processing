"""
图像增强界面模块
提供图像亮度、对比度、锐度等调整功能的用户界面
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import threading
from typing import List, Dict, Any, Optional

from ..utils.image_utils import (
    load_image, resize_image_for_display, get_image_for_tk, 
    enhance_image, denoise_image, auto_adjust
)


class ImageEnhancerTab(ttk.Frame):
    """图像增强标签页"""
    
    def __init__(self, parent):
        """初始化图像增强标签页
        
        Args:
            parent: 父级窗口组件
        """
        super().__init__(parent)
        
        # 初始化成员变量
        self.original_image = None  # 原始PIL图像
        self.enhanced_image = None  # 增强后的PIL图像
        self.preview_image = None   # 预览图像
        self.image_path = None      # 当前图像路径
        self.tk_image = None        # Tkinter图像对象
        self.batch_files = []       # 批量处理文件列表
        
        # 增强参数
        self.brightness_value = 0.0
        self.contrast_value = 0.0
        self.sharpness_value = 0.0
        self.saturation_value = 0.0
        self.denoise_value = 0
        
        # 设置UI
        self._setup_ui()
    
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
        
        # 创建单张增强标签页
        self.single_mode_frame = ttk.Frame(self.mode_notebook)
        self.mode_notebook.add(self.single_mode_frame, text="单张增强")
        self._setup_single_mode_ui()
        
        # 创建批量增强标签页
        self.batch_mode_frame = ttk.Frame(self.mode_notebook)
        self.mode_notebook.add(self.batch_mode_frame, text="批量增强")
        self._setup_batch_mode_ui()
        
        # 创建右侧显示区域
        self.display_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.display_frame, weight=1)
        
        # 创建画布用于显示图像
        self.canvas = tk.Canvas(self.display_frame, bg="#EEEEEE", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # 状态栏
        self.status_frame = ttk.Frame(self)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_label = ttk.Label(self.status_frame, text="就绪")
        self.status_label.pack(side=tk.LEFT, padx=5, pady=2)
        
        self.progress_bar = ttk.Progressbar(self.status_frame, mode='determinate')
        self.progress_bar.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5, pady=2)
        self.progress_bar.pack_forget()  # 隐藏进度条
    
    def _setup_single_mode_ui(self):
        """设置单张增强模式的UI"""
        # 图像加载区域
        load_frame = ttk.LabelFrame(self.single_mode_frame, text="图像加载")
        load_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(load_frame, text="打开图像", command=self._load_image).pack(fill=tk.X, padx=5, pady=5)
        
        # 增强设置区域
        enhance_frame = ttk.LabelFrame(self.single_mode_frame, text="增强设置")
        enhance_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 亮度调整
        ttk.Label(enhance_frame, text="亮度:").pack(anchor=tk.W, padx=5, pady=2)
        
        self.brightness_var = tk.DoubleVar(value=0.0)
        brightness_scale = ttk.Scale(
            enhance_frame, 
            from_=-1.0, to=1.0, 
            variable=self.brightness_var,
            orient=tk.HORIZONTAL,
            command=self._update_preview
        )
        brightness_scale.pack(fill=tk.X, padx=5, pady=5)
        
        # 对比度调整
        ttk.Label(enhance_frame, text="对比度:").pack(anchor=tk.W, padx=5, pady=2)
        
        self.contrast_var = tk.DoubleVar(value=0.0)
        contrast_scale = ttk.Scale(
            enhance_frame, 
            from_=-1.0, to=1.0, 
            variable=self.contrast_var,
            orient=tk.HORIZONTAL,
            command=self._update_preview
        )
        contrast_scale.pack(fill=tk.X, padx=5, pady=5)
        
        # 锐度调整
        ttk.Label(enhance_frame, text="锐度:").pack(anchor=tk.W, padx=5, pady=2)
        
        self.sharpness_var = tk.DoubleVar(value=0.0)
        sharpness_scale = ttk.Scale(
            enhance_frame, 
            from_=-1.0, to=1.0, 
            variable=self.sharpness_var,
            orient=tk.HORIZONTAL,
            command=self._update_preview
        )
        sharpness_scale.pack(fill=tk.X, padx=5, pady=5)
        
        # 饱和度调整
        ttk.Label(enhance_frame, text="饱和度:").pack(anchor=tk.W, padx=5, pady=2)
        
        self.saturation_var = tk.DoubleVar(value=0.0)
        saturation_scale = ttk.Scale(
            enhance_frame, 
            from_=-1.0, to=1.0, 
            variable=self.saturation_var,
            orient=tk.HORIZONTAL,
            command=self._update_preview
        )
        saturation_scale.pack(fill=tk.X, padx=5, pady=5)
        
        # 降噪设置
        ttk.Label(enhance_frame, text="降噪强度:").pack(anchor=tk.W, padx=5, pady=2)
        
        self.denoise_var = tk.IntVar(value=0)
        denoise_scale = ttk.Scale(
            enhance_frame, 
            from_=0, to=20, 
            variable=self.denoise_var,
            orient=tk.HORIZONTAL,
            command=self._update_preview
        )
        denoise_scale.pack(fill=tk.X, padx=5, pady=5)
        
        # 自动调整按钮
        ttk.Button(
            enhance_frame, 
            text="自动调整", 
            command=self._auto_enhance
        ).pack(fill=tk.X, padx=5, pady=5)
        
        # 重置按钮
        ttk.Button(
            enhance_frame, 
            text="重置参数", 
            command=self._reset_parameters
        ).pack(fill=tk.X, padx=5, pady=5)
        
        # 保存按钮
        self.save_button = ttk.Button(
            self.single_mode_frame, 
            text="保存增强结果", 
            command=self._save_enhanced_image,
            state=tk.DISABLED
        )
        self.save_button.pack(fill=tk.X, padx=5, pady=10)
    
    def _setup_batch_mode_ui(self):
        """设置批量增强模式的UI"""
        # 图像选择区域
        files_frame = ttk.LabelFrame(self.batch_mode_frame, text="图像选择")
        files_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(
            files_frame, 
            text="选择图像文件", 
            command=lambda: self._select_batch_files(False)
        ).pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(
            files_frame, 
            text="选择图像文件夹", 
            command=lambda: self._select_batch_files(True)
        ).pack(fill=tk.X, padx=5, pady=5)
        
        # 显示已选文件数量
        self.file_count_label = ttk.Label(files_frame, text="已选择: 0 个文件")
        self.file_count_label.pack(padx=5, pady=5)
        
        # 输出目录选择
        output_frame = ttk.LabelFrame(self.batch_mode_frame, text="输出设置")
        output_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(
            output_frame, 
            text="选择输出目录", 
            command=self._select_output_dir
        ).pack(fill=tk.X, padx=5, pady=5)
        
        self.output_dir_label = ttk.Label(output_frame, text="未选择输出目录")
        self.output_dir_label.pack(padx=5, pady=5)
        
        # 增强设置
        enhance_frame = ttk.LabelFrame(self.batch_mode_frame, text="增强设置")
        enhance_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 亮度调整
        ttk.Label(enhance_frame, text="亮度:").pack(anchor=tk.W, padx=5, pady=2)
        
        self.batch_brightness_var = tk.DoubleVar(value=0.0)
        brightness_scale = ttk.Scale(
            enhance_frame, 
            from_=-1.0, to=1.0, 
            variable=self.batch_brightness_var,
            orient=tk.HORIZONTAL
        )
        brightness_scale.pack(fill=tk.X, padx=5, pady=5)
        
        # 对比度调整
        ttk.Label(enhance_frame, text="对比度:").pack(anchor=tk.W, padx=5, pady=2)
        
        self.batch_contrast_var = tk.DoubleVar(value=0.0)
        contrast_scale = ttk.Scale(
            enhance_frame, 
            from_=-1.0, to=1.0, 
            variable=self.batch_contrast_var,
            orient=tk.HORIZONTAL
        )
        contrast_scale.pack(fill=tk.X, padx=5, pady=5)
        
        # 锐度调整
        ttk.Label(enhance_frame, text="锐度:").pack(anchor=tk.W, padx=5, pady=2)
        
        self.batch_sharpness_var = tk.DoubleVar(value=0.0)
        sharpness_scale = ttk.Scale(
            enhance_frame, 
            from_=-1.0, to=1.0, 
            variable=self.batch_sharpness_var,
            orient=tk.HORIZONTAL
        )
        sharpness_scale.pack(fill=tk.X, padx=5, pady=5)
        
        # 饱和度调整
        ttk.Label(enhance_frame, text="饱和度:").pack(anchor=tk.W, padx=5, pady=2)
        
        self.batch_saturation_var = tk.DoubleVar(value=0.0)
        saturation_scale = ttk.Scale(
            enhance_frame, 
            from_=-1.0, to=1.0, 
            variable=self.batch_saturation_var,
            orient=tk.HORIZONTAL
        )
        saturation_scale.pack(fill=tk.X, padx=5, pady=5)
        
        # 降噪设置
        ttk.Label(enhance_frame, text="降噪强度:").pack(anchor=tk.W, padx=5, pady=2)
        
        self.batch_denoise_var = tk.IntVar(value=0)
        denoise_scale = ttk.Scale(
            enhance_frame, 
            from_=0, to=20, 
            variable=self.batch_denoise_var,
            orient=tk.HORIZONTAL
        )
        denoise_scale.pack(fill=tk.X, padx=5, pady=5)
        
        # 自动增强选项
        self.auto_enhance_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            enhance_frame, 
            text="使用自动增强",
            variable=self.auto_enhance_var
        ).pack(anchor=tk.W, padx=5, pady=5)
        
        # 处理按钮
        self.batch_enhance_button = ttk.Button(
            self.batch_mode_frame, 
            text="开始批量增强", 
            command=self._start_batch_enhancement
        )
        self.batch_enhance_button.pack(fill=tk.X, padx=5, pady=10)
        
        # 停止按钮
        self.stop_button = ttk.Button(
            self.batch_mode_frame, 
            text="停止处理", 
            command=self._stop_batch_processing,
            state=tk.DISABLED
        )
        self.stop_button.pack(fill=tk.X, padx=5, pady=5)
    
    def _load_image(self):
        """加载单张图像"""
        file_path = filedialog.askopenfilename(
            title="选择图像",
            filetypes=[
                ("图像文件", "*.jpg *.jpeg *.png *.bmp *.tiff *.webp"),
                ("所有文件", "*.*")
            ]
        )
        
        if not file_path:
            return
            
        # 加载图像
        image = load_image(file_path)
        if image:
            self.original_image = image
            self.image_path = file_path
            self.enhanced_image = None
            
            # 重置参数
            self._reset_parameters()
            
            # 显示图像
            self._show_image(image)
            
            # 启用保存按钮
            self.save_button.config(state=tk.NORMAL)
            
            # 更新状态
            self._update_status(f"已加载图像: {os.path.basename(file_path)}")
        else:
            messagebox.showerror("错误", f"无法加载图像: {file_path}")
    
    def _update_preview(self, *args):
        """更新预览图像"""
        if not self.original_image:
            return
            
        # 获取当前参数值
        brightness = self._scale_to_factor(self.brightness_var.get())
        contrast = self._scale_to_factor(self.contrast_var.get())
        sharpness = self._scale_to_factor(self.sharpness_var.get())
        saturation = self._scale_to_factor(self.saturation_var.get())
        denoise = self.denoise_var.get()
        
        # 检查是否需要更新
        if (brightness == self.brightness_value and
            contrast == self.contrast_value and
            sharpness == self.sharpness_value and
            saturation == self.saturation_value and
            denoise == self.denoise_value):
            return
            
        # 更新参数值
        self.brightness_value = brightness
        self.contrast_value = contrast
        self.sharpness_value = sharpness
        self.saturation_value = saturation
        self.denoise_value = denoise
        
        # 在线程中处理图像增强
        threading.Thread(
            target=self._process_preview,
            daemon=True
        ).start()
    
    def _process_preview(self):
        """处理预览图像"""
        try:
            # 更新状态
            self.after(0, lambda: self._update_status("正在生成预览..."))
            
            # 应用增强
            img = self.original_image.copy()
            
            # 应用降噪
            if self.denoise_value > 0:
                img = denoise_image(img, self.denoise_value)
            
            # 应用增强
            img = enhance_image(
                img,
                brightness=self.brightness_value,
                contrast=self.contrast_value,
                sharpness=self.sharpness_value,
                color=self.saturation_value
            )
            
            # 保存增强结果
            self.enhanced_image = img
            
            # 更新界面显示
            self.after(0, lambda: self._show_image(img))
            self.after(0, lambda: self._update_status("预览已更新"))
            
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("错误", f"生成预览时出错: {str(e)}"))
            self.after(0, lambda: self._update_status("预览生成失败"))
    
    def _scale_to_factor(self, value):
        """将-1.0到1.0的滑块值转换为增强因子
        
        Args:
            value: 滑块值 (-1.0 到 1.0)
            
        Returns:
            增强因子 (0.0 到 2.0)
        """
        # 将-1到1映射到0.5到1.5
        return value + 1.0
    
    def _auto_enhance(self):
        """自动增强图像"""
        if not self.original_image:
            messagebox.showinfo("提示", "请先加载图像")
            return
            
        # 更新状态
        self._update_status("正在自动增强...")
        
        # 在线程中处理
        threading.Thread(
            target=self._process_auto_enhance,
            daemon=True
        ).start()
    
    def _process_auto_enhance(self):
        """处理自动增强"""
        try:
            # 应用自动增强
            img = auto_adjust(self.original_image)
            
            # 保存增强结果
            self.enhanced_image = img
            
            # 更新界面显示
            self.after(0, lambda: self._show_image(img))
            self.after(0, lambda: self._update_status("自动增强完成"))
            
            # 重置滑块
            self.after(0, lambda: self._reset_parameters())
            
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("错误", f"自动增强时出错: {str(e)}"))
            self.after(0, lambda: self._update_status("自动增强失败"))
    
    def _reset_parameters(self):
        """重置增强参数"""
        self.brightness_var.set(0.0)
        self.contrast_var.set(0.0)
        self.sharpness_var.set(0.0)
        self.saturation_var.set(0.0)
        self.denoise_var.set(0)
        
        # 如果有原始图像，显示它
        if self.original_image:
            self._show_image(self.original_image)
            self.enhanced_image = None
            
        # 更新参数值
        self.brightness_value = 1.0
        self.contrast_value = 1.0
        self.sharpness_value = 1.0
        self.saturation_value = 1.0
        self.denoise_value = 0
        
        # 更新状态
        self._update_status("参数已重置")
    
    def _save_enhanced_image(self):
        """保存增强后的图像"""
        # 检查是否有增强结果
        if not self.original_image:
            messagebox.showinfo("提示", "请先加载图像")
            return
            
        # 如果没有已增强的图像，使用原始图像
        save_image = self.enhanced_image if self.enhanced_image else self.original_image
        
        # 打开保存对话框
        file_path = filedialog.asksaveasfilename(
            title="保存增强结果",
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
            
        try:
            # 确定文件格式
            ext = os.path.splitext(file_path)[1].lower()
            
            # 准备保存参数
            save_args = {}
            
            # JPEG特殊处理
            if ext in ['.jpg', '.jpeg']:
                # 确保RGB模式
                if save_image.mode != "RGB":
                    save_image = save_image.convert("RGB")
                
                save_args["quality"] = 95
                
                # 处理EXIF数据
                if hasattr(self.original_image, "info") and "exif" in self.original_image.info:
                    save_args["exif"] = self.original_image.info["exif"]
            
            # 保存图像
            save_image.save(file_path, **save_args)
            
            # 更新状态
            self._update_status(f"增强结果已保存: {os.path.basename(file_path)}")
            
        except Exception as e:
            messagebox.showerror("保存失败", f"无法保存图像: {str(e)}")
    
    def _select_batch_files(self, use_folder=False):
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
            for root, _, files in os.walk(folder_path):
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp']:
                        image_files.append(os.path.join(root, file))
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
            
        # 保存批处理文件列表
        self.batch_files = list(image_files)
        
        # 更新文件数量显示
        self.file_count_label.config(text=f"已选择: {len(self.batch_files)} 个文件")
        
        # 预览第一个图像
        if self.batch_files:
            image = load_image(self.batch_files[0])
            if image:
                self._show_image(image)
                
        # 更新状态
        self._update_status(f"已选择 {len(self.batch_files)} 个图像文件")
    
    def _select_output_dir(self):
        """选择批量处理的输出目录"""
        output_dir = filedialog.askdirectory(title="选择输出目录")
        if not output_dir:
            return
            
        # 检查目录可写性
        if not os.access(output_dir, os.W_OK):
            messagebox.showerror("错误", f"输出目录不可写: {output_dir}")
            return
            
        # 更新显示
        self.output_dir = output_dir
        self.output_dir_label.config(text=f"输出目录: {output_dir}")
        
        # 更新状态
        self._update_status(f"已设置输出目录: {output_dir}")
    
    def _start_batch_enhancement(self):
        """开始批量增强处理"""
        # 检查是否有文件需要处理
        if not self.batch_files:
            messagebox.showinfo("提示", "请先选择图像文件")
            return
            
        # 检查是否已设置输出目录
        if not hasattr(self, 'output_dir') or not self.output_dir:
            messagebox.showinfo("提示", "请先选择输出目录")
            return
            
        # 获取增强参数
        enhance_params = {
            "brightness": self._scale_to_factor(self.batch_brightness_var.get()),
            "contrast": self._scale_to_factor(self.batch_contrast_var.get()),
            "sharpness": self._scale_to_factor(self.batch_sharpness_var.get()),
            "saturation": self._scale_to_factor(self.batch_saturation_var.get()),
            "denoise": self.batch_denoise_var.get(),
            "auto_enhance": self.auto_enhance_var.get()
        }
        
        # 更新UI状态
        self.batch_enhance_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        # 显示进度条
        self.progress_bar.config(mode='determinate', value=0, maximum=len(self.batch_files))
        self.progress_bar.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5, pady=2)
        
        # 更新状态
        self._update_status("开始批量增强...")
        
        # 设置停止标志
        self.stop_batch = False
        
        # 在独立线程中执行增强
        self.batch_thread = threading.Thread(
            target=self._batch_enhancement_thread,
            args=(enhance_params,),
            daemon=True
        )
        self.batch_thread.start()
    
    def _batch_enhancement_thread(self, enhance_params):
        """批量增强线程函数
        
        Args:
            enhance_params: 增强参数
        """
        results = {
            "total": len(self.batch_files),
            "success": 0,
            "failed": 0,
            "failed_files": []
        }
        
        # 处理每个文件
        for i, file_path in enumerate(self.batch_files):
            # 检查停止标志
            if self.stop_batch:
                break
                
            try:
                # 更新进度
                self.after(0, lambda i=i: self._update_batch_progress(i + 1, len(self.batch_files)))
                
                # 加载图像
                image = load_image(file_path)
                if not image:
                    results["failed"] += 1
                    results["failed_files"].append(file_path)
                    continue
                
                # 应用增强
                if enhance_params["auto_enhance"]:
                    # 自动增强
                    enhanced = auto_adjust(image)
                else:
                    # 手动参数增强
                    # 应用降噪
                    if enhance_params["denoise"] > 0:
                        image = denoise_image(image, enhance_params["denoise"])
                    
                    # 应用增强
                    enhanced = enhance_image(
                        image,
                        brightness=enhance_params["brightness"],
                        contrast=enhance_params["contrast"],
                        sharpness=enhance_params["sharpness"],
                        color=enhance_params["saturation"]
                    )
                
                # 生成输出文件名
                basename = os.path.basename(file_path)
                name, ext = os.path.splitext(basename)
                output_file = os.path.join(self.output_dir, name + "_enhanced" + ext)
                
                # 准备保存参数
                save_args = {}
                
                # JPEG特殊处理
                if ext.lower() in ['.jpg', '.jpeg']:
                    # 确保RGB模式
                    if enhanced.mode != "RGB":
                        save_image = enhanced.convert("RGB")
                    else:
                        save_image = enhanced
                    
                    save_args["quality"] = 95
                    
                    # 处理EXIF数据
                    if hasattr(image, "info") and "exif" in image.info:
                        save_args["exif"] = image.info["exif"]
                else:
                    save_image = enhanced
                
                # 保存图像
                save_image.save(output_file, **save_args)
                
                # 更新结果
                results["success"] += 1
                
            except Exception as e:
                print(f"增强文件 {file_path} 时出错: {e}")
                results["failed"] += 1
                results["failed_files"].append(file_path)
        
        # 在主线程更新UI
        self.after(0, lambda: self._finish_batch_enhancement(results))
    
    def _update_batch_progress(self, current, total):
        """更新批量处理进度
        
        Args:
            current: 当前处理数量
            total: 总数量
        """
        # 计算进度百分比
        percent = int((current / total) * 100)
        
        # 更新进度条
        self.progress_bar.config(value=current)
        
        # 更新状态
        self._update_status(f"正在增强: {current}/{total} - {percent}%")
    
    def _finish_batch_enhancement(self, results):
        """完成批量增强处理
        
        Args:
            results: 增强结果
        """
        # 隐藏进度条
        self.progress_bar.pack_forget()
        
        # 更新按钮状态
        self.batch_enhance_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
        # 更新状态
        self._update_status(f"批量增强完成: 成功 {results['success']}/{results['total']}")
        
        # 显示处理结果
        if results["failed"] > 0:
            # 有失败的文件
            failed_message = "\n".join(
                [os.path.basename(path) for path in results["failed_files"][:5]]
            )
            if len(results["failed_files"]) > 5:
                failed_message += f"\n...及其他 {len(results['failed_files'])-5} 个文件"
                
            messagebox.showwarning(
                "增强完成", 
                f"成功增强 {results['success']}/{results['total']} 个图像\n\n"
                f"失败的文件:\n{failed_message}"
            )
        else:
            # 全部成功
            messagebox.showinfo(
                "增强完成", 
                f"成功增强所有 {results['total']} 个图像\n\n"
                f"输出目录: {self.output_dir}"
            )
            
            # 尝试打开输出目录
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(self.output_dir)
                elif os.name == 'posix':  # macOS and Linux
                    if os.system('which xdg-open') == 0:  # Linux
                        os.system(f'xdg-open "{self.output_dir}"')
                    else:  # macOS
                        os.system(f'open "{self.output_dir}"')
            except:
                pass  # 忽略打开目录错误
    
    def _stop_batch_processing(self):
        """停止批量处理"""
        self.stop_batch = True
        self.stop_button.config(state=tk.DISABLED)
        self._update_status("正在停止处理...")
    
    def _show_image(self, image):
        """在画布上显示图像
        
        Args:
            image: PIL图像
        """
        if image is None:
            return
            
        # 获取画布大小
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # 如果画布尚未实际显示，使用默认大小
        if canvas_width <= 1:
            canvas_width = 800
        if canvas_height <= 1:
            canvas_height = 600
        
        # 调整图像大小以适应画布
        resized_image = resize_image_for_display(image, canvas_width, canvas_height)
        
        # 创建Tkinter图像
        self.tk_image = get_image_for_tk(resized_image)
        
        # 计算居中位置
        x_pos = (canvas_width - resized_image.width) // 2
        y_pos = (canvas_height - resized_image.height) // 2
        
        # 在画布上显示图像
        self.canvas.delete("all")
        self.canvas.create_image(x_pos, y_pos, anchor=tk.NW, image=self.tk_image)
    
    def _update_status(self, message):
        """更新状态栏信息
        
        Args:
            message: 状态消息
        """
        self.status_label.config(text=message) 