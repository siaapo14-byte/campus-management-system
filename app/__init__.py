from flask import Flask, redirect, url_for, jsonify, request, flash
from .models import db
from .routes import auth, admin, teacher
from flask_jwt_extended import JWTManager, exceptions as jwt_exceptions, unset_jwt_cookies
import logging
import openai
from app.routes.student import student_bp
from app.routes.api import api_bp

# 配置全局日志，确保所有模块的 DEBUG 消息都能输出
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def create_app():
    app = Flask(__name__)
    # 从 app.config.Config 加载所有配置，包括 SECRET_KEY 和 JWT_SECRET_KEY
    app.config.from_object('app.config.Config')
    openai.api_key = app.config.get("OPENAI_API_KEY")

    db.init_app(app)

    jwt = JWTManager(app)

    # JWT 令牌查找位置和 CSRF 保护已经在 app.config.Config 中配置，
    # 或者由 Flask-JWT-Extended 的默认行为处理，不需要在这里重复设置 JWT_SECRET_KEY
    # app.config["JWT_TOKEN_LOCATION"] = ["headers", "cookies"] # 已经在 Config 类中
    # app.config["JWT_COOKIE_SECURE"] = False # 已经在 Config 类中
    # app.config["JWT_COOKIE_CSRF_PROTECT"] = False # 已经在 Config 类中


    # 配置 Flask-JWT-Extended 的错误处理
    @jwt.unauthorized_loader
    def unauthorized_response(callback):
        # unauthorized_loader 和 invalid_token_loader 通常只接收一个字符串参数 (message)
        logging.warning(f"Unauthorized access detected: {callback}")
        if request.path.startswith('/admin') and 'text/html' in request.headers.get('Accept', ''):
            response = redirect(url_for('auth.login'))
            unset_jwt_cookies(response) # 清除可能的旧 Cookie
            flash('您需要登录才能访问此页面。', 'danger')
            return response, 302
        return jsonify({'message': '认证令牌缺失或无效'}), 401

    @jwt.invalid_token_loader
    def invalid_token_response(callback):
        logging.error(f"Invalid token detected: {callback}")
        if request.path.startswith('/admin') and 'text/html' in request.headers.get('Accept', ''):
            response = redirect(url_for('auth.login'))
            unset_jwt_cookies(response) # 清除可能的旧 Cookie
            flash('认证令牌无效，请重新登录。', 'danger')
            return response, 302
        return jsonify({'message': '无效的认证令牌'}), 401

    @jwt.expired_token_loader
    def expired_token_response(jwt_header, jwt_payload):
        logging.warning(f"Expired token detected: Header={jwt_header}, Payload={jwt_payload}")
        # 如果是 HTML 请求，清除 Cookie 并重定向
        if request.path.startswith('/admin') and 'text/html' in request.headers.get('Accept', ''):
            response = redirect(url_for('auth.login'))
            unset_jwt_cookies(response) # 清除过期的 JWT Cookie
            flash('认证令牌已过期，请重新登录。', 'danger')
            return response, 302
        return jsonify({'message': '认证令牌已过期'}), 401

    @jwt.revoked_token_loader
    def revoked_token_response(jwt_header, jwt_payload):
        logging.warning(f"Revoked token detected: Header={jwt_header}, Payload={jwt_payload}")
        # 如果是 HTML 请求，清除 Cookie 并重定向
        if request.path.startswith('/admin') and 'text/html' in request.headers.get('Accept', ''):
            response = redirect(url_for('auth.login'))
            unset_jwt_cookies(response) # 清除被撤销的 JWT Cookie
            flash('认证令牌已被撤销，请重新登录。', 'danger')
            return response, 302
        return jsonify({'message': '认证令牌已被撤销'}), 401

    @app.errorhandler(jwt_exceptions.JWTExtendedException)
    def handle_jwt_exceptions(error):
        logging.error(f"Caught JWT Extended Exception: {error}", exc_info=True)
        if request.path.startswith('/admin') and 'text/html' in request.headers.get('Accept', ''):
            response = redirect(url_for('auth.login'))
            unset_jwt_cookies(response) # 发生 JWT 异常时也尝试清除 Cookie
            flash(f'认证系统错误: {str(error)}，请重新登录。', 'danger')
            return response, 302
        return jsonify({'message': f'认证系统错误: {str(error)}'}), 401

    app.register_blueprint(auth.auth_bp)
    app.register_blueprint(admin.admin_bp)
    app.register_blueprint(teacher.teacher_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(api_bp)  # 注册微信小程序API蓝图

    @app.route('/')
    def index():
        """根路由：重定向到登录页面"""
        return redirect(url_for('auth.login'))

    return app
