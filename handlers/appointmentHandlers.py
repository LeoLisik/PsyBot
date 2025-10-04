import datetime

from aiogram import Router, F
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from DB.DBhandlers import *

router = Router()


class DateCallbackFactory(CallbackData, prefix="date="):
    date: str


class PsychologistCallbackFactory(CallbackData, prefix="psychologist="):
    id_psychologist: int


class SlotCallbackFactory(CallbackData, prefix="slot="):
    id_slot: int
    date: str


@router.callback_query(F.data == "tochoice")
async def handle_choice(callback: CallbackQuery):
    text = "Психологи нашей Психологической службы готовы принять тебя в любой будний день. Сделайте свой выбор.\n\nОбратите внимание, записи открываются на 2 недели вперед"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="По дням недели", callback_data="bydays"),
            InlineKeyboardButton(text="По фамилии", callback_data="bysurname")
        ]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "bysurname")
async def handle_surname(callback: CallbackQuery):
    text = "Выбери специалиста, к которому хочешь записаться"
    builder = InlineKeyboardBuilder()

    surnames = await get_psychologist_surnames()

    for id, surname in surnames.items():
        builder.button(text=surname, callback_data=PsychologistCallbackFactory(id_psychologist=id))

    builder.button(text="Назад", callback_data="tochoice")
    builder.adjust(2)

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(PsychologistCallbackFactory.filter())
async def handle_time(callback: CallbackQuery, callback_data: PsychologistCallbackFactory):
    builder = InlineKeyboardBuilder()

    times = await get_free_slots_for_psychologist(callback_data.id_psychologist)

    if len(times) == 0:
        await callback.message.edit_text(
            "Похоже у этого психолога заняты все записи, на ближайшие 2 недели\n\nПопробуй завтра, возможно появятся "
            "новые записи")

    for id, date, time, weekday in times:
        builder.button(
            text=f"{weekday} {time.strftime('%H:%M')} ({datetime.date.fromisoformat(date).strftime('%d.%m')})",
            callback_data=SlotCallbackFactory(id_slot=id, date=date))

    builder.button(text="Назад", callback_data="bysurname")
    builder.adjust(2)

    await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "bydays")
async def handle_days(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()

    dates = await get_slot_dates()

    for name, date in dates:
        builder.button(text=f"{name} ({date.strftime('%d.%m')})", callback_data=DateCallbackFactory(date=str(date)))

    builder.button(text="Назад", callback_data="tochoice")
    builder.adjust(2)

    await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(DateCallbackFactory.filter())
async def handle_date(callback: CallbackQuery, callback_data: DateCallbackFactory):
    builder = InlineKeyboardBuilder()

    options = await get_free_slots_for_date(datetime.date.fromisoformat(callback_data.date))

    for id, time, surname in options:
        builder.button(text=f"{surname} ({time.strftime('%H:%M')})",
                       callback_data=SlotCallbackFactory(id_slot=id, date=callback_data.date))

    builder.button(text="Назад", callback_data="bydays")
    builder.adjust(2)

    await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(SlotCallbackFactory.filter())
async def handle_slot(callback: CallbackQuery, callback_data: SlotCallbackFactory):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="В начало", callback_data="tochoice"),
        ]
    ])
    id_client = await get_client_id_by_telegram(id_telegram=callback.from_user.id)
    client = await get_client(id_client)
    assignments = await get_user_assignments(id_client, days=13)
    if assignments:
        await callback.message.edit_text(
            f"Ты уже записан:\n📅 {assignments[0]['date'].strftime('%d.%m')}\n⌛️ {assignments[0]['time'].strftime('%H:%M')}\n🙋‍♂️ {assignments[0]['psychologist']}\n📞 {assignments[0]['phone']}\n\n"
            f"Напиши психологу на WhatsApp за день до консультации не позднее 17:00 (поставь себе напоминание).\n\n"
            f"<code>Здравствуйте, я {client.surname} {client.name} записан(а) к Вам на консультацию {assignments[0]['date'].strftime('%d.%m')} на {assignments[0]['time'].strftime('%H:%M')}. В какой кабинет мне подойти?</code>\n"
            f"(Нажми чтобы скопировать)\n\n"
            f"Дождись ответа, психолог может быть занят с другим клиентом. Это сообщение "
            f"будет подтверждением твоей готовности к консультации."
            f"Без такого сообщения консультация не состоится.\n\n"
            f"Ты сможешь снова записаться после этого приема",
            reply_markup=keyboard)
        await callback.answer()
        return

    result = await assign_user_to_slot(id_client, callback_data.id_slot, callback_data.date)

    if result is not None:
        await callback.message.edit_text(f"Ты записан(а) к \n"
                                         f"🙋‍♂️ {result['psychologist']}\n📅 {datetime.date.fromisoformat(result['date']).strftime('%d.%m.%y')}\n⌛️ {result['time'].strftime('%H:%M')}\n\n"
                                         f"Напиши психологу на WhatsApp за день до консультации не позднее 17:00 (поставь себе напоминание).\n\n"
                                         f"<code>Здравствуйте, я {client.surname} {client.name} записан(а) к Вам на консультацию {datetime.date.fromisoformat(result['date']).strftime('%d.%m.%y')} на {result['time'].strftime('%H:%M')}. В какой кабинет мне подойти?</code>\n"
                                         f"(Нажми чтобы скопировать)\n\n"
                                         f"Дождись ответа, психолог может быть занят с другим клиентом. Это сообщение будет подтверждением твоей готовности к консультации. "
                                         f"Без такого сообщения консультация не состоится.",
                                         reply_markup=keyboard)
    else:
        await callback.message.edit_text("Кажется слот уже был занят кем-то другим", reply_markup=keyboard)
    await callback.answer()
