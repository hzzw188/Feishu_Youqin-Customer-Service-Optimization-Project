from fastapi import APIRouter, HTTPException
from typing import List, Optional
from app.schemas import PlatformOrderQuery, PlatformOrderOut, PlatformProductQuery, PlatformProductOut

router = APIRouter(prefix="/api/platforms", tags=["platforms"])

# 模拟四平台订单数据
MOCK_ORDERS = {
    "taobao": [
        {"platform": "淘宝", "order_no": "TB202607140028", "product_name": "卫生间垃圾桶 10L", "price": "¥69.0", "status": "已签收", "logistics": "中通快递 ZT1234567890", "created_at": "2026-07-14"},
        {"platform": "淘宝", "order_no": "TB202607120019", "product_name": "免打孔毛巾架", "price": "¥52.0", "status": "已签收", "logistics": "圆通快递 YT9876543210", "created_at": "2026-07-12"},
        {"platform": "淘宝", "order_no": "TB202607080001", "product_name": "厨房收纳架 三层", "price": "¥128.0", "status": "运输中", "logistics": "韵达快递 YD1122334455", "created_at": "2026-07-08"},
        {"platform": "淘宝", "order_no": "TB202607010022", "product_name": "折叠晾衣架", "price": "¥89.9", "status": "已签收", "logistics": "中通快递 ZT5566778899", "created_at": "2026-07-01"},
    ],
    "douyin": [
        {"platform": "抖音", "order_no": "DY202607100035", "product_name": "厨房置物架套装", "price": "¥89.9", "status": "已签收", "logistics": "极兔快递 JT0011223344", "created_at": "2026-07-10"},
        {"platform": "抖音", "order_no": "DY202606180087", "product_name": "折叠洗衣篮 大号", "price": "¥39.9", "status": "已签收", "logistics": "申通快递 ST9988776655", "created_at": "2026-06-18"},
        {"platform": "抖音", "order_no": "DY202606100011", "product_name": "电动牙刷消毒架", "price": "¥159.0", "status": "已签收", "logistics": "中通快递 ZT4433221100", "created_at": "2026-06-10"},
    ],
    "jd": [
        {"platform": "京东", "order_no": "JD202607150042", "product_name": "防滑衣架 30个装", "price": "¥45.9", "status": "待发货", "logistics": None, "created_at": "2026-07-15"},
        {"platform": "京东", "order_no": "JD202606200015", "product_name": "浴室防滑垫", "price": "¥59.9", "status": "已签收", "logistics": "京东物流 JD5544332211", "created_at": "2026-06-20"},
        {"platform": "京东", "order_no": "JD202606010088", "product_name": "智能感应垃圾桶", "price": "¥199.0", "status": "已签收", "logistics": "京东物流 JD1122334455", "created_at": "2026-06-01"},
    ],
    "pdd": [
        {"platform": "拼多多", "order_no": "PDD202607010006", "product_name": "吸盘挂钩 10个装", "price": "¥19.9", "status": "已签收", "logistics": "极兔快递 JT6677889900", "created_at": "2026-07-01"},
        {"platform": "拼多多", "order_no": "PDD202606100088", "product_name": "折叠收纳盒套装", "price": "¥35.8", "status": "已签收", "logistics": "邮政快递 YZ1231231234", "created_at": "2026-06-10"},
        {"platform": "拼多多", "order_no": "PDD202605150033", "product_name": "冰箱保鲜盒 6件套", "price": "¥29.9", "status": "已签收", "logistics": "韵达快递 YD5566778899", "created_at": "2026-05-15"},
    ],
}

MOCK_PRODUCTS = {
    "taobao": [
        {"platform": "淘宝", "product_id": "TB001", "name": "加厚折叠收纳箱 66L", "price": "¥59.9", "image_url": "", "stock": 1523, "category": "收纳用品"},
        {"platform": "淘宝", "product_id": "TB002", "name": "厨房置物架 三层不锈钢", "price": "¥128.0", "image_url": "", "stock": 892, "category": "厨房收纳"},
        {"platform": "淘宝", "product_id": "TB003", "name": "免打孔毛巾架 60cm", "price": "¥52.0", "image_url": "", "stock": 2100, "category": "卫浴收纳"},
    ],
    "douyin": [
        {"platform": "抖音", "product_id": "DY001", "name": "折叠洗衣篮 大号 45L", "price": "¥39.9", "image_url": "", "stock": 3200, "category": "洗衣用品"},
        {"platform": "抖音", "product_id": "DY002", "name": "厨房置物架套装 5件套", "price": "¥89.9", "image_url": "", "stock": 678, "category": "厨房收纳"},
    ],
    "jd": [
        {"platform": "京东", "product_id": "JD001", "name": "防滑衣架 30个装 不锈钢", "price": "¥45.9", "image_url": "", "stock": 4500, "category": "衣架"},
        {"platform": "京东", "product_id": "JD002", "name": "智能感应垃圾桶 12L", "price": "¥199.0", "image_url": "", "stock": 1200, "category": "垃圾桶"},
    ],
    "pdd": [
        {"platform": "拼多多", "product_id": "PDD001", "name": "吸盘挂钩 10个装 强力无痕", "price": "¥19.9", "image_url": "", "stock": 8900, "category": "挂钩"},
        {"platform": "拼多多", "product_id": "PDD002", "name": "冰箱保鲜盒 6件套 食品级", "price": "¥29.9", "image_url": "", "stock": 5600, "category": "保鲜用品"},
    ],
}


@router.get("/{platform}/orders", response_model=List[PlatformOrderOut])
def get_platform_orders(
    platform: str,
    order_no: Optional[str] = None,
    user_id: Optional[str] = None,
):
    if platform not in MOCK_ORDERS:
        raise HTTPException(status_code=404, detail=f"Platform '{platform}' not supported. Available: taobao, douyin, jd, pdd")

    orders = MOCK_ORDERS[platform]
    if order_no:
        orders = [o for o in orders if o["order_no"] == order_no]

    return [PlatformOrderOut(**o) for o in orders]


@router.get("/{platform}/products", response_model=List[PlatformProductOut])
def get_platform_products(
    platform: str,
    keyword: Optional[str] = None,
    product_id: Optional[str] = None,
):
    if platform not in MOCK_PRODUCTS:
        raise HTTPException(status_code=404, detail=f"Platform '{platform}' not supported")

    products = MOCK_PRODUCTS[platform]
    if product_id:
        products = [p for p in products if p["product_id"] == product_id]
    if keyword:
        products = [p for p in products if keyword in p["name"]]

    return [PlatformProductOut(**p) for p in products]


@router.get("/summary")
def get_platforms_summary():
    """获取各平台汇总数据"""
    return {
        "platforms": [
            {
                "name": "淘宝",
                "key": "taobao",
                "order_count": len(MOCK_ORDERS["taobao"]),
                "product_count": len(MOCK_PRODUCTS["taobao"]),
                "icon": "taobao",
            },
            {
                "name": "抖音",
                "key": "douyin",
                "order_count": len(MOCK_ORDERS["douyin"]),
                "product_count": len(MOCK_PRODUCTS["douyin"]),
                "icon": "douyin",
            },
            {
                "name": "京东",
                "key": "jd",
                "order_count": len(MOCK_ORDERS["jd"]),
                "product_count": len(MOCK_PRODUCTS["jd"]),
                "icon": "jd",
            },
            {
                "name": "拼多多",
                "key": "pdd",
                "order_count": len(MOCK_ORDERS["pdd"]),
                "product_count": len(MOCK_PRODUCTS["pdd"]),
                "icon": "pdd",
            },
        ]
    }