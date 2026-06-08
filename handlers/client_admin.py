from datetime import datetime, timedelta
from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from bson.objectid import ObjectId
from core.database import db
from utils.states import AdminSetup, AdminBroadcast, EditService
import asyncio
import random

client_admin_router = Router()

# ==========================================
# 🛠 1. Admin Menu Keyboard
# ==========================================
def admin_kb(is_owner=False):
    kb = [
        [InlineKeyboardButton(text="📝 Create Welcome Message", callback_data="set_welcome_msg")],
        [InlineKeyboardButton(text="💳 Add Payment Info", callback_data="set_payment")],
        [InlineKeyboardButton(text="➕ Add Service/ Plan", callback_data="add_service")],
        [InlineKeyboardButton(text="⚙️ Edit / Delete Service/ Plan", callback_data="manage_services")],
        [InlineKeyboardButton(text="📢 Broadcast to Customers", callback_data="broadcast_msg")]
    ]
    # ပိုင်ရှင် (Owner) ဖြစ်မှသာ Sub-Admin ခလုတ်ကို ပြမည်
    if is_owner:
        kb.append([InlineKeyboardButton(text="👥 Manage Sub-Admin", callback_data="manage_sub_admins")])
        
    return InlineKeyboardMarkup(inline_keyboard=kb)

# ==========================================
# 💳 2. Payment Info Setup (ငွေပေးချေမှု အချက်အလက်)
# ==========================================
@client_admin_router.callback_query(F.data == "set_payment")
async def set_payment_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
    # လုံခြုံရေး - ပိုင်ရှင် ဟုတ်/မဟုတ် စစ်ဆေးခြင်း
    business = await db.businesses.find_one({"bot_token": bot.token})
    owner_id = business.get("owner_id")
    sub_admins = business.get("sub_admins", [])
    if callback.from_user.id != owner_id and callback.from_user.id not in sub_admins:
        return

    text = "💳 Sent Payment Info \n ငွေပေးချေရမည့်အချက်အလက်ထည့်ပါ\n (ဥပမာ- KPay- Ko Ko : 09123456789, Wave- Ko Ko : 09987654321)"
    await callback.message.answer(text)
    await state.set_state(AdminSetup.waiting_for_payment_info)
    await callback.answer()

@client_admin_router.message(AdminSetup.waiting_for_payment_info)
async def receive_payment_info(message: Message, bot: Bot, state: FSMContext):
    await db.businesses.update_one(
        {"bot_token": bot.token}, 
        {"$set": {"payment_info": message.text}}
    )
    await message.answer("✅ Success! Pyament Info Setup")
    await state.clear()

# ==========================================
# ➕ 3. Add New Service (Service အသစ် ဖန်တီးခြင်း)
# ==========================================
@client_admin_router.callback_query(F.data == "add_service")
async def add_service_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
    business = await db.businesses.find_one({"bot_token": bot.token})
    owner_id = business.get("owner_id")
    sub_admins = business.get("sub_admins", [])
    if callback.from_user.id != owner_id and callback.from_user.id not in sub_admins:
        return

    await callback.message.answer("📝 Sent Service/ Plan Name\n သင့်ရဲ့ဝန်ဆောင်မှုနာမည်ရိုက်ထည့်ပါ\n (ဥပမာ- KoKo VIP Group..etc )")
    await state.set_state(AdminSetup.waiting_for_service_name)
    await callback.answer()

@client_admin_router.message(AdminSetup.waiting_for_service_name)
async def receive_service_name(message: Message, state: FSMContext):
    await state.update_data(service_name=message.text)
    await message.answer("💰 Sent Price for this Service/ Plan \n သင့်ဝန်ဆောင်မှု၏ စျေးနှုန်းကို နံပါတ်သီးသန့်ဖြင့်ရိုက်ထည့်ပေးပါ\n(ဥပမာ-  15000)")
    await state.set_state(AdminSetup.waiting_for_service_price)

@client_admin_router.message(AdminSetup.waiting_for_service_price)
async def receive_service_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Please Sent Number Only! (eg. 15000)")
        return
    await state.update_data(service_price=int(message.text))
    await message.answer("⏳ Sent Service/ Plan Duration.\n သင့်ဝန်ဆောင်မှု၏ အချိန်ကာလသတ်မှတ်ပေးပါ။ \n ဥပမာ- တစ်လအတွက် 30 ဟုရိုက်ထည့်ပါ။ တစ်သက်တာအတွက် 0 ဟုရိုက်ထည့်ပါ။")
    await state.set_state(AdminSetup.waiting_for_service_duration)

