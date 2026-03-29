import asyncio, os, uuid, time, subprocess, random, io
from PIL import Image
from google.genai import types
from core.brain import client, _on_task_done
from config import FFMPEG_PATH, IMAGE_MODEL_EDIT, LOCATION_GLOBAL

PROMPT_PRESETS = {
    'default': 'Professional photo retouch. Natural skin pores, fine hair, micro-details, sharp 8k focus.',
    'smooth': 'Professional beauty retouch. Smooth skin texture, soften wrinkles, even skin tone. Keep eyes, lips and facial structure sharp. Natural, not plastic.',
    'film': 'Analog film photography. Kodak Portra 400 grain, warm tones, slight vignette, organic color grading, natural skin tones. Cinematic feel.',
    'film_creative': 'Analog film photography with aggressive enhancement. Kodak Portra 400 grain, warm tones, vignette, rich shadows. Enhance micro-details and sharpness like KREA AI upscale.',
    'bw': lambda: random.choice([
        'Black and white photography in style of Peter Lindbergh. Dramatic contrast, raw emotion, cinematic grain.',
        'Black and white photography in style of Helmut Newton. High contrast, bold shadows, fashion editorial.',
        'Black and white photography in style of Henri Cartier-Bresson. Natural light, decisive moment, street grain.',
        'Black and white photography in style of Richard Avedon. Sharp details, strong contrast, clean.',
        'Black and white photography in style of Diane Arbus. Gritty grain, raw documentary style.',
    ]),
    'flash': 'Magazine editorial flash photography. Harsh direct flash on subject, blown highlights, deep dark background. Glossy paparazzi-meets-fashion look.',
}

async def enhance_image(img_path: str, factor: int = 2, mode: str = 'balanced') -> str:
    try:
        # --- ПРОВЕРКА ЛИМИТА ЧЕРЕЗ FFPROBE (без Pillow) ---
        cmd_size = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=s=x:p=0', img_path]
        size_res = subprocess.check_output(cmd_size).decode().strip()
        w, h = map(int, size_res.split('x'))
        
        target_pixels = (w * factor) * (h * factor)
        final_img_path = img_path

        if target_pixels > 16500000:
            print(f'[UPSCALE] Downscaling via FFmpeg...')
            scale_ratio = (16500000 / (factor**2 * w * h))**0.5
            new_w, new_h = int(w * scale_ratio), int(h * scale_ratio)
            tmp_resized = f'/tmp/res_{uuid.uuid4().hex}.jpg'
            subprocess.run([FFMPEG_PATH, '-y', '-i', img_path, '-vf', f'scale={new_w}:{new_h}', tmp_resized], capture_output=True)
            final_img_path = tmp_resized

        with open(final_img_path, 'rb') as f:
            data = f.read()

        # ШАГ 1: UPSCALE
        def _step1():
            image = types.Image(image_bytes=bytes(data), mime_type='image/jpeg')
            str_factor = f'x{factor}' if factor in [2, 4] else 'x2'
            res = client.models.upscale_image(
                model='imagen-4.0-upscale-preview',
                image=image,
                upscale_factor=str_factor,
                config=types.UpscaleImageConfig(outputMimeType='image/jpeg', outputCompressionQuality=95)
            )
            return res.generated_images[0].image.image_bytes if res.generated_images else None

        upscaled_data = await asyncio.to_thread(_step1)
        if not upscaled_data: return 'FAILED_STEP_1'

        # ШАГ 2: GENERATIVE ENHANCE
        if mode in ['creative', 'bw', 'smooth', 'film', 'film_creative', 'flash']:
            from google.genai import Client
            project = os.environ.get('GCLOUD_PROJECT', 'usbtest-490122')
            edit_client = Client(vertexai=True, project=project, location=LOCATION_GLOBAL)
            
            p_text = PROMPT_PRESETS['bw']() if mode == 'bw' else PROMPT_PRESETS.get(mode, PROMPT_PRESETS['default'])
            
            res = await edit_client.aio.models.generate_content(
                model=IMAGE_MODEL_EDIT,
                contents=[
                    types.Content(role="user", parts=[
                        types.Part(text=p_text),
                        types.Part.from_bytes(data=upscaled_data, mime_type='image/jpeg'),
                    ])
                ],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"]
                )
            )
            if res.candidates and res.candidates[0].content.parts:
                for part in res.candidates[0].content.parts:
                    if part.inline_data:
                        upscaled_data = part.inline_data.data
                        if mode == 'bw':
                            img = Image.open(io.BytesIO(upscaled_data))
                            img = img.convert('RGB')
                            buf = io.BytesIO()
                            img.save(buf, format='JPEG')
                            upscaled_data = buf.getvalue()
                        break

        out_path = f'/tmp/up_{uuid.uuid4().hex}.jpg'
        with open(out_path, 'wb') as f: f.write(upscaled_data)
        
        if final_img_path != img_path: os.remove(final_img_path)
        return out_path
        
    except Exception as e:
        return f'EXCEPTION_{str(e)}'
