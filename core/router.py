"""
router.py — USBAGENT NexusShell Core: маршрутизатор входящих сообщений v4.4

Использует ToolRegistry для диспетчеризации и обновлённый brain.py.
"""

import os
import re
import time
import asyncio
import uuid
import json

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes
from google.genai import types

from config import (
    ALLOWED_USER_ID, HISTORY_FILE, STABLE_MODEL,
    IMAGE_MODEL_EDIT, LOCATION_GLOBAL, IMAGE_MODEL_IMAGEN
)
from core.brain import (
    load_json, save_json,
    get_relevant_memories,
    generate_response_stream,
    load_history, persist_history,
    client,
    history_lock,
)
from core.logger import router_logger
from core.triggers import (
    has_trigger, VEO_PATTERN, NANOBANANA_TRIGGER, NANOBANANA_CLEAN_TRIGGERS,
    DRAW_TRIGGERS, EDIT_TRIGGERS, STYLE_TRIGGERS, CRYPTO_TRIGGERS,
    VOICE_TRIGGER, STYLE_SAVE_PREFIX, STYLE_SHOW_TRIGGERS, STYLE_RESET_TRIGGERS,
    extract_style_command, get_aspect_ratio, get_imagen_model,
    PHOTO_KEYWORDS, OSINT_TRIGGERS,
)
from core.media_handler import extract_media, detect_multi_photo_edit
from core.image_tools_handler import process_image_tools
from core.tool_registry import ToolRegistry, build_default_registry

from tools.veo import handle_video_generation
from tools.image import process_image_edit, generate_via_flash
from tools.memes import trigger_meme_if_needed
from tools.voice import generate_sarcastic_voice
from tools.watcher import get_crypto_prices
from tools.image_search import search_real_photos
from tools.prompt_enhancer import (
    enhance_prompt as _enhance_prompt_original,
    save_user_style,
    load_user_style,
)
from tools.trend_hunter import run_full_scan
from tools.osint import (
    check_nickname,
    check_crypto,
    social_footprint,
    format_nickname_result,
    format_crypto_result,
    format_footprint_result,
)
from core.prompt_cache import get_cached_prompt, cache_prompt

# ---------------------------------------------------------------------------
# Telegram message size constants
# ---------------------------------------------------------------------------

_TG_MAX_LEN: int = 4096          # hard Telegram limit
_TG_EDIT_THRESHOLD: int = 4000   # leave headroom for the typing cursor
_TG_SPLIT_LEN: int = 3900        # chunk size when splitting long messages

# ---------------------------------------------------------------------------
# USBAGENT USB-INIT: paths to context files injected into NexusShell Core on boot
# ---------------------------------------------------------------------------

USB_INIT_TRIGGER = 'usb-init'

_USB_INIT_CONTEXT_FILES = [
    'SESSION_STATE.md',
    'ARCHITECTURE.md',
    'CONVENTIONS.md',
    'GEMINI.md',
]

# ---------------------------------------------------------------------------
# Trend triggers (natural language)
# ---------------------------------------------------------------------------

TREND_TRIGGERS = [
    'что сейчас в тренде',
    'что в тренде',
    'найди сигналы',
    'найди тренды',
    'покажи тренды',
    'покажи сигналы',
    'трендовые темы',
    'актуальные темы',
    'что популярно',
    'что хайпует',
    'что хайп',
    'сигналы рынка',
    'trend report',
    'show trends',
    'find signals',
    'market signals',
    'what is trending',
    'whats trending',
    "what's trending",
    'trending now',
    'trend scan',
    'scan trends',
]

# ---------------------------------------------------------------------------
# OSINT regex helpers
# ---------------------------------------------------------------------------

# Крипто-адреса: BTC (legacy, P2SH, bech32), ETH/EVM, TRX
_RE_CRYPTO_ADDR = re.compile(
    r'\b('
    r'(1|3)[a-zA-HJ-NP-Z0-9]{25,34}'          # BTC legacy / P2SH
    r'|bc1[a-zA-HJ-NP-Z0-9]{39,59}'            # BTC bech32
    r'|0x[a-fA-F0-9]{40}'                       # ETH / EVM
    r'|T[a-zA-Z0-9]{33}'                        # TRX
    r')\b'
)

