"""Regras de negócio do módulo reports."""

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import text
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
# Escopo por perfil — SQL fixo, bindparams sempre presentes
# ---------------------------------------------------------------------------
def _scope_clause(
    user: Profile,
    *,
    student_id: UUID | None = None,
    teacher_id: UUID | None = None,
) -> tuple[str, dict[str, Any]]:
    """Devolve o WHERE de escopo + dicionário de params.

    Estratégia: o SQL é sempre o mesmo (não depende do papel para a estrutura),
    e os bindparams existem sempre — usamos `cast(:p as uuid) is null` para
    filtros opcionais. A diferença por papel é só nos valores passados.
    """
    if user.role == ROLE_STUDENT:
        return "a.student_id = cast(:scope_user_id as uuid)", {
            "scope_user_id": str(user.id),
        }
    if user.role == ROLE_TEACHER:
        return "a.teacher_id = cast(:scope_user_id as uuid)", {
            "scope_user_id": str(user.id),
        }
    if user.role == ROLE_ADMIN:
        return (
            "(cast(:scope_student_id as uuid) is null "
            "  or a.student_id = cast(:scope_student_id as uuid))"
            " and "
            "(cast(:scope_teacher_id as uuid) is null "
            "  or a.teacher_id = cast(:scope_teacher_id as uuid))"
        ), {
            "scope_student_id": str(student_id) if student_id else None,
            "scope_teacher_id": str(teacher_id) if teacher_id else None,
        }
    # Não deveria acontecer (current_user já validado pela dependência),
    # mas por segurança nega tudo.
    return "false", {}


def _filter_params(
    period_from: date | None,
    period_to: date | None,
    legal_area_id: UUID | None,
) -> dict[str, Any]:
    return {
        "period_from": period_from,
        "period_to": period_to,
        "legal_area_id": str(legal_area_id) if legal_area_id else None,
    }


# Cláusula de filtros opcionais usada por todas as queries — placeholders
# SEMPRE presentes, mesmo quando o valor é None.
_FILTERS_SQL = """
  and (cast(:period_from as date) is null or a.created_at >= cast(:period_from as date))
  and (cast(:period_to as date)   is null or a.created_at <= cast(:period_to as date))
  and (cast(:legal_area_id as uuid) is null or a.legal_area_id = cast(:legal_area_id as uuid))
"""


# ---------------------------------------------------------------------------
# Summary
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
    params = {
        **scope_params,
        **_filter_params(period_from, period_to, legal_area_id),
    }

    sql_counts = text(
        f"""
        select a.status, count(*)::int as count
          from attendances a
         where ({scope_sql})
         {_FILTERS_SQL}
         group by a.status
        """
    )
    rows = db.execute(sql_counts, params).mappings().all()

    counters = {s: 0 for s in ALL_STATUSES}
    for r in rows:
        if r["status"] in counters:
            counters[r["status"]] = r["count"]

    sql_urgentes = text(
        f"""
        select count(*)::int as count
          from attendances a
         where ({scope_sql})
         {_FILTERS_SQL}
           and a.urgency = true
           and a.status not in ('finalizado', 'arquivado')
        """
    )
    urgentes = db.execute(sql_urgentes, params).scalar() or 0

    return {
        "role": user.role,
        "period_from": period_from,
        "period_to": period_to,
        "total": sum(counters.values()),
        "counters": counters,
        "urgentes": urgentes,
    }


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
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

    today = date.today()
    appts_scope = ""
    appts_params: dict[str, Any] = {"today": today}
    if user.role == ROLE_STUDENT:
        appts_scope = (
            "and ("
            "  ap.responsible_id = cast(:user_id as uuid)"
            "  or exists (select 1 from attendances a "
            "             where a.id = ap.attendance_id "
            "               and a.student_id = cast(:user_id as uuid))"
            ")"
        )
        appts_params["user_id"] = str(user.id)
    elif user.role == ROLE_TEACHER:
        appts_scope = (
            "and ("
            "  ap.responsible_id = cast(:user_id as uuid)"
            "  or exists (select 1 from attendances a "
            "             where a.id = ap.attendance_id "
            "               and a.teacher_id = cast(:user_id as uuid))"
            ")"
        )
        appts_params["user_id"] = str(user.id)

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
        {
            "status": s,
            "label": ATTENDANCE_STATUS_LABELS[s],
            "count": summary["counters"][s],
        }
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
    params = {
        **scope_params,
        **_filter_params(period_from, period_to, None),
    }

    sql = text(
        f"""
        select a.legal_area_id, la.name as legal_area_name, count(*)::int as count
          from attendances a
          left join legal_areas la on la.id = a.legal_area_id
         where ({scope_sql})
         {_FILTERS_SQL}
         group by a.legal_area_id, la.name
         order by count desc
        """
    )
    rows = db.execute(sql, params).mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Produtividade por aluno / professor
# ---------------------------------------------------------------------------
def by_user(
    db: Session,
    user: Profile,
    *,
    join_field: str,
    period_from: date | None = None,
    period_to: date | None = None,
    legal_area_id: UUID | None = None,
) -> list[dict[str, Any]]:
    if join_field not in {"student_id", "teacher_id"}:
        raise ValueError("join_field deve ser 'student_id' ou 'teacher_id'.")

    scope_sql, scope_params = _scope_clause(user)
    params = {
        **scope_params,
        **_filter_params(period_from, period_to, legal_area_id),
    }

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
          and ({scope_sql})
          {_FILTERS_SQL}
        group by a.{join_field}, p.name
        order by total desc
        """
    )
    rows = db.execute(sql, params).mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Pending lists
# ---------------------------------------------------------------------------
def pending_documents(
    db: Session, user: Profile, *, limit: int = 100, offset: int = 0
) -> list[dict[str, Any]]:
    return _pending_list(
        db,
        user,
        status_filter="aguardando_documentos",
        limit=limit,
        offset=offset,
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
        where ({scope_sql})
          {extra_status_sql}
        order by a.urgency desc, a.created_at asc
        limit :limit offset :offset
        """
    )
    rows = db.execute(
        sql,
        {
            **scope_params,
            **extra_params,
            "limit": limit,
            "offset": offset,
        },
    ).mappings().all()
    return [dict(r) for r in rows]
