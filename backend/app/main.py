from __future__ import annotations

import os
import re
import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None  # type: ignore

try:
    import pytesseract
except Exception:  # pragma: no cover
    pytesseract = None  # type: ignore
from sqlalchemy.orm import Session

from openai import OpenAI

from app.crud.analyses import create_analysis, get_by_id, get_history
from app.db.deps import get_db
from app.routers.admin import router as admin_router

load_dotenv()

APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parent.parent
PROMPT_PATH = REPO_ROOT / "docs" / "ardhiq_system_prompt.md"
UPLOAD_DIR = REPO_ROOT / "backend" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MODEL = os.getenv("MODEL", "openai/gpt-5.2")
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI(title="ArdhIQ API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Admin routes (protected by x-admin-key)
app.include_router(admin_router)


class AnalyzeRequest(BaseModel):
    offer_text: str = Field(..., min_length=1, description="Raw offer text (Arabic/French/English)")
    user_context: str | None = Field(
        default=None,
        description="Optional buyer context (budget, purpose, region preferences).",
    )


class AnalyzeResponse(BaseModel):
    # Raw combined markdown (bilingual)
    report_markdown: str
    # Convenience split for clients
    report_ar_markdown: str | None = None
    report_fr_markdown: str | None = None

    score_total: int | None = None
    score_breakdown: dict[str, int] | None = None

    status: str | None = None
    error_code: str | None = None
    error_message: str | None = None

    # DB id (saved automatically)
    analysis_id: str | None = None


class HistoryItem(BaseModel):
    id: str
    created_at: str
    location_text: str | None = None
    score_total: int | None = None
    short_summary: str | None = None


class AnalysisDetail(BaseModel):
    id: str
    created_at: str
    offer_text: str
    image_path: str | None = None
    user_context: str | None = None

    report_markdown: str | None = None
    report_ar_markdown: str | None = None
    report_fr_markdown: str | None = None

    score_total: int | None = None
    score_breakdown: dict[str, int] | None = None

    location_text: str | None = None
    area_ha: float | None = None
    price_tnd: float | None = None
    price_per_m2_tnd: float | None = None
    water_source: str | None = None
    water_depth_m: float | None = None
    tree_type: str | None = None
    tree_count: int | None = None

    short_summary: str | None = None

    status: str | None = None
    error_code: str | None = None
    error_message: str | None = None


def _load_system_prompt() -> str:
    if PROMPT_PATH.exists():
        return PROMPT_PATH.read_text(encoding="utf-8")
    # Fallback (should not happen in this repo)
    return "You are ArdhIQ. Follow the spec and output the required format."


SCORE_TOTAL_RE = re.compile(r"ArdhIQ Score\s*:\s*(\d{1,3})\s*/\s*100", re.IGNORECASE)
SCORE_LINE_RE = re.compile(r"-\s*([A-Za-z ]+):\s*(\d{1,2})\s*/\s*25")

AR_MARKER = "## العربية"
FR_MARKER = "## Français"


def _extract_scores(markdown: str) -> tuple[int | None, dict[str, int] | None]:
    total = None
    m = SCORE_TOTAL_RE.search(markdown)
    if m:
        try:
            total = int(m.group(1))
        except ValueError:
            total = None

    breakdown: dict[str, int] = {}
    # Parse all matching breakdown lines (labels are in English in the spec)
    for label, val in SCORE_LINE_RE.findall(markdown):
        key = label.strip().lower().replace(" ", "_")
        try:
            breakdown[key] = int(val)
        except ValueError:
            continue

    return total, breakdown or None


def _split_bilingual_report(markdown: str) -> tuple[str | None, str | None]:
    """Split combined report into Arabic + French parts using explicit markers.

    Expected output format from the model:
    
    ## العربية
    ...
    ## Français
    ...
    """
    if AR_MARKER not in markdown or FR_MARKER not in markdown:
        return None, None

    ar_start = markdown.find(AR_MARKER)
    fr_start = markdown.find(FR_MARKER)
    if ar_start == -1 or fr_start == -1:
        return None, None

    if ar_start < fr_start:
        ar = markdown[ar_start + len(AR_MARKER) : fr_start].strip()
        fr = markdown[fr_start + len(FR_MARKER) :].strip()
    else:
        # Unexpected ordering; do best-effort
        fr = markdown[fr_start + len(FR_MARKER) : ar_start].strip()
        ar = markdown[ar_start + len(AR_MARKER) :].strip()

    # Add back headings as section titles (useful when rendering standalone)
    ar_md = f"{AR_MARKER}\n\n{ar}".strip()
    fr_md = f"{FR_MARKER}\n\n{fr}".strip()
    return ar_md, fr_md


JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)


def _extract_json_block(text: str) -> dict | None:
    m = JSON_BLOCK_RE.search(text or "")
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except Exception:
        return None


