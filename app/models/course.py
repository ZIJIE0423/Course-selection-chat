from sqlalchemy import Column, Integer, String, Text, Float, DateTime
from sqlalchemy.sql import func
from app.database.mysql import Base

class Course(Base):
    __tablename__ = "courses"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False) # 课程代码
    name = Column(String(255), index=True, nullable=False)             # 课程名称
    credit = Column(Float, nullable=True)                              # 学分
    semester = Column(String(50), nullable=True)                       # 开课学期
    department = Column(String(255), nullable=True)                    # 院系
    teachers = Column(String(255), nullable=True)                      # 授课教师
    course_level = Column(String(50), nullable=True)                   # 课程层面
    description = Column(Text, nullable=True)                          # 课程描述
    objectives = Column(Text, nullable=True)                           # 学习目标
    data_source = Column(String(255), nullable=True)                   # 数据来源
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now()) # 更新时间

class Programme(Base):
    __tablename__ = "programmes"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True)                 # 专业代码
    name = Column(String(255), nullable=False)                         # 专业名称
    department = Column(String(255), nullable=True)                    # 所属学院
    stage = Column(String(50), nullable=True)                          # 阶段信息

class CourseRequirement(Base):
    __tablename__ = "course_requirements"
    
    id = Column(Integer, primary_key=True, index=True)
    programme = Column(String(255), nullable=True)                     # 专业
    stage = Column(String(50), nullable=True)                          # 阶段
    requirement_type = Column(String(50), nullable=True)               # 必修/选修
    course_code = Column(String(50), index=True, nullable=False)       # 课程代码
    credit_requirement = Column(Float, nullable=True)                  # 学分要求
