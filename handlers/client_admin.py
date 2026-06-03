from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from core.database import db
from utils.states import AdminSetup

client_admin_router = Router()

# Admin Menu ခလုတ်များ
def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 ငွေပေးချေမှု အကောင့်ထည့်ရန်", callback_data="set_payment")],
        [InlineKeyboardButton(text="➕ Service အသစ်ထည့်ရန် (Next Step)", callback_data="add_service")]
    ])

@client_admin_router.message(Command("admin"))
async def admin_panel(message: Message, bot: Bot):
    business = await db.businesses.find_one({"bot_token": bot.token})
    if not business:
        return

    # ပထမဆုံး /admin နှိပ်သူကို ပိုင်ရှင် (Owner) အဖြစ် Database တွင် မှတ်မည်
    if not business.get("owner_id"):
        await db.businesses.update_one({"bot_token": bot.token}, {"$set": {"owner_id": message.from_user.id}})
        owner_id = message.from_user.id
    else:
        owner_id = business.get("owner_id")

    # ပိုင်ရှင် မဟုတ်သူ ဝင်နှိပ်ပါက တားဆီးမည်
    if message.from_user.id != owner_id:
        await message.answer("❌ သင်သည် ဤ Bot ၏ Admin မဟုတ်ပါ။")
        return

    text = "🛠 **လုပ်ငန်းရှင် Admin Panel** မှ ကြိုဆိုပါတယ်။\n\nလိုအပ်သော လုပ်ဆောင်ချက်ကို အောက်ပါခလုတ်များမှ ရွေးချယ်ပါ။"
    await message.answer(text, reply_markup=admin_kb(), parse_mode="Markdown")

# --- ငွေပေးချေမှု အကောင့် သတ်မှတ်ခြင်း (Payment Info) ---
@client_admin_router.callback_query(F.data == "set_payment")
async def set_payment_callback(callback: CallbackQuery, state: FSMContext):
    text = "💳 သင့်၏ ငွေပေးချေမှု အချက်အလက်များကို ရိုက်ထည့်ပါ။\n(ဥပမာ - KPay: 09123456789, Wave: 09987654321)"
    await callback.message.answer(text)
    await state.set_state(AdminSetup.waiting_for_payment_info)
    await callback.answer()

@client_admin_router.message(AdminSetup.waiting_for_payment_info)
async def receive_payment_info(message: Message, bot: Bot, state: FSMContext):
    # Database ထဲသို့ သိမ်းဆည်းခြင်း
    await db.businesses.update_one(
        {"bot_token": bot.token}, 
        {"$set": {"payment_info": message.text}}
    )
    await message.answer("✅ ငွေပေးချေမှု အချက်အလက်များကို အောင်မြင်စွာ သိမ်းဆည်းပြီးပါပြီ။")
    await state.clear()
