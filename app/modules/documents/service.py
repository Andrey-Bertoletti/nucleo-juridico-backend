"""Regras de negócio do módulo documents."""

import re
from datetime import datetime, timezone
from typing import Iterable
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.modules.attendances.models import Attendance, AttendanceHistory
from app.modules.documents.models import Document
from app.modules.documents.schemas import DocumentStatusUpdate
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

VALID_DOCUMENT_TYPES = {
    "rg",
    "cpf",
    "comprovante_residencia",
    "comprovante_renda",
    "certidao",
    "documento_caso",
    "outros",
}

SIGNED_URL_TTL_SECONDS = 3600  # 1 hora

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_filename(name: str) -> str:
    cleaned = _SAFE_NAME.sub("_", name).strip("_")
    return cleaned or "arquivo"


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------
def _signed_url(storage_path: str | None) -> str | None:
    """Gera signed URL temporária para download/visualização do arquivo.

    Retorna `None` se o `storage_path` for vazio ou se o Supabase recusar.
    """
    if not storage_path:
        return None
    try:
        sb = get_admin_client()
        bucket = sb.storage.from_(settings.SUPABASE_STORAGE_BUCKET)
        result = bucket.create_signed_url(storage_path, SIGNED_URL_TTL_SECONDS)
    except Exception:  # noqa: BLE001
        return None

    # supabase-py 2.x devolve um dict com chave `signedURL` ou variações.
    if isinstance(result, dict):
        return (
            result.get("signedURL")
            or result.get("signedUrl")
            or result.get("signed_url")
        )
    return None


def _attach_url(doc: Document) -> Document:
    """Injeta signed URL no campo `file_url` (em memória, não persiste)."""
    if doc.status == "removido":
        doc.file_url = None
    else:
        doc.file_url = _signed_url(doc.storage_path)
    return doc


def _attach_urls(docs: Iterable[Document]) -> list[Document]:
    return [_attach_url(d) for d in docs]


def _record_attendance_history(
    db: Session,
    *,
    attendance_id: UUID,
    user_id: UUID | None,
    event_type: str,
    description: str,
) -> None:
    db.add(
        AttendanceHistory(
            attendance_id=attendance_id,
            user_id=user_id,
            event_type=event_type,
            description=description,
        )
    )


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------
def get_document(db: Session, document_id: UUID) -> Document:
    doc = db.query(Document).filter(Document.id == document_id).one_or_none()
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento não encontrado.",
        )
    return _attach_url(doc)


def list_by_attendance(db: Session, attendance_id: UUID) -> list[Document]:
    a = (
        db.query(Attendance)
        .filter(Attendance.id == attendance_id)
        .one_or_none()
    )
    if a is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Atendimento não encontrado.",
        )
    docs = (
        db.query(Document)
        .filter(
            Document.attendance_id == attendance_id,
            Document.status != "removido",
        )
        .order_by(Document.created_at.desc())
        .all()
    )
    return _attach_urls(docs)


def list_by_client(db: Session, client_id: UUID) -> list[Document]:
    docs = (
        db.query(Document)
        .filter(
            Document.client_id == client_id,
            Document.status != "removido",
        )
        .order_by(Document.created_at.desc())
        .all()
    )
    return _attach_urls(docs)


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------
async def upload_to_attendance(
    db: Session,
    attendance_id: UUID,
    file: UploadFile,
    document_type: str,
    notes: str | None,
    current_user: Profile,
) -> Document:
    attendance = (
        db.query(Attendance)
        .filter(Attendance.id == attendance_id)
        .one_or_none()
    )
    if attendance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Atendimento não encontrado.",
        )

    if document_type not in VALID_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Tipo de documento inválido: {document_type}",
        )

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

    safe_name = _safe_filename(file.filename or "arquivo")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    storage_path = f"attendances/{attendance_id}/{timestamp}_{safe_name}"

    sb = get_admin_client()
    bucket_name = settings.SUPABASE_STORAGE_BUCKET
    bucket = sb.storage.from_(bucket_name)

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
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Falha no upload para o storage: {exc}",
        ) from exc

    doc = Document(
        client_id=attendance.client_id,
        attendance_id=attendance_id,
        document_type=document_type,
        file_name=file.filename or safe_name,
        file_url=None,  # bucket é privado — usamos signed URLs sob demanda
        storage_path=storage_path,
        status="entregue",
        notes=notes,
        uploaded_by=current_user.id,
    )
    db.add(doc)
    db.flush()

    _record_attendance_history(
        db,
        attendance_id=attendance_id,
        user_id=current_user.id,
        event_type="documento_adicionado",
        description=(
            f"Documento '{doc.file_name}' ({document_type}) anexado por "
            f"{current_user.name}."
        ),
    )

    db.commit()
    db.refresh(doc)
    return _attach_url(doc)


# ---------------------------------------------------------------------------
# Status + remoção
# ---------------------------------------------------------------------------
def change_status(
    db: Session,
    document_id: UUID,
    payload: DocumentStatusUpdate,
    current_user: Profile,
) -> Document:
    doc = db.query(Document).filter(Document.id == document_id).one_or_none()
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento não encontrado.",
        )
    if doc.status == payload.status:
        return _attach_url(doc)

    old_status = doc.status
    doc.status = payload.status

    if doc.attendance_id:
        event_type = (
            "documento_aprovado"
            if payload.status == "entregue"
            else "observacao"
        )
        _record_attendance_history(
            db,
            attendance_id=doc.attendance_id,
            user_id=current_user.id,
            event_type=event_type,
            description=(
                f"Status do documento '{doc.file_name}' alterado de "
                f"'{old_status}' para '{payload.status}' por {current_user.name}."
            ),
        )

    db.commit()
    db.refresh(doc)
    return _attach_url(doc)


def remove_document(
    db: Session, document_id: UUID, current_user: Profile
) -> Document:
    doc = db.query(Document).filter(Document.id == document_id).one_or_none()
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento não encontrado.",
        )
    if doc.status == "removido":
        return _attach_url(doc)

    try:
        sb = get_admin_client()
        sb.storage.from_(settings.SUPABASE_STORAGE_BUCKET).remove(
            [doc.storage_path]
        )
    except Exception:  # noqa: BLE001
        pass  # cleanup do storage é best-effort

    doc.status = "removido"

    if doc.attendance_id:
        _record_attendance_history(
            db,
            attendance_id=doc.attendance_id,
            user_id=current_user.id,
            event_type="observacao",
            description=(
                f"Documento '{doc.file_name}' removido por {current_user.name}."
            ),
        )

    db.commit()
    db.refresh(doc)
    return _attach_url(doc)
