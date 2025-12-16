import requests
import numpy as np
import cv2
from PIL import Image
from io import BytesIO
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ImageProcessor:
    def __init__(self, target_size=(128, 128), cache_dir='logo_cache'):
        self.target_size = target_size
        self.cache_dir = cache_dir
    
    def process_logo(self, logo_url):
        try:
            img_data = self._download_image(logo_url)
            if img_data is None:
                return None
            
            pil_img = Image.open(BytesIO(img_data))
            
            if pil_img.mode == 'RGBA':
                background = Image.new('RGB', pil_img.size, (255, 255, 255))
                background.paste(pil_img, mask=pil_img.split()[3])
                pil_img = background
            elif pil_img.mode != 'RGB':
                pil_img = pil_img.convert('RGB')
            
            pil_img = pil_img.resize(self.target_size, Image.Resampling.LANCZOS)
            
            np_img = np.array(pil_img)
            
            return np_img, pil_img
            
        except Exception as e:
            logger.debug(f"Failed to process {logo_url}: {e}")
            return None
    
    def _download_image(self, url):
        try:
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.debug(f"Failed to download {url}: {e}")
            return None