import re
from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

VolumeRequestStatus = Literal["pending", "approved", "rejected"]


class VolumeChangeRequestCreate(BaseModel):
    pond_id: int = Field(..., alias="pondId")
    requested_volume_m3: float = Field(..., alias="requestedVolumeM3")
    reason: str = Field(..., max_length=500)

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("requested_volume_m3")
    @classmethod
    def positive_volume(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("申请体积必须为正数")
        return v

    @field_validator("reason")
    @classmethod
    def reason_non_blank(cls, v: str) -> str:
        stripped = v.strip()
        if len(re.sub(r"\s+", "", v)) < 6:
            raise ValueError("理由去空白后至少 6 个字")
        return stripped


class VolumeChangeRequestReview(BaseModel):
    comment: Optional[str] = Field(None, max_length=500)


class VolumeChangeRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    pond_id: int = Field(serialization_alias="pondId")
    original_volume_m3: float = Field(serialization_alias="originalVolumeM3")
    requested_volume_m3: float = Field(serialization_alias="requestedVolumeM3")
    reason: str
    status: VolumeRequestStatus
    applicant_id: int = Field(serialization_alias="applicantId")
    approver_id: Optional[int] = Field(None, serialization_alias="approverId")
    review_comment: Optional[str] = Field(None, serialization_alias="reviewComment")
    created_at: datetime = Field(serialization_alias="createdAt")
    reviewed_at: Optional[datetime] = Field(None, serialization_alias="reviewedAt")

    applicant_name: Optional[str] = Field(None, serialization_alias="applicantName")
    approver_name: Optional[str] = Field(None, serialization_alias="approverName")
    pond_code: Optional[str] = Field(None, serialization_alias="pondCode")
