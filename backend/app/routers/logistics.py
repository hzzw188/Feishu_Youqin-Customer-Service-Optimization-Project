"""
物流路由 — 模拟快递平台 API
提供：查轨迹、按会话查物流、催件、推进状态（测试用）
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Order, LogisticsTrack
from app.services.logistics_service import (
    STATUS_LABELS,
    get_logistics_context,
    advance_logistics,
    urge_logistics,
    set_exception,
)

router = APIRouter(prefix="/api/logistics", tags=["logistics"])


@router.get("/tracking/{tracking_no}")
def get_tracking(tracking_no: str, db: Session = Depends(get_db)):
    """按物流单号查询轨迹"""
    order = db.query(Order).filter(Order.tracking_no == tracking_no).first()
    if not order:
        return {"error": "物流单号不存在"}

    tracks = (
        db.query(LogisticsTrack)
        .filter(LogisticsTrack.order_id == order.id)
        .order_by(LogisticsTrack.id)
        .all()
    )

    return {
        "tracking_no": order.tracking_no,
        "carrier": order.carrier,
        "status": order.logistics_status,
        "status_label": STATUS_LABELS.get(order.logistics_status, "未知"),
        "order_no": order.order_no,
        "product_name": order.name,
        "timeline": [
            {"time": t.time, "location": t.location, "desc": t.desc}
            for t in tracks
        ],
    }


@router.get("/session/{session_id}")
def get_session_logistics(session_id: int, db: Session = Depends(get_db)):
    """按会话ID查询该会话所有订单的物流信息"""
    orders = db.query(Order).filter(Order.session_id == session_id).all()
    if not orders:
        return {"orders": []}

    result = []
    for order in orders:
        tracks = (
            db.query(LogisticsTrack)
            .filter(LogisticsTrack.order_id == order.id)
            .order_by(LogisticsTrack.id)
            .all()
        )
        result.append({
            "order_id": order.id,
            "order_no": order.order_no,
            "product_name": order.name,
            "tracking_no": order.tracking_no,
            "carrier": order.carrier,
            "status": order.logistics_status,
            "status_label": STATUS_LABELS.get(order.logistics_status, "未知"),
            "timeline": [
                {"time": t.time, "location": t.location, "desc": t.desc}
                for t in tracks
            ],
        })

    return {"orders": result}


@router.post("/urge/{tracking_no}")
def urge(tracking_no: str, db: Session = Depends(get_db)):
    """催件 — 客服发起催促快递请求"""
    order, msg = urge_logistics(db, tracking_no)
    if not order:
        return {"error": msg}

    return {
        "success": True,
        "message": f"已为订单{order.order_no}提交催件请求，{order.carrier}将加急处理",
        "tracking_no": order.tracking_no,
    }


@router.post("/advance")
def advance(order_id: int = Query(...), db: Session = Depends(get_db)):
    """推进物流状态到下一阶段（测试/演示用）"""
    order, msg = advance_logistics(db, order_id)
    if not order:
        return {"error": msg}

    return {
        "success": True,
        "message": f"订单{order.order_no}物流状态已推进到：{msg}",
        "status": order.logistics_status,
        "status_label": STATUS_LABELS.get(order.logistics_status, "未知"),
        "tracking_no": order.tracking_no,
    }


@router.post("/exception")
def mark_exception(
    order_id: int = Query(...),
    reason: str = Query("物流信息长时间未更新"),
    db: Session = Depends(get_db),
):
    """标记物流异常（测试/演示用）"""
    order, msg = set_exception(db, order_id, reason)
    if not order:
        return {"error": msg}

    return {
        "success": True,
        "message": f"订单{order.order_no}已标记物流异常：{reason}",
        "status": order.logistics_status,
    }
