"""
飞书多维表格对接路由
====================
实现真实飞书开放平台 API 对接，支持：
1. 获取 tenant_access_token
2. 自动同步 SQLite 数据到飞书多维表格（6张表：用户/商品/会话/订单/客服动作/结果事件）
3. 一键同步全部数据
4. 查询多维表格记录

飞书多维表格 Base token: S02Lbjo4ca8Cqwse8NKcltTjnLh
表结构：用户表 / 商品表 / 会话表 / 订单表 / 客服动作表 / 结果事件表

配置方式（在 backend 目录创建 .env 文件）：
    FEISHU_APP_ID=cli_xxx
    FEISHU_APP_SECRET=xxx
    FEISHU_APP_TOKEN=S02Lbjo4ca8Cqwse8NKcltTjnLh
"""
import os
import time
import requests
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db, SessionLocal
from app.models import Session as SessionModel, Message, Order, Reply, LogisticsTrack
from app.routers.customer import MOCK_PRODUCTS

router = APIRouter(prefix="/api/feishu", tags=["feishu"])

# ====== 配置（从环境变量读取，未配置则降级为 mock 模式） ======
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
# 使用用户提供的飞书 Base token（6张表已建好）
FEISHU_APP_TOKEN = os.getenv("FEISHU_APP_TOKEN", "S02Lbjo4ca8Cqwse8NKcltTjnLh")

FEISHU_BASE = "https://open.feishu.cn/open-apis"

# 缓存 tenant_access_token（有效期约 2 小时）
_token_cache = {"token": "", "expire_at": 0}

# 飞书 Base 中已有的6张数据表（按真实表名和字段定义）
# type: 1=文本, 2=数字, 3=单选, 4=多选, 7=复选, 11=人员, 13=电话, 15=超链接, 17=附件, 18=关联, 19=查找引用, 20=公式, 21=双向关联, 22=地理位置, 23=群组, 1001=创建时间, 1002=最后更新时间, 1003=创建人, 1005=修改人, 3001=自动编号
TABLE_DEFS = {
    "user": {
        "name": "用户表",
        "fields": [
            {"field_name": "用户ID", "type": 1},
            {"field_name": "平台", "type": 3, "property": {"options": [
                {"name": v} for v in ["淘宝", "天猫", "京东", "拼多多", "苏宁易购", "唯品会", "抖音", "快手", "小红书", "微信"]
            ]}},
            {"field_name": "会员等级", "type": 3, "property": {"options": [
                {"name": v} for v in ["普通", "银卡", "金卡", "白金", "钻石"]
            ]}},
            {"field_name": "购买偏好", "type": 4, "property": {"options": [
                {"name": v} for v in ["价格敏感", "品质导向", "品牌导向", "促销驱动", "新品尝鲜", "其他"]
            ]}},
            {"field_name": "风险标签", "type": 4, "property": {"options": [
                {"name": v} for v in ["高退款风险", "高投诉风险", "疑似欺诈", "高频咨询", "其他"]
            ]}},
            {"field_name": "累计消费", "type": 3, "property": {"options": [
                {"name": v} for v in ["1k以下", "1k-1w", "1w以上"]
            ]}},
        ],
    },
    "product": {
        "name": "商品表",
        "fields": [
            {"field_name": "商品名称", "type": 1},
            {"field_name": "SKU", "type": 1},
            {"field_name": "库存", "type": 2},
            {"field_name": "规格", "type": 1},
            {"field_name": "尺寸", "type": 1},
            {"field_name": "材质", "type": 1},
            {"field_name": "适用场景", "type": 4, "property": {"options": [
                {"name": v} for v in ["日常", "送礼", "户外", "办公", "居家", "旅行", "其他"]
            ]}},
        ],
    },
    "session": {
        "name": "会话表",
        "fields": [
            {"field_name": "会话ID", "type": 1},
            {"field_name": "用户ID", "type": 1},
            {"field_name": "问题文本", "type": 1},
            {"field_name": "会话预览", "type": 1},
            {"field_name": "处理路径", "type": 3, "property": {"options": [
                {"name": v} for v in ["AI", "人工", "AI转人工", "其他"]
            ]}},
            {"field_name": "价值描述", "type": 1},
            {"field_name": "价值评分", "type": 2},
            {"field_name": "创建时间", "type": 1},
            {"field_name": "意图", "type": 3, "property": {"options": [
                {"name": v} for v in ["咨询", "投诉", "退款", "物流", "售后", "其他"]
            ]}},
            {"field_name": "情绪", "type": 3, "property": {"options": [
                {"name": v} for v in ["中性", "满意", "不满", "愤怒", "焦虑", "其他"]
            ]}},
        ],
    },
    "order": {
        "name": "订单表",
        "fields": [
            {"field_name": "订单ID", "type": 1},
            {"field_name": "用户ID", "type": 1},
            {"field_name": "会话ID", "type": 1},
            {"field_name": "商品名称", "type": 1},
            {"field_name": "SKU", "type": 1},
            {"field_name": "订单金额", "type": 2},
            {"field_name": "状态", "type": 3, "property": {"options": [
                {"name": v} for v in ["待支付", "已支付", "已发货", "已完成", "已取消", "退款中", "已退款"]
            ]}},
            {"field_name": "物流", "type": 3, "property": {"options": [
                {"name": v} for v in ["未发货", "运输中", "已签收", "异常", "其他"]
            ]}},
            {"field_name": "退款状态", "type": 3, "property": {"options": [
                {"name": v} for v in ["无", "申请中", "退款中", "已通过", "已拒绝", "已退款"]
            ]}},
        ],
    },
    "action": {
        "name": "客服动作表",
        "fields": [
            {"field_name": "会话ID", "type": 1},
            {"field_name": "用户ID", "type": 1},
            {"field_name": "AI回复", "type": 1},
            {"field_name": "转人工原因", "type": 3, "property": {"options": [
                {"name": v} for v in ["复杂问题", "情绪问题", "退款纠纷", "物流异常", "投诉", "其他"]
            ]}},
            {"field_name": "人工处理结果", "type": 3, "property": {"options": [
                {"name": v} for v in ["已解决", "未解决", "需跟进", "升级处理", "其他"]
            ]}},
            {"field_name": "优惠动作", "type": 3, "property": {"options": [
                {"name": v} for v in ["未使用", "已发放", "已使用", "拒绝", "其他"]
            ]}},
        ],
    },
    "event": {
        "name": "结果事件表",
        "fields": [
            {"field_name": "用户ID", "type": 1},
            {"field_name": "会话ID", "type": 1},
            {"field_name": "事件类型", "type": 3, "property": {"options": [
                {"name": v} for v in ["下单", "加购", "取消退款", "投诉", "复购"]
            ]}},
            {"field_name": "事件时间", "type": 1},
        ],
    },
    "message": {
        "name": "聊天消息表",
        "fields": [
            {"field_name": "消息ID", "type": 1},
            {"field_name": "会话ID", "type": 1},
            {"field_name": "用户ID", "type": 1},
            {"field_name": "消息方向", "type": 3, "property": {"options": [
                {"name": v} for v in ["客户", "AI", "客服", "系统"]
            ]}},
            {"field_name": "消息内容", "type": 1},
            {"field_name": "消息类型", "type": 3, "property": {"options": [
                {"name": v} for v in ["AI回答", "客户提问", "客服回复", "系统提示"]
            ]}},
            {"field_name": "发送时间", "type": 1},
        ],
    },
    "kpi": {
        "name": "KPI驾驶舱指标表",
        "fields": [
            {"field_name": "指标名称", "type": 1},
            {"field_name": "指标数值", "type": 1},
            {"field_name": "单位", "type": 1},
            {"field_name": "趋势说明", "type": 1},
            {"field_name": "详细描述", "type": 1},
            {"field_name": "进度", "type": 2},
            {"field_name": "同步时间", "type": 1},
        ],
    },
}

