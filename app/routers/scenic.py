from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import ScenicSpot
from ..schemas import CountItem, ScenicOut, ScenicPage, ScenicStats

router = APIRouter(prefix="/api/scenic", tags=["景区"])


@router.get("", response_model=ScenicPage, summary="景区列表（筛选 + 分页）")
def list_scenic(
    city: str | None = Query(None, description="地级市，如 银川市"),
    level: str | None = Query(None, description="等级，如 5A"),
    keyword: str | None = Query(None, description="名称模糊搜索"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(ScenicSpot)
    if city:
        stmt = stmt.where(ScenicSpot.city == city)
    if level:
        stmt = stmt.where(ScenicSpot.level == level)
    if keyword:
        stmt = stmt.where(ScenicSpot.name.like(f"%{keyword}%"))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(ScenicSpot.scenic_id).offset((page - 1) * size).limit(size)
    ).all()
    return ScenicPage(total=total, page=page, size=size, items=rows)


@router.get("/stats", response_model=ScenicStats, summary="统计：按等级 / 按城市")
def stats(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count()).select_from(ScenicSpot)) or 0
    with_addr = db.scalar(
        select(func.count()).select_from(ScenicSpot).where(ScenicSpot.address.is_not(None))
    ) or 0
    by_level = db.execute(
        select(ScenicSpot.level, func.count()).group_by(ScenicSpot.level)
    ).all()
    by_city = db.execute(
        select(ScenicSpot.city, func.count()).group_by(ScenicSpot.city)
    ).all()
    return ScenicStats(
        total=total,
        with_address=with_addr,
        by_level=[CountItem(key=k, count=c) for k, c in by_level],
        by_city=[CountItem(key=k, count=c) for k, c in by_city],
    )


@router.get("/{scenic_id}", response_model=ScenicOut, summary="景区详情")
def get_scenic(scenic_id: int, db: Session = Depends(get_db)):
    row = db.get(ScenicSpot, scenic_id)
    if not row:
        raise HTTPException(status_code=404, detail="景区不存在")
    return row
