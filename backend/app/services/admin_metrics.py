from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import case, func
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.models.analysis import Analysis


def _isoz(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat() + "Z"


def _date_key(dt: datetime) -> str:
    return dt.date().isoformat()


def get_metrics(db: Session) -> dict[str, Any]:
    """Return admin metrics using the exact JSON shape requested.

    - UTC timestamps
    - All computed from analyses table
    - Defensive around optional token columns (SQLite OperationalError)
    """

    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    last_7_days_start = today_start - timedelta(days=6)
    last_30_days_start = today_start - timedelta(days=29)

    tomorrow_start = today_start + timedelta(days=1)

    # Totals + completion health counts in one pass.
    parsing_failed_expr = (func.coalesce(Analysis.status, "ok") != "ok") | (Analysis.error_code == "parse_error")
    openai_failed_expr = (func.coalesce(Analysis.status, "ok") != "ok") | (Analysis.error_code == "openai_error")

    (
        total_analyses,
        analyses_today,
        analyses_last_7_days,
        analyses_last_30_days,
        has_score_count,
        bilingual_ok_count,
        parsing_failed_count,
        openai_failed_count,
    ) = (
        db.query(
            func.count(Analysis.id),
            func.sum(case(((Analysis.created_at >= today_start) & (Analysis.created_at < tomorrow_start), 1), else_=0)),
            func.sum(case((Analysis.created_at >= last_7_days_start, 1), else_=0)),
            func.sum(case((Analysis.created_at >= last_30_days_start, 1), else_=0)),
            func.sum(case((Analysis.score_total.isnot(None), 1), else_=0)),
            func.sum(case(((Analysis.report_ar_md.isnot(None)) & (Analysis.report_fr_md.isnot(None)), 1), else_=0)),
            func.sum(case((parsing_failed_expr, 1), else_=0)),
            func.sum(case((openai_failed_expr, 1), else_=0)),
        )
        .one()
    )

    total = int(total_analyses or 0)
    counts = {
        "has_score": int(has_score_count or 0),
        "bilingual_ok": int(bilingual_ok_count or 0),
        "parsing_failed": int(parsing_failed_count or 0),
        "openai_failed": int(openai_failed_count or 0),
    }

    def pct(n: int, d: int) -> float:
        return (n / d * 100.0) if d > 0 else 0.0

    completion_health = {
        "counts": counts,
        "pct": {
            "has_score_pct": pct(counts["has_score"], total),
            "bilingual_ok_pct": pct(counts["bilingual_ok"], total),
            "parsing_failed_pct": pct(counts["parsing_failed"], total),
            "openai_failed_pct": pct(counts["openai_failed"], total),
        },
        "notes": {
            "definition": {
                "has_score": "score_total != null",
                "bilingual_ok": "report_ar_md != null AND report_fr_md != null",
                "parsing_failed": "status != 'ok' OR error_code in ('parse_error')",
                "openai_failed": "status != 'ok' OR error_code in ('openai_error')",
            }
        },
    }

    # Usage by day (last 30), filled.
    per_day_rows = (
        db.query(func.date(Analysis.created_at).label("day"), func.count(Analysis.id).label("count"))
        .filter(Analysis.created_at >= last_30_days_start)
        .group_by("day")
        .order_by("day")
        .all()
    )
    per_day_map = {str(r.day): int(r.count) for r in per_day_rows}
    by_day_last_30 = []
    for i in range(30):
        d = last_30_days_start + timedelta(days=i)
        k = _date_key(d)
        by_day_last_30.append({"date": k, "count": per_day_map.get(k, 0)})

    # Usage by region (last 30)
    region_expr = func.coalesce(func.nullif(func.trim(Analysis.location_text), ""), "Unknown")
    region_rows = (
        db.query(region_expr.label("region"), func.count(Analysis.id).label("count"))
        .filter(Analysis.created_at >= last_30_days_start)
        .group_by("region")
        .order_by(func.count(Analysis.id).desc())
        .all()
    )
    by_region_last_30 = [{"region": r.region, "count": int(r.count)} for r in region_rows]

    usage = {
        "by_day_last_30": by_day_last_30,
        "by_region_last_30": by_region_last_30,
    }

    # Scores (last 30): distribution, avg, median, lowest 10
    dist = (
        db.query(
            func.sum(case(((Analysis.created_at >= last_30_days_start) & (Analysis.score_total >= 0) & (Analysis.score_total <= 19), 1), else_=0)),
            func.sum(case(((Analysis.created_at >= last_30_days_start) & (Analysis.score_total >= 20) & (Analysis.score_total <= 39), 1), else_=0)),
            func.sum(case(((Analysis.created_at >= last_30_days_start) & (Analysis.score_total >= 40) & (Analysis.score_total <= 59), 1), else_=0)),
            func.sum(case(((Analysis.created_at >= last_30_days_start) & (Analysis.score_total >= 60) & (Analysis.score_total <= 79), 1), else_=0)),
            func.sum(case(((Analysis.created_at >= last_30_days_start) & (Analysis.score_total >= 80) & (Analysis.score_total <= 100), 1), else_=0)),
            func.sum(case(((Analysis.created_at >= last_30_days_start) & (Analysis.score_total.is_(None)), 1), else_=0)),
        )
        .one()
    )

    avg_score_last_30 = (
        db.query(func.avg(Analysis.score_total))
        .filter(Analysis.created_at >= last_30_days_start)
        .scalar()
    )

    # Median: compute from ordered non-null scores in last 30 days.
    score_count = (
        db.query(func.count(Analysis.score_total))
        .filter(Analysis.created_at >= last_30_days_start)
        .filter(Analysis.score_total.isnot(None))
        .scalar()
    )
    score_count = int(score_count or 0)

    median_score_last_30 = None
    if score_count > 0:
        if score_count % 2 == 1:
            offset = score_count // 2
            mid = (
                db.query(Analysis.score_total)
                .filter(Analysis.created_at >= last_30_days_start)
                .filter(Analysis.score_total.isnot(None))
                .order_by(Analysis.score_total.asc())
                .offset(offset)
                .limit(1)
                .scalar()
            )
            median_score_last_30 = float(mid) if mid is not None else None
        else:
            offset1 = score_count // 2 - 1
            offset2 = score_count // 2
            vals = (
                db.query(Analysis.score_total)
                .filter(Analysis.created_at >= last_30_days_start)
                .filter(Analysis.score_total.isnot(None))
                .order_by(Analysis.score_total.asc())
                .offset(offset1)
                .limit(2)
                .all()
            )
            if len(vals) == 2 and vals[0][0] is not None and vals[1][0] is not None:
                median_score_last_30 = (float(vals[0][0]) + float(vals[1][0])) / 2.0

    lowest_rows = (
        db.query(Analysis.id, Analysis.score_total, Analysis.created_at, Analysis.location_text)
        .filter(Analysis.created_at >= last_30_days_start)
        .filter(Analysis.score_total.isnot(None))
        .order_by(Analysis.score_total.asc(), Analysis.created_at.desc())
        .limit(10)
        .all()
    )
    lowest_10_last_30 = [
        {
            "analysis_id": r.id,
            "score_total": int(r.score_total) if r.score_total is not None else None,
            "created_at": _isoz(r.created_at),
            "location_text": r.location_text,
        }
        for r in lowest_rows
    ]

    scores = {
        "distribution_last_30": {
            "0_19": int(dist[0] or 0),
            "20_39": int(dist[1] or 0),
            "40_59": int(dist[2] or 0),
            "60_79": int(dist[3] or 0),
            "80_100": int(dist[4] or 0),
            "unknown": int(dist[5] or 0),
        },
        "avg_score_last_30": float(avg_score_last_30) if avg_score_last_30 is not None else None,
        "median_score_last_30": median_score_last_30,
        "lowest_10_last_30": lowest_10_last_30,
    }

    # Tokens (last 30) - defensive if columns not migrated.
    tokens_totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    avg_tokens_per_analysis_last_30 = None
    top_models_last_30: list[dict[str, Any]] = []

    try:
        in_sum, out_sum, tot_sum, tot_avg = (
            db.query(
                func.sum(Analysis.input_tokens),
                func.sum(Analysis.output_tokens),
                func.sum(Analysis.total_tokens),
                func.avg(Analysis.total_tokens),
            )
            .filter(Analysis.created_at >= last_30_days_start)
            .one()
        )
        tokens_totals = {
            "input_tokens": int(in_sum) if in_sum is not None else 0,
            "output_tokens": int(out_sum) if out_sum is not None else 0,
            "total_tokens": int(tot_sum) if tot_sum is not None else 0,
        }
        avg_tokens_per_analysis_last_30 = float(tot_avg) if tot_avg is not None else None

        model_expr = func.coalesce(func.nullif(func.trim(Analysis.model_used), ""), "Unknown")
        rows = (
            db.query(
                model_expr.label("model_used"),
                func.count(Analysis.id).label("count"),
                func.sum(Analysis.total_tokens).label("total_tokens"),
                func.avg(Analysis.total_tokens).label("avg_tokens"),
            )
            .filter(Analysis.created_at >= last_30_days_start)
            .group_by("model_used")
            .order_by(func.count(Analysis.id).desc())
            .all()
        )
        top_models_last_30 = [
            {
                "model_used": r.model_used,
                "count": int(r.count),
                "total_tokens": int(r.total_tokens) if r.total_tokens is not None else 0,
                "avg_tokens": float(r.avg_tokens) if r.avg_tokens is not None else None,
            }
            for r in rows
        ]
    except OperationalError:
        # token columns not present
        tokens_totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        avg_tokens_per_analysis_last_30 = None
        top_models_last_30 = []

    tokens = {
        "totals_last_30": tokens_totals,
        "avg_tokens_per_analysis_last_30": avg_tokens_per_analysis_last_30,
        "top_models_last_30": top_models_last_30,
    }

    # Errors: by code last 30 + recent 20
    error_code_expr = func.coalesce(func.nullif(func.trim(Analysis.error_code), ""), "unknown")
    err_rows = (
        db.query(error_code_expr.label("error_code"), func.count(Analysis.id).label("count"))
        .filter(Analysis.created_at >= last_30_days_start)
        .filter((Analysis.status != "ok") | (Analysis.error_code.isnot(None)) | (Analysis.error_message.isnot(None)))
        .group_by("error_code")
        .order_by(func.count(Analysis.id).desc())
        .all()
    )
    by_code_last_30 = [{"error_code": r.error_code, "count": int(r.count)} for r in err_rows]

    recent_rows = (
        db.query(Analysis.id, Analysis.created_at, Analysis.error_code, Analysis.error_message, Analysis.model_used)
        .filter((Analysis.status != "ok") | (Analysis.error_code.isnot(None)) | (Analysis.error_message.isnot(None)))
        .order_by(Analysis.created_at.desc())
        .limit(20)
        .all()
    )
    recent_errors = [
        {
            "analysis_id": r.id,
            "created_at": _isoz(r.created_at),
            "error_code": r.error_code,
            "error_message": (r.error_message[:300] if r.error_message else None),
            "model_used": r.model_used,
        }
        for r in recent_rows
    ]

    errors = {"by_code_last_30": by_code_last_30, "recent_errors": recent_errors}

    return {
        "generated_at": _isoz(now),
        "range": {
            "timezone": "UTC",
            "today_start": _isoz(today_start),
            "last_7_days_start": _isoz(last_7_days_start),
            "last_30_days_start": _isoz(last_30_days_start),
        },
        "totals": {
            "total_analyses": total,
            "analyses_today": int(analyses_today or 0),
            "analyses_last_7_days": int(analyses_last_7_days or 0),
            "analyses_last_30_days": int(analyses_last_30_days or 0),
        },
        "completion_health": completion_health,
        "usage": usage,
        "scores": scores,
        "tokens": tokens,
        "errors": errors,
    }
