from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity, exceptions as jwt_exceptions
from sqlalchemy import func, or_
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask import current_app
import logging
import functools # Import functools for @wraps
import os
import sys
try:
    import openai
except ImportError:
    openai = None
from openai import OpenAI
import requests
from functools import wraps

# 确保Python正确处理UTF-8编码
if sys.version_info[0] >= 3:
    # Python 3 默认支持UTF-8，但确保环境变量设置正确
    import locale
    try:
        locale.setlocale(locale.LC_ALL, 'zh_CN.UTF-8')
    except:
        try:
            locale.setlocale(locale.LC_ALL, 'C.UTF-8')
        except:
            pass

# 配置日志，支持UTF-8编码
try:
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', encoding='utf-8')
except TypeError:
    # Python 3.9以下版本不支持encoding参数
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

from ..models import User, Student, Teacher, Course, Grade, Role
from .. import db
from app.models import Student, Grade

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Decorator to check if user is admin
def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or user.role != Role.ADMIN:
            return jsonify({'code': 1, 'msg': '无权限访问'}), 403
        return fn(*args, **kwargs)
    return wrapper

# ===============================================
# 仪表盘路由
# ===============================================

@admin_bp.route('/')
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """管理员仪表盘页面"""
    # 统计数据，用于直接渲染到仪表盘卡片
    total_students = Student.query.count()
    total_teachers = Teacher.query.count()
    total_courses = Course.query.count() # 新增
    total_grades = Grade.query.count() # 新增

    return render_template('admin/dashboard.html',
                           total_students=total_students,
                           total_teachers=total_teachers,
                           total_courses=total_courses,
                           total_grades=total_grades)

@admin_bp.route('/api/dashboard_data', methods=['GET'])
@admin_required
def get_dashboard_data():
    """获取仪表盘图表数据API"""
    try:
        # 课程分数分布饼图数据 (假设分数在0-100之间)
        score_bins = {
            '不及格 (0-59)': 0,
            '及格 (60-74)': 0,
            '良好 (75-89)': 0,
            '优秀 (90-100)': 0
        }
        all_grades = Grade.query.filter(Grade.score.isnot(None)).all()  # 过滤掉空值
        for grade in all_grades:
            if grade.score < 60:
                score_bins['不及格 (0-59)'] += 1
            elif grade.score < 75:
                score_bins['及格 (60-74)'] += 1
            elif grade.score < 90:
                score_bins['良好 (75-89)'] += 1
            else:
                score_bins['优秀 (90-100)'] += 1
        course_score_distribution_data = [{'label': k, 'count': v} for k, v in score_bins.items()]

        # 学生生源地柱状图数据
        hometown_stats = db.session.query(
            Student.hometown,
            func.count(Student.id)
        ).group_by(Student.hometown).order_by(func.count(Student.id).desc()).all() # 按数量降序
        hometowns = [hometown for hometown, _ in hometown_stats]
        student_counts_by_hometown = [count for _, count in hometown_stats]

        # 各专业平均成绩
        majors_avg = db.session.query(
            Student.major,
            func.avg(Grade.score)
        ).join(Grade, Student.id == Grade.student_id).filter(Grade.score.isnot(None)).group_by(Student.major).all()

        majors_avg_name = [major for major, _ in majors_avg]
        majors_avg_score = [round(float(avg), 2) for _, avg in majors_avg]

        # 学生各科成绩雷达图数据（以第一个学生为例，如果需要选择学生，前端可以再发请求）
        first_student = Student.query.first()
        first_student_name = first_student.name if first_student else '暂无学生'
        radar_courses = []
        radar_scores = []
        if first_student:
            # 过滤掉分数为 None 的成绩
            student_grades = Grade.query.filter_by(student_id=first_student.id).filter(Grade.score.isnot(None)).join(Course).all()
            for sg in student_grades:
                radar_courses.append(sg.course.name)
                radar_scores.append(sg.score)

        return jsonify({
            'code': 0,
            'msg': '数据获取成功',
            'course_score_distribution': {'scores': course_score_distribution_data},
            'hometowns': hometowns,
            'student_counts': student_counts_by_hometown,
            'majors_avg_name': majors_avg_name,
            'majors_avg_score': majors_avg_score,
            'first_student_name': first_student_name,
            'radar_courses': radar_courses,
            'radar_scores': radar_scores
        })
    except Exception as e:
        logging.error(f"获取仪表盘数据失败: {e}", exc_info=True)
        return jsonify({'code': 1, 'msg': f'获取仪表盘数据失败: {str(e)}'}), 500

# ===============================================
# 学生管理路由
# ===============================================

@admin_bp.route('/manage_students_layui')
@admin_required
def manage_students_layui():
    """学生管理页面"""
    # 获取筛选选项数据
    majors = db.session.query(Student.major).distinct().all()
    majors = [major[0] for major in majors if major[0]]
    
    classes = db.session.query(Student.class_name).distinct().all()
    classes = [class_name[0] for class_name in classes if class_name[0]]
    
    hometowns = db.session.query(Student.hometown).distinct().all()
    hometowns = [hometown[0] for hometown in hometowns if hometown[0]]
    
    return render_template('admin/students_layui.html', 
                         majors=majors, 
                         classes=classes, 
                         hometowns=hometowns)

