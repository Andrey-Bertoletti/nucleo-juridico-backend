"""Rotas do módulo appointments."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.core.dependencies import (
    ROLE_ADMIN,
    ROLE_STUDENT,
    ROLE_TEACHER,
    CurrentUser,
    DbSession,
)
from app.modules.appointments import service
from app.modules.appointments.schemas import (
    AppointmentCreate,
    AppointmentListItem,
    AppointmentResponse,
    AppointmentStatusUpdate,
    AppointmentUpdate,
)


router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.get("", response_model=list[AppointmentListItem])
def list_appointments(
    db: DbSession,
    current_user: CurrentUser,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    responsible_id: UUID | None = Query(default=None),
    status_filter: str | None = Query(
        default=None,
        alias="status",
        pattern="^(agendado|confirmado|compareceu|nao_compareceu|remarcado|cancelado)$",
    ),
    client_id: UUID | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[AppointmentListItem]:
    rows = service.list_appointments(
        db,
        current_user,
        from_date=from_date,
        to_date=to_date,
        responsible_id=responsible_id,
        status_filter=status_filter,
        client_id=client_id,
        limit=limit,
        offset=offset,
    )
    return [AppointmentListItem(**r) for r in rows]


@router.post(
    "",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_appointment(
    payload: AppointmentCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> AppointmentResponse:
    if current_user.role not in {ROLE_STUDENT, ROLE_TEACHER, ROLE_ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para agendar retornos.",
        )
    return service.create_appointment(db, payload, current_user)  # type: ignore[return-value]


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> AppointmentResponse:
    return service.get_appointment(db, appointment_id, current_user)  # type: ignore[return-value]


@router.patch("/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(
    appointment_id: UUID,
    payload: AppointmentUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> AppointmentResponse:
    return service.update_appointment(
        db, appointment_id, payload, current_user
    )  # type: ignore[return-value]


@router.patch(
    "/{appointment_id}/status", response_model=AppointmentResponse
)
def change_appointment_status(
    appointment_id: UUID,
    payload: AppointmentStatusUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> AppointmentResponse:
    return service.change_status(
        db, appointment_id, payload, current_user
    )  # type: ignore[return-value]


@router.delete(
    "/{appointment_id}",
    status_code=status.HTTP_200_OK,
    responses={204: {"description": "Retorno avulso removido fisicamente."}},
)
def delete_appointment(
    appointment_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> Response:
    result = service.delete_appointment(db, appointment_id, current_user)
    if result is None:
        # hard delete
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    # soft delete — devolve o registro atualizado
    return Response(
        status_code=status.HTTP_200_OK,
        content=AppointmentResponse.model_validate(result).model_dump_json(),
        media_type="application/json",
    )
