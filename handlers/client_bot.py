from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ChatJoinRequest
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from bson.objectid import ObjectId
from core.database import db
from handlers.client_admin import admin_kb
from utils.states import UserBooking
from datetime import datetime
import random
import string

client_router = Router()

@client_router.message(CommandStart())
async def client_start_cmd(message: Message, bot: Bot, state: FSMContext, command: CommandObject): # 💥 command ထပ်ထည့်ပါ
    await state.clear() 
    
    business = await db.businesses.find_one({"bot_token": bot.token})
    if not business: return

    # Super Admin မှ ယာယီရပ်ဆိုင်းထားခြင်း ရှိ/မရှိ စစ်ဆေးခြင်း
    if business.get("status") == "suspended":
        return await message.answer("🚫 This Bot has been temporarily suspended by the Platform.\n\nFor more information, please contact the Platform Admin.")

    # ==========================================
    # 📥 File Deep Link ဖြင့် ဝင်လာခြင်း ဟုတ်/မဟုတ် စစ်ဆေးခြင်း
    # ==========================================
    args = command.args
    if args and args.startswith("file_"):
        file_code = args.split("_")[1]
        
        # Force Sub စစ်ဆေးခြင်း
        f_id = business.get("force_sub_id")
        f_link = business.get("force_sub_link")
        
        if f_id and f_link:
            try:
                member = await bot.get_chat_member(chat_id=f_id, user_id=message.from_user.id)
                status_val = member.status.value if hasattr(member.status, "value") else str(member.status)
                
                if status_val in ["left", "kicked", "restricted"]:
                    # Join မလုပ်ရသေးလျှင် Join ခိုင်းမည်
                    kb = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🚀 Join Channel First", url=f_link)],
                        [InlineKeyboardButton(text="✅ Check & Get File", url=f"https://t.me/{(await bot.get_me()).username}?start=file_{file_code}")]
                    ])
                    return await message.answer("⚠️ <b>ဖိုင်ကို ရယူရန် အောက်ပါ Channel ကို အရင် Join ပေးပါ။</b> Join ပြီးပါက အောက်က Check ခလုတ်ကို ပြန်နှိပ်ပါ။", reply_markup=kb, parse_mode="HTML")
            except Exception as e:
                pass # Bot ကို Channel တွင် Admin မပေးထားလျှင် (သို့) ID မှားနေလျှင် အလိုအလျောက် ကျော်သွားမည်
        
        # File ကို Database မှ ရှာဖွေပြီး ပေးပို့ခြင်း
        file_data = await db.files.find_one({"bot_token": bot.token, "code": file_code})
        if not file_data:
            return await message.answer("❌ ဤဖိုင်မှာ ဖျက်သိမ်းခံလိုက်ရပါပြီ (သို့မဟုတ်) လင့်ခ်မှားယွင်းနေပါသည်။")
            
        f_type = file_data["type"]
        f_id_to_send = file_data["file_id"]
        f_caption = file_data.get("caption")
        
        try:
            if f_type == "document": await message.answer_document(document=f_id_to_send)
            elif f_type == "video": await message.answer_video(video=f_id_to_send)
            elif f_type == "photo": await message.answer_photo(photo=f_id_to_send)
            elif f_type == "audio": await message.answer_audio(audio=f_id_to_send)
            return
        except Exception:
            return await message.answer("❌ ဖိုင်ပေးပို့ရာတွင် အမှားအယွင်းဖြစ်ပေါ်ခဲ့ပါသည်။")

    # ==========================================
    owner_id = business.get("owner_id")
    sub_admins = business.get("sub_admins", [])
    
    user_id = message.from_user.id
    is_owner = (user_id == owner_id)
    is_sub_admin = (user_id in sub_admins)

    # (၁) လ သက်တမ်း ကုန်/မကုန် စစ်ဆေးခြင်း
    expires_at = business.get("expires_at")
    if expires_at and datetime.utcnow() > expires_at:
        # သက်တမ်းကုန်နေလျှင်
        if is_owner or is_sub_admin:
            await message.answer("⚠️ Your (1) month (Free Trial) Bot usage period has expired.\n\nIf you wish to continue using it, please contact the System Admin to renew it. @botdistribution")
        else:
            await message.answer("⚠️ This Bot is currently temporarily down.")
        return 

    # ပိုင်ရှင် (သို့) Admin အကူ ဖြစ်နေလျှင် Admin Panel ကို ပြမည်
    if is_owner or is_sub_admin:
        text = "Welcome to Business Admin Panel.\n\nSelect the required action from the buttons below."
        await message.answer(text, reply_markup=admin_kb(is_owner=is_owner), parse_mode="Markdown")
        
    else:
        # လက်ရှိ User မှာ Active ဖြစ်နေသော ဝန်ဆောင်မှု ရှိ/မရှိ စစ်ဆေးခြင်း
        active_subs = await db.subscriptions.find({"bot_token": bot.token, "user_id": message.from_user.id, "status": "active"}).to_list(length=10)
        
        cursor = db.services.find({"bot_token": bot.token, "status": "active"})
        services = await cursor.to_list(length=100)
        
        # 💥 NEW: Database မှ Custom Welcome Message ကို ဆွဲထုတ်ခြင်း (မရှိပါက Default စာသားပြမည်)
        welcome_msg = business.get("welcome_msg", "Welcome to our VIP service.")
        text = f"{welcome_msg}\n\n"
        
        keyboard = []
        
        if services:
            text += "Select the service you want to purchase from the buttons below.\n"
            for s in services:
                keyboard.append([InlineKeyboardButton(text=f" {s['name']} - {s['price']} MMK", callback_data=f"buy_{s['_id']}")])
        else:
            text += "There are currently no services available for purchase.\n"
            
        if active_subs:
            keyboard.append([InlineKeyboardButton(text="🔑 Backup Key (အကောင့်ပျက်လျှင် ပြန်ယူရန်)", callback_data="get_backup_key")])
        else:
            keyboard.append([InlineKeyboardButton(text="🔄 (Recover Old Account)", callback_data="recover_account")])
            
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await message.answer(text, reply_markup=reply_markup, parse_mode="Markdown")

