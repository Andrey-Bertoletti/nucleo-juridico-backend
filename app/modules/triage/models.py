"""Modelo ORM da tabela `triages`."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database.session import Base


class Triage(Base):
    __tablename__ = "triages"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    attendance_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, unique=True, index=True
    )
    client_report: Mapped[str | None] = mapped_column(Text, nullable=True)
    has_urgent_deadline: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    urgency_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    presented_documents: Mapped[str | None] = mapped_column(Text, nullable=True)
    pending_documents: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_forwarding: Mapped[str | None] = mapped_column(Text, nullable=True)
    student_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# silencia o aviso de import não utilizado para uma futura expansão de String.
_ = String
