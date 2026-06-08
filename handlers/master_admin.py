import os
import asyncio
from datetime import datetime, timedelta
from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from bson.objectid import ObjectId
from core.database import db
from utils.states import MasterSetup
from utils.states import MasterBooking
from utils.states import MasterBroadcast

master_router = Router()

# ==========================================
# 💥 Render Environment Variable မှ Super Admin ID များကို ဆွဲယူခြင်း
# ==========================================
admin_ids_str = os.getenv("SUPER_ADMIN_IDS", "")
SUPER_ADMINS = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip().isdigit()]

@master_router.message(CommandStart())
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    
    # 👑 Super Admin ဝင်လာလျှင်
    if message.from_user.id in SUPER_ADMINS:
        text = "👑 **SaaS Master Super Admin Bot** မှ ကြိုဆိုပါတယ်။\n\nသင်သည် Super Admin ဖြစ်သောကြောင့် အောက်ပါ ခလုတ်ကိုနှိပ်၍ စနစ်တစ်ခုလုံးကို စီမံနိုင်ပါသည်။"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 စနစ်တစ်ခုလုံး၏ စာရင်းဇယားကြည့်ရန်", callback_data="show_stats")]
        ])
        return await message.answer(text, reply_markup=kb, parse_mode="Markdown")
    
    # 🏢 သာမန် လုပ်ငန်းရှင် ဝင်လာလျှင် Database ကို အရင်ဆွဲထုတ်မည်
    biz = await db.businesses.find_one({"owner_id": message.from_user.id})
    config = await db.system_config.find_one({"_id": "master_config"})
    
    # Bot မချိတ်ရသေးသူ ဖြစ်ပါက
    if not biz:
        text = "🎉မင်္ဂလာပါခင်ဗျာ ကျွန်တော်တို့ Bot Myanmar Community မှ ကြိုဆိုပါတယ်။\n\nလူကြီးမင်း၏ ကိုယ်ပိုင် VIP Bot ကို ယခုဘဲ စတင်ဖန်တီးလိုက်ပါ။"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="➕ Bot အသစ် ဖန်တီးရန်", callback_data="create_new_bot")]])
        return await message.answer(text, reply_markup=kb, parse_mode="Markdown")
        
    # သက်တမ်းတွက်ချက်ခြင်း
    exp = biz.get("expires_at")
    if not exp:
        exp_text = "Lifetime"
        status_text = "🟢 Active"
    else:
        exp_text = exp.strftime("%d-%m-%Y")
        status_text = "🔴 Suspended" if biz.get("status") == "suspended" else "🟢 Active"

    # 💥 [အရေးကြီးသော ပြင်ဆင်ချက်] - bot_username ကို Token မှတစ်ဆင့် လှမ်းယူခြင်း
    try:
        temp_bot = Bot(token=biz['bot_token'])
        me = await temp_bot.get_me()
        bot_username = me.username
        await temp_bot.session.close()
    except Exception:
        bot_username = "Unknown"

    # 💥 NEW: Subscription Mode ပွင့်/မပွင့် စစ်ဆေးခြင်း
    is_sub_mode = config.get("subscription_mode", False) if config else False

    if not is_sub_mode:
        # 🟢 Free Mode တွင် ပြသမည့် UI (Payment နှင့် ခလုတ်များ မပြပါ)
        text = (
            f"🏢 Your Bot Information \n\n"
            f"🤖 Your Bot : @{bot_username}\n"
            f"⏳ Expire Date : {exp_text}\n"
            f"📊 Status : {status_text}\n\n"
            "🎁 လက်ရှိတွင် စနစ်ကို အခမဲ့အသုံးပြုခွင့် ပေးထားပါသည်။"
        )
        await message.answer(text, parse_mode="Markdown")
    else:
        # 🔴 Subscription Mode တွင် ပြသမည့် UI (Payment ပြမည်)
        pay_info = config.get("payment_info", "ငွေပေးချေရန် အကောင့် မသတ်မှတ်ရသေးပါ။ Admin ထံ ဆက်သွယ်ပါ။ @botdistribution") if config else "Admin ထံ ဆက်သွယ်ပါ။"
        text = (
            f"🏢 Your Bot Information \n\n"
            f"🤖 Your Bot: @{bot_username}\n"
            f"⏳ Expire Date : {exp_text}\n"
            f"📊 Status : {status_text}\n\n"
            f"🏦 Payment Info : \n`{pay_info}`\n\n"
            "💳 အောက်ပါ Plan များမှ ကြိုက်နှစ်သက်ရာ ရွေးချယ်နိုင်ပါသည်။"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=" 1 Month Plan - 10,000 MMK", callback_data="buyplan_30")],
            [InlineKeyboardButton(text=" 3 Months Plan - 25,000 MMK", callback_data="buyplan_90")],
            [InlineKeyboardButton(text=" 6 Months Plan - 40,000 MMK", callback_data="buyplan_180")],
            [InlineKeyboardButton(text=" Lifetime Plan - 80,000 MMK", callback_data="buyplan_0")]
        ])
        await message.answer(text, reply_markup=kb, parse_mode="Markdown")
# ==========================================
# 🏢 လုပ်ငန်းရှင်များ Bot Token ထည့်သွင်းခြင်း စနစ်
# ==========================================
@master_router.callback_query(F.data == "create_new_bot")
async def ask_bot_token(callback: CallbackQuery, state: FSMContext):
    text = "🤖 Bot Token ထည့်သွင်းပါ\n\n"
    text += "1. @BotFather သို့သွား၍ `/newbot` ဖြင့် Bot အသစ်တစ်ခု ဖန်တီးနိုင်ပါသည်။\n"
    text += "2. ရရှိလာသော HTTP API Token ကို ဤနေရာတွင် Copy/Paste လုပ်ပါ။"
    await callback.message.answer(text, parse_mode="Markdown")
    await state.set_state(MasterSetup.waiting_for_bot_token)
    await callback.answer()

