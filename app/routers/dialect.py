from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import DialectWord
from ..schemas import CountItem, DialectOut, DialectPage, DialectStats
from ..services.ai_service import ask_with_context
from ..services.ratelimit import rate_limit_ai

router = APIRouter(tags=["方言"])


class TranslateIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=200, description="要翻译的普通话句子")
    city: str | None = Field(None, description="限定地市，如 固原市")


class TranslateOut(BaseModel):
    answer: str
    matched: int
    context_preview: str | None = None


@router.get("", response_model=DialectPage, summary="方言词条列表（搜索 + 筛选 + 分页）")
def list_words(
    q: str | None = Query(None, description="关键词：方言词、普通话词或释义"),
    city: str | None = Query(None, description="地级市，如 固原市"),
    category: str | None = Query(None, description="词语类别，如 名词"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(DialectWord)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(
            DialectWord.dialect.like(like),
            DialectWord.mandarin.like(like),
            DialectWord.meaning.like(like),
        ))
    if city:
        stmt = stmt.where(DialectWord.city == city)
    if category:
        stmt = stmt.where(DialectWord.category == category)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(DialectWord.id).offset((page - 1) * size).limit(size)
    ).all()
    return DialectPage(total=total, page=page, size=size, items=rows)


@router.get("/stats", response_model=DialectStats, summary="统计：按城市 / 按类别")
def stats(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count()).select_from(DialectWord)) or 0
    by_city = db.execute(
        select(DialectWord.city, func.count()).group_by(DialectWord.city)
    ).all()
    by_cat = db.execute(
        select(DialectWord.category, func.count()).group_by(DialectWord.category)
    ).all()
    return DialectStats(
        total=total,
        by_city=[CountItem(key=k, count=c) for k, c in by_city],
        by_category=[CountItem(key=k or "未分类", count=c) for k, c in by_cat],
    )


@router.post("/translate", response_model=TranslateOut, summary="普通话 → 宁夏方言（基于词表 + AI）", dependencies=[Depends(rate_limit_ai)])
def translate(payload: TranslateIn, db: Session = Depends(get_db)):
    text = payload.text
    stmt = select(DialectWord)
    city = (payload.city or "").strip()
    # 忽略 Swagger 占位符 "string" 或非法城市名
    if city and city in {"银川市", "石嘴山市", "吴忠市", "固原市", "中卫市"}:
        stmt = stmt.where(DialectWord.city == city)
    rows = db.scalars(stmt.order_by(DialectWord.id)).all()

    # 先用词表做匹配：普通话词出现在句子里，或方言词出现在句子里
    hits = []
    for w in rows:
        if not w.mandarin:
            continue
        core = w.mandarin.strip()
        if core and (core in text or (w.dialect and w.dialect in text)):
            hits.append(w)

    if hits:
        lines = [
            f"- 普通话「{w.mandarin}」→ 宁夏话「{w.dialect}」（{w.city}"
            + (f"，{w.meaning}" if w.meaning else "") + "）"
            for w in hits[:20]
        ]
        context = "【词表匹配结果】\n" + "\n".join(lines)
    else:
        sample = rows[:15]
        lines = [f"- 普通话「{w.mandarin}」→ 宁夏话「{w.dialect}」（{w.city}）" for w in sample]
        context = (
            "【未在句中找到词表内的词，以下是部分词条供参考】\n" + "\n".join(lines)
            if lines else "【词表为空】"
        )

    prompt = (
        f"请把下面这句普通话翻译成宁夏方言的口语表达：\n「{text}」\n\n"
        "要求：\n"
        "1. 只能使用【词表匹配结果】里给出的方言词，不要自己造词；\n"
        "2. 词表里没有对应说法的地方，保留普通话原词；\n"
        "3. 先给方言译文，再用一句话说明用了哪些词、为什么；\n"
        "4. 如果词表完全匹配不上，就如实说明“词表里没有对应说法”，不要硬翻。"
    )

    try:
        answer = ask_with_context(prompt, context)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI 服务调用失败：{e}") from e

    return TranslateOut(answer=answer, matched=len(hits), context_preview=context[:600])


@router.get("/{word_id}", response_model=DialectOut, summary="方言词条详情")
def get_word(word_id: str, db: Session = Depends(get_db)):
    if not word_id.upper().startswith("NX-") and word_id.isdigit():
        word_id = f"NX-{int(word_id):03d}"
    else:
        word_id = word_id.upper()
    row = db.get(DialectWord, word_id)
    if not row:
        raise HTTPException(status_code=404, detail="词条不存在")
    return row
