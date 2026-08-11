from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ---------- Session ----------
class TagItem(BaseModel):
    text: str
    cls: str


class SessionBase(BaseModel):
    user_name: str
    source: str = "淘宝"
    platform: str = "taobao"
    preview: str = ""
    tab: str = "ai"


class SessionCreate(SessionBase):
    pass


class SessionOut(SessionBase):
    id: int
    user_avatar: str
    user_tag: str
    user_tag_class: str
    user_desc: str
    intent: str
    emotion: str
    emotion_class: str
    risk: str
    risk_class: str
    segment: str
    score: int
    score_color: str
    value_desc: str
    status: str
    time: str
    tags: List[TagItem] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------- Message ----------
class MessageBase(BaseModel):
    session_id: int
    dir: str = "left"
    text: str
    type: str = "ai"
    has_product: int = 0


class MessageCreate(MessageBase):
    pass


class MessageOut(MessageBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Order ----------
class OrderBase(BaseModel):
    session_id: int
    name: str
    order_no: str
    price: str = "¥0.0"
    status: str = "已签收"
    status_class: str = "text-success"
    platform: str = "taobao"


class OrderOut(OrderBase):
    id: int

    class Config:
        from_attributes = True


# ---------- Reply ----------
class ReplyBase(BaseModel):
    session_id: int
    text: str
    sort_order: int = 0


class ReplyOut(ReplyBase):
    id: int

    class Config:
        from_attributes = True


# ---------- AI Analysis ----------
class AIAnalysisRequest(BaseModel):
    session_id: int
    latest_message: str


class AIAnalysisResponse(BaseModel):
    intent: str
    emotion: str
    emotion_class: str
    risk: str
    risk_class: str
    segment: str
    score: int
    value_desc: str
    suggested_replies: List[str]


# ---------- Cockpit ----------
class CockpitKPIOut(BaseModel):
    id: int
    name: str
    icon: str
    value: str
    unit: str
    trend_text: str
    trend_class: str
    desc: str
    progress: float
    progress_color: str
    sort_order: int

    class Config:
        from_attributes = True


class CockpitTrendOut(BaseModel):
    id: int
    date_label: str
    session_count: int
    ai_resolve_rate: float

    class Config:
        from_attributes = True


class CockpitTopQuestionOut(BaseModel):
    id: int
    rank: int
    question: str
    count: int
    progress: float
    color: str

    class Config:
        from_attributes = True


class CockpitAttributionOut(BaseModel):
    id: int
    session_id: str
    event_type: str
    event_amount: str
    attrib_window: str
    confidence: str
    increment_value: str
    group: str

    class Config:
        from_attributes = True


# ---------- Platform API ----------
class PlatformOrderQuery(BaseModel):
    platform: str  # taobao / douyin / jd / pdd
    order_no: Optional[str] = None
    user_id: Optional[str] = None


class PlatformOrderOut(BaseModel):
    platform: str
    order_no: str
    product_name: str
    price: str
    status: str
    logistics: Optional[str] = None
    created_at: str


class PlatformProductQuery(BaseModel):
    platform: str
    keyword: Optional[str] = None
    product_id: Optional[str] = None


class PlatformProductOut(BaseModel):
    platform: str
    product_id: str
    name: str
    price: str
    image_url: str
    stock: int
    category: str