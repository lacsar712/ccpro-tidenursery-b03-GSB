from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Integer, Float, ForeignKey, Text, DateTime, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class VolumeChangeRequest(Base):
    """塘口体积变更审批单：体积只能凭通过的审批单落地，不允许直接改库。"""

    __tablename__ = "volume_change_requests"
    __table_args__ = (
        # 同一塘口同时只允许一张待审单
        Index(
            "uq_volume_request_pending_per_pond",
            "pond_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
            sqlite_where=text("status = 'pending'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    pond_id: Mapped[int] = mapped_column(ForeignKey("ponds.id"), nullable=False, index=True)
    original_volume_m3: Mapped[float] = mapped_column(Float, nullable=False)
    requested_volume_m3: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    # pending 待审 / approved 通过 / rejected 驳回
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    applicant_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    approver_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    decided_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    pond: Mapped["Pond"] = relationship("Pond", back_populates="volume_change_requests")
    applicant: Mapped["User"] = relationship("User", foreign_keys=[applicant_id])
    approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approver_id])

    @property
    def applicant_name(self) -> Optional[str]:
        return self.applicant.display_name if self.applicant else None

    @property
    def approver_name(self) -> Optional[str]:
        return self.approver.display_name if self.approver else None