# Customer က Service တစ်ခုခုကို ဝယ်ယူရန် နှိပ်လိုက်သောအခါ
@client_router.callback_query(F.data.startswith("buy_"))
async def buy_service_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
    service_id_str = callback.data.split("_")[1]
    
    service = await db.services.find_one({"_id": ObjectId(service_id_str)})
    business = await db.businesses.find_one({"bot_token": bot.token})
    
    if not service or not business:
        await callback.answer("❌Service not found.", show_alert=True)
        return
        
    payment_info = business.get("payment_info", "No payment information yet.")
    
    duration_val = service.get("duration", 0)
    duration_text = "Lifetime" if duration_val == 0 else f"{duration_val} Days"
    service_note = service.get("note", "Not yet") # 💥 Note အား ဆွဲထုတ်ခြင်း
    
    # 💥 ပြင်ဆင်ထားသော HTML ကုဒ်
    text = (
        f"💳 <b>'{service['name']}' ကို ဝယ်ယူရန် ငွေလွှဲရမည့် အချက်အလက်</b>\n\n"
        f"{payment_info}\n\n"
        f"💵 <b>Price :</b> {service['price']} MMK\n"
        f"⏳ <b>Duration :</b> {duration_text}\n"
        f"📝 <b>Note :</b> {service_note}\n\n"
        "⚠️ <b>Important :</b> ငွေလွှဲပြီးပါက ငွေလွှဲပြေစာ (Slip Screenshot) ကို ဤနေရာသို့ ဓာတ်ပုံ ပို့ပေးပါ။"
    )
    
    # 💥 parse_mode="HTML" ပြောင်းသည်
    await callback.message.answer(text, parse_mode="HTML")
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
        await message.answer("❌ There is a system error. Please press /start again.")
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
    await message.answer("⏳ Your payment receipt has been received. Please wait for the admin to verify. Once approved, the Group Link will be sent automatically.\n\n(‌ငွေလွှဲပြေစာလက်ခံရရှိပါသည်။ အတည်ပြုချိန်စောင့်ဆိုင်းပေးပါ။)")
    await state.clear()
    
    # ทำการ ပိုင်ရှင် (Owner) ဆီသို့ Slip ပုံနှင့် Approve/Reject ခလုတ် လှမ်းပို့မည်
    owner_id = business.get("owner_id")
    photo_id = message.photo[-1].file_id # အကြည်ဆုံးပုံကို ယူမည်
    
    # 💥 ပြင်ဆင်ထားသော HTML ကုဒ်
    admin_text = (
        f"💰 <b>New Payment Received!</b>\n\n"
        f"👤 <b>Customer :</b> {message.from_user.full_name} (@{message.from_user.username})\n"
        f"📦 <b>Service :</b> {service['name']}\n"
        f"💵 <b>Price :</b> {service['price']} MMK\n"
    )
    
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Approve", callback_data=f"sub_approve_{sub_id}"),
            InlineKeyboardButton(text="❌ Reject", callback_data=f"sub_reject_{sub_id}")
        ]
    ])
    
    try:
        # 💥 parse_mode="HTML" ပြောင်းသည်
        await bot.send_photo(chat_id=owner_id, photo=photo_id, caption=admin_text, reply_markup=admin_keyboard, parse_mode="HTML")
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
            await bot.send_message(user_id, "✅ Group/Channel Approved!")
        except:
            pass
    else:
        await update.decline() # မသက်ဆိုင်သူ ဖြစ်၍ အလိုအလျောက် ပယ်ချမည်
        try:
            await bot.send_message(user_id, "❌ Access has been denied because you do not have an active subscription.")
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

