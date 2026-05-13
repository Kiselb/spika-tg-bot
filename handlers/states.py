from aiogram.fsm.state import State, StatesGroup

class SurveyStates(StatesGroup):
    answering_extra = State()   # ответ на дополнительный вопрос (локальный)
    answering = State()         # ответ на основной вопрос (API)
