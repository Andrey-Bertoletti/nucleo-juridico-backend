"""Regras de negócio do módulo ai.

Fluxo: valida documento -> verifica cache (source_hash) -> dispara job em
segundo plano (BackgroundTasks) que extrai o texto, chama o provedor e
persiste o resultado. O frontend faz polling até `status` virar pronto/erro.
"""

import hashlib
import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.modules.ai import extraction
from app.modules.ai.models import AiAnalysis
from app.modules.ai.providers import get_provider
from app.modules.documents.models import Document
from app.modules.users.models import Profile

logger = logging.getLogger("nucleo_juridico")

GENERAL_ACTION = "analise_geral"


# ---------------------------------------------------------------------------
# Hashes de invalidação de cache
# ---------------------------------------------------------------------------
def _doc_hash(doc: Document) -> str:
    raw = f"{doc.id}:{doc.updated_at.isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _client_docs_hash(docs: list[Document]) -> str:
    parts = sorted(f"{d.id}:{d.updated_at.isoformat()}" for d in docs)
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


# ---------------------------------------------------------------------------
# Queries auxiliares
# ---------------------------------------------------------------------------
def _get_active_document(db: Session, document_id: UUID) -> Document:
    doc = db.query(Document).filter(Document.id == document_id).one_or_none()
    if doc is None or doc.status == "removido":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento não encontrado.",
        )
    return doc


def _client_documents(db: Session, client_id: UUID) -> list[Document]:
    return (
        db.query(Document)
        .filter(Document.client_id == client_id, Document.status != "removido")
        .order_by(Document.created_at.asc())
        .all()
    )


# ---------------------------------------------------------------------------
# Disparo — documento
# ---------------------------------------------------------------------------
def trigger_document_action(
    db: Session,
    *,
    document_id: UUID,
    action: str,
    force: bool,
    user: Profile,
    background_tasks,
) -> AiAnalysis:
    doc = _get_active_document(db, document_id)
    src = _doc_hash(doc)

    existing = (
        db.query(AiAnalysis)
        .filter(
            AiAnalysis.scope == "document",
            AiAnalysis.document_id == document_id,
            AiAnalysis.action == action,
        )
        .one_or_none()
    )

    if (
        existing is not None
        and existing.status == "pronto"
        and existing.source_hash == src
        and not force
    ):
        return existing  # cache-hit: sem custo

    if existing is None:
        existing = AiAnalysis(
            scope="document",
            document_id=doc.id,
            client_id=doc.client_id,
            action=action,
        )
        db.add(existing)

    # Se o documento mudou (ou foi forçado), descarta o texto extraído antigo.
    if force or existing.source_hash != src:
        existing.extracted_text = None
    existing.status = "processando"
    existing.error_message = None
    existing.source_hash = src
    existing.created_by = user.id
    db.commit()
    db.refresh(existing)

    background_tasks.add_task(_run_document_job, existing.id)
    return existing


def _run_document_job(analysis_id: UUID) -> None:
    db = SessionLocal()
    try:
        analysis = (
            db.query(AiAnalysis).filter(AiAnalysis.id == analysis_id).one_or_none()
        )
        if analysis is None:
            return
        doc = (
            db.query(Document)
            .filter(Document.id == analysis.document_id)
            .one_or_none()
        )
        if doc is None:
            _mark_error(db, analysis, "Documento não encontrado.")
            return

        text = analysis.extracted_text or extraction.extract_document_text(doc)
        result = get_provider().run_action(action=analysis.action, document_text=text)

        analysis.extracted_text = text
        analysis.result_text = result.result_text
        analysis.result_data = result.result_data
        analysis.model_used = result.model_used
        analysis.tokens_input = result.tokens_input
        analysis.tokens_output = result.tokens_output
        analysis.status = "pronto"
        db.commit()
        _record_history(db, doc, analysis)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Falha no job de análise de documento %s.", analysis_id)
        db.rollback()
        analysis = (
            db.query(AiAnalysis).filter(AiAnalysis.id == analysis_id).one_or_none()
        )
        if analysis is not None:
            _mark_error(db, analysis, str(exc))
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Disparo — análise geral (cliente)
# ---------------------------------------------------------------------------
def trigger_general_report(
    db: Session,
    *,
    client_id: UUID,
    force: bool,
    user: Profile,
    background_tasks,
) -> AiAnalysis:
    docs = _client_documents(db, client_id)
    if not docs:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Este cliente não possui documentos para analisar.",
        )
    src = _client_docs_hash(docs)

    existing = (
        db.query(AiAnalysis)
        .filter(
            AiAnalysis.scope == "client",
            AiAnalysis.client_id == client_id,
            AiAnalysis.action == GENERAL_ACTION,
        )
        .one_or_none()
    )

    if (
        existing is not None
        and existing.status == "pronto"
        and existing.source_hash == src
        and not force
    ):
        return existing

    if existing is None:
        existing = AiAnalysis(
            scope="client",
            client_id=client_id,
            action=GENERAL_ACTION,
        )
        db.add(existing)

    existing.status = "processando"
    existing.error_message = None
    existing.source_hash = src
    existing.created_by = user.id
    db.commit()
    db.refresh(existing)

    background_tasks.add_task(_run_general_job, existing.id, client_id)
    return existing


