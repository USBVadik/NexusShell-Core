"""
brain.py — NexusShell Core: ядро генерации ответов USBAGENT v4.4

Ключевые улучшения:
- Синглтон NexusShellClientManager с retry-логикой (exponential backoff)
- Атомарные записи истории через asyncio.Lock
- Чёткое разделение: загрузка/сохранение истории, ChromaDB, стриминг
- Lazy-init ChromaDB с авто-восстановлением при schema-mismatch
- Публичные алиасы/геттеры для ChromaDB-объектов (обратная совместимость)
- Memory 3.0: Deep RAG с семантическим ре-ранкингом через NexusShell Core
"""

import json
import os
import time
import asyncio
import re
import uuid
import subprocess
import sys
import shutil
from typing import AsyncGenerator, Optional, Tuple

from google import genai
from google.genai import types

from config import (
    PROJECT_ID, LOCATION, CHROMA_PATH,
    STABLE_MODEL, SYSTEM_PROMPT, HISTORY_FILE, ALLOWED_USER_ID
)
from core.logger import brain_logger

# ---------------------------------------------------------------------------
# Синглтон NexusShell Core Client с Retry-логикой
# ---------------------------------------------------------------------------

class NexusShellClientManager:
    """
    Синглтон-менеджер NexusShell Core клиента.
    Предоставляет клиент с автоматическим retry при 429/503.
    """
    _instance: Optional["NexusShellClientManager"] = None
    _client: Optional[genai.Client] = None
    _lock: asyncio.Lock = asyncio.Lock()

    # Retry-параметры
    MAX_RETRIES: int = 4
    BASE_DELAY: float = 1.5   # секунды
    MAX_DELAY: float = 30.0   # секунды
    RETRYABLE_CODES: tuple = (429, 503, 500)

    def __new__(cls) -> "NexusShellClientManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(
                vertexai=True,
                project=PROJECT_ID,
                location=LOCATION,
            )
            brain_logger.info("NexusShellClientManager: client initialised")
        return self._client

    async def generate_with_retry(
        self,
        model: str,
        contents,
        config: types.GenerateContentConfig,
    ):
        """
        Вызов generate_content с exponential backoff retry.
        Возвращает объект ответа или бросает последнее исключение.
        """
        last_exc: Optional[Exception] = None
        for attempt in range(self.MAX_RETRIES):
            try:
                return await self.client.aio.models.generate_content(
                    model=model,
                    contents=contents,
                    config=config,
                )
            except Exception as e:
                last_exc = e
                code = self._extract_code(e)
                if code not in self.RETRYABLE_CODES:
                    brain_logger.error(f"[NexusShell Core] Non-retryable error (code={code}): {e}")
                    raise
                delay = min(self.BASE_DELAY * (2 ** attempt), self.MAX_DELAY)
                brain_logger.warning(
                    f"[NexusShell Core] Retryable error (code={code}), "
                    f"attempt {attempt + 1}/{self.MAX_RETRIES}, "
                    f"retrying in {delay:.1f}s: {e}"
                )
                await asyncio.sleep(delay)
        brain_logger.error(f"[NexusShell Core] All {self.MAX_RETRIES} retries exhausted")
        raise last_exc  # type: ignore[misc]

    @staticmethod
    def _extract_code(exc: Exception) -> Optional[int]:
        """Извлечь HTTP-код из исключения."""
        msg = str(exc)
        for code in (429, 503, 500, 400, 403, 404):
            if str(code) in msg:
                return code
        return None


# Глобальный синглтон
_gemini_manager = NexusShellClientManager()
client = _gemini_manager.client  # Публичный алиас — обратная совместимость


# ---------------------------------------------------------------------------
# ChromaDB — Lazy-init с авто-восстановлением
# ---------------------------------------------------------------------------

_chromadb_lock: asyncio.Lock = asyncio.Lock()
_chroma_client = None
_collection = None
_meme_vibe_col = None
_chromadb_ready: bool = False


