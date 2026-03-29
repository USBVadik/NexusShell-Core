"""
trend_hunter.py — USBAGENT Trend Hunter v4.0

Scans for asymmetric leverage signals across AI, Crypto, OSINT, and Tech
using Gemini Search Grounding. God Mode persona maintained throughout.
"""

import asyncio
import json
import re
import time
from datetime import datetime

from google.genai import types

from core.brain import client
from config import STABLE_MODEL
from core.logger import trend_logger

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TREND_DOMAINS = ["AI", "Crypto", "OSINT", "Tech"]

GROUNDING_SCAN_PROMPT = """
You are USBAGENT — an elite intelligence operator with God Mode access to global information flows.
Today is {date}.

Your mission: Scan the current information landscape across these domains: AI, Crypto, OSINT, Tech.

Using your real-time search access, identify:
1. What topics are SURGING right now (last 24-72 hours)?
2. What narratives are being discussed in elite circles but haven't hit mainstream yet?
3. What technical breakthroughs, protocol launches, or geopolitical shifts are creating asymmetric opportunities?
4. What are the most discussed projects, tools, or events in each domain?

Focus on 2026 context. Be specific — name actual projects, protocols, people, events.
Return raw intelligence data as a structured list. Be brutally honest and precise.
No fluff. Operator-grade intel only.

Format each signal as:
SIGNAL: [name]
DOMAIN: [AI/Crypto/OSINT/Tech]
MOMENTUM: [description of current momentum]
SOURCE_INDICATORS: [what signals indicate this is rising]
"""

ANALYSIS_PROMPT = """
You are USBAGENT — God Mode intelligence analyst.

Here is raw trend intelligence data:
{raw_data}

Your mission: Identify ASYMMETRIC LEVERAGE opportunities — topics that are:
- Rising fast but NOT yet saturated in mainstream media
- Have high narrative potential (people will want to talk about this)
- Create actionable content/business opportunities RIGHT NOW

For each signal, output EXACTLY this format (JSON array):

[
  {{
    "signal_name": "Name of the trend/topic",
    "domain": "AI|Crypto|OSINT|Tech",
    "twitter_score": 8,
    "narrative": "Why this matters RIGHT NOW — the deeper story, the asymmetric angle, why 99% haven't caught on yet",
    "actionable_idea": "Specific action: e.g. 'Make a VEO video about X', 'Write a thread about Y', 'Build a tool for Z'",
    "saturation_level": "low|medium|high",
    "time_window": "How long this window stays open (e.g. '48 hours', '2 weeks')"
  }}
]

Rules:
- twitter_score: 0-10 based on virality potential (10 = guaranteed viral)
- Only include signals with twitter_score >= 6
- Maximum 7 signals
- Prioritize LOW saturation signals
- Be SPECIFIC. No generic advice. Name real projects, real people, real events.
- Maintain God Mode persona: direct, confident, no hedging

Return ONLY the JSON array. No markdown, no explanation.
"""

BRIEF_HEADER = """
⚡️ *USBAGENT SIGNAL BRIEF* ⚡️
`{timestamp}`
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 *ASYMMETRIC LEVERAGE REPORT*
Domains: AI · Crypto · OSINT · Tech

"""

BRIEF_SIGNAL_TEMPLATE = """
{index}. 🔥 *{signal_name}*
   📡 Domain: `{domain}`
   📊 Twitter Score: `{twitter_score}/10`
   ⏳ Window: `{time_window}` | Saturation: `{saturation_level}`

   💡 *Narrative:*
   _{narrative}_

   ⚡ *Action:*
   `{actionable_idea}`
"""

