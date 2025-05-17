"""
图像工具模块

提供常用的图像处理功能，包括图像加载、格式转换、调整大小、增强等
"""
import os
import io
import cv2
import numpy as np
from PIL import Image, ImageTk, ImageEnhance, ImageFilter, ExifTags
from typing import Tuple, List, Dict, Optional, Union, Any
import logging


def load_image(image_path: str) -> Optional[Image.Image]:
    """加载图像文件
    
    Args:
        image_path: 图像文件路径
    
    Returns:
        PIL图像对象，失败返回None
    """
    try:
        img = Image.open(image_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        return img
    except Exception as e:
        logging.error(f"加载图像失败: {str(e)}")
        return None


def pil_to_cv(pil_image: Image.Image) -> np.ndarray:
    """PIL图像转OpenCV格式
    
    Args:
        pil_image: PIL图像对象
    
    Returns:
        OpenCV格式图像数组，BGR顺序
    """
    # 确保图像是RGB模式
    if pil_image.mode != 'RGB':
        pil_image = pil_image.convert('RGB')
    
    # PIL转为numpy数组
    img_array = np.array(pil_image)
    
    # RGB转BGR
    return img_array[:, :, ::-1].copy()


def cv_to_pil(cv_image: np.ndarray) -> Image.Image:
    """OpenCV图像转PIL格式
    
    Args:
        cv_image: OpenCV格式图像数组，BGR顺序
    
    Returns:
        PIL图像对象
    """
    # BGR转RGB
    rgb = cv_image[:, :, ::-1]
    
    # numpy数组转为PIL
    return Image.fromarray(rgb)


def resize_image(img: Image.Image, width: int, height: int, 
                keep_aspect: bool = True, resample=Image.LANCZOS) -> Image.Image:
    """调整图像大小
    
    Args:
        img: 输入图像
        width: 目标宽度
        height: 目标高度
        keep_aspect: 是否保持宽高比
        resample: 重采样方法
    
    Returns:
        调整大小后的图像
    """
    if keep_aspect:
        # 计算缩放比例
        img_width, img_height = img.size
        scale_w = width / img_width
        scale_h = height / img_height
        
        # 使用较小的缩放比例
        scale = min(scale_w, scale_h)
        
        # 计算新的尺寸
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        
        # 调整大小
        return img.resize((new_width, new_height), resample)
    else:
        # 直接调整到指定尺寸
        return img.resize((width, height), resample)


def resize_image_for_display(img: Image.Image, max_width: int, max_height: int) -> Image.Image:
    """调整图像大小以适合显示区域
    
    Args:
        img: 输入图像
        max_width: 最大宽度
        max_height: 最大高度
    
    Returns:
        调整大小后的图像
    """
    img_width, img_height = img.size
    
    # 如果图像已经小于最大尺寸，直接返回
    if img_width <= max_width and img_height <= max_height:
        return img
    
    # 计算缩放比例
    scale_w = max_width / img_width
    scale_h = max_height / img_height
    
    # 使用较小的缩放比例
    scale = min(scale_w, scale_h)
    
    # 计算新的尺寸
    new_width = int(img_width * scale)
    new_height = int(img_height * scale)
    
    # 调整大小并返回
    return img.resize((new_width, new_height), Image.LANCZOS)


def get_image_for_tk(img: Image.Image) -> Any:
    """获取Tkinter可用的图像对象
    
    Args:
        img: PIL图像对象
    
    Returns:
        Tkinter兼容的图像对象
    """
    try:
        return ImageTk.PhotoImage(img)
    except ImportError:
        logging.error("导入ImageTk失败，请确保已安装PIL或Pillow")
        return None


def enhance_image(img: Image.Image, brightness: float = 1.0, contrast: float = 1.0, 
                 sharpness: float = 1.0, color: float = 1.0) -> Image.Image:
    """增强图像
    
    Args:
        img: 输入图像
        brightness: 亮度系数(0.0-2.0)
        contrast: 对比度系数(0.0-2.0)
        sharpness: 锐度系数(0.0-2.0)
        color: 色彩系数(0.0-2.0)
    
    Returns:
        增强后的图像
    """
    # 亮度调整
    if brightness != 1.0:
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(brightness)
    
    # 对比度调整
    if contrast != 1.0:
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(contrast)
    
    # 锐度调整
    if sharpness != 1.0:
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(sharpness)
    
    # 色彩调整
    if color != 1.0:
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(color)
    
    return img


def denoise_image(img: Image.Image, strength: int = 10) -> Image.Image:
    """降噪处理
    
    Args:
        img: 输入图像
        strength: 降噪强度(1-20)
    
    Returns:
        降噪后的图像
    """
    # 安全检查
    if strength < 1:
        strength = 1
    elif strength > 20:
        strength = 20
    
    # 转换为OpenCV格式
    cv_img = pil_to_cv(img)
    
    # 根据强度设置参数
    h = strength
    template_window_size = 7
    search_window_size = 21
    
    # 应用非局部均值降噪
    denoised = cv2.fastNlMeansDenoisingColored(
        cv_img, None, h, h, template_window_size, search_window_size
    )
    
    # 转回PIL格式
    return cv_to_pil(denoised)


def crop_image(img: Image.Image, left: int, top: int, right: int, bottom: int) -> Image.Image:
    """裁剪图像
    
    Args:
        img: 输入图像
        left, top, right, bottom: 裁剪区域坐标
    
    Returns:
        裁剪后的图像
    """
    # 确保坐标在图像范围内
    width, height = img.size
    left = max(0, left)
    top = max(0, top)
    right = min(width, right)
    bottom = min(height, bottom)
    
    # 确保区域有效
    if left >= right or top >= bottom:
        return img
    
    # 裁剪图像
    return img.crop((left, top, right, bottom))


def rotate_image(img: Image.Image, angle: float, expand: bool = True) -> Image.Image:
    """旋转图像
    
    Args:
        img: 输入图像
        angle: 旋转角度（顺时针）
        expand: 是否扩展图像以容纳完整旋转后的图像
    
    Returns:
        旋转后的图像
    """
    # 旋转图像
    return img.rotate(angle * -1, expand=expand, resample=Image.BICUBIC)


def apply_filter(img: Image.Image, filter_name: str) -> Image.Image:
    """应用图像滤镜
    
    Args:
        img: 输入图像
        filter_name: 滤镜名称，可选值：blur, contour, sharpen, smooth, edge_enhance
    
    Returns:
        应用滤镜后的图像
    """
    filter_map = {
        'blur': ImageFilter.BLUR,
        'contour': ImageFilter.CONTOUR,
        'sharpen': ImageFilter.SHARPEN,
        'smooth': ImageFilter.SMOOTH,
        'edge_enhance': ImageFilter.EDGE_ENHANCE,
    }
    
    if filter_name in filter_map:
        return img.filter(filter_map[filter_name])
    else:
        logging.warning(f"未知滤镜: {filter_name}")
        return img


def overlay_images(background: Image.Image, foreground: Image.Image, 
                  position: Tuple[int, int], opacity: float = 1.0) -> Image.Image:
    """叠加两个图像
    
    Args:
        background: 背景图像
        foreground: 前景图像
        position: 前景图像在背景图像上的位置(x, y)
        opacity: 前景图像的不透明度(0.0-1.0)
    
    Returns:
        叠加后的图像
    """
    # 确保前景图像有alpha通道
    if foreground.mode != 'RGBA':
        foreground = foreground.convert('RGBA')
    
    # 调整前景图像的不透明度
    if opacity < 1.0:
        foreground_data = foreground.getdata()
        new_data = []
        for item in foreground_data:
            # 调整alpha通道
            new_data.append((item[0], item[1], item[2], int(item[3] * opacity)))
        foreground.putdata(new_data)
    
    # 确保背景图像是RGBA模式
    result = background.copy().convert('RGBA')
    
    # 粘贴前景图像
    result.paste(foreground, position, foreground)
    
    # 转换回原始模式
    if background.mode != 'RGBA':
        result = result.convert(background.mode)
    
    return result


def create_image_grid(images: List[Image.Image], rows: int, cols: int, 
                     spacing: int = 10, bg_color: Tuple[int, int, int] = (255, 255, 255)) -> Image.Image:
    """创建图像网格
    
    Args:
        images: 图像列表
        rows: 行数
        cols: 列数
        spacing: 图像间距
        bg_color: 背景颜色
    
    Returns:
        网格图像
    """
    # 确保有足够的图像
    if len(images) == 0:
        return Image.new('RGB', (100, 100), bg_color)
    
    # 找出所有图像中的最大尺寸
    max_width = max(img.width for img in images)
    max_height = max(img.height for img in images)
    
    # 计算网格图像的尺寸
    grid_width = cols * max_width + (cols + 1) * spacing
    grid_height = rows * max_height + (rows + 1) * spacing
    
    # 创建网格图像
    grid_img = Image.new('RGB', (grid_width, grid_height), bg_color)
    
    # 将图像放置到网格中
    for idx, img in enumerate(images):
        if idx >= rows * cols:
            break
        
        # 计算行和列
        row = idx // cols
        col = idx % cols
        
        # 计算位置
        x = col * (max_width + spacing) + spacing
        y = row * (max_height + spacing) + spacing
        
        # 在中心位置放置图像
        x_offset = (max_width - img.width) // 2
        y_offset = (max_height - img.height) // 2
        
        # 粘贴图像
        grid_img.paste(img, (x + x_offset, y + y_offset))
    
    return grid_img


def extract_exif_data(img: Image.Image) -> Dict[str, Any]:
    """提取图像的EXIF数据
    
    Args:
        img: 输入图像
    
    Returns:
        EXIF数据字典
    """
    exif_data = {}
    
    # 检查图像是否有EXIF数据
    if hasattr(img, '_getexif') and img._getexif() is not None:
        exif = img._getexif()
        
        # 遍历所有EXIF标签
        for tag_id, value in exif.items():
            # 查找标签名称
            tag_name = ExifTags.TAGS.get(tag_id, tag_id)
            
            # 特殊处理一些标签
            if tag_name == 'GPSInfo':
                gps_data = {}
                for key in value:
                    gps_tag = ExifTags.GPSTAGS.get(key, key)
                    gps_data[gps_tag] = value[key]
                exif_data[tag_name] = gps_data
            else:
                exif_data[tag_name] = value
    
    return exif_data


def save_image(img: Image.Image, path: str, format: str = None, 
              quality: int = 95, keep_exif: bool = True) -> bool:
    """保存图像
    
    Args:
        img: 输入图像
        path: 保存路径
        format: 图像格式，如'PNG', 'JPEG'等，None表示根据扩展名自动确定
        quality: 质量参数(1-100)，仅对JPEG有效
        keep_exif: 是否保留原始EXIF数据
    
    Returns:
        保存是否成功
    """
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        
        # 如果未指定格式，从路径中获取
        if format is None:
            _, ext = os.path.splitext(path)
            if ext:
                format = ext[1:].upper()
            else:
                format = 'PNG'
        
        # 规范化格式名称
        format = format.upper()
        
        # 处理EXIF数据
        exif_data = None
        if keep_exif and format == 'JPEG' and hasattr(img, '_getexif') and img._getexif() is not None:
            exif_data = img.info.get('exif')
        
        # 保存图像
        if format == 'JPEG':
            img.save(path, format=format, quality=quality, exif=exif_data)
        else:
            img.save(path, format=format)
        
        return True
    except Exception as e:
        logging.error(f"保存图像失败: {str(e)}")
        return False


def get_image_info(img: Image.Image) -> Dict[str, Any]:
    """获取图像基本信息
    
    Args:
        img: 输入图像
    
    Returns:
        图像信息字典
    """
    info = {
        'width': img.width,
        'height': img.height,
        'mode': img.mode,
        'format': img.format,
    }
    
    # 添加EXIF数据
    exif_data = extract_exif_data(img)
    if exif_data:
        info['exif'] = exif_data
    
    return info


def inpaint_image(img: Image.Image, mask: Image.Image, method: str = 'ns') -> Image.Image:
    """修复图像（去除水印）
    
    Args:
        img: 原始图像
        mask: 掩码图像 (255表示要修复的区域)
        method: 修复方法，'ns'或'telea'
    
    Returns:
        修复后的图像
    """
    # 转换为OpenCV格式
    cv_img = pil_to_cv(img)
    cv_mask = np.array(mask)
    
    # 确保掩码是二值图像
    _, cv_mask = cv2.threshold(cv_mask, 127, 255, cv2.THRESH_BINARY)
    
    # 选择修复方法
    if method.lower() == 'telea':
        inpaint_method = cv2.INPAINT_TELEA
    else:
        inpaint_method = cv2.INPAINT_NS
    
    # 执行修复
    result_cv = cv2.inpaint(cv_img, cv_mask, 3, inpaint_method)
    
    # 转回PIL格式
    return cv_to_pil(result_cv)


def auto_contrast(img: Image.Image, cutoff: float = 0) -> Image.Image:
    """自动调整对比度
    
    Args:
        img: 输入图像
        cutoff: 剪切百分比(0-50)
    
    Returns:
        调整后的图像
    """
    from PIL import ImageOps
    return ImageOps.autocontrast(img, cutoff)


def auto_adjust(img: Image.Image) -> Image.Image:
    """自动调整图像（颜色、对比度、亮度）
    
    Args:
        img: 输入图像
    
    Returns:
        调整后的图像
    """
    # 转换为OpenCV格式
    cv_img = pil_to_cv(img)
    
    # 转换为LAB颜色空间
    lab = cv2.cvtColor(cv_img, cv2.COLOR_BGR2LAB)
    
    # 分离LAB通道
    l, a, b = cv2.split(lab)
    
    # 对亮度通道应用CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    
    # 合并通道
    adjusted_lab = cv2.merge((cl, a, b))
    
    # 转回BGR颜色空间
    adjusted_bgr = cv2.cvtColor(adjusted_lab, cv2.COLOR_LAB2BGR)
    
    # 转回PIL格式
    return cv_to_pil(adjusted_bgr)


def convert_image_format(img: Image.Image, format: str, quality: int = 95) -> bytes:
    """转换图像格式
    
    Args:
        img: 输入图像
        format: 目标格式，如'PNG', 'JPEG'等
        quality: 质量参数(1-100)，仅对JPEG有效
    
    Returns:
        格式转换后的图像数据
    """
    # 格式标准化
    format = format.upper()
    
    # 将图像写入内存
    buffer = io.BytesIO()
    
    # 根据格式保存
    if format == 'JPEG':
        img.save(buffer, format=format, quality=quality)
    else:
        img.save(buffer, format=format)
    
    # 返回数据
    return buffer.getvalue()


def convert_image_mode(img: Image.Image, mode: str) -> Image.Image:
    """转换图像模式
    
    Args:
        img: 输入图像
        mode: 目标模式，如'RGB', 'RGBA', 'L'等
    
    Returns:
        转换后的图像
    """
    return img.convert(mode) 