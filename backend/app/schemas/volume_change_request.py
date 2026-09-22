from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

VolumeRequestStatus = Literal["pending", "approved", "rejected"]


class VolumeChangeRequestCreate(BaseModel):
    pond_id: int = Field(..., alias="pondId")
    requested_volume_m3: float = Field(..., gt=0, alias="requestedVolumeM3")
    reason: str = Field(..., min_length=6)

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        # 去空白后至少 6 字
        stripped = v.strip()
        if len(stripped) < 6:
            raise ValueError("理由去空白后至少 6 个字")
        return stripped


class VolumeChangeRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    pond_id: int = Field(serialization_alias="pondId")
    original_volume_m3: float = Field(serialization_alias="originalVolumeM3")
    requested_volume_m3: float = Field(serialization_alias="requestedVolumeM3")
    reason: str
    status: VolumeRequestStatus
    applicant_id: int = Field(serialization_alias="applicantId")
    applicant_name: Optional[str] = Field(default=None, serialization_alias="applicantName")
    approver_id: Optional[int] = Field(default=None, serialization_alias="approverId")
    approver_name: Optional[str] = Field(default=None, serialization_alias="approverName")
    created_at: datetime = Field(serialization_alias="createdAt")
    decided_at: Optional[datetime] = Field(default=None, serialization_alias="decidedAt")