# Никнейм: @handle или слово после ключевых слов «ник», «nickname», «user»
_RE_NICKNAME = re.compile(
    r'@([A-Za-z0-9_]{2,32})'                    # @username
    r'|(?:ник|никнейм|nickname|user|юзер)[:\s]+([A-Za-z0-9_.]{2,32})',
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Инициализация ToolRegistry
# ---------------------------------------------------------------------------

_registry: ToolRegistry = build_default_registry()

# ---------------------------------------------------------------------------
# Кэш промптов
# ---------------------------------------------------------------------------

async def enhance_prompt(text: str, mode: str = 'imagen_generate') -> str:
    """Обёртка с кэшированием для enhance_prompt."""
    cached = get_cached_prompt(text, mode)
    if cached:
        router_logger.debug(f"[NexusShell Core] Prompt cache hit for mode={mode}")
        return cached
    enhanced = await _enhance_prompt_original(text, mode)
    cache_prompt(text, mode, enhanced)
    return enhanced


# ---------------------------------------------------------------------------
# Кэш поиска фото
# ---------------------------------------------------------------------------

_photo_cache: dict[str, tuple[bool, str, float]] = {}
PHOTO_CACHE_TTL = 300
PHOTO_CACHE_MAX_SIZE = 100


def _cleanup_photo_cache() -> None:
    current_time = time.time()
    expired = [k for k, (_, _, ts) in _photo_cache.items() if current_time - ts > PHOTO_CACHE_TTL]
    for k in expired:
        del _photo_cache[k]
    if len(_photo_cache) > PHOTO_CACHE_MAX_SIZE:
        sorted_items = sorted(_photo_cache.items(), key=lambda x: x[1][2])
        for k, _ in sorted_items[:len(_photo_cache) - PHOTO_CACHE_MAX_SIZE]:
            del _photo_cache[k]


async def needs_image_search(text: str) -> tuple[bool, str]:
    """Определяет, нужен ли поиск реального фото."""
    low_text = text.lower()

    if not any(kw in low_text for kw in PHOTO_KEYWORDS):
        return False, text

    if any(cmd in low_text for cmd in ['нарисуй', 'сгенерируй', 'измени', 'апскейл', 'ретушь']):
        return False, text

    cache_key = text.strip().lower()[:100]
    if cache_key in _photo_cache:
        need, query, ts = _photo_cache[cache_key]
        if time.time() - ts < PHOTO_CACHE_TTL:
            router_logger.debug(f"[NexusShell Core] Photo search cache hit: {query}")
            return need, query

    if len(_photo_cache) > PHOTO_CACHE_MAX_SIZE:
        _cleanup_photo_cache()

    prompt = f'User: "{text}"\nJSON only: {{"needs_photo": true/false, "search_query": "english query"}}'

    try:
        safety = [
            types.SafetySetting(category='HARM_CATEGORY_HATE_SPEECH',        threshold='BLOCK_ONLY_HIGH'),
            types.SafetySetting(category='HARM_CATEGORY_DANGEROUS_CONTENT',   threshold='BLOCK_ONLY_HIGH'),
            types.SafetySetting(category='HARM_CATEGORY_HARASSMENT',          threshold='BLOCK_ONLY_HIGH'),
            types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT',   threshold='BLOCK_ONLY_HIGH'),
        ]
        res = await client.aio.models.generate_content(
            model=STABLE_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0, max_output_tokens=80, safety_settings=safety
            ),
        )
        match = re.search(r'\{.*?\}', res.text, re.DOTALL)
        if match:
            data = json.loads(match.group())
            result = data.get('needs_photo', False), data.get('search_query', text)
            _photo_cache[cache_key] = (*result, time.time())
            router_logger.info(f"[NexusShell Core] Photo search needed: {result[0]}, query: {result[1]}")
            return result

    except json.JSONDecodeError as e:
        router_logger.error(f"[NexusShell Core] JSON parse error in photo search: {e}")
    except Exception as e:
        router_logger.error(f"[NexusShell Core] Error checking photo search need: {e}", exc_info=True)

    return False, text


# ---------------------------------------------------------------------------
# USB-INIT handler
# ---------------------------------------------------------------------------