@client_admin_router.message(AdminSetup.waiting_for_service_duration)
async def receive_service_duration(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Please Sent Number Only! (eg. 1 Month for 30/ 3 month for 90)")
        return
    await state.update_data(service_duration=int(message.text))
    
    # 💥 Link မမေးမီ Note ကို အရင်မေးမည်
    await message.answer("📝 About Your Service/ Plan (Note).\n သင့်ဝန်ဆောင်မှုနှင့်ပတ်၍ အကြောင်းအရာရေးပေးပါ \n (ဥပမာ- Daily Update, Contact info, etc.)")
    await state.set_state(AdminSetup.waiting_for_service_note)

@client_admin_router.message(AdminSetup.waiting_for_service_note)
async def receive_service_note(message: Message, state: FSMContext):
    await state.update_data(service_note=message.text) # Note အား သိမ်းဆည်းခြင်း
    
    text = (
        "🔗 Final Step! Group/ Channel Linking.\n\n"
        "No.1 First add this Bot to your Group or Channel as - Admin -\n"
        "Give full admin permission for all features to work! eg. Ban User, Invite User for Link.. etc..\n\n"
        "No.2 Forward any message from that Group/Channel to this Bot.\n\n"
        "နောက်ဆုံးအဆင့် သင့်ဝန်ဆောင်မှုအား customer များထံအသုံးပြုခွင့်ပေးမည့် Channel/Group များချိတ်ဆက်ခြင်း\n\n"
        "သင့်ရဲ့ bot ကို သတ်မှတ်ထားတဲ့ Vip channel/group ထဲတွင် Admin အဖြစ်ခန့်ထားပေးပါ \n\n"
        "ထို channel/group ထဲမှ postတစ်ခုခုကို သင့် botထံသို့ forward လုပ်ပေးပါ\n\n"
    )
    await message.answer(text, parse_mode="Markdown")
    await state.set_state(AdminSetup.waiting_for_service_link)
    
@client_admin_router.message(AdminSetup.waiting_for_service_link)
async def receive_service_link(message: Message, state: FSMContext, bot: Bot):
    chat_id_str = None
    
    # 💥 NEW: Forward လုပ်လာသော စာဖြစ်လျှင် ID အား အလိုအလျောက် ဆွဲယူမည်
    if message.forward_origin:
        if hasattr(message.forward_origin, 'chat'):
            chat_id_str = str(message.forward_origin.chat.id)
        else:
            return await message.answer("❌ Error! Only forward messages from within a group or channel, not from users.\n သတ်မှတ်ထားတဲ့ group/channel ထဲမှ forward လုပ်ပေးပါ")
            
    # 💥 (သို့မဟုတ်) စာသားတိုက်ရိုက် ရိုက်ထည့်လျှင်
    elif message.text and (message.text.startswith("-100") or message.text.startswith("@")):
        chat_id_str = message.text.strip()
        
    else:
        return await message.answer("❌ Error! Please make sure to forward the message from the Group/Channel.\n သတ်မှတ်ထားတဲ့ group/channel ထဲမှ forward လုပ်ပေးပါ )")

    data = await state.get_data()
    
    # Group/Channel အတွင်း Bot အား Admin ခန့်ထားခြင်း ရှိ/မရှိ အတိအကျ စစ်ဆေးခြင်း
    try:
        target_chat_id = int(chat_id_str) if chat_id_str.lstrip('-').isdigit() else chat_id_str
        
        chat = await bot.get_chat(target_chat_id)
        bot_user = await bot.get_me()
        member = await bot.get_chat_member(chat_id=target_chat_id, user_id=bot_user.id)
        
        status_val = member.status.value if hasattr(member.status, "value") else str(member.status)
        
        if status_val not in ["administrator", "creator"]:
            return await message.answer("❌ Error! Bot has not been added as an Admin in this Group/Channel yet.**\n\nPlease add the Bot as an Admin first before forwarding the message again.\n\n Botအား သတ်မှတ် group/channel တွင် admin ခန့်ထားခြင်းမရှိပါ")
        
        if status_val == "administrator":
            can_invite = getattr(member, "can_invite_users", False)
            
            if chat.type in ["group", "supergroup"]:
                can_restrict = getattr(member, "can_restrict_members", False)
                if not can_invite or not can_restrict:
                    return await message.answer("❌ Error! Incomplete permissions.\n\nWhen you are an Admin in a Group, you need to enable both 'Ban Users' and 'Invite Users via Link' permissions. Please forward again after making the changes.")
                    
            elif chat.type == "channel":
                if not can_invite:
                    return await message.answer("❌ Error! Incomplete permissions.\n\nWhen you are an Admin in a Group, you need to enable both 'Ban Users' and 'Invite Users via Link' permissions. Please forward again after making the changes.")
                    
    except Exception as e:
        err_msg = str(e).lower()
        if "not found" in err_msg:
            return await message.answer("❌ Error! Unable to join the Group/Channel. (Chat Not Found)\n\nThe bot may not have been added as an Admin to the Group/Channel. Please add an Admin and forward the message.")
        else:
            return await message.answer(f"❌ Error! {str(e)}\n\nThe information is incorrect. Please check and try again.")
            
    # အားလုံး မှန်ကန်ပါက DB ထဲသို့ သိမ်းဆည်းခြင်း 
    await db.services.insert_one({
        "bot_token": bot.token,
        "name": data['service_name'],
        "price": data['service_price'],
        "duration": data['service_duration'],
        "note": data.get('service_note', 'Not Yet'), 
        "link": chat_id_str,
        "status": "active"
    })
    
    duration_val = data['service_duration']
    duration_text = "Lifetime" if duration_val == 0 else f"{duration_val} Days"
    
    # 💥 ပြင်ဆင်ထားသော HTML ကုဒ်
    success_text = (
        "✅ <b>Service/ Plan is Successfully Created!</b>\n\n"
        f" <b>Name :</b> {data['service_name']}\n"
        f" <b>Price :</b> {data['service_price']} ကျပ်\n"
        f" <b>Duration :</b> {duration_text}\n"
        f" <b>Note :</b> {data.get('service_note', 'Not Yet')}\n"
        f" <b>Group/Channel ID:</b> <code>{chat_id_str}</code>"
    )
    # 💥 parse_mode="HTML" ပြောင်းသည်
    await message.answer(success_text, parse_mode="HTML")
    await state.clear()
  
# ==========================================
# ✅❌ 4. Slip Approval System (ငွေလွှဲပြေစာ အတည်ပြု/ပယ်ချ)
# ==========================================
@client_admin_router.callback_query(F.data.startswith("sub_approve_"))
async def approve_subscription(callback: CallbackQuery, bot: Bot):
    sub_id = callback.data.split("_")[2]
    
    subscription = await db.subscriptions.find_one({"_id": ObjectId(sub_id)})
    if not subscription or subscription.get("status") != "pending":
        await callback.answer("⚠️ This list is either already taken or no longer exists.", show_alert=True)
        return
        
    service = await db.services.find_one({"_id": ObjectId(subscription["service_id"])})
    if not service:
        await callback.answer("❌ Service not found.", show_alert=True)
        return
        
    # သက်တမ်း တွက်ချက်ခြင်း
    duration = service.get("duration", 0)
    start_date = datetime.utcnow()
    end_date = start_date + timedelta(days=duration) if duration > 0 else None
        
    # Database တွင် Active ပြောင်းမည်
    await db.subscriptions.update_one(
        {"_id": ObjectId(sub_id)},
        {"$set": {"status": "active", "start_date": start_date, "end_date": end_date}}
    )
    
    # Request to Join Link ထုတ်ပေးခြင်း
    chat_id_or_link = service.get("link")
    invite_link = chat_id_or_link
    
    if chat_id_or_link.startswith("-100") or chat_id_or_link.startswith("@"):
        try:
            chat_member_link = await bot.create_chat_invite_link(
                chat_id=chat_id_or_link, 
                creates_join_request=True, 
                name=f"User ID: {subscription['user_id']}"
            )
            invite_link = chat_member_link.invite_link
        except Exception as e:
            print(f"Error creating link: {e}")
            
    # ဝယ်ယူသူထံ အောင်မြင်ကြောင်းနှင့် Link ပို့ပေးခြင်း
    user_id = subscription["user_id"]
    success_msg = (
        f"✅ Your Payment is Successful!\n\n"
        f"📦 Service/ Plan : {service['name']}\n"
        f"⏳ Duration : {'Lifetime' if duration == 0 else f'{duration} Days'}\n\n"
        f"👇 Click the button below to request to join the Group/Channel."
    )
    user_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Join Group / Channel", url=invite_link)]
    ])
    
    try:
        await bot.send_message(chat_id=user_id, text=success_msg, reply_markup=user_kb, parse_mode="Markdown")
    except Exception:
        pass # User က Bot ကို Block ထားလျှင် ကျော်သွားမည်
        
    # လုပ်ငန်းရှင်ထံ ပြန်ပြောင်းလဲပြသခြင်း (ခလုတ်များကို ဖျောက်မည်)
    new_caption = callback.message.caption + "\n\n🟢 Status: APPROVED!"
    await callback.message.edit_caption(caption=new_caption, reply_markup=None)
    await callback.answer("✅ Successfully accepted.")

