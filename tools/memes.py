import json, random, asyncio
from google.genai import types
from config import MEMES_DB, STABLE_MODEL
from core.brain import client, get_meme_vibe_col, load_json, save_json

async def tag_meme_vibe(media_id, media_type, media_bytes):
    try:
        # FIX #9: правильный MIME для стикеров — webp
        mime = 'image/webp' if media_type == 'stickers' else 'video/mp4'
        res = await client.aio.models.generate_content(
            model=STABLE_MODEL,
            contents=[
                types.Part.from_bytes(data=bytes(media_bytes), mime_type=mime),
                "Describe the vibe of this meme in 3 keywords."
            ]
        )
        vibe = res.text.strip()
        col = get_meme_vibe_col()
        if col is not None:
            col.add(
                documents=[vibe],
                ids=[media_id],
                metadatas=[{"type": media_type}]
            )
    except Exception:
        pass

async def save_meme(media_id, media_type, media_bytes=None):
    db = load_json(MEMES_DB, {"stickers": {"general": []}, "gifs": {"general": []}})
    if media_id not in db.get(media_type, {}).get("general", []):
        if media_type not in db:
            db[media_type] = {"general": []}
        db[media_type]["general"].append(media_id)
        save_json(MEMES_DB, db)
        if media_bytes:
            # FIX #5: держим ссылку на таск
            t = asyncio.create_task(tag_meme_vibe(media_id, media_type, media_bytes))
            t.add_done_callback(lambda _: None)

async def trigger_meme_if_needed(reply_text, update):
    if any(w in reply_text.lower() for w in ["ору", "ахах", "жесть", "мда", "топ", "бутерин", "смешно", "лол", "кек"]):
        db = load_json(MEMES_DB, {})
        m_type = random.choice(["stickers", "gifs"])
        if db.get(m_type, {}).get("general"):
            m_id = random.choice(db[m_type]["general"])
            try:
                if m_type == "stickers":
                    await update.message.reply_sticker(sticker=m_id)
                else:
                    await update.message.reply_animation(animation=m_id)
            except Exception:
                pass
