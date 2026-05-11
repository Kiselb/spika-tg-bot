from aiogram.fsm.state import State, StatesGroup

class AuthStates(StatesGroup):
    waiting_for_email = State()

class SurveyStates(StatesGroup):
    answering = State()
    confirm_finish = State()
    editing = State()
    editing_answer = State()
    