@admin_bp.route('/api/students', methods=['GET'])
@admin_required
def get_students_api_route():
    """获取学生列表API (LayUI table 数据源)"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    keyword = request.args.get('keyword', '', type=str)
    major_filter = request.args.get('major', '', type=str)
    class_filter = request.args.get('class_name', '', type=str) # Changed from 'student_class' to 'class_name' to match model

    query = db.session.query(Student)

    if keyword:
        query = query.filter(
            (Student.student_id.like(f'%{keyword}%')) |
            (Student.name.like(f'%{keyword}%'))
        )
    if major_filter:
        query = query.filter(Student.major == major_filter)
    if class_filter:
        query = query.filter(Student.class_name == class_filter)

    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    students = pagination.items

    return jsonify({
        'code': 0,
        'msg': '',
        'count': pagination.total,
        'data': [s.to_dict() for s in students]
    })

@admin_bp.route('/api/students', methods=['POST'])
@admin_required
def create_student_api_route():
    """创建新学生API"""
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'msg': '请求数据为空'}), 400

    required_fields = ['name', 'student_id', 'gender', 'birthdate', 'major', 'enrollment_date']
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({'code': 1, 'msg': f'缺少必要字段: {field}'}), 400

    if Student.query.filter_by(student_id=data['student_id']).first():
        return jsonify({'code': 1, 'msg': '学号已存在'}), 400

    try:
        new_student = Student(
            name=data['name'],
            student_id=data['student_id'],
            gender=data['gender'],
            birthdate=datetime.strptime(data['birthdate'], '%Y-%m-%d').date(),
            major=data['major'],
            enrollment_date=datetime.strptime(data['enrollment_date'], '%Y-%m-%d').date(),
            hometown=data.get('hometown'),
            class_name=data.get('class_name') # 新增班级
        )
        db.session.add(new_student)
        db.session.commit()
        return jsonify({'code': 0, 'msg': '学生添加成功', 'data': new_student.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        logging.error(f"创建学生失败: {e}", exc_info=True)
        return jsonify({'code': 1, 'msg': f'创建学生失败: {str(e)}'}), 500

@admin_bp.route('/api/students/<int:student_id>', methods=['GET'])
@admin_required
def get_student_api_route(student_id):
    """获取单个学生详情API"""
    student = Student.query.get(student_id)
    if not student:
        return jsonify({'code': 1, 'msg': '学生未找到'}), 404
    return jsonify({'code': 0, 'msg': '成功', 'data': student.to_dict()})

@admin_bp.route('/api/students/<int:student_id>', methods=['PUT'])
@admin_required
def update_student_api_route(student_id):
    """更新学生信息API"""
    student = Student.query.get(student_id)
    if not student:
        return jsonify({'code': 1, 'msg': '学生未找到'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'msg': '请求数据为空'}), 400

    try:
        if 'student_id' in data and data['student_id'] != student.student_id and \
           Student.query.filter_by(student_id=data['student_id']).first():
            return jsonify({'code': 1, 'msg': '学号已存在'}), 400

        student.name = data.get('name', student.name)
        student.student_id = data.get('student_id', student.student_id)
        student.gender = data.get('gender', student.gender)
        student.major = data.get('major', student.major)
        student.hometown = data.get('hometown', student.hometown)
        student.class_name = data.get('class_name', student.class_name)

        if 'birthdate' in data and data['birthdate']:
            student.birthdate = datetime.strptime(data['birthdate'], '%Y-%m-%d').date()
        elif 'birthdate' in data and not data['birthdate']: # 允许清空
             student.birthdate = None

        if 'enrollment_date' in data and data['enrollment_date']:
            student.enrollment_date = datetime.strptime(data['enrollment_date'], '%Y-%m-%d').date()
        elif 'enrollment_date' in data and not data['enrollment_date']: # 允许清空
            student.enrollment_date = None

        db.session.commit()
        return jsonify({'code': 0, 'msg': '学生信息更新成功', 'data': student.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"更新学生失败: {e}", exc_info=True)
        return jsonify({'code': 1, 'msg': f'更新学生失败: {str(e)}'}), 500

@admin_bp.route('/api/students/<int:student_id>', methods=['POST', 'DELETE'])
@admin_required
def delete_student_api_route(student_id):
    """删除学生API"""
    student = Student.query.get(student_id)
    if not student:
        return jsonify({'code': 1, 'msg': '学生未找到'}), 404

    try:
        db.session.delete(student)
        db.session.commit()
        return jsonify({'code': 0, 'msg': '学生删除成功'}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"删除学生失败: {e}", exc_info=True)
        return jsonify({'code': 1, 'msg': f'删除学生失败: {str(e)}'}), 500

@admin_bp.route('/api/students/batch_delete', methods=['POST'])
@admin_required
def batch_delete_students_api_route():
    """批量删除学生API"""
    data = request.get_json()
    ids = data.get('ids', [])
    if not ids:
        return jsonify({'code': 1, 'msg': '请提供要删除的学生ID'}), 400

    try:
        deleted_count = Student.query.filter(Student.id.in_(ids)).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({'code': 0, 'msg': f'成功删除 {deleted_count} 条学生记录'}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"批量删除学生失败: {e}", exc_info=True)
        return jsonify({'code': 1, 'msg': f'批量删除失败: {str(e)}'}), 500

# ===============================================
# 教师管理路由
# ===============================================

@admin_bp.route('/manage_teachers_layui')
@admin_required
def manage_teachers_layui():
    """教师管理页面"""
    # 获取筛选选项数据
    departments = db.session.query(Teacher.department).distinct().all()
    departments = [dept[0] for dept in departments if dept[0]]
    
    return render_template('admin/teachers.html', departments=departments)

@admin_bp.route('/api/teachers', methods=['GET'])
@admin_required
def get_teachers_api_route():
    """获取教师列表API (LayUI table 数据源)"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    keyword = request.args.get('keyword', '', type=str)
    department_filter = request.args.get('department', '', type=str) # Changed from 'major' to 'department' to match model

    query = db.session.query(Teacher)

    if keyword:
        query = query.filter(
            (Teacher.teacher_id.like(f'%{keyword}%')) |
            (Teacher.name.like(f'%{keyword}%'))
        )
    if department_filter:
        query = query.filter(Teacher.department == department_filter)

    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    teachers = pagination.items

    return jsonify({
        'code': 0,
        'msg': '',
        'count': pagination.total,
        'data': [t.to_dict() for t in teachers]
    })

