from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from database import SessionLocal
import models
import auth

router = APIRouter(prefix="/homework")
templates = Jinja2Templates(directory="templates")

PAGE_SIZE = 10


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def parse_dt(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    return None


@router.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    page: int = 1,
    hw_no: str = "",
    course_id: str = "",
    status: str = "",
    db: Session = Depends(get_db),
):
    user = auth.get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)
    if user.role not in ("admin", "teacher"):
        return templates.TemplateResponse("error.html", {"request": request, "user": user, "message": "无权限访问"})
    q = db.query(models.Homework)
    total = q.count()
    homeworks = q.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE).all()
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    courses = db.query(models.Course).all()
    return templates.TemplateResponse("homework/index.html", {
        "request": request, "user": user, "homeworks": homeworks, "courses": courses,
        "page": page, "total_pages": total_pages, "total": total,
        "filters": {"hw_no": hw_no, "course_id": course_id, "status": status},
    })


@router.get("/create", response_class=HTMLResponse)
def create_page(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)
    if user.role not in ("admin", "teacher"):
        return templates.TemplateResponse("error.html", {"request": request, "user": user, "message": "无权限访问"})
    courses = db.query(models.Course).all()
    classes = db.query(models.ClassInfo).filter(models.ClassInfo.level == 3).all()
    students = db.query(models.User).filter(models.User.role == "student").all()
    questions = db.query(models.Question).filter(models.Question.status == "已发布").all()
    return templates.TemplateResponse("homework/create.html", {
        "request": request, "user": user, "courses": courses, "classes": classes,
        "students": students, "questions": questions, "error": None,
    })


