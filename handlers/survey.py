from aiogram import Router
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from api_client import api
from handlers.states import SurveyStates

EXTRA_QUESTIONS = [
    {"QuestionID": -1, "Question": "Сколько я ХОЧУ получать/достигать?"},
    {"QuestionID": -2, "Question": "Сколько я МОГУ получать/достигать?"},
    {"QuestionID": -3, "Question": "Сколько я ДОСТОИН получать/достигать?"},
    {"QuestionID": -4, "Question": "Какой идеальный результат я вижу для себя?"},
    {"QuestionID": -5, "Question": "За какой срок я хочу этого достичь?"},
]

router = Router()

async def start_extra_survey(message: Message, state: FSMContext):
    """Запускает локальный опрос из 5 дополнительных вопросов."""
    extra = [dict(q) for q in EXTRA_QUESTIONS]  # копия, чтобы не мусорить
    await state.update_data(extra_questions=extra, extra_index=0)

    first_q = extra[0]
    await message.answer(
        f"Дополнительный вопрос 1/{len(extra)}:\n\n{first_q['Question']}"
    )
    await state.set_state(SurveyStates.answering_extra)

@router.message(SurveyStates.answering_extra)
async def process_extra_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    extra_questions = data["extra_questions"]
    idx = data["extra_index"]

    answer = message.text.strip() if message.text else ""
    if len(answer) < 2 or len(answer) > 2048:
        await message.answer("Ответ должен быть от 2 до 2048 символов. Введите заново:")
        return

    extra_questions[idx]["Answer"] = answer
    await state.update_data(extra_questions=extra_questions)

    next_idx = idx + 1
    if next_idx < len(extra_questions):
        # Ещё есть доп. вопросы
        await state.update_data(extra_index=next_idx)
        next_q = extra_questions[next_idx]
        await message.answer(
            f"Дополнительный вопрос {next_idx+1}/{len(extra_questions)}:\n\n{next_q['Question']}"
        )
    else:
        # Все доп. вопросы отвечены – переходим к основному опросу через API
        token = data["access_token"]
        await create_and_start_survey(message, state, token)


async def create_and_start_survey(message: Message, state: FSMContext, token: str):
    """Создаёт опрос и выдаёт первый вопрос"""
    survey_id = await api.create_survey(token)
    if not survey_id:
        await message.answer("Не удалось создать опрос.")
        await state.clear()
        return

    survey_data = await api.get_survey(token, survey_id)
    if not survey_data or "qa" not in survey_data:
        await message.answer("Не удалось получить вопросы.")
        await state.clear()
        return

    questions = survey_data["qa"]
    await state.update_data(
        access_token=token,
        survey_id=survey_id,
        questions=questions,
        current_index=0,
    )
    first_q = questions[0]
    await message.answer(f"Вопрос 1/{len(questions)}:\n\n{first_q['question']}")
    await state.set_state(SurveyStates.answering)

@router.message(SurveyStates.answering)
async def process_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    questions = data["questions"]
    idx = data["current_index"]
    survey_id = data["survey_id"]
    token = data["access_token"]

    answer = message.text.strip() if message.text else ""
    if len(answer) < 2 or len(answer) > 2048:
        await message.answer("Ответ должен быть от 2 до 2048 символов. Введите заново:")
        return

    question = questions[idx]
    question_id = question["question_id"]
    question["answer"] = answer

    ok = await api.submit_answer(token, survey_id, question_id, answer)
    if not ok:
        await message.answer("Ошибка сохранения ответа.")
        return

    await state.update_data(questions=questions)

    # Если вопросов больше нет — завершаем опрос
    next_idx = idx + 1
    if next_idx >= len(questions):
        ok_conclusion = await api.submit_conclusion(token, survey_id)
        if ok_conclusion:
            await message.answer("✅ Опрос завершён. Спасибо!", reply_markup=ReplyKeyboardRemove())
        else:
            await message.answer("Ошибка завершения опроса.")
        await state.clear()
        return

    # Переход к следующему вопросу
    await state.update_data(current_index=next_idx)
    next_q = questions[next_idx]
    await message.answer(f"Вопрос {next_idx+1}/{len(questions)}:\n\n{next_q['question']}")
