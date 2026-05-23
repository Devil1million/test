"""
Advanced Auto Caption Bot - Configuration Module
Handles all bot settings, environment variables, and constants
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import List

# Load environment variables
load_dotenv()

class Config:
    """Main configuration class for the bot"""
    
    # ==================== TELEGRAM SETTINGS ====================
    API_ID: int = int(os.getenv("API_ID", "0"))
    API_HASH: str = os.getenv("API_HASH", "")
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    OWNER_ID: int = int(os.getenv("OWNER_ID", "0"))
    BOT_USERNAME: str = os.getenv("BOT_USERNAME", "")
    SUPPORT_USERNAME: str = os.getenv("SUPPORT_USERNAME", "World_Fastest_Bots")
    
    # ==================== DATABASE SETTINGS ====================
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "anime_caption_bot")
    
    # ==================== API KEYS ====================
    TMDB_API_KEY: str = os.getenv("TMDB_API_KEY", "")
    
    # ==================== LOGIN PASSWORDS ====================
    VALID_PASSWORDS: List[str] = [
        os.getenv("LOGIN_PASSWORD_1", "Developer Infinito"),
        os.getenv("LOGIN_PASSWORD_2", "Dev Infinito")
    ]
    LOGIN_EXPIRY_HOURS: int = 24
    
    # ==================== PERFORMANCE SETTINGS ====================
    MAX_PROCESSING_TIME: float = float(os.getenv("MAX_PROCESSING_TIME", "0.2"))
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "3600"))
    VIDEO_DOWNLOAD_ENABLED: bool = os.getenv("VIDEO_DOWNLOAD_ENABLED", "false").lower() == "true"
    
    # ==================== RATE LIMITING ====================
    RATE_LIMIT_SECONDS: int = int(os.getenv("RATE_LIMIT_SECONDS", "2"))
    MAX_VIDEOS_PER_HOUR: int = int(os.getenv("MAX_VIDEOS_PER_HOUR", "100"))
    
    # ==================== WEB DASHBOARD ====================
    WEB_DASHBOARD_ENABLED: bool = os.getenv("WEB_DASHBOARD_ENABLED", "true").lower() == "true"
    DASHBOARD_PORT: int = int(os.getenv("DASHBOARD_PORT", "8080"))
    DASHBOARD_HOST: str = os.getenv("DASHBOARD_HOST", "0.0.0.0")
    
    # ==================== LOGGING ====================
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE_ENABLED: bool = os.getenv("LOG_FILE_ENABLED", "true").lower() == "true"
    LOG_DIR: Path = Path("logs")
    
    # ==================== PATHS ====================
    BASE_DIR: Path = Path(__file__).parent.parent
    TEMP_DIR: Path = BASE_DIR / "temp"
    
    # ==================== BOT MESSAGES ====================
    UNAUTHORIZED_MESSAGE = """
🔒 **This bot is private.**

You are not authorized to use this bot.
Please contact @{support} for access.
    """.format(support=SUPPORT_USERNAME)
    
    START_MESSAGE = """
🎬 **Welcome to Auto Caption Bot!**

⚡ **The Fastest Anime Caption Bot**

🔥 **Features:**
├ Intelligent anime name detection
├ Auto quality verification
├ Custom caption formats
├ Multi-channel support
├ Scheduled posts
└ Ultra-fast processing (<0.2s)

📚 **Commands:**
/help - Show all commands
/setcaption - Set your caption format
/addchannel - Add a channel
/channels - View your channels
/schedule - Schedule a video post

👨‍💻 **Developer:** @{support}
    """.format(support=SUPPORT_USERNAME)
    
    HELP_MESSAGE = """
📖 **Bot Commands Guide**

**🎨 Caption Management:**
/setcaption - Set custom caption format
/getcaption - View current caption
/resetcaption - Reset to default

**📺 Channel Management:**
/addchannel - Add new channel
/remchannel - Remove channel
/channels - List all channels
/setchannel - Set active channel

**⏰ Scheduling:**
/schedule - Schedule video post
/scheduled - View scheduled posts
/cancelschedule - Cancel scheduled post

**👤 User Management (Admin Only):**
/addadmin - Add new admin
/remadmin - Remove admin
/users - List all users
/stats - Bot statistics

