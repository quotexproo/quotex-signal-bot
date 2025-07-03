# 📈 Quotex Elite Signal Bot

A high-accuracy Telegram signal bot for *Quotex binary trading, using **real-time market data* and smart indicators like *EMA, **MACD, **RSI, **ATR, and **Volume*.

---

## ✅ Features

- 💡 Sends 1 *high-confidence signal every 2 minutes*
- 🤖 Uses *3-of-5 indicator threshold* with *80% min confidence*
- 🔁 Rotates across 10 Quotex accounts (auto anti-ban)
- 📊 Live & OTC market data
- 📆 Uses *EUR/JPY & EUR/GBP* as priority on weekdays, OTC on weekends
- 📲 Sends signals via Telegram
- 🛠️ Built to run on *Render (free)* or *Replit*

---

## 📦 Tech Stack

- Python 3
- ta-lib for technical indicators
- quotexapi for data
- python-telegram-bot for Telegram integration

---

## 🚀 Deploy on Render

1. Fork or upload this repo to GitHub
2. Go to [https://render.com](https://render.com)
3. Create a *New Web Service*
4. Link your GitHub repo
5. Set:
   - *Build Command:* pip install -r requirements.txt
   - *Start Command:* python main.py
6. Deploy and let it run 24/7

---

## ⚙️ Telegram Commands

| Command     | Description                       |
|-------------|-----------------------------------|
| /start    | Starts scanning and sending signals |
| /stop     | Stops signal scanning             |
| /status   | Shows bot status and account info |

---

## 📁 Files
