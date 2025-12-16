import numpy as np
from pathlib import Path
from imagededup.methods import CNN
from PIL import Image
from tqdm import tqdm
from collections import defaultdict
from typing import Dict, List, Tuple

class SimilarityMatcher:
    def __init__(self, threshold: float = 0.65, color_threshold: float = 0.60):
        self.threshold = threshold 
        self.color_threshold = color_threshold 
        self.cnn = CNN()
        self.color_cache = {}

    def encode(self, image_dir: Path) -> Dict[str, np.ndarray]:
        return self.cnn.encode_images(image_dir=str(image_dir))

    def find_duplicates(self, encodings: Dict[str, np.ndarray]) -> Dict[str, List[Tuple[str, float]]]:
        return self.cnn.find_duplicates(
            encoding_map=encodings,
            min_similarity_threshold=self.threshold,
            scores=True
        )

    def get_dominant_color(self, img_path: Path) -> np.ndarray:
        if img_path in self.color_cache:
            return self.color_cache[img_path]
        try:
            img = Image.open(img_path).resize((50, 50)) 
            pixels = np.array(img.convert("RGB")).reshape(-1, 3)
            
            mask = np.any(pixels < 250, axis=1)
            
            if mask.sum() > 10: 
                pixels = pixels[mask]
                
            avg_color = pixels.mean(axis=0)
            self.color_cache[img_path] = avg_color
            return avg_color
        except:
            return np.array([128, 128, 128])

    def color_similarity(self, img1: Path, img2: Path) -> float:
        c1 = self.get_dominant_color(img1)
        c2 = self.get_dominant_color(img2)
        dist = np.linalg.norm(c1 - c2) / (np.sqrt(3) * 255) 
        return 1.0 - dist

    def should_match(self, w1: str, w2: str, cnn_sim: float, image_map: Dict[str, Path]) -> bool:
        if cnn_sim < self.threshold:
            return False
        
        color_sim = self.color_similarity(image_map[w1], image_map[w2])
        return color_sim >= self.color_threshold

    def cluster(self, duplicates: Dict[str, List[Tuple[str, float]]], image_map: Dict[str, Path]) -> List[List[str]]:
        rev_image_map = {v.name: k for k, v in image_map.items()}
        neighbors = defaultdict(set)

        for img_name, matches in tqdm(duplicates.items(), desc="Matching"):
            if img_name not in rev_image_map:
                continue
            w1 = rev_image_map[img_name]
            
            for other_img_name, score in matches:
                if other_img_name in rev_image_map:
                    w2 = rev_image_map[other_img_name]
                    if self.should_match(w1, w2, score, image_map):
                        neighbors[w1].add(w2)
                        neighbors[w2].add(w1)

        visited = set()
        groups: List[List[str]] = []

        def dfs(node, group):
            visited.add(node)
            group.append(node)
            for nb in neighbors.get(node, set()):
                if nb not in visited:
                    dfs(nb, group)

        for node in image_map.keys():
            if node not in visited:
                group: List[str] = []
                dfs(node, group)
                groups.append(group)

        return sorted(groups, key=len, reverse=True)