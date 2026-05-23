"""
Aura (Social Credit) System - RazeChan Bot
"""
from datetime import datetime, date
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from raze import app, aura_col, OWNER_ID

# ── Realm Definitions ─────────────────────────────────────────────────────────
REALMS = [
    {"name": "👤 Mortal",    "min": 0,     "max": 999,   "give": 700,  "steal": 600},
    {"name": "⚔️ Warrior",   "min": 1000,  "max": 2999,  "give": 1200, "steal": 1000},
    {"name": "🌿 Sage",      "min": 3000,  "max": 5999,  "give": 1800, "steal": 1500},
    {"name": "🔥 Legend",    "min": 6000,  "max": 9999,  "give": 2500, "steal": 2000},
    {"name": "💎 Immortal",  "min": 10000, "max": 19999, "give": 3500, "steal": 2800},
    {"name": "👑 Divine",    "min": 20000, "max": 999999,"give": 5000, "steal": 4000},
]

def get_realm(points: int) -> dict:
    for r in REALMS:
        if r["min"] <= points <= r["max"]:
            return r
    return REALMS[-1]

async def get_aura(user_id: int, chat_id: int) -> dict:
    doc = await aura_col.find_one({"user_id": user_id, "chat_id": chat_id})
    if not doc:
        doc = {
            "user_id": user_id, "chat_id": chat_id,
            "points": 0, "given_today": 0, "stolen_today": 0,
            "last_reset": str(date.today())
        }
        await aura_col.insert_one(doc)
    # daily reset
    if doc.get("last_reset") != str(date.today()):
        await aura_col.update_one(
            {"user_id": user_id, "chat_id": chat_id},
            {"$set": {"given_today": 0, "stolen_today": 0, "last_reset": str(date.today())}}
        )
        doc["given_today"] = 0
        doc["stolen_today"] = 0
    return doc

async def update_aura(user_id: int, chat_id: int, delta: int):
    await get_aura(user_id, chat_id)
    await aura_col.update_one(
        {"user_id": user_id, "chat_id": chat_id},
        {"$inc": {"points": delta}}
    )

# ── /aura command ─────────────────────────────────────────────────────────────
@app.on_message(filters.command("aura"))
async def aura_cmd(_, msg: Message):
    user = msg.from_user
    data = await get_aura(user.id, msg.chat.id)
    pts   = data["points"]
    realm = get_realm(pts)

    text = (
        f"✨ **{user.first_name} ki Aura Report**\n\n"
        f"🌐 Realm : **{realm['name']}**\n"
        f"💫 Points : **{pts:,}**\n\n"
        f"📤 Give Limit  : `{realm['give'] - data['given_today']} remaining`\n"
        f"🗡️ Steal Limit : `{realm['steal'] - data['stolen_today']} remaining`\n\n"
        f"_Daily limits reset at midnight_ 🌙"
    )
    btns = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏆 Global Rankings", callback_data="aura_leaderboard"),
         InlineKeyboardButton("🎁 Give Aura", callback_data="aura_give_info")],
        [InlineKeyboardButton("🏠 Back to Start", callback_data="start_home")]
    ])
    await msg.reply(text, reply_markup=btns)

# ── /give command ─────────────────────────────────────────────────────────────
@app.on_message(filters.command("give") & filters.reply)
async def give_aura(_, msg: Message):
    giver = msg.from_user
    target = msg.reply_to_message.from_user
    if not target or target.is_bot:
        return await msg.reply("❌ Bots ko aura nahi dete bestie 😂")
    if giver.id == target.id:
        return await msg.reply("💀 Khud ko aura? Self-love toh acha hai par ye nahi chalta~")

    try:
        amount = int(msg.command[1]) if len(msg.command) > 1 else 100
    except ValueError:
        return await msg.reply("❌ Valid number do yaar~")

    giver_data = await get_aura(giver.id, msg.chat.id)
    realm      = get_realm(giver_data["points"])
    remaining  = realm["give"] - giver_data["given_today"]

    if amount > remaining:
        return await msg.reply(f"💔 Aaj ke liye sirf **{remaining}** aura de sakte ho! Kal phir aana~")
    if amount <= 0:
        return await msg.reply("❌ Positive number chahiye bestie 🙄")

    await update_aura(target.id, msg.chat.id, amount)
    await aura_col.update_one(
        {"user_id": giver.id, "chat_id": msg.chat.id},
        {"$inc": {"given_today": amount}}
    )
    await msg.reply(
        f"💝 **{giver.first_name}** ne **{target.first_name}** ko "
        f"**{amount}** Aura gift kiya! So sweet~ 🥺✨"
    )

