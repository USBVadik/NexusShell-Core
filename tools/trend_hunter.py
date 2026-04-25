"""
trend_hunter.py — USBAGENT Narrative Alpha Engine v6.9 [FLASH] (Russian Edition)
"""
import asyncio, json, re, time, sys, html, os, traceback
from datetime import datetime
from google.genai import types
from core.brain import client
from config import STABLE_MODEL
from core.logger import trend_logger

# Агрессивный промпт на русском языке
SYNTHESIZER_PROMPT = """
ACT AS A VIRAL CHAOS STRATEGIST. 
Я дам тебе СЫРЫЕ ДАННЫЕ за {today}. 
Преврати их в 3 'Опасных' нарратива для X (Twitter).

STRICT RULES:
- ТОЛЬКО РУССКИЙ ЯЗЫК.
- НИКАКИХ СОВЕТОВ. НИКАКИХ 'ИССЛЕДУЙТЕ'. НИКАКИХ 'ИНВЕСТИРУЙТЕ'.
- Тон: Циничный, агрессивный, инсайдерский.
- Фокус на том, как эти события разрушают старую систему.

RAW DATA:
{raw_data}

Output JSON format:
[
  {{
    "name": "Заголовок (короткий и дерзкий)",
    "thesis": "Темная правда / Суть нарратива",
    "viral_why": "Почему это станет виральным",
    "x_post": "Хлесткий пост для X (без эмодзи, без хэштегов)"
  }}
]
"""

def _esc(text: str) -> str:
    if not text: return ""
    try:
        return html.escape(str(text), quote=True)
    except:
        return "[Error]"

def format_signal_brief(trends: list[dict]) -> str:
    if not trends: return "⚡️ <b>USBAGENT</b>\n\n🔴 <b>Нарративы не сформированы.</b>"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    brief = f"⚡️ <b>NARRATIVE ALPHA v6.9 [FLASH]</b>\n<code>{ts}</code>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for i, t in enumerate(trends, 1):
        if not isinstance(t, dict): continue
        name = _esc(t.get('name', 'Brutal Truth'))
        thesis = _esc(t.get('thesis', 'Confidential'))
        why = _esc(t.get('viral_why', 'High Tension'))
        post = _esc(t.get('x_post', 'Pending...'))
        
        brief += (
            f"<b>{i}. {name}</b>\n"
            f"🧬 <b>Тезис:</b> <i>{thesis}</i>\n"
            f"🔥 <b>Viral Edge:</b> {why}\n\n"
            f"📝 <b>X-READY POST:</b>\n<code>{post}</code>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        )
            
    return brief + "🧠 <b>Twitter Chaos Mode — USBAGENT v6.9</b>"

async def get_raw_data() -> str:
    today = datetime.now().strftime("%B %d, %Y")
    prompt = f"Search for 5 critical updates in AI and Crypto for {today}. Focus on: Binance Agentic SDK, Clanker Base fees, Virtuals Protocol GDP, ZKML developments, and GPU compute market shifts. Provide detailed facts."
    try:
        google_search_tool = types.Tool(google_search=types.GoogleSearch())
        res = await client.aio.models.generate_content(
            model=STABLE_MODEL, contents=prompt,
            config=types.GenerateContentConfig(tools=[google_search_tool], temperature=0.7)
        )
        return res.text if res.text else ""
    except:
        res = await client.aio.models.generate_content(model=STABLE_MODEL, contents=prompt)
        return res.text if res.text else ""

async def run_full_scan() -> tuple[str, list[dict]]:
    try:
        today = datetime.now().strftime("%d %B %Y")
        raw_data = await get_raw_data()
        
        if not raw_data or len(raw_data.strip()) < 50:
            return ("⚡️ <b>USBAGENT</b>\n\n🔴 Ошибка сбора данных.", [])

        prompt = SYNTHESIZER_PROMPT.format(today=today, raw_data=raw_data[:4000])
        
        res = await client.aio.models.generate_content(
            model=STABLE_MODEL, 
            contents=prompt, 
            config=types.GenerateContentConfig(temperature=0.8)
        )
        
        text = res.text
        # Очистка от markdown блоков
        text = re.sub(r'```[a-z]*\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if not match:
            return (f"🔴 Ошибка парсинга JSON. Raw: {_esc(text[:200])}", [])
            
        trends = json.loads(match.group())
        return (format_signal_brief(trends), trends)

    except Exception as e:
        err_msg = f"ERROR: {repr(e)}\\n{traceback.format_exc()[-150:]}"
        return (f"🔴 Ошибка системы: <code>{_esc(err_msg)}</code>", [])

if __name__ == "__main__":
    # Тестовый запуск
    async def test():
        brief, _ = await run_full_scan()
        print(brief)
    asyncio.run(test())
