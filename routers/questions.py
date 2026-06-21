from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_
from database import SessionLocal
import models
import auth

router = APIRouter(prefix="/questions")
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
    content: str = "",
    qtype: str = "",
    course_id: str = "",
    creator: str = "",
    status: str = "",
    db: Session = Depends(get_db),
):
    user = auth.get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)
    q = db.query(models.Question)
    if content:
        q = q.filter(models.Question.content.contains(content))
    if qtype:
        q = q.filter(models.Question.difficulty == qtype)
    if course_id:
        q = q.filter(models.Question.course_id.like(course_id))
    if creator:
        q = q.filter(models.Question.creator.contains(creator))
    if status:
        q = q.filter(models.Question.status == status)
    total = q.count()
    questions = q.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE).all()
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    courses = db.query(models.Course).all()
    return templates.TemplateResponse("questions/index.html", {
        "request": request, "user": user, "questions": questions, "courses": courses,
        "page": page, "total_pages": total_pages, "total": total,
        "filters": {"content": content, "qtype": qtype, "course_id": course_id, "creator": creator, "status": status},
    })


@router.get("/create", response_class=HTMLResponse)
def create_page(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)
    if user.role not in ("admin", "teacher"):
        return templates.TemplateResponse("error.html", {"request": request, "user": user, "message": "无权限访问"})
    courses = db.query(models.Course).all()
    return templates.TemplateResponse("questions/create.html", {
        "request": request, "user": user, "courses": courses, "error": None,
    })


