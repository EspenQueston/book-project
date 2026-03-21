cond#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'book_Project.settings')
django.setup()

from manager.models import Order, Book
from decimal import Decimal
import uuid

def create_test_orders():
    """Create some test orders for demonstration"""
    
    # Check if we have any books first
    books = Book.objects.all()
    if not books.exists():
        print("No books found in database. Creating a sample book first...")
        from manager.models import Publisher, Author
        
        # Create a publisher if none exists
        publisher, created = Publisher.objects.get_or_create(
            publisher_name="测试出版社",
            defaults={'publisher_address': "北京市测试区"}
        )
        
        # Create an author if none exists
        author, created = Author.objects.get_or_create(
            author_name="测试作者",
            defaults={'author_age': 35, 'author_email': 'test@example.com'}
        )
        
        # Create a sample book
        book = Book.objects.create(
            book_name="Python编程入门",
            book_price=Decimal("89.99"),
            publisher=publisher
        )
        book.author.add(author)
        print(f"Created sample book: {book.book_name}")
    
    # Create test orders
    orders_data = [
        {
            'customer_name': '张三',
            'customer_email': 'zhangsan@example.com',
            'customer_phone': '13800138000',
            'shipping_address': '北京市朝阳区建国门外大街1号',
            'total_amount': Decimal('99.99'),
            'status': 'pending',
            'payment_status': 'pending'
        },
        {
            'customer_name': '李四',
            'customer_email': 'lisi@example.com',
            'customer_phone': '13800138001',
            'shipping_address': '上海市浦东新区陆家嘴金融中心',
            'total_amount': Decimal('156.80'),
            'status': 'confirmed',
            'payment_status': 'completed'
        },
        {
            'customer_name': '王五',
            'customer_email': 'wangwu@example.com',
            'customer_phone': '13800138002',
            'shipping_address': '广州市天河区珠江新城',
            'total_amount': Decimal('238.50'),
            'status': 'shipped',
            'payment_status': 'completed'
        }
    ]
    
    created_orders = []
    for order_data in orders_data:
        order = Order.objects.create(
            order_number=str(uuid.uuid4())[:8].upper(),
            **order_data
        )
        created_orders.append(order)
        print(f"Created order: {order.order_number} for {order.customer_name}")
    
    print(f"\nSuccessfully created {len(created_orders)} test orders!")
    return created_orders

if __name__ == "__main__":
    create_test_orders()
