from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.services.admin_stats import get_admin_secret, get_dashboard_stats
from app.services.admin_metrics import get_metrics

router = APIRouter(prefix="/api/admin", tags=["admin"])


def require_admin_key(x_admin_key: str | None = Header(default=None, alias="x-admin-key")) -> None:
    secret = get_admin_secret()
    if not secret:
        # Safer default: do not run an admin endpoint without a configured secret.
        raise HTTPException(status_code=500, detail="ADMIN_SECRET is not configured")

    if not x_admin_key or x_admin_key != secret:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.get("/metrics")
def admin_metrics(
    _auth: None = Depends(require_admin_key),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return get_metrics(db)


@router.get("/dashboard")
def admin_dashboard(
    _auth: None = Depends(require_admin_key),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    # Backwards-compatible flat payload for the current mobile MVP UI.
    return get_dashboard_stats(db)


@router.get("/stats")
def admin_stats(
    _auth: None = Depends(require_admin_key),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    # Alias for the web MVP.
    return get_dashboard_stats(db)
