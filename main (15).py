"""
🎬 Advanced Auto Caption Bot - Main Application
Ultra-fast anime video captioning with AI verification
"""

import asyncio
import logging
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
import time

# Local imports
from config.settings import config
from database.mongodb import db, start_background_tasks
from utils.video_parser import video_parser, caption_formatter
from utils.anime_api import anime_api

# Setup logging
from loguru import logger as loguru_logger
import sys

# Remove default logger
loguru_logger.remove()

# Add custom format
loguru_logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> | <level>{message}</level>",
    level=config.LOG_LEVEL
)

if config.LOG_FILE_ENABLED:
    loguru_logger.add(
        config.LOG_DIR / f"bot_{datetime.now().strftime('%Y%m%d')}.log",
        rotation="1 day",
        retention="7 days",
        level=config.LOG_LEVEL
    )

logger = loguru_logger


# ==================== BOT INITIALIZATION ====================

app = Client(
    name="anime_caption_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
    workers=50,  # Handle multiple users concurrently
    sleep_threshold=60
)


# ==================== HELPER FUNCTIONS ====================

async def is_authorized(user_id: int) -> bool:
    """Check if user is authorized"""
    return await db.is_authorized(user_id)


async def check_permission(user_id: int, action: str) -> bool:
    """Check if user has permission for specific action"""
    role = await db.get_user_role(user_id)
    
    if not role:
        return False
    
    if role == config.UserRoles.OWNER:
        return True  # Owner has all permissions
    
    permissions = config.PERMISSIONS.get(role, [])
    return action in permissions or "ALL" in permissions


def create_channel_keyboard(channels: list) -> InlineKeyboardMarkup:
    """Create inline keyboard for channel selection"""
    buttons = []
    
    for channel in channels:
        buttons.append([
            InlineKeyboardButton(
                text=f"📺 {channel['channel_name']}",
                callback_data=f"select_channel:{channel['channel_id']}"
            )
        ])
    
    return InlineKeyboardMarkup(buttons)


# ==================== PERFORMANCE MONITOR ====================

class PerformanceMonitor:
    """Track bot performance"""
    
    def __init__(self):
        self.total_videos = 0
        self.total_time = 0.0
        self.slow_processes = 0
    
    def record(self, duration: float):
        """Record processing time"""
        self.total_videos += 1
        self.total_time += duration
        
        if duration > config.MAX_PROCESSING_TIME:
            self.slow_processes += 1
            logger.warning(f"⚠️ Slow processing: {duration:.3f}s")
    
    @property
    def avg_time(self) -> float:
        """Get average processing time"""
        return self.total_time / self.total_videos if self.total_videos > 0 else 0.0
    
    def get_stats(self) -> dict:
        """Get performance statistics"""
        return {
            "total_videos": self.total_videos,
            "avg_time": f"{self.avg_time:.3f}s",
            "slow_processes": self.slow_processes,
            "performance_score": f"{((self.total_videos - self.slow_processes) / max(self.total_videos, 1) * 100):.1f}%"
        }


monitor = PerformanceMonitor()


# ==================== COMMAND HANDLERS ====================

@app.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    """Handle /start command"""
    user_id = message.from_user.id
    
    if not await is_authorized(user_id):
        await message.reply(config.UNAUTHORIZED_MESSAGE)
        return
    
    await message.reply(
        config.START_MESSAGE,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📚 Help", callback_data="show_help")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="show_settings")],
            [InlineKeyboardButton("📊 Stats", callback_data="show_stats")]
        ])
    )
    
    logger.info(f"👤 User {user_id} started the bot")


@app.on_message(filters.command("help") & filters.private)
async def help_handler(client: Client, message: Message):
    """Handle /help command"""
    user_id = message.from_user.id
    
    if not await is_authorized(user_id):
        await message.reply(config.UNAUTHORIZED_MESSAGE)
        return
    
    await message.reply(config.HELP_MESSAGE)


