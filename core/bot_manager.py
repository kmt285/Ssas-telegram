import asyncio
import logging
from aiogram import Bot, Dispatcher
from handlers.client_bot import client_router
from handlers.client_admin import client_admin_router  # <--- (၁) ဒါလေး ထည့်မည်
from core.database import db

async def start_client_bot(token: str):
    try:
        bot = Bot(token=token)
        dp = Dispatcher()
        dp.include_router(client_router)
        dp.include_router(client_admin_router) # <--- (၂) ဒါလေး ထည့်မည်
        
        logging.info(f"🚀 Starting Client Bot: {token[:10]}...")
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"❌ Failed to start bot {token[:10]}: {e}")

async def start_all_client_bots():
    cursor = db.businesses.find({"status": "active"})
    businesses = await cursor.to_list(length=100)
    
    for biz in businesses:
        token = biz.get("bot_token")
        if token:
            asyncio.create_task(start_client_bot(token))
