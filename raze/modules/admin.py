"""
Admin & Group Management Module - RazeChan Bot
/set UI customizer, /all mention, group management
"""
import asyncio
import random
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from raze import app, ui_col, db, OWNER_ID, DB_CHANNEL_ID

# ── /set System (Admin UI Customizer) ────────────────────────────────────────
listening_for: dict = {}  # admin_id -> command_name

SETTABLE_COMMANDS = ["start", "help", "games", "aura", "leaderboard", "utility"]

@app.on_message(filters.command("set") & filters.user(OWNER_ID))
async def set_cmd(_, msg: Message):
    parts = msg.command
    if len(parts) < 2 or parts[1].lower() not in SETTABLE_COMMANDS:
        cmds_list = ", ".join(f"`/{c}`" for c in SETTABLE_COMMANDS)
        return await msg.reply(
            f"⚙️ **UI Customizer**\n\n"
            f"Usage: `/set [command]`\n"
            f"Available: {cmds_list}\n\n"
            f"_After sending this, send a Photo + Caption to set the banner._"
        )

    cmd_name = parts[1].lower()
    listening_for[msg.from_user.id] = cmd_name
    await msg.reply(
        f"👂 **Listening Mode ON** — `/{cmd_name}`\n\n"
        f"Ab ek **Photo + Caption** bhejo jo is command ka banner banega~\n"
        f"_Cancel karne ke liye /cancelset bhejo_"
    )

@app.on_message(filters.command("cancelset") & filters.user(OWNER_ID))
async def cancel_set(_, msg: Message):
    if msg.from_user.id in listening_for:
        del listening_for[msg.from_user.id]
        await msg.reply("✅ Set mode cancelled~")
    else:
        await msg.reply("Koi active set mode nahi tha!")

@app.on_message(filters.photo & filters.user(OWNER_ID))
async def capture_banner(_, msg: Message):
    admin_id = msg.from_user.id
    if admin_id not in listening_for:
        return

    cmd_name = listening_for.pop(admin_id)
    caption  = msg.caption or f"Welcome to /{cmd_name}~"

    # Forward to DB channel for storage
    try:
        forwarded = await msg.forward(DB_CHANNEL_ID)
        file_id   = msg.photo.file_id

        await ui_col.update_one(
            {"command": cmd_name},
            {"$set": {
                "command":  cmd_name,
                "file_id":  file_id,
                "caption":  caption,
                "msg_id":   forwarded.id if forwarded else None
            }},
            upsert=True
        )
        await msg.reply(
            f"✅ **/{cmd_name}** ka banner save ho gaya!\n\n"
            f"Caption: `{caption[:80]}...`" if len(caption) > 80 else
            f"✅ **/{cmd_name}** ka banner save ho gaya!\n\nCaption: `{caption}`"
        )
    except Exception as e:
        await msg.reply(f"❌ Error saving banner: `{e}`")

async def get_ui(command: str) -> dict | None:
    return await ui_col.find_one({"command": command})

# ── /start Dashboard ──────────────────────────────────────────────────────────
@app.on_message(filters.command("start"))
async def start_cmd(_, msg: Message):
    user   = msg.from_user
    name   = user.first_name
    ui     = await get_ui("start")

    from raze.modules.aura import get_aura, get_realm
    aura_data = await get_aura(user.id, msg.chat.id)
    realm     = get_realm(aura_data["points"])

    welcome = (
        f"**Heyyy {name}~** 👋\n\n"
        f"Main **Raze Chan** hoon! 💁‍♀️\n"
        f"Tumhari Aura: `{aura_data['points']:,}` ✨ | {realm['name']}\n\n"
        f"_Kya karna hai aaj?_ 👇"
    )
    caption = ui["caption"] if ui else welcome

    btns = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ Core",       callback_data="info:core"),
         InlineKeyboardButton("✨ Aura",       callback_data="aura_panel"),
         InlineKeyboardButton("🎮 Games",      callback_data="games_panel")],
        [InlineKeyboardButton("🛠️ Utility",    callback_data="info:utility"),
         InlineKeyboardButton("👤 Identity",   callback_data="info:identity"),
         InlineKeyboardButton("📝 Notes",      callback_data="info:notes")],
        [InlineKeyboardButton("💰 Economy",    callback_data="info:economy"),
         InlineKeyboardButton("♻️ Cycles",     callback_data="info:cycles"),
         InlineKeyboardButton("❓ Help Index", callback_data="help_index")],
        [InlineKeyboardButton("🛡️ Admin & Safety", callback_data="info:admin"),
         InlineKeyboardButton("🏆 Aura Board", callback_data="aura_leaderboard")],
        [InlineKeyboardButton("💙 Support",    url="https://t.me/razechanbot"),
         InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{(await app.get_me()).username}?startgroup=true")]
    ])

    if ui and ui.get("file_id"):
        await msg.reply_photo(ui["file_id"], caption=caption, reply_markup=btns)
    else:
        await msg.reply(caption, reply_markup=btns)

