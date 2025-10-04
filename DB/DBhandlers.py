import datetime
from datetime import date, timedelta
from sqlalchemy import select, and_, not_, exists, cast, String, result_tuple
from sqlalchemy.exc import SQLAlchemyError

from DB.DB import SessionLocal
from DB.models import *


def is_even_week(day: date) -> bool:
    """
    Возвращает True, если неделя чётная, False если нечётная.
    1 сентября считается началом нечётной недели.
    """
    # Находим 1 сентября для года этой даты
    sept1 = date(day.year, 9, 1)

    # Если дата до 1 сентября — берём 1 сентября прошлого года
    if day < sept1:
        sept1 = date(day.year - 1, 9, 1)

    # Разница в неделях
    week_diff = (day.isocalendar()[1] - sept1.isocalendar()[1])

    # Иногда ISO-нумерация недели "перескакивает" в конце года, поэтому безопаснее:
    week_diff = (day - sept1).days // 7

    # 0 → нечётная, 1 → чётная, 2 → снова нечётная и т.д.
    return week_diff % 2 == 1


async def get_psychologist_surnames():
    async with SessionLocal() as session:
        result = await session.execute(select(Psychologist.id, Psychologist.surname))
        return {row[0]: row[1] for row in result.fetchall()}


async def get_institutes():
    async with SessionLocal() as session:
        result = await session.execute(select(Institute.id, Institute.name))
        return {row[0]: row[1] for row in result.fetchall()}


async def get_client(client_id: int) -> Client | None:
    """Получить клиента по id (возвращает ORM-объект или None)."""
    async with SessionLocal() as session:
        try:
            q = select(Client).where(Client.id == client_id)
            result = await session.execute(q)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            print(f"Ошибка при получении клиента: {e}")
            return None


async def get_slot_dates():
    today = date.today() + timedelta(days=1)
    days = 14

    async with SessionLocal() as session:
        free_days = []

        # перебираем 14 дней календаря
        for i in range(days):
            current_date = today + timedelta(days=i)
            even_week = is_even_week(current_date)
            weekday = current_date.isoweekday()  # 1=Monday .. 7=Sunday

            # EXISTS-подзапрос: есть ли занятие для слота на эту дату
            assigned_exists = (
                select(SlotAssignment.id)
                .where(
                    SlotAssignment.id_slot == Slot.id,
                    SlotAssignment.date == current_date
                )
                .exists()
            )

            # ищем хотя бы один активный слот для этого weekday, который свободен
            q = (
                select(Slot.id, Weekday.name_ru)
                .join(Slot.weekday)
                .where(
                    Slot.is_active.is_(True),
                    Slot.id_day == weekday,
                    Slot.is_even_week == even_week,
                    not_(assigned_exists)
                )
                .limit(1)
            )

            result = await session.execute(q)
            row = result.first()
            if row is not None:
                slot_id, day_name = row
                free_days.append((day_name, current_date))

        return free_days


async def get_free_slots_for_date(target_date: date):
    even_week = is_even_week(target_date)
    weekday = target_date.isoweekday()

    # Подзапрос: есть ли занятие на этот слот и дату
    assigned_exists = (
        select(SlotAssignment.id)
        .where(
            SlotAssignment.id_slot == Slot.id,
            SlotAssignment.date == target_date
        )
        .exists()
    )

    # Основной запрос: все активные слоты, где нет записи на target_date
    q = (
        select(Slot.id, Slot.time, Psychologist.surname)
        .join(Psychologist, Slot.id_psychologist == Psychologist.id)
        .where(
            Slot.is_active.is_(True),  # если в SQLite хранится текст
            Slot.is_even_week == even_week,
            Slot.id_day == weekday,
            not_(assigned_exists)
        )
        .order_by(Slot.time)
    )

    async with SessionLocal() as session:
        result = await session.execute(q)
    return result.all()


async def assign_user_to_slot(id_user: int, id_slot: int, date_str: str):
    day = datetime.date.fromisoformat(date_str)
    async with SessionLocal() as session:
        # Проверяем, занят ли слот
        exists_query = select(SlotAssignment).where(
            SlotAssignment.id_slot == id_slot,
            SlotAssignment.date == day
        )
        result = await session.execute(exists_query)
        if result.first():
            return None  # слот уже занят

        # Создаём запись
        new_assignment = SlotAssignment(
            id_slot=id_slot,
            id_client=id_user,
            date=day
        )
        session.add(new_assignment)
        await session.commit()
        await session.refresh(new_assignment)

        # Получаем время и психолога
        q = (
            select(Slot.time, Psychologist.surname, Psychologist.name)
            .join(Psychologist, Slot.id_psychologist == Psychologist.id)
            .where(Slot.id == id_slot)
        )
        result = await session.execute(q)
        time, surname, name = result.first()

        return {
            "date": day.isoformat(),
            "time": time,
            "psychologist": f"{surname} {name}"
        }


