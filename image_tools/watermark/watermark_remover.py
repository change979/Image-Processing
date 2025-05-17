"""
水印去除核心处理类
负责图像中水印区域的识别和去除
"""
import os
import cv2
import numpy as np
from PIL import Image
import time
from typing import Tuple, Optional, List, Dict, Any

class WatermarkRemover:
    """水印去除核心类，处理单个图像的水印去除功能"""
    
    def __init__(self):
        """初始化水印去除器"""
        # 图像相关属性
        self.image = None  # 当前处理的图像
        self.original_image = None  # 原始图像
        self.mask = None  # 水印掩码
        self.result_image = None  # 处理结果图像
        self.masked_preview = None  # 带掩码的预览图像
        
        # 处理参数
        self.inpaint_radius = 3  # 修复半径
        self.algorithm = cv2.INPAINT_TELEA  # 默认算法
        self.advanced_method = "none"  # 高级方法，默认不使用
        
        # 状态标志
        self.is_processing = False  # 是否正在处理
        
        # 图像显示相关
        self.display_width = 0  # 显示宽度
        self.display_height = 0  # 显示高度
        self.scale_factor = 1.0  # 缩放因子
        
        # 绘制历史
        self.mask_history = []  # 掩码历史，用于撤销操作
        self.history_index = -1  # 历史索引
        
    def load_image(self, image_path: str) -> bool:
        """加载图像文件
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            bool: 加载是否成功
        """
        if not os.path.exists(image_path):
            return False
            
        try:
            # 使用OpenCV读取图像
            self.original_image = cv2.imread(image_path)
            
            # 如果OpenCV读取失败，尝试使用PIL读取
            if self.original_image is None:
                pil_image = Image.open(image_path)
                self.original_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            
            # 创建工作副本
            self.image = self.original_image.copy()
            
            # 创建空白掩码
            h, w = self.original_image.shape[:2]
            self.mask = np.zeros((h, w), dtype=np.uint8)
            
            # 重置结果和预览
            self.result_image = None
            self.masked_preview = None
            
            # 清空历史
            self.mask_history = []
            self.history_index = -1
            
            # 保存首次空白掩码到历史
            self._save_mask_to_history()
            
            return True
        except Exception as e:
            print(f"加载图像时出错: {e}")
            return False
    
    def set_algorithm(self, algorithm_name: str) -> None:
        """设置使用的算法
        
        Args:
            algorithm_name: 算法名称，'TELEA'或'NS'
        """
        if algorithm_name.upper() == "TELEA":
            self.algorithm = cv2.INPAINT_TELEA
        elif algorithm_name.upper() == "NS":
            self.algorithm = cv2.INPAINT_NS
        else:
            # 默认使用TELEA算法
            self.algorithm = cv2.INPAINT_TELEA
    
    def set_inpaint_radius(self, radius: int) -> None:
        """设置修复半径
        
        Args:
            radius: 修复半径，通常在1-10之间
        """
        self.inpaint_radius = max(1, min(20, radius))  # 限制范围在1-20之间
    
    def set_advanced_method(self, method: str) -> None:
        """设置高级修复方法
        
        Args:
            method: 高级修复方法名称
        """
        self.advanced_method = method.lower()
    
    def set_display_size(self, width: int, height: int) -> None:
        """设置显示尺寸
        
        Args:
            width: 显示宽度
            height: 显示高度
        """
        self.display_width = width
        self.display_height = height
        
        # 如果有图像，计算缩放因子
        if self.image is not None:
            img_h, img_w = self.image.shape[:2]
            self.scale_factor = min(width / img_w, height / img_h) * 0.9
    
    def canvas_to_image_coords(self, canvas_coords):
        """
        将画布坐标转换为图像坐标
        
        参数:
            canvas_coords (tuple): 画布上的坐标 (x, y)
            
        返回:
            tuple: 图像上的坐标 (x, y)
        """
        if self.image is None:
            return canvas_coords
        
        # 获取画布和图像尺寸
        canvas_width = self.display_width
        canvas_height = self.display_height
        
        img_height, img_width = self.image.shape[:2]
        
        # 计算缩放后的图像尺寸
        scaled_width = int(img_width * self.scale_factor)
        scaled_height = int(img_height * self.scale_factor)
        
        # 计算图像在画布上的位置（居中）
        x_offset = max(0, (canvas_width - scaled_width) // 2)
        y_offset = max(0, (canvas_height - scaled_height) // 2)
        
        # 转换坐标
        img_x = int((canvas_coords[0] - x_offset) / self.scale_factor)
        img_y = int((canvas_coords[1] - y_offset) / self.scale_factor)
        
        # 确保坐标在图像范围内
        img_x = max(0, min(img_x, img_width - 1))
        img_y = max(0, min(img_y, img_height - 1))
        
        return (img_x, img_y)
    
    def add_mask_region(self, canvas_points, radius=5):
        """
        在掩码上添加一个区域
        
        参数:
            canvas_points (list): 画布坐标点列表
            radius (int): 添加区域的半径
        """
        if self.image is None or self.mask is None:
            return
        
        # 确保掩码与当前图像尺寸一致
        if self.mask.shape[:2] != self.image.shape[:2]:
            h, w = self.image.shape[:2]
            self.mask = np.zeros((h, w), dtype=np.uint8)
        
        # 将画布坐标转换为图像坐标，并在掩码上绘制
        for point in canvas_points:
            img_point = self.canvas_to_image_coords(point)
            # 检查坐标是否有效
            if 0 <= img_point[0] < self.mask.shape[1] and 0 <= img_point[1] < self.mask.shape[0]:
                cv2.circle(self.mask, img_point, radius, 255, -1)
        
        # 更新掩码预览
        self._update_mask_preview()
    
    def draw_line_on_mask(self, start_canvas_coords, end_canvas_coords, brush_size):
        """
        在掩码上绘制线条
        
        参数:
            start_canvas_coords (tuple): 起始点画布坐标 (x, y)
            end_canvas_coords (tuple): 终点画布坐标 (x, y)
            brush_size (int): 线条宽度
        """
        if self.image is None or self.mask is None:
            return
        
        # 确保掩码与当前图像尺寸一致
        if self.mask.shape[:2] != self.image.shape[:2]:
            h, w = self.image.shape[:2]
            self.mask = np.zeros((h, w), dtype=np.uint8)
        
        # 转换为图像坐标
        start_img = self.canvas_to_image_coords(start_canvas_coords)
        end_img = self.canvas_to_image_coords(end_canvas_coords)
        
        # 检查坐标是否有效
        h, w = self.mask.shape[:2]
        if (0 <= start_img[0] < w and 0 <= start_img[1] < h and
            0 <= end_img[0] < w and 0 <= end_img[1] < h):
            
            # 计算半径
            radius = max(1, brush_size // 2)
            
            # 在掩码上绘制线条
            cv2.line(self.mask, start_img, end_img, 255, brush_size)
            
            # 在起点和终点画圆，确保线条连贯
            cv2.circle(self.mask, start_img, radius, 255, -1)
            cv2.circle(self.mask, end_img, radius, 255, -1)
        
        # 更新掩码预览
        self._update_mask_preview()
        
        # 每绘制5条线保存一次掩码到历史
        if np.random.random() < 0.2:  # 大约每5次保存一次
            self._save_mask_to_history()
    
    def clear_mask(self) -> None:
        """清除掩码并更新显示"""
        if self.image is not None:
            h, w = self.image.shape[:2]
            self.mask = np.zeros((h, w), dtype=np.uint8)
            # 清除后更新预览，显示原始图像
            self._update_mask_preview()
            
    def start_draw(self, canvas_point, brush_size):
        """
        开始绘制，处理第一个点
        
        参数:
            canvas_point (tuple): 画布坐标 (x, y)
            brush_size (int): 画笔大小
        """
        if self.image is None or self.mask is None:
            return
            
        # 确保掩码与当前图像尺寸一致
        if self.mask.shape[:2] != self.image.shape[:2]:
            h, w = self.image.shape[:2]
            self.mask = np.zeros((h, w), dtype=np.uint8)
            
        # 转换坐标
        img_point = self.canvas_to_image_coords(canvas_point)
        
        # 绘制第一个点
        radius = max(1, brush_size // 2)
        if 0 <= img_point[0] < self.mask.shape[1] and 0 <= img_point[1] < self.mask.shape[0]:
            cv2.circle(self.mask, img_point, radius, 255, -1)
            
        # 更新掩码预览
        self._update_mask_preview()
        
    def update_brush_size(self, size):
        """
        更新画笔大小
        
        参数:
            size (int): 新的画笔大小
        
        返回:
            bool: 是否更新成功
        """
        try:
            # 确保画笔大小有效
            brush_size = max(1, min(100, int(size)))
            return True
        except:
            return False
            
    def show_brush_preview(self, canvas_coords, brush_size):
        """
        获取带有笔刷预览的图像
        
        参数:
            canvas_coords (tuple): 画布坐标 (x, y)
            brush_size (int): 画笔大小
            
        返回:
            numpy.ndarray: 带有笔刷预览的图像
        """
        if self.image is None:
            return None
            
        # 获取当前显示的预览图像（带有掩码或处理结果）
        if self.masked_preview is not None:
            preview = self.masked_preview.copy()
        else:
            preview = self.image.copy()
            
        # 转换坐标
        img_point = self.canvas_to_image_coords(canvas_coords)
        
        # 检查坐标是否有效
        h, w = preview.shape[:2]
        if 0 <= img_point[0] < w and 0 <= img_point[1] < h:
            # 在预览图像上绘制圆形笔刷
            radius = max(1, brush_size // 2)
            cv2.circle(preview, img_point, radius, (0, 0, 255), 2)
            
        return preview
    
    def get_masked_preview(self) -> Optional[np.ndarray]:
        """获取带有掩码标记的预览图像
        
        Returns:
            带有掩码标记的预览图像
        """
        if self.image is None or self.mask is None:
            return None
            
        # 创建带有掩码标记的预览图像
        preview = self.image.copy()
        
        # 创建掩码覆盖层（红色）
        overlay = np.zeros_like(preview)
        overlay[:,:,2] = 255  # 红色通道
        
        # 将掩码扩展为3通道
        mask_3ch = cv2.merge([self.mask, self.mask, self.mask])
        
        # 在掩码区域创建蒙版
        mask_indices = mask_3ch > 0
        
        # 创建临时图像用于混合
        temp = preview.copy()
        # 在掩码区域显示半透明红色
        alpha = 0.5
        cv2.addWeighted(overlay, alpha, preview, 1 - alpha, 0, temp)
        
        # 只在掩码区域应用混合效果
        np.copyto(preview, temp, where=mask_indices)
        
        return preview
    
    def remove_watermark(self) -> bool:
        """执行水印去除操作
        
        Returns:
            bool: 操作是否成功
        """
        if self.image is None or self.mask is None:
            return False
            
        try:
            self.is_processing = True
            
            # 记录开始时间
            start_time = time.time()
            
            # 准备掩码
            h, w = self.original_image.shape[:2]
            
            # 确保掩码尺寸正确
            mask_resized = cv2.resize(self.mask, (w, h), interpolation=cv2.INTER_NEAREST)
            
            # 二值化掩码
            _, mask_binary = cv2.threshold(mask_resized, 127, 255, cv2.THRESH_BINARY)
            
            # 如果没有掩码区域，返回失败
            if np.max(mask_binary) == 0:
                self.is_processing = False
                return False
            
            # 使用OpenCV内置算法去除水印
            self.result_image = cv2.inpaint(
                self.original_image, 
                mask_binary, 
                self.inpaint_radius, 
                self.algorithm
            )
            
            # 记录结束时间
            end_time = time.time()
            print(f"水印去除用时: {end_time - start_time:.2f} 秒")
            
            self.is_processing = False
            return True
        except Exception as e:
            print(f"水印去除过程中出错: {e}")
            self.is_processing = False
            return False
    
    def remove_watermark_advanced(self) -> bool:
        """使用高级算法去除水印
        
        Returns:
            bool: 操作是否成功
        """
        # 如果没有选择高级方法或高级方法是none，使用基本方法
        if not self.advanced_method or self.advanced_method == "none":
            return self.remove_watermark()
            
        # 这里可以根据需要实现或调用不同的高级水印去除算法
        # 例如泊松融合、纹理合成等方法
        # 目前仅作为示例，仍使用基本方法
        return self.remove_watermark()
    
    def get_result_image(self) -> Optional[np.ndarray]:
        """获取处理结果图像
        
        Returns:
            处理后的图像，如果未处理则返回None
        """
        return self.result_image
    
    def continue_edit_result(self) -> bool:
        """将处理结果设置为当前图像，以便继续编辑
        
        Returns:
            bool: 操作是否成功
        """
        if self.result_image is None:
            return False
            
        # 将结果图像设置为当前图像
        self.image = self.result_image.copy()
        self.original_image = self.result_image.copy()
        
        # 重置掩码
        h, w = self.image.shape[:2]
        self.mask = np.zeros((h, w), dtype=np.uint8)
        
        # 清空历史
        self.mask_history = []
        self.history_index = -1
        
        # 保存首次空白掩码到历史
        self._save_mask_to_history()
        
        # 重置结果
        self.result_image = None
        self.masked_preview = None
        
        # 更新预览
        self._update_mask_preview()
        
        return True
    
    def _update_mask_preview(self):
        """更新掩码预览图像"""
        self.masked_preview = self.get_masked_preview()
    
    def save_result(self, output_path: str, quality: int = 95) -> bool:
        """保存处理结果
        
        Args:
            output_path: 输出文件路径
            quality: JPEG压缩质量 (1-100)
            
        Returns:
            bool: 保存是否成功
        """
        if self.result_image is None:
            return False
            
        try:
            # 确定文件扩展名
            _, ext = os.path.splitext(output_path)
            ext = ext.lower()
            
            # 根据不同格式使用不同参数
            if ext in ['.jpg', '.jpeg']:
                params = [cv2.IMWRITE_JPEG_QUALITY, quality]
            elif ext == '.png':
                params = [cv2.IMWRITE_PNG_COMPRESSION, 1]  # 1表示较低压缩率，速度快
            else:
                params = []
            
            # 保存图像
            cv2.imwrite(output_path, self.result_image, params)
            
            return True
        except Exception as e:
            print(f"保存结果时出错: {e}")
            return False
    
    def _save_mask_to_history(self):
        """保存当前掩码到历史记录"""
        if self.mask is None:
            return
            
        # 如果不是在历史最新状态，丢弃之后的历史
        if self.history_index < len(self.mask_history) - 1:
            self.mask_history = self.mask_history[:self.history_index + 1]
            
        # 复制当前掩码并添加到历史
        mask_copy = self.mask.copy()
        self.mask_history.append(mask_copy)
        self.history_index = len(self.mask_history) - 1
    
    def undo_mask(self) -> bool:
        """撤销最后一次掩码编辑
        
        Returns:
            bool: 是否成功撤销
        """
        if not self.mask_history or self.history_index <= 0:
            return False
            
        # 减少历史索引
        self.history_index -= 1
        
        # 恢复掩码
        self.mask = self.mask_history[self.history_index].copy()
        
        # 更新预览
        self._update_mask_preview()
        
        return True
        
    def redo_mask(self) -> bool:
        """重做掩码编辑
        
        Returns:
            bool: 是否成功重做
        """
        if self.history_index >= len(self.mask_history) - 1:
            return False
            
        # 增加历史索引
        self.history_index += 1
        
        # 恢复掩码
        self.mask = self.mask_history[self.history_index].copy()
        
        # 更新预览
        self._update_mask_preview()
        
        return True 