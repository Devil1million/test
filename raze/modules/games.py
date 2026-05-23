"""
Games Module - RazeChan Bot
Tic-Tac-Toe, Minesweeper, RPS, Wordchain, Word Guess
"""
import random
import json
from datetime import datetime
from pyrogram import filters
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)
from raze import app, games_col, aura_col
from raze.modules.aura import update_aura

# ═══════════════════════════════════════════════════════════════
#  TIC-TAC-TOE
# ═══════════════════════════════════════════════════════════════
ttt_games: dict = {}  # chat_msg_id -> game state

def ttt_board_markup(board: list, game_id: str) -> InlineKeyboardMarkup:
    symbols = {0: "⬜", 1: "❌", 2: "⭕"}
    rows = []
    for r in range(3):
        row = []
        for c in range(3):
            idx = r * 3 + c
            row.append(InlineKeyboardButton(
                symbols[board[idx]],
                callback_data=f"ttt:{game_id}:{idx}"
            ))
        rows.append(row)
    rows.append([InlineKeyboardButton("❌ Forfeit", callback_data=f"ttt_quit:{game_id}")])
    return InlineKeyboardMarkup(rows)

def ttt_check_winner(board: list) -> int:
    wins = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
    for a,b,c in wins:
        if board[a] == board[b] == board[c] != 0:
            return board[a]
    return 0

def ttt_ai_move(board: list) -> int:
    # Try to win
    for i in range(9):
        if board[i] == 0:
            board[i] = 2
            if ttt_check_winner(board) == 2:
                board[i] = 0
                return i
            board[i] = 0
    # Block player
    for i in range(9):
        if board[i] == 0:
            board[i] = 1
            if ttt_check_winner(board) == 1:
                board[i] = 0
                return i
            board[i] = 0
    # Center
    if board[4] == 0:
        return 4
    # Random
    empty = [i for i in range(9) if board[i] == 0]
    return random.choice(empty) if empty else -1

@app.on_message(filters.command("ttt"))
async def start_ttt(_, msg: Message):
    if not GAMES_ENABLED_CHECK():
        return await msg.reply("🎮 Games abhi disabled hain~")
    board = [0] * 9
    game_id = f"{msg.chat.id}_{msg.from_user.id}_{int(datetime.now().timestamp())}"
    ttt_games[game_id] = {"board": board, "player": msg.from_user.id, "chat": msg.chat.id}
    sent = await msg.reply(
        f"🎮 **Tic-Tac-Toe** vs Raze~\n\n"
        f"Tum **❌** ho, main **⭕** hoon!\nTumhari baari~ 😏",
        reply_markup=ttt_board_markup(board, game_id)
    )
    ttt_games[game_id]["msg_id"] = sent.id

@app.on_callback_query(filters.regex(r"^ttt:"))
async def ttt_move(_, cb: CallbackQuery):
    _, game_id, idx_str = cb.data.split(":")
    idx = int(idx_str)
    game = ttt_games.get(game_id)
    if not game:
        return await cb.answer("Game expired! /ttt se naya shuru karo~", show_alert=True)
    if cb.from_user.id != game["player"]:
        return await cb.answer("Ye tumhara game nahi hai 😤", show_alert=True)
    board = game["board"]
    if board[idx] != 0:
        return await cb.answer("Ye cell pehle se bhari hai! 🙅‍♀️", show_alert=True)

    board[idx] = 1
    winner = ttt_check_winner(board)
    if winner == 1:
        del ttt_games[game_id]
        await update_aura(cb.from_user.id, game["chat"], 50)
        return await cb.message.edit(
            f"🎉 **Tumne jeeta!** Congrats bestie~ 🥳\n+50 Aura points mile!",
            reply_markup=None
        )
    if all(b != 0 for b in board):
        del ttt_games[game_id]
        return await cb.message.edit("🤝 **Draw!** Acha khela tum ne~ 😊", reply_markup=None)

    # AI move
    ai_idx = ttt_ai_move(board)
    if ai_idx >= 0:
        board[ai_idx] = 2
    winner = ttt_check_winner(board)
    if winner == 2:
        del ttt_games[game_id]
        return await cb.message.edit(
            "😈 **Maine jeeta!** Better luck next time~ 💅\n_Hint: Center se shuru karo_",
            reply_markup=None
        )
    if all(b != 0 for b in board):
        del ttt_games[game_id]
        return await cb.message.edit("🤝 **Draw!** Almost tha~ 😄", reply_markup=None)

    await cb.message.edit_reply_markup(reply_markup=ttt_board_markup(board, game_id))
    await cb.answer("Tumhari baari! 🎯")