def _load_usb_init_context() -> str:
    """
    Read all 4 context files and return them as a single formatted string.
    Missing files are noted but do not raise an exception.
    """
    parts: list[str] = []
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    for filename in _USB_INIT_CONTEXT_FILES:
        filepath = os.path.join(base_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as fh:
                content = fh.read().strip()
            parts.append(f"=== {filename} ===\n{content}")
            router_logger.info(f"[NexusShell Core] usb-init: loaded {filename} ({len(content)} chars)")
        except FileNotFoundError:
            parts.append(f"=== {filename} ===\n[FILE NOT FOUND]")
            router_logger.warning(f"[NexusShell Core] usb-init: {filename} not found at {filepath}")
        except Exception as e:
            parts.append(f"=== {filename} ===\n[READ ERROR: {e}]")
            router_logger.error(f"[NexusShell Core] usb-init: error reading {filename}: {e}", exc_info=True)

    return "\n\n".join(parts)


async def _handle_usb_init(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    uid_str: str,
) -> bool:
    """
    USBAGENT NexusShell Core HARD-BOOT sequence.

    1. Reads SESSION_STATE.md, ARCHITECTURE.md, CONVENTIONS.md, GEMINI.md
    2. Injects them as the first (system-level) turn in the conversation
       sent to NexusShell Core, BEFORE any user message.
    3. Asks NexusShell Core to acknowledge the context and respond as v4.4 Expert.
    4. Returns True so the main handler exits immediately after.
    """
    router_logger.info("[NexusShell Core] usb-init: HARD-BOOT sequence triggered")
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)

    status_msg = await update.message.reply_text(
        "🔄 *USBAGENT NexusShell Core — HARD-BOOT SEQUENCE*\n\n"
        "📂 Reading context files...\n"
        "`SESSION_STATE.md` · `ARCHITECTURE.md` · `CONVENTIONS.md` · `GEMINI.md`",
        parse_mode='Markdown',
    )

    # --- Step 1: load all context files ---
    context_block = _load_usb_init_context()

    boot_prompt = (
        "CRITICAL BOOT SEQUENCE — usb-init\n\n"
        "You have just received the full project context below. "
        "Read every file carefully. Then:\n"
        "1. Adopt the role of USBAGENT NexusShell Core v4.4 Expert as described in GEMINI.md.\n"
        "2. Apply all CONVENTIONS (httpx, get_collection, strip CoT blocks).\n"
        "3. Acknowledge the current SESSION_STATE (status, last task, blockers, next step).\n"
        "4. Output a concise status report: current version, active modules, "
        "pending tasks, and any blockers.\n\n"
        "DO NOT answer anything else until you have processed the context below.\n\n"
        f"{context_block}\n\n"
        "--- END OF CONTEXT ---\n\n"
        "Now output your NexusShell Core v4.4 Expert status report."
    )

    # --- Step 2: send to NexusShell Core with empty history (clean session context) ---
    try:
        _, raw_history = await load_history(uid_str)

        boot_parts = [types.Part.from_text(text=boot_prompt)]

        full_reply = ""
        async for chunk, chart_media in generate_response_stream(
            raw_history, boot_parts, boot_prompt
        ):
            if chunk:
                full_reply += chunk

        # --- Step 3: deliver the response ---
        router_logger.info(f"[NexusShell Core] usb-init: replied ({len(full_reply)} chars)")
        await _send_long_text(update, context, full_reply or "...", placeholder_msg=status_msg)

        # --- Step 4: persist so the boot context is part of history ---
        await persist_history(uid_str, "usb-init", full_reply)

    except Exception as e:
        router_logger.error(f"[NexusShell Core] usb-init: call failed: {e}", exc_info=True)
        try:
            await status_msg.edit_text(
                f"❌ *USBAGENT usb-init failed*: `{str(e)[:200]}`", parse_mode='Markdown'
            )
        except Exception:
            await update.message.reply_text(f"❌ usb-init failed: {str(e)[:200]}")

    return True


# ---------------------------------------------------------------------------
# Trend Hunter handler
# ---------------------------------------------------------------------------

async def _handle_trend_scan(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    """Handle natural language trend scan requests."""
    try:
        router_logger.info("[NexusShell Core] TrendHunter: natural language trigger detected")

        await update.message.reply_text(
            "⚡️ *USBAGENT TREND HUNTER — NexusShell Core v4.4*\n\n"
            "🔍 Scanning global signals...\n"
            "_AI · Crypto · OSINT · Tech_\n\n"
            "⏳ This takes 15–30 seconds...",
            parse_mode='Markdown'
        )

        await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)

        brief = await run_full_scan()

        if len(brief) <= 4096:
            await update.message.reply_text(brief, parse_mode='Markdown')
        else:
            chunks = [brief[i:i+4000] for i in range(0, len(brief), 4000)]
            for chunk in chunks:
                await update.message.reply_text(chunk, parse_mode='Markdown')
                await asyncio.sleep(0.5)

        router_logger.info("[NexusShell Core] TrendHunter: scan complete")
        return True

    except Exception as e:
        router_logger.error(f"[NexusShell Core] TrendHunter handler error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Trend scan failed: {str(e)[:100]}")
        return True


# ---------------------------------------------------------------------------
# OSINT handler
# ---------------------------------------------------------------------------

def _extract_osint_target(text: str) -> tuple[str, str]:
    """
    Извлечь цель OSINT-запроса и определить режим.

    Возвращает (mode, target) где mode ∈ {'crypto', 'nickname', 'footprint'}.
    """
    # 1. Крипто-адрес имеет наивысший приоритет
    crypto_match = _RE_CRYPTO_ADDR.search(text)
    if crypto_match:
        return 'crypto', crypto_match.group(1)

    # 2. Явный никнейм (@handle или «ник: xxx»)
    nick_match = _RE_NICKNAME.search(text)
    if nick_match:
        target = nick_match.group(1) or nick_match.group(2)
        return 'nickname', target.strip()

    # 3. Общий поиск — берём текст после триггерного слова
    cleaned = text.strip()
    trigger_words = [
        'пробей', 'пробить', 'найди инфо', 'найди информацию',
        'проверь ник', 'проверь никнейм', 'найди аккаунты',
        'кто владелец', 'social footprint', 'цифровой след', 'пробив',
        'найди человека', 'поищи человека', 'osint', 'check nickname',
        'crypto trace', 'find accounts', 'lookup user', 'trace address',
        'who owns', 'find user', 'найди', 'проверь', 'инфа по',
        'чекни ник', 'проверь адрес', 'trace',
    ]
    for tw in sorted(trigger_words, key=len, reverse=True):
        pattern = re.compile(re.escape(tw), re.IGNORECASE)
        cleaned = pattern.sub('', cleaned).strip()

    # Убираем лишние знаки препинания в начале
    cleaned = re.sub(r'^[\s:,.\-]+', '', cleaned).strip()

    return 'footprint', cleaned if cleaned else text.strip()


