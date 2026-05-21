"""Regras de negócio do módulo reports."""

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import Date, String, Uuid, bindparam, text
from sqlalchemy.orm import Session

from app.core.dependencies import ROLE_ADMIN, ROLE_STUDENT, ROLE_TEACHER
from app.modules.users.models import Profile


ATTENDANCE_STATUS_LABELS: dict[str, str] = {
    "novo_atendimento": "Novo atendimento",
    "em_triagem": "Em triagem",
    "aguardando_documentos": "Aguardando documentos",
    "encaminhado_ao_professor": "Encaminhado ao professor",
    "em_analise_pelo_professor": "Em análise pelo professor",
    "correcao_solicitada": "Correção solicitada",
    "aguardando_retorno_cliente": "Aguardando retorno do cliente",
    "encaminhamento_aprovado": "Encaminhamento aprovado",
    "finalizado": "Finalizado",
    "arquivado": "Arquivado",
}

ALL_STATUSES = list(ATTENDANCE_STATUS_LABELS.keys())
FINAL_STATUSES = {"finalizado", "arquivado"}
ANALYSIS_STATUSES = {
    "encaminhado_ao_professor",
    "em_analise_pelo_professor",
    "correcao_solicitada",
}


# ---------------------------------------------------------------------------
# Escopo por perfil
# ---------------------------------------------------------------------------
def _scope_clause(
    user: Profile,
    *,
    student_id: UUID | None = None,
    teacher_id: UUID | None = None,
) -> tuple[str, dict[str, Any]]:
    """Devolve o trecho SQL + params para escopar a query por perfil.

    Filtros explícitos (student_id, teacher_id) só são aplicados para o admin.
    """
    if user.role == ROLE_STUDENT:
        return "a.student_id = :scope_user_id", {"scope_user_id": user.id}
    if user.role == ROLE_TEACHER:
        return "a.teacher_id = :scope_user_id", {"scope_user_id": user.id}
    if user.role == ROLE_ADMIN:
        clauses: list[str] = []
        params: dict[str, Any] = {}
        if student_id is not None:
            clauses.append("a.student_id = :scope_student_id")
            params["scope_student_id"] = student_id
        if teacher_id is not None:
            clauses.append("a.teacher_id = :scope_teacher_id")
            params["scope_teacher_id"] = teacher_id
        return (" and ".join(clauses) if clauses else "true"), params
    return "false", {}


def _common_filters(
    period_from: date | None,
    period_to: date | None,
    legal_area_id: UUID | None,
    status_filter: str | None,
) -> tuple[str, dict[str, Any]]:
    parts: list[str] = []
    params: dict[str, Any] = {}
    if period_from is not None:
        parts.append("a.created_at >= :period_from")
        params["period_from"] = period_from
    if period_to is not None:
        parts.append("a.created_at <= :period_to")
        params["period_to"] = period_to
    if legal_area_id is not None:
        parts.append("a.legal_area_id = :legal_area_id")
        params["legal_area_id"] = legal_area_id
    if status_filter is not None:
        parts.append("a.status = :status_filter")
        params["status_filter"] = status_filter
    return (" and ".join(parts) if parts else "true"), params


# ---------------------------------------------------------------------------
# Dashboard / summary
# ---------------------------------------------------------------------------
def get_summary(
    db: Session,
    user: Profile,
    *,
    period_from: date | None = None,
    period_to: date | None = None,
    legal_area_id: UUID | None = None,
    student_id: UUID | None = None,
    teacher_id: UUID | None = None,
) -> dict[str, Any]:
    scope_sql, scope_params = _scope_clause(
        user, student_id=student_id, teacher_id=teacher_id
    )
    filters_sql, filters_params = _common_filters(
        period_from, period_to, legal_area_id, None
    )

    sql = text(
        f"""
        select a.status, count(*)::int as count
          from attendances a
         where {scope_sql} and {filters_sql}
         group by a.status
        """
    ).bindparams(
        bindparam("period_from", type_=Date),
        bindparam("period_to", type_=Date),
        bindparam("legal_area_id", type_=Uuid),
    )
    rows = db.execute(
        sql,
        {**scope_params, **filters_params, **_null_defaults(filters_params)},
    ).mappings().all()

    counters = {s: 0 for s in ALL_STATUSES}
    for r in rows:
        if r["status"] in counters:
            counters[r["status"]] = r["count"]

    total = sum(counters.values())

    urgentes_sql = text(
        f"""
        select count(*)::int as count
          from attendances a
         where {scope_sql} and {filters_sql}
           and a.urgency = true
           and a.status not in ('finalizado', 'arquivado')
        """
    ).bindparams(
        bindparam("period_from", type_=Date),
        bindparam("period_to", type_=Date),
        bindparam("legal_area_id", type_=Uuid),
    )
    urgentes = db.execute(
        urgentes_sql,
        {**scope_params, **filters_params, **_null_defaults(filters_params)},
    ).scalar() or 0

    return {
        "role": user.role,
        "period_from": period_from,
        "period_to": period_to,
        "total": total,
        "counters": counters,
        "urgentes": urgentes,
    }


