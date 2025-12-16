import numpy as np
from pathlib import Path
from typing import Dict, Set, Tuple
from PIL import Image
from imagededup.methods import CNN
from tqdm import tqdm


class SimilarityMatcher:
    def __init__(self, threshold: float = 0.92, color_threshold: float = 0.65):
        self.threshold = threshold
        self.color_threshold = color_threshold
        self.cnn = CNN()
        self.color_cache: Dict[Path, np.ndarray] = {}

    def encode(self, image_dir: Path) -> dict:
        return self.cnn.encode_images(image_dir=str(image_dir))

    def find_duplicates(self, enc: dict) -> dict:
        return self.cnn.find_duplicates(
            encoding_map=enc,
            min_similarity_threshold=self.threshold,
            scores=True,
        )

    def _dominant_color(self, path: Path) -> np.ndarray:
        if path in self.color_cache:
            return self.color_cache[path]

        img = Image.open(path).resize((50, 50)).convert("RGB")
        px = np.array(img).reshape(-1, 3)
        mask = np.all(px < 240, axis=1)
        if mask.sum() > 10:
            px = px[mask]

        avg = px.mean(axis=0)
        self.color_cache[path] = avg
        return avg

    def _color_similarity(self, a: Path, b: Path) -> float:
        d = np.linalg.norm(self._dominant_color(a) - self._dominant_color(b))
        return 1.0 - d / (np.sqrt(3) * 255)

    def cluster(self, duplicates: dict, image_map: Dict[str, Path]) -> list[list[str]]:
        rev = {p.name: w for w, p in image_map.items()}
        pairs: Set[Tuple[str, str]] = set()

        for img, matches in tqdm(duplicates.items(), desc="Matching"):
            if img not in rev:
                continue
            w1 = rev[img]
            for other, score in matches:
                if other not in rev or score < self.threshold:
                    continue
                w2 = rev[other]
                if self._color_similarity(image_map[w1], image_map[w2]) >= self.color_threshold:
                    pairs.add(tuple(sorted((w1, w2))))

        parent = {}

        def find(x):
            parent.setdefault(x, x)
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(a, b):
            pa, pb = find(a), find(b)
            if pa != pb:
                parent[pb] = pa

        for a, b in pairs:
            union(a, b)

        groups = {}
        for w in image_map:
            r = find(w)
            groups.setdefault(r, []).append(w)

        final = []
        for g in groups.values():
            if len(g) <= 10:
                final.append(g)
            else:
                for w in g:
                    final.append([w])

        return sorted(final, key=len, reverse=True)
