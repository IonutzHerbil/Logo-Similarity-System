from PIL import Image
from pathlib import Path
from math import ceil

class LogoVisualizer:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_group_grid(self, group_id: str, image_paths: list[Path], max_width: int = 1024):
        if not image_paths:
            return
        images = [Image.open(p).resize((128, 128)) for p in image_paths]
        cols = min(len(images), max_width // 128)
        rows = ceil(len(images) / cols)
        grid = Image.new("RGB", (cols * 128, rows * 128), (255, 255, 255))
        for idx, img in enumerate(images):
            x = (idx % cols) * 128
            y = (idx // cols) * 128
            grid.paste(img, (x, y))
        path = self.output_dir / f"group_{group_id}.jpg"
        grid.save(path, "JPEG", quality=90)

    def save_all_groups(self, groups: list[list[str]], image_map: dict, top_n: int = 20):
        for i, g in enumerate(groups[:top_n], 1):
            imgs = [image_map[w] for w in g if w in image_map]
            self.save_group_grid(str(i), imgs)