@master_router.message(MasterSetup.waiting_for_bot_token)
async def receive_bot_token(message: Message, state: FSMContext):
    token = message.text.strip()
    
    if ":" not in token:
        return await message.answer("❌ Token ပုံစံ မှားယွင်းနေပါသည်။ သေချာစွာ ပြန်လည်စစ်ဆေးပြီး ထပ်မံရိုက်ထည့်ပါ။")
        
    existing_bot = await db.businesses.find_one({"bot_token": token})
    if existing_bot:
        return await message.answer("⚠️ ဤ Bot Token မှာ စနစ်ထဲတွင် ထည့်သွင်းပြီးသား ဖြစ်နေပါသည်။")

    await message.answer("⏳ Verifying Bot Token... Please wait.")

    try:
        temp_bot = Bot(token=token)
        me = await temp_bot.get_me()
        bot_username = me.username
        await temp_bot.session.close() 
    except Exception as e:
        return await message.answer("❌ Bot Token is incorrect!")

    # 💥 NEW: လက်ရှိ System သည် Subscription Mode ပြောင်းပြီးသား ဟုတ်/မဟုတ် စစ်ဆေးခြင်း
    config = await db.system_config.find_one({"_id": "master_config"})
    is_sub_mode = config.get("subscription_mode", False) if config else False

    created_date = datetime.utcnow()
    # Subscription Mode ဖြစ်နေလျှင် ၃၀ ရက် ပေးမည်။ မဟုတ်လျှင် Lifetime (None) ပေးမည်။
    expires_date = created_date + timedelta(days=30) if is_sub_mode else None

    await db.businesses.insert_one({
        "bot_token": token, 
        "status": "active",
        "owner_id": message.from_user.id,
        "owner_username": message.from_user.username, 
        "created_at": created_date,
        "expires_at": expires_date
    })
    
    from core.bot_manager import start_client_bot 
    asyncio.create_task(start_client_bot(token))
    
    dur_text = "(၁) လ" if is_sub_mode else "Lifetime"
    success_text = f"✅ Client Bot (@{bot_username}) အသစ် အောင်မြင်စွာ တည်ဆောက်ပြီးပါပြီ။**\n\n"
    success_text += f"🎁 ဤ Bot အား {dur_text} အခမဲ့ အသုံးပြုခွင့် ပေးထားပါသည်။\n"
    success_text += f"👉 ယခု သင့်၏ Bot ( https://t.me/{bot_username} ) ဆီသွား၍ `/start` ကိုနှိပ်ပြီး ဝန်ဆောင်မှုများကို စတင် ဖန်တီးနိုင်ပါပြီ။"
    await message.answer(success_text, parse_mode="Markdown")
    await state.clear()

# ==========================================
# 📊 စနစ်တစ်ခုလုံးကို စောင့်ကြည့်မည့် Super Admin Panel (Admin သီးသန့်)
# ==========================================
@master_router.callback_query(F.data == "show_stats")
async def view_system_stats_cb(callback: CallbackQuery):
    # 💥 အောက်ပါစာကြောင်းရှိ fromuser ကို from_user အဖြစ် ပြင်ဆင်ထားပါသည်
    if callback.from_user.id not in SUPER_ADMINS: return 
    
    total_bots = await db.businesses.count_documents({})
    total_services = await db.services.count_documents({})
    active_users = await db.subscriptions.count_documents({"status": "active"})
    
    stats_text = (
        "📊 **SaaS System Overview (စာရင်းဇယား)**\n\n"
        f"🏢 **လုပ်ငန်းရှင် Bots:** {total_bots} ခု\n"
        f"📦 **စုစုပေါင်း Services:** {total_services} မျိုး\n"
        f"👥 **Active Users:** {active_users} ဦး\n\n"
        "စနစ်တစ်ခုလုံး တည်ငြိမ်စွာ လည်ပတ်နေပါသည်။ 🚀"
    )
    
    # 💥 လက်ရှိ Subscription ဖွင့်ထားသလား ပိတ်ထားသလား စစ်ဆေးမည်
    config = await db.system_config.find_one({"_id": "master_config"})
    is_sub_mode = config.get("subscription_mode", False) if config else False
    
    # အခြေအနေပေါ်မူတည်၍ ခလုတ်စာသားကို ပြောင်းလဲပြသမည်
    sub_btn_text = "🔴 Subscription စနစ် ပိတ်မည် (Free Mode)" if is_sub_mode else "🟢 Subscription စနစ်သို့ အားလုံးပြောင်းလဲမည်"
    sub_callback = "disable_sub_mode" if is_sub_mode else "trigger_sub_transition"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏢 လုပ်ငန်းရှင်များစာရင်း အသေးစိတ်ကြည့်ရန်", callback_data="view_businesses")],
        [InlineKeyboardButton(text=sub_btn_text, callback_data=sub_callback)],
        [InlineKeyboardButton(text="📢 လုပ်ငန်းရှင်များထံ Broadcast ပို့ရန်", callback_data="master_broadcast")],
        [InlineKeyboardButton(text="🧹 Database အမှိုက်များ ရှင်းလင်းမည်", callback_data="clean_database")]
    ])
    await callback.message.edit_text(stats_text, reply_markup=kb, parse_mode="Markdown")
    