async def _handle_osint(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
) -> bool:
    """
    USBAGENT OSINT-обработчик. Классифицирует запрос и вызывает нужную функцию.

    Возвращает True если запрос был обработан как OSINT.
    """
    try:
        router_logger.info(f"[NexusShell Core] OSINT: processing request: {text[:80]}")
        await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)

        status_msg = await update.message.reply_text(
            "🕵️ *USBAGENT OSINT — NexusShell Core*\n⏳ Scanning open sources...",
            parse_mode='Markdown',
        )

        mode, target = _extract_osint_target(text)
        router_logger.info(f"[NexusShell Core] OSINT: mode={mode}, target={target[:60]}")

        if not target:
            await status_msg.edit_text("❌ Не удалось определить цель поиска. Уточни запрос.")
            return True

        if mode == 'crypto':
            result = await check_crypto(target)
            formatted = format_crypto_result(result)

        elif mode == 'nickname':
            result = await check_nickname(target)
            formatted = format_nickname_result(result)

        else:  # footprint
            result = await social_footprint(target)
            formatted = format_footprint_result(result)

        # Отправляем результат
        if len(formatted) <= _TG_EDIT_THRESHOLD:
            try:
                await status_msg.edit_text(formatted, parse_mode='Markdown')
            except Exception:
                await update.message.reply_text(formatted, parse_mode='Markdown')
        else:
            await status_msg.edit_text("✅ OSINT результат готов:", parse_mode='Markdown')
            chunks = _split_text(formatted)
            for chunk in chunks:
                await update.message.reply_text(chunk, parse_mode='Markdown')
                await asyncio.sleep(0.3)

        router_logger.info(f"[NexusShell Core] OSINT: completed mode={mode}, target={target[:40]}")
        return True

    except Exception as e:
        router_logger.error(f"[NexusShell Core] OSINT handler error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ OSINT ошибка: {str(e)[:120]}")
        return True


# ---------------------------------------------------------------------------
# Обработчики инструментов
# ---------------------------------------------------------------------------

async def handle_photo_edit(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    base_bytes,
    ref_bytes,
    text: str,
) -> bool:
    """Multi-photo editing с 429 Retry (NexusShell Core)."""
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.UPLOAD_PHOTO)

    from google.genai import Client
    project = os.environ.get('GCLOUD_PROJECT', 'usbtest-490122')
    edit_client = Client(vertexai=True, project=project, location=LOCATION_GLOBAL)

    for attempt in range(2):
        try:
            router_logger.info(f"[NexusShell Core] Multi-photo edit attempt {attempt + 1}/2")
            res = await edit_client.aio.models.generate_content(
                model=IMAGE_MODEL_EDIT,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(
                                text=(
                                    f"Take the first image as the base scene. {text}. "
                                    "The second image is the reference/source. "
                                    "Seamlessly blend/integrate. Output only the final image."
                                )
                            ),
                            types.Part.from_bytes(data=bytes(base_bytes), mime_type='image/jpeg'),
                            types.Part.from_bytes(data=bytes(ref_bytes),  mime_type='image/jpeg'),
                        ],
                    )
                ],
                config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
            )

            if res.candidates and res.candidates[0].content.parts:
                for part in res.candidates[0].content.parts:
                    if part.inline_data:
                        p = f"/tmp/multi_{uuid.uuid4().hex}.png"
                        with open(p, "wb") as f:
                            f.write(part.inline_data.data)
                        with open(p, "rb") as f:
                            await update.message.reply_photo(
                                photo=f, caption="🎨 USBAGENT Multi-Photo Edit — Done"
                            )
                        os.remove(p)
                        router_logger.info("[NexusShell Core] Multi-photo edit successful")
                        return True
            break

        except Exception as e:
            if '429' in str(e) and attempt == 0:
                router_logger.warning("[NexusShell Core] Rate limit hit (429), retrying in 5s...")
                await asyncio.sleep(5)
                continue
            router_logger.error(f"[NexusShell Core] Multi-photo edit error: {e}", exc_info=True)
            return False

    return False


