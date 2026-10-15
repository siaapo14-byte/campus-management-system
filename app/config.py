import os
from datetime import timedelta
from dotenv import load_dotenv
# from flask import current_app  # 不需要在 config.py 里用 current_app
# import openai  # 不需要在 config.py 里用 openai

load_dotenv()

class Config:
    OPENAI_API_KEY = "sk-你的OpenAI-API-Key"  # ChatGPT API Key
    # 应用程序的通用密钥，用于会话管理、CSRF保护等
    # 生产环境中应从环境变量获取，并使用一个复杂、随机的字符串
    SECRET_KEY = os.environ.get('SECRET_KEY') or '5456154654561'
    
    # SQLite 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), '../instance/campus.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT 配置 - 必须确保这个密钥在整个应用中是唯一的且被所有 JWT 相关操作使用
    # 生产环境中同样应从环境变量获取，并使用一个复杂、随机的字符串
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or '564646546423235465135'
    
    # JWT 令牌的有效期
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7) # ✅ 将有效期从1天改为7天
    
    # JWT 令牌的查找位置（头部和 Cookie）
    JWT_TOKEN_LOCATION = ["headers", "cookies"]
    
    # JWT Cookie 是否只在安全连接（HTTPS）下发送 (开发环境设置为 False)
    JWT_COOKIE_SECURE = False 
    
    # 禁用 CSRF 保护 (开发环境中可以暂时禁用，生产环境强烈建议启用)
    JWT_COOKIE_CSRF_PROTECT = False 

    # 分页设置
    ITEMS_PER_PAGE = 10
    
# openai.api_key = current_app.config.get("OPENAI_API_KEY")