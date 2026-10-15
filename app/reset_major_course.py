from app import db
from app.models import Course, MajorCourse

# 专业列表
majors = [
    '数据科学与大数据技术',
    '机器人工程',
    '人工智能'
]

# 所有专业必修
common_required = {'高等数学', '大学英语', '数据结构', '操作系统', '数据库原理'}
# 各专业额外必修
ds_required = {'深度学习', '大数据技术'}
re_required = {'机器人学', '机器学习'}
ai_required = {'人工智能导论', '深度学习', '大数据技术'}

# 清空原有数据
MajorCourse.query.delete()
db.session.commit()

all_courses = Course.query.all()

for major in majors:
    for course in all_courses:
        name = course.name
        is_required = False
        if name in common_required:
            is_required = True
        elif major == '数据科学与大数据技术' and name in ds_required:
            is_required = True
        elif major == '机器人工程' and name in re_required:
            is_required = True
        elif major == '人工智能' and name in ai_required:
            is_required = True
        mc = MajorCourse(course_id=course.id, major=major, is_required=is_required)
        db.session.add(mc)
db.session.commit()
print('MajorCourse表已批量初始化完成') 