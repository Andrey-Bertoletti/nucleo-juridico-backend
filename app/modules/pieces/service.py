"""Regras de negócio do módulo pieces."""

import re
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import case, func as sa_func
from sqlalchemy.orm import Session

from app.core.dependencies import ROLE_ADMIN, ROLE_STUDENT, ROLE_TEACHER
from app.core.settings import settings
from app.modules.pieces.models import Piece
from app.modules.pieces.schemas import PieceCorrection, PieceUpdate
from app.modules.users.models import Profile
from app.services.supabase_client import get_admin_client


MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

SIGNED_URL_TTL_SECONDS = 3600  # 1 hora

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")

# Status em que o aluno pode editar a peça
EDITABLE_STATUSES = {"entregue", "devolvida_para_ajuste"}


def _safe_filename(name: str) -> str:
    cleaned = _SAFE_NAME.sub("_", name).strip("_")
    return cleaned or "arquivo"


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------
def _signed_url(storage_path: str | None) -> str | None:
    """Gera signed URL temporária para download/visualização do arquivo."""
    if not storage_path:
        return None
    try:
        sb = get_admin_client()
        bucket = sb.storage.from_(settings.SUPABASE_STORAGE_BUCKET)
        result = bucket.create_signed_url(storage_path, SIGNED_URL_TTL_SECONDS)
    except Exception:  # noqa: BLE001
        return None

    if isinstance(result, dict):
        return (
            result.get("signedURL")
            or result.get("signedUrl")
            or result.get("signed_url")
        )
    return None


def _enrich_piece(piece: Piece, db: Session) -> dict:
    """Enriquece o modelo com nomes denormalizados e signed URL."""
    data = {
        "id": piece.id,
        "student_id": piece.student_id,
        "student_name": None,
        "attendance_id": piece.attendance_id,
        "title": piece.title,
        "description": piece.description,
        "file_name": piece.file_name,
        "file_url": _signed_url(piece.storage_path),
        "storage_path": piece.storage_path,
        "status": piece.status,
        "corrected_by": piece.corrected_by,
        "corrected_by_name": None,
        "correction_notes": piece.correction_notes,
        "student_notes": piece.student_notes,
        "delivered_at": piece.delivered_at,
        "corrected_at": piece.corrected_at,
        "created_at": piece.created_at,
        "updated_at": piece.updated_at,
    }

    if piece.student_id:
        student = db.query(Profile).filter(Profile.id == piece.student_id).one_or_none()
        if student:
            data["student_name"] = student.name

    if piece.corrected_by:
        teacher = db.query(Profile).filter(Profile.id == piece.corrected_by).one_or_none()
        if teacher:
            data["corrected_by_name"] = teacher.name

    return data


# ---------------------------------------------------------------------------
# Verificação de acesso
# ---------------------------------------------------------------------------
def _check_piece_access(piece: Piece, current_user: Profile) -> None:
    """Verifica se o usuário pode ver a peça."""
    if current_user.role in {ROLE_ADMIN, ROLE_TEACHER}:
        return
    if current_user.role == ROLE_STUDENT and piece.student_id == current_user.id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Acesso negado a esta peça.",
    )


