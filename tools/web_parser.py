import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import Optional

# Tags that are purely structural/chrome — not article content
_NOISE_TAGS = [
    'script', 'style', 'noscript', 'iframe', 'svg', 'canvas',
    'nav', 'header', 'footer', 'aside', 'form', 'button',
    'meta', 'link', 'head',
]

# CSS class/id fragments that strongly indicate non-content blocks
_NOISE_ATTRS = [
    'nav', 'navbar', 'menu', 'sidebar', 'footer', 'header',
    'cookie', 'banner', 'popup', 'modal', 'overlay', 'ad',
    'advertisement', 'promo', 'social', 'share', 'comment',
    'related', 'recommended', 'newsletter', 'subscribe',
]

_DEFAULT_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/122.0.0.0 Safari/537.36'
    ),
    'Accept': (
        'text/html,application/xhtml+xml,application/xml;'
        'q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8'
    ),
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.google.com/',
}


def _is_noisy_element(tag) -> bool:
    """Return True if a BS4 tag looks like navigation/chrome rather than content."""
    for attr in ('class', 'id'):
        values = tag.get(attr, [])
        if isinstance(values, str):
            values = [values]
        for val in values:
            val_low = val.lower()
            if any(noise in val_low for noise in _NOISE_ATTRS):
                return True
    return False


async def scrape_text(url: str, max_chars: int = 8000) -> Optional[str]:
    """
    Fetch *url* and return clean article text stripped of all scripts,
    styles, navigation, footers and other chrome.

    Returns None on any fetch / parse error.
    Truncates to *max_chars* to keep LLM context manageable.
    """
    try:
        async with httpx.AsyncClient(
            timeout=20.0,
            headers=_DEFAULT_HEADERS,
            follow_redirects=True,
        ) as client:
            res = await client.get(url)
            if res.status_code != 200:
                print(f'[WEB_PARSER] scrape_text: status {res.status_code} for {url}')
                return None

        soup = BeautifulSoup(res.text, 'html.parser')

        # 1. Remove all hard-noise tags unconditionally
        for tag in soup.find_all(_NOISE_TAGS):
            tag.decompose()

        # 2. Remove elements whose class/id looks like navigation chrome
        for tag in soup.find_all(True):
            if _is_noisy_element(tag):
                tag.decompose()

        # 3. Prefer <article> or <main> if present — they are the content zone
        content_root = (
            soup.find('article')
            or soup.find('main')
            or soup.find('div', {'id': 'content'})
            or soup.find('div', {'class': 'content'})
            or soup.body
            or soup
        )

        # 4. Extract text with single-space separator, then clean up whitespace
        raw_text = content_root.get_text(separator=' ', strip=True)

        # Collapse runs of whitespace / blank lines
        import re
        clean = re.sub(r'[ \t]{2,}', ' ', raw_text)
        clean = re.sub(r'\n{3,}', '\n\n', clean)
        clean = clean.strip()

        if not clean:
            return None

        return clean[:max_chars]

    except Exception as e:
        print(f'[WEB_PARSER ERROR] scrape_text({url}): {e}')
        return None


async def extract_images_from_url(url: str, limit: int = 3):
    try:
        async with httpx.AsyncClient(
            timeout=20.0,
            headers=_DEFAULT_HEADERS,
            follow_redirects=True,
        ) as client:
            res = await client.get(url)
            if res.status_code != 200:
                print(f'[WEB_PARSER] Status {res.status_code} for {url}')
                return []

            soup = BeautifulSoup(res.text, 'html.parser')
            images = []
            EXCLUDE = [
                'logo', 'icon', 'avatar', 'button', 'ads', 'badge',
                'app-store', 'google-play', 'social', 'facebook', 'twitter',
                'footer', 'header', 'sidebar', 'pixel', 'tracking',
            ]

            # OpenGraph image first — usually the best representative image
            og_img = soup.find('meta', property='og:image')
            if og_img and og_img.get('content'):
                images.append(urljoin(url, og_img['content']))

            for img in soup.find_all('img'):
                src = (
                    img.get('src')
                    or img.get('data-src')
                    or img.get('srcset')
                    or img.get('data-lazy-src')
                )
                if not src:
                    continue
                if ' ' in src:
                    src = src.strip().split(' ')[0]
                img_url = urljoin(url, src)

                low_url = img_url.lower()
                if any(x in low_url for x in EXCLUDE):
                    continue
                if not low_url.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    continue

                if img_url not in images:
                    images.append(img_url)

                if len(images) >= limit:
                    break

            print(f'[WEB_PARSER] Found {len(images)} images on {url}')
            return images

    except Exception as e:
        print(f'[WEB_PARSER ERROR] {url}: {e}')
        return []


async def get_images_from_multiple_urls(urls: list, total_limit: int = 5):
    all_images = []
    for url in urls[:3]:
        if len(all_images) >= total_limit:
            break
        imgs = await extract_images_from_url(url, limit=2)
        all_images.extend(imgs)
    return list(dict.fromkeys(all_images))[:total_limit]
