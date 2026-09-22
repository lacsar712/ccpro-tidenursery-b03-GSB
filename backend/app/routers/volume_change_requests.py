from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_admin
from app.database import get_db
from app.models.pond import Pond
from app.models.user import User
from app.models.volume_change_request import VolumeChangeRequest
from app.schemas.volume_change_request import (
    VolumeChangeRequestCreate,
    VolumeChangeRequestOut,
)

router = APIRouter(prefix="/api/volume-change-requests", tags=["volume-change-requests"])


@router.get("", response_model=List[VolumeChangeRequestOut])
def list_requests(
    pond_id: Optional[int] = Query(None, alias="pondId"),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(VolumeChangeRequest)
    if pond_id is not None:
        q = q.filter(VolumeChangeRequest.pond_id == pond_id)
    if status_filter is not None:
        q = q.filter(VolumeChangeRequest.status == status_filter)
    return q.order_by(VolumeChangeRequest.created_at.desc()).all()


@router.post("", response_model=VolumeChangeRequestOut, status_code=status.HTTP_201_CREATED)
def create_request(
    payload: VolumeChangeRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 技术员可发起体积变更申请
    pond = db.query(Pond).filter(Pond.id == payload.pond_id).first()
    if not pond:
        raise HTTPException(status_code=404, detail="塘口不存在")

    if payload.requested_volume_m3 == pond.volume_m3:
        raise HTTPException(status_code=400, detail="申请体积必须与原体积不同")

    pending = (
        db.query(VolumeChangeRequest)
        .filter(
            VolumeChangeRequest.pond_id == pond.id,
            VolumeChangeRequest.status == "pending",
        )
        .first()
    )
    if pending:
        raise HTTPException(
            status_code=409,
            detail="该塘口已有一张待审体积变更单，请等待场长审批后再申请",
        )

    item = VolumeChangeRequest(
        pond_id=pond.id,
        original_volume_m3=pond.volume_m3,
        requested_volume_m3=payload.requested_volume_m3,
        reason=payload.reason,
        status="pending",
        applicant_id=current_user.id,
    )
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="该塘口已有一张待审体积变更单，请等待场长审批后再申请",
        )
    db.refresh(item)
    return item


@router.post("/{request_id}/approve", response_model=VolumeChangeRequestOut)
def approve_request(
    request_id: int,
    db: Session = Depends(get_db),
    approver: User = Depends(require_admin),
):
    # 场长通过：同事务把塘口体积改成申请体积
    item = (
        db.query(VolumeChangeRequest)
        .filter(VolumeChangeRequest.id == request_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="审批单不存在")
    if item.status != "pending":
        raise HTTPException(status_code=409, detail="该审批单已终态，不可再改")

    pond = db.query(Pond).filter(Pond.id == item.pond_id).first()
    if not pond:
        raise HTTPException(status_code=404, detail="塘口不存在")

    pond.volume_m3 = item.requested_volume_m3
    item.status = "approved"
    item.approver_id = approver.id
    item.decided_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return item


@router.post("/{request_id}/reject", response_model=VolumeChangeRequestOut)
def reject_request(
    request_id: int,
    db: Session = Depends(get_db),
    approver: User = Depends(require_admin),
):
    # 场长驳回：不改体积
    item = (
        db.query(VolumeChangeRequest)
        .filter(VolumeChangeRequest.id == request_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="审批单不存在")
    if item.status != "pending":
        raise HTTPException(status_code=409, detail="该审批单已终态，不可再改")

    item.status = "rejected"
    item.approver_id = approver.id
    item.decided_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return item
