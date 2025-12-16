import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from fake_useragent import UserAgent
from typing import Optional
from requests.adapters import HTTPAdapter

class LogoExtractor:
    def __init__(self, timeout: int = 10, workers: int = 20):
        self.timeout = timeout
        self.session = requests.Session()
        adapter = HTTPAdapter(pool_connections=workers, pool_maxsize=workers)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.ua = UserAgent()

    def extract(self, website: str) -> Optional[str]:
        if not website.startswith(("http://", "https://")):
            website = f"https://{website}"

        try:
            parsed = urlparse(website)
            domain = (parsed.netloc or parsed.path.split("/")[0]).replace("www.", "")
        except Exception:
            return None

        clearbit = f"https://logo.clearbit.com/{domain}"
        if self._is_image(clearbit):
            return clearbit

        try:
            r = self.session.get(
                website,
                timeout=self.timeout,
                headers={"User-Agent": self.ua.random},
                allow_redirects=True,
            )
            r.raise_for_status()
            soup = BeautifulSoup(r.content, "html.parser")

            for meta in (
                soup.find("meta", property="og:image"),
                soup.find("meta", attrs={"itemprop": "logo"}),
                soup.find("link", rel="apple-touch-icon"),
                soup.find("link", rel="icon", sizes="256x256"),
            ):
                content_attr = meta.get("content") if meta else None
                href_attr = meta.get("href") if meta else None
                
                url = content_attr or href_attr

                if url:
                    full_url = urljoin(website, url)
                    if self._is_image(full_url, min_size=2000):
                        return full_url

            header = soup.find(["header", "nav"])
            if header:
                best = None
                best_score = 0
                for img in header.find_all("img", limit=30):
                    src = img.get("src") or img.get("data-src")
                    if not src:
                        continue
                        
                    text = " ".join([
                        img.get("alt", ""),
                        " ".join(img.get("class", [])),
                        src
                    ]).lower()
                    
                    score = 0
                    if "logo" in text: score += 10
                    if "brand" in text: score += 5
                    
                    w = img.get("width")
                    if w and w.isdigit():
                        score += int(w) / 10
                        
                    if score > best_score:
                        full_url = urljoin(website, src)
                        if self._is_image(full_url, min_size=2000):
                            best_score = score
                            best = src
                        
                if best:
                    return urljoin(website, best)

        except Exception:
            pass

        for p in ("/logo.png", "/logo.svg", "/images/logo.png", "/favicon.ico"):
            url = urljoin(website, p)
            if self._is_image(url):
                return url

        return None

    def _is_image(self, url: str, min_size: int = 500) -> bool:
        try:
            r = self.session.head(url, timeout=5, allow_redirects=True)
            if r.status_code != 200:
                return False
            
            content_type = r.headers.get("content-type", "").lower()
            if "image" not in content_type:
                return False
                
            size = r.headers.get("content-length")
            return not size or int(size) > min_size
            
        except Exception:
            return False

    def close(self):
        self.session.close()