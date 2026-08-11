"""
模拟快递平台服务 — 生成物流单号、轨迹、状态推进、催件
"""
import random
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import Order, LogisticsTrack

# 快递公司列表
CARRIERS = ["中通快递", "韵达快递", "极兔速递", "圆通速递", "申通快递"]

# 模拟城市路线（发货地 → 中转 → 目的地）
CITY_ROUTES = [
    {"from": "广州", "transit": "上海", "to": "杭州"},
    {"from": "广州", "transit": "北京", "to": "天津"},
    {"from": "广州", "transit": "成都", "to": "重庆"},
    {"from": "广州", "transit": "武汉", "to": "长沙"},
    {"from": "广州", "transit": "郑州", "to": "石家庄"},
    {"from": "义乌", "transit": "上海", "to": "南京"},
    {"from": "义乌", "transit": "北京", "to": "济南"},
]

# 物流状态推进顺序
STATUS_FLOW = ["pending", "shipped", "in_transit", "delivering", "delivered"]

# 状态中文映射
STATUS_LABELS = {
    "pending": "待发货",
    "shipped": "已发货",
    "in_transit": "运输中",
    "delivering": "派送中",
    "delivered": "已签收",
    "exception": "物流异常",
}


def generate_tracking_no(carrier: str) -> str:
    """生成模拟物流单号"""
    prefix_map = {
        "中通快递": "ZT",
        "韵达快递": "YD",
        "极兔速递": "JT",
        "圆通速递": "YT",
        "申通快递": "ST",
    }
    prefix = prefix_map.get(carrier, "ZT")
    num = random.randint(10000000000000, 99999999999999)
    return f"{prefix}{num}"


def get_logistics_context(db: Session, session_id: int) -> str:
    """
    获取会话关联的物流上下文（格式化为文本，供 DeepSeek prompt 使用）。
    让 AI 基于真实物流数据回复，而不是背通用政策。
    """
    orders = db.query(Order).filter(Order.session_id == session_id).all()
    if not orders:
        return ""

    # 优先找有物流单号的订单
    tracked_orders = [o for o in orders if o.tracking_no]
    if not tracked_orders:
        # 没有物流单号 → 待发货
        pending = [o for o in orders if o.logistics_status == "pending"]
        if pending:
            o = pending[0]
            return (
                f"## 物流系统数据（实时查询）\n"
                f"订单号：{o.order_no}\n"
                f"商品：{o.name}\n"
                f"物流状态：待发货（尚未生成物流单号）\n"
                f"注意：该订单还未发货，客户如询问物流单号请告知尚未发货，预计48小时内发货。"
            )
        return ""

    # 取最近一个有物流的订单
    order = tracked_orders[0]
    tracks = (
        db.query(LogisticsTrack)
        .filter(LogisticsTrack.order_id == order.id)
        .order_by(LogisticsTrack.id)
        .all()
    )

    status_label = STATUS_LABELS.get(order.logistics_status, "未知")

    lines = ["## 物流系统数据（实时查询）"]
    lines.append(f"订单号：{order.order_no}")
    lines.append(f"商品：{order.name}")
    lines.append(f"快递公司：{order.carrier}")
    lines.append(f"物流单号：{order.tracking_no}")
    lines.append(f"当前状态：{status_label}")

    if tracks:
        lines.append("物流轨迹：")
        for t in tracks:
            lines.append(f"  [{t.time}] {t.location} - {t.desc}")

    if order.logistics_status == "exception":
        lines.append("⚠ 物流异常：该订单物流信息长时间未更新，需要人工跟进催件。")

    lines.append("请基于以上真实物流数据回复客户，不要编造其他物流信息。")

    return "\n".join(lines)


def advance_logistics(db: Session, order_id: int):
    """推进物流状态到下一阶段，生成新轨迹。返回 (order, message)"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return None, "订单不存在"

    if order.logistics_status == "delivered":
        return order, "已签收，无法继续推进"

    if order.logistics_status == "exception":
        return order, "物流异常，需人工处理"

    # pending → shipped（发货）
    if order.logistics_status == "pending":
        if not order.carrier:
            order.carrier = random.choice(CARRIERS)
        if not order.tracking_no:
            order.tracking_no = generate_tracking_no(order.carrier)
        order.logistics_status = "shipped"
        order.status = "已发货"
        order.status_class = "text-primary"

        route = random.choice(CITY_ROUTES)
        now = datetime.now()
        track = LogisticsTrack(
            order_id=order.id,
            time=now.strftime("%m-%d %H:%M"),
            location=f"{route['from']}分拣中心",
            desc=f"已发货，{order.carrier}已揽收，离开{route['from']}分拣中心",
        )
        db.add(track)
        db.commit()
        return order, "已发货"

    # 推进到下一状态
    current_idx = STATUS_FLOW.index(order.logistics_status)
    next_status = STATUS_FLOW[current_idx + 1]
    order.logistics_status = next_status

    route = random.choice(CITY_ROUTES)
    now = datetime.now()
    time_str = now.strftime("%m-%d %H:%M")

    if next_status == "in_transit":
        track = LogisticsTrack(
            order_id=order.id,
            time=time_str,
            location=f"{route['transit']}转运中心",
            desc=f"到达{route['transit']}转运中心，正在转运中",
        )
    elif next_status == "delivering":
        track = LogisticsTrack(
            order_id=order.id,
            time=time_str,
            location=f"{route['to']}派送网点",
            desc=f"已到达{route['to']}，快递员正在派送中",
        )
    elif next_status == "delivered":
        track = LogisticsTrack(
            order_id=order.id,
            time=time_str,
            location=route["to"],
            desc="已签收，签收人：本人",
        )
        order.status = "已签收"
        order.status_class = "text-success"

    db.add(track)
    db.commit()
    return order, STATUS_LABELS.get(next_status, "已推进")


def urge_logistics(db: Session, tracking_no: str):
    """催件处理。返回 (order, message)"""
    order = db.query(Order).filter(Order.tracking_no == tracking_no).first()
    if not order:
        return None, "物流单号不存在"

    now = datetime.now()
    track = LogisticsTrack(
        order_id=order.id,
        time=now.strftime("%m-%d %H:%M"),
        location="客服系统",
        desc=f"客服已发起催件请求，已联系{order.carrier}加急处理",
    )
    db.add(track)
    db.commit()
    return order, "催件请求已提交"


def set_exception(db: Session, order_id: int, reason: str = "物流信息长时间未更新"):
    """标记物流异常。返回 (order, message)"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return None, "订单不存在"

    order.logistics_status = "exception"
    now = datetime.now()
    track = LogisticsTrack(
        order_id=order.id,
        time=now.strftime("%m-%d %H:%M"),
        location="物流系统",
        desc=f"物流异常：{reason}",
    )
    db.add(track)
    db.commit()
    return order, "已标记异常"
