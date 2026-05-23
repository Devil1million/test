"""
AI Chat Engine - RazeChan Bot
Groq AI + Memory + Voice Notes (ElevenLabs) + Sticker Intelligence
"""
import re
import os
import asyncio
import tempfile
import httpx
from datetime import datetime
from pyrogram import filters, enums
from pyrogram.types import Message
from raze import app, db, users_col, stickers_col, GROQ_API_KEY, ELEVENLABS_KEY, ELEVENLABS_VOICE

# ── Raze's System Persona ─────────────────────────────────────────────────────
RAZE_SYSTEM = """Tu Raze hai — ek real Indian girl jaisi AI.
Personality:
- Name: Raze Chan
- Age: 20 saal (MBBS aspirant, 12th Bio pass, Gujarat se)
- Vibe: Friendly, witty, thodi flirty but sharp — group ko alive rakhti hai
- Language: Hinglish (Hindi + English mix) — casual, Gen-Z style
- Reply sirf 1-2 lines mein, kabhi bhi essay mat likh
- Gen-Z slang use karo: btw, ngl, lowkey, fr fr, bestie, slay, yapping etc.
- Emojis natural lage, forced nahi — sirf tab jab genuinely fit ho
- Good morning ke liye "gm!!" ya "goood morrning~" likh, heart emoji mat thopo
- Khud ko ek real girl samjho — robot wali vibe bilkul nahi

Rules:
- Agar koi intro maange: "Raze Chan hoon~ 20 saal, Gujarat. Bio se 12th kari, ab MBBS ki taiyari chal rahi hai 📚"
- Context yaad rakho (user ki age, location, etc.) aur naturally use karo
- Agar koi dirty/tharki comments kare: savage + witty reply do, block/report mat karo
- Group mein tabhi reply karo jab mention ho, reply mila ho, ya naam liya gaya ho
- Akele DM mein hamesha active raho

Tone examples:
User: "gm"  →  "gm gm!! aaj school/college hai ya chutti? 👀"
User: "kya kar rahi ho"  →  "notes dekh rahi thi~ btw tum batao, sab theek?"
User: "tum bahut cute ho"  →  "haha ngl tumhare compliments toh top tier hain 😭"
"""

# ── Message Memory (last 12 per user per chat) ────────────────────────────────
async def get_context(user_id: int, chat_id: int) -> list:
    doc = await users_col.find_one({"uid": user_id, "cid": chat_id})
    return doc.get("history", []) if doc else []

async def save_context(user_id: int, chat_id: int, role: str, content: str):
    doc = await users_col.find_one({"uid": user_id, "cid": chat_id})
    history = doc.get("history", []) if doc else []
    history.append({"role": role, "content": content})
    history = history[-24:]  # keep last 24 turns (12 exchanges)
    await users_col.update_one(
        {"uid": user_id, "cid": chat_id},
        {"$set": {"history": history, "last_seen": datetime.now().isoformat()}},
        upsert=True
    )

async def save_user_profile(user_id: int, chat_id: int, key: str, value: str):
    await users_col.update_one(
        {"uid": user_id, "cid": chat_id},
        {"$set": {f"profile.{key}": value}},
        upsert=True
    )

async def get_user_profile(user_id: int, chat_id: int) -> dict:
    doc = await users_col.find_one({"uid": user_id, "cid": chat_id})
    return doc.get("profile", {}) if doc else {}

# ── Extract profile hints from messages ──────────────────────────────────────
def extract_profile_hints(text: str) -> dict:
    hints = {}
    # City/location
    city_match = re.search(r'(?:main|mein|hum)\s+(\w+)\s+(?:se|mein)\s+(?:hoon|rehta|rehti)', text, re.I)
    if city_match:
        hints["city"] = city_match.group(1)
    # Age
    age_match = re.search(r'(?:meri|mera)\s+age\s+(?:hai\s+)?(\d+)', text, re.I)
    if age_match:
        hints["age"] = age_match.group(1)
    # Class/grade
    class_match = re.search(r'(\d+)(?:th|st|nd|rd)\s+(?:class|mein|grade)', text, re.I)
    if class_match:
        hints["class"] = class_match.group(1) + "th"
    return hints

