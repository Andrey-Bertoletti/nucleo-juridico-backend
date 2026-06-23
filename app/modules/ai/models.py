"""Modelo ORM da tabela `ai_analyses` — cache de análises de IA.

Uma linha por (documento, ação) quando `scope='document'`, ou por
(cliente, ação) quando `scope='client'` (usado pela Análise Geral). O cache
evita reprocessar — e repagar — a mesma análise. A invalidação é feita pelo
`source_hash` (muda quando o documento é alterado ou um novo é anexado).
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database.session import Base


class AiAnalysis(Base):
    __tablename__ = "ai_analyses"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    # 'document' | 'client'
    scope: Mapped[str] = mapped_column(String, nullable=False)
    document_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True, index=True
    )
    client_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="processando", server_default="processando"
    )
    result_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_used: Mapped[str | None] = mapped_column(String, nullable=True)
    tokens_input: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_output: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        # Um único registro por (documento, ação) no escopo de documento...
        Index(
            "uq_ai_analyses_document_action",
            "document_id",
            "action",
            unique=True,
            postgresql_where=text("scope = 'document'"),
        ),
        # ...e por (cliente, ação) no escopo de cliente (Análise Geral).
        Index(
            "uq_ai_analyses_client_action",
            "client_id",
            "action",
            unique=True,
            postgresql_where=text("scope = 'client'"),
        ),
    )
