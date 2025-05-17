"""
图像格式转换界面模块
提供转换图像格式的用户界面
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import threading
from typing import List, Dict, Any, Optional

from ..utils.image_utils import load_image, resize_image_for_display, get_image_for_tk


class FormatConverterTab(ttk.Frame):
    """图像格式转换标签页"""
    
    def __init__(self, parent):
        """初始化格式转换标签页
        
        Args:
            parent: 父级窗口组件
        """
        super().__init__(parent)
        
        # 初始化成员变量
        self.image = None  # 当前加载的PIL图像
        self.image_path = None  # 当前图像路径
        self.tk_image = None  # Tkinter图像对象
        self.batch_files = []  # 批量处理文件列表
        
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
        
        # 创建单张转换标签页
        self.single_mode_frame = ttk.Frame(self.mode_notebook)
        self.mode_notebook.add(self.single_mode_frame, text="单张转换")
        self._setup_single_mode_ui()
        
        # 创建批量转换标签页
        self.batch_mode_frame = ttk.Frame(self.mode_notebook)
        self.mode_notebook.add(self.batch_mode_frame, text="批量转换")
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
        """设置单张转换模式的UI"""
        # 图像加载区域
        load_frame = ttk.LabelFrame(self.single_mode_frame, text="图像加载")
        load_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(load_frame, text="打开图像", command=self._load_image).pack(fill=tk.X, padx=5, pady=5)
        
        # 格式设置区域
        format_frame = ttk.LabelFrame(self.single_mode_frame, text="格式设置")
        format_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 目标格式选择
        ttk.Label(format_frame, text="目标格式:").pack(anchor=tk.W, padx=5, pady=2)
        
        self.format_var = tk.StringVar(value="PNG")
        format_values = ["PNG", "JPEG", "BMP", "TIFF", "WEBP"]
        
        format_combo = ttk.Combobox(
            format_frame, 
            textvariable=self.format_var,
            values=format_values,
            state="readonly"
        )
        format_combo.pack(fill=tk.X, padx=5, pady=5)
        
        # JPEG质量设置
        self.jpeg_quality_frame = ttk.Frame(format_frame)
        self.jpeg_quality_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(self.jpeg_quality_frame, text="JPEG质量:").pack(anchor=tk.W)
        
        self.quality_var = tk.IntVar(value=95)
        quality_scale = ttk.Scale(
            self.jpeg_quality_frame, 
            from_=1, to=100, 
            variable=self.quality_var,
            orient=tk.HORIZONTAL
        )
        quality_scale.pack(fill=tk.X, pady=5)
        
        quality_label = ttk.Label(self.jpeg_quality_frame, textvariable=self.quality_var)
        quality_label.pack(side=tk.RIGHT, padx=5)
        
        # 根据格式显示/隐藏质量设置
        def on_format_change(*args):
            if self.format_var.get() == "JPEG":
                self.jpeg_quality_frame.pack(fill=tk.X, padx=5, pady=5)
            else:
                self.jpeg_quality_frame.pack_forget()
        
        # 绑定格式变更事件
        self.format_var.trace_add("write", on_format_change)
        on_format_change()  # 初始化
        
        # 保留EXIF数据选项
        self.keep_exif_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            format_frame, 
            text="保留EXIF数据",
            variable=self.keep_exif_var
        ).pack(anchor=tk.W, padx=5, pady=5)
        
        # 添加删除源文件选项
        self.delete_source_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            format_frame, 
            text="转换后删除源文件",
            variable=self.delete_source_var
        ).pack(anchor=tk.W, padx=5, pady=5)
        
        # 转换按钮
        ttk.Button(
            self.single_mode_frame, 
            text="转换并保存", 
            command=self._convert_and_save
        ).pack(fill=tk.X, padx=5, pady=10)
    
    def _setup_batch_mode_ui(self):
        """设置批量转换模式的UI"""
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
        
        # 格式设置
        format_frame = ttk.LabelFrame(self.batch_mode_frame, text="格式设置")
        format_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 目标格式
        ttk.Label(format_frame, text="目标格式:").pack(anchor=tk.W, padx=5, pady=2)
        
        self.batch_format_var = tk.StringVar(value="PNG")
        format_values = ["PNG", "JPEG", "BMP", "TIFF", "WEBP"]
        
        format_combo = ttk.Combobox(
            format_frame, 
            textvariable=self.batch_format_var,
            values=format_values,
            state="readonly"
        )
        format_combo.pack(fill=tk.X, padx=5, pady=5)
        
        # JPEG质量设置
        self.batch_jpeg_quality_frame = ttk.Frame(format_frame)
        self.batch_jpeg_quality_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(self.batch_jpeg_quality_frame, text="JPEG质量:").pack(anchor=tk.W)
        
        self.batch_quality_var = tk.IntVar(value=95)
        quality_scale = ttk.Scale(
            self.batch_jpeg_quality_frame, 
            from_=1, to=100, 
            variable=self.batch_quality_var,
            orient=tk.HORIZONTAL
        )
        quality_scale.pack(fill=tk.X, pady=5)
        
        quality_label = ttk.Label(self.batch_jpeg_quality_frame, textvariable=self.batch_quality_var)
        quality_label.pack(side=tk.RIGHT, padx=5)
        
        # 根据格式显示/隐藏质量设置
        def on_batch_format_change(*args):
            if self.batch_format_var.get() == "JPEG":
                self.batch_jpeg_quality_frame.pack(fill=tk.X, padx=5, pady=5)
            else:
                self.batch_jpeg_quality_frame.pack_forget()
        
        # 绑定格式变更事件
        self.batch_format_var.trace_add("write", on_batch_format_change)
        on_batch_format_change()  # 初始化
        
        # 保留EXIF数据选项
        self.batch_keep_exif_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            format_frame, 
            text="保留EXIF数据",
            variable=self.batch_keep_exif_var
        ).pack(anchor=tk.W, padx=5, pady=5)
        
        # 添加删除源文件选项
        self.batch_delete_source_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            format_frame, 
            text="转换后删除源文件",
            variable=self.batch_delete_source_var
        ).pack(anchor=tk.W, padx=5, pady=5)
        
        # 转换按钮
        self.convert_button = ttk.Button(
            self.batch_mode_frame, 
            text="开始批量转换", 
            command=self._start_batch_conversion
        )
        self.convert_button.pack(fill=tk.X, padx=5, pady=10)
        
        # 停止按钮
        self.stop_button = ttk.Button(
            self.batch_mode_frame, 
            text="停止转换", 
            command=self._stop_batch_conversion,
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
            self.image = image
            self.image_path = file_path
            
            # 显示图像
            self._show_image(image)
            
            # 更新状态
            self._update_status(f"已加载图像: {os.path.basename(file_path)}")
        else:
            messagebox.showerror("错误", f"无法加载图像: {file_path}")
    
    def _convert_and_save(self):
        """转换并保存单张图像"""
        if not self.image:
            messagebox.showinfo("提示", "请先加载图像")
            return
            
        # 获取目标格式
        format = self.format_var.get()
        
        # 确定文件扩展名
        extensions = {
            "PNG": ".png",
            "JPEG": ".jpg",
            "BMP": ".bmp",
            "TIFF": ".tif",
            "WEBP": ".webp"
        }
        ext = extensions.get(format, ".png")
        
        # 打开保存对话框
        file_path = filedialog.asksaveasfilename(
            title="保存转换后的图像",
            defaultextension=ext,
            filetypes=[
                ("PNG图像", "*.png"),
                ("JPEG图像", "*.jpg"),
                ("BMP图像", "*.bmp"),
                ("TIFF图像", "*.tif"),
                ("WEBP图像", "*.webp"),
                ("所有文件", "*.*")
            ]
        )
        
        if not file_path:
            return
            
        try:
            # 准备保存参数
            save_args = {}
            
            # JPEG特殊处理
            if format == "JPEG":
                # 确保RGB模式
                if self.image.mode != "RGB":
                    save_image = self.image.convert("RGB")
                else:
                    save_image = self.image
                
                save_args["quality"] = self.quality_var.get()
                
                # 处理EXIF数据
                if self.keep_exif_var.get() and hasattr(self.image, "info") and "exif" in self.image.info:
                    save_args["exif"] = self.image.info["exif"]
            else:
                save_image = self.image
            
            # 保存图像
            save_image.save(file_path, format=format, **save_args)
            
            # 如果选择了删除源文件选项，则在转换完成后删除源文件
            if self.delete_source_var.get() and self.image_path:
                try:
                    # 确保源文件和目标文件不是同一个
                    if os.path.normpath(self.image_path) != os.path.normpath(file_path):
                        os.remove(self.image_path)
                        self._update_status(f"图像已保存为 {format} 格式，源文件已删除: {os.path.basename(file_path)}")
                    else:
                        self._update_status(f"图像已保存为 {format} 格式: {os.path.basename(file_path)}")
                except Exception as e:
                    messagebox.showwarning("警告", f"无法删除源文件: {str(e)}")
                    self._update_status(f"图像已保存为 {format} 格式，但源文件删除失败: {os.path.basename(file_path)}")
            else:
                # 更新状态
                self._update_status(f"图像已保存为 {format} 格式: {os.path.basename(file_path)}")
            
        except Exception as e:
            messagebox.showerror("保存失败", f"无法保存图像: {str(e)}")
    
    def _select_batch_files(self, use_folder=False):
        """选择批量转换的图像文件
        
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
        """选择批量转换的输出目录"""
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
    
    def _start_batch_conversion(self):
        """开始批量转换"""
        # 检查是否有文件需要处理
        if not self.batch_files:
            messagebox.showinfo("提示", "请先选择图像文件")
            return
            
        # 检查是否已设置输出目录
        if not hasattr(self, 'output_dir') or not self.output_dir:
            messagebox.showinfo("提示", "请先选择输出目录")
            return
            
        # 获取格式设置
        target_format = self.batch_format_var.get()
        quality = self.batch_quality_var.get() if target_format == "JPEG" else 95
        keep_exif = self.batch_keep_exif_var.get()
        
        # 更新UI状态
        self.convert_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        # 显示进度条
        self.progress_bar.config(mode='determinate', value=0, maximum=len(self.batch_files))
        self.progress_bar.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5, pady=2)
        
        # 更新状态
        self._update_status("开始批量转换...")
        
        # 设置停止标志
        self.stop_batch = False
        
        # 在独立线程中执行转换
        self.batch_thread = threading.Thread(
            target=self._batch_conversion_thread,
            args=(target_format, quality, keep_exif),
            daemon=True
        )
        self.batch_thread.start()
    
    def _batch_conversion_thread(self, target_format, quality, keep_exif):
        """批量转换线程函数
        
        Args:
            target_format: 目标格式
            quality: JPEG质量
            keep_exif: 是否保留EXIF数据
        """
        results = {
            "total": len(self.batch_files),
            "success": 0,
            "failed": 0,
            "failed_files": [],
            "delete_failed": 0,
            "delete_failed_files": []
        }
        
        # 确定文件扩展名
        extensions = {
            "PNG": ".png",
            "JPEG": ".jpg",
            "BMP": ".bmp",
            "TIFF": ".tif",
            "WEBP": ".webp"
        }
        ext = extensions.get(target_format, ".png")
        
        # 是否删除源文件
        delete_source = self.batch_delete_source_var.get()
        
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
                
                # 准备保存参数
                save_args = {}
                
                # JPEG特殊处理
                if target_format == "JPEG":
                    # 确保RGB模式
                    if image.mode != "RGB":
                        save_image = image.convert("RGB")
                    else:
                        save_image = image
                    
                    save_args["quality"] = quality
                    
                    # 处理EXIF数据
                    if keep_exif and hasattr(image, "info") and "exif" in image.info:
                        save_args["exif"] = image.info["exif"]
                else:
                    save_image = image
                
                # 生成输出文件名
                basename = os.path.basename(file_path)
                name, _ = os.path.splitext(basename)
                output_file = os.path.join(self.output_dir, name + ext)
                
                # 保存图像
                save_image.save(output_file, format=target_format, **save_args)
                
                # 更新结果
                results["success"] += 1
                
                # 如果设置了删除源文件选项，则删除源文件
                if delete_source:
                    try:
                        # 确保源文件和目标文件不是同一个
                        if os.path.normpath(file_path) != os.path.normpath(output_file):
                            os.remove(file_path)
                        else:
                            # 源文件和目标文件是同一个，不删除
                            pass
                    except Exception as e:
                        print(f"删除源文件 {file_path} 时出错: {e}")
                        results["delete_failed"] += 1
                        results["delete_failed_files"].append(file_path)
                
            except Exception as e:
                print(f"转换文件 {file_path} 时出错: {e}")
                results["failed"] += 1
                results["failed_files"].append(file_path)
        
        # 在主线程更新UI
        self.after(0, lambda: self._finish_batch_conversion(results))
    
    def _update_batch_progress(self, current, total):
        """更新批量转换进度
        
        Args:
            current: 当前处理数量
            total: 总数量
        """
        # 计算进度百分比
        percent = int((current / total) * 100)
        
        # 更新进度条
        self.progress_bar.config(value=current)
        
        # 更新状态
        self._update_status(f"正在转换: {current}/{total} - {percent}%")
    
    def _finish_batch_conversion(self, results):
        """完成批量转换
        
        Args:
            results: 转换结果
        """
        # 隐藏进度条
        self.progress_bar.pack_forget()
        
        # 更新按钮状态
        self.convert_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
        # 更新状态
        self._update_status(f"批量转换完成: 成功 {results['success']}/{results['total']}")
        
        # 准备消息内容
        message_parts = [f"成功转换 {results['success']}/{results['total']} 个图像"]
        
        # 如果有转换失败的文件
        if results["failed"] > 0:
            failed_files = [os.path.basename(path) for path in results["failed_files"][:5]]
            if len(results["failed_files"]) > 5:
                failed_files.append(f"...及其他 {len(results['failed_files'])-5} 个文件")
            message_parts.append(f"转换失败: {results['failed']} 个文件\n" + "\n".join(failed_files))
        
        # 如果有删除失败的文件
        if "delete_failed" in results and results["delete_failed"] > 0:
            delete_failed_files = [os.path.basename(path) for path in results["delete_failed_files"][:5]]
            if len(results["delete_failed_files"]) > 5:
                delete_failed_files.append(f"...及其他 {len(results['delete_failed_files'])-5} 个文件")
            message_parts.append(f"删除源文件失败: {results['delete_failed']} 个文件\n" + "\n".join(delete_failed_files))
        
        # 添加输出目录信息
        message_parts.append(f"输出目录: {self.output_dir}")
        
        # 显示处理结果
        if results["failed"] > 0 or ("delete_failed" in results and results["delete_failed"] > 0):
            # 有失败的文件
            messagebox.showwarning("转换完成", "\n\n".join(message_parts))
        else:
            # 全部成功
            messagebox.showinfo("转换完成", "\n\n".join(message_parts))
            
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
    
    def _stop_batch_conversion(self):
        """停止批量转换"""
        self.stop_batch = True
        self.stop_button.config(state=tk.DISABLED)
        self._update_status("正在停止转换...")
    
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