@app.on_callback_query(filters.regex(r"^ttt_quit:"))
async def ttt_quit(_, cb: CallbackQuery):
    game_id = cb.data.split(":")[1]
    if game_id in ttt_games:
        if cb.from_user.id == ttt_games[game_id]["player"]:
            del ttt_games[game_id]
            await cb.message.edit("🏳️ Forfeit kar diya... darr gaye? 😏", reply_markup=None)
        else:
            await cb.answer("Ye tumhara game nahi~ 😤", show_alert=True)

# ═══════════════════════════════════════════════════════════════
#  MINESWEEPER 5x5
# ═══════════════════════════════════════════════════════════════
mine_games: dict = {}

def gen_minesweeper(size=5, mines=6) -> dict:
    board = [0] * (size * size)
    mine_pos = random.sample(range(size * size), mines)
    for m in mine_pos:
        board[m] = -1  # mine
    # Count neighbors
    for i in range(size * size):
        if board[i] == -1:
            continue
        r, c = divmod(i, size)
        count = 0
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < size and 0 <= nc < size and board[nr * size + nc] == -1:
                    count += 1
        board[i] = count
    return {"board": board, "revealed": [False] * (size * size), "size": size, "mines": mine_pos}

def mine_markup(state: dict, game_id: str, show_all=False) -> InlineKeyboardMarkup:
    size  = state["size"]
    board = state["board"]
    rev   = state["revealed"]
    nums  = ["0️⃣","1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣"]
    rows  = []
    for r in range(size):
        row = []
        for c in range(size):
            i = r * size + c
            if show_all:
                sym = "💣" if board[i] == -1 else (nums[board[i]] if board[i] > 0 else "🟩")
            elif rev[i]:
                sym = "💣" if board[i] == -1 else (nums[board[i]] if board[i] > 0 else "🟩")
            else:
                sym = "🟦"
            row.append(InlineKeyboardButton(sym, callback_data=f"mine:{game_id}:{i}"))
        rows.append(row)
    return InlineKeyboardMarkup(rows)

@app.on_message(filters.command("minesweeper"))
async def start_mine(_, msg: Message):
    state   = gen_minesweeper()
    game_id = f"mine_{msg.chat.id}_{msg.from_user.id}_{int(datetime.now().timestamp())}"
    mine_games[game_id] = {**state, "player": msg.from_user.id, "chat": msg.chat.id, "safe_clicked": 0}
    await msg.reply(
        "💣 **Minesweeper** — 5×5 Grid, 6 Mines\n\n"
        "Blue cells = unknown, click to reveal!\nMine pe click = Game Over 💀",
        reply_markup=mine_markup(state, game_id)
    )

@app.on_callback_query(filters.regex(r"^mine:"))
async def mine_click(_, cb: CallbackQuery):
    _, game_id, idx_str = cb.data.split(":")
    idx   = int(idx_str)
    state = mine_games.get(game_id)
    if not state:
        return await cb.answer("Game expired! /minesweeper se shuru karo~", show_alert=True)
    if cb.from_user.id != state["player"]:
        return await cb.answer("Ye tumhara game nahi~ 😤", show_alert=True)
    if state["revealed"][idx]:
        return await cb.answer("Pehle se reveal hai~ 👀", show_alert=True)

    state["revealed"][idx] = True

    if state["board"][idx] == -1:
        # BOOM
        del mine_games[game_id]
        return await cb.message.edit(
            "💥 **BOOM! Mine mil gayi!**\nBetter luck next time~ 😂\n_Pro tip: Corners se shuru karo_",
            reply_markup=mine_markup({**state, "revealed": [True]*25}, game_id, show_all=True)
        )

    state["safe_clicked"] = state.get("safe_clicked", 0) + 1
    total_safe = state["size"] ** 2 - len(state["mines"])

    if state["safe_clicked"] >= total_safe:
        score = state["safe_clicked"] * 10
        await check_world_record(cb.from_user, "Minesweeper", score, cb.message.chat.id)
        del mine_games[game_id]
        await update_aura(cb.from_user.id, state["chat"], 100)
        return await cb.message.edit(
            f"🎊 **Minesweeper Clear!** Amazing~ 🥳\n"
            f"Score: `{score}` | +100 Aura!",
            reply_markup=None
        )

    await cb.message.edit_reply_markup(reply_markup=mine_markup(state, game_id))
    await cb.answer(f"Safe! {state['safe_clicked']}/{total_safe} cleared 🎯")

