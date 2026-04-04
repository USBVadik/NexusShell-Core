import os
import re
import uuid
import hashlib
import subprocess
import asyncio
from config import STABLE_MODEL, FFMPEG_PATH
from core.brain import client
from google.genai import types

# ─── Префиксы, которые нужно удалять перед озвучкой ───────────────────────────
_PREFIX_RE = re.compile(
    r'^(?:озвучь|/voice)\s*:?\s*',
    re.IGNORECASE | re.UNICODE,
)

# ─── Параметры чанкинга ────────────────────────────────────────────────────────
_CHUNK_MAX = 300          # максимальная длина одного чанка (символов)
_TTS_MODEL  = 'gemini-2.5-flash-lite-preview-tts'
_PCM_RATE   = 24000       # Hz, RAW PCM S16LE из Gemini TTS
_PCM_CHANNELS = 1


def _strip_prefix(text: str) -> str:
    """Удаляет команды-префиксы озвучки из начала строки."""
    return _PREFIX_RE.sub('', text).strip()


def _split_sentences(text: str, max_len: int = _CHUNK_MAX) -> list[str]:
    """
    Разбивает текст на чанки не длиннее max_len символов,
    стараясь резать по границам предложений (. ! ? …).
    """
    # Сначала разбиваем по концам предложений
    raw = re.split(r'(?<=[.!?…])\s+', text)
    chunks: list[str] = []
    current = ''

    for sentence in raw:
        sentence = sentence.strip()
        if not sentence:
            continue
        # Если одно предложение само по себе длиннее max_len — режем жёстко
        while len(sentence) > max_len:
            space = sentence.rfind(' ', 0, max_len)
            cut = space if space > 0 else max_len
            piece = sentence[:cut].strip()
            if piece:
                chunks.append(piece)
            sentence = sentence[cut:].strip()

        if len(current) + len(sentence) + 1 <= max_len:
            current = (current + ' ' + sentence).strip() if current else sentence
        else:
            if current:
                chunks.append(current)
            current = sentence

    if current:
        chunks.append(current)

    return [c for c in chunks if c]


async def _generate_pcm_chunk(text: str) -> bytes | None:
    """
    Генерирует RAW PCM S16LE для одного текстового чанка через Gemini Puck TTS.
    Возвращает bytes или None при ошибке.
    """
    try:
        res = await client.aio.models.generate_content(
            model=_TTS_MODEL,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=['AUDIO'],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name='Puck')
                    )
                ),
            ),
        )
        if (
            res.candidates
            and res.candidates[0].content.parts
            and hasattr(res.candidates[0].content.parts[0], 'inline_data')
            and res.candidates[0].content.parts[0].inline_data
        ):
            return res.candidates[0].content.parts[0].inline_data.data
    except Exception:
        pass
    return None


async def transcribe_audio(audio_bytes: bytes) -> str:
    """Транскрибация аудио через Gemini с анализом эмоций."""
    try:
        from core.logger import media_logger  # noqa: F401
        mime_types = ['audio/ogg', 'audio/mpeg', 'audio/mp4', 'audio/wav']
        for mime in mime_types:
            try:
                res = await client.aio.models.generate_content(
                    model=STABLE_MODEL,
                    contents=[
                        types.Part.from_bytes(data=audio_bytes, mime_type=mime),
                        types.Part.from_text(text='Transcribe this Russian audio message.'),
                    ],
                )
                if res.text:
                    return res.text
            except Exception:
                continue
        return '[Не удалось распознать аудио]'
    except Exception as e:
        return f'[Ошибка: {e}]'


async def generate_sarcastic_voice(text: str) -> str | None:
    """
    Генерация голоса через Gemini 2.5 Flash Lite TTS (Puck).

    Механика:
      1. Удаление префиксов команды озвучки.
      2. Разбивка на чанки ≤300 символов по границам предложений.
      3. Последовательная генерация RAW PCM для каждого чанка.
      4. Детекция аномалий через SHA-256 (дубликаты / пустые пропускаются).
      5. Склейка PCM-буферов в один файл.
      6. Единая конвертация PCM → OGG через FFmpeg.
      7. Fallback на Edge-TTS при полном провале.
    """
    from core.logger import media_logger

    # 1. Удаляем префиксы и обрезаем до разумного предела
    text = _strip_prefix(text)[:4000]
    if not text:
        media_logger.warning('[TTS] Empty text after prefix strip')
        return None

    # 2. Разбиваем на чанки
    chunks = _split_sentences(text)
    media_logger.info(f'[TTS] {len(chunks)} chunk(s) for {len(text)} chars')

    # 3 + 4. Последовательная генерация + SHA-256 детекция аномалий
    pcm_parts: list[bytes] = []
    seen_hashes: set[str] = set()

    for idx, chunk in enumerate(chunks):
        media_logger.info(f'[TTS] Chunk {idx + 1}/{len(chunks)}: {len(chunk)} chars')
        pcm = await _generate_pcm_chunk(chunk)

        if not pcm:
            media_logger.warning(f'[TTS] Chunk {idx + 1} returned no data — skipping')
            continue

        digest = hashlib.sha256(pcm).hexdigest()
        if digest in seen_hashes:
            media_logger.warning(
                f'[TTS] Chunk {idx + 1} is a duplicate (sha256={digest[:16]}…) — skipping'
            )
            continue

        seen_hashes.add(digest)
        media_logger.info(f'[TTS] Chunk {idx + 1} OK: {len(pcm)} bytes, sha256={digest[:16]}…')
        pcm_parts.append(pcm)

    if not pcm_parts:
        media_logger.error('[TTS] All chunks failed or were duplicates')
    else:
        # 5. Склейка PCM
        combined_pcm = b''.join(pcm_parts)
        p_raw = f'/tmp/v_raw_{uuid.uuid4().hex}.pcm'
        out   = f'/tmp/voice_{uuid.uuid4().hex}.ogg'

        try:
            with open(p_raw, 'wb') as f:
                f.write(combined_pcm)

            # 6. Единая конвертация PCM → OGG
            cmd = [
                FFMPEG_PATH, '-y',
                '-f', 's16le',
                '-ar', str(_PCM_RATE),
                '-ac', str(_PCM_CHANNELS),
                '-i', p_raw,
                '-c:a', 'libopus',
                '-b:a', '32k',
                out,
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)

            if os.path.exists(out) and os.path.getsize(out) > 500:
                media_logger.info(
                    f'✅ [TTS] OGG SUCCESS: {out} ({os.path.getsize(out)} bytes), '
                    f'{len(pcm_parts)} chunk(s) merged'
                )
                return out
            else:
                media_logger.error(f'[TTS] FFmpeg failed. Stderr: {proc.stderr}')
        finally:
            if os.path.exists(p_raw):
                os.remove(p_raw)

    # 7. Fallback на Edge-TTS
    try:
        import edge_tts
        media_logger.info('[TTS] Edge-TTS Fallback')
        out_fb = f'/tmp/voice_{uuid.uuid4().hex}.mp3'
        communicate = edge_tts.Communicate(text, 'ru-RU-DmitryNeural')
        await communicate.save(out_fb)
        if os.path.exists(out_fb) and os.path.getsize(out_fb) > 0:
            return out_fb
    except Exception as e:
        media_logger.error(f'[TTS] Fallback failed: {e}')

    return None
