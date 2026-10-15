from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date
from enum import Enum # 导入 Enum
import random
import string

db = SQLAlchemy()

# ✅ 新增：Role 枚举定义
class Role(Enum):
    ADMIN = 'Admin'
    STUDENT = 'Student'
    TEACHER = 'Teacher'

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False) # 存储密码哈希值
    # email = db.Column(db.String(120), unique=True, nullable=True) # 根据需要添加 email 字段
    role = db.Column(db.Enum(Role), nullable=False, default=Role.STUDENT)

    # 定义与 Student 和 Teacher 的关系
    # 如果您的 Student 和 Teacher 表中没有 user_id，需要先添加
    student = db.relationship('Student', backref='user', uselist=False, lazy=True, primaryjoin="User.id==Student.user_id")
    teacher = db.relationship('Teacher', backref='user', uselist=False, lazy=True, primaryjoin="User.id==Teacher.user_id")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            # 'email': self.email, # 如果有 email 字段，取消注释
            'role': self.role.value if self.role else None
        }

    def __repr__(self):
        return f'<User {self.username} ({self.role.value})>'

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    gender = db.Column(db.String(10), nullable=True) # 添加 gender 字段
    major = db.Column(db.String(80), nullable=False)
    class_name = db.Column(db.String(80), nullable=True) # 添加 class_name 字段
    birthdate = db.Column(db.Date, nullable=True)
    enrollment_date = db.Column(db.Date, nullable=True)
    hometown = db.Column(db.String(80), nullable=True) # 添加 hometown 字段

    # ✅ 新增：关联到 User 模型，确保 user_id 字段在数据库表中存在
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'name': self.name,
            'gender': self.gender,
            'major': self.major,
            'class_name': self.class_name,
            'birthdate': self.birthdate.strftime('%Y-%m-%d') if self.birthdate else None,
            'enrollment_date': self.enrollment_date.strftime('%Y-%m-%d') if self.enrollment_date else None,
            'hometown': self.hometown,
            'user_id': self.user_id
        }

    def __repr__(self):
        return f'<Student {self.name}>'

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.String(20), unique=True, nullable=True) # 假设 teacher_id 可为空，如果唯一且必填，请设为 nullable=False
    name = db.Column(db.String(80), nullable=False)
    gender = db.Column(db.String(10), nullable=True) # 添加 gender 字段
    title = db.Column(db.String(80), nullable=True) # 添加 title 字段
    department = db.Column(db.String(80), nullable=True)

    # ✅ 新增：关联到 User 模型，确保 user_id 字段在数据库表中存在
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'teacher_id': self.teacher_id,
            'name': self.name,
            'gender': self.gender,
            'title': self.title,
            'department': self.department,
            'user_id': self.user_id
        }

    def __repr__(self):
        return f'<Teacher {self.name}>'

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=True) # 课程可以没有老师，如果必选请设为 False
    credits = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=True)
    type = db.Column(db.String(20), nullable=False, default='必修')  # 新增字段，必修/选修
    teacher = db.relationship('Teacher', backref='courses_taught') # backref 名称建议更明确

    def to_dict(self):
        return {
            'id': self.id,
            'course_id': self.course_id,
            'name': self.name,
            'teacher_id': self.teacher_id,
            'teacher_name': self.teacher.name if self.teacher else 'N/A',
            'credits': self.credits,
            'description': self.description,
            'type': self.type
        }

    def __repr__(self):
        return f'<Course {self.name}>'

class Grade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    score = db.Column(db.Float, nullable=True)
    student = db.relationship('Student', backref='grades_received') # backref 名称建议更明确
    course = db.relationship('Course', backref='grades_given') # backref 名称建议更明确

    # Add a unique constraint to prevent a student from having multiple grades for the same course
    __table_args__ = (db.UniqueConstraint('student_id', 'course_id', name='_student_course_uc'),)

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'student_name': self.student.name if self.student else 'N/A',
            'student_id_num': self.student.student_id if self.student else 'N/A',
            'course_id': self.course_id,
            'course_name': self.course.name if self.course else 'N/A',
            'course_type': self.course.type if self.course and hasattr(self.course, 'type') else 'N/A',
            'credits': self.course.credits if self.course else 'N/A',
            'teacher_name': self.course.teacher.name if self.course and self.course.teacher else 'N/A',
            'score': self.score
        }

    def __repr__(self):
        return f'<Grade {self.grade}>'

