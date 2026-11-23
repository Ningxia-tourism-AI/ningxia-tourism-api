from decimal import Decimal

from sqlalchemy import Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class ScenicSpot(Base):
    __tablename__ = "scenic_spots"

    scenic_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(20), nullable=False)
    level: Mapped[str] = mapped_column(String(4), nullable=False)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    data_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    tags: Mapped[str | None] = mapped_column(String(100), nullable=True)


class DialectWord(Base):
    __tablename__ = "dialect_words"

    id: Mapped[str] = mapped_column(String(10), primary_key=True)
    mandarin: Mapped[str] = mapped_column(String(50), nullable=False)
    dialect: Mapped[str] = mapped_column(String(50), nullable=False)
    city: Mapped[str] = mapped_column(String(20), nullable=False)
    county: Mapped[str | None] = mapped_column(String(20), nullable=True)
    site: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pinyin: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ipa: Mapped[str | None] = mapped_column(String(100), nullable=True)
    meaning: Mapped[str | None] = mapped_column(Text, nullable=True)
    scenario: Mapped[str | None] = mapped_column(String(20), nullable=True)
    example_dialect: Mapped[str | None] = mapped_column(String(300), nullable=True)
    example_standard: Mapped[str | None] = mapped_column(String(300), nullable=True)
    category: Mapped[str | None] = mapped_column(String(30), nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    author: Mapped[str | None] = mapped_column(String(60), nullable=True)
    pub_year: Mapped[str | None] = mapped_column(String(10), nullable=True)
    page: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    verify_status: Mapped[str | None] = mapped_column(String(10), nullable=True)