def _ocr_image_to_text(upload_path: Path) -> str:
    if pytesseract is None or Image is None:
        raise HTTPException(
            status_code=400,
            detail="OCR is not available on this server (missing pillow/pytesseract).",
        )

    try:
        img = Image.open(upload_path)
        # Arabic + French + English is common in Tunisia listings.
        return pytesseract.image_to_string(img, lang="ara+fra+eng").strip()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OCR failed: {str(e)[:200]}")


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "model": MODEL}


@app.get("/api/history", response_model=list[HistoryItem])
def history(limit: int = 50, db: Session = Depends(get_db)) -> list[HistoryItem]:
    rows = get_history(db, limit=limit)
    return [
        HistoryItem(
            id=r.id,
            created_at=r.created_at.isoformat() + "Z",
            location_text=r.location_text,
            score_total=r.score_total,
            short_summary=r.short_summary,
        )
        for r in rows
    ]


@app.get("/api/analysis/{analysis_id}", response_model=AnalysisDetail)
def analysis_detail(analysis_id: str, db: Session = Depends(get_db)) -> AnalysisDetail:
    r = get_by_id(db, analysis_id)
    if not r:
        raise HTTPException(status_code=404, detail="Not found")

    breakdown = r.score_breakdown_json if isinstance(r.score_breakdown_json, dict) else None

    def fnum(v):
        return float(v) if v is not None else None

    return AnalysisDetail(
        id=r.id,
        created_at=r.created_at.isoformat() + "Z",
        offer_text=r.offer_text,
        image_path=r.image_path,
        user_context=r.user_context,
        report_markdown=r.report_markdown,
        report_ar_markdown=r.report_ar_md,
        report_fr_markdown=r.report_fr_md,
        score_total=r.score_total,
        score_breakdown=breakdown,
        location_text=r.location_text,
        area_ha=fnum(r.area_ha),
        price_tnd=fnum(r.price_tnd),
        price_per_m2_tnd=fnum(r.price_per_m2_tnd),
        water_source=r.water_source,
        water_depth_m=fnum(r.water_depth_m),
        tree_type=r.tree_type,
        tree_count=r.tree_count,
        short_summary=r.short_summary,
        status=getattr(r, "status", None),
        error_code=getattr(r, "error_code", None),
        error_message=getattr(r, "error_message", None),
    )