@client_admin_router.callback_query(F.data.startswith("sub_reject_"))
async def reject_subscription(callback: CallbackQuery, bot: Bot):
    sub_id = callback.data.split("_")[2]
    
    subscription = await db.subscriptions.find_one({"_id": ObjectId(sub_id)})
    if not subscription or subscription.get("status") != "pending":
        await callback.answer("⚠️ This list has already been handled.", show_alert=True)
        return
        
    # Database တွင် Rejected ပြောင်းမည်
    await db.subscriptions.update_one(
        {"_id": ObjectId(sub_id)}, 
        {"$set": {"status": "rejected"}}
    )
    
    # ဝယ်ယူသူထံ ငြင်းပယ်ကြောင်း ပို့ခြင်း
    user_id = subscription["user_id"]
    reject_msg = "❌ The transfer Screenshot you sent could not be validated.\n\nPlease double-check the transfer amount and details, re-select the service, and submit a new slip."
    
    try:
        await bot.send_message(chat_id=user_id, text=reject_msg, parse_mode="Markdown")
    except Exception:
        pass
        
    # လုပ်ငန်းရှင်ထံ ပြန်ပြောင်းလဲပြသခြင်း (ခလုတ်များကို ဖျောက်မည်)
    new_caption = callback.message.caption + "\n\n🔴 Status: REJECTED!"
    await callback.message.edit_caption(caption=new_caption, reply_markup=None)
    await callback.answer("❌ REJECTED!")