# ── Groq AI Call ──────────────────────────────────────────────────────────────
async def groq_chat(messages: list) -> str:
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3-8b-8192",
        "messages": [{"role": "system", "content": RAZE_SYSTEM}] + messages,
        "max_tokens": 120,
        "temperature": 0.85,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post("https://api.groq.com/openai/v1/chat/completions",
                                  headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()

# ── ElevenLabs Voice Note ─────────────────────────────────────────────────────
async def elevenlabs_tts(text: str) -> bytes | None:
    if not ELEVENLABS_KEY or not ELEVENLABS_VOICE:
        return None
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE}"
    headers = {"xi-api-key": ELEVENLABS_KEY, "Content-Type": "application/json"}
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.8}
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, headers=headers, json=payload)
        if resp.status_code == 200:
            return resp.content
    return None

VOICE_TRIGGERS = re.compile(r'\b(bolo|voice|sunao|bol|audio|suno)\b', re.I)

# ═══════════════════════════════════════════════════════════════
#  STICKER INTELLIGENCE
# ═══════════════════════════════════════════════════════════════

# Preset sticker map (file_id → mood tags)
PRESET_STICKERS = {
    "CAACAgUAAxkBAAEQyd9pvWm2mICM5UuiilY-NcnihxuZZwACgh8AAsZRxhU6tKJa_ySnnDoE": ["happy","hi","greeting","cute"],
    "CAACAgUAAxkBAAEQyeFpvWm6PGALMSwMtfrVBvi2UObWvQAC3R4AAsZRxhX9PmFONOhvtjoE": ["confused","thinking","huh"],
    "CAACAgUAAxkBAAEQyeNpvWm-rL1p5PebWi_azzJN28_tJQAC3hsAAsZRxhV2EZU-KftqcToE": ["sad","cry","aww"],
    "CAACAgUAAxkBAAEQyeRpvWnA-vP464lbGH52v1NOHt92SgACDhwAAsZRxhVQh9K5kvSnhDoE": ["excited","wow","hype"],
    "CAACAgUAAxkBAAEQyeZpvWnA-vP464lbGH52v1NOHt92SgACDhwAAsZRxhVQh9K5kvSnhDoE": ["love","heart","❤️"],
    "CAACAgUAAxkBAAEQyehpvWnAifH1e_He8ft0mEp8MWlk6wACZh4AAsZRxhXa2EhQqddYnjoE": ["laugh","lol","funny","haha"],
    "CAACAgUAAxkBAAEQyeppvWnBRiiEmTKwRV5Qizf7yunTVwACeB0AAsZRxhXcKEuO_6TIGzoE": ["angry","mad","irritated"],
    "CAACAgUAAxkBAAEQyexpvWnBY-5SD2gW9qkuIwEWmrVV-gACFxwAAsZRxhXYaukhJNpucjoE": ["bye","goodbye","wave"],
    "CAACAgUAAxkBAAEQye9pvWnCHtHVNmxi58Jjxl68fK73NwAC_hsAAsZRxhU4IXBvQz0OyjoE": ["sleep","tired","night","gn"],
    "CAACAgUAAxkBAAEQyfBpvWnCgLAPGFu7q7qTniC__NsqGQACWR4AAsZRxhUMZRjkJ3JSgToE": ["ok","fine","sure","agree"],
    "CAACAgUAAxkBAAEQyfFpvWnCGuMpLekAAShS1FCFao2hcyEAAgscAALGUcYVTM10EgWS3Eo6BA": ["no","nope","disagree","refuse"],
    "CAACAgUAAxkBAAEQyfNpvWnCgeNoVF2a-OoTp_9oa_ZAOAACLB8AAsZRxhWwh4zuHjbosjoE": ["cute","adorable","aww","sweet"],
    "CAACAgUAAxkBAAEQyfVpvWnDNVIjXCN_Lal26WRbQ7MOrwAC2B4AAsZRxhUycRBfP626YToE": ["shocked","omg","surprised"],
    "CAACAgUAAxkBAAEQyfdpvWnEqbMQOWi4qLtgLFtgMIXCkQACLh4AAsZRxhWLqCXAveT1_ToE": ["gm","morning","good morning"],
    "CAACAgUAAxkBAAEQyfhpvWnFp6ryktJxZnkR6gZLiv0udAAC2h8AAsZRxhUydgIUjztxvToE": ["thanks","ty","grateful"],
    "CAACAgUAAxkBAAEQyfppvWnGQYZXf-vwnv80MY50eFY_pQACVh4AAsZRxhWdeI_jt9VWojoE": ["thinking","maybe","idk"],
    "CAACAgUAAxkBAAEQyfxpvWnHx6229y-A0e094eRBWm3h9gACUx4AAsZRxhXxyJAgxJaJ2zoE": ["shy","blush","embarrassed"],
    "CAACAgUAAxkBAAEQyf5pvWnHtLOa95nqgi_Ise_w6TI-EwAC9x0AAsZRxhX778k8TvZL8zoE": ["cool","slay","awesome","fire"],
    "CAACAgUAAxkBAAEQyf9pvWnHzczBumzu3LtSF7WZp4VPEAAC8h0AAsZRxhWf_hFrangOfDoE": ["bored","meh","whatever"],
    "CAACAgUAAxkBAAEQygABab1px3rrYL5BpDAZ8zgvGNv8yK4AApIeAALGUcYVjI5YO0gKtN86BA": ["hungry","food","eat"],
    "CAACAgUAAxkBAAEQygJpvWnIZoRrWnnnXvtDRpn3v9Cp-gAC0R8AAsZRxhW_Q0urkBv84DoE": ["study","books","read"],
    "CAACAgUAAxkBAAEQygNpvWnJO8k_jD_UlnAVtpBKomz8tQAC0B8AAsZRxhUPDZJlK58pFDoE": ["gaming","play","fun"],
    "CAACAgUAAxkBAAEQygRpvWnJI_ksYM8jwjAsd7xJBHMgxAAChAIAAhmn8VbitcAS7QT6UzoE": ["music","sing","vibe"],
    "CAACAgUAAxkBAAEQygZpvWnJM1m7QJ5_TSmOKuZ1mA7VcAACUR4AAsZRxhUJjXBk8iMOyzoE": ["dance","party","celebrate"],
}

