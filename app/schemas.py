from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ScenicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scenic_id: int
    name: str
    city: str
    level: str
    address: str | None = None
    data_source: str | None = None
    longitude: Decimal | None = None
    latitude: Decimal | None = None
    tags: str | None = None


class ScenicPage(BaseModel):
    total: int
    page: int
    size: int
    items: list[ScenicOut]


class CountItem(BaseModel):
    key: str
    count: int


class ScenicStats(BaseModel):
    total: int
    with_address: int
    by_level: list[CountItem]
    by_city: list[CountItem]


class DialectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    mandarin: str
    dialect: str
    city: str
    county: str | None = None
    pinyin: str | None = None
    ipa: str | None = None
    meaning: str | None = None
    scenario: str | None = None
    example_dialect: str | None = None
    category: str | None = None
    source_name: str | None = None
    author: str | None = None
    pub_year: str | None = None
    page: str | None = None


class DialectPage(BaseModel):
    total: int
    page: int
    size: int
    items: list[DialectOut]


class DialectStats(BaseModel):
    total: int
    by_city: list[CountItem]
    by_category: list[CountItem]


class PlanSpot(BaseModel):
    scenic_id: int
    name: str
    level: str
    city: str
    address: str | None = None
    tags: str | None = None
    desc: str | None = None


class PlanDay(BaseModel):
    day: int
    city: str
    spots: list[PlanSpot]
    note: str


class ItineraryIn(BaseModel):
    days: int = 3
    areas: list[str] | None = None
    interests: list[str] | None = None
    budget: str | None = "舒适"
    must_see: list[str] | None = None


class ItineraryOut(BaseModel):
    days: int
    budget_estimate: int
    budget_note: str
    plan: list[PlanDay]
    summary: str
    disclaimer: str
