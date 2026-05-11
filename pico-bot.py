# pico_bot_proxy.py
import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.client.session.aiohttp import AiohttpSession
from dotenv import load_dotenv

load_dotenv()
BOT_SECRET_KEY = os.getenv("BOT_SECRET_KEY")

# Настройки прокси
PROXY_URL = "socks5://127.0.0.1:10808"  # замените на ваш порт, если нужно
# Если V2rayN использует HTTP-прокси, то:
# PROXY_URL = "http://127.0.0.1:10809"

def get_bot():
    session = AiohttpSession(proxy=PROXY_URL)
    return Bot(token=BOT_SECRET_KEY, session=session)

bot = get_bot()
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Hello world! (прокси работает)")

async def main():
    await dp.start_polling(bot)
    await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
