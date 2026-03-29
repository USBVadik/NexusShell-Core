import asyncio, os, time, requests, json, re, aiohttp
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
from google.cloud import vision
from core.brain import client
from config import PROJECT_ID, LOCATION, STABLE_MODEL

# ✅ FIX: Явно указываем проект для Vision API
vision_client = vision.ImageAnnotatorClient(client_options={"quota_project_id": PROJECT_ID})

async def extract_image_from_page(page_url: str) -> str | None:
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1)'}
        async with aiohttp.ClientSession() as session:
            async with session.get(page_url, timeout=aiohttp.ClientTimeout(total=5), headers=headers) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    og = soup.find('meta', property='og:image')
                    if og and og.get('content'): return og['content']
                    for img in soup.find_all('img'):
                        src = img.get('src')
                        if src and (src.endswith('.jpg') or src.endswith('.png')) and 'http' in src: return src
    except: pass
    return None

async def generate_search_queries(user_query: str) -> list[str]:
    prompt = f'''User wants to find a RECENT real photo: "{user_query}".
Generate 5 precise English search queries for high-quality photography.
IMPORTANT: Prioritize queries with current year (2026), recent events, latest appearances.
Return ONLY the list, one per line.'''
    try:
        res = await client.aio.models.generate_content(model=STABLE_MODEL, contents=prompt)
        return [q.strip() for q in res.text.strip().split('\n') if q.strip()][:5]
    except: return [user_query]

async def grounding_image_search(query: str) -> dict | None:
    try:
        tools = [types.Tool(google_search=types.GoogleSearch())]
        config = types.GenerateContentConfig(tools=tools)
        res = await client.aio.models.generate_content(model=STABLE_MODEL, contents=f"Find recent photo of: {query}", config=config)
        if res.candidates and res.candidates[0].grounding_metadata:
            for chunk in res.candidates[0].grounding_metadata.grounding_chunks:
                if hasattr(chunk, 'web') and chunk.web:
                    page_url = chunk.web.uri
                    title = getattr(chunk.web, 'title', query)
                    img_url = await extract_image_from_page(page_url)
                    if img_url: return {'image_url': img_url, 'title': title}
    except Exception as e: print(f'[SEARCH] Error: {e}')
    return None

def validate_image(image_url: str) -> dict:
    try:
        image = vision.Image(source=vision.ImageSource(image_uri=image_url))
        res = vision_client.annotate_image({'image': image, 'features': [{'type_': vision.Feature.Type.SAFE_SEARCH_DETECTION}]})
        safe = res.safe_search_annotation
        if safe.adult >= 3 or safe.violence >= 3: return {'valid': False}
        return {'valid': True}
    except Exception as e:
        print(f'[VISION] Network skip: {e}')
        return {'valid': True}

async def search_real_photos(queries: list):
    main_query = queries[0] if queries else ''
    smart_queries = await generate_search_queries(main_query)
    for q in smart_queries:
        res = await grounding_image_search(q)
        if res and validate_image(res['image_url'])['valid']: return res
    return None