# ---------------------------------------------------------------------------
# Listagem
# ---------------------------------------------------------------------------
def list_pieces(
    db: Session,
    current_user: Profile,
    *,
    status_filter: str | None = None,
    student_id: UUID | None = None,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Lista peças com escopo automático por role."""
    query = db.query(Piece)

    # Escopo por role
    if current_user.role == ROLE_STUDENT:
        query = query.filter(Piece.student_id == current_user.id)
    elif student_id:
        query = query.filter(Piece.student_id == student_id)

    # Filtros
    if status_filter:
        query = query.filter(Piece.status == status_filter)
    if search:
        query = query.filter(Piece.title.ilike(f"%{search}%"))
    if date_from:
        query = query.filter(Piece.delivered_at >= date_from)
    if date_to:
        query = query.filter(Piece.delivered_at <= date_to)

    pieces = (
        query.order_by(Piece.delivered_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    result = []
    # Pré-carrega os nomes de alunos e professores para eficiência
    student_ids = {p.student_id for p in pieces if p.student_id}
    corrector_ids = {p.corrected_by for p in pieces if p.corrected_by}
    all_user_ids = student_ids | corrector_ids

    names: dict[UUID, str] = {}
    if all_user_ids:
        profiles = db.query(Profile.id, Profile.name).filter(
            Profile.id.in_(all_user_ids)
        ).all()
        names = {p.id: p.name for p in profiles}

    for piece in pieces:
        result.append({
            "id": piece.id,
            "student_id": piece.student_id,
            "student_name": names.get(piece.student_id) if piece.student_id else None,
            "attendance_id": piece.attendance_id,
            "title": piece.title,
            "file_name": piece.file_name,
            "status": piece.status,
            "delivered_at": piece.delivered_at,
            "corrected_at": piece.corrected_at,
            "corrected_by_name": names.get(piece.corrected_by) if piece.corrected_by else None,
        })

    return result


# ---------------------------------------------------------------------------
# Detalhe
# ---------------------------------------------------------------------------
def get_piece(db: Session, piece_id: UUID, current_user: Profile) -> dict:
    piece = db.query(Piece).filter(Piece.id == piece_id).one_or_none()
    if piece is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Peça não encontrada.",
        )
    _check_piece_access(piece, current_user)
    return _enrich_piece(piece, db)


# ---------------------------------------------------------------------------
# Criação (com upload)
# ---------------------------------------------------------------------------
async def create_piece(
    db: Session,
    file: UploadFile,
    title: str,
    current_user: Profile,
    *,
    description: str | None = None,
    attendance_id: UUID | None = None,
    student_notes: str | None = None,
) -> dict:
    """Cria peça com upload obrigatório em uma única operação."""
    # Validação de MIME
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Tipo de arquivo não suportado: {file.content_type}. "
                "Aceitamos PDF, imagens (JPG/PNG/WebP) e Word."
            ),
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Arquivo vazio.",
        )
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Arquivo maior que {MAX_FILE_SIZE // (1024 * 1024)} MB.",
        )

    # Criar a peça no banco primeiro para ter o ID
    piece = Piece(
        student_id=current_user.id,
        attendance_id=attendance_id,
        title=title.strip(),
        description=description.strip() if description else None,
        file_name=file.filename or "arquivo",
        storage_path="",  # será atualizado após upload
        status="entregue",
        student_notes=student_notes.strip() if student_notes else None,
    )
    db.add(piece)
    db.flush()  # obtém o ID gerado

    # Upload para o storage
    safe_name = _safe_filename(file.filename or "arquivo")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    storage_path = f"pieces/{piece.id}/{timestamp}_{safe_name}"

    sb = get_admin_client()
    bucket = sb.storage.from_(settings.SUPABASE_STORAGE_BUCKET)

    try:
        bucket.upload(
            path=storage_path,
            file=content,
            file_options={
                "content-type": file.content_type or "application/octet-stream",
                "upsert": "false",
            },
        )
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Falha no upload para o storage: {exc}",
        ) from exc

    piece.storage_path = storage_path
    db.commit()
    db.refresh(piece)
    return _enrich_piece(piece, db)


# ---------------------------------------------------------------------------
# Atualização (aluno)
# ---------------------------------------------------------------------------
def update_piece(
    db: Session,
    piece_id: UUID,
    payload: PieceUpdate,
    current_user: Profile,
) -> dict:
    piece = db.query(Piece).filter(Piece.id == piece_id).one_or_none()
    if piece is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Peça não encontrada.",
        )

    # Apenas o aluno dono ou admin pode editar
    if current_user.role == ROLE_STUDENT:
        if piece.student_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas o autor da peça pode editá-la.",
            )
        if piece.status not in EDITABLE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Peça com status '{piece.status}' não pode ser editada. "
                    "Apenas peças 'entregue' ou 'devolvida para ajuste' podem ser editadas."
                ),
            )
    elif current_user.role != ROLE_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado.",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(piece, key, value)

    db.commit()
    db.refresh(piece)
    return _enrich_piece(piece, db)


# ---------------------------------------------------------------------------
# Correção (professor)
# ---------------------------------------------------------------------------
def correct_piece(
    db: Session,
    piece_id: UUID,
    payload: PieceCorrection,
    current_user: Profile,
) -> dict:
    piece = db.query(Piece).filter(Piece.id == piece_id).one_or_none()
    if piece is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Peça não encontrada.",
        )

    if current_user.role not in {ROLE_TEACHER, ROLE_ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas professores e coordenação podem corrigir peças.",
        )

    piece.status = payload.status
    if payload.correction_notes is not None:
        piece.correction_notes = payload.correction_notes
    piece.corrected_by = current_user.id

    if payload.status == "corrigida":
        piece.corrected_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(piece)
    return _enrich_piece(piece, db)


# ---------------------------------------------------------------------------
# Download (signed URL)
# ---------------------------------------------------------------------------
def download_piece(
    db: Session,
    piece_id: UUID,
    current_user: Profile,
) -> dict:
    piece = db.query(Piece).filter(Piece.id == piece_id).one_or_none()
    if piece is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Peça não encontrada.",
        )
    _check_piece_access(piece, current_user)

    url = _signed_url(piece.storage_path)
    if url is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível gerar o link de download.",
        )
    return {"file_name": piece.file_name, "signed_url": url}


# ---------------------------------------------------------------------------
# Remoção (admin)
# ---------------------------------------------------------------------------
def delete_piece(
    db: Session,
    piece_id: UUID,
    current_user: Profile,
) -> None:
    piece = db.query(Piece).filter(Piece.id == piece_id).one_or_none()
    if piece is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Peça não encontrada.",
        )

    # Tenta remover do storage (best-effort)
    try:
        sb = get_admin_client()
        sb.storage.from_(settings.SUPABASE_STORAGE_BUCKET).remove(
            [piece.storage_path]
        )
    except Exception:  # noqa: BLE001
        pass

    db.delete(piece)
    db.commit()


# ---------------------------------------------------------------------------
# Resumo por aluno (professor/admin)
# ---------------------------------------------------------------------------
def get_summary_by_student(db: Session) -> list[dict]:
    """Retorna contadores de peças agrupados por aluno."""
    rows = (
        db.query(
            Piece.student_id,
            Profile.name.label("student_name"),
            sa_func.count(Piece.id).label("total"),
            sa_func.count(
                case((Piece.status == "entregue", 1))
            ).label("entregue"),
            sa_func.count(
                case((Piece.status == "em_correcao", 1))
            ).label("em_correcao"),
            sa_func.count(
                case((Piece.status == "corrigida", 1))
            ).label("corrigida"),
            sa_func.count(
                case((Piece.status == "devolvida_para_ajuste", 1))
            ).label("devolvida_para_ajuste"),
        )
        .join(Profile, Piece.student_id == Profile.id)
        .group_by(Piece.student_id, Profile.name)
        .order_by(Profile.name)
        .all()
    )

    return [
        {
            "student_id": r.student_id,
            "student_name": r.student_name,
            "total": r.total,
            "entregue": r.entregue,
            "em_correcao": r.em_correcao,
            "corrigida": r.corrigida,
            "devolvida_para_ajuste": r.devolvida_para_ajuste,
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Estatísticas
# ---------------------------------------------------------------------------
def get_stats(db: Session, current_user: Profile) -> dict:
    """Retorna estatísticas gerais de peças."""
    query = db.query(
        sa_func.count(Piece.id).label("total"),
        sa_func.count(
            case((Piece.status == "entregue", 1))
        ).label("entregue"),
        sa_func.count(
            case((Piece.status == "em_correcao", 1))
        ).label("em_correcao"),
        sa_func.count(
            case((Piece.status == "corrigida", 1))
        ).label("corrigida"),
        sa_func.count(
            case((Piece.status == "devolvida_para_ajuste", 1))
        ).label("devolvida_para_ajuste"),
    )

    # Aluno vê apenas suas próprias estatísticas
    if current_user.role == ROLE_STUDENT:
        query = query.filter(Piece.student_id == current_user.id)

    r = query.one()
    return {
        "total": r.total,
        "entregue": r.entregue,
        "em_correcao": r.em_correcao,
        "corrigida": r.corrigida,
        "devolvida_para_ajuste": r.devolvida_para_ajuste,
    }