def _init_chromadb_sync() -> bool:
    """
    Синхронная инициализация ChromaDB.
    При schema-mismatch или любой ошибке — переименовывает повреждённую БД
    в backup и создаёт свежую.
    Возвращает True при успехе, False при неудаче.
    """
    global _chroma_client, _collection, _meme_vibe_col, _chromadb_ready

    import chromadb

    def _try_init(path: str) -> bool:
        global _chroma_client, _collection, _meme_vibe_col, _chromadb_ready
        try:
            _chroma_client = chromadb.PersistentClient(path=path)
            _collection = _chroma_client.get_or_create_collection(name='usb_memory')
            _meme_vibe_col = _chroma_client.get_or_create_collection(name='usb_memes_vibe')
            _chromadb_ready = True
            brain_logger.info(f"[NexusShell Core] ChromaDB initialised successfully at {path}")
            return True
        except Exception as e:
            brain_logger.error(f"[NexusShell Core] ChromaDB init failed at {path}: {e}", exc_info=True)
            _chromadb_ready = False
            return False

    # Первая попытка — штатная инициализация
    if _try_init(CHROMA_PATH):
        return True

    # Вторая попытка — переименовываем повреждённую БД и создаём свежую
    try:
        backup_path = f"{CHROMA_PATH}_backup_{int(time.time())}"
        if os.path.exists(CHROMA_PATH):
            shutil.move(CHROMA_PATH, backup_path)
            brain_logger.warning(
                f"[NexusShell Core] ChromaDB schema mismatch or corruption detected. "
                f"Moved old DB to {backup_path}. Creating fresh DB."
            )
        else:
            brain_logger.warning("[NexusShell Core] ChromaDB path does not exist. Creating fresh DB.")
    except Exception as move_err:
        brain_logger.error(f"[NexusShell Core] Failed to move corrupt ChromaDB: {move_err}", exc_info=True)

    # Третья попытка — свежая БД
    if _try_init(CHROMA_PATH):
        return True

    brain_logger.error("[NexusShell Core] ChromaDB is completely unavailable. Memory features disabled.")
    return False


def _ensure_chromadb() -> bool:
    """
    Гарантирует, что ChromaDB инициализирована.
    Вызывается лениво перед каждым обращением к коллекциям.
    Возвращает True если БД доступна.
    """
    global _chromadb_ready
    if _chromadb_ready and _collection is not None:
        return True
    return _init_chromadb_sync()


# ---------------------------------------------------------------------------
# Публичные геттеры ChromaDB (для импорта из других модулей)
# ---------------------------------------------------------------------------

def get_chroma_client():
    """Вернуть ChromaDB PersistentClient (с lazy-init). Может быть None."""
    _ensure_chromadb()
    return _chroma_client


def get_collection():
    """Вернуть коллекцию usb_memory (с lazy-init). Может быть None."""
    _ensure_chromadb()
    return _collection


def get_meme_vibe_col():
    """Вернуть коллекцию usb_memes_vibe (с lazy-init). Может быть None."""
    _ensure_chromadb()
    return _meme_vibe_col


# ---------------------------------------------------------------------------
# Публичные алиасы ChromaDB — обратная совместимость
# ---------------------------------------------------------------------------

try:
    _init_chromadb_sync()
except Exception as _chroma_init_err:
    brain_logger.error(f"[NexusShell Core] ChromaDB startup init exception: {_chroma_init_err}", exc_info=True)

collection = _collection
meme_vibe_col = _meme_vibe_col
chroma_client = _chroma_client


# ---------------------------------------------------------------------------
# История (JSON) — атомарные операции
# ---------------------------------------------------------------------------

_history_lock: asyncio.Lock = asyncio.Lock()
history_lock: asyncio.Lock = _history_lock

_history_cache: dict = {}
_cache_timestamp: float = 0.0
CACHE_TTL: int = 60  # секунды