# --- လုပ်ငန်းရှင်များ စာရင်းပြသခြင်း ---
@master_router.callback_query(F.data == "view_businesses")
async def list_businesses(callback: CallbackQuery):
    if callback.from_user.id not in SUPER_ADMINS: return 
    
    businesses = await db.businesses.find({}).to_list(length=100)
    
    if not businesses:
        await callback.answer("လုပ်ငန်းရှင် မရှိသေးပါ။", show_alert=True)
        return

    keyboard = []
    for biz in businesses:
        token_prefix = biz['bot_token'][:10]
        keyboard.append([InlineKeyboardButton(text=f"🤖 Bot: {token_prefix}...", callback_data=f"biz_{str(biz['_id'])}")])
    
    keyboard.append([InlineKeyboardButton(text="🔙 နောက်သို့", callback_data="show_stats")])
    
    await callback.message.edit_text(
        "🏢 **လုပ်ငန်းရှင်များ စာရင်း**\n\nအသေးစိတ်ကြည့်လိုသော Bot ကို ရွေးချယ်ပါ-", 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), 
        parse_mode="Markdown"
    )

# --- Bot တစ်ခုချင်းစီ၏ အသေးစိတ် အချက်အလက်များပြသခြင်း ---
@master_router.callback_query(F.data.startswith("biz_"))
async def view_business_detail(callback: CallbackQuery):
    if callback.from_user.id not in SUPER_ADMINS: return 
    
    biz_id = callback.data.split("_")[1]
    biz = await db.businesses.find_one({"_id": ObjectId(biz_id)})
    
    if not biz:
        await callback.answer("အချက်အလက် ရှာမတွေ့ပါ။", show_alert=True)
        return
        
    token = biz['bot_token']
    
    try:
        temp_bot = Bot(token=token)
        me = await temp_bot.get_me()
        bot_username = me.username
        await temp_bot.session.close()
    except:
        bot_username = "Unknown"

    user_count = await db.subscriptions.count_documents({"bot_token": token, "status": "active"})
    services = await db.services.find({"bot_token": token, "status": "active"}).to_list(length=100)
    
    is_suspended = biz.get("status") == "suspended"
    expires_at = biz.get("expires_at")
    
    if is_suspended:
        status_text = "🚫 Suspended ရပ်ဆိုင်းထားသည်"
        toggle_btn = "🟢 Bot အား ပြန်ဖွင့်ပေးမည်"
    elif expires_at:
        is_expired = datetime.utcnow() > expires_at
        exp_date_str = expires_at.strftime("%d-%m-%Y")
        status_text = "🔴 Expired (သက်တမ်းကုန်နေပါသည်)" if is_expired else f"🟢 Active (Exp: {exp_date_str})"
        toggle_btn = "🚫 Bot အား ရပ်ဆိုင်းမည် (Suspend)"
    else:
        status_text = "🟢 Active (Unlimited)"
        toggle_btn = "🚫 Bot အား ရပ်ဆိုင်းမည် (Suspend)"

    o_username = biz.get('owner_username')
    owner_display = f"@{o_username}" if o_username else "noexit"

    # 💥 ပြင်ဆင်ထားသော HTML ကုဒ်
    text = f"🤖 <b>Bot အမည်:</b> @{bot_username}\n"
    text += f"🔗 <b>Bot Link:</b> https://t.me/{bot_username}\n"
    text += f"👤 <b>Owner:</b> {owner_display} (ID: <code>{biz.get('owner_id', 'Unknown')}</code>)\n"
    text += f"👥 <b>လက်ရှိ Active Users:</b> {user_count} ဦး\n"
    text += f"⏳ <b>Bot အခြေအနေ:</b> {status_text}\n\n"
    text += "📦 <b>Services & Channels:</b>\n"
    
    keyboard = []
    for s in services:
        text += f" {s['name']} (Price: {s['price']})\n"
        if s['link'].startswith("-100") or s['link'].startswith("@"):
            keyboard.append([InlineKeyboardButton(text=f"🔗 '{s['name']}' Invite Link ယူရန်", callback_data=f"genlink_{str(s['_id'])}")])
    
    keyboard.append([InlineKeyboardButton(text=toggle_btn, callback_data=f"togglebot_{str(biz['_id'])}")])
    keyboard.append([InlineKeyboardButton(text="🗑 Bot အား အပြီးတိုင် ဖျက်သိမ်းမည်", callback_data=f"harddelete_{str(biz['_id'])}")])
    keyboard.append([InlineKeyboardButton(text="🔙 နောက်သို့", callback_data="view_businesses")])
    
    # 💥 parse_mode="HTML" ဟု ပြောင်းထားသည်
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML", disable_web_page_preview=True)

# --- Super Admin အတွက် Invite Link အလိုအလျောက် ထုတ်ပေးခြင်း ---
@master_router.callback_query(F.data.startswith("genlink_"))
async def generate_invite_link(callback: CallbackQuery):
    if callback.from_user.id not in SUPER_ADMINS: return 
    
    service_id = callback.data.split("_")[1]
    service = await db.services.find_one({"_id": ObjectId(service_id)})
    
    if not service:
        await callback.answer("Service ရှာမတွေ့ပါ။", show_alert=True)
        return
        
    token = service['bot_token']
    chat_id = service['link']
    
    try:
        temp_bot = Bot(token=token)
        link_obj = await temp_bot.create_chat_invite_link(chat_id=chat_id, member_limit=1)
        invite_link = link_obj.invite_link
        await temp_bot.session.close()
        
        await callback.answer()
        await callback.message.answer(
            f"✅ **{service['name']}** သို့ဝင်ရန် Invite Link ရရှိပါပြီ (တစ်ခါသုံး Link ဖြစ်ပါသည်) -\n{invite_link}",
            disable_web_page_preview=True
        )
    except Exception as e:
        await callback.answer("❌ Error: လုပ်ငန်းရှင်မှ ၎င်း၏ Group/Channel တွင် Bot အား Admin ခန့်ထားခြင်း မရှိသေးပါ။", show_alert=True)