async def _handle_user_style(update: Update, text: str, low_text: str) -> bool:
    """Обработка команд пользовательского стиля."""
    style_cmd = extract_style_command(text)
    if style_cmd:
        save_user_style(style_cmd)
        await update.message.reply_text(
            f'✅ Стиль сохранён:\n_{style_cmd}_', parse_mode='Markdown'
        )
        router_logger.info(f"[NexusShell Core] User style saved: {style_cmd[:50]}")
        return True

    if low_text in STYLE_SHOW_TRIGGERS:
        style = load_user_style()
        if style:
            await update.message.reply_text(f'🎨 Твой стиль:\n_{style}_', parse_mode='Markdown')
        else:
            await update.message.reply_text('Стиль не задан. Используй: сохрани стиль: [описание]')
        return True

    if low_text in STYLE_RESET_TRIGGERS:
        save_user_style('')
        await update.message.reply_text('✅ Стиль сброшен.')
        router_logger.info("[NexusShell Core] User style reset")
        return True

    return False


async def _handle_nanobanana(
    update: Update, context: ContextTypes.DEFAULT_TYPE, text: str
) -> bool:
    """Генерация изображений через NexusShell Core Image Engine."""
    try:
        router_logger.info("[NexusShell Core] Processing NexusShell Image generation")
        await context.bot.send_chat_action(update.effective_chat.id, ChatAction.UPLOAD_PHOTO)

        clean_text = text
        for trigger in NANOBANANA_CLEAN_TRIGGERS:
            clean_text = clean_text.replace(trigger, '').strip()

        enhanced_text = await enhance_prompt(clean_text, mode='imagen_generate')
        router_logger.info(f"[NexusShell Core] Enhanced prompt: {enhanced_text[:80]}")

        path = await generate_via_flash(enhanced_text)
        if path:
            with open(path, 'rb') as f:
                await update.message.reply_photo(photo=f, caption='⚡ USBAGENT NexusShell Image')
            if os.path.exists(path):
                os.remove(path)
        else:
            await update.message.reply_text('❌ NexusShell Image generation failed')
        return True

    except Exception as e:
        router_logger.error(f"[NexusShell Core] Image generation error: {e}", exc_info=True)
        await update.message.reply_text('❌ Ошибка при генерации')
        return True


async def _handle_veo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    img_bytes,
    video_bytes,
    multi_photo: tuple | None = None,
) -> bool:
    """
    USBAGENT VEO видео-генерация через NexusShell Core.

    Поддерживаемые режимы (в порядке приоритета):
    1. Start/End Frame Control — если передан multi_photo (два фото из альбома).
       Первое фото → start_image_bytes, второе → end_image_bytes.
    2. Image-to-Video          — если передан один img_bytes.
    3. Video-to-Video          — если передан video_bytes.
    4. Text-to-Video           — только промпт.
    """
    try:
        # Очищаем промпт от VEO-триггеров
        prompt = VEO_PATTERN.sub('', text).strip() or 'Animate this scene naturally'
        enhanced_prompt = await enhance_prompt(prompt, mode='veo')

        start_image_bytes = None
        end_image_bytes = None
        call_image_bytes = img_bytes
        call_video_bytes = video_bytes

        if multi_photo is not None:
            start_image_bytes = multi_photo[0]
            end_image_bytes   = multi_photo[1]
            call_image_bytes  = None
            call_video_bytes  = None
            router_logger.info(
                f"[NexusShell Core] VEO: Start/End Frame Control — "
                f"start={len(start_image_bytes)} bytes, "
                f"end={len(end_image_bytes)} bytes"
            )
        elif img_bytes is not None:
            router_logger.info(f"[NexusShell Core] VEO: Image-to-Video — {len(img_bytes)} bytes")
        elif video_bytes is not None:
            router_logger.info(f"[NexusShell Core] VEO: Video-to-Video — {len(video_bytes)} bytes")
        else:
            router_logger.info("[NexusShell Core] VEO: Text-to-Video")

        router_logger.info(f"[NexusShell Core] VEO: prompt='{enhanced_prompt[:80]}'")

        await handle_video_generation(
            update,
            context,
            enhanced_prompt,
            image_bytes=call_image_bytes,
            video_bytes=call_video_bytes,
            start_image_bytes=start_image_bytes,
            end_image_bytes=end_image_bytes,
        )
        return True

    except Exception as e:
        router_logger.error(f"[NexusShell Core] VEO error: {e}", exc_info=True)
        await update.message.reply_text(f'❌ USBAGENT VEO Error: {e}')
        return True