def load_json(path: str, default):
    """
    Загрузить JSON с in-memory кэшем для HISTORY_FILE.
    """
    global _history_cache, _cache_timestamp

    try:
        current_time = time.time()
        if (
            path == HISTORY_FILE
            and _history_cache
            and (current_time - _cache_timestamp) < CACHE_TTL
        ):
            return _history_cache

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if path == HISTORY_FILE:
            _history_cache = data
            _cache_timestamp = current_time

        return data

    except FileNotFoundError:
        brain_logger.warning(f"[NexusShell Core] File not found: {path}, using default")
        return default
    except json.JSONDecodeError as e:
        brain_logger.error(f"[NexusShell Core] JSON decode error in {path}: {e}")
        return default
    except Exception as e:
        brain_logger.error(f"[NexusShell Core] Error loading {path}: {e}", exc_info=True)
        return default


def save_json(path: str, data) -> None:
    """
    Атомарная запись JSON через временный файл + os.replace.
    """
    global _history_cache, _cache_timestamp

    try:
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

        if path == HISTORY_FILE:
            _history_cache = data
            _cache_timestamp = time.time()

    except Exception as e:
        brain_logger.error(f"[NexusShell Core] Error saving {path}: {e}", exc_info=True)
        raise


async def load_history(uid_str: str) -> Tuple[dict, list]:
    """
    Потокобезопасная загрузка истории пользователя.
    """
    async with _history_lock:
        all_h = load_json(HISTORY_FILE, {})
        return all_h, all_h.get(uid_str, [])


async def persist_history(uid_str: str, query_text: str, full_text: str) -> None:
    """
    Потокобезопасное сохранение пары User/Bot в историю.
    Хранит последние 30 записей (15 пар).
    """
    try:
        async with _history_lock:
            all_h = load_json(HISTORY_FILE, {})
            history = all_h.get(uid_str, [])
            history.append(f'User: {query_text or "[Media]"}')
            history.append(f'Bot: {full_text[:300]}')
            all_h[uid_str] = history[-30:]
            save_json(HISTORY_FILE, all_h)
            brain_logger.debug(f"[NexusShell Core] Persisted history for user {uid_str}")
    except Exception as e:
        brain_logger.error(f"[NexusShell Core] Error persisting history: {e}", exc_info=True)


# ---------------------------------------------------------------------------
# Grounding / поиск
# ---------------------------------------------------------------------------

SEARCH_KEYWORDS = [
    'цена', 'купить', 'стоимость', 'макбук', 'м4', 'м5', 'характеристики',
    'курс', 'btc', 'eth', 'крипто', 'новост', 'сейчас', 'сегодня',
    'последн', 'вышел', 'релиз', '2026', 'актуальн', 'кто такой', 'что такое'
]


def _needs_grounding(query_text: str) -> bool:
    if not query_text:
        return False
    low = query_text.lower()
    return any(kw in low for kw in SEARCH_KEYWORDS)


# ---------------------------------------------------------------------------
# CoT (Chain-of-Thought) block stripping
# ---------------------------------------------------------------------------

