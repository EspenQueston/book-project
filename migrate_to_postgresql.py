"""
Migration Script: MySQL to PostgreSQL
Django Book Management System

This script helps migrate from MySQL to PostgreSQL database.
Run this after setting up PostgreSQL and before running Django migrations.
"""

import os
import sys
import django
from django.conf import settings

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'book_Project.settings')
django.setup()

from manager.models import Manager, Publisher, Book, Author

def create_sample_data():
    """Create sample data for testing the PostgreSQL migration"""
    
    print("Creating sample data for PostgreSQL database...")
    
    try:
        # Create managers
        print("Creating managers...")
        manager1, created = Manager.objects.get_or_create(
            number='admin',
            defaults={'password': 'admin123', 'name': 'Administrator'}
        )
        if created:
            print(f"✓ Created manager: {manager1.name}")
        else:
            print(f"✓ Manager already exists: {manager1.name}")
            
        manager2, created = Manager.objects.get_or_create(
            number='manager',
            defaults={'password': 'manager123', 'name': 'Manager User'}
        )
        if created:
            print(f"✓ Created manager: {manager2.name}")
        else:
            print(f"✓ Manager already exists: {manager2.name}")

        # Create publishers
        print("\nCreating publishers...")
        publishers_data = [
            {'name': '清华大学出版社', 'address': '北京市海淀区清华大学'},
            {'name': '机械工业出版社', 'address': '北京市西城区百万庄大街22号'},
            {'name': '人民邮电出版社', 'address': '北京市丰台区成寿寺路11号'},
            {'name': '电子工业出版社', 'address': '北京市海淀区万寿路173号'},
            {'name': '中国青年出版社', 'address': '北京市东城区东四十二条21号'}
        ]
        
        publishers = []
        for pub_data in publishers_data:
            pub, created = Publisher.objects.get_or_create(
                publisher_name=pub_data['name'],
                defaults={'publisher_address': pub_data['address']}
            )
            publishers.append(pub)
            if created:
                print(f"✓ Created publisher: {pub.publisher_name}")
            else:
                print(f"✓ Publisher already exists: {pub.publisher_name}")

        # Create books
        print("\nCreating books...")
        books_data = [
            {
                'name': 'Python编程从入门到实践(第2版)',
                'description': '一本优秀的Python编程入门书籍，内容全面，实例丰富，适合初学者学习。书中包含大量的实践项目，帮助读者快速掌握Python编程技能。',
                'price': 89.99,
                'inventory': 50,
                'sale_num': 25,
                'publisher': publishers[0]
            },
            {
                'name': 'Django Web开发指南',
                'description': '全面介绍Django框架的权威指南，包含最佳实践和高级技巧。适合有一定Python基础的开发者学习Web开发。',
                'price': 119.99,
                'inventory': 30,
                'sale_num': 15,
                'publisher': publishers[1]
            },
            {
                'name': '数据库系统概论(第5版)',
                'description': '经典的数据库教材，理论与实践相结合，深入浅出。涵盖关系数据库、SQL语言、数据库设计等核心内容。',
                'price': 79.99,
                'inventory': 40,
                'sale_num': 35,
                'publisher': publishers[2]
            },
            {
                'name': 'JavaScript高级程序设计',
                'description': 'JavaScript开发的经典教材，深入讲解JavaScript语言特性和高级编程技巧。适合前端开发工程师进阶学习。',
                'price': 99.99,
                'inventory': 35,
                'sale_num': 28,
                'publisher': publishers[0]
            },
            {
                'name': '深入理解计算机系统',
                'description': '计算机科学经典教材，从程序员的角度深入理解计算机系统。涵盖处理器、内存、存储等核心概念。',
                'price': 139.99,
                'inventory': 25,
                'sale_num': 18,
                'publisher': publishers[3]
            },
            {
                'name': 'Linux系统管理技术手册',
                'description': 'Linux系统管理的权威指南，包含系统安装、配置、维护等方面的详细说明。适合系统管理员和运维工程师。',
                'price': 109.99,
                'inventory': 28,
                'sale_num': 22,
                'publisher': publishers[4]
            }
        ]
        
        books = []
        for book_data in books_data:
            book, created = Book.objects.get_or_create(
                name=book_data['name'],
                defaults={
                    'description': book_data['description'],
                    'price': book_data['price'],
                    'inventory': book_data['inventory'],
                    'sale_num': book_data['sale_num'],
                    'publisher': book_data['publisher']
                }
            )
            books.append(book)
            if created:
                print(f"✓ Created book: {book.name}")
            else:
                print(f"✓ Book already exists: {book.name}")

        # Create authors
        print("\nCreating authors...")
        authors_data = [
            {'name': '埃里克·马瑟斯', 'books': [0]},  # Python编程
            {'name': '威廉·文森特', 'books': [1]},    # Django
            {'name': '王珊', 'books': [2]},           # 数据库
            {'name': '萨师煊', 'books': [2]},         # 数据库(合著)
            {'name': '尼古拉斯·扎卡斯', 'books': [3]}, # JavaScript
            {'name': '兰德尔·布莱恩特', 'books': [4]}, # 计算机系统
            {'name': '大卫·奥哈利伦', 'books': [4]},   # 计算机系统(合著)
            {'name': '埃维·内梅思', 'books': [5]},     # Linux
            {'name': '加思·斯奈德', 'books': [5]},     # Linux(合著)
        ]
        
        for author_data in authors_data:
            author, created = Author.objects.get_or_create(
                name=author_data['name']
            )
            
            if created:
                print(f"✓ Created author: {author.name}")
            else:
                print(f"✓ Author already exists: {author.name}")
                
            # Associate author with books
            for book_index in author_data['books']:
                if book_index < len(books):
                    author.book.add(books[book_index])
                    
        print("\n" + "="*50)
        print("✅ Sample data creation completed!")
        print("="*50)
        
        # Print statistics
        print(f"📊 Database Statistics:")
        print(f"   - Managers: {Manager.objects.count()}")
        print(f"   - Publishers: {Publisher.objects.count()}")
        print(f"   - Books: {Book.objects.count()}")
        print(f"   - Authors: {Author.objects.count()}")
        
        # Test queries
        print(f"\n📚 Sample Books:")
        for book in Book.objects.all()[:3]:
            authors = book.author_set.all()
            author_names = ", ".join([a.name for a in authors]) if authors else "未知作者"
            print(f"   - {book.name} by {author_names} (¥{book.price})")
            
    except Exception as e:
        print(f"❌ Error creating sample data: {e}")
        return False
        
    return True

