#!/usr/bin/env python
"""
Script to add 10 random Chinese books with publishers and covers to the database
"""

import os
import sys
import django
import requests
from decimal import Decimal
import random
from pathlib import Path

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'book_Project.settings')
django.setup()

from manager.models import Book, Publisher, Author
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage


def download_book_cover(url, filename):
    """Download book cover image from URL"""
    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        
        # Create the media/book_covers directory if it doesn't exist
        covers_dir = Path('media/book_covers')
        covers_dir.mkdir(parents=True, exist_ok=True)
        
        # Save the image
        filepath = covers_dir / filename
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"✓ Downloaded cover: {filename}")
        return f"book_covers/{filename}"
    except Exception as e:
        print(f"✗ Failed to download {url}: {e}")
        return None


def create_chinese_publishers():
    """Create Chinese publishers if they don't exist"""
    publishers_data = [
        {'name': '清华大学出版社', 'address': '北京市海淀区清华大学'},
        {'name': '机械工业出版社', 'address': '北京市西城区百万庄大街22号'},
        {'name': '人民邮电出版社', 'address': '北京市丰台区成寿寺路11号'},
        {'name': '电子工业出版社', 'address': '北京市海淀区万寿路173号'},
        {'name': '中国青年出版社', 'address': '北京市东城区东四十二条21号'},
        {'name': '华中科技大学出版社', 'address': '湖北省武汉市洪山区珞喻路1037号'},
        {'name': '北京理工大学出版社', 'address': '北京市海淀区中关村南大街5号'},
        {'name': '上海交通大学出版社', 'address': '上海市徐汇区华山路1954号'},
    ]
    
    publishers = []
    for pub_data in publishers_data:
        # First try to get existing publisher
        existing_publisher = Publisher.objects.filter(publisher_name=pub_data['name']).first()
        if existing_publisher:
            publishers.append(existing_publisher)
            print(f"✓ Found existing publisher: {existing_publisher.publisher_name}")
        else:
            # Create new publisher
            publisher = Publisher.objects.create(
                publisher_name=pub_data['name'],
                publisher_address=pub_data['address']
            )
            publishers.append(publisher)
            print(f"✓ Created publisher: {publisher.publisher_name}")
    
    return publishers


