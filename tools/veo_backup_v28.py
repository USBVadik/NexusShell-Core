import asyncio, os, time, subprocess, sys
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes
from google.genai import types
from core.brain import client
from config import GCS_BUCKET, FFMPEG_PATH

async def poll_video_operation(operation, update: Update, context: ContextTypes.DEFAULT_TYPE, status_msg):
    op_name = operation.name if hasattr(operation, 'name') else str(operation)
    print(f"[VEO] Polling for: {op_name}")
    sys.stdout.flush()
    current_op = operation if isinstance(operation, types.GenerateVideosOperation) else types.GenerateVideosOperation(name=op_name)
    while True:
        await asyncio.sleep(15)
        try:
            current_op = await client.aio.operations.get(current_op)
            if current_op.done:
                if current_op.error:
                    await status_msg.edit_text(f"❌ Ошибка VEO: {current_op.error}")
                    return
                try:
                    video_result = current_op.response.generated_videos[0].video
                    v_path = f"/tmp/v_{int(time.time())}.mp4"
                    if hasattr(video_result, 'video_bytes') and video_result.video_bytes:
                        with open(v_path, 'wb') as f: f.write(video_result.video_bytes)
                    elif hasattr(video_result, 'uri') and video_result.uri:
                        subprocess.run(["gcloud", "storage", "cp", video_result.uri, v_path], capture_output=True)
                    if os.path.exists(v_path):
                        await update.message.reply_video(video=open(v_path, 'rb'), caption="🎥 Стилизация v2.0. Надеюсь, теперь не кринж.")
                        os.remove(v_path)
                        await status_msg.delete()
                        if hasattr(video_result, 'uri') and video_result.uri:
                            subprocess.run(["gcloud", "storage", "rm", video_result.uri], capture_output=True)
                        return
                except: pass
                return
        except: continue

async def handle_video_generation(update: Update, context: ContextTypes.DEFAULT_TYPE, prompt: str, image_bytes=None, video_bytes=None):
    # Try 3.1 Fast for potentially more aggressive styling
    model_name = 'veo-3.1-generate-001'
    status_msg_text = "🎬 Инициализация рендера..."
    
    # HARDCORE STYLING PROMPT
    if video_bytes:
        status_msg_text = "🎬 Глубокая переработка стиля (Full Style Transfer)..."
        prompt = f"Full artistic video-to-video style transfer into {prompt}. Recreate every frame in this style. High quality, cinematic, consistent. No overlays."

    status_msg = await update.message.reply_text(status_msg_text)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.RECORD_VIDEO)
    
    try:
        if video_bytes:
            orig_tmp = f"/tmp/orig_{int(time.time())}.mp4"
            conv_tmp = f"/tmp/conv_{int(time.time())}.mp4"
            with open(orig_tmp, 'wb') as f: f.write(video_bytes)
            vf_filter = "fps=24,scale=w='if(gte(iw,ih),1280,720)':h='if(gte(iw,ih),720,1280)':force_original_aspect_ratio=decrease,pad=w='if(gte(iw,ih),1280,720)':h='if(gte(iw,ih),720,1280)':x=(ow-iw)/2:y=(oh-ih)/2"
            subprocess.run([FFMPEG_PATH, '-y', '-i', orig_tmp, '-vf', vf_filter, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', conv_tmp], capture_output=True)
            if os.path.exists(conv_tmp):
                with open(conv_tmp, 'rb') as f: video_bytes = f.read()
                os.remove(conv_tmp); os.remove(orig_tmp)

        gcs_output_uri = f"gs://{GCS_BUCKET}/output_{int(time.time())}.mp4"
        v_config = types.GenerateVideosConfig(person_generation='ALLOW_ADULT', output_gcs_uri=gcs_output_uri)
        kwargs = {'model': model_name, 'prompt': prompt, 'config': v_config}
        if image_bytes: kwargs['image'] = {'image_bytes': bytes(image_bytes), 'mime_type': 'image/jpeg'}
        elif video_bytes: kwargs['video'] = {'video_bytes': bytes(video_bytes), 'mime_type': 'video/mp4'}
            
        op = await client.aio.models.generate_videos(**kwargs)
        await status_msg.edit_text("⏳ Запустил хардкор-режим стилизации. Рендерим заново...")
        asyncio.create_task(poll_video_operation(op, update, context, status_msg))
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка: {str(e)}")
