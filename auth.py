from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Request, HTTPException, status
from typing import Optional
from database import SessionLocal
import models

SECRET_KEY = "online-course-assignment-management-system-secret-2024"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 12

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def get_current_user(request: Request) -> Optional[models.User]:
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    user_id = payload.get("user_id")
    if not user_id:
        return None
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        return user
    finally:
        db.close()


def require_login(request: Request) -> models.User:
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/auth/login"})
    return user


def require_role(request: Request, roles: list) -> models.User:
    user = require_login(request)
    if user.role not in roles:
        raise HTTPException(status_code=403, detail="无权限访问")
    return user


def generate_captcha():
    import random
    from PIL import Image, ImageDraw, ImageFont
    import io
    import base64

    code = "".join([str(random.randint(0, 9)) for _ in range(4)])
    width, height = 120, 40
    image = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except Exception:
        font = ImageFont.load_default()
    for i, char in enumerate(code):
        x = 10 + i * 26
        y = random.randint(2, 8)
        color = (random.randint(0, 100), random.randint(0, 100), random.randint(0, 100))
        draw.text((x, y), char, font=font, fill=color)
    for _ in range(5):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=(random.randint(0, 200), random.randint(0, 200), random.randint(0, 200)))
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    return code, img_base64
