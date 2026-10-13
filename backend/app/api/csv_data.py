from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_export_user
from app.core.db import get_session, get_snapshot_session
from app.models import User
from app.schemas.csv_data import CsvExportOut, CsvImportIn, CsvKind, CsvPreviewOut
from app.services import csv_service

router = APIRouter(prefix="/data", tags=["data"])


@router.post("/preview", response_model=CsvPreviewOut)
async def preview(
    body: CsvImportIn,
    response: Response,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    response.headers["Cache-Control"] = "no-store"
    return await csv_service.import_csv(session, user, body)


@router.post("/import", response_model=CsvPreviewOut)
async def import_data(
    body: CsvImportIn,
    response: Response,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    response.headers["Cache-Control"] = "no-store"
    return await csv_service.import_csv(session, user, body, commit=True)


@router.get("/export/{kind}", response_model=CsvExportOut)
async def export(
    kind: CsvKind,
    response: Response,
    user: User = Depends(get_export_user),
    session: AsyncSession = Depends(get_snapshot_session),
):
    response.headers["Cache-Control"] = "no-store"
    return CsvExportOut(
        filename=f"sleepguide-{kind}-{datetime.now(UTC):%Y-%m-%d}.csv",
        csv=await csv_service.export_csv(session, user, kind),
    )
