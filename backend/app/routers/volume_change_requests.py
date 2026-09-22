from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user, require_role
from app.database import get_db
from app.models.pond import Pond
from app.models.user import User
from app.models.volume_change_request import VolumeChangeRequest
from app.schemas.volume_change_request import (
    VolumeChangeRequestCreate,
    VolumeChangeRequestOut,
    VolumeChangeRequestReview,
)

router = APIRouter(prefix="/api/volume-change-requests", tags=["volume-change-requests"])


def _to_out(item: VolumeChangeRequest) -> VolumeChangeRequestOut:
    return VolumeChangeRequestOut(
        id=item.id,
        pond_id=item.pond_id,
        original_volume_m3=item.original_volume_m3,
        requested_volume_m3=item.requested_volume_m3,
        reason=item.reason,
        status=item.status,
        applicant_id=item.applicant_id,
        approver_id=item.approver_id,
        review_comment=item.review_comment,
        created_at=item.created_at,
        reviewed_at=item.reviewed_at,
        applicant_name=item.applicant.display_name if item.applicant else None,
        approver_name=item.approver.display_name if item.approver else None,
        pond_code=item.pond.pond_code if item.pond else None,
    )


@router.get("", response_model=List[VolumeChangeRequestOut])
def list_requests(
    status_filter: Optional[str] = Query(None, alias="status"),
    pond_id: Optional[int] = Query(None, alias="pondId"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(VolumeChangeRequest).options(
        joinedload(VolumeChangeRequest.pond),
        joinedload(VolumeChangeRequest.applicant),
        joinedload(VolumeChangeRequest.approver),
    )
    if status_filter:
        q = q.filter(VolumeChangeRequest.status == status_filter)
    if pond_id is not None:
        q = q.filter(VolumeChangeRequest.pond_id == pond_id)
    rows = q.order_by(VolumeChangeRequest.id.desc()).all()
    return [_to_out(r) for r in rows]


@router.post("", response_model=VolumeChangeRequestOut, status_code=status.HTTP_201_CREATED)
def create_request(
    payload: VolumeChangeRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("technician")),
):
    pond = db.query(Pond).filter(Pond.id == payload.pond_id).first()
    if not pond:
        raise HTTPException(status_code=404, detail="塘口不存在")
    if payload.requested_volume_m3 <= 0:
        raise HTTPException(status_code=400, detail="申请体积必须为正数")
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
            status_code=409, detail="该塘口已有待审批的体积变更单，不能重复申请"
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
            status_code=409, detail="该塘口已有待审批的体积变更单，不能重复申请"
        )
    db.refresh(item)
    item = (
        db.query(VolumeChangeRequest)
        .options(
            joinedload(VolumeChangeRequest.pond),
            joinedload(VolumeChangeRequest.applicant),
            joinedload(VolumeChangeRequest.approver),
        )
        .filter(VolumeChangeRequest.id == item.id)
        .first()
    )
    return _to_out(item)


def _get_pending_or_409(db: Session, request_id: int) -> VolumeChangeRequest:
    item = (
        db.query(VolumeChangeRequest)
        .options(joinedload(VolumeChangeRequest.pond))
        .filter(VolumeChangeRequest.id == request_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="审批单不存在")
    if item.status != "pending":
        raise HTTPException(status_code=409, detail="审批单已终态（通过/驳回），不可再改")
    return item


@router.post("/{request_id}/approve", response_model=VolumeChangeRequestOut)
def approve_request(
    request_id: int,
    payload: Optional[VolumeChangeRequestReview] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    item = _get_pending_or_409(db, request_id)
    comment = payload.comment if payload else None

    # 通过：同事务落地塘口体积
    try:
        item.pond.volume_m3 = item.requested_volume_m3
        item.status = "approved"
        item.approver_id = current_user.id
        item.review_comment = comment
        item.reviewed_at = datetime.now(timezone.utc)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="审批处理失败（数据冲突），请重试")

    row = (
        db.query(VolumeChangeRequest)
        .options(
            joinedload(VolumeChangeRequest.pond),
            joinedload(VolumeChangeRequest.applicant),
            joinedload(VolumeChangeRequest.approver),
        )
        .filter(VolumeChangeRequest.id == item.id)
        .first()
    )
    return _to_out(row)


@router.post("/{request_id}/reject", response_model=VolumeChangeRequestOut)
def reject_request(
    request_id: int,
    payload: Optional[VolumeChangeRequestReview] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    item = _get_pending_or_409(db, request_id)
    comment = payload.comment if payload else None

    # 驳回：不改体积
    item.status = "rejected"
    item.approver_id = current_user.id
    item.review_comment = comment
    item.reviewed_at = datetime.now(timezone.utc)
    db.commit()

    row = (
        db.query(VolumeChangeRequest)
        .options(
            joinedload(VolumeChangeRequest.pond),
            joinedload(VolumeChangeRequest.applicant),
            joinedload(VolumeChangeRequest.approver),
        )
        .filter(VolumeChangeRequest.id == item.id)
        .first()
    )
    return _to_out(row)
