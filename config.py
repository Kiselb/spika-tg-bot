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
    "Этот бот поможет вам лучше понять себя через серию вопросов, разработанных на основе методологии Spiral Dynamics.\n\n"
    "Данный бот разрабатывается в рамках стажировки Университета Искусственного Интеллекта по проекту SPIKA.\n\n"
    "Необходимо ответить на 5 вопросов и пройти опрос из 38 вопросов, чтобы получить персональный профиль мышления и ценностей. \n\n"
    "Чтобы начать, нажмите /start.\n")

EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