@app.on_message(filters.command("login") & filters.private)
async def login_handler(client: Client, message: Message):
    """Handle /login command"""
    user_id = message.from_user.id
    
    # Extract password from command
    if len(message.command) < 2:
        await message.reply(
            "❌ **Usage:** `/login password`\n\n"
            "Please provide the login password."
        )
        return
    
    # Get password (can be multi-word)
    password = message.text.split(maxsplit=1)[1]
    
    # Validate password
    if password not in config.VALID_PASSWORDS:
        await message.reply("❌ **Invalid password!**")
        logger.warning(f"⚠️ Failed login attempt by {user_id}")
        return
    
    # Check if user already exists
    existing_user = await db.get_user(user_id)
    
    if existing_user:
        # Update login expiry
        await db.create_user(
            user_id,
            config.UserRoles.LOGIN_USER,
            message.from_user.username,
            message.from_user.first_name
        )
    else:
        # Create new login user
        success = await db.create_user(
            user_id,
            config.UserRoles.LOGIN_USER,
            message.from_user.username,
            message.from_user.first_name
        )
        
        if not success:
            await message.reply("❌ **Login failed!** Please try again.")
            return
    
    expiry_time = datetime.now() + timedelta(hours=config.LOGIN_EXPIRY_HOURS)
    
    await message.reply(
        f"✅ **Access granted for {config.LOGIN_EXPIRY_HOURS} hours!**\n\n"
        f"⏰ Expires: {expiry_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"Use /help to see available commands."
    )
    
    logger.info(f"✅ User {user_id} logged in successfully")


# ==================== CAPTION MANAGEMENT ====================

@app.on_message(filters.command("setcaption") & filters.private)
async def setcaption_handler(client: Client, message: Message):
    """Handle /setcaption command"""
    user_id = message.from_user.id
    
    if not await is_authorized(user_id):
        await message.reply(config.UNAUTHORIZED_MESSAGE)
        return
    
    if not await check_permission(user_id, "setcaption"):
        await message.reply("❌ You don't have permission to set captions!")
        return
    
    # Get caption format from message
    if len(message.text.split('\n', 1)) < 2:
        await message.reply(
            "❌ **Usage:**\n\n"
            "/setcaption\n"
            "Your caption format here\n\n"
            "**Variables:**\n"
            "`{a}` = Anime Name\n"
            "`{s}` = Season Number\n"
            "`{e}` = Episode Number\n"
            "`{q}` = Quality\n"
            "`[B]` = Make text bold\n\n"
            "**Example:**\n"
            "```\n➥ {a} [{s}]\n Episode - {e}\n Quality : {q}\n [B]Powered by Bot```"
        )
        return
    
    caption_format = message.text.split('\n', 1)[1]
    
    # Validate format
    is_valid, error_msg = caption_formatter.validate_format(caption_format)
    
    if not is_valid:
        await message.reply(f"❌ {error_msg}")
        return
    
    # Save caption format
    success = await db.set_caption(user_id, caption_format)
    
    if success:
        # Show preview
        sample_data = {
            "anime_name": "Naruto",
            "season": 1,
            "episode": 5,
            "quality": "1080p"
        }
        
        preview = caption_formatter.apply_caption(sample_data, caption_format)
        
        await message.reply(
            f"✅ **Caption format saved!**\n\n"
            f"**Preview:**\n{preview}"
        )
        logger.info(f"✅ User {user_id} set custom caption")
    else:
        await message.reply("❌ Failed to save caption format!")


@app.on_message(filters.command("getcaption") & filters.private)
async def getcaption_handler(client: Client, message: Message):
    """Handle /getcaption command"""
    user_id = message.from_user.id
    
    if not await is_authorized(user_id):
        await message.reply(config.UNAUTHORIZED_MESSAGE)
        return
    
    caption_format = await db.get_caption(user_id)
    
    await message.reply(
        f"**Your Current Caption Format:**\n\n"
        f"```\n{caption_format}```\n\n"
        f"Use /setcaption to change it."
    )


@app.on_message(filters.command("resetcaption") & filters.private)
async def resetcaption_handler(client: Client, message: Message):
    """Handle /resetcaption command"""
    user_id = message.from_user.id
    
    if not await is_authorized(user_id):
        await message.reply(config.UNAUTHORIZED_MESSAGE)
        return
    
    success = await db.set_caption(user_id, config.DEFAULT_CAPTION)
    
    if success:
        await message.reply(
            "✅ **Caption reset to default!**\n\n"
            f"```\n{config.DEFAULT_CAPTION}```"
        )
    else:
        await message.reply("❌ Failed to reset caption!")


# ==================== CHANNEL MANAGEMENT ====================