# ==========================================
# 📢 5. Broadcast System (လုပ်ငန်းရှင်များအတွက်)
# ==========================================
@client_admin_router.callback_query(F.data == "broadcast_msg")
async def start_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot):
    business = await db.businesses.find_one({"bot_token": bot.token})
    owner_id = business.get("owner_id")
    sub_admins = business.get("sub_admins", [])
    if callback.from_user.id != owner_id and callback.from_user.id not in sub_admins:
        return
    
    # 💥 စာသားကိုပါ ပြင်ဆင်လိုက်သည်
    await callback.message.answer("📢 Now send a text, photo, video, or caption that will be sent to all visitors to the bot.\n\n customer များထံသို့ အသိပေးစာ ကြော်ငြာစာများပေးပို့နိုင်သည်။")
    await state.set_state(AdminBroadcast.waiting_for_msg)
    await callback.answer()

# 💥 NEW: မည်သည့် Media Type မဆို လက်ခံပြီး Copy ကူး၍ ပို့ဆောင်ပေးမည့် စနစ်
@client_admin_router.message(AdminBroadcast.waiting_for_msg)
async def do_broadcast(message: Message, state: FSMContext, bot: Bot):
    await message.answer("⏳ Messages are starting to be sent. Please wait...")
    await state.clear()
    
    # ဤ Bot တွင် ဝယ်ယူဖူးသူ/လာနှိပ်ဖူးသူ ID အားလုံးကို ထုတ်ယူခြင်း (ပုံစံမတူအောင် Unique ယူမည်)
    user_ids = await db.subscriptions.distinct("user_id", {"bot_token": bot.token})
    
    success_count = 0
    for u_id in user_ids:
        try:
            # 💥 send_message အစား copy_message ကို သုံးခြင်းဖြင့် Media မျိုးစုံကို ပို့နိုင်သည်
            await bot.copy_message(
                chat_id=u_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            success_count += 1
            await asyncio.sleep(0.05) # Telegram Rate Limit မမိစေရန် ဖြည်းဖြည်းချင်းပို့မည်
        except Exception:
            pass # User မှ Bot ကို Block ထားပါက ကျော်သွားမည်
            
    await message.answer(f"✅ Message delivery completed.\n📊 Successfully delivered to a total of {success_count} people.")
    
# ==========================================
# ⚙️ 6. Manage Services (ဝန်ဆောင်မှုများ ပြင်ဆင်/ဖျက်သိမ်းရန်)
# ==========================================
@client_admin_router.callback_query(F.data == "manage_services")
async def manage_services_list(callback: CallbackQuery, bot: Bot):
    business = await db.businesses.find_one({"bot_token": bot.token})
    owner_id = business.get("owner_id")
    sub_admins = business.get("sub_admins", [])
    if callback.from_user.id != owner_id and callback.from_user.id not in sub_admins:
        return

    # Active ဖြစ်နေသော Service များကိုသာ ဆွဲထုတ်မည်
    services = await db.services.find({"bot_token": bot.token, "status": "active"}).to_list(length=100)
    
    if not services:
        await callback.answer("No service yet.", show_alert=True)
        return

    keyboard = []
    for s in services:
        keyboard.append([InlineKeyboardButton(text=f"⚙️ {s['name']}", callback_data=f"service_detail_{s['_id']}")])
    
    keyboard.append([InlineKeyboardButton(text="🔙 Admin Menu ", callback_data="back_to_admin")])
    
    await callback.message.edit_text("⚙️ Select the service/ Plan you want to edit/delete.**", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")

@client_admin_router.callback_query(F.data == "back_to_admin")
async def back_to_admin_menu(callback: CallbackQuery, bot: Bot):
    business = await db.businesses.find_one({"bot_token": bot.token})
    is_owner = (callback.from_user.id == business.get("owner_id"))
    await callback.message.edit_text("🛠 Welcome Your Admin Panel!\n\nSelect the required action from the buttons below.", reply_markup=admin_kb(is_owner=is_owner), parse_mode="Markdown")

@client_admin_router.callback_query(F.data.startswith("service_detail_"))
async def show_service_detail(callback: CallbackQuery):
    service_id = callback.data.split("_")[2]
    service = await db.services.find_one({"_id": ObjectId(service_id)})
    
    if not service:
        await callback.answer("This service is no longer available.", show_alert=True)
        return
        
    duration_val = service.get("duration", 0)
    duration_text = "Lifetime" if duration_val == 0 else f"{duration_val} Days"
    
    # 💥 ပြင်ဆင်ထားသော HTML ကုဒ်
    text = (
        f" <b>Service အသေးစိတ်</b>\n\n"
        f" <b>Service/ Plan Name :</b> {service['name']}\n"
        f" <b>Price :</b> {service['price']} MMK\n"
        f" <b>Duration :</b> {duration_text}\n\n"
        f" <b>Note :</b> {service.get('note', 'Not Yet')}\n\n"
        "Choose from the following actions -"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Edit Service/ Plan Name", callback_data=f"edit_name_{service_id}")],
        [InlineKeyboardButton(text="✏️ Edit Price", callback_data=f"edit_price_{service_id}")],
        [InlineKeyboardButton(text="✏️ Edit Note", callback_data=f"edit_note_{service_id}")],
        [InlineKeyboardButton(text="🔄 Migrate to New Channel (ချန်နယ်အသစ်သို့ ပြောင်းမည်)", callback_data=f"migrate_svc_{service_id}")],
        [InlineKeyboardButton(text="❌ Delete Permanently!", callback_data=f"delete_svc_{service_id}")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="manage_services")]
    ])
    
    # 💥 parse_mode="HTML" ပြောင်းသည်
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@client_admin_router.callback_query(F.data.startswith("delete_svc_"))
async def delete_service(callback: CallbackQuery):
    service_id = callback.data.split("_")[2]
    
    # 💥 (အရေးကြီး) - Database ထဲမှ အပြီးတိုင်မဖျက်ဘဲ 'deleted' ဟုသာ ပြောင်းလိုက်မည်။
    # သို့မှသာ ယခင်ဝယ်ထားသော User များကို Auto-Kick စနစ်က ဆက်လက်အလုပ်လုပ်နိုင်မည် ဖြစ်သည်။
    await db.services.update_one({"_id": ObjectId(service_id)}, {"$set": {"status": "deleted"}})
    
    await callback.answer("✅ The service has been successfully deleted.", show_alert=True)
    await manage_services_list(callback, callback.bot)

