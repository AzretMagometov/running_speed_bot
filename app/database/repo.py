import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.database.engine import session_maker
from app.database.models import Goal, User

logger = logging.getLogger(__name__)

# Настройка логирования (если еще не настроено глобально)
if not logger.hasHandlers():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler()
        ]
    )


async def add_user(tg_id: int, name: str) -> Optional[User]:
    """
    Добавляет нового пользователя или обновляет существующего, разблокируя его.

    :param tg_id: Telegram ID пользователя.
    :param name: Имя пользователя.
    :return: Объект User, если добавление или обновление прошло успешно, иначе None.
    """
    async with session_maker() as session:
        try:
            async with session.begin():
                stmt = select(User).where(User.tg_id == tg_id).limit(1)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()

                if user:
                    user.is_blocked = False
                    logger.info(f"Пользователь с tg_id={tg_id} найден и разблокирован.")
                else:
                    user = User(tg_id=tg_id, tg_name=name)
                    session.add(user)
                    logger.info(f"Добавлен новый пользователь с tg_id={tg_id} и именем '{name}'.")
                return user
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при добавлении/обновлении пользователя с tg_id={tg_id}: {e}")
            await session.rollback()
            return None


async def set_user_blocked(tg_id: int) -> bool:
    """
    Блокирует пользователя с заданным tg_id.

    :param tg_id: Telegram ID пользователя.
    :return: True, если операция успешна, False в противном случае.
    """
    logger.info(f'set_user_blocked - {tg_id}')
    async with session_maker() as session:
        try:
            async with session.begin():
                stmt = select(User).where(User.tg_id == tg_id).limit(1)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()
                if user:
                    user.is_blocked = True
                    logger.info(f"Пользователь с tg_id={tg_id} заблокирован.")
                    return True
                else:
                    logger.warning(f"Пользователь с tg_id={tg_id} не найден.")
                    return False

        except SQLAlchemyError as e:
            logger.error(f"Ошибка при блокировке пользователя с tg_id={tg_id}: {e}")
            await session.rollback()
            return False


async def get_user_goals(tg_id: int) -> List[Goal]:
    """
    Получает список целей пользователя по его tg_id.

    :param tg_id: Telegram ID пользователя.
    :return: Список объектов Goal. Пустой список, если пользователь не найден или у него нет целей.
    """
    async with session_maker() as session:
        try:
            async with session.begin():
                stmt = select(User).options(selectinload(User.goals)).where(User.tg_id == tg_id).limit(1)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()
                
                if user:
                    logger.info(f"Найден пользователь с tg_id={tg_id} и {len(user.goals)} целей.")
                    return user.goals
                else:
                    logger.warning(f"Пользователь с tg_id={tg_id} не найден.")
                    return []
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при получении целей пользователя с tg_id={tg_id}: {e}")
            await session.rollback()
            return []


async def add_goal(tg_id: int, name: str, selected_value: int) -> Optional[Goal]:
    """
    Добавляет новую цель пользователю с заданным tg_id.

    :param tg_id: Telegram ID пользователя.
    :param name: Название цели.
    :param selected_value: Выбранное значение цели.
    :return: Объект Goal, если добавление прошло успешно, иначе None.
    """
    async with session_maker() as session:
        try:
            now = datetime.now(timezone.utc)
            # Определение последнего дня текущего месяца
            next_month = now.replace(day=1) + timedelta(days=32)
            last_day_of_month = next_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(seconds=1)

            async with session.begin():
                stmt = select(User).options(selectinload(User.goals)).where(User.tg_id == tg_id).limit(1)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()
                
                if user:
                    new_goal = Goal(name=name, selected_value=selected_value, period_end=last_day_of_month)
                    user.goals.append(new_goal)
                    logger.info(f"Добавлена цель '{name}' для пользователя с tg_id={tg_id}.")
                    return new_goal
                else:
                    logger.warning(f"Пользователь с tg_id={tg_id} не найден. Цель не добавлена.")
                    return None
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при добавлении цели '{name}' для пользователя с tg_id={tg_id}: {e}")
            await session.rollback()
            return None


async def get_goal(goal_id: int) -> Optional[Goal]:
    """
    Получает цель по её ID.

    :param goal_id: ID цели.
    :return: Объект Goal, если найдено, иначе None.
    """
    async with session_maker() as session:
        try:
            async with session.begin():
                stmt = select(Goal).where(Goal.id == goal_id).limit(1)
                result = await session.execute(stmt)
                goal = result.scalar_one_or_none()
                
                if goal:
                    logger.info(f"Найдена цель с id={goal_id}.")
                else:
                    logger.warning(f"Цель с id={goal_id} не найдена.")
                
                return goal
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при получении цели с id={goal_id}: {e}")
            await session.rollback()
            return None


async def add_progress_to_goal(goal_id: int, progress: int) -> bool:
    """
    Добавляет прогресс к текущему значению цели.

    :param goal_id: ID цели.
    :param progress: Значение прогресса для добавления.
    :return: True, если операция успешна, False в противном случае.
    """
    async with session_maker() as session:
        try:
            async with session.begin():
                stmt = update(Goal).where(Goal.id == goal_id).values(current_value=Goal.current_value + progress)
                result = await session.execute(stmt)
                
                if result.rowcount == 0:
                    logger.warning(f"Цель с id={goal_id} не найдена. Прогресс не добавлен.")
                    return False
                
                logger.info(f"Добавлен прогресс {progress} к цели с id={goal_id}.")
                return True
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при добавлении прогресса к цели с id={goal_id}: {e}")
            await session.rollback()
            return False


async def set_progress_to_goal(goal_id: int, progress: int) -> bool:
    """
    Устанавливает текущее значение прогресса цели.

    :param goal_id: ID цели.
    :param progress: Новое значение прогресса.
    :return: True, если операция успешна, False в противном случае.
    """
    async with session_maker() as session:
        try:
            async with session.begin():
                stmt = update(Goal).where(Goal.id == goal_id).values(current_value=progress)
                result = await session.execute(stmt)
                
                if result.rowcount == 0:
                    logger.warning(f"Цель с id={goal_id} не найдена. Прогресс не установлен.")
                    return False
                
                logger.info(f"Установлен прогресс {progress} для цели с id={goal_id}.")
                return True
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при установке прогресса для цели с id={goal_id}: {e}")
            await session.rollback()
            return False