# 缓存表ID（首次创建/查询后保存）
_table_id_cache = {}


def is_configured() -> bool:
    """是否已配置飞书凭证"""
    return bool(FEISHU_APP_ID and FEISHU_APP_SECRET)


def _get_tenant_token() -> str:
    """获取 tenant_access_token（带缓存）"""
    if not is_configured():
        return ""

    # 缓存有效则直接返回
    if _token_cache["token"] and time.time() < _token_cache["expire_at"]:
        return _token_cache["token"]

    url = f"{FEISHU_BASE}/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET,
    }, timeout=10)
    data = resp.json()
    if data.get("code") != 0:
        raise Exception(f"获取飞书token失败: {data.get('msg')}")

    token = data["tenant_access_token"]
    _token_cache["token"] = token
    _token_cache["expire_at"] = time.time() + data.get("expire", 7200) - 300  # 提前5分钟过期
    return token


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_tenant_token()}",
        "Content-Type": "application/json",
    }


def _ensure_app_token() -> str:
    """确保有 app_token；若未配置则创建一个新的多维表格"""
    if FEISHU_APP_TOKEN:
        return FEISHU_APP_TOKEN

    # 创建新的多维表格
    url = f"{FEISHU_BASE}/bitable/v1/apps"
    resp = requests.post(url, headers=_headers(), json={
        "name": "优勤智服客服数据",
        "folder_token": "",
    }, timeout=10)
    data = resp.json()
    if data.get("code") != 0:
        raise Exception(f"创建多维表格失败: {data.get('msg')}")
    new_token = data["data"]["app"]["app_token"]
    # 提示用户保存到环境变量
    print(f"⚠️ 已创建多维表格 app_token={new_token}，请保存到 .env 文件中的 FEISHU_APP_TOKEN")
    return new_token


def _ensure_table(app_token: str, table_key: str) -> str:
    """确保数据表存在且字段完整，返回 table_id"""
    if table_key in _table_id_cache:
        # 表已缓存：sync 高频调用时跳过字段检查（字段在 rebuild 时已建好），
        # 避免每次同步都发 HTTP 请求查字段，显著降低延迟
        return _table_id_cache[table_key]

    table_def = TABLE_DEFS[table_key]

    # 先尝试查询已有表（按名字匹配）
    url = f"{FEISHU_BASE}/bitable/v1/apps/{app_token}/tables"
    resp = requests.get(url, headers=_headers(), timeout=10)
    data = resp.json()
    if data.get("code") == 0:
        for t in data.get("data", {}).get("items", []):
            if t.get("name") == table_def["name"]:
                tid = t["table_id"]
                _table_id_cache[table_key] = tid
                # 首次发现表时补齐缺失字段
                _ensure_fields(app_token, tid, table_key)
                return tid

    # 不存在则创建
    url = f"{FEISHU_BASE}/bitable/v1/apps/{app_token}/tables"
    resp = requests.post(url, headers=_headers(), json={
        "table": {
            "name": table_def["name"],
            "default_view_name": "默认视图",
            "fields": table_def["fields"],
        },
    }, timeout=10)
    data = resp.json()
    if data.get("code") != 0:
        raise Exception(f"创建数据表 {table_def['name']} 失败: {data.get('msg')}")

    table_id = data["data"]["table_id"]
    _table_id_cache[table_key] = table_id
    return table_id