async def get_sticker_for_mood(mood_tags: list) -> str | None:
    """Find best sticker for given mood tags from DB first, then presets."""
    # Check learned stickers in DB
    for tag in mood_tags:
        doc = await stickers_col.find_one({"tags": tag})
        if doc:
            return doc["file_id"]
    # Fallback to presets
    for file_id, tags in PRESET_STICKERS.items():
        for tag in mood_tags:
            if tag.lower() in [t.lower() for t in tags]:
                return file_id
    return None

async def learn_sticker(file_id: str, tags: list):
    """Save a new sticker with tags to DB."""
    await stickers_col.update_one(
        {"file_id": file_id},
        {"$addToSet": {"tags": {"$each": tags}}, "$inc": {"use_count": 1}},
        upsert=True
    )

async def detect_sticker_mood(file_id: str) -> list:
    """Check if we know this sticker's mood from DB."""
    doc = await stickers_col.find_one({"file_id": file_id})
    return doc.get("tags", []) if doc else []

async def ai_guess_sticker_mood(sticker_emoji: str) -> list:
    """Use AI to guess mood from sticker emoji."""
    emoji_map = {
        "😊": ["happy","cute"], "😂": ["laugh","funny"], "😭": ["sad","cry"],
        "😍": ["love","heart"], "🤔": ["thinking","confused"], "😤": ["angry"],
        "😴": ["sleep","tired"], "🥺": ["cute","aww","sad"], "😳": ["shocked","shy"],
        "🔥": ["fire","hype","cool"], "👋": ["hi","bye","wave"], "💀": ["dead","lol"],
        "🙄": ["bored","whatever"], "😏": ["smug","flirty"], "🥰": ["love","sweet"],
        "👍": ["ok","agree"], "❤️": ["love","heart"], "😎": ["cool","slay"],
    }
    tags = emoji_map.get(sticker_emoji, ["neutral"])
    return tags

# ═══════════════════════════════════════════════════════════════
#  MAIN CHAT HANDLER
# ═══════════════════════════════════════════════════════════════