# --- Bot ရပ်ဆိုင်းသည့် ကုဒ် ---
@master_router.callback_query(F.data.startswith("togglebot_"))
async def toggle_business_bot(callback: CallbackQuery):
    if callback.from_user.id not in SUPER_ADMINS: return 
    
    biz_id = callback.data.split("_")[1]
    biz = await db.businesses.find_one({"_id": ObjectId(biz_id)})
    
    if not biz:
        return
        
    new_status = "suspended" if biz.get("status") == "active" else "active"
    
    await db.businesses.update_one({"_id": ObjectId(biz_id)}, {"$set": {"status": new_status}})
    
    msg = "🚫 Bot အား အောင်မြင်စွာ ရပ်ဆိုင်းလိုက်ပါပြီ。" if new_status == "suspended" else "🟢 Bot အား အောင်မြင်စွာ ပြန်ဖွင့်ပေးလိုက်ပါပြီ。"
    await callback.answer(msg, show_alert=True)
    
    await callback.message.edit_text(f"{msg}\n\nအပြောင်းအလဲအား မြင်တွေ့ရရန် နောက်သို့ပြန်ထွက်ပြီး ပြန်ဝင်ကြည့်ပါ။", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 စာရင်းများသို့ ပြန်သွားရန်", callback_data="view_businesses")]]))

# ==========================================
# 🧹 Database ရှင်းလင်းရေး (Clean Database - 7 Days Grace Period)
# ==========================================
@master_router.callback_query(F.data == "clean_database")
async def clean_database_handler(callback: CallbackQuery):
    if callback.from_user.id not in SUPER_ADMINS: return 
    
    await callback.message.edit_text("⏳ **Database အား စတင် ရှင်းလင်းနေပါသည်...**\nခေတ္တစောင့်ဆိုင်းပါ။")
    
    # ၁။ (၇) ရက် ကျော်လွန်သွားသော သက်တမ်းကုန် Bot များ၏ Data များကို ရှင်းလင်းမည် (Token ကို ချန်ထားမည်)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    expired_businesses = await db.businesses.find({"expires_at": {"$lt": seven_days_ago}}).to_list(length=1000)
    
    cleaned_bots_count = 0
    for biz in expired_businesses:
        token = biz["bot_token"]
        # ထို Bot နှင့်သက်ဆိုင်သော Service နှင့် Subscription အားလုံးကို ရှင်းလင်းမည်
        await db.services.delete_many({"bot_token": token})
        await db.subscriptions.delete_many({"bot_token": token})
        cleaned_bots_count += 1

    # ၂။ ငြင်းပယ်ခံထားရသော (Rejected) စာရင်းဟောင်းများကို ရှင်းလင်းမည်
    del_rejected = await db.subscriptions.delete_many({"status": "rejected"})
    
    text = (
        "✅ **Database ရှင်းလင်းခြင်း အောင်မြင်ပါသည်။**\n\n"
        f"🧹 သက်တမ်း (၇) ရက်ကျော်လွန်သွားသော Bot ပေါင်း **{cleaned_bots_count}** ခု၏ Services နှင့် Users များကို ရှင်းလင်းပြီးပါပြီ။\n*(မှတ်ချက် - ၎င်းတို့၏ Bot Token များကိုမူ ဆက်လက် ထိန်းသိမ်းထားပါသည်)*\n\n"
        f"🗑 ပယ်ချထားသော (Rejected) ပြေစာဟောင်း **{del_rejected.deleted_count}** ခုကို ရှင်းလင်းပြီးပါပြီ။"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 စာရင်းဇယားသို့ ပြန်သွားရန်", callback_data="show_stats")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

# ==========================================
# 🗑 အပြီးတိုင် ဖျက်သိမ်းခြင်း (Hard Delete)
# ==========================================
@master_router.callback_query(F.data.startswith("harddelete_"))
async def hard_delete_bot(callback: CallbackQuery):
    if callback.from_user.id not in SUPER_ADMINS: return 
    
    biz_id = callback.data.split("_")[1]
    biz = await db.businesses.find_one({"_id": ObjectId(biz_id)})
    
    if biz:
        token = biz["bot_token"]
        # Database ထဲမှ ဤ Bot နှင့် ပတ်သက်သမျှ အရာအားလုံးကို အမြစ်ပြတ် ရှင်းထုတ်မည်
        await db.businesses.delete_one({"_id": ObjectId(biz_id)})
        await db.services.delete_many({"bot_token": token})
        await db.subscriptions.delete_many({"bot_token": token})
        
    await callback.answer("✅ Bot အား Database မှ အပြီးတိုင် ဖျက်သိမ်းလိုက်ပါပြီ။", show_alert=True)
    
    # ရှင်းပြီးပါက လုပ်ငန်းရှင်များစာရင်းသို့ ပြန်သွားမည်
    await list_businesses(callback)

# 💳 Master Payment Info (Super Admin မှ သတ်မှတ်ရန်)
# ==========================================
@master_router.message(Command("setpayment"))
async def set_master_payment(message: Message):
    if message.from_user.id not in SUPER_ADMINS: return
    
    pay_info = message.text.replace("/setpayment", "").strip()
    if not pay_info:
        return await message.answer("❌ ပုံစံမှားနေပါသည်။\nအသုံးပြုရန်: `/setpayment KPay - 09123456789 (U Mya)`", parse_mode="Markdown")
        
    await db.system_config.update_one(
        {"_id": "master_config"}, 
        {"$set": {"payment_info": pay_info}}, 
        upsert=True
    )
    await message.answer(f"✅ လုပ်ငန်းရှင်များ ငွေလွှဲရန် အကောင့်ကို အောင်မြင်စွာ မှတ်သားပြီးပါပြီ။\n\n{pay_info}")

# ==========================================
# 🛍 လုပ်ငန်းရှင်များ Subscription ဝယ်ယူခြင်း (Renew Plans)
# ==========================================
@master_router.callback_query(F.data.startswith("buyplan_"))
async def buy_master_plan(callback: CallbackQuery, state: FSMContext):
    days = int(callback.data.split("_")[1])
    
    config = await db.system_config.find_one({"_id": "master_config"})
    pay_info = config.get("payment_info", "ငွေပေးချေမှု အချက်အလက် မရှိသေးပါ။ Platform Admin ထံ ဆက်သွယ်ပါ။ @botdistribution") if config else "Admin ထံ ဆက်သွယ်ပါ။"
    
    plan_names = {30: "၁ လ (30 Days)", 90: "၃ လ (90 Days)", 180: "၆ လ (180 Days)", 0: "တစ်သက်လုံး (Lifetime)"}
    prices = {30: "30,000", 90: "80,000", 180: "150,000", 0: "500,000"} # 💥 ဤနေရာတွင် ဈေးနှုန်းများ ပြင်နိုင်သည်
    
    text = (
        f"💳 '{plan_names[days]}' သက်တမ်းတိုးရန် ငွေလွှဲရမည့် အချက်အလက်\n\n"
        f"🏦 Payment Account : {pay_info}\n"
        f"💵 Price : {prices[days]} MMK\n\n"
        "⚠️ Important : ငွေလွှဲပြီးပါက ငွေလွှဲပြေစာ (Slip Screenshot) ကို ဤနေရာသို့ ဓာတ်ပုံအဖြစ် ပို့ပေးပါ။"
    )
    
    await state.update_data(plan_days=days)
    await state.set_state(MasterBooking.waiting_for_slip)
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@master_router.message(MasterBooking.waiting_for_slip, F.photo)
async def receive_master_slip(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    days = data.get("plan_days")
    photo_id = message.photo[-1].file_id
    
    await message.answer("⏳ Receipt received. Platform Admin မှ အတည်ပြုပြီးပါက သက်တမ်း အလိုအလျောက် တိုးသွားပါမည်။")
    await state.clear()
    
    # Super Admin များထံသို့ ပြေစာလှမ်းပို့မည်
    plan_names = {30: "၁ လ", 90: "၃ လ", 180: "၆ လ", 0: "Lifetime"}
    admin_text = (
        f"💰 **လုပ်ငန်းရှင်ထံမှ သက်တမ်းတိုး ပြေစာ ရောက်ရှိလာပါသည်!**\n\n"
        f"👤 **လုပ်ငန်းရှင်:** {message.from_user.full_name} (@{message.from_user.username})\n"
        f"🆔 **ID:** `{message.from_user.id}`\n"
        f"📦 **Plan:** {plan_names[days]}\n"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Approve", callback_data=f"master_approve_{message.from_user.id}_{days}")],
        [InlineKeyboardButton(text="❌ Reject", callback_data=f"master_reject_{message.from_user.id}")]
    ])
    
    for admin_id in SUPER_ADMINS:
        try:
            await bot.send_photo(chat_id=admin_id, photo=photo_id, caption=admin_text, reply_markup=kb, parse_mode="Markdown")
        except: pass

# --- Super Admin မှ Approve / Reject ပြုလုပ်ခြင်း ---
@master_router.callback_query(F.data.startswith("master_approve_"))
async def approve_business_sub(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id not in SUPER_ADMINS: return
    
    parts = callback.data.split("_")
    owner_id = int(parts[2])
    days = int(parts[3])
    
    biz = await db.businesses.find_one({"owner_id": owner_id})
    if not biz:
        return await callback.answer("ဤလုပ်ငန်းရှင် ရှာမတွေ့ပါ။", show_alert=True)
        
    now = datetime.utcnow()
    current_exp = biz.get("expires_at")
    
    if days == 0:
        new_exp = None # Lifetime
    else:
        if current_exp and current_exp > now:
            new_exp = current_exp + timedelta(days=days) # ရှိရင်းစွဲသက်တမ်းပေါ် ထပ်ပေါင်းမည်
        else:
            new_exp = now + timedelta(days=days) # သက်တမ်းကုန်နေပါက ယနေ့မှစ၍ ပေါင်းမည်
            
    await db.businesses.update_one(
        {"owner_id": owner_id},
        {"$set": {
            "expires_at": new_exp, 
            "status": "active",
            "notified_7": False, "notified_3": False, "notified_1": False # သတိပေးချက်များကို Reset ချမည်
        }}
    )
    
    # လုပ်ငန်းရှင်ထံ အကြောင်းကြားမည်
    try:
        await bot.send_message(owner_id, "✅ Congratulations. Your Bot renewal was successful!\n\nစနစ်အား ပုံမှန်အတိုင်း ပြန်လည်အသုံးပြုနိုင်ပါပြီ။", parse_mode="Markdown")
    except: pass
    
    await callback.message.edit_caption(caption=callback.message.caption + "\n\n🟢 APPROVED", reply_markup=None)
    await callback.answer("သက်တမ်းတိုးပေးလိုက်ပါပြီ။")

@master_router.callback_query(F.data.startswith("master_reject_"))
async def reject_business_sub(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id not in SUPER_ADMINS: return
    owner_id = int(callback.data.split("_")[2])
    
    try:
        await bot.send_message(owner_id, "❌ Your payment receipt could not be verified!\n\nPlease double-check the authenticity of the receipt and resubmit.(ပြေစာမှားယွင်းနေသည်)", parse_mode="Markdown")
    except: pass
    
    await callback.message.edit_caption(caption=callback.message.caption + "\n\n🔴 REJECTED", reply_markup=None)

# ==========================================
# 🔄 Subscription Mode သို့ ကူးပြောင်းခြင်း
# ==========================================
@master_router.callback_query(F.data == "trigger_sub_transition")
async def trigger_subscription_transition(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id not in SUPER_ADMINS: return
    
    # System ကို Subscription Mode သို့ ပြောင်းကြောင်း DB တွင် မှတ်သားမည်
    await db.system_config.update_one(
        {"_id": "master_config"}, 
        {"$set": {"subscription_mode": True}}, 
        upsert=True
    )
    
    # expires_at မရှိသော (Free) အသုံးပြုနေသူများကို ရှာမည်
    free_biz = await db.businesses.find({"expires_at": None, "status": "active"}).to_list(length=1000)
    
    if not free_biz:
        return await callback.answer("⚠️ အခမဲ့ (Lifetime) အသုံးပြုနေသော လုပ်ငန်းရှင် မရှိပါ။ (သို့မဟုတ်) ပြောင်းလဲပြီးသား ဖြစ်နေပါသည်။", show_alert=True)
        
    await callback.message.edit_text("⏳ စနစ်ကို Subscription သို့ ပြောင်းလဲနေပါသည်...\nလုပ်ငန်းရှင်များထံ အသိပေးစာများ ပို့နေသဖြင့် ခေတ္တစောင့်ဆိုင်းပါ။")
    
    now = datetime.utcnow()
    new_exp = now + timedelta(days=30)
    count = 0
    
    for biz in free_biz:
        owner_id = biz.get("owner_id")
        
        # Database တွင် (၁) လ သက်တမ်း အသစ် သတ်မှတ်ခြင်း
        await db.businesses.update_one(
            {"_id": biz["_id"]},
            {"$set": {"expires_at": new_exp, "notified_7": False, "notified_3": False, "notified_1": False}}
        )
        count += 1
        
        # လုပ်ငန်းရှင်တိုင်းထံသို့ Broadcast ပို့ခြင်း
        msg_text = (
            "📢 အရေးကြီး ကြေညာချက် Subscription စနစ်သို့ ပြောင်းလဲခြင်း\n\n"
            "ကျွန်ုပ်တို့၏ Bot Myanmar ကို ယုံကြည်စွာ အသုံးပြုပေးခဲ့ကြတဲ့ လုပ်ငန်းရှင် Customer များကျေးဇူးတင်ပါတယ်။ စနစ်တကျ ရေရှည်ဝန်ဆောင်မှုပေးနိုင်ရန်အတွက် ယနေ့မှစ၍ Subscription စနစ်သို့ ပြောင်းလဲလိုက်ပြီဖြစ်ကြောင်း အသိပေးအပ်ပါတယ်ခင်ဗျာ..\n\n"
            "🎁 လက်ရှိအသုံးပြုသူများအား ကျေးဇူးတုံ့ပြန်သောအားဖြင့် ယနေ့မှစ၍ နောက်ထပ် (၁) လတိတိ (ရက် ၃၀) ဆက်လက်၍ အခမဲ့ အသုံးပြုခွင့် ပေးထားပါသည်။\n\n"
            "သက်တမ်းတိုးရန် @forsubscriptionbot တွင် /start နှိပ်၍ Plan များကို ရွေးချယ်၍ ငွေပေးချေနိုင်ပါသည်။"
        )
        try:
            await bot.send_message(owner_id, msg_text, parse_mode="Markdown")
            await asyncio.sleep(0.05) # Flood Wait မဖြစ်စေရန် ထိန်းထားခြင်း
        except: pass
        
    success_text = (
        f"✅ **Subscription စနစ်သို့ အောင်မြင်စွာ ကူးပြောင်းပြီးပါပြီ!**\n\n"
        f"လုပ်ငန်းရှင်ပေါင်း **({count})** ဦးကို ရက် ၃၀ သက်တမ်း ပြောင်းလဲသတ်မှတ်ပြီး၊ အသိပေးစာ (Broadcast) များ အလိုအလျောက် ပို့ဆောင်ပြီးပါပြီ။\n\n"
        f"*(မှတ်ချက် - ယခုမှစ၍ Bot အသစ်လာချိတ်သော လုပ်ငန်းရှင်များကိုလည်း အလိုအလျောက် (၁) လ သက်တမ်းသာ သတ်မှတ်ပေးတော့မည် ဖြစ်ပါသည်။)*"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="show_stats")]])
    await callback.message.edit_text(success_text, reply_markup=kb, parse_mode="Markdown")

# ==========================================
# 🛑 Subscription Mode အား ပိတ်၍ Free Mode သို့ ပြန်ပြောင်းခြင်း
# ==========================================
@master_router.callback_query(F.data == "disable_sub_mode")
async def disable_subscription_transition(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id not in SUPER_ADMINS: return
    
    # System ကို Free Mode သို့ ပြန်ပြောင်းကြောင်း DB တွင် မှတ်သားမည်
    await db.system_config.update_one(
        {"_id": "master_config"}, 
        {"$set": {"subscription_mode": False}}, 
        upsert=True
    )
    
    # လက်ရှိ active ဖြစ်နေသော (ငွေပေးသွင်းရမည့်) လုပ်ငန်းရှင်များကို ရှာမည်
    active_biz = await db.businesses.find({"status": "active", "expires_at": {"$ne": None}}).to_list(length=1000)
    
    await callback.message.edit_text("⏳ စနစ်ကို Free Mode သို့ ပြန်လည်ပြောင်းလဲနေပါသည်...\nလုပ်ငန်းရှင်များထံ အသိပေးစာများ ပို့နေသဖြင့် ခေတ္တစောင့်ဆိုင်းပါ။")
    
    count = 0
    for biz in active_biz:
        owner_id = biz.get("owner_id")
        
        # Database တွင် Lifetime (None) သို့ ပြန်လည်ပြောင်းလဲသတ်မှတ်ခြင်း
        await db.businesses.update_one(
            {"_id": biz["_id"]},
            {"$set": {"expires_at": None}}
        )
        count += 1
        
        # လုပ်ငန်းရှင်တိုင်းထံသို့ သတင်းကောင်း Broadcast ပို့ခြင်း
        msg_text = (
            "🎉ဝမ်းမြောက်ဖွယ်ရာ အသိပေးချက် Free Mode သို့ ပြောင်းလဲခြင်း\n\n"
            "ကျွန်ုပ်တို့၏ စနစ်ကို Promotion အနေဖြင့် ယခုမှစ၍ အခမဲ့အဖြစ် ပြန်လည်အသုံးပြုခွင့် ပေးလိုက်ပါသည်။\n\n"
            "Promotion ကာလ အကန့်အသတ်မရှိသေးပါ။ Promotion ကာလကုန်ဆုံးပါက ပြန်လည်အကြောင်းကြားပေးပါမည်။"
        )
        try:
            await bot.send_message(owner_id, msg_text, parse_mode="Markdown")
            await asyncio.sleep(0.05) # Flood Wait မဖြစ်စေရန် ထိန်းထားခြင်း
        except: pass
        
    success_text = (
        f"✅ **Free Mode သို့ အောင်မြင်စွာ ပြန်လည်ကူးပြောင်းပြီးပါပြီ!**\n\n"
        f"လုပ်ငန်းရှင်ပေါင်း **({count})** ဦးကို Lifetime သက်တမ်း ပြန်လည်သတ်မှတ်ပေးပြီး၊ သတင်းကောင်း အသိပေးစာ (Broadcast) များ အလိုအလျောက် ပို့ဆောင်ပြီးပါပြီ။"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="show_stats")]])
    await callback.message.edit_text(success_text, reply_markup=kb, parse_mode="Markdown")

