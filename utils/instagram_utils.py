import os
import json
import random
import time
import requests
from typing import Dict, List, Optional
from instaloader import Instaloader, Profile, StoryItem, Highlight
from dotenv import load_dotenv
from utils.logging_utils import setup_logging, logger

load_dotenv()
logger = setup_logging()

def load_user_agents(file_path: str = "user-agents.json") -> List[str]:
    """Memuat daftar user agents dari file JSON."""
    logger.debug(f"Loading user agents from {file_path}")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            agents = json.load(f)
            return [ua for ua in agents if isinstance(ua, str) and ua.strip()]
    except Exception as e:
        logger.error(f"Error loading user agents: {str(e)}")
        raise RuntimeError(f"Error loading user agents: {str(e)}")

USER_AGENTS = load_user_agents()

class InstagramClient:
    def __init__(self, env_vars: Dict[str, str]):
        """Inisialisasi InstagramClient dengan autentikasi berbasis username dan password."""
        self.env_vars = env_vars
        self.username = env_vars['INSTAGRAM_USERNAME']
        self.password = env_vars['INSTAGRAM_PASSWORD']
        self.loader = Instaloader(
            user_agent=random.choice(USER_AGENTS),
            sleep=True,
            quiet=False,  # Set ke False untuk melihat output instaloader
            request_timeout=30,
            dirname_pattern="{target}",
            filename_pattern="{date_utc}_UTC_{profile}",
            download_pictures=True,
            download_videos=True,
            download_video_thumbnails=False,
            download_geotags=False,
            post_metadata_txt_pattern="",
            storyitem_metadata_txt_pattern="",
            compress_json=False,
            download_comments=False
        )
        self.login()
        self.request_count = 0
        
        # Ambil semua cookie sebagai dictionary
        cookie_dict = self.loader.context._session.cookies.get_dict()
        logger.debug(f"Cookies after login: {cookie_dict}")
        
        # Ambil sessionid dan csrftoken dari dictionary
        sessionid = cookie_dict.get('sessionid', '').strip()
        csrftoken = cookie_dict.get('csrftoken', '').strip()
        
        # Periksa apakah sessionid atau csrftoken kosong atau tidak ada
        if not sessionid or not csrftoken:
            logger.error(f"Invalid sessionid or csrftoken. sessionid: '{sessionid}', csrftoken: '{csrftoken}', Available cookies: {cookie_dict}")
            # Jika sessionid kosong, hapus sesi lama dan coba login ulang
            session_file = f"session_{self.username}.dat"
            if os.path.exists(session_file):
                logger.warning(f"Removing invalid session file {session_file} and retrying login")
                os.remove(session_file)
                self.login()  # Login ulang
                cookie_dict = self.loader.context._session.cookies.get_dict()
                logger.debug(f"Cookies after retry login: {cookie_dict}")
                sessionid = cookie_dict.get('sessionid', '').strip()
                csrftoken = cookie_dict.get('csrftoken', '').strip()
                if not sessionid or not csrftoken:
                    logger.error(f"Retry login failed. sessionid: '{sessionid}', csrftoken: '{csrftoken}', Available cookies: {cookie_dict}")
                    raise RuntimeError("Failed to obtain valid sessionid or csrftoken even after retry")
        
        # Validasi sesi setelah login
        if not self.validate_session():
            logger.error("Session validation failed after login")
            raise RuntimeError("Session is invalid despite successful login")

        self.headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Cookie": f"sessionid={sessionid}; csrftoken={csrftoken}",
            "X-CSRFToken": csrftoken,
            "Referer": "https://www.instagram.com/",
        }
        logger.debug(f"Headers initialized: {self.headers}")

    def login(self):
        """Login ke Instagram menggunakan username dan password, dengan sesi tersimpan."""
        logger.debug(f"Attempting to login as {self.username}")
        session_file = f"session_{self.username}.dat"
        try:
            if os.path.exists(session_file):
                logger.info(f"Loading existing session from {session_file}")
                self.loader.load_session_from_file(self.username, session_file)
                if self.validate_session():
                    logger.info("Session loaded and validated successfully")
                else:
                    logger.warning("Loaded session invalid, performing new login")
                    self.loader.login(self.username, self.password)
                    self.loader.save_session_to_file(session_file)
                    logger.info(f"New session saved to {session_file}")
            else:
                logger.info(f"No session file found, performing new login for {self.username}")
                self.loader.login(self.username, self.password)
                self.loader.save_session_to_file(session_file)
                logger.info(f"New session saved to {session_file}")
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            raise RuntimeError(f"Failed to login: {str(e)}")

    def validate_session(self) -> bool:
        """Memvalidasi sesi yang dimuat."""
        logger.debug(f"Validating session for {self.username}")
        try:
            Profile.from_username(self.loader.context, self.username)
            logger.info("Session validated successfully")
            return True
        except Exception as e:
            logger.error(f"Session validation failed: {str(e)}")
            return False

    def simulate_human_behavior(self):
        """Mensimulasikan perilaku manusia untuk menghindari deteksi bot."""
        self.request_count += 1
        logger.debug(f"Request count: {self.request_count}")
        delay = random.uniform(2, 5)
        logger.debug(f"Applying human-like delay of {delay:.2f} seconds")
        time.sleep(delay)
        if self.request_count % random.randint(5, 10) == 0:
            long_delay = random.uniform(30, 60)
            logger.info(f"Simulating long pause of {long_delay:.2f} seconds")
            time.sleep(long_delay)
        if random.random() < 0.2:
            logger.debug("Simulating dummy visit to Instagram homepage")
            requests.get("https://www.instagram.com/", headers=self.headers)
            time.sleep(random.uniform(1, 3))

    def get_profile(self, username: str) -> Profile:
        """Mengambil profil Instagram berdasarkan username."""
        logger.debug(f"Fetching profile for username: {username}")
        self.simulate_human_behavior()
        try:
            profile = Profile.from_username(self.loader.context, username)
            logger.info(f"Profile fetched successfully for {username}")
            return profile
        except Exception as e:
            logger.error(f"Failed to fetch profile for {username}: {str(e)}")
            raise

    def get_stories(self, user_ids: List[int]) -> List[StoryItem]:
        """Mengambil stories dari user ID yang diberikan."""
        logger.debug(f"Fetching stories for user IDs: {user_ids}")
        self.simulate_human_behavior()
        try:
            stories = []
            for story in self.loader.get_stories(user_ids):
                stories.extend(story.get_items())
            stories.sort(key=lambda x: x.date_utc)  # Urutkan berdasarkan tanggal
            logger.info(f"Fetched {len(stories)} stories")
            return stories
        except Exception as e:
            logger.error(f"Error fetching stories: {str(e)}")
            raise Exception(f"Failed to fetch stories: {str(e)}")

    def get_highlights(self, profile: Profile) -> List[Highlight]:
        """Mengambil highlights dari profil yang diberikan."""
        logger.debug(f"Fetching highlights for profile: {profile.username}")
        self.simulate_human_behavior()
        try:
            highlights = list(self.loader.get_highlights(user=profile))
            logger.info(f"Fetched {len(highlights)} highlights")
            return highlights
        except Exception as e:
            logger.error(f"Error fetching highlights: {str(e)}")
            raise Exception(f"Failed to fetch highlights: {str(e)}")

    def download_storyitem(self, item: StoryItem, target: str) -> str:
        """Mengunduh item story ke direktori target."""
        logger.debug(f"Downloading story item {item.mediaid} to {target}")
        self.simulate_human_behavior()
        os.makedirs(target, exist_ok=True)
        try:
            self.loader.download_storyitem(item, target)
            valid_extensions = ('.jpg', '.jpeg', '.png', '.mp4', '.mov')
            media_files = [
                f for f in os.listdir(target)
                if f.lower().endswith(valid_extensions)
            ]
            if not media_files:
                logger.error(f"No valid media files found for item {item.mediaid}")
                raise Exception("No media files downloaded")
            latest_file = max(
                [os.path.join(target, f) for f in media_files],
                key=os.path.getmtime
            )
            logger.info(f"Story item {item.mediaid} downloaded to {latest_file}")
            return latest_file
        except Exception as e:
            logger.error(f"Failed to download story item {item.mediaid}: {str(e)}")
            raise