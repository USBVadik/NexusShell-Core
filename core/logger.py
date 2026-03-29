"""
Централизованная система логирования для USB BOT V3.1
"""
import logging
import sys
from datetime import datetime

# Настройка форматирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def get_logger(name: str) -> logging.Logger:
    """Получить логгер для модуля"""
    return logging.getLogger(name)

# Performance monitoring decorator
import time
import asyncio
from functools import wraps

def log_performance(logger):
    """Декоратор для логирования времени выполнения"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                elapsed = time.time() - start
                if elapsed > 1.0:  # Логируем только медленные операции
                    logger.info(f"{func.__name__} took {elapsed:.2f}s")
                return result
            except Exception as e:
                elapsed = time.time() - start
                logger.error(f"{func.__name__} failed after {elapsed:.2f}s: {e}")
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start
                if elapsed > 1.0:
                    logger.info(f"{func.__name__} took {elapsed:.2f}s")
                return result
            except Exception as e:
                elapsed = time.time() - start
                logger.error(f"{func.__name__} failed after {elapsed:.2f}s: {e}")
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

# Экспортируем готовые логгеры
router_logger = get_logger('router')
brain_logger = get_logger('brain')
image_logger = get_logger('image')
video_logger = get_logger('video')
api_logger = get_logger('api')
media_logger = get_logger('media')
trend_logger = get_logger('trend_hunter')

def retry_on_rate_limit(max_retries=3, base_delay=5, notify_user=None):
    """Декоратор для повторных попыток при rate limit с уведомлением пользователя"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if '429' in str(e) and attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)  # Exponential backoff
                        api_logger.warning(f"Rate limit hit, retry {attempt + 1}/{max_retries} after {delay}s")
                        
                        # Уведомляем пользователя если передан callback
                        if notify_user and attempt == 0:
                            try:
                                await notify_user(f"⏳ Много запросов к API. Подожди {delay} секунд...")
                            except: pass
                        
                        await asyncio.sleep(delay)
                        continue
                    raise
            return None
        return wrapper
    return decorator
