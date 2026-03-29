"""
tools/osint.py — USBAGENT NexusShell Core: OSINT Intelligence Module v4.4

Три режима:
  - check_nickname(nickname)      → Social Footprint по нику
  - check_crypto(address)         → Crypto Trace по адресу BTC/ETH
  - social_footprint(query)       → Широкий поиск по имени/юзернейму

Использует httpx (async) согласно CONVENTIONS.md.
Все запросы параллельны через asyncio.gather.
"""

import asyncio
import re
from typing import Optional

import httpx

# ---------------------------------------------------------------------------
# Константы
# ---------------------------------------------------------------------------

_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=2.0)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# Платформы для проверки никнейма.
# Значение — URL с {nick} плейсхолдером.
_NICKNAME_PLATFORMS: dict[str, str] = {
    "GitHub":     "https://github.com/{nick}",
    "Reddit":     "https://www.reddit.com/user/{nick}",
    "Twitter/X":  "https://twitter.com/{nick}",
    "Instagram":  "https://www.instagram.com/{nick}/",
    "TikTok":     "https://www.tiktok.com/@{nick}",
    "Telegram":   "https://t.me/{nick}",
    "Pinterest":  "https://www.pinterest.com/{nick}/",
    "Twitch":     "https://www.twitch.tv/{nick}",
    "YouTube":    "https://www.youtube.com/@{nick}",
    "Medium":     "https://medium.com/@{nick}",
    "Dev.to":     "https://dev.to/{nick}",
    "Keybase":    "https://keybase.io/{nick}",
    "Gitlab":     "https://gitlab.com/{nick}",
    "Linktree":   "https://linktr.ee/{nick}",
    "Patreon":    "https://www.patreon.com/{nick}",
}

# Статус-коды, которые считаем «найден»
_FOUND_CODES = {200, 301, 302}

# Паттерны для определения типа крипто-адреса
_BTC_PATTERN  = re.compile(r'^(1|3)[a-zA-HJ-NP-Z0-9]{25,34}$|^bc1[a-zA-HJ-NP-Z0-9]{39,59}$')
_ETH_PATTERN  = re.compile(r'^0x[a-fA-F0-9]{40}$')
_TRON_PATTERN = re.compile(r'^T[a-zA-Z0-9]{33}$')


# ---------------------------------------------------------------------------
# Внутренние хелперы
# ---------------------------------------------------------------------------

async def _check_one_platform(
    client: httpx.AsyncClient,
    name: str,
    url: str,
) -> tuple[str, str, bool]:
    """
    Проверить одну платформу.
    Возвращает (name, url, found).
    """
    try:
        resp = await client.get(url, follow_redirects=True)
        found = resp.status_code in _FOUND_CODES
        # Дополнительная проверка: некоторые платформы возвращают 200 для несуществующих
        # профилей с редиректом на главную — проверяем финальный URL
        if found and resp.url and str(resp.url) in (
            "https://twitter.com/", "https://www.instagram.com/",
            "https://www.tiktok.com/", "https://t.me/",
        ):
            found = False
        return name, url, found
    except httpx.TimeoutException:
        return name, url, False
    except httpx.ConnectError:
        return name, url, False
    except Exception:
        return name, url, False


def _detect_crypto_network(address: str) -> Optional[str]:
    """Определить сеть по формату адреса."""
    addr = address.strip()
    if _BTC_PATTERN.match(addr):
        return "BTC"
    if _ETH_PATTERN.match(addr):
        return "ETH"
    if _TRON_PATTERN.match(addr):
        return "TRX"
    return None


# ---------------------------------------------------------------------------
# Публичные функции
# ---------------------------------------------------------------------------

async def check_nickname(nickname: str) -> dict:
    """
    USBAGENT NexusShell Core — Social Footprint:
    проверяет никнейм на 15+ платформах параллельно.

    Возвращает dict:
    {
        "nickname": str,
        "found": {platform: url, ...},
        "not_found": [platform, ...],
        "total_found": int,
        "total_checked": int,
    }
    """
    nickname = nickname.strip().lstrip("@")
    if not nickname:
        return {"error": "Empty nickname"}

    found: dict[str, str] = {}
    not_found: list[str] = []

    async with httpx.AsyncClient(
        timeout=_TIMEOUT,
        headers=_HEADERS,
        follow_redirects=True,
    ) as client:
        tasks = [
            _check_one_platform(client, name, url.format(nick=nickname))
            for name, url in _NICKNAME_PLATFORMS.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=False)

    for name, url, is_found in results:
        if is_found:
            found[name] = url
        else:
            not_found.append(name)

    return {
        "nickname": nickname,
        "found": found,
        "not_found": not_found,
        "total_found": len(found),
        "total_checked": len(_NICKNAME_PLATFORMS),
    }


