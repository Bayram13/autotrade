import os
import re
import time
import hmac
import hashlib
import requests
from telethon import TelegramClient, events
from dotenv import load_dotenv

# .env faylını yüklə
load_dotenv()

TG_API_ID = int(os.getenv("TG_API_ID"))
TG_API_HASH = os.getenv("TG_API_HASH")
SESSION_NAME = os.getenv("SESSION_NAME", "bingx_bot")

BINGX_API_KEY = os.getenv("BINGX_API_KEY")
BINGX_SECRET_KEY = os.getenv("BINGX_SECRET_KEY")
SOURCE_CHAT = os.getenv("SOURCE_CHAT")
TRADE_QTY = float(os.getenv("TRADE_QTY", 0.01))

# ===== BingX imza funksiyası =====
def sign(params):
    query = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
    return hmac.new(BINGX_SECRET_KEY.encode(), query.encode(), hashlib.sha256).hexdigest()

# ===== BingX əməliyyat açma funksiyası =====
def place_order(symbol, side, price, qty):
    url = "https://open-api.bingx.com/openApi/swap/v2/trade/order"
    params = {
        "symbol": symbol,
        "side": side,  # BUY = Long, SELL = Short
        "price": price,
        "type": "LIMIT",
        "quantity": qty,
        "timestamp": int(time.time() * 1000)
    }
    params["signature"] = sign(params)
    headers = {"X-BX-APIKEY": BINGX_API_KEY}
    r = requests.post(url, params=params, headers=headers)
    print("📤 BingX cavabı:", r.json())

# ===== Siqnal mesajını analiz et =====
def parse_signal(msg):
    try:
        # Coin simvolu (BTCUSDT, MAGICUSDT və s.)
        symbol = re.search(r'([A-Z]{3,10}USDT)', msg).group(1)

        # LONG / SHORT tapmaq
        side = 'BUY' if 'LONG' in msg.upper() else 'SELL'

        # GİRİŞ və ya ENTRY
        entry = re.search(r'(GİRİŞ|ENTRY)[: ]+([\d\.,]+)', msg, re.IGNORECASE)
        entry = float(entry.group(2).replace(",", ".")) if entry else None

        # TP (Take Profit)
        tp = re.search(r'TP[: ]+([\d\.,]+)', msg, re.IGNORECASE)
        tp = float(tp.group(1).replace(",", ".")) if tp else None

        # SL (Stop Loss)
        sl = re.search(r'SL[: ]+([\d\.,]+)', msg, re.IGNORECASE)
        sl = float(sl.group(1).replace(",", ".")) if sl else None

        return symbol, side, entry, tp, sl
    except Exception as e:
        print("❌ Siqnal pars edilmədi:", e)
        return None

# ===== Telegram Client =====
client = TelegramClient(SESSION_NAME, TG_API_ID, TG_API_HASH)

@client.on(events.NewMessage(chats=int(SOURCE_CHAT)))
async def handler(event):
    msg = event.message.message
    signal = parse_signal(msg)
    if signal:
        symbol, side, entry, tp, sl = signal
        print(f"📩 Siqnal: {symbol} {side} Entry={entry} TP={tp} SL={sl}")
        place_order(symbol.replace("USDT", "-USDT"), side, entry, TRADE_QTY)

client.start()
print("🚀 Bot işə düşdü - Render versiyası çalışır...")
client.run_until_disconnected()
