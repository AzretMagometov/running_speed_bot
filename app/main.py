import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.base import DefaultKeyBuilder
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats
from aiogram_dialog import setup_dialogs
from redis.asyncio import Redis

from app.config.provider import config
from app.handlers import goal_handler, start_handler
from app.utils.logging import setup_logging_base_config

log_file_path = 'logs/app.log'
setup_logging_base_config(log_file_path)


async def main():
    bot = Bot(token=config.token)

    await bot.set_my_commands([
        BotCommand(command="/help", description="Поддержка"),
    ], BotCommandScopeAllPrivateChats())

    redis = Redis(host=config.redis_info.host, port=config.redis_info.port, db=config.redis_info.db)

    dp = Dispatcher(storage=RedisStorage(redis=redis, key_builder=DefaultKeyBuilder(with_destiny=True)))
    dp.include_routers(
        start_handler.router,
        goal_handler.router
    )
    
    setup_dialogs(dp)

    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
