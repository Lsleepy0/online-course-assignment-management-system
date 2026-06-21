from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import SessionLocal
import models
import auth

router = APIRouter(prefix="/courses")
templates = Jinja2Templates(directory="templates")

PAGE_SIZE = 10


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_class=HTMLResponse)
def index(request: Request, page: int = 1, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)
    if user.role not in ("admin", "teacher"):
        return templates.TemplateResponse("error.html", {"request": request, "user": user, "message": "无权限访问"})
    q = db.query(models.Course)
    total = q.count()
    courses = q.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE).all()
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    return templates.TemplateResponse("courses/index.html", {
        "request": request, "user": user, "courses": courses,
        "page": page, "total_pages": total_pages, "total": total,
    })


@router.get("/create", response_class=HTMLResponse)
def create_page(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)
    if user.role not in ("admin", "teacher"):
        return templates.TemplateResponse("error.html", {"request": request, "user": user, "message": "无权限访问"})
    classes = db.query(models.ClassInfo).filter(models.ClassInfo.level == 3).all()
    return templates.TemplateResponse("courses/create.html", {
        "request": request, "user": user, "classes": classes, "error": None,
    })


@router.post("/create")
def create(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    class_ids: list = Form([]),
    db: Session = Depends(get_db),
):
    user = auth.get_current_user(request)
    if not user or user.role not in ("admin", "teacher"):
        return RedirectResponse("/auth/login", status_code=303)
    course = models.Course(name=name, description=description, teacher_id=user.id)
    db.add(course)
    db.commit()
    for cid in class_ids:
        cc = models.CourseClass(course_id=course.id, class_id=int(cid))
        db.add(cc)
    db.commit()
    return RedirectResponse(url="/courses/", status_code=303)


@router.get("/edit/{course_id}", response_class=HTMLResponse)
def edit_page(course_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)
    if user.role not in ("admin", "teacher"):
        return templates.TemplateResponse("error.html", {"request": request, "user": user, "message": "无权限访问"})
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    classes = db.query(models.ClassInfo).filter(models.ClassInfo.level == 3).all()
    selected = [cc.class_id for cc in db.query(models.CourseClass).filter(models.CourseClass.course_id == course_id).all()]
    return templates.TemplateResponse("courses/edit.html", {
        "request": request, "user": user, "course": course, "classes": classes, "selected": selected, "error": None,
    })


@router.post("/edit/{course_id}")
def edit_course(
    course_id: int,
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    class_ids: list = Form([]),
    db: Session = Depends(get_db),
):
    user = auth.get_current_user(request)
    if not user or user.role not in ("admin", "teacher"):
        return RedirectResponse("/auth/login", status_code=303)
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        return RedirectResponse(url="/courses/", status_code=303)
    course.name = name
    course.description = description
    db.query(models.CourseClass).filter(models.CourseClass.course_id == course_id).delete()
    for cid in class_ids:
        db.add(models.CourseClass(course_id=course_id, class_id=int(cid)))
    db.commit()
    return RedirectResponse(url="/courses/", status_code=303)


@router.post("/delete/{course_id}")
def delete(course_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user or user.role not in ("admin", "teacher"):
        return JSONResponse({"error": "无权限"}, status_code=403)
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        return JSONResponse({"error": "课程不存在"}, status_code=404)
    db.delete(course)
    db.commit()
    return JSONResponse({"success": True})
