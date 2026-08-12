from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_name = Column(String(50), nullable=False)
    user_avatar = Column(String(10), default="客")
    user_tag = Column(String(50), default="普通用户")
    user_tag_class = Column(String(50), default="bg-gray-100 text-gray-500")
    source = Column(String(50), nullable=False, default="淘宝")
    platform = Column(String(20), nullable=False, default="taobao")
    user_desc = Column(Text, default="")
    intent = Column(String(100), default="")
    emotion = Column(String(50), default="平稳")
    emotion_class = Column(String(50), default="bg-green-50 text-success")
    risk = Column(String(50), default="✅ 低风险")
    risk_class = Column(String(50), default="bg-gray-100 text-gray-500")
    segment = Column(String(50), default="普通用户")
    score = Column(Integer, default=50)
    score_color = Column(String(20), default="bg-primary")
    value_desc = Column(Text, default="")
    preview = Column(String(200), default="")
    tab = Column(String(20), default="ai")  # ai / wait / all
    status = Column(String(20), default="active")  # active / transferred / closed
    time = Column(String(10), default="")
    tags = Column(JSON, default=list)

    # ===== 营收贡献（基于《客户价值视角的电商客服营收贡献测算模型》） =====
    is_deal = Column(Integer, default=0)          # 售前：是否成交（客户点击"下单"）
    deal_amount = Column(Float, default=0)        # 成交金额
    resolved = Column(Integer, default=0)         # 售后：问题是否已解决（客户点击"已解决"）
    refund_amount = Column(Float, default=0)      # 实际退款金额（已解决=0，即全额挽回）
    base_convert_prob = Column(Float, default=0)  # 基准成交概率 p（规则基准模型）
    base_refund_prob = Column(Float, default=0)   # 基准退款概率 q（规则基准模型）
    contrib_conv = Column(Float, default=0)       # 售前转化价值 Vconv
    contrib_retain = Column(Float, default=0)     # 退款挽回价值 Vretain
    contrib_total = Column(Float, default=0)      # 营收贡献合计
    final_handler = Column(String(10), default="ai")  # ai / manual（会话最终闭环方）

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    messages = relationship("Message", back_populates="session", order_by="Message.created_at")
    orders = relationship("Order", back_populates="session")
    replies = relationship("Reply", back_populates="session")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    dir = Column(String(20), default="left")  # left: AI, right: user, center: system
    text = Column(Text, nullable=False)
    type = Column(String(30), default="ai")  # ai / user / system-msg / insight / insight-risk / insight-success
    has_product = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    # AI 回答生成时刻的置信度快照（仅 type='ai' 有值），避免所有气泡跟随当前会话状态联动
    confidence = Column(Integer, nullable=True)

    session = relationship("Session", back_populates="messages")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    name = Column(String(100), nullable=False)
    status = Column(String(20), default="已签收")
    status_class = Column(String(30), default="text-success")
    order_no = Column(String(50), nullable=False)
    price = Column(String(20), default="¥0.0")
    platform = Column(String(20), default="taobao")
    # 物流相关字段
    tracking_no = Column(String(50), default="")          # 物流单号
    carrier = Column(String(30), default="")              # 快递公司
    logistics_status = Column(String(20), default="pending")  # pending/shipped/in_transit/delivering/delivered/exception
    created_at = Column(DateTime, default=datetime.now)

    session = relationship("Session", back_populates="orders")
    tracks = relationship("LogisticsTrack", back_populates="order", order_by="LogisticsTrack.id")


class LogisticsTrack(Base):
    """物流轨迹表 — 每条记录是一个物流节点"""
    __tablename__ = "logistics_tracks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    time = Column(String(30), nullable=False)    # 如 "07-15 16:20"
    location = Column(String(100), default="")   # 如 "广州分拣中心"
    desc = Column(String(200), nullable=False)   # 如 "已发货，离开广州分拣中心"
    created_at = Column(DateTime, default=datetime.now)

    order = relationship("Order", back_populates="tracks")


class Reply(Base):
    __tablename__ = "replies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    text = Column(Text, nullable=False)
    sort_order = Column(Integer, default=0)

    session = relationship("Session", back_populates="replies")


class CockpitKPI(Base):
    __tablename__ = "cockpit_kpis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    icon = Column(String(10), default="")
    value = Column(String(50), nullable=False)
    unit = Column(String(10), default="")
    trend_text = Column(String(50), default="")
    trend_class = Column(String(50), default="bg-green-50 text-success")
    desc = Column(Text, default="")
    progress = Column(Float, default=0)
    progress_color = Column(String(20), default="bg-success")
    sort_order = Column(Integer, default=0)
    period = Column(String(20), default="30d")


class CockpitTrend(Base):
    __tablename__ = "cockpit_trends"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date_label = Column(String(20), nullable=False)
    session_count = Column(Integer, default=0)
    ai_resolve_rate = Column(Float, default=0)
    period = Column(String(20), default="7d")


class CockpitTopQuestion(Base):
    __tablename__ = "cockpit_top_questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rank = Column(Integer, default=0)
    question = Column(String(200), nullable=False)
    count = Column(Integer, default=0)
    progress = Column(Float, default=0)
    color = Column(String(20), default="bg-danger")


class CockpitAttribution(Base):
    __tablename__ = "cockpit_attributions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(30), nullable=False)
    event_type = Column(String(30), nullable=False)
    event_amount = Column(String(30), default="-")
    attrib_window = Column(String(30), default="")
    confidence = Column(String(50), default="")
    increment_value = Column(String(50), default="")
    group = Column(String(30), default="实验组")


class User(Base):
    """用户表 — 用于登录注册"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    password_hash = Column(String(200), nullable=False)  # salt:hash
    created_at = Column(DateTime, default=datetime.now)