class MajorCourse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    major = db.Column(db.String(80), nullable=False)
    is_required = db.Column(db.Boolean, nullable=False, default=True)  # True=必修, False=选修
    course = db.relationship('Course', backref='major_requirements')

    def to_dict(self):
        return {
            'id': self.id,
            'course_id': self.course_id,
            'major': self.major,
            'is_required': self.is_required
        }

def random_chinese_name():
    # 常用姓氏
    surnames = ['赵','钱','孙','李','周','吴','郑','王','冯','陈','褚','卫','蒋','沈','韩','杨','朱','秦','尤','许','何','吕','施','张','孔','曹','严','华','金','魏','陶','姜','戚','谢','邹','喻','柏','水','窦','章','云','苏','潘','葛','奚','范','彭','郎','鲁','韦','昌','马','苗','凤','花','方','俞','任','袁','柳','酆','鲍','史','唐','费','廉','岑','薛','雷','贺','倪','汤','滕','殷','罗','毕','郝','邬','安','常','乐','于','时','傅','皮','卞','齐','康','伍','余','元','卜','顾','孟','平','黄','和','穆','萧','尹']
    # 常用名
    names = [
        '伟','芳','娜','秀英','敏','静','丽','强','磊','军','洋','勇','艳','杰','娟','涛','明','超','秀兰','霞','平','刚','桂英','丹','萍','鑫','玉兰','飞','玲','桂兰','英','梅','波','斌','宇','浩','凯','秀珍','鹏','华','慧','巧','旭','健','俊','帆','雪','龙','晨','瑞','博','欣','玉','宁','建华','玉珍','春梅','志强','燕','文','玉英','志刚','雪梅','志伟','子','佳','倩','欣怡','梓涵','子轩','梓萱','子涵','雨欣','嘉怡','佳怡','子怡','梓怡','欣妍','佳琪','子萱','梓琪','子妍','梓妍','欣怡','佳欣','子琪','梓欣','子琪','梓涵','子涵','梓萱','子萱','梓琪','子琪','梓妍','子妍','梓欣','子欣','梓怡','子怡','梓琪','子琪','梓涵','子涵','梓萱','子萱','梓妍','子妍','梓欣','子欣','梓怡','子怡'
    ]
    # 姓+1~2字名，保证总长不超过3
    surname = random.choice(surnames)
    name_len = random.choice([1,2])
    name = ''.join(random.choices(names, k=name_len))
    if len(surname + name) > 3:
        name = name[:(3-len(surname))]
    return surname + name

