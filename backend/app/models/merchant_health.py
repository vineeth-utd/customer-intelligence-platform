from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MerchantHealth(Base):
    __tablename__ = "merchant_health"

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchants.merchant_id"), primary_key=True
    )
    health_score: Mapped[float] = mapped_column(Numeric, nullable=False)
    health_status: Mapped[str] = mapped_column(String, nullable=False)
    churn_risk_score: Mapped[float] = mapped_column(Numeric, nullable=False)
    engagement_score: Mapped[float] = mapped_column(Numeric, nullable=False)
    feature_adoption_score: Mapped[float] = mapped_column(Numeric, nullable=False)
    business_performance_score: Mapped[float] = mapped_column(Numeric, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    merchant: Mapped["Merchant"] = relationship()
