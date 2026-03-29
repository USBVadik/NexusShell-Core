import asyncio, requests, time
from config import ALLOWED_USER_ID

class CryptoWatcher:
    def __init__(self, bot):
        self.bot = bot
        self.prices = {'BTC': 0, 'ETH': 0}
        self.threshold = 0.03 # 3%
        self.running = True

    async def get_price(self, symbol):
        try:
            url = f'https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT'
            res = requests.get(url, timeout=10).json()
            return float(res['price'])
        except: return 0

    async def loop(self):
        print('📡 Watcher: BTC/ETH monitoring started.')
        while self.running:
            for s in ['BTC', 'ETH']:
                new_p = await self.get_price(s)
                old_p = self.prices[s]
                
                if old_p > 0 and abs(new_p - old_p) / old_p > self.threshold:
                    emoji = '🚀' if new_p > old_p else '🔻'
                    diff = (new_p - old_p) / old_p * 100
                    alert = f"{emoji} **WATCHER ALERT: {s}**\nЦена: ({diff:+.2f}%) за последние 15 мин."
                    try: await self.bot.send_message(chat_id=ALLOWED_USER_ID, text=alert, parse_mode='Markdown')
                    except Exception as e: print(f"[Watcher Error] {e}")
                
                self.prices[s] = new_p
            await asyncio.sleep(900) # Проверка каждые 15 минут

def start_watcher(bot):
    watcher = CryptoWatcher(bot)
    asyncio.create_task(watcher.loop())

async def get_crypto_prices():
    try:
        res_btc = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT', timeout=5).json()
        res_eth = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT', timeout=5).json()
        return f"BTC: {float(res_btc['price']):.2f}, ETH: {float(res_eth['price']):.2f}"
    except:
        return "Ошибка получения курсов"
