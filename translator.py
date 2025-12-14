import json
import requests
from deep_translator import GoogleTranslator
import os

# --- Path to local word cache ---
WORD_FILE = "word.json"

# Load or create cache
if os.path.exists(WORD_FILE):
    with open(WORD_FILE, "r", encoding="utf-8") as f:
        CACHE = json.load(f)
else:
    CACHE = {}

def save_cache():
    """Save updated cache to local file."""
    with open(WORD_FILE, "w", encoding="utf-8") as f:
        json.dump(CACHE, f, ensure_ascii=False, indent=2)

def lookup_word(word):
    """
    Get definitions, synonyms, and Uzbek translation for a word.
    Returns a dictionary ready to use in bot.py
    """
    word = word.lower().strip()

    # 1. Check cache
    if word in CACHE:
        return CACHE[word]

    # 2. Fetch definition from Free Dictionary API
    dict_url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    try:
        resp = requests.get(dict_url)
        if resp.status_code != 200:
            return {"error": "Word not found"}

        data = resp.json()[0]
        meaning = data["meanings"][0]
        part_of_speech = meaning.get("partOfSpeech", "N/A")
        definition = meaning["definitions"][0].get("definition", "N/A")
        examples = meaning["definitions"][0].get("example", "No example available")

        # 3. Get synonyms from Datamuse API
        syn_resp = requests.get(f"https://api.datamuse.com/words?rel_syn={word}")
        synonyms = [item["word"] for item in syn_resp.json()[:5]]

        # 4. Translate definition to Uzbek
        text_to_translate = f"({part_of_speech}) {definition}"
        uzbek_translation = GoogleTranslator(source="en", target="uz").translate(text_to_translate)

        # 5. Prepare result
        result = {
            "word": word,
            "translation_uz": uzbek_translation,
            "part_of_speech": part_of_speech,
            "level": None,  # Placeholder for CEFR level
            "prefixes": [],  # Can be expanded
            "suffixes": [],
            "example_sentence_1": examples,
            "example_sentence_2": f"This is another example of the word '{word}' in a sentence.",
            "synonyms_en": synonyms
        }

        # 6. Cache result
        CACHE[word] = result
        save_cache()

        return result

    except Exception as e:
        return {"error": str(e)}
@bot.message_handler(content_types=["text"])
def translate_handler(message):
    text = message.text.strip()

    # translation logic here
    translated = translate(text)

    tracker.log_query(
        message=message,
        word=text,
        direction="uz-en"
    )

    bot.send_message(message.chat.id, translated)
