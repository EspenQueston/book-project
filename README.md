# 图书管理系统 (Book Management System)

一个基于Django框架开发的图书管理系统，用于管理图书、作者和出版社信息。

[![GitHub Repository](https://img.shields.io/badge/GitHub-Repository-blue?logo=github)](https://github.com/PoiresGomai/book-project.git)
[![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-4.1+-green?logo=django)](https://www.djangoproject.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue?logo=postgresql)](https://www.postgresql.org/)

## 🚀 快速开始

### 克隆项目
```bash
git clone https://github.com/PoiresGomai/book-project.git
cd book-project
```

### 环境设置 (PostgreSQL版本)
```bash
# 创建conda环境 (推荐)
conda create -n book_project python=3.9 -y
conda activate book_project

# 安装核心依赖
conda install django pillow -c conda-forge -y
pip install psycopg2-binary python-decouple
```

### 数据库配置 (PostgreSQL)
```bash
# 1. 安装PostgreSQL 15+ (如果未安装)
# 下载: https://www.postgresql.org/download/

# 2. 创建数据库和用户
psql -U postgres -c "CREATE DATABASE db_book;"
psql -U postgres -c "CREATE USER bookuser WITH PASSWORD 'BookProject123!';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE db_book TO bookuser;"

# 3. 运行Django迁移
python manage.py makemigrations manager
python manage.py migrate

# 4. 创建示例数据
python migrate_to_postgresql.py
```

### 从MySQL迁移 (可选)
```bash
# 如果你有现有的MySQL数据
python data_migration.py

# 或者使用修复后的mysqldump
mysql -u root -p < mysql_fix_permissions.sql
mysqldump -u migrationuser -p --single-transaction --no-tablespaces db_book > mysql_export.sql
```

### 运行项目
```bash
# 启动开发服务器
python manage.py runserver
```

### 访问系统
- 🌐 **主页**: http://127.0.0.1:8000/
- 🔐 **管理员登录**: http://127.0.0.1:8000/manager/login/
- 📚 **公共图书目录**: http://127.0.0.1:8000/manager/public/
- ⚙️ **Django管理**: http://127.0.0.1:8000/admin/

### 登录凭据
- 👤 **管理员账号**: admin
- 🔑 **密码**: admin123

## 📋 项目简介

本系统是一个完整的图书管理平台，提供了对图书、作者和出版社的全面管理功能。系统已升级为PostgreSQL数据库，具有更好的性能和功能。

## ✨ 功能特点

### 📚 增强的图书管理
- ➕ 添加/编辑/删除图书
- 📝 图书详细描述
- 🖼️ 图书封面上传
- 💰 价格和库存管理
- 📊 销量统计

### 👥 用户管理
- 🔐 管理员登录认证
- 🔒 会话管理
- 👤 用户权限控制

### 🏢 出版社管理
- ➕ 添加新出版社
- ✏️ 编辑出版社信息
- 🗑️ 删除出版社
- 📋 查看所有出版社列表

### ✍️ 作者管理
- ➕ 添加新作者
- ✏️ 编辑作者信息及其关联图书
- 🗑️ 删除作者
- 📋 查看所有作者及其著作列表

### 🌐 公共界面
- 📖 美观的图书浏览界面
- 🔍 图书搜索功能
- 📱 响应式设计
- 🎨 现代化UI界面

## 🛠️ 技术栈

- **🐍 后端**: Django 4.1+
- **🗄️ 数据库**: PostgreSQL 15+ (升级自MySQL)
- **🎨 前端**: HTML5, CSS3, JavaScript
- **📱 UI框架**: Bootstrap 5
- **⚡ 前端库**: jQuery, Font Awesome
- **🔗 数据库驱动**: psycopg2-binary
- **🖼️ 图像处理**: Pillow

## 📁 项目结构

```
book_Project/
├── 📁 book_Project/          # 项目配置目录
│   ├── settings.py        # 项目设置 (PostgreSQL配置)
│   ├── urls.py            # 主URL配置
│   └── wsgi.py            # WSGI配置
├── 📁 manager/               # 应用目录
│   ├── 📁 migrations/        # 数据库迁移文件
│   ├── models.py          # 数据模型 (包含图像字段)
│   ├── views.py           # 视图函数
│   ├── urls.py            # 应用URL配置
│   └── 📁 templates/         # HTML模板
│       ├── 📁 admin/         # 管理界面模板
│       └── 📁 public/        # 公共界面模板
├── 📁 media/                 # 媒体文件 (图书封面)
├── 📁 static/                # 静态资源
├── manage.py              # Django命令行工具
├── requirements.txt       # 依赖文件 (PostgreSQL版本)
├── data_migration.py      # 数据迁移脚本
├── migrate_to_postgresql.py # PostgreSQL迁移脚本
├── setup_guide.md        # 详细安装指南
└── README.md             # 项目说明
```

## 🎯 系统要求

### 必需软件
- **Python**: 3.8+ (推荐 3.9+)
- **PostgreSQL**: 15+ (新数据库)
- **pip**: Python包管理器

### 必需Python包
```bash
Django>=4.1.0,<5.0.0
psycopg2-binary>=2.9.5    # PostgreSQL数据库驱动
Pillow>=10.0.0            # 图像处理
python-decouple>=3.8      # 环境变量配置
```

### 可选工具
- **Git**: 用于版本控制
- **Conda**: 环境管理 (强烈推荐)
- **pgAdmin**: PostgreSQL图形管理工具

## 🗄️ 数据模型 (Enhanced Data Models)

### Manager (管理员)
- `id`: 主键 (int)
- `number`: 账号 (varchar 32)
- `password`: 密码 (varchar 32)
- `name`: 名字 (varchar 32)

### Publisher (出版社)
- `id`: 主键 (bigint)
- `publisher_name`: 出版社名称 (varchar 32)
- `publisher_address`: 出版社地址 (varchar 32)

### Book (图书) - **增强版**
- `id`: 主键 (int)
- `name`: 图书名称 (varchar 32)
- `description`: 图书描述 (text) - **新增**
- `cover_image`: 封面图片 (ImageField) - **新增**
- `price`: 价格 (decimal 5,2)
- `inventory`: 库存数量 (int)
- `sale_num`: 销售数量 (int)
- `publisher`: 外键关联出版社 (bigint)

### Author (作者)
- `id`: 主键 (int)
- `name`: 作者名称 (varchar 32)
- `book`: 多对多关系关联图书

## 🛣️ 路由说明 (URL Routes)

### 公共访问
- `/` - 重定向到管理员界面
- `/manager/public/` - 公共图书目录
- `/manager/public/books/` - 图书列表
- `/manager/public/authors/` - 作者列表
- `/manager/public/authors/<id>/` - 作者详情
- `/manager/public/publishers/` - 出版社列表
- `/manager/public/publishers/<id>/` - 出版社详情

### 管理员功能
- `/manager/login/` - 管理员登录
- `/manager/logout/` - 退出登录
- `/manager/book_list/` - 图书管理
- `/manager/author_list/` - 作者管理
- `/manager/publisher_list/` - 出版社管理

### Django管理
- `/admin/` - Django内置管理界面

## 🚨 故障排除 (Troubleshooting)

### 数据库迁移问题

#### 1. MySQL权限错误
```
mysqldump: Error: 'Access denied; you need PROCESS privilege(s)'
```
**解决方案:**
```sql
-- 以root用户连接MySQL
mysql -u root -p

-- 授予必要权限
GRANT PROCESS, RELOAD ON *.* TO 'bookuser'@'localhost';
GRANT LOCK TABLES ON db_book.* TO 'bookuser'@'localhost';
FLUSH PRIVILEGES;

-- 或使用Django迁移脚本
python data_migration.py
```

#### 2. PostgreSQL连接错误
```
django.db.utils.OperationalError: could not connect to server
```
**解决方案:**
```bash
# 检查PostgreSQL服务
sc query postgresql-x64-15

# 启动服务
net start postgresql-x64-15

# 测试连接
psql -U bookuser -d db_book -h localhost
```

#### 3. Pillow安装失败
```
error: Microsoft Visual C++ 14.0 is required
```
**解决方案:**
```bash
# 使用conda安装 (推荐)
conda install pillow -c conda-forge

# 或使用预编译版本
pip install --only-binary=all Pillow
```

### 迁移步骤
1. **检查现有MySQL数据**
   ```bash
   python mysql_check.py
   ```

2. **修复MySQL权限**
   ```bash
   mysql -u root -p < mysql_fix_permissions.sql
   ```

3. **迁移数据到PostgreSQL**
   ```bash
   python data_migration.py
   ```

4. **验证迁移结果**
   ```bash
   python manage.py shell -c "from manager.models import *; print(f'Books: {Book.objects.count()}, Authors: {Author.objects.count()}')"
   ```

## 🔒 安全注意事项

1. **🔐 密码安全**: 生产环境应实现密码加密
2. **🗄️ 数据库安全**: 使用专用数据库用户，限制权限
3. **🔑 SECRET_KEY**: 确保Django的SECRET_KEY在生产环境中是唯一且安全的
4. **🚫 DEBUG模式**: 生产环境应设置 `DEBUG = False`
5. **📁 媒体文件**: 配置适当的文件上传限制

## 🎯 使用说明

1. **访问公共界面**
   - 浏览图书目录和详细信息
   - 查看作者和出版社信息

2. **管理员登录**
   - 使用admin/admin123登录管理系统

3. **图书管理**
   - 添加图书时可上传封面和描述
   - 编辑现有图书信息

4. **数据统计**
   - 查看销量和库存统计
   - 分析出版社和作者数据

## 📞 联系方式

- **GitHub**: [PoiresGomai](https://github.com/PoiresGomai)
- **项目仓库**: [book-project](https://github.com/PoiresGomai/book-project.git)

## 📄 许可证 (License)

此项目采用 MIT 许可证 - 详情请参阅 [LICENSE](LICENSE) 文件

---

⭐ 如果这个项目对你有帮助，请给它一个 star！

## 🔄 更新日志

### v2.0 - PostgreSQL迁移版本
- ✅ 迁移到PostgreSQL数据库
- ✅ 增加图书封面上传功能
- ✅ 添加图书详细描述字段
- ✅ 改进公共浏览界面
- ✅ 增强响应式设计
- ✅ 提供数据迁移工具

### v1.0 - MySQL原始版本
- ✅ 基础图书管理功能
- ✅ MySQL数据库支持
- ✅ 管理员登录系统