BRIEF_FOOTER = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 *God Mode Intel — USBAGENT v4.0*
_Next scan in 12 hours_
"""

_SAFETY_SETTINGS = [
    types.SafetySetting(
        category='HARM_CATEGORY_HATE_SPEECH',
        threshold='BLOCK_ONLY_HIGH'
    ),
    types.SafetySetting(
        category='HARM_CATEGORY_DANGEROUS_CONTENT',
        threshold='BLOCK_ONLY_HIGH'
    ),
    types.SafetySetting(
        category='HARM_CATEGORY_HARASSMENT',
        threshold='BLOCK_ONLY_HIGH'
    ),
    types.SafetySetting(
        category='HARM_CATEGORY_SEXUALLY_EXPLICIT',
        threshold='BLOCK_ONLY_HIGH'
    ),
]


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

async def get_daily_signals() -> str:
    """
    Use Gemini Search Grounding to scan for trending topics.
    Returns raw intelligence data as a string.
    """
    trend_logger.info("TrendHunter: Starting daily signal scan...")

    today = datetime.now().strftime("%B %d, %Y")
    prompt = GROUNDING_SCAN_PROMPT.format(date=today)

    try:
        google_search_tool = types.Tool(google_search=types.GoogleSearch())

        res = await client.aio.models.generate_content(
            model=STABLE_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[google_search_tool],
                temperature=0.7,
                max_output_tokens=2048,
                safety_settings=_SAFETY_SETTINGS,
            ),
        )

        raw_data = res.text if res.text else ""
        trend_logger.info(f"TrendHunter: Raw scan complete, {len(raw_data)} chars")
        return raw_data

    except Exception as e:
        trend_logger.error(f"TrendHunter: get_daily_signals error: {e}", exc_info=True)
        # Fallback without grounding
        try:
            trend_logger.info("TrendHunter: Falling back to non-grounded scan...")
            res = await client.aio.models.generate_content(
                model=STABLE_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.8,
                    max_output_tokens=2048,
                    safety_settings=_SAFETY_SETTINGS,
                ),
            )
            return res.text if res.text else ""
        except Exception as e2:
            trend_logger.error(f"TrendHunter: Fallback also failed: {e2}", exc_info=True)
            return ""


async def analyze_signals(raw_data: str) -> list[dict]:
    """
    Analyze raw trend data to identify asymmetric leverage opportunities.
    Returns a list of signal dicts.
    """
    if not raw_data or len(raw_data.strip()) < 50:
        trend_logger.warning("TrendHunter: Raw data too short for analysis")
        return []

    trend_logger.info("TrendHunter: Analyzing signals for asymmetric leverage...")

    prompt = ANALYSIS_PROMPT.format(raw_data=raw_data[:4000])

    try:
        res = await client.aio.models.generate_content(
            model=STABLE_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.4,
                max_output_tokens=2048,
                safety_settings=_SAFETY_SETTINGS,
            ),
        )

        response_text = res.text if res.text else ""

        # Extract JSON array — handle potential markdown code fences
        match = re.search(r'\[.*?\]', response_text, re.DOTALL)
        if not match:
            trend_logger.error("TrendHunter: No JSON array found in analysis response")
            trend_logger.debug(f"TrendHunter: Raw response was: {response_text[:300]}")
            return []

        signals = json.loads(match.group())

        if not isinstance(signals, list):
            trend_logger.error("TrendHunter: Parsed JSON is not a list")
            return []

        # Validate and filter
        valid_signals = []
        for s in signals:
            if not isinstance(s, dict):
                continue
            required_keys = ['signal_name', 'domain', 'twitter_score', 'narrative', 'actionable_idea']
            if not all(k in s for k in required_keys):
                trend_logger.warning(f"TrendHunter: Signal missing required keys: {s.keys()}")
                continue
            try:
                s['twitter_score'] = int(s['twitter_score'])
            except (ValueError, TypeError):
                s['twitter_score'] = 5
            # Ensure optional fields have defaults
            s.setdefault('saturation_level', 'medium')
            s.setdefault('time_window', 'unknown')
            if s['twitter_score'] >= 6:
                valid_signals.append(s)

        # Sort by twitter_score descending
        valid_signals.sort(key=lambda x: x.get('twitter_score', 0), reverse=True)

        trend_logger.info(f"TrendHunter: Found {len(valid_signals)} valid signals")
        return valid_signals[:7]

    except json.JSONDecodeError as e:
        trend_logger.error(f"TrendHunter: JSON parse error in analysis: {e}")
        return []
    except Exception as e:
        trend_logger.error(f"TrendHunter: analyze_signals error: {e}", exc_info=True)
        return []


def format_signal_brief(signals: list[dict]) -> str:
    """
    Format signals into a God Mode Signal Brief for Telegram.
    Returns formatted Markdown string.
    """
    if not signals:
        return (
            "⚡️ *USBAGENT SIGNAL BRIEF*\n\n"
            "🔴 *No high-leverage signals detected this cycle.*\n"
            "_Markets are quiet. Stay ready._\n\n"
            "🧠 *God Mode Intel — USBAGENT v4.0*"
        )

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    brief = BRIEF_HEADER.format(timestamp=timestamp)

    for i, signal in enumerate(signals, 1):
        saturation_emoji = {
            'low': '🟢',
            'medium': '🟡',
            'high': '🔴',
        }.get(signal.get('saturation_level', 'medium'), '🟡')

        brief += BRIEF_SIGNAL_TEMPLATE.format(
            index=i,
            signal_name=signal.get('signal_name', 'Unknown'),
            domain=signal.get('domain', 'Tech'),
            twitter_score=signal.get('twitter_score', 0),
            time_window=signal.get('time_window', 'Unknown'),
            saturation_level=f"{saturation_emoji} {signal.get('saturation_level', 'medium')}",
            narrative=signal.get('narrative', ''),
            actionable_idea=signal.get('actionable_idea', ''),
        )

    brief += BRIEF_FOOTER
    return brief


async def run_full_scan() -> str:
    """
    Run a complete trend scan: get signals → analyze → format brief.
    Returns formatted brief string ready to send to Telegram.
    """
    trend_logger.info("TrendHunter: Running full scan pipeline...")

    try:
        raw_data = await get_daily_signals()

        if not raw_data:
            return (
                "⚡️ *USBAGENT SIGNAL BRIEF*\n\n"
                "🔴 *Scan failed — no data retrieved.*\n"
                "_Check Gemini API connectivity._\n\n"
                "🧠 *God Mode Intel — USBAGENT v4.0*"
            )

        signals = await analyze_signals(raw_data)
        brief = format_signal_brief(signals)

        trend_logger.info(f"TrendHunter: Full scan complete, {len(signals)} signals")
        return brief

    except Exception as e:
        trend_logger.error(f"TrendHunter: run_full_scan error: {e}", exc_info=True)
        return (
            f"⚡️ *USBAGENT SIGNAL BRIEF*\n\n"
            f"🔴 *Scan error:* `{str(e)[:100]}`\n\n"
            f"🧠 *God Mode Intel — USBAGENT v4.0*"
        )