# ═══════════════════════════════════════════════════════════════
#  ROCK-PAPER-SCISSORS
# ═══════════════════════════════════════════════════════════════
@app.on_message(filters.command("rps"))
async def rps_cmd(_, msg: Message):
    btns = InlineKeyboardMarkup([[
        InlineKeyboardButton("🪨 Rock",   callback_data="rps:rock"),
        InlineKeyboardButton("📄 Paper",  callback_data="rps:paper"),
        InlineKeyboardButton("✂️ Scissors", callback_data="rps:scissors"),
    ]])
    await msg.reply("🎮 **Rock Paper Scissors!**\nChoose karo~ 👇", reply_markup=btns)

@app.on_callback_query(filters.regex(r"^rps:"))
async def rps_play(_, cb: CallbackQuery):
    player_choice = cb.data.split(":")[1]
    bot_choice    = random.choice(["rock", "paper", "scissors"])
    emojis        = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
    wins           = {"rock": "scissors", "paper": "rock", "scissors": "paper"}

    pe = emojis[player_choice]
    be = emojis[bot_choice]

    if player_choice == bot_choice:
        result = f"🤝 **Draw!**\n{pe} vs {be}\nDono same choice~ 😄"
    elif wins[player_choice] == bot_choice:
        await update_aura(cb.from_user.id, cb.message.chat.id, 10)
        result = f"🎉 **Tum jeete!**\n{pe} vs {be}\n+10 Aura~ 💫"
    else:
        result = f"😈 **Main jeeti!**\n{pe} vs {be}\nBetter luck next time~"

    await cb.message.edit(result, reply_markup=None)
    await cb.answer()

# ═══════════════════════════════════════════════════════════════
#  WORD GUESS (Hangman style)
# ═══════════════════════════════════════════════════════════════
WORD_LIST = [
    "python", "telegram", "beautiful", "sunshine", "butterfly",
    "chocolate", "adventure", "friendship", "happiness", "universe",
    "mountain", "keyboard", "instagram", "developer", "artificial"
]
word_games: dict = {}

@app.on_message(filters.command("wordguess"))
async def start_word_guess(_, msg: Message):
    word    = random.choice(WORD_LIST)
    game_id = f"wg_{msg.chat.id}_{msg.from_user.id}"
    word_games[game_id] = {
        "word": word, "guessed": [], "wrong": 0,
        "player": msg.from_user.id, "chat": msg.chat.id,
        "max_wrong": 6
    }
    await msg.reply(
        f"🔤 **Word Guess!** ({len(word)} letters)\n\n"
        f"`{get_display(word, [])}`\n\n"
        "Reply with a single letter to guess!\n_Example: reply `/g a`_"
    )

