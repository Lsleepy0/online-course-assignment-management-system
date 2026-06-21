from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import SessionLocal
import models
import auth

router = APIRouter(prefix="/classes")
templates = Jinja2Templates(directory="templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)
    if user.role != "admin":
        return templates.TemplateResponse("error.html", {"request": request, "user": user, "message": "无权限访问"})
    nodes = db.query(models.ClassInfo).order_by(models.ClassInfo.sort_no).all()
    return templates.TemplateResponse("classes/index.html", {"request": request, "user": user, "nodes": nodes})


@router.get("/tree")
def tree(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user:
        return JSONResponse({"error": "未登录"}, status_code=401)
    nodes = db.query(models.ClassInfo).all()
    result = []
    for n in nodes:
        result.append({
            "id": n.id,
            "name": n.name,
            "parent_id": n.parent_id,
            "level": n.level,
            "sort_no": n.sort_no,
            "status": n.status,
            "remark": n.remark or "",
        })
    return JSONResponse({"nodes": result})


@router.get("/detail/{node_id}")
def detail(node_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user:
        return JSONResponse({"error": "未登录"}, status_code=401)
    node = db.query(models.ClassInfo).filter(models.ClassInfo.id == node_id).first()
    if not node:
        return JSONResponse({"error": "节点不存在"}, status_code=404)
    parent_name = ""
    if node.parent_id:
        parent = db.query(models.ClassInfo).filter(models.ClassInfo.id == node.parent_id).first()
        if parent:
            parent_name = parent.name
    return JSONResponse({
        "id": node.id,
        "name": node.name,
        "parent_name": parent_name,
        "level": node.level,
        "sort_no": node.sort_no,
        "status": node.status,
        "remark": node.remark or "",
    })


@router.post("/create")
def create(
    request: Request,
    name: str = Form(...),
    parent_id: str = Form(""),
    sort_no: str = Form(""),
    status: str = Form("可用"),
    remark: str = Form(""),
    db: Session = Depends(get_db),
):
    user = auth.get_current_user(request)
    if not user or user.role != "admin":
        return JSONResponse({"error": "无权限"}, status_code=403)

    sort_no_int = int(sort_no) if sort_no else None
    parent_id_int = int(parent_id) if parent_id else None
    level = 1
    if parent_id_int:
        parent = db.query(models.ClassInfo).filter(models.ClassInfo.id == parent_id_int).first()
        if parent:
            level = parent.level + 1
    node = models.ClassInfo(
        name=name,
        parent_id=parent_id_int,
        level=level,
        sort_no=sort_no_int,
        status=status,
        remark=remark,
    )
    db.add(node)
    db.commit()
    return JSONResponse({"success": True, "id": node.id})


@router.post("/update/{node_id}")
def update(
    node_id: int,
    request: Request,
    name: str = Form(...),
    sort_no: str = Form(""),
    status: str = Form("可用"),
    remark: str = Form(""),
    db: Session = Depends(get_db),
):
    user = auth.get_current_user(request)
    if not user or user.role != "admin":
        return JSONResponse({"error": "无权限"}, status_code=403)
    node = db.query(models.ClassInfo).filter(models.ClassInfo.id == node_id).first()
    if not node:
        return JSONResponse({"error": "节点不存在"}, status_code=404)
    node.name = name
    node.sort_no = int(sort_no) if sort_no else None
    node.status = status
    node.remark = remark
    db.commit()
    return JSONResponse({"success": True})


@router.post("/delete/{node_id}")
def delete(node_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user or user.role != "admin":
        return JSONResponse({"error": "无权限"}, status_code=403)
    node = db.query(models.ClassInfo).filter(models.ClassInfo.id == node_id).first()
    if not node:
        return JSONResponse({"error": "节点不存在"}, status_code=404)
    db.delete(node)
    db.commit()
    return JSONResponse({"success": True})
