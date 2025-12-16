import requests
from pathlib import Path
from PIL import Image
from io import BytesIO
from fake_useragent import UserAgent


class ImageProcessor:
    def __init__(self, image_dir: Path):
        self.image_dir = image_dir
        self.image_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.ua = UserAgent()

    def download(self, website: str, url: str) -> Path | None:
        try:
            r = self.session.get(
                url,
                timeout=10,
                headers={"User-Agent": self.ua.random},
            )
            r.raise_for_status()

            img = Image.open(BytesIO(r.content))
            if min(img.size) < 64:
                return None

            if img.mode == "RGBA":
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[3])
                img = bg
            else:
                img = img.convert("RGB")

            safe = website.replace("/", "_").replace(":", "_").replace(".", "_")
            path = self.image_dir / f"{safe}.jpg"
            img.save(path, "JPEG", quality=95)
            return path

        except Exception:
            return None

    def close(self):
        self.session.close()
