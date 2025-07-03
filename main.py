import requests
import talib
import numpy as np
import time
import asyncio
import threading
from datetime import datetime, timedelta
import pytz
from quotexapi.stable_api import Quotex
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ===== CONFIGURATION =====
TELEGRAM_TOKEN = "8037637139:AAHjAXxvU8_qEUTUINVaxFCuwljNnriSqh8"
CHAT_ID = "1251491690"
PAKISTAN_TZ = pytz.timezone('Asia/Karachi')
SCAN_INTERVAL = 30
COOLDOWN = 120  # 2 minutes
BOT_RUNNING = False

QUOTEX_ACCOUNTS = [
    {"email": "khattisiddique10@gmail.com", "password": "Mujeeb@12"},
    {"email": "hasseb50@gmail.com", "password": "Haseeb@12"},
    {"email": "haseeb60@gmail.com", "password": "Haseeb@12"},
    {"email": "juman900@gmail.com", "password": "Haseeb@12"},
    {"email": "mujeeb100@gmail.com", "password": "Mujeeb@12"},
    {"email": "siddique87@gmail.com", "password": "Mujeeb@12"},
    {"email": "mujeebb200@gmail.com", "password": "Mujeeb@12"},
    {"email": "mueeb689@gmail.com", "password": "Mujeeb@12"},
    {"email": "mueebb45@gmail.com", "password": "Mujeeb@12"},
    {"email": "mueeg12@gmail.com", "password": "Mujeeb@12"}
]

CURRENT_ACCOUNT_INDEX = 0
qx = None
ROTATION_COUNT = 0
MAX_ROTATION = 10

LIVE_PAIRS = ['EUR/JPY', 'EUR/GBP', 'EUR/CAD', 'GBP/JPY']
OTC_PAIRS = ['EUR/CAD:OTC', 'EUR/JPY:OTC', 'EUR/GBP:OTC', 'USD/JPY:OTC']

SETTINGS = {
    'EUR/JPY': {'ema_fast': 3, 'ema_slow': 9, 'rsi_period': 4, 'rsi_min': 45, 'rsi_max': 55, 'min_atr': 0.0006, 'volume_multiplier': 1.5},
    'EUR/GBP': {'ema_fast': 4, 'ema_slow': 10, 'rsi_period': 5, 'rsi_min': 45, 'rsi_max': 55, 'min_atr': 0.0004, 'volume_multiplier': 1.6},
    'EUR/CAD': {'ema_fast': 5, 'ema_slow': 11, 'rsi_period': 5, 'rsi_min': 45, 'rsi_max': 55, 'min_atr': 0.0005, 'volume_multiplier': 1.4},
    'GBP/JPY': {'ema_fast': 4, 'ema_slow': 9, 'rsi_period': 4, 'rsi_min': 45, 'rsi_max': 55, 'min_atr': 0.0007, 'volume_multiplier': 1.5},
}

def init_quotex():
    global qx, CURRENT_ACCOUNT_INDEX
    creds = QUOTEX_ACCOUNTS[CURRENT_ACCOUNT_INDEX]
    qx = Quotex(email=creds['email'], password=creds['password'])
    connected, reason = asyncio.run(qx.connect())
    if not connected:
        raise Exception(f"Quotex login failed: {reason}")
    print(f"[✔] Connected to Quotex ({creds['email']})")

def rotate_account():
    global CURRENT_ACCOUNT_INDEX, ROTATION_COUNT
    ROTATION_COUNT += 1
    if ROTATION_COUNT >= MAX_ROTATION:
        CURRENT_ACCOUNT_INDEX = (CURRENT_ACCOUNT_INDEX + 1) % len(QUOTEX_ACCOUNTS)
        init_quotex()
        ROTATION_COUNT = 0

def get_alpha_data(pair):
    global qx
    symbol = pair.replace(":OTC", "").replace("/", "")
    try:
        candles = asyncio.run(qx.get_candles(asset=symbol, interval=60, duration=30))
        closes = np.array([c["close"] for c in candles])
        highs = np.array([c["high"] for c in candles])
        lows = np.array([c["low"] for c in candles])
        volumes = np.array([c.get("volume", 1000) for c in candles])
        return closes, highs, lows, volumes
    except Exception as e:
        print(f"Quotex API Error: {e}")
        return None, None, None, None

