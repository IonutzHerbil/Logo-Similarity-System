import requests
from PIL import Image
from io import BytesIO
from pathlib import Path
from fake_useragent import UserAgent
from typing import Optional

class ImageProcessor:
    def __init__(self, image_dir: Path):
        self.image_dir = image_dir
        self.image_dir.mkdir(exist_ok=True)
        self.session = requests.Session()
        self.ua = UserAgent()

    def download(self, website: str, url: str) -> Optional[Path]:
        try:
            r = self.session.get(url, timeout=10, headers={"User-Agent": self.ua.random})
            r.raise_for_status()
            img = Image.open(BytesIO(r.content))
            
            if min(img.size) < 64:
                return None
            if img.mode == "RGBA":
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[-1])
                img = bg
            elif img.mode != "RGB":
            elif img.mode != "RGB":
                img = img.convert("RGB")

            safe_website = website.replace("https://", "").replace("http://", "").replace("/", "_").replace(":", "_").replace("?", "_")
            path = self.image_dir / f"{safe_website}.jpg"
            
            img.save(path, "JPEG", quality=95)
            return path
        except:
            return None

    def cleanup(self):
        self.session.close()