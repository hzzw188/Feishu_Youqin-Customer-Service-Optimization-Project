"""
营收贡献测算服务（基于《客户价值视角的电商客服营收贡献测算模型》：基准差额法）

四类价值：
  Vconv   = (1 - p) × GMV     售前转化价值（p=基准成交概率，仅成交时计入）
  Vretain = (q - r) × GMV     退款挽回价值（q=基准退款概率，r=实际退款比例）
  Vrep    = 0                 复购增量价值（需 90 天消费跟踪，预留）
  Vvoc    = 0                 VOC 信息价值（需工单确认流程，预留）

基准概率用规则权重模型估算（可解释、无需训练数据），
未来接入真实客户行为特征后，只需替换 estimate_* 内部实现，接口不变。
"""
from sqlalchemy.orm import Session

from app.models import Session as SessionModel, Order


def parse_price(price) -> float:
    """解析价格字符串 ¥29.9 → 29.9"""
    try:
        return float(str(price).replace("¥", "").replace(",", "").strip())
    except (ValueError, TypeError):
        return 0.0


def estimate_base_convert_prob(s: SessionModel) -> float:
    """基准成交概率 p：意图/情绪/风险/客群加权，模拟客户的'自然转化'水平"""
    p = 0.5
    tag = s.user_tag or ""
    if "高价值" in tag:
        p += 0.15
    elif "普通" in tag:
        p += 0.05
    if s.intent in ("优惠咨询", "商品推荐"):
        p += 0.15
    elif s.intent in ("产品咨询", "商品咨询"):
        p += 0.05
    emotion = s.emotion or ""
    if "积极" in emotion:
        p += 0.10
    risk = s.risk or ""
    if "高" in risk:
        p -= 0.30
    elif "中" in risk:
        p -= 0.10
    return round(max(0.05, min(0.95, p)), 4)


def estimate_base_refund_prob(s: SessionModel, orders) -> float:
    """基准退款概率 q：物流异常 / 大件组装商品退款风险加权"""
    q = 0.15
    for o in orders:
        if (o.logistics_status or "") == "exception":
            q += 0.30
        if o.name and o.name in ("零食置物架小推车", "YOUQIN抽拉式厨房置物架", "厨房抽拉式置物架"):
            q += 0.15
    return round(min(0.8, q), 4)


def calc_session_contribution(s: SessionModel, db: Session) -> dict:
    """
    计算会话营收贡献并写回快照：
      Vconv   = (1 - p) × GMV    售前转化价值（仅客户点击"下单"成交时计入）
      Vretain = (q - r) × GMV    退款挽回价值（仅售后会话点击"已解决"时计入）
    售前会话没有退款场景，不产生挽回价值。
    """
    orders = db.query(Order).filter(Order.session_id == s.id).all()
    gmv = sum(parse_price(o.price) for o in orders)
    p = estimate_base_convert_prob(s)
    is_pre_sale = "售前" in (s.user_tag or "")

    vconv = round((1 - p) * gmv, 2) if s.is_deal else 0.0

    vretain = 0.0
    q = 0.0
    if not is_pre_sale and s.resolved and gmv:
        q = estimate_base_refund_prob(s, orders)
        r = s.refund_amount / gmv
        vretain = round((q - r) * gmv, 2)

    s.base_convert_prob = p
    s.base_refund_prob = q
    s.contrib_conv = vconv
    s.contrib_retain = vretain
    s.contrib_total = round(vconv + vretain, 2)

    return {
        "gmv": round(gmv, 2),
        "base_convert_prob": p,
        "base_refund_prob": q,
        "conv": vconv,
        "retain": vretain,
        "total": s.contrib_total,
    }