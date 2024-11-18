import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.database.repo import add_user

logger = logging.getLogger(__name__)

router = Router()


@router.message(CommandStart())
async def on_start_command(message: Message):
    await add_user(message.from_user.id, message.from_user.username)
    await message.answer(text="Вызови /goal для настройки своих целей")
