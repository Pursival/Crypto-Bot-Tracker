import os
import json
import requests
import asyncio
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ====== Config ======
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
DATA_FILE = "crypto_data.json"
UPDATE_INTERVAL = 60           # seconds

# ====== Load or create saved data ======
try:
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
except:
    data = {
        "xrp_buy": 0.0,
        "sol_buy": 0.0,
        "last_xrp_change": 0.0,
        "last_sol_change": 0.0,
        "last_xrp_price": 0.0,
        "last_sol_price": 0.0,
        "discrepancy_threshold": 2.0,
        "spam_enabled": True,
        "discrepancy_active": False
    }
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# ====== Command Handlers ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Commands:\n"
        "/set_xrp <price> - set XRP buy price\n"
        "/set_sol <price> - set SOL buy price\n"
        "/last - show last ping percentages, prices, and threshold\n"
        "/set_threshold <percent> - set discrepancy threshold\n"
        "/toggle_spam - enable/disable spam alerts"
    )

async def set_xrp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        try:
            value = float(context.args[0])
            data["xrp_buy"] = value
            with open(DATA_FILE, "w") as f:
                json.dump(data, f)
            await update.message.reply_text(f"XRP buy price set to {value} USDT")
        except ValueError:
            await update.message.reply_text("Usage: /set_xrp <price> (number required)")
    else:
        await update.message.reply_text("Usage: /set_xrp <price>")

async def set_sol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        try:
            value = float(context.args[0])
            data["sol_buy"] = value
            with open(DATA_FILE, "w") as f:
                json.dump(data, f)
            await update.message.reply_text(f"SOL buy price set to {value} USDT")
        except ValueError:
            await update.message.reply_text("Usage: /set_sol <price> (number required)")
    else:
        await update.message.reply_text("Usage: /set_sol <price>")

async def last(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = f"""
📊 Last Ping:

XRP: ${data.get('last_xrp_price', 0):.4f} ({data['last_xrp_change']:+.2f}%)
SOL: ${data.get('last_sol_price', 0):.2f} ({data['last_sol_change']:+.2f}%)
Discrepancy: {data['last_xrp_change'] - data['last_sol_change']:+.2f}%
Threshold: {data.get('discrepancy_threshold', 2.0):.2f}%
Spam Enabled: {'Yes' if data.get('spam_enabled', True) else 'No'}
"""
    await update.message.reply_text(msg)

async def set_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        try:
            value = float(context.args[0])
            data["discrepancy_threshold"] = value
            with open(DATA_FILE, "w") as f:
                json.dump(data, f)
            await update.message.reply_text(f"Discrepancy threshold set to {value:.2f}%")
        except ValueError:
            await update.message.reply_text("Usage: /set_threshold <percent> (number required)")
    else:
        await update.message.reply_text("Usage: /set_threshold <percent>")

async def toggle_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data["spam_enabled"] = not data.get("spam_enabled", True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)
    status = "enabled" if data["spam_enabled"] else "disabled"
    await update.message.reply_text(f"Spam alerts are now {status}.")

# ====== Automatic Checker ======
async def auto_update(app):
    while True:
        try:
            xrp = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=XRPUSDT", timeout=10).json()
            sol = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=SOLUSDT", timeout=10).json()

            xrp_price = float(xrp["price"])
            sol_price = float(sol["price"])

            xrp_change = (xrp_price - data["xrp_buy"]) / data["xrp_buy"] * 100 if data["xrp_buy"] > 0 else 0
            sol_change = (sol_price - data["sol_buy"]) / data["sol_buy"] * 100 if data["sol_buy"] > 0 else 0

            data["last_xrp_change"] = xrp_change
            data["last_sol_change"] = sol_change
            data["last_xrp_price"] = xrp_price
            data["last_sol_price"] = sol_price

            discrepancy = xrp_change - sol_change
            abs_discrepancy = abs(discrepancy)
            threshold = data.get("discrepancy_threshold", 2.0)

            if data.get("spam_enabled", True):
                if abs_discrepancy >= threshold:
                    leader = "XRP ahead" if discrepancy > 0 else "SOL ahead"
                    msg = (
                        f"⚡ Discrepancy ongoing ⚡\n"
                        f"XRP: ${xrp_price:.4f} ({xrp_change:+.2f}%) | "
                        f"SOL: ${sol_price:.2f} ({sol_change:+.2f}%)\n"
                        f"Discrepancy: {discrepancy:+.2f}% ({leader}, Threshold: {threshold:.2f}%)"
                    )
                    await app.bot.send_message(chat_id=CHAT_ID, text=msg)
                    data["discrepancy_active"] = True
                elif data.get("discrepancy_active", False) and abs_discrepancy < threshold:
                    msg = f"✅ Discrepancy cleared. XRP: {xrp_change:+.2f}%, SOL: {sol_change:+.2f}%, Discrepancy: {discrepancy:+.2f}%"
                    await app.bot.send_message(chat_id=CHAT_ID, text=msg)
                    data["discrepancy_active"] = False

            with open(DATA_FILE, "w") as f:
                json.dump(data, f)

        except Exception as e:
            print("Error fetching prices:", e)

        await asyncio.sleep(UPDATE_INTERVAL)

# ====== Flask Web Server for UptimeRobot ======
flask_app = Flask("")

@flask_app.route("/")
def home():
    return "Bot is running!"

def run_flask():
    flask_app.run(host="0.0.0.0", port=3000)

# ====== Run Bot ======
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("set_xrp", set_xrp))
app.add_handler(CommandHandler("set_sol", set_sol))
app.add_handler(CommandHandler("last", last))
app.add_handler(CommandHandler("set_threshold", set_threshold))
app.add_handler(CommandHandler("toggle_spam", toggle_spam))

async def main():
    # Start Flask in a separate thread
    threading.Thread(target=run_flask).start()
    # Start automatic updates
    asyncio.create_task(auto_update(app))
    # Start the Telegram bot
    await app.start()
    await app.updater.start_polling()
    await app.updater.idle()

asyncio.run(main())
