import asyncio
import os
from logger_config import logger

from aiogram import Dispatcher, Bot, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

from sqlalchemy_storage import SQLAlchemyStorage

from DB.DB import engine, SessionLocal, init_db
from DB.DBhandlers import get_client_id_by_telegram
from DB.models import Base

from handlers import appointmentHandlers, registrationHandlers

storage = SQLAlchemyStorage(sessionmaker=SessionLocal, metadata=Base.metadata)

dp = Dispatcher(storage=storage)
dp.include_router(appointmentHandlers.router)
dp.include_router(registrationHandlers.router)


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    logger.debug("Вызвано первое сообщение")
    if await get_client_id_by_telegram(message.from_user.id):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Записаться", callback_data="tochoice"),
            ]
        ])
        logger.debug("Обнаружен вход авторизованного пользователя")
        await message.answer(
            "Психологи нашей Психологической службы готовы принять тебя в любой будний день. Сделай свой выбор.\n\nОбрати внимание, записи открываются на 2 недели вперед",
            reply_markup=keyboard)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Познакомиться", callback_data="register")
        ]
    ])
    await message.answer(
        f"Привет, это психологическая служба университета им. А.Н. Косыгина. Перед тем как записаться к психологу "
        f"давай познакомимся😉\n\nВводи пожалуйста настоящие данные, они надежно защищены и мы используем их только "
        f"для внутренней статистики",
        reply_markup=keyboard)


async def main() -> None:
    await init_db()
    token = str(os.getenv("BOT_TOKEN"))
    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    logger.info("Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