async def check_crypto(address: str) -> dict:
    """
    USBAGENT NexusShell Core — Crypto Trace:
    определяет сеть и запрашивает публичные блокчейн-API.

    Поддерживает BTC (blockchain.info), ETH (etherscan.io public),
    TRX (tronscan.org).

    Возвращает dict с балансом, количеством транзакций и ссылкой
    на блокчейн-эксплорер.
    """
    address = address.strip()
    network = _detect_crypto_network(address)

    if not network:
        return {
            "address": address,
            "error": "Unrecognized address format. Supported: BTC, ETH, TRX",
        }

    result: dict = {"address": address, "network": network}

    async with httpx.AsyncClient(timeout=_TIMEOUT, headers=_HEADERS) as client:

        if network == "BTC":
            try:
                resp = await client.get(
                    f"https://blockchain.info/rawaddr/{address}?limit=0"
                )
                if resp.status_code == 200:
                    data = resp.json()
                    balance_btc = data.get("final_balance", 0) / 1e8
                    result.update({
                        "balance": f"{balance_btc:.8f} BTC",
                        "total_received": f"{data.get('total_received', 0) / 1e8:.8f} BTC",
                        "total_sent":     f"{data.get('total_sent', 0) / 1e8:.8f} BTC",
                        "tx_count":       data.get("n_tx", 0),
                        "explorer":       f"https://www.blockchain.com/explorer/addresses/btc/{address}",
                    })
                else:
                    result["error"] = f"blockchain.info returned {resp.status_code}"
            except Exception as e:
                result["error"] = f"BTC lookup failed: {str(e)[:80]}"

        elif network == "ETH":
            try:
                # Публичный endpoint etherscan без API-ключа (лимит 1 req/5s)
                resp = await client.get(
                    "https://api.etherscan.io/api",
                    params={
                        "module": "account",
                        "action": "balance",
                        "address": address,
                        "tag": "latest",
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "1":
                        balance_eth = int(data.get("result", 0)) / 1e18
                        result.update({
                            "balance":  f"{balance_eth:.6f} ETH",
                            "explorer": f"https://etherscan.io/address/{address}",
                        })
                    else:
                        result["error"] = data.get("message", "Etherscan error")
                else:
                    result["error"] = f"etherscan returned {resp.status_code}"
            except Exception as e:
                result["error"] = f"ETH lookup failed: {str(e)[:80]}"

        elif network == "TRX":
            try:
                resp = await client.get(
                    f"https://apilist.tronscanapi.com/api/accountv2?address={address}"
                )
                if resp.status_code == 200:
                    data = resp.json()
                    balance_trx = data.get("balance", 0) / 1e6
                    result.update({
                        "balance":  f"{balance_trx:.2f} TRX",
                        "tx_count": data.get("transactions_count", "N/A"),
                        "explorer": f"https://tronscan.org/#/address/{address}",
                    })
                else:
                    result["error"] = f"tronscan returned {resp.status_code}"
            except Exception as e:
                result["error"] = f"TRX lookup failed: {str(e)[:80]}"

    return result


async def social_footprint(query: str) -> dict:
    """
    USBAGENT NexusShell Core — Social Footprint:
    широкий поиск по имени или юзернейму.
    Комбинирует check_nickname + дополнительные источники.

    Возвращает агрегированный dict с результатами по всем источникам.
    """
    query = query.strip()
    if not query:
        return {"error": "Empty query"}

    # Параллельно запускаем проверку ника и дополнительные источники
    nickname_task = asyncio.create_task(check_nickname(query))

    # Дополнительные источники (публичные, без авторизации)
    extra_sources: dict[str, str] = {
        "HaveIBeenPwned": f"https://haveibeenpwned.com/account/{query}",
        "Gravatar":       f"https://en.gravatar.com/{query}",
        "About.me":       f"https://about.me/{query}",
        "Behance":        f"https://www.behance.net/{query}",
        "Dribbble":       f"https://dribbble.com/{query}",
    }

    extra_found: dict[str, str] = {}

    async with httpx.AsyncClient(
        timeout=_TIMEOUT,
        headers=_HEADERS,
        follow_redirects=True,
    ) as client:
        extra_tasks = [
            _check_one_platform(client, name, url)
            for name, url in extra_sources.items()
        ]
        extra_results = await asyncio.gather(*extra_tasks, return_exceptions=False)

    for name, url, is_found in extra_results:
        if is_found:
            extra_found[name] = url

    nickname_result = await nickname_task

    # Объединяем результаты
    all_found = {**nickname_result.get("found", {}), **extra_found}

    return {
        "query": query,
        "found": all_found,
        "total_found": len(all_found),
        "total_checked": nickname_result.get("total_checked", 0) + len(extra_sources),
        "sources": {
            "social_platforms": nickname_result.get("found", {}),
            "extra": extra_found,
        },
    }


# ---------------------------------------------------------------------------
# Форматирование результатов для Telegram
# ---------------------------------------------------------------------------

def format_nickname_result(result: dict) -> str:
    """Форматировать результат check_nickname для отправки в Telegram."""
    if "error" in result:
        return f"❌ Ошибка: {result['error']}"

    nick = result["nickname"]
    found = result["found"]
    total_found = result["total_found"]
    total_checked = result["total_checked"]

    lines = [
        f"🔍 *USBAGENT OSINT — Nickname `{nick}`*",
        f"📊 Найдено: *{total_found}/{total_checked}* платформ\n",
    ]

    if found:
        lines.append("✅ *Найден на:*")
        for platform, url in found.items():
            lines.append(f"  • [{platform}]({url})")
    else:
        lines.append("❌ Аккаунты не найдены ни на одной платформе.")

    return "\n".join(lines)


def format_crypto_result(result: dict) -> str:
    """Форматировать результат check_crypto для отправки в Telegram."""
    if "error" in result:
        return f"❌ Ошибка: {result['error']}"

    addr = result["address"]
    network = result.get("network", "?")
    short_addr = f"{addr[:6]}...{addr[-4:]}"

    lines = [
        f"🔗 *USBAGENT OSINT — Crypto Trace*",
        f"📍 Адрес: `{short_addr}` ({network})",
    ]

    if "balance" in result:
        lines.append(f"💰 Баланс: *{result['balance']}*")
    if "total_received" in result:
        lines.append(f"📥 Получено: {result['total_received']}")
    if "total_sent" in result:
        lines.append(f"📤 Отправлено: {result['total_sent']}")
    if "tx_count" in result:
        lines.append(f"🔄 Транзакций: {result['tx_count']}")
    if "explorer" in result:
        lines.append(f"\n🌐 [Открыть в эксплорере]({result['explorer']})")

    return "\n".join(lines)


def format_footprint_result(result: dict) -> str:
    """Форматировать результат social_footprint для отправки в Telegram."""
    if "error" in result:
        return f"❌ Ошибка: {result['error']}"

    query = result["query"]
    total_found = result["total_found"]
    total_checked = result["total_checked"]
    sources = result.get("sources", {})

    lines = [
        f"🕵️ *USBAGENT OSINT — Social Footprint*",
        f"🔎 Запрос: `{query}`",
        f"📊 Найдено: *{total_found}/{total_checked}* источников\n",
    ]

    social = sources.get("social_platforms", {})
    if social:
        lines.append("📱 *Социальные сети:*")
        for platform, url in social.items():
            lines.append(f"  • [{platform}]({url})")

    extra = sources.get("extra", {})
    if extra:
        lines.append("\n🌐 *Дополнительные источники:*")
        for platform, url in extra.items():
            lines.append(f"  • [{platform}]({url})")

    if not social and not extra:
        lines.append("❌ Цифровой след не обнаружен.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI тест
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    async def _test():
        if len(sys.argv) < 3:
            print("Usage: python osint.py nickname <nick>")
            print("       python osint.py crypto <address>")
            print("       python osint.py footprint <query>")
            return

        mode = sys.argv[1]
        target = sys.argv[2]

        if mode == "nickname":
            res = await check_nickname(target)
            print(format_nickname_result(res))
        elif mode == "crypto":
            res = await check_crypto(target)
            print(format_crypto_result(res))
        elif mode == "footprint":
            res = await social_footprint(target)
            print(format_footprint_result(res))
        else:
            print(f"Unknown mode: {mode}")

    asyncio.run(_test())
