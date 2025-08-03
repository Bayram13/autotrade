import os
import re
import time
import hmac
import hashlib
import requests
import threading
from telethon import TelegramClient, events
from flask import Flask
from dotenv import load_dotenv

# ====== ENV faylını yüklə ======
load_dotenv()

# ====== Telegram API məlumatları ======
TG_API_ID = int(os.getenv("TG_API_ID"))
TG_API_HASH = os.getenv("TG_API_HASH")
SESSION_NAME = 'bingx_bot'

# ====== BingX API məlumatları ======
API_KEY = os.getenv("BINGX_API_KEY")
SECRET_KEY = os.getenv("BINGX_SECRET_KEY")

# ====== Siqnal gələn qrup ======
SOURCE_CHAT = int(os.getenv("SOURCE_CHAT_ID"))  # məsələn: -1001234567890

# ====== BingX imza funksiyası ======
def sign(params):
    query = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
    return hmac.new(SECRET_KEY.encode(), query.encode(), hashlib.sha256).hexdigest()

# ====== BingX-də əməliyyat açmaq ======
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
    headers = {"X-BX-APIKEY": API_KEY}
    r = requests.post(url, params=params, headers=headers)
    print("📤 BingX cavabı:", r.json())

# ====== Mesajdan məlumat çıxarma ======
def parse_signal(msg):
    try:
        # Simvolu tap (məs: SXTUSDT)
        symbol = re.search(r'([A-Z]{3,5}USDT)', msg).group(1)
        # Long / Short müəyyən et
        side = 'BUY' if 'LONG' in msg.upper() else 'SELL'
        # Entry qiyməti
        entry = float(re.search(r'(GİRİŞ|ENTRY)[: ]+(\d+\.?\d*)', msg, re.IGNORECASE).group(2))
        # TP / SL
        tp = re.search(r'TP[: ]+(\d+\.?\d*)', msg, re.IGNORECASE)
        sl = re.search(r'SL[: ]+(\d+\.?\d*)', msg, re.IGNORECASE)
        tp = float(tp.group(1)) if tp else None
        sl = float(sl.group(1)) if sl else None
        return symbol, side, entry, tp, sl
    except:
        return None

# ====== Telegram Client ======
client = TelegramClient(SESSION_NAME, TG_API_ID, TG_API_HASH)

@client.on(events.NewMessage(chats=SOURCE_CHAT))
async def handler(event):
    msg = event.message.message
    signal = parse_signal(msg)
    if signal:
        symbol, side, entry, tp, sl = signal
        print(f"✅ Siqnal tapıldı: {symbol} {side} Entry={entry} TP={tp} SL={sl}")
        place_order(symbol.replace("USDT", "-USDT"), side, entry, 0.01)

# ====== Telegram botu arxa planda işə sal ======
def start_telegram():
    client.start()
    print("📡 Telegram bot başladı...")
    client.run_until_disconnected()

threading.Thread(target=start_telegram, daemon=True).start()

# ====== Flask Web Server ======
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Bot işləyir və Telegram siqnallarını izləyir."

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
