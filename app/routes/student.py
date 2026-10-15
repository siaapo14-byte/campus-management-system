from flask import Blueprint, request, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import User, Student, Course, Grade, Role
from .. import db

student_bp = Blueprint('student', __name__, url_prefix='/student')

# 学生端主页重定向到个人信息
@student_bp.route('/')
@jwt_required()
def index():
    return render_template('student/profile.html')

# 个人信息页面
@student_bp.route('/profile')
@jwt_required()
def profile_page():
    return render_template('student/profile.html')

# 个人信息API
@student_bp.route('/api/profile')
@jwt_required()
def profile_api():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or user.role != Role.STUDENT:
        return jsonify({'code': 1, 'msg': '无权限'}), 403
    student = Student.query.filter_by(user_id=user_id).first()
    if not student:
        return jsonify({'code': 1, 'msg': '未找到学生信息'}), 404
    return jsonify({'code': 0, 'data': student.to_dict()})

# 课程列表页面
@student_bp.route('/courses')
@jwt_required()
def courses_page():
    return render_template('student/courses.html')

# 课程列表API
@student_bp.route('/api/courses')
@jwt_required()
def courses_api():
    courses = Course.query.all()
    return jsonify({'code': 0, 'data': [c.to_dict() for c in courses]})

# 成绩页面
@student_bp.route('/grades')
@jwt_required()
def grades_page():
    return render_template('student/grades.html')

# 成绩API
@student_bp.route('/api/grades')
@jwt_required()
def grades_api():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or user.role != Role.STUDENT:
        return jsonify({'code': 1, 'msg': '无权限'}), 403
    student = Student.query.filter_by(user_id=user_id).first()
    if not student:
        return jsonify({'code': 1, 'msg': '未找到学生信息'}), 404
    grades = Grade.query.filter_by(student_id=student.id).all()
    data = []
    for g in grades:
        course = g.course
        ctype = get_course_type(course.name, student.major) if course else 'N/A'
        d = g.to_dict()
        d['course_type'] = ctype
        data.append(d)
    return jsonify({'code': 0, 'data': data})

# 成绩分析页面
@student_bp.route('/analysis')
@jwt_required()
def analysis_page():
    return render_template('student/analysis.html')

# 成绩雷达图API
@student_bp.route('/api/grade_radar')
@jwt_required()
def grade_radar_api():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or user.role != Role.STUDENT:
        return jsonify({'code': 1, 'msg': '无权限'}), 403
    student = Student.query.filter_by(user_id=user_id).first()
    if not student:
        return jsonify({'code': 1, 'msg': '未找到学生信息'}), 404
    grades = Grade.query.filter_by(student_id=student.id).all()
    courses = [g.course.name for g in grades if g.course]
    scores = [g.score for g in grades]
    return jsonify({'code': 0, 'data': {'courses': courses, 'scores': scores}})

# 成绩分布饼图API
@student_bp.route('/api/grade_pie')
@jwt_required()
def grade_pie_api():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or user.role != Role.STUDENT:
        return jsonify({'code': 1, 'msg': '无权限'}), 403
    student = Student.query.filter_by(user_id=user_id).first()
    if not student:
        return jsonify({'code': 1, 'msg': '未找到学生信息'}), 404
    grades = Grade.query.filter_by(student_id=student.id).all()
    bins = {'不及格 (0-59)': 0, '及格 (60-74)': 0, '良好 (75-89)': 0, '优秀 (90-100)': 0}
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

# 选课页面
@student_bp.route('/choose_courses')
@jwt_required()
def choose_courses_page():
    return render_template('student/choose_courses.html')

# 选课API（POST）
@student_bp.route('/api/choose_course', methods=['POST'])
@jwt_required()
def choose_course_api():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or user.role != Role.STUDENT:
        return jsonify({'code': 1, 'msg': '无权限'}), 403
    student = Student.query.filter_by(user_id=user_id).first()
    if not student:
        return jsonify({'code': 1, 'msg': '未找到学生信息'}), 404
    data = request.get_json()
    course_id = data.get('course_id')
    if not course_id:
        return jsonify({'code': 1, 'msg': '缺少课程ID'}), 400
    # 检查是否已选过该课
    from app.models import Grade
    exist = Grade.query.filter_by(student_id=student.id, course_id=course_id).first()
    if exist:
        return jsonify({'code': 1, 'msg': '已选过该课程'}), 400
    # 新增成绩记录，分数为None
    grade = Grade(student_id=student.id, course_id=course_id, score=None)
    db.session.add(grade)
    db.session.commit()
    return jsonify({'code': 0, 'msg': '选课成功'})

# 课程类型判定函数
REQUIRED_COURSES_COMMON = {'高等数学', '大学英语', '数据结构', '操作系统', '数据库原理'}
REQUIRED_COURSES_DS = {'深度学习', '大数据技术'}
REQUIRED_COURSES_RE = {'机器人学', '机器学习'}
REQUIRED_COURSES_AI = {'人工智能导论', '深度学习', '大数据技术'}

def get_course_type(course_name, major):
    if course_name in REQUIRED_COURSES_COMMON:
        return '必修'
    if major == '数据科学与大数据技术' and course_name in REQUIRED_COURSES_DS:
        return '必修'
    if major == '机器人工程' and course_name in REQUIRED_COURSES_RE:
        return '必修'
    if major == '人工智能' and course_name in REQUIRED_COURSES_AI:
        return '必修'
    return '选修'

