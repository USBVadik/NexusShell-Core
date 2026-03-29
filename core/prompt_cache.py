"""
Кэш для enhance_prompt - избегаем повторных вызовов AI
USB BOT V3.1
"""
import time
from typing import Dict, Tuple

_prompt_cache: Dict[str, Tuple[str, float]] = {}
CACHE_TTL = 3600  # 1 час
MAX_CACHE_SIZE = 200

def get_cached_prompt(original: str, mode: str) -> str | None:
    """Получить закэшированный промпт"""
    cache_key = f"{mode}:{original[:100]}"
    
    if cache_key in _prompt_cache:
        enhanced, timestamp = _prompt_cache[cache_key]
        if time.time() - timestamp < CACHE_TTL:
            return enhanced
        else:
            del _prompt_cache[cache_key]
    
    return None

def cache_prompt(original: str, mode: str, enhanced: str):
    """Сохранить промпт в кэш"""
    cache_key = f"{mode}:{original[:100]}"
    
    # Очистка старых записей если кэш переполнен
    if len(_prompt_cache) >= MAX_CACHE_SIZE:
        current_time = time.time()
        expired = [k for k, (_, ts) in _prompt_cache.items() if current_time - ts > CACHE_TTL]
        for k in expired:
            del _prompt_cache[k]
        
        # Если всё ещё переполнен, удаляем самые старые
        if len(_prompt_cache) >= MAX_CACHE_SIZE:
            sorted_items = sorted(_prompt_cache.items(), key=lambda x: x[1][1])
            for k, _ in sorted_items[:50]:
                del _prompt_cache[k]
    
    _prompt_cache[cache_key] = (enhanced, time.time())
