from flask import Blueprint, request, jsonify, render_template, redirect, url_for
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, set_access_cookies, unset_jwt_cookies
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

from ..models import User, Student, Teacher, Role
from .. import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录接口：验证凭据并生成 JWT"""
    if request.method == 'GET':
        return render_template('auth/login.html')
    
    data = request.get_json()

    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': '缺少用户名或密码'}), 400

    user = User.query.filter_by(username=data.get('username')).first()

    if not user or not user.check_password(data.get('password')):
        return jsonify({'message': '无效的用户名或密码'}), 401

    try:
        # 强制将 user.id 转换为字符串，这是解决 "Subject must be a string" 的关键
        access_token = create_access_token(identity=str(user.id), additional_claims={'role': user.role.value})
    except Exception as e:
        return jsonify({'message': f'生成令牌失败: {str(e)}'}), 500

    # 创建响应对象
    response = jsonify({
        'message': '登录成功',
        'user': user.to_dict(),
        'access_token': access_token # ✅ 新增：在 JSON 响应中返回 access_token
    })
    
    # 仍保留设置 HTTP Only Cookie 的功能，这对于直接访问页面（非 AJAX）很重要
    set_access_cookies(response, access_token) 

    return response, 200 # 返回响应和状态码

@auth_bp.route('/register', methods=['POST'])
def register():
    """用户注册接口"""
    data = request.get_json()

    required_fields = ['username', 'password', 'role']
    for field in required_fields:
        if field not in data:
            return jsonify({'message': f'缺少必填字段: {field}'}), 400

    if User.query.filter_by(username=data['username']).first():
        return jsonify({'message': '用户名已存在'}), 400

    role_str = data['role'].upper()
    if role_str not in [r.name for r in Role]:
        return jsonify({'message': '无效的用户角色'}), 400
    
    if Role[role_str] == Role.ADMIN:
        return jsonify({'message': '不允许通过此接口注册管理员账号'}), 403

    user = User(
        username=data['username'],
        role=Role[role_str]
    )
    user.set_password(data['password'])

    db.session.add(user)

    if user.role == Role.STUDENT and 'student_data' in data:
        student_data = data['student_data']
        student = Student(
            student_id=student_data.get('student_id'),
            name=student_data.get('name'),
            gender=student_data.get('gender'),
            major=student_data.get('major'),
            birthdate=datetime.strptime(student_data.get('birthdate'), '%Y-%m-%d').date() if student_data.get('birthdate') else None,
            enrollment_date=datetime.strptime(student_data.get('enrollment_date'), '%Y-%m-%d').date() if student_data.get('enrollment_date') else None,
            hometown=student_data.get('hometown'), # Changed from 'origin' to 'hometown'
            student_class=student_data.get('student_class'), # Added student_class
            user_id=user.id
        )
        db.session.add(student)

    elif user.role == Role.TEACHER and 'teacher_data' in data:
        teacher_data = data['teacher_data']
        teacher = Teacher(
            name=teacher_data.get('name'),
            teacher_id=teacher_data.get('teacher_id'), # Added teacher_id
            gender=teacher_data.get('gender'), # Added gender
            title=teacher_data.get('title'), # Added title
            major=teacher_data.get('major'), # Changed from 'department' to 'major'
            phone=teacher_data.get('phone'), # Added phone
            email=teacher_data.get('email'), # Added email
            address=teacher_data.get('address'), # Added address
            user_id=user.id
        )
        db.session.add(teacher)

    try:
        db.session.commit()
        return jsonify({
            'message': '用户注册成功',
            'user': user.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'注册用户失败: {str(e)}'}), 500

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """获取当前用户资料"""
    # get_jwt_identity() 返回的将是字符串形式的用户ID
    current_user_id = get_jwt_identity() 
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({'message': '用户未找到'}), 404

    profile_data = user.to_dict()

    if user.role == Role.STUDENT and user.student:
        profile_data['student_data'] = user.student.to_dict()
    elif user.role == Role.TEACHER and user.teacher:
        profile_data['teacher_data'] = user.teacher.to_dict()

    return jsonify(profile_data), 200

@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """更新当前用户资料"""
    # get_jwt_identity() 返回的将是字符串形式的用户ID
    current_user_id = get_jwt_identity() 
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({'message': '用户未找到'}), 404

    data = request.get_json()

    if 'password' in data and data['password']:
        user.set_password(data['password'])

    if user.role == Role.STUDENT and user.student and 'student_data' in data:
        student_data = data['student_data']
        student = user.student

        for key, value in student_data.items():
            if hasattr(student, key) and key not in ['id', 'user_id']:
                if key in ['birthdate', 'enrollment_date'] and value:
                    setattr(student, key, datetime.strptime(value, '%Y-%m-%d').date())
                elif key in ['birthdate', 'enrollment_date'] and not value:
                    setattr(student, key, None)
                else:
                    setattr(student, key, value)

    elif user.role == Role.TEACHER and user.teacher and 'teacher_data' in data:
        teacher_data = data['teacher_data']
        teacher = user.teacher

        for key, value in teacher_data.items():
            if hasattr(teacher, key) and key not in ['id', 'user_id']:
                setattr(teacher, key, value)

    try:
        db.session.commit()
        return jsonify({
            'message': '个人资料更新成功',
            'user': user.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'更新个人资料失败: {str(e)}'}), 500

@auth_bp.route('/logout', methods=['GET', 'POST'])
@jwt_required(optional=True)
def logout():
    """用户登出接口：清除客户端JWT并重定向到登录页"""
    # 记录完整的 Authorization header，用于调试
    auth_header = request.headers.get('Authorization')
    print(f"Logout request received. Method: {request.method}. Authorization header: '{auth_header}'")

    if request.method == 'GET':
        # 当通过 GET 请求登出时，清除 JWT Cookie 并重定向
        response = redirect(url_for('auth.login'))
        unset_jwt_cookies(response)
        print("GET logout: Cleared JWT cookie and redirected to login.")
        return response, 302
    
    # 对于 POST 请求，通常用于 API 登出，仅返回 JSON 响应并清除 Cookie
    response = jsonify({'message': '已成功登出'})
    unset_jwt_cookies(response)
    print("POST logout: Cleared JWT cookie.")
    return response, 200

