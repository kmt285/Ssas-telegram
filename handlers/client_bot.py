from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart

# Client Bot အတွက် Router (လမ်းကြောင်း)
client_router = Router()

@client_router.message(CommandStart())
async def client_start_cmd(message: Message):
    await message.answer("မင်္ဂလာပါ။ ကျွန်ုပ်တို့၏ VIP ဝန်ဆောင်မှုမှ ကြိုဆိုပါတယ်။\n(ဒါက လုပ်ငန်းရှင်ရဲ့ Client Bot ဖြစ်ပါတယ်။)")
