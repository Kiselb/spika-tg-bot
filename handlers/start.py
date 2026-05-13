from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config import WELCOME_MESSAGE
from api_client import api
from handlers.survey import start_extra_survey

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    telegram_id = message.from_user.id
    telegram_nick = message.from_user.username or message.from_user.full_name

    await message.answer("Выполняется вход...")

    resp = await api.telegram_login(telegram_id, telegram_nick)
    if resp["status"] == 200:
        data = resp["data"]
        token = data.get("access_token")
        if token:
            await state.update_data(access_token=token)
            await message.answer(f"Вход выполнен успешно.\n\n{WELCOME_MESSAGE}")
            await start_extra_survey(message, state)   # начинаем с доп. вопросов
            return

    await message.answer("Ошибка подключения. Попробуйте позже.")
