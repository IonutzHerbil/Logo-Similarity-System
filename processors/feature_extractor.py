import numpy as np
import cv2
from PIL import Image
import imagehash
from skimage.feature import hog
from sklearn.cluster import KMeans
import logging
from typing import Dict, List, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FeatureExtractor:
    def __init__(self):
        self.hog_pixels_per_cell = (8, 8)
        self.hog_cells_per_block = (2, 2)
        self.num_dominant_colors = 5
    
    def extract_features(self, image: np.ndarray, pil_image: Image.Image) -> Dict:
        features = {}
        
        try:
            features['color_hist'] = self.extract_color_histogram(image)
            features['dominant_colors'] = self.extract_dominant_colors(image)
            features['hog'] = self.extract_hog_features(image)
            features['phash'] = self.extract_perceptual_hash(pil_image)
            features['dhash'] = self.extract_difference_hash(pil_image)
            features['ahash'] = self.extract_average_hash(pil_image)
            features['hsv_hist'] = self.extract_hsv_histogram(image)
            
            logger.debug(f"Successfully extracted all features")
            return features
        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            return {}
    
    def extract_color_histogram(self, image: np.ndarray, bins: int = 32) -> np.ndarray:
        hist_r = np.histogram(image[:,:,0], bins=bins, range=(0, 256))[0]
        hist_g = np.histogram(image[:,:,1], bins=bins, range=(0, 256))[0]
        hist_b = np.histogram(image[:,:,2], bins=bins, range=(0, 256))[0]
        
        hist = np.concatenate([hist_r, hist_g, hist_b])
        hist = hist / (hist.sum() + 1e-7)
        
        return hist
    
    def extract_hsv_histogram(self, image: np.ndarray, bins_h: int = 32, bins_s: int = 16) -> np.ndarray:
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        
        hist_h = np.histogram(hsv[:,:,0], bins=bins_h, range=(0, 180))[0]
        hist_s = np.histogram(hsv[:,:,1], bins=bins_s, range=(0, 256))[0]
        
        hist = np.concatenate([hist_h, hist_s])
        hist = hist / (hist.sum() + 1e-7)
        
        return hist
    
    def extract_dominant_colors(self, image: np.ndarray) -> Dict:
        try:
            pixels = image.reshape(-1, 3)
            
            kmeans = KMeans(n_clusters=self.num_dominant_colors, random_state=42, n_init=10)
            kmeans.fit(pixels)
            
            colors = kmeans.cluster_centers_.astype(int)
            labels = kmeans.labels_
            
            unique, counts = np.unique(labels, return_counts=True)
            proportions = counts / len(labels)
            
            sorted_idx = np.argsort(proportions)[::-1]
            colors = colors[sorted_idx]
            proportions = proportions[sorted_idx]
            
            return {
                'colors': colors.tolist(),
                'proportions': proportions.tolist()
            }
        except Exception as e:
            logger.debug(f"Dominant color extraction failed: {e}")
            return {
                'colors': [[0, 0, 0]] * self.num_dominant_colors,
                'proportions': [1.0/self.num_dominant_colors] * self.num_dominant_colors
            }
    
    def extract_hog_features(self, image: np.ndarray) -> np.ndarray:
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            
            features = hog(
                gray,
                orientations=9,
                pixels_per_cell=self.hog_pixels_per_cell,
                cells_per_block=self.hog_cells_per_block,
                block_norm='L2-Hys',
                visualize=False,
                feature_vector=True
            )
            
            features = features / (np.linalg.norm(features) + 1e-7)
            
            return features
        except Exception as e:
            logger.debug(f"HOG extraction failed: {e}")
            return np.zeros(100)
    
    def extract_perceptual_hash(self, pil_image: Image.Image, hash_size: int = 8) -> str:
        try:
            phash = imagehash.phash(pil_image, hash_size=hash_size)
            return str(phash)
        except Exception as e:
            logger.debug(f"pHash extraction failed: {e}")
            return "0" * (hash_size ** 2)
    
    def extract_difference_hash(self, pil_image: Image.Image, hash_size: int = 8) -> str:
        try:
            dhash = imagehash.dhash(pil_image, hash_size=hash_size)
            return str(dhash)
        except Exception as e:
            logger.debug(f"dHash extraction failed: {e}")
            return "0" * (hash_size ** 2)
    
    def extract_average_hash(self, pil_image: Image.Image, hash_size: int = 8) -> str:
        try:
            ahash = imagehash.average_hash(pil_image, hash_size=hash_size)
            return str(ahash)
        except Exception as e:
            logger.debug(f"aHash extraction failed: {e}")
            return "0" * (hash_size ** 2)
    
    def create_feature_vector(self, features: Dict) -> np.ndarray:
        try:
            components = []
            
            if 'color_hist' in features:
                components.append(features['color_hist'])
            
            if 'hsv_hist' in features:
                components.append(features['hsv_hist'])
            
            if 'dominant_colors' in features:
                colors = np.array(features['dominant_colors']['colors']).flatten()
                proportions = np.array(features['dominant_colors']['proportions'])
                components.extend([colors, proportions])
            
            if 'hog' in features:
                components.append(features['hog'])
            
            if components:
                feature_vector = np.concatenate(components)
                return feature_vector
            else:
                return np.zeros(1)
        except Exception as e:
            logger.error(f"Feature vector creation failed: {e}")
            return np.zeros(1)