# Patterns for various CoT / scratchpad / reasoning block formats that
# models may emit but should never reach the end user.
_COT_PATTERNS = [
    # XML-style thinking/reasoning/scratchpad tags (with optional attributes)
    re.compile(r'<thinking\b[^>]*>.*?</thinking>', re.DOTALL | re.IGNORECASE),
    re.compile(r'<reasoning\b[^>]*>.*?</reasoning>', re.DOTALL | re.IGNORECASE),
    re.compile(r'<scratchpad\b[^>]*>.*?</scratchpad>', re.DOTALL | re.IGNORECASE),
    re.compile(r'<reflection\b[^>]*>.*?</reflection>', re.DOTALL | re.IGNORECASE),
    re.compile(r'<analysis\b[^>]*>.*?</analysis>', re.DOTALL | re.IGNORECASE),
    re.compile(r'<plan\b[^>]*>.*?</plan>', re.DOTALL | re.IGNORECASE),
    re.compile(r'<cot\b[^>]*>.*?</cot>', re.DOTALL | re.IGNORECASE),
    re.compile(r'<internal\b[^>]*>.*?</internal>', re.DOTALL | re.IGNORECASE),
    re.compile(r'<thought\b[^>]*>.*?</thought>', re.DOTALL | re.IGNORECASE),
    # Markdown-fenced blocks labelled as thinking/reasoning
    re.compile(r'```thinking\b.*?```', re.DOTALL | re.IGNORECASE),
    re.compile(r'```reasoning\b.*?```', re.DOTALL | re.IGNORECASE),
    re.compile(r'```scratchpad\b.*?```', re.DOTALL | re.IGNORECASE),
    # [THINKING] ... [/THINKING] bracket style
    re.compile(r'\[THINKING\].*?\[/THINKING\]', re.DOTALL | re.IGNORECASE),
    re.compile(r'\[REASONING\].*?\[/REASONING\]', re.DOTALL | re.IGNORECASE),
    re.compile(r'\[SCRATCHPAD\].*?\[/SCRATCHPAD\]', re.DOTALL | re.IGNORECASE),
    re.compile(r'\[ANALYSIS\].*?\[/ANALYSIS\]', re.DOTALL | re.IGNORECASE),
    # [SYSTEM: ...] injected reality-check blocks we add ourselves
    re.compile(r'\[SYSTEM:.*?\]', re.DOTALL),
]


def _strip_cot_blocks(text: str) -> str:
    """
    Remove all Chain-of-Thought / scratchpad / internal reasoning blocks
    from the NexusShell Core output before delivering it to the user.
    Also collapses any resulting runs of blank lines to at most two.
    """
    if not text:
        return text
    for pattern in _COT_PATTERNS:
        text = pattern.sub('', text)
    # Collapse excessive blank lines produced by removal
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# ---------------------------------------------------------------------------
# ChromaDB — память (Memory 3.0: Deep RAG)
# ---------------------------------------------------------------------------

_RERANK_TOP_K: int = 15
_RERANK_TOP_N: int = 5


async def rerank_memories_with_gemini(
    query: str,
    candidates: list[str],
    top_n: int = _RERANK_TOP_N,
) -> list[str]:
    """
    Memory 3.0 Re-ranker: использует NexusShell Core для семантического отбора
    наиболее релевантных, неизбыточных и качественных фактов из кандидатов.
    """
    if not candidates:
        return []

    numbered = "\n".join(f"{i+1}. {c}" for i, c in enumerate(candidates))

    rerank_prompt = (
        f"QUERY: {query}\n\n"
        f"FACTS:\n{numbered}\n\n"
        f"Task: Return JSON array of indices (1-based) of the top {top_n} facts "
        f"most relevant to QUERY. Exclude irrelevant or redundant facts. "
        f"If none are relevant, return []. "
        f"Output ONLY valid JSON array, no explanation. Example: [2,5,1]"
    )

    try:
        res = await _gemini_manager.generate_with_retry(
            model=STABLE_MODEL,
            contents=[rerank_prompt],
            config=types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=64,
            ),
        )
        raw = res.text.strip() if res.text else "[]"

        match = re.search(r'\[[\d,\s]*\]', raw)
        if not match:
            brain_logger.warning(f"[NexusShell Core] Re-ranker returned unexpected format: {raw!r}")
            return []

        indices = json.loads(match.group())
        if not isinstance(indices, list):
            return []

        selected = []
        seen: set[int] = set()
        for idx in indices:
            if isinstance(idx, int) and 1 <= idx <= len(candidates) and idx not in seen:
                selected.append(candidates[idx - 1])
                seen.add(idx)
            if len(selected) >= top_n:
                break

        brain_logger.info(
            f"[NexusShell Core] Re-ranker: {len(candidates)} candidates → {len(selected)} selected "
            f"(indices={list(seen)})"
        )
        return selected

    except Exception as e:
        brain_logger.error(f"[NexusShell Core] Re-ranker error: {e}", exc_info=True)
        brain_logger.warning("[NexusShell Core] Re-ranker fallback: returning raw top candidates")
        return candidates[:top_n]


