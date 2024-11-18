from datetime import datetime
import json
import logging
import operator

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, User, ContentType
from aiogram_dialog import StartMode, Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Select, SwitchTo, Group, Button
from aiogram_dialog.widgets.text import Format, Const
from aiogram_dialog.widgets.input import MessageInput

from app.database.models import Goal
from app.database.repo import add_goal, add_progress_to_goal, get_user_goals, set_progress_to_goal
from aiogram.enums.parse_mode import ParseMode

logger = logging.getLogger(__name__)


class GoalStates(StatesGroup):
    goals_info = State()
    add_goal = State()
    add_goal_limit = State()
    confirm_goal = State()
    edit_goal = State()
    new_progress = State()


async def goals_info_getter(event_from_user: User, dialog_manager: DialogManager, **kwargs) -> dict:
    goals: list[Goal] = await get_user_goals(event_from_user.id)
    if goals:
        goal_info = "\n".join([f"- {goal.name}, прогресс: {goal.current_value}/{goal.selected_value}" for goal in goals])
    else:
        goal_info = "Цели на этот месяц ещё не заданы"

    for goal in goals:
        dialog_manager.dialog_data[f"goal_{goal.id}"] = {
            "id": goal.id,
            "name": goal.name,
            "current_value": goal.current_value,
            "selected_value": goal.selected_value,
            "period_end": goal.period_end.isoformat(),
            "user_id": goal.user_id
        }

    return {
        "has_goals": len(goals) > 0,
        "goal_info": goal_info,
        "goals": [(goal.id, goal.name) for goal in goals]
    }


async def on_goal_click(callback: CallbackQuery, select: Select, dm: DialogManager, item_id: str):
    dm.dialog_data['selected_goal'] = item_id
    await dm.switch_to(GoalStates.edit_goal)


user_goals_window = Window(
    Format(text="{goal_info}"),
    Group(
        Select(
            text=Format("{item[1]}"),
            id="sl_goal",
            item_id_getter=operator.itemgetter(0),
            items="goals",
            on_click=on_goal_click
        ),
        SwitchTo(text=Const("Добавить цель"), id="sw_add_goal", state=GoalStates.add_goal),
        width=1
    ),
    state=GoalStates.goals_info,
    getter=goals_info_getter
)


async def on_goal_input(message: Message, message_input: MessageInput, dialog_manager: DialogManager):
    dialog_manager.dialog_data['new_goal'] = message.text
    await dialog_manager.switch_to(GoalStates.add_goal_limit)


add_goal_window = Window(
    Const("Введите цель."),
    Const("Например, <i>пробежать 10 км</i> или <i>Ходить на тренировки по боксу</i>"),
    Const('Одна цель - один вид тренировок и один способ фиксировать прогресс'),
    MessageInput(on_goal_input, ContentType.TEXT),
    parse_mode=ParseMode.HTML,
    state=GoalStates.add_goal
)


async def on_goal_limit_input(message: Message, message_input: MessageInput, dialog_manager: DialogManager):
    try:
        limit = int(message.text)
        dialog_manager.dialog_data['goal_limit'] = limit
        await dialog_manager.switch_to(GoalStates.confirm_goal)
    except ValueError:
        await message.answer("Пожалуйста, введите значение цели.")


add_goal_limit_window = Window(
    Const("Введите значение цели, число."),
    MessageInput(on_goal_limit_input, ContentType.TEXT),
    state=GoalStates.add_goal_limit
)


