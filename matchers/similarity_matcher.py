import numpy as np
from pathlib import Path
from imagededup.methods import CNN
from PIL import Image
from tqdm import tqdm

class SimilarityMatcher:
    def __init__(self, threshold: float = 0.92):
        self.threshold = threshold
        self.cnn = CNN()
        self.color_cache = {}

    def encode(self, image_dir: Path):
        return self.cnn.encode_images(image_dir=str(image_dir))

    def find_duplicates(self, encodings: dict):
        return self.cnn.find_duplicates(
            encoding_map=encodings,
            min_similarity_threshold=self.threshold,
            scores=True
        )

    def get_dominant_color(self, img_path: Path):
        if img_path in self.color_cache:
            return self.color_cache[img_path]
        try:
            img = Image.open(img_path).resize((50, 50))
            pixels = np.array(img.convert("RGB")).reshape(-1, 3)
            mask = np.all(pixels < 240, axis=1)
            if mask.sum() > 10:
                pixels = pixels[mask]
            avg_color = pixels.mean(axis=0)
            self.color_cache[img_path] = avg_color
            return avg_color
        except:
            return np.array([128, 128, 128])

    def color_similarity(self, img1: Path, img2: Path):
        c1 = self.get_dominant_color(img1)
        c2 = self.get_dominant_color(img2)
        dist = np.linalg.norm(c1 - c2) / (np.sqrt(3) * 255)
        return 1.0 - dist

    def should_match(self, w1: str, w2: str, cnn_sim: float, image_map: dict):
        if cnn_sim < self.threshold:
            return False
        color_sim = self.color_similarity(image_map[w1], image_map[w2])
        if color_sim < 0.65:
            return False
        return True

    def cluster(self, duplicates: dict, image_map: dict):
        rev = {v.name: k for k, v in image_map.items()}
        pairs = set()
        for img, matches in tqdm(duplicates.items(), desc="Matching"):
            if img not in rev:
                continue
            w1 = rev[img]
            for other, score in matches:
                if other in rev:
                    w2 = rev[other]
                    if self.should_match(w1, w2, score, image_map):
                        pairs.add(tuple(sorted([w1, w2])))
        parent = {}
        def find(x):
            if x not in parent:
                parent[x] = x
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]
        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[py] = px
        for w1, w2 in pairs:
            union(w1, w2)
        groups_dict = {}
        for w in image_map:
            root = find(w)
            if root not in groups_dict:
                groups_dict[root] = []
            groups_dict[root].append(w)
        groups = []
        for g in groups_dict.values():
            if len(g) <= 10:
                groups.append(g)
            else:
                for w in g:
                    groups.append([w])
        return sorted(groups, key=len, reverse=True)