async def distill_and_save_memory(user_text: str, bot_response: str, media_desc=None) -> None:
    """Извлечь и сохранить важные факты из диалога в ChromaDB."""
    try:
        if not _ensure_chromadb():
            brain_logger.warning("[NexusShell Core] ChromaDB unavailable, skipping memory save")
            return

        if any(w in bot_response.lower() for w in ['не умею', 'не могу', 'ограничен', 'нельзя']):
            brain_logger.debug("[NexusShell Core] Skipping outdated limitation response")
            return

        prompt = f'Выдели ВАЖНЫЕ факты: User: {user_text}\nBot: {bot_response}'
        res = await _gemini_manager.generate_with_retry(
            model=STABLE_MODEL,
            contents=[prompt],
            config=types.GenerateContentConfig(temperature=0.3),
        )
        fact = res.text.strip()

        if fact and len(fact) > 5:
            ts = int(time.time())
            async with _chromadb_lock:
                if _collection is not None:
                    _collection.add(
                        documents=[fact],
                        ids=[f'fact_{ts}_{uuid.uuid4().hex[:6]}'],
                        metadatas=[{'timestamp': ts}],
                    )
                    brain_logger.info(f"[NexusShell Core] Saved memory fact: {fact[:50]}...")
                else:
                    brain_logger.warning("[NexusShell Core] ChromaDB collection is None, skipping memory save")
    except Exception as e:
        brain_logger.error(f"[NexusShell Core] Error saving memory: {e}", exc_info=True)


async def get_relevant_memories(query: str, top_n: int = _RERANK_TOP_N) -> str:
    """
    Memory 3.0 — Deep RAG с семантическим ре-ранкингом через NexusShell Core.
    """
    try:
        if not _ensure_chromadb():
            brain_logger.warning("[NexusShell Core] ChromaDB unavailable, returning empty memories")
            return ''

        if _collection is None:
            brain_logger.warning("[NexusShell Core] ChromaDB collection is None, returning empty memories")
            return ''

        loop = asyncio.get_event_loop()
        try:
            results = await loop.run_in_executor(
                None,
                lambda: _collection.query(
                    query_texts=[query],
                    n_results=min(_RERANK_TOP_K, _collection.count()),
                )
            )
        except Exception as chroma_err:
            brain_logger.error(f"[NexusShell Core] ChromaDB query error: {chroma_err}", exc_info=True)
            return ''

        raw_docs = results.get('documents', [[]])[0]
        if not raw_docs:
            brain_logger.debug("[NexusShell Core] ChromaDB returned no candidates for query")
            return ''

        brain_logger.debug(
            f"[NexusShell Core] ChromaDB raw candidates: {len(raw_docs)} for query: {query[:60]!r}"
        )

        reranked = await rerank_memories_with_gemini(query, raw_docs, top_n=top_n)

        if not reranked:
            brain_logger.debug("[NexusShell Core] Re-ranker returned no relevant facts")
            return ''

        memories = '\n'.join(f'Fact: {doc}' for doc in reranked)
        brain_logger.info(
            f"[NexusShell Core] Memory 3.0: retrieved {len(reranked)}/{len(raw_docs)} facts "
            f"after re-ranking for query: {query[:60]!r}"
        )
        return memories

    except Exception as e:
        brain_logger.error(f"[NexusShell Core] Error retrieving memories: {e}", exc_info=True)
        return ''


# ---------------------------------------------------------------------------
# Вспомогательные утилиты
# ---------------------------------------------------------------------------

def _on_task_done(t: asyncio.Task, label: str) -> None:
    if not t.cancelled() and t.exception():
        brain_logger.error(f"[NexusShell Core] [{label}] Background task error: {t.exception()}")


