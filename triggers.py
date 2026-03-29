"""
Централизованное хранилище всех триггеров и паттернов
USB BOT V3.1
"""
import re

# === СТИЛИ ===
STYLE_TRIGGERS = [
    'срисуй', 'перерисуй', 'аниме', 'pixar', 'ghibli',
    'скетч', 'акварель', 'маслом', 'мультяшн', 'cartoon'
]
_STYLE_TRIGGERS_SET = set(STYLE_TRIGGERS)

# === ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЙ ===
DRAW_TRIGGERS = [
    'нарисуй', 'изобрази', 'сгенерируй', 'draw', 'построй картинку'
]
_DRAW_TRIGGERS_SET = set(DRAW_TRIGGERS)

# === РЕДАКТИРОВАНИЕ ИЗОБРАЖЕНИЙ ===
EDIT_TRIGGERS = [
    'измени', 'правь', 'поправь', 'поменяй', 'сделай',
    'добавь', 'увеличь', 'уменьшь', 'исправь', 'убери',
    'удали', 'почисти', 'артефакт', 'недостат'
]
_EDIT_TRIGGERS_SET = set(EDIT_TRIGGERS)

# === OCR ===
OCR_TRIGGERS = [
    'прочитай', 'ocr', 'что написано', 'прочитай текст',
    'текст на фото', 'распознай текст'
]

# === РЕТУШЬ ===
RETOUCH_TRIGGERS = [
    'ретушь', 'retouch', 'убери морщины', 'убери поры',
    'сгладь кожу', 'разгладь кожу'
]

RETOUCH_SMOOTH_TRIGGERS = [
    'сгладь кожу', 'разгладь кожу', 'убери поры', 'ретушь кожи'
]

# === АПСКЕЙЛ ===
UPSCALE_TRIGGERS = ['апскейл', 'улучши', 'качество', 'upscale']
UPSCALE_FILM_TRIGGERS = ['пленка', 'плёнка', 'film']
UPSCALE_CREATIVE_TRIGGERS = ['creative', 'krea', 'агрессивно', 'креатив']
UPSCALE_BW_TRIGGERS = ['чб', 'черно-белый', 'чёрно-белый', 'bw']
UPSCALE_FLASH_TRIGGERS = ['вспышка', 'flash', 'папарацци']
UPSCALE_SMOOTH_TRIGGERS = ['smooth', 'гладко', 'лицо гладкое', 'бьюти']

# === OUTPAINT ===
OUTPAINT_TRIGGERS = [
    'расширь', 'дорисуй', 'фон', 'outpaint',
    'панорама', 'широкий кадр'
]

OUTPAINT_HORIZONTAL = ['горизонтально', 'широко', '16:9']
OUTPAINT_VERTICAL = ['вертикально', 'сторис', '9:16', 'вертикаль']

# === ПОИСК ФОТО ===
PHOTO_KEYWORDS = [
    'покажи', 'фото', 'photo', 'picture',
    'картинку', 'картинка', 'как выглядит'
]

# === КРИПТА ===
CRYPTO_TRIGGERS = ['цена', 'курс', 'крипта', 'btc', 'eth']

# === VEO (ВИДЕО) ===
VEO_PATTERN = re.compile(
    r'\b(оживи|veo)\b|^(сними|создай видео|сгенерируй видео|make video)',
    re.IGNORECASE
)

# === НАНОБАНАНА ===
NANOBANANA_TRIGGER = 'нанобанана'
NANOBANANA_CLEAN_TRIGGERS = ['нанобанана', 'сгенерируй фото', 'сгенерируй', 'нарисуй']

# === ОЗВУЧКА ===
VOICE_TRIGGER = 'озвучь'

# === СТИЛЬ ПОЛЬЗОВАТЕЛЯ ===
STYLE_SAVE_PREFIX = 'сохрани стиль:'
STYLE_SHOW_TRIGGERS = ['покажи мой стиль', 'мой стиль']
STYLE_RESET_TRIGGERS = ['сбрось стиль', 'удали стиль']

# === ASPECT RATIO ===
ASPECT_HORIZONTAL = ['горизонтально', 'landscape', 'широкий']
ASPECT_VERTICAL = ['вертикально', 'stories', 'портретный', 'вертикаль']

# === IMAGEN MODELS ===
IMAGEN_ULTRA_TRIGGERS = ['ультра', 'ultra', 'журнал', 'максимум']
IMAGEN_FAST_TRIGGERS = ['быстро', 'fast', 'набросок', 'draft']

