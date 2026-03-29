"""
Обработчик инструментов для работы с изображениями
OCR, Retouch, Upscale, Outpaint
USB BOT V3.1
"""
import os
import uuid
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes
from core.logger import router_logger
from core.triggers import (
    has_trigger, OCR_TRIGGERS, RETOUCH_TRIGGERS, UPSCALE_TRIGGERS,
    OUTPAINT_TRIGGERS, get_retouch_mode, get_upscale_mode,
    get_upscale_factor, get_aspect_ratio
)
from tools.image import extract_text_from_image, retouch_face_pro, outpaint_image
from tools.upscale import enhance_image


async def handle_ocr(update: Update, context: ContextTypes.DEFAULT_TYPE, img_bytes: bytearray) -> bool:
    """Обработка OCR запроса"""
    try:
        router_logger.info("Processing OCR request")
        ocr_text = await extract_text_from_image(img_bytes)
        await update.message.reply_text(f"📖 Извлеченный текст:\n\n{ocr_text}")
        return True
    except Exception as e:
        router_logger.error(f"OCR error: {e}", exc_info=True)
        await update.message.reply_text("❌ Ошибка при распознавании текста")
        return False


async def handle_retouch(update: Update, context: ContextTypes.DEFAULT_TYPE, img_bytes: bytearray, text: str) -> bool:
    """Обработка ретуши лица"""
    try:
        await context.bot.send_chat_action(update.effective_chat.id, ChatAction.UPLOAD_PHOTO)

        mode = get_retouch_mode(text)
        router_logger.info(f"Processing retouch request: mode={mode}")

        path = await retouch_face_pro(img_bytes, mode=mode)
        if path:
            with open(path, 'rb') as f:
                await update.message.reply_photo(photo=f, caption=f'✨ Pro Retouch ({mode})')
            os.remove(path)
            return True
        else:
            await update.message.reply_text("❌ Ошибка при ретуши")
            return False
    except Exception as e:
        router_logger.error(f"Retouch error: {e}", exc_info=True)
        await update.message.reply_text("❌ Ошибка при ретуши")
        return False


async def handle_upscale(update: Update, context: ContextTypes.DEFAULT_TYPE, img_bytes: bytearray, text: str) -> bool:
    """Обработка апскейла изображения"""
    tmp_in = f"/tmp/in_{uuid.uuid4().hex}.jpg"
    res_path = None

    try:
        await context.bot.send_chat_action(update.effective_chat.id, ChatAction.UPLOAD_PHOTO)

        mode = get_upscale_mode(text)
        factor = get_upscale_factor(text)

        router_logger.info(f"Processing upscale: mode={mode}, factor=x{factor}")

        with open(tmp_in, "wb") as f:
            f.write(bytes(img_bytes))

        res_path = await enhance_image(tmp_in, factor=factor, mode=mode)

        if res_path and os.path.exists(res_path):
            with open(res_path, "rb") as f:
                if factor == 4:
                    await update.message.reply_document(document=f, caption=f"✨ x{factor} ({mode})")
                else:
                    await update.message.reply_photo(photo=f, caption=f"✨ x{factor} ({mode})")
            router_logger.info(f"Upscale successful: mode={mode}, factor=x{factor}")
            return True
        else:
            await update.message.reply_text("❌ Ошибка при апскейле")
            return False

    except Exception as e:
        router_logger.error(f"Upscale error: {e}", exc_info=True)
        await update.message.reply_text("❌ Ошибка при апскейле")
        return False

    finally:
        # Гарантированная очистка временных файлов
        for path in (tmp_in, res_path):
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError as e:
                    router_logger.warning(f"Failed to remove temp file {path}: {e}")


async def handle_outpaint(update: Update, context: ContextTypes.DEFAULT_TYPE, img_bytes: bytearray, text: str) -> bool:
    """Обработка outpaint (расширение изображения)"""
    try:
        await context.bot.send_chat_action(update.effective_chat.id, ChatAction.UPLOAD_PHOTO)

        aspect = get_aspect_ratio(text)
        router_logger.info(f"Processing outpaint: aspect={aspect}")

        path = await outpaint_image(img_bytes, prompt=text, aspect=aspect)
        if path:
            with open(path, 'rb') as f:
                await update.message.reply_photo(photo=f, caption=f'🖼 Outpaint ({aspect}) Done')
            os.remove(path)
            return True
        else:
            await update.message.reply_text("❌ Ошибка при расширении изображения")
            return False

    except Exception as e:
        router_logger.error(f"Outpaint error: {e}", exc_info=True)
        await update.message.reply_text("❌ Ошибка при расширении изображения")
        return False


async def process_image_tools(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    img_bytes: bytearray,
    text: str,
) -> bool:
    """
    Главная функция обработки image tools.
    Возвращает True если запрос обработан, False если нужно продолжить.
    """
    if not img_bytes:
        return False

    low_text = text.lower()

    # OCR
    if has_trigger(low_text, OCR_TRIGGERS):
        return await handle_ocr(update, context, img_bytes)

    # Retouch
    if has_trigger(low_text, RETOUCH_TRIGGERS):
        return await handle_retouch(update, context, img_bytes, text)

    # Upscale
    if has_trigger(low_text, UPSCALE_TRIGGERS):
        return await handle_upscale(update, context, img_bytes, text)

    # Outpaint
    if has_trigger(low_text, OUTPAINT_TRIGGERS):
        return await handle_outpaint(update, context, img_bytes, text)

    return False
