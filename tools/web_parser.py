import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin

async def extract_images_from_url(url: str, limit=3):
    try:
        # Максимально человеческие заголовки
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.google.com/'
        }
        async with httpx.AsyncClient(timeout=20.0, headers=headers, follow_redirects=True) as client:
            res = await client.get(url)
            if res.status_code != 200: 
                print(f'[WEB_PARSER] Status {res.status_code} for {url}')
                return []
            
            soup = BeautifulSoup(res.text, 'html.parser')
            images = []
            EXCLUDE = ['logo', 'icon', 'avatar', 'button', 'ads', 'badge', 'app-store', 'google-play', 'social', 'facebook', 'twitter', 'footer', 'header', 'sidebar', 'pixel', 'tracking']
            
            # Сначала ищем в OpenGraph (там обычно лучшее фото статьи)
            og_img = soup.find('meta', property='og:image')
            if og_img and og_img.get('content'):
                images.append(urljoin(url, og_img['content']))

            for img in soup.find_all('img'):
                src = img.get('src') or img.get('data-src') or img.get('srcset') or img.get('data-lazy-src')
                if not src: continue
                if ' ' in src: src = src.strip().split(' ')[0]
                img_url = urljoin(url, src)
                
                low_url = img_url.lower()
                if any(x in low_url for x in EXCLUDE): continue
                if not low_url.endswith(('.jpg', '.jpeg', '.png', '.webp')): continue
                
                if img_url not in images:
                    images.append(img_url)
                
                if len(images) >= limit: break
            
            print(f'[WEB_PARSER] Found {len(images)} images on {url}')
            return images
    except Exception as e:
        print(f'[WEB_PARSER ERROR] {url}: {e}')
        return []

async def get_images_from_multiple_urls(urls: list, total_limit=5):
    all_images = []
    # Берем только первые 3 ссылки, чтобы не ждать вечно
    for url in urls[:3]:
        if len(all_images) >= total_limit: break
        imgs = await extract_images_from_url(url, limit=2)
        all_images.extend(imgs)
    return list(dict.fromkeys(all_images))[:total_limit]
