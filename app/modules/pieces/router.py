"""Rotas do módulo pieces."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.core.dependencies import (
    ROLE_ADMIN,
    ROLE_STUDENT,
    CurrentUser,
    DbSession,
    require_admin,
    require_teacher,
)
from app.modules.pieces import service
from app.modules.pieces.schemas import (
    PieceCorrection,
    PieceDownloadResponse,
    PieceListItem,
    PieceResponse,
    PieceStats,
    PieceStudentSummary,
    PieceUpdate,
)
from app.modules.users.models import Profile


router = APIRouter(prefix="/pieces", tags=["pieces"])


# ---------------------------------------------------------------------------
# Helpers de permissão
# ---------------------------------------------------------------------------
def require_piece_creator(current_user: CurrentUser) -> Profile:
    """Apenas alunos e admin podem criar peças."""
    if current_user.role not in {ROLE_STUDENT, ROLE_ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas alunos/estagiários e coordenação podem entregar peças.",
        )
    return current_user


PieceCreator = Annotated[Profile, Depends(require_piece_creator)]


# ---------------------------------------------------------------------------
# Rotas estáticas (antes de /{piece_id} para evitar conflito)
# ---------------------------------------------------------------------------
@router.get("/summary/by-student", response_model=list[PieceStudentSummary])
def get_piece_summary(
    db: DbSession,
    current_user: Profile = Depends(require_teacher),
) -> list[PieceStudentSummary]:
    rows = service.get_summary_by_student(db)
    return [PieceStudentSummary(**r) for r in rows]


@router.get("/stats", response_model=PieceStats)
def get_piece_stats(
    db: DbSession,
    current_user: CurrentUser,
) -> PieceStats:
    data = service.get_stats(db, current_user)
    return PieceStats(**data)


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------
@router.get("", response_model=list[PieceListItem])
def list_pieces(
    db: DbSession,
    current_user: CurrentUser,
    status_filter: str | None = Query(default=None, alias="status"),
    student_id: UUID | None = Query(default=None),
    search: str | None = Query(default=None, description="Busca por título da peça."),
    date_from: str | None = Query(default=None, alias="from"),
    date_to: str | None = Query(default=None, alias="to"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[PieceListItem]:
    rows = service.list_pieces(
        db,
        current_user,
        status_filter=status_filter,
        student_id=student_id,
        search=search,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return [PieceListItem(**r) for r in rows]


@router.post(
    "",
    response_model=PieceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_piece(
    db: DbSession,
    current_user: PieceCreator,
    title: str = Form(..., max_length=300, description="Título da peça."),
    file: UploadFile = File(..., description="Arquivo da peça processual."),
    description: str | None = Form(default=None, max_length=4000),
    attendance_id: UUID | None = Form(default=None, description="Vinculação opcional a um atendimento."),
    student_notes: str | None = Form(default=None, max_length=4000),
) -> PieceResponse:
    data = await service.create_piece(
        db,
        file,
        title,
        current_user,
        description=description,
        attendance_id=attendance_id,
        student_notes=student_notes,
    )
    return PieceResponse(**data)


@router.get("/{piece_id}", response_model=PieceResponse)
def get_piece(
    piece_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> PieceResponse:
    data = service.get_piece(db, piece_id, current_user)
    return PieceResponse(**data)


@router.patch("/{piece_id}", response_model=PieceResponse)
def update_piece(
    piece_id: UUID,
    payload: PieceUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> PieceResponse:
    data = service.update_piece(db, piece_id, payload, current_user)
    return PieceResponse(**data)


@router.get("/{piece_id}/download", response_model=PieceDownloadResponse)
def download_piece(
    piece_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> PieceDownloadResponse:
    data = service.download_piece(db, piece_id, current_user)
    return PieceDownloadResponse(**data)


@router.patch("/{piece_id}/correct", response_model=PieceResponse)
def correct_piece(
    piece_id: UUID,
    payload: PieceCorrection,
    db: DbSession,
    current_user: Profile = Depends(require_teacher),
) -> PieceResponse:
    data = service.correct_piece(db, piece_id, payload, current_user)
    return PieceResponse(**data)


@router.delete("/{piece_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_piece(
    piece_id: UUID,
    db: DbSession,
    current_user: Profile = Depends(require_admin),
) -> None:
    service.delete_piece(db, piece_id, current_user)