# === OSINT ===
OSINT_TRIGGERS = [
    # RU
    'пробей', 'пробить', 'найди инфо', 'найди информацию',
    'проверь ник', 'проверь никнейм', 'найди аккаунты',
    'кто владелец', 'крипто трейс', 'крипто адрес',
    'social footprint', 'цифровой след', 'пробив',
    'найди человека', 'поищи человека',
    # EN
    'osint', 'check nickname', 'crypto trace',
    'find accounts', 'lookup user', 'trace address',
    'who owns', 'find user',
]

# ---------------------------------------------------------------------------
# Кэш скомпилированных regex паттернов
# Ключ: tuple(sorted(triggers)) — чтобы порядок не влиял на кэш
# ---------------------------------------------------------------------------
_trigger_cache: dict[tuple, re.Pattern] = {}


def _get_pattern(triggers: list) -> re.Pattern:
    """Получить (или создать и закэшировать) скомпилированный regex для списка триггеров."""
    cache_key = tuple(sorted(triggers))
    if cache_key not in _trigger_cache:
        pattern = '|'.join(re.escape(t) for t in sorted(triggers, key=len, reverse=True))
        _trigger_cache[cache_key] = re.compile(pattern, re.IGNORECASE)
    return _trigger_cache[cache_key]


def has_trigger(text: str, triggers: list) -> bool:
    """
    Проверка наличия триггера в тексте.

    Использует regex-поиск подстрок, что корректно обрабатывает
    многословные триггеры типа 'что написано', 'убери морщины' и т.д.

    Однословные триггеры дополнительно проверяются через set-пересечение
    для скорости, но финальный арбитр — всегда regex.
    """
    if not text or not triggers:
        return False

    low_text = text.lower()

    # Быстрая проверка: однословные триггеры через set-пересечение слов текста.
    # Это O(n) по словам, но работает только для триггеров без пробелов.
    words = set(low_text.split())
    single_word_triggers = {t for t in triggers if ' ' not in t}
    if words & single_word_triggers:
        return True

    # Полная проверка через regex — ловит многословные триггеры и подстроки.
    return bool(_get_pattern(triggers).search(low_text))


def extract_style_command(text: str) -> str | None:
    """Извлечь команду сохранения стиля"""
    if text.lower().startswith(STYLE_SAVE_PREFIX):
        return text[len(STYLE_SAVE_PREFIX):].strip()
    return None


def get_aspect_ratio(text: str) -> str:
    """Определить aspect ratio из текста"""
    low_text = text.lower()
    if has_trigger(low_text, ASPECT_HORIZONTAL):
        return '16:9'
    elif has_trigger(low_text, ASPECT_VERTICAL):
        return '9:16'
    elif '3:2' in low_text:
        return '3:2'
    elif '4:3' in low_text:
        return '4:3'
    return '1:1'


def get_upscale_mode(text: str) -> str:
    """Определить режим апскейла"""
    low_text = text.lower()
    is_film = has_trigger(low_text, UPSCALE_FILM_TRIGGERS)
    is_creative = has_trigger(low_text, UPSCALE_CREATIVE_TRIGGERS)

    if has_trigger(low_text, UPSCALE_BW_TRIGGERS):
        return 'bw'
    elif has_trigger(low_text, UPSCALE_FLASH_TRIGGERS):
        return 'flash'
    elif is_film and is_creative:
        return 'film_creative'
    elif is_film:
        return 'film'
    elif has_trigger(low_text, UPSCALE_SMOOTH_TRIGGERS):
        return 'smooth'
    elif is_creative:
        return 'creative'
    return 'balanced'


def get_upscale_factor(text: str) -> int:
    """Определить фактор апскейла (2 или 4)"""
    return 4 if 'x4' in text.lower() else 2


def get_imagen_model(text: str, default_model: str) -> str:
    """Определить модель Imagen"""
    from config import IMAGE_MODEL_IMAGEN_ULTRA, IMAGE_MODEL_IMAGEN_FAST
    low_text = text.lower()

    if has_trigger(low_text, IMAGEN_ULTRA_TRIGGERS):
        return IMAGE_MODEL_IMAGEN_ULTRA
    elif has_trigger(low_text, IMAGEN_FAST_TRIGGERS):
        return IMAGE_MODEL_IMAGEN_FAST
    return default_model


def get_retouch_mode(text: str) -> str:
    """Определить режим ретуши"""
    low_text = text.lower()
    if has_trigger(low_text, RETOUCH_SMOOTH_TRIGGERS):
        return 'smooth'
    return 'pro'