def get_dashboard(
    db: Session,
    user: Profile,
    *,
    period_from: date | None = None,
    period_to: date | None = None,
    legal_area_id: UUID | None = None,
) -> dict[str, Any]:
    summary = get_summary(
        db,
        user,
        period_from=period_from,
        period_to=period_to,
        legal_area_id=legal_area_id,
    )

    counters = summary["counters"]
    pending_documents = counters.get("aguardando_documentos", 0)
    pending_teacher_analysis = sum(
        counters.get(s, 0) for s in ANALYSIS_STATUSES
    )

    # Retornos de hoje (escopado)
    today = date.today()
    appts_scope = ""
    appts_params: dict[str, Any] = {"today": today}
    if user.role == ROLE_STUDENT:
        appts_scope = (
            "and ("
            "  ap.responsible_id = :user_id"
            "  or exists (select 1 from attendances a "
            "             where a.id = ap.attendance_id "
            "               and a.student_id = :user_id)"
            ")"
        )
        appts_params["user_id"] = user.id
    elif user.role == ROLE_TEACHER:
        appts_scope = (
            "and ("
            "  ap.responsible_id = :user_id"
            "  or exists (select 1 from attendances a "
            "             where a.id = ap.attendance_id "
            "               and a.teacher_id = :user_id)"
            ")"
        )
        appts_params["user_id"] = user.id

    appts_sql = text(
        f"""
        select count(*)::int from appointments ap
         where ap.appointment_date = :today
           and ap.status not in ('cancelado', 'nao_compareceu')
           {appts_scope}
        """
    )
    appointments_today = db.execute(appts_sql, appts_params).scalar() or 0

    return {
        **summary,
        "appointments_today": appointments_today,
        "pending_documents": pending_documents,
        "pending_teacher_analysis": pending_teacher_analysis,
    }


# ---------------------------------------------------------------------------
# By-status / by-area
# ---------------------------------------------------------------------------
def by_status(
    db: Session,
    user: Profile,
    *,
    period_from: date | None = None,
    period_to: date | None = None,
    legal_area_id: UUID | None = None,
    student_id: UUID | None = None,
    teacher_id: UUID | None = None,
) -> list[dict[str, Any]]:
    summary = get_summary(
        db,
        user,
        period_from=period_from,
        period_to=period_to,
        legal_area_id=legal_area_id,
        student_id=student_id,
        teacher_id=teacher_id,
    )
    return [
        {"status": s, "label": ATTENDANCE_STATUS_LABELS[s], "count": summary["counters"][s]}
        for s in ALL_STATUSES
    ]


def by_area(
    db: Session,
    user: Profile,
    *,
    period_from: date | None = None,
    period_to: date | None = None,
    student_id: UUID | None = None,
    teacher_id: UUID | None = None,
) -> list[dict[str, Any]]:
    scope_sql, scope_params = _scope_clause(
        user, student_id=student_id, teacher_id=teacher_id
    )
    filters_sql, filters_params = _common_filters(
        period_from, period_to, None, None
    )

    sql = text(
        f"""
        select a.legal_area_id, la.name as legal_area_name, count(*)::int as count
          from attendances a
          left join legal_areas la on la.id = a.legal_area_id
         where {scope_sql} and {filters_sql}
         group by a.legal_area_id, la.name
         order by count desc
        """
    ).bindparams(
        bindparam("period_from", type_=Date),
        bindparam("period_to", type_=Date),
    )
    rows = db.execute(
        sql,
        {**scope_params, **filters_params, **_null_defaults(filters_params)},
    ).mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# By-student / by-teacher (produtividade)