@app.on_message(filters.command("addchannel") & filters.private)
async def addchannel_handler(client: Client, message: Message):
    """Handle /addchannel command"""
    user_id = message.from_user.id
    
    if not await is_authorized(user_id):
        await message.reply(config.UNAUTHORIZED_MESSAGE)
        return
    
    if not await check_permission(user_id, "addchannel"):
        await message.reply("❌ You don't have permission to add channels!")
        return
    
    if len(message.command) < 2:
        await message.reply(
            "❌ **Usage:** `/addchannel -100xxxxxxxxxx`\n\n"
            "Get your channel ID from @username_to_id_bot\n\n"
            "**Note:** Make sure the bot is admin in your channel!"
        )
        return
    
    channel_id_str = message.command[1]
    
    # Validate channel ID format
    if not channel_id_str.startswith('-100'):
        await message.reply("❌ Invalid channel ID format! Must start with -100")
        return
    
    try:
        channel_id = int(channel_id_str)
    except ValueError:
        await message.reply("❌ Invalid channel ID!")
        return
    
    # Try to get channel info
    try:
        chat = await client.get_chat(channel_id)
        channel_name = chat.title
        
        # Check if bot is admin
        bot_member = await client.get_chat_member(channel_id, "me")
        if bot_member.status not in ["administrator", "creator"]:
            await message.reply(
                f"❌ I'm not an admin in **{channel_name}**!\n\n"
                "Please make me admin and try again."
            )
            return
        
    except Exception as e:
        await message.reply(
            f"❌ Could not access channel!\n\n"
            f"Error: {str(e)}\n\n"
            "Make sure:\n"
            "1. Channel ID is correct\n"
            "2. Bot is added as admin"
        )
        return
    
    # Add channel to database
    success = await db.add_channel(user_id, channel_id, channel_name)
    
    if success:
        await message.reply(
            f"✅ **Channel added successfully!**\n\n"
            f"📺 **Name:** {channel_name}\n"
            f"🆔 **ID:** `{channel_id}`\n\n"
            f"This channel is now active for video uploads!"
        )
        logger.info(f"✅ User {user_id} added channel {channel_id}")
    else:
        await message.reply("❌ Channel already exists or failed to add!")


@app.on_message(filters.command("channels") & filters.private)
async def channels_handler(client: Client, message: Message):
    """Handle /channels command"""
    user_id = message.from_user.id
    
    if not await is_authorized(user_id):
        await message.reply(config.UNAUTHORIZED_MESSAGE)
        return
    
    channels = await db.get_user_channels(user_id)
    active_channel = await db.get_active_channel(user_id)
    
    if not channels:
        await message.reply(
            "📺 **No channels added yet!**\n\n"
            "Use /addchannel to add a channel."
        )
        return
    
    text = "**📺 Your Channels:**\n\n"
    
    for channel in channels:
        is_active = "✅" if channel["channel_id"] == active_channel else "⭕"
        text += f"{is_active} **{channel['channel_name']}**\n"
        text += f"   🆔 `{channel['channel_id']}`\n"
        text += f"   📊 Posts: {channel['total_posts']}\n\n"
    
    text += "\n💡 Click a channel to set it as active:"
    
    await message.reply(
        text,
        reply_markup=create_channel_keyboard(channels)
    )


@app.on_message(filters.command("remchannel") & filters.private)
async def remchannel_handler(client: Client, message: Message):
    """Handle /remchannel command"""
    user_id = message.from_user.id
    
    if not await is_authorized(user_id):
        await message.reply(config.UNAUTHORIZED_MESSAGE)
        return
    
    if len(message.command) < 2:
        await message.reply("❌ **Usage:** `/remchannel -100xxxxxxxxxx`")
        return
    
    try:
        channel_id = int(message.command[1])
    except ValueError:
        await message.reply("❌ Invalid channel ID!")
        return
    
    success = await db.remove_channel(user_id, channel_id)
    
    if success:
        await message.reply("✅ **Channel removed successfully!**")
        logger.info(f"✅ User {user_id} removed channel {channel_id}")
    else:
        await message.reply("❌ Channel not found or failed to remove!")


# ==================== VIDEO PROCESSING ====================

