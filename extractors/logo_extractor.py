import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from fake_useragent import UserAgent


class LogoExtractor:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.ua = UserAgent()

    def extract(self, website: str) -> str | None:
        if not website.startswith(("http://", "https://")):
            website = f"https://{website}"

        parsed = urlparse(website)
        domain = (parsed.netloc or parsed.path.split("/")[0]).replace("www.", "")

        clearbit = f"https://logo.clearbit.com/{domain}"
        if self._is_image(clearbit):
            return clearbit

        try:
            r = self.session.get(
                website,
                timeout=self.timeout,
                headers={"User-Agent": self.ua.random},
            )
            r.raise_for_status()
            soup = BeautifulSoup(r.content, "html.parser")

            for meta in (
                soup.find("meta", property="og:image"),
                soup.find("meta", attrs={"itemprop": "logo"}),
            ):
                if meta and meta.get("content"):
                    url = urljoin(website, meta["content"])
                    if self._is_image(url):
                        return url

            header = soup.find(["header", "nav"])
            if header:
                best = None
                best_score = 0
                for img in header.find_all("img", limit=20):
                    src = img.get("src") or img.get("data-src")
                    if not src:
                        continue
                    text = " ".join([
                        img.get("alt", ""),
                        " ".join(img.get("class", [])),
                        src
                    ]).lower()
                    score = 0
                    if "logo" in text:
                        score += 10
                    if "brand" in text:
                        score += 5
                    w = img.get("width")
                    if w and w.isdigit():
                        score += int(w) / 10
                    if score > best_score:
                        best_score = score
                        best = src

                if best:
                    url = urljoin(website, best)
                    if self._is_image(url):
                        return url

        except Exception:
            pass

        for p in ("/logo.png", "/logo.svg", "/images/logo.png"):
            url = urljoin(website, p)
            if self._is_image(url):
                return url

        return f"https://www.google.com/s2/favicons?domain={domain}&sz=256"

    def _is_image(self, url: str) -> bool:
        try:
            r = self.session.head(url, timeout=5, allow_redirects=True)
            if r.status_code != 200:
                return False
            if "image" not in r.headers.get("content-type", "").lower():
                return False
            size = r.headers.get("content-length")
            return not size or int(size) > 1000
        except Exception:
            return False

    def close(self):
        self.session.close()
