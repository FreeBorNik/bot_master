"""FSM состояния для пользователей."""
from aiogram.fsm.state import State, StatesGroup


class QuestionnaireStates(StatesGroup):
    """Состояния для заполнения анкеты."""
    age = State()
    hours_per_day = State()
    has_other_job = State()
