# 校园综合管理系统

## 项目简介

本项目为一套面向高校的校园综合管理系统，包含**后端Web管理平台**、**学生Web端**、**微信小程序端**，支持学生、教师、管理员三类角色，涵盖用户认证、学生/教师/课程/成绩管理、数据分析、AI智能分析等功能。后端基于 Flask + SQLAlchemy，前端支持 Web（Layui）和微信小程序，数据可视化采用 ECharts，部分分析功能集成 OpenAI 智能分析。

---

## 目录结构

```
campus-management-system/
│
├── app/                # Flask后端主程序
│   ├── models.py       # ORM模型定义
│   ├── config.py       # 配置文件
│   ├── __init__.py     # 应用工厂
│   ├── routes/         # 路由蓝图（admin, student, teacher, api, auth）
│   ├── static/         # 静态资源
│   └── templates/      # Jinja2模板（Web端页面）
│
├── Wx/                 # 微信小程序端
│   ├── pages/          # 小程序页面
│   ├── utils/          # 工具类
│   ├── ec-canvas/      # ECharts封装
│   └── ...             # 其它配置与资源
│
├── instance/           # 数据库存储
├── requirements.txt    # Python依赖
├── run.py              # 后端启动入口
├── reset_*.py          # 数据初始化/重置脚本
└── ...
```

---

## 主要功能

### 1. 用户与权限管理

- 支持三类角色：管理员、教师、学生
- JWT认证，安全的登录与权限控制
- 支持学号/工号密码登录，微信小程序端支持微信授权登录

### 2. 学生管理

- 学生信息的增删改查
- 支持班级、专业、生源地等多维度筛选
- 个人信息、成绩、课程一站式管理

### 3. 教师管理

- 教师信息管理
- 教师与课程关联

### 4. 课程与成绩管理

- 课程信息管理，支持必修/选修分类
- 成绩录入、修改、批量导入
- 成绩分布、及格率、优秀率等统计

### 5. 数据分析与AI智能分析

- ECharts可视化：成绩分布、专业均分、生源地分布、雷达图等
- AI智能分析（OpenAI）：成绩趋势预测、课程热度预测、风险预警、智能建议

### 6. 微信小程序端

- 成绩查询、课程管理、成绩分析（雷达图、饼图、柱状图）
- 选课/退课、个人信息、智能建议
- 支持微信一键登录与学号密码登录

---

## 技术栈

- **后端**：Flask、Flask-SQLAlchemy、Flask-JWT-Extended、OpenAI
- **数据库**：SQLite（可扩展为MySQL/PostgreSQL）
- **前端Web**：Layui、Jinja2模板
- **小程序端**：微信小程序原生、ECharts
- **数据可视化**：ECharts
- **AI分析**：OpenAI API（未实现）

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 初始化数据库与测试数据

```bash
python run.py
# 或使用 reset_student.py/reset_major_course.py/reset_password.py 等脚本初始化部分数据
```

### 3. 启动后端服务

```bash
python run.py
# 默认监听 http://localhost:5000
```

### 4. 启动微信小程序端

- 使用微信开发者工具打开 `Wx/` 目录
- 勾选“不校验合法域名”
- 配置后端API地址为 `http://localhost:5000`
- 运行并调试小程序

---

## 主要API接口

- `/api/auth/login`  登录
- `/api/student/info`  获取学生信息
- `/api/student/grades`  获取成绩
- `/api/student/courses`  获取课程
- `/api/student/analysis`  获取分析数据
- `/api/student/select_course`  选课
- `/api/student/drop_course`  退课
- `/admin/*`  管理员端管理接口

详见各路由文件和小程序 `utils/api.js`。

---

## 配置说明

- 配置文件：`app/config.py`，支持环境变量和 .env 文件
- OpenAI API Key 需在配置中设置
- 数据库文件默认在 `instance/campus.db`

---

## 常见问题

- **小程序请求域名不合法**：开发时请在微信开发者工具勾选“不校验合法域名”
- **AI分析不可用**：请正确配置 OpenAI API Key
- **数据库初始化失败**：请确保有写权限，或手动删除 `instance/campus.db` 重新初始化

---

## 适用场景

- 高校/中学的学生信息、课程、成绩管理
- 数据可视化与智能分析教学演示
- 微信小程序开发与Flask后端集成示例

---

## 免责声明

本项目仅供学习和教学演示使用，勿用于生产环境。

---

如需详细功能说明、二次开发或遇到问题，欢迎联系开发者团队。 