import os

# ── Telegram ──────────────────────────────────────────────────────────────────
TG_TOKEN        = os.getenv('TG_TOKEN', '8712250367:AAFdou4vYwTMaQAKeWVQDCfXxvfmG4iZ_Eo')
ALLOWED_USER_ID = int(os.getenv('ALLOWED_USER_ID', '213133014'))

# ── Google Cloud ──────────────────────────────────────────────────────────────
PROJECT_ID      = os.getenv('GCLOUD_PROJECT', 'usbtest-490122')
LOCATION        = os.getenv('GCLOUD_LOCATION', 'us-central1')
LOCATION_GLOBAL = 'global'
KEY_PATH        = os.getenv('GOOGLE_KEY_PATH', '/root/hero_key.json')

# ── Models ────────────────────────────────────────────────────────────────────
STABLE_MODEL             = 'publishers/google/models/gemini-2.5-flash'
IMAGE_MODEL              = os.getenv('IMAGE_MODEL', 'publishers/google/models/gemini-2.5-flash-image')
IMAGE_MODEL_EDIT         = 'publishers/google/models/gemini-3.1-flash-image-preview'
IMAGE_MODEL_IMAGEN       = 'publishers/google/models/imagen-4.0-generate-001'
IMAGE_MODEL_IMAGEN_ULTRA = 'publishers/google/models/imagen-4.0-ultra-generate-001'
IMAGE_MODEL_IMAGEN_FAST  = 'publishers/google/models/imagen-4.0-fast-generate-001'
IMAGE_MODEL_UPSCALE      = 'publishers/google/models/imagen-4.0-upscale-preview-06-06'

# ── Storage paths ─────────────────────────────────────────────────────────────
HISTORY_FILE   = os.getenv('HISTORY_FILE', '/root/usb_history.json')
MEMES_DB       = os.getenv('MEMES_DB', '/root/memes_db.json')
VOICE_REFS_DIR = os.getenv('VOICE_REFS_DIR', '/root/voice_refs')
CHROMA_PATH    = os.getenv('CHROMA_PATH', '/root/chroma_db')
GCS_BUCKET     = os.getenv('GCS_BUCKET', 'usb-bot-render-storage-usbtest')
STYLE_FILE     = os.getenv('STYLE_FILE', '/root/user_style.txt')

# ── External tools ────────────────────────────────────────────────────────────
FFMPEG_PATH    = os.getenv('FFMPEG_PATH', '/usr/bin/ffmpeg')

# ── API Keys ──────────────────────────────────────────────────────────────────
KREA_API_KEY   = os.getenv('KREA_API_KEY', '')
ELEVEN_API_KEY = os.getenv('ELEVEN_API_KEY', '')

# ── Misc ──────────────────────────────────────────────────────────────────────
# Default style preset — used as fallback when STYLE_FILE does not exist yet.
# Mirrors the content of user_style.txt on a fresh deploy.
USER_STYLE_PRESET = os.getenv(
    'USER_STYLE_PRESET',
    'natural lighting, realistic skin texture, cinematic shadows'
)

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = (
    "СЕГОДНЯШНЯЯ ДАТА: 26 марта 2026 года. Ты — USB Master, хакер-перфекционист. "
    "ПРАВИЛА КОДА: 1. В Python-скриптах используй ТОЛЬКО английский для дат и данных. "
    "2. Для графиков используй matplotlib. "
    "3. НИКОГДА не печатай base64-строки в stdout. "
    "4. Если рисуешь график — вызови plt.show() в конце. НЕ используй savefig, base64, BytesIO, "
    "print(IMAGE_BASE64). plt.show() — это всё что нужно, система сама поймает изображение. "
    "5. Не пиши в чат слишком много кода, если тебя не просили 'покажи код'. "
    "ДАННЫЕ: Если данные из поиска на русском — переведи их на английский для использования в коде. "
    "СТИЛЬ: Дерзкий, краткий, по делу. Сначала результат/график, потом едкий комментарий."
)

# ── Environment ───────────────────────────────────────────────────────────────
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = KEY_PATH
