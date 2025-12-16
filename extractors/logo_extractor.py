import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
from fake_useragent import UserAgent
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LogoExtractor:
    def __init__(self, timeout=10, cache_dir='logo_cache', use_selenium=False):
        self.timeout = timeout
        self.ua = UserAgent()
        self.session = requests.Session()
        self.cache = {}
        self.stats = {
            'third_party': 0,
            'metadata': 0,
            'opengraph': 0,
            'heuristic': 0,
            'common_paths': 0,
            'failed': 0
        }
    
    def _get_headers(self):
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
    
    def _normalize_url(self, url):
        if not url.startswith(('http://', 'https://')):
            return f'https://{url}'
        return url
    
    def extract_logo(self, website_url):
        website_url = self._normalize_url(website_url)
        
        if website_url in self.cache:
            return self.cache[website_url]
        
        result = self._try_services(website_url)
        if result:
            self.stats['third_party'] += 1
            self.cache[website_url] = result
            return result
        
        result = self._try_metadata(website_url)
        if result:
            self.stats['metadata'] += 1
            self.cache[website_url] = result
            return result
        
        result = self._try_opengraph(website_url)
        if result:
            self.stats['opengraph'] += 1
            self.cache[website_url] = result
            return result
        
        result = self._search_page(website_url)
        if result:
            self.stats['heuristic'] += 1
            self.cache[website_url] = result
            return result
        
        result = self._try_common_paths(website_url)
        if result:
            self.stats['common_paths'] += 1
            self.cache[website_url] = result
            return result
        
        self.stats['failed'] += 1
        self.cache[website_url] = None
        return None
    
    def _try_services(self, url):
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path.split('/')[0]
        domain = domain.replace('www.', '')
        
        services = [
            f"https://www.google.com/s2/favicons?domain={domain}&sz=256",
            f"https://logo.clearbit.com/{domain}",
            f"https://icons.duckduckgo.com/ip3/{domain}.ico",
        ]
        
        for svc in services:
            try:
                resp = self.session.head(svc, timeout=5, allow_redirects=True)
                if resp.status_code == 200:
                    if 'image' in resp.headers.get('content-type', '').lower():
                        return svc
            except:
                pass
        return None
    
    def _try_metadata(self, url):
        try:
            soup = self._get_soup(url)
            if not soup:
                return None
            
            priorities = [
                ['apple-touch-icon-precomposed'],
                ['apple-touch-icon'],
                ['icon'],
                ['shortcut icon'],
            ]
            
            for rel_list in priorities:
                tags = soup.find_all('link', rel=lambda r: r and any(x in r for x in rel_list))
                best = None
                best_size = 0
                
                for tag in tags:
                    href = tag.get('href')
                    if not href:
                        continue
                    
                    sizes = tag.get('sizes', '0x0')
                    if sizes and 'x' in str(sizes):
                        try:
                            size = int(str(sizes).split('x')[0])
                            if size > best_size:
                                best_size = size
                                best = tag
                        except:
                            if best is None:
                                best = tag
                    elif best is None:
                        best = tag
                
                if best:
                    href = best.get('href')
                    full = urljoin(url, href)
                    if self._check_url(full):
                        return full
            return None
        except:
            return None
    
    def _try_opengraph(self, url):
        try:
            soup = self._get_soup(url)
            if not soup:
                return None
            
            props = ['og:logo', 'og:image', 'twitter:image']
            for prop in props:
                tag = soup.find('meta', property=prop)
                if not tag:
                    tag = soup.find('meta', attrs={'name': prop})
                
                if tag and tag.get('content'):
                    full = urljoin(url, tag['content'])
                    if self._check_url(full):
                        return full
            return None
        except:
            return None
    
    def _search_page(self, url):
        try:
            soup = self._get_soup(url)
            if not soup:
                return None
            
            keywords = ['logo', 'brand', 'site-logo', 'header-logo']
            header = soup.find(['header', 'nav'])
            if header:
                imgs = header.find_all('img', limit=20)
                for img in imgs:
                    if self._img_looks_like_logo(img, keywords):
                        src = img.get('src') or img.get('data-src')
                        if src:
                            full = urljoin(url, src)
                            if self._check_url(full):
                                return full
            
            for kw in keywords:
                elems = soup.find_all(class_=re.compile(kw, re.I), limit=10)
                for elem in elems:
                    img = elem.find('img')
                    if img and img.get('src'):
                        full = urljoin(url, img['src'])
                        if self._check_url(full):
                            return full
            return None
        except:
            return None
    
    def _img_looks_like_logo(self, img, keywords):
        alt = img.get('alt', '').lower()
        src = img.get('src', '').lower()
        cls = ' '.join(img.get('class', [])).lower()
        text = f"{alt} {src} {cls}"
        return any(kw in text for kw in keywords)
    
    def _try_common_paths(self, url):
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        
        paths = [
            '/logo.png', '/logo.svg', '/assets/logo.png',
            '/images/logo.png', '/static/logo.png',
            '/favicon.ico', '/apple-touch-icon.png',
        ]
        
        for path in paths:
            test_url = urljoin(base, path)
            if self._check_url(test_url):
                return test_url
        return None
    
    def _get_soup(self, url):
        try:
            resp = self.session.get(url, headers=self._get_headers(), 
                                   timeout=self.timeout, allow_redirects=True)
            resp.raise_for_status()
            return BeautifulSoup(resp.content, 'lxml')
        except:
            return None
    
    def _check_url(self, url):
        try:
            resp = self.session.head(url, timeout=5, allow_redirects=True)
            if resp.status_code == 200:
                return 'image' in resp.headers.get('content-type', '').lower()
        except:
            pass
        exts = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico')
        return any(url.lower().endswith(ext) for ext in exts)
    
    def get_statistics(self):
        total = sum(self.stats.values())
        if total == 0:
            return None
        
        result = {}
        for key, value in self.stats.items():
            pct = (value / total) * 100
            result[key] = {'count': value, 'percentage': round(pct, 1)}
        return result
    
    def cleanup(self):
        self.session.close()