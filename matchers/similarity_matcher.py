import numpy as np
from pathlib import Path
from typing import Dict
from collections import defaultdict
from imagededup.methods import CNN
from PIL import Image
from tqdm import tqdm


class SimilarityMatcher:
    def __init__(self, threshold: float = 0.88):
        self.threshold = threshold
        self.cnn = CNN()
        self.color_cache = {}
    
    def encode_images(self, image_dir: str) -> dict:
        return self.cnn.encode_images(image_dir=image_dir)
    
    def find_duplicates(self, encodings: dict, min_threshold: float = 0.80) -> dict:
        return self.cnn.find_duplicates(
            encoding_map=encodings,
            min_similarity_threshold=min_threshold,
            scores=True
        )
    
    def get_dominant_color(self, img_path: Path) -> np.ndarray:
        if img_path in self.color_cache:
            return self.color_cache[img_path]
        
        try:
            img = Image.open(img_path).resize((50, 50))
            pixels = np.array(img.convert("RGB")).reshape(-1, 3)
            
            mask = np.all(pixels < 250, axis=1)
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
    
    def should_group(self, w1: str, w2: str, cnn_sim: float, image_map: Dict[str, Path]) -> bool:
        color_sim = self.color_similarity(image_map[w1], image_map[w2])
        
        if color_sim < 0.5:
            return False
        
        boosted_sim = cnn_sim * 0.7 + color_sim * 0.3
        
        return boosted_sim >= self.threshold
    
    def cluster(self, duplicates: dict, image_map: Dict[str, Path]) -> list[list[str]]:
        rev = {v.name: k for k, v in image_map.items()}
        graph = defaultdict(set)
        
        print("Building graph with color filtering...")
        
        for img, matches in tqdm(duplicates.items(), desc="Filtering"):
            if img not in rev:
                continue
            
            w1 = rev[img]
            for other, cnn_score in matches:
                if other in rev:
                    w2 = rev[other]
                    if self.should_group(w1, w2, cnn_score, image_map):
                        graph[w1].add(w2)
                        graph[w2].add(w1)
        
        visited, groups = set(), []
        
        def dfs(n, acc):
            visited.add(n)
            acc.append(n)
            for m in graph[n]:
                if m not in visited:
                    dfs(m, acc)
        
        for n in graph:
            if n not in visited:
                g = []
                dfs(n, g)
                groups.append(g)
        
        for w in image_map:
            if w not in visited:
                groups.append([w])
        
        return sorted(groups, key=len, reverse=True)