**💡 Caption Variables:**
{a} = Anime Name
{s} = Season Number
{e} = Episode Number
{q} = Quality
[B] = Make text bold

**Example Caption:**
```
➥ {a} [{s}]
 Episode - {e}
 Quality : {q}
 [B]Powered by @World_Fastest_Bots
```

**Note:** Each user has their own caption format and channels!
    """
    
    # ==================== DEFAULT CAPTION ====================
    DEFAULT_CAPTION = """➥ {a} [{s}]
 Episode - {e}
 Language - Hindi #Official
 Quality : {q}
 [B]Powered by :
@World_Fastest_Bots."""
    
    # ==================== USER ROLES ====================
    class UserRoles:
        OWNER = "OWNER"
        ADMIN = "ADMIN"
        LOGIN_USER = "LOGIN_USER"
    
    # ==================== PERMISSIONS ====================
    PERMISSIONS = {
        UserRoles.OWNER: ["ALL"],
        UserRoles.ADMIN: ["caption", "setcaption", "addchannel", "remchannel", "schedule"],
        UserRoles.LOGIN_USER: ["caption", "setcaption", "addchannel", "remchannel"]
    }
    
    # ==================== VIDEO REGEX PATTERNS ====================
    VIDEO_PATTERNS = [
        # Pattern 1: [SubsPlease] Anime Name - S01E07 [720p]
        r'\[?([^\]]+)\]?\s*-?\s*S?(\d+)[xE](\d+)\s*\[?(\d+p)?\]?',
        
        # Pattern 2: Anime.Name.S01.E07.720p.WEB-DL
        r'([A-Za-z.\s]+?)\.S(\d+)\.E(\d+)\.(\d+p)',
        
        # Pattern 3: Anime Name - 01x07 - 720p
        r'([A-Za-z\s]+?)\s*-?\s*(\d+)x(\d+)\s*-?\s*(\d+p)?',
        
        # Pattern 4: [Group] Anime Name - 07 [1080p]
        r'\[([^\]]+)\]\s*([A-Za-z\s]+)\s*-\s*(\d+)\s*\[(\d+p)\]',
        
        # Pattern 5: Anime_Name_E07_720p
        r'([A-Za-z_]+)_E(\d+)_(\d+p)',
    ]
    
    # ==================== QUALITY MAPPING ====================
    QUALITY_RANGES = {
        (0, 480): "480p",
        (481, 720): "720p",
        (721, 1080): "1080p",
        (1081, 2160): "4K",
        (2161, 99999): "8K"
    }
    
    # ==================== SUPPORTED VIDEO FORMATS ====================
    SUPPORTED_FORMATS = ['.mp4', '.mkv', '.avi', '.webm', '.mov', '.flv', '.wmv']
    
    @classmethod
    def validate(cls) -> bool:
        """Validate essential configuration"""
        errors = []
        
        if cls.API_ID == 0:
            errors.append("API_ID is not set")
        if not cls.API_HASH:
            errors.append("API_HASH is not set")
        if not cls.BOT_TOKEN:
            errors.append("BOT_TOKEN is not set")
        if cls.OWNER_ID == 0:
            errors.append("OWNER_ID is not set")
        
        if errors:
            print("❌ Configuration Errors:")
            for error in errors:
                print(f"  - {error}")
            return False
        
        print("✅ Configuration validated successfully!")
        return True
    
    @classmethod
    def create_dirs(cls):
        """Create necessary directories"""
        cls.LOG_DIR.mkdir(exist_ok=True)
        cls.TEMP_DIR.mkdir(exist_ok=True)
        print("✅ Directories created successfully!")


# Create singleton instance
config = Config()

if __name__ == "__main__":
    # Test configuration
    if config.validate():
        config.create_dirs()
        print("\n✅ Configuration is ready!")
        print(f"📊 Bot: @{config.BOT_USERNAME}")
        print(f"👑 Owner ID: {config.OWNER_ID}")
        print(f"🗄️ Database: {config.DATABASE_NAME}")
        print(f"⚡ Max Processing Time: {config.MAX_PROCESSING_TIME}s")
    else:
        print("\n❌ Please fix configuration errors in .env file!")
