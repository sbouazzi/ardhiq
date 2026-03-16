# ArdhIQ (Spec-based MVP)

This repo contains a **Next.js web app**, a **Flutter mobile app**, and a **Python backend** implementing the ArdhIQ spec you shared:
- Conservative, skeptical land-offer analysis for Tunisia
- Fixed output template + 0–100 scoring breakdown

## Repo layout
- `backend/` – FastAPI service (SQLite + SQLAlchemy + OpenAI + optional OCR)
- `web/` – Next.js MVP web app (landing, analyze, result, history, admin)
- `mobile/` – Flutter app (API client + UI to paste offers and view reports)
- `docs/` – spec documents copied from chat

## Quick start (backend)
1. Create `backend/.env`:
   ```bash
   OPENAI_API_KEY=sk-...
   MODEL=openai/gpt-5.2
   ```
2. Run:
   ```bash
   cd backend
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   ```
3. Test:
   ```bash
   curl -X POST http://localhost:8000/api/analyze \
     -H 'Content-Type: application/json' \
     -d '{"offer_text":"أرض فلاحية للبيع 7 هكتارات 1200 شجرة زيتون بئر 45 متر 470 ألف دينار"}'
   ```

## Quick start (Web)
1. Configure `web/.env.local` from `web/.env.example`.
2. Run:
   ```bash
   cd web
   npm install
   npm run dev
   ```
3. Open <http://localhost:3000>.

## Quick start (Flutter)
1. Install Flutter (local machine).
2. From `mobile/`:
   ```bash
   flutter pub get
   flutter run
   ```
3. Set backend base URL inside the app (Settings).

## Notes
- The authoritative analysis rules live in `docs/ardhiq_system_prompt.md`.
- The backend **instructs the model to output exactly** using that template.
