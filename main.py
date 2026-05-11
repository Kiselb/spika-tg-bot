import asyncio
import os
import re
import secrets
import string
from typing import Any, Dict, List, Optional

import aiohttp
from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from dotenv import load_dotenv

# Загрузка переменных окружения из .env
load_dotenv()

# ---------- Конфигурация ----------
BOT_TOKEN = os.getenv("BOT_SECRET_KEY")
BOT_SECRET_KEY = os.getenv("BOT_SECRET_KEY")

# Базовые URL (в соответствии с заданием: telegram-login на .com, остальное на .ru)
AUTH_BASE_URL = "https://spika.legion.ru"
API_BASE_URL = "https://spika.legion.ru"

WELCOME_MESSAGE = (
    "Добро пожаловать в AI-Диагностику Мышления и Ценностей!\n"
    "Для начала работы нам потребуется ваш e-mail."
)

# Regex для валидации email
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

# ---------- Состояния FSM ----------
class AuthStates(StatesGroup):
    waiting_for_email = State()

class SurveyStates(StatesGroup):
    answering = State()
    confirm_finish = State()
    editing = State()
    editing_answer = State()

# ---------- Класс для работы с API ----------
class ApiClient:
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def telegram_login(self, telegram_id: int) -> Dict[str, Any]:
        """Возвращает ответ API в виде словаря (status, data)."""
        session = await self.get_session()
        url = f"{AUTH_BASE_URL}/auth/telegram-login"
        payload = {"telegram_id": telegram_id, "bot_secret": BOT_SECRET_KEY}
        async with session.post(url, json=payload) as resp:
            data = await resp.json()
            print(f"Telegram login response: {resp.status} - {data}")
            return {"status": resp.status, "data": data}

    async def register_user(
        self, email: str, telegram_nick: str, password: str
    ) -> Dict[str, Any]:
        session = await self.get_session()
        url = f"{API_BASE_URL}/auth/register"
        payload = {
            "Email": email,
            "Telegram": telegram_nick,
            "password": password,
        }
        async with session.post(url, json=payload) as resp:
            data = await resp.json()
            return {"status": resp.status, "data": data}

    async def create_survey(self, token: str) -> Optional[int]:
        """Создаёт опрос и возвращает SurveyID."""
        session = await self.get_session()
        url = f"{API_BASE_URL}/Survey"
        headers = {"Authorization": f"Bearer {token}"}
        async with session.post(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("SurveyID")
            return None

    async def get_survey(self, token: str, survey_id: int) -> Optional[Dict[str, Any]]:
        """Получает структуру опроса (в задании указан POST, так и делаем)."""
        session = await self.get_session()
        url = f"{API_BASE_URL}/Survey/{survey_id}"
        headers = {"Authorization": f"Bearer {token}"}
        async with session.get(url, headers=headers) as resp: # !!!!!!!!!!!
            if resp.status == 200:
                return await resp.json()
            return None

    async def submit_answer(
        self, token: str, survey_id: int, question_id: int, answer: str
    ) -> bool:
        """Отправляет ответ на конкретный вопрос."""
        session = await self.get_session()
        url = f"{API_BASE_URL}/Survey/{survey_id}/{question_id}"
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"Answer": answer}
        async with session.post(url, json=payload, headers=headers) as resp:
            return resp.status == 200

    async def submit_conclusion(self, token: str, survey_id: int) -> bool:
        """Отправляет запрос на завершение опроса."""
        session = await self.get_session()
        url = f"{API_BASE_URL}/Survey/{survey_id}/Conclusion"
        headers = {"Authorization": f"Bearer {token}"}
        async with session.post(url, headers=headers) as resp:
            return resp.status == 200


api = ApiClient()

