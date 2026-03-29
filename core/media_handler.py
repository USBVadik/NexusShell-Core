"""
Обработчик медиа-контента: фото, видео, аудио, документы
USB BOT V3.1
"""
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from core.logger import media_logger
from tools.memes import save_meme
from tools.docs import process_document
from tools.voice import transcribe_audio

# ---------------------------------------------------------------------------
# Константы для сборки альбомов
# ---------------------------------------------------------------------------

# Ключ в bot_data для хранения накопленных альбомов
_ALBUM_STORE_KEY = '_media_group_store'

# Сколько секунд ждём все части альбома перед обработкой
_ALBUM_COLLECT_TIMEOUT = 1.5


class MediaData:
    """Структура для хранения медиа-данных"""
    def __init__(self):
        self.img_bytes: bytearray | None = None
        self.video_bytes: bytearray | None = None
        self.text_addition: str = ""
        # Список всех фото из альбома (media group).
        # Заполняется только если сообщение является частью альбома с фото.
        # img_bytes при этом указывает на первое фото (для обратной совместимости).
        self.img_bytes_list: list[bytearray] = []


async def extract_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> MediaData:
    """
    Извлекает медиа из сообщения или reply.
    Возвращает MediaData с заполненными полями.

    Если сообщение является частью media group (альбома), пытается собрать
    все фото альбома в img_bytes_list. img_bytes при этом = img_bytes_list[0].
    """
    media = MediaData()
    target_msg = update.message

    try:
        # ------------------------------------------------------------------
        # Альбом (media group) — собираем все фото
        # ------------------------------------------------------------------
        if target_msg.media_group_id and target_msg.photo:
            album_photos = await _collect_album_photos(
                update, context, target_msg.media_group_id
            )
            if album_photos:
                media.img_bytes_list = album_photos
                media.img_bytes = album_photos[0]
                media_logger.info(
                    f"Album collected: {len(album_photos)} photos "
                    f"(media_group_id={target_msg.media_group_id})"
                )
                return media

        # ------------------------------------------------------------------
        # Одиночное сообщение
        # ------------------------------------------------------------------
        if target_msg.photo:
            media.img_bytes = await _download_photo(target_msg.photo[-1].file_id, context)
            media.img_bytes_list = [media.img_bytes]
            media_logger.info("Detected photo in message")

        elif target_msg.sticker:
            await save_meme(target_msg.sticker.file_id, 'sticker', target_msg.sticker.emoji)
            media.text_addition = f'[STICKER: {target_msg.sticker.emoji}]'
            media_logger.info(f"Saved sticker: {target_msg.sticker.emoji}")

        elif target_msg.animation:
            media.video_bytes = await _download_file(target_msg.animation.file_id, context)
            await save_meme(target_msg.animation.file_id, 'gif')
            media_logger.info("Detected GIF animation")

        elif target_msg.video:
            media.video_bytes = await _download_file(target_msg.video.file_id, context)
            media_logger.info("Detected video")

        elif target_msg.voice or target_msg.audio:
            file_id = (target_msg.voice or target_msg.audio).file_id
            audio_bytes = await _download_file(file_id, context)

            # Транскрибируем аудио
            transcribed_text = await transcribe_audio(bytes(audio_bytes))
            # Проверяем что транскрипция успешна и не содержит ошибок
            if transcribed_text and not transcribed_text.startswith('[Не удалось') and not transcribed_text.startswith('[Ошибка'):
                # Добавляем префикс чтобы бот понимал что это транскрипция
                media.text_addition = f"[Голосовое сообщение]: {transcribed_text}"
                media_logger.info(f"Transcribed audio: {transcribed_text[:50]}...")
            else:
                media_logger.warning(f"Audio transcription failed: {transcribed_text}")

        elif target_msg.document:
            if target_msg.document.mime_type.startswith('image/'):
                media.img_bytes = await _download_file(target_msg.document.file_id, context)
                media.img_bytes_list = [media.img_bytes]
                media_logger.info("Detected image document")
            else:
                doc_bytes = await _download_file(target_msg.document.file_id, context)
                doc_text = await process_document(doc_bytes, target_msg.document.mime_type, target_msg.document.file_name)
                media.text_addition = f'[ДОКУМЕНТ: {target_msg.document.file_name}]\n{doc_text}'
                media_logger.info(f"Processed document: {target_msg.document.file_name}")

        # Проверка reply сообщения
        if not media.img_bytes and not media.video_bytes and target_msg.reply_to_message:
            reply_media = await _extract_from_reply(target_msg.reply_to_message, context)
            media.img_bytes = reply_media.img_bytes or media.img_bytes
            media.img_bytes_list = reply_media.img_bytes_list or media.img_bytes_list
            media.video_bytes = reply_media.video_bytes or media.video_bytes
            if reply_media.text_addition:
                media.text_addition = reply_media.text_addition
            if reply_media.img_bytes or reply_media.video_bytes:
                media_logger.info("Extracted media from reply message")

    except Exception as e:
        media_logger.error(f"Error extracting media: {e}", exc_info=True)

    return media