def _build_contents_from_history(raw_history: list) -> list:
    """Преобразовать плоский список истории в types.Content[]."""
    contents = []
    for h in raw_history:
        if h.startswith('User: '):
            contents.append(
                types.Content(
                    role='user',
                    parts=[types.Part.from_text(text=h.replace('User: ', '', 1))],
                )
            )
        elif h.startswith('Bot: '):
            clean_h = re.sub(
                r'```python.*?```', '',
                h.replace('Bot: ', '', 1),
                flags=re.DOTALL,
            )
            contents.append(
                types.Content(
                    role='model',
                    parts=[types.Part.from_text(text=clean_h)],
                )
            )
    return contents


# ---------------------------------------------------------------------------
# Выполнение Python-кода (графики)
# ---------------------------------------------------------------------------

async def _execute_python_code(code_str: str) -> Optional[bytes]:
    """
    Безопасно выполнить Python-код в подпроцессе.
    Возвращает байты PNG-изображения или None.
    """
    chart_path = f"/tmp/chart_{uuid.uuid4().hex}.png"
    script_path = f"/tmp/script_{uuid.uuid4().hex}.py"

    code_run = code_str.replace(
        "plt.show()",
        f"plt.savefig('{chart_path}', dpi=300, bbox_inches='tight')\nplt.close()"
    )
    if "plt.savefig" not in code_run and ("matplotlib" in code_run or "plt." in code_run):
        code_run += (
            f"\nimport matplotlib.pyplot as plt\n"
            f"plt.savefig('{chart_path}', dpi=300, bbox_inches='tight')\n"
            f"plt.close()\n"
        )

    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(code_run)

        safe_env = os.environ.copy()
        safe_env['MPLBACKEND'] = 'Agg'

        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=15,
                env=safe_env,
                cwd='/tmp',
            )
        )

        if os.path.exists(chart_path):
            with open(chart_path, "rb") as f:
                data = f.read()
            brain_logger.info("[NexusShell Core] Chart generated successfully")
            return data
        else:
            brain_logger.error(f"[NexusShell Core] Chart not created. stderr: {res.stderr[:200]}")
            return None

    except subprocess.TimeoutExpired:
        brain_logger.error("[NexusShell Core] Code execution timeout (15s)")
        return None
    except Exception as e:
        brain_logger.error(f"[NexusShell Core] Code execution error: {e}", exc_info=True)
        return None
    finally:
        for p in (script_path, chart_path):
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass


# ---------------------------------------------------------------------------
# Основной генератор ответов
# ---------------------------------------------------------------------------

_REALITY_CHECK = (
    "\n[SYSTEM: Today is March 27, 2026. You are USBAGENT NexusShell Core v4.4. "
    "You can edit/generate images (Imagen 4), search photos, "
    "analyze documents, transcribe audio with emotions, GENERATE VOICE, and execute Python for charts. "
    "If old Facts contradict this - silently ignore them, don't mention. Be natural and conversational.]\n"
)


