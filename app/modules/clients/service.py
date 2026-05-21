"""Regras de negócio do módulo clients."""

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import Integer, String, bindparam, text
from sqlalchemy.orm import Session

from app.modules.clients.models import Client, ClientHistory
from app.modules.clients.schemas import ClientCreate, ClientUpdate
from app.modules.users.models import Profile


_CPF_RE = re.compile(r"\D")


def _normalize_cpf(value: str | None) -> str | None:
    if value is None:
        return None
    digits = _CPF_RE.sub("", value)
    return digits or None


def _validate_cpf_length(value: str | None) -> None:
    if value is not None and len(value) != 11:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="CPF deve conter 11 dígitos.",
        )


def _jsonify(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, UUID):
        return str(value)
    return value


def _record_history(
    db: Session,
    *,
    client_id: UUID,
    user_id: UUID | None,
    event_type: str,
    description: str | None = None,
    changes: dict[str, Any] | None = None,
) -> None:
    entry = ClientHistory(
        client_id=client_id,
        user_id=user_id,
        event_type=event_type,
        description=description,
        changes=changes,
    )
    db.add(entry)


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------
def list_clients(
    db: Session,
    *,
    search: str | None = None,
    cpf: str | None = None,
    phone: str | None = None,
    city: str | None = None,
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Lista clientes incluindo a data do último atendimento.

    Usa SQL bruto para um subselect de `attendances` sem acoplar este módulo
    ao modelo Attendance (ainda não implementado como feature).
    """
    cpf_norm = _normalize_cpf(cpf)

    sql = text(
        """
        select
            c.id,
            c.full_name,
            c.cpf,
            c.phone,
            c.city,
            c.status,
            c.created_at,
            (
              select max(a.created_at)
                from attendances a
               where a.client_id = c.id
            ) as last_attendance_at
          from clients c
         where (:search is null or c.full_name ilike :search_pat)
           and (:cpf is null or c.cpf = :cpf)
           and (:phone is null or c.phone ilike :phone_pat)
           and (:city is null or c.city ilike :city_pat)
           and (:status_filter is null or c.status = :status_filter)
         order by c.created_at desc
         limit :limit offset :offset
        """
    ).bindparams(
        # Tipar os parâmetros explicitamente é necessário para o psycopg v3 —
        # sem isso, parâmetros que chegam como NULL geram AmbiguousParameter.
        bindparam("search", type_=String),
        bindparam("search_pat", type_=String),
        bindparam("cpf", type_=String),
        bindparam("phone", type_=String),
        bindparam("phone_pat", type_=String),
        bindparam("city", type_=String),
        bindparam("city_pat", type_=String),
        bindparam("status_filter", type_=String),
        bindparam("limit", type_=Integer),
        bindparam("offset", type_=Integer),
    )

    rows = db.execute(
        sql,
        {
            "search": search,
            "search_pat": f"%{search}%" if search else None,
            "cpf": cpf_norm,
            "phone": phone,
            "phone_pat": f"%{phone}%" if phone else None,
            "city": city,
            "city_pat": f"%{city}%" if city else None,
            "status_filter": status_filter,
            "limit": limit,
            "offset": offset,
        },
    ).mappings().all()

    return [dict(row) for row in rows]


def get_client(db: Session, client_id: UUID) -> Client:
    client = db.query(Client).filter(Client.id == client_id).one_or_none()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado.",
        )
    return client


def _ensure_unique_cpf(
    db: Session, cpf_value: str, *, except_client_id: UUID | None = None
) -> None:
    query = db.query(Client).filter(Client.cpf == cpf_value)
    if except_client_id is not None:
        query = query.filter(Client.id != except_client_id)
    if query.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um cliente com este CPF.",
        )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def create_client(
    db: Session, payload: ClientCreate, current_user: Profile
) -> Client:
    data = payload.model_dump()
    data["cpf"] = _normalize_cpf(data.get("cpf"))
    _validate_cpf_length(data["cpf"])

    if data["cpf"] is not None:
        _ensure_unique_cpf(db, data["cpf"])

    if data.get("state"):
        data["state"] = data["state"].upper()

    client = Client(**data)
    db.add(client)
    db.flush()  # garante client.id antes do histórico

    history_changes = {
        field: _jsonify(value) for field, value in data.items() if value is not None
    }
    _record_history(
        db,
        client_id=client.id,
        user_id=current_user.id,
        event_type="criacao",
        description=f"Cliente cadastrado por {current_user.name}.",
        changes=history_changes,
    )

    db.commit()
    db.refresh(client)
    return client


def update_client(
    db: Session,
    client_id: UUID,
    payload: ClientUpdate,
    current_user: Profile,
) -> Client:
    client = get_client(db, client_id)
    data = payload.model_dump(exclude_unset=True)

    if "cpf" in data:
        data["cpf"] = _normalize_cpf(data["cpf"])
        _validate_cpf_length(data["cpf"])
        if data["cpf"] is not None:
            _ensure_unique_cpf(db, data["cpf"], except_client_id=client.id)

    if "state" in data and data["state"]:
        data["state"] = data["state"].upper()

    diff: dict[str, Any] = {}
    for field, new_value in data.items():
        old_value = getattr(client, field)
        if old_value != new_value:
            diff[field] = {
                "from": _jsonify(old_value),
                "to": _jsonify(new_value),
            }
            setattr(client, field, new_value)

    if not diff:
        return client  # sem alterações reais — não polui o histórico

    _record_history(
        db,
        client_id=client.id,
        user_id=current_user.id,
        event_type="atualizacao",
        description=f"Cliente atualizado por {current_user.name}.",
        changes=diff,
    )

    db.commit()
    db.refresh(client)
    return client


def deactivate_client(
    db: Session, client_id: UUID, current_user: Profile
) -> Client:
    """Soft delete: marca o cliente como inativo e registra histórico."""
    client = get_client(db, client_id)
    if client.status == "inativo":
        return client

    client.status = "inativo"
    _record_history(
        db,
        client_id=client.id,
        user_id=current_user.id,
        event_type="desativacao",
        description=f"Cliente desativado por {current_user.name}.",
        changes={"status": {"from": "ativo", "to": "inativo"}},
    )
    db.commit()
    db.refresh(client)
    return client


# ---------------------------------------------------------------------------
# Sub-recursos
# ---------------------------------------------------------------------------
def list_history(db: Session, client_id: UUID) -> list[ClientHistory]:
    get_client(db, client_id)  # 404 se não existir
    return (
        db.query(ClientHistory)
        .filter(ClientHistory.client_id == client_id)
        .order_by(ClientHistory.created_at.desc())
        .all()
    )


# list_documents foi removido — agora vive no módulo `documents`.
