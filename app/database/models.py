from datetime import datetime
from typing import List

from sqlalchemy import BigInteger, Integer, String, Boolean, ForeignKey, DateTime, func, Index
from sqlalchemy.orm import DeclarativeBase, mapped_column, relationship, Mapped


class Base(DeclarativeBase):
    created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now()
    )
    updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now()
    )


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(
        autoincrement=True,
        primary_key=True,
        nullable=False
    )
    tg_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        unique=True,
        index=True
    )
    tg_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default=''
    )
    is_blocked: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    goals: Mapped[List["Goal"]] = relationship(
        back_populates="user",
        lazy="selectin",
        uselist=True
    )


class Goal(Base):
    __tablename__ = "goal"

    id: Mapped[int] = mapped_column(
        autoincrement=True,
        primary_key=True,
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default=''
    )

    current_value: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )   

    selected_value: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )   

    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now()
    ) 

    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id"),
        nullable=False
    )   

    

    user: Mapped["User"] = relationship(
        back_populates="goals",
        lazy="selectin",
        uselist=False
    )   


