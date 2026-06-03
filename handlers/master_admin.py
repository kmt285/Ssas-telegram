import asyncio
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from core.database import db

master_router = Router()

@master_router.message(CommandStart())
async def start_cmd(message: Message):
    text = "👑 **SaaS Master Super Admin Bot** မှ ကြိုဆိုပါတယ်။\n\n"
    text += "🛠 **အသုံးပြုနိုင်သော အမိန့်စာများ:**\n"
    text += "👉 `/addbot <Bot_Token>` - လုပ်ငန်းရှင် Bot အသစ် ထည့်သွင်းရန်\n"
    text += "👉 `/stats` - စနစ်တစ်ခုလုံး၏ Data စာရင်းများ ကြည့်ရှုရန်"
    await message.answer(text, parse_mode="Markdown")

@master_router.message(Command("addbot"))
async def add_bot_cmd(message: Message):
    args = message.text.split()
    if len(args) != 2:
        await message.answer("❌ ပုံစံမှားနေပါသည်။ \nဥပမာ - `/addbot 123456:ABC...`", parse_mode="Markdown")
        return
    
    token = args[1]
    existing_bot = await db.businesses.find_one({"bot_token": token})
    if existing_bot:
        await message.answer("⚠️ ဒီ Bot Token က စနစ်ထဲမှာ ထည့်သွင်းပြီးသား ဖြစ်နေပါတယ်။")
        return

    await db.businesses.insert_one({
        "bot_token": token, 
        "status": "active",
        "owner_id": message.from_user.id 
    })
    
    from core.bot_manager import start_client_bot 
    asyncio.create_task(start_client_bot(token))
    
    await message.answer("✅ Client Bot အသစ် အောင်မြင်စွာ ထည့်သွင်းပြီးပါပြီ။ သင့် Bot ဆီသွား၍ /start ကိုနှိပ်ပါ။")

# 💥 NEW: စနစ်တစ်ခုလုံး၏ စာရင်းဇယားများကို ကြည့်ရှုခြင်း 💥
@master_router.message(Command("stats"))
async def view_system_stats(message: Message):
    # စုစုပေါင်း လုပ်ငန်းရှင် အရေအတွက်
    total_bots = await db.businesses.count_documents({})
    # စုစုပေါင်း ဖန်တီးထားသော ဝန်ဆောင်မှု အရေအတွက်
    total_services = await db.services.count_documents({})
    # စုစုပေါင်း Active VIP သမား အရေအတွက်
    active_users = await db.subscriptions.count_documents({"status": "active"})
    
    stats_text = (
        "📊 **SaaS System Overview (စာရင်းဇယား)**\n\n"
        f"🏢 **စုစုပေါင်း လုပ်ငန်းရှင် Bots:** {total_bots} ခု\n"
        f"📦 **စုစုပေါင်း ဖန်တီးထားသော Services:** {total_services} မျိုး\n"
        f"👥 **လက်ရှိ VIP အသုံးပြုနေသူ (Active Users):** {active_users} ဦး\n\n"
        "စနစ်တစ်ခုလုံး တည်ငြိမ်စွာ လည်ပတ်နေပါသည်။ 🚀"
    )
    await message.answer(stats_text, parse_mode="Markdown")
