import os, json, time, threading
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from apify_client import ApifyClient

# ------------------ СЮДА ВСТАВЛЯЕМ КЛЮЧИ ------------------
TELEGRAM_TOKEN = '8400432306:AAFg0b3sUA-bODsf4Ddbym8OcbW4eWOpzU8'
APIFY_TOKEN    = 'apify_api_7yp5Ewu4VH6IKPfayKNaxOIUQdAcyd0JlaHj'
# -----------------------------------------------------------

apify  = ApifyClient(APIFY_TOKEN)
app    = Application.builder().token(TELEGRAM_TOKEN).build()

# хранилище: {chat_id: [список видео]}
storage = {}

def run_actor(profile_url):
    """Запускаем TikTok Scraper, получаем список видео"""
    run = apify.actor('clockworks/tiktok-scraper').call(
        run_input={'profiles': [profile_url], 'resultsPerPage': 50}
    )
    items = []
    for item in apify.dataset(run['defaultDatasetId']).iterate_items():
        items.append(item)
    return items

def format_changes(old, new):
    """Сравниваем старое и новое, возвращаем список сообщений"""
    msgs = []
    old_map = {v['id']: v for v in old}
    for v in new:
        vid = v['id']
        if vid not in old_map:
            msgs.append(f"🆕 Новое видео!\n{v['webVideoUrl']}")
            continue
        o = old_map[vid]
        if v['diggCount'] > o['diggCount']:
            msgs.append(f"❤️ Лайков стало больше: {v['diggCount']} (+{v['diggCount']-o['diggCount']})\n{v['webVideoUrl']}")
        if v['commentCount'] > o['commentCount']:
            msgs.append(f"💬 Комментариев стало больше: {v['commentCount']} (+{v['commentCount']-o['commentCount']})\n{v['webVideoUrl']}")
    return msgs

# ------ команды бота ------
async def start(update: Update, _):
    await update.message.reply_text("Пришли мне URL профиля TikTok (https://www.tiktok.com/@username)")

async def got_url(update: Update, _):
    url = update.message.text.strip()
    if not url.startswith('https://www.tiktok.com/@'):
        await update.message.reply_text("❗️ Пришли корректный URL профиля TikTok")
        return
    chat_id = update.effective_chat.id
    await update.message.reply_text("✅ Принято! Начинаю слежку...")
    threading.Thread(target=worker, args=(chat_id, url), daemon=True).start()

def worker(chat_id, profile_url):
    while True:
        try:
            data = run_actor(profile_url)
            if chat_id in storage:
                diffs = format_changes(storage[chat_id], data)
                for txt in diffs:
                    app.bot.send_message(chat_id=chat_id, text=txt)
            storage[chat_id] = data
        except Exception as e:
            app.bot.send_message(chat_id=chat_id, text=f"Ошибка: {e}")
        time.sleep(300)  # 5 минут

# ------ регистрируем обработчики ------
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, got_url))

# ------ запуск ------
if __name__ == '__main__':
    app.run_polling()