# --- ပြင်ဆင်ခြင်း (Edit Name / Edit Price) အပိုင်း ---
@client_admin_router.callback_query(F.data.startswith("edit_name_"))
async def ask_edit_name(callback: CallbackQuery, state: FSMContext):
    service_id = callback.data.split("_")[2]
    await state.update_data(edit_svc_id=service_id)
    await callback.message.answer("✏️ Enter the new name of the service/ plan.\n\n ဝန်ဆောင်မှုနာမည်အသစ်ထည့်ပါ")
    await state.set_state(EditService.waiting_for_new_name)
    await callback.answer()

@client_admin_router.message(EditService.waiting_for_new_name)
async def save_new_name(message: Message, state: FSMContext):
    data = await state.get_data()
    service_id = data.get("edit_svc_id")
    await db.services.update_one({"_id": ObjectId(service_id)}, {"$set": {"name": message.text}})
    await message.answer("✅ The service name has been modified. Click /start to return to the Admin Panel.")
    await state.clear()

@client_admin_router.callback_query(F.data.startswith("edit_price_"))
async def ask_edit_price(callback: CallbackQuery, state: FSMContext):
    service_id = callback.data.split("_")[2]
    await state.update_data(edit_svc_id=service_id)
    await callback.message.answer("✏️ Enter the new price of the service/ plan in numbers only.\n\n ဝန်ဆောင်မှု၏ စျေးနှုန်းအသစ်ရိုက်ထည့်ပါ")
    await state.set_state(EditService.waiting_for_new_price)
    await callback.answer()