def _batch_create_records(app_token: str, table_id: str, records: list) -> int:
    """批量新增记录（每批最多 500 条）"""
    if not records:
        return 0
    url = f"{FEISHU_BASE}/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create"
    total = 0
    for i in range(0, len(records), 500):
        batch = records[i:i+500]
        resp = requests.post(url, headers=_headers(), json={"records": batch}, timeout=30)
        data = resp.json()
        if data.get("code") != 0:
            raise Exception(f"批量写入失败: {data.get('msg')}")
        total += len(data.get("data", {}).get("records", []))
    return total


def _clear_table(app_token: str, table_id: str) -> int:
    """清空数据表所有记录（同步前调用，避免重复累积）"""
    deleted = 0
    while True:
        # 查询一页记录
        url = f"{FEISHU_BASE}/bitable/v1/apps/{app_token}/tables/{table_id}/records"
        resp = requests.get(url, headers=_headers(), params={"page_size": 500}, timeout=10)
        data = resp.json()
        if data.get("code") != 0:
            break
        items = data.get("data", {}).get("items", [])
        if not items:
            break
        # 批量删除
        record_ids = [it["record_id"] for it in items if it.get("record_id")]
        if not record_ids:
            break
        del_url = f"{FEISHU_BASE}/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_delete"
        del_resp = requests.post(del_url, headers=_headers(), json={"records": record_ids}, timeout=30)
        del_data = del_resp.json()
        if del_data.get("code") != 0:
            break
        deleted += len(record_ids)
        if len(items) < 500:
            break
    return deleted


def _delete_all_tables(app_token: str) -> dict:
    """删除多维表格中的所有数据表（用于重建前清理）
    飞书限制：至少保留1张表。策略：先把旧表改名为 待删除_xxx，创建新表后再删除改名表。
    若直接删除失败，记录失败原因。
    """
    url = f"{FEISHU_BASE}/bitable/v1/apps/{app_token}/tables"
    resp = requests.get(url, headers=_headers(), timeout=10)
    data = resp.json()
    if data.get("code") != 0:
        raise Exception(f"查询数据表列表失败: {data.get('msg')}")

    old_tables = data.get("data", {}).get("items", [])
    deleted = []
    failed = []
    for t in old_tables:
        tid = t.get("table_id")
        tname = t.get("name", "")
        if not tid:
            continue
        del_url = f"{FEISHU_BASE}/bitable/v1/apps/{app_token}/tables/{tid}"
        del_resp = requests.delete(del_url, headers=_headers(), timeout=10)
        del_data = del_resp.json()
        if del_data.get("code") == 0:
            deleted.append({"table_id": tid, "name": tname})
        else:
            failed.append({"table_id": tid, "name": tname, "reason": del_data.get("msg", "未知")})

    # 清空本地缓存
    _table_id_cache.clear()
    return {"deleted": deleted, "count": len(deleted), "failed": failed}


def _create_table_with_fields(app_token: str, table_key: str) -> str:
    """直接创建数据表（带完整字段），不查询已有表"""
    table_def = TABLE_DEFS[table_key]
    url = f"{FEISHU_BASE}/bitable/v1/apps/{app_token}/tables"
    resp = requests.post(url, headers=_headers(), json={
        "table": {
            "name": table_def["name"],
            "default_view_name": "默认视图",
            "fields": table_def["fields"],
        },
    }, timeout=10)
    data = resp.json()
    if data.get("code") != 0:
        raise Exception(f"创建数据表 {table_def['name']} 失败: {data.get('msg')}")

    table_id = data["data"]["table_id"]
    _table_id_cache[table_key] = table_id
    return table_id


def _ensure_fields(app_token: str, table_id: str, table_key: str) -> dict:
    """检测表字段并补齐缺失字段（不删表，直接新增字段）"""
    table_def = TABLE_DEFS[table_key]
    # 查询现有字段
    url = f"{FEISHU_BASE}/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
    resp = requests.get(url, headers=_headers(), timeout=10)
    data = resp.json()
    if data.get("code") != 0:
        return {"added": [], "error": data.get("msg")}

    existing_names = {f.get("field_name") for f in data.get("data", {}).get("items", [])}
    added = []
    for fdef in table_def["fields"]:
        if fdef["field_name"] not in existing_names:
            # 新增字段
            add_url = f"{FEISHU_BASE}/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
            add_resp = requests.post(add_url, headers=_headers(), json={
                "field_name": fdef["field_name"],
                "type": fdef["type"],
                "property": fdef.get("property", {}),
            }, timeout=10)
            add_data = add_resp.json()
            if add_data.get("code") == 0:
                added.append(fdef["field_name"])
    return {"added": added}


