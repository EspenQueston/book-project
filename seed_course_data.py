"""Seed CourseSection and CourseLesson data for existing courses."""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'book_Project.settings')
django.setup()

from marketplace.models import Course, CourseSection, CourseLesson

def seed_course_data():
    courses = Course.objects.filter(is_active=True)
    print(f"Found {courses.count()} active courses")

    for course in courses:
        # Skip if already has sections
        if CourseSection.objects.filter(course=course).exists():
            print(f"  Skipping '{course.title}' - already has sections")
            continue

        print(f"\n  Creating sections for: {course.title}")
        slug = course.slug

        if 'python' in slug:
            sections_data = [
                ("Python 基础入门", "Python Basics", [
                    ("Python 安装与环境配置", "Learn how to install Python and set up your development environment.", 15, True),
                    ("第一个 Python 程序", "Write and run your first Python script — Hello World!", 12, True),
                    ("变量与数据类型", "Understanding variables, strings, integers, floats, and booleans.", 20, False),
                ]),
                ("控制流与函数", "Control Flow & Functions", [
                    ("条件判断 if/elif/else", "Master conditional statements for decision making in code.", 18, False),
                    ("循环 for 和 while", "Iterate over data with for loops and while loops.", 22, False),
                    ("函数定义与参数", "Define reusable functions with parameters and return values.", 25, False),
                ]),
                ("数据结构与文件操作", "Data Structures & Files", [
                    ("列表与元组", "Work with lists and tuples for storing collections of data.", 20, False),
                    ("字典与集合", "Use dictionaries and sets for efficient data management.", 18, False),
                    ("文件读写操作", "Read from and write to files using Python.", 15, False),
                ]),
            ]
        elif 'web' in slug or 'django' in slug:
            sections_data = [
                ("Web 开发基础", "Web Development Basics", [
                    ("HTML5 核心标签", "Learn essential HTML5 elements for building web pages.", 20, True),
                    ("CSS3 样式与布局", "Style your pages with CSS3 flexbox and grid layouts.", 25, True),
                    ("JavaScript 基础语法", "Introduction to JavaScript variables, functions, and DOM.", 22, False),
                ]),
                ("前端框架入门", "Frontend Framework", [
                    ("Bootstrap 快速上手", "Build responsive layouts using Bootstrap 5.", 18, False),
                    ("React 组件基础", "Create interactive UIs with React components.", 30, False),
                    ("前后端交互 AJAX", "Connect frontend to backend using fetch and AJAX.", 20, False),
                ]),
                ("Django 后端开发", "Django Backend", [
                    ("Django 项目搭建", "Set up a Django project from scratch.", 25, False),
                    ("模型与数据库迁移", "Define models and run database migrations.", 22, False),
                    ("视图与模板系统", "Build views and render templates with context data.", 28, False),
                ]),
            ]
        elif 'data' in slug or '数据' in slug:
            sections_data = [
                ("数据分析基础", "Data Analysis Basics", [
                    ("数据分析概论", "Overview of data analysis workflow and tools.", 15, True),
                    ("NumPy 数组操作", "Work with numerical arrays using NumPy.", 20, False),
                    ("Pandas 数据处理", "Load, clean, and transform data with Pandas.", 25, False),
                ]),
                ("数据可视化", "Data Visualization", [
                    ("Matplotlib 基础绘图", "Create charts and plots with Matplotlib.", 22, False),
                    ("Seaborn 高级图表", "Build beautiful statistical visualizations.", 18, False),
                    ("交互式可视化 Plotly", "Create interactive dashboards with Plotly.", 20, False),
                ]),
            ]
        elif 'english' in slug or '英语' in slug:
            sections_data = [
                ("商务英语基础", "Business English Basics", [
                    ("商务场景自我介绍", "Master professional self-introductions in English.", 12, True),
                    ("邮件写作技巧", "Write clear and professional business emails.", 18, False),
                    ("电话沟通用语", "Handle phone calls professionally in English.", 15, False),
                ]),
                ("高级商务沟通", "Advanced Business Communication", [
                    ("会议主持与参与", "Lead and participate effectively in English meetings.", 20, False),
                    ("谈判策略与表达", "Negotiation strategies and key phrases.", 22, False),
                    ("商务演讲技巧", "Deliver impactful business presentations.", 25, False),
                ]),
            ]
        elif 'ai' in slug or '人工' in slug or 'machine' in slug:
            sections_data = [
                ("AI 与机器学习概论", "AI & ML Overview", [
                    ("什么是人工智能？", "Introduction to artificial intelligence and its applications.", 15, True),
                    ("机器学习基本概念", "Understand supervised, unsupervised, and reinforcement learning.", 20, True),
                    ("Python 机器学习环境", "Set up Jupyter, scikit-learn, and TensorFlow.", 18, False),
                ]),
                ("核心算法", "Core Algorithms", [
                    ("线性回归与逻辑回归", "Implement regression models for prediction tasks.", 25, False),
                    ("决策树与随机森林", "Build tree-based models for classification.", 22, False),
                    ("神经网络入门", "Introduction to neural networks and deep learning.", 30, False),
                ]),
            ]
        elif 'french' in slug or '法语' in slug:
            sections_data = [
                ("法语入门", "French Basics", [
                    ("法语字母与发音", "Learn the French alphabet and pronunciation rules.", 15, True),
                    ("基础问候与自我介绍", "Master everyday greetings and introductions.", 12, True),
                    ("数字与日期表达", "Count in French and express dates.", 10, False),
                ]),
                ("日常法语会话", "Daily French Conversation", [
                    ("餐厅点餐用语", "Order food and drink at a French restaurant.", 18, False),
                    ("购物与讨价还价", "Shop and negotiate prices in French.", 15, False),
                    ("问路与交通", "Ask for directions and use public transport.", 12, False),
                ]),
            ]
        else:
            # Generic course structure
            sections_data = [
                ("课程介绍", "Course Introduction", [
                    ("课程概览", "Overview of what you will learn in this course.", 10, True),
                    ("学习方法指导", "Tips and strategies for effective learning.", 8, False),
                ]),
                ("核心内容", "Core Content", [
                    ("第一课: 基础概念", "Fundamental concepts and terminology.", 20, False),
                    ("第二课: 实战练习", "Hands-on exercises and practice.", 25, False),
                    ("第三课: 进阶技巧", "Advanced techniques and best practices.", 22, False),
                ]),
            ]

        for order_idx, (title, title_en, lessons) in enumerate(sections_data, 1):
            section = CourseSection.objects.create(
                course=course,
                title=title,
                title_en=title_en,
                order=order_idx,
            )
            print(f"    Section {order_idx}: {title}")

            for lesson_idx, (l_title, l_desc, duration, is_free) in enumerate(lessons, 1):
                CourseLesson.objects.create(
                    section=section,
                    title=l_title,
                    description=l_desc,
                    duration_minutes=duration,
                    order=lesson_idx,
                    is_free=is_free,
                )
                print(f"      Lesson {lesson_idx}: {l_title} ({duration}min, {'free' if is_free else 'locked'})")

    total_sections = CourseSection.objects.count()
    total_lessons = CourseLesson.objects.count()
    print(f"\nDone! Total: {total_sections} sections, {total_lessons} lessons")


if __name__ == '__main__':
    seed_course_data()
