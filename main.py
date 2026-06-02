# main.py
import os
import sys
import mimetypes
import asyncio

# ==========================================================================
# 🌟 PERFECT EVENT LOOP FIX FOR PYTHON 3.12 / 3.14
# ==========================================================================
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

from pyrogram import Client, filters
from pyrogram.types import Message
from aiohttp import web

# ==========================================================================
# ⚠️ ENVIRONMENT VARIABLES များကို ဖတ်ရှုခြင်း
# ==========================================================================
try:
    API_ID = int(os.environ.get("API_ID", "0"))
    BIN_CHANNEL = int(os.environ.get("BIN_CHANNEL", "0"))
except ValueError as e:
    print(f"❌ ENV ERROR: API_ID သို့မဟုတ် BIN_CHANNEL ကို Number အစစ်ပဲ ထည့်ရပါမည်။ ({e})")
    sys.exit(1)

API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
APP_URL = os.environ.get("APP_URL", "")
PORT = int(os.environ.get("PORT", "8080"))

if not API_ID or not API_HASH or not BOT_TOKEN or not BIN_CHANNEL:
    print("❌ CRITICAL ERROR: Environment Variables မပြည့်စုံပါ။")
    sys.exit(1)

# 🌟 RENDER RESTART FIX: in_memory=True ကို သုံးထားသဖြင့် ဆာဗာ Restart ဖြစ်လျှင် ဆက်ရှင်ငြိသည့် ပြဿနာ လုံးဝ မရှိတော့ပါ။
bot = Client("KMTStreamBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)
routes = web.RouteTableDef()

# ==========================================================================
# ၁။ TELEGRAM BOT LOGIC
# ==========================================================================

@bot.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    await message.reply_text(
        "👋 **KYAW MIN TUN - File Stream Bot မှ ကြိုဆိုပါတယ်ဗျာ။**\n\n"
        "📁 ကျွန်တော့်ထံသို့ မည်သည့် ဖိုင်၊ ဓာတ်ပုံ၊ ဗီဒီယို သို့မဟုတ် အော်ဒီယိုမဆို ပေးပို့လိုက်ပါ။\n"
        "💡 သင့် Blog/Website ၏ Download Button သို့မဟုတ် ဗီဒီယို Player တွင် တိုက်ရိုက်ထည့်သွင်းအသုံးပြုနိုင်မယ့် **Direct Link** ကို ချက်ချင်း ထုတ်ပေးသွားမှာ ဖြစ်ပါတယ်ခင်ဗျာ။",
        reply_to_message_id=message.id
    )

@bot.on_message(filters.private & (filters.document | filters.video | filters.audio | filters.photo))
async def handle_incoming_file(client: Client, message: Message):
    try:
        reply_msg = await message.reply_text("🔄 Processing file... Please wait...", reply_to_message_id=message.id)
        
        # Log Channel သို့ Forward လှမ်းလုပ်မည်
        forwarded = await message.forward(BIN_CHANNEL)
        msg_id = forwarded.id
        direct_link = f"{APP_URL}/file/{msg_id}"
        
        await reply_msg.edit_text(
            f"**✅ Direct Download / Stream Link ထုတ်ပေးပြီးပါပြီ**\n\n"
            f"🔗 **လင့်ခ်အမှန်:**\n`{direct_link}`\n\n"
            f"💡 ဤလင့်ခ်ကို မိမိ Blog ၏ Download Button တွင် ဖြစ်စေ၊ ဗီဒီယို Player တွင်ဖြစ်စေ တိုက်ရိုက်ထည့်သွင်းအသုံးပြုနိုင်ပါပြီခင်ဗျာ။",
            disable_web_page_preview=True
        )
    except Exception as e:
        await message.reply_text(
            f"❌ **Error occurred:** {str(e)}\n\n"
            f"💡 **အကြံပြုချက်:**\n"
            f"၁။ Bot အား ခင်ဗျား၏ Private Channel ထဲတွင် **Admin** အဖြစ် သေချာခန့်ထားရပါမည်။\n"
            f"၂။ Admin Role ပေးသည့်အခါ **Post Messages (စာပို့ခွင့်)** ပါဝါကို သေချာ အမှန်ခြစ် ပေးထားရပါမည်ဗျာ။"
        )

@bot.on_message(filters.private & filters.text)
async def text_guide(client: Client, message: Message):
    await message.reply_text(
        "ℹ️ **စာသား (Text) များကို လင့်ခ်ပြောင်းပေး၍ မရပါခင်ဗျာ။**\n\n"
        "ဒေါင်းလုဒ်လင့်ခ် ထုတ်ယူလိုသော ဖိုင် (Document)၊ ဗီဒီယို (Video) သို့မဟုတ် ဓာတ်ပုံ (Photo) များကိုသာ ပူးတွဲ (Attachment) အနေဖြင့် ပေးပို့ပေးပါဗျာ။"
    )

# ==========================================================================
# ၂။ WEB SERVER LOGIC
# ==========================================================================
@routes.get("/file/{msg_id}")
async def stream_handler(request):
    msg_id = int(request.match_info["msg_id"])
    try:
        message = await bot.get_messages(BIN_CHANNEL, msg_id)
        media = message.document or message.video or message.audio or message.photo
        
        if not media:
            return web.Response(text="ဖိုင်ကို ရှာမတွေ့တော့ပါ။", status=404)
            
        file_name = getattr(media, "file_name", "image.png" if message.photo else "file.bin")
        file_size = media.file_size
        
        mime_type, _ = mimetypes.guess_type(file_name)
        if not mime_type:
            mime_type = "application/octet-stream"
            
        headers = {
            "Content-Type": mime_type,
            "Content-Length": str(file_size),
            "Content-Disposition": f'inline; filename="{file_name}"',
            "Accept-Ranges": "bytes"
        }
        
        response = web.StreamResponse(status=200, reason="OK", headers=headers)
        await response.prepare(request)
        
        async for chunk in bot.stream_media(media):
            await response.write(chunk)
            
        await response.write_eof()
        return response
    except Exception as e:
        return web.Response(text=f"Server Error: {str(e)}", status=500)

@routes.get("/")
async def home_page(request):
    return web.Response(text="KYAW MIN TUN - Direct File Stream Engine is securely running Live!")

# ==========================================================================
# ၃။ SERVER နှင့် BOT ကို စတင်ပတ်မည့်စနစ်
# ==========================================================================
async def main():
    print("🔄 Connecting to Telegram Servers...")
    try:
        await bot.start()
        print("✅ Telegram Bot Connected Successfully!")
        
        # 🌟 PEER ID INVALID FIX: ဆာဗာစတင်ပတ်သည်နှင့် Channel ID ကို အတင်းဆွဲယူပြီး Cache သွင်းခိုင်းသည့်စနစ် 🌟
        print(f"🔄 Fetching and Caching Log Channel (ID: {BIN_CHANNEL})...")
        try:
            chat = await bot.get_chat(BIN_CHANNEL)
            print(f"✅ Peer Cached Successfully! Linked to Channel: '{chat.title}'")
        except Exception as peer_err:
            print(f"❌ PEER CACHE CRITICAL ERROR: {peer_err}")
            print("💡 ရာနှုန်းပြည့် သေချာသွားပါပြီ - ဤ Error ပြနေပါက Render Environment Variable ထဲက BIN_CHANNEL ID အမှားကြီး ဖြစ်နေလို့ပါ သို့မဟုတ် Bot က အဲဒီ Channel ထဲမှာ Admin မဖြစ်သေးလို့ပါ။")
            
    except Exception as e:
        print(f"❌ TELEGRAM CONNECTION FAILED: {e}")
        sys.exit(1)

    print("🔄 Starting Web Server...")
    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    
    print(f"🚀 All Services are Live on Port {PORT}!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    loop.run_until_complete(main())
