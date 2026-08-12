"""
AI 路由 - 使用 DeepSeek API 进行智能分析、自动回答和话术推荐
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import random
from datetime import datetime
from app.database import get_db
from app.models import Session as SessionModel, Message, Reply, Order
from app.schemas import AIAnalysisRequest, AIAnalysisResponse
from app.services.deepseek_service import analyze_and_reply
from app.services.knowledge_base import search_knowledge, search_knowledge_structured, get_chunk_count, get_category_counts
from app.services.logistics_service import get_logistics_context

router = APIRouter(prefix="/api/ai", tags=["ai"])


def _calc_confidence(risk: str, emotion: str, intent: str) -> int:
    """
    AI 置信度纯函数：基于 risk/emotion/intent 推算，与前端 calcConfidence 保持同规则。
    用于在 AI 回答生成时打「生成时刻」快照，存入 messages.confidence，
    避免所有气泡跟随当前会话状态联动变化。
    """
    score = 92  # 基础分（RAG+DeepSeek 通常能给出可靠回复）
    if "高风险" in (risk or ""):
        score -= 18
    elif "中风险" in (risk or ""):
        score -= 8
    negative_emotions = ["愤怒", "激动", "不满"]
    if (emotion or "") in negative_emotions:
        score -= 15
    elif emotion in ("略有不满", "略有焦虑"):
        score -= 5
    if not intent or intent == "待识别":
        score -= 12
    well_covered = ["产品咨询", "物流查询", "优惠咨询", "安装指导", "商品推荐", "退换咨询"]
    if intent and intent in well_covered:
        score += 5
    return max(0, min(100, score))

# ========== 对话流（每个意图是一条完整的对话序列，按顺序发送） ==========
# 每条消息都是客户在收到客服/AI回复后才会发下一条
CONVERSATION_FLOWS = {
    "物流查询": [
        "什么时候能发货啊？昨天就下单了还没动静",
        "好的，那大概几天能到？",
        "行，谢谢",
    ],
    "物流异常": [
        "我的快递到哪了？已经三天了还没更新物流信息",
        "那能帮我催一下快递吗？",
        "好的，麻烦尽快处理",
    ],
    "售后退款诉求": [
        "收到的商品有瑕疵，我要退款！",
        "照片我发了，什么时候能处理？",
        "好的，麻烦快点退款",
    ],
    "退换咨询": [
        "买大了，能换小一号吗？",
        "换货运费谁出？",
        "好的，那我申请换货了",
    ],
    "优惠咨询": [
        "现在有什么优惠活动吗？",
        "满减怎么凑最划算？",
        "好的，那我直接下单了",
    ],
    "安装指导": [
        "这个置物架怎么安装？有视频教程吗？",
        "需要打孔吗？我租的房子不能打孔",
        "好的，我试试看",
    ],
    "商品参数咨询": [
        "这个零食小推车承重多少？放书会不会压弯？",
        "尺寸是多少？我量一下柜子能不能放",
        "好的，那我拍一个",
    ],
    "商品推荐": [
        "新房装修，有什么收纳产品推荐吗？",
        "小户型适合哪款？",
        "行，我看看你推荐的",
    ],
    "投诉升级": [
        "你们客服效率太低了，能不能找个负责人来？",
        "我已经等了很久了，到底有没有人处理？",
        "这个问题不解决我就去投诉了",
    ],
    "差评威胁": [
        "不给我解决我就在评论区曝光",
        "再这样我就要去小红书发帖了",
    ],
    "大额退款": [
        "我买的整套厨具质量太差了，全部都要退",
        "花了这么多钱买到这种质量，必须全额退款加赔偿",
    ],
    "售后投诉": [
        "用了半个月就坏了，是不是质量问题？",
        "这个挂钩根本粘不住，掉了好几次",
    ],
    "商品咨询": [
        "这个零食小推车有几款？有什么区别？",
        "可以叠放吗？会不会不稳？",
        "好的，谢谢",
    ],
}

# 催促消息（客服/AI迟迟不回复时，客户会发催促）
URGE_MESSAGES = [
    "在吗？",
    "麻烦回复一下",
    "人呢？等半天了",
    "客服在吗？急",
]

# 内存中记录每个会话的对话流进度: {session_id: {"intent": "...", "step": 0}}
_session_flow: dict = {}

# 权重设计：约50%可自动回答，50%不可自动回答
# 可自动：物流查询、退换咨询、优惠咨询、安装指导、商品参数咨询、商品推荐、商品咨询
# 不可自动：物流异常、售后退款诉求、投诉升级、差评威胁、大额退款、售后投诉
INTENT_WEIGHTS = {
    "物流查询": 7, "退换咨询": 6, "优惠咨询": 8, "安装指导": 6,
    "商品参数咨询": 8, "商品推荐": 7, "商品咨询": 6,
    "物流异常": 7, "售后退款诉求": 10, "投诉升级": 8,
    "差评威胁": 5, "大额退款": 5, "售后投诉": 8,
}

# 意图对应的情绪/风险（用于降级模式）
INTENT_DEFAULT_EMOTION = {
    "物流查询": ("平稳", "bg-green-50 text-success"),
    "物流异常": ("略有焦虑", "bg-orange-50 text-warning"),
    "售后退款诉求": ("不满", "bg-red-50 text-danger"),
    "退换咨询": ("略有焦虑", "bg-orange-50 text-warning"),
    "优惠咨询": ("积极", "bg-green-50 text-success"),
    "安装指导": ("平稳", "bg-green-50 text-success"),
    "商品参数咨询": ("平稳理性", "bg-green-50 text-success"),
    "商品推荐": ("积极意向", "bg-green-50 text-success"),
    "投诉升级": ("愤怒", "bg-red-50 text-danger"),
    "差评威胁": ("愤怒", "bg-red-50 text-danger"),
    "大额退款": ("激动", "bg-red-50 text-danger"),
    "售后投诉": ("不满", "bg-red-50 text-danger"),
    "商品咨询": ("平稳", "bg-green-50 text-success"),
}

DEFAULT_REPLIES = [
    "亲，您的问题我已经了解了，正在为您查询中，请稍等～",
    "您好，感谢您的反馈，我马上帮您核实处理～",
    "收到您的信息，我已经记录下来了，会尽快为您解决。",
]


def _build_session_context(db: Session, session_id: int, limit: int = 6) -> str:
    """
    构建会话上下文：包含会话关联的订单信息（客户购买的商品）+ 最近 limit 条消息。
    让 AI 知道客户买了什么，回答商品使用/售后问题时可针对性回复，避免反问"您问的是哪款商品"。
    """
    # 会话关联订单（售前下单/售后选单都会创建）
    orders = db.query(Order).filter(Order.session_id == session_id).all()
    order_lines = []
    for o in orders:
        order_lines.append(f"[订单] 商品：{o.name}，状态：{o.status}，金额：{o.price}")

    recent_msgs = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.id.desc())
        .limit(limit)
        .all()
    )
    # 反转为时间正序
    recent_msgs.reverse()

    lines = []
    if order_lines:
        lines.append("【客户本次会话关联的订单】")
        lines.extend(order_lines)
    for m in recent_msgs:
        role = "客户" if m.dir == "right" else ("AI客服" if m.type == "ai" else "人工客服")
        lines.append(f"[{role}] {m.text}")
    return "\n".join(lines)


def _ai_analyze(customer_message: str, session_score: int = 50, session_context: str = "", db=None, session_id: int = None) -> dict:
    """
    调用DeepSeek进行AI分析
    返回统一格式的分析结果
    如果识别到物流意图且有db/session_id，会查询物流系统数据增强AI上下文
    """
    # 第一次调用DeepSeek分析（传入对话历史，让模型理解上下文）
    ds_result = analyze_and_reply(customer_message, session_context=session_context)

    intent = ds_result.get("intent", "商品咨询")

    # 物流意图 → 查询物流系统实时数据，增强上下文后重新生成回复
    if intent in ("物流查询", "物流异常") and db and session_id:
        logistics_data = get_logistics_context(db, session_id)
        if logistics_data:
            # 把物流实时数据拼入上下文，重新调用DeepSeek
            enriched_context = session_context + "\n\n" + logistics_data
            ds_result = analyze_and_reply(customer_message, session_context=enriched_context)

    emotion = ds_result.get("emotion", "平稳")
    risk = ds_result.get("risk", "低风险")
    can_auto = ds_result.get("can_auto_answer", False)
    auto_answer = ds_result.get("auto_answer", "")
    suggested_replies = ds_result.get("suggested_replies", DEFAULT_REPLIES)
    analysis_note = ds_result.get("analysis_note", "")

    # 情绪class映射
    emotion_map = {
        "平稳": ("bg-green-50 text-success", "平稳"),
        "积极": ("bg-green-50 text-success", "积极"),
        "略有不满": ("bg-orange-50 text-warning", "略有不满"),
        "略有焦虑": ("bg-orange-50 text-warning", "略有焦虑"),
        "不满": ("bg-red-50 text-danger", "不满"),
        "愤怒": ("bg-red-50 text-danger", "愤怒"),
        "焦虑": ("bg-orange-50 text-warning", "焦虑"),
        "激动": ("bg-red-50 text-danger", "激动"),
        "满意": ("bg-green-50 text-success", "满意"),
    }
    emotion_class, emotion_label = emotion_map.get(emotion, ("bg-green-50 text-success", emotion))

    # 风险class映射
    risk_map = {
        "低风险": ("✅ 低风险", "bg-gray-100 text-gray-500"),
        "中风险": ("⚠ 中风险", "bg-orange-50 text-warning"),
        "高风险": ("🔴 高风险", "bg-red-50 text-danger"),
    }
    risk_label, risk_class = risk_map.get(risk, ("✅ 低风险", "bg-gray-100 text-gray-500"))

    # 根据风险和情绪调整评分
    score = session_score
    segment = "普通用户"
    value_desc = "🟢 中等价值，AI可处理"

    if "高风险" in risk:
        score = max(25, session_score - 30)
        value_desc = "🔴 高风险，必须立即人工介入"
        segment = "高风险 · 需人工"
    elif "中风险" in risk:
        score = max(40, session_score - 15)
        value_desc = "🟡 中高价值，建议人工跟进"
        segment = "中风险用户"
    elif "积极" in emotion:
        score = min(90, session_score + 10)
        value_desc = "🟡 中高价值，导购促单机会"
        segment = "老客 · 高价值"

    score_color = "bg-warning" if score >= 70 else ("bg-primary" if score >= 50 else "bg-danger")

    # ====== 安全网：强制需人工的场景 ======
    # DeepSeek 有时未严格遵守提示词（如把"找负责人"判成可自动回答），
    # 这里做一道兜底：负面情绪 / 高风险 / 投诉类关键词 → 一律 can_auto_answer=False
    manual_keywords = ['负责人', '效率', '等了', '等很久', '等半天', '半天', '不回复', '没人',
                       '没人理', '人呢', '在吗', '客服在吗', '急', '着急', '催', '怎么还不',
                       '退钱', '赔偿', '曝光', '差评', '投诉', '举报', '小红书', '微博',
                       '太慢', '太差', '什么质量', '失望', '骗子', '忽悠', '神经病']
    negative_emotions = ['愤怒', '激动', '不满', '焦虑']
    need_manual = False
    if emotion in negative_emotions:
        need_manual = True
    if "高风险" in (risk_label or "") or "中风险" in (risk_label or ""):
        need_manual = True
    if any(kw in customer_message for kw in manual_keywords):
        need_manual = True
        # 同时把情绪/风险升级，确保前端标签也显示需人工
        if emotion not in negative_emotions:
            emotion = "不满"
            emotion_class = "bg-red-50 text-danger"
        if "高风险" not in (risk_label or ""):
            risk_label = "🔴 高风险"
            risk_class = "bg-red-50 text-danger"
            segment = "高风险 · 需人工"
            value_desc = "🔴 高风险，必须立即人工介入"

    if need_manual:
        can_auto = False
        auto_answer = ""

    return {
        "intent": intent,
        "emotion": emotion_label if not need_manual else emotion,
        "emotion_class": emotion_class,
        "risk": risk_label,
        "risk_class": risk_class,
        "segment": segment,
        "score": score,
        "score_color": score_color,
        "value_desc": value_desc,
        "can_auto_answer": can_auto,
        "auto_answer": auto_answer,
        "suggested_replies": suggested_replies,
        "analysis_note": analysis_note,
    }


@router.post("/analyze", response_model=AIAnalysisResponse)
def analyze_message(req: AIAnalysisRequest, db: Session = Depends(get_db)):
    result = _ai_analyze(req.latest_message)
    return AIAnalysisResponse(
        intent=result["intent"],
        emotion=result["emotion"],
        emotion_class=result["emotion_class"],
        risk=result["risk"],
        risk_class=result["risk_class"],
        segment=result["segment"],
        score=result["score"],
        value_desc=result["value_desc"],
        suggested_replies=result["suggested_replies"],
    )


@router.get("/suggestions/{session_id}")
def get_suggestions(session_id: int, db: Session = Depends(get_db)):
    replies = (
        db.query(Reply)
        .filter(Reply.session_id == session_id)
        .order_by(Reply.sort_order)
        .all()
    )
    if replies:
        return [{"id": r.id, "text": r.text} for r in replies]
    return [{"id": 0, "text": r} for r in DEFAULT_REPLIES]


@router.post("/regenerate-replies/{session_id}")
def regenerate_replies(session_id: int, db: Session = Depends(get_db)):
    """
    基于最新客户消息，重新调用DeepSeek生成推荐话术。
    用于"查看更多话术"按钮。
    """
    s = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")

    # 取最新一条客户消息
    latest_msg = (
        db.query(Message)
        .filter(Message.session_id == session_id, Message.dir == "right")
        .order_by(Message.id.desc())
        .first()
    )
    if not latest_msg:
        raise HTTPException(status_code=404, detail="No customer message found")

    # 构建对话历史上下文
    session_context = _build_session_context(db, session_id, limit=6)

    # 调用DeepSeek重新生成话术（基于对话历史）
    ds_result = analyze_and_reply(latest_msg.text, session_context=session_context)
    new_replies = ds_result.get("suggested_replies", DEFAULT_REPLIES)

    # 更新数据库中的推荐话术
    db.query(Reply).filter(Reply.session_id == session_id).delete()
    for i, text in enumerate(new_replies):
        db.add(Reply(session_id=session_id, text=text, sort_order=i))
    db.commit()

    return {
        "replies": [{"id": i, "text": t} for i, t in enumerate(new_replies)],
    }


@router.post("/simulate-customer")
def simulate_customer_message(
    session_id: int = Query(...),
    intent: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    模拟客户发送消息（带对话流和等待检测）。
    逻辑：
    1. 如果最后一条是客户消息且客服/AI还没回复 → 30%催促，70%等待
    2. 如果最后一条是AI/客服回复（或没有消息）→ 发对话流的下一条
    """
    s = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")

    # ====== 检查最后一条消息 ======
    last_msg = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.id.desc())
        .first()
    )

    # 如果最后一条是客户消息（dir=right），说明客服/AI还没回复
    if last_msg and last_msg.dir == "right":
        # 30%概率发催促消息，70%返回等待状态
        if random.random() < 0.3:
            customer_msg = random.choice(URGE_MESSAGES)
            is_urge = True
        else:
            return {
                "status": "waiting",
                "message": None,
                "chosen_intent": None,
            }
    else:
        is_urge = False
        # ====== 正常发消息：基于对话流 ======
        flow = _session_flow.get(session_id)

        if intent and intent in CONVERSATION_FLOWS:
            # 前端指定了意图，重新开始该意图的对话流
            chosen_intent = intent
            step = 0
        elif flow and flow["step"] < len(CONVERSATION_FLOWS.get(flow["intent"], [])):
            # 有进行中的对话流，取下一条
            chosen_intent = flow["intent"]
            step = flow["step"]
        else:
            # 对话流已结束或没有，随机开始新的对话流
            intents = list(CONVERSATION_FLOWS.keys())
            weights = [INTENT_WEIGHTS.get(k, 1) for k in intents]
            chosen_intent = random.choices(intents, weights=weights, k=1)[0]
            step = 0

        # 取对话流中的消息
        flow_msgs = CONVERSATION_FLOWS[chosen_intent]
        if step >= len(flow_msgs):
            # 安全兜底：重新开始
            chosen_intent = random.choices(
                list(CONVERSATION_FLOWS.keys()),
                weights=[INTENT_WEIGHTS.get(k, 1) for k in CONVERSATION_FLOWS],
                k=1,
            )[0]
            step = 0
            flow_msgs = CONVERSATION_FLOWS[chosen_intent]

        customer_msg = flow_msgs[step]

        # 更新对话流进度（+1，表示下一条该发了）
        _session_flow[session_id] = {"intent": chosen_intent, "step": step + 1}

    # ====== 保存客户消息 ======
    now = datetime.now()
    db_msg = Message(
        session_id=session_id,
        dir="right",
        text=customer_msg,
        type="user",
    )
    db.add(db_msg)

    # 更新会话预览
    s.preview = customer_msg
    s.time = now.strftime("%H:%M")
    s.updated_at = now
    db.commit()
    db.refresh(db_msg)

    return {
        "status": "ok",
        "message": {
            "id": db_msg.id,
            "dir": db_msg.dir,
            "text": db_msg.text,
            "type": db_msg.type,
            "has_product": False,
            "created_at": db_msg.created_at.isoformat(),
        },
        "chosen_intent": _session_flow.get(session_id, {}).get("intent", ""),
        "is_urge": is_urge,
    }