def _rename_table(app_token: str, table_id: str, new_name: str) -> bool:
    """重命名数据表"""
    url = f"{FEISHU_BASE}/bitable/v1/apps/{app_token}/tables/{table_id}"
    resp = requests.patch(url, headers=_headers(), json={"name": new_name}, timeout=10)
    data = resp.json()
    return data.get("code") == 0


# ========== API 接口 ==========

@router.get("/status")
def feishu_status():
    """飞书对接状态"""
    return {
        "configured": is_configured(),
        "app_id": FEISHU_APP_ID[:8] + "***" if FEISHU_APP_ID else "",
        "app_token": FEISHU_APP_TOKEN if is_configured() else "",
        "app_token_configured": bool(FEISHU_APP_TOKEN),
        "mode": "real" if is_configured() else "mock",
        "message": "已配置飞书凭证，可真实同步" if is_configured() else "未配置 FEISHU_APP_ID/FEISHU_APP_SECRET，当前为 mock 模式。请在 backend/.env 中配置后启用真实对接",
    }


@router.get("/bitable/tables")
def list_bitable_tables():
    """获取多维表格列表（未配置时返回结构定义）"""
    if not is_configured():
        return {
            "mode": "mock",
            "tables": [
                {
                    "table_id": k,
                    "name": v["name"],
                    "fields": [f["field_name"] for f in v["fields"]],
                    "record_count": 0,
                }
                for k, v in TABLE_DEFS.items()
            ],
        }

    # 真实查询
    try:
        app_token = _ensure_app_token()
        url = f"{FEISHU_BASE}/bitable/v1/apps/{app_token}/tables"
        resp = requests.get(url, headers=_headers(), timeout=10)
        data = resp.json()
        if data.get("code") != 0:
            return {"error": data.get("msg")}

        tables = []
        for t in data.get("data", {}).get("items", []):
            tables.append({
                "table_id": t["table_id"],
                "name": t["name"],
                "fields": [f["field_name"] for f in t.get("fields", [])],
                "record_count": t.get("record_count", 0),
            })
        return {"mode": "real", "app_token": app_token, "tables": tables}
    except Exception as e:
        return {"error": str(e)}


@router.post("/bitable/init")
def init_bitable():
    """初始化飞书多维表格：创建3张数据表（首次使用时调用）"""
    if not is_configured():
        return {"success": False, "message": "未配置飞书凭证，无法初始化。请在 backend/.env 中配置 FEISHU_APP_ID 和 FEISHU_APP_SECRET"}

    try:
        app_token = _ensure_app_token()
        created = []
        for table_key in TABLE_DEFS:
            table_id = _ensure_table(app_token, table_key)
            created.append({
                "key": table_key,
                "name": TABLE_DEFS[table_key]["name"],
                "table_id": table_id,
            })
        return {
            "success": True,
            "app_token": app_token,
            "tables": created,
            "message": "飞书多维表格初始化完成，6张数据表已就绪",
        }
    except Exception as e:
        return {"success": False, "message": f"初始化失败: {str(e)}"}


@router.get("/bitable/init-browser")
def init_bitable_browser():
    """浏览器一键创建多维表格（GET 方式，方便用户在浏览器直接访问）
    访问 http://localhost:8000/api/feishu/bitable/init-browser 即可
    """
    return init_bitable()


@router.post("/bitable/delete-tables")
def delete_tables():
    """删除飞书多维表格中的所有数据表（清空旧结构，便于重建）"""
    if not is_configured():
        return {"success": False, "message": "未配置飞书凭证"}
    try:
        app_token = _ensure_app_token()
        result = _delete_all_tables(app_token)
        return {"success": True, **result, "message": f"已删除 {result['count']} 张数据表"}
    except Exception as e:
        return {"success": False, "message": f"删除失败: {str(e)}"}


@router.get("/bitable/delete-tables-browser")
def delete_tables_browser():
    """浏览器一键删除所有数据表（GET 方式）"""
    return delete_tables()


@router.post("/bitable/rebuild")
def rebuild_tables():
    """重建所有数据表：先改名旧表为 待删除_xxx，创建新表，再删除改名表（绕过飞书至少保留1张表限制）"""
    if not is_configured():
        return {"success": False, "message": "未配置飞书凭证"}
    try:
        app_token = _ensure_app_token()

        # 1. 查询所有旧表并改名为 待删除_xxx
        list_url = f"{FEISHU_BASE}/bitable/v1/apps/{app_token}/tables"
        list_resp = requests.get(list_url, headers=_headers(), timeout=10)
        list_data = list_resp.json()
        renamed = []
        if list_data.get("code") == 0:
            for t in list_data.get("data", {}).get("items", []):
                tid = t.get("table_id")
                tname = t.get("name", "")
                if tid and _rename_table(app_token, tid, f"待删除_{tname}"):
                    renamed.append({"table_id": tid, "old_name": tname})

        # 2. 清空本地缓存
        _table_id_cache.clear()

        # 3. 按新字段定义创建所有新表
        created = []
        for table_key in TABLE_DEFS:
            try:
                table_id = _create_table_with_fields(app_token, table_key)
                created.append({
                    "key": table_key,
                    "name": TABLE_DEFS[table_key]["name"],
                    "table_id": table_id,
                    "fields": [f["field_name"] for f in TABLE_DEFS[table_key]["fields"]],
                })
            except Exception as ce:
                created.append({"key": table_key, "error": str(ce)})

        # 4. 删除所有改名后的旧表
        deleted = []
        for r in renamed:
            del_url = f"{FEISHU_BASE}/bitable/v1/apps/{app_token}/tables/{r['table_id']}"
            del_resp = requests.delete(del_url, headers=_headers(), timeout=10)
            if del_resp.json().get("code") == 0:
                deleted.append(r["old_name"])

        return {
            "success": True,
            "renamed_count": len(renamed),
            "deleted_count": len(deleted),
            "created_count": len([c for c in created if "error" not in c]),
            "tables": created,
            "message": f"已改名 {len(renamed)} 张旧表，创建 {len([c for c in created if 'error' not in c])} 张新表，删除 {len(deleted)} 张旧表（共8张表：用户/商品/会话/订单/客服动作/结果事件/聊天消息/KPI指标）",
        }
    except Exception as e:
        return {"success": False, "message": f"重建失败: {str(e)}"}