# ── /steal command ────────────────────────────────────────────────────────────
@app.on_message(filters.command("steal") & filters.reply)
async def steal_aura(_, msg: Message):
    thief  = msg.from_user
    victim = msg.reply_to_message.from_user
    if not victim or victim.is_bot:
        return await msg.reply("❌ Bot se steal? Boring~ 😴")
    if thief.id == victim.id:
        return await msg.reply("💀 Khud se steal? Bhai... sab theek hai? 😭")

    try:
        amount = int(msg.command[1]) if len(msg.command) > 1 else 50
    except ValueError:
        return await msg.reply("❌ Number sahi se likho~")

    thief_data  = await get_aura(thief.id, msg.chat.id)
    victim_data = await get_aura(victim.id, msg.chat.id)
    realm       = get_realm(thief_data["points"])
    remaining   = realm["steal"] - thief_data["stolen_today"]

    if amount > remaining:
        return await msg.reply(f"🚫 Aaj sirf **{remaining}** aura steal kar sakte ho! Thoda ruko~")
    if victim_data["points"] < amount:
        return await msg.reply(f"💸 {victim.first_name} ke paas itna aura hi nahi hai 😅")

    await update_aura(victim.id, msg.chat.id, -amount)
    await update_aura(thief.id,  msg.chat.id,  amount)
    await aura_col.update_one(
        {"user_id": thief.id, "chat_id": msg.chat.id},
        {"$inc": {"stolen_today": amount}}
    )
    await msg.reply(
        f"🗡️ **{thief.first_name}** ne **{victim.first_name}** se "
        f"**{amount}** Aura chura liya! Savage~ 😈✨"
    )

# ── /leaderboard ──────────────────────────────────────────────────────────────
@app.on_message(filters.command("leaderboard"))
async def leaderboard(_, msg: Message):
    top = await aura_col.find(
        {"chat_id": msg.chat.id}
    ).sort("points", -1).limit(10).to_list(10)

    if not top:
        return await msg.reply("📊 Abhi koi data nahi hai! Pehle /aura chalao~")

    text = "🏆 **Aura Leaderboard** 🏆\n\n"
    medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    for i, entry in enumerate(top):
        realm = get_realm(entry["points"])
        try:
            user = await app.get_users(entry["user_id"])
            name = user.first_name
        except Exception:
            name = f"User#{entry['user_id']}"
        text += f"{medals[i]} **{name}** — `{entry['points']:,}` pts | {realm['name']}\n"

    await msg.reply(text)

# ── Callback: aura leaderboard button ────────────────────────────────────────
@app.on_callback_query(filters.regex("^aura_leaderboard$"))
async def aura_lb_cb(_, cb: CallbackQuery):
    await cb.answer()
    top = await aura_col.find(
        {"chat_id": cb.message.chat.id}
    ).sort("points", -1).limit(10).to_list(10)
    if not top:
        return await cb.message.reply("📊 Abhi koi data nahi~")
    text = "🏆 **Global Aura Rankings**\n\n"
    medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    for i, entry in enumerate(top):
        realm = get_realm(entry["points"])
        try:
            user = await app.get_users(entry["user_id"])
            name = user.first_name
        except Exception:
            name = f"User#{entry['user_id']}"
        text += f"{medals[i]} **{name}** — `{entry['points']:,}` | {realm['name']}\n"
    await cb.message.reply(text)
