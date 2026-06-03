from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ChatJoinRequest
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from bson.objectid import ObjectId
from core.database import db
from handlers.client_admin import admin_kb
from utils.states import UserBooking

client_router = Router()

@client_router.message(CommandStart())
async def client_start_cmd(message: Message, bot: Bot, state: FSMContext):
    await state.clear() # မည်သည့်အခြေအနေမဆို သန့်ရှင်းရေးလုပ်မည်
    
    business = await db.businesses.find_one({"bot_token": bot.token})
    if not business:
        return

    owner_id = business.get("owner_id")

    # လုပ်ငန်းရှင် (Owner) လာနှိပ်ပါက
    if message.from_user.id == owner_id:
        text = "🛠 **လုပ်ငန်းရှင် Admin Panel** မှ ကြိုဆိုပါတယ်။\n\nလိုအပ်သော လုပ်ဆောင်ချက်ကို အောက်ပါခလုတ်များမှ ရွေးချယ်ပါ။"
        await message.answer(text, reply_markup=admin_kb(), parse_mode="Markdown")
        
    # သာမန် ဝယ်ယူသူ (Customer) လာနှိပ်ပါက
    else:
        # လက်ရှိ Bot ၏ Active ဖြစ်နေသော Services များကို ရှာမည်
        cursor = db.services.find({"bot_token": bot.token, "status": "active"})
        services = await cursor.to_list(length=100)
        
        if not services:
            await message.answer("🌟 ကျွန်ုပ်တို့၏ VIP ဝန်ဆောင်မှုမှ ကြိုဆိုပါတယ်။\n\nလောလောဆယ် ဝယ်ယူနိုင်သော ဝန်ဆောင်မှုများ မရှိသေးပါ။")
            return
            
        text = "🌟 **ကျွန်ုပ်တို့၏ VIP ဝန်ဆောင်မှုမှ ကြိုဆိုပါတယ်။** 🌟\n\nဝယ်ယူလိုသော ဝန်ဆောင်မှုကို အောက်ပါခလုတ်များမှ ရွေးချယ်ပါ-"
        
        keyboard = []
        for s in services:
            keyboard.append([InlineKeyboardButton(text=f"🔹 {s['name']} - {s['price']} ကျပ်", callback_data=f"buy_{s['_id']}")])
            
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await message.answer(text, reply_markup=reply_markup, parse_mode="Markdown")

# Customer က Service တစ်ခုခုကို ဝယ်ယူရန် နှိပ်လိုက်သောအခါ
@client_router.callback_query(F.data.startswith("buy_"))
async def buy_service_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
    service_id_str = callback.data.split("_")[1]
    
    service = await db.services.find_one({"_id": ObjectId(service_id_str)})
    business = await db.businesses.find_one({"bot_token": bot.token})
    
    if not service or not business:
        await callback.answer("❌ ဝန်ဆောင်မှု ရှာမတွေ့ပါ။", show_alert=True)
        return
        
    payment_info = business.get("payment_info", "ငွေပေးချေမှုအချက်အလက် မရှိသေးပါ။ Admin ကို ဆက်သွယ်ပါ။")
    
    text = (
        f"💳 **'{service['name']}' ကို ဝယ်ယူရန် ငွေလွှဲရမည့် အချက်အလက်**\n\n"
        f"{payment_info}\n\n"
        f"💵 **ကျသင့်ငွေ:** {service['price']} ကျပ်\n\n"
        "⚠️ **အရေးကြီးသည်:** ငွေလွှဲပြီးပါက ငွေလွှဲပြေစာ (Slip Screenshot) ကို ဤနေရာသို့ ဓာတ်ပုံ (Photo) အဖြစ် ပို့ပေးပါ။"
    )
    
    await callback.message.answer(text, parse_mode="Markdown")
    await state.set_state(UserBooking.waiting_for_slip)
    await state.update_data(buy_service_id=service_id_str)
    await callback.answer()