# 所有课程API
@student_bp.route('/api/all_courses')
@jwt_required()
def all_courses_api():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or user.role != Role.STUDENT:
        return jsonify({'code': 1, 'msg': '无权限'}), 403
    student = Student.query.filter_by(user_id=user_id).first()
    if not student:
        return jsonify({'code': 1, 'msg': '未找到学生信息'}), 404
    from app.models import Course, Grade
    all_courses = Course.query.all()
    selected = {g.course_id for g in Grade.query.filter_by(student_id=student.id).all()}
    data = []
    for c in all_courses:
        ctype = get_course_type(c.name, student.major)
        data.append({
            'id': c.id,
            'course_id': c.course_id,
            'name': c.name,
            'credits': c.credits,
            'teacher_name': c.teacher.name if c.teacher else '',
            'selected': c.id in selected,
            'type': ctype
        })
    return jsonify({'code': 0, 'data': data})

# 已选课程API（带课程类型、成绩）
@student_bp.route('/api/selected_courses')
@jwt_required()
def selected_courses_api():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or user.role != Role.STUDENT:
        return jsonify({'code': 1, 'msg': '无权限'}), 403
    student = Student.query.filter_by(user_id=user_id).first()
    if not student:
        return jsonify({'code': 1, 'msg': '未找到学生信息'}), 404
    from app.models import Grade, Course
    grades = Grade.query.filter_by(student_id=student.id).all()
    data = []
    for g in grades:
        course = Course.query.get(g.course_id)
        if course:
            ctype = get_course_type(course.name, student.major)
            data.append({
                'id': course.id,
                'course_id': course.course_id,
                'name': course.name,
                'credits': course.credits,
                'teacher_name': course.teacher.name if course.teacher else '',
                'score': g.score,
                'type': ctype
            })
    return jsonify({'code': 0, 'data': data})

# 退课API
@student_bp.route('/api/drop_course', methods=['POST'])
@jwt_required()
def drop_course_api():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or user.role != Role.STUDENT:
        return jsonify({'code': 1, 'msg': '无权限'}), 403
    student = Student.query.filter_by(user_id=user_id).first()
    if not student:
        return jsonify({'code': 1, 'msg': '未找到学生信息'}), 404
    data = request.get_json()
    course_id = data.get('course_id')
    if not course_id:
        return jsonify({'code': 1, 'msg': '缺少课程ID'}), 400
    from app.models import Grade
    grade = Grade.query.filter_by(student_id=student.id, course_id=course_id).first()
    if not grade:
        return jsonify({'code': 1, 'msg': '未选该课程'}), 400
    db.session.delete(grade)
    db.session.commit()
    return jsonify({'code': 0, 'msg': '退课成功'})

# 成绩趋势图API
@student_bp.route('/api/grade_trend')
@jwt_required()
def grade_trend_api():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or user.role != Role.STUDENT:
        return jsonify({'code': 1, 'msg': '无权限'}), 403
    student = Student.query.filter_by(user_id=user_id).first()
    if not student:
        return jsonify({'code': 1, 'msg': '未找到学生信息'}), 404
    from app.models import Grade, Course
    grades = Grade.query.filter_by(student_id=student.id).all()
    trend = []
    for g in grades:
        course = Course.query.get(g.course_id)
        if course and g.score is not None:
            trend.append({'course': course.name, 'score': g.score})
    # 按课程名排序
    trend.sort(key=lambda x: x['course'])
    return jsonify({'code': 0, 'data': trend})

# 成绩分析API
@student_bp.route('/api/analysis_data')
@jwt_required()
def analysis_data_api():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or user.role != Role.STUDENT:
        return jsonify({'code': 1, 'msg': '无权限'}), 403
    student = Student.query.filter_by(user_id=user_id).first()
    if not student:
        return jsonify({'code': 1, 'msg': '未找到学生信息'}), 404
    from app.models import Grade, Course
    grades = Grade.query.filter_by(student_id=student.id).all()
    all_courses = Course.query.all()
    # 课程平均分
    course_avg = {}
    for c in all_courses:
        c_grades = Grade.query.filter_by(course_id=c.id).filter(Grade.score.isnot(None)).all()
        if c_grades:
            course_avg[c.id] = sum(g.score for g in c_grades) / len(c_grades)
        else:
            course_avg[c.id] = None
    # 统计
    total_credits = 0
    total_weighted_score = 0
    fail_count = 0
    elective_pass = 0
    elective_fail = 0
    analysis = []
    for g in grades:
        course = Course.query.get(g.course_id)
        if not course:
            continue
        ctype = get_course_type(course.name, student.major)
        avg = course_avg.get(course.id)
        higher_than_avg = (avg is not None and g.score is not None and g.score > avg)
        # 必修课学分绩统计
        if ctype == '必修':
            if g.score is not None and g.score >= 60:
                total_credits += course.credits
                total_weighted_score += course.credits * g.score
            if g.score is not None and g.score < 60:
                fail_count += 1
        else:
            if g.score is not None and g.score >= 60:
                elective_pass += 1
            elif g.score is not None:
                elective_fail += 1
        analysis.append({
            'course_id': course.course_id,
            'name': course.name,
            'type': ctype,
            'score': g.score,
            'avg': avg,
            'higher_than_avg': higher_than_avg,
            'credits': course.credits
        })
    gpa = round(total_weighted_score / total_credits, 2) if total_credits > 0 else None
    return jsonify({'code': 0, 'data': {
        'analysis': analysis,
        'gpa': gpa,
        'fail_count': fail_count,
        'elective_pass': elective_pass,
        'elective_fail': elective_fail,
        'total_credits': total_credits
    }})