def add_chinese_books():
    """Add 10 Chinese books with covers"""
    
    print("Adding 10 Chinese books to the database...")
    print("=" * 60)
    
    # Ensure we have publishers
    publishers = create_chinese_publishers()
    
    # Sample book cover URLs (using placeholder images that look like book covers)
    # These are free placeholder images that resemble book covers
    cover_urls = [
        "https://picsum.photos/300/400?random=1",
        "https://picsum.photos/300/400?random=2", 
        "https://picsum.photos/300/400?random=3",
        "https://picsum.photos/300/400?random=4",
        "https://picsum.photos/300/400?random=5",
        "https://picsum.photos/300/400?random=6",
        "https://picsum.photos/300/400?random=7",
        "https://picsum.photos/300/400?random=8",
        "https://picsum.photos/300/400?random=9",
        "https://picsum.photos/300/400?random=10",
    ]
    
    # Chinese books data with realistic information
    books_data = [
        {
            'name': 'Python程序设计基础',
            'description': '本书系统介绍Python编程语言的基础知识，包括语法、数据结构、函数、面向对象编程等核心概念。适合初学者入门学习，内容循序渐进，配有大量实例和练习。',
            'price': Decimal('89.50'),
            'inventory': 45,
            'sale_num': 23,
            'cover_filename': 'python_basics.jpg'
        },
        {
            'name': '数据结构与算法分析（C++版）',
            'description': '经典的数据结构与算法教材，以C++语言为实现工具，深入讲解各种数据结构和算法的原理与应用。包含大量的分析和实现代码，是计算机专业学生的必读教材。',
            'price': Decimal('126.80'),
            'inventory': 32,
            'sale_num': 18,
            'cover_filename': 'data_structures_cpp.jpg'
        },
        {
            'name': '机器学习实战指南',
            'description': '结合理论与实践的机器学习教程，涵盖监督学习、无监督学习、深度学习等主要领域。提供完整的Python代码实现和真实数据集案例，帮助读者快速掌握机器学习技能。',
            'price': Decimal('158.90'),
            'inventory': 28,
            'sale_num': 31,
            'cover_filename': 'ml_practice.jpg'
        },
        {
            'name': '深入理解Java虚拟机（第3版）',
            'description': 'JVM领域的经典著作，深入剖析Java虚拟机的内部机制。包括内存管理、垃圾收集、字节码执行、类加载等核心技术，是Java开发者进阶必读的技术书籍。',
            'price': Decimal('142.30'),
            'inventory': 38,
            'sale_num': 27,
            'cover_filename': 'jvm_deep_dive.jpg'
        },
        {
            'name': '现代操作系统（第4版）',
            'description': '操作系统领域的权威教材，全面介绍现代操作系统的设计原理和实现技术。涵盖进程管理、内存管理、文件系统、I/O系统等核心内容，理论与实践并重。',
            'price': Decimal('168.70'),
            'inventory': 25,
            'sale_num': 15,
            'cover_filename': 'modern_os.jpg'
        },
        {
            'name': 'Web前端开发技术详解',
            'description': '全面介绍Web前端开发技术，包括HTML5、CSS3、JavaScript、Vue.js、React等主流技术栈。通过项目实战的方式，帮助读者掌握现代前端开发技能。',
            'price': Decimal('108.60'),
            'inventory': 42,
            'sale_num': 35,
            'cover_filename': 'frontend_dev.jpg'
        },
        {
            'name': '计算机网络原理与应用',
            'description': '系统讲解计算机网络的基本原理、协议和应用，涵盖OSI模型、TCP/IP协议族、网络安全、无线网络等内容。配有丰富的实验和案例分析。',
            'price': Decimal('134.20'),
            'inventory': 35,
            'sale_num': 22,
            'cover_filename': 'computer_networks.jpg'
        },
        {
            'name': '人工智能：一种现代方法（第4版）',
            'description': 'AI领域的经典教材，全面介绍人工智能的理论基础和实践方法。涵盖搜索、知识表示、机器学习、自然语言处理、计算机视觉等核心领域。',
            'price': Decimal('198.50'),
            'inventory': 20,
            'sale_num': 12,
            'cover_filename': 'ai_modern_approach.jpg'
        },
        {
            'name': '数据库系统设计与实现',
            'description': '深入讲解数据库系统的设计原理和实现技术，包括存储引擎、查询优化、事务处理、分布式数据库等高级主题。适合数据库相关专业学生和工程师学习。',
            'price': Decimal('156.40'),
            'inventory': 30,
            'sale_num': 19,
            'cover_filename': 'database_systems.jpg'
        },
        {
            'name': '云计算技术与应用实践',
            'description': '全面介绍云计算的技术架构、服务模式和应用实践。涵盖虚拟化、容器技术、微服务架构、DevOps等现代云计算技术栈，配有实际项目案例。',
            'price': Decimal('145.80'),
            'inventory': 33,
            'sale_num': 26,
            'cover_filename': 'cloud_computing.jpg'
        },
    ]
    
    # Authors data
    authors_data = [
        {'name': '张伟教授', 'books': [0]},
        {'name': '李明华', 'books': [1]},
        {'name': '王小红', 'books': [2]},
        {'name': '陈建国', 'books': [3]},
        {'name': '刘晓东', 'books': [4]},
        {'name': '杨丽娟', 'books': [5]},
        {'name': '赵国强', 'books': [6]},
        {'name': '孙美玲', 'books': [7]},
        {'name': '周文华', 'books': [8]},
        {'name': '吴志强', 'books': [9]},
    ]
    
    books = []
    
    # Create books
    for i, book_data in enumerate(books_data):
        # Check if book already exists
        existing_book = Book.objects.filter(name=book_data['name']).first()
        if existing_book:
            print(f"⚠️  Book already exists: {book_data['name']}")
            books.append(existing_book)
            continue
        
        # Download cover image
        cover_path = None
        cover_url = cover_urls[i % len(cover_urls)]
        cover_filename = book_data['cover_filename']
        
        print(f"📚 Creating book: {book_data['name']}")
        print(f"   📷 Downloading cover from: {cover_url}")
        
        cover_path = download_book_cover(cover_url, cover_filename)
        
        # Select random publisher
        publisher = random.choice(publishers)
        
        # Create book
        book = Book.objects.create(
            name=book_data['name'],
            description=book_data['description'],
            price=book_data['price'],
            inventory=book_data['inventory'],
            sale_num=book_data['sale_num'],
            publisher=publisher,
            cover_image=cover_path if cover_path else ''
        )
        
        books.append(book)
        print(f"   ✅ Created book: {book.name}")
        print(f"   📍 Publisher: {publisher.publisher_name}")
        print(f"   💰 Price: ¥{book.price}")
        print(f"   📦 Inventory: {book.inventory}")
        print("-" * 50)
    
    # Create authors and associate with books
    print("\n👥 Creating authors...")
    for author_data in authors_data:
        author, created = Author.objects.get_or_create(
            name=author_data['name']
        )
        
        if created:
            print(f"✓ Created author: {author.name}")
        
        # Associate author with books
        for book_index in author_data['books']:
            if book_index < len(books):
                author.book.add(books[book_index])
                print(f"   📖 Associated with: {books[book_index].name}")
    
    print("\n" + "=" * 60)
    print("✅ Successfully added Chinese books to the database!")
    print("=" * 60)
    
    # Print statistics
    total_books = Book.objects.count()
    total_publishers = Publisher.objects.count()
    total_authors = Author.objects.count()
    
    print(f"📊 Database Statistics:")
    print(f"   📚 Total Books: {total_books}")
    print(f"   🏢 Total Publishers: {total_publishers}")
    print(f"   👥 Total Authors: {total_authors}")
    
    print(f"\n📖 Recently Added Books:")
    for book in books[-5:]:  # Show last 5 books
        authors = book.author_set.all()
        author_names = ", ".join([a.name for a in authors]) if authors else "未知作者"
        print(f"   • {book.name}")
        print(f"     作者: {author_names}")
        print(f"     出版社: {book.publisher.publisher_name}")
        print(f"     价格: ¥{book.price}")
        print(f"     库存: {book.inventory}")
        print()

if __name__ == "__main__":
    add_chinese_books()
