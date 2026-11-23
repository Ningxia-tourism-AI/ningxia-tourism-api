import re
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import DialectWord, ScenicSpot
from ..services.ai_service import ask_with_context
from ..services.ratelimit import rate_limit_ai

router = APIRouter()

CITIES = ["银川市", "石嘴山市", "吴忠市", "固原市", "中卫市"]
LEVELS = ["5A", "4A", "3A", "2A", "1A"]
SUFFIXES = ("旅游景区", "旅游度假区", "生态旅游区", "风景旅游区", "文化旅游区", "旅游区", "景区")


class ChatIn(BaseModel):
    question: str = Field(..., min_length=1, max_length=500, description="用户问题")


class ChatOut(BaseModel):
    answer: str
    matched: int
    dialect_matched: int = 0
    source: str = "ai"
    context_preview: str | None = None


def _core(name: str) -> str:
    s = re.sub(r"[\s·▪・\.，,、\-—（）()]", "", name or "")
    for suf in SUFFIXES:
        if s.endswith(suf) and len(s) > len(suf):
            s = s[: -len(suf)]
            break
    return s


def _fmt(row: ScenicSpot) -> str:
    addr = f"，地址：{row.address}" if row.address else "，地址暂未收录"
    return f"- {row.name}（{row.city}，{row.level}{addr}）"


def _dialect_part(db: Session, question: str) -> tuple[str, int]:
    """返回 (方言上下文片段, 命中条数)。未命中时允许 AI 推测，但要求标注。"""
    rows = db.scalars(select(DialectWord)).all()
    head = (
        f"\n\n【方言词条库】共 {len(rows)} 条（银川 26 条、固原 21 条；"
        "来源：《银川方言词典》、高顺斌《固原方言四字格词语的结构和语义特点》）。"
    )
    hits = [
        w for w in rows
        if (w.dialect and w.dialect in question)
        or (w.mandarin and len(w.mandarin) >= 2 and w.mandarin in question)
    ]
    if hits:
        lines = [
            f"- 宁夏话「{w.dialect}」= 普通话「{w.mandarin}」；{w.meaning or ''}"
            f"（{w.city}，{w.source_name}{w.page}）"
            for w in hits[:10]
        ]
        return head + "\n本次提问命中的词条：\n" + "\n".join(lines), len(hits)

    return head + (
        "\n本次提问未命中词条。若问题属于宁夏方言类，可以给出你了解的常见说法，但必须做到："
        "① 开头明确写“词库未收录，以下为推测”；"
        "② 说明可能存在的地区差异；③ 不得声称这些说法来自本平台词库。"
    ), 0


def build_context(db: Session, question: str) -> tuple[str, int, int]:
    rows = db.scalars(select(ScenicSpot).order_by(ScenicSpot.scenic_id)).all()
    q = question

    hits = [r for r in rows if r.name in q or (len(_core(r.name)) >= 2 and _core(r.name) in q)]

    city = next((c for c in CITIES if c in q or c[:-1] in q), None)
    level = next((lv for lv in LEVELS if lv in q), None)
    if not hits and (city or level):
        hits = [r for r in rows
                if (not city or r.city == city) and (not level or r.level == level)]

    by_level = Counter(r.level for r in rows)
    by_city = Counter(r.city for r in rows)
    total = len(rows)
    overview = (
        f"全区共 {total} 家 A 级景区：" +
        "、".join(f"{lv} {by_level[lv]} 家" for lv in LEVELS if by_level.get(lv)) +
        "。按城市：" +
        "、".join(f"{c} {by_city[c]} 家" for c in CITIES if by_city.get(c)) + "。"
    )

    if hits:
        shown = hits[:25]
        body = "\n".join(_fmt(r) for r in shown)
        extra = f"（共匹配 {len(hits)} 家，此处列出前 {len(shown)} 家）" if len(hits) > len(shown) else ""
        base = f"{overview}\n\n匹配到的景区{extra}：\n{body}"
    else:
        sample = [r for r in rows if r.level == "5A"][:10] + [r for r in rows if r.level == "4A"][:8]
        body = "\n".join(_fmt(r) for r in sample)
        base = f"{overview}\n\n未匹配到具体景区，以下是部分 5A/4A 景区供参考：\n{body}"

    dial, dial_hits = _dialect_part(db, question)
    return base + dial, len(hits), dial_hits


@router.post("", response_model=ChatOut, summary="AI 问答（景区 + 方言）", dependencies=[Depends(rate_limit_ai)])
def chat(payload: ChatIn, db: Session = Depends(get_db)):
    context, matched, dialect_matched = build_context(db, payload.question)
    try:
        answer = ask_with_context(payload.question, context)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI 服务调用失败：{e}") from e

    # db = 有结构化数据支撑（命中景区/方言词条，或属于库内统计类问题）；ai = 纯模型推测
    stat_words = ("多少", "几家", "统计", "分布", "排名", "总数", "占比")
    is_stat = any(w in payload.question for w in stat_words) and any(
        w in payload.question for w in ("景区", "方言", "宁夏")
    )
    source = "db" if (matched > 0 or dialect_matched > 0 or is_stat) else "ai"
    return ChatOut(
        answer=answer,
        matched=matched,
        dialect_matched=dialect_matched,
        source=source,
        context_preview=context[:600],
    )
