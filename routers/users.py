from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_
from database import SessionLocal
import models
import auth

router = APIRouter(prefix="/users")
templates = Jinja2Templates(directory="templates")

PAGE_SIZE = 10


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    page: int = 1,
    username: str = "",
    real_name: str = "",
    role: str = "",
    status: str = "",
    db: Session = Depends(get_db),
):
    user = auth.get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)
    if user.role != "admin":
        return templates.TemplateResponse("error.html", {"request": request, "user": user, "message": "无权限访问"})
    q = db.query(models.User)
    if username:
        q = q.filter(models.User.username.contains(username))
    if real_name:
        q = q.filter(models.User.real_name.contains(real_name))
    if role:
        q = q.filter(models.User.role == role)
    if status:
        q = q.filter(models.User.status == status)
    total = q.count()
    users = q.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE).all()
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    return templates.TemplateResponse("users/index.html", {
        "request": request, "user": user, "users": users,
        "page": page, "total_pages": total_pages, "total": total,
        "filters": {"username": username, "real_name": real_name, "role": role, "status": status},
    })


@router.get("/create", response_class=HTMLResponse)
def create_page(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)
    if user.role != "admin":
        return templates.TemplateResponse("error.html", {"request": request, "user": user, "message": "无权限访问"})
    classes = db.query(models.ClassInfo).all()
    classes_data = [{"id": c.id, "name": c.name, "parent_id": c.parent_id, "level": c.level} for c in classes]
    return templates.TemplateResponse("users/create.html", {
        "request": request, "user": user, "classes": classes_data, "error": None,
    })


@router.post("/create_submit")
async def create_submit(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user or user.role != "admin":
        return RedirectResponse("/auth/login", status_code=303)
    form = await request.form()
    username = form.get("username", "")
    real_name = form.get("real_name", "")
    role = form.get("role", "student")
    class_id = form.get("class_id", "")
    status = form.get("status", "可用")
    remark = form.get("remark", "")
    id_card = form.get("id_card", "")
    address = form.get("address", "")
    phone = form.get("phone", "")
    gender = form.get("gender", "")
    emergency_contact = form.get("emergency_contact", "")
    emergency_phone = form.get("emergency_phone", "")
    enroll_date = form.get("enroll_date", "")
    leave_date = form.get("leave_date", "")
    nation = form.get("nation", "")
    work_status = form.get("work_status", "")
    detail_remark = form.get("detail_remark", "")

    if len(username) < 1 or len(username) > 20:
        classes = db.query(models.ClassInfo).all()
        classes_data = [{"id": c.id, "name": c.name, "parent_id": c.parent_id, "level": c.level} for c in classes]
        return templates.TemplateResponse("users/create.html", {
            "request": request, "user": user, "classes": classes_data, "error": "登录账号长度需1-20字符",
        })
    if len(real_name) < 1 or len(real_name) > 20:
        classes = db.query(models.ClassInfo).all()
        classes_data = [{"id": c.id, "name": c.name, "parent_id": c.parent_id, "level": c.level} for c in classes]
        return templates.TemplateResponse("users/create.html", {
            "request": request, "user": user, "classes": classes_data, "error": "用户姓名长度需1-20字符",
        })
    if db.query(models.User).filter(models.User.username == username).first():
        classes = db.query(models.ClassInfo).all()
        classes_data = [{"id": c.id, "name": c.name, "parent_id": c.parent_id, "level": c.level} for c in classes]
        return templates.TemplateResponse("users/create.html", {
            "request": request, "user": user, "classes": classes_data, "error": "登录账号已存在",
        })

    new_user = models.User(
        username=username,
        password=auth.hash_password("111111"),
        real_name=real_name,
        role=role,
        class_id=int(class_id) if class_id else None,
        status=status,
        remark=remark,
        id_card=id_card,
        address=address,
        phone=phone,
        gender=gender,
        emergency_contact=emergency_contact,
        emergency_phone=emergency_phone,
        enroll_date=enroll_date,
        leave_date=leave_date,
        nation=nation,
        work_status=work_status,
        detail_remark=detail_remark,
    )
    db.add(new_user)
    db.commit()
    return RedirectResponse(url="/users/", status_code=303)


@router.get("/edit/{user_id}", response_class=HTMLResponse)
def edit_page(user_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)
    if user.role != "admin":
        return templates.TemplateResponse("error.html", {"request": request, "user": user, "message": "无权限访问"})
    edit_user = db.query(models.User).filter(models.User.id == user_id).first()
    classes = db.query(models.ClassInfo).all()
    return templates.TemplateResponse("users/edit.html", {
        "request": request, "user": user, "edit_user": edit_user, "classes": classes, "error": None,
    })


@router.post("/edit/{user_id}")
async def edit_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user or user.role != "admin":
        return RedirectResponse("/auth/login", status_code=303)
    form = await request.form()
    edit_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not edit_user:
        return RedirectResponse(url="/users/", status_code=303)
    edit_user.real_name = form.get("real_name", edit_user.real_name)
    edit_user.role = form.get("role", edit_user.role)
    class_id = form.get("class_id", "")
    edit_user.class_id = int(class_id) if class_id else None
    edit_user.status = form.get("status", edit_user.status)
    edit_user.remark = form.get("remark", edit_user.remark)
    edit_user.id_card = form.get("id_card", edit_user.id_card)
    edit_user.address = form.get("address", edit_user.address)
    edit_user.phone = form.get("phone", edit_user.phone)
    edit_user.gender = form.get("gender", edit_user.gender)
    edit_user.emergency_contact = form.get("emergency_contact", edit_user.emergency_contact)
    edit_user.emergency_phone = form.get("emergency_phone", edit_user.emergency_phone)
    edit_user.enroll_date = form.get("enroll_date", edit_user.enroll_date)
    edit_user.leave_date = form.get("leave_date", edit_user.leave_date)
    edit_user.nation = form.get("nation", edit_user.nation)
    edit_user.work_status = form.get("work_status", edit_user.work_status)
    edit_user.detail_remark = form.get("detail_remark", edit_user.detail_remark)
    db.commit()
    return RedirectResponse(url="/users/", status_code=303)


@router.post("/delete/{user_id}")
def delete(user_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user or user.role != "admin":
        return JSONResponse({"error": "无权限"}, status_code=403)
    edit_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not edit_user:
        return JSONResponse({"error": "用户不存在"}, status_code=404)
    db.delete(edit_user)
    db.commit()
    return JSONResponse({"success": True})
