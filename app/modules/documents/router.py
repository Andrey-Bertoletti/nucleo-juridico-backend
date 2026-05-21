"""Rotas do módulo documents."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.core.dependencies import (
    ROLE_ADMIN,
    ROLE_STUDENT,
    CurrentUser,
    DbSession,
    require_admin,
)
from app.modules.documents import service
from app.modules.documents.schemas import DocumentResponse, DocumentStatusUpdate
from app.modules.users.models import Profile


router = APIRouter(tags=["documents"])


def require_uploader(current_user: CurrentUser) -> Profile:
    if current_user.role not in {ROLE_STUDENT, ROLE_ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas alunos/estagiários e coordenação podem enviar documentos.",
        )
    return current_user


Uploader = Annotated[Profile, Depends(require_uploader)]


@router.get(
    "/attendances/{attendance_id}/documents",
    response_model=list[DocumentResponse],
)
def list_attendance_documents(
    attendance_id: UUID,
    db: DbSession,
    _current: CurrentUser,
) -> list[DocumentResponse]:
    return service.list_by_attendance(db, attendance_id)  # type: ignore[return-value]


@router.post(
    "/attendances/{attendance_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attendance_document(
    attendance_id: UUID,
    db: DbSession,
    current_user: Uploader,
    document_type: str = Form(..., description="Tipo do documento (enum)."),
    notes: str | None = Form(default=None, description="Observação opcional."),
    file: UploadFile = File(..., description="Arquivo a ser enviado."),
) -> DocumentResponse:
    doc = await service.upload_to_attendance(
        db, attendance_id, file, document_type, notes, current_user
    )
    return doc  # type: ignore[return-value]


@router.get(
    "/clients/{client_id}/documents",
    response_model=list[DocumentResponse],
)
def list_client_documents(
    client_id: UUID,
    db: DbSession,
    _current: CurrentUser,
) -> list[DocumentResponse]:
    return service.list_by_client(db, client_id)  # type: ignore[return-value]


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: UUID,
    db: DbSession,
    _current: CurrentUser,
) -> DocumentResponse:
    return service.get_document(db, document_id)  # type: ignore[return-value]


@router.patch(
    "/documents/{document_id}/status", response_model=DocumentResponse
)
def change_document_status(
    document_id: UUID,
    payload: DocumentStatusUpdate,
    db: DbSession,
    current_user: Uploader,
) -> DocumentResponse:
    return service.change_status(db, document_id, payload, current_user)  # type: ignore[return-value]


@router.delete(
    "/documents/{document_id}", response_model=DocumentResponse
)
def delete_document(
    document_id: UUID,
    db: DbSession,
    current_user: Profile = Depends(require_admin),
) -> DocumentResponse:
    return service.remove_document(db, document_id, current_user)  # type: ignore[return-value]
