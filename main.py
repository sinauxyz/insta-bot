import json
import os
import logging
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    CallbackQueryHandler
)
from dotenv import load_dotenv
from utils.logging_utils import setup_logging
from utils.instagram_utils import InstagramClient
from handlers.telegram_handlers import start, handle_message, button_handler

load_dotenv()
logger = setup_logging(logging.DEBUG)

# Load Configuration
logger.debug("Loading configuration from config.json")
with open("config/config.json", "r", encoding="utf-8") as f:
    CONFIG = json.load(f)
logger.info("Configuration loaded successfully")

# Load Environment Variables
REQUIRED_ENV_VARS = ['TOKEN_BOT', 'INSTAGRAM_USERNAME', 'INSTAGRAM_PASSWORD']
env_vars = {var: os.getenv(var).strip('"').strip("'") if os.getenv(var) else None for var in REQUIRED_ENV_VARS}

if any(value is None for value in env_vars.values()):
    missing = [var for var, val in env_vars.items() if val is None]
    logger.error(f"Missing .env variables: {', '.join(missing)}")
    exit(1)
logger.info("All required environment variables loaded")

# Initialize Instagram Client
logger.debug("Initializing Instagram client")
client = InstagramClient(env_vars)
if not client.validate_session():
    logger.error("Initial session validation failed after login")
    admin_chat_id = "YOUR_ADMIN_CHAT_ID"  # Ganti dengan ID chat Anda
    app = Application.builder().token(env_vars['TOKEN_BOT']).build()
    app.bot.send_message(chat_id=admin_chat_id, text="⚠️ Gagal login ke Instagram. Periksa username dan password di .env.")
    exit(1)
logger.info(f"Instagram login successful as {client.username}")

# Main Function
def main():
    logger.debug("Building Telegram application")
    application = Application.builder().token(env_vars['TOKEN_BOT']).build()

    # Add Handlers
    application.add_handler(CommandHandler("start", lambda u, c: start(u, c, CONFIG)))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: handle_message(u, c, CONFIG, client)))
    application.add_handler(CallbackQueryHandler(lambda u, c: button_handler(u, c, CONFIG, client)))

    logger.info("Bot started successfully")
    application.run_polling()

if __name__ == "__main__":
    main()