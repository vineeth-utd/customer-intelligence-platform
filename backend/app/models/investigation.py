import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Investigation(Base):
    __tablename__ = "investigations"

    investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    merchant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("merchants.merchant_id"))
    title: Mapped[str] = mapped_column(String, nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    merchant: Mapped["Merchant | None"] = relationship()
    messages: Mapped[list["InvestigationMessage"]] = relationship(back_populates="investigation")
    tool_executions: Mapped[list["InvestigationToolExecution"]] = relationship(back_populates="investigation")
    evidence: Mapped[list["InvestigationEvidence"]] = relationship(back_populates="investigation")


class InvestigationMessage(Base):
    __tablename__ = "investigation_messages"

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("investigations.investigation_id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    investigation: Mapped["Investigation"] = relationship(back_populates="messages")


class InvestigationToolExecution(Base):
    __tablename__ = "investigation_tool_executions"

    tool_execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("investigations.investigation_id"), nullable=False, index=True
    )
    tool_name: Mapped[str] = mapped_column(String, nullable=False)
    tool_input: Mapped[dict] = mapped_column(JSONB, nullable=False)
    tool_output: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    investigation: Mapped["Investigation"] = relationship(back_populates="tool_executions")
    evidence: Mapped[list["InvestigationEvidence"]] = relationship(back_populates="tool_execution")


class InvestigationEvidence(Base):
    __tablename__ = "investigation_evidence"

    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("investigations.investigation_id"), nullable=False, index=True
    )
    tool_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("investigation_tool_executions.tool_execution_id")
    )
    evidence_type: Mapped[str] = mapped_column(String, nullable=False)
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    source_reference: Mapped[dict] = mapped_column(JSONB, nullable=False)
    evidence_summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    investigation: Mapped["Investigation"] = relationship(back_populates="evidence")
    tool_execution: Mapped["InvestigationToolExecution | None"] = relationship(back_populates="evidence")