async def _collect_album_photos(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    media_group_id: str,
) -> list[bytearray]:
    """
    Собирает все фото из Telegram media group (альбома).

    Telegram присылает фото альбома как отдельные сообщения с одинаковым
    media_group_id. Мы накапливаем file_id в bot_data и ждём _ALBUM_COLLECT_TIMEOUT
    секунд, чтобы собрать все части.

    Возвращает список bytearray (по одному на каждое фото альбома),
    отсортированных по message_id (порядок отправки).
    """
    store: dict = context.bot_data.setdefault(_ALBUM_STORE_KEY, {})

    msg = update.message
    if not msg.photo:
        return []

    # Сохраняем (message_id, file_id) для этого альбома
    entry = store.setdefault(media_group_id, {'items': [], 'event': None})
    entry['items'].append((msg.message_id, msg.photo[-1].file_id))

    # Создаём asyncio.Event для координации между параллельными вызовами
    if entry['event'] is None:
        entry['event'] = asyncio.Event()

    event: asyncio.Event = entry['event']

    # Ждём таймаут — за это время придут остальные части альбома
    try:
        await asyncio.wait_for(event.wait(), timeout=_ALBUM_COLLECT_TIMEOUT)
    except asyncio.TimeoutError:
        # Таймаут истёк — сигнализируем остальным ожидающим что сбор завершён
        event.set()

    # Только первый вызов (с наименьшим message_id) скачивает все фото
    items: list[tuple[int, str]] = entry['items']
    items_sorted = sorted(items, key=lambda x: x[0])

    # Проверяем, является ли текущее сообщение первым в альбоме
    is_first = items_sorted[0][0] == msg.message_id

    if not is_first:
        # Остальные вызовы просто возвращают пустой список —
        # первый вызов уже обработает весь альбом
        media_logger.debug(
            f"Album {media_group_id}: skipping non-first message {msg.message_id}"
        )
        return []

    # Скачиваем все фото альбома
    media_logger.info(
        f"Album {media_group_id}: downloading {len(items_sorted)} photos "
        f"(message_ids={[i[0] for i in items_sorted]})"
    )

    photo_bytes_list: list[bytearray] = []
    for _, file_id in items_sorted:
        try:
            photo_bytes = await _download_photo(file_id, context)
            photo_bytes_list.append(photo_bytes)
        except Exception as e:
            media_logger.error(
                f"Album {media_group_id}: failed to download file_id={file_id}: {e}",
                exc_info=True,
            )

    # Очищаем store чтобы не копить память
    store.pop(media_group_id, None)

    media_logger.info(
        f"Album {media_group_id}: collected {len(photo_bytes_list)} photos successfully"
    )
    return photo_bytes_list


async def _extract_from_reply(reply_msg, context: ContextTypes.DEFAULT_TYPE) -> MediaData:
    """Извлечь медиа из reply сообщения"""
    media = MediaData()

    try:
        if reply_msg.photo:
            media.img_bytes = await _download_photo(reply_msg.photo[-1].file_id, context)
            media.img_bytes_list = [media.img_bytes]
        elif reply_msg.animation:
            media.video_bytes = await _download_file(reply_msg.animation.file_id, context)
        elif reply_msg.video:
            media.video_bytes = await _download_file(reply_msg.video.file_id, context)
        elif reply_msg.voice or reply_msg.audio:
            file_id = (reply_msg.voice or reply_msg.audio).file_id
            audio_bytes = await _download_file(file_id, context)

            # Транскрибируем аудио из reply
            transcribed_text = await transcribe_audio(bytes(audio_bytes))
            if transcribed_text and not transcribed_text.startswith('[Не удалось') and not transcribed_text.startswith('[Ошибка'):
                media.text_addition = f"[Голосовое из reply]: {transcribed_text}"
    except Exception as e:
        media_logger.error(f"Error extracting from reply: {e}", exc_info=True)

    return media


async def _download_photo(file_id: str, context: ContextTypes.DEFAULT_TYPE) -> bytearray:
    """Скачать фото"""
    file = await context.bot.get_file(file_id)
    return await file.download_as_bytearray()


async def _download_file(file_id: str, context: ContextTypes.DEFAULT_TYPE) -> bytearray:
    """Скачать файл"""
    file = await context.bot.get_file(file_id)
    return await file.download_as_bytearray()


async def detect_multi_photo_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> tuple[bytearray, bytearray] | None:
    """
    Определяет multi-photo edit (2 фото: base + reference).

    Проверяет два сценария:
    1. Альбом из 2 фото в одном сообщении (media_group_id).
    2. Фото в текущем сообщении + фото в reply (старое поведение).

    Возвращает (base_bytes, ref_bytes) или None.
    """
    target_msg = update.message

    try:
        # Сценарий 1: альбом из 2+ фото
        if target_msg.media_group_id and target_msg.photo:
            album = await _collect_album_photos(update, context, target_msg.media_group_id)
            if len(album) >= 2:
                media_logger.info(
                    f"detect_multi_photo_edit: album with {len(album)} photos detected"
                )
                return album[0], album[1]

        # Сценарий 2: фото в сообщении + фото в reply (оригинальное поведение)
        if target_msg.photo and target_msg.reply_to_message and target_msg.reply_to_message.photo:
            base_img = await _download_photo(target_msg.reply_to_message.photo[-1].file_id, context)
            ref_img = await _download_photo(target_msg.photo[-1].file_id, context)
            media_logger.info("detect_multi_photo_edit: reply+photo scenario detected")
            return base_img, ref_img

    except Exception as e:
        media_logger.error(f"Error detecting multi-photo: {e}", exc_info=True)

    return None
