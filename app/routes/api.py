from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import check_password_hash
from datetime import datetime

from ..models import User, Student, Course, Grade, Role, MajorCourse
from .. import db

api_bp = Blueprint('api', __name__, url_prefix='/api')

# 认证相关API
@api_bp.route('/auth/login', methods=['POST'])
def login():
    """微信小程序登录接口"""
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({
            'success': False,
            'message': '缺少用户名或密码'
        }), 400

    user = User.query.filter_by(username=data.get('username')).first()

    if not user or not user.check_password(data.get('password')):
        return jsonify({
            'success': False,
            'message': '无效的用户名或密码'
        }), 401

    # 检查用户角色
    if user.role != Role.STUDENT:
        return jsonify({
            'success': False,
            'message': '只有学生可以登录小程序'
        }), 403

    try:
        # 生成JWT token
        access_token = create_access_token(identity=str(user.id), additional_claims={'role': user.role.value})
        
        # 获取学生信息
        student = Student.query.filter_by(user_id=user.id).first()
        if not student:
            return jsonify({
                'success': False,
                'message': '未找到学生信息'
            }), 404

        return jsonify({
            'success': True,
            'message': '登录成功',
            'token': access_token,
            'user': student.to_dict()
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'登录失败: {str(e)}'
        }), 500

@api_bp.route('/auth/wechat_login', methods=['POST'])
def wechat_login():
    """微信登录接口（预留）"""
    data = request.get_json()
    code = data.get('code')
    
    if not code:
        return jsonify({
            'success': False,
            'message': '缺少微信授权码'
        }), 400

    # TODO: 实现微信登录逻辑
    # 1. 使用code获取微信用户信息
    # 2. 绑定到系统用户
    # 3. 生成JWT token
    
    return jsonify({
        'success': False,
        'message': '微信登录功能开发中'
    }), 501

# 学生相关API
@api_bp.route('/student/info', methods=['GET'])
@jwt_required()
def get_student_info():
    """获取学生信息"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or user.role != Role.STUDENT:
        return jsonify({
            'success': False,
            'message': '无权限访问'
        }), 403

    student = Student.query.filter_by(user_id=user_id).first()
    if not student:
        return jsonify({
            'success': False,
            'message': '未找到学生信息'
        }), 404

    return jsonify({
        'success': True,
        'student': student.to_dict()
    }), 200

@api_bp.route('/student/grades', methods=['GET'])
@jwt_required()
def get_student_grades():
    """获取学生成绩列表"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or user.role != Role.STUDENT:
        return jsonify({
            'success': False,
            'message': '无权限访问'
        }), 403

    student = Student.query.filter_by(user_id=user_id).first()
    if not student:
        return jsonify({
            'success': False,
            'message': '未找到学生信息'
        }), 404

    grades = Grade.query.filter_by(student_id=student.id).all()
    grades_data = []
    
    for grade in grades:
        if grade.course:
            # 获取课程类型
            course_type = get_course_type(grade.course.name, student.major)
            
            grade_data = {
                'id': grade.id,
                'course_name': grade.course.name,
                'course_type': course_type,
                'credits': grade.course.credits,
                'teacher_name': grade.course.teacher.name if grade.course.teacher else 'N/A',
                'score': grade.score
            }
            grades_data.append(grade_data)

    return jsonify({
        'success': True,
        'grades': grades_data
    }), 200

