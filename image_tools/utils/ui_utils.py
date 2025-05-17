"""
UI工具模块
提供常用UI处理功能
"""
import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
from typing import Callable, Dict, Any, List, Optional, Tuple, Union


def create_tooltip(widget, text: str):
    """为控件创建工具提示
    
    Args:
        widget: 需要添加提示的控件
        text: 提示文本
    """
    tooltip = None
    
    def enter(event):
        nonlocal tooltip
        x, y, _, _ = widget.bbox("insert")
        x += widget.winfo_rootx() + 25
        y += widget.winfo_rooty() + 25
        
        # 创建工具提示窗口
        tooltip = tk.Toplevel(widget)
        tooltip.wm_overrideredirect(True)
        tooltip.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(tooltip, text=text, bg="#FFFFDD", relief="solid", borderwidth=1)
        label.pack()
        
    def leave(event):
        nonlocal tooltip
        if tooltip:
            tooltip.destroy()
            tooltip = None
            
    widget.bind("<Enter>", enter)
    widget.bind("<Leave>", leave)


def center_window(window, width: int, height: int):
    """使窗口在屏幕中居中显示
    
    Args:
        window: 要居中的窗口
        width: 窗口宽度
        height: 窗口高度
    """
    # 获取屏幕宽高
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    
    # 计算居中坐标
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    
    # 设置窗口大小和位置
    window.geometry(f"{width}x{height}+{x}+{y}")


def create_styled_button(parent, text: str, command: Callable, 
                         width: int = 10, height: int = 1,
                         bg: str = "#4CAF50", fg: str = "white",
                         hover_bg: str = "#45a049", **kwargs) -> tk.Button:
    """创建样式化按钮
    
    Args:
        parent: 父容器
        text: 按钮文本
        command: 点击回调函数
        width: 按钮宽度
        height: 按钮高度
        bg: 背景色
        fg: 前景色
        hover_bg: 悬停背景色
        **kwargs: 其他参数
        
    Returns:
        创建的按钮
    """
    button = tk.Button(parent, text=text, command=command, width=width,
                      height=height, bg=bg, fg=fg, **kwargs)
    
    # 添加悬停效果
    def on_enter(e):
        button['background'] = hover_bg
        
    def on_leave(e):
        button['background'] = bg
    
    button.bind("<Enter>", on_enter)
    button.bind("<Leave>", on_leave)
    
    return button


def create_scrollable_frame(parent) -> Tuple[ttk.Frame, ttk.Frame]:
    """创建带滚动条的框架
    
    Args:
        parent: 父容器
        
    Returns:
        (容器框架, 内部可滚动框架)
    """
    # 创建容器框架
    container = ttk.Frame(parent)
    
    # 创建画布
    canvas = tk.Canvas(container)
    scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
    
    # 创建可滚动框架
    scrollable_frame = ttk.Frame(canvas)
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    # 在画布上添加框架
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    # 布局
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # 绑定鼠标滚轮
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    canvas.bind_all("<MouseWheel>", _on_mousewheel)
    
    return container, scrollable_frame


def show_progress(parent, title: str, max_value: int) -> Tuple[tk.Toplevel, ttk.Progressbar, tk.Label]:
    """显示进度对话框
    
    Args:
        parent: 父窗口
        title: 对话框标题
        max_value: 进度条最大值
        
    Returns:
        (对话框窗口, 进度条控件, 标签控件)
    """
    # 创建对话框
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()
    
    # 进度条
    progress = ttk.Progressbar(dialog, orient="horizontal", length=300, mode="determinate")
    progress["maximum"] = max_value
    progress["value"] = 0
    progress.pack(padx=10, pady=10)
    
    # 进度文本
    progress_label = tk.Label(dialog, text="0%")
    progress_label.pack(pady=5)
    
    # 居中显示
    center_window(dialog, 350, 100)
    
    return dialog, progress, progress_label


def update_progress(progress: ttk.Progressbar, label: tk.Label, value: int):
    """更新进度条
    
    Args:
        progress: 进度条控件
        label: 标签控件
        value: 当前进度值
    """
    progress["value"] = value
    percent = int((value / progress["maximum"]) * 100)
    label.config(text=f"{percent}%")
    
    # 更新UI
    progress.update()
    label.update()


def create_file_drag_drop(widget, callback: Callable[[str], None]):
    """为控件添加文件拖放功能
    
    Args:
        widget: 接收拖放的控件
        callback: 文件路径回调函数
    """
    try:
        # Windows平台
        if sys.platform == 'win32':
            import win32file
            import win32con
            import pythoncom
            import pywintypes
            import win32gui
            
            # 注册拖放处理
            def drop_handler(hwnd, msg, wp, lp):
                if msg == win32con.WM_DROPFILES:
                    # 获取拖放文件路径
                    drop_count = win32gui.DragQueryFile(wp, -1, None, None)
                    for i in range(drop_count):
                        file_path = win32gui.DragQueryFile(wp, i, None, None)
                        callback(file_path)
                    win32gui.DragFinish(wp)
                    return True
                return False
            
            # 设置控件接收拖放
            hwnd = widget.winfo_id()
            old_win_proc = win32gui.SetWindowLong(hwnd, win32con.GWL_WNDPROC, drop_handler)
            win32gui.DragAcceptFiles(hwnd, True)
            
        # Linux/Mac平台
        else:
            widget.bind("<Drop>", lambda e: callback(e.data))
            
    except Exception as e:
        print(f"设置拖放失败: {e}")


def confirm_dialog(parent, title: str, message: str) -> bool:
    """显示确认对话框
    
    Args:
        parent: 父窗口
        title: 对话框标题
        message: 对话框消息
        
    Returns:
        用户是否确认
    """
    return messagebox.askyesno(title, message, parent=parent)


def show_error(parent, title: str, message: str):
    """显示错误对话框
    
    Args:
        parent: 父窗口
        title: 对话框标题
        message: 错误消息
    """
    messagebox.showerror(title, message, parent=parent)


def show_info(parent, title: str, message: str):
    """显示信息对话框
    
    Args:
        parent: 父窗口
        title: 对话框标题
        message: 信息消息
    """
    messagebox.showinfo(title, message, parent=parent)


def apply_theme(root):
    """应用自定义主题
    
    Args:
        root: 根窗口
    """
    style = ttk.Style()
    
    # 配置Treeview样式
    style.configure("Treeview", 
                    background="#F5F5F5",
                    foreground="black",
                    rowheight=25)
    style.configure("Treeview.Heading", 
                    font=('Arial', 10, 'bold'),
                    background="#4CAF50",
                    foreground="white")
    
    # 配置按钮样式
    style.configure("TButton", padding=6, relief="flat",
                   background="#4CAF50", foreground="white")
    style.map("TButton",
              background=[('active', '#45a049'), ('pressed', '#3e8e41')],
              foreground=[('pressed', 'white'), ('active', 'white')])
    
    # 配置选项卡样式
    style.configure("TNotebook", background="#f0f0f0", tabmargins=[2, 5, 2, 0])
    style.configure("TNotebook.Tab", background="#e0e0e0", padding=[10, 2],
                   font=('Arial', 10))
    style.map("TNotebook.Tab",
              background=[("selected", "#4CAF50")],
              foreground=[("selected", "white")])
    
    # 配置进度条样式
    style.configure("TProgressbar", 
                   background="#4CAF50",
                   troughcolor="#f0f0f0",
                   borderwidth=1,
                   thickness=20) 