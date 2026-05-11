from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def finish_confirmation_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Да"), KeyboardButton(text="Нет")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

def editing_menu_kb(questions):
    """Создаёт клавиатуру со списком вопросов и кнопкой Завершить"""
    buttons = []
    for i, q in enumerate(questions):
        text = q["Question"]
        status = "✅" if q.get("Answer") else "❌"
        preview = (text[:47] + "...") if len(text) > 50 else text
        buttons.append([InlineKeyboardButton(
            text=f"{i+1}. {preview} {status}",
            callback_data=f"edit_{i}"
        )])
    buttons.append([InlineKeyboardButton(
        text="🏁 Завершить опрос",
        callback_data="conclude"
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
