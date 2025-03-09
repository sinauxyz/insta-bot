import os
import pytz
import time
import shutil
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils.logging_utils import logger, log_errors
from utils.instagram_utils import InstagramClient

# Zona waktu Indonesia (WIB, UTC+7)
WIB_TIMEZONE = pytz.timezone("Asia/Jakarta")

@log_errors(logger)
async def handle_profile_pic(query, username: str, client: InstagramClient, config: dict, lang: str):
    logger.info(f"Handling profile pic request for {username}")
    profile = client.get_profile(username)

    if profile.is_private and not profile.followed_by_viewer:
        logger.warning(f"Profile {username} is private and not followed")
        await query.message.reply_text(config["languages"][lang]["private_profile"])
        return

    hd_url = profile.profile_pic_url.replace("/s150x150/", "/s1080x1080/")
    temp_file = f"temp_{username}_{int(time.time())}.jpg"
    try:
        response = requests.get(hd_url, headers=client.headers, stream=True)
        response.raise_for_status()
        with open(temp_file, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        with open(temp_file, "rb") as f:
            await query.message.reply_photo(
                photo=f,
                caption=f"📷 Foto Profil @{username}",
                read_timeout=60
            )
        logger.info(f"Profile pic sent for {username}")
    except requests.RequestException as e:
        logger.error(f"Failed to download profile pic for {username}: {str(e)}")
        await query.message.reply_text("⚠️ Gagal mengambil foto profil")
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)
            logger.info(f"🗑️ File sementara {temp_file} dihapus")

@log_errors(logger)
async def handle_profile_info(query, username: str, client: InstagramClient, config: dict, lang: str):
    logger.info(f"Handling profile info request for {username}")
    profile = client.get_profile(username)

    info_text = (
        f"📊 Info Profil @{username}:\n"
        f"👤 Nama: {profile.full_name}\n"
        f"📝 Bio: {profile.biography or 'Tidak ada bio'}\n"
        f"✅ Terverifikasi: {'Ya' if profile.is_verified else 'Tidak'}\n"
        f"🏢 Bisnis: {'Ya' if profile.is_business_account else 'Tidak'}\n"
        f"🔗 Followers: {profile.followers:,}\n"
        f"👀 Following: {profile.followees:,}\n"
        f"📌 Post: {profile.mediacount:,}"
    )

    try:
        await query.message.reply_text(info_text)
        logger.info(f"Profile info sent for {username}")
    except Exception as e:
        logger.error(f"Failed to send profile info for {username}: {str(e)}")
        await query.message.reply_text("⚠️ Gagal mengambil info profil")

@log_errors(logger)
async def handle_stories(query, username: str, client: InstagramClient, config: dict, lang: str):
    logger.info(f"Handling stories request for {username}")
    profile = client.get_profile(username)
    if profile.is_private and not profile.followed_by_viewer:
        logger.warning(f"Profile {username} is private and not followed")
        await query.message.reply_text(config["languages"][lang]["private_profile"])
        return

    stories = client.get_stories([profile.userid])
    if not stories:
        logger.info(f"No stories available for {username}")
        await query.message.reply_text(config["languages"][lang]["no_stories"])
        return

    temp_dir = f"temp_{username}_{int(time.time())}"
    os.makedirs(temp_dir, exist_ok=True)
    sent_count = 0

    try:
        logger.info(f"🔄 Memproses {len(stories)} story untuk @{username}")
        for story_item in stories:
            try:
                file_path = client.download_storyitem(story_item, temp_dir)
                file_size = os.path.getsize(file_path)
                if file_size > config["max_file_size_mb"] * 1024 * 1024:
                    logger.warning(f"File {file_path} exceeds size limit: {file_size} bytes")
                    await query.message.reply_text("⚠️ File melebihi batas ukuran")
                    os.remove(file_path)
                    continue

                # Konversi waktu UTC ke WIB (UTC+7)
                local_time = story_item.date_utc.replace(tzinfo=pytz.utc).astimezone(WIB_TIMEZONE)
                caption = f"{'📹' if story_item.is_video else '📸'} {local_time.strftime('%d-%m-%Y %H:%M:%S WIB')}"
                with open(file_path, "rb") as f:
                    logger.info(f"Sending story item {story_item.mediaid} for {username}")
                    if story_item.is_video:
                        await query.message.reply_video(video=f, caption=caption, read_timeout=60, write_timeout=60)
                    else:
                        await query.message.reply_photo(photo=f, caption=caption, read_timeout=60)
                sent_count += 1
                os.remove(file_path)
                time.sleep(2)
            except Exception as e:
                logger.error(f"Failed to process story item {story_item.mediaid}: {str(e)}")
                continue

        logger.info(f"Sent {sent_count} stories for {username}")
        await query.message.reply_text(f"📤 Total {sent_count} story berhasil dikirim")
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.info(f"🗑️ Direktori {temp_dir} berhasil dibersihkan")