@client_admin_router.message(EditService.waiting_for_new_price)
async def save_new_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Please sent Number Only!")
        return
    data = await state.get_data()
    service_id = data.get("edit_svc_id")
    await db.services.update_one({"_id": ObjectId(service_id)}, {"$set": {"price": int(message.text)}})
    await message.answer("✅The service price has been modified. Click /start to return to the Admin Panel.")
    await state.clear()

# --- Note ပြင်ဆင်ခြင်း ---
@client_admin_router.callback_query(F.data.startswith("edit_note_"))
async def ask_edit_note(callback: CallbackQuery, state: FSMContext):
    service_id = callback.data.split("_")[2]
    await state.update_data(edit_svc_id=service_id)
    await callback.message.answer("✏️ Enter a New Note for the service/ plan.\n(If you don't want to leave a comment, you can enter 'Not Yet'.)")
    await state.set_state(EditService.waiting_for_new_note)
    await callback.answer()

@client_admin_router.message(EditService.waiting_for_new_note)
async def save_new_note(message: Message, state: FSMContext):
    data = await state.get_data()
    service_id = data.get("edit_svc_id")
    await db.services.update_one({"_id": ObjectId(service_id)}, {"$set": {"note": message.text}})
    await message.answer("✅ The service/ plan Note has been edited. Click /start to return to the Admin Panel.")
    await state.clear()

