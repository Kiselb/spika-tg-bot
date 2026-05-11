import os
import re
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_SECRET_KEY")
BOT_SECRET_KEY = os.getenv("BOT_SECRET_KEY")

AUTH_BASE_URL = "https://spika.legion.ru"
API_BASE_URL = "https://spika.legion.ru"

PROXY_URL = "socks5://127.0.0.1:10808"

WELCOME_MESSAGE = (
    "Добро пожаловать в AI-Диагностику Мышления и Ценностей!\n"
    "Для начала работы нам потребуется ваш e-mail."
)

EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
