"""Rotas do módulo templates (modelos + geração de documentos)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.dependencies import CurrentUser, DbSession, require_admin
from app.modules.templates import service
from app.modules.templates.schemas import (
    GenerateDocumentRequest,
    GeneratedDocumentResponse,
    TemplateCreate,
    TemplateResponse,
    TemplateType,
    TemplateUpdate,
)
from app.modules.users.models import Profile


router = APIRouter(tags=["templates"])


# ---------------------------------------------------------------------------
# Templates — CRUD
# ---------------------------------------------------------------------------
@router.get("/templates", response_model=list[TemplateResponse])
def list_templates(
    db: DbSession,
    _current: CurrentUser,
    type: TemplateType | None = Query(default=None, description="Filtra por tipo."),
    only_active: bool = Query(default=False, description="Apenas ativos."),
) -> list[TemplateResponse]:
    return service.list_templates(db, template_type=type, only_active=only_active)  # type: ignore[return-value]


@router.get("/templates/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: UUID,
    db: DbSession,
    _current: CurrentUser,
) -> TemplateResponse:
    return service.get_template(db, template_id)  # type: ignore[return-value]


@router.post(
    "/templates",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_template(
    payload: TemplateCreate,
    db: DbSession,
    current_user: Profile = Depends(require_admin),
) -> TemplateResponse:
    return service.create_template(db, payload, current_user)  # type: ignore[return-value]


@router.patch("/templates/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: UUID,
    payload: TemplateUpdate,
    db: DbSession,
    _admin: Profile = Depends(require_admin),
) -> TemplateResponse:
    return service.update_template(db, template_id, payload)  # type: ignore[return-value]


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: UUID,
    db: DbSession,
    _admin: Profile = Depends(require_admin),
) -> Response:
    service.delete_template(db, template_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Geração de documento a partir de modelo
# ---------------------------------------------------------------------------
@router.post(
    "/templates/{template_id}/generate",
    response_model=GeneratedDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_from_template(
    template_id: UUID,
    payload: GenerateDocumentRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> GeneratedDocumentResponse:
    return service.generate_document(db, template_id, payload, current_user)  # type: ignore[return-value]


@router.get(
    "/generated-documents/{generated_id}",
    response_model=GeneratedDocumentResponse,
)
def get_generated(
    generated_id: UUID,
    db: DbSession,
    _current: CurrentUser,
) -> GeneratedDocumentResponse:
    return service.get_generated_document(db, generated_id)  # type: ignore[return-value]


@router.get(
    "/generated-documents",
    response_model=list[GeneratedDocumentResponse],
)
def list_generated(
    db: DbSession,
    _current: CurrentUser,
    template_id: UUID | None = Query(default=None),
    attendance_id: UUID | None = Query(default=None),
    client_id: UUID | None = Query(default=None),
) -> list[GeneratedDocumentResponse]:
    return service.list_generated_documents(  # type: ignore[return-value]
        db,
        template_id=template_id,
        attendance_id=attendance_id,
        client_id=client_id,
    )