# ==========================================
# 💥 NEW: Account Recovery (အကောင့်ဟောင်း ပြန်ယူခြင်း စနစ်)
# ==========================================
@client_router.callback_query(F.data == "get_backup_key")
async def get_backup_key(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    
    # Active ဖြစ်နေသော စာရင်းတစ်ခုကို ရှာမည်
    sub = await db.subscriptions.find_one({"bot_token": bot.token, "user_id": user_id, "status": "active"})
    if not sub:
        await callback.answer("Active ဝန်ဆောင်မှု မရှိပါ။", show_alert=True)
        return

    backup_key = sub.get("backup_key")
    # Key မရှိသေးပါက အသစ်ထုတ်ပေးမည် (ဥပမာ - BKP-A1B2C3)
    if not backup_key:
        random_str = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        backup_key = f"BKP-{random_str}"
        
        # User ၏ Active ဖြစ်နေသော စာရင်းအားလုံးတွင် ဤ Key ကို မှတ်သားမည်
        await db.subscriptions.update_many(
            {"bot_token": bot.token, "user_id": user_id, "status": "active"},
            {"$set": {"backup_key": backup_key}}
        )

    text = (
        f"🔑 Your Backup Key - `{backup_key}`\n\n"
        "⚠️ ဤ Key အား Copy ကူး၍ လုံခြုံသောနေရာတွင် သေချာစွာ မှတ်သားထားပါ။ သင့်အကောင့် ပျက်သွားပါက အကောင့်သစ်မှတစ်ဆင့် ဤ Key ကိုအသုံးပြု၍ သင်၏ ဝန်ဆောင်မှုများကို ပြန်လည်ရယူနိုင်ပါသည်။"
    )
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()


@client_router.callback_query(F.data == "recover_account")
async def ask_recover_key(callback: CallbackQuery, state: FSMContext):
    text = "🔄 Recover Old Account \n\nလူကြီးမင်း၏ ယခင်အကောင့်မှ ရယူထားသော `Backup Key` ကို ရိုက်ထည့်ပါ။"
    await callback.message.answer(text)
    await state.set_state(UserBooking.waiting_for_recovery_key)
    await callback.answer()


@client_router.message(UserBooking.waiting_for_recovery_key)
async def process_recovery_key(message: Message, state: FSMContext, bot: Bot):
    input_key = message.text.strip()
    
    # Database ထဲတွင် ထို Key ဖြင့် Active ဖြစ်နေသော စာရင်းများကို ရှာမည်
    cursor = db.subscriptions.find({"bot_token": bot.token, "backup_key": input_key, "status": "active"})
    subs = await cursor.to_list(length=100)

    if not subs:
        await message.answer("❌ The key is incorrect or has expired.\n\nPress /start to try again.")
        await state.clear()
        return

    # လုံခြုံရေးအရ Key အသစ်တစ်ခု ချက်ချင်းပြောင်းပေးမည် (တစ်ခြားသူ ပြန်ခိုးသုံး၍ မရစေရန်)
    new_random_str = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    new_backup_key = f"BKP-{new_random_str}"
    
    keyboard = [] # 💥 NEW: Group ဝင်ရန် ခလုတ်များ စုဆောင်းရန်

    for sub in subs:
        old_user_id = sub["user_id"]
        service_id = sub["service_id"]

        service = await db.services.find_one({"_id": ObjectId(service_id)})
        if service:
            chat_id = service.get("link")
            if chat_id and (chat_id.startswith("-100") or chat_id.startswith("@")):
                # (၁) အကောင့်ဟောင်းအား အလိုအလျောက် ကန်ထုတ်ခြင်း
                try:
                    await bot.ban_chat_member(chat_id=chat_id, user_id=old_user_id)
                    await bot.unban_chat_member(chat_id=chat_id, user_id=old_user_id)
                except Exception as e:
                    print(f"Failed to kick old user {old_user_id}: {e}")
                
                # 💥 (၂) NEW: အကောင့်သစ်အတွက် ဝင်ခွင့် Link အသစ် ချက်ချင်း ထုတ်ပေးခြင်း
                try:
                    link_obj = await bot.create_chat_invite_link(
                        chat_id=chat_id, 
                        creates_join_request=True, 
                        name=f"Recovered ID: {message.from_user.id}"
                    )
                    keyboard.append([InlineKeyboardButton(text=f"🚀 Join {service['name']}", url=link_obj.invite_link)])
                except Exception as e:
                    print(f"Error creating recovery link: {e}")
            else:
                # Group ID မဟုတ်ဘဲ ရိုးရိုး Link အသေ ဖြစ်နေပါက
                if chat_id:
                    keyboard.append([InlineKeyboardButton(text=f"🚀 Join {service['name']}", url=chat_id)])

        # ထို့နောက် Database တွင် အကောင့်သစ်၏ အချက်အလက်များဖြင့် အစားထိုး Update လုပ်မည်
        await db.subscriptions.update_one(
            {"_id": sub["_id"]},
            {"$set": {
                "user_id": message.from_user.id,
                "username": message.from_user.username,
                "full_name": message.from_user.full_name,
                "backup_key": new_backup_key
            }}
        )

    success_text = (
        "✅ Recover Old Account Success!\n\n"
        "ယခင်အကောင့်ရှိ ဝန်ဆောင်မှုများကို ဤအကောင့်သစ်သို့ အောင်မြင်စွာ လွှဲပြောင်းပေးလိုက်ပါပြီ။ \n\n"
        "👇 Join Your Group / Channel"
    )
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None
    
    await message.answer(success_text, reply_markup=reply_markup, parse_mode="Markdown")
    await state.clear()

# ==========================================
# 💥 NEW: Admin Invite Code ဖြင့် Sub-Admin အဖြစ် ဝင်ရောက်ခြင်း
# ==========================================
@client_router.message(F.text.startswith("ADMIN-"))
async def claim_sub_admin(message: Message, bot: Bot):
    input_code = message.text.strip()
    
    business = await db.businesses.find_one({"bot_token": bot.token})
    if not business:
        return
        
    invite_code = business.get("admin_invite_code")
    
    # Code မှန်ကန်ပြီး အသုံးပြုခွင့်ရှိနေလျှင်
    if invite_code and input_code == invite_code:
        user_id = message.from_user.id
        
        # Sub Admin စာရင်းထဲသို့ ၎င်း၏ ID ကို ထည့်သွင်းမည် (ထပ်နေပါက နှစ်ခါမထည့်ရန် $addToSet)
        # ထို့နောက် တစ်ခါသုံး Code ဖြစ်၍ admin_invite_code ကို ဖျက်ပစ်မည်
        await db.businesses.update_one(
            {"bot_token": bot.token},
            {
                "$addToSet": {"sub_admins": user_id},
                "$unset": {"admin_invite_code": ""}
            }
        )
        
        await message.answer("🎉 Congratulations!. You have been successfully added as a Sub-Admin of this Bot.\n\nClick /start to get started.", parse_mode="Markdown")
    else:
        await message.answer("❌ The invitation code is incorrect or has already been used!")