@router.get("/bitable/rebuild-browser")
def rebuild_tables_browser():
    """浏览器一键重建所有数据表（GET 方式）"""
    return rebuild_tables()


@router.get("/bitable/sync-all-browser")
def sync_all_browser(db: Session = Depends(get_db)):
    """浏览器一键同步全部数据（GET 方式）"""
    return sync_all(db)


# ========== 6张表同步函数 ==========

def _map_level(score: int) -> str:
    """评分映射会员等级"""
    if score >= 80:
        return "钻石"
    elif score >= 65:
        return "白金"
    elif score >= 50:
        return "金卡"
    elif score >= 35:
        return "银卡"
    return "普通"


def _map_consume(orders: list) -> str:
    """根据订单金额映射累计消费"""
    total = 0
    for o in orders:
        try:
            total += float(str(o.price).replace("¥", "").replace(",", "").strip())
        except (ValueError, TypeError):
            pass
    if total >= 10000:
        return "1w以上"
    elif total >= 1000:
        return "1k-1w"
    return "1k以下"


@router.post("/bitable/sync-users")
def sync_users(db: Session = Depends(get_db)):
    """同步用户数据到飞书【用户表】"""
    if not is_configured():
        return _mock_sync("用户表", 0)
    try:
        app_token = _ensure_app_token()
        table_id = _ensure_table(app_token, "user")

        # 按 user_name+platform 去重聚合
        user_map = {}
        for s in db.query(SessionModel).all():
            key = (s.user_name, s.source)
            if key not in user_map:
                user_map[key] = {"score": s.score or 50, "risk": s.risk or "", "session_ids": []}
            user_map[key]["session_ids"].append(s.id)
            user_map[key]["score"] = max(user_map[key]["score"], s.score or 50)

        records = []
        for (name, platform), info in user_map.items():
            # 查该用户的订单
            user_orders = (
                db.query(Order)
                .join(SessionModel, Order.session_id == SessionModel.id)
                .filter(SessionModel.user_name == name, SessionModel.source == platform)
                .all()
            )
            records.append({
                "fields": {
                    "用户ID": name,
                    "平台": platform,
                    "会员等级": _map_level(info["score"]),
                    "累计消费": _map_consume(user_orders),
                }
            })

        _clear_table(app_token, table_id)
        count = _batch_create_records(app_token, table_id, records)
        return {"success": True, "table": "用户表", "synced_count": count, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        return {"success": False, "message": f"同步失败: {str(e)}"}


@router.post("/bitable/sync-products")
def sync_products(db: Session = Depends(get_db)):
    """同步商品数据到飞书【商品表】"""
    if not is_configured():
        return _mock_sync("商品表", 0)
    try:
        app_token = _ensure_app_token()
        table_id = _ensure_table(app_token, "product")

        records = []
        for p in MOCK_PRODUCTS:
            records.append({
                "fields": {
                    "商品名称": p.get("name", ""),
                    "SKU": p.get("sku", ""),
                    "库存": p.get("stock", 0),
                    "规格": p.get("spec", ""),
                    "尺寸": p.get("size", ""),
                    "材质": p.get("material", ""),
                    "适用场景": p.get("scenes", []),
                }
            })

        _clear_table(app_token, table_id)
        count = _batch_create_records(app_token, table_id, records)
        return {"success": True, "table": "商品表", "synced_count": count, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        return {"success": False, "message": f"同步失败: {str(e)}"}


def _map_path(tab: str, status: str) -> str:
    """处理路径映射"""
    if status == "closed":
        return "其他"
    if tab == "wait":
        return "AI转人工"
    if tab == "ai":
        return "AI"
    return "人工"


def _map_intent(intent: str) -> str:
    """意图映射到飞书选项"""
    if not intent:
        return "其他"
    mapping = {"咨询": "咨询", "商品": "咨询", "参数": "咨询", "推荐": "咨询",
               "投诉": "投诉", "退款": "退款", "退货": "退款", "物流": "物流",
               "发货": "物流", "售后": "售后", "维修": "售后"}
    for k, v in mapping.items():
        if k in intent:
            return v
    return "其他"


def _map_emotion(emotion: str) -> str:
    """情绪映射到飞书选项"""
    if not emotion:
        return "中性"
    if "愤怒" in emotion or "生气" in emotion:
        return "愤怒"
    if "不满" in emotion or "抱怨" in emotion:
        return "不满"
    if "焦虑" in emotion or "着急" in emotion:
        return "焦虑"
    if "满意" in emotion or "开心" in emotion:
        return "满意"
    return "中性"


@router.post("/bitable/sync-sessions")
def sync_sessions(db: Session = Depends(get_db)):
    """同步会话数据到飞书【会话表】"""
    if not is_configured():
        return _mock_sync("会话表", 0)
    try:
        app_token = _ensure_app_token()
        table_id = _ensure_table(app_token, "session")

        sessions = db.query(SessionModel).all()
        records = []
        for s in sessions:
            # 汇总该会话所有客户发送的消息（dir='right'）作为问题文本
            customer_msgs = (
                db.query(Message)
                .filter(Message.session_id == s.id, Message.dir == "right")
                .order_by(Message.created_at)
                .all()
            )
            question_text = "\n".join(m.text for m in customer_msgs) if customer_msgs else (s.preview or "")

            records.append({
                "fields": {
                    "会话ID": str(s.id),
                    "用户ID": s.user_name,
                    "问题文本": question_text,
                    "会话预览": s.preview or "",
                    "处理路径": _map_path(s.tab or "ai", s.status or "active"),
                    "价值描述": s.value_desc or "",
                    "价值评分": s.score or 0,
                    "创建时间": s.created_at.strftime("%Y-%m-%d %H:%M:%S") if s.created_at else "",
                    "意图": _map_intent(s.intent or ""),
                    "情绪": _map_emotion(s.emotion or ""),
                }
            })

        _clear_table(app_token, table_id)
        count = _batch_create_records(app_token, table_id, records)
        return {"success": True, "table": "会话表", "synced_count": count, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        return {"success": False, "message": f"同步失败: {str(e)}"}


def _map_order_status(status: str) -> str:
    """订单状态映射"""
    if not status:
        return "已支付"
    mapping = {"待支付": "待支付", "已支付": "已支付", "已发货": "已发货",
               "已完成": "已完成", "已签收": "已完成", "已取消": "已取消",
               "退款中": "退款中", "已退款": "已退款", "咨询中": "已支付"}
    return mapping.get(status, "已支付")


def _map_logistics(logistics_status: str) -> str:
    """物流状态映射"""
    mapping = {"pending": "未发货", "shipped": "运输中", "in_transit": "运输中",
               "delivering": "运输中", "delivered": "已签收", "exception": "异常"}
    return mapping.get(logistics_status, "未发货")


def _map_refund(status: str) -> str:
    """退款状态映射"""
    if "退款" in (status or ""):
        if "中" in status:
            return "退款中"
        if "已" in status:
            return "已退款"
        return "申请中"
    return "无"


@router.post("/bitable/sync-orders")
def sync_orders(db: Session = Depends(get_db)):
    """同步订单数据到飞书【订单表】"""
    if not is_configured():
        return _mock_sync("订单表", 0)
    try:
        app_token = _ensure_app_token()
        table_id = _ensure_table(app_token, "order")

        orders = (
            db.query(Order, SessionModel.user_name, SessionModel.id)
            .join(SessionModel, Order.session_id == SessionModel.id)
            .all()
        )
        records = []
        for o, user_name, session_id in orders:
            try:
                amount = float(str(o.price).replace("¥", "").replace(",", "").strip())
            except (ValueError, TypeError):
                amount = 0
            records.append({
                "fields": {
                    "订单ID": o.order_no or f"ORD-{o.id:04d}",
                    "用户ID": user_name,
                    "会话ID": str(session_id),
                    "商品名称": o.name or "",
                    "SKU": o.name or "",
                    "订单金额": amount,
                    "状态": _map_order_status(o.status),
                    "物流": _map_logistics(o.logistics_status),
                    "退款状态": _map_refund(o.status),
                }
            })

        _clear_table(app_token, table_id)
        count = _batch_create_records(app_token, table_id, records)
        return {"success": True, "table": "订单表", "synced_count": count, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        return {"success": False, "message": f"同步失败: {str(e)}"}


@router.post("/bitable/sync-actions")
def sync_actions(db: Session = Depends(get_db)):
    """同步客服动作数据到飞书【客服动作表】"""
    if not is_configured():
        return _mock_sync("客服动作表", 0)
    try:
        app_token = _ensure_app_token()
        table_id = _ensure_table(app_token, "action")

        sessions = db.query(SessionModel).all()
        records = []
        for s in sessions:
            # 取该会话的AI回复消息
            ai_msgs = (
                db.query(Message)
                .filter(Message.session_id == s.id, Message.type == "ai", Message.dir == "left")
                .order_by(Message.created_at)
                .all()
            )
            ai_reply_text = "\n".join(m.text for m in ai_msgs[:3]) if ai_msgs else ""

            # 转人工原因
            transfer_reason = ""
            if s.tab == "wait":
                if s.intent and "退款" in s.intent:
                    transfer_reason = "退款纠纷"
                elif s.emotion and ("愤怒" in s.emotion or "不满" in s.emotion):
                    transfer_reason = "情绪问题"
                elif s.intent and "物流" in s.intent:
                    transfer_reason = "物流异常"
                elif s.intent and "投诉" in s.intent:
                    transfer_reason = "投诉"
                else:
                    transfer_reason = "复杂问题"

            # 人工处理结果
            result = "需跟进"
            if s.status == "closed":
                result = "已解决"
            elif s.tab == "ai":
                result = "已解决"

            records.append({
                "fields": {
                    "会话ID": str(s.id),
                    "用户ID": s.user_name,
                    "AI回复": ai_reply_text,
                    "转人工原因": transfer_reason,
                    "人工处理结果": result,
                    "优惠动作": "未使用",
                }
            })

        _clear_table(app_token, table_id)
        count = _batch_create_records(app_token, table_id, records)
        return {"success": True, "table": "客服动作表", "synced_count": count, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        return {"success": False, "message": f"同步失败: {str(e)}"}


@router.post("/bitable/sync-events")
def sync_events(db: Session = Depends(get_db)):
    """同步结果事件数据到飞书【结果事件表】"""
    if not is_configured():
        return _mock_sync("结果事件表", 0)
    try:
        app_token = _ensure_app_token()
        table_id = _ensure_table(app_token, "event")

        sessions = db.query(SessionModel).all()
        records = []
        for s in sessions:
            sid = str(s.id)
            # 会话创建 → 咨询事件
            records.append({
                "fields": {
                    "用户ID": s.user_name,
                    "会话ID": sid,
                    "事件类型": "加购",
                    "事件时间": s.created_at.strftime("%Y-%m-%d %H:%M:%S") if s.created_at else "",
                }
            })
            # 有订单 → 下单事件
            has_order = db.query(Order).filter(Order.session_id == s.id).first()
            if has_order:
                records.append({
                    "fields": {
                        "用户ID": s.user_name,
                        "会话ID": sid,
                        "事件类型": "下单",
                        "事件时间": has_order.created_at.strftime("%Y-%m-%d %H:%M:%S") if has_order.created_at else "",
                    }
                })
            # 退款 → 取消退款事件
            if "退款" in (s.intent or ""):
                records.append({
                    "fields": {
                        "用户ID": s.user_name,
                        "会话ID": sid,
                        "事件类型": "取消退款",
                        "事件时间": s.updated_at.strftime("%Y-%m-%d %H:%M:%S") if s.updated_at else "",
                    }
                })

        _clear_table(app_token, table_id)
        count = _batch_create_records(app_token, table_id, records)
        return {"success": True, "table": "结果事件表", "synced_count": count, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        return {"success": False, "message": f"同步失败: {str(e)}"}


def _map_msg_dir(dir_val: str) -> str:
    """消息方向映射"""
    if dir_val == "right":
        return "客户"
    if dir_val == "left":
        return "AI"
    return "系统"


def _map_msg_type(m: Message) -> str:
    """消息类型映射"""
    if m.dir == "right":
        return "客户提问"
    if m.type == "ai" and m.dir == "left":
        return "AI回答"
    if m.type == "agent":
        return "客服回复"
    return "系统提示"


@router.post("/bitable/sync-messages")
def sync_messages(db: Session = Depends(get_db)):
    """同步聊天消息数据到飞书【聊天消息表】"""
    if not is_configured():
        return _mock_sync("聊天消息表", 0)
    try:
        app_token = _ensure_app_token()
        table_id = _ensure_table(app_token, "message")

        # 关联查询消息 + 所属会话的用户名
        rows = (
            db.query(Message, SessionModel.user_name)
            .join(SessionModel, Message.session_id == SessionModel.id)
            .order_by(Message.created_at)
            .all()
        )
        records = []
        for m, user_name in rows:
            records.append({
                "fields": {
                    "消息ID": str(m.id),
                    "会话ID": str(m.session_id),
                    "用户ID": user_name,
                    "消息方向": _map_msg_dir(m.dir),
                    "消息内容": m.text or "",
                    "消息类型": _map_msg_type(m),
                    "发送时间": m.created_at.strftime("%Y-%m-%d %H:%M:%S") if m.created_at else "",
                }
            })

        _clear_table(app_token, table_id)
        count = _batch_create_records(app_token, table_id, records)
        return {"success": True, "table": "聊天消息表", "synced_count": count, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        return {"success": False, "message": f"同步失败: {str(e)}"}


@router.post("/bitable/sync-kpis")
def sync_kpis(db: Session = Depends(get_db)):
    """同步KPI驾驶舱指标到飞书【KPI驾驶舱指标表】"""
    if not is_configured():
        return _mock_sync("KPI驾驶舱指标表", 0)
    try:
        app_token = _ensure_app_token()
        table_id = _ensure_table(app_token, "kpi")

        # 调用 cockpit 接口逻辑计算 KPI
        from app.routers.cockpit import get_cockpit_summary
        summary = get_cockpit_summary(period="30d", db=db)
        kpis = summary.get("kpis", [])
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        records = []
        for k in kpis:
            records.append({
                "fields": {
                    "指标名称": k.get("name", ""),
                    "指标数值": str(k.get("value", "")),
                    "单位": k.get("unit", ""),
                    "趋势说明": k.get("trend_text", ""),
                    "详细描述": k.get("desc", ""),
                    "进度": k.get("progress", 0),
                    "同步时间": now_str,
                }
            })

        _clear_table(app_token, table_id)
        count = _batch_create_records(app_token, table_id, records)
        return {"success": True, "table": "KPI驾驶舱指标表", "synced_count": count, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        return {"success": False, "message": f"同步失败: {str(e)}"}


@router.post("/bitable/sync-all")
def sync_all(db: Session = Depends(get_db)):
    """一键同步全部数据到飞书多维表格（8张表）
    优化：用线程池并行同步 8 张表（飞书 API 不同表之间无依赖），
    每个任务用独立 Session（SQLAlchemy Session 非线程安全）。
    相比串行 30+ 次 HTTP 请求，并行可将耗时从 ~30s 降到 ~5-8s。
    """
    if not is_configured():
        return {
            "success": False,
            "message": "未配置飞书凭证。请在 backend/.env 中配置 FEISHU_APP_ID、FEISHU_APP_SECRET，可选配置 FEISHU_APP_TOKEN",
            "guide": {
                "step1": "前往 https://open.feishu.cn 创建企业自建应用",
                "step2": "在应用'权限管理'中添加 bitable:app 和 bitable:app:create 权限",
                "step3": "在 backend 目录创建 .env 文件，写入：FEISHU_APP_ID=xxx\\nFEISHU_APP_SECRET=xxx",
                "step4": "调用 POST /api/feishu/bitable/init 初始化多维表格",
                "step5": "调用 POST /api/feishu/bitable/sync-all 同步数据",
            },
        }

    # 8 张表的同步函数映射（接收独立 Session）
    sync_funcs = {
        "users": sync_users,
        "products": sync_products,
        "sessions": sync_sessions,
        "orders": sync_orders,
        "actions": sync_actions,
        "events": sync_events,
        "messages": sync_messages,
        "kpis": sync_kpis,
    }

    # 并行执行：每个任务开独立 Session（SQLAlchemy Session 非线程安全）
    def _run_one(name_func):
        name, func = name_func
        s = SessionLocal()
        try:
            return name, func(s)
        finally:
            s.close()

    results = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        for name, res in executor.map(_run_one, sync_funcs.items()):
            results[name] = res

    total = sum(r.get("synced_count", 0) for r in results.values() if isinstance(r, dict))
    failed_tables = [k for k, v in results.items() if isinstance(v, dict) and not v.get("success", True)]
    return {
        "success": len(failed_tables) == 0,
        "message": f"同步完成，共写入 {total} 条记录" + (f"，{len(failed_tables)}张表同步失败: {failed_tables}" if failed_tables else ""),
        "details": results,
        "total": total,
        "failed_tables": failed_tables,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/bitable/{table_id}/records")
def get_bitable_records(table_id: str, page_size: int = Query(20, le=100)):
    """获取多维表格记录"""
    if not is_configured():
        return _mock_records(table_id)

    try:
        app_token = _ensure_app_token()
        url = f"{FEISHU_BASE}/bitable/v1/apps/{app_token}/tables/{table_id}/records"
        params = {"page_size": page_size}
        resp = requests.get(url, headers=_headers(), params=params, timeout=10)
        data = resp.json()
        if data.get("code") != 0:
            return {"error": data.get("msg")}

        return {
            "total": data.get("data", {}).get("total", 0),
            "records": [
                {"record_id": r.get("record_id"), "fields": r.get("fields")}
                for r in data.get("data", {}).get("items", [])
            ],
        }
    except Exception as e:
        return {"error": str(e)}


# ========== Mock 降级函数 ==========

def _mock_sync(table_name: str, count: int) -> dict:
    return {
        "success": True,
        "mode": "mock",
        "message": f"未配置飞书凭证，当前为 mock 模式。配置 FEISHU_APP_ID/FEISHU_APP_SECRET 后可真实同步。",
        "table": table_name,
        "synced_count": count,
        "timestamp": datetime.now().isoformat(),
    }


def _mock_records(table_id: str) -> dict:
    mock_data = {
        "user": [
            {"用户ID": "李先生", "平台": "抖音", "会员等级": "金卡", "累计消费": "1k-1w"},
            {"用户ID": "张女士", "平台": "淘宝", "会员等级": "银卡", "累计消费": "1k以下"},
        ],
        "product": [
            {"SKU": "YQ-ZWJ-001", "库存": 500, "规格": "三层", "尺寸": "40×25×15cm", "材质": "304不锈钢"},
            {"SKU": "YQ-SNX-002", "库存": 300, "规格": "35L", "尺寸": "50×35×30cm", "材质": "PP环保塑料"},
        ],
        "session": [
            {"用户ID": "李先生", "处理路径": "AI转人工", "意图": "咨询", "情绪": "不满", "价值评分": 78},
            {"用户ID": "张女士", "处理路径": "AI", "意图": "退款", "情绪": "愤怒", "价值评分": 42},
        ],
        "order": [
            {"订单ID": "TB202401001", "用户ID": "李先生", "SKU": "免打孔不锈钢置物架", "订单金额": 39.9, "状态": "已发货", "物流": "运输中", "退款状态": "无"},
        ],
        "action": [
            {"AI回复": "您好，这款置物架承重20kg...", "转人工原因": "复杂问题", "人工处理结果": "已解决", "优惠动作": "未使用"},
        ],
        "event": [
            {"用户ID": "李先生", "事件类型": "下单", "事件时间": "2026-08-09 10:30:00"},
        ],
    }
    return {"mode": "mock", "records": mock_data.get(table_id, [])}
