from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from collections import Counter
from app.database import get_db
from app.models import Session as SessionModel, Message, Order
from app.services.revenue_service import parse_price

router = APIRouter(prefix="/api/cockpit", tags=["cockpit"])


@router.get("/summary")
def get_cockpit_summary(period: str = Query("30d"), db: Session = Depends(get_db)):
    """基于真实会话和消息数据计算驾驶舱指标
    period: 30d / 7d / today / 618
    """
    now = datetime.now()

    # ====== 根据 period 过滤会话 ======
    query = db.query(SessionModel)
    if period == "7d":
        start_date = now - timedelta(days=7)
        query = query.filter(SessionModel.created_at >= start_date)
    elif period == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        query = query.filter(SessionModel.created_at >= start_date)
    elif period == "618":
        # 618大促周期：6.1-6.20
        start_date = now.replace(month=6, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now.replace(month=6, day=20, hour=23, minute=59, second=59)
        query = query.filter(SessionModel.created_at >= start_date, SessionModel.created_at <= end_date)

    sessions = query.all()
    total_sessions = len(sessions)

    if total_sessions == 0:
        return {
            "kpis": [],
            "trends": [],
            "top_questions": [],
            "attributions": [],
            "csat": [],
            "hourly": [],
        }

    # ====== 统计会话分布 ======
    ai_sessions = [s for s in sessions if s.tab == "ai"]
    wait_sessions = [s for s in sessions if s.tab == "wait"]
    closed_sessions = [s for s in sessions if s.status == "closed"]

    ai_count = len(ai_sessions)
    wait_count = len(wait_sessions)
    closed_count = len(closed_sessions)

    # AI自动解决率 = AI接待数 / 总会话数
    ai_resolve_rate = round(ai_count / total_sessions * 100, 1) if total_sessions else 0

    # 转人工率 = 待接手数 / 总会话数
    transfer_rate = round(wait_count / total_sessions * 100, 1) if total_sessions else 0

    # ====== 统计消息（基于当前周期会话） ======
    session_ids = [s.id for s in sessions]
    all_messages = db.query(Message).filter(Message.session_id.in_(session_ids)).all() if session_ids else []
    total_messages = len(all_messages)
    ai_messages = [m for m in all_messages if m.type == "ai"]
    user_messages = [m for m in all_messages if m.type == "user" and m.dir == "right"]
    ai_answer_count = len(ai_messages)

    # AI自动回答率 = AI回答消息数 / 客户消息数
    auto_answer_rate = round(ai_answer_count / len(user_messages) * 100, 1) if user_messages else 0

    # ====== 统计订单（基于当前周期会话） ======
    all_orders = db.query(Order).filter(Order.session_id.in_(session_ids)).all() if session_ids else []
    total_orders = len(all_orders)
    total_order_value = 0
    for o in all_orders:
        total_order_value += parse_price(o.price)

    # ====== 营收贡献（基于《客户价值视角的电商客服营收贡献测算模型》快照汇总） ======
    # 单会话贡献由客户在客户端点击"下单/已解决"时触发计算并写入 Session 快照
    total_contrib = round(sum(s.contrib_total or 0 for s in sessions), 2)
    vconv_total = round(sum(s.contrib_conv or 0 for s in sessions), 2)
    vretain_total = round(sum(s.contrib_retain or 0 for s in sessions), 2)
    contrib_session_count = sum(1 for s in sessions if (s.contrib_total or 0) > 0)
    ai_contrib = round(sum((s.contrib_total or 0) for s in sessions if s.tab == "ai"), 2)
    ai_contrib_count = sum(1 for s in sessions if s.tab == "ai" and (s.contrib_total or 0) > 0)
    ai_contrib_rate = round(ai_contrib / total_contrib * 100, 1) if total_contrib else 0

    # ====== AI vs 人工价值互补结构（饼图数据） ======
    ai_conv = round(sum(s.contrib_conv or 0 for s in sessions if s.tab == "ai"), 2)
    ai_retain = round(sum(s.contrib_retain or 0 for s in sessions if s.tab == "ai"), 2)
    human_conv = round(sum(s.contrib_conv or 0 for s in sessions if s.tab != "ai"), 2)
    human_retain = round(sum(s.contrib_retain or 0 for s in sessions if s.tab != "ai"), 2)
    value_comparison = {
        "ai_total": round(ai_conv + ai_retain, 2),
        "human_total": round(human_conv + human_retain, 2),
        "ai_conv": ai_conv,
        "ai_retain": ai_retain,
        "human_conv": human_conv,
        "human_retain": human_retain,
    }

    # ====== 售前转化价值（替换原满意度分布卡） ======
    conv_sessions = [s for s in sessions if (s.contrib_conv or 0) > 0]
    conv_sessions.sort(key=lambda x: x.contrib_conv or 0, reverse=True)
    conversion_value = {
        "total": vconv_total,
        "session_count": len(conv_sessions),
        "avg_per_session": round(vconv_total / len(conv_sessions), 2) if conv_sessions else 0,
        "top_sessions": [
            {
                "session_id": f"#SES-{s.id:04d}",
                "name": s.user_name or "未知",
                "amount": round(s.contrib_conv or 0, 2),
                "gmvs": round(s.deal_amount or 0, 2),
            }
            for s in conv_sessions[:5]
        ],
    }

    # ====== 统计意图分布（Top问题） ======
    intent_counter = Counter()
    for s in sessions:
        if s.intent:
            intent_counter[s.intent] += 1
    top_intents = intent_counter.most_common(5)
    max_count = top_intents[0][1] if top_intents else 1
    question_colors = ["bg-danger", "bg-warning", "bg-primary", "bg-gray-400", "bg-gray-400"]

    top_questions = [
        {
            "rank": i + 1,
            "question": intent,
            "count": count,
            "progress": round(count / max_count * 100),
            "color": question_colors[i] if i < len(question_colors) else "bg-gray-400",
        }
        for i, (intent, count) in enumerate(top_intents)
    ]

    # ====== 趋势数据（按日期分组） ======
    date_counts = {}
    for s in sessions:
        if s.created_at:
            date_key = s.created_at.strftime("%m-%d")
            if date_key not in date_counts:
                date_counts[date_key] = {"total": 0, "ai": 0}
            date_counts[date_key]["total"] += 1
            if s.tab == "ai":
                date_counts[date_key]["ai"] += 1

    # 取最近7天有数据的日期
    trends = []
    sorted_dates = sorted(date_counts.keys())[-7:]
    for d in sorted_dates:
        info = date_counts[d]
        rate = round(info["ai"] / info["total"] * 100, 1) if info["total"] else 0
        trends.append({
            "date_label": d,
            "session_count": info["total"],
            "ai_resolve_rate": rate,
        })

    # 如果没有趋势数据，用今天的数据
    if not trends:
        today_key = now.strftime("%m-%d")
        trends.append({
            "date_label": today_key,
            "session_count": total_sessions,
            "ai_resolve_rate": ai_resolve_rate,
        })

    # ====== 会话时段分布（按小时统计，0-23点全时段） ======
    # 用 time 字段（工作台显示的 "HH:MM"）统计，和工作台展示一致；
    # time 为空时回退到 created_at
    hour_range = list(range(0, 24))  # 0~23 点
    hour_counts = {h: 0 for h in hour_range}
    for s in sessions:
        hour = None
        if s.time and ":" in s.time:
            try:
                hour = int(s.time.split(":")[0])
            except (ValueError, IndexError):
                pass
        if hour is None and s.created_at:
            hour = s.created_at.hour
        if hour in hour_counts:
            hour_counts[hour] += 1
    # 归一化为百分比（相对于最大值），避免数据少时柱子全为0看不见
    max_hour = max(hour_counts.values()) if hour_counts else 0
    hourly = [
        {
            "hour": str(h),
            "count": hour_counts[h],
            "percent": round(hour_counts[h] / max_hour * 100) if max_hour else 0,
        }
        for h in hour_range
    ]

    # ====== 归因明细（基于客户价值视角模型的真实贡献值） ======
    # 优先展示有营收贡献的会话（按贡献降序），再补充待转化会话，共 10 条
    attributions = []
    contrib_sessions = [s for s in sessions if (s.contrib_total or 0) > 0]
    contrib_sessions.sort(key=lambda x: x.contrib_total or 0, reverse=True)
    pending_sessions = [
        s for s in sessions
        if not (s.contrib_total or 0) and any(o.session_id == s.id for o in all_orders)
    ]
    for s in (contrib_sessions + pending_sessions)[:10]:
        orders = [o for o in all_orders if o.session_id == s.id]
        order_val = sum(parse_price(o.price) for o in orders)
        contrib = s.contrib_total or 0
        vconv = s.contrib_conv or 0
        vretain = s.contrib_retain or 0

        if contrib > 0:
            # 已有真实贡献快照（客户点击下单/已解决触发）
            parts = []
            if vconv:
                parts.append(f"转化+¥{vconv:.1f}")
            if vretain:
                parts.append(f"挽回+¥{vretain:.1f}")
            attributions.append({
                "session_id": f"#SES-{s.id:04d}",
                "event_type": "成交" if s.is_deal else "售后解决",
                "event_amount": f"¥{order_val:.0f}",
                "attrib_window": "会话内",
                "confidence": "高",
                "increment_value": f"+¥{contrib:.1f}（{'、'.join(parts)}）",
                "group": "AI归因" if s.tab == "ai" else "人工归因",
            })
        else:
            # 有订单但未触发贡献计算 → 待转化
            attributions.append({
                "session_id": f"#SES-{s.id:04d}",
                "event_type": "咨询",
                "event_amount": f"¥{order_val:.0f}",
                "attrib_window": "会话内",
                "confidence": "中",
                "increment_value": "待转化",
                "group": "实验组",
            })

    # ====== CSAT 满意度分布（基于真实会话状态推算） ======
    # 非常满意：AI 解决且已归档的会话
    # 满意：AI 解决但活跃的会话
    # 一般：转人工但已归档的会话
    # 不满意：转人工且活跃的会话
    # 非常不满意：意图为投诉/退款/物流异常 的会话
    very_good = sum(1 for s in sessions if s.tab == "ai" and s.status == "closed")
    good = sum(1 for s in sessions if s.tab == "ai" and s.status != "closed")
    normal = sum(1 for s in sessions if s.tab == "wait" and s.status == "closed")
    bad = sum(1 for s in sessions if s.tab == "wait" and s.status != "closed")
    very_bad = sum(1 for s in sessions if s.intent and any(k in s.intent for k in ["投诉", "退款", "物流异常"]))

    # 归一化为百分比
    csat_total_count = very_good + good + normal + bad + very_bad
    if csat_total_count == 0:
        csat_rows = [
            {"label": "非常满意", "value": 0},
            {"label": "满意", "value": 0},
            {"label": "一般", "value": 0},
            {"label": "不满意", "value": 0},
            {"label": "非常不满意", "value": 0},
        ]
    else:
        csat_rows = [
            {"label": "非常满意", "value": round(very_good / csat_total_count * 100)},
            {"label": "满意", "value": round(good / csat_total_count * 100)},
            {"label": "一般", "value": round(normal / csat_total_count * 100)},
            {"label": "不满意", "value": round(bad / csat_total_count * 100)},
            {"label": "非常不满意", "value": round(very_bad / csat_total_count * 100)},
        ]

    # 满意度KPI = (非常满意 + 满意) 占比
    csat_score = round((very_good + good) / total_sessions * 100, 1) if total_sessions else 0

    # ====== KPI（4项，一行展示） ======
    # KPI 描述：只展示有数值的价值项，避免"退款挽回 ¥0"这类冗余
    desc_parts = []
    if vconv_total:
        desc_parts.append(f"售前转化 ¥{vconv_total:.0f}")
    if vretain_total:
        desc_parts.append(f"退款挽回 ¥{vretain_total:.0f}")
    if not desc_parts:
        desc_parts.append("暂无贡献数据，等待客户下单/解决")

    kpis = [
        {
            "id": 1,
            "name": "💰 客服总营收贡献",
            "icon": "💰",
            "value": f"¥{total_contrib:.0f}",
            "unit": "",
            "trend_text": f"贡献会话 {contrib_session_count} 个",
            "trend_class": "bg-green-50 text-success",
            "desc": " · ".join(desc_parts),
            "progress": 100,
            "progress_color": "bg-success",
        },
        {
            "id": 2,
            "name": "🤖 AI贡献值",
            "icon": "🤖",
            "value": f"¥{ai_contrib:.0f}",
            "unit": "",
            "trend_text": f"AI自助会话 {ai_contrib_count} 个",
            "trend_class": "bg-blue-50 text-primary",
            "desc": f"占客服总贡献 {ai_contrib_rate}%",
            "progress": ai_contrib_rate,
            "progress_color": "bg-primary",
        },
        {
            "id": 3,
            "name": "😊 客户满意度",
            "icon": "😊",
            "value": str(csat_score),
            "unit": "%",
            "trend_text": f"非常满意{very_good} · 满意{good} · 一般{normal} · 不满意{bad+very_bad}",
            "trend_class": "bg-green-50 text-success",
            "desc": f"基于 {total_sessions} 个会话的真实解决状态计算",
            "progress": round(csat_score),
            "progress_color": "bg-success",
        },
        {
            "id": 4,
            "name": "⚡ AI响应效率",
            "icon": "⚡",
            "value": str(round(ai_answer_count / max(len(user_messages), 1) * 100, 1)),
            "unit": "%",
            "trend_text": f"自动回答 {ai_answer_count} 条",
            "trend_class": "bg-blue-50 text-primary",
            "desc": f"客户提问 {len(user_messages)} 次，AI回答 {ai_answer_count} 次",
            "progress": round(ai_answer_count / max(len(user_messages), 1) * 100),
            "progress_color": "bg-primary",
        },
    ]

    return {
        "kpis": kpis,
        "trends": trends,
        "top_questions": top_questions,
        "attributions": attributions,
        "csat": csat_rows,
        "hourly": hourly,
        "value_comparison": value_comparison,
        "conversion_value": conversion_value,
    }
