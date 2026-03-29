"""
ToolRegistry — синглтон-реестр инструментов бота.
Каждый инструмент регистрируется с именем, обработчиком и опциональным предикатом.
"""
import asyncio
from dataclasses import dataclass, field
from typing import Callable, Awaitable, Any, Optional
from core.logger import router_logger


@dataclass
class Tool:
    name: str
    # handler is optional — routing logic in router.py handles dispatch by tool name
    handler: Optional[Callable[..., Awaitable[Any]]] = None
    # Предикат: принимает (text, low_text, context_dict) -> bool
    predicate: Optional[Callable[[str, str, dict], bool]] = None
    # Приоритет: меньше = выше приоритет
    priority: int = 100
    # Описание для логов
    description: str = ""


class ToolRegistry:
    """
    Синглтон-реестр инструментов.
    Использование:
        registry = ToolRegistry.get_instance()
        registry.register(Tool(...))
        matched = registry.match(text, low_text, ctx)
    """
    _instance: Optional["ToolRegistry"] = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __init__(self):
        self._tools: list[Tool] = []

    @classmethod
    def get_instance(cls) -> "ToolRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, tool: Tool) -> None:
        """Зарегистрировать инструмент."""
        self._tools.append(tool)
        # Сортируем по приоритету после каждой регистрации
        self._tools.sort(key=lambda t: t.priority)
        router_logger.debug(f"[ToolRegistry] Registered tool: {tool.name} (priority={tool.priority})")

    def register_many(self, tools: list[Tool]) -> None:
        """Зарегистрировать несколько инструментов."""
        for tool in tools:
            self._tools.append(tool)
        self._tools.sort(key=lambda t: t.priority)
        router_logger.debug(f"[ToolRegistry] Registered {len(tools)} tools")

    def match(self, text: str, low_text: str, ctx: dict) -> Optional[Tool]:
        """
        Найти первый подходящий инструмент по предикату.
        ctx — произвольный словарь с контекстом (media, update, etc.)
        """
        for tool in self._tools:
            if tool.predicate is None:
                continue
            try:
                if tool.predicate(text, low_text, ctx):
                    router_logger.debug(f"[ToolRegistry] Matched tool: {tool.name}")
                    return tool
            except Exception as e:
                router_logger.error(f"[ToolRegistry] Predicate error for {tool.name}: {e}", exc_info=True)
        return None

    def get_all(self) -> list[Tool]:
        return list(self._tools)

    def get_by_name(self, name: str) -> Optional[Tool]:
        for tool in self._tools:
            if tool.name == name:
                return tool
        return None

    def clear(self) -> None:
        """Очистить реестр (для тестов)."""
        self._tools.clear()


def build_default_registry() -> ToolRegistry:
    """
    Создаёт и возвращает реестр с инструментами по умолчанию.
    Импорты внутри функции — чтобы избежать циклических зависимостей.
    """
    from core.triggers import (
        has_trigger, VEO_PATTERN, NANOBANANA_TRIGGER,
        DRAW_TRIGGERS, EDIT_TRIGGERS, STYLE_TRIGGERS, CRYPTO_TRIGGERS,
        VOICE_TRIGGER, STYLE_SAVE_PREFIX, STYLE_SHOW_TRIGGERS, STYLE_RESET_TRIGGERS,
        extract_style_command,
    )

    registry = ToolRegistry.get_instance()

    # Guard: if already populated (e.g. module reloaded), clear to avoid duplicates
    if registry.get_all():
        registry.clear()

    # --- Предикаты ---

    def pred_user_style(text: str, low_text: str, ctx: dict) -> bool:
        return bool(extract_style_command(text)) or \
               low_text in STYLE_SHOW_TRIGGERS or \
               low_text in STYLE_RESET_TRIGGERS

    def pred_multi_photo(text: str, low_text: str, ctx: dict) -> bool:
        return bool(ctx.get("multi_photo"))

    def pred_veo(text: str, low_text: str, ctx: dict) -> bool:
        return bool(VEO_PATTERN.search(low_text))

    def pred_nanobanana(text: str, low_text: str, ctx: dict) -> bool:
        return NANOBANANA_TRIGGER in low_text

    def pred_image(text: str, low_text: str, ctx: dict) -> bool:
        return has_trigger(low_text, DRAW_TRIGGERS + EDIT_TRIGGERS + STYLE_TRIGGERS)

    def pred_crypto(text: str, low_text: str, ctx: dict) -> bool:
        return has_trigger(low_text, CRYPTO_TRIGGERS)

    def pred_voice(text: str, low_text: str, ctx: dict) -> bool:
        return VOICE_TRIGGER in low_text

    def pred_photo_search(text: str, low_text: str, ctx: dict) -> bool:
        return bool(ctx.get("needs_photo"))

    def pred_image_tools(text: str, low_text: str, ctx: dict) -> bool:
        return bool(ctx.get("image_tools_triggered"))

    # --- Регистрация ---
    registry.register_many([
        Tool(name="user_style",   predicate=pred_user_style,   priority=10,  description="Управление стилем пользователя"),
        Tool(name="multi_photo",  predicate=pred_multi_photo,  priority=20,  description="Редактирование нескольких фото"),
        Tool(name="image_tools",  predicate=pred_image_tools,  priority=30,  description="OCR / Retouch / Upscale / Outpaint"),
        Tool(name="veo",          predicate=pred_veo,          priority=40,  description="VEO видео-генерация"),
        Tool(name="nanobanana",   predicate=pred_nanobanana,   priority=50,  description="Flash Image генерация"),
        Tool(name="image",        predicate=pred_image,        priority=60,  description="Генерация/редактирование изображений"),
        Tool(name="crypto",       predicate=pred_crypto,       priority=70,  description="Курсы криптовалют"),
        Tool(name="voice",        predicate=pred_voice,        priority=80,  description="Голосовые сообщения"),
        Tool(name="photo_search", predicate=pred_photo_search, priority=90,  description="Поиск реальных фотографий"),
    ])

    router_logger.info(f"[ToolRegistry] Built default registry with {len(registry.get_all())} tools")
    return registry
