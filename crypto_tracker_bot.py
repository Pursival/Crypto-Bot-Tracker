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
UPDATE_INTERVAL = 300          # seconds (5 minutes)

# CoinGecko ID map for common symbols
COIN_IDS = {
    "XRP":  "ripple",
    "SOL":  "solana",
    "BTC":  "bitcoin",
    "ETH":  "ethereum",
    "BNB":  "binancecoin",
    "ADA":  "cardano",
    "DOGE": "dogecoin",
    "DOT":  "polkadot",
    "AVAX": "avalanche-2",
    "MATIC":"matic-network",
    "LINK": "chainlink",
    "LTC":  "litecoin",
    "UNI":  "uniswap",
    "ATOM": "cosmos",
    "XLM":  "stellar",
}

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
        "discrepancy_active": False,
        "bought_coin": "XRP",
        "bought_price": 0.0,
        "sold_coin": "SOL",
        "sold_price": 0.0,
    }
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# Ensure position keys exist for older saved data
for key, default in [("bought_coin", "XRP"), ("bought_price", 0.0),
                      ("sold_coin", "SOL"), ("sold_price", 0.0)]:
    data.setdefault(key, default)

# ====== Price Fetcher ======
def fetch_coingecko_prices(symbols: list[str]) -> dict[str, float]:
    ids = []
    sym_to_id = {}
    for sym in symbols:
        cg_id = COIN_IDS.get(sym.upper())
        if cg_id:
            ids.append(cg_id)
            sym_to_id[cg_id] = sym.upper()
        else:
            raise ValueError(f"Unknown coin symbol: {sym}. Supported: {', '.join(COIN_IDS)}")
    resp = requests.get(
        f"https://api.coingecko.com/api/v3/simple/price?ids={','.join(ids)}&vs_currencies=usd",
        timeout=10
    ).json()
    return {sym_to_id[cg_id]: float(resp[cg_id]["usd"]) for cg_id in ids}

def fetch_xrp_sol_prices():
    prices = fetch_coingecko_prices(["XRP", "SOL"])
    return prices["XRP"], prices["SOL"]

# ====== Command Handlers ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Commands:\n"
        "/set_xrp <price> - set XRP buy price\n"
        "/set_sol <price> - set SOL buy price\n"
        "/set_position <bought|sold> <coin> <price> - set a position\n"
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

async def set_position(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 3:
        await update.message.reply_text("Usage: /set_position <bought|sold> <coin> <price>")
        return

    action, coin, price_str = context.args
    coin = coin.upper()

    if coin not in COIN_IDS:
        await update.message.reply_text(
            f"Unknown coin '{coin}'.\nSupported: {', '.join(COIN_IDS)}"
        )
        return

    try:
        price = float(price_str)
    except ValueError:
        await update.message.reply_text("Price must be a number.")
        return

    if action.lower() == "bought":
        data["bought_coin"] = coin
        data["bought_price"] = price
        await update.message.reply_text(f"Bought {coin} at {price} USDT")
    elif action.lower() == "sold":
        data["sold_coin"] = coin
        data["sold_price"] = price
        await update.message.reply_text(f"Sold {coin} at {price} USDT")
    else:
        await update.message.reply_text("Action must be 'bought' or 'sold'.")
        return

    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

async def last(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        f"📊 Last Ping:\n\n"
        f"XRP: ${data.get('last_xrp_price', 0):.4f} ({data['last_xrp_change']:+.2f}%)\n"
        f"SOL: ${data.get('last_sol_price', 0):.2f} ({data['last_sol_change']:+.2f}%)\n"
        f"Discrepancy: {data['last_xrp_change'] - data['last_sol_change']:+.2f}%\n"
        f"Threshold: {data.get('discrepancy_threshold', 2.0):.2f}%\n"
        f"Spam Enabled: {'Yes' if data.get('spam_enabled', True) else 'No'}\n\n"
        f"Position — Bought: {data.get('bought_coin', '—')} @ {data.get('bought_price', 0):.4f}\n"
        f"Position — Sold:   {data.get('sold_coin', '—')} @ {data.get('sold_price', 0):.4f}"
    )
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
            # Fetch XRP + SOL for /last command
            xrp_price, sol_price = fetch_xrp_sol_prices()
            xrp_change = (xrp_price - data["xrp_buy"]) / data["xrp_buy"] * 100 if data["xrp_buy"] > 0 else 0
            sol_change = (sol_price - data["sol_buy"]) / data["sol_buy"] * 100 if data["sol_buy"] > 0 else 0
            data["last_xrp_change"] = xrp_change
            data["last_sol_change"] = sol_change
            data["last_xrp_price"] = xrp_price
            data["last_sol_price"] = sol_price

            # Fetch bought/sold position coins
            bought_coin = data.get("bought_coin", "XRP")
            sold_coin = data.get("sold_coin", "SOL")
            bought_price_ref = data.get("bought_price", 0.0)
            sold_price_ref = data.get("sold_price", 0.0)

            coins_needed = list({bought_coin, sold_coin})
            prices = fetch_coingecko_prices(coins_needed)

            bought_current = prices[bought_coin]
            sold_current = prices[sold_coin]

            bought_change = (bought_current - bought_price_ref) / bought_price_ref * 100 if bought_price_ref > 0 else 0
            sold_change = (sold_current - sold_price_ref) / sold_price_ref * 100 if sold_price_ref > 0 else 0

            profit_discrepancy = bought_change - sold_change
            threshold = data.get("discrepancy_threshold", 2.0)

            # Alert only when bought coin is outperforming sold coin by threshold
            if data.get("spam_enabled", True) and profit_discrepancy >= threshold:
                await app.bot.send_message(
                    chat_id=CHAT_ID,
                    text=(
                        f"💰 Profit opportunity!\n"
                        f"{bought_coin}: ${bought_current:.4f} ({bought_change:+.2f}%)\n"
                        f"{sold_coin}: ${sold_current:.4f} ({sold_change:+.2f}%)\n"
                        f"Discrepancy: {profit_discrepancy:+.2f}%"
                    )
                )

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
app.add_handler(CommandHandler("set_position", set_position))
app.add_handler(CommandHandler("last", last))
app.add_handler(CommandHandler("set_threshold", set_threshold))
app.add_handler(CommandHandler("toggle_spam", toggle_spam))

async def main():
    # Start Flask in a separate thread
    threading.Thread(target=run_flask, daemon=True).start()
    # Initialize and run bot
    async with app:
        await app.start()
        await app.updater.start_polling()
        # Start automatic price checker
        asyncio.create_task(auto_update(app))
        # Keep running forever (idle() uses OS signals that don't work on Replit)
        await asyncio.Event().wait()

asyncio.run(main())
