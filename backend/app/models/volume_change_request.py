from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Integer, Float, ForeignKey, Index, DateTime, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class VolumeChangeRequest(Base):
    __tablename__ = "volume_change_requests"
    __table_args__ = (
        # 同塘同时只许一张待审单（pending 唯一）
        Index(
            "uq_pending_volume_request_per_pond",
            "pond_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    pond_id: Mapped[int] = mapped_column(ForeignKey("ponds.id"), nullable=False, index=True)
    original_volume_m3: Mapped[float] = mapped_column(Float, nullable=False)
    requested_volume_m3: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    applicant_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    approver_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    review_comment: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    pond: Mapped["Pond"] = relationship("Pond", foreign_keys=[pond_id])
    applicant: Mapped["User"] = relationship("User", foreign_keys=[applicant_id])
    approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approver_id])
