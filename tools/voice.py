import os, uuid, subprocess, asyncio
from config import STABLE_MODEL, FFMPEG_PATH
from core.brain import client
from google.genai import types

async def transcribe_audio(audio_bytes: bytes) -> str:
    """Транскрибация аудио через Gemini с анализом эмоций"""
    try:
        from core.logger import media_logger
        mime_types = ['audio/ogg', 'audio/mpeg', 'audio/mp4', 'audio/wav']
        for mime in mime_types:
            try:
                res = await client.aio.models.generate_content(
                    model=STABLE_MODEL,
                    contents=[
                        types.Part.from_bytes(data=audio_bytes, mime_type=mime),
                        types.Part.from_text(text='Transcribe this Russian audio message.')
                    ]
                )
                if res.text: return res.text
            except: continue
        return '[Не удалось распознать аудио]'
    except Exception as e:
        return f'[Ошибка: {e}]'

async def generate_sarcastic_voice(text: str) -> str:
    """
    Генерация голоса через Gemini 2.5 Flash Lite TTS (Puck)
    Обработка RAW PCM S16LE
    """
    from core.logger import media_logger
    text = text[:1500]
    try:
        model_id = 'gemini-2.5-flash-lite-preview-tts'
        media_logger.info(f'[TTS] Gemini Puck started for {len(text)} chars')
        
        res = await client.aio.models.generate_content(
            model=model_id,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=['AUDIO'],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name='Puck')
                    )
                )
            )
        )
        
        if res.candidates and res.candidates[0].content.parts:
            part = res.candidates[0].content.parts[0]
            if hasattr(part, 'inline_data') and part.inline_data:
                data = part.inline_data.data
                p_raw = f'/tmp/v_raw_{uuid.uuid4().hex}.pcm'
                with open(p_raw, 'wb') as f: f.write(data)
                
                # Явно указываем параметры PCM для FFmpeg
                out = f'/tmp/voice_{uuid.uuid4().hex}.ogg'
                cmd = [
                    FFMPEG_PATH, '-y',
                    '-f', 's16le', '-ar', '24000', '-ac', '1',  # Входные параметры (RAW PCM)
                    '-i', p_raw, 
                    '-c:a', 'libopus', '-b:a', '32k', 
                    out
                ]
                proc = subprocess.run(cmd, capture_output=True, text=True)
                
                if os.path.exists(out) and os.path.getsize(out) > 500:
                    media_logger.info(f'✅ [TTS] OGG SUCCESS: {out} ({os.path.getsize(out)} bytes)')
                    if os.path.exists(p_raw): os.remove(p_raw)
                    return out
                else:
                    media_logger.error(f'[TTS] FFmpeg failed. Stderr: {proc.stderr}')
                    return None
        
        media_logger.warning('[TTS] No audio in response')
    except Exception as e:
        media_logger.error(f'[TTS] Gemini Puck fatal error: {e}')
    
    # Fallback на Edge-TTS
    try:
        import edge_tts
        media_logger.info('[TTS] Edge-TTS Fallback')
        out = f'/tmp/voice_{uuid.uuid4().hex}.mp3'
        communicate = edge_tts.Communicate(text, 'ru-RU-DmitryNeural')
        await communicate.save(out)
        return out
    except Exception as e:
        media_logger.error(f'[TTS] Fallback failed: {e}')
    return None
