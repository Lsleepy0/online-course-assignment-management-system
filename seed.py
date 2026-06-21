from database import SessionLocal
import models
from auth import hash_password
from datetime import datetime


def run_seed(db):
    admin = models.User(
        username="admin",
        password=hash_password("111111"),
        real_name="系统管理员",
        role="admin",
        status="可用",
    )
    teacher = models.User(
        username="teacher1",
        password=hash_password("111111"),
        real_name="张老师",
        role="teacher",
        status="可用",
    )
    db.add_all([admin, teacher])
    db.commit()

    branches = ["北京分部", "上海分部", "广州分部"]
    majors = ["计算机科学与技术", "软件工程"]
    classes = ["一班", "二班"]
    student_class_id = None
    for b in branches:
        branch = models.ClassInfo(name=b, parent_id=None, level=1, sort_no=1, status="可用", remark="分部")
        db.add(branch)
        db.commit()
        for m in majors:
            major = models.ClassInfo(name=m, parent_id=branch.id, level=2, sort_no=1, status="可用", remark="专业")
            db.add(major)
            db.commit()
            for c in classes:
                cls = models.ClassInfo(name=c, parent_id=major.id, level=3, sort_no=1, status="可用", remark="班级")
                db.add(cls)
                db.commit()
                if student_class_id is None and b == "北京分部" and m == "计算机科学与技术" and c == "一班":
                    student_class_id = cls.id

    student = models.User(
        username="student1",
        password=hash_password("111111"),
        real_name="李同学",
        role="student",
        class_id=student_class_id,
        status="可用",
    )
    db.add(student)
    db.commit()

    course1 = models.Course(name="Python程序设计", description="Python基础与应用开发", teacher_id=teacher.id)
    course2 = models.Course(name="数据结构", description="数据结构与算法基础", teacher_id=teacher.id)
    db.add_all([course1, course2])
    db.commit()

    questions = [
        models.Question(
            type="单选",
            content="Python中用于输出的是哪个函数？",
            option_a="echo()",
            option_b="print()",
            option_c="console.log()",
            option_d="printf()",
            answer="B",
            score=10,
            difficulty="简单",
            course_id=course1.id,
            status="已发布",
            creator="teacher1",
        ),
        models.Question(
            type="多选",
            content="下列哪些是Python的基本数据类型？",
            option_a="int",
            option_b="str",
            option_c="list",
            option_d="dict",
            option_e="array",
            answer="ABCD",
            score=15,
            difficulty="中等",
            course_id=course1.id,
            status="已发布",
            creator="teacher1",
        ),
        models.Question(
            type="判断",
            content="Python是解释型语言。",
            answer="正确",
            score=5,
            difficulty="简单",
            course_id=course1.id,
            status="已发布",
            creator="teacher1",
        ),
        models.Question(
            type="填空",
            content="Python中定义函数使用的关键字是____。",
            answer="def",
            score=5,
            difficulty="简单",
            course_id=course1.id,
            status="已发布",
            creator="teacher1",
        ),
        models.Question(
            type="简答",
            content="简述Python中列表和元组的区别。",
            answer="列表可变，元组不可变；列表用[]定义，元组用()定义。",
            score=20,
            difficulty="中等",
            course_id=course2.id,
            status="已发布",
            creator="teacher1",
        ),
    ]
    db.add_all(questions)
    db.commit()

    print("预置数据初始化完成")
