import asyncio, os, time, requests, json, re, uuid, aiohttp
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
from google.genai.types import RawReferenceImage, MaskReferenceImage, MaskReferenceConfig, EditImageConfig
from google.cloud import vision
from core.brain import client
from core.logger import image_logger
from config import PROJECT_ID, LOCATION, STABLE_MODEL, IMAGE_MODEL, IMAGE_MODEL_EDIT, LOCATION_GLOBAL, IMAGE_MODEL_IMAGEN, IMAGE_MODEL_IMAGEN_FAST, IMAGE_MODEL_IMAGEN_ULTRA

# ✅ FIX: Явно указываем проект для Vision API
vision_client = vision.ImageAnnotatorClient(client_options={'quota_project_id': PROJECT_ID})

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

async def process_image_edit(img_bytes, prompt, mode='edit', aspect='1:1', imagen_model=IMAGE_MODEL_IMAGEN) -> str | None:
    """
    Обработка изображений: генерация (Imagen 4), редактирование/стиль (Gemini Flash Image)
    Возвращает путь к файлу или код ошибки: 'FILTERED', 'RATE_LIMIT', 'ERROR'
    """
    try:
        from google.genai import Client
        project = os.environ.get('GCLOUD_PROJECT', 'usbtest-490122')
        
        image_logger.info(f"Image processing: mode={mode}, aspect={aspect}, model={imagen_model}")
        image_logger.debug(f"Prompt: {prompt[:100]}")
        
        # mode: 'generate' (Imagen 4.0), 'style' (Gemini Flash Image Identity), 'edit' (Gemini Flash Image Standard)
        model_name = imagen_model if mode == 'generate' else IMAGE_MODEL_EDIT
        is_imagen = mode == 'generate'
        current_location = LOCATION if is_imagen else LOCATION_GLOBAL
        
        edit_client = Client(vertexai=True, project=project, location=current_location)

        if mode == 'generate':
            # Imagen path: text-to-image (Imagen 4.0)
            res = await edit_client.aio.models.generate_images(
                model=model_name,
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    aspect_ratio=aspect,
                    number_of_images=1
                )
            )
            if res.generated_images:
                path = f'/tmp/gen_{uuid.uuid4().hex}.png'
                with open(path, 'wb') as f:
                    f.write(res.generated_images[0].image.image_bytes)
                image_logger.info(f"Image generated: {path}")
                return path
        else:
            # Gemini path: image-to-image (Gemini Flash Image)
            parts = []
            if img_bytes:
                parts.append(types.Part.from_bytes(data=bytes(img_bytes), mime_type='image/jpeg'))
            
            final_prompt = prompt
            if mode == 'style':
                final_prompt = (
                    f"Redraw the subject from this photo preserving exact facial features, "
                    f"hair, body proportions and identity. {prompt}. "
                    "High quality, subject consistency. Output only the final image."
                )
            
            parts.append(types.Part.from_text(text=final_prompt))

            res = await edit_client.aio.models.generate_content(
                model=model_name,
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                    image_config={'aspect_ratio': aspect}
                )
            )
            if res.candidates and res.candidates[0].content.parts:
                for part in res.candidates[0].content.parts:
                    if part.inline_data:
                        path = f'/tmp/edit_{uuid.uuid4().hex}.png'
                        with open(path, 'wb') as f:
                            f.write(part.inline_data.data)
                        image_logger.info(f"Image edited: {path}")
                        return path
                        
    except Exception as e:
        error_str = str(e)
        if '429' in error_str:
            image_logger.warning("Rate limit hit (429)")
            return 'RATE_LIMIT'
        if 'SAFETY' in error_str.upper():
            image_logger.warning("Content filtered by safety")
            return 'FILTERED'
        image_logger.error(f"Image processing error: {e}", exc_info=True)
        
    return 'ERROR'

async def extract_text_from_image(img_bytes) -> str:
    """Извлечение текста из изображения через Gemini OCR"""
    try:
        res = await client.aio.models.generate_content(
            model=STABLE_MODEL,
            contents=[types.Part.from_bytes(data=bytes(img_bytes), mime_type='image/jpeg'), "OCR. Extract all text."]
        )
        text = res.text or 'Текст не найден.'
        image_logger.info(f"OCR extracted {len(text)} characters")
        return text
    except Exception as e:
        image_logger.error(f"OCR error: {e}", exc_info=True)
        return 'Ошибка OCR.'

