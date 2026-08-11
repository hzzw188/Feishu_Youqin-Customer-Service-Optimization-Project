from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import Session as SessionModel, Message, Order, Reply, LogisticsTrack
from app.schemas import SessionOut, SessionCreate, MessageCreate, MessageOut, OrderOut, ReplyOut

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("", response_model=List[dict])
def list_sessions(
    tab: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(SessionModel)
    if tab and tab != "all":
        query = query.filter(SessionModel.tab == tab)
    if platform:
        query = query.filter(SessionModel.platform == platform)
    if search:
        query = query.filter(
            (SessionModel.user_name.contains(search))
            | (SessionModel.preview.contains(search))
        )
    sessions = query.order_by(SessionModel.updated_at.desc().nullslast()).all()
    return [_session_to_dict(s) for s in sessions]


@router.delete("/all")
def clear_all_sessions(db: Session = Depends(get_db)):
    """一键清除所有客户信息：会话、消息、订单、推荐话术、物流轨迹"""
    # 按外键依赖顺序删除
    track_count = db.query(LogisticsTrack).count()
    reply_count = db.query(Reply).count()
    order_count = db.query(Order).count()
    msg_count = db.query(Message).count()
    session_count = db.query(SessionModel).count()

    db.query(LogisticsTrack).delete()
    db.query(Reply).delete()
    db.query(Order).delete()
    db.query(Message).delete()
    db.query(SessionModel).delete()
    db.commit()

    return {
        "ok": True,
        "message": "已清除所有客户信息",
        "deleted": {
            "sessions": session_count,
            "messages": msg_count,
            "orders": order_count,
            "replies": reply_count,
            "logistics_tracks": track_count,
        },
    }


@router.get("/{session_id}", response_model=dict)
def get_session(session_id: int, db: Session = Depends(get_db)):
    s = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    return _session_to_dict(s)


@router.get("/{session_id}/messages", response_model=List[dict])
def get_messages(session_id: int, db: Session = Depends(get_db)):
    msgs = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at)
        .all()
    )
    return [
        {
            "id": m.id,
            "dir": m.dir,
            "text": m.text,
            "type": m.type,
            "has_product": bool(m.has_product),
            "created_at": m.created_at.isoformat(),
            "confidence": m.confidence,
        }
        for m in msgs
    ]


@router.post("/{session_id}/messages", response_model=dict)
def send_message(session_id: int, msg: MessageCreate, db: Session = Depends(get_db)):
    s = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")

    db_msg = Message(
        session_id=session_id,
        dir=msg.dir,
        text=msg.text,
        type=msg.type,
        has_product=msg.has_product,
    )
    db.add(db_msg)
    s.updated_at = db_msg.created_at
    db.commit()
    db.refresh(db_msg)

    return {
        "id": db_msg.id,
        "dir": db_msg.dir,
        "text": db_msg.text,
        "type": db_msg.type,
        "has_product": bool(db_msg.has_product),
        "created_at": db_msg.created_at.isoformat(),
        "confidence": db_msg.confidence,
    }


@router.get("/{session_id}/orders", response_model=List[dict])
def get_orders(session_id: int, db: Session = Depends(get_db)):
    orders = (
        db.query(Order).filter(Order.session_id == session_id).all()
    )
    return [
        {
            "id": o.id,
            "name": o.name,
            "status": o.status,
            "status_class": o.status_class,
            "order_no": o.order_no,
            "price": o.price,
            "platform": o.platform,
            "logistics_status": o.logistics_status,
            "tracking_no": o.tracking_no,
            "carrier": o.carrier,
        }
        for o in orders
    ]


@router.get("/{session_id}/replies", response_model=List[dict])
def get_replies(session_id: int, db: Session = Depends(get_db)):
    replies = (
        db.query(Reply)
        .filter(Reply.session_id == session_id)
        .order_by(Reply.sort_order)
        .all()
    )
    return [{"id": r.id, "text": r.text, "sort_order": r.sort_order} for r in replies]


@router.put("/{session_id}/tab")
def update_session_tab(
    session_id: int, tab: str = Query(...), db: Session = Depends(get_db)
):
    s = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    s.tab = tab
    if tab == "wait":
        s.tags = [{"text": "已转人工", "cls": "bg-orange-50 text-warning"}]
    db.commit()
    return {"ok": True}


@router.put("/{session_id}/status")
def update_session_status(
    session_id: int, status: str = Query(...), db: Session = Depends(get_db)
):
    s = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    s.status = status
    if status == "closed":
        s.tags = [{"text": "已结束", "cls": "bg-gray-100 text-gray-500"}]
    db.commit()
    return {"ok": True}


@router.put("/{session_id}/risk")
def mark_risk(session_id: int, db: Session = Depends(get_db)):
    s = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    s.risk = "🔴 高风险"
    s.risk_class = "bg-red-50 text-danger"
    s.tab = "wait"
    s.tags = [{"text": "高风险标记", "cls": "bg-red-50 text-danger"}]
    db.commit()
    return {"ok": True}


@router.delete("/{session_id}/messages")
def clear_messages(session_id: int, db: Session = Depends(get_db)):
    """清除指定会话的所有聊天记录"""
    s = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    db.query(Message).filter(Message.session_id == session_id).delete()
    s.preview = ""
    db.commit()
    return {"ok": True}


@router.delete("/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db)):
    """删除指定会话及其所有关联数据"""
    s = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    db.query(Message).filter(Message.session_id == session_id).delete()
    # 先删订单关联的物流轨迹，避免外键约束失败
    order_ids = [o.id for o in db.query(Order).filter(Order.session_id == session_id).all()]
    if order_ids:
        db.query(LogisticsTrack).filter(LogisticsTrack.order_id.in_(order_ids)).delete(synchronize_session=False)
    db.query(Order).filter(Order.session_id == session_id).delete()
    db.query(Reply).filter(Reply.session_id == session_id).delete()
    db.delete(s)
    db.commit()
    return {"ok": True}


def _session_to_dict(s: SessionModel) -> dict:
    return {
        "id": s.id,
        "user_name": s.user_name,
        "user_avatar": s.user_avatar,
        "user_tag": s.user_tag,
        "user_tag_class": s.user_tag_class,
        "source": s.source,
        "platform": s.platform,
        "user_desc": s.user_desc,
        "intent": s.intent,
        "emotion": s.emotion,
        "emotion_class": s.emotion_class,
        "risk": s.risk,
        "risk_class": s.risk_class,
        "segment": s.segment,
        "score": s.score,
        "score_color": s.score_color,
        "value_desc": s.value_desc,
        "preview": s.preview,
        "tab": s.tab,
        "status": s.status,
        "time": s.time,
        "tags": s.tags or [],
        "created_at": (s.created_at.isoformat() if s.created_at else None),
        "updated_at": (s.updated_at.isoformat() if s.updated_at else None),
    }