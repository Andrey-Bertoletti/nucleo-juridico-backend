"""Regras de negócio do módulo templates (modelos + geração)."""

import re
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.templates.models import GeneratedDocument, Template
from app.modules.templates.schemas import (
    GenerateDocumentRequest,
    TemplateCreate,
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
    for field, value in data.items():
        setattr(tpl, field, value)
    db.commit()
    db.refresh(tpl)
    return tpl


def delete_template(db: Session, template_id: UUID) -> None:
    """Soft delete: marca status='inativo'. Histórico de gerados é preservado."""
    tpl = get_template(db, template_id)
    tpl.status = "inativo"
    db.commit()


# ---------------------------------------------------------------------------
# Geração de documento
# ---------------------------------------------------------------------------
def _interpolate(content: str, data: dict[str, Any]) -> str:
    """Substitui `{{nome}}` por `data["nome"]`. Campos ausentes viram `____`
    (linha em branco) para facilitar o preenchimento manual posterior."""

    def _sub(match: re.Match[str]) -> str:
        key = match.group(1)
        value = data.get(key)
        if value is None or value == "":
            return "____________"
        return str(value)

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