@admin_bp.route('/api/teachers', methods=['POST'])
@admin_required
def create_teacher_api_route():
    """创建新教师API"""
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'msg': '请求数据为空'}), 400

    required_fields = ['name', 'teacher_id', 'gender', 'title', 'department']
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({'code': 1, 'msg': f'缺少必要字段: {field}'}), 400

    if Teacher.query.filter_by(teacher_id=data['teacher_id']).first():
        return jsonify({'code': 1, 'msg': '工号已存在'}), 400

    try:
        new_teacher = Teacher(
            name=data['name'],
            teacher_id=data['teacher_id'],
            gender=data['gender'],
            title=data['title'],
            department=data['department']
        )
        db.session.add(new_teacher)
        db.session.commit()
        return jsonify({'code': 0, 'msg': '教师添加成功', 'data': new_teacher.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        logging.error(f"创建教师失败: {e}", exc_info=True)
        return jsonify({'code': 1, 'msg': f'创建教师失败: {str(e)}'}), 500

@admin_bp.route('/api/teachers/<int:teacher_id>', methods=['GET'])
@admin_required
def get_teacher_api_route(teacher_id):
    """获取单个教师详情API"""
    teacher = Teacher.query.get(teacher_id)
    if not teacher:
        return jsonify({'code': 1, 'msg': '教师未找到'}), 404
    return jsonify({'code': 0, 'msg': '成功', 'data': teacher.to_dict()})

@admin_bp.route('/api/teachers/<int:teacher_id>', methods=['PUT'])
@admin_required
def update_teacher_api_route(teacher_id):
    """更新教师信息API"""
    teacher = Teacher.query.get(teacher_id)
    if not teacher:
        return jsonify({'code': 1, 'msg': '教师未找到'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'msg': '请求数据为空'}), 400

    try:
        if 'teacher_id' in data and data['teacher_id'] != teacher.teacher_id and \
           Teacher.query.filter_by(teacher_id=data['teacher_id']).first():
            return jsonify({'code': 1, 'msg': '工号已存在'}), 400

        teacher.name = data.get('name', teacher.name)
        teacher.teacher_id = data.get('teacher_id', teacher.teacher_id)
        teacher.gender = data.get('gender', teacher.gender)
        teacher.title = data.get('title', teacher.title)
        teacher.department = data.get('department', teacher.department)

        db.session.commit()
        return jsonify({'code': 0, 'msg': '教师信息更新成功', 'data': teacher.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"更新教师失败: {e}", exc_info=True)
        return jsonify({'code': 1, 'msg': f'更新教师失败: {str(e)}'}), 500

@admin_bp.route('/api/teachers/<int:teacher_id>', methods=['POST', 'DELETE'])
@admin_required
def delete_teacher_api_route(teacher_id):
    """删除教师API"""
    teacher = Teacher.query.get(teacher_id)
    if not teacher:
        return jsonify({'code': 1, 'msg': '教师未找到'}), 404

    try:
        db.session.delete(teacher)
        db.session.commit()
        return jsonify({'code': 0, 'msg': '教师删除成功'}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"删除教师失败: {e}", exc_info=True)
        return jsonify({'code': 1, 'msg': f'删除教师失败: {str(e)}'}), 500

@admin_bp.route('/api/teachers/batch_delete', methods=['POST'])
@admin_required
def batch_delete_teachers_api_route():
    """批量删除教师API"""
    data = request.get_json()
    ids = data.get('ids', [])
    if not ids:
        return jsonify({'code': 1, 'msg': '请提供要删除的教师ID'}), 400

    try:
        deleted_count = Teacher.query.filter(Teacher.id.in_(ids)).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({'code': 0, 'msg': f'成功删除 {deleted_count} 条教师记录'}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"批量删除教师失败: {e}", exc_info=True)
        return jsonify({'code': 1, 'msg': f'批量删除失败: {str(e)}'}), 500

# ===============================================
# 课程管理路由 (更新为使用通用表单)
# ===============================================

@admin_bp.route('/manage_courses_layui')
@admin_required
def manage_courses_layui():
    """课程管理页面"""
    teachers = Teacher.query.all()
    return render_template('admin/courses_layui.html', teachers=teachers) # 传递教师列表

@admin_bp.route('/api/courses', methods=['GET'])
@admin_required
def get_courses_api_route():
    """获取课程列表API (LayUI table 数据源)"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    keyword = request.args.get('keyword', '', type=str)
    teacher_id_filter = request.args.get('teacher_id', type=int) # 新增教师筛选

    query = db.session.query(Course)

    if keyword:
        query = query.filter(Course.name.like(f'%{keyword}%') | Course.course_id.like(f'%{keyword}%'))

    if teacher_id_filter:
        query = query.filter(Course.teacher_id == teacher_id_filter)

    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    courses = pagination.items

    data = []
    for course in courses:
        course_dict = course.to_dict()
        if course.teacher:
            course_dict['teacher_name'] = course.teacher.name
        else:
            course_dict['teacher_name'] = '未指定'
        data.append(course_dict)

    return jsonify({
        'code': 0,
        'msg': '',
        'count': pagination.total,
        'data': data
    })

@admin_bp.route('/api/courses', methods=['POST'])
@admin_required
def create_course_api_route():
    """创建新课程API"""
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'msg': '请求数据为空'}), 400

    required_fields = ['name', 'course_id', 'credits']
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({'code': 1, 'msg': f'缺少必要字段: {field}'}), 400

    if Course.query.filter_by(course_id=data['course_id']).first():
        return jsonify({'code': 1, 'msg': '课程代码已存在'}), 400

    try:
        new_course = Course(
            name=data['name'],
            course_id=data['course_id'],
            credits=int(data['credits']),
            description=data.get('description'),
            teacher_id=data.get('teacher_id')
        )
        db.session.add(new_course)
        db.session.commit()
        return jsonify({'code': 0, 'msg': '课程添加成功', 'data': new_course.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        logging.error(f"创建课程失败: {e}", exc_info=True)
        return jsonify({'code': 1, 'msg': f'创建课程失败: {str(e)}'}), 500

@admin_bp.route('/api/courses/<int:course_id>', methods=['GET'])
@admin_required
def get_course_api_route(course_id):
    """获取单个课程详情API"""
    course = Course.query.get(course_id)
    if not course:
        return jsonify({'code': 1, 'msg': '课程未找到'}), 404
    return jsonify({'code': 0, 'msg': '成功', 'data': course.to_dict()})

@admin_bp.route('/api/courses/<int:course_id>', methods=['PUT'])
@admin_required
def update_course_api_route(course_id):
    """更新课程信息API"""
    course = Course.query.get(course_id)
    if not course:
        return jsonify({'code': 1, 'msg': '课程未找到'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'msg': '请求数据为空'}), 400

    try:
        if 'course_id' in data and data['course_id'] != course.course_id and Course.query.filter_by(course_id=data['course_id']).first():
            return jsonify({'code': 1, 'msg': '课程代码已存在'}), 400

        course.name = data.get('name', course.name)
        course.course_id = data.get('course_id', course.course_id)
        course.credits = int(data.get('credits', course.credits))
        course.description = data.get('description', course.description)
        course.teacher_id = data.get('teacher_id', course.teacher_id)

        db.session.commit()
        return jsonify({'code': 0, 'msg': '课程更新成功', 'data': course.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"更新课程失败: {e}", exc_info=True)
        return jsonify({'code': 1, 'msg': f'更新课程失败: {str(e)}'}), 500

@admin_bp.route('/api/courses/<int:course_id>', methods=['POST', 'DELETE'])
@admin_required
def delete_course_api_route(course_id):
    """删除课程API"""
    course = Course.query.get(course_id)
    if not course:
        return jsonify({'code': 1, 'msg': '课程未找到'}), 404

    try:
        # 在删除课程前，先解除与成绩的关联，或设置成绩为无效，避免外键冲突
        # For simplicity, we are deleting grades associated with the course.
        # In a real application, you might want to soft delete or reassign.
        Grade.query.filter_by(course_id=course_id).delete()
        db.session.delete(course)
        db.session.commit()
        return jsonify({'code': 0, 'msg': '课程删除成功'}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"删除课程失败: {e}", exc_info=True)
        return jsonify({'code': 1, 'msg': f'删除课程失败: {str(e)}'}), 500

@admin_bp.route('/api/courses/batch_delete', methods=['POST'])
@admin_required
def batch_delete_courses_api_route():
    """批量删除课程API"""
    data = request.get_json()
    ids = data.get('ids', [])
    if not ids:
        return jsonify({'code': 1, 'msg': '请提供要删除的课程ID'}), 400

    try:
        # 批量删除关联的成绩
        Grade.query.filter(Grade.course_id.in_(ids)).delete(synchronize_session=False)
        deleted_count = Course.query.filter(Course.id.in_(ids)).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({'code': 0, 'msg': f'成功删除 {deleted_count} 条课程'}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"批量删除课程失败: {e}", exc_info=True)
        return jsonify({'code': 1, 'msg': f'批量删除失败: {str(e)}'}), 500

# ===============================================
# 成绩管理路由 (更新)
# ===============================================

@admin_bp.route('/manage_grades_layui')
@admin_required
def manage_grades_layui():
    """成绩管理页面"""
    # 获取筛选选项数据
    students = Student.query.all()
    students_data = [{'id': s.id, 'name': f"{s.name} ({s.student_id})"} for s in students]
    
    courses = Course.query.all()
    courses_data = [{'id': c.id, 'name': f"{c.name} ({c.course_id})"} for c in courses]
    
    return render_template('admin/grades.html', 
                         students=students_data, 
                         courses=courses_data)

@admin_bp.route('/api/grades', methods=['GET'])
@admin_required
def get_grades():
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    student_id = request.args.get('student_id', type=int)
    course_id = request.args.get('course_id', type=int)
    query = Grade.query
    if student_id:
        query = query.filter(Grade.student_id == student_id)
    if course_id:
        query = query.filter(Grade.course_id == course_id)
    total = query.count()
    grades = query.order_by(Grade.id).offset((page-1)*limit).limit(limit).all()
    data = []
    for g in grades:
        d = g.to_dict()
        d['pass_status'] = '及格' if g.score >= 60 else '未及格'
        data.append(d)
    return jsonify({'code': 0, 'data': data, 'count': total})

@admin_bp.route('/api/grades', methods=['POST'])
@admin_required
def create_grade_api_route():
    """录入成绩API"""
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'msg': '请求数据为空'}), 400

    required_fields = ['student_id', 'course_id', 'score']
    for field in required_fields:
        if field not in data or data[field] is None: # 允许分数为0
            return jsonify({'code': 1, 'msg': f'缺少必要字段或字段值为空: {field}'}), 400

    # 检查是否已存在该学生该课程的成绩 (可以根据需求选择覆盖或报错)
    existing_grade = Grade.query.filter_by(student_id=data['student_id'], course_id=data['course_id']).first()
    if existing_grade:
        return jsonify({'code': 1, 'msg': '该学生该课程的成绩已存在，请勿重复录入或进行编辑操作'}), 400

    try:
        new_grade = Grade(
            student_id=data['student_id'],
            course_id=data['course_id'],
            score=float(data['score'])
        )
        db.session.add(new_grade)
        db.session.commit()
        return jsonify({'code': 0, 'msg': '成绩录入成功', 'data': new_grade.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        logging.error(f"录入成绩失败: {e}", exc_info=True)
        return jsonify({'code': 1, 'msg': f'录入成绩失败: {str(e)}'}), 500

@admin_bp.route('/api/grades/<int:grade_id>', methods=['GET'])
@admin_required
def get_grade_api_route(grade_id):
    """获取单个成绩详情API"""
    grade = Grade.query.get(grade_id)
    if not grade:
        return jsonify({'code': 1, 'msg': '成绩记录未找到'}), 404
    return jsonify({'code': 0, 'msg': '成功', 'data': grade.to_dict()})

@admin_bp.route('/api/grades/<int:grade_id>', methods=['PUT'])
@admin_required
def update_grade_api_route(grade_id):
    """更新成绩信息API"""
    grade = Grade.query.get(grade_id)
    if not grade:
        return jsonify({'code': 1, 'msg': '成绩记录未找到'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'msg': '请求数据为空'}), 400

    try:
        # 允许更新学生和课程，但通常这两个字段在成绩记录创建后不应修改
        # 如果要修改，需要检查新的组合是否已存在
        new_student_id = data.get('student_id', grade.student_id)
        new_course_id = data.get('course_id', grade.course_id)
        
        if (new_student_id != grade.student_id or new_course_id != grade.course_id) and \
           Grade.query.filter_by(student_id=new_student_id, course_id=new_course_id).first():
            return jsonify({'code': 1, 'msg': '该学生该课程的新成绩组合已存在'}), 400

        grade.student_id = new_student_id
        grade.course_id = new_course_id
        grade.score = float(data.get('score', grade.score))

        db.session.commit()
        return jsonify({'code': 0, 'msg': '成绩更新成功', 'data': grade.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"更新成绩失败: {e}", exc_info=True)
        return jsonify({'code': 1, 'msg': f'更新成绩失败: {str(e)}'}), 500

@admin_bp.route('/api/grades/<int:grade_id>', methods=['POST', 'DELETE'])
@admin_required
def delete_grade_api_route(grade_id):
    """删除成绩API"""
    grade = Grade.query.get(grade_id)
    if not grade:
        return jsonify({'code': 1, 'msg': '成绩记录未找到'}), 404

    try:
        db.session.delete(grade)
        db.session.commit()
        return jsonify({'code': 0, 'msg': '成绩删除成功'}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"删除成绩失败: {e}", exc_info=True)
        return jsonify({'code': 1, 'msg': f'删除成绩失败: {str(e)}'}), 500

@admin_bp.route('/api/grades/batch_delete', methods=['POST'])
@admin_required
def batch_delete_grades_api_route():
    """批量删除成绩API"""
    data = request.get_json()
    ids = data.get('ids', [])
    if not ids:
        return jsonify({'code': 1, 'msg': '请提供要删除的成绩ID'}), 400

    try:
        deleted_count = Grade.query.filter(Grade.id.in_(ids)).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({'code': 0, 'msg': f'成功删除 {deleted_count} 条成绩记录'}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"批量删除成绩失败: {e}", exc_info=True)
        return jsonify({'code': 1, 'msg': f'批量删除失败: {str(e)}'}), 500

# ===============================================
# 通用表单支持
# ===============================================

@admin_bp.route('/add_edit_form', methods=['GET'])
@admin_required
def add_edit_form():
    """
    通用添加/编辑表单页面。
    通过URL参数 form_type 和 id 来加载不同实体的表单。
    """
    form_type = request.args.get('form_type')
    entity_id = request.args.get('id', type=int) # 用于编辑模式

    if form_type not in ['student', 'teacher', 'course', 'grade']:
        flash('无效的表单类型', 'error')
        return "无效的表单类型", 400 # 也可以重定向到仪表盘

    return render_template('admin/generic_form.html', form_type=form_type, entity_id=entity_id)

@admin_bp.route('/api/form_config/<string:form_type>', methods=['GET'])
@admin_required
def get_form_config(form_type):
    """
    获取通用表单的配置信息，包括字段定义、API endpoints，
    以及下拉选择框所需的选项数据。
    """
    config = {
        'student': {
            'title': '学生信息',
            'api_get_single': url_for('admin.get_student_api_route', student_id=0),
            'api_create_url': url_for('admin.create_student_api_route'),
            'api_update_url': url_for('admin.update_student_api_route', student_id=0),
            'fields': [
                {'name': 'name', 'label': '姓名', 'type': 'text', 'verify': 'required'},
                {'name': 'student_id', 'label': '学号', 'type': 'text', 'verify': 'required'},
                {'name': 'gender', 'label': '性别', 'type': 'select', 'options': [
                    {'value': 'Male', 'label': '男'},
                    {'value': 'Female', 'label': '女'}
                ], 'verify': 'required'},
                {'name': 'birthdate', 'label': '出生日期', 'type': 'date', 'verify': 'required'},
                {'name': 'major', 'label': '专业', 'type': 'text', 'verify': 'required'},
                {'name': 'enrollment_date', 'label': '入学日期', 'type': 'date', 'verify': 'required'},
                {'name': 'class_name', 'label': '班级', 'type': 'text', 'verify': ''},
                {'name': 'hometown', 'label': '生源地', 'type': 'text', 'verify': ''}
            ]
        },
        'teacher': {
            'title': '教师信息',
            'api_get_single': url_for('admin.get_teacher_api_route', teacher_id=0),
            'api_create_url': url_for('admin.create_teacher_api_route'),
            'api_update_url': url_for('admin.update_teacher_api_route', teacher_id=0),
            'fields': [
                {'name': 'name', 'label': '姓名', 'type': 'text', 'verify': 'required'},
                {'name': 'teacher_id', 'label': '工号', 'type': 'text', 'verify': 'required'},
                {'name': 'gender', 'label': '性别', 'type': 'select', 'options': [
                    {'value': 'Male', 'label': '男'},
                    {'value': 'Female', 'label': '女'}
                ], 'verify': 'required'},
                {'name': 'title', 'label': '职称', 'type': 'text', 'verify': 'required'},
                {'name': 'department', 'label': '所属学院/专业', 'type': 'text', 'verify': 'required'}
            ]
        },
        'course': {
            'title': '课程信息',
            'api_get_single': url_for('admin.get_course_api_route', course_id=0),
            'api_create_url': url_for('admin.create_course_api_route'),
            'api_update_url': url_for('admin.update_course_api_route', course_id=0),
            'fields': [
                {'name': 'name', 'label': '课程名称', 'type': 'text', 'verify': 'required'},
                {'name': 'course_id', 'label': '课程代码', 'type': 'text', 'verify': 'required'},
                {'name': 'credits', 'label': '学分', 'type': 'number', 'verify': 'required|number'},
                {'name': 'teacher_id', 'label': '授课教师', 'type': 'select', 'verify': 'required',
                 'options_api': url_for('admin.get_all_teachers_api_route'), # 获取教师列表的API
                 'option_value_field': 'id',
                 'option_label_field': 'name'},
                {'name': 'description', 'label': '课程描述', 'type': 'textarea', 'verify': ''}
            ]
        },
        'grade': {
            'title': '成绩信息',
            'api_get_single': url_for('admin.get_grade_api_route', grade_id=0),
            'api_create_url': url_for('admin.create_grade_api_route'),
            'api_update_url': url_for('admin.update_grade_api_route', grade_id=0),
            'fields': [
                {'name': 'student_id', 'label': '学生', 'type': 'select', 'verify': 'required',
                 'options_api': url_for('admin.get_all_students_api_route'), # 获取学生列表的API
                 'option_value_field': 'id',
                 'option_label_field': 'name'},
                {'name': 'course_id', 'label': '课程', 'type': 'select', 'verify': 'required',
                 'options_api': url_for('admin.get_all_courses_api_route'), # 获取课程列表的API
                 'option_value_field': 'id',
                 'option_label_field': 'name'},
                {'name': 'score', 'label': '分数', 'type': 'number', 'verify': 'required|number', 'step': '0.1', 'min': 0, 'max': 100}
            ]
        }
    }

    form_config = config.get(form_type)
    if not form_config:
        return jsonify({'code': 1, 'msg': '无效的表单类型'}), 400

    return jsonify({'code': 0, 'msg': '成功', 'data': form_config})

# ===============================================
# 辅助API (用于通用表单的下拉选择框)
# ===============================================

@admin_bp.route('/api/students/all', methods=['GET'])
@admin_required
def get_all_students_api_route():
    """获取所有学生列表 (用于下拉选择，不分页)"""
    students = Student.query.all()
    # 转换为字典列表，只包含id和name
    data = [{'id': s.id, 'name': f"{s.name} ({s.student_id})"} for s in students]
    return jsonify({'code': 0, 'msg': '', 'data': data})

@admin_bp.route('/api/teachers/all', methods=['GET'])
@admin_required
def get_all_teachers_api_route():
    """获取所有教师列表 (用于下拉选择，不分页)"""
    teachers = Teacher.query.all()
    # 转换为字典列表，只包含id和name
    data = [{'id': t.id, 'name': f"{t.name} ({t.teacher_id})"} for t in teachers]
    return jsonify({'code': 0, 'msg': '', 'data': data})

@admin_bp.route('/api/courses/all', methods=['GET'])
@admin_required
def get_all_courses_api_route():
    """获取所有课程列表 (用于下拉选择，不分页)"""
    courses = Course.query.all()
    # 转换为字典列表，只包含id和name
    data = [{'id': c.id, 'name': f"{c.name} ({c.course_id})"} for c in courses]
    return jsonify({'code': 0, 'msg': '', 'data': data})

@admin_bp.route('/api/ai_analysis', methods=['GET'])
@admin_required
def ai_analysis():
    prompt_en = (
        "Based on the students' grades and course data in the campus management system, please provide:\n"
        "1. Grade prediction (overall trend, excellence rate, pass rate, etc.);\n"
        "2. Course popularity prediction (which courses are most popular, and which may become popular in the future);\n"
        "3. Failure prediction (which courses or students are at high risk of failing, and suggested measures).\n"
        "Please summarize concisely in English."
    )

    api_key = current_app.config.get("OPENAI_API_KEY")
    analysis_text = None

    try:
        client = OpenAI(api_key=api_key)

        # 英文分析
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt_en}],
            max_tokens=512,
            temperature=0.7
        )
        analysis_text_en = response.choices[0].message.content.strip()

        # 翻译成中文
        translate_prompt = f"请将以下内容翻译成简洁的中文：\n{analysis_text_en}"
        response2 = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": translate_prompt}],
            max_tokens=512,
            temperature=0.7
        )
        analysis_text = response2.choices[0].message.content.strip()

    except Exception as e:
        try:
            analysis_text = f"AI分析失败：{str(e)}"
        except Exception:
            analysis_text = "AI分析失败：未知错误"

    if not analysis_text:
        analysis_text = (
            "1. 成绩预测：本学期学生整体成绩呈上升趋势，优秀率达35%，及格率达92%。\n"
            "2. 课程热度预测：数据结构、人工智能、Python编程等课程最受欢迎，预计下学期选课人数将继续增加。\n"
            "3. 挂科预测：高等数学、大学英语为挂科高发课程，建议加强辅导和答疑。"
        )

    return jsonify({"code": 0, "data": analysis_text, "msg": ""})

@admin_bp.route('/ai_analysis')
@admin_required
def ai_analysis_page():
    return render_template('admin/ai_analysis.html', active_page='ai_analysis')

@admin_bp.route('/manage_users')
@admin_required
def manage_users():
    return render_template('admin/users.html', active_page='users')

@admin_bp.route('/api/users', methods=['GET'])
@admin_required
def get_users():
    # 分页参数
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    # 筛选参数
    keyword = request.args.get('keyword', '').strip()
    major = request.args.get('major', '').strip()
    class_name = request.args.get('class_name', '').strip()
    hometown = request.args.get('hometown', '').strip()
    query = User.query
    # 只查学生
    if request.args.get('role') == 'Student':
        query = query.filter(User.role == Role.STUDENT)
    # 关键字搜索用户名
    if keyword:
        query = query.filter(User.username.like(f'%{keyword}%'))
    # 通过学生表筛选专业、班级、生源地
    if major or class_name or hometown:
        from app.models import Student
        query = query.join(Student, Student.user_id == User.id)
        if major:
            query = query.filter(Student.major == major)
        if class_name:
            query = query.filter(Student.class_name == class_name)
        if hometown:
            query = query.filter(Student.hometown == hometown)
    total = query.count()
    users = query.order_by(User.id).offset((page-1)*limit).limit(limit).all()
    # 查询成绩状态
    from app.models import Student, Grade
    user_dicts = []
    for u in users:
        user_info = {
            'id': u.id,
            'username': u.username,
            'password_mask': '******',
            'role': u.role.value if hasattr(u.role, 'value') else u.role,
        }
        if u.role == Role.STUDENT or (hasattr(u.role, 'value') and u.role.value == 'Student'):
            if u.student:
                user_info['bind_name'] = u.student.name
                user_info['bind_id'] = u.student.student_id
            else:
                user_info['bind_name'] = ''
                user_info['bind_id'] = ''
        elif u.role == Role.TEACHER or (hasattr(u.role, 'value') and u.role.value == 'Teacher'):
            if u.teacher:
                user_info['bind_name'] = u.teacher.name
                user_info['bind_id'] = u.teacher.teacher_id
            else:
                user_info['bind_name'] = ''
                user_info['bind_id'] = ''
        else:
            user_info['bind_name'] = ''
            user_info['bind_id'] = ''
        user_dicts.append(user_info)
    return jsonify({'code': 0, 'data': user_dicts, 'count': total})


@admin_bp.route('/api/users/batch_delete', methods=['POST'])
@admin_required
def batch_delete_users():
    ids = request.get_json().get('ids', [])
    if not ids:
        return jsonify({'code': 1, 'msg': '未提供用户ID'}), 400
    try:
        User.query.filter(User.id.in_(ids)).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({'code': 0, 'msg': '批量删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 1, 'msg': f'批量删除失败: {str(e)}'}), 500

# ===================== 仪表盘API =====================

@admin_bp.route('/api/majors/all', methods=['GET'])
@admin_required
def get_all_majors():
    majors = db.session.query(Student.major).distinct().all()
    data = [{'name': m[0]} for m in majors if m[0]]
    return jsonify({'code': 0, 'data': data})

@admin_bp.route('/api/hometown_distribution', methods=['GET'])
@admin_required
def get_hometown_distribution():
    stats = db.session.query(Student.hometown, func.count(Student.id)).group_by(Student.hometown).all()
    names = [s[0] for s in stats]
    counts = [s[1] for s in stats]
    return jsonify({'code': 0, 'data': {'names': names, 'counts': counts}})

@admin_bp.route('/api/course_score_distribution', methods=['GET'])
@admin_required
def get_course_score_distribution():
    course_id = request.args.get('course_id', type=int)
    bins = {'不及格 (0-59)': 0, '及格 (60-74)': 0, '良好 (75-89)': 0, '优秀 (90-100)': 0}
    if not course_id:
        return jsonify({'code': 1, 'msg': '缺少课程ID'}), 400
    grades = Grade.query.filter_by(course_id=course_id).filter(Grade.score.isnot(None)).all()
    for g in grades:
        if g.score < 60:
            bins['不及格 (0-59)'] += 1
        elif g.score < 75:
            bins['及格 (60-74)'] += 1
        elif g.score < 90:
            bins['良好 (75-89)'] += 1
        else:
            bins['优秀 (90-100)'] += 1
    data = [{'name': k, 'value': v} for k, v in bins.items()]
    return jsonify({'code': 0, 'data': data})

@admin_bp.route('/api/student_radar', methods=['GET'])
@admin_required
def get_student_radar():
    student_id = request.args.get('student_id', type=int)
    if not student_id:
        return jsonify({'code': 1, 'msg': '缺少学生ID'}), 400
    grades = Grade.query.filter_by(student_id=student_id).filter(Grade.score.isnot(None)).join(Course).all()
    courses = [g.course.name for g in grades]
    scores = [g.score for g in grades]
    return jsonify({'code': 0, 'data': {'courses': courses, 'scores': scores}})

@admin_bp.route('/api/major_avg_score', methods=['GET'])
@admin_required
def get_major_avg_score():
    major = request.args.get('major', type=str)
    if not major:
        # 返回所有专业的平均分
        stats = db.session.query(Student.major, func.avg(Grade.score)).join(Grade, Student.id==Grade.student_id).filter(Grade.score.isnot(None)).group_by(Student.major).all()
        names = [s[0] for s in stats]
        scores = [round(float(s[1]),2) for s in stats]
    else:
        stats = db.session.query(Student.major, func.avg(Grade.score)).join(Grade, Student.id==Grade.student_id).filter(Grade.score.isnot(None), Student.major==major).group_by(Student.major).all()
        names = [s[0] for s in stats]
        scores = [round(float(s[1]),2) for s in stats]
    return jsonify({'code': 0, 'data': {'names': names, 'scores': scores}})

@admin_bp.route('/api/course_score_boxplot', methods=['GET'])
@admin_required
def get_course_score_boxplot():
    # 查询所有课程
    courses = Course.query.all()
    course_names = []
    scores = []
    for course in courses:
        grades = Grade.query.filter_by(course_id=course.id).filter(Grade.score.isnot(None)).all()
        score_list = [g.score for g in grades]
        if score_list:
            course_names.append(course.name)
            scores.append(score_list)
    return jsonify({'code': 0, 'data': {'course_names': course_names, 'scores': scores}})
