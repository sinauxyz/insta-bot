import re
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from handlers.instagram_handlers import (
    handle_profile_pic, handle_stories, handle_highlights, handle_highlight_items,
    handle_profile_info
)
from utils.logging_utils import setup_logging, log_errors

logger = setup_logging(logging.DEBUG)

@log_errors(logger)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE, config: dict):
    if not update.message or not update.effective_user:
        logger.warning("Received update without message or user in start handler")
        return
    lang = update.effective_user.language_code or config["default_language"]
    logger.info(f"Sending start message to user {update.effective_user.id}")
    await update.message.reply_text(config["languages"][lang]["start"])

@log_errors(logger)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE, config: dict, client):
    # Periksa apakah update memiliki message dan effective_user
    if not update.message:
        logger.warning(f"Received update without message: {update}")
        return
    if not update.effective_user:
        logger.warning(f"Received update without effective_user: {update}")
        lang = config["default_language"]  # Fallback ke default jika user tidak ada
    else:
        lang = update.effective_user.language_code or config["default_language"]

    url = update.message.text.strip()
    logger.info(f"Received message from user {update.effective_user.id if update.effective_user else 'unknown'}: {url}")
    username = extract_username(url)

    if not username:
        logger.warning(f"Invalid URL received: {url}")
        await update.message.reply_text(config["languages"][lang]["invalid_url"])
        return

    context.user_data['current_profile'] = username
    keyboard = [
        [
            InlineKeyboardButton("📷 Foto Profil", callback_data='profile_pic'),
            InlineKeyboardButton("📹 Story", callback_data='story')
        ],
        [
            InlineKeyboardButton("🌟 Highlights", callback_data='highlights'),
            InlineKeyboardButton("📊 Info Profil", callback_data='profile_info')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    logger.info(f"Sending feature menu for {username}")
    await update.message.reply_text(f"Pilih fitur untuk @{username}:", reply_markup=reply_markup)

@log_errors(logger)
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, config: dict, client):
    query = update.callback_query
    if not query:
        logger.warning("Received update without callback_query")
        return
    await query.answer()
    logger.info(f"Received callback query: {query.data} from user {query.from_user.id}")

    lang = update.effective_user.language_code or config["default_language"] if update.effective_user else config["default_language"]
    username = context.user_data.get('current_profile')
    if not username:
        logger.warning("Session expired, no current_profile found")
        await query.edit_message_text("❌ Session expired, silakan kirim URL lagi")
        return

    try:
        if query.data == 'profile_pic':
            await handle_profile_pic(query, username, client, config, lang)
        elif query.data == 'story':
            await handle_stories(query, username, client, config, lang)
        elif query.data == 'highlights':
            await handle_highlights(query, username, 0, client, config, lang)  # Tambahkan page=0 sebagai default
        elif query.data.startswith('highlights_next_'):
            next_page = int(query.data.split('_')[2])
            await handle_highlights(query, username, next_page, client, config, lang)
        elif query.data.startswith('highlights_prev_'):
            prev_page = int(query.data.split('_')[2])
            await handle_highlights(query, username, prev_page, client, config, lang)
        elif query.data.startswith('highlight_'):
            highlight_id = query.data.split('_')[1]
            await handle_highlight_items(query, username, highlight_id, client, config, lang)
        elif query.data == 'profile_info':
            await handle_profile_info(query, username, client, config, lang)
    except Exception as e:
        logger.error(f"Failed to process callback {query.data}: {str(e)}")
        await query.edit_message_text(config["languages"][lang]["error"])

def extract_username(url: str) -> str:
    logger.debug(f"Extracting username from URL: {url}")
    match = re.match(
        r"(?:https?://)?(?:www\.)?instagram\.com/([a-zA-Z0-9_.]+)/?",
        url,
        re.IGNORECASE
    )
    username = match.group(1) if match else None
    logger.debug(f"Extracted username: {username}")
    return username