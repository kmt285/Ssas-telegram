from aiogram import Router, Bot
from aiogram.types import Message
from aiogram.filters import CommandStart
from core.database import db
from handlers.client_admin import admin_kb

client_router = Router()

@client_router.message(CommandStart())
async def client_start_cmd(message: Message, bot: Bot):
    # Database ထဲမှ Bot အချက်အလက်များကို ရှာခြင်း
    business = await db.businesses.find_one({"bot_token": bot.token})
    if not business:
        return

    owner_id = business.get("owner_id")

    # လာနှိပ်သူသည် ပိုင်ရှင် (Owner) ဖြစ်နေပါက
    if message.from_user.id == owner_id:
        text = "🛠 **လုပ်ငန်းရှင် Admin Panel** မှ ကြိုဆိုပါတယ်။\n\nလိုအပ်သော လုပ်ဆောင်ချက်ကို အောက်ပါခလုတ်များမှ ရွေးချယ်ပါ။"
        await message.answer(text, reply_markup=admin_kb(), parse_mode="Markdown")
        
    # သာမန် Customer လာနှိပ်ပါက
    else:
        text = "မင်္ဂလာပါ။ ကျွန်ုပ်တို့၏ VIP ဝန်ဆောင်မှုမှ ကြိုဆိုပါတယ်။ 🌟\n\nအောက်ပါ Menu များမှ တစ်ဆင့် ဝန်ဆောင်မှုများကို ဝယ်ယူနိုင်ပါသည်။"
        # (နောက်ပိုင်းတွင် ဝယ်ယူရန် ခလုတ်များ ဤနေရာ၌ ထည့်သွင်းမည်)
        await message.answer(text)