# ── /help Command ─────────────────────────────────────────────────────────────
@app.on_message(filters.command("help"))
async def help_cmd(_, msg: Message):
    ui = await get_ui("help")
    text = (
        "📖 **Raze Chan — Command Guide**\n\n"
        "**💬 Chat:**\n"
        "  • Mention me, reply me, ya naam lo → main reply karungi~\n\n"
        "**✨ Aura System:**\n"
        "  `/aura` — apni aura stats dekho\n"
        "  `/give [amount]` — kisi ko aura do (reply)\n"
        "  `/steal [amount]` — kisi se aura lo (reply)\n"
        "  `/leaderboard` — top aura holders\n\n"
        "**🎮 Games:**\n"
        "  `/games` — game zone kholne ke liye\n"
        "  `/ttt` — Tic-Tac-Toe vs Raze\n"
        "  `/minesweeper` — 5×5 mine clear karo\n"
        "  `/rps` — Rock Paper Scissors\n"
        "  `/wordguess` — word guess game\n\n"
        "**👥 Group:**\n"
        "  `/all` — sabko mention karo\n\n"
        "**⚙️ Admin:**\n"
        "  `/set [cmd]` — UI banner customize karo\n\n"
        "_Bot ko mention karo, reply karo, ya naam lo — main hamesha sunti hoon~_ 👂"
    )
    btns = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Back to Start", callback_data="start_home")]])

    if ui and ui.get("file_id"):
        await msg.reply_photo(ui["file_id"], caption=ui["caption"] or text, reply_markup=btns)
    else:
        await msg.reply(text, reply_markup=btns)

# ── /all Mention (Smart Anti-Flood) ──────────────────────────────────────────
RANDOM_MENTIONS = [
    "Kahan ho sab? 👀",
    "Uth jao yaar, group mein aao~ 😤",
    "Suno toh ek minute! 📢",
    "Reply do warna block 😂 jk jk~",
    "Aree exam kaise gaye? 📝",
    "Koi hai? Main akeli nahi hona chahti 🥺",
    "Active ho jao toh~ 💤",
    "Dekho dekho main hoon 😏",
    "Koi online? Baat karni hai~ 💬",
    "Uthoooo pagalo! 🌅",
]

@app.on_message(filters.command("all") & filters.group)
async def mention_all(_, msg: Message):
    chat = msg.chat
    members = []
    async for member in app.get_chat_members(chat.id):
        if not member.user.is_bot and not member.user.is_deleted:
            members.append(member.user)
        if len(members) >= 50:  # cap at 50
            break

    if not members:
        return await msg.reply("Koi nahi mila mention karne ke liye~ 😅")

    batch = []
    count = 0
    for user in members:
        mention = f"[{user.first_name}](tg://user?id={user.id})"
        batch.append(mention)
        count += 1
        if count % 5 == 0:
            text = random.choice(RANDOM_MENTIONS) + "\n\n" + " ".join(batch)
            await msg.reply(text, disable_notification=False)
            batch = []
            await asyncio.sleep(1.5)  # anti-flood

    if batch:
        text = random.choice(RANDOM_MENTIONS) + "\n\n" + " ".join(batch)
        await msg.reply(text)

