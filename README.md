# 🌸 RazeChan Bot — Complete Setup Guide

> **AI Girl Telegram Bot** — Groq AI + Voice Notes + Sticker Learning + Games + Aura System

---

## 📁 Project Structure

```
RazeChanBot/
├── main.py                  ← Bot runner (yahan se start hoga)
├── requirements.txt         ← Python libraries
├── .env.example             ← Environment variables template
└── raze/
    ├── __init__.py          ← App + DB setup
    └── modules/
        ├── chat.py          ← AI chat + voice notes + sticker learning
        ├── aura.py          ← Aura/social credit system
        ├── games.py         ← Tic-Tac-Toe, Minesweeper, RPS, Word Guess
        └── admin.py         ← /start dashboard, /set UI, /all mention
```

---

## 🔑 Step 1 — API Keys Collect Karo

### 1️⃣ Telegram API (FREE)
1. https://my.telegram.org/apps par jao
2. "Create Application" karo
3. `API_ID` aur `API_HASH` copy karo

### 2️⃣ Bot Token (FREE)
1. Telegram pe @BotFather ko open karo
2. `/newbot` likho
3. Name: `Raze Chan` | Username: `razechanbot` (ya jo available ho)
4. Token copy karo → ye hai `BOT_TOKEN`

### 3️⃣ MongoDB Atlas (FREE)
1. https://mongodb.com/atlas par signup karo
2. Free M0 cluster create karo
3. Database user banao (username + password)
4. Network Access → `0.0.0.0/0` allow karo
5. Connect → Drivers → URI copy karo → ye hai `MONGO_URI`

### 4️⃣ Groq AI (FREE — best speed!)
1. https://console.groq.com par signup karo
2. API Keys → Create key
3. Copy karo → ye hai `GROQ_API_KEY`

### 5️⃣ DB Channel banana
1. Telegram pe ek private channel banao
2. Bot ko admin banao (post messages permission)
3. Channel ka ID nikalne ke liye: @userinfobot ko channel mein add karo
4. Wo `-100xxxxxxxxxx` format mein ID dega → `DB_CHANNEL_ID`

### 6️⃣ ElevenLabs (Voice Notes — Optional)
1. https://elevenlabs.io par signup karo
2. Profile → API Key copy karo
3. Voices mein se koi `VOICE_ID` copy karo
4. ⚠️ Free tier = 10k chars/month. Voice notes skip karna ho toh blank chhod do.

---

## 🖥️ Step 2 — Local Setup (PC)

```bash
# 1. Python 3.11+ install hona chahiye
python --version

# 2. Project folder mein jao
cd RazeChanBot

# 3. Virtual environment (recommended)
python -m venv venv
source venv/bin/activate     # Linux/Mac
venv\Scripts\activate        # Windows

# 4. Libraries install karo
pip install -r requirements.txt

# 5. .env file banao
cp .env.example .env
# Ab .env file open karke apni keys fill karo

# 6. Bot chalaao!
python main.py
```

---

## ☁️ Step 3 — Cloud Deploy (24/7 ke liye)

### Option A: Railway.app (RECOMMENDED — FREE)
1. https://railway.app par signup karo (GitHub se)
2. "New Project" → "Deploy from GitHub repo"
3. Apna repo upload karo (ya GitHub pe push karo)
4. Variables tab mein sab `.env` values daalo
5. Deploy! ✅

**Start Command:** `python main.py`

### Option B: Render.com (FREE)
1. https://render.com par signup karo
2. New → Background Worker
3. Build: `pip install -r requirements.txt`
4. Start: `python main.py`
5. Environment variables add karo

### Option C: VPS (DigitalOcean/Hetzner)
```bash
# Server pe yeh commands chalao
git clone <your-repo>
cd RazeChanBot
pip install -r requirements.txt
cp .env.example .env && nano .env

# Background mein chalaane ke liye:
screen -S razechan
python main.py
# Ctrl+A, D to detach
```

---

## 🤖 Step 4 — Bot Ko Group Mein Add Karo

1. Bot ke username pe jao → "Add to Group"
2. Bot ko **admin** banao (jaruri permissions):
   - ✅ Delete messages
   - ✅ Pin messages
   - ✅ Add members (optional)

---

## ⚙️ Features Guide

### 💬 AI Chat
- Group mein sirf tab reply karegi jab:
  - `@botusername` mention karo
  - Raze ka naam likho ("raze", "raze chan")
  - Bot ki message pe reply karo
- DM mein hamesha active

### 🎙️ Voice Notes
- Message mein `bolo`, `sunao`, `voice`, `audio` likho
- Raze voice note bhejegi (ElevenLabs key chahiye)

### 🏷️ Sticker Learning
- Koi sticker bhejo → Raze similar mood ka sticker reply karegi
- Waqt ke saath naye stickers seekhti rahegi

### ✨ Aura System
| Command | Kaam |
|---------|------|
| `/aura` | Apni stats dekho |
| `/give 100` (reply mein) | Kisi ko aura do |
| `/steal 50` (reply mein) | Kisi se aura lo |
| `/leaderboard` | Top 10 aura holders |

**Realms:**
| Realm | Points | Give/day | Steal/day |
|-------|--------|----------|-----------|
| 👤 Mortal | 0–999 | 700 | 600 |
| ⚔️ Warrior | 1K–2.9K | 1200 | 1000 |
| 🌿 Sage | 3K–5.9K | 1800 | 1500 |
| 🔥 Legend | 6K–9.9K | 2500 | 2000 |
| 💎 Immortal | 10K–19.9K | 3500 | 2800 |
| 👑 Divine | 20K+ | 5000 | 4000 |

### 🎮 Games
| Command | Game |
|---------|------|
| `/ttt` | Tic-Tac-Toe vs Raze (inline keyboard) |
| `/minesweeper` | 5×5 Minesweeper (6 mines) |
| `/rps` | Rock Paper Scissors |
| `/wordguess` | Word Guess (Hangman style) |
| `/g a` | Word guess mein letter guess karo |

### 👑 Admin Commands (Owner Only)
```
/set start      → /start ka banner set karo
/set help       → /help ka banner set karo
/set games      → /games ka banner set karo
/set aura       → /aura ka banner set karo
/cancelset      → set mode cancel karo
/all            → sabko mention karo
```

**Banner set kaise karo:**
1. `/set start` likho
2. Bot "Listening Mode" on karega
3. Ek Photo + Caption bhejo
4. Done! ✅

---

## 🐛 Common Issues

| Problem | Solution |
|---------|----------|
| `API_ID invalid` | my.telegram.org se naya ID lo |
| `Bot token invalid` | @BotFather se /token lo |
| `MongoDB connection failed` | URI check karo, 0.0.0.0 whitelist karo |
| `Groq rate limit` | Free plan mein 30 req/min limit hai |
| `Voice notes nahi aa raha` | ElevenLabs key check karo, ya blank chhod do |
| `Bot group mein reply nahi karta` | Bot ko admin banao + mention karo |

---

## 📞 Support

Bot ka username set karo aur `/start` karo — Raze khud help karegi~ 😄

---

*Made with 💜 — RazeChan Bot v1.0*
