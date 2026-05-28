import os
import re
import sys
from pathlib import Path

# Add the project root to sys.path so we can import app modules
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from app.database.mysql import SessionLocal, Base, engine
from app.models.course import Course, Programme, CourseRequirement

def parse_md_table(filepath):
    """
    解析 Markdown 文件中的表格，返回字典列表
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    tables = []
    current_table = []
    in_table = False
    
    for line in lines:
        line = line.strip()
        if line.startswith('|') and line.endswith('|'):
            if not in_table:
                in_table = True
            current_table.append(line)
        else:
            if in_table:
                tables.append(current_table)
                current_table = []
                in_table = False
    
    if current_table:
        tables.append(current_table)

    all_data = []
    for table in tables:
        if len(table) < 3:
            continue
        
        headers = [col.strip() for col in table[0].strip('|').split('|')]
        # Skip the separator line
        for row in table[2:]:
            cols = [col.strip() for col in row.strip('|').split('|')]
            # Handle cases where cols might be fewer than headers due to empty trailing cells
            if len(cols) < len(headers):
                cols.extend([''] * (len(headers) - len(cols)))
            elif len(cols) > len(headers):
                cols = cols[:len(headers)]
            
            row_data = dict(zip(headers, cols))
            all_data.append(row_data)
            
    return all_data

def main():
    print("正在初始化数据库表...")
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"数据库连接失败，请检查 .env 配置或 MySQL 服务是否启动: {e}")
        return

    data_dir = project_root / '数据文件'
    if not data_dir.exists():
        print(f"错误: 数据目录不存在 {data_dir}")
        return

    courses_dict = {} # key: course_code, value: course_data_dict

    # 1. 解析 官方选课信息_结构化数据_评价参考适配版.md
    file1 = data_dir / '官方选课信息_结构化数据_评价参考适配版.md'
    if file1.exists():
        print(f"正在读取 {file1.name}...")
        data1 = parse_md_table(file1)
        for row in data1:
            code = row.get('课程编号')
            if not code:
                continue
            
            name = row.get('课程名称', '')
            semester = row.get('学年学期', '')
            level = row.get('课程层面', '')
            teacher = row.get('授课教师', '')
            dept = row.get('上课院系', '')
            source = row.get('来源截图', '')
            
            if code not in courses_dict:
                courses_dict[code] = {
                    'code': code,
                    'name': name,
                    'semester': semester,
                    'course_level': level,
                    'teachers': set(),
                    'department': dept,
                    'data_source': file1.name,
                    'credit': None
                }
            if teacher:
                courses_dict[code]['teachers'].add(teacher)
            # Update semester if multiple are available (simple comma separation)
            if semester and semester not in courses_dict[code]['semester']:
                courses_dict[code]['semester'] += f", {semester}" if courses_dict[code]['semester'] else semester

    # 2. 解析 培养方案.md
    file2 = data_dir / '培养方案.md'
    if file2.exists():
        print(f"正在读取 {file2.name}...")
        data2 = parse_md_table(file2)
        for row in data2:
            code = row.get('课程编号')
            if not code or code == '课程编号': # Skip invalid
                continue
                
            name = row.get('课程名称', '')
            credit_str = row.get('学分', '0')
            try:
                credit = float(credit_str)
            except ValueError:
                credit = None
                
            semester = row.get('开设学期', '')
            
            if code not in courses_dict:
                courses_dict[code] = {
                    'code': code,
                    'name': name,
                    'semester': f"第{semester}学期" if semester else "",
                    'course_level': row.get('体系', ''),
                    'teachers': set(),
                    'department': '',
                    'data_source': file2.name,
                    'credit': credit
                }
            else:
                if credit is not None and courses_dict[code]['credit'] is None:
                    courses_dict[code]['credit'] = credit
                if semester and "学期" not in courses_dict[code]['semester']:
                    courses_dict[code]['semester'] += f" (推荐第{semester}学期)"

    db = SessionLocal()
    
    total_read = len(courses_dict)
    success_count = 0
    skip_count = 0
    fail_count = 0
    
    print(f"共识别到 {total_read} 门不重复课程，开始导入...")
    
    for code, data in courses_dict.items():
        try:
            # Join teachers
            teachers_str = ", ".join(filter(None, data['teachers']))
            
            # Check if exists
            existing = db.query(Course).filter(Course.code == code).first()
            if existing:
                # Update existing
                existing.name = data['name'] or existing.name
                existing.credit = data['credit'] if data['credit'] is not None else existing.credit
                existing.semester = data['semester'] or existing.semester
                existing.department = data['department'] or existing.department
                existing.teachers = teachers_str or existing.teachers
                existing.course_level = data['course_level'] or existing.course_level
                skip_count += 1
            else:
                new_course = Course(
                    code=code,
                    name=data['name'],
                    credit=data['credit'],
                    semester=data['semester'],
                    department=data['department'],
                    teachers=teachers_str,
                    course_level=data['course_level'],
                    data_source=data['data_source']
                )
                db.add(new_course)
                success_count += 1
                
        except Exception as e:
            print(f"导入课程 {code} 失败: {e}")
            fail_count += 1
            db.rollback()

    try:
        db.commit()
        print("\n=== 导入统计 ===")
        print(f"识别总数: {total_read}")
        print(f"成功新增: {success_count}")
        print(f"成功更新(跳过新增): {skip_count}")
        print(f"失败条数: {fail_count}")
    except Exception as e:
        print(f"提交数据库失败: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
