tee core/config.py > /dev/null << 'EOF'
import os
from dotenv import load_dotenv

load_dotenv()

MASTER_BOT_TOKEN = os.getenv("MASTER_BOT_TOKEN")
MONGODB_URI = "mongodb://localhost:27017/"
DB_NAME = "saas_bot_db"

# Webhook Settings 
WEBHOOK_HOST = "34.134.65.219"
WEBHOOK_PORT = 8443
EOF