# Customer ဆီမှ Slip ပုံကို လက်ခံရရှိသောအခါ
@client_router.message(UserBooking.waiting_for_slip, F.photo)
async def receive_slip_photo(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    service_id_str = data.get("buy_service_id")
    
    service = await db.services.find_one({"_id": ObjectId(service_id_str)})
    business = await db.businesses.find_one({"bot_token": bot.token})
    
    if not service or not business:
        await message.answer("❌ စနစ်ချို့ယွင်းမှု ရှိနေပါသည်။ ကျေးဇူးပြု၍ /start ကို ပြန်နှိပ်ပါ။")
        await state.clear()
        return
        
    # Database တွင် စောင့်ဆိုင်းဆဲစာရင်း (Pending Subscription) သွားမှတ်မည်
    sub_result = await db.subscriptions.insert_one({
        "user_id": message.from_user.id,
        "username": message.from_user.username,
        "full_name": message.from_user.full_name,
        "bot_token": bot.token,
        "service_id": service_id_str,
        "status": "pending"
    })
    sub_id = str(sub_result.inserted_id)
    
    # ဝယ်ယူသူထံ စာပြန်မည်
    await message.answer("⏳ လူကြီးမင်း၏ ငွေလွှဲပြေစာကို လက်ခံရရှိပါပြီ။ Admin ၏ စစ်ဆေးအတည်ပြုချက်ကို ခေတ္တစောင့်ဆိုင်းပေးပါ။ အတည်ပြုပြီးပါက Group Link ကို အလိုအလျောက် ပေးပို့ပေးပါမည်။")
    await state.clear()
    
    # ทำการ ပိုင်ရှင် (Owner) ဆီသို့ Slip ပုံနှင့် Approve/Reject ခလုတ် လှမ်းပို့မည်
    owner_id = business.get("owner_id")
    photo_id = message.photo[-1].file_id # အကြည်ဆုံးပုံကို ယူမည်
    
    admin_text = (
        f"💰 **ငွေလွှဲပြေစာအသစ် ရောက်ရှိလာပါသည်!**\n\n"
        f"👤 **ဝယ်ယူသူ:** {message.from_user.full_name} (@{message.from_user.username})\n"
        f"📦 **Service:** {service['name']}\n"
        f"💵 **ဈေးနှုန်း:** {service['price']} ကျပ်\n"
    )
    
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Approve (လက်ခံမည်)", callback_data=f"sub_approve_{sub_id}"),
            InlineKeyboardButton(text="❌ Reject (ပယ်ချမည်)", callback_data=f"sub_reject_{sub_id}")
        ]
    ])
    
    try:
        await bot.send_photo(chat_id=owner_id, photo=photo_id, caption=admin_text, reply_markup=admin_keyboard, parse_mode="Markdown")
    except Exception as e:
        print(f"Failed to send slip to admin: {e}")

# ==========================================
# 💥 NEW: Request to Join တောင်းလာသူများကို စစ်ဆေးခြင်း
# ==========================================
@client_router.chat_join_request()
async def handle_join_request(update: ChatJoinRequest, bot: Bot):
    user_id = update.from_user.id
    chat_id = str(update.chat.id) # ဝင်ခွင့်တောင်းသော Group ၏ ID

    # ထို User တွင် လက်ရှိ Bot ၌ Active ဖြစ်နေသော Subscription များရှိမရှိ ရှာမည်
    cursor = db.subscriptions.find({
        "user_id": user_id, 
        "bot_token": bot.token, 
        "status": "active"
    })
    subs = await cursor.to_list(length=100)

    is_allowed = False
    for sub in subs:
        # User ဝယ်ထားသော Service ထဲက Link(Chat ID) နှင့် ဝင်ခွင့်တောင်းသော Chat ID တူမတူ စစ်ဆေးမည်
        service = await db.services.find_one({"_id": ObjectId(sub["service_id"])})
        if service and service.get("link") == chat_id:
            is_allowed = True
            break

    # သေချာစွာ စစ်ဆေးပြီးနောက်
    if is_allowed:
        await update.approve() # မှန်ကန်သော ဝယ်ယူသူဖြစ်၍ အလိုအလျောက် လက်ခံပေးမည်
        try:
            await bot.send_message(user_id, "✅ Group/Channel သို့ ဝင်ခွင့်ပြုလိုက်ပါပြီ။")
        except:
            pass
    else:
        await update.decline() # မသက်ဆိုင်သူ ဖြစ်၍ အလိုအလျောက် ပယ်ချမည်
        try:
            await bot.send_message(user_id, "❌ သင့်တွင် ဝင်ခွင့် (Active Subscription) မရှိသောကြောင့် ဝင်ခွင့်ပယ်ချလိုက်ပါသည်။")
        except:
            pass

    # ==========================================
    # 💥 လင့်ခ်ကို အလိုအလျောက် ပိတ်ပစ်မည် (Auto-Revoke) 
    # ==========================================
    # User ဝင်ခွင့်တောင်းလိုက်သော လင့်ခ်အား အခြားသူများ ထပ်သုံးမရအောင် ချက်ချင်း ပိတ်ပစ်မည်
    if update.invite_link:
        try:
            await bot.revoke_chat_invite_link(chat_id=chat_id, invite_link=update.invite_link.invite_link)
        except Exception as e:
            print(f"Failed to revoke link: {e}")