async def _handle_image_generation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    low_text: str,
    img_bytes,
    is_audio: bool,
) -> bool:
    """USBAGENT NexusShell Core — генерация/редактирование изображений."""
    try:
        await context.bot.send_chat_action(update.effective_chat.id, ChatAction.UPLOAD_PHOTO)

        if img_bytes and not is_audio:
            mode = 'style' if has_trigger(low_text, STYLE_TRIGGERS) else 'edit'
            enhance_mode = 'imagen_edit'
        else:
            mode = 'generate'
            enhance_mode = 'imagen_generate'

        router_logger.info(f"[NexusShell Core] Image processing: mode={mode}")

        aspect = get_aspect_ratio(text)
        imagen_model = get_imagen_model(text, IMAGE_MODEL_IMAGEN)
        enhanced_text = await enhance_prompt(text, mode=enhance_mode)
        path = await process_image_edit(
            img_bytes, enhanced_text, mode=mode, aspect=aspect, imagen_model=imagen_model
        )

        if path == 'FILTERED':
            await update.message.reply_text(
                "❌ Запрос заблокирован Safety Policy. Попробуй другой промпт."
            )
            return True
        elif path == 'RATE_LIMIT':
            await update.message.reply_text(
                "⏳ Rate limit. Попробуй через минуту."
            )
            return True
        elif path == 'ERROR':
            await update.message.reply_text("❌ Произошла ошибка при обработке изображения.")
            return True
        elif path:
            caption_map = {
                'generate': '🎨 USBAGENT Imagen 4',
                'style':    '🎭 USBAGENT NexusShell — Style',
                'edit':     '✏️ USBAGENT NexusShell — Edit',
            }
            with open(path, 'rb') as f:
                await update.message.reply_photo(
                    photo=f,
                    caption=f'{caption_map.get(mode, "🖼 USBAGENT Image")} ({aspect})',
                )
            os.remove(path)
            router_logger.info(f"[NexusShell Core] Image {mode} successful")
            return True

    except Exception as e:
        router_logger.error(f"[NexusShell Core] Image generation error: {e}", exc_info=True)
        await update.message.reply_text("❌ Ошибка при обработке изображения")
        return True

    return False


async def _handle_photo_search(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    search_query: str,
    text: str,
    user_id: int,
) -> bool:
    """Поиск реальных фотографий через NexusShell Core."""
    try:
        await context.bot.send_chat_action(update.effective_chat.id, ChatAction.UPLOAD_PHOTO)
        router_logger.info(f"[NexusShell Core] Searching real photo: {search_query}")

        result = await search_real_photos([search_query])

        if result:
            await update.message.reply_photo(
                photo=result['image_url'],
                caption=f"📸 {result.get('title', search_query)}",
            )
            photo_note = f"[Отправил фото по запросу: {search_query}]"
            router_logger.info(f"[NexusShell Core] Photo found and sent: {search_query}")
        else:
            await update.message.reply_text(f"🔍 Искал фото «{search_query}» — ничего не нашёл.")
            photo_note = f"[Искал фото «{search_query}» — не нашёл]"
            router_logger.info(f"[NexusShell Core] Photo not found: {search_query}")

        async with history_lock:
            all_h = load_json(HISTORY_FILE, {})
            uid_str = str(user_id)
            ph = all_h.get(uid_str, [])
            ph.append(f"User: {text}")
            ph.append(f"Bot: {photo_note}")
            all_h[uid_str] = ph[-20:]
            save_json(HISTORY_FILE, all_h)

        return True

    except Exception as e:
        router_logger.error(f"[NexusShell Core] Photo search error: {e}", exc_info=True)
        await update.message.reply_text("❌ Ошибка при поиске фото")
        return True


# ---------------------------------------------------------------------------
# Голосовые сообщения
# ---------------------------------------------------------------------------

async def _try_voice_reply(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text_to_voice: str,
    label: str = "",
) -> bool:
    """Сгенерировать и отправить голосовое сообщение. Возвращает True при успехе."""
    if not text_to_voice or len(text_to_voice.strip()) < 3:
        return False
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.RECORD_VOICE)
    v_path = await generate_sarcastic_voice(text_to_voice)
    if v_path and os.path.exists(v_path):
        with open(v_path, 'rb') as f:
            await update.message.reply_voice(voice=f)
        os.remove(v_path)
        router_logger.info(f"[NexusShell Core] Voice message sent ({label})")
        return True
    router_logger.error(f"[NexusShell Core] Voice generation failed ({label}): path={v_path}")
    return False


# ---------------------------------------------------------------------------
# Helpers — Telegram message sending
# ---------------------------------------------------------------------------

def _split_text(text: str, chunk_size: int = _TG_SPLIT_LEN) -> list[str]:
    """
    Split *text* into chunks of at most *chunk_size* characters.
    Tries to split on newlines first, then on spaces, then hard-cuts.
    """
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    while len(text) > chunk_size:
        split_at = text.rfind('\n', 0, chunk_size)
        if split_at <= 0:
            split_at = text.rfind(' ', 0, chunk_size)
        if split_at <= 0:
            split_at = chunk_size
        chunks.append(text[:split_at].rstrip())
        text = text[split_at:].lstrip()
    if text:
        chunks.append(text)
    return chunks