# ==========================================
# 📥 Manual Channel Content Backup (Super Admin Only)
# ==========================================
@master_router.message(Command("backup"))
async def run_backup_cmd(message: Message, bot: Bot):
    if message.from_user.id not in SUPER_ADMINS: return

    # Command Format စစ်ဆေးခြင်း: /backup [source_id] [target_id] [start_id] [end_id]
    args = message.text.split()
    if len(args) != 5:
        text = "❌ Format မှားယွင်းနေပါသည်။\nအသုံးပြုရန်: `/backup -100123... -100456... 1 500`"
        return await message.answer(text, parse_mode="Markdown")
    
    source_id = args[1].strip()
    target_id = args[2].strip()
    
    try:
        start_id = int(args[3])
        end_id = int(args[4])
    except ValueError:
        return await message.answer("❌ Message ID များသည် ဂဏန်းများသာ ဖြစ်ရပါမည်။")

    if start_id > end_id:
        return await message.answer("❌ start_msg_id သည် end_msg_id ထက် ငယ်ရပါမည်။")

    # Source Channel နှင့် ချိတ်ဆက်ထားသော Client Bot ကို Database တွင် ရှာဖွေခြင်း
    service = await db.services.find_one({"link": {"$regex": source_id}})
    if not service:
        return await message.answer("❌ Database ထဲတွင် ထို Source Channel ID နှင့် ချိတ်ဆက်ထားသော လုပ်ငန်းရှင်၏ Bot ကို ရှာမတွေ့ပါ။")

    client_token = service['bot_token']
    
    msg_text = (
        f"⏳ **Backup စတင်နေပါပြီ...**\n\n"
        f"📥 Source: `{source_id}`\n"
        f"📤 Target: `{target_id}`\n"
        f"🔢 Messages: `{start_id}` to `{end_id}`\n\n"
        f"(ဤလုပ်ငန်းစဉ်သည် Background တွင် အလုပ်လုပ်နေမည်ဖြစ်ပြီး Client Bot များကို လေးလံသွားစေမည် မဟုတ်ပါ။ ပြီးစီးပါက အကြောင်းကြားပေးပါမည်။)"
    )
    await message.answer(msg_text, parse_mode="Markdown")

    # နောက်ကွယ် (Background) တွင် အလုပ်လုပ်စေရန် Task အသစ်ခွဲ၍ Run ခြင်း
    asyncio.create_task(
        perform_background_backup(
            master_bot=bot,
            admin_id=message.from_user.id,
            client_token=client_token,
            source_id=source_id,
            target_id=target_id,
            start_id=start_id,
            end_id=end_id
        )
    )