# ---------- Вспомогательные функции ----------
def generate_password(length: int = 10) -> str:
    """Генерирует стойкий пароль из букв, цифр и спецсимволов."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))

def is_valid_email(email: str) -> bool:
    return bool(EMAIL_PATTERN.fullmatch(email))

def format_question_preview(question: dict, idx: int) -> str:
    answer_status = "✅" if question.get("Answer") else "❌"
    text = question["Question"]
    preview = text[:50] + "..." if len(text) > 50 else text
    return f"{idx+1}. {preview} {answer_status}"

# ---------- Инициализация бота и роутера ----------

PROXY_URL = "socks5://127.0.0.1:10808"
session = AiohttpSession(proxy=PROXY_URL)

bot = Bot(token=BOT_TOKEN, session=session)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

# ---------- Обработчики ----------

@router.message(Command(commands=["start"]))
async def cmd_start(message: Message, state: FSMContext):
    """Начало работы: авторизация или приглашение зарегистрироваться."""
    await state.clear()
    telegram_id = message.from_user.id
    await message.answer("Выполняется вход...")

    # Попытка входа через Telegram ID
    resp = await api.telegram_login(telegram_id)

    if resp["status"] == 200:
        data = resp["data"]
        token = data.get("access_token")
        if token:
            await state.update_data(access_token=token)
            await message.answer("Вход выполнен успешно. Создаю опрос...")
            await create_and_start_survey(message, state, token)
            return

    if resp["status"] == 404:
        # Пользователь не найден – регистрация
        await message.answer(WELCOME_MESSAGE)
        await state.set_state(AuthStates.waiting_for_email)
        return

    # Непредвиденная ошибка
    await message.answer(
        "Произошла ошибка при подключении к серверу. Попробуйте позже."
    )


@router.message(AuthStates.waiting_for_email)
async def process_email(message: Message, state: FSMContext):
    """Получение и валидация email, генерация пароля, регистрация."""
    email = message.text.strip() if message.text else ""
    if not is_valid_email(email):
        await message.answer(
            "Некорректный e-mail. Пожалуйста, введите действительный адрес:"
        )
        return

    # Генерация пароля
    password = generate_password()
    # Telegram-имя: username или полное имя
    telegram_nick = message.from_user.username or message.from_user.full_name

    # Отправляем пароль скрытым
    await message.answer(
        f"Ваш пароль для входа на сайт: {password}\n\n"
        "⚠️ <b>Обязательно сохраните пароль в надёжном месте!</b>\n"
        "Не передавайте его третьим лицам. Он потребуется для доступа к личному кабинету.",
        parse_mode="HTML",
    )

    # Регистрация через API
    resp = await api.register_user(email, telegram_nick, password)
    if resp["status"] == 200:
        data = resp["data"]
        token = data.get("access_token")
        if token:
            print(f"Registration successful. Access token: {token}")
            await state.update_data(access_token=token)
            await message.answer("Регистрация прошла успешно. Создаю опрос...")
            await create_and_start_survey(message, state, token)
        else:
            await message.answer("Ошибка получения токена. Попробуйте /start ещё раз.")
            await state.clear()
    else:
        await message.answer(
            f"Ошибка регистрации (код {resp['status']}). Проверьте данные или попробуйте позже."
        )
        await state.clear()


async def create_and_start_survey(
    message: Message, state: FSMContext, token: str
):
    """Создаёт опрос, получает вопросы и запускает цикл ответов."""
    survey_id = await api.create_survey(token)
    if not survey_id:
        await message.answer("Не удалось создать опрос. Попробуйте /start позже.")
        await state.clear()
        return

    print(f"Survey created with ID: {survey_id}")

    survey_data = await api.get_survey(token, survey_id)
    if not survey_data or "QA" not in survey_data:
        await message.answer("Не удалось получить вопросы опроса.")
        await state.clear()
        return

    questions = survey_data["QA"]
    # Сохраняем в состоянии
    await state.update_data(
        access_token=token,
        survey_id=survey_id,
        questions=questions,
        current_index=0,
    )
    # Начинаем с первого вопроса
    first_question = questions[0]
    await message.answer(
        f"Вопрос 1/{len(questions)}:\n\n{first_question['Question']}"
    )
    await state.set_state(SurveyStates.answering)


@router.message(SurveyStates.answering)
async def process_answer(message: Message, state: FSMContext):
    """Обрабатывает ответ на текущий вопрос."""
    data = await state.get_data()
    questions: List[Dict] = data["questions"]
    current_index: int = data["current_index"]
    survey_id: int = data["survey_id"]
    token: str = data["access_token"]

    answer_text = message.text.strip()
    if not answer_text:
        await message.answer("Ответ не может быть пустым. Пожалуйста, введите ваш ответ:")
        return

    question = questions[current_index]
    question_id = question["QuestionID"]
    question["Answer"] = answer_text

    # Отправляем ответ на сервер
    ok = await api.submit_answer(token, survey_id, question_id, answer_text)
    if not ok:
        await message.answer("Ошибка сохранения ответа. Повторите попытку.")
        return

    # Сохраняем обновлённые вопросы
    await state.update_data(questions=questions)

    # Переходим к следующему вопросу
    next_index = current_index + 1
    if next_index < len(questions):
        await state.update_data(current_index=next_index)
        next_q = questions[next_index]
        await message.answer(
            f"Вопрос {next_index+1}/{len(questions)}:\n\n{next_q['Question']}"
        )
    else:
        # Все вопросы отвечены – запрос подтверждения завершения
        await message.answer(
            "Вы ответили на все вопросы. Завершить опрос?",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="Да"), KeyboardButton(text="Нет")]
                ],
                resize_keyboard=True,
                one_time_keyboard=True,
            ),
        )
        await state.set_state(SurveyStates.confirm_finish)


@router.message(SurveyStates.confirm_finish, F.text.lower() == "да")
async def confirm_yes(message: Message, state: FSMContext):
    """Пользователь подтвердил завершение опроса."""
    data = await state.get_data()
    survey_id: int = data["survey_id"]
    token: str = data["access_token"]

    success = await api.submit_conclusion(token, survey_id)
    if success:
        await message.answer(
            "✅ Опрос завершён. Благодарим за участие!",
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        await message.answer(
            "Ошибка при завершении опроса. Попробуйте позже.",
            reply_markup=ReplyKeyboardRemove(),
        )
    await state.clear()


@router.message(SurveyStates.confirm_finish, F.text.lower() == "нет")
async def confirm_no(message: Message, state: FSMContext):
    """Пользователь отказался завершать — переход в редактирование."""
    await state.set_state(SurveyStates.editing)
    await show_editing_menu(message, state)


async def show_editing_menu(message: Message, state: FSMContext):
    """Показывает меню редактирования ответов с кнопкой 'Завершить опрос'."""
    data = await state.get_data()
    questions: List[Dict] = data["questions"]

    keyboard = []
    for i, q in enumerate(questions):
        btn_text = format_question_preview(q, i)
        keyboard.append(
            [InlineKeyboardButton(text=btn_text, callback_data=f"edit_{i}")]
        )
    keyboard.append(
        [InlineKeyboardButton(text="🏁 Завершить опрос", callback_data="conclude")]
    )
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    await message.answer(
        "Выберите вопрос для редактирования или завершите опрос:",
        reply_markup=markup,
    )


@router.callback_query(SurveyStates.editing, F.data.startswith("edit_"))
async def edit_question(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора вопроса для редактирования."""
    await callback.answer()
    idx = int(callback.data.split("_")[1])
    data = await state.get_data()
    questions: List[Dict] = data["questions"]
    if idx < 0 or idx >= len(questions):
        await callback.message.answer("Некорректный выбор.")
        return

    question = questions[idx]
    await state.update_data(editing_question_index=idx)
    await callback.message.answer(
        f"Редактирование ответа на вопрос:\n\n{question['Question']}\n\n"
        f"Текущий ответ: {question.get('Answer', '—')}\n"
        "Введите новый ответ (или /cancel для отмены):"
    )
    await state.set_state(SurveyStates.editing_answer)
    # Убираем клавиатуру, чтобы не мешала
    await callback.message.edit_reply_markup(reply_markup=None)