def generate_elite_signal(pair):
    closes, highs, lows, volumes = get_alpha_data(pair)
    if closes is None or len(closes) < 20:
        return None

    settings = SETTINGS.get(pair.split(':')[0], SETTINGS['EUR/JPY'])
    ema_fast = talib.EMA(closes, settings['ema_fast'])
    ema_slow = talib.EMA(closes, settings['ema_slow'])
    rsi = talib.RSI(closes, settings['rsi_period'])
    atr = talib.ATR(highs, lows, closes, 10)[-1]
    macd, signal, _ = talib.MACD(closes, fastperiod=settings['ema_fast'], slowperiod=settings['ema_slow'])

    confidence = 0
    pass_count = 0

    ema_gap = abs(ema_fast[-1] - ema_slow[-1])
    if ema_gap > settings['min_atr'] * 2:
        confidence += 40
        pass_count += 1
    elif ema_gap > settings['min_atr']:
        confidence += 25
        pass_count += 1

    if settings['rsi_min'] < rsi[-1] < settings['rsi_max']:
        confidence += 30 - abs(rsi[-1] - 50)/2
        pass_count += 1

    if volumes[-1] > np.mean(volumes[-10:]) * settings['volume_multiplier']:
        confidence += 30
        pass_count += 1

    if atr > settings['min_atr']:
        pass_count += 1

    # 👇 UPDATED THRESHOLD AND CONFIDENCE
    if pass_count < 3 or confidence < 80:
        return None

    if ema_fast[-1] > ema_slow[-1] and macd[-1] > signal[-1]:
        return 'UP', confidence
    elif ema_fast[-1] < ema_slow[-1] and macd[-1] < signal[-1]:
        return 'DOWN', confidence

    return None

class EliteTrader:
    def _init_(self):
        self.last_signal_time = 0

    def get_strongest_signal(self):
        is_weekend = datetime.now(PAKISTAN_TZ).weekday() >= 5
        pairs = OTC_PAIRS if is_weekend else ['EUR/JPY', 'EUR/GBP'] + [p for p in LIVE_PAIRS if p not in ['EUR/JPY', 'EUR/GBP']]

        best = None
        best_conf = 0
        for pair in pairs:
            if time.time() - self.last_signal_time < COOLDOWN:
                continue
            signal = generate_elite_signal(pair)
            if signal and signal[1] > best_conf:
                best = (pair, *signal)
                best_conf = signal[1]
        return best

def send_elite_alert(pair, direction, confidence):
    now = datetime.now(PAKISTAN_TZ) + timedelta(seconds=20)
    msg = f"🚀 {direction}\n📊 {pair}\n🕐 Trade at: {now.strftime('%H:%M:%S')}\n✅ Confidence: {confidence:.1f}%"
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={'chat_id': CHAT_ID, 'text': msg, 'parse_mode': 'Markdown'}
        )
    except Exception as e:
        print(f"Telegram send error: {e}")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global BOT_RUNNING
    BOT_RUNNING = True
    await update.message.reply_text("✅ Bot started. Scanning for high-confidence signals...")

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global BOT_RUNNING
    BOT_RUNNING = False
    await update.message.reply_text("⏹ Bot stopped.")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = "✅ Running" if BOT_RUNNING else "⏸ Stopped"
    now = datetime.now(PAKISTAN_TZ).strftime("%Y-%m-%d %H:%M")
    await update.message.reply_text(f"Status: {status}\nTime: {now}\nCurrent Account: {QUOTEX_ACCOUNTS[CURRENT_ACCOUNT_INDEX]['email']}")

def trading_operation():
    trader = EliteTrader()
    while True:
        try:
            if BOT_RUNNING:
                signal = trader.get_strongest_signal()
                if signal:
                    pair, direction, confidence = signal
                    send_elite_alert(pair, direction, confidence)
                    trader.last_signal_time = time.time()
                rotate_account()
            time.sleep(SCAN_INTERVAL)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)

if _name_ == "_main_":
    print("""
🚀 ELITE SIGNAL BOT ACTIVE
- Uses real Quotex data (live/OTC)
- Prioritizes EUR/JPY and EUR/GBP during weekdays
- Sends 1 high-confidence signal every 2 minutes
- Indicators: EMA, MACD, RSI, ATR, Volume
- Telegram commands: /start /stop /status
""")
    init_quotex()
    threading.Thread(target=trading_operation, daemon=True).start()

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("status", status_command))
    app.run_polling()
