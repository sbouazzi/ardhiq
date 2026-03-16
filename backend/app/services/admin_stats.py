from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import case, func
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.models.analysis import Analysis


def get_dashboard_stats(db: Session) -> dict[str, Any]:
    """Compute admin dashboard metrics.

    Designed to be efficient on SQLite while remaining portable.
    Returns mostly-aggregated data; the client may fill missing days.
    """

    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    tomorrow_start = today_start + timedelta(days=1)

    last_7_days_start = now - timedelta(days=7)
    last_30_days_start = now - timedelta(days=30)

    # One query for the "headline" metrics + completion health aggregates.
    parsing_failed_expr = (
        (func.coalesce(Analysis.status, "ok") != "ok")
        | (Analysis.error_code.isnot(None))
        | (Analysis.error_message.isnot(None))
    )

    (
        total_analyses,
        analyses_today,
        analyses_last_7_days,
        analyses_last_30_days,
        average_score_total,
        average_score_last_7_days,
        has_score_count,
        bilingual_ok_count,
        parsing_failed_count,
    ) = (
        db.query(
            func.count(Analysis.id),
            func.sum(
                case(
                    (
                        (Analysis.created_at >= today_start) & (Analysis.created_at < tomorrow_start),
                        1,
                    ),
                    else_=0,
                )
            ),
            func.sum(case((Analysis.created_at >= last_7_days_start, 1), else_=0)),
            func.sum(case((Analysis.created_at >= last_30_days_start, 1), else_=0)),
            func.avg(Analysis.score_total),
            func.avg(case((Analysis.created_at >= last_7_days_start, Analysis.score_total), else_=None)),
            func.sum(case((Analysis.score_total.isnot(None), 1), else_=0)),
            func.sum(case(((Analysis.report_ar_md.isnot(None)) & (Analysis.report_fr_md.isnot(None)), 1), else_=0)),
            func.sum(case((parsing_failed_expr, 1), else_=0)),
        )
        .one()
    )

    # Token aggregates (last 30 days)
    # Be defensive: if migrations weren't applied yet, SQLite will raise OperationalError.
    tokens_total_last_30_days = 0
    avg_tokens_per_analysis_last_30_days = None
    top_models_last_30_days: list[dict[str, Any]] = []

    try:
        tokens_total_last_30_days, avg_tokens_per_analysis_last_30_days = (
            db.query(
                func.sum(case((Analysis.created_at >= last_30_days_start, Analysis.total_tokens), else_=None)),
                func.avg(case((Analysis.created_at >= last_30_days_start, Analysis.total_tokens), else_=None)),
            )
            .one()
        )

        model_expr = func.coalesce(func.nullif(func.trim(Analysis.model_used), ""), "Unknown")
        top_models_rows = (
            db.query(
                model_expr.label("model"),
                func.count(Analysis.id).label("count"),
                func.sum(Analysis.total_tokens).label("total_tokens"),
            )
            .filter(Analysis.created_at >= last_30_days_start)
            .group_by("model")
            .order_by(func.count(Analysis.id).desc())
            .all()
        )
        top_models_last_30_days = [
            {
                "model": r.model,
                "count": int(r.count),
                "total_tokens": int(r.total_tokens) if r.total_tokens is not None else 0,
            }
            for r in top_models_rows
        ]
    except OperationalError:
        # Columns may not exist yet.
        tokens_total_last_30_days, avg_tokens_per_analysis_last_30_days = 0, None
        top_models_last_30_days = []

    # Lowest 5 scores (ignore NULL scores).
    lowest_rows = (
        db.query(Analysis.id, Analysis.score_total, Analysis.location_text)
        .filter(Analysis.score_total.isnot(None))
        .order_by(Analysis.score_total.asc(), Analysis.created_at.desc())
        .limit(5)
        .all()
    )
    lowest_5_scores = [
        {
            "id": r.id,
            "score_total": int(r.score_total) if r.score_total is not None else None,
            "location_text": r.location_text,
        }
        for r in lowest_rows
    ]

    # Errors breakdown (last 30 days) + recent errors
    errors_breakdown_last_30_days: list[dict[str, Any]] = []
    recent_errors: list[dict[str, Any]] = []

    error_code_expr = func.coalesce(func.nullif(func.trim(Analysis.error_code), ""), "unknown")
    error_rows = (
        db.query(error_code_expr.label("error_code"), func.count(Analysis.id).label("count"))
        .filter(Analysis.created_at >= last_30_days_start)
        .filter((Analysis.status != "ok") | (Analysis.error_code.isnot(None)) | (Analysis.error_message.isnot(None)))
        .group_by("error_code")
        .order_by(func.count(Analysis.id).desc())
        .all()
    )
    errors_breakdown_last_30_days = [
        {"error_code": r.error_code, "count": int(r.count)} for r in error_rows
    ]

    recent_error_rows = (
        db.query(Analysis.id, Analysis.created_at, Analysis.error_code, Analysis.error_message)
        .filter((Analysis.status != "ok") | (Analysis.error_code.isnot(None)) | (Analysis.error_message.isnot(None)))
        .order_by(Analysis.created_at.desc())
        .limit(20)
        .all()
    )
    recent_errors = [
        {
            "id": r.id,
            "created_at": r.created_at.isoformat() + "Z",
            "error_code": r.error_code,
            "error_message": (r.error_message[:300] if r.error_message else None),
        }
        for r in recent_error_rows
    ]

    # Usage by region.
    # Normalize NULL/empty to "Unknown" at query time.
    region_expr = func.nullif(func.trim(Analysis.location_text), "")
    usage_rows = (
        db.query(func.coalesce(region_expr, "Unknown").label("region"), func.count(Analysis.id).label("count"))
        .group_by("region")
        .order_by(func.count(Analysis.id).desc())
        .all()
    )
    usage_by_region = [{"region": r.region, "count": int(r.count)} for r in usage_rows]

    # Analyses per day for last 30 days (sparse list; client can fill missing dates).
    per_day_rows = (
        db.query(func.date(Analysis.created_at).label("day"), func.count(Analysis.id).label("count"))
        .filter(Analysis.created_at >= last_30_days_start)
        .group_by("day")
        .order_by("day")
        .all()
    )
    analyses_per_day_last_30_days = [
        {"date": str(r.day), "count": int(r.count)} for r in per_day_rows
    ]

    total = int(total_analyses or 0)
    has_score_count_i = int(has_score_count or 0)
    bilingual_ok_count_i = int(bilingual_ok_count or 0)
    parsing_failed_count_i = int(parsing_failed_count or 0)

    def pct(n: int, d: int) -> float:
        return (n / d * 100.0) if d > 0 else 0.0

    return {
        "total_analyses": total,
        "analyses_today": int(analyses_today or 0),
        "analyses_last_7_days": int(analyses_last_7_days or 0),
        "analyses_last_30_days": int(analyses_last_30_days or 0),
        "average_score_total": float(average_score_total) if average_score_total is not None else None,
        "average_score_last_7_days": float(average_score_last_7_days) if average_score_last_7_days is not None else None,
        "completion_health": {
            "has_score": {"count": has_score_count_i, "pct": pct(has_score_count_i, total)},
            "bilingual_ok": {"count": bilingual_ok_count_i, "pct": pct(bilingual_ok_count_i, total)},
            "parsing_failed": {"count": parsing_failed_count_i, "pct": pct(parsing_failed_count_i, total)},
        },
        "tokens_total_last_30_days": int(tokens_total_last_30_days) if tokens_total_last_30_days is not None else 0,
        "avg_tokens_per_analysis_last_30_days": float(avg_tokens_per_analysis_last_30_days)
        if avg_tokens_per_analysis_last_30_days is not None
        else None,
        "top_models_last_30_days": top_models_last_30_days,
        "errors_breakdown_last_30_days": errors_breakdown_last_30_days,
        "recent_errors": recent_errors,
        "lowest_5_scores": lowest_5_scores,
        "usage_by_region": usage_by_region,
        "analyses_per_day_last_30_days": analyses_per_day_last_30_days,
    }


def get_admin_secret() -> str | None:
    return os.getenv("ADMIN_SECRET")
