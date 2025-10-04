import os
import asyncpg
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from .models import Base, Weekday, Institute

#DB_URL = "sqlite+aiosqlite:///DB/database.db"
DB_USER = os.getenv("DB_USER", "psybot")
DB_PASSWORD = os.getenv("DB_PASSWORD", "123")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "psybot")

DB_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_async_engine(DB_URL, echo=False)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    # 1. Проверяем и создаём базу через asyncpg
    pg_conn = await asyncpg.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database="postgres"
    )

    exists = await pg_conn.fetchval(
        "SELECT 1 FROM pg_database WHERE datname=$1", DB_NAME
    )

    if not exists:
        await pg_conn.execute(f'CREATE DATABASE "{DB_NAME}"')
        print(f"База {DB_NAME} создана")
    else:
        print(f"База {DB_NAME} уже существует")

    await pg_conn.close()

    # 2. Создаём таблицы через SQLAlchemy
    async with engine.begin() as sa_conn:
        await sa_conn.run_sync(Base.metadata.create_all)

    await insert_days()
    await insert_institutes()


async def insert_days():
    weekdays = [
        {"id": 1, "name_ru": "Пн"},
        {"id": 2, "name_ru": "Вт"},
        {"id": 3, "name_ru": "Ср"},
        {"id": 4, "name_ru": "Чт"},
        {"id": 5, "name_ru": "Пт"},
        {"id": 6, "name_ru": "Сб"},
        {"id": 7, "name_ru": "Вс"},
    ]

    async with SessionLocal() as session:
        # Проверяем, есть ли уже записи
        result = await session.execute(select(Weekday.id))
        if not result.scalars().first():
            await session.execute(insert(Weekday), weekdays)
            await session.commit()
            print("Дни недели добавлены")


async def insert_institutes():
    institutes = [
        "Колледж",
        "ИД",
        "ИИ",
        "ИМИР",
        "ИИТИЦТ",
        "ИСИ",
        "ИХТИПЭ",
        "ИЭИМ",
        "ТИТЛП",
        "ИСК",
        "Академия",
        "Гимназия",
    ]
    institutes_data = [{"name": inst} for inst in institutes]

    async with SessionLocal() as session:
        result = await session.execute(select(Institute.id))
        if not result.scalars().first():
            await session.execute(insert(Institute), institutes_data)
            await session.commit()
