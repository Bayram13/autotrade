from telethon import TelegramClient, events
import re
import requests
import time
import hmac
import hashlib
import os
from dotenv import load_dotenv

# ====== .env faylını yüklə ======
load_dotenv()

# ====== Telegram API məlumatları ======
TG_API_ID = int(os.getenv("TG_API_ID"))
TG_API_HASH = os.getenv("TG_API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Telegram Bot Token
SESSION_NAME = "bingx_bot"

# ====== BingX API məlumatları ======
API_KEY = os.getenv("BINGX_API_KEY")
SECRET_KEY = os.getenv("BINGX_SECRET_KEY")

# ====== Siqnal gələn qrup ID və ya istifadəçi adı ======
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

# ====== Siqnal mesajını oxuma ======
def parse_signal(msg):
    try:
        # Simvol (BTCUSDT, SXTUSDT və s.)
        symbol_match = re.search(r'([A-Z]{3,5}USDT)', msg)
        if not symbol_match:
            return None
        symbol = symbol_match.group(1)

        # Yön (LONG/SHORT → BUY/SELL)
        if "LONG" in msg.upper():
            side = "BUY"
        elif "SHORT" in msg.upper():
            side = "SELL"
        else:
            return None

        # Giriş qiyməti
        entry_match = re.search(r'(GİRİŞ|ENTRY)[: ]+(\d+\.?\d*)', msg, re.IGNORECASE)
        if not entry_match:
            return None
        entry = float(entry_match.group(2))

        # TP qiyməti
        tp_match = re.search(r'TP[: ]+(\d+\.?\d*)', msg, re.IGNORECASE)
        tp = float(tp_match.group(1)) if tp_match else None

        # SL qiyməti
        sl_match = re.search(r'SL[: ]+(\d+\.?\d*)', msg, re.IGNORECASE)
        sl = float(sl_match.group(1)) if sl_match else None

        return symbol, side, entry, tp, sl
    except Exception as e:
        print("❌ Parse xətası:", e)
        return None

# ====== Telegram Client (Bot Token ilə) ======
client = TelegramClient(SESSION_NAME, TG_API_ID, TG_API_HASH).start(bot_token=BOT_TOKEN)

@client.on(events.NewMessage(chats=SOURCE_CHAT))
async def handler(event):
    msg = event.message.message
    signal = parse_signal(msg)
    if signal:
        symbol, side, entry, tp, sl = signal
        print(f"✅ Siqnal tapıldı: {symbol} {side} Entry={entry} TP={tp} SL={sl}")
        # Məsələn 0.01 miqdar ilə əməliyyat açır
        place_order(symbol.replace("USDT", "-USDT"), side, entry, 0.01)

print("📡 Bot işə düşdü... Siqnalları gözləyir.")
client.run_until_disconnected()
