import os
from dotenv import load_dotenv

load_dotenv()

MASTER_BOT_TOKEN = os.getenv("MASTER_BOT_TOKEN")
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
DB_NAME = "saas_bot_db"

# Webhook Settings
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", 8443))