@app.on_message(filters.command("g"))
async def guess_letter(_, msg: Message):
    game_id = f"wg_{msg.chat.id}_{msg.from_user.id}"
    state   = word_games.get(game_id)
    if not state:
        return await msg.reply("No active game! /wordguess se shuru karo~")

    if len(msg.command) < 2 or len(msg.command[1]) != 1:
        return await msg.reply("Ek letter bhejo! Example: `/g a`")

    letter = msg.command[1].lower()
    word   = state["word"]

    if letter in state["guessed"]:
        return await msg.reply(f"'{letter}' pehle try kar chuke ho! 🙄")

    state["guessed"].append(letter)

    if letter not in word:
        state["wrong"] += 1

    display = get_display(word, state["guessed"])
    hangman = ["😊","🙂","😐","😟","😰","😱","💀"][state["wrong"]]

    if "_" not in display:
        score = (state["max_wrong"] - state["wrong"]) * 20
        await check_world_record(msg.from_user, "Word Guess", score, msg.chat.id)
        del word_games[game_id]
        await update_aura(msg.from_user.id, msg.chat.id, 30)
        return await msg.reply(
            f"🎉 **Correct! Word tha: `{word}`**\n"
            f"Score: `{score}` | +30 Aura~ ✨"
        )

    if state["wrong"] >= state["max_wrong"]:
        del word_games[game_id]
        return await msg.reply(
            f"💀 **Game Over!** Word tha: `{word}`\nNext time better karna~ 😤"
        )

    await msg.reply(
        f"{hangman} `{display}`\n\n"
        f"❌ Wrong: {state['wrong']}/{state['max_wrong']}\n"
        f"✅ Tried: {', '.join(state['guessed'])}"
    )

def get_display(word: str, guessed: list) -> str:
    return " ".join(c if c in guessed else "_" for c in word)

# ═══════════════════════════════════════════════════════════════
#  WORLD RECORDS
# ═══════════════════════════════════════════════════════════════
async def check_world_record(user, game_name: str, score: int, chat_id: int):
    rec = await games_col.find_one({"game": game_name})
    if not rec or score > rec.get("score", 0):
        await games_col.update_one(
            {"game": game_name},
            {"$set": {"score": score, "user_id": user.id, "name": user.first_name}},
            upsert=True
        )
        try:
            await app.send_message(
                chat_id,
                f"🏆 **NEW WORLD RECORD!**\n\n"
                f"🎮 Game: **{game_name}**\n"
                f"👑 Player: [{user.first_name}](tg://user?id={user.id})\n"
                f"📊 Score: **{score}**\n\n"
                f"_Can anyone beat this?_ 😏",
                parse_mode="markdown"
            )
        except Exception:
            pass

# ═══════════════════════════════════════════════════════════════
#  /games MENU
# ═══════════════════════════════════════════════════════════════
@app.on_message(filters.command("games"))
async def games_menu(_, msg: Message):
    btns = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Tic-Tac-Toe", callback_data="launch:ttt"),
         InlineKeyboardButton("💣 Minesweeper", callback_data="launch:mine")],
        [InlineKeyboardButton("✂️ RPS",          callback_data="launch:rps"),
         InlineKeyboardButton("🔤 Word Guess",   callback_data="launch:wordguess")],
        [InlineKeyboardButton("🏆 Leaderboard",  callback_data="games_lb")],
        [InlineKeyboardButton("🏠 Back to Start", callback_data="start_home")]
    ])
    await msg.reply(
        "🎮 **Raze's Game Zone!**\n\nSelect your challenge~ 🔥\n"
        "_Win games to earn Aura points!_",
        reply_markup=btns
    )

@app.on_callback_query(filters.regex(r"^launch:"))
async def launch_game(_, cb: CallbackQuery):
    game = cb.data.split(":")[1]
    await cb.answer()
    fake_msg = cb.message
    fake_msg.from_user = cb.from_user
    if game == "ttt":       await start_ttt(_, fake_msg)
    elif game == "mine":    await start_mine(_, fake_msg)
    elif game == "rps":     await rps_cmd(_, fake_msg)
    elif game == "wordguess": await start_word_guess(_, fake_msg)

@app.on_callback_query(filters.regex("^games_lb$"))
async def games_lb_cb(_, cb: CallbackQuery):
    await cb.answer()
    records = await games_col.find().to_list(20)
    if not records:
        return await cb.message.reply("🏆 Abhi koi records nahi hain!")
    text = "🏆 **World Records**\n\n"
    for rec in records:
        text += f"🎮 **{rec['game']}** — {rec.get('name','?')} — `{rec.get('score',0)}`\n"
    await cb.message.reply(text)

def GAMES_ENABLED_CHECK():
    from raze import GAMES_ENABLED
    return GAMES_ENABLED