# 🔄 Background တွင် အလုပ်လုပ်မည့် Function
async def perform_background_backup(master_bot: Bot, admin_id: int, client_token: str, source_id: str, target_id: str, start_id: int, end_id: int):
    client_bot = Bot(token=client_token)
    success_count = 0
    fail_count = 0
    
    for msg_id in range(start_id, end_id + 1):
        try:
            await client_bot.copy_message(
                chat_id=target_id,
                from_chat_id=source_id,
                message_id=msg_id
            )
            success_count += 1
        except Exception as e:
            # စာဖျက်သွားခြင်း သို့မဟုတ် Target Channel တွင် ပို့ခွင့်မရှိခြင်းတို့ကြောင့် ဖြစ်နိုင်သည်
            fail_count += 1
        
        # 💥 အရေးကြီးဆုံး: Telegram Rate Limit မမိစေရန်နှင့် Server မလေးစေရန် ၂ စက္ကန့် စောင့်မည်
        await asyncio.sleep(2.0) 

    await client_bot.session.close()

    # Super Admin ထံသို့ ပြီးစီးကြောင်း အစီရင်ခံစာ ပြန်ပို့မည်
    report = (
        f"✅ **Backup လုပ်ငန်းစဉ် ပြီးဆုံးပါပြီ!**\n\n"
        f"📥 Source: `{source_id}`\n"
        f"📤 Target: `{target_id}`\n"
        f"✔️ အောင်မြင်: **{success_count}** posts\n"
        f"❌ မအောင်မြင်: **{fail_count}** posts (ဖျက်ထားသောစာများ/ ID ကျော်သွားခြင်းများ)"
    )
    try:
        await master_bot.send_message(chat_id=admin_id, text=report, parse_mode="Markdown")
    except:
        pass