@router.post("/analyze-customer")
def analyze_customer_message(
    session_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """
    第二步：对最新客户消息进行AI分析（RAG+DeepSeek），返回分析结果和AI自动回答。
    前端在显示客户消息后调用此接口，期间展示AI思考动画。
    """
    s = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")

    # 取最新一条客户消息
    latest_msg = (
        db.query(Message)
        .filter(Message.session_id == session_id, Message.dir == "right")
        .order_by(Message.id.desc())
        .first()
    )
    if not latest_msg:
        raise HTTPException(status_code=404, detail="No customer message found")

    customer_msg = latest_msg.text

    # 构建对话历史上下文（最近6条消息，包含当前这条）
    session_context = _build_session_context(db, session_id, limit=6)

    # DeepSeek AI分析（传入对话历史，识别情绪演变；物流意图会自动查询物流系统）
    analysis = _ai_analyze(customer_msg, s.score, session_context=session_context, db=db, session_id=session_id)

    # 更新会话字段
    s.intent = analysis["intent"]
    s.emotion = analysis["emotion"]
    s.emotion_class = analysis["emotion_class"]
    s.risk = analysis["risk"]
    s.risk_class = analysis["risk_class"]
    s.segment = analysis["segment"]
    s.score = analysis["score"]
    s.score_color = analysis["score_color"]
    s.value_desc = analysis["value_desc"]
    # 需人工处理时自动移到「待接手」标签，AI 可自动回答时移回「AI接待」
    if analysis["can_auto_answer"]:
        s.tab = "ai"
    else:
        s.tab = "wait"

    # 如果AI可以自动回答，保存AI回答消息
    auto_answer_msg = None
    if analysis["can_auto_answer"] and analysis["auto_answer"]:
        # 计算该 AI 回答生成时刻的置信度快照，存入数据库
        conf = _calc_confidence(analysis.get("risk", ""), analysis.get("emotion", ""), analysis.get("intent", ""))
        auto_msg = Message(
            session_id=session_id,
            dir="left",
            text=analysis["auto_answer"],
            type="ai",
            confidence=conf,
        )
        db.add(auto_msg)
        db.flush()
        auto_answer_msg = {
            "id": auto_msg.id,
            "dir": auto_msg.dir,
            "text": auto_msg.text,
            "type": auto_msg.type,
            "has_product": False,
            "created_at": auto_msg.created_at.isoformat(),
            "confidence": conf,
        }

    # 保存推荐话术到Reply表（持久化，切换会话不丢失）
    db.query(Reply).filter(Reply.session_id == session_id).delete()
    for i, text in enumerate(analysis.get("suggested_replies", [])):
        db.add(Reply(session_id=session_id, text=text, sort_order=i))

    db.commit()

    return {
        "auto_answer": auto_answer_msg,
        "analysis": {
            "intent": analysis["intent"],
            "emotion": analysis["emotion"],
            "emotion_class": analysis["emotion_class"],
            "risk": analysis["risk"],
            "risk_class": analysis["risk_class"],
            "segment": analysis["segment"],
            "score": analysis["score"],
            "score_color": analysis["score_color"],
            "value_desc": analysis["value_desc"],
            "can_auto_answer": analysis["can_auto_answer"],
            "auto_answer": analysis["auto_answer"],
            "suggested_replies": analysis["suggested_replies"],
            "analysis_note": analysis.get("analysis_note", ""),
        },
    }


@router.get("/knowledge/search")
def knowledge_search(q: str = Query(...)):
    """搜索知识库（文本拼接）"""
    result = search_knowledge(q)
    return {"query": q, "result": result}


@router.get("/knowledge/search-structured")
def knowledge_search_structured_api(q: str = Query(...), top_k: int = Query(5)):
    """搜索知识库（结构化结果，含得分）"""
    results = search_knowledge_structured(q, top_k=top_k)
    return {"query": q, "results": results, "total": len(results)}


@router.get("/knowledge/stats")
def knowledge_stats():
    """知识库统计信息"""
    return {
        "total_chunks": get_chunk_count(),
        "categories": get_category_counts(),
    }