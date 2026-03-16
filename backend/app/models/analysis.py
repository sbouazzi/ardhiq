from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    offer_text: Mapped[str] = mapped_column(Text)
    image_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_context: Mapped[str | None] = mapped_column(Text, nullable=True)

    report_markdown: Mapped[str] = mapped_column(Text)
    report_ar_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_fr_md: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(16), default="ok")
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    score_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_info: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_viability: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_risk: Mapped[int | None] = mapped_column(Integer, nullable=True)

    location_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    area_ha: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)
    price_tnd: Mapped[float | None] = mapped_column(Numeric(14, 3), nullable=True)
    price_per_m2_tnd: Mapped[float | None] = mapped_column(Numeric(14, 6), nullable=True)

    water_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    water_depth_m: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)

    tree_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tree_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    short_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Token usage tracking (cost estimation later)
    model_used: Mapped[str | None] = mapped_column(String(128), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)

    score_breakdown_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