@api_bp.route('/student/courses', methods=['GET'])
@jwt_required()
def get_student_courses():
    """获取学生课程列表"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or user.role != Role.STUDENT:
        return jsonify({
            'success': False,
            'message': '无权限访问'
        }), 403

    student = Student.query.filter_by(user_id=user_id).first()
    if not student:
        return jsonify({
            'success': False,
            'message': '未找到学生信息'
        }), 404

    # 获取所有课程
    all_courses = Course.query.all()
    # 获取已选课程ID
    selected_course_ids = {g.course_id for g in Grade.query.filter_by(student_id=student.id).all()}
    
    courses_data = []
    for course in all_courses:
        course_type = get_course_type(course.name, student.major)
        courses_data.append({
            'id': course.id,
            'course_id': course.course_id,
            'name': course.name,
            'credits': course.credits,
            'teacher_name': course.teacher.name if course.teacher else 'N/A',
            'course_type': course_type,
            'selected': course.id in selected_course_ids
        })

    return jsonify({
        'success': True,
        'courses': courses_data
    }), 200

@api_bp.route('/student/analysis', methods=['GET'])
@jwt_required()
def get_student_analysis():
    """获取学生成绩分析数据"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or user.role != Role.STUDENT:
        return jsonify({
            'success': False,
            'message': '无权限访问'
        }), 403

    student = Student.query.filter_by(user_id=user_id).first()
    if not student:
        return jsonify({
            'success': False,
            'message': '未找到学生信息'
        }), 404

    grades = Grade.query.filter_by(student_id=student.id).all()
    
    if not grades:
        return jsonify({
            'success': True,
            'analysis': {
                'radar_data': {'courses': [], 'scores': []},
                'pie_data': [],
                'bar_data': {'courses': [], 'personal_scores': [], 'class_averages': []},
                'statistics': {
                    'total_courses': 0,
                    'average_score': 0,
                    'pass_rate': 0,
                    'best_subject': '无'
                }
            }
        }), 200

    # 雷达图数据
    courses = [g.course.name for g in grades if g.course and g.score is not None]
    scores = [g.score for g in grades if g.course and g.score is not None]
    
    # 饼图数据
    score_distribution = {
        '优秀(90-100)': 0,
        '良好(80-89)': 0,
        '中等(70-79)': 0,
        '及格(60-69)': 0,
        '不及格(0-59)': 0
    }
    
    for grade in grades:
        if grade.score is not None:
            if grade.score >= 90:
                score_distribution['优秀(90-100)'] += 1
            elif grade.score >= 80:
                score_distribution['良好(80-89)'] += 1
            elif grade.score >= 70:
                score_distribution['中等(70-79)'] += 1
            elif grade.score >= 60:
                score_distribution['及格(60-69)'] += 1
            else:
                score_distribution['不及格(0-59)'] += 1
    
    pie_data = [{'name': k, 'value': v} for k, v in score_distribution.items() if v > 0]
    
    # 柱状图数据（与班级平均分对比）
    bar_courses = [g.course.name for g in grades if g.course and g.score is not None][:5]  # 最多显示5门
    personal_scores = [g.score for g in grades if g.course and g.score is not None][:5]
    # 模拟班级平均分（实际应该从数据库计算）
    class_averages = [score + (score * 0.1) for score in personal_scores]  # 模拟数据
    
    # 统计数据
    total_courses = len([g for g in grades if g.score is not None])
    if total_courses > 0:
        average_score = sum([g.score for g in grades if g.score is not None]) / total_courses
        pass_count = len([g for g in grades if g.score is not None and g.score >= 60])
        pass_rate = (pass_count / total_courses) * 100
        
        # 最强科目
        best_grade = max([g for g in grades if g.score is not None], key=lambda x: x.score)
        best_subject = best_grade.course.name if best_grade.course else '无'
    else:
        average_score = 0
        pass_rate = 0
        best_subject = '无'

    return jsonify({
        'success': True,
        'analysis': {
            'radar_data': {
                'courses': courses,
                'scores': scores
            },
            'pie_data': pie_data,
            'bar_data': {
                'courses': bar_courses,
                'personal_scores': personal_scores,
                'class_averages': class_averages
            },
            'statistics': {
                'total_courses': total_courses,
                'average_score': round(average_score, 1),
                'pass_rate': round(pass_rate, 1),
                'best_subject': best_subject
            }
        }
    }), 200

# 课程相关API
@api_bp.route('/student/select_course', methods=['POST'])
@jwt_required()
def select_course():
    """学生选课"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or user.role != Role.STUDENT:
        return jsonify({
            'success': False,
            'message': '无权限访问'
        }), 403

    student = Student.query.filter_by(user_id=user_id).first()
    if not student:
        return jsonify({
            'success': False,
            'message': '未找到学生信息'
        }), 404

    data = request.get_json()
    course_id = data.get('course_id')
    
    if not course_id:
        return jsonify({
            'success': False,
            'message': '缺少课程ID'
        }), 400

    # 检查课程是否存在
    course = Course.query.get(course_id)
    if not course:
        return jsonify({
            'success': False,
            'message': '课程不存在'
        }), 404

    # 检查是否已选过该课
    existing_grade = Grade.query.filter_by(student_id=student.id, course_id=course_id).first()
    if existing_grade:
        return jsonify({
            'success': False,
            'message': '已选过该课程'
        }), 400

    # 新增成绩记录（分数为None，表示已选但未考试）
    grade = Grade(student_id=student.id, course_id=course_id, score=None)
    db.session.add(grade)
    
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '选课成功'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'选课失败: {str(e)}'
        }), 500

@api_bp.route('/student/drop_course', methods=['POST'])
@jwt_required()
def drop_course():
    """学生退课"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or user.role != Role.STUDENT:
        return jsonify({
            'success': False,
            'message': '无权限访问'
        }), 403

    student = Student.query.filter_by(user_id=user_id).first()
    if not student:
        return jsonify({
            'success': False,
            'message': '未找到学生信息'
        }), 404

    data = request.get_json()
    course_id = data.get('course_id')
    
    if not course_id:
        return jsonify({
            'success': False,
            'message': '缺少课程ID'
        }), 400

    # 查找并删除选课记录
    grade = Grade.query.filter_by(student_id=student.id, course_id=course_id).first()
    if not grade:
        return jsonify({
            'success': False,
            'message': '未选择该课程'
        }), 404

    # 如果已有成绩，不允许退课
    if grade.score is not None:
        return jsonify({
            'success': False,
            'message': '已有成绩的课程不能退课'
        }), 400

    db.session.delete(grade)
    
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '退课成功'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'退课失败: {str(e)}'
        }), 500

# 课程类型判定函数
REQUIRED_COURSES_COMMON = {'高等数学', '大学英语', '数据结构', '操作系统', '数据库原理'}
REQUIRED_COURSES_DS = {'深度学习', '大数据技术'}
REQUIRED_COURSES_RE = {'机器人学', '机器学习'}
REQUIRED_COURSES_AI = {'人工智能导论', '深度学习', '大数据技术'}

def get_course_type(course_name, major):
    """根据课程名称和专业判断课程类型"""
    if course_name in REQUIRED_COURSES_COMMON:
        return '必修'
    if major == '数据科学与大数据技术' and course_name in REQUIRED_COURSES_DS:
        return '必修'
    if major == '机器人工程' and course_name in REQUIRED_COURSES_RE:
        return '必修'
    if major == '人工智能' and course_name in REQUIRED_COURSES_AI:
        return '必修'
    return '选修' 