async def generate_response_stream(
    raw_history: list,
    current_parts: list,
    query_text: Optional[str] = None,
    media_desc=None,
) -> AsyncGenerator[Tuple[Optional[str], Optional[object]], None]:
    """
    NexusShell Core: стриминг ответа.
    Yields: (text_chunk | None, media_object | None)

    All CoT / scratchpad / thinking blocks are stripped from the final
    text before it is yielded to the caller.
    """
    full_text = ''

    try:
        contents = _build_contents_from_history(raw_history)

        q_low = query_text.lower() if query_text else ''
        use_grounding = _needs_grounding(q_low)
        use_code = any(w in q_low for w in ['график', 'посчитай', 'код', 'схему'])
        show_code = any(w in q_low for w in ['покажи код', 'исходник', 'скрипт'])

        if use_grounding and use_code:
            try:
                s_res = await _gemini_manager.generate_with_retry(
                    model=STABLE_MODEL,
                    contents=f"GET NUMERICAL DATA FOR CHART: {query_text}",
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())]
                    ),
                )
                data_found = s_res.text or "No data."
                for p in current_parts:
                    if hasattr(p, 'text') and p.text:
                        p.text = f"[SEARCH DATA: {data_found}]\n{p.text}"
                use_grounding = False
            except Exception as e:
                brain_logger.warning(f"[NexusShell Core] Pre-search for chart failed: {e}")

        # Добавляем reality check к первому текстовому парту
        for part in current_parts:
            if hasattr(part, 'text') and part.text:
                part.text = f"{_REALITY_CHECK}\nUSER: {part.text}"
                break

        contents.append(types.Content(role='user', parts=current_parts))

        tools = []
        if use_grounding:
            tools.append(types.Tool(google_search=types.GoogleSearch()))

        gen_config = types.GenerateContentConfig(
            tools=tools,
            system_instruction=SYSTEM_PROMPT,
            temperature=0.7,
        )

        # --- Collect full streamed response into buffer ---
        raw_buffer = ""
        code_str = ""

        try:
            async for chunk in await client.aio.models.generate_content_stream(
                model=STABLE_MODEL,
                contents=contents,
                config=gen_config,
            ):
                if chunk.candidates:
                    for part in chunk.candidates[0].content.parts:
                        if part.text:
                            raw_buffer += part.text
        except asyncio.CancelledError:
            brain_logger.warning("[NexusShell Core] Stream cancelled by user")
            raise
        except Exception as stream_error:
            brain_logger.error(f"[NexusShell Core] Stream error: {stream_error}", exc_info=True)
            yield f"\n\n❌ NexusShell Core stream error: {str(stream_error)}", None
            return

        # --- Strip CoT blocks from the complete raw buffer BEFORE processing ---
        raw_buffer = _strip_cot_blocks(raw_buffer)
        brain_logger.debug(f"[NexusShell Core] Buffer after CoT strip: {len(raw_buffer)} chars")

        # --- Extract python code blocks from the cleaned buffer ---
        text_parts = []
        remaining = raw_buffer
        in_code = False

        while remaining:
            if not in_code:
                start_idx = remaining.find('```python')
                if start_idx != -1:
                    # Text before the code block
                    before = remaining[:start_idx]
                    if before:
                        text_parts.append(before)
                    remaining = remaining[start_idx + 9:]  # skip '```python'
                    in_code = True
                else:
                    # No more code blocks — rest is plain text
                    text_parts.append(remaining)
                    remaining = ''
            else:
                end_idx = remaining.find('```')
                if end_idx != -1:
                    code_str += remaining[:end_idx]
                    remaining = remaining[end_idx + 3:]  # skip closing '```'
                    in_code = False
                else:
                    # Unclosed code block — treat rest as code
                    code_str += remaining
                    remaining = ''

        # --- Yield the assembled text as a single chunk ---
        final_text = ''.join(text_parts).strip()
        if final_text:
            full_text = final_text
            yield final_text, None

        # --- Show code source if requested ---
        if code_str and show_code:
            code_display = f"\n```python\n{code_str}\n```\n"
            full_text += code_display
            yield code_display, None

        # --- Execute code and yield chart ---
        if code_str:
            brain_logger.info(f"[NexusShell Core] Executing Python code, length={len(code_str)}")
            chart_data = await _execute_python_code(code_str)
            if chart_data:
                MediaObj = type('MediaObj', (), {'data': chart_data, 'mime_type': 'image/png'})
                yield None, MediaObj()
            else:
                brain_logger.warning("[NexusShell Core] Code executed but no chart produced")

    except asyncio.CancelledError:
        raise
    except Exception as e:
        brain_logger.error(f"[NexusShell Core] generate_response_stream error: {e}", exc_info=True)
        yield f'❌ USBAGENT NexusShell Core error: {str(e)}', None
    finally:
        if query_text and full_text:
            task = asyncio.create_task(
                distill_and_save_memory(query_text, full_text)
            )
            task.add_done_callback(lambda t: _on_task_done(t, "distill_memory"))
