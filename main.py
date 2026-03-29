import sys, os, psutil, time, asyncio, glob
from datetime import datetime, timedelta

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from telegram.ext import Application, MessageHandler, filters, CommandHandler
from core.router import handle_msg
from tools.watcher import start_watcher
from config import TG_TOKEN, ALLOWED_USER_ID
from tools.trend_hunter import run_full_scan

# Глобальный счётчик для статистики
_request_times = []

def cleanup_old_temp_files():
    """Очистка временных файлов старше 1 часа"""
    try:
        cutoff_time = time.time() - 3600  # 1 час назад
        patterns = ['/tmp/gen_*.png', '/tmp/edit_*.png', '/tmp/flash_*.png', 
                   '/tmp/retouch_*.png', '/tmp/out_*.jpg', '/tmp/voice_*.mp3',
                   '/tmp/chart_*.png', '/tmp/in_*.jpg', '/tmp/multi_*.png',
                   '/tmp/temp_chart_script.py']
        
        cleaned = 0
        for pattern in patterns:
            for filepath in glob.glob(pattern):
                try:
                    if os.path.getmtime(filepath) < cutoff_time:
                        os.remove(filepath)
                        cleaned += 1
                except: pass
        
        if cleaned > 0:
            print(f'🧹 Cleaned {cleaned} old temp files')
        
        # Выводим статистику времени ответов
        if _request_times:
            avg_time = sum(_request_times) / len(_request_times)
            max_time = max(_request_times)
            print(f'📊 Avg response time: {avg_time:.2f}s, Max: {max_time:.2f}s, Count: {len(_request_times)}')
            _request_times.clear()
            
    except Exception as e:
        print(f'⚠️ Cleanup error: {e}')

async def status_command(update, context):
    if update.effective_user.id != ALLOWED_USER_ID: return
    cpu  = psutil.cpu_percent(interval=0.5)
    ram  = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Проверка /tmp
    tmp_files = len(glob.glob('/tmp/gen_*.png') + glob.glob('/tmp/edit_*.png') + 
                    glob.glob('/tmp/voice_*.mp3') + glob.glob('/tmp/chart_*.png'))
    
    # Статистика времени ответов
    perf_stats = ""
    if _request_times:
        avg_time = sum(_request_times) / len(_request_times)
        max_time = max(_request_times)
        perf_stats = f"⚡ Avg Response: {avg_time:.1f}s (max: {max_time:.1f}s)"
    
    lines = [
        "🖥 USBAGENT V1 SYSTEM STATUS",
        "",
        f"⚙️ CPU Load:   {cpu}%",
        f"🧠 RAM Usage:  {ram.percent}% ({ram.used // (1024**2)}MB / {ram.total // (1024**2)}MB)",
        f"💾 SSD Usage:  {disk.percent}% ({disk.free // (1024**3)}GB free)",
        f"📁 Temp Files: {tmp_files}",
    ]
    
    if perf_stats:
        lines.append(perf_stats)
    
    lines.extend([
        "",
        f"🟢 Process:    Online",
        f"🕒 Server Time: {time.strftime('%H:%M:%S')}",
    ])
    
    await update.message.reply_text("\n".join(lines))

async def trends_command(update, context):
    """Manual /trends command — triggers an immediate trend scan."""
    if update.effective_user.id != ALLOWED_USER_ID:
        return

    await update.message.reply_text(
        "⚡️ *USBAGENT TREND HUNTER v4.0*\n\n"
        "🔍 Scanning global signals...\n"
        "_AI · Crypto · OSINT · Tech_\n\n"
        "⏳ This takes 15-30 seconds...",
        parse_mode='Markdown'
    )

    try:
        brief = await run_full_scan()
        if len(brief) <= 4096:
            await update.message.reply_text(brief, parse_mode='Markdown')
        else:
            chunks = [brief[i:i+4000] for i in range(0, len(brief), 4000)]
            for chunk in chunks:
                await update.message.reply_text(chunk, parse_mode='Markdown')
                await asyncio.sleep(0.5)
    except Exception as e:
        print(f'⚠️ Trends command error: {e}')
        await update.message.reply_text(f"❌ Trend scan failed: {str(e)[:100]}")

async def health_check():
    """Сторожевой таймер - проверка зависания бота"""
    last_activity = time.time()
    
    while True:
        await asyncio.sleep(60)  # Проверка каждую минуту
        
        if time.time() - last_activity > 300:
            print(f'⚠️ WARNING: No activity for {int((time.time() - last_activity) / 60)} minutes')
        
        last_activity = time.time()

async def trend_hunter_loop(bot):
    """Background loop: runs a full trend scan every 12 hours and sends to ALLOWED_USER_ID."""
    print('📡 TrendHunter loop started (12h interval)')

    # Initial delay: wait 60 seconds after startup before first scan
    await asyncio.sleep(60)

    while True:
        try:
            print(f'📡 TrendHunter: Starting scheduled scan at {time.strftime("%H:%M:%S")}')
            brief = await run_full_scan()

            if len(brief) <= 4096:
                await bot.send_message(
                    chat_id=ALLOWED_USER_ID,
                    text=brief,
                    parse_mode='Markdown'
                )
            else:
                chunks = [brief[i:i+4000] for i in range(0, len(brief), 4000)]
                for chunk in chunks:
                    await bot.send_message(
                        chat_id=ALLOWED_USER_ID,
                        text=chunk,
                        parse_mode='Markdown'
                    )
                    await asyncio.sleep(0.5)

            print(f'📡 TrendHunter: Scheduled scan sent successfully')

        except Exception as e:
            print(f'⚠️ TrendHunter loop error: {e}')
            try:
                await bot.send_message(
                    chat_id=ALLOWED_USER_ID,
                    text=f"⚠️ *TrendHunter Error*\n`{str(e)[:200]}`",
                    parse_mode='Markdown'
                )
            except Exception:
                pass

        # Wait 12 hours before next scan
        await asyncio.sleep(12 * 3600)

async def post_init(application: Application):
    start_watcher(application.bot)
    
    async def periodic_cleanup():
        while True:
            await asyncio.sleep(3600)
            cleanup_old_temp_files()
    
    asyncio.create_task(periodic_cleanup())
    asyncio.create_task(health_check())
    asyncio.create_task(trend_hunter_loop(application.bot))

    print('🧹 Temp files cleanup scheduled (every 1 hour)')
    print('💓 Health check started')
    print('📡 TrendHunter v4.0 scheduled (every 12 hours)')

def main():
    app = Application.builder().token(TG_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler('status', status_command))
    app.add_handler(CommandHandler('trends', trends_command))
    app.add_handler(MessageHandler(filters.ALL, handle_msg))
    print('🚀 USBAGENT V1 STABLE Ready.')
    app.run_polling(close_loop=False)

if __name__ == '__main__':
    main()
