"""
客户客户端路由 - 模拟真实客户从外部发起咨询
无需登录，客户通过 /server 页面进入
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import random

from app.database import get_db
from app.models import Session as SessionModel, Message, Order, Reply
from app.routers.ai import _ai_analyze, _build_session_context, DEFAULT_REPLIES, _calc_confidence

router = APIRouter(prefix="/api/customer", tags=["customer"])

# ========== 模拟商品数据（对应飞书商品表结构，数据来源：优勤企业数据参考） ==========
MOCK_PRODUCTS = [
    {"id": 1, "name": "厨房挂钩免打孔挂杆", "sku": "685181334733", "price": "¥29.9", "stock": 500,
     "category": "厨房", "material": "不锈钢烤漆", "size": "多钩排", "spec": "免钉胶安装",
     "scenes": ["日常", "厨房"], "desc": "不锈钢烤漆承重强不惧潮湿，免钉胶安装不伤墙面，挂锅铲勺子",
     "questions": [
        "这个挂钩怎么装啊？要打孔吗？我租的房子",
        "厨房潮湿会不会生锈啊？能用多久？",
        "粘墙上结实吗？会不会挂着挂着掉了？",
        "有安装视频吗？怕装不好",
        "瓷砖和玻璃都能粘吗？乳胶漆墙行不行？",
        "里面都有啥配件？粘胶要自己买吗？",
      ]},
    {"id": 2, "name": "防烫夹取碗夹", "sku": "696228242482", "price": "¥19.9", "stock": 300,
     "category": "厨房", "material": "不锈钢+硅胶", "size": "标准款", "spec": "食品级接触用",
     "scenes": ["日常", "厨房"], "desc": "食品级不锈钢耐腐蚀，硅胶防滑夹头不滑落，横竖可用无需安装",
     "questions": [
        "夹热的碗会不会烫手？防滑吗？",
        "这个夹子安全吗？接触食物没问题吧？",
        "能夹多大的碗？蒸鱼的大盘子能夹吗？",
        "用久了夹头会不会松？硅胶容易老化吗？",
        "好清洗吗？洗碗机能洗吗？",
        "买回来要自己装吗？还是直接用？",
      ]},
    {"id": 3, "name": "牙刷置物架免打孔套装", "sku": "697324608981", "price": "¥39.9", "stock": 200,
     "category": "卫浴", "material": "加厚材质", "size": "家庭套装", "spec": "杯口倒挂设计",
     "scenes": ["日常", "卫浴"], "desc": "杯口倒挂不易积水，免打孔壁挂安装，含杯架牙膏架配件",
     "questions": [
        "里面都有什么？杯子牙刷都能放吗？",
        "倒挂着放杯子会不会积水发霉啊？",
        "卫生间瓷砖能粘住吗？时间久了会不会掉？",
        "安装麻烦吗？有没有视频教程？",
        "一套能放几个人的牙刷？三口之家够用吗？",
        "好清洁吗？牙膏渍好擦掉吗？",
      ]},
    {"id": 4, "name": "锡纸空气炸锅专用纸", "sku": "717949271470", "price": "¥9.9", "stock": 1000,
     "category": "厨房", "material": "食品级铝箔", "size": "圆形", "spec": "一次性50张",
     "scenes": ["日常", "厨房"], "desc": "食品级加厚材质耐热防水，免洗护锅，适配空气炸锅",
     "questions": [
        "这个锡纸安全吗？加热会不会有味道？",
        "用一次就得扔吗？能不能洗洗再用？",
        "耐高温吗？烤箱也能用吗？",
        "一包能用多久？50张大概几次？",
        "什么牌子的空气炸锅都能用吗？",
        "用完直接扔垃圾桶就行吗？环保吗？",
      ]},
    {"id": 5, "name": "洗脸盆收纳架子", "sku": "865266110253", "price": "¥49.9", "stock": 400,
     "category": "卫浴", "material": "PP+钢管", "size": "伸缩款", "spec": "悬浮置物架",
     "scenes": ["日常", "卫浴"], "desc": "悬浮设计一架多用，伸缩自如适配柜体，承重力强",
     "questions": [
        "这个架子怎么装？要打孔吗？有图纸吗？",
        "能伸缩多宽？我家浴室柜下面能放得下吗？",
        "结实吗？放几个盆会不会塌？",
        "能放其他东西吗？不光是盆子？",
        "浴室潮湿会不会生锈变形？",
        "好安装吗？女生一个人能装好吗？",
      ]},
    {"id": 6, "name": "厨房抽拉式置物架", "sku": "873585526605", "price": "¥69.9", "stock": 150,
     "category": "厨房", "material": "PP+钢架", "size": "三层组装款", "spec": "抽拉式拉篮",
     "scenes": ["日常", "厨房"], "desc": "橱柜内分层收纳，抽拉设计取物方便，大小号可选",
     "questions": [
        "安装复杂吗？有没有视频教程？",
        "大号和小号差多少？我家橱柜选哪个？",
        "拉出来顺不顺？会不会卡？",
        "能放锅吗？还是只能放调料瓶？",
        "放水槽下面潮湿会不会发霉？",
        "里面都带什么配件？要自己买螺丝吗？",
      ]},
    {"id": 7, "name": "零食置物架小推车", "sku": "876196854199", "price": "¥79.9", "stock": 300,
     "category": "居家", "material": "PP+钢管", "size": "多层落地款", "spec": "带万向轮",
     "scenes": ["日常", "居家", "办公"], "desc": "多层带轮移动方便，收纳零食杂物书籍，多款可选",
     "questions": [
        "有好几款？有什么区别？哪个好用？",
        "带轮子推起来顺不顺？会不会跑偏？",
        "安装难吗？有视频吗？要多久装好？",
        "放客厅好看吗？会不会显得廉价？",
        "结实吗？放书会不会压弯？",
        "租房用合适吗？搬家能带走吗？",
      ]},
    {"id": 8, "name": "浴室吸盘伸缩浴巾架", "sku": "899439835742", "price": "¥59.9", "stock": 250,
     "category": "卫浴", "material": "太空铝+吸盘", "size": "60cm伸缩款", "spec": "免打孔吸盘",
     "scenes": ["日常", "卫浴"], "desc": "吸盘式免打孔不伤墙面，折叠设计节省空间，适合租房",
     "questions": [
        "吸盘真的不会掉吗？以前买的都掉了",
        "装好后要等多久才能挂东西？",
        "能放几条浴巾？湿的挂上去行吗？",
        "瓷砖能用吗？我家是磨砂瓷砖",
        "折叠的怎么用？不用的时候能收起来？",
        "有安装视频吗？怕装不好",
      ]},
    {"id": 9, "name": "YOUQIN抽拉式厨房置物架", "sku": "931620460379", "price": "¥129.0", "stock": 100,
     "category": "厨房", "material": "PP+钢架", "size": "多层落地款", "spec": "抽拉/固定双款可选",
     "scenes": ["日常", "厨房"], "desc": "可放微波炉等电器，抽拉款取物方便，固定款稳固耐用",
     "questions": [
        "抽拉的和固定的哪个好？纠结死了",
        "能放微波炉吗？会不会太重压坏？",
        "好安装吗？有视频教程吗？",
        "多大尺寸？我家厨房小能放得下吗？",
        "稳不稳？拉出来会不会倒？",
        "这个日本YOUQIN和优勤是一家吗？",
      ]},
    {"id": 10, "name": "粘毛器滚筒可撕式", "sku": "996877163053", "price": "¥15.9", "stock": 800,
     "category": "居家", "material": "PP+粘纸", "size": "标准款", "spec": "可撕式替换纸",
     "scenes": ["日常", "居家"], "desc": "可撕式滚刷除灰尘猫毛头发，养宠家庭必备，轻便易用",
     "questions": [
        "家里两只猫，这个粘毛效果好吗？",
        "用完了怎么换纸？替换纸哪买？",
        "一卷能用多久？一天粘一次的话",
        "粘力大不大？会不会粘不干净？",
        "沙发和床单都能用吗？会不会留胶？",
        "粘完直接撕掉就行？不用洗？",
      ]},
]

# ========== 模拟订单数据（对应飞书订单表结构） ==========
def _gen_orders(name: str, platform: str) -> list:
    """根据客户名和平台生成模拟历史订单（使用局部随机实例，不污染全局状态）"""
    rng = random.Random(hash(name + platform) & 0xFFFFFFFF)
    order_templates = [
        {"name": "厨房挂钩免打孔挂杆", "price": "¥29.9", "status": "已发货", "logistics": "运输中"},
        {"name": "防烫夹取碗夹", "price": "¥19.9", "status": "已签收", "logistics": "已签收"},
        {"name": "牙刷置物架免打孔套装", "price": "¥39.9", "status": "已支付", "logistics": "未发货"},
        {"name": "厨房抽拉式置物架", "price": "¥69.9", "status": "已完成", "logistics": "已签收"},
        {"name": "零食置物架小推车", "price": "¥79.9", "status": "退款中", "logistics": "已签收"},
    ]
    count = rng.randint(1, 3)
    chosen = rng.sample(order_templates, min(count, len(order_templates)))
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
        raise HTTPException(status_code=404, detail="Session not found")

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

    # AI 分析（外覆异常保护：分析失败不阻塞客户消息已保存的结果）
    analysis = None
    try:
        analysis = _ai_analyze(
            req.text, s.score,
            session_context=session_context, db=db, session_id=session_id,
        )
    except Exception as e:
        import logging
        logging.getLogger("uvicorn.error").error(f"AI分析失败 (session={session_id}): {e}")
        # 降级：标记为需人工处理，不生成 AI 回复
        analysis = {
            "intent": "待识别", "emotion": "平稳", "emotion_class": "bg-green-50 text-success",
            "risk": "✅ 低风险", "risk_class": "bg-gray-100 text-gray-500",
            "segment": "普通用户", "score": s.score or 50, "score_color": "bg-primary",
            "value_desc": "AI分析异常，已转人工",
            "can_auto_answer": False, "auto_answer": "",
            "suggested_replies": [
                "亲，您的问题我已经了解了，正在为您查询中，请稍等～",
                "您好，感谢您的反馈，我马上帮您核实处理～",
                "收到您的信息，我已经记录下来了，会尽快为您解决。",
            ],
        }

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


# ========== 营收贡献测算（基于《客户价值视角的电商客服营收贡献测算模型》：基准差额法） ==========
# 核心测算函数统一放在 app/services/revenue_service.py，供 cockpit.py 驾驶舱复用
from app.services.revenue_service import (
    parse_price,
    estimate_base_convert_prob,
    estimate_base_refund_prob,
    calc_session_contribution,
)


def _sys_msg_dict(m: Message) -> dict:
    return {
        "id": m.id,
        "dir": m.dir,
        "text": m.text,
        "type": m.type,
        "has_product": False,
        "created_at": m.created_at.isoformat(),
    }


@router.post("/{session_id}/place-order")
def place_order(session_id: int, db: Session = Depends(get_db)):
    """售前：客户点击'下单' → 标记成交并计算客服收益贡献 Vconv"""
    s = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    orders = db.query(Order).filter(Order.session_id == s.id).all()
    gmv = sum(parse_price(o.price) for o in orders)
    if gmv <= 0:
        raise HTTPException(status_code=400, detail="请先选择咨询的商品再下单")
    if s.is_deal:
        result = calc_session_contribution(s, db)
        return {"already_deal": True, "contribution": result, "message": None}

    s.is_deal = 1
    s.deal_amount = gmv
    for o in orders:
        if o.status in ("咨询中",):
            o.status = "已支付"
            o.status_class = "text-primary"
    result = calc_session_contribution(s, db)

    sys_msg = Message(
        session_id=session_id,
        dir="center",
        text=f"🛒 已下单（¥{s.deal_amount:.1f}）· 客服转化贡献 +¥{result['conv']:.1f}",
        type="system-msg",
    )
    db.add(sys_msg)
    db.commit()
    db.refresh(sys_msg)
    return {
        "already_deal": False,
        "message": _sys_msg_dict(sys_msg),
        "session": {"deal_amount": s.deal_amount, "contrib_total": s.contrib_total},
        "contribution": result,
    }


@router.post("/{session_id}/resolve")
def resolve_issue(session_id: int, db: Session = Depends(get_db)):
    """售后：客户点击'已解决' → 标记问题解决，计算退款挽回价值 Vretain"""
    s = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    orders = db.query(Order).filter(Order.session_id == s.id).all()
    gmv = sum(parse_price(o.price) for o in orders)
    if gmv <= 0:
        raise HTTPException(status_code=400, detail="请先选择相关订单")
    if s.resolved:
        result = calc_session_contribution(s, db)
        return {"already_resolved": True, "contribution": result, "message": None}

    s.resolved = 1
    s.refund_amount = 0  # 问题解决未退款，订单全额挽回
    result = calc_session_contribution(s, db)

    sys_msg = Message(
        session_id=session_id,
        dir="center",
        text=f"✅ 售后问题已解决 · 挽回订单 ¥{result['gmv']:.1f} · 客服挽回贡献 +¥{result['retain']:.1f}",
        type="system-msg",
    )
    db.add(sys_msg)
    db.commit()
    db.refresh(sys_msg)
    return {
        "already_resolved": False,
        "message": _sys_msg_dict(sys_msg),
        "session": {"resolved": s.resolved, "contrib_total": s.contrib_total},
        "contribution": result,
    }
