import os
import json
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ====== Config ======
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
DATA_FILE = "crypto_data.json"

# ====== Load or create saved prices ======
try:
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
except:
    data = {"xrp_buy": 0.0, "sol_buy": 0.0}
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# ====== Command Handlers ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /set_xrp, /set_sol to set buy prices and /status to see gains.")

async def set_xrp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        value = float(context.args[0])
        data["xrp_buy"] = value
        with open(DATA_FILE, "w") as f:
            json.dump(data, f)
        await update.message.reply_text(f"XRP buy price set to {value} USDT")
    except:
        await update.message.reply_text("Usage: /set_xrp <price>")

async def set_sol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        value = float(context.args[0])
        data["sol_buy"] = value
        with open(DATA_FILE, "w") as f:
            json.dump(data, f)
        await update.message.reply_text(f"SOL buy price set to {value} USDT")
    except:
        await update.message.reply_text("Usage: /set_sol <price>")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        xrp = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=XRPUSDT").json()
        sol = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=SOLUSDT").json()

        xrp_price = float(xrp["price"])
        sol_price = float(sol["price"])

        xrp_change = (xrp_price - data["xrp_buy"]) / data["xrp_buy"] * 100 if data["xrp_buy"] > 0 else 0
        sol_change = (sol_price - data["sol_buy"]) / data["sol_buy"] * 100 if data["sol_buy"] > 0 else 0

        msg = f"""
📊 Crypto Status:

XRP: {xrp_price:.4f} USDT
Change: {xrp_change:.2f} %

SOL: {sol_price:.2f} USDT
Change: {sol_change:.2f} %
"""
        await update.message.reply_text(msg)
    except:
        await update.message.reply_text("Error fetching prices.")

# ====== Run Bot ======
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("set_xrp", set_xrp))
app.add_handler(CommandHandler("set_sol", set_sol))
app.add_handler(CommandHandler("status", status))

app.run_polling()