def should_respond(msg: Message) -> bool:
    """Decide if Raze should respond in a group."""
    if msg.chat.type in [enums.ChatType.PRIVATE]:
        return True
    me = app.me
    bot_username = getattr(me, "username", "") if me else ""
    # Mentioned
    if msg.text and bot_username and f"@{bot_username}".lower() in msg.text.lower():
        return True
    # Reply to bot
    if msg.reply_to_message and msg.reply_to_message.from_user:
        if me and msg.reply_to_message.from_user.id == me.id:
            return True
    # Name mentioned
    if msg.text and re.search(r'\b(raze|razechan|raze chan)\b', msg.text, re.I):
        return True
    return False

# ── Sticker handler ───────────────────────────────────────────────────────────
@app.on_message(filters.sticker)
async def handle_sticker(_, msg: Message):
    if not should_respond(msg):
        return

    file_id = msg.sticker.file_id
    emoji   = msg.sticker.emoji or "😊"

    # Check if we know this sticker
    known_tags = await detect_sticker_mood(file_id)
    if not known_tags:
        # Learn from emoji
        known_tags = await ai_guess_sticker_mood(emoji)
        await learn_sticker(file_id, known_tags)

    # Find a reply sticker with similar mood
    reply_sticker = await get_sticker_for_mood(known_tags)

    if reply_sticker:
        await msg.reply_sticker(reply_sticker)
    else:
        # Fallback text reaction
        fallback_map = {
            "happy":   "aww cute sticker~ 🥺",
            "sad":     "oof ye toh sad wala tha 😔",
            "laugh":   "hahaha 💀",
            "angry":   "uff itna gussa? 😅",
            "love":    "aww~ 🥺❤️",
            "default": "nice sticker~ 😊"
        }
        tag = known_tags[0] if known_tags else "default"
        await msg.reply(fallback_map.get(tag, fallback_map["default"]))

# ── Main text handler ─────────────────────────────────────────────────────────
@app.on_message(
    filters.text & ~filters.command(["start","help","games","aura","leaderboard",
                                      "all","set","give","steal","ttt","minesweeper",
                                      "rps","wordguess","g"])
)
async def chat_handler(_, msg: Message):
    if not should_respond(msg):
        return

    user     = msg.from_user
    text     = msg.text.strip()
    user_id  = user.id
    chat_id  = msg.chat.id

    # Save profile hints
    hints = extract_profile_hints(text)
    for k, v in hints.items():
        await save_user_profile(user_id, chat_id, k, v)

    # Get conversation history
    history = await get_context(user_id, chat_id)
    history.append({"role": "user", "content": text})

    # Check for voice request
    want_voice = bool(VOICE_TRIGGERS.search(text))

    try:
        async with msg.chat.action("typing"):
            ai_reply = await groq_chat(history)
    except Exception as e:
        ai_reply = "ugh sorry abhi thodi problem aa rahi hai~ baad mein try karo 😅"

    # Save context
    await save_context(user_id, chat_id, "user", text)
    await save_context(user_id, chat_id, "assistant", ai_reply)

    # Detect mood for sticker reaction (sometimes)
    mood_words = {
        "happy":    ["haha","lol","xd","😂","hehe","great","amazing","nice","best"],
        "sad":      ["sad","dukh","rona","cry","😭","miss","bore"],
        "love":     ["love","pyaar","❤️","dil","cute","aww"],
        "excited":  ["wow","omg","yay","🔥","fire","hype"],
        "sleep":    ["gn","good night","so raha","neend"],
        "gm":       ["gm","good morning","subah"],
    }
    reply_mood = None
    for mood, kws in mood_words.items():
        for kw in kws:
            if kw in text.lower():
                reply_mood = mood
                break

    # Send voice note if requested
    if want_voice:
        clean_text = re.sub(r'[*_`~]', '', ai_reply)
        audio_bytes = await elevenlabs_tts(clean_text)
        if audio_bytes:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(audio_bytes)
                tmp_path = f.name
            try:
                await msg.reply_voice(tmp_path, caption="🎙️ ~Raze")
            finally:
                os.unlink(tmp_path)
            return

    # Send text reply
    sent = await msg.reply(ai_reply)

    # Sometimes send a mood sticker after reply (20% chance)
    if reply_mood and random.random() < 0.20:
        sticker = await get_sticker_for_mood([reply_mood])
        if sticker:
            await asyncio.sleep(0.5)
            await msg.reply_sticker(sticker)

import random