# ---------------------------------------------------------------------------
def by_user(
    db: Session,
    user: Profile,
    *,
    join_field: str,  # "student_id" ou "teacher_id"
    period_from: date | None = None,
    period_to: date | None = None,
    legal_area_id: UUID | None = None,
) -> list[dict[str, Any]]:
    """Agrega por aluno (student_id) ou professor (teacher_id).

    O escopo automático por perfil ainda se aplica: aluno só vê suas linhas;
    professor só vê as suas (quando join_field=teacher_id) ou os alunos dos
    seus casos.
    """
    scope_sql, scope_params = _scope_clause(user)
    filters_sql, filters_params = _common_filters(
        period_from, period_to, legal_area_id, None
    )

    sql = text(
        f"""
        select
          a.{join_field}                                 as user_id,
          p.name                                         as user_name,
          count(*)::int                                  as total,
          count(*) filter (
            where a.status in ('finalizado', 'arquivado')
          )::int                                         as finalizados,
          count(*) filter (
            where a.status not in ('finalizado', 'arquivado')
          )::int                                         as em_andamento,
          count(*) filter (where a.urgency = true)::int  as urgentes
        from attendances a
        join profiles p on p.id = a.{join_field}
        where a.{join_field} is not null
          and {scope_sql} and {filters_sql}
        group by a.{join_field}, p.name
        order by total desc
        """
    ).bindparams(
        bindparam("period_from", type_=Date),
        bindparam("period_to", type_=Date),
        bindparam("legal_area_id", type_=Uuid),
    )
    rows = db.execute(
        sql,
        {**scope_params, **filters_params, **_null_defaults(filters_params)},
    ).mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Pending lists
# ---------------------------------------------------------------------------
def pending_documents(
    db: Session, user: Profile, *, limit: int = 100, offset: int = 0
) -> list[dict[str, Any]]:
    return _pending_list(
        db, user, status_filter="aguardando_documentos", limit=limit, offset=offset
    )


def pending_teacher_analysis(
    db: Session, user: Profile, *, limit: int = 100, offset: int = 0
) -> list[dict[str, Any]]:
    return _pending_list(
        db,
        user,
        status_filter=None,
        statuses_in=ANALYSIS_STATUSES,
        limit=limit,
        offset=offset,
    )


def _pending_list(
    db: Session,
    user: Profile,
    *,
    status_filter: str | None = None,
    statuses_in: set[str] | None = None,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    scope_sql, scope_params = _scope_clause(user)
    extra_status_sql = ""
    extra_params: dict[str, Any] = {}
    if status_filter is not None:
        extra_status_sql = "and a.status = :status_filter"
        extra_params["status_filter"] = status_filter
    if statuses_in is not None:
        placeholders = ",".join(f"'{s}'" for s in statuses_in)
        extra_status_sql = f"and a.status in ({placeholders})"

    sql = text(
        f"""
        select
          a.id, a.client_id,
          c.full_name                            as client_name,
          a.legal_area_id, la.name               as legal_area_name,
          a.demand_type_id, dt.name              as demand_type_name,
          a.student_id, s.name                   as student_name,
          a.teacher_id, t.name                   as teacher_name,
          a.status, a.urgency,
          a.created_at, a.updated_at
        from attendances a
        join clients c                  on c.id  = a.client_id
        left join legal_areas la        on la.id = a.legal_area_id
        left join demand_types dt       on dt.id = a.demand_type_id
        left join profiles s            on s.id  = a.student_id
        left join profiles t            on t.id  = a.teacher_id
        where {scope_sql}
          {extra_status_sql}
        order by a.urgency desc, a.created_at asc
        limit :limit offset :offset
        """
    )
    rows = db.execute(
        sql,
        {**scope_params, **extra_params, "limit": limit, "offset": offset},
    ).mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------
def _null_defaults(params: dict[str, Any]) -> dict[str, Any]:
    """Garante que os bindparams tipados que não estão em `params` tenham None.

    Necessário porque o SQLAlchemy reclama se um bindparam declarado não
    receber valor.
    """
    keys = {"period_from", "period_to", "legal_area_id"}
    return {k: None for k in keys if k not in params}
