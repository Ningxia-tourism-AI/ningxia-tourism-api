from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import ScenicSpot
from ..schemas import ItineraryIn, ItineraryOut, PlanDay, PlanSpot
from ..services.ai_service import ask_with_context

router = APIRouter(tags=["行程"])

BUDGET = {"经济": 400, "舒适": 700, "品质": 1200}
CITY_ORDER = ["银川市", "石嘴山市", "吴忠市", "固原市", "中卫市"]
LEVEL_SCORE = {"5A": 5, "4A": 4, "3A": 3, "2A": 2, "1A": 1}
VALID_TAGS = ["自然风光", "历史人文", "美食", "亲子", "摄影", "徒步", "冬季"]


def _score(spot: ScenicSpot, interests: list[str]) -> float:
    s = LEVEL_SCORE.get(spot.level, 1)
    tags = (spot.tags or "").split("、")
    s += 3 * len([t for t in tags if t in interests])
    return s


def _order_by_distance(items: list[ScenicSpot]) -> list[ScenicSpot]:
    with_geo = [s for s in items if s.latitude is not None]
    without = [s for s in items if s.latitude is None]
    if len(with_geo) < 2:
        return items
    rest = with_geo[1:]
    ordered = [with_geo[0]]
    while rest:
        last = ordered[-1]
        nxt = min(rest, key=lambda s: (float(s.latitude) - float(last.latitude)) ** 2
                  + (float(s.longitude) - float(last.longitude)) ** 2)
        ordered.append(nxt)
        rest.remove(nxt)
    return ordered + without


@router.post("/plan", response_model=ItineraryOut, summary="按条件生成行程（规则选点 + AI 说明）")
def plan(payload: ItineraryIn, db: Session = Depends(get_db)):
    days = max(1, min(payload.days, 7))
    interests = [t for t in (payload.interests or []) if t in VALID_TAGS]
    must = [m for m in (payload.must_see or []) if m]

    spots = db.scalars(select(ScenicSpot)).all()
    pool = spots
    if payload.areas:
        pool = [s for s in pool if s.city in payload.areas]
    if interests:
        matched = [s for s in pool if any(t in (s.tags or "") for t in interests)]
        pool = matched or pool

    forced = [s for s in spots if s.name in must]
    available = payload.areas or [c for c in CITY_ORDER if any(s.city == c for s in pool)]
    if not available:
        available = ["银川市"]

    # 选几个城市：天少则集中，天多则分散；必去景点所在城市优先
    need = 1 if days <= 2 else (2 if days <= 4 else 3)
    cities = list(dict.fromkeys(available))[:need]
    for s in forced:
        if s.city not in cities:
            cities.append(s.city)
    cities = cities[:3]

    # 每天 2 个还是 3 个
    per_day = 2 if days <= 2 else 3

    # 按城市分配天数（均衡），并维护每城待用队列，避免跨天重复
    alloc, base, rem = {}, days // len(cities), days % len(cities)
    for i, c in enumerate(cities):
        alloc[c] = base + (1 if i < rem else 0)
    # 必去景点所在城市至少 1 天
    for s in forced:
        if alloc.get(s.city, 0) == 0:
            donor = max(alloc, key=alloc.get)
            if alloc[donor] > 1:
                alloc[donor] -= 1
                alloc[s.city] = 1

    queues = {}
    for c in cities:
        items = [s for s in pool if s.city == c]
        items.sort(key=lambda s: _score(s, interests), reverse=True)
        for s in forced:
            if s.city == c and s in items:
                items.remove(s)
                items.insert(0, s)
        queues[c] = items

    plan_days: list[PlanDay] = []
    day_no = 0
    for c in cities:
        for _ in range(alloc.get(c, 0)):
            day_no += 1
            take = queues[c][:per_day]
            del queues[c][:per_day]
            if not take:
                take = [s for s in pool if s.city == c][:per_day]
            take = _order_by_distance(take)
            plan_spots = [
                PlanSpot(
                    scenic_id=s.scenic_id, name=s.name, level=s.level, city=s.city,
                    address=s.address, tags=s.tags,
                    desc=f"{s.level}级景区，位于{s.city}" + (f"，{s.address}" if s.address else "") + "。",
                )
                for s in take
            ]
            plan_days.append(PlanDay(
                day=day_no, city=c, spots=plan_spots,
                note=f"本日集中在{c}，安排 {len(plan_spots)} 个景点，按同城就近顺序排列。",
            ))

    tier = payload.budget if payload.budget in BUDGET else "舒适"
    estimate = BUDGET[tier] * days

    context = "\n".join(
        f"第{d.day}天 {d.city}：" + "、".join(s.name for s in d.spots) for d in plan_days
    )
    prompt = (
        "下面是一份按用户条件生成的宁夏行程框架（景点已由系统选定）。"
        "请用 2-3 句话写一段总述：整体节奏、覆盖了哪些类型的地方、适合什么样的游客。"
        "不要新增景点，不要编造门票、开放时间或车程。\n\n" + context
    )
    try:
        summary = ask_with_context(prompt, context).strip()
    except Exception:
        summary = f"共 {days} 天，覆盖 {('、'.join(cities))}，按同城就近安排，节奏适中。"

    return ItineraryOut(
        days=days,
        budget_estimate=estimate,
        budget_note=f"{tier}档 × {days} 天，人均参考，不含往返大交通",
        plan=plan_days,
        summary=summary,
        disclaimer="行程由规则生成，未考虑实时路况与景区闭园；门票、开放时间以景区官方发布为准。",
    )
