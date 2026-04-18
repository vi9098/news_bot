import telebot
import requests
import random
import time
import threading
import json
from bs4 import BeautifulSoup
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "8278824209:AAGJNf1sPQE8IMI0Q9pFejpNkkxFoO28jh8"
OWNER_ID = 123456789

bot = telebot.TeleBot(BOT_TOKEN)

# ===== FILES =====
CHANNEL_FILE = "channels.json"
POSTED_FILE = "posted.json"

# Load channels
try:
    with open(CHANNEL_FILE, "r") as f:
        channels = set(json.load(f))
except:
    channels = set()

# Load posted news
try:
    with open(POSTED_FILE, "r") as f:
        posted = set(json.load(f))
except:
    posted = set()

def save_channels():
    with open(CHANNEL_FILE, "w") as f:
        json.dump(list(channels), f)

def save_posted():
    with open(POSTED_FILE, "w") as f:
        json.dump(list(posted), f)

# ===== SCRAPERS =====
def fetch_hindu(url):
    try:
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        data = []
        for a in soup.select("h3 a")[:5]:
            link = a.get("href")
            data.append({
                "title": a.text.strip(),
                "url": link,
                "source": "The Hindu",
                "image": get_image(link)
            })
        return data
    except:
        return []

def fetch_pib():
    try:
        res = requests.get("https://pib.gov.in/allRel.aspx", timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        data = []
        for a in soup.select("a"):
            link = a.get("href")
            if link and "ReleaseID" in link:
                full = "https://pib.gov.in/" + link
                data.append({
                    "title": a.text.strip(),
                    "url": full,
                    "source": "PIB",
                    "image": None
                })
        return data[:5]
    except:
        return []

# ===== IMAGE EXTRACTOR =====
def get_image(url):
    try:
        res = requests.get(url, timeout=5)
        soup = BeautifulSoup(res.text, "html.parser")

        img = soup.find("meta", property="og:image")
        if img:
            return img.get("content")
    except:
        return None

# ===== CATEGORY =====
CATEGORIES = {
    "defence": [fetch_pib, lambda: fetch_hindu("https://www.thehindu.com/news/national/")],
    "technology": [lambda: fetch_hindu("https://www.thehindu.com/sci-tech/technology/")],
    "business": [lambda: fetch_hindu("https://www.thehindu.com/business/")]
}

# ===== SUMMARY =====
def summarize(title):
    return " ".join(title.split()[:18]) + "..."

# ===== MCQ =====
def generate_mcq():
    questions = [
        ("What is this news related to?", "Current Affairs"),
        ("This news belongs to which category?", "Current Affairs"),
        ("Identify the correct context:", "Current Affairs")
    ]

    q, correct = random.choice(questions)

    options = ["Current Affairs", "Sports", "Science", "Economy"]
    random.shuffle(options)

    correct_letter = chr(65 + options.index(correct))
    opt_text = "\n".join([f"{chr(65+i)}. {opt}" for i, opt in enumerate(options)])

    return f"{q}\n\n{opt_text}\n\n||✅ Answer: {correct_letter}||"

# ===== FETCH =====
def fetch_news():
    category = random.choice(list(CATEGORIES.keys()))
    articles = []

    for f in CATEGORIES[category]:
        articles += f()

    return articles

# ===== SEND =====
def send_news(chat_id):
    articles = fetch_news()

    for article in articles:
        if article["title"] in posted:
            continue

        posted.add(article["title"])
        save_posted()

        caption = f"""📰 *{article['title']}*

📌 {summarize(article['title'])}

🌐 {article['source']}
🔗 {article['url']}

👤 Owner: tg://user?id={OWNER_ID}
"""

        try:
            if article["image"]:
                bot.send_photo(chat_id, article["image"], caption=caption, parse_mode="Markdown")
            else:
                bot.send_message(chat_id, caption, parse_mode="Markdown")

            bot.send_message(chat_id, generate_mcq(), parse_mode="Markdown")
            break

        except Exception as e:
            print(e)

# ===== BUTTON =====
def keyboard():
    markup = InlineKeyboardMarkup()
    for cat in CATEGORIES.keys():
        markup.add(InlineKeyboardButton(cat.capitalize(), callback_data=cat))
    return markup

# ===== START =====
@bot.message_handler(commands=['start'])
def start(msg):
    if msg.chat.type == "private":
        bot.send_message(msg.chat.id, "Select category:", reply_markup=keyboard())
    else:
        bot.send_message(msg.chat.id, "✅ Bot active")

# ===== BUTTON CLICK =====
@bot.callback_query_handler(func=lambda call: True)
def cb(call):
    send_news(call.message.chat.id)

# ===== TRACK CHANNEL =====
@bot.my_chat_member_handler()
def track(update):
    chat = update.chat
    status = update.new_chat_member.status

    if chat.type == "channel" and status in ["administrator", "member"]:
        channels.add(chat.id)
        save_channels()

# ===== AUTO POST =====
def auto_post():
    for ch in channels:
        try:
            send_news(ch)
        except:
            pass

def scheduler():
    while True:
        auto_post()
        time.sleep(random.randint(600, 900))  # 10–15 min

threading.Thread(target=scheduler, daemon=True).start()

# ===== RUN =====
print("💎 Premium Bot Running...")
bot.infinity_polling()