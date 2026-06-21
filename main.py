from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from database import init_db, SessionLocal
import models
import auth
from routers import auth as auth_router
from routers import classes, users, courses, questions, homework

app = FastAPI(title="在线课程作业管理系统")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(auth_router.router)
app.include_router(classes.router)
app.include_router(users.router)
app.include_router(courses.router)
app.include_router(questions.router)
app.include_router(homework.router)


@app.on_event("startup")
def startup():
    init_db()
    db = SessionLocal()
    try:
        if db.query(models.User).count() == 0:
            import seed
            seed.run_seed(db)
    finally:
        db.close()


@app.get("/")
def index(request: Request):
    user = auth.get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)
    return RedirectResponse("/dashboard", status_code=303)


@app.get("/dashboard")
def dashboard(request: Request):
    user = auth.get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)
    db = SessionLocal()
    try:
        stats = {
            "user_count": db.query(models.User).count(),
            "class_count": db.query(models.ClassInfo).count(),
            "course_count": db.query(models.Course).count(),
            "question_count": db.query(models.Question).count(),
            "homework_count": db.query(models.Homework).count(),
        }
    finally:
        db.close()
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user, "stats": stats})
