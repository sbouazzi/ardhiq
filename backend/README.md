# ArdhIQ Backend (FastAPI)

## Endpoints
- `GET /health`
- `POST /api/analyze` (auto-saves to SQLite)
- `GET /api/history?limit=50`
- `GET /api/analysis/{id}`

### POST /api/analyze
Request:
```json
{
  "offer_text": "أرض فلاحية للبيع 7 هكتارات ...",
  "user_context": "optional"
}
```

Response:
```json
{
  "report_markdown": "...combined bilingual markdown...",
  "report_ar_markdown": "...arabic section markdown...",
  "report_fr_markdown": "...french section markdown...",
  "score_total": 72,
  "score_breakdown": {
    "information_completeness": 18,
    "price_reasonableness": 17,
    "viability_indicators": 20,
    "risk_assessment": 17
  },
  "analysis_id": "0f1c0a4c-..."
}
```

## Config
Use `.env`:
- `OPENAI_API_KEY`
- `MODEL` (default: `openai/gpt-5.2`)
- `ALLOWED_ORIGINS` (comma-separated or `*`)
- `DATABASE_URL` (optional; default is `backend/data/ardhiq.sqlite`)

## Migrations
From `backend/`:
```bash
alembic upgrade head
```
