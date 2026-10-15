import os
import time
import requests
import pandas as pd

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

BASE_URL = "https://api.binance.com/api/v3/klines"

last_signal = None

def get_data(interval):
    response = requests.get(
        BASE_URL,
        params={
            "symbol": "BTCUSDT",
            "interval": interval,
            "limit": 100
        },
        timeout=15
    )
    response.raise_for_status()

    data = response.json()
    df = pd.DataFrame(data, columns=[
        "time", "open", "high", "low", "close",
        "volume", "close_time", "quote_volume",
        "trades", "taker_buy", "taker_quote", "ignore"
    ])

    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)

    return df

def analyze(interval):
    df = get_data(interval)

    # آخرین کندل بسته‌شده
    close = df["close"].iloc[:-1]
    high = df["high"].iloc[:-1]
    low = df["low"].iloc[:-1]

    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))

    price = close.iloc[-1]
    rsi_now = rsi.iloc[-1]

    if ema20.iloc[-1] > ema50.iloc[-1] and 50 < rsi_now < 70:
        return "LONG", price

    if ema20.iloc[-1] < ema50.iloc[-1] and 30 < rsi_now < 50:
        return "SHORT", price

    return "WAIT", price

def send_message(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={"chat_id": CHAT_ID, "text": message},
        timeout=15
    )
    response.raise_for_status()

def main():
    global last_signal

    if not TOKEN or not CHAT_ID:
        raise ValueError("TELEGRAM_TOKEN یا CHAT_ID تنظیم نشده است.")

    send_message("ربات تحلیل BTC/USDT فعال شد.")

    while True:
        try:
            signal15, price = analyze("15m")
            signal1h, _ = analyze("1h")

            if signal15 == signal1h and signal15 in ("LONG", "SHORT"):
                signal_key = (signal15, round(price, 1))

                if signal_key != last_signal:
                    message = (
                        f"BTC/USDT | {signal15}\n"
                        f"قیمت: {price:.2f} USDT\n"
                        f"تأیید: تایم‌فریم ۱۵ دقیقه و ۱ ساعت\n"
                        "این سیگنال قطعی نیست؛ قبل از معامله بررسی کن."
                    )
                    send_message(message)
                    last_signal = signal_key

            print
