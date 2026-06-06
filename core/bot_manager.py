import asyncio
import logging
from aiogram import Bot, Dispatcher
from core.database import db
from handlers.client_bot import client_router
from handlers.client_admin import client_admin_router

# ==========================================
# 💥 Master Dispatcher (ဦးနှောက်) အား တစ်ခုတည်းသာ တည်ဆောက်မည်
# ==========================================
client_dp = Dispatcher()
client_dp.include_router(client_router)
client_dp.include_router(client_admin_router)

# ==========================================
# 💥 NEW: Bot တစ်ခုချင်းစီအတွက် သီးသန့် Polling လုပ်ပေးမည့် အင်ဂျင်
# ==========================================
async def poll_bot(bot: Bot):
    offset = None
    logging.info(f"✅ Started Polling for Client Bot: {bot.token[:10]}...")
    while True:
        try:
            # Telegram Server ထံမှ အချက်အလက်များကို သီးသန့် လှမ်းယူမည်
            updates = await bot.get_updates(offset=offset, timeout=20)
            for update in updates:
                offset = update.update_id + 1
                # ရရှိလာသော အချက်အလက်ကို Dispatcher ထံသို့ Manual ဖြည့်သွင်းပေးမည်
                await client_dp.feed_update(bot, update)
        except asyncio.CancelledError:
            break
        except Exception as e:
            # Error တက်ပါက (ဥပမာ- အင်တာနက်ပြတ်သွားပါက) ၃ စက္ကန့်နားပြီး ပြန်စစ်မည်
            await asyncio.sleep(3)

# ==========================================
# 💥 Bot အသစ်များကို စတင်ချိတ်ဆက်မည့် Function
# ==========================================
async def start_client_bot(token):
    try:
        bot = Bot(token=token)
        # 💥 aiogram ၏ start_polling အစား သီးသန့် poll_bot ကိုသာ အသုံးပြုမည်
        asyncio.create_task(poll_bot(bot))
    except Exception as e:
        logging.error(f"❌ Failed to start bot {token[:10]}: {e}")

async def start_all_client_bots():
    logging.info("🔄 Starting all Client Bots from Database...")
    businesses = await db.businesses.find({"status": "active"}).to_list(length=1000)
    for biz in businesses:
        token = biz.get("bot_token")
        if token:
            await start_client_bot(token)
