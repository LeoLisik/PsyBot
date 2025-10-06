import logging
from logging.handlers import RotatingFileHandler
import os

# === Папка для логов (создаётся, если нет) ===
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# === Основной лог-файл ===
LOG_FILE = os.path.join(LOG_DIR, "bot.log")

# === Формат вывода ===
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# === Настройка логгера ===
logging.basicConfig(
    level=logging.DEBUG,
    format=LOG_FORMAT,
    datefmt=DATE_FORMAT,
    handlers=[
        # 1️⃣ В консоль (для docker logs)
        logging.StreamHandler(),
        # 2️⃣ В файл с ротацией
        RotatingFileHandler(LOG_FILE, maxBytes=5_000_000, backupCount=5, encoding="utf-8")
    ],
)

# Получаем экземпляр логгера
logger = logging.getLogger("psybot")