@app.on_message((filters.video | filters.document) & filters.private)
async def video_handler(client: Client, message: Message):
    """Handle video uploads - Main caption processing"""
    user_id = message.from_user.id
    
    if not await is_authorized(user_id):
        await message.reply(config.UNAUTHORIZED_MESSAGE)
        return
    
    # Start performance timer
    start_time = time.time()
    
    # Progress message
    progress_msg = await message.reply("⚡ **Processing video...**")
    
    try:
        # Get video object
        video = message.video or message.document
        
        # Validate video format
        if message.document:
            file_ext = Path(video.file_name).suffix.lower()
            if file_ext not in config.SUPPORTED_FORMATS:
                await progress_msg.edit(f"❌ Unsupported format: {file_ext}")
                return
        
        # Extract metadata
        filename = video.file_name or "video"
        caption = message.caption or ""
        
        # Get active channel
        active_channel = await db.get_active_channel(user_id)
        
        if not active_channel:
            await progress_msg.edit(
                "❌ **No active channel!**\n\n"
                "Please add a channel using /addchannel"
            )
            return
        
        # Step 1: Extract anime info (0.01s)
        await progress_msg.edit("⚡ **Extracting anime info...**")
        video_data = await video_parser.extract_anime_info(filename, caption)
        
        # Step 2: Verify quality from video metadata (0.05s)
        await progress_msg.edit("⚡ **Verifying quality...**")
        if hasattr(video, 'height') and video.height:
            metadata = {"height": video.height, "width": video.width}
            actual_quality = await video_parser.verify_quality_from_metadata(metadata)
            
            if video_data.get("quality"):
                if video_data["quality"] != actual_quality:
                    logger.warning(f"Quality mismatch: {video_data['quality']} vs {actual_quality}")
            
            video_data["quality"] = actual_quality
        
        # Step 3: Verify anime name with APIs (0.15s)
        await progress_msg.edit("⚡ **Verifying anime name...**")
        verified = await anime_api.verify_anime_name(video_data["anime_name"])
        video_data["anime_name"] = verified["verified_name"]
        
        # Step 4: Get user's caption format (0.01s)
        caption_format = await db.get_caption(user_id)
        
        # Step 5: Apply caption (0.01s)
        final_caption = caption_formatter.apply_caption(video_data, caption_format)
        
        # Step 6: Send to channel (0.03s)
        await progress_msg.edit("⚡ **Sending to channel...**")
        
        sent_message = await message.copy(
            chat_id=active_channel,
            caption=final_caption
        )
        
        # Step 7: Update statistics
        await db.increment_channel_posts(active_channel)
        await db.increment_user_videos(user_id)
        
        # Calculate processing time
        elapsed = time.time() - start_time
        monitor.record(elapsed)
        
        # Delete original message
        await message.delete()
        
        # Success message
        await progress_msg.edit(
            f"✅ **Video sent successfully!**\n\n"
            f"📺 **Channel:** Active Channel\n"
            f"🎬 **Anime:** {video_data['anime_name']}\n"
            f"📊 **S{video_data['season']:02d}E{video_data['episode']:02d}**\n"
            f"🎯 **Quality:** {video_data['quality']}\n"
            f"⏱️ **Processed in:** {elapsed:.2f}s\n"
            f"🔗 **Message ID:** {sent_message.id}"
        )
        
        logger.info(f"✅ Video processed in {elapsed:.2f}s for user {user_id}")
        
    except FloodWait as e:
        await progress_msg.edit(f"⚠️ Flood wait: Please wait {e.x} seconds")
        await asyncio.sleep(e.x)
    except Exception as e:
        logger.error(f"❌ Video processing error: {e}")
        await progress_msg.edit(
            f"❌ **Processing failed!**\n\n"
            f"Error: {str(e)}\n\n"
            f"Please check:\n"
            f"• Video format is supported\n"
            f"• Filename contains anime info\n"
            f"• Bot has channel permissions"
        )


# ==================== SCHEDULING ====================

@app.on_message(filters.command("schedule") & filters.private)
async def schedule_handler(client: Client, message: Message):
    """Handle /schedule command"""
    user_id = message.from_user.id
    
    if not await is_authorized(user_id):
        await message.reply(config.UNAUTHORIZED_MESSAGE)
        return
    
    await message.reply(
        "📅 **Schedule Video Post**\n\n"
        "**Usage:**\n"
        "1. Send me a video\n"
        "2. I'll process it\n"
        "3. Reply with time: `/schedule 2024-12-25 18:00`\n\n"
        "**Format:** `YYYY-MM-DD HH:MM`"
    )


