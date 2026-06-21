from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(200), nullable=False)
    real_name = Column(String(50))
    role = Column(String(20), nullable=False, default="student")
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=True)
    status = Column(String(20), default="可用")
    remark = Column(String(100))
    id_card = Column(String(20))
    address = Column(String(100))
    phone = Column(String(11))
    gender = Column(String(10))
    emergency_contact = Column(String(20))
    emergency_phone = Column(String(20))
    photo = Column(String(200))
    enroll_date = Column(String(20))
    leave_date = Column(String(20))
    nation = Column(String(20))
    work_status = Column(String(20))
    detail_remark = Column(String(200))
    created_at = Column(DateTime, default=datetime.now)

    class_ = relationship("ClassInfo", back_populates="users")


class ClassInfo(Base):
    __tablename__ = "classes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(30), nullable=False)
    parent_id = Column(Integer, ForeignKey("classes.id"), nullable=True)
    level = Column(Integer, default=1)
    sort_no = Column(Integer, nullable=True)
    status = Column(String(20), default="可用")
    remark = Column(String(100))

    parent = relationship("ClassInfo", remote_side=[id], backref="children")
    users = relationship("User", back_populates="class_")
    courses = relationship("CourseClass", back_populates="class_")


class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    description = Column(String(200))
    teacher_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.now)

    teacher = relationship("User", foreign_keys=[teacher_id])
    classes = relationship("CourseClass", back_populates="course")
    questions = relationship("Question", back_populates="course")
    homeworks = relationship("Homework", back_populates="course")


class CourseClass(Base):
    __tablename__ = "course_classes"
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    class_id = Column(Integer, ForeignKey("classes.id"))

    course = relationship("Course", back_populates="classes")
    class_ = relationship("ClassInfo", back_populates="courses")


class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    option_a = Column(String(200))
    option_b = Column(String(200))
    option_c = Column(String(200))
    option_d = Column(String(200))
    option_e = Column(String(200))
    answer = Column(String(500), nullable=False)
    score = Column(Integer, default=1)
    difficulty = Column(String(20), default="简单")
    course_id = Column(Integer, ForeignKey("courses.id"))
    remark = Column(String(100))
    status = Column(String(20), default="未审核")
    creator = Column(String(50))
    reject_reason = Column(String(200))
    created_at = Column(DateTime, default=datetime.now)

    course = relationship("Course", back_populates="questions")
    homework_questions = relationship("HomeworkQuestion", back_populates="question")


class Homework(Base):
    __tablename__ = "homeworks"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"))
    publish_time = Column(DateTime)
    deadline = Column(DateTime)
    total_score = Column(Integer, default=100)
    status = Column(String(20), default="未发布")
    created_at = Column(DateTime, default=datetime.now)

    course = relationship("Course", back_populates="homeworks")
    questions = relationship("HomeworkQuestion", back_populates="homework")
    classes = relationship("HomeworkClass", back_populates="homework")
    submissions = relationship("Submission", back_populates="homework")


class HomeworkQuestion(Base):
    __tablename__ = "homework_questions"
    id = Column(Integer, primary_key=True, index=True)
    homework_id = Column(Integer, ForeignKey("homeworks.id"))
    question_id = Column(Integer, ForeignKey("questions.id"))
    score = Column(Integer, default=1)

    homework = relationship("Homework", back_populates="questions")
    question = relationship("Question", back_populates="homework_questions")


class HomeworkClass(Base):
    __tablename__ = "homework_classes"
    id = Column(Integer, primary_key=True, index=True)
    homework_id = Column(Integer, ForeignKey("homeworks.id"))
    class_id = Column(Integer, ForeignKey("classes.id"))

    homework = relationship("Homework", back_populates="classes")
    class_ = relationship("ClassInfo")


class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True, index=True)
    homework_id = Column(Integer, ForeignKey("homeworks.id"))
    student_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String(20), default="未提交")
    submit_time = Column(DateTime)
    grade_time = Column(DateTime)
    total_score = Column(Integer)
    comment = Column(Text)

    homework = relationship("Homework", back_populates="submissions")
    student = relationship("User", foreign_keys=[student_id])
    answers = relationship("Answer", back_populates="submission")


class Answer(Base):
    __tablename__ = "answers"
    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"))
    question_id = Column(Integer, ForeignKey("questions.id"))
    content = Column(Text)
    score = Column(Integer, default=0)
    comment = Column(String(200))
    is_correct = Column(Boolean, default=False)

    submission = relationship("Submission", back_populates="answers")
    question = relationship("Question")
