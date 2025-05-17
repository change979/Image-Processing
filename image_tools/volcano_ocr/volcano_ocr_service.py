"""
火山引擎OCR服务模块
提供图像文字识别、图像描述和问答功能
"""

import os
import base64
import json
import logging
import requests
from typing import Dict, Any, List, Generator, Optional
import time

class VolcanoOCRService:
    """
    火山引擎OCR服务类
    提供图像文字识别、图像描述和问答功能
    """
    
    def __init__(self, config_manager):
        """
        初始化火山引擎OCR服务
        
        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        
        # API密钥信息
        self.api_key = None
        self.secret_key = None
        self.region = "cn-beijing"
        
        # 视觉模型配置
        self.model_id = "doubao-1.5-ui-tars"
        
        # 加载API密钥
        self._load_api_keys()
    
    def _load_api_keys(self) -> bool:
        """
        从配置中加载API密钥
        
        Returns:
            bool: 密钥是否加载成功
        """
        try:
            # 从配置中获取API密钥
            self.api_key = self.config_manager.get_config("api_keys.volcano_engine_access_key")
            self.secret_key = self.config_manager.get_config("api_keys.volcano_engine_secret_key")
            
            # 获取区域信息（如果有）
            region = self.config_manager.get_config("api_keys.volcano_engine_region")
            if region:
                self.region = region
            
            return bool(self.api_key and self.secret_key)
        
        except Exception as e:
            self.logger.error(f"Failed to load API keys: {str(e)}", exc_info=True)
            return False
    
    def _encode_image(self, image_path: str) -> Optional[str]:
        """
        将图像编码为Base64字符串
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            Optional[str]: Base64编码的图像字符串，如果失败则返回None
        """
        try:
            if not os.path.exists(image_path):
                self.logger.error(f"Image file not found: {image_path}")
                return None
                
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
                return encoded_string
        
        except Exception as e:
            self.logger.error(f"Failed to encode image: {str(e)}", exc_info=True)
            return None
    
    def _check_api_keys(self) -> bool:
        """
        检查API密钥是否已配置
        
        Returns:
            bool: 密钥是否已配置
        """
        if not self.api_key or not self.secret_key:
            if not self._load_api_keys():
                self.logger.error("API keys not configured")
                return False
        return True
    
    def analyze_image(self, image_path: str, prompt: str) -> Dict[str, Any]:
        """
        分析图像内容
        
        Args:
            image_path: 图像文件路径
            prompt: 分析提示
            
        Returns:
            Dict[str, Any]: 分析结果
            
        Raises:
            ValueError: 当API密钥未配置或请求失败时
        """
        if not self._check_api_keys():
            raise ValueError("火山引擎API密钥未配置，请在设置中配置API密钥")
        
        # 编码图像
        encoded_image = self._encode_image(image_path)
        if not encoded_image:
            raise ValueError("图像编码失败")
        
        # 构建请求数据
        payload = {
            "stream": False,
            "model_id": self.model_id,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}}
                    ]
                }
            ]
        }
        
        # 构建请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}:{self.secret_key}"
        }
        
        # 发送请求
        try:
            response = requests.post(
                f"https://visual.volces.com/{self.region}/api/v1/chat/completions",
                headers=headers,
                json=payload
            )
            
            # 检查响应状态
            if response.status_code != 200:
                error_msg = f"API请求失败: HTTP {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
                
            # 解析响应
            result = response.json()
            return result
            
        except requests.RequestException as e:
            error_msg = f"API请求异常: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg)
    
    def extract_text(self, image_path: str) -> str:
        """
        提取图像中的文字
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            str: 提取的文字
            
        Raises:
            ValueError: 当API密钥未配置或请求失败时
        """
        prompt = "请识别并提取这张图片中的所有文字内容，按照图片中的布局排列。"
        
        try:
            result = self.analyze_image(image_path, prompt)
            
            # 提取响应内容
            if "choices" in result and len(result["choices"]) > 0:
                choice = result["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    return choice["message"]["content"]
            
            return "未能识别出文字内容"
            
        except Exception as e:
            self.logger.error(f"Text extraction failed: {str(e)}", exc_info=True)
            raise ValueError(f"文字提取失败: {str(e)}")
    
    def describe_image(self, image_path: str) -> str:
        """
        描述图像内容
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            str: 图像描述
            
        Raises:
            ValueError: 当API密钥未配置或请求失败时
        """
        prompt = "请详细描述这张图片的内容，包括场景、物体、人物、活动等关键信息。"
        
        try:
            result = self.analyze_image(image_path, prompt)
            
            # 提取响应内容
            if "choices" in result and len(result["choices"]) > 0:
                choice = result["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    return choice["message"]["content"]
            
            return "未能生成图像描述"
            
        except Exception as e:
            self.logger.error(f"Image description failed: {str(e)}", exc_info=True)
            raise ValueError(f"图像描述失败: {str(e)}")
    
    def answer_question(self, image_path: str, question: str) -> str:
        """
        回答关于图像的问题
        
        Args:
            image_path: 图像文件路径
            question: 问题文本
            
        Returns:
            str: 问题回答
            
        Raises:
            ValueError: 当API密钥未配置或请求失败时
        """
        try:
            result = self.analyze_image(image_path, question)
            
            # 提取响应内容
            if "choices" in result and len(result["choices"]) > 0:
                choice = result["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    return choice["message"]["content"]
            
            return "未能回答问题"
            
        except Exception as e:
            self.logger.error(f"Question answering failed: {str(e)}", exc_info=True)
            raise ValueError(f"回答问题失败: {str(e)}")
    
    def chat_stream(self, image_path: str, question: str) -> Generator[str, None, None]:
        """
        流式回答关于图像的问题
        
        Args:
            image_path: 图像文件路径
            question: 问题文本
            
        Yields:
            str: 回答内容块
            
        Raises:
            ValueError: 当API密钥未配置或请求失败时
        """
        if not self._check_api_keys():
            raise ValueError("火山引擎API密钥未配置，请在设置中配置API密钥")
        
        # 编码图像
        encoded_image = self._encode_image(image_path)
        if not encoded_image:
            raise ValueError("图像编码失败")
        
        # 构建请求数据
        payload = {
            "stream": True,
            "model_id": self.model_id,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}}
                    ]
                }
            ]
        }
        
        # 构建请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}:{self.secret_key}"
        }
        
        # 发送请求并处理流式响应
        try:
            response = requests.post(
                f"https://visual.volces.com/{self.region}/api/v1/chat/completions",
                headers=headers,
                json=payload,
                stream=True
            )
            
            # 检查响应状态
            if response.status_code != 200:
                error_msg = f"API请求失败: HTTP {response.status_code}"
                self.logger.error(f"{error_msg} - {response.text}")
                raise ValueError(error_msg)
            
            # 处理流式响应
            for line in response.iter_lines():
                if line:
                    line = line.decode("utf-8")
                    
                    # 跳过空行和前缀
                    if not line.strip() or line.startswith("data: [DONE]"):
                        continue
                    
                    # 提取JSON数据
                    if line.startswith("data: "):
                        data = line[6:]  # 移除 "data: " 前缀
                        try:
                            chunk = json.loads(data)
                            if "choices" in chunk and len(chunk["choices"]) > 0:
                                choice = chunk["choices"][0]
                                if "delta" in choice and "content" in choice["delta"]:
                                    content = choice["delta"]["content"]
                                    if content:
                                        yield content
                        except json.JSONDecodeError:
                            self.logger.warning(f"Failed to decode JSON from line: {line}")
        
        except requests.RequestException as e:
            error_msg = f"API请求异常: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg) 