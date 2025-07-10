import os, random, logging, sqlite3, requests, zipfile, io
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
DRIVE_FILE_ID = os.getenv("DRIVE_FILE_ID")
ADMIN_IDS = [123456789]
MEME_FOLDER = "memes"

logging.basicConfig(level=logging.INFO)

# Auto-download & sort meme pack
def download_meme_pack():
    if not DRIVE_FILE_ID: return
    r = requests.get(f"https://drive.google.com/uc?export=download&id={DRIVE_FILE_ID}")
    if r.status_code == 200:
        z = zipfile.ZipFile(io.BytesIO(r.content))
        z.extractall("memes/imported")
        logging.info("Downloaded meme pack.")
    else:
        logging.error("Failed to download meme pack.")
        import threading
import os
import time

# Exit after N seconds (e.g., 43200 sec = 12 hours)
def self_shutdown():
    time.sleep(43200)  # 12 hours
    print("🛑 Shutting down to conserve Railway hours.")
    os._exit(0)

threading.Thread(target=self_shutdown).start()


def sort_imported_memes():
    src = "memes/imported"
    for root, _, files in os.walk(src):
        for f in files:
            low = f.lower()
            cat = "default"
            if "happy" in low: cat = "happy"
            elif "sad" in low: cat = "sad"
            elif "dark" in low or "dkmh" in low: cat = "dark"
            dst = os.path.join(MEME_FOLDER, cat)
            os.makedirs(dst, exist_ok=True)
            os.rename(os.path.join(root, f), os.path.join(dst, f))
    logging.info("Sorted imported memes.")
    
download_meme_pack()
sort_imported_memes()

# DB
conn = sqlite3.connect("memory.db", check_same_thread=False)
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS memory (user_id INTEGER, message TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)""")
conn.commit()

def save_message(uid, txt):
    c.execute("INSERT INTO memory VALUES (?, ?)", (uid, txt))
    conn.commit()

def get_user_history(uid, lim=10):
    c.execute("SELECT message FROM memory WHERE user_id=? ORDER BY timestamp DESC LIMIT ?", (uid, lim))
    return [r[0] for r in c.fetchall()][::-1]

def generate_reply(hist):
    last = hist[-1].lower() if hist else ""
    if "sad" in last: return "Feeling down?", "sad"
    if "happy" in last: return "That’s awesome!", "happy"
    if "dkmh" in last or "dark" in last: return "Embrace the darkness.", "dark"
    return "I hear you.", "default"

def get_meme(cat):
    fld = os.path.join(MEME_FOLDER, cat)
    if not os.path.isdir(fld): return None
    pics = [f for f in os.listdir(fld) if f.lower().endswith((".jpg",".png"))]
    return os.path.join(fld, random.choice(pics)) if pics else None

# Handlers
async def handle_message(u, ctx):
    uid = u.effective_user.id
    txt = u.message.text
    save_message(uid, txt)
    hist = get_user_history(uid)
    resp, cat = generate_reply(hist)
    meme = get_meme(cat)
    if meme: await ctx.bot.send_photo(u.effective_chat.id, photo=InputFile(meme), caption=resp)
    else: await u.message.reply_text(resp)

async def start(u, ctx): await u.message.reply_text("👋 Say anything!")
async def help_cmd(u, ctx): await u.message.reply_text("/meme <cat> | /broadcast")

async def meme_cmd(u, ctx):
    if ctx.args:
        m = get_meme(ctx.args[0].lower())
        if m: await u.message.reply_photo(photo=InputFile(m))
        else: await u.message.reply_text("No such category.")
    else: await u.message.reply_text("Usage: /meme [happy|sad|dark]")

async def broadcast(u, ctx):
    if u.effective_user.id not in ADMIN_IDS:
        return await u.message.reply_text("🚫 Not admin.")
    msg = " ".join(ctx.args)
    for (uid,) in c.execute("SELECT DISTINCT user_id FROM memory"):
        try: await ctx.bot.send_message(uid, msg)
        except: pass
    await u.message.reply_text("Broadcast sent.")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("meme", meme_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__": main()
