from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from core.database import db
from utils.states import AdminSetup

client_admin_router = Router()

def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 ငွေပေးချေမှု အကောင့်ထည့်ရန်", callback_data="set_payment")],
        [InlineKeyboardButton(text="➕ Service အသစ်ထည့်ရန်", callback_data="add_service")]
    ])

@client_admin_router.callback_query(F.data == "set_payment")
async def set_payment_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
    # လုံခြုံရေး - ပိုင်ရှင်မှလွဲ၍ အခြားသူ ခလုတ်နှိပ်ပါက ပယ်ချမည်
    business = await db.businesses.find_one({"bot_token": bot.token})
    if callback.from_user.id != business.get("owner_id"):
        await callback.answer("❌ သင်သည် ဤ Bot ၏ Admin မဟုတ်ပါ။", show_alert=True)
        return

    text = "💳 သင့်၏ ငွေပေးချေမှု အချက်အလက်များကို ရိုက်ထည့်ပါ။\n(ဥပမာ - KPay: 09123456789, Wave: 09987654321)"
    await callback.message.answer(text)
    await state.set_state(AdminSetup.waiting_for_payment_info)
    await callback.answer()

@client_admin_router.message(AdminSetup.waiting_for_payment_info)
async def receive_payment_info(message: Message, bot: Bot, state: FSMContext):
    await db.businesses.update_one(
        {"bot_token": bot.token}, 
        {"$set": {"payment_info": message.text}}
    )
    await message.answer("✅ ငွေပေးချေမှု အချက်အလက်များကို အောင်မြင်စွာ သိမ်းဆည်းပြီးပါပြီ။")
    await state.clear()

# --- Service အသစ် ထည့်သွင်းခြင်း လုပ်ငန်းစဉ် ---

@client_admin_router.callback_query(F.data == "add_service")
async def add_service_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
    # လုံခြုံရေး စစ်ဆေးခြင်း
    business = await db.businesses.find_one({"bot_token": bot.token})
    if callback.from_user.id != business.get("owner_id"):
        await callback.answer("❌ သင်သည် ဤ Bot ၏ Admin မဟုတ်ပါ။", show_alert=True)
        return

    await callback.message.answer("📝 ဝန်ဆောင်မှု (Service) အမည်ကို ရိုက်ထည့်ပါ။\n(ဥပမာ - VIP Trading Signals, Premium English Course)")
    await state.set_state(AdminSetup.waiting_for_service_name)
    await callback.answer()

@client_admin_router.message(AdminSetup.waiting_for_service_name)
async def receive_service_name(message: Message, state: FSMContext):
    # အမည်ကို ယာယီ မှတ်ထားမည်
    await state.update_data(service_name=message.text)
    
    await message.answer("💰 ဤ Service အတွက် ဈေးနှုန်းကို ရိုက်ထည့်ပါ။\n(ဥပမာ - 15000)")
    await state.set_state(AdminSetup.waiting_for_service_price)

@client_admin_router.message(AdminSetup.waiting_for_service_price)
async def receive_service_price(message: Message, state: FSMContext):
    # ဂဏန်းဟုတ်မဟုတ် စစ်ဆေးခြင်း
    if not message.text.isdigit():
        await message.answer("⚠️ ကျေးဇူးပြု၍ ဂဏန်းသာ ရိုက်ထည့်ပါ။ (ဥပမာ - 15000)")
        return
        
    await state.update_data(service_price=int(message.text))
    
    text = "⏳ ဤ Service ၏ သက်တမ်း (ရက်အရေအတွက်) ကို ရိုက်ထည့်ပါ။\nတစ်သက်လုံး (Lifetime) သုံးခွင့်ပြုမည်ဆိုပါက 0 ဟု ရိုက်ထည့်ပါ။\n(ဥပမာ - ၁ လ အတွက် 30)"
    await message.answer(text)
    await state.set_state(AdminSetup.waiting_for_service_duration)

@client_admin_router.message(AdminSetup.waiting_for_service_duration)
async def receive_service_duration(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ ကျေးဇူးပြု၍ ဂဏန်းသာ ရိုက်ထည့်ပါ။ (ဥပမာ - 30)")
        return
        
    await state.update_data(service_duration=int(message.text))
    
    text = "🔗 ဝယ်ယူသူများကို ထည့်သွင်းမည့် Private Group / Channel Link ကို ရိုက်ထည့်ပါ။\n(ဥပမာ - https://t.me/+AbCdEfGhIjK)"
    await message.answer(text)
    await state.set_state(AdminSetup.waiting_for_service_link)

@client_admin_router.message(AdminSetup.waiting_for_service_link)
async def receive_service_link(message: Message, state: FSMContext, bot: Bot):
    # ယာယီမှတ်ထားသော အချက်အလက်များအားလုံးကို ပြန်ထုတ်ယူခြင်း
    data = await state.get_data()
    service_name = data['service_name']
    service_price = data['service_price']
    service_duration = data['service_duration']
    service_link = message.text

    # Database ထဲရှိ 'services' Collection သို့ အတည်ပြု သိမ်းဆည်းခြင်း
    await db.services.insert_one({
        "bot_token": bot.token,
        "name": service_name,
        "price": service_price,
        "duration": service_duration,
        "link": service_link,
        "status": "active"
    })

    # အောင်မြင်ကြောင်း ပြန်လည်အကြောင်းကြားခြင်း
    success_text = (
        "✅ **Service အသစ် အောင်မြင်စွာ ဖန်တီးပြီးပါပြီ!**\n\n"
        f"🔹 **အမည်:** {service_name}\n"
        f"🔹 **ဈေးနှုန်း:** {service_price} ကျပ်\n"
        f"🔹 **သက်တမ်း:** {'Lifetime' if service_duration == 0 else f'{service_duration} ရက်'}\n"
        f"🔹 **Link:** {service_link}\n\n"
        "Customer များ /start နှိပ်ပါက ဤ Service ကို မြင်တွေ့ရမည် ဖြစ်သည်။"
    )
    await message.answer(success_text, parse_mode="Markdown")
    
    # State များကို ရှင်းလင်းခြင်း
    await state.clear()
