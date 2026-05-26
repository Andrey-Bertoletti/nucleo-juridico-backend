"""Modelos ORM dos módulos `templates` e `generated_documents`."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database.session import Base


class Template(Base):
    """Modelo reutilizável (relatório, atendimento ou documento).

    `content` é texto livre com placeholders no formato `{{nome_campo}}` —
    os campos disponíveis vêm de `dynamic_fields` (lista de definições) e
    são preenchidos na hora de gerar um documento final.
    """

    __tablename__ = "templates"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    # type ∈ {"relatorio", "atendimento", "documento"} — validado no schema
    type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Lista de campos dinâmicos: [{"name", "label", "type", "required"}, ...].
    dynamic_fields: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    status: Mapped[str] = mapped_column(
        String(10), nullable=False, default="ativo", server_default="ativo"
    )
    created_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class GeneratedDocument(Base):
    """Documento gerado a partir de um Template, com identificação manual do
    aluno responsável (campo obrigatório por causa do login compartilhado).

    `final_content` guarda o texto JÁ interpolado (campos preenchidos) — fica
    redundante com `filled_data` + `template.content`, mas é o que se imprime
    e o que fica como prova caso o template original seja editado depois.
    """

    __tablename__ = "generated_documents"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    template_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )
    # Espelha `templates.type` no momento da geração — preservado mesmo se o
    # tipo do template mudar depois.
    template_type: Mapped[str] = mapped_column(String(20), nullable=False)
    template_title: Mapped[str] = mapped_column(String(200), nullable=False)

    # Quem estava logado quando gerou (auditoria do SISTEMA).
    generated_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True, index=True
    )

    # ⚠ Identificação MANUAL do aluno responsável — obrigatória mesmo se o
    # `generated_by_user_id` for o "aluno geral". Esse é o registro auditável
    # de quem realmente assinou o documento físico.
    student_name: Mapped[str] = mapped_column(String(200), nullable=False)
    student_matricula: Mapped[str] = mapped_column(String(50), nullable=False)
    # Data que o aluno coloca no documento (não confundir com `generated_at`).
    attendance_date: Mapped[datetime] = mapped_column(
        Date, nullable=False
    )

    # Dados do form (chave = nome do campo dinâmico do template).
    filled_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    # Texto final já interpolado, pronto para impressão.
    final_content: Mapped[str] = mapped_column(Text, nullable=False)

    # FKs opcionais para vincular ao registro de origem (quando aplicável).
    attendance_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True, index=True
    )
    client_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True, index=True
    )

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
