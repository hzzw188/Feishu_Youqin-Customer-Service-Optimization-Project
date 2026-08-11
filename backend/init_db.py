"""
初始化数据库并填充模拟数据
运行: python init_db.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.database import engine, Base, SessionLocal
from app.models import (
    Session, Message, Order, Reply, LogisticsTrack,
    CockpitKPI, CockpitTrend, CockpitTopQuestion, CockpitAttribution,
)
from datetime import datetime, timedelta
import random


def init_db():
    # 创建所有表（保留 cockpit_* 表结构以兼容旧数据，但不再初始化数据）
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # 清空已有数据
    for tbl in [LogisticsTrack, Message, Reply, Order, Session,
                CockpitKPI, CockpitTrend, CockpitTopQuestion, CockpitAttribution]:
        db.query(tbl).delete()
    db.commit()

    # ========== 会话数据 ==========
    session_data = [
        {
            "id": 1, "user_name": "李先生", "user_avatar": "李", "user_tag": "高价值用户",
            "user_tag_class": "bg-orange-50 text-warning", "source": "抖音商城", "platform": "douyin",
            "user_desc": "历史订单：3单 · 客单价：¥128 · 复购用户 · 金卡会员",
            "intent": "商品咨询 + 适配推荐", "emotion": "略有不满 (-0.52)", "emotion_class": "bg-orange-50 text-warning",
            "risk": "⚠ 中高风险", "risk_class": "bg-red-50 text-danger", "segment": "老客 · 高价值",
            "score": 78, "score_color": "bg-warning", "value_desc": "🔴 高价值高风险，建议人工优先跟进",
            "preview": "这个收纳箱承重力怎么样？会不会变形？", "tab": "wait", "time": "13:42",
            "tags": [{"text": "高价值", "cls": "bg-orange-50 text-warning"}, {"text": "售前咨询", "cls": "bg-gray-100 text-gray-500"}],
        },
        {
            "id": 2, "user_name": "张女士", "user_avatar": "张", "user_tag": "售后风险",
            "user_tag_class": "bg-red-50 text-danger", "source": "淘宝天猫", "platform": "taobao",
            "user_desc": "历史订单：1单 · 客单价：¥69 · 新用户",
            "intent": "售后退款诉求", "emotion": "不满愤怒 (-0.81)", "emotion_class": "bg-red-50 text-danger",
            "risk": "🔴 高风险", "risk_class": "bg-red-50 text-danger", "segment": "新客 · 退款风险",
            "score": 42, "score_color": "bg-danger", "value_desc": "🔴 高风险，必须立即人工介入",
            "preview": "收到的垃圾桶有裂痕，怎么处理？", "tab": "wait", "time": "13:38",
            "tags": [{"text": "售后风险", "cls": "bg-red-50 text-danger"}, {"text": "售后", "cls": "bg-gray-100 text-gray-500"}],
        },
        {
            "id": 3, "user_name": "王先生", "user_avatar": "王", "user_tag": "普通用户",
            "user_tag_class": "bg-gray-100 text-gray-500", "source": "京东", "platform": "jd",
            "user_desc": "历史订单：2单 · 客单价：¥95 · 活跃用户",
            "intent": "物流查询", "emotion": "平稳理性", "emotion_class": "bg-green-50 text-success",
            "risk": "✅ 低风险", "risk_class": "bg-gray-100 text-gray-500", "segment": "普通用户",
            "score": 68, "score_color": "bg-primary", "value_desc": "🟡 中等价值，AI可自动处理",
            "preview": "什么时候发货？发什么快递？", "tab": "ai", "time": "13:25",
            "tags": [{"text": "AI已解决", "cls": "bg-green-50 text-success"}],
        },
        {
            "id": 4, "user_name": "赵同学", "user_avatar": "赵", "user_tag": "潜力用户",
            "user_tag_class": "bg-blue-50 text-primary", "source": "拼多多", "platform": "pdd",
            "user_desc": "历史订单：5单 · 客单价：¥45 · 价格敏感型",
            "intent": "优惠咨询", "emotion": "积极意向", "emotion_class": "bg-green-50 text-success",
            "risk": "✅ 低风险", "risk_class": "bg-gray-100 text-gray-500", "segment": "老客 · 价格敏感",
            "score": 75, "score_color": "bg-warning", "value_desc": "🟡 中高价值，导购促单机会",
            "preview": "凑单满减怎么用？能叠加优惠券吗？", "tab": "ai", "time": "13:12",
            "tags": [{"text": "促单中", "cls": "bg-blue-50 text-primary"}],
        },
        {
            "id": 5, "user_name": "刘女士", "user_avatar": "刘", "user_tag": "普通用户",
            "user_tag_class": "bg-gray-100 text-gray-500", "source": "淘宝", "platform": "taobao",
            "user_desc": "历史订单：1单 · 客单价：¥52 · 新用户",
            "intent": "安装指导", "emotion": "平稳", "emotion_class": "bg-green-50 text-success",
            "risk": "✅ 低风险", "risk_class": "bg-gray-100 text-gray-500", "segment": "新客",
            "score": 55, "score_color": "bg-primary", "value_desc": "🟡 中等价值，AI可处理",
            "preview": "安装视频能发我一下吗？", "tab": "ai", "time": "12:58",
            "tags": [{"text": "已结束", "cls": "bg-gray-100 text-gray-500"}],
        },
    ]

    # 生成更多会话 (共8个：5主+2AI+1待接手)
    ai_seeds = [
        {"id": 6, "name": "陈女士", "avatar": "陈", "source": "淘宝商城", "platform": "taobao", "intent": "物流查询", "emotion": "平稳", "risk": "✅ 低风险", "preview": "我的快递到哪了？已经发货三天了还没更新物流", "score": 62, "time": "12:45", "tag": "物流查询", "tag_cls": "bg-gray-100 text-gray-500"},
        {"id": 7, "name": "周先生", "avatar": "周", "source": "京东", "platform": "jd", "intent": "商品参数", "emotion": "平稳", "risk": "✅ 低风险", "preview": "这个收纳盒是什么材质的？有没有味道？", "score": 58, "time": "12:30", "tag": "商品咨询", "tag_cls": "bg-gray-100 text-gray-500"},
    ]

    wait_seeds = [
        {"id": 8, "name": "许先生", "avatar": "许", "source": "京东", "platform": "jd", "intent": "投诉升级", "emotion": "愤怒", "risk": "🔴 高风险", "preview": "等了10分钟还没人回复？你们客服是摆设吗！", "score": 38, "time": "12:55", "tag": "投诉风险", "tag_cls": "bg-red-50 text-danger"},
    ]

    for s in session_data:
        db.add(Session(**s))

    for s in ai_seeds:
        db.add(Session(
            id=s["id"], user_name=s["name"], user_avatar=s["avatar"],
            user_tag=s["tag"], user_tag_class=s["tag_cls"],
            source=s["source"], platform=s["platform"],
            user_desc=f"历史订单：{s['id'] % 5 + 1}单 · 客单价：¥{s['score'] + 20}",
            intent=s["intent"],
            emotion=s["emotion"], emotion_class="bg-orange-50 text-warning" if ("焦虑" in s["emotion"] or "不满" in s["emotion"]) else "bg-green-50 text-success",
            risk=s["risk"], risk_class="bg-orange-50 text-warning" if "中" in s["risk"] else "bg-gray-100 text-gray-500",
            segment="普通用户",
            score=s["score"], score_color="bg-warning" if s["score"] >= 70 else ("bg-primary" if s["score"] >= 50 else "bg-gray-400"),
            value_desc="🟡 中高价值，可引导促单" if s["score"] >= 70 else ("🟢 中等价值，AI可处理" if s["score"] >= 50 else "⚪ 低价值，快速闭环"),
            preview=s["preview"], tab="ai", time=s["time"],
            tags=[{"text": s["tag"], "cls": s["tag_cls"]}],
        ))

    for s in wait_seeds:
        db.add(Session(
            id=s["id"], user_name=s["name"], user_avatar=s["avatar"],
            user_tag=s["tag"], user_tag_class=s["tag_cls"],
            source=s["source"], platform=s["platform"],
            user_desc=f"历史订单：{s['id'] % 3 + 1}单",
            intent=s["intent"],
            emotion=s["emotion"], emotion_class="bg-red-50 text-danger",
            risk=s["risk"], risk_class="bg-red-50 text-danger",
            segment="高风险 · 需人工",
            score=s["score"], score_color="bg-danger",
            value_desc="🔴 高风险，必须立即人工介入",
            preview=s["preview"], tab="wait", time=s["time"],
            tags=[{"text": s["tag"], "cls": s["tag_cls"]}],
        ))

    # ========== 消息数据 ==========
    messages_data = [
        # 会话1
        {"session_id": 1, "dir": "center", "text": "13:40 · 用户进入会话，AI已自动接待", "type": "system-msg"},
        {"session_id": 1, "dir": "right", "text": "你好，我想问下那款折叠收纳箱承重力怎么样？放书会不会变形啊？", "type": "user"},
        {"session_id": 1, "dir": "left", "text": "您好~这款折叠收纳箱采用加厚PP材质，箱体承重可达30kg，放书籍完全没问题，正常使用不会变形哦。\n\n现在下单2件立减15元，叠加满减更划算，需要我给您发一下链接吗？", "type": "ai", "has_product": 1},
        {"session_id": 1, "dir": "right", "text": "那尺寸是多少？衣柜里放得下吗？还有质量不好能退吗？", "type": "user"},
        {"session_id": 1, "dir": "center", "text": "AI智能建议：用户关注尺寸与售后，建议回复尺寸参数+上门取件退换政策，同时推荐同系列组合套餐提升客单价。", "type": "insight"},
        # 会话2
        {"session_id": 2, "dir": "center", "text": "13:38 · 用户进入会话，AI已自动接待", "type": "system-msg"},
        {"session_id": 2, "dir": "right", "text": "我收到的垃圾桶有一道裂痕，你们质量也太差了吧！赶紧给我处理！", "type": "user"},
        {"session_id": 2, "dir": "left", "text": "非常抱歉给您带来不好的体验！我们非常重视产品质量问题。请您方便的时候拍一下裂痕的照片，我立即为您处理——您可以选择免费补发一个新的，或者全额退款。", "type": "ai"},
        {"session_id": 2, "dir": "right", "text": "我要退款！不想要了，太失望了。", "type": "user"},
        {"session_id": 2, "dir": "center", "text": "⚠ AI智能建议：用户情绪激动，检测到强烈退款意图。建议立即转人工处理，并授权客服发放补偿优惠券。", "type": "insight-risk"},
        # 会话3
        {"session_id": 3, "dir": "center", "text": "13:25 · 用户进入会话，AI已自动接待", "type": "system-msg"},
        {"session_id": 3, "dir": "right", "text": "我昨天下的单，什么时候能发货？发什么快递？", "type": "user"},
        {"session_id": 3, "dir": "left", "text": "您好~您的订单#JD202607150042预计今天下午4点前发出，发中通快递，预计3-5天送达。物流单号发出后会同步到订单详情页，请留意查收哦～", "type": "ai"},
        {"session_id": 3, "dir": "right", "text": "好的，谢谢。", "type": "user"},
        {"session_id": 3, "dir": "center", "text": "✅ 会话已由AI自动解决，用户未追问，满意度良好。", "type": "insight-success"},
        # 会话4
        {"session_id": 4, "dir": "center", "text": "13:12 · 用户进入会话，AI已自动接待", "type": "system-msg"},
        {"session_id": 4, "dir": "right", "text": "凑单满减怎么用？能叠加优惠券吗？", "type": "user"},
        {"session_id": 4, "dir": "left", "text": "亲，现在店铺满199减30、满299减60，可以和平台优惠券叠加使用。您的购物车目前¥156，再凑¥43就能触发满199减30，相当于再省30元。推荐您加购这款收纳套装¥49.9，正好凑满哦～", "type": "ai", "has_product": 1},
        # 会话5
        {"session_id": 5, "dir": "center", "text": "12:58 · 用户进入会话", "type": "system-msg"},
        {"session_id": 5, "dir": "right", "text": "刚收到毛巾架，安装视频能发我一下吗？", "type": "user"},
        {"session_id": 5, "dir": "left", "text": "好的，这是免打孔毛巾架的安装教程视频，跟着步骤走5分钟就能装好。如果还有不清楚的随时问我～ [视频链接]", "type": "ai"},
        {"session_id": 5, "dir": "right", "text": "好的谢谢", "type": "user"},
        {"session_id": 5, "dir": "center", "text": "✅ 会话已由AI自动解决并归档。", "type": "insight-success"},
    ]
    for m in messages_data:
        db.add(Message(**m))

    # ========== 订单数据（含物流字段） ==========
    # logistics_status: pending(待发货) / shipped(已发货) / in_transit(运输中) / delivering(派送中) / delivered(已签收)
    orders_data = [
        {"session_id": 1, "name": "厨房置物架套装", "status": "已签收", "status_class": "text-success", "order_no": "DY202607100035", "price": "¥89.9", "platform": "douyin", "tracking_no": "ZT88293475610392", "carrier": "中通快递", "logistics_status": "delivered"},
        {"session_id": 1, "name": "折叠洗衣篮 大号", "status": "已签收", "status_class": "text-success", "order_no": "DY202606180087", "price": "¥39.9", "platform": "douyin", "tracking_no": "YD55610293847561", "carrier": "韵达快递", "logistics_status": "delivered"},
        {"session_id": 1, "name": "纳米无痕挂钩 20个装", "status": "已签收", "status_class": "text-success", "order_no": "DY202605200012", "price": "¥29.9", "platform": "douyin", "tracking_no": "JT77482910375620", "carrier": "极兔速递", "logistics_status": "delivered"},
        {"session_id": 2, "name": "卫生间垃圾桶 10L", "status": "已签收", "status_class": "text-success", "order_no": "TB202607140028", "price": "¥69.0", "platform": "taobao", "tracking_no": "YT99384726105384", "carrier": "圆通速递", "logistics_status": "delivered"},
        {"session_id": 3, "name": "防滑衣架 30个装", "status": "待发货", "status_class": "text-warning", "order_no": "JD202607150042", "price": "¥45.9", "platform": "jd", "tracking_no": "", "carrier": "", "logistics_status": "pending"},
        {"session_id": 3, "name": "浴室防滑垫", "status": "已签收", "status_class": "text-success", "order_no": "JD202606200015", "price": "¥59.9", "platform": "jd", "tracking_no": "ZT66102938475612", "carrier": "中通快递", "logistics_status": "delivered"},
        {"session_id": 4, "name": "吸盘挂钩 10个装", "status": "已签收", "status_class": "text-success", "order_no": "PDD202607010006", "price": "¥19.9", "platform": "pdd", "tracking_no": "ST22839475610394", "carrier": "申通快递", "logistics_status": "delivered"},
        {"session_id": 4, "name": "折叠收纳盒套装", "status": "已签收", "status_class": "text-success", "order_no": "PDD202606100088", "price": "¥35.8", "platform": "pdd", "tracking_no": "JT44561029384756", "carrier": "极兔速递", "logistics_status": "delivered"},
        {"session_id": 4, "name": "冰箱保鲜盒 6件套", "status": "已签收", "status_class": "text-success", "order_no": "PDD202605150033", "price": "¥29.9", "platform": "pdd", "tracking_no": "YT77102938475620", "carrier": "圆通速递", "logistics_status": "delivered"},
        {"session_id": 5, "name": "免打孔毛巾架", "status": "已签收", "status_class": "text-success", "order_no": "TB202607120019", "price": "¥52.0", "platform": "taobao", "tracking_no": "ZT33847561029384", "carrier": "中通快递", "logistics_status": "delivered"},
        # session 6: 陈女士 — 物流查询场景，订单运输中
        {"session_id": 6, "name": "加厚折叠收纳箱 2个装", "status": "已发货", "status_class": "text-primary", "order_no": "TB202607200051", "price": "¥104.0", "platform": "taobao", "tracking_no": "ZT20260720005188", "carrier": "中通快递", "logistics_status": "in_transit"},
        # session 7: 周先生 — 商品咨询，有历史订单已签收
        {"session_id": 7, "name": "桌面收纳盒", "status": "已签收", "status_class": "text-success", "order_no": "JD202607180033", "price": "¥35.9", "platform": "jd", "tracking_no": "YD20260718003355", "carrier": "韵达快递", "logistics_status": "delivered"},
    ]
    for o in orders_data:
        db.add(Order(**o))
    db.flush()  # flush 让 order.id 可用

    # ========== 物流轨迹数据 ==========
    # 为有物流单号的订单生成轨迹
    route_map = [
        {"from": "广州", "transit": "上海", "to": "杭州"},
        {"from": "广州", "transit": "北京", "to": "天津"},
        {"from": "义乌", "transit": "上海", "to": "南京"},
        {"from": "广州", "transit": "武汉", "to": "长沙"},
    ]

    all_orders = db.query(Order).all()
    now = datetime.now()

    for order in all_orders:
        if not order.tracking_no:
            continue  # 待发货订单无轨迹

        route = random.choice(route_map)
        status = order.logistics_status

        # 根据状态生成对应数量的轨迹
        tracks = []
        if status in ("shipped", "in_transit", "delivering", "delivered"):
            t = now - timedelta(days=3)
            tracks.append(("shipped", t, f"{route['from']}分拣中心",
                          f"已发货，{order.carrier}已揽收，离开{route['from']}分拣中心"))
        if status in ("in_transit", "delivering", "delivered"):
            t = now - timedelta(days=2)
            tracks.append(("in_transit", t, f"{route['transit']}转运中心",
                          f"到达{route['transit']}转运中心，正在转运中"))
        if status in ("delivering", "delivered"):
            t = now - timedelta(days=1)
            tracks.append(("delivering", t, f"{route['to']}派送网点",
                          f"已到达{route['to']}，快递员正在派送中"))
        if status == "delivered":
            t = now - timedelta(hours=6)
            tracks.append(("delivered", t, route["to"],
                          "已签收，签收人：本人"))

        for _, t_time, location, desc in tracks:
            db.add(LogisticsTrack(
                order_id=order.id,
                time=t_time.strftime("%m-%d %H:%M"),
                location=location,
                desc=desc,
            ))

    # ========== 推荐话术 ==========
    replies_data = [
        {"session_id": 1, "text": "这款收纳箱采用加厚PP材质，承重可达30kg，放书籍完全不会变形。尺寸45×35×30cm，标准衣柜层板都能放。", "sort_order": 0},
        {"session_id": 1, "text": "现在入手2个组合装更划算，平均每个只要52元，收纳衣物和书籍分类用很方便～", "sort_order": 1},
        {"session_id": 1, "text": "我们支持7天无理由退换，上门取件，质量问题包运费，您完全不用担心。今天下单还送运费险。", "sort_order": 2},
        {"session_id": 2, "text": "非常抱歉给您带来不好的体验！请您拍一下裂痕的照片发给我，我马上帮您处理换新或退款。", "sort_order": 0},
        {"session_id": 2, "text": "我们支持破损包赔，您可以选择重新补发一个新的，或者全额退款，都支持上门取件。", "sort_order": 1},
        {"session_id": 2, "text": "为了表达歉意，这边给您申请一张10元店铺无门槛优惠券，您看可以吗？", "sort_order": 2},
        {"session_id": 3, "text": "您的订单今天下午4点前发出，发中通快递，预计3-5天送达，物流单号稍后同步到订单详情页～", "sort_order": 0},
        {"session_id": 4, "text": "亲，现在店铺满199减30、满299减60，还可以叠加平台优惠券和店铺关注券，凑单下来相当于打了7折！", "sort_order": 0},
        {"session_id": 4, "text": "您现在购物车里的是¥156，再凑¥43就能满199减30，推荐加购这个收纳套装，正好凑满～", "sort_order": 1},
        {"session_id": 5, "text": "安装视频已经发给您了，跟着步骤操作大概5分钟就能装好，免打孔的设计非常简单～", "sort_order": 0},
    ]
    for r in replies_data:
        db.add(Reply(**r))

    # ========== 驾驶舱数据说明 ==========
    # 驾驶舱的 KPI/趋势/高频问题/归因 现已由 cockpit.py 实时基于会话/消息/订单数据计算
    # 不再需要预先初始化 mock 数据，保持数据真实性
    # 4张 cockpit_* 表仍保留在 models.py 中以兼容旧版本，但不再写入数据

    db.commit()
    db.close()
    print("✅ 数据库初始化完成！共创建 8 个会话、消息/订单/物流轨迹/话术数据。")
    print("📦 模拟物流 API 已就绪：/api/logistics/tracking/{tracking_no}")
    print("📊 驾驶舱数据由 cockpit.py 实时计算，无需预先初始化。")


if __name__ == "__main__":
    init_db()