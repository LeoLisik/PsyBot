from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Time, Date
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Weekday(Base):
    __tablename__ = "weekday"

    id = Column(Integer, primary_key=True)
    name_ru = Column(String, nullable=False)

    slots = relationship("Slot", back_populates="weekday")


class Psychologist(Base):
    __tablename__ = "psychologist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    surname = Column(String, nullable=False)
    name = Column(String, nullable=False)
    patronymic = Column(String, nullable=True)
    phone = Column(String, nullable=False)

    slots = relationship("Slot", back_populates="psychologist")


class Slot(Base):
    __tablename__ = "slot"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_day = Column(Integer, ForeignKey("weekday.id"), nullable=False)  # например, 1=понедельник, 2=вторник...
    id_psychologist = Column(Integer, ForeignKey("psychologist.id"), nullable=False)
    is_even_week = Column(Boolean, default=False)  # 0/1 -> False/True
    time = Column(Time, nullable=False)
    is_active = Column(Boolean, default=True)

    # связь с психологом
    psychologist = relationship("Psychologist", back_populates="slots")
    assignments = relationship("SlotAssignment", back_populates="slot")
    weekday = relationship("Weekday", back_populates="slots")


class SlotAssignment(Base):
    __tablename__ = "slot_assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_slot = Column(Integer, ForeignKey("slot.id"), nullable=False)
    date = Column(Date, nullable=False)  # хранится как 'YYYY-MM-DD'
    id_client = Column(Integer, ForeignKey("client.id"), nullable=False)

    slot = relationship("Slot", back_populates="assignments")
    client = relationship("Client", back_populates="assignments")


class Client(Base):
    __tablename__ = "client"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_telegram = Column(Integer, nullable=False)
    surname = Column(String, nullable=False)
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    id_institute = Column(Integer, ForeignKey("institute.id"), nullable=False)

    assignments = relationship("SlotAssignment", back_populates="client")
    institute = relationship("Institute", back_populates="clients")


class Institute(Base):
    __tablename__ = "institute"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)

    clients = relationship("Client", back_populates="institute")
