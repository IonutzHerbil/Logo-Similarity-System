import requests
from PIL import Image
import numpy as np
import cv2
from io import BytesIO
import logging
from typing import Optional, Tuple
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ImageProcessor:
    def __init__(self, target_size: Tuple[int, int] = (128, 128), cache_dir: str = 'logo_cache'):
        self.target_size = target_size
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def download_image(self, url: str, timeout: int = 10) -> Optional[Image.Image]:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, timeout=timeout, headers=headers, stream=True)
            response.raise_for_status()
            
            image = Image.open(BytesIO(response.content))
            
            if image.mode == 'RGBA':
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[3])
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')
            
            return image
        except Exception as e:
            logger.debug(f"Failed to download image from {url}: {e}")
            return None
    
    def preprocess_image(self, image: Image.Image) -> Optional[np.ndarray]:
        try:
            image_resized = image.resize(self.target_size, Image.Resampling.LANCZOS)
            img_array = np.array(image_resized)
            
            if len(img_array.shape) != 3 or img_array.shape[2] != 3:
                logger.debug("Image does not have 3 channels")
                return None
            
            return img_array
        except Exception as e:
            logger.debug(f"Failed to preprocess image: {e}")
            return None
    
    def convert_to_hsv(self, image: np.ndarray) -> np.ndarray:
        return cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
    
    def convert_to_lab(self, image: np.ndarray) -> np.ndarray:
        return cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
    
    def convert_to_grayscale(self, image: np.ndarray) -> np.ndarray:
        return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    
    def process_logo(self, logo_url: str) -> Optional[Tuple[np.ndarray, Image.Image]]:
        pil_image = self.download_image(logo_url)
        if pil_image is None:
            return None
        
        processed = self.preprocess_image(pil_image)
        if processed is None:
            return None
        
        return processed, pil_image
    
    def save_image(self, image: Image.Image, filepath: str):
        try:
            image.save(filepath, 'PNG')
            logger.debug(f"Saved image to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save image to {filepath}: {e}")
