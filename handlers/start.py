from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config import WELCOME_MESSAGE
from handlers.states import AuthStates
from api_client import api
from utils import generate_password, is_valid_email  # нужно будет создать utils.py
from handlers.survey import create_and_start_survey  # импортируем функцию из survey.py

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    telegram_id = message.from_user.id
    await message.answer("Выполняется вход...")

    resp = await api.telegram_login(telegram_id)
    if resp["status"] == 200:
        data = resp["data"]
        token = data.get("access_token")
        if token:
            await state.update_data(access_token=token)
            await message.answer("Вход выполнен успешно. Создаю опрос...")
            await create_and_start_survey(message, state, token)
            return
    elif resp["status"] == 404:
        await message.answer(WELCOME_MESSAGE)
        await state.set_state(AuthStates.waiting_for_email)
        return

    await message.answer("Ошибка подключения. Попробуйте позже.")

@router.message(AuthStates.waiting_for_email)
async def process_email(message: Message, state: FSMContext):
    email = message.text.strip() if message.text else ""
    if not is_valid_email(email):
        await message.answer("Некорректный e-mail. Введите действительный адрес:")
        return

    password = generate_password()
    telegram_nick = message.from_user.username or message.from_user.full_name
    telegram_id = message.from_user.id

    await message.answer(
        f"Ваш пароль для входа на сайт: {password}\n\n"
        "⚠️ <b>Обязательно сохраните пароль в надёжном месте!</b>\n"
        "Не передавайте его третьим лицам.",
        parse_mode="HTML",
    )

    resp = await api.register_user(email, telegram_nick, telegram_id, password)
    if resp["status"] == 200:
        token = resp["data"].get("access_token")
        if token:
            await state.update_data(access_token=token)
            await message.answer("Регистрация успешна. Создаю опрос...")
            await create_and_start_survey(message, state, token)
            return
    if resp["status"] == 400:
        await message.answer("Пользователь с таким e-mail уже зарегистрирован. Попробуйте /start заново.")
        return
    await message.answer("Ошибка регистрации. Попробуйте /start заново.")
    await state.clear()