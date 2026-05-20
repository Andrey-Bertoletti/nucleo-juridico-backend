"""Rotas do módulo clients."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.core.dependencies import (
    ROLE_ADMIN,
    ROLE_STUDENT,
    CurrentUser,
    DbSession,
    require_admin,
)
from app.modules.clients import service
from app.modules.clients.schemas import (
    ClientCreate,
    ClientDocumentItem,
    ClientHistoryItem,
    ClientListItem,
    ClientResponse,
    ClientUpdate,
)
from app.modules.users.models import Profile


router = APIRouter(prefix="/clients", tags=["clients"])


# Aluno e admin podem criar/editar; professor é somente-leitura.
def require_client_writer(current_user: CurrentUser) -> Profile:
    if current_user.role not in {ROLE_STUDENT, ROLE_ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Acesso negado: apenas alunos/estagiários e coordenação podem "
                "cadastrar ou editar clientes."
            ),
        )
    return current_user


ClientWriter = Annotated[Profile, Depends(require_client_writer)]


@router.get("", response_model=list[ClientListItem])
def list_clients(
    db: DbSession,
    _current: CurrentUser,
    search: str | None = Query(default=None, description="Busca por nome (ilike)."),
    cpf: str | None = Query(default=None, description="CPF com ou sem máscara."),
    phone: str | None = Query(default=None, description="Busca parcial por telefone."),
    city: str | None = Query(default=None, description="Busca parcial por cidade."),
    status_filter: str | None = Query(
        default=None,
        alias="status",
        pattern="^(ativo|inativo)$",
        description="Filtrar por status.",
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[ClientListItem]:
    rows = service.list_clients(
        db,
        search=search,
        cpf=cpf,
        phone=phone,
        city=city,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )
    return [ClientListItem(**row) for row in rows]


@router.post(
    "",
    response_model=ClientResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_client(
    payload: ClientCreate,
    db: DbSession,
    current_user: ClientWriter,
) -> ClientResponse:
    return service.create_client(db, payload, current_user)  # type: ignore[return-value]


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(
    client_id: UUID,
    db: DbSession,
    _current: CurrentUser,
) -> ClientResponse:
    return service.get_client(db, client_id)  # type: ignore[return-value]


@router.patch("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: UUID,
    payload: ClientUpdate,
    db: DbSession,
    current_user: ClientWriter,
) -> ClientResponse:
    return service.update_client(db, client_id, payload, current_user)  # type: ignore[return-value]


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: UUID,
    db: DbSession,
    current_user: Profile = Depends(require_admin),
) -> Response:
    """Soft-delete: marca o cliente como `inativo`."""
    service.deactivate_client(db, client_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{client_id}/history", response_model=list[ClientHistoryItem])
def get_client_history(
    client_id: UUID,
    db: DbSession,
    _current: CurrentUser,
) -> list[ClientHistoryItem]:
    return service.list_history(db, client_id)  # type: ignore[return-value]


@router.get("/{client_id}/documents", response_model=list[ClientDocumentItem])
def get_client_documents(
    client_id: UUID,
    db: DbSession,
    _current: CurrentUser,
) -> list[ClientDocumentItem]:
    return service.list_documents(db, client_id)  # type: ignore[return-value]