def _run_general_job(analysis_id: UUID, client_id: UUID) -> None:
    db = SessionLocal()
    try:
        analysis = (
            db.query(AiAnalysis).filter(AiAnalysis.id == analysis_id).one_or_none()
        )
        if analysis is None:
            return
        docs = _client_documents(db, client_id)
        payload = []
        for doc in docs:
            try:
                text = extraction.extract_document_text(doc)
            except Exception as exc:  # noqa: BLE001
                text = f"[Falha ao extrair: {exc}]"
            payload.append(
                {
                    "document_id": str(doc.id),
                    "file_name": doc.file_name,
                    "document_type": doc.document_type,
                    "text": text,
                }
            )

        result = get_provider().run_action(
            action=GENERAL_ACTION, document_text="", documents=payload
        )
        analysis.result_text = result.result_text
        analysis.result_data = result.result_data
        analysis.model_used = result.model_used
        analysis.tokens_input = result.tokens_input
        analysis.tokens_output = result.tokens_output
        analysis.status = "pronto"
        db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Falha no job de análise geral %s.", analysis_id)
        db.rollback()
        analysis = (
            db.query(AiAnalysis).filter(AiAnalysis.id == analysis_id).one_or_none()
        )
        if analysis is not None:
            _mark_error(db, analysis, str(exc))
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Leituras (cache / polling)
# ---------------------------------------------------------------------------
def get_document_action(db: Session, document_id: UUID, action: str) -> AiAnalysis:
    row = (
        db.query(AiAnalysis)
        .filter(
            AiAnalysis.scope == "document",
            AiAnalysis.document_id == document_id,
            AiAnalysis.action == action,
        )
        .one_or_none()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma análise dessa ação para este documento.",
        )
    return row


def list_document_analyses(db: Session, document_id: UUID) -> list[AiAnalysis]:
    return (
        db.query(AiAnalysis)
        .filter(
            AiAnalysis.scope == "document",
            AiAnalysis.document_id == document_id,
        )
        .order_by(AiAnalysis.updated_at.desc())
        .all()
    )


def get_general_report(db: Session, client_id: UUID) -> AiAnalysis:
    row = (
        db.query(AiAnalysis)
        .filter(
            AiAnalysis.scope == "client",
            AiAnalysis.client_id == client_id,
            AiAnalysis.action == GENERAL_ACTION,
        )
        .one_or_none()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma análise geral para este cliente.",
        )
    return row


def get_analysis(db: Session, analysis_id: UUID) -> AiAnalysis:
    row = db.query(AiAnalysis).filter(AiAnalysis.id == analysis_id).one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Análise não encontrada.",
        )
    return row


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------
def _mark_error(db: Session, analysis: AiAnalysis, message: str) -> None:
    analysis.status = "erro"
    analysis.error_message = (message or "Erro desconhecido.")[:500]
    db.commit()


def _record_history(db: Session, doc: Document, analysis: AiAnalysis) -> None:
    """Registra evento no histórico do atendimento (best-effort)."""
    if not doc.attendance_id:
        return
    try:
        from app.modules.ai.prompts import ACTION_LABELS
        from app.modules.attendances.models import AttendanceHistory

        db.add(
            AttendanceHistory(
                attendance_id=doc.attendance_id,
                user_id=analysis.created_by,
                event_type="observacao",
                description=(
                    f"Análise de IA ({ACTION_LABELS.get(analysis.action, analysis.action)}) "
                    f"gerada para o documento '{doc.file_name}'."
                ),
            )
        )
        db.commit()
    except Exception:  # noqa: BLE001 — histórico é best-effort
        db.rollback()
