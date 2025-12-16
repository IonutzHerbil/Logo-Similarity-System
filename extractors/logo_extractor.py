import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from fake_useragent import UserAgent

class LogoExtractor:
    def __init__(self, timeout=10):
        self.timeout = timeout
        self.session = requests.Session()
        self.ua = UserAgent()

    def extract(self, website: str) -> str | None:
        if not website.startswith(("http://", "https://")):
            website = f"https://{website}"
        parsed = urlparse(website)
        domain = (parsed.netloc or parsed.path.split("/")[0]).replace("www.", "")
        clearbit = f"https://logo.clearbit.com/{domain}"
        try:
            r = self.session.head(clearbit, timeout=5, allow_redirects=True)
            if r.status_code == 200:
                return clearbit
        except:
            pass
        try:
            r = self.session.get(
                website,
                timeout=self.timeout,
                headers={"User-Agent": self.ua.random, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
            )
            r.raise_for_status()
            soup = BeautifulSoup(r.content, "html.parser")
            og = soup.find("meta", property="og:image")
            if og and og.get("content"):
                img_url = urljoin(website, og["content"])
                if self._is_valid_image(img_url):
                    return img_url
            schema = soup.find("meta", {"itemprop": "logo"})
            if schema and schema.get("content"):
                img_url = urljoin(website, schema["content"])
                if self._is_valid_image(img_url):
                    return img_url
            header = soup.find(["header", "nav"])
            if header:
                imgs = header.find_all("img", limit=20)
                best_img, best_score = None, 0
                for img in imgs:
                    score = 0
                    alt = img.get("alt", "").lower()
                    cls = " ".join(img.get("class", [])).lower()
                    src = img.get("src", "").lower()
                    if "logo" in alt or "logo" in cls or "logo" in src:
                        score += 10
                    if "brand" in alt or "brand" in cls:
                        score += 5
                    width = img.get("width")
                    if width and width.isdigit():
                        score += int(width) / 10
                    if score > best_score:
                        best_score = score
                        best_img = img
                if best_img:
                    src = best_img.get("src") or best_img.get("data-src")
                    img_url = urljoin(website, src)
                    if self._is_valid_image(img_url):
                        return img_url
            for path in ["/logo.png", "/logo.svg", "/assets/logo.png", "/images/logo.png"]:
                test_url = urljoin(website, path)
                if self._is_valid_image(test_url):
                    return test_url
        except:
            pass
        return f"https://www.google.com/s2/favicons?domain={domain}&sz=256"

    def _is_valid_image(self, url: str) -> bool:
        try:
            r = self.session.head(url, timeout=5, allow_redirects=True)
            if r.status_code == 200:
                ct = r.headers.get("content-type", "").lower()
                if "image" in ct:
                    size = r.headers.get("content-length")
                    if size and int(size) < 1000:
                        return False
                    return True
        except:
            pass
        return False

    def cleanup(self):
        self.session.close()
