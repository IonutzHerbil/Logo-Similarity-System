import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
from typing import Optional, List, Dict
import time
from fake_useragent import UserAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LogoExtractor:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.ua = UserAgent()
        self.session = requests.Session()
        
    def _get_headers(self) -> Dict[str, str]:
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    def _normalize_url(self, url: str) -> str:
        if not url.startswith(('http://', 'https://')):
            return f'https://{url}'
        return url
    
    def _is_valid_image_url(self, url: str) -> bool:
        if not url:
            return False
        image_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico')
        parsed = urlparse(url.lower())
        return any(parsed.path.endswith(ext) for ext in image_extensions)
    
    def extract_logo(self, website_url: str) -> Optional[str]:
        website_url = self._normalize_url(website_url)
        
        logo_url = self._extract_from_metadata(website_url)
        if logo_url:
            logger.info(f"Logo found via metadata for {website_url}")
            return logo_url
        
        logo_url = self._extract_from_opengraph(website_url)
        if logo_url:
            logger.info(f"Logo found via Open Graph for {website_url}")
            return logo_url
        
        logo_url = self._extract_from_heuristics(website_url)
        if logo_url:
            logger.info(f"Logo found via heuristics for {website_url}")
            return logo_url
        
        logo_url = self._extract_from_common_paths(website_url)
        if logo_url:
            logger.info(f"Logo found via common paths for {website_url}")
            return logo_url
        
        logger.warning(f"No logo found for {website_url}")
        return None
    
    def _extract_from_metadata(self, url: str) -> Optional[str]:
        try:
            soup = self._get_soup(url)
            if not soup:
                return None
            
            link_tags = soup.find_all('link', rel=True)
            for tag in link_tags:
                rel = tag.get('rel', [])
                if isinstance(rel, str):
                    rel = [rel]
                
                if any(r in ['apple-touch-icon', 'icon', 'shortcut icon'] for r in rel):
                    href = tag.get('href')
                    if href:
                        full_url = urljoin(url, href)
                        if self._is_valid_image_url(full_url):
                            return full_url
            
            return None
        except Exception as e:
            logger.debug(f"Metadata extraction failed for {url}: {e}")
            return None
    
    def _extract_from_opengraph(self, url: str) -> Optional[str]:
        try:
            soup = self._get_soup(url)
            if not soup:
                return None
            
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                full_url = urljoin(url, og_image['content'])
                if self._is_valid_image_url(full_url):
                    return full_url
            
            og_logo = soup.find('meta', property='og:logo')
            if og_logo and og_logo.get('content'):
                full_url = urljoin(url, og_logo['content'])
                if self._is_valid_image_url(full_url):
                    return full_url
            
            return None
        except Exception as e:
            logger.debug(f"Open Graph extraction failed for {url}: {e}")
            return None
    
    def _extract_from_heuristics(self, url: str) -> Optional[str]:
        try:
            soup = self._get_soup(url)
            if not soup:
                return None
            
            logo_keywords = ['logo', 'brand', 'site-logo', 'header-logo', 'company-logo']
            
            header = soup.find(['header', 'nav'])
            if header:
                img = self._find_logo_in_element(header, logo_keywords, url)
                if img:
                    return img
            
            for keyword in logo_keywords:
                elements = soup.find_all(class_=lambda x: x and keyword in x.lower())
                for elem in elements:
                    img = self._find_logo_in_element(elem, logo_keywords, url)
                    if img:
                        return img
                
                elements = soup.find_all(id=lambda x: x and keyword in x.lower())
                for elem in elements:
                    img = self._find_logo_in_element(elem, logo_keywords, url)
                    if img:
                        return img
            
            all_imgs = soup.find_all('img')
            for img in all_imgs[:20]:
                alt = img.get('alt', '').lower()
                src = img.get('src', '').lower()
                
                if any(keyword in alt or keyword in src for keyword in logo_keywords):
                    src_url = img.get('src')
                    if src_url:
                        full_url = urljoin(url, src_url)
                        if self._is_valid_image_url(full_url):
                            return full_url
            
            return None
        except Exception as e:
            logger.debug(f"Heuristic extraction failed for {url}: {e}")
            return None
    
    def _find_logo_in_element(self, element, keywords: List[str], base_url: str) -> Optional[str]:
        img = element.find('img')
        if img and img.get('src'):
            full_url = urljoin(base_url, img['src'])
            if self._is_valid_image_url(full_url):
                return full_url
        
        if element.get('style'):
            style = element['style']
            if 'background-image' in style or 'background:' in style:
                import re
                urls = re.findall(r'url\([\'"]?([^\'"()]+)[\'"]?\)', style)
                if urls:
                    full_url = urljoin(base_url, urls[0])
                    if self._is_valid_image_url(full_url):
                        return full_url
        
        return None
    
    def _extract_from_common_paths(self, url: str) -> Optional[str]:
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        common_paths = [
            '/favicon.ico',
            '/logo.png',
            '/logo.svg',
            '/images/logo.png',
            '/assets/logo.png',
            '/static/logo.png',
            '/img/logo.png',
        ]
        
        for path in common_paths:
            test_url = urljoin(base_url, path)
            if self._url_exists(test_url):
                return test_url
        
        return None
    
    def _get_soup(self, url: str) -> Optional[BeautifulSoup]:
        try:
            response = self.session.get(
                url, 
                headers=self._get_headers(), 
                timeout=self.timeout,
                allow_redirects=True
            )
            response.raise_for_status()
            return BeautifulSoup(response.content, 'lxml')
        except Exception as e:
            logger.debug(f"Failed to fetch {url}: {e}")
            return None
    
    def _url_exists(self, url: str) -> bool:
        try:
            response = self.session.head(url, timeout=5, allow_redirects=True)
            return response.status_code == 200
        except:
            return False