# ── Callback Handlers for Dashboard buttons ───────────────────────────────────
from pyrogram.types import CallbackQuery

@app.on_callback_query(filters.regex("^start_home$"))
async def back_to_start(_, cb: CallbackQuery):
    await cb.answer()
    # Re-trigger start
    cb.message.from_user = cb.from_user
    await start_cmd(_, cb.message)

@app.on_callback_query(filters.regex("^games_panel$"))
async def games_panel_cb(_, cb: CallbackQuery):
    await cb.answer()
    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    btns = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Tic-Tac-Toe",  callback_data="launch:ttt"),
         InlineKeyboardButton("💣 Minesweeper",  callback_data="launch:mine")],
        [InlineKeyboardButton("✂️ RPS",           callback_data="launch:rps"),
         InlineKeyboardButton("🔤 Word Guess",    callback_data="launch:wordguess")],
        [InlineKeyboardButton("🏆 Records",       callback_data="games_lb")],
        [InlineKeyboardButton("🏠 Back",          callback_data="start_home")]
    ])
    await cb.message.reply("🎮 **Game Zone** — choose karo~", reply_markup=btns)

@app.on_callback_query(filters.regex("^aura_panel$"))
async def aura_panel_cb(_, cb: CallbackQuery):
    await cb.answer()
    from raze.modules.aura import get_aura, get_realm
    data  = await get_aura(cb.from_user.id, cb.message.chat.id)
    realm = get_realm(data["points"])
    btns = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏆 Leaderboard",  callback_data="aura_leaderboard"),
         InlineKeyboardButton("ℹ️ Realms Info",  callback_data="realms_info")],
        [InlineKeyboardButton("🏠 Back",          callback_data="start_home")]
    ])
    await cb.message.reply(
        f"✨ **{cb.from_user.first_name} ki Aura**\n\n"
        f"Realm: {realm['name']}\nPoints: `{data['points']:,}`\n"
        f"Give left: `{realm['give'] - data['given_today']}`\n"
        f"Steal left: `{realm['steal'] - data['stolen_today']}`",
        reply_markup=btns
    )

@app.on_callback_query(filters.regex("^realms_info$"))
async def realms_info_cb(_, cb: CallbackQuery):
    await cb.answer()
    from raze.modules.aura import REALMS
    text = "🌐 **Realm System**\n\n"
    for r in REALMS:
        text += f"{r['name']} — `{r['min']:,}–{r['max']:,}` pts\n  Give: {r['give']} | Steal: {r['steal']}\n\n"
    await cb.message.reply(text)

@app.on_callback_query(filters.regex("^info:"))
async def info_panel(_, cb: CallbackQuery):
    await cb.answer()
    section = cb.data.split(":")[1]
    info_map = {
        "core":     "⚡ **Core Features**\n\nAI Chat, Voice Notes, Sticker Learning, Memory System",
        "utility":  "🛠️ **Utility**\n\nIncoming: Weather, Quotes, Calculator, Translate~",
        "identity": "👤 **Identity**\n\nRaze Chan — 20 saal, Gujarat, MBBS aspirant 📚",
        "notes":    "📝 **Notes**\n\nIncoming: Personal notes feature~",
        "economy":  "💰 **Economy**\n\nAura System — earn, give, steal points. Realms unlock perks!",
        "cycles":   "♻️ **Cycles**\n\nDaily aura resets at midnight. Stay active to climb realms~",
        "admin":    "🛡️ **Admin**\n\n`/set` — UI customize\n`/all` — mention everyone\nOwner-only features enabled",
    }
    text = info_map.get(section, "Coming soon~")
    btns = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Back", callback_data="start_home")]])
    await cb.message.reply(text, reply_markup=btns)

@app.on_callback_query(filters.regex("^help_index$"))
async def help_index_cb(_, cb: CallbackQuery):
    await cb.answer()
    cb.message.from_user = cb.from_user
    await help_cmd(_, cb.message)
