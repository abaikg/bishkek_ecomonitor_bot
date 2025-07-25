# config.py
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AQICN_API_KEY = os.getenv("AQICN_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в .env файле!")
if not AQICN_API_KEY:
    raise ValueError("AQICN_API_KEY не найден в .env файле! Данные о качестве воздуха могут быть недоступны.")