@router.post("/create")
async def create(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user or user.role not in ("admin", "teacher"):
        return RedirectResponse("/auth/login", status_code=303)
    form = await request.form()
    name = form.get("name", "")
    course_id = form.get("course_id", "")
    publish_time = form.get("publish_time", "")
    deadline = form.get("deadline", "")
    total_score = form.get("total_score", "100")
    class_ids = form.getlist("class_ids")
    student_ids = form.getlist("student_ids")
    question_ids = form.getlist("question_ids")
    scores = form.getlist("scores")

    courses = db.query(models.Course).all()
    classes = db.query(models.ClassInfo).filter(models.ClassInfo.level == 3).all()
    students = db.query(models.User).filter(models.User.role == "student").all()
    questions = db.query(models.Question).filter(models.Question.status == "已发布").all()

    if not name:
        return templates.TemplateResponse("homework/create.html", {
            "request": request, "user": user, "courses": courses, "classes": classes,
            "students": students, "questions": questions, "error": "作业名称不能为空",
        })
    if not course_id:
        return templates.TemplateResponse("homework/create.html", {
            "request": request, "user": user, "courses": courses, "classes": classes,
            "students": students, "questions": questions, "error": "请选择所属课程",
        })

    hw = models.Homework(
        name=name,
        course_id=int(course_id),
        publish_time=parse_dt(publish_time),
        deadline=parse_dt(deadline),
        total_score=int(total_score) if total_score else 100,
        status="未发布",
    )
    db.add(hw)
    db.commit()
    for cid in class_ids:
        db.add(models.HomeworkClass(homework_id=hw.id, class_id=int(cid)))
    for sid in student_ids:
        pass
    for i, qid in enumerate(question_ids):
        sc = int(scores[i]) if i < len(scores) and scores[i] else 1
        db.add(models.HomeworkQuestion(homework_id=hw.id, question_id=int(qid), score=sc))
    db.commit()
    return RedirectResponse(url="/homework/", status_code=303)


@router.get("/edit/{hw_id}", response_class=HTMLResponse)
def edit_page(hw_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)
    if user.role not in ("admin", "teacher"):
        return templates.TemplateResponse("error.html", {"request": request, "user": user, "message": "无权限访问"})
    hw = db.query(models.Homework).filter(models.Homework.id == hw_id).first()
    courses = db.query(models.Course).all()
    classes = db.query(models.ClassInfo).filter(models.ClassInfo.level == 3).all()
    students = db.query(models.User).filter(models.User.role == "student").all()
    questions = db.query(models.Question).filter(models.Question.status == "已发布").all()
    selected_classes = [hc.class_id for hc in db.query(models.HomeworkClass).filter(models.HomeworkClass.homework_id == hw_id).all()]
    hw_questions = db.query(models.HomeworkQuestion).filter(models.HomeworkQuestion.homework_id == hw_id).all()
    return templates.TemplateResponse("homework/edit.html", {
        "request": request, "user": user, "hw": hw, "courses": courses, "classes": classes,
        "students": students, "questions": questions, "selected_classes": selected_classes,
        "hw_questions": hw_questions, "error": None,
    })


@router.post("/edit/{hw_id}")
async def edit_hw(hw_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user or user.role not in ("admin", "teacher"):
        return RedirectResponse("/auth/login", status_code=303)
    form = await request.form()
    hw = db.query(models.Homework).filter(models.Homework.id == hw_id).first()
    if not hw:
        return RedirectResponse(url="/homework/", status_code=303)
    hw.name = form.get("name", hw.name)
    hw.course_id = int(form.get("course_id", hw.course_id))
    hw.publish_time = parse_dt(form.get("publish_time", ""))
    hw.deadline = parse_dt(form.get("deadline", ""))
    ts = form.get("total_score", "100")
    hw.total_score = int(ts) if ts else 100
    db.query(models.HomeworkClass).filter(models.HomeworkClass.homework_id == hw_id).delete()
    db.query(models.HomeworkQuestion).filter(models.HomeworkQuestion.homework_id == hw_id).delete()
    for cid in form.getlist("class_ids"):
        db.add(models.HomeworkClass(homework_id=hw_id, class_id=int(cid)))
    question_ids = form.getlist("question_ids")
    scores = form.getlist("scores")
    for i, qid in enumerate(question_ids):
        sc = int(scores[i]) if i < len(scores) and scores[i] else 1
        db.add(models.HomeworkQuestion(homework_id=hw_id, question_id=int(qid), score=sc))
    db.commit()
    return RedirectResponse(url="/homework/", status_code=303)


@router.post("/publish/{hw_id}")
def publish(hw_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user or user.role not in ("admin", "teacher"):
        return JSONResponse({"error": "无权限"}, status_code=403)
    hw = db.query(models.Homework).filter(models.Homework.id == hw_id).first()
    if not hw:
        return JSONResponse({"error": "作业不存在"}, status_code=404)
    hw.status = "已发布"
    db.commit()
    return JSONResponse({"success": True})


@router.post("/delete/{hw_id}")
def delete(hw_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user or user.role not in ("admin", "teacher"):
        return JSONResponse({"error": "无权限"}, status_code=403)
    hw = db.query(models.Homework).filter(models.Homework.id == hw_id).first()
    if not hw:
        return JSONResponse({"error": "作业不存在"}, status_code=404)
    db.delete(hw)
    db.commit()
    return JSONResponse({"success": True})


@router.get("/manage", response_class=HTMLResponse)
def manage(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)
    if user.role not in ("admin", "teacher"):
        return templates.TemplateResponse("error.html", {"request": request, "user": user, "message": "无权限访问"})
    homeworks = db.query(models.Homework).filter(models.Homework.status == "已发布").all()
    return templates.TemplateResponse("homework/manage.html", {
        "request": request, "user": user, "homeworks": homeworks,
    })


@router.get("/manage/{hw_id}", response_class=HTMLResponse)
def manage_detail(hw_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)
    if user.role not in ("admin", "teacher"):
        return templates.TemplateResponse("error.html", {"request": request, "user": user, "message": "无权限访问"})
    hw = db.query(models.Homework).filter(models.Homework.id == hw_id).first()
    hw_questions = db.query(models.HomeworkQuestion).filter(models.HomeworkQuestion.homework_id == hw_id).all()
    class_ids = [hc.class_id for hc in db.query(models.HomeworkClass).filter(models.HomeworkClass.homework_id == hw_id).all()]
    students = db.query(models.User).filter(models.User.role == "student").all()
    student_list = []
    for s in students:
        submission = db.query(models.Submission).filter(
            models.Submission.homework_id == hw_id,
            models.Submission.student_id == s.id,
        ).first()
        sub_status = "未提交"
        if submission:
            sub_status = "未提交"
        student_list.append({
            "id": s.id,
            "username": s.username,
            "real_name": s.real_name,
            "status": sub_status,
            "grade": submission.total_score if submission else None,
        })
    return templates.TemplateResponse("homework/grade.html", {
        "request": request, "user": user, "hw": hw, "hw_questions": hw_questions,
        "students": student_list,
    })


@router.get("/grade/{hw_id}/{student_id}", response_class=HTMLResponse)
def grade_page(hw_id: int, student_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)
    if user.role not in ("admin", "teacher"):
        return templates.TemplateResponse("error.html", {"request": request, "user": user, "message": "无权限访问"})
    hw = db.query(models.Homework).filter(models.Homework.id == hw_id).first()
    student = db.query(models.User).filter(models.User.id == student_id).first()
    submission = db.query(models.Submission).filter(
        models.Submission.homework_id == hw_id,
        models.Submission.student_id == student_id,
    ).first()
    hw_questions = db.query(models.HomeworkQuestion).filter(models.HomeworkQuestion.homework_id == hw_id).all()
    answers = {}
    if submission:
        for a in submission.answers:
            answers[a.question_id] = a
    return templates.TemplateResponse("homework/grade_detail.html", {
        "request": request, "user": user, "hw": hw, "student": student,
        "submission": submission, "hw_questions": hw_questions, "answers": answers,
    })


@router.post("/grade/{hw_id}/{student_id}")
async def do_grade(hw_id: int, student_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user or user.role not in ("admin", "teacher"):
        return RedirectResponse("/auth/login", status_code=303)
    form = await request.form()
    submission = db.query(models.Submission).filter(
        models.Submission.homework_id == hw_id,
        models.Submission.student_id == student_id,
    ).first()
    if not submission:
        return RedirectResponse(url=f"/homework/manage/{hw_id}", status_code=303)
    total = 0
    hw_questions = db.query(models.HomeworkQuestion).filter(models.HomeworkQuestion.homework_id == hw_id).all()
    for hq in hw_questions:
        answer = db.query(models.Answer).filter(
            models.Answer.submission_id == submission.id,
            models.Answer.question_id == hq.question_id,
        ).first()
        if answer:
            score_key = f"score_{hq.question_id}"
            comment_key = f"comment_{hq.question_id}"
            s = form.get(score_key, "0")
            try:
                answer.score = int(s)
            except Exception:
                answer.score = 0
            answer.comment = form.get(comment_key, "")
            total += answer.score
    submission.total_score = total
    submission.status = "已批改"
    submission.grade_time = datetime.now()
    submission.comment = form.get("total_comment", "")
    db.commit()
    return RedirectResponse(url=f"/homework/manage/{hw_id}", status_code=303)


@router.get("/student", response_class=HTMLResponse)
def student_list(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)
    if user.role != "student":
        return templates.TemplateResponse("error.html", {"request": request, "user": user, "message": "无权限访问"})
    homeworks = db.query(models.Homework).filter(models.Homework.status == "已发布").all()
    my_class_ids = []
    if user.class_id:
        my_class_ids.append(user.class_id)
    visible = []
    for hw in homeworks:
        hw_classes = [hc.class_id for hc in hw.classes]
        if not hw_classes or set(hw_classes) & set(my_class_ids):
            submission = db.query(models.Submission).filter(
                models.Submission.homework_id == hw.id,
                models.Submission.student_id == user.id,
            ).first()
            visible.append({"hw": hw, "submission": submission})
    return templates.TemplateResponse("homework/student.html", {
        "request": request, "user": user, "items": visible,
    })


@router.get("/answer/{hw_id}", response_class=HTMLResponse)
def answer_page(hw_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)
    if user.role != "student":
        return templates.TemplateResponse("error.html", {"request": request, "user": user, "message": "无权限访问"})
    hw = db.query(models.Homework).filter(models.Homework.id == hw_id).first()
    hw_questions = db.query(models.HomeworkQuestion).filter(models.HomeworkQuestion.homework_id == hw_id).all()
    submission = db.query(models.Submission).filter(
        models.Submission.homework_id == hw_id,
        models.Submission.student_id == user.id,
    ).first()
    answers = {}
    if submission:
        for a in submission.answers:
            answers[a.question_id] = a.content
    return templates.TemplateResponse("homework/answer.html", {
        "request": request, "user": user, "hw": hw, "hw_questions": hw_questions,
        "submission": submission, "answers": answers,
    })


@router.post("/answer/{hw_id}")
async def submit_answer(hw_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user or user.role != "student":
        return RedirectResponse("/auth/login", status_code=303)
    form = await request.form()
    action = form.get("action", "submit")
    hw = db.query(models.Homework).filter(models.Homework.id == hw_id).first()
    if not hw:
        return RedirectResponse(url="/homework/student", status_code=303)
    submission = db.query(models.Submission).filter(
        models.Submission.homework_id == hw_id,
        models.Submission.student_id == user.id,
    ).first()
    if not submission:
        submission = models.Submission(
            homework_id=hw_id, student_id=user.id, status="未提交",
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)
    db.query(models.Answer).filter(models.Answer.submission_id == submission.id).delete()
    hw_questions = db.query(models.HomeworkQuestion).filter(models.HomeworkQuestion.homework_id == hw_id).all()
    for hq in hw_questions:
        content = form.get(f"q_{hq.question_id}", "")
        answer = models.Answer(
            submission_id=submission.id,
            question_id=hq.question_id,
            content=content,
            score=0,
        )
        db.add(answer)
    if action == "submit":
        submission.status = "已提交"
        submission.submit_time = datetime.now()
        for hq in hw_questions:
            answer = db.query(models.Answer).filter(
                models.Answer.submission_id == submission.id,
                models.Answer.question_id == hq.question_id,
            ).first()
            if answer and hq.question:
                qtype = hq.question.type
                if qtype in ("单选", "多选", "判断"):
                    if answer.content.strip() == hq.question.answer.lower():
                        answer.score = hq.score
                        answer.is_correct = True
                    else:
                        answer.score = 0
                        answer.is_correct = False
    db.commit()
    return RedirectResponse(url="/homework/student", status_code=303)


@router.get("/history", response_class=HTMLResponse)
def history(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)
    if user.role not in ("admin", "teacher"):
        return templates.TemplateResponse("error.html", {"request": request, "user": user, "message": "无权限访问"})
    homeworks = db.query(models.Homework).all()
    return templates.TemplateResponse("homework/history.html", {
        "request": request, "user": user, "homeworks": homeworks,
    })


@router.get("/result/{hw_id}", response_class=HTMLResponse)
def result(hw_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)
    if user.role != "student":
        return templates.TemplateResponse("error.html", {"request": request, "user": user, "message": "无权限访问"})
    hw = db.query(models.Homework).filter(models.Homework.id == hw_id).first()
    submission = db.query(models.Submission).filter(
        models.Submission.homework_id == hw_id,
        models.Submission.student_id == user.id,
    ).first()
    hw_questions = db.query(models.HomeworkQuestion).filter(models.HomeworkQuestion.homework_id == hw_id).all()
    answers = {}
    if submission:
        for a in submission.answers:
            answers[a.question_id] = a
    return templates.TemplateResponse("homework/result.html", {
        "request": request, "user": user, "hw": hw, "submission": submission,
        "hw_questions": hw_questions, "answers": answers,
    })
