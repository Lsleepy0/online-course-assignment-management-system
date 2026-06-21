from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import SessionLocal
import models
import auth
import re

router = APIRouter(prefix="/auth")
templates = Jinja2Templates(directory="templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    code, img_base64 = auth.generate_captcha()
    return templates.TemplateResponse("login.html", {
        "request": request,
        "captcha_img": img_base64,
        "captcha_code": code,
        "error": None,
    })


@router.get("/captcha")
def get_captcha(request: Request):
    code, img_base64 = auth.generate_captcha()
    return JSONResponse({"img": img_base64, "code": code})


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    captcha: str = Form(...),
    captcha_code: str = Form(...),
    db: Session = Depends(get_db),
):
    if captcha != captcha_code:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "captcha_img": None,
            "captcha_code": "",
            "error": "验证码错误",
        }, status_code=200)
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not auth.verify_password(password, user.password):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "captcha_img": None,
            "captcha_code": "",
            "error": "用户名或密码错误",
        }, status_code=200)
    if user.status == "禁用":
        return templates.TemplateResponse("login.html", {
            "request": request,
            "captcha_img": None,
            "captcha_code": "",
            "error": "账号已禁用",
        }, status_code=200)
    token = auth.create_access_token({"user_id": user.id, "username": user.username, "role": user.role})
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie("access_token", token, httponly=True, max_age=43200)
    return response


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    db = SessionLocal()
    try:
        classes = db.query(models.ClassInfo).filter(models.ClassInfo.level == 3).all()
        return templates.TemplateResponse("register.html", {
            "request": request,
            "classes": classes,
            "error": None,
        })
    finally:
        db.close()


@router.post("/register")
def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    role: str = Form(...),
    class_id: str = Form(""),
    db: Session = Depends(get_db),
):
    if len(username) < 1 or len(username) > 20:
        return templates.TemplateResponse("register.html", {
            "request": request, "classes": db.query(models.ClassInfo).filter(models.ClassInfo.level == 3).all(),
            "error": "用户名长度需1-20字符",
        })
    if len(password) < 6 or len(password) > 20:
        return templates.TemplateResponse("register.html", {
            "request": request, "classes": db.query(models.ClassInfo).filter(models.ClassInfo.level == 3).all(),
            "error": "密码长度需6-20字符",
        })
    if not re.match(r"^(?=.*[a-zA-Z])(?=.*\d).+$", password):
        return templates.TemplateResponse("register.html", {
            "request": request, "classes": db.query(models.ClassInfo).filter(models.ClassInfo.level == 3).all(),
            "error": "密码必须包含字母和数字",
        })
    if db.query(models.User).filter(models.User.username == username).first():
        return templates.TemplateResponse("register.html", {
            "request": request, "classes": db.query(models.ClassInfo).filter(models.ClassInfo.level == 3).all(),
            "error": "用户名已存在",
        })
    if role == "student" and not class_id:
        return templates.TemplateResponse("register.html", {
            "request": request, "classes": db.query(models.ClassInfo).filter(models.ClassInfo.level == 3).all(),
            "error": "学生角色必须选择班级",
        })
    user = models.User(
        username=username,
        password=auth.hash_password(password),
        real_name=username,
        role=role,
        class_id=int(class_id) if class_id else None,
        status="可用",
    )
    db.add(user)
    db.commit()
    return RedirectResponse(url="/auth/login", status_code=303)


@router.get("/change_password", response_class=HTMLResponse)
def change_password_page(request: Request):
    user = auth.get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)
    return templates.TemplateResponse("change_password.html", {"request": request, "user": user, "error": None, "success": None})


@router.post("/change_password")
def change_password(
    request: Request,
    old_password: str = Form(...),
    new_password: str = Form(...),
    confirm_new_password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = auth.get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)
    db_user = db.query(models.User).filter(models.User.id == user.id).first()
    if not auth.verify_password(old_password, db_user.password):
        return templates.TemplateResponse("change_password.html", {
            "request": request, "user": user, "error": "旧密码错误", "success": None,
        })
    if len(new_password) < 6 or len(new_password) > 20:
        return templates.TemplateResponse("change_password.html", {
            "request": request, "user": user, "error": "新密码长度需6-20字符", "success": None,
        })
    if new_password != confirm_new_password:
        return templates.TemplateResponse("change_password.html", {
            "request": request, "user": user, "error": "两次新密码不一致", "success": None,
        })
    db_user.password = auth.hash_password(new_password)
    db.commit()
    return templates.TemplateResponse("change_password.html", {
        "request": request, "user": user, "error": None, "success": "密码修改成功",
    })


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/auth/login", status_code=303)
    response.delete_cookie("access_token")
    return response