# ==========================================
# 📢 Super Admin Broadcast System (လုပ်ငန်းရှင်များထံ အသိပေးစာပို့ခြင်း)
# ==========================================
@master_router.callback_query(F.data == "master_broadcast")
async def master_broadcast_btn(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in SUPER_ADMINS: return
    
    text = (
        "📢 **လုပ်ငန်းရှင်များထံ Broadcast ပို့ရန်**\n\n"
        "စနစ်ကို အသုံးပြုနေသော လုပ်ငန်းရှင်အားလုံးထံသို့ ပေးပို့လိုသော စာသား၊ ပုံ၊ ဗီဒီယို (သို့) မည်သည့် Media ကိုမဆို ယခု ပေးပို့ပါ။"
    )
    await callback.message.answer(text, parse_mode="Markdown")
    await state.set_state(MasterBroadcast.waiting_for_msg)
    await callback.answer()

@master_router.message(MasterBroadcast.waiting_for_msg)
async def process_master_broadcast(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    await message.answer("⏳ **Broadcast စတင်ပို့ဆောင်နေပါသည်...**\n(ဤလုပ်ငန်းစဉ်သည် Background တွင် အလုပ်လုပ်နေမည်ဖြစ်ပြီး ပြီးဆုံးပါက အကြောင်းကြားပေးပါမည်။)")
    
    # 💥 Bot မလေးစေရန် Task အသစ်ခွဲ၍ Background တွင် Run မည်
    asyncio.create_task(
        run_master_broadcast(
            bot=bot, 
            from_chat_id=message.chat.id, 
            message_id=message.message_id, 
            admin_id=message.from_user.id
        )
    )

# 🔄 Background တွင် အလုပ်လုပ်မည့် Function
async def run_master_broadcast(bot: Bot, from_chat_id: int, message_id: int, admin_id: int):
    # Database မှ လုပ်ငန်းရှင်များ၏ ID အားလုံးကို ထုတ်ယူမည် (ID ထပ်နေတာတွေ မပါအောင် distinct သုံးမည်)
    owner_ids = await db.businesses.distinct("owner_id")
    
    success_count = 0
    fail_count = 0
    
    for owner_id in owner_ids:
        try:
            # 💥 copy_message သုံးခြင်းဖြင့် Media (ပုံ၊ ဗီဒီယို၊ ဖိုင်) အစုံအလင်ကို Forward tag မပါဘဲ ပို့နိုင်သည်
            await bot.copy_message(
                chat_id=owner_id,
                from_chat_id=from_chat_id,
                message_id=message_id
            )
            success_count += 1
        except Exception:
            # User မှ Bot ကို Block ထားခြင်း (သို့) အကောင့် ဖျက်သွားခြင်းတို့ကြောင့် Fail ဖြစ်နိုင်သည်
            fail_count += 1
        
        # 💥 Telegram Flood Wait မဖြစ်စေရန် 0.05 စက္ကန့် စောင့်မည် (တစ်စက္ကန့်လျှင် အများဆုံး အစောင် ၂၀ နှုန်းဖြင့် လုံခြုံစွာ ပို့မည်)
        await asyncio.sleep(0.05)
        
    # ပို့ဆောင်ပြီးစီးကြောင်း Super Admin ထံသို့ အစီရင်ခံစာ ပြန်ပို့မည်
    report = (
        f"✅ **Broadcast ပို့ဆောင်ခြင်း ပြီးဆုံးပါပြီ!**\n\n"
        f"📊 **အကျဉ်းချုပ် အခြေအနေ:**\n"
        f"✔️ အောင်မြင်စွာ ရရှိသူ: **{success_count}** ဦး\n"
        f"❌ မအောင်မြင်သူ (Bot ကို Block ထားသူများ): **{fail_count}** ဦး"
    )
    try:
        await bot.send_message(chat_id=admin_id, text=report, parse_mode="Markdown")
    except:
        pass
