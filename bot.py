import os
import re
import threading
from fastapi import FastAPI
from telethon import TelegramClient, events
from pybit.unified_trading import HTTP
from dotenv import load_dotenv
import uvicorn

load_dotenv()

# ==== Telegram API ====
TG_API_ID = int(os.getenv("TG_API_ID"))
TG_API_HASH = os.getenv("TG_API_HASH")
SESSION_NAME = os.getenv("SESSION_NAME", "bybit_bot")
SOURCE_CHAT = int(os.getenv("SOURCE_CHAT_ID"))

# ==== Bybit API ====
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")

# ==== Bybit Testnet client ====
session = HTTP(
    testnet=True,
    api_key=BYBIT_API_KEY,
    api_secret=BYBIT_API_SECRET
)

# ==== Telegram Client ====
client = TelegramClient(SESSION_NAME, TG_API_ID, TG_API_HASH)

# ==== Mesajdan məlumat çıxarma ====
def parse_signal(msg):
    try:
        # Nümunə: BTCUSDT LONG Entry: 68000 TP: 69000 SL: 67000
        symbol_match = re.search(r'([A-Z]{3,5}USDT)', msg)
        side = "Buy" if "LONG" in msg.upper() else "Sell"
        entry_match = re.search(r'(\d+\.?\d+)', msg)

        if not symbol_match or not entry_match:
            return None

        symbol = symbol_match.group(1)
        entry = float(entry_match.group(1))
        return symbol, side, entry
    except Exception:
        return None

# ==== Bybit-də əməliyyat aç ====
def place_order(symbol, side, price, qty):
    try:
        print(f"[Bybit] Order göndərilir: {symbol} {side} {price} {qty}")
        result = session.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            orderType="Limit",
            qty=qty,
            price=price,
            timeInForce="GTC",
            reduceOnly=False
        )
        print("Bybit cavabı:", result)
    except Exception as e:
        print("[Xəta] Order açıla bilmədi:", e)

# ==== Telegram siqnal izləmə ====
@client.on(events.NewMessage(chats=SOURCE_CHAT))
async def handler(event):
    msg = event.message.message
    signal = parse_signal(msg)
    if signal:
        symbol, side, entry = signal
        print(f"Siqnal tapıldı: {symbol} {side} Entry={entry}")
        place_order(symbol, side, entry, 0.01)

# ==== Botu ayrıca thread-də işə sal ====
def run_telegram_bot():
    client.start()
    print("🚀 Telegram bot işə düşdü...")
    client.run_until_disconnected()

# ==== FastAPI server ====
app = FastAPI()

@app.get("/")
def home():
    return {"status": "ok", "message": "Bybit Testnet Auto-Trading Bot is running"}

# ==== Əsas giriş nöqtəsi ====
if __name__ == "__main__":
    threading.Thread(target=run_telegram_bot).start()
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