def _run_analysis(req: AnalyzeRequest, db: Session) -> AnalyzeResponse:
    system_prompt = _load_system_prompt()

    user_msg = """Analyze this Tunisia land offer using the ArdhIQ spec.

Rules:
- Output MUST be bilingual, in this exact wrapper format:
  1) A line with: ## العربية
  2) Then the full ArdhIQ report in Arabic (same template/sections as the spec).
  3) A line with: ## Français
  4) Then the full ArdhIQ report in French (same template/sections as the spec).
- Inside each language section: Follow the OUTPUT STRUCTURE exactly as specified (sections and order).
- Keep a conservative, skeptical, protective tone.
- If information is missing, flag it clearly as a risk.
- Do NOT claim verification or ground truth.

After the bilingual markdown report, append ONE JSON code block in this exact format:
```json
{{
  "location_text": "... or null",
  "area_ha": 0.0,
  "price_tnd": 0.0,
  "price_per_m2_tnd": 0.0,
  "water_source": "... or null",
  "water_depth_m": 0.0,
  "tree_type": "... or null",
  "tree_count": 0,
  "short_summary": "1-2 sentences",
  "score_total": 0,
  "score_breakdown": {{
    "information_completeness": 0,
    "price_reasonableness": 0,
    "viability_indicators": 0,
    "risk_assessment": 0
  }}
}}
Use null for unknown fields. Numbers must be numbers.

Offer text:
{offer_text}

""".format(
        offer_text=req.offer_text.strip()
    )

    if req.user_context:
        user_msg += "\nBuyer context (optional):\n---\n{ctx}\n---\n".format(
            ctx=req.user_context.strip()
        )

    offer_text = req.offer_text.strip()
    user_context = req.user_context.strip() if req.user_context else None

    report = ""
    total = None
    breakdown = None
    report_ar = None
    report_fr = None
    extracted_override = None

    status = "ok"
    error_code = None
    error_message = None

    model_used = MODEL
    input_tokens = None
    output_tokens = None
    total_tokens = None

    try:
        resp = client.responses.create(
            model=MODEL,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
        )

        model_used = getattr(resp, "model", None) or MODEL
        usage = getattr(resp, "usage", None)
        if usage is not None:
            input_tokens = getattr(usage, "input_tokens", None)
            output_tokens = getattr(usage, "output_tokens", None)
            total_tokens = getattr(usage, "total_tokens", None)

        report = getattr(resp, "output_text", None) or ""
        print("RAW MODEL OUTPUT:", repr(report[:2000]))

        parsed = _extract_json_block(report)
        if isinstance(parsed, dict):
            extracted_override = {
                "location_text": parsed.get("location_text"),
                "area_ha": parsed.get("area_ha"),
                "price_tnd": parsed.get("price_tnd"),
                "price_per_m2_tnd": parsed.get("price_per_m2_tnd"),
                "water_source": parsed.get("water_source"),
                "water_depth_m": parsed.get("water_depth_m"),
                "tree_type": parsed.get("tree_type"),
                "tree_count": parsed.get("tree_count"),
                "short_summary": parsed.get("short_summary"),
            }
            if isinstance(parsed.get("score_breakdown"), dict):
                breakdown = parsed.get("score_breakdown")
            if parsed.get("score_total") is not None:
                try:
                    total = int(parsed.get("score_total"))
                except Exception:
                    pass

    except Exception as e:
        status = "error"
        error_code = "openai_error"
        error_message = str(e)[:500]

        saved = create_analysis(
            db,
            offer_text=offer_text,
            image_path=None,
            user_context=user_context,
            report_markdown=report,
            report_ar_md=None,
            report_fr_md=None,
            score_total=None,
            breakdown=None,
            model=MODEL,
            prompt_version="spec-v1",
            status=status,
            error_code=error_code,
            error_message=error_message,
            model_used=model_used,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )

        return AnalyzeResponse(
            report_markdown=report,
            report_ar_markdown=None,
            report_fr_markdown=None,
            score_total=None,
            score_breakdown=None,
            status=status,
            error_code=error_code,
            error_message=error_message,
            analysis_id=saved.id,
        )

    try:
        if total is None or breakdown is None:
            t2, b2 = _extract_scores(report)
            total = total if total is not None else t2
            breakdown = breakdown if breakdown is not None else b2

        report_ar, report_fr = _split_bilingual_report(report)

        if report_ar is None and report_fr is None:
            report_ar = report or "No analysis text returned."
            report_fr = None
            status = "error"
            error_code = "parse_error"
            error_message = "Bilingual markers not found"

    except Exception as e:
        status = "error"
        error_code = "parse_error"
        error_message = str(e)[:500]

        if not report_ar:
            report_ar = report or "No analysis text returned."
        if not report_fr:
            report_fr = None

    saved = create_analysis(
        db,
        offer_text=offer_text,
        image_path=None,
        user_context=user_context,
        report_markdown=report,
        report_ar_md=report_ar,
        report_fr_md=report_fr,
        score_total=total,
        breakdown=breakdown,
        model=MODEL,
        prompt_version="spec-v1",
        extracted_override=extracted_override,
        status=status,
        error_code=error_code,
        error_message=error_message,
        model_used=model_used,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
    )

    return AnalyzeResponse(
        report_markdown=report,
        report_ar_markdown=report_ar,
        report_fr_markdown=report_fr,
        score_total=total,
        score_breakdown=breakdown,
        status=status,
        error_code=error_code,
        error_message=error_message,
        analysis_id=saved.id,
    )

@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(
    request: Request,
    db: Session = Depends(get_db),
) -> AnalyzeResponse:
    content_type = (request.headers.get("content-type") or "").lower()

    if "application/json" in content_type:
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON body.")

        try:
            req = AnalyzeRequest.model_validate(payload)
        except Exception as e:
            raise HTTPException(status_code=422, detail=str(e))

        return _run_analysis(req, db)

    form = await request.form()
    offer_text = str(form.get("offer_text") or "")
    user_context_raw = form.get("user_context")
    user_context = str(user_context_raw).strip() if user_context_raw is not None else None
    image = form.get("image")

    ocr_text = None
    saved_path = None
    if image is not None and hasattr(image, "read"):
        suffix = Path(getattr(image, "filename", None) or "upload").suffix or ".png"
        fname = f"{os.urandom(8).hex()}{suffix}"
        saved_path = UPLOAD_DIR / fname
        content = await image.read()
        saved_path.write_bytes(content)
        ocr_text = _ocr_image_to_text(saved_path)

    combined = "\n\n".join([t.strip() for t in [offer_text, ocr_text or ""] if t and t.strip()]).strip()
    if not combined:
        raise HTTPException(status_code=400, detail="No offer text found (paste text or upload a screenshot).")

    req = AnalyzeRequest(offer_text=combined, user_context=user_context)
    resp = _run_analysis(req, db)

    if saved_path and resp.analysis_id:
        try:
            from app.models.analysis import Analysis

            row = db.query(Analysis).filter(Analysis.id == resp.analysis_id).first()
            if row:
                row.image_path = str(saved_path.relative_to(REPO_ROOT))
                db.commit()
        except Exception:
            pass

    return resp


@app.post("/api/analyze_json", response_model=AnalyzeResponse)
def analyze_json(req: AnalyzeRequest, db: Session = Depends(get_db)) -> AnalyzeResponse:
    return _run_analysis(req, db)
