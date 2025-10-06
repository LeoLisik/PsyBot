from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from DB.DBhandlers import *
from logger_config import logger

from aiogram.fsm.state import StatesGroup, State

router = Router()


class Reg(StatesGroup):
    enter_fio = State()
    enter_age = State()
    enter_institute = State()


class InstituteCallbackFactory(CallbackData, prefix="institute="):
    id: int


@router.callback_query(F.data == "register")
async def handle_choice(callback: CallbackQuery, state: FSMContext):
    logger.debug(f"{callback.from_user.id} Запущена регистрация")
    text = "Как тебя зовут? (Фамилия Имя)"
    await callback.message.edit_text(text)
    await state.update_data(message=callback.message.message_id)
    await state.set_state(Reg.enter_fio)
    await callback.answer()


@router.message(StateFilter(Reg.enter_fio))
async def fio_handler(message: Message, state: FSMContext):
    logger.debug(f"{message.from_user.id} Вызвана обработка ФИО")
    data = await state.get_data()
    last_message = data.get("message")

    if len(message.text.strip()) < 3:
        logger.debug(f"{message.from_user.id} Введено слишком короткое ФИО: {message.text}")
        await message.bot.edit_message_text(chat_id=message.chat.id, message_id=last_message,
                                            text="Слишком коротко для имени и фамилии😥\nПопробуй еще раз (Фамилия Имя)")
        await message.delete()
        return
    surname, name = message.text.replace("(", "").replace(")", "").strip().split(" ")

    if len(surname) < 3:
        logger.debug(f"{message.from_user.id} Введена слишком короткая фамилия: {surname} в {message.text}")
        await message.bot.edit_message_text(chat_id=message.chat.id, message_id=last_message,
                                            text="Слишком короткая фамилия😥\nПопробуй еще раз (Фамилия Имя)")
        await message.delete()
        return
    if len(name) < 3:
        logger.debug(f"{message.from_user.id} Введено слишком короткое имя: {name} в {message.text}")
        await message.bot.edit_message_text(chat_id=message.chat.id, message_id=last_message,
                                            text="Слишком короткое имя😥\nПопробуй еще раз (Фамилия Имя)")
        await message.delete()
        return

    await state.update_data(surname=surname, name=name)
    await message.bot.edit_message_text(chat_id=message.chat.id, message_id=last_message,
                                        text=f"Отлично, привет {name}!\nТеперь введи свой возраст")
    await state.set_state(Reg.enter_age)
    await message.delete()


@router.message(StateFilter(Reg.enter_age))
async def age_handler(message: Message, state: FSMContext):
    logger.debug(f"{message.from_user.id} Вызвана обработка возраста")
    data = await state.get_data()
    last_message = data.get("message")

    if not message.text.strip().isdigit():
        logger.debug(f"{message.from_user.id} Введены буквы в возрасте: {message.text}")
        await message.bot.edit_message_text(chat_id=message.chat.id, message_id=last_message,
                                            text="Не думаю, что возраст может содержать буквы😀\nПопробуй ввести возраст еще раз")
        await message.delete()
        return

    age = int(message.text)
    if not 14 < age < 99:
        logger.debug(f"{message.from_user.id} Некорректный возраст: {message.text}")
        await message.bot.edit_message_text(chat_id=message.chat.id, message_id=last_message,
                                            text="Кажется ты ввел некорректный возраст\nПопробуй ввести возраст еще раз")
        await message.delete()
        return

    builder = InlineKeyboardBuilder()

    institutes = await get_institutes()

    for id, name in institutes.items():
        builder.button(text=name, callback_data=InstituteCallbackFactory(id=id))

    builder.adjust(2)

    await state.update_data(age=age)
    await message.bot.edit_message_text(chat_id=message.chat.id, message_id=last_message,
                                        text=f"Отлично! Мы почти закончили\nТеперь выбери институт в котором ты учишься",
                                        reply_markup=builder.as_markup())
    await state.set_state(Reg.enter_institute)
    await message.delete()


@router.callback_query(InstituteCallbackFactory.filter())
async def institute_handler(callback: CallbackQuery, callback_data: CallbackData, state: FSMContext):
    logger.debug(f"{callback.from_user.id} Вызвана обработка института")
    data = await state.get_data()
    last_message = data.get("message")

    surname = data.get('surname')
    name = data.get('name')
    age = data.get('age')
    institute = callback_data.id
    result = await register_client(callback.from_user.id, surname, name, age, institute)

    if not result:
        logger.warning(f"Ошибка регистрации пользователя с данными {callback.from_user.id} {surname} {name} {age} {institute}")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Познакомиться", callback_data="register")
            ]
        ])

        await callback.bot.edit_message_text(chat_id=callback.message.chat.id, message_id=last_message,
                                             text=f"Что-то пошло не так😥\nПопробуй еще раз позже или обратись к администратору",
                                             reply_markup=keyboard)
        await state.set_state(None)
        return

    logger.info(f"Пользователь с telegram id {callback.from_user.id} зарегистрировался")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Записаться", callback_data="tochoice"),
        ]
    ])

    await callback.bot.edit_message_text(chat_id=callback.message.chat.id, message_id=last_message,
                                         text=f"Молодец! Ты успешно зарегистрировался, теперь можешь записаться к нашим психологам",
                                         reply_markup=keyboard)
    await state.set_state(None)