async def add_goal_to_user(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    tg_id = callback.from_user.id
    new_goal = dialog_manager.dialog_data.get('new_goal', '')
    goal_limit = dialog_manager.dialog_data.get('goal_limit', 0)

    if new_goal and goal_limit > 0:
        await add_goal(tg_id, new_goal, goal_limit)
        await callback.message.answer("Цель успешно добавлена!")
    else:
        await callback.message.answer("Ошибка при добавлении цели. Пожалуйста, попробуйте снова.")

    await dialog_manager.switch_to(GoalStates.goals_info)


async def confirm_getter(dialog_manager: DialogManager, **kwargs) -> dict:
    return {
        "new_goal": dialog_manager.dialog_data.get("new_goal", ""),
        "goal_limit": dialog_manager.dialog_data.get("goal_limit", 0)
    }


confirm_goal_window = Window(
    Const("Вы уверены, что хотите добавить эту цель?"),
    Format("Цель: {new_goal}"),
    Format("Значение: {goal_limit}"),
    Group(
        Button(text=Const("Подтвердить"), id="confirm_goal", on_click=add_goal_to_user),
        SwitchTo(text=Const("Отмена"), id="cancel_goal", state=GoalStates.goals_info),
        width=2
    ),
    state=GoalStates.confirm_goal,
    getter=confirm_getter
)


async def edit_goal_getter(dialog_manager: DialogManager, **kwargs) -> dict:
    goal_id = f"goal_{dialog_manager.dialog_data['selected_goal']}"
    goal = dialog_manager.dialog_data.get(goal_id, None)
    if goal is None:
        return {"info": "Цель не найдена."}

    goal = Goal(
        id=goal.get('id'),
        name=goal.get('name'),
        current_value=goal.get('current_value', 0),
        selected_value=goal.get('selected_value', 0),
        period_end=datetime.fromisoformat(goal.get('period_end')),
        user_id=goal.get('user_id')
    )

    return {
        "info": f"Цель: {goal.name}, прогресс: {goal.current_value}/{goal.selected_value}"
    }


async def on_edit_progress_click(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    dialog_manager.dialog_data['edit_type'] = button.widget_id
    await dialog_manager.switch_to(GoalStates.new_progress)


edit_goal_window = Window(
    Format("{info}"),
    Button(text=Const("Добавить прогресс"), id="add_progress", on_click=on_edit_progress_click),
    Button(text=Const("Задать прогресс"), id="set_progress", on_click=on_edit_progress_click),
    getter=edit_goal_getter,
    state=GoalStates.edit_goal
)


async def new_progress_getter(dialog_manager: DialogManager, **kwargs) -> dict:
    selected_goal_id = dialog_manager.dialog_data.get('selected_goal')
    if selected_goal_id is None:
        return {"title_new_progress": "Цель не выбрана."}

    goal_id = f"goal_{selected_goal_id}"
    goal = dialog_manager.dialog_data.get(goal_id, None)
    if goal is None:
        return {"title_new_progress": "Цель не найдена."}

    if dialog_manager.dialog_data.get('edit_type') == 'add_progress':
        title_new_progress = f"Сейчас прогресс - {goal['current_value']}. Сколько добавить?"
    else:
        title_new_progress = f"Сейчас прогресс - {goal['current_value']}. Сколько теперь должно быть?"

    return {
        "title_new_progress": title_new_progress
    }


async def on_progress_enter(message: Message, mi: MessageInput, dialog_manager: DialogManager):
    try:
        progress = int(message.text)
        selected_goal_id = int(dialog_manager.dialog_data.get('selected_goal'))

        if selected_goal_id is None:
            await message.answer("Цель не выбрана.")
            return

        if dialog_manager.dialog_data.get('edit_type') == 'add_progress':
            await add_progress_to_goal(selected_goal_id, progress)
            await message.answer(f"Прогресс {progress} добавлен к цели.")
        elif dialog_manager.dialog_data.get('edit_type') == 'set_progress':
            await set_progress_to_goal(selected_goal_id, progress)
            await message.answer(f"Прогресс цели установлен на {progress}.")

        await dialog_manager.switch_to(GoalStates.goals_info)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное числовое значение.")


new_progress_window = Window(
    Format('{title_new_progress}'),
    MessageInput(on_progress_enter, ContentType.TEXT),
    getter=new_progress_getter,
    state=GoalStates.new_progress
)


dialog = Dialog(
    user_goals_window, 
    add_goal_window, 
    add_goal_limit_window, 
    confirm_goal_window, 
    edit_goal_window, 
    new_progress_window
)

router = Router()
router.include_routers(dialog)


@router.message(Command('goal'))
async def on_goal_command(message: Message, dialog_manager: DialogManager):
    await dialog_manager.reset_stack()
    await dialog_manager.start(GoalStates.goals_info, mode=StartMode.RESET_STACK)
