"""
客户客户端路由 - 模拟真实客户从外部发起咨询
无需登录，客户通过 /server 页面进入
"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import random

from app.database import get_db
from app.models import Session as SessionModel, Message, Order, Reply
from app.routers.ai import _ai_analyze, _build_session_context, DEFAULT_REPLIES, _calc_confidence

router = APIRouter(prefix="/api/customer", tags=["customer"])

# ========== 模拟商品数据（对应飞书商品表结构） ==========
MOCK_PRODUCTS = [
    {"id": 1, "name": "免打孔不锈钢置物架", "sku": "YQ-ZWJ-001", "price": "¥39.9", "stock": 500,
     "category": "居家", "material": "304不锈钢", "size": "40×25×15cm", "spec": "三层",
     "scenes": ["日常", "居家"], "desc": "强力粘贴免打孔，承重20kg，浴室厨房通用"},
    {"id": 2, "name": "可折叠收纳箱大容量", "sku": "YQ-SNX-002", "price": "¥59.9", "stock": 300,
     "category": "居家", "material": "PP环保塑料", "size": "50×35×30cm", "spec": "35L",
     "scenes": ["日常", "居家", "办公"], "desc": "可折叠不占地，承重50kg，自带提手"},
    {"id": 3, "name": "恒温电热水杯便携款", "sku": "YQ-DSB-003", "price": "¥129.0", "stock": 150,
     "category": "生活", "material": "316不锈钢内胆", "size": "350ml", "spec": "USB充电",
     "scenes": ["日常", "办公", "旅行"], "desc": "三档调温，续航8小时，出差办公必备"},
    {"id": 4, "name": "北欧风实木衣帽架", "sku": "YQ-YMJ-004", "price": "¥89.0", "stock": 200,
     "category": "居家", "material": "榉木实木", "size": "高170cm", "spec": "六钩",
     "scenes": ["日常", "居家"], "desc": "稳固底座不摇晃，简约北欧风，安装简单"},
    {"id": 5, "name": "食品级密封保鲜盒套装", "sku": "YQ-BXH-005", "price": "¥49.9", "stock": 800,
     "category": "厨房", "material": "硼硅玻璃", "size": "三件套", "spec": "800ml+1200ml+1800ml",
     "scenes": ["日常", "居家", "办公"], "desc": "耐高温可微波，密封防漏，叠放省空间"},
    {"id": 6, "name": "吸壁式吹风机支架", "sku": "YQ-CFJ-006", "price": "¥19.9", "stock": 1000,
     "category": "卫浴", "material": "ABS工程塑料", "size": "标准款", "spec": "免打孔",
     "scenes": ["日常", "居家"], "desc": "强力吸盘免打孔，适配99%吹风机，解放双手"},
]

# ========== 模拟订单数据（对应飞书订单表结构） ==========
def _gen_orders(name: str, platform: str) -> list:
    """根据客户名和平台生成模拟历史订单"""
    random.seed(hash(name + platform) & 0xFFFFFFFF)
    order_templates = [
        {"name": "免打孔不锈钢置物架", "price": "¥39.9", "status": "已发货", "logistics": "运输中"},
        {"name": "可折叠收纳箱大容量", "price": "¥59.9", "status": "已签收", "logistics": "已签收"},
        {"name": "恒温电热水杯便携款", "price": "¥129.0", "status": "已支付", "logistics": "未发货"},
        {"name": "北欧风实木衣帽架", "price": "¥89.0", "status": "已完成", "logistics": "已签收"},
        {"name": "食品级密封保鲜盒套装", "price": "¥49.9", "status": "退款中", "logistics": "已签收"},
    ]
    count = random.randint(1, 3)
    chosen = random.sample(order_templates, min(count, len(order_templates)))
    orders = []
    for i, t in enumerate(chosen):
        orders.append({
            "id": i + 1,
            "order_no": f"{platform[:1].upper()}{random.randint(202401000, 202401999)}",
            "name": t["name"],
            "price": t["price"],
            "status": t["status"],
            "logistics": t["logistics"],
            "platform": platform,
        })
    return orders


# ========== 请求模型 ==========
class CustomerStartRequest(BaseModel):
    name: str
    platform: str
    type: str  # "pre-sale" | "after-sale"
    product_id: Optional[int] = None
    order_info: Optional[dict] = None


class CustomerSendRequest(BaseModel):
    text: str


# ========== 接口 ==========

@router.get("/products")
def get_products():
    """获取商品列表（售前咨询用）"""
    return MOCK_PRODUCTS


@router.get("/orders")
def get_orders(name: str = Query(...), platform: str = Query(...)):
    """获取客户历史订单（售后咨询用）"""
    return _gen_orders(name, platform)


# ========== 历史会话 + 6条关联提问 ==========
# 售前场景6条关联提问
PRE_SALE_QUESTIONS = [
    "这个商品多少钱？有优惠活动吗？",
    "商品有现货吗？什么时候能发货？",
    "支持七天无理由退换货吗？",
    "发什么快递？运费多少？",
    "材质是什么？尺寸规格多大？",
    "质量有保证吗？有售后质保吗？",
]

# 售后场景6条关联提问
AFTER_SALE_QUESTIONS = [
    "我的订单什么时候能送到？",
    "物流到哪了？能帮忙催一下吗？",
    "商品有质量问题，想申请退换货",
    "申请退款，大概多久能到账？",
    "能修改收货地址吗？",
    "需要开发票，怎么操作？",
]


def _gen_questions(user_tag: str) -> list:
    """根据会话类型生成6条关联提问"""
    if "售前" in (user_tag or ""):
        return PRE_SALE_QUESTIONS
    return AFTER_SALE_QUESTIONS


@router.get("/history")
def get_history(name: str = Query(...), platform: str = Query(...), db: Session = Depends(get_db)):
    """
    获取客户历史会话列表，每个会话附带6条关联提问。
    客户端主页展示历史聊天记录 + 提问复选框。
    """
    sessions = (
        db.query(SessionModel)
        .filter(SessionModel.user_name == name, SessionModel.source == platform)
        .order_by(SessionModel.created_at.desc())
        .all()
    )
    result = []
    for s in sessions:
        msgs = (
            db.query(Message)
            .filter(Message.session_id == s.id)
            .order_by(Message.created_at)
            .all()
        )
        # 最近5条消息摘要
        recent = msgs[-5:] if len(msgs) > 5 else msgs
        result.append({
            "session_id": s.id,
            "type": "售前" if "售前" in (s.user_tag or "") else "售后",
            "preview": s.preview or "",
            "time": s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else "",
            "message_count": len(msgs),
            "recent_messages": [
                {"dir": m.dir, "text": m.text, "time": m.created_at.strftime("%H:%M") if m.created_at else ""}
                for m in recent
            ],
            "questions": _gen_questions(s.user_tag or ""),
        })
    return result


@router.post("/start")
def start_session(req: CustomerStartRequest, db: Session = Depends(get_db)):
    """
    客户发起咨询，创建新会话。
    工作台会通过轮询看到新客户出现。
    """
    # 平台映射
    platform_map = {
        "淘宝": "taobao", "天猫": "tmall", "京东": "jd", "拼多多": "pdd",
        "苏宁易购": "suning", "唯品会": "vip", "抖音": "douyin",
        "快手": "kuaishou", "小红书": "xhs", "微信": "wechat",
    }
    platform_code = platform_map.get(req.platform, "taobao")

    # 首字头像
    avatar = req.name[:1] if req.name else "客"

    # 售前/售后标签
    if req.type == "pre-sale":
        tag = "售前咨询"
        tag_cls = "bg-blue-50 text-primary"
        desc = f"售前咨询 · {req.platform}"
    else:
        tag = "售后咨询"
        tag_cls = "bg-orange-50 text-warning"
        desc = f"售后咨询 · {req.platform}"

    # 创建会话
    now = datetime.now()
    s = SessionModel(
        user_name=req.name,
        user_avatar=avatar,
        user_tag=tag,
        user_tag_class=tag_cls,
        source=req.platform,
        platform=platform_code,
        user_desc=desc,
        preview="新客户进入咨询...",
        tab="ai",
        status="active",
        time=now.strftime("%H:%M"),
        tags=[{"text": tag, "cls": tag_cls}],
    )
    db.add(s)
    db.flush()

    # 如果是售前且有商品，创建关联订单（用于工作台展示）
    if req.type == "pre-sale" and req.product_id:
        product = next((p for p in MOCK_PRODUCTS if p["id"] == req.product_id), None)
        if product:
            order = Order(
                session_id=s.id,
                name=product["name"],
                status="咨询中",
                status_class="text-primary",
                order_no=f"PRE-{s.id}-{product['sku']}",
                price=product["price"],
                platform=platform_code,
            )
            db.add(order)

    # 如果是售后且有订单信息，创建关联订单
    if req.type == "after-sale" and req.order_info:
        oi = req.order_info
        order = Order(
            session_id=s.id,
            name=oi.get("name", ""),
            status=oi.get("status", "已签收"),
            status_class="text-warning" if "退款" in oi.get("status", "") else "text-success",
            order_no=oi.get("order_no", ""),
            price=oi.get("price", ""),
            platform=platform_code,
        )
        db.add(order)

    # 系统欢迎消息
    welcome_msg = Message(
        session_id=s.id,
        dir="left",
        text=f"您好，欢迎咨询优勤智服！我是AI智能客服，请问有什么可以帮您的？😊",
        type="ai",
    )
    db.add(welcome_msg)

    # 更新预览
    s.preview = f"{req.name} 进入{tag}"
    db.commit()
    db.refresh(s)
    db.refresh(welcome_msg)

    return {
        "session_id": s.id,
        "welcome_message": {
            "id": welcome_msg.id,
            "dir": welcome_msg.dir,
            "text": welcome_msg.text,
            "type": welcome_msg.type,
            "has_product": False,
            "created_at": welcome_msg.created_at.isoformat(),
        },
    }


@router.get("/{session_id}/messages")
def get_messages(session_id: int, db: Session = Depends(get_db)):
    """获取会话消息列表（客户端轮询用）"""
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
        }
        for m in msgs
    ]


@router.post("/{session_id}/send")
def send_message(session_id: int, req: CustomerSendRequest, db: Session = Depends(get_db)):
    """
    客户发送消息，同时触发AI分析。
    AI可能自动回复，也可能转人工（工作台客服看到后处理）。
    """
    s = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not s:
        return {"error": "Session not found"}

    # 保存客户消息
    now = datetime.now()
    customer_msg = Message(
        session_id=session_id,
        dir="right",
        text=req.text,
        type="user",
    )
    db.add(customer_msg)
    s.preview = req.text
    s.time = now.strftime("%H:%M")
    s.updated_at = now
    db.flush()
    # 先 commit 客户消息，让工作台轮询能立即看到客户消息（不必等AI回复完）
    db.commit()
    db.refresh(customer_msg)
    db.refresh(s)

    # 构建对话上下文
    session_context = _build_session_context(db, session_id, limit=6)

    # AI 分析
    analysis = _ai_analyze(
        req.text, s.score,
        session_context=session_context, db=db, session_id=session_id,
    )

    # 更新会话分析字段
    s.intent = analysis["intent"]
    s.emotion = analysis["emotion"]
    s.emotion_class = analysis["emotion_class"]
    s.risk = analysis["risk"]
    s.risk_class = analysis["risk_class"]
    s.segment = analysis["segment"]
    s.score = analysis["score"]
    s.score_color = analysis["score_color"]
    s.value_desc = analysis["value_desc"]

    # 如果不可自动回答，标记为需人工
    if not analysis["can_auto_answer"]:
        s.tab = "wait"
        s.tags = [{"text": "需人工处理", "cls": "bg-orange-50 text-warning"}]

    # AI 自动回复
    auto_answer_msg = None
    if analysis["can_auto_answer"] and analysis["auto_answer"]:
        # 用本次分析结果计算置信度快照（与 ai.py 的 _calc_confidence 一致）
        _conf = _calc_confidence(
            risk=analysis.get("risk", ""),
            emotion=analysis.get("emotion", ""),
            intent=analysis.get("intent", ""),
        )
        ai_msg = Message(
            session_id=session_id,
            dir="left",
            text=analysis["auto_answer"],
            type="ai",
            confidence=_conf,
        )
        db.add(ai_msg)
        db.flush()
        auto_answer_msg = {
            "id": ai_msg.id,
            "dir": ai_msg.dir,
            "text": ai_msg.text,
            "type": ai_msg.type,
            "has_product": False,
            "created_at": ai_msg.created_at.isoformat(),
            "confidence": _conf,
        }
    else:
        # 不可自动回答，发送"正在为您转接人工客服"提示（无置信度）
        transfer_msg = Message(
            session_id=session_id,
            dir="left",
            text="您的问题我需要转接人工客服为您处理，请稍等片刻～",
            type="ai",
        )
        db.add(transfer_msg)
        db.flush()
        auto_answer_msg = {
            "id": transfer_msg.id,
            "dir": transfer_msg.dir,
            "text": transfer_msg.text,
            "type": transfer_msg.type,
            "has_product": False,
            "created_at": transfer_msg.created_at.isoformat(),
            "confidence": None,
        }

    # 保存推荐话术（供工作台客服使用）
    db.query(Reply).filter(Reply.session_id == session_id).delete()
    for i, text in enumerate(analysis.get("suggested_replies", [])):
        db.add(Reply(session_id=session_id, text=text, sort_order=i))

    db.commit()

    return {
        "customer_message": {
            "id": customer_msg.id,
            "dir": customer_msg.dir,
            "text": customer_msg.text,
            "type": customer_msg.type,
            "has_product": False,
            "created_at": customer_msg.created_at.isoformat(),
        },
        "ai_reply": auto_answer_msg,
        "analysis": {
            "intent": analysis["intent"],
            "emotion": analysis["emotion"],
            "can_auto_answer": analysis["can_auto_answer"],
        },
    }