@app.on_message(filters.command("scheduled") & filters.private)
async def scheduled_handler(client: Client, message: Message):
    """Handle /scheduled command - Show scheduled posts"""
    user_id = message.from_user.id
    
    if not await is_authorized(user_id):
        await message.reply(config.UNAUTHORIZED_MESSAGE)
        return
    
    scheduled = await db.get_user_scheduled_posts(user_id)
    
    if not scheduled:
        await message.reply("📅 **No scheduled posts!**")
        return
    
    text = "**📅 Your Scheduled Posts:**\n\n"
    
    for post in scheduled:
        text += f"🆔 ID: `{post['_id']}`\n"
        text += f"⏰ Time: {post['scheduled_time'].strftime('%Y-%m-%d %H:%M')}\n"
        text += f"📺 Channel: {post['channel_id']}\n\n"
    
    text += "\n💡 Use `/cancelschedule <id>` to cancel"
    
    await message.reply(text)


# ==================== ADMIN COMMANDS ====================

@app.on_message(filters.command("addadmin") & filters.private)
async def addadmin_handler(client: Client, message: Message):
    """Handle /addadmin command - Owner only"""
    user_id = message.from_user.id
    
    if user_id != config.OWNER_ID:
        await message.reply("❌ Only owner can add admins!")
        return
    
    if len(message.command) < 2:
        await message.reply("❌ **Usage:** `/addadmin user_id`")
        return
    
    try:
        new_admin_id = int(message.command[1])
    except ValueError:
        await message.reply("❌ Invalid user ID!")
        return
    
    # Check if user exists
    user = await db.get_user(new_admin_id)
    
    if user:
        # Update role
        success = await db.update_user_role(new_admin_id, config.UserRoles.ADMIN)
    else:
        # Create new admin
        success = await db.create_user(new_admin_id, config.UserRoles.ADMIN)
    
    if success:
        await message.reply(f"✅ User {new_admin_id} is now an admin!")
        logger.info(f"✅ Owner added admin: {new_admin_id}")
    else:
        await message.reply("❌ Failed to add admin!")


@app.on_message(filters.command("remadmin") & filters.private)
async def remadmin_handler(client: Client, message: Message):
    """Handle /remadmin command - Owner only"""
    user_id = message.from_user.id
    
    if user_id != config.OWNER_ID:
        await message.reply("❌ Only owner can remove admins!")
        return
    
    if len(message.command) < 2:
        await message.reply("❌ **Usage:** `/remadmin user_id`")
        return
    
    try:
        admin_id = int(message.command[1])
    except ValueError:
        await message.reply("❌ Invalid user ID!")
        return
    
    success = await db.update_user_role(admin_id, config.UserRoles.LOGIN_USER)
    
    if success:
        await message.reply(f"✅ Admin {admin_id} removed!")
        logger.info(f"✅ Owner removed admin: {admin_id}")
    else:
        await message.reply("❌ Failed to remove admin!")


@app.on_message(filters.command("stats") & filters.private)
async def stats_handler(client: Client, message: Message):
    """Handle /stats command"""
    user_id = message.from_user.id
    
    if not await is_authorized(user_id):
        await message.reply(config.UNAUTHORIZED_MESSAGE)
        return
    
    # Get bot stats
    bot_stats = await db.get_bot_stats()
    perf_stats = monitor.get_stats()
    user_counts = await db.get_all_users_count()
    
    stats_text = f"""
📊 **Bot Statistics**

**👥 Users:**
├ Total: {bot_stats['total_users']}
├ Admins: {user_counts.get('ADMIN', 0)}
└ Login Users: {user_counts.get('LOGIN_USER', 0)}

**📺 Channels:**
└ Total: {bot_stats['total_channels']}

**🎬 Videos:**
├ Total Processed: {bot_stats['total_videos']}
└ Scheduled: {bot_stats['total_scheduled']}

**⚡ Performance:**
├ Avg Time: {perf_stats['avg_time']}
├ Total Videos: {perf_stats['total_videos']}
├ Slow Processes: {perf_stats['slow_processes']}
└ Score: {perf_stats['performance_score']}

**🤖 Bot Info:**
└ Version: 4.5 Advanced
    """
    
    await message.reply(stats_text)


# ==================== CALLBACK QUERY HANDLERS ====================