async def get_free_slots_for_psychologist(id_psychologist: int):
    days = 14
    today = date.today() + timedelta(days=1)
    free_slots = []

    for i in range(days):
        current_date = today + timedelta(days=i)
        weekday_num = current_date.isoweekday()  # 1=понедельник ... 7=воскресенье
        even_week = is_even_week(current_date)

        # Подзапрос: есть ли запись на этот слот и дату
        assigned_exists = (
            select(SlotAssignment.id)
            .where(
                SlotAssignment.id_slot == Slot.id,
                SlotAssignment.date == current_date
            )
            .exists()
        )

        # Основной запрос: ищем все активные слоты психолога на этот день недели, где нет записи
        q = (
            select(Slot.id, Slot.time, Weekday.name_ru)
            .select_from(Slot)
            .join(Weekday, Slot.id_day == Weekday.id)
            .where(
                Slot.is_active.is_(True),  # или Slot.is_active.is_(True) если Boolean хранится корректно
                Slot.id_psychologist == id_psychologist,
                Slot.id_day == weekday_num,
                Slot.is_even_week == even_week,
                not_(assigned_exists)
            )
            .order_by(Slot.time)
        )

        async with SessionLocal() as session:
            result = await session.execute(q)
        times = result.all()

        # Если есть свободные слоты, добавляем (дата, время) в список
        for id, time, weekday in times:
            free_slots.append((id, str(current_date), time, weekday))

    return free_slots


async def register_client(id: int, surname: str, name: str, age: int, id_institute: int) -> bool:
    async with SessionLocal() as session:
        try:
            # Проверка, существует ли уже такой клиент
            q = select(Client).where(
                Client.surname == surname,
                Client.name == name,
                Client.age == age,
                Client.id_institute == id_institute
            )
            result = await session.execute(q)
            existing_client = result.scalar_one_or_none()

            if existing_client:
                return False  # Уже есть такой клиент

            # Создание нового клиента
            new_client = Client(
                id_telegram=id,
                surname=surname,
                name=name,
                age=age,
                id_institute=id_institute
            )

            session.add(new_client)
            await session.commit()
            return True
        except SQLAlchemyError as e:
            await session.rollback()
            print(f"Ошибка при регистрации клиента: {e}")
            return False


async def get_client_id_by_telegram(id_telegram: int) -> int | None:
    """Возвращает id клиента по Telegram ID, либо None если не найден"""
    async with SessionLocal() as session:
        try:
            q = select(Client.id).where(Client.id_telegram == id_telegram)
            result = await session.execute(q)
            client_id = result.scalar_one_or_none()
            return client_id
        except SQLAlchemyError as e:
            print(f"Ошибка при поиске клиента: {e}")
            return None


async def get_user_assignments(id_client: int, days: int = 7):
    """Возвращает записи клиента по его ID на ближайшие days дней"""
    today = date.today()
    end_date = today + timedelta(days=days)

    async with SessionLocal() as session:
        try:
            q = (
                select(
                    SlotAssignment.date,
                    Slot.time,
                    Weekday.name_ru,
                    Psychologist.name,
                    Psychologist.patronymic,
                    Psychologist.phone
                )
                .join(Slot, SlotAssignment.id_slot == Slot.id)
                .join(Weekday, Slot.id_day == Weekday.id)
                .join(Psychologist, Slot.id_psychologist == Psychologist.id)
                .where(
                    SlotAssignment.id_client == id_client,
                    SlotAssignment.date >= today,
                    SlotAssignment.date <= end_date,
                )
                .order_by(SlotAssignment.date, Slot.time)
            )

            result = await session.execute(q)
            assignments = result.all()

            return [
                {
                    "date": row[0],
                    "time": row[1],
                    "weekday": row[2],
                    "psychologist": row[3] + " " + row[4],
                    "phone": row[5]
                }
                for row in assignments
            ]

        except SQLAlchemyError as e:
            print(f"Ошибка при получении записей: {e}")
            return []