def generate_mock_data(app, db, num_students=100, num_courses=8, num_teachers=10):
    import random
    from datetime import date

    with app.app_context():
        # 清空所有表，确保不会因重复数据报错（仅开发/测试环境使用）
        db.drop_all()
        db.create_all()

        # Create Admin User (if not exists)
        admin_username = 'admin'
        admin_password = 'admin_password_123'
        if not User.query.filter_by(username=admin_username, role=Role.ADMIN).first():
            admin_user = User(
                username=admin_username,
                role=Role.ADMIN
            )
            admin_user.set_password(admin_password)
            db.session.add(admin_user)
            db.session.commit()
            print(f"Created initial admin user: {admin_username}")
        else:
            print(f"Admin user '{admin_username}' already exists.")

        # 生成班级与专业映射（中文）
        class_major_map = {
            '23016101': '数据科学与大数据技术',
            '23016102': '数据科学与大数据技术',
            '23016201': '机器人工程',
            '23016301': '人工智能',
            '23016302': '人工智能',
            '23016303': '人工智能',
        }
        # 生成班级名映射（中文）
        class_name_map = {
            '23016101': '23016101班',
            '23016102': '23016102班',
            '23016201': '23016201班',
            '23016301': '23016301班',
            '23016302': '23016302班',
            '23016303': '23016303班',
        }
        # 生成生源地列表（中文，详细到市）
        hometowns = [
            '四川-遂宁','广西-来宾','广东-广州','江苏-南京','山东-济南','河南-郑州','河北-石家庄','湖南-长沙','湖北-武汉','浙江-杭州',
            '福建-福州','江西-南昌','辽宁-沈阳','吉林-长春','黑龙江-哈尔滨','陕西-西安','山西-太原','云南-昆明','贵州-贵阳','重庆-重庆',
            '北京-北京','上海-上海','天津-天津'
        ]
        # 课程名（中文）
        course_names = [
            '高等数学', '大学英语', '数据结构', '人工智能导论', '机器学习', '深度学习', '大数据技术', '机器人学', '操作系统', '数据库原理'
        ]

        # Create teachers
        teachers = []
        for i in range(num_teachers):
            teacher_id = f'T{i+1:03}'
            name = random_chinese_name()
            gender = random.choice(['男','女'])
            title = random.choice(['教授','副教授','讲师'])
            department = ''  # 老师不再生成专业
            t = Teacher(
                teacher_id=teacher_id,
                name=name,
                gender=gender,
                title=title,
                department=department
            )
            teachers.append(t)
            db.session.add(t)
            # Create a user for each teacher
            teacher_user = User(
                username=f'teacher{i+1}',
                role=Role.TEACHER
            )
            teacher_user.set_password('password123')
            db.session.add(teacher_user)
            db.session.flush()
            t.user_id = teacher_user.id
            db.session.add(t)
        db.session.commit()
        print(f"Generated {num_teachers} teachers.")

        # Create courses（生成课程号和课程名）
        courses = []
        available_teachers = Teacher.query.all()
        if not available_teachers:
            print("No teachers available to assign to courses. Please create teachers first.")
            return 0, 0, 0
        for i in range(num_courses):
            course = Course(
                course_id=f'C{i+1:03}',
                name=course_names[i % len(course_names)],
                credits=random.choice([2, 3, 4]),
                teacher_id=random.choice(available_teachers).id,
                description=f'{course_names[i % len(course_names)]}课程简介'
            )
            courses.append(course)
            db.session.add(course)
        db.session.commit()
        print(f"Generated {num_courses} courses.")

        # 按班级循环生成学生，确保学号唯一
        students = []
        student_count = 0
        for class_code in class_major_map.keys():
            for seq_num in range(1, 31):  # 每班最多30人
                if student_count >= num_students:
                    break
                seq = f'{seq_num:02}'
                student_id = f'{class_code}{seq}'
                name = random_chinese_name()
                gender = random.choice(['男','女'])
                major = class_major_map[class_code]
                class_name = class_name_map[class_code]
                birthdate = date(2005, random.randint(1,12), random.randint(1,28))
                enrollment_date = date(2023, 9, 1)
                hometown = random.choice(hometowns)
                s = Student(
                    student_id=student_id,
                    name=name,
                    gender=gender,
                    major=major,
                    class_name=class_name,
                    birthdate=birthdate,
                    enrollment_date=enrollment_date,
                    hometown=hometown
                )
                students.append(s)
                db.session.add(s)
                db.session.flush()
                # 用户管理逻辑：一个账号只能绑定一个已知的学生
                existing_user = User.query.filter_by(username=student_id).first()
                if not existing_user:
                    student_user = User(
                        username=student_id,
                        role=Role.STUDENT
                    )
                    student_user.set_password('password123')
                    db.session.add(student_user)
                    db.session.flush()
                    s.user_id = student_user.id
                    db.session.add(s)
                else:
                    s.user_id = existing_user.id
                    db.session.add(s)
                student_count += 1
        db.session.commit()
        print(f"Generated {student_count} students.")

        # 教师账号唯一绑定
        for i, t in enumerate(teachers):
            username = f'teacher{i+1}'
            existing_user = User.query.filter_by(username=username).first()
            if not existing_user:
                teacher_user = User(
                    username=username,
                    role=Role.TEACHER
                )
                teacher_user.set_password('password123')
                db.session.add(teacher_user)
                db.session.flush()
                t.user_id = teacher_user.id
                db.session.add(t)
            else:
                t.user_id = existing_user.id
                db.session.add(t)
        db.session.commit()

        # Create grades
        available_students = Student.query.all()
        available_courses = Course.query.all()

        for student in available_students:
            # Each student takes 3-5 random courses
            num_courses_for_student = random.randint(3, 5)
            selected_courses = random.sample(available_courses, min(num_courses_for_student, len(available_courses)))

            for course in selected_courses:
                # Check if a grade already exists for this student and course
                existing_grade = Grade.query.filter_by(student_id=student.id, course_id=course.id).first()
                if not existing_grade:
                    grade = Grade(
                        student_id=student.id,
                        course_id=course.id,
                        score=random.randint(50, 100) # Random score between 50 and 100
                    )
                    db.session.add(grade)
        db.session.commit()
        print("Generated grades.")

        return num_students, num_courses, num_teachers # Return all counts