@app.on_callback_query()
async def callback_handler(client: Client, callback_query):
    """Handle callback queries"""
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    if not await is_authorized(user_id):
        await callback_query.answer("❌ Not authorized!", show_alert=True)
        return
    
    if data == "show_help":
        await callback_query.message.edit(config.HELP_MESSAGE)
    
    elif data == "show_stats":
        bot_stats = await db.get_bot_stats()
        perf_stats = monitor.get_stats()
        
        stats_text = f"""
📊 **Quick Stats**

🎬 Videos: {bot_stats['total_videos']}
⏱️ Avg Time: {perf_stats['avg_time']}
📺 Channels: {bot_stats['total_channels']}
        """
        await callback_query.answer(stats_text, show_alert=True)
    
    elif data == "show_settings":
        await callback_query.message.edit(
            "⚙️ **Settings**\n\n"
            "Available commands:\n"
            "/setcaption - Set caption format\n"
            "/addchannel - Add channel\n"
            "/channels - Manage channels",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Back", callback_data="back_to_start")
            ]])
        )
    
    elif data == "back_to_start":
        await callback_query.message.edit(
            config.START_MESSAGE,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📚 Help", callback_data="show_help")],
                [InlineKeyboardButton("⚙️ Settings", callback_data="show_settings")],
                [InlineKeyboardButton("📊 Stats", callback_data="show_stats")]
            ])
        )
    
    elif data.startswith("select_channel:"):
        channel_id = int(data.split(":")[1])
        success = await db.set_active_channel(user_id, channel_id)
        
        if success:
            await callback_query.answer("✅ Channel activated!", show_alert=True)
            await channels_handler(client, callback_query.message)
        else:
            await callback_query.answer("❌ Failed to set channel!", show_alert=True)


# ==================== SCHEDULED POSTS PROCESSOR ====================

async def process_scheduled_posts():
    """Background task to send scheduled posts"""
    while True:
        try:
            # Get pending posts
            pending = await db.get_pending_posts()
            
            for post in pending:
                try:
                    # Send video to channel
                    await app.copy_message(
                        chat_id=post['channel_id'],
                        from_chat_id=post['user_id'],
                        message_id=post['video_file_id'],
                        caption=post['caption']
                    )
                    
                    # Mark as sent
                    await db.mark_post_sent(str(post['_id']))
                    
                    logger.info(f"✅ Scheduled post sent: {post['_id']}")
                    
                except Exception as e:
                    logger.error(f"❌ Scheduled post failed: {e}")
            
            # Check every minute
            await asyncio.sleep(60)
            
        except Exception as e:
            logger.error(f"❌ Scheduled processor error: {e}")
            await asyncio.sleep(60)


# ==================== BOT STARTUP & SHUTDOWN ====================

async def startup():
    """Run on bot startup"""
    logger.info("🚀 Starting Advanced Auto Caption Bot...")
    
    # Validate configuration
    if not config.validate():
        logger.error("❌ Configuration validation failed!")
        return False
    
    # Create directories
    config.create_dirs()
    
    # Connect to database
    connected = await db.connect()
    if not connected:
        logger.error("❌ Database connection failed!")
        return False
    
    # Initialize API client
    await anime_api.create_session()
    
    # Start background tasks
    await start_background_tasks()
    
    # Start scheduled posts processor
    asyncio.create_task(process_scheduled_posts())
    
    logger.success("✅ Bot started successfully!")
    logger.info(f"📊 Bot: @{config.BOT_USERNAME}")
    logger.info(f"👑 Owner: {config.OWNER_ID}")
    
    return True


async def shutdown():
    """Run on bot shutdown"""
    logger.info("🛑 Shutting down bot...")
    
    # Close database connection
    await db.close()
    
    # Close API session
    await anime_api.close_session()
    
    logger.info("✅ Bot shutdown complete!")


# ==================== MAIN ====================

async def main():
    """Main function"""
    # Startup
    if not await startup():
        logger.error("❌ Bot startup failed!")
        return
    
    try:
        # Start bot
        await app.start()
        logger.success(f"🤖 Bot is running as @{config.BOT_USERNAME}")
        
        # Keep alive
        await asyncio.Event().wait()
        
    except KeyboardInterrupt:
        logger.info("⚠️ Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")
    finally:
        # Shutdown
        await shutdown()
        await app.stop()


if __name__ == "__main__":
    # Run bot
    asyncio.run(main())