@router.post("/create")
async def create(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user or user.role not in ("admin", "teacher"):
        return RedirectResponse("/auth/login", status_code=303)
    form = await request.form()
    qtype = form.get("type", "")
    content = form.get("content", "")
    answer = form.get("answer", "")
    course_id = form.get("course_id", "")
    score = form.get("score", "1")
    remark = form.get("remark", "")
    courses = db.query(models.Course).all()

    if not qtype:
        return templates.TemplateResponse("questions/create.html", {
            "request": request, "user": user, "courses": courses, "error": "请选择题目类型",
        })
    if not content:
        return templates.TemplateResponse("questions/create.html", {
            "request": request, "user": user, "courses": courses, "error": "题目内容不能为空",
        })
    if not answer:
        return templates.TemplateResponse("questions/create.html", {
            "request": request, "user": user, "courses": courses, "error": "正确答案不能为空",
        })
    if not course_id:
        return templates.TemplateResponse("questions/create.html", {
            "request": request, "user": user, "courses": courses, "error": "请选择所属课程",
        })
    try:
        score_int = int(score)
    except Exception:
        return templates.TemplateResponse("questions/create.html", {
            "request": request, "user": user, "courses": courses, "error": "分值必须为整数",
        })
    try:
        question = models.Question(
            type=qtype,
            content=content,
            option_a=form.get("option_a", ""),
            option_b=form.get("option_b", ""),
            option_c=form.get("option_c", ""),
            option_d=form.get("option_d", ""),
            option_e=form.get("option_e", ""),
            answer=answer,
            score=score_int,
            difficulty=form.get("difficulty", "简单"),
            course_id=int(course_id),
            remark=remark,
            status="未审核",
            creator=user.username,
        )
        db.add(question)
        db.commit()
    except Exception:
        return templates.TemplateResponse("questions/create.html", {
            "request": request, "user": user, "courses": courses, "error": "未知错误",
        })
    return RedirectResponse(url="/questions/", status_code=303)


@router.get("/edit/{question_id}", response_class=HTMLResponse)
def edit_page(question_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)
    if user.role not in ("admin", "teacher"):
        return templates.TemplateResponse("error.html", {"request": request, "user": user, "message": "无权限访问"})
    question = db.query(models.Question).filter(models.Question.id == question_id).first()
    courses = db.query(models.Course).all()
    return templates.TemplateResponse("questions/edit.html", {
        "request": request, "user": user, "question": question, "courses": courses, "error": None,
    })


@router.post("/edit/{question_id}")
async def edit_question(question_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user or user.role not in ("admin", "teacher"):
        return RedirectResponse("/auth/login", status_code=303)
    form = await request.form()
    question = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not question:
        return RedirectResponse(url="/questions/", status_code=303)
    question.type = form.get("type", question.type)
    question.content = form.get("content", question.content)
    question.option_a = form.get("option_a", question.option_a)
    question.option_b = form.get("option_b", question.option_b)
    question.option_c = form.get("option_c", question.option_c)
    question.option_d = form.get("option_d", question.option_d)
    question.option_e = form.get("option_e", question.option_e)
    question.answer = form.get("answer", question.answer)
    score = form.get("score", "1")
    try:
        question.score = int(score)
    except Exception:
        pass
    question.difficulty = form.get("difficulty", question.difficulty)
    question.course_id = int(form.get("course_id", question.course_id))
    question.remark = form.get("remark", question.remark)
    db.commit()
    return RedirectResponse(url="/questions/", status_code=303)


@router.post("/submit_review/{question_id}")
def submit_review(question_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user or user.role not in ("admin", "teacher"):
        return JSONResponse({"error": "无权限"}, status_code=403)
    question = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not question:
        return JSONResponse({"error": "试题不存在"}, status_code=404)
    db.commit()
    return JSONResponse({"success": True})


@router.post("/delete/{question_id}")
def delete(question_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user or user.role not in ("admin", "teacher"):
        return JSONResponse({"error": "无权限"}, status_code=403)
    question = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not question:
        return JSONResponse({"error": "试题不存在"}, status_code=404)
    db.delete(question)
    db.commit()
    return JSONResponse({"success": True})


@router.get("/review", response_class=HTMLResponse)
def review_page(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)
    if user.role not in ("admin", "teacher"):
        return templates.TemplateResponse("error.html", {"request": request, "user": user, "message": "无权限访问"})
    questions = db.query(models.Question).filter(models.Question.status == "待审核").all()
    return templates.TemplateResponse("questions/review.html", {
        "request": request, "user": user, "questions": questions,
    })


@router.post("/review/approve/{question_id}")
def approve(question_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user or user.role not in ("admin", "teacher"):
        return JSONResponse({"error": "无权限"}, status_code=403)
    question = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not question:
        return JSONResponse({"error": "试题不存在"}, status_code=404)
    question.status = "已发布"
    question.reject_reason = None
    db.commit()
    return JSONResponse({"success": True})


@router.post("/review/reject/{question_id}")
async def reject(question_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user or user.role not in ("admin", "teacher"):
        return JSONResponse({"error": "无权限"}, status_code=403)
    form = await request.form()
    reason = form.get("reason", "")
    question = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not question:
        return JSONResponse({"error": "试题不存在"}, status_code=404)
    question.status = "未审核"
    question.reject_reason = reason
    db.commit()
    return JSONResponse({"success": True})


@router.get("/library", response_class=HTMLResponse)
def library(
    request: Request,
    page: int = 1,
    qtype: str = "",
    course_id: str = "",
    status: str = "",
    db: Session = Depends(get_db),
):
    user = auth.get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)
    q = db.query(models.Question)
    if qtype:
        q = q.filter(models.Question.type == qtype)
    if course_id:
        q = q.filter(models.Question.course_id == course_id)
    if status:
        q = q.filter(models.Question.status == status)
    total = q.count()
    questions = q.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE).all()
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    courses = db.query(models.Course).all()
    return templates.TemplateResponse("questions/library.html", {
        "request": request, "user": user, "questions": questions, "courses": courses,
        "page": page, "total_pages": total_pages, "total": total,
        "filters": {"qtype": qtype, "course_id": course_id, "status": status},
    })


@router.post("/close/{question_id}")
def close(question_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user or user.role not in ("admin", "teacher"):
        return JSONResponse({"error": "无权限"}, status_code=403)
    question = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not question:
        return JSONResponse({"error": "试题不存在"}, status_code=404)
    question.status = "已关闭"
    db.commit()
    return JSONResponse({"success": True})


@router.get("/detail/{question_id}")
def detail(question_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user:
        return JSONResponse({"error": "未登录"}, status_code=401)
    question = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not question:
        return JSONResponse({"error": "试题不存在"}, status_code=404)
    course_name = ""
    if question.course_id:
        course = db.query(models.Course).filter(models.Course.id == question.course_id).first()
        if course:
            course_name = course.name
    return JSONResponse({
        "id": question.id,
        "type": question.type,
        "content": question.content,
        "option_a": question.option_a or "",
        "option_b": question.option_b or "",
        "option_c": question.option_c or "",
        "option_d": question.option_d or "",
        "option_e": question.option_e or "",
        "answer": question.answer,
        "score": question.score,
        "difficulty": question.difficulty,
        "course_name": course_name,
        "status": question.status,
        "creator": question.creator or "",
        "remark": question.remark or "",
        "reject_reason": question.reject_reason or "",
    })
