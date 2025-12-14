# bot.py — FINAL WIZARD VERSION (NO FOLDERS, PRODUCTION SAFE)

import os
import json
import random
import threading
import time
from typing import Any, Optional

from flask import Flask, request, abort
from telebot import TeleBot, types
from deep_translator import GoogleTranslator
from dotenv import load_dotenv

# ==================================================
# ENVIRONMENT
# ==================================================
load_dotenv()
TOKEN = os.getenv("TOKEN")
PUBLIC_URL = os.getenv("PUBLIC_URL", "")

if not TOKEN:
    raise RuntimeError("TOKEN is required")

BOT_NAME = "Vocabulary with Mr. Korsh"

# ==================================================
# PATHS (ROOT LEVEL ONLY)
# ==================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

WORDS_FILE = os.path.join(DATA_DIR, "words.json")
PHRASES_FILE = os.path.join(DATA_DIR, "phrases.json")
TRACK_FILE = os.path.join(BASE_DIR, "tracking.json")

os.makedirs(DATA_DIR, exist_ok=True)

# ==================================================
# JSON HELPERS
# ==================================================
def load_json(path: str) -> Any:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_json(path: str, data: Any):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# ==================================================
# TRACKING (FINAL DESIGN)
# ==================================================
def track_activity(user_id: int, word: str | None = None):
    data = load_json(TRACK_FILE)

    if "users" not in data or not isinstance(data.get("users"), dict):
        data["users"] = {}

    uid = str(user_id)

    if uid not in data["users"]:
        data["users"][uid] = {
            "first_seen": time.strftime("%Y-%m-%d"),
            "words": []
        }

    if word:
        data["users"][uid]["words"].append(word.lower())

    save_json(TRACK_FILE, data)


def load_all_users():
    data = load_json(TRACK_FILE)
    if "users" in data:
        return list(data["users"].keys())
    return []


# ==================================================
# TRANSLATION
# ==================================================
def detect_uzbek(text: str) -> bool:
    if not text:
        return False

    for ch in text:
        if "\u0400" <= ch <= "\u04FF":
            return True

    uz_tokens = {
        "men", "sen", "biz", "siz", "ular", "va", "yo'q", "rahmat",
        "salom", "yaxshi", "bor", "qanday", "iltimos"
    }

    for tok in text.lower().split():
        if tok.strip(".,!?;:") in uz_tokens:
            return True

    return False


def translate_dynamic(text: str):
    is_uz = detect_uzbek(text)
    try:
        if is_uz:
            return GoogleTranslator(source="uz", target="en").translate(text)
        return GoogleTranslator(source="auto", target="uz").translate(text)
    except Exception:
        return "❌ Translation failed"


# ==================================================
# WORD DATABASE
# ==================================================
def find_word_info(word: str) -> Optional[dict]:
    words = load_json(WORDS_FILE)
    if isinstance(words, dict):
        return words.get(word.lower())
    return None


def format_word_response(word: str, translation: str, info: Optional[dict]):
    msg = f"📝 *{word}*\n🔤 *{translation}*\n"
    if not info:
        return msg

    if info.get("part_of_speech"):
        msg += f"📚 {info['part_of_speech']}\n"
    if info.get("examples"):
        msg += "📖 Examples:\n"
        for ex in info["examples"]:
            msg += f"- {ex}\n"
    return msg


# ==================================================
# BOT INIT
# ==================================================
bot = TeleBot(TOKEN, parse_mode="Markdown")


# ==================================================
# UI
# ==================================================
def main_menu(chat_id, name=None):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🌐 Translate a Word", "🗣 Learn a Phrase")

    text = f"Hello {name}! 👋\nWelcome to *{BOT_NAME}*" if name else f"Welcome to *{BOT_NAME}*"
    bot.send_message(chat_id, text, reply_markup=kb)


# ==================================================
# HANDLERS
# ==================================================
@bot.message_handler(commands=["start"])
def start_cmd(message: types.Message):
    track_activity(message.from_user.id)
    main_menu(message.chat.id, message.from_user.first_name)


@bot.message_handler(func=lambda m: True)
def main_handler(message: types.Message):
    text = message.text.strip()

    if text == "🌐 Translate a Word":
        msg = bot.send_message(message.chat.id, "Enter a word (EN / UZ):")
        bot.register_next_step_handler(msg, translate_word)
        return

    if text == "🗣 Learn a Phrase":
        phrases = load_json(PHRASES_FILE)
        if not phrases:
            bot.send_message(message.chat.id, "No phrases available")
            return
        kb = types.InlineKeyboardMarkup()
        for k in phrases:
            kb.add(types.InlineKeyboardButton(k, callback_data=f"phrase:{k}"))
        bot.send_message(message.chat.id, "Choose a topic:", reply_markup=kb)
        return

    translate_word(message)


# ==================================================
# TRANSLATE WORD
# ==================================================
def translate_word(message: types.Message):
    word = message.text.strip()
    track_activity(message.from_user.id, word)

    info = find_word_info(word)
    if info:
        translation = info.get("translation", word)
        response = format_word_response(word, translation, info)
    else:
        translation = translate_dynamic(word)
        response = f"📝 *{word}*\n🔤 *{translation}*"

    bot.send_message(message.chat.id, response)
    main_menu(message.chat.id)


# ==================================================
# PHRASES
# ==================================================
@bot.callback_query_handler(func=lambda c: c.data.startswith("phrase:"))
def phrase_handler(call: types.CallbackQuery):
    topic = call.data.split(":", 1)[1]
    phrases = load_json(PHRASES_FILE).get(topic, [])

    if not phrases:
        bot.send_message(call.message.chat.id, "No phrases found")
        return

    text = f"📌 *{topic}* phrases:\n"
    for p in phrases:
        text += f"- {p}\n"

    bot.send_message(call.message.chat.id, text)


# ==================================================
# QUIZ SYSTEM (SAFE MODE)
# ==================================================
def send_quiz_to_user(user_id: int):
    words = load_json(WORDS_FILE)
    if not words:
        return

    try:
        word = random.choice(list(words.keys()))
        bot.send_message(
            user_id,
            f"🎯 Quiz time! Translate this word:\n*{word}*",
            parse_mode="Markdown"
        )
    except Exception as e:
        print("Quiz failed for", user_id, e)


def quiz_loop(interval_hours=12):
    while True:
        for uid in load_all_users():
            send_quiz_to_user(int(uid))
        time.sleep(interval_hours * 3600)


def start_quiz_thread():
    threading.Thread(target=quiz_loop, daemon=True).start()


# ==================================================
# FLASK WEBHOOK
# ==================================================
app = Flask(__name__)
WEBHOOK_PATH = f"/webhook/{TOKEN}"


@app.route("/")
def index():
    return f"{BOT_NAME} is running"


@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    if request.headers.get("content-type") != "application/json":
        abort(403)
    update = types.Update.de_json(request.get_json())
    bot.process_new_updates([update])
    return "", 200


def set_webhook():
    if not PUBLIC_URL:
        return
    bot.remove_webhook()
    bot.set_webhook(url=f"{PUBLIC_URL}{WEBHOOK_PATH}")


# ==================================================
# START
# ==================================================
if __name__ == "__main__":
    start_quiz_thread()
    set_webhook()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
