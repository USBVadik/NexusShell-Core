import asyncio
import os
import uuid
import sys
import subprocess
from typing import Optional

import httpx
from telegram import Update
from telegram.ext import ContextTypes
from google.genai import types
from google.auth import default, transport
from google.auth.transport.requests import Request

from core.brain import client, _on_task_done
from config import GCS_BUCKET, PROJECT_ID

MAX_POLL_ATTEMPTS = 45

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def _get_token() -> str:
    try:
        creds, _ = default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
        creds.refresh(Request())
        return creds.token
    except Exception as e:
        print(f'[USBAGENT VEO Auth Error] {e}')
        try:
            return subprocess.check_output(['gcloud', 'auth', 'print-access-token']).decode().strip()
        except Exception:
            return ''


def _extract_model_id(op_name: str) -> str:
    parts = op_name.split('/')
    try:
        idx = parts.index('models')
        return parts[idx + 1]
    except (ValueError, IndexError):
        return 'veo-3.0-generate-001'


# ---------------------------------------------------------------------------
# Polling
# ---------------------------------------------------------------------------

async def poll_video_operation(
    op_name: str,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    status_msg,
):
    model_id = _extract_model_id(op_name)
    poll_url = (
        f'https://us-central1-aiplatform.googleapis.com/v1/'
        f'projects/{PROJECT_ID}/locations/us-central1/'
        f'publishers/google/models/{model_id}:fetchPredictOperation'
    )
    poll_body = {'operationName': op_name}

    print(f'[USBAGENT VEO v4.4] polling {op_name}')
    sys.stdout.flush()

    for attempt in range(MAX_POLL_ATTEMPTS):
        await asyncio.sleep(15)
        try:
            async def _poll() -> tuple[int, dict | str]:
                token = _get_token()
                if not token:
                    return 500, {'error': 'Auth token empty'}
                headers = {
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json',
                }
                async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as http:
                    res = await http.post(poll_url, headers=headers, json=poll_body)
                try:
                    return res.status_code, res.json()
                except Exception:
                    return res.status_code, res.text

            status_code, data = await _poll()

            is_done = False
            if isinstance(data, dict):
                is_done = data.get('done', False)
                print(f'[USBAGENT VEO v4.4] att {attempt + 1}: {status_code}, done={is_done}')
            else:
                print(f'[USBAGENT VEO v4.4] att {attempt + 1}: {status_code}, HTML/Raw')

            sys.stdout.flush()

            if status_code != 200:
                continue

            if not is_done:
                elapsed = (attempt + 1) * 15
                try:
                    await status_msg.edit_text(f'⏳ USBAGENT VEO — рендерим... {elapsed}s')
                except Exception:
                    pass
                continue

            # Error in response
            if isinstance(data, dict) and 'error' in data:
                e_obj = data['error']
                msg = e_obj.get('message', str(e_obj)) if isinstance(e_obj, dict) else str(e_obj)
                await status_msg.edit_text(f'❌ USBAGENT VEO Error: {msg}')
                return

            response = data.get('response', {})
            videos = response.get('videos', [])
            if not videos:
                gen_videos = response.get('generatedVideos', [])
                if gen_videos:
                    v_obj = gen_videos[0].get('video', {})
                    uri = v_obj.get('uri') or v_obj.get('gcsUri')
                    if uri:
                        videos = [{'gcsUri': uri}]

            if not videos:
                await status_msg.edit_text('❌ USBAGENT VEO: видео не найдено.')
                return

            gcs_uri = videos[0].get('gcsUri') or videos[0].get('uri')
            v_path = f'/tmp/v_{uuid.uuid4().hex}.mp4'

            proc = await asyncio.create_subprocess_exec(
                'gcloud', 'storage', 'cp', gcs_uri, v_path,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

            if os.path.exists(v_path) and os.path.getsize(v_path) > 0:
                with open(v_path, 'rb') as f:
                    await update.message.reply_video(video=f, caption='🎥 USBAGENT VEO — готово (v4.4)')
                os.remove(v_path)
                try:
                    await status_msg.delete()
                except Exception:
                    pass
            else:
                await status_msg.edit_text('❌ USBAGENT VEO: ошибка GCS Transfer.')
            return

        except Exception as e:
            print(f'[USBAGENT VEO v4.4] Error: {e}')
            continue

    await status_msg.edit_text('⏰ USBAGENT VEO: timeout.')


# ---------------------------------------------------------------------------
# Video generation
# ---------------------------------------------------------------------------

async def handle_video_generation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    prompt: str,
    image_bytes: Optional[bytes] = None,
    video_bytes: Optional[bytes] = None,
    start_image_bytes: Optional[bytes] = None,
    end_image_bytes: Optional[bytes] = None,
):
    """
    USBAGENT NexusShell Core — VEO Video Generation.

    Modes:
    - Text-to-video:            prompt only
    - Image-to-video:           prompt + image_bytes
    - Video-to-video:           prompt + video_bytes
    - Start/End Frame Control:  prompt + start_image_bytes and/or end_image_bytes

    Start/End Frame Control and image/video-to-video always use
    veo-3.0-generate-001 (full quality). Text-to-video uses the fast variant.
    """
    has_frame_control = start_image_bytes is not None or end_image_bytes is not None
    has_reference_media = image_bytes is not None or video_bytes is not None

    # Model selection: full model required for any media input
    if has_frame_control or has_reference_media:
        model_name = 'veo-3.0-generate-001'
    else:
        model_name = 'veo-3.0-fast-generate-001'

    # Status message
    if has_frame_control:
        mode_label = '🎬 USBAGENT VEO — Start/End Frame Control'
        if start_image_bytes and end_image_bytes:
            mode_label += ' (start + end)'
        elif start_image_bytes:
            mode_label += ' (start frame)'
        else:
            mode_label += ' (end frame)'
    elif image_bytes:
        mode_label = '🖼 USBAGENT VEO — Image-to-Video'
    elif video_bytes:
        mode_label = '🎞 USBAGENT VEO — Video-to-Video'
    else:
        mode_label = '✍️ USBAGENT VEO — Text-to-Video'

    status_msg = await update.message.reply_text(
        f'{mode_label}\n🎬 Инициализация рендера NexusShell Core...'
    )

    try:
        # Build config
        config_kwargs: dict = dict(
            aspect_ratio='16:9',
            number_of_videos=1,
            enhance_prompt=True,
            person_generation='ALLOW_ADULT',
            output_gcs_uri=f'gs://{GCS_BUCKET}/veo_output/',
        )

        # Start/End Frame Control
        if start_image_bytes is not None:
            config_kwargs['start_image'] = types.Image(
                image_bytes=bytes(start_image_bytes),
                mime_type='image/jpeg',
            )
        if end_image_bytes is not None:
            config_kwargs['end_image'] = types.Image(
                image_bytes=bytes(end_image_bytes),
                mime_type='image/jpeg',
            )

        config = types.GenerateVideosConfig(**config_kwargs)

        # Build call kwargs
        kwargs: dict = {
            'model': model_name,
            'prompt': prompt,
            'config': config,
        }

        # Reference media (image-to-video / video-to-video)
        # Only used when NOT doing frame control — they are mutually exclusive
        if not has_frame_control:
            if image_bytes is not None:
                kwargs['image'] = types.Image(
                    image_bytes=bytes(image_bytes),
                    mime_type='image/jpeg',
                )
            elif video_bytes is not None:
                kwargs['video'] = types.Video(
                    video_bytes=bytes(video_bytes),
                    mime_type='video/mp4',
                )

        def _start():
            return client.models.generate_videos(**kwargs)

        operation = await asyncio.to_thread(_start)
        op_name = operation.name if hasattr(operation, 'name') else str(operation)

        await status_msg.edit_text(f'{mode_label}\n⏳ NexusShell Core рендерит... 0s')

        t = asyncio.create_task(
            poll_video_operation(op_name, update, context, status_msg)
        )
        t.add_done_callback(lambda fut: _on_task_done(fut, 'USBAGENT VEO Poll'))

    except Exception as e:
        await status_msg.edit_text(f'❌ USBAGENT VEO Ошибка: {str(e)}')
