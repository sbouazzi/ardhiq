from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.analysis import Analysis


def _to_float(s: str) -> float | None:
    try:
        return float(s)
    except Exception:
        return None


# Very lightweight extraction (best-effort). We'll improve as we get real data.
HA_RE = re.compile(r"(\d+(?:[\.,]\d+)?)\s*(?:ha|hectare|هكتار)", re.IGNORECASE)
TREE_RE = re.compile(r"(\d{2,6})\s*(?:شجرة|أشجار|arbres|arbre|trees)\s*(?:زيتون|olive|oliviers)?", re.IGNORECASE)
PRICE_TND_RE = re.compile(r"(\d{2,9}(?:[\s\.,]\d{3})*(?:[\.,]\d+)?)\s*(?:tnd|دينار)", re.IGNORECASE)
PRICE_PER_M2_RE = re.compile(r"Per\s*m²\s*:\s*([0-9]+(?:[\.,][0-9]+)?)", re.IGNORECASE)
WATER_DEPTH_RE = re.compile(r"(\d+(?:[\.,]\d+)?)\s*m(?:\b|\s)", re.IGNORECASE)


def _normalize_number(num: str) -> str:
    # remove spaces; normalize comma decimal.
    n = num.replace(" ", "")
    # if looks like thousands separators (.) or (,), remove grouping
    # simple heuristic: remove '.' when also has ','
    if "," in n and "." in n:
        n = n.replace(".", "")
    # handle "470 ألف" isn't covered
    return n.replace(",", ".")


def extract_key_fields(report_md: str) -> dict:
    md = report_md

    # Location: first bullet under Location heading (English template). Works if model keeps headings.
    location_text = None
    m = re.search(r"###\s*📍\s*Location\s*\n-\s*(.+)", md)
    if m:
        location_text = m.group(1).strip()

    # Summary: try Bottom Line block.
    short_summary = None
    m = re.search(r"\*\*Bottom Line:\*\*\s*\n?(.+)", md)
    if m:
        short_summary = m.group(1).strip()
    else:
        # French/Arabic possibilities
        m2 = re.search(r"\*\*(?:Conclusion|Bottom line|الخلاصة|الخلاصة:|خلاصة):\*\*\s*\n?(.+)", md, re.IGNORECASE)
        if m2:
            short_summary = m2.group(1).strip()

    # Area
    area_ha = None
    m = HA_RE.search(md)
    if m:
        area_ha = _to_float(_normalize_number(m.group(1)))

    # Tree count
    tree_count = None
    m = TREE_RE.search(md)
    if m:
        try:
            tree_count = int(_normalize_number(m.group(1)).split(".")[0])
        except Exception:
            tree_count = None

    # Price (TND)
    price_tnd = None
    m = PRICE_TND_RE.search(md)
    if m:
        # strip grouping
        val = _normalize_number(m.group(1))
        # remove trailing .000 etc allowed
        price_tnd = _to_float(val)

    price_per_m2_tnd = None
    m = PRICE_PER_M2_RE.search(md)
    if m:
        price_per_m2_tnd = _to_float(_normalize_number(m.group(1)))

    # Water
    water_depth_m = None
    # Use explicit patterns like "45 متر" might appear; current is generic m
    m = re.search(r"(?:depth|profondeur|بئر|عمق|sondage|puits)[^\n]{0,40}?([0-9]{1,4}(?:[\.,][0-9]+)?)\s*(?:m|متر)", md, re.IGNORECASE)
    if m:
        water_depth_m = _to_float(_normalize_number(m.group(1)))

    water_source = None
    if re.search(r"\bSONEDE\b", md, re.IGNORECASE):
        water_source = "SONEDE"
    elif re.search(r"sondage", md, re.IGNORECASE):
        water_source = "sondage"
    elif re.search(r"puits|well|بئر", md, re.IGNORECASE):
        water_source = "well"

    tree_type = None
    if re.search(r"زيتون|olive|olivier", md, re.IGNORECASE):
        tree_type = "olive"

    return {
        "location_text": location_text,
        "short_summary": short_summary[:300] if short_summary else None,
        "area_ha": area_ha,
        "tree_count": tree_count,
        "tree_type": tree_type,
        "price_tnd": price_tnd,
        "price_per_m2_tnd": price_per_m2_tnd,
        "water_depth_m": water_depth_m,
        "water_source": water_source,
    }


def create_analysis(
    db: Session,
    *,
    offer_text: str,
    image_path: str | None = None,
    user_context: str | None,
    report_markdown: str,
    report_ar_md: str | None,
    report_fr_md: str | None,
    score_total: int | None,
    breakdown: dict | None,
    model: str | None,
    prompt_version: str | None,
    extracted_override: dict | None = None,
    status: str = "ok",
    error_code: str | None = None,
    error_message: str | None = None,
    model_used: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    total_tokens: int | None = None,
) -> Analysis:
    extracted = extract_key_fields(report_fr_md or report_markdown)
    if extracted_override:
        extracted.update({k: v for k, v in extracted_override.items() if v is not None})

    a = Analysis(
        created_at=datetime.utcnow(),
        offer_text=offer_text,
        image_path=image_path,
        user_context=user_context,
        report_markdown=report_markdown,
        report_ar_md=report_ar_md,
        report_fr_md=report_fr_md,
        status=status,
        error_code=error_code,
        error_message=error_message,
        score_total=score_total,
        score_info=(breakdown or {}).get("information_completeness"),
        score_price=(breakdown or {}).get("price_reasonableness"),
        score_viability=(breakdown or {}).get("viability_indicators"),
        score_risk=(breakdown or {}).get("risk_assessment"),
        score_breakdown_json=breakdown,
        model=model,
        prompt_version=prompt_version,
        model_used=model_used,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        **extracted,
    )

    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def get_history(db: Session, limit: int = 50) -> list[Analysis]:
    limit = max(1, min(int(limit), 200))
    return (
        db.query(Analysis)
        .order_by(Analysis.created_at.desc())
        .limit(limit)
        .all()
    )


def get_by_id(db: Session, analysis_id: str) -> Analysis | None:
    return db.query(Analysis).filter(Analysis.id == analysis_id).first()