async def _send_long_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    placeholder_msg=None,
) -> None:
    """
    Send *text* to the user, splitting into multiple messages if needed.

    If *placeholder_msg* is provided, the first chunk replaces it via
    edit_text; subsequent chunks are sent as new messages.
    If editing fails the first chunk is sent as a new message.
    """
    if not text:
        text = "..."

    chunks = _split_text(text)
    first = True

    for chunk in chunks:
        if not chunk:
            continue
        if first and placeholder_msg is not None:
            try:
                await placeholder_msg.edit_text(chunk)
                first = False
                continue
            except Exception as edit_err:
                router_logger.warning(
                    f"[NexusShell Core] edit_text failed, sending as new message: {edit_err}"
                )
        try:
            await update.message.reply_text(chunk)
        except Exception as send_err:
            router_logger.error(f"[NexusShell Core] reply_text failed: {send_err}", exc_info=True)
        first = False
        if len(chunks) > 1:
            await asyncio.sleep(0.3)


# ---------------------------------------------------------------------------
# Главный обработчик
# ---------------------------------------------------------------------------

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """USBAGENT NexusShell Core — главный обработчик входящих сообщений."""
    start_time = time.time()

    # --- Валидация ---
    if not update.message or not update.message.from_user:
        return

    user_id = update.message.from_user.id
    if user_id != ALLOWED_USER_ID:
        router_logger.warning(f"[NexusShell Core] Unauthorized access attempt: {user_id}")
        return

    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    text = update.message.text or update.message.caption or ''
    low_text = text.lower().strip()
    uid_str = str(user_id)

    router_logger.info(f"[NexusShell Core] Processing message: {text[:100]}")

    # =========================================================================
    # 0. USB-INIT — HARD-BOOT SEQUENCE (highest priority)
    # =========================================================================
    if low_text == USB_INIT_TRIGGER:
        await _handle_usb_init(update, context, uid_str)
        return

    # =========================================================================
    # 1. СТИЛЬ ПОЛЬЗОВАТЕЛЯ
    # =========================================================================
    if await _handle_user_style(update, text, low_text):
        return

    # =========================================================================
    # 2. TREND HUNTER (natural language triggers)
    # =========================================================================
    if any(trigger in low_text for trigger in TREND_TRIGGERS):
        if await _handle_trend_scan(update, context):
            return

    # =========================================================================
    # 3. MEDIA EXTRACTION
    # =========================================================================
    media = await extract_media(update, context)
    if media and media.text_addition:
        text = f'{media.text_addition}\n\n{text}' if text else media.text_addition
        router_logger.info(
            f"[NexusShell Core] Added transcription to text: {media.text_addition[:50]}"
        )
        low_text = text.lower()

    # =========================================================================
    # 4. IMAGE TOOLS (OCR / RETOUCH / UPSCALE / OUTPAINT)
    # =========================================================================
    if await process_image_tools(update, context, media.img_bytes, text):
        return

    # =========================================================================
    # 5. VEO (VIDEO GENERATION)
    # =========================================================================
    if VEO_PATTERN.search(low_text):
        veo_multi: tuple | None = None
        if len(media.img_bytes_list) >= 2:
            veo_multi = (media.img_bytes_list[0], media.img_bytes_list[1])
            router_logger.info(
                f"[NexusShell Core] VEO: album with {len(media.img_bytes_list)} photos → "
                "Start/End Frame Control"
            )

        if await _handle_veo(
            update, context, text,
            img_bytes=media.img_bytes if not veo_multi else None,
            video_bytes=media.video_bytes,
            multi_photo=veo_multi,
        ):
            return

    # =========================================================================
    # 6. MULTI-PHOTO IMAGE EDIT (non-VEO path)
    # =========================================================================
    if len(media.img_bytes_list) >= 2:
        base_img = media.img_bytes_list[0]
        ref_img  = media.img_bytes_list[1]
        router_logger.info("[NexusShell Core] Multi-photo image edit: using album photos")
        if await handle_photo_edit(update, context, base_img, ref_img, text):
            return
        await update.message.reply_text(
            "⏳ Модель перегружена или произошла ошибка. Попробуй через 10 секунд."
        )
        return
    else:
        multi_photo = await detect_multi_photo_edit(update, context)
        if multi_photo:
            base_img, ref_img = multi_photo
            if await handle_photo_edit(update, context, base_img, ref_img, text):
                return
            await update.message.reply_text(
                "⏳ Модель перегружена или произошла ошибка. Попробуй через 10 секунд."
            )
            return

    # =========================================================================
    # 7. NEXUSSHELL IMAGE ENGINE (быстрая генерация)
    # =========================================================================
    if NANOBANANA_TRIGGER in low_text:
        if await _handle_nanobanana(update, context, text):
            return

    # =========================================================================
    # 8. IMAGE GENERATION / STYLE / EDIT
    # =========================================================================
    if has_trigger(low_text, DRAW_TRIGGERS + EDIT_TRIGGERS + STYLE_TRIGGERS):
        if await _handle_image_generation(update, context, text, low_text, media.img_bytes, False):
            return

    # =========================================================================
    # 9. CRYPTO PRICES
    # =========================================================================
    if has_trigger(low_text, CRYPTO_TRIGGERS):
        try:
            prices = await get_crypto_prices()
            text = f'[ТЕКУЩИЕ КУРСЫ: {prices}]\n{text}'
            router_logger.info("[NexusShell Core] Added crypto prices to context")
        except Exception as e:
            router_logger.error(f"[NexusShell Core] Crypto prices error: {e}", exc_info=True)

    # =========================================================================
    # 9.5. OSINT
    # =========================================================================
    if has_trigger(low_text, OSINT_TRIGGERS):
        if await _handle_osint(update, context, text):
            return

    # =========================================================================
    # 10. ГОЛОС — проверяем ДО brain
    # =========================================================================
    voice_reply_sent = False
    if VOICE_TRIGGER in low_text:
        try:
            text_to_voice = None

            if update.message.reply_to_message:
                reply_msg = update.message.reply_to_message
                if reply_msg.text and not reply_msg.text.startswith(('[Голосовое', '[STICKER')):
                    text_to_voice = reply_msg.text
                elif reply_msg.caption:
                    text_to_voice = reply_msg.caption

            if text_to_voice:
                ok = await _try_voice_reply(update, context, text_to_voice, label="reply")
                if ok:
                    return
                await update.message.reply_text("❌ Не удалось сгенерировать голос. Попробуй позже.")
                return

            router_logger.info(
                "[NexusShell Core] No reply found for voice — will voice bot response after generation"
            )

        except Exception as e:
            router_logger.error(f"[NexusShell Core] Voice pre-check error: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Ошибка при генерации голоса: {str(e)[:100]}")
            return

    # =========================================================================
    # 11. ПАРАЛЛЕЛЬНАЯ ЗАГРУЗКА: поиск фото + история
    # =========================================================================
    (needs_photo, search_query), (all_h, raw_history) = await asyncio.gather(
        needs_image_search(text),
        load_history(uid_str),
    )

    if needs_photo:
        if await _handle_photo_search(update, context, search_query, text, user_id):
            return

    # =========================================================================
    # 12. NEXUSSHELL CORE BRAIN (ОСНОВНОЙ ДИАЛОГ)
    # =========================================================================
    try:
        memories = await get_relevant_memories(text) if len(text) > 10 else ""

        if memories:
            current_parts = [types.Part.from_text(text=f"Memories: {memories}\n\nUser: {text}")]
        else:
            current_parts = [types.Part.from_text(text=f"User: {text}")]

        if media.img_bytes:
            current_parts.append(
                types.Part.from_bytes(data=bytes(media.img_bytes), mime_type='image/jpeg')
            )
        if media.video_bytes:
            current_parts.append(
                types.Part.from_bytes(data=bytes(media.video_bytes), mime_type='video/mp4')
            )

        full_reply = ""
        msg = await update.message.reply_text("⚡️")

        last_edit_len: int = 0
        _EDIT_INTERVAL: int = 200

        async for chunk, chart_media in generate_response_stream(
            raw_history, current_parts, text
        ):
            if chunk:
                full_reply += chunk

                if (
                    len(full_reply) - last_edit_len >= _EDIT_INTERVAL
                    and len(full_reply) <= _TG_EDIT_THRESHOLD
                ):
                    try:
                        await msg.edit_text(full_reply + " ▌")
                        last_edit_len = len(full_reply)
                    except Exception:
                        pass

            if chart_media and hasattr(chart_media, 'data'):
                try:
                    await context.bot.send_chat_action(
                        update.effective_chat.id, ChatAction.UPLOAD_PHOTO
                    )
                    await update.message.reply_photo(
                        photo=bytes(chart_media.data), caption="📊 USBAGENT Chart"
                    )
                    router_logger.info("[NexusShell Core] Chart sent successfully")
                except Exception as e:
                    router_logger.error(f"[NexusShell Core] Chart send error: {e}", exc_info=True)

        router_logger.info(f"[NexusShell Core] Final reply length: {len(full_reply)} chars")
        await _send_long_text(update, context, full_reply or "...", placeholder_msg=msg)

        await persist_history(uid_str, text, full_reply)

        if VOICE_TRIGGER in low_text and not voice_reply_sent:
            ok = await _try_voice_reply(update, context, full_reply, label="bot_response")
            if not ok:
                router_logger.warning("[NexusShell Core] Voice generation failed for bot response")

        await trigger_meme_if_needed(full_reply, update)

    except Exception as e:
        router_logger.error(f"[NexusShell Core] Chat brain error: {e}", exc_info=True)
        await update.message.reply_text("❌ USBAGENT NexusShell Core: ошибка при обработке запроса")

    finally:
        elapsed = time.time() - start_time
        router_logger.info(f"[NexusShell Core] Request processed in {elapsed:.2f}s")
        try:
            from main import _request_times
            _request_times.append(elapsed)
            if len(_request_times) > 100:
                _request_times.pop(0)
        except Exception:
            pass
