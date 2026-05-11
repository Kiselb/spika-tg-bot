from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from api_client import api
from handlers.states import SurveyStates
from keyboards.reply import finish_confirmation_kb, editing_menu_kb

router = Router()

async def create_and_start_survey(message: Message, state: FSMContext, token: str):
    """Создаёт опрос и выдаёт первый вопрос"""
    survey_id = await api.create_survey(token)
    if not survey_id:
        await message.answer("Не удалось создать опрос.")
        await state.clear()
        return

    survey_data = await api.get_survey(token, survey_id)
    if not survey_data or "QA" not in survey_data:
        await message.answer("Не удалось получить вопросы.")
        await state.clear()
        return

    questions = survey_data["QA"]
    await state.update_data(
        access_token=token,
        survey_id=survey_id,
        questions=questions,
        current_index=0,
    )
    first_q = questions[0]
    await message.answer(f"Вопрос 1/{len(questions)}:\n\n{first_q['Question']}")
    await state.set_state(SurveyStates.answering)

@router.message(SurveyStates.answering)
async def process_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    questions = data["questions"]
    idx = data["current_index"]
    survey_id = data["survey_id"]
    token = data["access_token"]

    answer = message.text.strip()
    if not answer:
        await message.answer("Ответ не может быть пустым. Введите ответ:")
        return

    question = questions[idx]
    question_id = question["QuestionID"]
    question["Answer"] = answer

    ok = await api.submit_answer(token, survey_id, question_id, answer)
    if not ok:
        await message.answer("Ошибка сохранения ответа.")
        return

    await state.update_data(questions=questions)
    next_idx = idx + 1
    if next_idx < len(questions):
        await state.update_data(current_index=next_idx)
        next_q = questions[next_idx]
        await message.answer(f"Вопрос {next_idx+1}/{len(questions)}:\n\n{next_q['Question']}")
    else:
        await message.answer(
            "Вы ответили на все вопросы. Завершить опрос?",
            reply_markup=finish_confirmation_kb(),
        )
        await state.set_state(SurveyStates.confirm_finish)

@router.message(SurveyStates.confirm_finish, F.text.lower() == "да")
async def confirm_yes(message: Message, state: FSMContext):
    data = await state.get_data()
    token = data["access_token"]
    survey_id = data["survey_id"]
    ok = await api.submit_conclusion(token, survey_id)
    if ok:
        await message.answer("✅ Опрос завершён. Спасибо!", reply_markup=ReplyKeyboardRemove())
    else:
        await message.answer("Ошибка завершения.")
    await state.clear()

@router.message(SurveyStates.confirm_finish, F.text.lower() == "нет")
async def confirm_no(message: Message, state: FSMContext):
    await state.set_state(SurveyStates.editing)
    data = await state.get_data()
    questions = data["questions"]
    await message.answer(
        "Редактирование ответов:",
        reply_markup=editing_menu_kb(questions)
    )

@router.callback_query(SurveyStates.editing, F.data.startswith("edit_"))
async def start_edit_question(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    idx = int(callback.data.split("_")[1])
    data = await state.get_data()
    questions = data["questions"]
    question = questions[idx]
    await state.update_data(editing_question_index=idx)
    await callback.message.answer(
        f"Вопрос:\n{question['Question']}\n\nТекущий ответ: {question.get('Answer', '—')}\nВведите новый ответ:"
    )
    await callback.message.edit_reply_markup(reply_markup=None)
    await state.set_state(SurveyStates.editing_answer)

@router.message(SurveyStates.editing_answer)
async def editing_answer_input(message: Message, state: FSMContext):
    if message.text and message.text.strip().lower() == "/cancel":
        await state.set_state(SurveyStates.editing)
        data = await state.get_data()
        await message.answer("Отмена.", reply_markup=editing_menu_kb(data["questions"]))
        return

    answer = message.text.strip()
    if not answer:
        await message.answer("Ответ не может быть пустым.")
        return

    data = await state.get_data()
    idx = data["editing_question_index"]
    questions = data["questions"]
    survey_id = data["survey_id"]
    token = data["access_token"]

    question = questions[idx]
    question["Answer"] = answer
    ok = await api.submit_answer(token, survey_id, question["QuestionID"], answer)
    if not ok:
        await message.answer("Ошибка сохранения.")
        return

    await state.update_data(questions=questions)
    await message.answer("Ответ обновлён.")
    await state.set_state(SurveyStates.editing)
    await message.answer("Продолжайте:", reply_markup=editing_menu_kb(questions))

@router.callback_query(SurveyStates.editing, F.data == "conclude")
async def conclude_survey(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    questions = data["questions"]
    token = data["access_token"]
    survey_id = data["survey_id"]

    unanswered = [q for q in questions if not q.get("Answer")]
    if unanswered:
        await callback.message.answer(f"Не все ответы заполнены. Осталось: {len(unanswered)}")
        return

    ok = await api.submit_conclusion(token, survey_id)
    if ok:
        await callback.message.answer("✅ Опрос завершён!")
        await callback.message.edit_reply_markup(reply_markup=None)
    else:
        await callback.message.answer("Ошибка завершения.")
    await state.clear()