async def outpaint_image(img_bytes: bytes, prompt: str = '', aspect: str = '16:9') -> str:
    """Расширение изображения (outpaint) через Imagen"""
    try:
        image_logger.info(f"Outpaint: aspect={aspect}")
        from google.genai import Client
        from google.genai.types import RawReferenceImage, MaskReferenceImage, MaskReferenceConfig, EditImageConfig
        import io
        from PIL import Image as PILImage

        edit_client = Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

        # Создаём маску: расширяем canvas до нужного соотношения сторон
        src = PILImage.open(io.BytesIO(img_bytes)).convert('RGB')
        w, h = src.size
        if aspect == '16:9':
            new_w, new_h = max(w, int(h * 16 / 9)), max(h, int(w * 9 / 16))
        elif aspect == '9:16':
            new_w, new_h = max(w, int(h * 9 / 16)), max(h, int(w * 16 / 9))
        else:
            new_w, new_h = max(w, h), max(w, h)

        canvas = PILImage.new('RGB', (new_w, new_h), (0, 0, 0))
        canvas.paste(src, ((new_w - w) // 2, (new_h - h) // 2))
        mask = PILImage.new('L', (new_w, new_h), 255)
        mask.paste(PILImage.new('L', (w, h), 0), ((new_w - w) // 2, (new_h - h) // 2))

        buf_img, buf_mask = io.BytesIO(), io.BytesIO()
        canvas.save(buf_img, format='JPEG')
        mask.save(buf_mask, format='PNG')

        from google.genai import types
        raw_ref = RawReferenceImage(reference_id=0,
            reference_image=types.Image(image_bytes=buf_img.getvalue()))
        mask_ref = MaskReferenceImage(reference_id=1,
            reference_image=types.Image(image_bytes=buf_mask.getvalue()),
            config=MaskReferenceConfig(mask_mode='MASK_MODE_USER_PROVIDED', mask_dilation=0.03))

        res = await edit_client.aio.models.edit_image(
            model='imagen-3.0-capability-002',
            prompt=prompt or 'Extend the scenery naturally, keep same style and lighting',
            reference_images=[raw_ref, mask_ref],
            config=EditImageConfig(edit_mode='EDIT_MODE_OUTPAINT', number_of_images=1)
        )
        data = res.generated_images[0].image.image_bytes
        out = f'/tmp/out_{uuid.uuid4().hex}.jpg'
        with open(out, 'wb') as f:
            f.write(data)
        image_logger.info(f"Outpaint completed: {out}")
        return out
        
    except Exception as e:
        image_logger.error(f"Outpaint error: {e}", exc_info=True)
        return None

async def retouch_face_pro(img_bytes, mode='pro') -> str:
    """Профессиональная ретушь лица"""
    try:
        image_logger.info(f"Retouch face: mode={mode}")
        from google.genai import Client
        edit_client = Client(vertexai=True, project=PROJECT_ID, location=LOCATION_GLOBAL)
        
        if mode == 'smooth':
            p_text = "Beauty skin retouching. Aggressively smooth skin: eliminate all visible pores, blemishes, redness, uneven patches. Apply high-end airbrush finish. Keep eyes sharp, lips defined, facial structure unchanged. Result: porcelain skin like Vogue magazine cover. Do NOT alter face shape, lighting or background. Output only the retouched image."
        else:
            p_text = "High-End Professional Photo Enhancement. Sharp details, natural skin pores, enhanced lighting, 8k resolution, deep focus, realistic textures. Improve contrast and clarity."
            
        parts = [types.Part.from_bytes(data=bytes(img_bytes), mime_type='image/jpeg')]
        parts.append(types.Part.from_text(text=f"{p_text} Output only the retouched image."))

        res = await edit_client.aio.models.generate_content(
            model=IMAGE_MODEL_EDIT,
            contents=[types.Content(role='user', parts=parts)],
            config=types.GenerateContentConfig(response_modalities=['IMAGE', 'TEXT'])
        )
        if res.candidates and res.candidates[0].content.parts:
            for part in res.candidates[0].content.parts:
                if part.inline_data:
                    path = f'/tmp/retouch_{uuid.uuid4().hex}.png'
                    with open(path, 'wb') as f:
                        f.write(part.inline_data.data)
                    image_logger.info(f"Retouch completed: {path}")
                    return path
                    
    except Exception as e:
        image_logger.error(f"Retouch error: {e}", exc_info=True)
        
    return None

async def generate_via_flash(prompt: str) -> str | None:
    """Генерация через Gemini 3.1 Flash Image"""
    try:
        image_logger.info(f"Flash generation: {prompt[:80]}")
        from google.genai import Client, types
        from config import PROJECT_ID, LOCATION_GLOBAL, IMAGE_MODEL_EDIT
        import uuid
        flash_client = Client(vertexai=True, project=PROJECT_ID, location=LOCATION_GLOBAL)
        res = await flash_client.aio.models.generate_content(
            model=IMAGE_MODEL_EDIT,
            contents=prompt,
            config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"])
        )
        if res.candidates and res.candidates[0].content.parts:
            for part in res.candidates[0].content.parts:
                if part.inline_data:
                    path = f"/tmp/flash_{uuid.uuid4().hex}.png"
                    with open(path, 'wb') as f:
                        f.write(part.inline_data.data)
                    image_logger.info(f"Flash generated: {path}")
                    return path
                    
    except Exception as e:
        image_logger.error(f"Flash generation error: {e}", exc_info=True)
        
    return None
