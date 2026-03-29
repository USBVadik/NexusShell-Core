import asyncio, os, uuid, subprocess, requests, sys
from telegram import Update
from telegram.ext import ContextTypes
from google.genai import types
from core.brain import client, _on_task_done
from config import GCS_BUCKET, PROJECT_ID

MAX_POLL_ATTEMPTS = 40

def _get_token() -> str:
    return subprocess.check_output(
        ['gcloud', 'auth', 'print-access-token']
    ).decode().strip()

def _extract_model_id(op_name: str) -> str:
    parts = op_name.split('/')
    try:
        idx = parts.index('models')
        return parts[idx + 1]
    except (ValueError, IndexError):
        return 'veo-3.0-generate-001'

async def poll_video_operation(op_name: str, update: Update, context: ContextTypes.DEFAULT_TYPE, status_msg):
    model_id = _extract_model_id(op_name)

    # ✅ ПРАВИЛЬНЫЙ эндпоинт по официальной документации Google
    poll_url = (
        f'https://us-central1-aiplatform.googleapis.com/v1/'
        f'projects/{PROJECT_ID}/locations/us-central1/'
        f'publishers/google/models/{model_id}:fetchPredictOperation'
    )
    poll_body = {'operationName': op_name}

    print(f'[VEO] Polling via fetchPredictOperation: {poll_url}')
    sys.stdout.flush()

    for attempt in range(MAX_POLL_ATTEMPTS):
        await asyncio.sleep(15)
        try:
            def _poll():
                token = _get_token()
                headers = {
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                }
                res = requests.post(poll_url, headers=headers, json=poll_body, timeout=30)
                return res.status_code, res.json()

            status_code, data = await asyncio.to_thread(_poll)
            print(f'[VEO] attempt {attempt+1}: status={status_code}, done={data.get("done")}')
            sys.stdout.flush()

            if status_code != 200:
                print(f'[VEO] Poll error {status_code}: {data}')
                continue

            if not data.get('done', False):
                elapsed = (attempt + 1) * 15
                try: await status_msg.edit_text(f'⏳ Рендерим... {elapsed}s')
                except: pass
                continue

            # Проверяем ошибку
            if 'error' in data:
                err_msg = data['error'].get('message', str(data['error']))
                if 'usage guidelines' in err_msg.lower() or 'safety' in err_msg.lower():
                    await status_msg.edit_text(
                        '🛡 VEO заблокировал контент.\n'
                        'Система безопасности Google считает эту сцену небезопасной.'
                    )
                else:
                    await status_msg.edit_text(f'❌ Ошибка VEO: {err_msg}')
                return

            # ✅ Результат — в response.videos[].gcsUri
            response = data.get('response', {})
            videos = response.get('videos', [])

            if not videos:
                gen_videos = response.get('generatedVideos', [])
                if gen_videos:
                    video_obj = gen_videos[0].get('video', {})
                    uri = video_obj.get('uri') or video_obj.get('gcsUri')
                    if uri: videos = [{'gcsUri': uri}]

            if not videos:
                await status_msg.edit_text('❌ VEO: видео не найдено в ответе.')
                return

            gcs_uri = videos[0].get('gcsUri') or videos[0].get('uri')
            if not gcs_uri:
                await status_msg.edit_text('❌ VEO: нет GCS URI в ответе.')
                return

            v_path = f'/tmp/v_{uuid.uuid4().hex}.mp4'

            # Скачиваем из GCS
            proc = await asyncio.create_subprocess_exec(
                'gcloud', 'storage', 'cp', gcs_uri, v_path,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await proc.communicate()
            
            if os.path.exists(v_path) and os.path.getsize(v_path) > 0:
                with open(v_path, 'rb') as f:
                    await update.message.reply_video(video=f, caption='🎥 Ожило.')
                os.remove(v_path)
                try: await status_msg.delete()
                except: pass
            else:
                await status_msg.edit_text('❌ Файл пустой или не скачался.')
            return

        except Exception as e:
            print(f'[VEO Poll] error: {e}')
            continue

    await status_msg.edit_text('⏰ VEO timeout.')

async def handle_video_generation(update: Update, context: ContextTypes.DEFAULT_TYPE, prompt: str, image_bytes=None, video_bytes=None):
    model_name = 'veo-3.0-generate-001' if (image_bytes or video_bytes) else 'veo-3.1-generate-001'
    status_msg = await update.message.reply_text('🎬 Инициализация рендера...')

    try:
        config = types.GenerateVideosConfig(
            aspect_ratio='16:9',
            number_of_videos=1,
            enhance_prompt=True,
            person_generation='ALLOW_ADULT',
            output_gcs_uri=f'gs://{GCS_BUCKET}/veo_output/'
        )

        kwargs = {'model': model_name, 'prompt': prompt, 'config': config}
        if image_bytes:
            kwargs['image'] = types.Image(image_bytes=bytes(image_bytes), mime_type='image/jpeg')
        elif video_bytes:
            kwargs['video'] = types.Video(video_bytes=bytes(video_bytes), mime_type='video/mp4')

        def _start():
            return client.models.generate_videos(**kwargs)

        operation = await asyncio.to_thread(_start)
        op_name = operation.name if hasattr(operation, 'name') else str(operation)
        
        await status_msg.edit_text('⏳ Рендерим... 0s')
        asyncio.create_task(poll_video_operation(op_name, update, context, status_msg))

    except Exception as e:
        await status_msg.edit_text(f'❌ Ошибка запуска VEO: {str(e)}')
