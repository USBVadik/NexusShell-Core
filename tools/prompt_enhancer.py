"""
Prompt enhancer — upgrades user prompts for Imagen / Gemini / Veo.
USB BOT V3.2
"""
from __future__ import annotations

import asyncio
import json
import os

from core.brain import client
from config import STABLE_MODEL, USER_STYLE_PRESET, STYLE_FILE

# ── Intent classification prompt ──────────────────────────────────────────────

INTENT_PROMPT = (
    'Analyze this image request and return ONLY valid JSON, no markdown:\n'
    '{"style":"candid|editorial|cinematic|commercial|artistic",'
    '"realism":"candid|photoreal|hyperreal|stylized",'
    '"subject":"person|landscape|product|animal|abstract",'
    '"lighting":"natural|golden_hour|indoor_ambient|studio|dramatic",'
    '"avoid":["list","of","bad","tags"]}'
)

# ── Style templates ───────────────────────────────────────────────────────────

STYLE_TEMPLATES: dict[str, str] = {
    "candid": (
        "handheld shot, candid documentary photography, from stills archive, "
        "f/1.8 natural ambient light, visible skin pores and texture, slight film grain, "
        "no retouching, no studio setup, raw unedited capture, imperfect real-world lighting, "
        "authentic moment"
    ),
    "editorial": (
        "85mm f/1.4 portrait lens, shallow depth of field, professional editorial photography, "
        "soft diffused light, magazine quality, natural skin texture, muted color grading"
    ),
    "cinematic": (
        "anamorphic 35mm lens, cinematic color grade, film stock texture, dramatic lighting setup, "
        "movie still, shallow depth of field, atmospheric haze"
    ),
    "commercial": (
        "product hero shot, clean sharp focus, professional studio lighting, high contrast, "
        "commercial photography, pristine quality"
    ),
    "artistic": (
        "artistic composition, intentional color palette, fine art photography, "
        "deliberate aesthetic choices, creative lighting"
    ),
}

NEGATIVE_MAP: dict[str, str] = {
    "candid":     "no plastic skin, no airbrushing, no CGI, no studio lighting, no perfect symmetry, no hyperrealistic render, no artificial shine",
    "editorial":  "no over-retouching, no plastic skin, no harsh flash",
    "cinematic":  "no flat lighting, no amateur framing, no overexposure",
    "commercial": "no noise, no blur, no lens distortion",
    "artistic":   "no cliché, no overprocessed HDR",
}

# ── Style file helpers ────────────────────────────────────────────────────────

# Lock protects concurrent reads/writes to the style file
_style_lock = asyncio.Lock()


def load_user_style() -> str:
    """Read the persisted user style (synchronous, safe for single-file access)."""
    try:
        if os.path.exists(STYLE_FILE):
            with open(STYLE_FILE, 'r', encoding='utf-8') as fh:
                return fh.read().strip()
    except OSError:
        pass
    return USER_STYLE_PRESET


def save_user_style(style: str) -> None:
    """Atomically write the user style to disk."""
    tmp = STYLE_FILE + '.tmp'
    try:
        with open(tmp, 'w', encoding='utf-8') as fh:
            fh.write(style.strip())
        os.replace(tmp, STYLE_FILE)
    except OSError as exc:
        # Clean up orphaned tmp if something went wrong
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass
        raise exc


# ── Intent classifier ─────────────────────────────────────────────────────────

async def classify_intent(text: str) -> dict:
    """Ask Gemini to classify the visual intent of a prompt."""
    try:
        res = await client.aio.models.generate_content(
            model=STABLE_MODEL,
            contents=f"{INTENT_PROMPT}\n\nRequest: {text}",
        )
        raw = res.text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception:
        return {
            "style":    "editorial",
            "realism":  "photoreal",
            "subject":  "person",
            "lighting": "natural",
            "avoid":    [],
        }


# ── Main enhancer ─────────────────────────────────────────────────────────────

_CLEAN_TRIGGERS = [
    "сгенерируй фото", "сгенерируй", "нарисуй", "draw",
    "generate", "создай фото", "нанобанана",
]


