"""
水印移除模块
提供水印检测和去除功能的核心实现
"""
import os
import cv2
import numpy as np
from PIL import Image, ImageDraw
import logging
from typing import Tuple, Optional, List, Dict, Any, Union
import time
from concurrent.futures import ThreadPoolExecutor

from ..utils.image_utils import pil_to_cv, cv_to_pil, inpaint_image


class WatermarkRemover:
    """水印移除类
    
    提供多种水印移除算法和手动标记功能
    """
    
    # 可用的水印去除算法
    ALGORITHMS = {
        "基础修复": "basic",
        "NS算法": "ns",
        "Telea算法": "telea",
        "基于PatchMatch": "patchmatch",
        "智能检测": "auto"
    }
    
    def __init__(self):
        """初始化水印移除器"""
        # 原始图像（PIL格式）
        self.original_image = None
        # 当前处理中的图像
        self.current_image = None
        # 显示用的图像（带标记覆盖）
        self.display_image = None
        # 掩码图像（标记要移除的区域）
        self.mask = None
        # 画笔大小
        self.brush_size = 15
        # 绘制过程中的上一个点
        self.last_point = None
        # 水印检测结果
        self.detected_regions = []
        # 选择的算法
        self.algorithm = "ns"
        # 处理状态
        self.processing = False
        # 预览质量（0-100）
        self.preview_quality = 80
    
    def load_image(self, image: Union[str, Image.Image]) -> bool:
        """加载图像
        
        Args:
            image: 图像文件路径或PIL图像对象
        
        Returns:
            加载是否成功
        """
        try:
            if isinstance(image, str):
                # 从文件加载
                img = Image.open(image)
                # 转换为RGB模式
                if img.mode != 'RGB':
                    img = img.convert('RGB')
            else:
                # 已经是PIL图像对象
                img = image
                if img.mode != 'RGB':
                    img = img.convert('RGB')
            
            # 存储原始图像
            self.original_image = img
            self.current_image = img.copy()
            self.display_image = img.copy()
            
            # 创建空白掩码
            self.mask = Image.new('L', img.size, 0)
            
            # 重置状态
            self.last_point = None
            self.detected_regions = []
            
            logging.info(f"图像已加载, 尺寸: {img.size}")
            return True
        
        except Exception as e:
            logging.error(f"加载图像失败: {str(e)}")
            return False
    
    def start_draw(self, x: int, y: int) -> None:
        """开始绘制
        
        Args:
            x: 起始点x坐标
            y: 起始点y坐标
        """
        self.last_point = (x, y)
        self.draw(x, y)  # 绘制第一个点
    
    def draw(self, x: int, y: int) -> None:
        """绘制掩码
        
        Args:
            x: 当前点x坐标
            y: 当前点y坐标
        """
        if self.mask is None or self.original_image is None:
            return
        
        # 确保坐标在图像范围内
        width, height = self.mask.size
        if x < 0 or y < 0 or x >= width or y >= height:
            return
            
        # 获取绘图对象
        draw = ImageDraw.Draw(self.mask)
        
        # 绘制圆形笔触
        draw.ellipse((x - self.brush_size, y - self.brush_size,
                      x + self.brush_size, y + self.brush_size), fill=255)
        
        # 如果有上一个点，连接两点之间的线段
        if self.last_point and self.last_point != (x, y):
            draw.line([self.last_point, (x, y)], fill=255, width=self.brush_size * 2)
        
        # 更新上一个点
        self.last_point = (x, y)
        
        # 更新显示图像（原图 + 红色标记区域）
        self._update_display_image()
    
    def end_draw(self) -> None:
        """结束绘制"""
        self.last_point = None
    
    def clear_mask(self) -> None:
        """清除掩码"""
        if self.mask is not None and self.original_image is not None:
            # 重置掩码为全黑
            self.mask = Image.new('L', self.original_image.size, 0)
            # 恢复显示图像为原始图像
            self.display_image = self.original_image.copy()
    
    def update_brush_size(self, size: int) -> bool:
        """更新画笔大小
        
        Args:
            size: 新的画笔半径大小
        
        Returns:
            是否成功更新
        """
        try:
            size = int(size)
            if size < 1:
                size = 1
            elif size > 100:
                size = 100
            
            self.brush_size = size
            return True
        except:
            logging.error("更新画笔大小失败，输入值无效")
            return False
    
    def set_algorithm(self, algorithm: str) -> bool:
        """设置水印去除算法
        
        Args:
            algorithm: 算法名称或代码
        
        Returns:
            是否成功设置
        """
        # 如果输入算法是显示名称，转换为代码
        if algorithm in self.ALGORITHMS.keys():
            algorithm = self.ALGORITHMS[algorithm]
        
        # 验证算法是否支持
        valid_algorithms = list(self.ALGORITHMS.values())
        if algorithm not in valid_algorithms:
            logging.error(f"不支持的算法: {algorithm}")
            return False
        
        self.algorithm = algorithm
        logging.info(f"算法已设置为: {algorithm}")
        return True
    
    def set_preview_quality(self, quality: int) -> bool:
        """设置预览质量
        
        Args:
            quality: 预览质量值(1-100)
        
        Returns:
            是否成功设置
        """
        try:
            quality = int(quality)
            if quality < 1:
                quality = 1
            elif quality > 100:
                quality = 100
            
            self.preview_quality = quality
            return True
        except:
            logging.error("设置预览质量失败，输入值无效")
            return False
    
    def detect_watermark(self) -> List[Dict[str, Any]]:
        """自动检测水印
        
        Returns:
            检测到的水印区域列表，每个区域包含位置和大小信息
        """
        if self.original_image is None:
            return []
        
        try:
            # 转换为OpenCV格式
            cv_image = pil_to_cv(self.original_image)
            
            # 转为灰度图
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # 应用自适应阈值处理
            thresh = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY_INV, 11, 2
            )
            
            # 形态学操作，连接临近区域
            kernel = np.ones((3, 3), np.uint8)
            morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
            
            # 查找轮廓
            contours, _ = cv2.findContours(
                morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            
            # 筛选可能的水印区域
            img_area = self.original_image.width * self.original_image.height
            detected_regions = []
            
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                area = w * h
                
                # 过滤太小或太大的区域
                if 0.001 * img_area < area < 0.2 * img_area:
                    region = {
                        "x": x,
                        "y": y,
                        "width": w,
                        "height": h,
                        "area": area,
                        "confidence": self._calculate_watermark_confidence(gray, x, y, w, h)
                    }
                    detected_regions.append(region)
            
            # 按置信度排序
            detected_regions.sort(key=lambda r: r["confidence"], reverse=True)
            
            # 保存检测结果
            self.detected_regions = detected_regions[:5]  # 最多返回5个最可能的区域
            
            # 在掩码上标记检测到的区域
            if detected_regions:
                # 清除之前的掩码
                self.clear_mask()
                
                draw = ImageDraw.Draw(self.mask)
                for region in self.detected_regions:
                    x, y, w, h = region["x"], region["y"], region["width"], region["height"]
                    # 在掩码上绘制矩形
                    draw.rectangle([x, y, x+w, y+h], fill=255)
                
                # 更新显示图像
                self._update_display_image()
            
            return self.detected_regions
            
        except Exception as e:
            logging.error(f"水印检测失败: {str(e)}")
            return []
    
    def _calculate_watermark_confidence(self, gray_img: np.ndarray, x: int, y: int, 
                                       w: int, h: int) -> float:
        """计算区域是水印的置信度
        
        Args:
            gray_img: 灰度图像
            x, y, w, h: 区域坐标和尺寸
        
        Returns:
            置信度，0-1范围
        """
        # 提取区域
        roi = gray_img[y:y+h, x:x+w]
        
        # 计算区域内的标准差和平均值
        std_dev = np.std(roi)
        mean_val = np.mean(roi)
        
        # 计算区域内梯度的总和
        gradient_x = cv2.Sobel(roi, cv2.CV_64F, 1, 0, ksize=3)
        gradient_y = cv2.Sobel(roi, cv2.CV_64F, 0, 1, ksize=3)
        gradient_mag = np.sqrt(gradient_x**2 + gradient_y**2)
        gradient_sum = np.sum(gradient_mag)
        
        # 归一化梯度总和
        normalized_gradient = gradient_sum / (w * h)
        
        # 结合标准差和梯度计算置信度
        # 水印区域通常有一定的对比度且边缘清晰
        confidence = (1 - (std_dev / 255)) * 0.5 + (normalized_gradient / 100) * 0.5
        
        # 限制在0-1范围内
        confidence = max(0, min(1, confidence))
        
        return confidence
    
    def _update_display_image(self) -> None:
        """更新显示图像，添加红色蒙版标记区域"""
        if self.original_image is None or self.mask is None:
            return
        
        # 创建一个红色覆盖区
        red_overlay = Image.new('RGBA', self.original_image.size, (255, 0, 0, 128))
        
        # 创建临时图像
        temp_img = self.original_image.copy().convert('RGBA')
        
        # 将掩码转换为RGBA模式，用于混合
        mask_rgba = Image.new('RGBA', self.mask.size, (0, 0, 0, 0))
        mask_rgba.putalpha(self.mask)
        
        # 混合红色覆盖区和掩码
        red_mask = Image.composite(red_overlay, mask_rgba, self.mask)
        
        # 混合到原图
        self.display_image = Image.alpha_composite(temp_img, red_mask).convert('RGB')
    
    def remove_watermark(self, preview: bool = False) -> Optional[Image.Image]:
        """移除水印
        
        Args:
            preview: 是否为预览模式（低质量快速处理）
        
        Returns:
            处理后的图像，失败则返回None
        """
        if self.original_image is None or self.mask is None:
            logging.error("没有加载图像或未标记水印区域")
            return None
        
        # 检查掩码是否有标记区域
        mask_array = np.array(self.mask)
        if np.max(mask_array) == 0:
            logging.warning("未标记水印区域")
            return self.original_image.copy()
        
        try:
            self.processing = True
            start_time = time.time()
            
            # 根据不同算法处理
            if self.algorithm == "basic":
                result = self._basic_remove(preview)
            elif self.algorithm == "ns":
                result = self._ns_algorithm(preview)
            elif self.algorithm == "telea":
                result = self._telea_algorithm(preview)
            elif self.algorithm == "patchmatch":
                result = self._patchmatch_algorithm(preview)
            elif self.algorithm == "auto":
                result = self._auto_algorithm(preview)
            else:
                # 默认使用NS算法
                result = self._ns_algorithm(preview)
            
            elapsed_time = time.time() - start_time
            logging.info(f"水印移除完成，耗时: {elapsed_time:.2f}秒")
            
            # 更新当前图像
            self.current_image = result
            
            self.processing = False
            return result
            
        except Exception as e:
            self.processing = False
            logging.error(f"水印移除失败: {str(e)}")
            return None
    
    def _basic_remove(self, preview: bool = False) -> Image.Image:
        """基础修复算法
        
        简单的邻域填充
        
        Args:
            preview: 是否为预览模式
        
        Returns:
            处理后的图像
        """
        # 如果是预览模式，缩小图像以加快处理
        if preview:
            scale_factor = self.preview_quality / 100
            current_size = self.original_image.size
            new_size = (int(current_size[0] * scale_factor), 
                     int(current_size[1] * scale_factor))
            
            small_image = self.original_image.resize(new_size, Image.LANCZOS)
            small_mask = self.mask.resize(new_size, Image.LANCZOS)
            
            # 处理图像
            cv_image = pil_to_cv(small_image)
            cv_mask = np.array(small_mask)
            
            # 确保掩码是二值图像
            _, cv_mask = cv2.threshold(cv_mask, 127, 255, cv2.THRESH_BINARY)
            
            # 使用基础的修复算法
            result_cv = cv2.inpaint(cv_image, cv_mask, 3, cv2.INPAINT_NS)
            result_small = cv_to_pil(result_cv)
            
            # 调整回原始尺寸
            result = result_small.resize(self.original_image.size, Image.LANCZOS)
        else:
            # 转换为OpenCV格式
            cv_image = pil_to_cv(self.original_image)
            cv_mask = np.array(self.mask)
            
            # 确保掩码是二值图像
            _, cv_mask = cv2.threshold(cv_mask, 127, 255, cv2.THRESH_BINARY)
            
            # 使用基础的修复算法
            result_cv = cv2.inpaint(cv_image, cv_mask, 3, cv2.INPAINT_NS)
            result = cv_to_pil(result_cv)
        
        return result
    
    def _ns_algorithm(self, preview: bool = False) -> Image.Image:
        """NS算法水印移除
        
        基于Navier-Stokes方程的修复算法
        
        Args:
            preview: 是否为预览模式
        
        Returns:
            处理后的图像
        """
        # 使用util函数直接处理
        if preview:
            # 缩小图像以加快处理
            scale_factor = self.preview_quality / 100
            current_size = self.original_image.size
            new_size = (int(current_size[0] * scale_factor), 
                     int(current_size[1] * scale_factor))
            
            small_image = self.original_image.resize(new_size, Image.LANCZOS)
            small_mask = self.mask.resize(new_size, Image.LANCZOS)
            
            # 修复图像
            result_small = inpaint_image(small_image, small_mask, 'ns')
            
            # 调整回原始尺寸
            result = result_small.resize(self.original_image.size, Image.LANCZOS)
        else:
            result = inpaint_image(self.original_image, self.mask, 'ns')
        
        return result
    
    def _telea_algorithm(self, preview: bool = False) -> Image.Image:
        """Telea算法水印移除
        
        基于快速行进算法的修复
        
        Args:
            preview: 是否为预览模式
        
        Returns:
            处理后的图像
        """
        # 使用util函数直接处理
        if preview:
            # 缩小图像以加快处理
            scale_factor = self.preview_quality / 100
            current_size = self.original_image.size
            new_size = (int(current_size[0] * scale_factor), 
                     int(current_size[1] * scale_factor))
            
            small_image = self.original_image.resize(new_size, Image.LANCZOS)
            small_mask = self.mask.resize(new_size, Image.LANCZOS)
            
            # 修复图像
            result_small = inpaint_image(small_image, small_mask, 'telea')
            
            # 调整回原始尺寸
            result = result_small.resize(self.original_image.size, Image.LANCZOS)
        else:
            result = inpaint_image(self.original_image, self.mask, 'telea')
        
        return result
    
    def _patchmatch_algorithm(self, preview: bool = False) -> Image.Image:
        """PatchMatch算法水印移除
        
        基于PatchMatch的高质量修复
        
        Args:
            preview: 是否为预览模式
        
        Returns:
            处理后的图像
        """
        # 将PIL图像转换为CV格式
        cv_image = pil_to_cv(self.original_image)
        cv_mask = np.array(self.mask)
        
        # 确保掩码是二值图像
        _, cv_mask = cv2.threshold(cv_mask, 127, 255, cv2.THRESH_BINARY)
        
        # 如果是预览模式，缩小图像以加快处理
        if preview:
            scale_factor = self.preview_quality / 100
            h, w = cv_image.shape[:2]
            new_size = (int(w * scale_factor), int(h * scale_factor))
            
            cv_image = cv2.resize(cv_image, new_size, interpolation=cv2.INTER_AREA)
            cv_mask = cv2.resize(cv_mask, new_size, interpolation=cv2.INTER_AREA)
            _, cv_mask = cv2.threshold(cv_mask, 127, 255, cv2.THRESH_BINARY)
        
        try:
            # 尝试使用OpenCV的Photo模块中的高质量修复
            # 检查OpenCV版本是否支持
            major, _, _ = cv2.__version__.split('.')
            if int(major) >= 4:  # OpenCV 4.x及以上支持
                # 创建OpenCV的Photo模块修复器
                # inpaint可能会因为OpenCV版本或编译选项而不可用
                result_cv = cv2.inpaint(cv_image, cv_mask, 3, cv2.INPAINT_TELEA)
                
                # 定义PatchMatch算法参数（根据实际情况调整）
                # 对于预览模式使用较小的半径和迭代次数
                if preview:
                    radius = 5
                    iterations = 2
                else:
                    radius = 10
                    iterations = 5
                
                # 分块处理以提高效率
                h, w = cv_image.shape[:2]
                block_size = 512  # 每块大小
                
                # 创建结果图像
                result_blocks = result_cv.copy()
                
                # 获取需要处理的区域
                y_indices, x_indices = np.where(cv_mask > 0)
                if len(y_indices) > 0 and len(x_indices) > 0:
                    min_x, max_x = np.min(x_indices), np.max(x_indices)
                    min_y, max_y = np.min(y_indices), np.max(y_indices)
                    
                    # 扩展区域
                    min_x = max(0, min_x - radius)
                    min_y = max(0, min_y - radius)
                    max_x = min(w, max_x + radius)
                    max_y = min(h, max_y + radius)
                    
                    # 分块处理
                    for y in range(min_y, max_y, block_size):
                        for x in range(min_x, max_x, block_size):
                            # 计算当前块的范围
                            y_end = min(y + block_size, max_y)
                            x_end = min(x + block_size, max_x)
                            
                            # 提取块
                            block = cv_image[y:y_end, x:x_end]
                            block_mask = cv_mask[y:y_end, x:x_end]
                            
                            # 只处理包含掩码的块
                            if np.sum(block_mask) > 0:
                                # 处理块
                                # 在当前块内多次使用基础修复，模拟PatchMatch效果
                                block_result = block.copy()
                                for _ in range(iterations):
                                    block_result = cv2.inpaint(
                                        block_result, block_mask, radius, cv2.INPAINT_TELEA
                                    )
                                
                                # 将结果写回
                                result_blocks[y:y_end, x:x_end] = block_result
                
                # 结果图像
                result_cv = result_blocks
            else:
                # 旧版OpenCV使用基本的Telea修复
                result_cv = cv2.inpaint(cv_image, cv_mask, 3, cv2.INPAINT_TELEA)
            
            # 如果是预览模式，放大回原尺寸
            if preview:
                h, w = self.original_image.size[1], self.original_image.size[0]
                result_cv = cv2.resize(result_cv, (w, h), interpolation=cv2.INTER_LANCZOS4)
            
            # 转回PIL格式
            result = cv_to_pil(result_cv)
            
        except Exception as e:
            logging.error(f"PatchMatch算法失败，回退到Telea算法: {str(e)}")
            # 回退到Telea算法
            result = self._telea_algorithm(preview)
        
        return result
    
    def _auto_algorithm(self, preview: bool = False) -> Image.Image:
        """自动选择最佳算法
        
        根据水印区域特性自动选择合适的算法
        
        Args:
            preview: 是否为预览模式
        
        Returns:
            处理后的图像
        """
        # 分析掩码区域
        mask_array = np.array(self.mask)
        
        # 掩码的总面积
        total_pixels = self.mask.width * self.mask.height
        mask_area = np.sum(mask_array > 127) / total_pixels
        
        # 计算掩码的复杂度（边缘像素与总像素的比例）
        kernel = np.ones((3, 3), np.uint8)
        dilated = cv2.dilate(mask_array, kernel, iterations=1)
        eroded = cv2.erode(mask_array, kernel, iterations=1)
        edge = dilated - eroded
        complexity = np.sum(edge > 0) / np.sum(mask_array > 127) if np.sum(mask_array > 127) > 0 else 0
        
        # 根据面积和复杂度选择算法
        if mask_area < 0.01:  # 小面积水印
            if complexity > 0.2:  # 复杂形状
                logging.info("自动选择: Telea算法 (小面积复杂形状)")
                return self._telea_algorithm(preview)
            else:  # 简单形状
                logging.info("自动选择: NS算法 (小面积简单形状)")
                return self._ns_algorithm(preview)
        elif mask_area < 0.1:  # 中等面积水印
            if complexity > 0.3:  # 复杂形状
                logging.info("自动选择: PatchMatch算法 (中等面积复杂形状)")
                return self._patchmatch_algorithm(preview)
            else:  # 简单形状
                logging.info("自动选择: Telea算法 (中等面积简单形状)")
                return self._telea_algorithm(preview)
        else:  # 大面积水印
            logging.info("自动选择: PatchMatch算法 (大面积水印)")
            return self._patchmatch_algorithm(preview)
    
    def batch_process(self, image_paths: List[str], output_dir: str, 
                      output_format: str = None, max_workers: int = 4) -> Dict[str, Any]:
        """批量处理多个图像
        
        Args:
            image_paths: 图像文件路径列表
            output_dir: 输出目录
            output_format: 输出格式，None表示与源格式相同
            max_workers: 最大工作线程数
        
        Returns:
            处理结果统计
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # 结果统计
        results = {
            "total": len(image_paths),
            "success": 0,
            "fail": 0,
            "skipped": 0,
            "elapsed_time": 0,
            "failed_files": []
        }
        
        start_time = time.time()
        
        # 记录当前的掩码和算法
        current_mask = self.mask.copy() if self.mask is not None else None
        current_algorithm = self.algorithm
        
        # 定义工作函数
        def process_image(image_path):
            try:
                # 加载图像
                img = Image.open(image_path)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 调整掩码大小以匹配当前图像
                if current_mask is not None:
                    resized_mask = current_mask.resize(img.size, Image.LANCZOS)
                    
                    # 设置状态
                    self.original_image = img
                    self.mask = resized_mask
                    self.algorithm = current_algorithm
                    
                    # 处理图像
                    result = self.remove_watermark(preview=False)
                    
                    if result is not None:
                        # 确定输出格式
                        out_format = output_format
                        if out_format is None:
                            # 使用源格式
                            out_format = os.path.splitext(image_path)[1].strip('.')
                            if not out_format:
                                out_format = "png"
                        
                        # 确定输出文件名
                        base_name = os.path.basename(image_path)
                        name_without_ext = os.path.splitext(base_name)[0]
                        output_path = os.path.join(output_dir, f"{name_without_ext}.{out_format}")
                        
                        # 保存结果
                        result.save(output_path)
                        return True
                    else:
                        return False
                else:
                    logging.warning(f"没有可用的掩码，跳过: {image_path}")
                    return None
            except Exception as e:
                logging.error(f"处理图像失败 {image_path}: {str(e)}")
                return False
        
        # 使用线程池并行处理
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_path = {executor.submit(process_image, path): path for path in image_paths}
            
            # 收集结果
            for future in future_to_path:
                path = future_to_path[future]
                try:
                    result = future.result()
                    if result is True:
                        results["success"] += 1
                    elif result is False:
                        results["fail"] += 1
                        results["failed_files"].append(path)
                    else:  # None表示跳过
                        results["skipped"] += 1
                except Exception as e:
                    logging.error(f"任务异常 {path}: {str(e)}")
                    results["fail"] += 1
                    results["failed_files"].append(path)
        
        # 恢复原始状态
        self.mask = current_mask
        self.algorithm = current_algorithm
        
        # 计算总耗时
        results["elapsed_time"] = time.time() - start_time
        
        return results
    
    def show_brush_preview(self, x: int, y: int) -> Optional[Image.Image]:
        """显示画笔预览
        
        Args:
            x: 预览位置x坐标
            y: 预览位置y坐标
        
        Returns:
            带画笔预览的图像，失败返回None
        """
        if self.original_image is None:
            return None
        
        try:
            # 创建临时图像
            preview_img = self.display_image.copy()
            draw = ImageDraw.Draw(preview_img)
            
            # 绘制画笔预览圆圈
            draw.ellipse(
                (x - self.brush_size, y - self.brush_size, 
                 x + self.brush_size, y + self.brush_size), 
                outline=(255, 255, 0), width=2
            )
            
            return preview_img
        except Exception as e:
            logging.error(f"创建画笔预览失败: {str(e)}")
            return None
    
    def get_display_image(self) -> Optional[Image.Image]:
        """获取当前显示图像
        
        Returns:
            当前显示图像
        """
        return self.display_image 