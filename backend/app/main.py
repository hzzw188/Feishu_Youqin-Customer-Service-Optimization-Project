import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量（飞书凭证、DeepSeek API Key 等）
load_dotenv()

# 记录服务器原时区（设置 TZ 之前）：部署服务器默认 UTC 时 time.timezone == 0，
# 用于修正历史错位数据；本地开发（东八区）time.timezone != 0，不受影响
import time as _time
_SRV_WAS_UTC = (_time.timezone == 0)

# 统一使用中国时区（Asia/Shanghai），避免部署服务器默认 UTC 导致时间偏移 8 小时
os.environ["TZ"] = "Asia/Shanghai"
try:
    _time.tzset()
except AttributeError:
    pass

from app.database import engine, Base, SessionLocal
from app.routers import sessions, cockpit, ai, platforms, feishu, logistics, auth, customer

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 轻量级表结构迁移：给 messages 表追加 confidence 列（SQLite ALTER TABLE，幂等）
def _migrate_messages_confidence():
    from sqlalchemy import text, inspect
    insp = inspect(engine)
    if "messages" not in insp.get_table_names():
        return
    cols = [c["name"] for c in insp.get_columns("messages")]
    if "confidence" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE messages ADD COLUMN confidence INTEGER"))

_migrate_messages_confidence()


# 一次性时区迁移：Railway 服务器此前为 UTC 时区，历史 created_at / time 字段均偏早 8 小时，
# 切换到 Asia/Shanghai 后统一 +8 小时补齐（幂等：PRAGMA user_version 标记已执行）
def _migrate_utc_time_offset():
    if not _SRV_WAS_UTC:
        return
    from sqlalchemy import text
    from datetime import timedelta
    from app.models import Session as SessionModel, Message, Order, LogisticsTrack
    try:
        with engine.connect() as conn:
            ver = conn.execute(text("PRAGMA user_version")).scalar() or 0
        if ver >= 1:
            return

        db = SessionLocal()
        try:
            delta = timedelta(hours=8)

            def fix_hhmm(s):
                """HH:MM 字符串 +8 小时（跨天取模）"""
                if s and ":" in s:
                    parts = s.split(":")
                    try:
                        h, m = int(parts[0]), int(parts[1])
                        return f"{(h + 8) % 24:02d}:{m:02d}"
                    except (ValueError, IndexError):
                        pass
                return s

            n = 0
            for s in db.query(SessionModel).all():
                if s.created_at:
                    s.created_at += delta
                    s.updated_at += delta
                if s.time:
                    s.time = fix_hhmm(s.time)
                n += 1
            for m in db.query(Message).all():
                if m.created_at:
                    m.created_at += delta
                n += 1
            for o in db.query(Order).all():
                if o.created_at:
                    o.created_at += delta
                n += 1
            for t in db.query(LogisticsTrack).all():
                if t.created_at:
                    t.created_at += delta
                n += 1
            db.commit()
            with engine.begin() as conn:
                conn.execute(text("PRAGMA user_version = 1"))
            import logging
            logging.getLogger("uvicorn.error").info(f"✅ 时区迁移完成：已修正 {n} 条历史数据 (+8小时)")
        finally:
            db.close()
    except Exception as e:
        import logging
        logging.getLogger("uvicorn.error").error(f"时区迁移失败: {e}")


_migrate_utc_time_offset()

# 初始化默认测试账号 admin / password
def _init_default_user():
    db = SessionLocal()
    try:
        from app.models import User
        from app.routers.auth import hash_password
        if not db.query(User).filter(User.username == "admin").first():
            db.add(User(username="admin", password_hash=hash_password("password")))
            db.commit()
    finally:
        db.close()

_init_default_user()

# 首次启动时自动初始化演示数据（8个会话+消息+订单+话术+物流轨迹）
def _init_demo_data():
    db = SessionLocal()
    try:
        from app.models import Session as SessionModel
        if db.query(SessionModel).count() == 0:
            db.close()
            import subprocess, sys, os
            init_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "init_db.py")
            subprocess.run([sys.executable, init_script], check=True)
        else:
            db.close()
    except Exception as e:
        import logging
        logging.getLogger("uvicorn.error").error(f"演示数据初始化失败: {e}")
        try:
            db.close()
        except Exception:
            pass

_init_demo_data()

app = FastAPI(
    title="优勤智服 · AI客服利润引擎 API",
    description="整合淘宝/抖音/京东/拼多多四平台客服一体化后端服务",
    version="1.0.0",
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(cockpit.router)
app.include_router(ai.router)
app.include_router(platforms.router)
app.include_router(feishu.router)
app.include_router(logistics.router)
app.include_router(customer.router)


@app.get("/")
def root():
    return {
        "name": "优勤智服 · AI客服利润引擎",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/api/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}