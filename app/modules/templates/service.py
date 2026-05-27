"""Regras de negócio do módulo templates (modelos + geração)."""

import html
import re
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.templates.models import GeneratedDocument, Template
from app.modules.templates.schemas import (
    GenerateDocumentRequest,
    TemplateCreate,
    TemplateStatusUpdate,
    TemplateUpdate,
)
from app.modules.users.models import Profile


_PLACEHOLDER = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


# ---------------------------------------------------------------------------
# Templates CRUD
# ---------------------------------------------------------------------------
def list_templates(
    db: Session,
    template_type: str | None = None,
    only_active: bool = False,
) -> list[Template]:
    q = db.query(Template)
    if template_type:
        q = q.filter(Template.type == template_type)
    if only_active:
        q = q.filter(Template.status == "ativo")
    return q.order_by(Template.created_at.desc()).all()


def get_template(db: Session, template_id: UUID) -> Template:
    tpl = db.query(Template).filter(Template.id == template_id).one_or_none()
    if tpl is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Modelo não encontrado.",
        )
    return tpl


def create_template(
    db: Session, payload: TemplateCreate, current_user: Profile
) -> Template:
    tpl = Template(
        title=payload.title.strip(),
        description=payload.description.strip() if payload.description else None,
        type=payload.type,
        content=payload.content,
        dynamic_fields=[f.model_dump() for f in payload.dynamic_fields],
        status=payload.status,
        created_by=current_user.user_id,
    )
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return tpl


def update_template(
    db: Session, template_id: UUID, payload: TemplateUpdate
) -> Template:
    tpl = get_template(db, template_id)
    data = payload.model_dump(exclude_unset=True)
    if "dynamic_fields" in data and data["dynamic_fields"] is not None:
        data["dynamic_fields"] = [
            f if isinstance(f, dict) else f.model_dump()
            for f in payload.dynamic_fields or []
        ]
    if "title" in data and data["title"] is not None:
        data["title"] = data["title"].strip()
    if "description" in data and data["description"] is not None:
        data["description"] = data["description"].strip() or None
    for field, value in data.items():
        setattr(tpl, field, value)
    db.commit()
    db.refresh(tpl)
    return tpl


def change_template_status(
    db: Session, template_id: UUID, payload: TemplateStatusUpdate
) -> Template:
    """Ativa ou inativa o modelo (mudança reversível)."""
    tpl = get_template(db, template_id)
    tpl.status = payload.status
    db.commit()
    db.refresh(tpl)
    return tpl


def delete_template(db: Session, template_id: UUID) -> None:
    """Soft delete: marca status='inativo'. Histórico de gerados é preservado."""
    tpl = get_template(db, template_id)
    tpl.status = "inativo"
    db.commit()


def delete_template_permanently(db: Session, template_id: UUID) -> None:
    """Exclui permanentemente o modelo do banco.

    Bloqueado se houver `generated_documents` apontando para ele — preservar
    auditoria é mais importante que economizar registros. Se a coordenação
    quiser remover de qualquer jeito, precisa primeiro apagar os documentos
    gerados (não exposto via API por enquanto).
    """
    tpl = get_template(db, template_id)
    in_use = (
        db.query(GeneratedDocument)
        .filter(GeneratedDocument.template_id == tpl.id)
        .first()
    )
    if in_use is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Este modelo já gerou documentos e não pode ser excluído "
                "permanentemente. Inative-o para evitar novos usos."
            ),
        )
    db.delete(tpl)
    db.commit()


# ---------------------------------------------------------------------------
# Geração de documento
# ---------------------------------------------------------------------------
def _interpolate(content: str, data: dict[str, Any]) -> str:
    """Substitui `{{nome}}` por `data["nome"]` dentro do HTML do conteúdo.

    Valores são HTML-escapados para impedir que algum input do usuário
    quebre o markup (ou injete tags). Campos vazios viram uma linha de
    underscores — útil para preenchimento manual posterior no papel.
    Quebras de linha (`\\n`) no valor viram `<br>` para preservar a
    formatação visual do que o aluno digitou.
    """

    def _sub(match: re.Match[str]) -> str:
        key = match.group(1)
        value = data.get(key)
        if value is None or value == "":
            return "____________"
        escaped = html.escape(str(value), quote=False)
        return escaped.replace("\n", "<br>")

    return _PLACEHOLDER.sub(_sub, content)


def _validate_required_fields(
    template: Template, data: dict[str, Any]
) -> None:
    missing: list[str] = []
    for field_def in template.dynamic_fields or []:
        if field_def.get("required") and not data.get(field_def["name"]):
            missing.append(field_def.get("label") or field_def["name"])
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Campos obrigatórios não preenchidos: {', '.join(missing)}.",
        )


def generate_document(
    db: Session,
    template_id: UUID,
    payload: GenerateDocumentRequest,
    current_user: Profile,
) -> GeneratedDocument:
    tpl = get_template(db, template_id)
    if tpl.status != "ativo":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este modelo está inativo e não pode ser usado.",
        )
    _validate_required_fields(tpl, payload.filled_data)

    final_content = _interpolate(tpl.content, payload.filled_data)

    generated = GeneratedDocument(
        template_id=tpl.id,
        template_type=tpl.type,
        template_title=tpl.title,
        generated_by_user_id=current_user.user_id,
        student_name=payload.student_name,
        student_matricula=payload.student_matricula,
        attendance_date=payload.attendance_date,
        filled_data=payload.filled_data,
        final_content=final_content,
        attendance_id=payload.attendance_id,
        client_id=payload.client_id,
    )
    db.add(generated)
    db.commit()
    db.refresh(generated)
    return generated


def get_generated_document(
    db: Session, generated_id: UUID
) -> GeneratedDocument:
    doc = (
        db.query(GeneratedDocument)
        .filter(GeneratedDocument.id == generated_id)
        .one_or_none()
    )
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento gerado não encontrado.",
        )
    return doc


def list_generated_documents(
    db: Session,
    template_id: UUID | None = None,
    attendance_id: UUID | None = None,
    client_id: UUID | None = None,
) -> list[GeneratedDocument]:
    q = db.query(GeneratedDocument)
    if template_id:
        q = q.filter(GeneratedDocument.template_id == template_id)
    if attendance_id:
        q = q.filter(GeneratedDocument.attendance_id == attendance_id)
    if client_id:
        q = q.filter(GeneratedDocument.client_id == client_id)
    return q.order_by(GeneratedDocument.generated_at.desc()).all()
