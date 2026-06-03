import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiohttp import web
from core.config import MASTER_BOT_TOKEN, PORT

# Logging သတ်မှတ်ခြင်း
logging.basicConfig(level=logging.INFO)

# Bot နှင့် Dispatcher တည်ဆောက်ခြင်း
bot = Bot(token=MASTER_BOT_TOKEN)
dp = Dispatcher()

# Master Bot /start Command
@dp.message(CommandStart())
async def start_cmd(message: Message):
    await message.answer("မင်္ဂလာပါ။ SaaS Master Bot မှ ကြိုဆိုပါတယ်။")

# Render အတွက် Dummy Web Server (Error မတက်စေရန်)
async def handle(request):
    return web.Response(text="Bot is running smoothly on Render!")

async def web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logging.info(f"Web server started on port {PORT}")

# Main Function (Bot နှင့် Web Server တွဲ Run မည်)
async def main():
    # Web server စတင်ခြင်း
    asyncio.create_task(web_server())
    
    # Bot စတင်ခြင်း
    logging.info("Starting Telegram Bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
