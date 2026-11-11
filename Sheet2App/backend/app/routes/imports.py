"""Upload a spreadsheet, see what the AI proposed, confirm it into an app.

    POST /imports                 upload .xlsx -> stored in Supabase Storage -> run_import()
    GET  /imports/{id}            the proposal, reconciliation and warnings
    POST /imports/{id}/confirm    create the app, make the uploader admin, insert the rows
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.app import storage, tables
from backend.app.auth import AuthUser, current_user
from backend.app.config import get_settings
from backend.app.db import get_db
from backend.app.profiles import upsert_profile
from backend.core import run_import

router = APIRouter(prefix="/imports", tags=["imports"])


def _summary(imp: tables.Import) -> dict:
    return {
        "id": str(imp.id),
        "file_name": imp.file_name,
        "status": imp.status,
        "error": imp.error,
        "proposal": imp.proposal,
        "reconciliation": imp.reconciliation,
        "warnings": imp.warnings or [],
        "app_id": str(imp.app_id) if imp.app_id else None,
    }


def _own_import(db: Session, import_id: uuid.UUID, user: AuthUser) -> tables.Import:
    imp = db.get(tables.Import, import_id)
    if imp is None or str(imp.owner_id) != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Import not found")
    return imp


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_import(
    file: UploadFile,
    user: AuthUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    name = file.filename or "upload.xlsx"
    if not name.lower().endswith(".xlsx"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Please upload an Excel .xlsx file")
    data = await file.read()
    if len(data) > get_settings().max_upload_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File is over 25 MB")

    upsert_profile(db, user)  # foreign keys point at the profile row

    imp = tables.Import(
        id=uuid.uuid4(),
        owner_id=uuid.UUID(user.id),
        file_name=name,
        file_path="",
        status="processing",
    )
    imp.file_path = storage.upload(f"{user.id}/{imp.id}.xlsx", data)
    db.add(imp)

    # v1 runs the import inline. When the real parser + LLM make this slow,
    # move it to a FastAPI BackgroundTask and have the frontend poll GET /imports/{id}.
    try:
        result = run_import(data)
    except Exception as exc:  # noqa: BLE001 - report any failure back to the user
        imp.status, imp.error = "failed", str(exc)
        return _summary(imp)

    imp.status = "ready"
    imp.digest = result.digest.model_dump(mode="json")
    imp.proposal = result.proposal.model_dump(mode="json")
    imp.reconciliation = result.reconciliation.model_dump(mode="json")
    imp.rows = result.model_dump(mode="json")["rows"]
    imp.warnings = result.warnings
    return _summary(imp)


@router.get("/{import_id}")
def get_import(import_id: uuid.UUID, user: AuthUser = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    return _summary(_own_import(db, import_id, user))


@router.post("/{import_id}/confirm")
def confirm_import(import_id: uuid.UUID, user: AuthUser = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    imp = _own_import(db, import_id, user)
    if imp.status != "ready" or imp.proposal is None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Import is {imp.status}, not ready")
    if imp.app_id is not None:
        return {"app_id": str(imp.app_id)}  # already confirmed; safe to call twice

    owner = uuid.UUID(user.id)
    new_app = tables.App(id=uuid.uuid4(), owner_id=owner, name=imp.proposal.get("name", imp.file_name), spec=imp.proposal)
    db.add(new_app)
    db.flush()  # the app row must exist before memberships/records point at it
    db.add(tables.Membership(app_id=new_app.id, user_id=owner, role="admin"))

    count = 0
    for entity, rows in (imp.rows or {}).items():
        for row in rows:
            data = dict(row)
            state = data.pop("__state__", None)  # from the Status column
            approved_by = data.pop("__approved_by__", None)  # names from "Approved by"
            if approved_by:
                data["_imported_approved_by"] = approved_by
            db.add(tables.Record(app_id=new_app.id, entity=entity, data=data, state=state, created_by=owner))
            count += 1
    # TODO: turn _imported_approved_by names into approvals rows once members can be matched
    # to profiles (docs/contract-notes.md, item 4).

    imp.app_id = new_app.id
    return {"app_id": str(new_app.id), "records_imported": count}
