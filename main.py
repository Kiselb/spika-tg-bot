import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.types import BotCommand
from config import BOT_TOKEN, PROXY_URL
from api_client import api
from handlers.start import router as start_router
from handlers.survey import router as survey_router

async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Запустить бота / начать опрос")
    ]
    await bot.set_my_commands(commands)

async def main():
    session = AiohttpSession(proxy=PROXY_URL)
    bot = Bot(token=BOT_TOKEN, session=session)
    dp = Dispatcher()
    dp.include_router(start_router)
    dp.include_router(survey_router)

    await set_commands(bot)

    try:
        await dp.start_polling(bot)
    finally:
        await api.close()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
