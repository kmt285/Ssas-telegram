import asyncio
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from core.database import db

master_router = Router()

@master_router.message(CommandStart())
async def start_cmd(message: Message):
    text = "မင်္ဂလာပါ။ SaaS Master Bot မှ ကြိုဆိုပါတယ်။ 👑\n\n"
    text += "လုပ်ငန်းရှင် Bot အသစ်ထည့်ရန် အောက်ပါအတိုင်း ရိုက်ထည့်ပါ-\n"
    text += "👉 `/addbot <Bot_Token>`"
    await message.answer(text, parse_mode="Markdown")

@master_router.message(Command("addbot"))
async def add_bot_cmd(message: Message):
    # စာသားကို ခွဲထုတ်ခြင်း (ဥပမာ - /addbot 12345:ABCDE)
    args = message.text.split()
    if len(args) != 2:
        await message.answer("❌ ပုံစံမှားနေပါသည်။ \nဥပမာ - `/addbot 123456:ABCDEFGHIJK...`", parse_mode="Markdown")
        return
    
    token = args[1]
    
    # Database ထဲတွင် ရှိပြီးသားလား စစ်ဆေးခြင်း
    existing_bot = await db.businesses.find_one({"bot_token": token})
    if existing_bot:
        await message.answer("⚠️ ဒီ Bot Token က စနစ်ထဲမှာ ထည့်သွင်းပြီးသား ဖြစ်နေပါတယ်။")
        return

    # Database သို့ သိမ်းဆည်းခြင်း
    await db.businesses.insert_one({"bot_token": token, "status": "active"})
    
    # 💥 Bot အသစ်ကို ချက်ချင်း Run ပေးရန် (core.bot_manager ထဲက function ကို လှမ်းခေါ်ပါမည်)
    from core.bot_manager import start_client_bot 
    asyncio.create_task(start_client_bot(token))
    
    await message.answer("✅ Client Bot အသစ် အောင်မြင်စွာ ထည့်သွင်းပြီးပါပြီ။ ၎င်း Bot ကို သွားရောက် အသုံးပြုနိုင်ပါပြီ။")