# ==========================================
# 👥 7. Manage Sub-Admins (အက်ဒမင်အကူ စီမံခန့်ခွဲခြင်း)
# ==========================================
@client_admin_router.callback_query(F.data == "manage_sub_admins")
async def manage_sub_admins(callback: CallbackQuery, bot: Bot):
    business = await db.businesses.find_one({"bot_token": bot.token})
    # ပိုင်ရှင်မှလွဲ၍ ကျန်သူများ ဝင်ခွင့်မရှိပါ
    if callback.from_user.id != business.get("owner_id"): 
        return await callback.answer("❌ Only the owner has access.", show_alert=True)
        
    sub_admins = business.get("sub_admins", [])
    
    text = "👥 Sub-Admin Lists!\n\n"
    if not sub_admins:
        text += "There is currently no Sub-Admin."
    else:
        for idx, admin_id in enumerate(sub_admins, 1):
            text += f"{idx}. User ID: `{admin_id}`\n"
            
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕Add Sub-Admin", callback_data="add_sub_admin")],
        [InlineKeyboardButton(text="❌ Remove Sub-Admin", callback_data="remove_sub_admin")],
        [InlineKeyboardButton(text="🔙 Admin Menu", callback_data="back_to_admin")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

# ==========================================
# 💥 NEW: Admin Invite Code ထုတ်ပေးခြင်း
# ==========================================
@client_admin_router.callback_query(F.data == "add_sub_admin")
async def generate_sub_admin_code(callback: CallbackQuery, bot: Bot):
    # ကျပန်း ဂဏန်း ၆ လုံးပါသော Code ဖန်တီးမည်
    random_code = f"ADMIN-{random.randint(100000, 999999)}"
    
    # DB ထဲသို့ Code အသစ်ကို ယာယီမှတ်သားထားမည်
    await db.businesses.update_one(
        {"bot_token": bot.token},
        {"$set": {"admin_invite_code": random_code}}
    )

    text = (
        "➕ <b>Sub-Admin Invite Code</b>\n\n"
        "အCopy the code below and send it to the person you want to add as an Sub-Admin.\n\n"
        f"<code>{random_code}</code>\n\n"
        "<i>(Once that person enters the above code into this Bot, the Bot will automatically capture their ID and assign them as an Sub-Admin.)\n\n အထက်ပါ ကုတ်ကို admin အကူအဖြစ်ထားရှိချင်သူအား ပို့ပေးပါ။ ထိုသူမှ သင်၏ botတွင် အထက်ပါကုတ်ကို ရိုက်ထည့်ခိုင်းပါ။</i>"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="manage_sub_admins")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

    
@client_admin_router.callback_query(F.data == "remove_sub_admin")
async def remove_sub_admin_prompt(callback: CallbackQuery, bot: Bot):
    business = await db.businesses.find_one({"bot_token": bot.token})
    sub_admins = business.get("sub_admins", [])
    
    # 💥 ခန့်ထားသော Sub-Admin မရှိပါက ချက်ချင်း အသိပေးမည်
    if not sub_admins:
        return await callback.answer("⚠️ There is currently no Sub-Admin assigned.", show_alert=True)
        
    text = "❌ Select the Sub-Admin you want to remove from the list below.\n\n"
    
    keyboard = []
    for admin_id in sub_admins:
        keyboard.append([InlineKeyboardButton(text=f"❌ Remove (ID: {admin_id})", callback_data=f"del_sub_{admin_id}")])
        
    keyboard.append([InlineKeyboardButton(text="🔙 Back", callback_data="manage_sub_admins")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")

# 💥 စာရိုက်ထည့်စရာမလိုတော့ဘဲ ခလုတ်နှိပ်ရုံဖြင့် ဖယ်ရှားပေးမည့်စနစ် 💥
@client_admin_router.callback_query(F.data.startswith("del_sub_"))
async def delete_sub_admin_callback(callback: CallbackQuery, bot: Bot):
    remove_id = int(callback.data.split("_")[2])
    
    # Database ထဲမှ ဖယ်ရှားမည်
    await db.businesses.update_one(
        {"bot_token": bot.token},
        {"$pull": {"sub_admins": remove_id}}
    )
    
    await callback.answer("✅ Sub-Admin has been successfully removed.", show_alert=True)
    
    # ဖယ်ရှားပြီးပါက Sub-Admin စီမံသည့် စာမျက်နှာသို့ အလိုအလျောက် ပြန်သွားမည်
    await manage_sub_admins(callback, bot)

# ==========================================
# 📝 Welcome Message သတ်မှတ်ခြင်း
# ==========================================
@client_admin_router.callback_query(F.data == "set_welcome_msg")
async def set_welcome_msg_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
    business = await db.businesses.find_one({"bot_token": bot.token})
    owner_id = business.get("owner_id")
    sub_admins = business.get("sub_admins", [])
    if callback.from_user.id != owner_id and callback.from_user.id not in sub_admins:
        return

    text = "📝 Create Welcome Message!\n\nEnter the first greeting text that customers will see when they press `/start` to enter the Bot.\n\n ပထမဆုံး သင့်bot ထံလာသူများကို မိတ်ဆက်စကားထည့်ရန်ဖြစ်သည်။\n(eg. A warmly welcome to our VIP Channel...)*"
    await callback.message.answer(text, parse_mode="Markdown")
    await state.set_state(AdminSetup.waiting_for_welcome_msg)
    await callback.answer()

@client_admin_router.message(AdminSetup.waiting_for_welcome_msg)
async def receive_welcome_msg(message: Message, bot: Bot, state: FSMContext):
    await db.businesses.update_one(
        {"bot_token": bot.token}, 
        {"$set": {"welcome_msg": message.text}} # Database သို့ welcome_msg အဖြစ် သိမ်းဆည်းခြင်း
    )
    await message.answer("✅ Welcome Message Created Successfully! \nClick /start to return to the Admin Panel.")
    await state.clear()


# ==========================================
# 🔄 Channel Migration System (ချန်နယ်ပျက်သွားပါက အသစ်သို့ ပြောင်းရွှေ့ခြင်း)
# ==========================================
@client_admin_router.callback_query(F.data.startswith("migrate_svc_"))
async def ask_migration_channel(callback: CallbackQuery, state: FSMContext):
    service_id = callback.data.split("_")[2]
    await state.update_data(migrate_svc_id=service_id)
    
    text = (
        "🔄 **Migrate to New Channel (ချန်နယ်အသစ်သို့ ပြောင်းရွှေ့ခြင်း)**\n\n"
        "ဤစနစ်သည် သင့်၏ လက်ရှိ Group/Channel ပျက်သွားပါက၊ သက်တမ်းကျန်သေးသော (Active) ဖြစ်နေသည့် Customer များအားလုံးထံသို့ Channel အသစ်၏ လင့်ခ်ကို အလိုအလျောက် ပေးပို့ပေးမည့် စနစ်ဖြစ်ပါသည်။\n\n"
        "**လုပ်ဆောင်ရမည့် အဆင့်များ-**\n"
        "၁။ Channel / Group အသစ်တစ်ခု တည်ဆောက်ပြီး ဤ Bot ကို Admin အပြည့်အဝပေးပါ။\n"
        "၂။ ထို Channel / Group အသစ်ထဲမှ စာတစ်ကြောင်းကို ဤနေရာသို့ **Forward** လုပ်ပို့ပေးပါ။"
    )
    await callback.message.answer(text, parse_mode="Markdown")
    await state.set_state(EditService.waiting_for_new_channel)
    await callback.answer()

@client_admin_router.message(EditService.waiting_for_new_channel)
async def process_channel_migration(message: Message, state: FSMContext, bot: Bot):
    chat_id_str = None
    
    # Forward လုပ်လာသော စာဖြစ်လျှင် ID အား ဆွဲယူမည်
    if message.forward_origin:
        if hasattr(message.forward_origin, 'chat'):
            chat_id_str = str(message.forward_origin.chat.id)
        else:
            return await message.answer("❌ Error! Only forward messages from within a group or channel.")
    # စာသားတိုက်ရိုက် ရိုက်ထည့်လျှင်
    elif message.text and (message.text.startswith("-100") or message.text.startswith("@")):
        chat_id_str = message.text.strip()
    else:
        return await message.answer("❌ Error! Please forward a message from the new Group/Channel.")

    data = await state.get_data()
    service_id = data.get("migrate_svc_id")
    
    await message.answer("⏳ Checking permissions and migrating users... Please wait.")
    
    # ၁။ Bot အား Admin ခန့်ထားခြင်း ရှိ/မရှိ စစ်ဆေးခြင်း
    try:
        target_chat_id = int(chat_id_str) if chat_id_str.lstrip('-').isdigit() else chat_id_str
        chat = await bot.get_chat(target_chat_id)
        bot_user = await bot.get_me()
        member = await bot.get_chat_member(chat_id=target_chat_id, user_id=bot_user.id)
        
        status_val = member.status.value if hasattr(member.status, "value") else str(member.status)
        
        if status_val not in ["administrator", "creator"]:
            return await message.answer("❌ Error! Bot is not an Admin in the new Group/Channel yet.")
            
    except Exception as e:
        return await message.answer(f"❌ Error! Unable to verify the new channel. Make sure the bot is added as Admin. ({str(e)})")
        
    # ၂။ Database တွင် Service ၏ Link အဟောင်းကို အသစ်ဖြင့် အစားထိုးမည်
    await db.services.update_one(
        {"_id": ObjectId(service_id)},
        {"$set": {"link": chat_id_str}}
    )
    
    # ၃။ လက်ရှိ Service အား ဝယ်ယူထားသော Active User များကို ဆွဲထုတ်မည်
    active_subs = await db.subscriptions.find({"service_id": service_id, "status": "active"}).to_list(length=5000)
    
    if not active_subs:
        await message.answer("✅ Channel ID updated successfully. (There are no active users to migrate right now).")
        return await state.clear()
        
    # ၄။ User များအတွက် Invite Link အသစ် ဖန်တီးမည်
    try:
        chat_member_link = await bot.create_chat_invite_link(
            chat_id=target_chat_id, 
            creates_join_request=True, 
            name="Migration Link"
        )
        invite_link = chat_member_link.invite_link
    except Exception as e:
        return await message.answer(f"❌ Error creating invite link: {e}")

    # ၅။ Active User များအားလုံးထံသို့ လင့်ခ်များ အလိုအလျောက် လိုက်ပို့မည်
    success_count = 0
    fail_count = 0
    
    service = await db.services.find_one({"_id": ObjectId(service_id)})
    service_name = service.get("name", "our VIP Service")
    
    migration_msg = (
        f"📢 **Channel Migration Notice (အရေးကြီး အသိပေးချက်)**\n\n"
        f"လူကြီးမင်း ဝယ်ယူထားသော **{service_name}** ၏ ချန်နယ်ဟောင်းမှာ အကြောင်းအမျိုးမျိုးကြောင့် ပျက်ယွင်းသွားပါသဖြင့် ချန်နယ်အသစ်သို့ အောက်ပါလင့်ခ်မှတစ်ဆင့် ပြန်လည်ဝင်ရောက်ပေးပါရန် အသိပေးအပ်ပါသည်။\n\n"
        f"*(လူကြီးမင်း၏ ကျန်ရှိသော သက်တမ်းများမှာ မူလအတိုင်း ဆက်လက် တည်ရှိနေမည်ဖြစ်ပါသည်။)*"
    )
    user_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Join New Channel", url=invite_link)]
    ])

    for sub in active_subs:
        user_id = sub["user_id"]
        try:
            await bot.send_message(chat_id=user_id, text=migration_msg, reply_markup=user_kb, parse_mode="Markdown")
            success_count += 1
            await asyncio.sleep(0.05) # Rate Limit မမိစေရန် ဖြည်းဖြည်းချင်းပို့မည်
        except Exception:
            fail_count += 1 # User က Bot ကို Block ထားလျှင် Fail ဖြစ်မည်
            
    final_text = (
        f"✅ **Migration Successfully Completed!**\n\n"
        f"Group/Channel အသစ်သို့ အောင်မြင်စွာ ချိတ်ဆက်ပြီးပါပြီ။\n"
        f"👥 Active Users ထံသို့ လင့်ခ်ပေးပို့မှု အခြေအနေ:\n"
        f"✔️ အောင်မြင်: **{success_count}** ဦး\n"
        f"❌ မအောင်မြင် (Bot ကို Block ထားသူများ): **{fail_count}** ဦး"
    )
    await message.answer(final_text, parse_mode="Markdown")
    await state.clear()