@router.message(SurveyStates.editing_answer)
async def process_editing_answer(message: Message, state: FSMContext):
    """Принимает новый ответ при редактировании."""
    if message.text and message.text.strip().lower() == "/cancel":
        await state.set_state(SurveyStates.editing)
        await show_editing_menu(message, state)
        return

    answer_text = message.text.strip()
    if not answer_text:
        await message.answer("Ответ не может быть пустым. Введите ответ или /cancel:")
        return

    data = await state.get_data()
    idx: int = data["editing_question_index"]
    questions: List[Dict] = data["questions"]
    survey_id: int = data["survey_id"]
    token: str = data["access_token"]
    question = questions[idx]
    question_id = question["QuestionID"]
    question["Answer"] = answer_text

    ok = await api.submit_answer(token, survey_id, question_id, answer_text)
    if not ok:
        await message.answer("Ошибка сохранения ответа. Попробуйте ещё раз.")
        return

    await state.update_data(questions=questions)
    await message.answer("Ответ обновлён.")
    await state.set_state(SurveyStates.editing)
    await show_editing_menu(message, state)


@router.callback_query(SurveyStates.editing, F.data == "conclude")
async def conclude_from_editing(callback: CallbackQuery, state: FSMContext):
    """Проверка и завершение опроса из меню редактирования."""
    await callback.answer()
    data = await state.get_data()
    questions: List[Dict] = data["questions"]
    token: str = data["access_token"]
    survey_id: int = data["survey_id"]

    # Проверяем, что на все вопросы даны ответы
    unanswered_ids = [
        q["QuestionID"] for q in questions if not q.get("Answer")
    ]
    if unanswered_ids:
        await callback.message.answer(
            f"❌ Не на все вопросы даны ответы. Осталось: {len(unanswered_ids)}. "
            "Пожалуйста, заполните их перед завершением."
        )
        return

    success = await api.submit_conclusion(token, survey_id)
    if success:
        await callback.message.answer("✅ Опрос завершён. Благодарим за участие!")
        await callback.message.edit_reply_markup(reply_markup=None)
    else:
        await callback.message.answer("Ошибка при завершении опроса.")
    await state.clear()


# ---------- Точка входа ----------
async def main():
    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(e)
    finally:
        await api.close()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())