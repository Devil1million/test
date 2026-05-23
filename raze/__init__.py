"""
RazeChan Bot - AI Girl Telegram Bot
"""
import os
from pyrogram import Client
from motor.motor_asyncio import AsyncIOMotorClient

# ── Secrets (set these as environment variables) ──────────────────────────────
API_ID          = int(os.environ.get("API_ID", 0))
API_HASH        = os.environ.get("API_HASH", "")
BOT_TOKEN       = os.environ.get("BOT_TOKEN", "")
MONGO_URI       = os.environ.get("MONGO_URI", "")
OWNER_ID        = int(os.environ.get("OWNER_ID", 0))
DB_CHANNEL_ID   = int(os.environ.get("DB_CHANNEL_ID", 0))
GROQ_API_KEY    = os.environ.get("GROQ_API_KEY", "")
ELEVENLABS_KEY  = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE= os.environ.get("VOICE_ID", "")
GAMES_ENABLED   = os.environ.get("GAMES_ENABLED", "True") == "True"

# ── MongoDB ───────────────────────────────────────────────────────────────────
mongo_client = AsyncIOMotorClient(MONGO_URI)
db           = mongo_client["razechan"]

users_col    = db["users"]        # user profiles & context memory
aura_col     = db["aura"]         # aura points & realm data
games_col    = db["game_stats"]   # world records
ui_col       = db["ui_config"]    # /set banners & captions
stickers_col = db["stickers"]     # learned sticker mappings

# ── Pyrogram Client ───────────────────────────────────────────────────────────
app = Client(
    "razechan",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins={"root": "raze/modules"},
)