def test_database_connection():
    """Test PostgreSQL database connection"""
    
    print("Testing PostgreSQL database connection...")
    
    try:
        from django.db import connection
        cursor = connection.cursor()
        
        # Test basic connection
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ PostgreSQL connection successful!")
        print(f"   Database version: {version[:50]}...")
        
        # Test table creation
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        
        if tables:
            print(f"✅ Found {len(tables)} tables in database:")
            for table in tables:
                print(f"   - {table[0]}")
        else:
            print("⚠️  No tables found. Run migrations first:")
            print("   python manage.py makemigrations manager")
            print("   python manage.py migrate")
            
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("\n🔧 Troubleshooting steps:")
        print("1. Ensure PostgreSQL service is running")
        print("2. Check database credentials in settings.py")
        print("3. Verify database 'db_book' exists")
        print("4. Check user 'bookuser' has proper permissions")
        return False

def main():
    """Main migration function"""
    
    print("="*60)
    print("🐘 Django Book Management System")
    print("   MySQL to PostgreSQL Migration Script")
    print("="*60)
    
    # Test database connection first
    if not test_database_connection():
        print("\n❌ Migration aborted due to database connection issues.")
        return
    
    print("\n" + "-"*50)
    
    # Create sample data
    if create_sample_data():
        print("\n🎉 Migration completed successfully!")
        print("\n📋 Next steps:")
        print("1. Start the Django development server:")
        print("   python manage.py runserver")
        print("\n2. Test the application:")
        print("   - Main app: http://127.0.0.1:8000/")
        print("   - Django admin: http://127.0.0.1:8000/admin/")
        print("   - Manager login: http://127.0.0.1:8000/manager/")
        print("   - Public catalog: http://127.0.0.1:8000/manager/public/")
        print("\n3. Login credentials:")
        print("   - Manager: admin / admin123")
        print("   - Django admin: Create with 'python manage.py createsuperuser'")
    else:
        print("\n❌ Migration failed. Please check the error messages above.")

if __name__ == "__main__":
    main()
