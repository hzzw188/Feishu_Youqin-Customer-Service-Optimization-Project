"""
认证路由 — 注册、登录
密码使用 pbkdf2_hmac + 随机 salt 存储（标准库，无需额外依赖）
"""
import hashlib
import secrets
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------- 密码工具 ----------
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return f"{salt}:{h.hex()}"


def verify_password(password: str, stored: str) -> bool:
    parts = stored.split(":")
    if len(parts) != 2:
        return False
    salt, h = parts
    computed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return secrets.compare_digest(h, computed.hex())


# ---------- 请求模型 ----------
class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


# ---------- 路由 ----------
@router.post("/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    username = req.username.strip()
    if not username or not req.password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    if len(username) < 2:
        raise HTTPException(status_code=400, detail="用户名至少2个字符")
    if len(req.password) < 4:
        raise HTTPException(status_code=400, detail="密码至少4个字符")

    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(status_code=409, detail="该用户名已被注册")

    user = User(username=username, password_hash=hash_password(req.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "success": True,
        "message": "注册成功",
        "user": {"id": user.id, "username": user.username},
    }


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username.strip()).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    return {
        "success": True,
        "message": "登录成功",
        "token": secrets.token_hex(32),
        "user": {
            "id": user.id,
            "username": user.username,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
    }


@router.get("/check")
def check_username(username: str, db: Session = Depends(get_db)):
    """检查用户名是否可用"""
    existing = db.query(User).filter(User.username == username.strip()).first()
    return {"available": existing is None}
