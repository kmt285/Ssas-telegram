import os
from dotenv import load_dotenv

load_dotenv()

MASTER_BOT_TOKEN = os.getenv("MASTER_BOT_TOKEN")
MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = "saas_bot_db"
PORT = int(os.getenv("PORT", 8080)) # Render အတွက် Port