@log_errors(logger)
async def handle_highlights(query, username: str, page: int, client: InstagramClient, config: dict, lang: str):
    logger.info(f"Handling highlights request for {username}, page {page}")
    profile = client.get_profile(username)
    highlights = client.get_highlights(profile)

    if not highlights:
        logger.info(f"No highlights available for {username}")
        await query.message.reply_text(config["languages"][lang]["no_highlights"])
        return

    items_per_page = 10
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    current_highlights = highlights[start_idx:end_idx]

    keyboard = []
    for highlight in current_highlights:
        title = highlight.title[:15] + "..." if len(highlight.title) > 15 else highlight.title
        keyboard.append([
            InlineKeyboardButton(f"🌟 {title}", callback_data=f"highlight_{highlight.unique_id}")
        ])

    navigation_buttons = []
    if page > 0:
        navigation_buttons.append(InlineKeyboardButton("⏪ Kembali", callback_data=f"highlights_prev_{page - 1}"))
    if len(highlights) > end_idx:
        navigation_buttons.append(InlineKeyboardButton("⏩ Lanjutkan", callback_data=f"highlights_next_{page + 1}"))
    if navigation_buttons:
        keyboard.append(navigation_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(
        f"Pilih highlight untuk @{username} (Halaman {page + 1}):",
        reply_markup=reply_markup
    )

@log_errors(logger)
async def handle_highlight_items(query, username: str, highlight_id: str, client: InstagramClient, config: dict, lang: str):
    logger.info(f"Handling highlight items for {username}, highlight_id {highlight_id}")
    profile = client.get_profile(username)
    highlights = client.get_highlights(profile)
    highlight = next((h for h in highlights if str(h.unique_id) == highlight_id), None)

    if not highlight:
        logger.warning(f"Highlight {highlight_id} not found for {username}")
        await query.message.reply_text("❌ Highlight tidak ditemukan")
        return

    items = list(highlight.get_items())
    if not items:
        logger.info(f"No items in highlight {highlight_id} for {username}")
        await query.message.reply_text("📭 Tidak ada item di highlight ini")
        return

    temp_dir = f"temp_highlight_{username}_{int(time.time())}"
    os.makedirs(temp_dir, exist_ok=True)
    sent_count = 0

    try:
        logger.info(f"🔄 Memproses {len(items)} item dari highlight '{highlight.title}'")
        for idx, item in enumerate(items, start=1):
            try:
                file_path = client.download_storyitem(item, temp_dir)
                file_size = os.path.getsize(file_path)
                if file_size > config["max_file_size_mb"] * 1024 * 1024:
                    logger.warning(f"File {file_path} exceeds size limit: {file_size} bytes")
                    await query.message.reply_text("⚠️ File melebihi batas ukuran")
                    os.remove(file_path)
                    continue

                # Konversi waktu UTC ke WIB (UTC+7)
                local_time = item.date_utc.replace(tzinfo=pytz.utc).astimezone(WIB_TIMEZONE)
                # Gunakan tag HTML <b> untuk teks tebal
                caption = f"<b>[{idx}].</b>🌟 {highlight.title} - {'📹' if item.is_video else '📸'} {local_time.strftime('%d-%m-%Y %H:%M:%S WIB')}"
                with open(file_path, "rb") as f:
                    logger.info(f"Sending highlight item {item.mediaid} for {username}")
                    if item.is_video:
                        await query.message.reply_video(
                            video=f,
                            caption=caption,
                            parse_mode="HTML",  # Aktifkan parsing HTML
                            read_timeout=60,
                            write_timeout=60
                        )
                    else:
                        await query.message.reply_photo(
                            photo=f,
                            caption=caption,
                            parse_mode="HTML",  # Aktifkan parsing HTML
                            read_timeout=60
                        )
                sent_count += 1
                os.remove(file_path)
                time.sleep(1)
            except Exception as e:
                logger.error(f"Failed to process highlight item {item.mediaid}: {str(e)}")
                continue

        logger.info(f"Sent {sent_count} items for highlight {highlight_id}")
        await query.message.reply_text(f"✅ {sent_count} item dari highlight '{highlight.title}' berhasil dikirim")
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.info(f"🗑️ Direktori {temp_dir} berhasil dibersihkan")