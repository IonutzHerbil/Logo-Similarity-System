import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed

def extract_logo(domain):
    url = f"https://{domain}"
    try:
        response = requests.get(url, timeout=10, allow_redirects=True)
        soup = BeautifulSoup(response.content, 'html.parser')
        base = response.url
        
        for img in soup.find_all('img'):
            classes = ' '.join(img.get('class', [])).lower()
            if 'logo' in classes:
                src = img.get('src')
                if src:
                    return urljoin(base, src)
        
        return None
    except:
        return None

df = pd.read_parquet('logos.snappy.parquet')
domains = df['domain'].tolist()

logos = {}
with ThreadPoolExecutor(max_workers=20) as executor:
    future_to_domain = {executor.submit(extract_logo, domain): domain for domain in domains}
    
    for i, future in enumerate(as_completed(future_to_domain), 1):
        domain = future_to_domain[future]
        print(f"[{i}/{len(domains)}] {domain[:50]}...", end='\r')
        
        logo_url = future.result()
        if logo_url:
            logos[domain] = logo_url

print(f"\nExtracted: {len(logos)}/{len(domains)} = {len(logos)/len(domains)*100:.1f}%")