async def enhance_prompt(user_text: str, mode: str = "imagen_generate") -> str:
    """
    Enhance a user prompt for the given generation mode.

    Modes:
        imagen_generate — full Imagen 4 prompt engineering
        imagen_edit     — surgical photo-editing instruction
        veo             — cinematic shot description for Veo 3
    """
    if not user_text or len(user_text) < 2:
        return user_text

    use_style  = "мойпромт" in user_text.lower()
    clean_text = user_text.lower().replace("мойпромт", "").strip()
    for trigger in _CLEAN_TRIGGERS:
        clean_text = clean_text.replace(trigger, "").strip()

    # Optionally inject the user's saved visual style
    style_hint = ""
    if use_style:
        style = load_user_style()
        if style:
            style_hint = f"\nApply this visual style: {style}"

    # ── imagen_generate ───────────────────────────────────────────────────────
    if mode == "imagen_generate":
        intent           = await classify_intent(clean_text)
        detected_style   = intent.get("style",   "editorial")
        detected_lighting = intent.get("lighting", "natural")
        style_block      = STYLE_TEMPLATES.get(detected_style, STYLE_TEMPLATES["editorial"])
        negative_block   = NEGATIVE_MAP.get(detected_style, "")

        build_prompt = (
            f"You are an elite Imagen 4 Ultra prompt engineer.\n"
            f"Detected intent: style={detected_style}, lighting={detected_lighting}\n"
            f"Rules:\n"
            f"1. Preserve 100% of user details — every word, every specific.\n"
            f"2. Add this style layer: {style_block}\n"
            f"3. Append negative constraints naturally: {negative_block}\n"
            f"4. If user prompt is already 300+ chars and technical — add max 1 sentence only.\n"
            f"5. Output ONLY the final English prompt. No explanations, no markdown.{style_hint}"
        )
        try:
            res = await client.aio.models.generate_content(
                model=STABLE_MODEL,
                contents=f"{build_prompt}\n\nUser request: {clean_text}",
            )
            enhanced = res.text.strip()
            print(
                f"[ENHANCER] intent={detected_style}/{detected_lighting} | "
                f"'{clean_text[:50]}' → '{enhanced[:120]}'"
            )
            return enhanced if enhanced else clean_text
        except Exception as exc:
            print(f"[ENHANCER] imagen_generate error: {exc}")
            return clean_text

    # ── imagen_edit ───────────────────────────────────────────────────────────
    if mode == "imagen_edit":
        edit_prompt = (
            "You are a professional photo retouching director.\n"
            "Rules:\n"
            "1. Preserve everything NOT mentioned for change.\n"
            "2. Be surgical: describe exactly what changes and what stays.\n"
            "3. Include: lighting consistency, skin texture preservation, realism anchors.\n"
            "4. If prompt is already detailed — keep 90%, only add realism constraints.\n"
            "5. Output ONLY the English editing instruction. No markdown, no explanations."
        )
        try:
            res = await client.aio.models.generate_content(
                model=STABLE_MODEL,
                contents=f"{edit_prompt}\n\nUser request: {clean_text}",
            )
            enhanced = res.text.strip()
            print(f"[ENHANCER] edit | '{clean_text[:50]}' → '{enhanced[:120]}'")
            return enhanced if enhanced else clean_text
        except Exception as exc:
            print(f"[ENHANCER] imagen_edit error: {exc}")
            return clean_text

    # ── veo ───────────────────────────────────────────────────────────────────
    if mode == "veo":
        veo_prompt = (
            "You are an award-winning cinematographer writing for Veo 3.\n"
            "Include: camera movement (dolly/pan/tracking), focal length, lighting type, "
            "color grade, atmosphere, subject action.\n"
            "Start with camera movement. Output ONLY the English shot description."
        )
        try:
            res = await client.aio.models.generate_content(
                model=STABLE_MODEL,
                contents=f"{veo_prompt}\n\nUser request: {clean_text}",
            )
            enhanced = res.text.strip()
            print(f"[ENHANCER] veo | '{clean_text[:50]}' → '{enhanced[:120]}'")
            return enhanced if enhanced else clean_text
        except Exception as exc:
            print(f"[ENHANCER] veo error: {exc}")
            return clean_text

    # Fallback — unknown mode
    return clean_text
